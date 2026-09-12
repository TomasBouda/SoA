"""What is under a point of the screen, and "go there" - asked of the game
through its mailbox.

Read off the UIPlayer's click handler (0x5DC7B0): a right click takes the
mouse position, asks 0x5DB0E0 what is under it - which asks the landscape
(0x880F98) for the terrain point with 0x686A90(x, y, &vector), and the
objects with 0x686640 - and hands the first hit's world x and y to
0x5DAC80(this, x, y, released, mode, queue, flag), the order at a point.
The picks use the renderer's view and projection matrices of the moment, so
a call from a thread of our own answers only when it happens to land in the
right part of a frame - the first try worked, the next eight did not. Hence
the mailbox (patch_exe.py --mailbox): this writes a request into the
padding of .text and the mission's Tick makes the call, on the game's own
thread, once a frame.

    pick(x, y)       x, y in the game's own 800x600 screen -> world x, y, z
    order(wx, wy)    the selected units go there, as after a right click
    matrices()       the view and projection matrices the game draws with
    call(this, off, args)   a thiscall on any object - every order a unit takes

Usage:
    python ui_inject.py --pick 400,300
    python ui_inject.py --order 390,900
    python ui_inject.py --install       write the mailbox into a running game that lacks it
"""
import argparse
import ctypes
import os
import struct
import sys
import time
from ctypes import wintypes

import scan_memory as sm

BOX = 0x007B4750
REQ, X, Y, COUNT, RX = BOX, BOX + 4, BOX + 8, BOX + 0xC, BOX + 0x10
SITE = 0x5E93A1


def _open():
    pid = sm.find_process('soa.exe')
    if not pid:
        raise SystemExit('soa.exe is not running')
    return sm.open_process(pid, write=True)


def _installed(h):
    b = sm.read(h, SITE, 1)
    return bool(b) and b[0] == 0xE9


def _request(h, kind, x, y, timeout=2.0):
    if not _installed(h):
        raise SystemExit('the mailbox is not in this soa.exe - patch_exe.py --mailbox, '
                         'or --install into the running game')
    sm.write_value(h, X, struct.pack('<ff', x, y))
    sm.write_value(h, COUNT, b'\0' * 4)
    sm.write_value(h, REQ, bytes([kind]))
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.02)
        if sm.read(h, REQ, 1)[0] == 0:
            return True
    return False


def pick(x, y, h=None):
    """The terrain point under screen (x, y), or None when nothing is there.
    A paused game still ticks, so it still answers."""
    h = h or _open()
    if not _request(h, 1, x, y):
        raise SystemExit('the game did not answer - is a mission running?')
    count = struct.unpack('<I', sm.read(h, COUNT, 4))[0]
    if count == 0:
        return None
    return struct.unpack('<fff', sm.read(h, RX, 12))


def order(wx, wy, h=None):
    """The selected units go to the world point. Returns what the game's
    order function returned."""
    h = h or _open()
    if not _request(h, 2, wx, wy):
        raise SystemExit('the game did not answer - is a mission running?')
    return struct.unpack('<I', sm.read(h, COUNT, 4))[0]


def matrices(h=None):
    """The view and projection matrices the game is drawing with, as two
    4x4 row-major lists - read out of the Direct3D device by the game."""
    h = h or _open()
    if not _request(h, 3, 0.0, 0.0):
        raise SystemExit('the game did not answer - is a mission running?')
    raw = sm.read(h, BOX + 0x40, 128)
    v = struct.unpack('<16f', raw[:64])
    p = struct.unpack('<16f', raw[64:])
    return [list(v[i:i + 4]) for i in range(0, 16, 4)], [list(p[i:i + 4]) for i in range(0, 16, 4)]


def call(this, vtable_offset, args, h=None):
    """A thiscall on any object of the game, on the game's thread: the
    method at [vtable + offset] with the arguments in order (dwords; floats
    are packed as floats). Returns eax. Twelve arguments at most."""
    h = h or _open()
    if len(args) > 12:
        raise SystemExit('twelve arguments at most')
    packed = b''.join(struct.pack('<f', a) if isinstance(a, float) else struct.pack('<I', a & 0xFFFFFFFF) for a in args)
    sm.write_value(h, BOX + 4, struct.pack('<II', this, vtable_offset) + struct.pack('<I', len(args)) + packed)
    sm.write_value(h, REQ, bytes([4]))
    t0 = time.time()
    while time.time() - t0 < 2.0:
        time.sleep(0.02)
        if sm.read(h, REQ, 1)[0] == 0:
            return struct.unpack('<I', sm.read(h, COUNT, 4))[0]
    raise SystemExit('the game did not answer - is a mission running?')


def install(h):
    """The same bytes patch_exe.py --mailbox writes, into the running game."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import patch_exe
    k32 = sm.k32
    k32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
                                     ctypes.POINTER(wintypes.DWORD)]
    old = wintypes.DWORD()
    # the code first, the jump into it last - the other way round the game
    # runs whatever the padding held while the code is still being written
    sites = [p for p in patch_exe.PATCHES if p[0] == 'mailbox']
    sites.sort(key=lambda p: 0 if isinstance(p[2], int) else 1)
    # and before anything, the jump out: a game that carries an older
    # mailbox jumps into the very bytes about to be rewritten
    for group, name, anchor, original, patched in sites:
        if isinstance(anchor, int):
            continue
        data = sm.read(h, 0x5E9000, 0x1000)
        va = 0x5E9000 + data.find(anchor) + len(anchor)
        if sm.read(h, va, 1)[0] == 0xE9:
            k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(original), 0x40, ctypes.byref(old))
            sm.write_value(h, va, original)
            time.sleep(0.1)
    for group, name, anchor, original, patched in sites:
        if isinstance(anchor, int):
            va = 0x400000 + anchor
        else:
            data = sm.read(h, 0x5E9000, 0x1000)     # the site is in this page
            va = 0x5E9000 + data.find(anchor) + len(anchor)
        have = sm.read(h, va, len(original))
        if isinstance(anchor, int) and have not in (original, patched):
            # an earlier, different cave: the jump is not in place, so the
            # bytes are dead and may go
            k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(patched), 0x40, ctypes.byref(old))
            sm.write_value(h, va, bytes(len(patched)))
        elif have not in (original, patched):
            raise SystemExit('unexpected bytes at %08X' % va)
        k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(patched), 0x40, ctypes.byref(old))
        sm.write_value(h, va, patched)
        k32.VirtualProtectEx(h, ctypes.c_void_p(va), len(patched), old.value, ctypes.byref(old))
        print('wrote %s at %08X' % (name, va))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pick', metavar='X,Y', help='screen point in the game\'s 800x600')
    ap.add_argument('--order', metavar='WX,WY', help='world point the selected units go to')
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--matrices', action='store_true')
    args = ap.parse_args()
    h = _open()
    if args.install:
        install(h)
    if args.matrices:
        view, proj = matrices(h)
        for name, m in (('view', view), ('projection', proj)):
            print(name)
            for row in m:
                print('   ' + ' '.join('%10.4f' % v for v in row))
    if args.pick:
        x, y = [float(v) for v in args.pick.split(',')]
        hit = pick(x, y, h)
        print('nothing under it' if hit is None else 'terrain at %.2f, %.2f, %.2f' % hit)
    if args.order:
        wx, wy = [float(v) for v in args.order.split(',')]
        print('order returned', order(wx, wy, h))


if __name__ == '__main__':
    main()
