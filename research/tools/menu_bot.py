"""Clicks the game from its main menu into a saved game, or from inside a
mission into another one, so a program can start a mission without a person
at the mouse.

The menus are laid out for 800x600 and scaled to whatever the window is, so
the clicks are given in 784x561 (the window the game makes on a 1080p desktop)
and scaled to the client area found. Between clicks the bot waits for the
screen to change (play_bot.Game.screenshot, a GDI grab from outside) instead
of sleeping a fixed time, which is what made the earlier version miss a step
on a slow load.

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
        user32.SetForegroundWindow(self.g.hwnd)
        time.sleep(0.5)

    def click(self, x, y):
        p = wintypes.POINT(0, 0)
        user32.ClientToScreen(self.g.hwnd, ctypes.byref(p))
        user32.SetCursorPos(int(p.x + x * self.scale[0]), int(p.y + y * self.scale[1]))
        time.sleep(0.15)
        user32.mouse_event(2, 0, 0, 0, 0)
        time.sleep(0.06)
        user32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(0.15)

    def key(self, vk):
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.08)
        user32.keybd_event(vk, 0, 2, 0)

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
