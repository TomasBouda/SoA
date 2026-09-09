"""Watch one object in the running game and see what a change does to it.

This is the method that answered the binoculars question, made into a tool
because it had to be written twice by hand in one afternoon.

The trouble with reading an object once before a change and once after is that
a running game moves half of it on its own - timers, aim, animation, health.
The first attempt at the binoculars was ruined that way: thirty-three words
differed and most of them were a firefight, not the item. So this measures the
noise first. It reads the object twice a few seconds apart while nothing is
being done to it, and every word that moved by itself is set aside. What
differs after that is the change.

    python diff_memory.py --at 079B1688
    python diff_memory.py --vtable 007CFE38          find the object first
    python diff_memory.py --at 03B2CFD8 --size 0x1000 --quiet 10

It reads and never writes. The game can be left running throughout.

The output is the offsets that changed, with each read as an int, a float and
a pointer, because which of the three it is only becomes clear from what the
numbers look like.
"""
import argparse
import ctypes
import struct
import subprocess
import sys
import time
from ctypes import wintypes

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
    return buf.raw[:got.value] if got.value == length else None


def find_by_vtable(handle, vtable):
    """Every object in the game's own memory whose first word is `vtable`."""
    want = struct.pack('<I', vtable)
    found = []
    info = MEMORY_BASIC_INFORMATION()
    address = 0x10000
    while address < 0x7FFF0000:
        if not kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address),
                                       ctypes.byref(info), ctypes.sizeof(info)):
            break
        size = info.RegionSize
        if size == 0:
            break
        base = info.BaseAddress or 0
        if (info.State == MEM_COMMIT and info.Type == MEM_PRIVATE
                and info.Protect & READABLE and not info.Protect & PAGE_GUARD):
            raw = read(handle, base, size)
            if raw:
                start = 0
                while True:
                    i = raw.find(want, start)
                    if i < 0:
                        break
                    if i % 4 == 0:
                        found.append(base + i)
                    start = i + 1
        address = base + size
    return found


def describe(before, after, off):
    """One changed word, read the three ways it might be meant."""
    a, = struct.unpack_from('<i', before, off)
    b, = struct.unpack_from('<i', after, off)
    fa, = struct.unpack_from('<f', before, off)
    fb, = struct.unpack_from('<f', after, off)
    line = '  +%03X  %11d -> %-11d' % (off, a, b)
    if 0x10000 < (a & 0xFFFFFFFF) < 0x7F000000 or 0x10000 < (b & 0xFFFFFFFF) < 0x7F000000:
        line += '   as pointers %08X -> %08X' % (a & 0xFFFFFFFF, b & 0xFFFFFFFF)
    elif any(1e-3 < abs(f) < 1e7 for f in (fa, fb)):
        line += '   as floats %.3f -> %.3f' % (fa, fb)
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--at', help='the object, as a hex address')
    ap.add_argument('--vtable', help='find the object by its vtable instead')
    ap.add_argument('--size', default='0x400', help='how much of it to watch (default 0x400)')
    ap.add_argument('--quiet', type=float, default=7,
                    help='seconds of standing still, to learn what moves on its own')
    args = ap.parse_args()

    pid = find_game()
    if pid is None:
        raise SystemExit('soa.exe is not running')
    handle = kernel32.OpenProcess(0x0410, False, pid)
    if not handle:
        raise SystemExit('cannot attach to soa.exe (%d)' % ctypes.get_last_error())

    if args.vtable:
        vtable = int(args.vtable, 16)
        found = find_by_vtable(handle, vtable)
        print('%d objects with vtable %08X' % (len(found), vtable))
        for a in found[:20]:
            print('   %08X' % a)
        if len(found) != 1 and not args.at:
            raise SystemExit('give --at to say which one' if found else 'none found')
        address = int(args.at, 16) if args.at else found[0]
    elif args.at:
        address = int(args.at, 16)
    else:
        raise SystemExit('give --at or --vtable')

    size = int(args.size, 0)
    first = read(handle, address, size)
    if first is None:
        raise SystemExit('%08X could not be read whole' % address)
    print('\nwatching %08X, %d bytes' % (address, size))

    print('learning what moves on its own - leave the game alone for %.0f s' % args.quiet)
    time.sleep(args.quiet)
    quiet = read(handle, address, size)
    if quiet is None:
        raise SystemExit('the object went away')
    noise = {off for off in range(0, size - 3, 4)
             if first[off:off + 4] != quiet[off:off + 4]}
    print('%d words move by themselves: %s'
          % (len(noise), ' '.join('+%03X' % o for o in sorted(noise)) or 'none'))

    print('\nnow do the thing you want to see, then press Enter.')
    try:
        sys.stdin.readline()
    except KeyboardInterrupt:
        return
    after = read(handle, address, size)
    if after is None:
        raise SystemExit('the object went away')

    changed = [off for off in range(0, size - 3, 4)
               if quiet[off:off + 4] != after[off:off + 4]]
    interesting = [off for off in changed if off not in noise]
    print('\n%d words differ, %d of them after the noise is set aside\n'
          % (len(changed), len(interesting)))
    for off in interesting:
        print(describe(quiet, after, off))
    if not interesting:
        print('  nothing outside the noise - whatever it was, it is not in this object')


if __name__ == '__main__':
    main()
