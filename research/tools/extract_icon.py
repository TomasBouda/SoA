"""Pulls the icon out of a PE file into an .ico.

Used once, to get the game icon for the launcher:

    python extract_icon.py ..\\..\\_patched\\soa.exe launcher\\soa.ico

The resulting .ico is committed next to App.cs so that building the package
stays dependent only on what ships with Windows (csc.exe of the .NET
Framework).

The icon is not stored in one piece in a PE. The RT_GROUP_ICON (14) resource is
only a directory that references the individual sizes by id in RT_ICON (3); an
.ico file has the same structure, it just carries an offset instead of the id.
So the conversion is mostly about putting the two parts back together.
"""

import struct
import sys


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def load_pe(path):
    d = open(path, 'rb').read()
    pe = u32(d, 0x3c)
    assert d[pe:pe + 4] == b'PE\0\0', 'not a PE file'
    coff = pe + 4
    nsec = u16(d, coff + 2)
    opt = coff + 20
    optsize = u16(d, coff + 16)
    pe32plus = u16(d, opt) == 0x20b
    ddir = opt + (112 if pe32plus else 96)
    res_rva = u32(d, ddir + 8 * 2)
    assert res_rva, 'the file has no resource section'

    sections = []
    sec = opt + optsize
    for i in range(nsec):
        o = sec + 40 * i
        sections.append((u32(d, o + 12), u32(d, o + 16), u32(d, o + 20)))  # rva, size, raw

    def to_offset(rva):
        for rva0, size, raw in sections:
            if rva0 <= rva < rva0 + size:
                return raw + (rva - rva0)
        raise ValueError('RVA 0x%x lies in no section' % rva)

    return d, to_offset, to_offset(res_rva)


def walk(d, base, off, level=0):
    """Return {id: (offset of the next level | (rva, size))} for one tree node."""
    nnamed = u16(d, off + 12)
    nid = u16(d, off + 14)
    out = {}
    for i in range(nnamed + nid):
        e = off + 16 + 8 * i
        name = u32(d, e)
        entry = u32(d, e + 4)
        key = name & 0x7FFFFFFF if name & 0x80000000 else name
        if entry & 0x80000000:
            out[key] = ('dir', base + (entry & 0x7FFFFFFF))
        else:
            data = base + entry
            out[key] = ('data', u32(d, data), u32(d, data + 4))  # rva, size
    return out


def first_leaf(d, base, node):
    """Descend the tree down to the data - the language level does not matter."""
    kind = node[0]
    while kind == 'dir':
        children = walk(d, base, node[1])
        node = children[sorted(children)[0]]
        kind = node[0]
    return node[1], node[2]


def extract(exe, ico):
    d, to_offset, res = load_pe(exe)
    types = walk(d, res, res)
    if 14 not in types or 3 not in types:
        raise SystemExit('there are no icons in %s' % exe)

    groups = walk(d, res, types[14][1])
    rva, size = first_leaf(d, res, groups[sorted(groups)[0]])
    grp = d[to_offset(rva):to_offset(rva) + size]

    icons = walk(d, res, types[3][1])
    count = u16(grp, 4)
    images = []
    for i in range(count):
        e = 6 + 14 * i
        ident = u16(grp, e + 12)
        irva, isize = first_leaf(d, res, icons[ident])
        # The first eight bytes (width, height, colours, reserve, planes, bits)
        # are the same in both formats; the rest of the entry is computed below.
        images.append((grp[e:e + 8], d[to_offset(irva):to_offset(irva) + isize]))

    # An entry in an .ico is 16 bytes: the eight shared ones, then the size of
    # the data and the offset where it starts in the file. A PE carries a
    # two-byte resource id instead of the offset.
    offset = 6 + 16 * count
    head = struct.pack('<HHH', 0, 1, count)
    body = b''
    for meta, data in images:
        head += meta + struct.pack('<II', len(data), offset)
        body += data
        offset += len(data)

    open(ico, 'wb').write(head + body)
    print('%s -> %s' % (exe, ico))
    for meta, data in images:
        w, h, colors = meta[0] or 256, meta[1] or 256, meta[2]
        print('  %3dx%-3d  %s colours  %6d B' % (w, h, colors or 'true', len(data)))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: extract_icon.py <exe> <ico>')
    extract(sys.argv[1], sys.argv[2])
