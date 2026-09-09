"""Searching for values in the memory of the running game - the groundwork for the trainer.

soa.exe has ASLR off (DllCharacteristics 0x0000), so the global variables sit
at the same address on every start. Once it is found where the game keeps, say,
the ammunition, it can be overwritten at a fixed address from then on.

The procedure is the same as with any memory search: the first scan finds every
address holding the given value (there are thousands of them), then the value is
changed in the game and the next scan narrows the list down. After two or three
rounds a handful is left.

Usage:
    python scan_memory.py --first 250
        First scan: find every place holding the value 250.

    python scan_memory.py --next 180
        Narrowing: out of the earlier candidates keep only those that now hold 180.

    python scan_memory.py --list
        Print what is left.

    python scan_memory.py --write 0x00876543 999
        Write a value to an address.

    python scan_memory.py --watch 0x00876543
        Print the value until interrupted - to confirm the address is right.

Extra switches:
    --type float      look for a floating point number instead of an integer
    --process X.exe   a process other than soa.exe
    --pid 1234        pick the process by number when several are running
"""
import argparse
import ctypes
import json
import os
import struct
import sys
import time
from ctypes import wintypes

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
STATE = os.path.join(ROOT, '_research', '_trainer', 'candidates.json')

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008

MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
READABLE = (0x02, 0x04, 0x20, 0x40)   # READONLY, READWRITE, EXECUTE_READ, EXECUTE_READWRITE

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)

k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                               ctypes.c_void_p, ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.OpenProcess.restype = wintypes.HANDLE
# Without the declaration ctypes passes the module handle as a plain int and a
# 64-bit handle - which is what the modules of other processes have - ends in
# "int too long to convert".
psapi.GetModuleBaseNameW.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                     wintypes.LPWSTR, wintypes.DWORD]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wintypes.DWORD), ('RegionSize', ctypes.c_size_t),
                ('State', wintypes.DWORD), ('Protect', wintypes.DWORD),
                ('Type', wintypes.DWORD)]


def find_process(name):
    array = (wintypes.DWORD * 4096)()
    returned = wintypes.DWORD()
    psapi.EnumProcesses(ctypes.byref(array), ctypes.sizeof(array), ctypes.byref(returned))
    for pid in array[:returned.value // 4]:
        if not pid:
            continue
        h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not h:
            continue
        buf = ctypes.create_unicode_buffer(260)
        modules = (ctypes.c_void_p * 1)()
        needed = wintypes.DWORD()
        if psapi.EnumProcessModules(h, ctypes.byref(modules), ctypes.sizeof(modules),
                                    ctypes.byref(needed)):
            psapi.GetModuleBaseNameW(h, modules[0], buf, 260)
            if buf.value.lower() == name.lower():
                k32.CloseHandle(h)
                return pid
        k32.CloseHandle(h)
    return None


def open_process(pid, write=False):
    rights = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    if write:
        rights |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
    h = k32.OpenProcess(rights, False, pid)
    if not h:
        raise SystemExit('cannot open process %d (error %d)' % (pid, ctypes.get_last_error()))
    return h


def regions(h):
    """Yields (address, length) of every readable region of the process.

    It walks on until VirtualQueryEx fails. An earlier version stopped at
    0x7FFF0000 on the grounds that a 32-bit process has no business above it -
    except the first free region tends to be enormous, so that boundary was
    jumped in the very first round and nothing was walked at all.
    """
    mbi = MEMORY_BASIC_INFORMATION()
    address = 0
    while k32.VirtualQueryEx(h, ctypes.c_void_p(address), ctypes.byref(mbi),
                             ctypes.sizeof(mbi)):
        base = mbi.BaseAddress or 0
        if (mbi.State == MEM_COMMIT and mbi.Protect in READABLE
                and not (mbi.Protect & PAGE_GUARD)):
            yield base, mbi.RegionSize
        nxt = base + mbi.RegionSize
        if nxt <= address:
            break
        address = nxt


def read(h, address, length):
    buf = ctypes.create_string_buffer(length)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(address), buf, length,
                                 ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def write_value(h, address, data):
    written = ctypes.c_size_t()
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(address), data, len(data),
                                ctypes.byref(written))
    return bool(ok) and written.value == len(data)


def pack(value, kind):
    return struct.pack('<f' if kind == 'float' else '<i',
                       float(value) if kind == 'float' else int(value))


def unpack(data, kind):
    return struct.unpack('<f' if kind == 'float' else '<i', data)[0]


def load_state():
    if not os.path.exists(STATE):
        raise SystemExit('no candidates - start with the --first switch')
    with open(STATE) as f:
        s = json.load(f)
    return s['pid'], s['type'], [int(a) for a in s['addresses']]


def save_state(pid, kind, addresses):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, 'w') as f:
        json.dump({'pid': pid, 'type': kind, 'addresses': addresses}, f)


def first_scan(h, pid, value, kind):
    pattern = pack(value, kind)
    hits = []
    searched = 0
    for address, length in regions(h):
        data = read(h, address, length)
        if not data:
            continue
        searched += len(data)
        start = 0
        while True:
            i = data.find(pattern, start)
            if i < 0:
                break
            if i % 4 == 0:                      # values tend to be aligned
                hits.append(address + i)
            start = i + 1
    print('searched %.1f MB, candidates: %d' % (searched / 1048576.0, len(hits)))
    save_state(pid, kind, hits)
    if len(hits) < 40:
        show(h, hits, kind)
    else:
        print('change the value in the game and run --next <new value>')


def next_scan(h, pid, value, kind, addresses):
    pattern = pack(value, kind)
    left = [a for a in addresses if read(h, a, 4) == pattern]
    print('%d candidates narrowed down to %d' % (len(addresses), len(left)))
    save_state(pid, kind, left)
    if len(left) < 40:
        show(h, left, kind)
    else:
        print('change the value in the game and run --next again')


def show(h, addresses, kind):
    for a in addresses:
        data = read(h, a, 4)
        value = unpack(data, kind) if data else '?'
        # Addresses inside the exe image (below 0x800000) are static and
        # survive a restart.
        mark = '  <- static, inside the exe image' if a < 0x800000 else ''
        print('  0x%08X = %s%s' % (a, value, mark))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--process', default='soa.exe')
    ap.add_argument('--pid', type=int, help='pick the process by number when several run')
    ap.add_argument('--type', default='int', choices=('int', 'float'))
    ap.add_argument('--first')
    ap.add_argument('--next', dest='next_value')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--write', nargs=2, metavar=('ADDRESS', 'VALUE'))
    ap.add_argument('--watch', metavar='ADDRESS')
    args = ap.parse_args()

    pid = args.pid or find_process(args.process)
    if not pid:
        raise SystemExit('%s is not running' % args.process)
    print('process %d' % pid)

    if args.first is not None:
        h = open_process(pid)
        first_scan(h, pid, args.first, args.type)
    elif args.next_value is not None:
        saved_pid, kind, addresses = load_state()
        if saved_pid != pid:
            raise SystemExit('the game restarted in the meantime, start over with --first')
        h = open_process(pid)
        next_scan(h, pid, args.next_value, kind, addresses)
    elif args.list:
        _, kind, addresses = load_state()
        h = open_process(pid)
        print('candidates: %d' % len(addresses))
        show(h, addresses[:40], kind)
    elif args.write:
        address = int(args.write[0], 0)
        h = open_process(pid, write=True)
        before = read(h, address, 4)
        if not write_value(h, address, pack(args.write[1], args.type)):
            raise SystemExit('the write failed (error %d)' % ctypes.get_last_error())
        print('0x%08X: %s -> %s' % (address, unpack(before, args.type) if before else '?',
                                    args.write[1]))
    elif args.watch:
        address = int(args.watch, 0)
        h = open_process(pid)
        last = None
        try:
            while True:
                data = read(h, address, 4)
                if data and data != last:
                    print('0x%08X = %s' % (address, unpack(data, args.type)))
                    last = data
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
    else:
        raise SystemExit('give --first, --next, --list, --write or --watch')


if __name__ == '__main__':
    main()
