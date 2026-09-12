"""Calls an air strike inside the running game, on points of our choosing.

The game has the whole mechanism (architecture.md, "The air strike is a
shipped feature"): a plane with bombs in the bunker's hangar, a list of
target points, and one function that sends the plane. What the shipped game
lacks in most missions is the target markers, so the button never shows. This
tool skips the button and calls the launch with points of its own - which is
exactly what the developers' `AirStrike` console command did, except that it
flew a fixed diagonal.

What is injected, read off the console case at 0x6D48AD:

    vector<xyz> points = {}            ; 16 bytes on the stack: alloc, first, last, end
    AirStrike strike;                  ; 4 bytes, the ctor 0x6B8D20 only writes a vtable
    points.insert(points.end(), 1, p)  ; 0x6AF670, thiscall, once per point
    strike.Launch(&points)             ; 0x6B9030, thiscall, ret 4
    free(points.first)                 ; 0x756600

The launch answers 0 when a plane went, 1 when no plane with ammunition was
in the bunker, and a negative HRESULT when something else refused. It is safe
to call with nothing in the hangar - it just says 1.

Safety: the bunker global 0x8759C0 must be set and a mission must be running
(the world global 0x880F98 non-null), otherwise the plane has nowhere to be
put. The injector refuses both cases before writing anything.

Usage:
    python airstrike_inject.py --at 560,560
    python airstrike_inject.py --at 560,560 --at 600,540      (two bombs, two points)
    python airstrike_inject.py --status
"""
import argparse
import ctypes
import struct
from ctypes import wintypes

import scan_memory as sm

# Addresses valid for soa.exe 1.1.2.178. ASLR is off, so they are stable.
CTOR_STRIKE = 0x006B8D20
VECTOR_INSERT = 0x006AF670
LAUNCH = 0x006B9030
FREE = 0x00756600
BUNKER_GLOBAL = 0x008759C0
WORLD_GLOBAL = 0x00880F98

MEM_COMMIT_RESERVE = 0x3000
PAGE_EXECUTE_READWRITE = 0x40
MEM_RELEASE = 0x8000

k32 = sm.k32
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                               wintypes.DWORD, wintypes.DWORD]
k32.CreateRemoteThread.restype = wintypes.HANDLE


def shellcode(strike_address, point_addresses, result_address):
    """The console case, with the points taken from our memory instead of
    immediates. The vector lives on the thread's stack, like the original."""
    b = bytearray()
    b += b'\x83\xEC\x10'                                    # sub esp, 0x10
    b += b'\x31\xC0'                                        # xor eax, eax
    b += b'\x89\x04\x24'                                    # mov [esp], eax
    b += b'\x89\x44\x24\x04'                                # mov [esp+4], eax
    b += b'\x89\x44\x24\x08'                                # mov [esp+8], eax
    b += b'\x89\x44\x24\x0C'                                # mov [esp+0xC], eax
    b += b'\xB9' + struct.pack('<I', strike_address)        # mov ecx, strike
    b += b'\xB8' + struct.pack('<I', CTOR_STRIKE)           # mov eax, ctor
    b += b'\xFF\xD0'                                        # call eax
    for address in point_addresses:
        b += b'\x8B\x44\x24\x08'                            # mov eax, [esp+8]   ; end()
        b += b'\x68' + struct.pack('<I', address)           # push &point
        b += b'\x6A\x01'                                    # push 1
        b += b'\x50'                                        # push eax
        b += b'\x8D\x4C\x24\x0C'                            # lea ecx, [esp+0xC] ; the vector
        b += b'\xB8' + struct.pack('<I', VECTOR_INSERT)     # mov eax, insert
        b += b'\xFF\xD0'                                    # call eax           ; ret 0xC
    b += b'\x8D\x04\x24'                                    # lea eax, [esp]
    b += b'\x50'                                            # push eax           ; &points
    b += b'\xB9' + struct.pack('<I', strike_address)        # mov ecx, strike
    b += b'\xB8' + struct.pack('<I', LAUNCH)                # mov eax, launch
    b += b'\xFF\xD0'                                        # call eax           ; ret 4
    b += b'\xA3' + struct.pack('<I', result_address)        # mov [result], eax
    b += b'\xFF\x74\x24\x04'                                # push [esp+4]       ; first
    b += b'\xB8' + struct.pack('<I', FREE)                  # mov eax, free
    b += b'\xFF\xD0'                                        # call eax
    b += b'\x83\xC4\x04'                                    # add esp, 4
    b += b'\xA1' + struct.pack('<I', result_address)        # mov eax, [result]
    b += b'\x83\xC4\x10'                                    # add esp, 0x10
    b += b'\xC2\x04\x00'                                    # ret 4
    return bytes(b)


def status(h):
    bunker = struct.unpack('<I', sm.read(h, BUNKER_GLOBAL, 4) or b'\0\0\0\0')[0]
    world = struct.unpack('<I', sm.read(h, WORLD_GLOBAL, 4) or b'\0\0\0\0')[0]
    return bunker, world


def run(points, process='soa.exe', pid=None, dry_run=False):
    pid = pid or sm.find_process(process)
    if not pid:
        raise SystemExit('%s is not running' % process)
    h = sm.open_process(pid, write=True)
    bunker, world = status(h)
    if not bunker:
        raise SystemExit('there is no bunker yet (0x8759C0 is null) - start the game properly')
    if not world:
        raise SystemExit('no mission is running (0x880F98 is null) - the plane would have nowhere to go')

    memory = k32.VirtualAllocEx(h, None, 0x1000, MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
    if not memory:
        raise SystemExit('allocation in the process failed (%d)' % ctypes.get_last_error())
    try:
        strike_address = memory
        result_address = memory + 0x10
        point_addresses = [memory + 0x20 + 12 * i for i in range(len(points))]
        code_address = memory + 0x100

        sm.write_value(h, strike_address, b'\0' * 4)
        sm.write_value(h, result_address, b'\xEE\xEE\xEE\xEE')
        for address, (x, y, z) in zip(point_addresses, points):
            sm.write_value(h, address, struct.pack('<fff', x, y, z))
        code = shellcode(strike_address, point_addresses, result_address)
        sm.write_value(h, code_address, code)

        if dry_run:
            print('bunker 0x%08X world 0x%08X, %d point(s), code at 0x%08X (%d B)'
                  % (bunker, world, len(points), code_address, len(code)))
            return

        thread = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(code_address),
                                        None, 0, None)
        if not thread:
            raise SystemExit('cannot create a thread (%d)' % ctypes.get_last_error())
        k32.WaitForSingleObject(thread, 5000)
        returned = wintypes.DWORD()
        k32.GetExitCodeThread(thread, ctypes.byref(returned))
        k32.CloseHandle(thread)
        value = returned.value
        if value == 0:
            print('launched: a plane is on its way to %s' % ', '.join('(%g, %g)' % (x, y) for x, y, z in points))
        elif value == 1:
            print('the game found no plane with ammunition in the bunker (returned 1)')
        else:
            print('the game refused (0x%08X) - tracefile.log says why' % value)
    finally:
        k32.VirtualFreeEx(h, ctypes.c_void_p(memory), 0, MEM_RELEASE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--at', action='append', metavar='X,Y[,Z]',
                    help='a target point in world units; repeat for more bombs')
    ap.add_argument('--status', action='store_true', help='only tell whether injecting is possible')
    ap.add_argument('--dry-run', action='store_true', help='prepare it but do not run it')
    ap.add_argument('--pid', type=int)
    args = ap.parse_args()

    if args.status:
        pid = args.pid or sm.find_process('soa.exe')
        if not pid:
            raise SystemExit('soa.exe is not running')
        bunker, world = status(sm.open_process(pid))
        print('pid %d, bunker 0x%08X, world 0x%08X -> %s' % (
            pid, bunker, world,
            'a mission is running, injecting is possible' if bunker and world
            else 'not in a mission'))
        return

    if not args.at:
        raise SystemExit('give at least one --at X,Y')
    points = []
    for text in args.at:
        parts = [float(p) for p in text.split(',')]
        if len(parts) == 2:
            parts.append(0.0)
        if len(parts) != 3:
            raise SystemExit('a point is X,Y or X,Y,Z: %r' % text)
        points.append(tuple(parts))
    run(points, pid=args.pid, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
