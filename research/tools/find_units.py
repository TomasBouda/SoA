"""Finding the units of a running mission in memory, and what holds them.

The map window can say what stands somewhere but not whose it is, because the
cell array carries a kind and not a side, and it only carries what the party
can see. Both are answered by the unit objects themselves - this walks to them.

The chain comes out of the code that stamps an object into the cell array
(`0x6C3FD0`, see _research/architecture.md):

    a map object keeps a stamp at +0x150            (0x578800 is the getter)
    the stamp keeps the position at +0x24 and +0x28 (and +0x2C, an angle or a
                                                     size, small either way)
    the stamp keeps the bits it writes at +0x18 and the mask at +0x14

So a stamp is recognisable on sight: two numbers inside the map and a value
whose 0x00000F00 says a unit stands there. The rest is pointer chasing -
whoever holds a pointer to the stamp at +0x150 is the unit, and whoever holds
a pointer to the unit is the list the mission keeps them in.

Nothing is written. The game is only read.

Usage:
    python find_units.py               find the stamps, the units and the lists
    python find_units.py --stamps      stop after the stamps
    python find_units.py --unit ADDR   print one unit: its stamp, where it is,
                                       and the first words of the object
    python find_units.py --all         every unit on the map, seen or not
    python find_units.py --player      the player's own party object

Once the chain above is walked once, the objects turn out to share a layout,
which --all uses instead: a map object keeps its position as two floats at
+0x54 and +0x58 and its stamp at +0x150. Since the stamp belongs to the object
and not to what the party can see, that finds the units the map window cannot
show - which is the point of the whole exercise.
"""
import argparse
import ctypes
import struct
import subprocess
from ctypes import wintypes

import numpy

WORLD_GLOBAL = 0x00880F98
WIDTH_AT = 0x24
HEIGHT_AT = 0x28
CELLS_AT = 0x2C

# The class the map of the exe calls Y2KKIUIPlayer - the player whose party
# the interface belongs to. Its vtable is installed by the constructor at
# 0x5D7F53, and there should be exactly one of it in a mission. Whatever field
# holds the party number, it is in here.
UIPLAYER_VTABLE = 0x007CFE38

STAMP_AT = 0x150            # the map object keeps its stamp here
STAMP_MASK_AT = 0x14
STAMP_VALUE_AT = 0x18
STAMP_X_AT = 0x24
STAMP_Y_AT = 0x28
STAMP_THIRD_AT = 0x2C

MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
PAGE_GUARD = 0x100
READABLE = 0x02 | 0x04 | 0x08 | 0x20 | 0x40

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.ReadProcessMemory.argtypes = (wintypes.HANDLE, wintypes.LPCVOID,
                                       wintypes.LPVOID, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t))


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p),
                ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wintypes.DWORD),
                ('RegionSize', ctypes.c_size_t),
                ('State', wintypes.DWORD),
                ('Protect', wintypes.DWORD),
                ('Type', wintypes.DWORD)]


kernel32.VirtualQueryEx.argtypes = (wintypes.HANDLE, wintypes.LPCVOID,
                                    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                                    ctypes.c_size_t)


def find_game():
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


def regions(handle):
    """The game's own memory, region by region, as (address, bytes)."""
    info = MEMORY_BASIC_INFORMATION()
    address = 0x10000
    while address < 0x7FFF0000:
        if not kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address),
                                       ctypes.byref(info),
                                       ctypes.sizeof(info)):
            break
        size = info.RegionSize
        if size == 0:
            break
        base = info.BaseAddress or 0
        if (info.State == MEM_COMMIT and info.Type == MEM_PRIVATE
                and info.Protect & READABLE and not info.Protect & PAGE_GUARD):
            raw = read(handle, base, size)
            if raw is not None and len(raw) >= 4:
                yield base, raw
        address = base + size


def as_words(raw):
    """The block as unsigned 32-bit words, dropping any odd tail."""
    return numpy.frombuffer(raw[:len(raw) // 4 * 4], dtype='<u4')


def unit_cells(handle, world, width, height):
    """Where the map says a unit stands, as {(x, y): kind}."""
    cells = dword(handle, world + CELLS_AT)
    found = {}
    for y in range(height):
        raw = read(handle, cells + y * width * 4, width * 4)
        if raw is None or len(raw) < width * 4:
            break
        row = numpy.frombuffer(raw, dtype='<u4')
        for x in numpy.nonzero(row & 0x00000F00)[0]:
            found[(int(x), y)] = (int(row[int(x)]) >> 8) & 0xF
    return found


def find_stamps(handle, where):
    """The stamps of the units the map knows about.

    Loose filters find hundreds of thousands of accidents, so the map does the
    filtering: a stamp has to sit on a cell the map says a unit is on, carry a
    kind that cell carries, and keep something that looks like a mask at +0x14 -
    the game resets that field to 0xFFFFFFFF and in use it only clears a few
    low bits.
    """
    xs = numpy.array(sorted({x for x, _ in where}), dtype='<u4')
    ys = numpy.array(sorted({y for _, y in where}), dtype='<u4')
    found = []
    for base, raw in regions(handle):
        words = as_words(raw)
        if len(words) < STAMP_THIRD_AT // 4 + 1:
            continue
        top = len(words) - (STAMP_THIRD_AT // 4 + 1)
        mask = words[STAMP_MASK_AT // 4: STAMP_MASK_AT // 4 + top]
        value = words[STAMP_VALUE_AT // 4: STAMP_VALUE_AT // 4 + top]
        x = words[STAMP_X_AT // 4: STAMP_X_AT // 4 + top]
        y = words[STAMP_Y_AT // 4: STAMP_Y_AT // 4 + top]
        hit = ((value & 0x00000F00) != 0) & (value < 0x01000000) \
            & (mask >= 0xF0000000) & numpy.isin(x, xs) & numpy.isin(y, ys)
        for index in numpy.nonzero(hit)[0]:
            index = int(index)
            spot = (int(x[index]), int(y[index]))
            kind = (int(value[index]) >> 8) & 0xF
            if where.get(spot, 0) & kind != kind:
                continue
            found.append((base + index * 4, spot[0], spot[1], kind,
                          int(value[index])))
    return found


def find_pointers(handle, targets, at=None):
    """Where a pointer to one of `targets` is kept.

    Returns {target: [address of the word holding it]}. With `at` given, only
    words that would put the holder at a sensible object start are kept.
    """
    wanted = numpy.array(sorted(targets), dtype='<u4')
    found = {}
    for base, raw in regions(handle):
        words = as_words(raw)
        if len(words) == 0:
            continue
        index = numpy.nonzero(numpy.isin(words, wanted))[0]
        for i in index:
            i = int(i)
            address = base + i * 4
            if at is not None and address < at:
                continue
            found.setdefault(int(words[i]), []).append(address)
    return found


UNIT_X_AT = 0x54            # the position, as two floats
UNIT_Y_AT = 0x58


def find_everything(handle, width, height):
    """Every map object, by the layout rather than by what the map shows.

    An object is taken when its first word is a vtable in the exe, the two
    floats at +0x54 and +0x58 fall inside the map, and the pointer at +0x150
    leads to a stamp whose position agrees with those floats. Three fields
    agreeing is enough that nothing else in the heap looks like it.
    """
    found = []
    for base, raw in regions(handle):
        words = as_words(raw)
        top = len(words) - (STAMP_AT // 4 + 1)
        if top <= 0:
            continue
        floats = numpy.frombuffer(raw[:len(words) * 4], dtype='<f4')
        vtable = words[0:top]
        x = floats[UNIT_X_AT // 4: UNIT_X_AT // 4 + top]
        y = floats[UNIT_Y_AT // 4: UNIT_Y_AT // 4 + top]
        stamp = words[STAMP_AT // 4: STAMP_AT // 4 + top]
        hit = (vtable > 0x400000) & (vtable < 0x800000) \
            & (x >= 1.0) & (x < width) & (y >= 1.0) & (y < height) \
            & (stamp > 0x10000) & (stamp < 0x80000000)
        for index in numpy.nonzero(hit)[0]:
            index = int(index)
            at = int(stamp[index])
            head = read(handle, at, 0x30)
            if head is None or len(head) < 0x30:
                continue
            mask, value = struct.unpack_from('<II', head, STAMP_MASK_AT)
            sx, sy = struct.unpack_from('<II', head, STAMP_X_AT)
            if mask < 0xF0000000 or abs(sx - x[index]) > 2 or abs(sy - y[index]) > 2:
                continue
            found.append((base + index * 4, int(vtable[index]),
                          float(x[index]), float(y[index]), value))

    units = [f for f in found if f[4] & 0x00000F00]
    print('\n%d map objects, %d of them units' % (len(found), len(units)))
    classes = {}
    for address, vtable, x, y, value in units:
        classes.setdefault(vtable, []).append((address, x, y, value))
    print('\nunits by class:')
    for vtable in sorted(classes, key=lambda v: -len(classes[v])):
        rows = classes[vtable]
        kinds = {}
        for _, _, _, value in rows:
            kind = (value >> 8) & 0xF
            kinds[kind] = kinds.get(kind, 0) + 1
        print('   vtable %08X   %3d   kinds %s' % (vtable, len(rows),
              ' '.join('%X:%d' % k for k in sorted(kinds.items()))))
        for address, x, y, value in sorted(rows, key=lambda r: (r[2], r[1]))[:3]:
            print('        %08X  at %6.1f %6.1f  value %08X' % (address, x, y, value))


def find_player(handle):
    """Every object whose first word is the UI player's vtable."""
    found = []
    for base, raw in regions(handle):
        words = as_words(raw)
        for index in numpy.nonzero(words == UIPLAYER_VTABLE)[0]:
            found.append(base + int(index) * 4)
    return found


def show_player(handle, parties):
    """The player object, with the fields that could be a party number.

    `parties` is what the map says is on the board, so a field holding one of
    those numbers is worth looking at and a field holding 47 is not.
    """
    found = find_player(handle)
    print('%d objects with the UI player vtable %08X' % (len(found), UIPLAYER_VTABLE))
    for address in found:
        raw = read(handle, address, 0x200)
        if raw is None or len(raw) < 0x200:
            continue
        print('\n   %08X' % address)
        hits = []
        for off in range(4, 0x200, 4):
            value, = struct.unpack_from('<i', raw, off)
            if value in parties:
                hits.append('+%03X = %d' % (off, value))
        print('      fields holding a party number that is on the map: %s'
              % (', '.join(hits) if hits else 'none'))
        small = ['+%03X=%d' % (o, struct.unpack_from('<i', raw, o)[0])
                 for o in range(4, 0x80, 4)
                 if 0 <= struct.unpack_from('<i', raw, o)[0] <= 15]
        print('      small numbers in the first 0x80: %s' % ' '.join(small))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stamps', action='store_true', help='stop after the stamps')
    ap.add_argument('--unit', help='print one unit, by address')
    ap.add_argument('--all', action='store_true',
                    help='every unit on the map by its layout, seen or not')
    ap.add_argument('--player', action='store_true',
                    help="the player's own party object, and what looks like its number")
    args = ap.parse_args()

    pid = find_game()
    if pid is None:
        raise SystemExit('soa.exe is not running')
    handle = kernel32.OpenProcess(0x0410, False, pid)
    if not handle:
        raise SystemExit('cannot attach to soa.exe (%d)' % ctypes.get_last_error())

    world = dword(handle, WORLD_GLOBAL)
    if world == 0:
        raise SystemExit('no mission is running')
    width = dword(handle, world + WIDTH_AT)
    height = dword(handle, world + HEIGHT_AT)
    print('mission %08X, %d x %d world units' % (world, width, height))

    if args.player:
        where = unit_cells(handle, world, width, height)
        parties = sorted({k for k in where.values()})
        print('parties the map shows: %s' % parties)
        show_player(handle, set(parties))
        return

    if args.all:
        find_everything(handle, width, height)
        return

    if args.unit:
        unit = int(args.unit, 0)
        stamp = dword(handle, unit + STAMP_AT)
        print('unit  %08X' % unit)
        print('stamp %08X' % stamp)
        if stamp:
            print('   at %d %d   value %08X   mask %08X'
                  % (dword(handle, stamp + STAMP_X_AT),
                     dword(handle, stamp + STAMP_Y_AT),
                     dword(handle, stamp + STAMP_VALUE_AT),
                     dword(handle, stamp + STAMP_MASK_AT)))
        raw = read(handle, unit, 0x160) or b''
        for offset in range(0, len(raw) - 3, 16):
            words = struct.unpack_from('<4I', raw, offset)
            print('   +%03X  %08X %08X %08X %08X' % ((offset,) + words))
        return

    where = unit_cells(handle, world, width, height)
    print('the map has units on %d cells' % len(where))
    stamps = find_stamps(handle, where)
    print('\n%d stamps that carry a unit:' % len(stamps))
    for address, x, y, kind, value in sorted(stamps, key=lambda s: (s[2], s[1]))[:40]:
        print('   %08X   at %4d %4d   kind %X   value %08X'
              % (address, x, y, kind, value))
    if len(stamps) > 40:
        print('   ... and %d more' % (len(stamps) - 40))
    if args.stamps or not stamps:
        return

    holders = find_pointers(handle, [s[0] for s in stamps])
    candidates = {}
    for stamp, places in holders.items():
        for place in places:
            candidates[place - STAMP_AT] = stamp
    print('\n%d objects hold one of those at +0x150' % len(candidates))

    # Not all of them are units: the same pointer is kept in other places too,
    # at other offsets, and subtracting 0x150 from those lands on nothing. A
    # unit is a C++ object, so its first word is a vtable - a pointer into the
    # exe, which is loaded at 0x400000 and has no ASLR. Grouping by that both
    # throws the accidents away and says how many classes are on the map.
    units = {}
    classes = {}
    for unit, stamp in candidates.items():
        vtable = dword(handle, unit)
        if not 0x400000 < vtable < 0x800000:
            continue
        units[unit] = stamp
        classes.setdefault(vtable, []).append(unit)
    print('%d of them start with a pointer into the exe, in %d classes:'
          % (len(units), len(classes)))
    by_stamp = {s[0]: s for s in stamps}
    for vtable in sorted(classes, key=lambda v: -len(classes[v])):
        kinds = {}
        for unit in classes[vtable]:
            kind = by_stamp[units[unit]][3]
            kinds[kind] = kinds.get(kind, 0) + 1
        print('   vtable %08X   %3d objects   kinds %s'
              % (vtable, len(classes[vtable]),
                 ' '.join('%X:%d' % k for k in sorted(kinds.items()))))
        for unit in sorted(classes[vtable])[:4]:
            s2 = by_stamp[units[unit]]
            print('        %08X  at %4d %4d  kind %X' % (unit, s2[1], s2[2], s2[3]))

    if not units:
        return
    lists = find_pointers(handle, list(units))
    places = {}
    for unit, where in lists.items():
        for address in where:
            if address - STAMP_AT in units:
                continue          # that is the stamp pointer, not a list
            places.setdefault(address & ~0xFFF, []).append((address, unit))
    print('\nwhere pointers to those units are kept, by page:')
    for page in sorted(places, key=lambda p: -len(places[p]))[:12]:
        addresses = sorted(a for a, _ in places[page])
        step = ''
        if len(addresses) > 1:
            gaps = {addresses[i + 1] - addresses[i] for i in range(len(addresses) - 1)}
            if len(gaps) == 1:
                step = '   evenly, every %d bytes - that looks like the list' % gaps.pop()
        print('   page %08X: %d pointers, %08X..%08X%s'
              % (page, len(addresses), addresses[0], addresses[-1], step))


if __name__ == '__main__':
    main()
