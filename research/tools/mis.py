"""Reader for the mission files (.mis) of Soldiers of Anarchy.

A mission is a container of the same family as the saves (magic byte 0x38) and
falls into three parts:

    header      version, map size, the list of parties
    terrain     a row of zlib streams, 32 KB each when unpacked
    contents    the placed objects, then the units, characters and scripts

The header and the terrain are understood, the object table is read as a fixed
44-byte record, and everything past it is still unmapped - the tool reports it
as "tail" so it is visible how much is left.

    header      16 B magic, u32 version (3..10), u32 2, u32 sub-version
                u32 width, u32 height, u32 party count   <- big endian
                per party: u32 kind + a length-prefixed name
    terrain     per chunk: u32 packed length + a zlib stream
    objects     u32 unknown, u32 2, u32 count, then count records of 44 B:
                u32 library index, u32 attributes, 5 floats (x, y and three
                more), 16 bytes of 0xFF

The coordinates are in world units. In every mission the objects reach from 0 to
about 16 times the map size in both axes, so one map cell is 16 world units - a
75x75 mission is 1200x1200 units across.

Usage:
    python mis.py                       summary of every mission in the archive
    python mis.py <member>              one mission in detail
    python mis.py <member> --ids        plus the histogram of object indexes
"""
import argparse
import collections
import os
import struct
import sys
import zipfile
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ROOT_UBN = os.path.join(ROOT, '_patched', 'missions.ubn')
OBJECT_RECORD = 44


def read_string(d, pos):
    """1 byte length + bytes; returns (text, new position)."""
    n = d[pos]
    pos += 1
    return d[pos:pos + n], pos + n


def parse(d):
    """Return a dictionary describing one mission."""
    out = {'size': len(d)}
    if d[:8].hex() != '38f9b30a6293d111':
        raise ValueError('not a .mis file (bad magic)')

    version, a, sub = struct.unpack_from('<3I', d, 16)
    # The map size and the party count are written big endian, unlike
    # everything else in the file.
    width, height, parties = struct.unpack_from('>3I', d, 28)
    out.update(version=version, unknown=a, sub=sub,
               width=width, height=height, parties=parties)

    pos = 40
    names = []
    for _ in range(parties):
        if pos + 5 > len(d):
            break
        kind = struct.unpack_from('<I', d, pos)[0]
        raw, pos = read_string(d, pos + 4)
        names.append((kind, raw))
    out['party_names'] = names

    # --- terrain: a row of zlib streams ---
    # The streams follow one another without a gap. Scanning the whole file for
    # them instead would swallow the compressed blocks that lie further back and
    # the object table would never be found.
    def chunk_at(p):
        if p + 6 > len(d):
            return None
        n = struct.unpack_from('<I', d, p)[0]
        if not (0 < n <= len(d) - p - 4) or d[p + 4:p + 6] != b'\x78\xda':
            return None
        try:
            return n, len(zlib.decompress(d[p + 4:p + 4 + n]))
        except zlib.error:
            return None

    start = None
    for p in range(pos, min(pos + 4096, len(d) - 8)):
        if chunk_at(p):
            start = p
            break

    # The streams sit next to one another, but here and there a few bytes of
    # sector bookkeeping slip in between, so a small gap is allowed. Anything
    # larger ends the terrain - what follows is the object table.
    chunks = []
    pos = start if start is not None else pos
    while True:
        got = chunk_at(pos)
        if got:
            chunks.append(got)
            pos += 4 + got[0]
            continue
        for gap in (4, 8, 12, 16):
            if chunk_at(pos + gap):
                pos += gap
                break
        else:
            break
    out['chunks'] = chunks
    out['terrain_packed'] = sum(c[0] for c in chunks)
    out['terrain_raw'] = sum(c[1] for c in chunks)
    out['terrain_end'] = pos

    # --- the object table ---
    # Every record ends with sixteen 0xFF bytes, so the start of the table is
    # the first offset where that pattern repeats at the record stride.
    def records_from(p):
        n = 0
        while p + OBJECT_RECORD <= len(d) and d[p + 28:p + 44] == b'\xff' * 16:
            n += 1
            p += OBJECT_RECORD
        return n

    table = None
    for p in range(pos, min(pos + 64, len(d) - OBJECT_RECORD)):
        if records_from(p) >= 3:
            table = p
            break

    ids = collections.Counter()
    attrs = collections.Counter()
    count = 0
    xs = []
    ys = []
    p = table if table is not None else pos
    while p + OBJECT_RECORD <= len(d) and d[p + 28:p + 44] == b'\xff' * 16:
        index, attr = struct.unpack_from('<2I', d, p)
        x, y = struct.unpack_from('<2f', d, p + 8)
        ids[index] += 1
        attrs[attr] += 1
        xs.append(x)
        ys.append(y)
        count += 1
        p += OBJECT_RECORD
    out['extent'] = (min(xs), max(xs), min(ys), max(ys)) if xs else None
    out.update(objects=count, object_ids=ids, object_attrs=attrs, tail=len(d) - p)
    return out


def summary_line(name, m):
    return ('%-46s v%-3d %3dx%-3d %2d  %5d chunks %7.1f MB  %6d obj  %8d tail'
            % (name.split('/')[-1], m['version'], m['width'], m['height'],
               m['parties'], len(m['chunks']), m['terrain_raw'] / 1048576.0,
               m['objects'], m['tail']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('member', nargs='?')
    ap.add_argument('--ubn', default=ROOT_UBN)
    ap.add_argument('--ids', action='store_true', help='histogram of object indexes')
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    z = zipfile.ZipFile(args.ubn)
    members = sorted(n for n in z.namelist() if n.lower().endswith('.mis'))

    if not args.member:
        print('%-46s %-4s %-8s %-3s %s' % ('mission', 'ver', 'map', 'pty', 'terrain / objects'))
        for n in members:
            try:
                print(summary_line(n, parse(z.read(n))))
            except Exception as e:
                print('%-46s failed: %s' % (n.split('/')[-1], e))
        return

    matches = [n for n in members if args.member.lower() in n.lower()]
    if not matches:
        raise SystemExit('no mission matches %r' % args.member)
    for n in matches:
        m = parse(z.read(n))
        print('=== %s' % n)
        print('  file          %d bytes' % m['size'])
        print('  version       %d (%d, %d)' % (m['version'], m['unknown'], m['sub']))
        print('  map           %d x %d cells' % (m['width'], m['height']))
        print('  parties       %d' % m['parties'])
        print('  terrain       %d chunks, %d B packed -> %d B raw'
              % (len(m['chunks']), m['terrain_packed'], m['terrain_raw']))
        print('  objects       %d records of %d B' % (m['objects'], OBJECT_RECORD))
        print('  attributes    %s' % ', '.join('0x%08X x%d' % (k, v)
                                               for k, v in m['object_attrs'].most_common(4)))
        print('  unmapped tail %d bytes (units, characters, scripts)' % m['tail'])
        if args.ids:
            print('  object indexes: %s'
                  % ', '.join('%d x%d' % (k, v) for k, v in m['object_ids'].most_common(20)))


if __name__ == '__main__':
    main()
