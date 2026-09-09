"""A trainer that calls the base cheat directly inside the game process.

Why not through the keyboard: the cheats are typed on the base screen and the
key that opens the command line goes through DirectInput, so the game would
have to be focused - and the game drops to the taskbar as soon as it loses
focus. So it is called directly.

How it works
------------
The cheat dispatcher is a method at 0x52F4A0. It is called with ecx = this from
the global at 0x8759D4, one pushed cheat number (5 = vehicle, 4 = equipment)
and an argument of type tsString passed BY VALUE, that is built on the stack
right behind that number. Read off from how the developer cheats call it:

    sub  esp, 0x10           ; room for the tsString
    lea  edx, [esp+0x5b]     ; pointer to the flag byte
    mov  ecx, esp
    push edx
    push 0x849d60            ; the literal "(92)"
    call 0x405d80            ; tsString(text, flag)
    push 0xc                 ; cheat number
    mov  ecx, esi            ; this
    call 0x52f4a0

The string "(92)" is hardcoded in the exe, so it is enough to slip our own in.
The shellcode below does exactly this sequence; the tsString is built by the
game itself, so its destructor also disposes of it properly.

Safety: the global at 0x8759D4 is null until the base screen is running. While
it is null the injector refuses to continue - otherwise the game would crash.

Usage:
    python trainer_inject.py --vehicle 8
    python trainer_inject.py --equipment 125
    python trainer_inject.py --status
"""
import argparse
import ctypes
import struct
import sys
from ctypes import wintypes

import scan_memory as sm

# Addresses valid for soa.exe 1.1.2.178. ASLR is off, so they are stable.
DISPATCHER = 0x0052F4A0
CTOR_TSSTRING = 0x00405D80
THIS_GLOBAL = 0x008759D4

CHEAT_EQUIPMENT = 4
CHEAT_VEHICLE = 5

MEM_COMMIT_RESERVE = 0x3000
PAGE_EXECUTE_READWRITE = 0x40
MEM_RELEASE = 0x8000

k32 = sm.k32
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                               wintypes.DWORD, wintypes.DWORD]
k32.CreateRemoteThread.restype = wintypes.HANDLE


def shellcode(text_address, flag_address, cheat_number):
    """Assembles the same sequence the developer cheats use."""
    b = bytearray()
    b += b'\x83\xEC\x10'                                  # sub esp, 0x10
    b += b'\x8B\xCC'                                      # mov ecx, esp
    b += b'\x68' + struct.pack('<I', flag_address)        # push flag
    b += b'\x68' + struct.pack('<I', text_address)        # push text
    b += b'\xB8' + struct.pack('<I', CTOR_TSSTRING)       # mov eax, ctor
    b += b'\xFF\xD0'                                      # call eax
    b += b'\x68' + struct.pack('<I', cheat_number)        # push cheat number
    b += b'\x8B\x0D' + struct.pack('<I', THIS_GLOBAL)     # mov ecx, [this]
    b += b'\xB8' + struct.pack('<I', DISPATCHER)          # mov eax, dispatcher
    b += b'\xFF\xD0'                                      # call eax
    b += b'\xC2\x04\x00'                                  # ret 4
    return bytes(b)


def run(cheat_number, argument, process='soa.exe', pid=None, dry_run=False):
    pid = pid or sm.find_process(process)
    if not pid:
        raise SystemExit('%s is not running' % process)

    h = sm.open_process(pid, write=True)
    pointer = sm.read(h, THIS_GLOBAL, 4)
    if not pointer:
        raise SystemExit('cannot read from the game')
    this = struct.unpack('<I', pointer)[0]
    if this == 0:
        raise SystemExit('the base screen is not running (the global is null) - '
                         'the injection would take the game down')

    text = ('(%d)' % argument).encode('latin1') + b'\x00'
    code = None
    memory = k32.VirtualAllocEx(h, None, 0x1000, MEM_COMMIT_RESERVE,
                                PAGE_EXECUTE_READWRITE)
    if not memory:
        raise SystemExit('allocation in the process failed (%d)' % ctypes.get_last_error())
    try:
        text_address = memory
        flag_address = memory + 0x40      # one zero byte
        code_address = memory + 0x80
        code = shellcode(text_address, flag_address, cheat_number)

        sm.write_value(h, text_address, text)
        sm.write_value(h, flag_address, b'\x00')
        sm.write_value(h, code_address, code)

        if dry_run:
            print('this = 0x%08X, text %r at 0x%08X, code at 0x%08X (%d B)'
                  % (this, text, text_address, code_address, len(code)))
            return

        thread = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(code_address),
                                        None, 0, None)
        if not thread:
            raise SystemExit('cannot create a thread (%d)' % ctypes.get_last_error())
        k32.WaitForSingleObject(thread, 5000)
        returned = wintypes.DWORD()
        k32.GetExitCodeThread(thread, ctypes.byref(returned))
        k32.CloseHandle(thread)
        print('done, cheat %d%s returned %d'
              % (cheat_number, text.rstrip(b'\x00').decode(), returned.value))
    finally:
        k32.VirtualFreeEx(h, ctypes.c_void_p(memory), 0, MEM_RELEASE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vehicle', type=int, metavar='N')
    ap.add_argument('--equipment', type=int, metavar='N')
    ap.add_argument('--status', action='store_true', help='only tell whether injecting is possible')
    ap.add_argument('--dry-run', action='store_true', help='prepare it but do not run it')
    ap.add_argument('--pid', type=int)
    args = ap.parse_args()

    if args.status:
        pid = args.pid or sm.find_process('soa.exe')
        if not pid:
            raise SystemExit('soa.exe is not running')
        h = sm.open_process(pid)
        data = sm.read(h, THIS_GLOBAL, 4)
        this = struct.unpack('<I', data)[0] if data else 0
        print('pid %d, this = 0x%08X -> %s' % (
            pid, this, 'the base is running, injecting is possible' if this
            else 'the base is not running'))
        return

    if args.vehicle is not None:
        run(CHEAT_VEHICLE, args.vehicle, pid=args.pid, dry_run=args.dry_run)
    elif args.equipment is not None:
        run(CHEAT_EQUIPMENT, args.equipment, pid=args.pid, dry_run=args.dry_run)
    else:
        raise SystemExit('give --vehicle N, --equipment N or --status')


if __name__ == '__main__':
    main()
