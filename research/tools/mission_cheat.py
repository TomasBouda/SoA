r"""Sends a mission cheat - endlessmunition, immortalone, winmission ... - into
the running game, the way the launcher's console does (GameLink.RunMissionCheat).

The handler is 0x5ECA70, a thiscall on the mission object taking the whole
line as a tsString by value; it matches the text against its own table
(cheats.md) and ends in ret 0x10, so it disposes of the string itself. The
mission object is the global 0x875AA4 (the StartPing event reads it there,
0x59768A) - the launcher scans the heap for it by its two vtables, 0x7D0568
at the start and 0x7D0564 at +8, because that global was found later; the
scan stays as the fallback and as the check that the global holds a
mission.

endlessmunition and immortalone are toggles: the handler flips a byte
(0x875AA0 and 0x875A30, cases 2 and 3 of its switch at 0x5EE200) and the
byte outlives the mission, so a second call turns the cheat off again - which
is how a whole test ran without ammunition. So those two are asked for as a
state: the byte is read first and the handler only called when it has to
flip.

The same door loads a save: quick load (0x5F26F0) builds the path of
QuickSave.sav and hands it to 0x5F2C10, another method of the mission taking
a tsString by value - given a different full path it loads a different save,
with no menu involved (what the launcher's GameLink.LoadSave does). It needs
a mission running, like quick load; the first mission of a session still
comes through the menus (menu_bot.py --load).

Usage:
    python mission_cheat.py endlessmunition          on (a no-op when it already is)
    python mission_cheat.py endlessmunition=off
    python mission_cheat.py immortalone winmission
    python mission_cheat.py --load BombTest.sav      loads SaveGames\<profile>\BombTest.sav into the running game
"""
import os
import time
import ctypes
import struct
import sys
from ctypes import wintypes

import scan_memory as sm

HANDLER = 0x005ECA70
LOAD_SAVE = 0x005F2C10
FLAGS = {'endlessmunition': 0x00875AA0, 'immortalone': 0x00875A30}
CTOR_TSSTRING = 0x00405D80
VTABLE, VTABLE_2 = 0x007D0568, 0x007D0564
MEMBERS = (0x250, 0x260, 0x270)

k32 = sm.k32
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
k32.CreateRemoteThread.restype = wintypes.HANDLE


def looks_like_mission(h, a):
    head = sm.read(h, a, 0x274)
    if not head or len(head) < 0x274:
        return False
    if struct.unpack_from('<I', head, 0)[0] != VTABLE or struct.unpack_from('<I', head, 8)[0] != VTABLE_2:
        return False
    for m in MEMBERS:
        p = struct.unpack_from('<I', head, m)[0]
        if not (0x10000 <= p < 0x80000000) or not sm.read(h, p, 1):
            return False
    return True


MISSION_GLOBAL = 0x00875AA4


def find_mission(h):
    """The mission object: the global first, the heap when the global does
    not hold one - the image is skipped so the constructor's own mention of
    the vtable does not come up."""
    g = sm.read(h, MISSION_GLOBAL, 4)
    if g:
        a = struct.unpack('<I', g)[0]
        if a and looks_like_mission(h, a):
            return a
    needle = struct.pack('<I', VTABLE)
    for base, size in sm.regions(h):
        if base < 0x900000 and base + size > 0x400000:
            continue
        data = sm.read(h, base, size)
        if not data:
            continue
        i = data.find(needle)
        while i >= 0:
            if i % 4 == 0 and looks_like_mission(h, base + i):
                return base + i
            i = data.find(needle, i + 4)
    return 0


def shellcode(text, flag, mission, method=HANDLER):
    b = b'\x83\xEC\x10'                              # sub esp, 0x10 - room for the tsString
    b += b'\x8B\xCC'                                 # mov ecx, esp
    b += b'\x68' + struct.pack('<I', flag)           # push flag
    b += b'\x68' + struct.pack('<I', text)           # push text
    b += b'\xB8' + struct.pack('<I', CTOR_TSSTRING) + b'\xFF\xD0'   # tsString(text, flag)
    b += b'\xB9' + struct.pack('<I', mission)        # mov ecx, the mission
    b += b'\xB8' + struct.pack('<I', method) + b'\xFF\xD0'         # the method, ret 0x10
    b += b'\xC2\x04\x00'                             # ret 4
    return b


def send(line, h=None, mission=0, method=HANDLER):
    """Sends the line to the method (the cheat handler unless told
    otherwise); for the two toggles, "name" or "name=on" turns the cheat on
    and "name=off" off, whatever state it is in. Returns what the method
    returned, or None when there was nothing to do."""
    h = h or sm.open_process(sm.find_process('soa.exe') or 0, write=True)
    mission = mission or find_mission(h)
    if not mission:
        raise SystemExit('no mission is running - these cheats only work inside one')
    name, _, state = line.partition('=')
    if method == HANDLER and name in FLAGS:
        wanted = state.lower() not in ('off', '0', 'false')
        if bool(sm.read(h, FLAGS[name], 1)[0]) == wanted:
            return None
        line = name
    mem = k32.VirtualAllocEx(h, None, 0x1000, 0x3000, 0x40)
    try:
        sm.write_value(h, mem, line.encode('latin1') + b'\0')
        sm.write_value(h, mem + 0x40, b'\0')
        sm.write_value(h, mem + 0x80, shellcode(mem, mem + 0x40, mission, method))
        t = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(mem + 0x80), None, 0, None)
        k32.WaitForSingleObject(t, 5000)
        code = wintypes.DWORD()
        k32.GetExitCodeThread(t, ctypes.byref(code))
        k32.CloseHandle(t)
        return code.value
    finally:
        k32.VirtualFreeEx(h, ctypes.c_void_p(mem), 0, 0x8000)


def load_save(name, h=None, mission=0):
    r"""Loads <game>\SaveGames\<profile>\<name> (or a full path) into the
    running mission - the saves sit under the profile the player picked, the
    one folder in SaveGames. Waits until the UI player's squad has been rebuilt, up to a
    minute, and says whether it was."""
    import play_bot
    g = play_bot.Game()
    h = h or g.h
    path = name
    if not os.path.isabs(name):
        saves = os.path.join(g.game_folder(), 'SaveGames')
        profiles = [d for d in os.listdir(saves) if os.path.isdir(os.path.join(saves, d))]
        found = [os.path.join(saves, d, name) for d in profiles if os.path.exists(os.path.join(saves, d, name))]
        if not found:
            raise SystemExit('no such save under %s: %s' % (saves, name))
        path = found[0]
    before = [u['address'] for u in g.squad()]
    send(path, h, mission, LOAD_SAVE)
    t0 = time.time()
    while time.time() - t0 < 60:
        time.sleep(1)
        now = g.squad()
        if now and [u['address'] for u in now] != before:
            time.sleep(2)
            return True
        if not now and time.time() - t0 > 10:
            # a bunker save lands on the team screen: two clicks start it
            import menu_bot
            return menu_bot.Menus().wait_mission()
    return False


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == '--load':
        print('loaded' if load_save(sys.argv[2]) else 'the squad did not change - did it load?')
        return
    pid = sm.find_process('soa.exe')
    if not pid:
        raise SystemExit('soa.exe is not running')
    h = sm.open_process(pid, write=True)
    mission = find_mission(h)
    if not mission:
        raise SystemExit('no mission is running - these cheats only work inside one')
    print('mission at %08X' % mission)
    for line in sys.argv[1:]:
        r = send(line, h, mission)
        name = line.partition('=')[0]
        if name in FLAGS:
            print('%s is %s' % (name, 'on' if sm.read(h, FLAGS[name], 1)[0] else 'off'))
        else:
            print('%s -> %d' % (line, r))


if __name__ == '__main__':
    main()
