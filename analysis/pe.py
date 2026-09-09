import struct, sys

def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def analyze(path):
    d=open(path,'rb').read()
    e_lfanew=u32(d,0x3c)
    assert d[e_lfanew:e_lfanew+4]==b'PE\0\0', 'not PE'
    coff=e_lfanew+4
    machine=u16(d,coff); nsec=u16(d,coff+2); tstamp=u32(d,coff+4)
    opthdr_size=u16(d,coff+16); chars=u16(d,coff+18)
    opt=coff+20
    magic=u16(d,opt)
    pe32plus = magic==0x20b
    subsystem=u16(d,opt+68)
    dllchars=u16(d,opt+70)
    imgbase = u32(d,opt+28) if not pe32plus else struct.unpack_from('<Q',d,opt+24)[0]
    ddir_off = opt + (112 if pe32plus else 96)
    nddir = u32(d, opt + (108 if pe32plus else 92))
    print(f'File: {path}')
    print(f'  Machine: 0x{machine:04x} ({"x86-32" if machine==0x14c else "x64" if machine==0x8664 else machine})')
    print(f'  TimeStamp: {tstamp} ', end='')
    import datetime; print(datetime.datetime.utcfromtimestamp(tstamp).isoformat())
    print(f'  Characteristics: 0x{chars:04x} (LARGE_ADDRESS_AWARE={bool(chars&0x20)})')
    print(f'  Subsystem: {subsystem} ({"GUI" if subsystem==2 else "CUI" if subsystem==3 else subsystem})')
    print(f'  DllCharacteristics: 0x{dllchars:04x} (DEP/NX={bool(dllchars&0x100)}, ASLR={bool(dllchars&0x40)}, TS-aware={bool(dllchars&0x2000)})')
    print(f'  ImageBase: 0x{imgbase:x}')
    # sections
    sec=opt+opthdr_size
    secs=[]
    print('  Sections:')
    for i in range(nsec):
        o=sec+i*40
        name=d[o:o+8].rstrip(b'\0').decode('latin1')
        vsize=u32(d,o+8); vaddr=u32(d,o+12); rsize=u32(d,o+16); raddr=u32(d,o+20); c=u32(d,o+36)
        secs.append((vaddr,vsize,raddr,rsize,name))
        print(f'    {name:10s} VA=0x{vaddr:08x} VSize=0x{vsize:08x} RawSz=0x{rsize:08x} Chars=0x{c:08x}')
    def rva2off(rva):
        for vaddr,vsize,raddr,rsize,name in secs:
            if vaddr<=rva<vaddr+max(vsize,rsize):
                return raddr+(rva-vaddr)
        return None
    def cstr(off):
        end=d.index(b'\0',off); return d[off:end].decode('latin1')
    # imports
    imp_rva=u32(d,ddir_off+8*1); imp_size=u32(d,ddir_off+8*1+4)
    print('  Imports:')
    if imp_rva:
        o=rva2off(imp_rva)
        while True:
            oft=u32(d,o); tstamp2=u32(d,o+4); fwd=u32(d,o+8); namerva=u32(d,o+12); fthunk=u32(d,o+16)
            if namerva==0 and fthunk==0: break
            dll=cstr(rva2off(namerva))
            funcs=[]
            th=rva2off(oft or fthunk)
            while True:
                v=u32(d,th)
                if v==0: break
                if v & 0x80000000:
                    funcs.append(f'#{v & 0xffff}')
                else:
                    no=rva2off(v)
                    funcs.append(cstr(no+2))
                th+=4
            print(f'    {dll} ({len(funcs)})')
            for f in funcs: print(f'        {f}')
            o+=20
    # delay imports dir 13
    dl_rva=u32(d,ddir_off+8*13)
    if dl_rva:
        print('  (has delay-load imports)')
    # exports? resources
    res_rva=u32(d,ddir_off+8*2)
    print(f'  Resource dir RVA: 0x{res_rva:x}')

for p in sys.argv[1:]:
    analyze(p); print()
