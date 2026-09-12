"""Reader for the mission files (.mis) of Soldiers of Anarchy.

A mission is a container of the same family as the saves (magic byte 0x38) and
falls into three parts:

    header      version, map size, the list of parties
    terrain     a row of zlib streams, 32 KB each when unpacked
    contents    the placed objects, then the units, characters and scripts

The header and the terrain are understood, the object table is read as a fixed
44-byte record, and everything past it is still unmapped - the tool reports it
as "tail" so it is visible how much is left.

What is now known of the tail
-----------------------------
It opens with a 4x4 matrix - where the camera starts - and the serialiser's
`FF FF FF FF 01`, the same prefix the saves use.

Then the **parties**, one record each, ending in a length-prefixed name. Their
records shrink by eight bytes each in turn - 116, 108, 100, 92, 84, 76, 68 in
an eight party mission - which is what a triangular table of who stands with
whom looks like: the first party needs a relation to seven others, the last to
none.

Then the **characters**, at a nearly fixed stride - 357 bytes in one mission,
417 in another. Each is a length-prefixed name, a zero byte, eight bytes of
`FF`, and then eight numbers. Four of them sit between 50 and 78 across every
character in every mission looked at, which is what a skill out of a hundred
looks like; two more move together and by party, so they are more likely to be
which face and body the man is drawn with. `--people` lists them.

**The last number is one of the soldier's special skills**, an index into
the seven the editor's own resources list - light weapon, heavy weapon,
demolition, sniper, heal, thief, athlet - with an eighth meaning none. Over 581
characters in every mission in the archive it never leaves that range once the
version is accounted for.

A soldier carries **two** of them - the infirmary panel has `SPECIALSKILL1` and
`SPECIALSKILL2` - and in versions 3 to 6 both sit at the end of the record. In 9
and 10 only the last one is reliably placed, so the reader names that one and
leaves the other alone rather than inventing it.

Versions 9 and 10 carry one field more at the front, a constant 4, which shifts
everything behind it; read on the older alignment a skill lands where a number
in the sixties belongs, and that is how the shift showed itself.

**The four numbers in front of them are still unnamed.** They sit between 50 and
78 and behave like ability out of a hundred, but calling one of them accuracy
would be a guess. That wants the code that loads them.

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


NAME_TAIL = bytes([0]) + bytes([0xFF]) * 8


# The seven a soldier can have, in the order the editor's own resources list
# them - RES_EDITOR_QUICKSELECT_SPECIALSKILL_* in Editor.gui - with NONE last.
# The bunker's help text names only six of these; the thief is in the editor
# and not in the list of what a soldier may be taught.
SPECIAL_SKILLS = ('light weapon', 'heavy weapon', 'demolition', 'sniper',
                  'heal', 'thief', 'athlet', 'none')


def written_names(d, tail_at):
    """The strings a mission author typed, in the order they were written.

    Past the characters the tail holds the names of the regions drawn in the
    editor - `base/start`, `valley`, `timer 1` - and then the scripts, whose
    names the designers used as notes to themselves: `start mission -> start
    tutorial dialog`, `bear in small outpost killed -> wait 5 sec.`. After those
    come the dialogs and the music each event plays.

    Read in order they are a plain-language account of how the mission works,
    which is worth having on its own - the numbers around them, the ids the
    scripts reference, are not decoded.

    `unknown name` is what the engine calls everything nobody named, and the
    TRES keys are the interface's, so neither is the author's writing.
    """
    out = []
    i = tail_at
    while i < len(d) - 1:
        n = d[i]
        if 4 <= n <= 64 and i + 1 + n <= len(d):
            body = d[i + 1:i + 1 + n]
            if all(32 <= c < 127 for c in body):
                text = body.decode('latin1')
                letters = sum(c.isalpha() or c in ' _-/.>' for c in text)
                if (letters >= n * 0.8 and text != 'unknown name'
                        and not text.startswith('TRES_')):
                    out.append((i, text))
                i += 1 + n
                continue
        i += 1
    return out


def people(d, tail_at, version=0):
    """The characters in the tail: (offset, name, the eight numbers after it).

    A name here is one a mission author typed - two words with a space between
    them - and what confirms it is what follows: a zero byte, eight bytes of
    0xFF, and then eight numbers. That signature is what tells a character from
    an interface key and from four bytes of terrain that happen to read as
    letters.
    """
    found = []
    i = tail_at
    while i < len(d) - 1:
        n = d[i]
        if 3 <= n <= 40 and i + 1 + n <= len(d):
            body = d[i + 1:i + 1 + n]
            named = (all(32 <= c < 127 for c in body)
                     and body.count(32) == 1
                     and body != b'Player')
            after = i + 1 + n
            if named and d[after:after + 9] == NAME_TAIL and after + 41 <= len(d):
                found.append((i, body.decode('latin1'),
                              struct.unpack_from('<8I', d, after + 9)))
                i = after
                continue
        i += 1
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('member', nargs='?')
    ap.add_argument('--ubn', default=ROOT_UBN)
    ap.add_argument('--ids', action='store_true', help='histogram of object indexes')
    ap.add_argument('--names', action='store_true',
                    help='the regions, scripts, dialogs and music the author named')
    ap.add_argument('--people', action='store_true',
                    help='the characters in the tail, with the numbers after each name')
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
        d = z.read(n)
        m = parse(d)
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
        if args.names:
            got = written_names(d, len(d) - m['tail'])
            print('')
            print('  %d names the author wrote' % len(got))
            for at, text in got:
                print('    0x%-8X %s' % (at, text))
        if args.people:
            found = people(d, len(d) - m['tail'], m['version'])
            print('')
            print('  %d characters' % len(found))
            for at, who, nums in found:
                # Only the last field is named. A soldier carries two special
                # skills and in versions 3 to 6 both sit at the end, but in 9
                # and 10 the second is not reliably located yet, so naming it
                # would be inventing one.
                v = nums[-1]
                skills = SPECIAL_SKILLS[v] if v < len(SPECIAL_SKILLS) else '?'
                print('    0x%-7X %-22s %s   %s'
                      % (at, who, '  '.join('%4d' % v for v in nums[:-2]), skills))
        if args.ids:
            print('  object indexes: %s'
                  % ', '.join('%d x%d' % (k, v) for k, v in m['object_ids'].most_common(20)))


if __name__ == '__main__':
    main()
