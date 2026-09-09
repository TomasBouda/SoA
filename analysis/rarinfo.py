import struct, sys, os, glob

METHODS = {0x30: 'store', 0x31: 'fastest', 0x32: 'fast', 0x33: 'normal', 0x34: 'good', 0x35: 'best'}

def rar4(path):
    d = open(path, 'rb').read()
    sig = d[:7]
    if sig[:6] != b'Rar!\x1a\x07':
        print('  not a RAR4 archive (sig=%r)' % sig[:8]); return
    pos = 7
    while pos < len(d) - 7:
        try:
            crc, btype, flags, size = struct.unpack_from('<HBHH', d, pos)
        except struct.error:
            break
        if size < 7:
            break
        add = 0
        off = pos + 7
        if btype == 0x74:  # file header: PACK_SIZE is the ADD_SIZE as well
            packsz, unpsz, hostos, filecrc, ftime, unpver, method, namesz, attr = \
                struct.unpack_from('<IIBIIBBHI', d, off)
            o2 = off + 25
            if flags & 0x100:
                o2 += 8
            name = d[o2:o2 + namesz].split(b'\0')[0].decode('latin1', 'replace')
            solid = bool(flags & 0x10)
            print('  %-24s packed=%-9d unpacked=%-9d method=%-8s solid=%-3s ver=%d' %
                  (name, packsz, unpsz, METHODS.get(method, hex(method)),
                   'yes' if solid else 'no', unpver))
            add = packsz
        elif flags & 0x8000:
            add = struct.unpack_from('<I', d, off)[0]
        pos += size + add

for p in sorted(glob.glob(sys.argv[1])):
    print('=== %s (%d B) ===' % (os.path.basename(p), os.path.getsize(p)))
    rar4(p)
