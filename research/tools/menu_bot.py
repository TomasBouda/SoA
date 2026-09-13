"""Clicks the game from its main menu into a saved game, or from inside a
mission into another one, so a program can start a mission without a person
at the mouse.

The menus are laid out for 800x600 and scaled to whatever the window is, so
the clicks are given in 784x561 (the window the game makes on a 1080p desktop)
and scaled to the client area found. Between clicks the bot waits for the
screen to change (play_bot.Game.screenshot, a GDI grab from outside) instead
of sleeping a fixed time, which is what made the earlier version miss a step
on a slow load.

The clicks and keys are posted to the game's window as messages
(WM_MOUSEMOVE, WM_LBUTTONDOWN/UP, WM_KEYDOWN/UP): the game reads its input
from them, so nothing has to touch the real mouse or the keyboard, and a
person can keep working beside a test. The first version moved the cursor
and took the mouse away from whoever was at the machine.

Usage:
    python menu_bot.py --load 0        main menu -> profile -> Load Saved Game -> row 0 -> team -> mission
    python menu_bot.py --reload 0      inside a mission: Esc -> Load -> row 0 -> the mission again
"""
import argparse
import ctypes
import time
from ctypes import wintypes

from PIL import Image, ImageChops

import play_bot

user32 = ctypes.windll.user32
VK_ESCAPE = 0x1B

# client coordinates in a 784x561 window
START = (395, 250)
PROFILE_FIRST, PROFILE_OK = (390, 291), (346, 364)
LOAD_SAVED = (392, 315)
SAVE_FIRST_ROW, SAVE_ROW_STEP, SAVE_OK = (100, 219), 17, (308, 450)
TEAM_AUTOMATIC, START_MISSION = (515, 20), (258, 20)
ESC_MENU_LOAD = (257, 161)
ESC_LOAD_FIRST_ROW, ESC_LOAD_ROW_STEP, ESC_LOAD_OK = (398, 164), 16.7, (579, 291)


class Menus:
    def __init__(self):
        self.g = play_bot.Game()
        r = wintypes.RECT()
        user32.GetClientRect(self.g.hwnd, ctypes.byref(r))
        self.scale = (r.right / 784.0, r.bottom / 561.0)

    WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x200, 0x201, 0x202
    WM_KEYDOWN, WM_KEYUP = 0x100, 0x101

    def lparam(self, x, y):
        cx, cy = int(x * self.scale[0]), int(y * self.scale[1])
        return (cy << 16) | (cx & 0xFFFF)

    def click(self, x, y):
        lp = self.lparam(x, y)
        user32.PostMessageW(self.g.hwnd, self.WM_MOUSEMOVE, 0, lp)
        time.sleep(0.1)
        user32.PostMessageW(self.g.hwnd, self.WM_LBUTTONDOWN, 1, lp)
        time.sleep(0.06)
        user32.PostMessageW(self.g.hwnd, self.WM_LBUTTONUP, 0, lp)
        time.sleep(0.15)

    def double_click(self, x, y):
        self.click(x, y)
        time.sleep(0.05)
        self.click(x, y)

    def key(self, vk):
        scan = user32.MapVirtualKeyW(vk, 0)
        user32.PostMessageW(self.g.hwnd, self.WM_KEYDOWN, vk, (scan << 16) | 1)
        time.sleep(0.08)
        user32.PostMessageW(self.g.hwnd, self.WM_KEYUP, vk, (scan << 16) | 0xC0000001)

    def screen(self):
        return Image.open(self.g.screenshot()).convert('L').resize((196, 140))

    def changed(self, before, after, threshold=6.0):
        diff = ImageChops.difference(before, after)
        return sum(diff.getdata()) / (196 * 140) > threshold

    def click_and_wait(self, x, y, timeout=30, settle=1.0):
        """Click, then wait until the screen looks different and has stopped
        changing for a moment. False when nothing happened in time."""
        before = self.screen()
        self.click(x, y)
        t0 = time.time()
        moved = False
        while time.time() - t0 < timeout:
            time.sleep(0.5)
            now = self.screen()
            if not moved and self.changed(before, now):
                moved = True
            if moved:
                time.sleep(settle)
                later = self.screen()
                if not self.changed(now, later, 2.0):
                    return True
        return moved

    def wait_mission(self, timeout=90):
        """Until a mission with a squad is up; on the team screen of a
        bunker save it picks the automatic team and starts."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.g.in_mission() and self.g.squad():
                time.sleep(2)
                return True
            time.sleep(1)
            if self.g.in_mission() and not self.g.squad() and time.time() - t0 > 5:
                self.click(*TEAM_AUTOMATIC)
                time.sleep(1.5)
                self.click(*START_MISSION)
                time.sleep(5)
        return False

    def load(self, row=0):
        self.click_and_wait(*START)
        self.click_and_wait(*PROFILE_FIRST, timeout=5)
        self.click_and_wait(*PROFILE_OK)
        self.click_and_wait(*LOAD_SAVED)
        self.click(SAVE_FIRST_ROW[0], SAVE_FIRST_ROW[1] + SAVE_ROW_STEP * row)
        time.sleep(0.6)
        self.click(*SAVE_OK)
        return self.wait_mission()

    def reload(self, row=0):
        """From inside a mission: Esc, Load, the row, OK."""
        squad_before = [u['address'] for u in self.g.squad()]
        self.key(VK_ESCAPE)
        time.sleep(1.5)
        self.click_and_wait(*ESC_MENU_LOAD, timeout=10)
        self.click(ESC_LOAD_FIRST_ROW[0], round(ESC_LOAD_FIRST_ROW[1] + ESC_LOAD_ROW_STEP * row))
        time.sleep(0.6)
        self.click(*ESC_LOAD_OK)
        t0 = time.time()
        while time.time() - t0 < 30 and [u['address'] for u in self.g.squad()] == squad_before:
            time.sleep(1)
        return self.wait_mission()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--load', type=int, metavar='ROW', help='from the main menu: which row of the load list, counted from 0')
    ap.add_argument('--reload', type=int, metavar='ROW', help='from inside a mission: Esc, Load, that row')
    args = ap.parse_args()
    m = Menus()
    if args.reload is not None:
        ok = m.reload(args.reload)
    else:
        ok = m.load(args.load or 0)
    print('in a mission with a squad' if ok else 'did not get there')


if __name__ == '__main__':
    main()
