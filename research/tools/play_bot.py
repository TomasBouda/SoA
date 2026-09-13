"""A program at the controls: reads the mission out of the running game,
gives orders through the game's mailbox, checks what happened.

What it knows
-------------
The squad is the pointer array at [UIPlayer+0x78], the UIPlayer at
[[0x875A84]+0x18]; a unit's position is the floats at +0x54/+0x58 and the
point it is walking to at +0x304/+0x308. The camera is [0x8838E8].

The screen and the world are tied together by the view and projection
matrices the game hands Direct3D, read out of the device through the mailbox
(ui_inject.matrices): clip = world . View . Proj, the screen being the game's
own 800x600 with x = 400 + 400 nx and y = 300 - 300 ny. Unprojecting a screen
point and cutting the ray with the ground plane gives the same answer as the
game's own pick at the centre of the screen to two decimals - and, unlike
that pick, it answers everywhere.

Orders go through the mailbox too (ui_inject.order): the selected units are
sent to a world point exactly as after a right click, with no mouse, no
window and no focus involved. The active pause (P) makes thinking free.

Verified: a unit sent to (400, 850) arrived at (400.0, 850.0), then (392,
845) at (392.0, 845.0).

Usage:
    python play_bot.py --status                 the squad, where each is going, the camera
    python play_bot.py --goto 400,850           the selected units go there (through the mailbox)
    python play_bot.py --screen 400,300         what world point is under that screen point
    python play_bot.py --project 400,850        where that world point is on the screen
    python play_bot.py --watch 10               the squad's positions for ten seconds
    python play_bot.py --shot                   a picture of the game window (GDI, from outside)
    python play_bot.py --enemies                every hostile unit with its health, nearest first
    python play_bot.py --unit 2 --move 430,820  that unit runs there
    python play_bot.py --unit 2 --attack        that unit attacks the nearest enemy
"""
import argparse
import ctypes
import math
import os
import struct
import time
from ctypes import wintypes

import numpy as np

import scan_memory as sm
import ui_inject

UIPLAYER_HOLDER = 0x00875A84
UIPLAYER_VTABLE = 0x007CFE38
KIMISSION_GLOBAL = 0x00875A58
CAMERA_GLOBAL = 0x008838E8
WORLD_GLOBAL = 0x00880F98
PAUSED_BYTE = 0x007B4680

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
KEYEVENTF_KEYUP = 0x0002
VK_SPACE, VK_P = 0x20, 0x50


class Game:
    def __init__(self):
        self.pid = sm.find_process('soa.exe')
        if not self.pid:
            raise SystemExit('soa.exe is not running')
        self.h = sm.open_process(self.pid, write=True)
        self.hwnd = self.find_window()

    def find_window(self):
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, lparam):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == self.pid and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
            return True
        user32.EnumWindows(cb, 0)
        return found[0] if found else None

    def dword(self, a):
        b = sm.read(self.h, a, 4)
        return struct.unpack('<I', b)[0] if b else 0

    def flt(self, a):
        b = sm.read(self.h, a, 4)
        return struct.unpack('<f', b)[0] if b else 0.0

    def game_folder(self):
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(self.h, 0, buf, ctypes.byref(size))
        return os.path.dirname(buf.value)

    # --------------------------------------------------------------- state

    def in_mission(self):
        return self.dword(WORLD_GLOBAL) != 0

    # ------------------------------------------------------- the mission

    def players(self):
        """Every player of the mission, out of KIMission [0x875A58] +0x2C,
        the PlayerLibrary, whose vector at +0x20 holds the UIPlayer and the
        AI players alike. A player's units are the vector at +0x78, its
        number at +0x20 (the party the map draws is that plus two), and its
        diplomacy the map<int, int> at +0x90, player number -> 0 neutral,
        1 enemy, 2 friend (the order the editor's SetDiplomacy names come
        in at 0x5578E4; a player not in the map is neutral). Reading it the
        other way round - 0 enemy, 1 friend - cost a squad: the "friends"
        at the monastery had a tank."""
        mission = self.dword(KIMISSION_GLOBAL)
        library = self.dword(mission + 0x2C) if mission else 0
        if not library:
            return []
        first, last = self.dword(library + 0x20), self.dword(library + 0x24)
        out = []
        for a in range(first, last, 4):
            p = self.dword(a)
            out.append({'address': p, 'index': self.dword(p + 0x20), 'ui': self.dword(p) == UIPLAYER_VTABLE,
                        'units': [self.dword(u) for u in range(self.dword(p + 0x78), self.dword(p + 0x7C), 4)],
                        'diplomacy': self._map(self.dword(p + 0x94))})
        return out

    def _map(self, head):
        """A Microsoft std::map<int,int>: head -> root at +4; node left +0,
        parent +4, right +8, key +0xC, value +0x10; the shared nil node is at
        [0x875A78]."""
        nil = self.dword(0x875A78)
        out = {}

        def walk(n, depth=0):
            if n in (0, nil) or depth > 64:
                return
            walk(self.dword(n), depth + 1)
            out[self.dword(n + 0xC)] = self.dword(n + 0x10)
            walk(self.dword(n + 8), depth + 1)
        walk(self.dword(head + 4))
        return out

    def unit(self, u):
        """What a unit object says about itself: class (+8: 4 soldiers, 0
        vehicles), type (+4), position, and its health - +0xD0 the most and
        +0xD4 what is left of it, +0xD8/+0xDC the same for the armour
        (100/2500 on a tank, 0 on a soldier). Read off ApplyDamage 0x57C950
        and the getters it goes through, +0x7C/+0x84/+0xA8/+0xB0. Dead is
        +0x17C above zero - the first thing the command acceptor 0x580B40
        checks (0x587430); a body keeps its last hit points."""
        return {'address': u, 'vtable': self.dword(u), 'kind': self.dword(u + 8), 'type': self.dword(u + 4),
                'x': self.flt(u + 0x54), 'y': self.flt(u + 0x58), 'z': self.flt(u + 0x5C),
                'hp': self.dword(u + 0xD4), 'hp_max': self.dword(u + 0xD0),
                'armour': self.dword(u + 0xDC), 'armour_max': self.dword(u + 0xD8),
                'dead': self.dword(u + 0x17C) > 0, 'player': self.dword(u + 0x198)}

    def action(self, unit):
        """The action the unit is on, +0x178: the id of its current command
        (0x515000 on the command) - 17 waiting, 10 moving, 7 kneeling, 2
        attacking. An attack on a target the unit cannot see, or cannot
        reach, runs out within a second and the unit is back on 17."""
        return self.dword(unit + 0x178)

    NEUTRAL, ENEMY, FRIEND = 0, 1, 2

    def enemies(self):
        """The units of every player the UI player's diplomacy calls enemy,
        alive and on the map (a unit inside a vehicle sits at -1e7, -1e7)."""
        players = self.players()
        me = next((p for p in players if p['ui']), None)
        if not me:
            return []
        out = []
        for p in players:
            if p is me or me['diplomacy'].get(p['index'], self.NEUTRAL) != self.ENEMY:
                continue
            for u in p['units']:
                info = self.unit(u)
                if info['hp'] > 0 and not info['dead'] and info['x'] > -1e6:
                    out.append(info)
        return out

    def squad(self):
        """The UI player's units, the vector at +0x78..+0x7C - the dead are
        taken out of it, so it shrinks as the mission goes badly."""
        holder = self.dword(UIPLAYER_HOLDER)
        player = self.dword(holder + 0x18) if holder else 0
        if not player:
            return []
        out = []
        for a in range(self.dword(player + 0x78), self.dword(player + 0x7C), 4):
            u = self.dword(a)
            if not (0x10000 < u < 0x7fffffff):
                continue
            vt = self.dword(u)
            if not (0x400000 < vt < 0x900000):
                continue
            out.append({'address': u, 'type': self.dword(u + 4),
                        'x': self.flt(u + 0x54), 'y': self.flt(u + 0x58), 'z': self.flt(u + 0x5C)})
        return out

    def position(self, unit):
        return self.flt(unit + 0x54), self.flt(unit + 0x58)

    def target(self, unit):
        return self.flt(unit + 0x304), self.flt(unit + 0x308)

    def camera(self):
        cam = self.dword(CAMERA_GLOBAL)
        if not cam:
            return None
        return {'address': cam,
                'pos': (self.flt(cam + 0x18), self.flt(cam + 0x1C), self.flt(cam + 0x20)),
                'mouse': (self.flt(cam + 0xA4), self.flt(cam + 0xA8))}

    def paused(self):
        b = sm.read(self.h, PAUSED_BYTE, 1)
        return bool(b and b[0])

    # ---------------------------------------------------------- the screen

    def projection(self):
        return Projection(*ui_inject.matrices(self.h))

    # --------------------------------------------------------------- doing

    # The orders a unit takes are virtual calls on it, one slot per
    # Commando_* function of CY2KKIBasicPartyObject (the trace strings in the
    # exe name them, and each is reached from exactly one slot of the KIChar
    # vtable 0x7D66F4). Every one builds a command object, stamps it with the
    # source - 6 is CS_UI, the player - and whether it queues behind the
    # current order (Shift held), and hands it to +0x2E8, which executes it
    # at once in a single-player game. Wrong slot, wrong order: +0x384 is
    # not "attack" but "throw the secondary weapon", which is how this table
    # was checked - with the game's own trace (mask 0x861288 |= 0x40) saying
    # what each call really did.
    FROM_PLAYER = 6
    MOVE_TO, ATTACK_GROUND, ATTACK_TARGET = 0x358, 0x324, 0x328
    STOP_MOVE, WAIT, KNEEL, LIE_DOWN, STAND_UP = 0x370, 0x374, 0x378, 0x37C, 0x380
    GET_IN, GET_OUT, THROW_SECONDARY, THROW_SMOKE, RELOAD = 0x344, 0x348, 0x384, 0x30C, 0x3A0
    PATROL, APPROACH, ESCAPE, LOOT_AREA, USE_EQUIPMENT = 0x35C, 0x320, 0x33C, 0x354, 0x38C

    def goto(self, wx, wy):
        """The selected units go there, through the UIPlayer's own order
        (what a right click does, formation included)."""
        return ui_inject.order(wx, wy, self.h)

    def _order(self, unit, slot, args):
        return ui_inject.call(unit, slot, args, self.h)

    def move(self, unit, x, y, mode=3, queue=0):
        """MoveTo(x, y, mode, flag, source, queue). Mode 3 is what the right
        click passes; a unit sent 25 units away with it was there in three
        seconds."""
        return self._order(unit, self.MOVE_TO, [float(x), float(y), mode, 0, self.FROM_PLAYER, queue])

    def attack(self, unit, target, queue=0):
        """Attack Target(object, flag, source, queue) - the object is a live
        unit address; a stale one from a previous game crashes soa.exe."""
        return self._order(unit, self.ATTACK_TARGET, [target, 0, self.FROM_PLAYER, queue])

    def attack_ground(self, unit, x, y, queue=0):
        return self._order(unit, self.ATTACK_GROUND, [float(x), float(y), 0, self.FROM_PLAYER, queue])

    def stop(self, unit, queue=0): return self._order(unit, self.STOP_MOVE, [self.FROM_PLAYER, queue])
    def stand(self, unit, queue=0): return self._order(unit, self.STAND_UP, [self.FROM_PLAYER, queue])
    def kneel(self, unit, queue=0): return self._order(unit, self.KNEEL, [self.FROM_PLAYER, queue])
    def lie_down(self, unit, queue=0): return self._order(unit, self.LIE_DOWN, [self.FROM_PLAYER, queue])
    def reload(self, unit, queue=0): return self._order(unit, self.RELOAD, [self.FROM_PLAYER, queue])
    def get_out(self, unit, queue=0): return self._order(unit, self.GET_OUT, [0, self.FROM_PLAYER, queue])

    # Healing (button 22) first asks the unit for the medikit object with the
    # plain call 0x5860E0(unit, 0x80) and hands that to UseEquipment(item,
    # patient, 6, 1); the mailbox only makes virtual calls so far, so that one
    # waits.

    def key(self, vk):
        """A key press posted to the game's window, so the keyboard itself is
        left alone (the game reads its keys from the messages)."""
        scan = user32.MapVirtualKeyW(vk, 0)
        user32.PostMessageW(self.hwnd, 0x100, vk, (scan << 16) | 1)
        time.sleep(0.05)
        user32.PostMessageW(self.hwnd, 0x101, vk, (scan << 16) | 0xC0000001)
        time.sleep(0.1)

    def wait_arrival(self, unit, timeout=30):
        """The unit's position once it has stood still for a second and a half."""
        last = None
        still = 0
        t0 = time.time()
        p = self.position(unit)
        while time.time() - t0 < timeout:
            time.sleep(0.5)
            p = self.position(unit)
            if last and abs(p[0] - last[0]) < 0.05 and abs(p[1] - last[1]) < 0.05:
                still += 1
                if still >= 3:
                    return p
            else:
                still = 0
            last = p
        return p

    ACT_WAIT, ACT_ATTACK, ACT_KNEEL, ACT_MOVE = 17, 2, 7, 10

    def hunt(self, reach=25.0, keep_off=80.0, timeout=600):
        """The first plan: the squad closes on the nearest enemy soldier and
        shoots him. Far from the target everybody runs to a point short of
        it - an attack ordered on a unit out of sight is taken (the action
        reads 2) but nothing comes of it, the soldier just stands. Within
        reach every unit not already attacking is told to attack; a dead
        target gives way to the next one. Ends when no enemy is left, or
        nobody is, or time runs out.

        Vehicles are not for rifles: an armoured enemy (kind 0, armour above
        zero) is never a target, and a soldier standing within keep_off of
        one is left alone too - the first hunt ran the squad into a
        courtyard with a tank and lost it."""
        t0 = time.time()
        units = [u['address'] for u in self.squad() if u['x'] > -1e6]
        last_goal = None
        while time.time() - t0 < timeout:
            units = [u for u in units if not self.unit(u)['dead'] and self.unit(u)['x'] > -1e6]
            if not units:
                print('nobody left to give orders to')
                return False
            everyone = self.enemies()
            armour = [e for e in everyone if e['armour_max'] > 0 or e['kind'] == 0]
            enemies = [e for e in everyone if e not in armour
                       and all(math.hypot(e['x'] - a['x'], e['y'] - a['y']) > keep_off for a in armour)]
            if not enemies:
                print('no enemy left to take on with rifles (%d armoured or under armour)' % len(everyone))
                return not everyone
            cx = sum(self.position(u)[0] for u in units) / len(units)
            cy = sum(self.position(u)[1] for u in units) / len(units)
            target = min(enemies, key=lambda e: math.hypot(e['x'] - cx, e['y'] - cy))
            d = math.hypot(target['x'] - cx, target['y'] - cy)
            if d > reach:
                # in legs of at most a hundred units: a goal the path finder
                # cannot reach (inside the enemy camp, say) is simply not
                # walked to, and a leg that ends on open ground gets walked
                step = min(d - reach * 0.8, 100.0)
                goal = (round(cx + (target['x'] - cx) * step / d), round(cy + (target['y'] - cy) * step / d))
                idle = [u for u in units if self.action(u) == self.ACT_WAIT]
                if goal != last_goal or idle:
                    for u in (units if goal != last_goal else idle):
                        ux, uy = self.position(u)
                        self.move(u, goal[0] + (ux - cx) * 0.5, goal[1] + (uy - cy) * 0.5)
                    last_goal = goal
                what = 'closing on %d,%d' % goal
            else:
                last_goal = None
                idle = [u for u in units if self.action(u) != self.ACT_ATTACK]
                for u in idle:
                    self.attack(u, target['address'])
                what = '%d told to attack' % len(idle)
            print('%4.0fs target %08X hp %3d at %.0f: %s; squad hp %s'
                  % (time.time() - t0, target['address'], target['hp'], d, what, [self.unit(u)['hp'] for u in units]))
            time.sleep(3)
        return False

    def screenshot(self, path=None):
        """A picture of the game window. The game takes it itself: F12 is
        bound in the shipped settings and writes shot0000.png and up beside
        soa.exe, so a posted F12 gets the frame whatever the window's state
        - behind others, or on another virtual desktop, where a screen grab
        of its rectangle showed the wallpaper and PrintWindow the last frame
        the compositor had. When no file appears (a state the key is not
        read in) PrintWindow is the fallback. The game's own screenshot call
        driven from a thread of ours, 0x6031B0, took the game down twice
        with a DirectDraw 0x887602F8 whenever a menu or a dialog was up, so
        that route is not used."""
        import glob
        import shutil
        path = path or os.path.join(os.environ.get('CLAUDE_SCRATCH', os.environ.get('TEMP', '.')), 'soa_shot.png')
        folder = self.game_folder()
        pattern = os.path.join(folder, 'shot*.png') if folder else None
        before = set(glob.glob(pattern)) if pattern else set()
        if pattern:
            VK_F12 = 0x7B
            scan = user32.MapVirtualKeyW(VK_F12, 0)
            user32.PostMessageW(self.hwnd, 0x100, VK_F12, (scan << 16) | 1)
            time.sleep(0.05)
            user32.PostMessageW(self.hwnd, 0x101, VK_F12, (scan << 16) | 0xC0000001)
            for _ in range(30):
                time.sleep(0.1)
                new = set(glob.glob(pattern)) - before
                if new:
                    shot = new.pop()
                    time.sleep(0.2)                     # let the game finish writing
                    shutil.move(shot, path)
                    return path
        self.print_window(path)
        return path

    def print_window(self, path):
        """The window's surface from the compositor, PrintWindow with
        PW_RENDERFULLCONTENT; the last frame it has, which is stale when the
        window is not being composed."""
        from PIL import Image
        gdi32 = ctypes.windll.gdi32
        r = wintypes.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(r))
        w, h = r.right, r.bottom
        hdc = user32.GetDC(0)
        mdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        gdi32.SelectObject(mdc, bmp)
        user32.PrintWindow(self.hwnd, mdc, 3)          # PW_CLIENTONLY | PW_RENDERFULLCONTENT
        info = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(mdc, bmp, 0, h, buf, info, 0)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(0, hdc)
        Image.frombuffer('RGBA', (w, h), buf.raw, 'raw', 'BGRA', 0, 1).convert('RGB').save(path)


class Projection:
    """Screen (the game's 800x600) to world and back, from the matrices the
    game draws with. Good until the camera moves - read them again then."""

    def __init__(self, view, proj):
        self.vp = np.array(view) @ np.array(proj)
        self.inv = np.linalg.inv(self.vp)

    def project(self, wx, wy, wz):
        c = np.array([wx, wy, wz, 1.0]) @ self.vp
        c = c[:3] / c[3]
        return float(c[0] * 400 + 400), float(300 - c[1] * 300)

    def unproject(self, sx, sy, z=0.0):
        """The point on the plane of height z under screen (sx, sy)."""
        nx, ny = (sx - 400) / 400.0, (300 - sy) / 300.0
        a = np.array([nx, ny, 0.0, 1.0]) @ self.inv
        b = np.array([nx, ny, 1.0, 1.0]) @ self.inv
        a, b = a[:3] / a[3], b[:3] / b[3]
        t = (z - a[2]) / (b[2] - a[2])
        p = a + t * (b - a)
        return float(p[0]), float(p[1]), float(p[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--goto', metavar='X,Y')
    ap.add_argument('--screen', metavar='SX,SY')
    ap.add_argument('--project', metavar='X,Y')
    ap.add_argument('--watch', type=float, metavar='SECONDS')
    ap.add_argument('--shot', action='store_true')
    ap.add_argument('--unit', type=int, default=None, help='which of the squad to wait for after --goto, or to order')
    ap.add_argument('--kneel', action='store_true')
    ap.add_argument('--stand', action='store_true')
    ap.add_argument('--attack', action='store_true', help='the unit attacks the nearest enemy')
    ap.add_argument('--move', metavar='X,Y', help='the unit runs there')
    ap.add_argument('--enemies', action='store_true', help='every hostile unit, nearest first')
    ap.add_argument('--hunt', action='store_true', help='the squad closes on the nearest enemy and shoots it, until none is left')
    args = ap.parse_args()
    g = Game()

    if args.shot:
        print(g.screenshot())
        return
    if args.watch:
        t0 = time.time()
        while time.time() - t0 < args.watch:
            print('  '.join('%d:(%.1f,%.1f)' % (u['type'], u['x'], u['y']) for u in g.squad()))
            time.sleep(1)
        return
    if args.screen:
        sx, sy = [float(v) for v in args.screen.split(',')]
        z = g.squad()[0]['z'] if g.squad() else 0.0
        print('screen %.0f,%.0f -> world %.1f, %.1f (on the plane z=%.1f)' % ((sx, sy) + g.projection().unproject(sx, sy, z)[:2] + (z,)))
        return
    if args.project:
        wx, wy = [float(v) for v in args.project.split(',')]
        print('world %.1f,%.1f -> screen %.0f,%.0f' % ((wx, wy) + g.projection().project(wx, wy, 0.0)))
        return
    if args.hunt:
        g.hunt()
        return
    if args.enemies:
        sq = g.squad()
        cx = sum(u['x'] for u in sq) / max(len(sq), 1)
        cy = sum(u['y'] for u in sq) / max(len(sq), 1)
        for e in sorted(g.enemies(), key=lambda e: math.hypot(e['x'] - cx, e['y'] - cy)):
            print('%08X kind %d type %5d hp %3d/%-3d at %6.1f,%6.1f  %5.1f from the squad'
                  % (e['address'], e['kind'], e['type'], e['hp'], e['hp_max'], e['x'], e['y'],
                     math.hypot(e['x'] - cx, e['y'] - cy)))
        return
    if args.kneel or args.stand or args.attack or args.move:
        unit = g.squad()[args.unit or 0]['address']
        if args.kneel: print('kneel returned', g.kneel(unit))
        if args.stand: print('stand returned', g.stand(unit))
        if args.move:
            x, y = [float(v) for v in args.move.split(',')]
            print('move returned', g.move(unit, x, y))
        if args.attack:
            p = g.position(unit)
            enemies = sorted(g.enemies(), key=lambda e: math.hypot(e['x'] - p[0], e['y'] - p[1]))
            if not enemies:
                print('no enemy in the mission')
            else:
                print('attack %08X returned %d' % (enemies[0]['address'], g.attack(unit, enemies[0]['address'])))
        return
    if args.goto:
        wx, wy = [float(v) for v in args.goto.split(',')]
        print('order returned', g.goto(wx, wy))
        if args.unit is not None:
            p = g.wait_arrival(g.squad()[args.unit]['address'])
            print('unit %d arrived at %.1f,%.1f (off by %.1f, %.1f)' % (args.unit, p[0], p[1], p[0] - wx, p[1] - wy))
        return

    print('pid %d window %s mission %s paused %s' % (g.pid, hex(g.hwnd or 0), g.in_mission(), g.paused()))
    cam = g.camera()
    if cam:
        print('camera %08X pos %.1f %.1f %.1f  mouse %.0f,%.0f' % ((cam['address'],) + cam['pos'] + cam['mouse']))
    for i, u in enumerate(g.squad()):
        print('unit %d %08X type %d at %.1f,%.1f  going to %.1f,%.1f'
              % ((i, u['address'], u['type'], u['x'], u['y']) + g.target(u['address'])))


if __name__ == '__main__':
    main()
