"""What the bits of the map cell array actually hold, out of a running mission.

The engine keeps one dword per world unit in a flat array - see
_research/architecture.md. Which bit is which came from reading the overlay
that asks for it, and that named six fields:

    0x00000008  air              0x00010000  a structure
    0x000000F0  object size      0x00060000  ground type
    0x00000F00  what stands here 0x00200000  smoke

The field at 0x00000F00 is the number of the party a unit belongs to. Counting
here ruled out a count of units - the values that turn up are 1, 2, 3, 4, 5, 6,
8 and 9, and a count would not skip 7 - and find_units.py ruled out the reading
that came next, four flags one to a side, by showing one class of unit object
under four different numbers.

Nothing is written. The game is only read, so this is safe to run while
playing - it does not even need the mission paused.

The unit bits raise a second question: whether they stay once a place has been
visited or only stand while somebody is looking. --watch answers it. It counts
the cells carrying each kind every couple of seconds and says how many appeared
and how many went; walk the party away from a place and watch the number fall,
and the bits are live sight rather than a map that fills in as it is explored.

Usage:
    python map_bits.py                 the whole map
    python map_bits.py --sample 200    only a 200x200 corner, if the map is big
    python map_bits.py --cell 40 37    everything about one cell
    python map_bits.py --watch         count the units until interrupted
"""
import argparse
import ctypes
import struct
import sys
from ctypes import wintypes

WORLD_GLOBAL = 0x00880F98
WIDTH_AT = 0x24
HEIGHT_AT = 0x28
CELLS_AT = 0x2C

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.ReadProcessMemory.argtypes = (wintypes.HANDLE, wintypes.LPCVOID,
                                       wintypes.LPVOID, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t))

FIELDS = [
    ('air', 0x00000008, 3),
    ('object size', 0x000000F0, 4),
    ('what stands here', 0x00000F00, 8),
    ('structure', 0x00010000, 16),
    ('ground', 0x00060000, 17),
    ('smoke', 0x00200000, 21),
]


def find_game():
    import subprocess
    out = subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq soa.exe', '/FO', 'CSV', '/NH'])
    for line in out.decode('latin1').splitlines():
        if line.startswith('"soa.exe"'):
            return int(line.split('","')[1])
    return None


def read(handle, address, length):
    buf = ctypes.create_string_buffer(length)
    got = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf,
                                      length, ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def dword(handle, address):
    raw = read(handle, address, 4)
    return struct.unpack('<I', raw)[0] if raw else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=0,
                    help='read only a corner of this many units on a side')
    ap.add_argument('--cell', nargs=2, type=int, metavar=('X', 'Y'),
                    help='print everything about one cell instead')
    ap.add_argument('--watch', action='store_true',
                    help='count the unit cells every few seconds until interrupted')
    ap.add_argument('--every', type=float, default=2.0,
                    help='seconds between readings when watching (default 2)')
    args = ap.parse_args()

    pid = find_game()
    if pid is None:
        raise SystemExit('soa.exe is not running')
    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION,
                                  False, pid)
    if not handle:
        raise SystemExit('cannot attach to soa.exe (%d)' % ctypes.get_last_error())

    world = dword(handle, WORLD_GLOBAL)
    if world == 0:
        raise SystemExit('no mission is running - the world is null')
    width = dword(handle, world + WIDTH_AT)
    height = dword(handle, world + HEIGHT_AT)
    cells = dword(handle, world + CELLS_AT)
    print('world %08X   %d x %d world units   cells at %08X' % (world, width, height, cells))

    if args.cell:
        x, y = args.cell
        if not (0 <= x < width and 0 <= y < height):
            raise SystemExit('that cell is outside the map')
        value = dword(handle, cells + (y * width + x) * 4)
        print('cell %d %d = %08X' % (x, y, value))
        for name, mask, shift in FIELDS:
            print('   %-12s %d' % (name, (value & mask) >> shift))
        return

    if args.watch:
        watch(handle, width, height, cells, args.every)
        return

    rows = height if args.sample <= 0 else min(height, args.sample)
    columns = width if args.sample <= 0 else min(width, args.sample)
    counts = {name: {} for name, _, _ in FIELDS}
    both = {}
    total = 0
    for y in range(rows):
        raw = read(handle, cells + y * width * 4, columns * 4)
        if raw is None or len(raw) < columns * 4:
            raise SystemExit('the map could not be read at row %d' % y)
        row = struct.unpack('<%dI' % columns, raw)
        for value in row:
            total += 1
            for name, mask, shift in FIELDS:
                v = (value & mask) >> shift
                counts[name][v] = counts[name].get(v, 0) + 1
            kind = (value >> 8) & 0xF
            if kind:
                key = (kind, (value >> 4) & 0xF)
                both[key] = both.get(key, 0) + 1

    print('%d cells read\n' % total)
    for name, _, _ in FIELDS:
        pairs = sorted(counts[name].items())
        print('%-12s %s' % (name, '  '.join('%d:%d' % p for p in pairs)))
    if both:
        print('\nparty and object size together (party, size): count')
        for key in sorted(both):
            print('   %d, %-2d  %d' % (key[0], key[1], both[key]))


def unit_cells(handle, width, height, cells):
    """The set of cells carrying a unit, by kind."""
    found = {}
    for y in range(height):
        raw = read(handle, cells + y * width * 4, width * 4)
        if raw is None or len(raw) < width * 4:
            return None
        row = struct.unpack('<%dI' % width, raw)
        for x, value in enumerate(row):
            kind = (value >> 8) & 0xF
            if kind:
                found[(x, y)] = kind
    return found


def watch(handle, width, height, cells, every):
    import time
    print('counting the unit cells every %.1f s - move the party and watch.' % every)
    print('Ctrl+C stops.\n')
    before = None
    while True:
        now = unit_cells(handle, width, height, cells)
        if now is None:
            print('the map could not be read - the mission may be ending')
            return
        per_kind = {}
        for kind in now.values():
            for bit in range(4):
                if kind >> bit & 1:
                    per_kind[bit] = per_kind.get(bit, 0) + 1
        line = '%5d cells   ' % len(now)
        line += '  '.join('bit %d: %d' % (b, per_kind.get(b, 0)) for b in range(4))
        if before is not None:
            appeared = len(set(now) - set(before))
            gone = len(set(before) - set(now))
            line += '   (+%d -%d)' % (appeared, gone)
        print(line)
        before = now
        time.sleep(every)


if __name__ == '__main__':
    main()
