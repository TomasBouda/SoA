"""A map of soa.exe: which code belongs to which of the original source files.

The game has no RTTI, so the classes carry no names in the file - which is why
every vtable in this project so far had to be found by hand. But it does carry
something almost as good. Every trace call passes the file it is written in,
and the compiler put those in as whole paths off the machine the game was built
on:

    D:\\Sebastian\\oldPC\\C\\Dev\\builds\\unborn\\y2k_source\\quellui_mission\\
        MissionMPStatisticPanel.cpp

There are 538 of them, in directories that group the code the way its authors
did. A file's name is referenced only from inside that file's own functions, so
following those references backwards to the function they sit in says which
file each function came from. One file is, near enough, one class.

Function starts are found the way they were found by hand all day: everything
that is the target of a call, plus everything a vtable or another table points
at. The largest such address at or below a reference is the function it is in.

Nothing here is exact. A function nobody calls directly and no table names is
invisible, and a file whose functions never trace anything cannot be placed at
all. What comes out is a map, not a decompilation - but a map is what was
missing.

Usage:
    python map_exe.py                  the summary, by directory
    python map_exe.py --file Mission   the files whose name contains this
    python map_exe.py --at 004D9715    which file that address belongs to
    python map_exe.py --write          write map.md next to the other docs
"""
import argparse
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
EXE = os.path.join(ROOT, '_patched', 'soa.exe')
OUT = os.path.join(HERE, '..', 'map.md')
IMAGE_BASE = 0x400000
TEXT_START = 0x1000
TEXT_END = 0x1000 + 3883008


def load():
    return open(EXE, 'rb').read()


def source_files(data):
    """Every __FILE__ string, as {address: (directory, name)}."""
    found = {}
    for m in re.finditer(rb'[A-Za-z]:\\[A-Za-z0-9_\\.\- ]{10,160}\.cpp', data):
        path = m.group().decode('latin1')
        parts = path.replace('/', '\\').split('\\')
        found[m.start() + IMAGE_BASE] = (parts[-2] if len(parts) > 1 else '', parts[-1])
    return found


def function_starts(data):
    """Everything called or pointed at - the same rule used by hand."""
    starts = set()
    i = TEXT_START
    while i < TEXT_END - 5:
        if data[i] == 0xE8:
            target = i + 5 + struct.unpack_from('<i', data, i + 1)[0] + IMAGE_BASE
            if IMAGE_BASE + TEXT_START <= target < IMAGE_BASE + TEXT_END:
                starts.add(target)
        i += 1
    for o in range(TEXT_START, len(data) - 4, 4):
        v = struct.unpack_from('<I', data, o)[0]
        if IMAGE_BASE + TEXT_START <= v < IMAGE_BASE + TEXT_END:
            starts.add(v)
    return sorted(starts)


def references(data, addresses):
    """Where each of those addresses is pushed or loaded, inside the code."""
    wanted = {}
    for address in addresses:
        wanted[struct.pack('<I', address)] = address
    found = {}
    for pattern, address in wanted.items():
        i = TEXT_START
        while True:
            i = data.find(pattern, i, TEXT_END)
            if i < 0:
                break
            found.setdefault(address, []).append(i + IMAGE_BASE)
            i += 1
    return found


def owning(starts, address):
    """The function an address is inside, or None."""
    lo, hi = 0, len(starts)
    while lo < hi:
        mid = (lo + hi) // 2
        if starts[mid] <= address:
            lo = mid + 1
        else:
            hi = mid
    return starts[lo - 1] if lo else None


def build():
    data = load()
    files = source_files(data)
    starts = function_starts(data)
    where = references(data, files)

    by_file = {}
    for address, (folder, name) in files.items():
        spots = where.get(address, [])
        functions = sorted({owning(starts, s) for s in spots if owning(starts, s)})
        by_file[name] = {'folder': folder, 'at': address, 'functions': functions}
    return by_file, starts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', help='only the files whose name contains this')
    ap.add_argument('--at', help='which file an address belongs to')
    ap.add_argument('--write', action='store_true', help='write map.md')
    args = ap.parse_args()

    by_file, starts = build()
    placed = {n: d for n, d in by_file.items() if d['functions']}

    if args.at:
        address = int(args.at, 16)
        best, distance = None, None
        for name, d in placed.items():
            for f in d['functions']:
                if f <= address and (distance is None or address - f < distance):
                    best, distance = (name, f), address - f
        if best:
            print('%08X is in %s, in the function that starts at %08X'
                  % (address, best[0], best[1]))
        else:
            print('%08X could not be placed' % address)
        return

    if args.file:
        for name in sorted(placed):
            if args.file.lower() not in name.lower():
                continue
            d = placed[name]
            print('%s   (%s)' % (name, d['folder']))
            for f in d['functions']:
                print('    %08X' % f)
        return

    folders = {}
    for name, d in placed.items():
        folders.setdefault(d['folder'], []).append(name)
    print('%d source files in the exe, %d of them placed in code\n'
          % (len(by_file), len(placed)))
    for folder in sorted(folders, key=lambda f: -len(folders[f])):
        print('  %-28s %3d files' % (folder or '(no folder)', len(folders[folder])))

    if args.write:
        lines = ['# Which code belongs to which source file', '',
                 'Made by [tools/map_exe.py](tools/map_exe.py) - see the comment at the',
                 'top of it for how, and for what it cannot see.', '',
                 '%d source files are named in the exe and %d of them could be placed in'
                 % (len(by_file), len(placed)),
                 'code by following the trace calls back to the function they sit in.', '']
        for folder in sorted(folders):
            lines.append('## %s' % (folder or 'no folder'))
            lines.append('')
            lines.append('| file | functions |')
            lines.append('|---|---|')
            for name in sorted(folders[folder]):
                d = placed[name]
                shown = ', '.join('`%08X`' % f for f in d['functions'][:8])
                if len(d['functions']) > 8:
                    shown += ' and %d more' % (len(d['functions']) - 8)
                lines.append('| %s | %s |' % (name, shown))
            lines.append('')
        with open(OUT, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('\nwritten to %s' % os.path.normpath(OUT))


if __name__ == '__main__':
    main()
