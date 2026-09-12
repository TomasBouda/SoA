"""A hit tracer for the running game: which functions run, with what.

There is no debugger in this project and the game's own trace mask says a
lot about commands and nothing about most functions. This is the third
way: a hook at the entry of each function of interest - a jump into a
trampoline in memory allocated in the game - that appends a record (which
hook, ecx, and the first three stack arguments) to a buffer and then runs
the displaced instructions and jumps back. The game logs nothing; the
buffer is read from outside afterwards.

    import probe, play_bot
    g = play_bot.Game()
    p = probe.Probe(g.h)
    p.hook({'OnStart': 0x711C60, 'Throw': 0x5E6980})
    ... make the game do something ...
    for name, ecx, a1, a2, a3 in p.hits():
        ...
    p.unhook()

A hook needs five bytes of prologue with no relative jump or call in them
(capstone checks; the ones that fail are reported, not hooked). The
arguments are read as if the function were thiscall or stdcall with the
arguments on the stack - for one that takes fewer, the extra values are
whatever was on the stack. A ring buffer of a megabyte holds fifty
thousand records, which is a few seconds of a busy function; read it
often or hook less.

This is how the M34 grenade's throw was found (m34_patch.py): hooking the
throw pipeline for a Molotov and for the new item showed where the two
parted - the animation ran for both, and Throw (0x5E6980) ran for one.
"""
import ctypes, struct
from ctypes import wintypes
import capstone
import scan_memory as sm

k32 = sm.k32
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
CS.detail = True
REC = 20


class Probe:
    def __init__(self, h, size=1 << 20):
        self.h = h
        self.base = k32.VirtualAllocEx(h, None, size + 0x20000, 0x3000, 0x40)
        assert self.base, ctypes.get_last_error()
        self.buf = self.base + 0x10000          # records
        self.end = self.buf + size - 2 * REC   # the wrap check comes after the write
        self.ptr = self.base                    # [base] = write pointer, [base+4] = overflow count
        sm.write_value(h, self.base, struct.pack('<II', self.buf, 0))
        self.code = self.base + 0x100
        self.hooks = []                         # (addr, original bytes)
        self.names = {}

    def poke(self, va, data):
        old = wintypes.DWORD()
        k32.VirtualProtectEx(self.h, ctypes.c_void_p(va), len(data), 0x40, ctypes.byref(old))
        sm.write_value(self.h, va, data)
        k32.VirtualProtectEx(self.h, ctypes.c_void_p(va), len(data), old.value, ctypes.byref(old))

    def displaced(self, at):
        code = sm.read(self.h, at, 32)
        n = 0
        for ins in CS.disasm(code, at):
            if ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_RET):
                raise ValueError('%08X: relative control flow in the prologue: %s %s' % (at, ins.mnemonic, ins.op_str))
            n += ins.size
            if n >= 5:
                return code[:n]
        raise ValueError('%08X: prologue too short' % at)

    def hook(self, targets):
        for pid, (name, at) in enumerate(targets.items(), 1):
            orig = self.displaced(at)
            self.names[pid] = name
            cave = self.code
            c = b'\x9C\x60'                                        # pushfd; pushad
            c += b'\xA1' + struct.pack('<I', self.ptr)             # mov eax, [ptr]
            c += b'\xC7\x00' + struct.pack('<I', pid)              # mov [eax], pid
            c += b'\x89\x48\x04'                                   # mov [eax+4], ecx
            c += b'\x8B\x54\x24\x28' + b'\x89\x50\x08'             # mov edx, [esp+0x28] (arg1); mov [eax+8], edx
            c += b'\x8B\x54\x24\x2C' + b'\x89\x50\x0C'             # arg2
            c += b'\x8B\x54\x24\x30' + b'\x89\x50\x10'             # arg3
            c += b'\x83\xC0' + bytes([REC])                        # add eax, REC
            c += b'\x3D' + struct.pack('<I', self.end)             # cmp eax, end
            c += b'\x72\x05'                                       # jb +5
            c += b'\xB8' + struct.pack('<I', self.buf)             # mov eax, buf (wrap)
            c += b'\xA3' + struct.pack('<I', self.ptr)             # mov [ptr], eax
            c += b'\x61\x9D'                                       # popad; popfd
            c += orig
            back = at + len(orig)
            c += b'\xE9' + struct.pack('<i', back - (cave + len(c) + 5))
            sm.write_value(self.h, cave, c)
            self.poke(at, b'\xE9' + struct.pack('<i', cave - (at + 5)) + b'\x90' * (len(orig) - 5))
            self.hooks.append((at, orig))
            self.code += (len(c) + 15) & ~15

    def hits(self, clear=True):
        ptr = struct.unpack('<I', sm.read(self.h, self.ptr, 4))[0]
        data = sm.read(self.h, self.buf, ptr - self.buf)
        out = []
        for i in range(0, len(data), REC):
            pid, ecx, a1, a2, a3 = struct.unpack_from('<IIIII', data, i)
            out.append((self.names.get(pid, pid), ecx, a1, a2, a3))
        if clear:
            sm.write_value(self.h, self.ptr, struct.pack('<I', self.buf))
        return out

    def unhook(self):
        for at, orig in self.hooks:
            self.poke(at, orig)
        self.hooks = []
