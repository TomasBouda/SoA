"""Parser for the text resources (.trs) of Soldiers of Anarchy.

Format:
    16 B   magic GUID (40 f9 b3 0a 62 93 d1 11 9a 2b 08 00 00 30 05 12)
    u32    version (0, 1 or 2)
    u32    record count
    then for every record:
    u32    ordinal number
    str    resource id ("TRES_...")
    str    German text (always "leer" = empty in the English build)
    str    text
    str    reserve ("leer")   - only in version 1 and 2

    A version 0 file has no reserve string. TRES_TRADER.trs is the only one, and
    reading a fourth string there swallowed the following record and threw the
    whole file away with an IndexError.

    str = 1 B length + bytes (latin1); length 0xFF means a two-byte length
          follows - the long vehicle descriptions use it

Usage:
    python trs.py <file.trs>               print ids and texts
    python trs.py <archive.ubn> <pattern>  print every matching .trs in an archive
"""
import struct
import sys
import zipfile

MAGIC = bytes([0x40, 0xF9, 0xB3, 0x0A, 0x62, 0x93, 0xD1, 0x11,
               0x9A, 0x2B, 0x08, 0x00, 0x00, 0x30, 0x05, 0x12])


def parse(data):
    """Return a list of (id, text) pairs."""
    if data[:16] != MAGIC:
        raise ValueError('not a .trs file (bad magic)')
    pos = 16
    version, count = struct.unpack_from('<II', data, pos)
    pos += 8

    def rstr():
        """The length is one byte; 0xFF means a two-byte length follows.

        Without this the parser fell apart on TRES_BUNKER_DESCRIPTIONS, where
        the vehicle descriptions go past 254 characters.
        """
        nonlocal pos
        n = data[pos]
        pos += 1
        if n == 0xFF:
            n = struct.unpack_from('<H', data, pos)[0]
            pos += 2
        s = data[pos:pos + n].decode('latin1')
        pos += n
        return s

    out = []
    for _ in range(count):
        if pos + 4 > len(data):
            break
        pos += 4                      # ordinal number
        rid = rstr()
        rstr()                        # German ("leer" in the English build)
        text = rstr()
        if version >= 1:
            rstr()                    # reserve
        out.append((rid, text))
    return out


def load(path, member=None):
    if path.lower().endswith('.ubn'):
        with zipfile.ZipFile(path) as z:
            return parse(z.read(member))
    with open(path, 'rb') as f:
        return parse(f.read())


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    src = sys.argv[1]
    if src.lower().endswith('.ubn'):
        pattern = sys.argv[2] if len(sys.argv) > 2 else '.trs'
        with zipfile.ZipFile(src) as z:
            members = [n for n in z.namelist()
                       if n.lower().endswith('.trs') and pattern.lower() in n.lower()]
        for m in members:
            rows = load(src, m)
            print('=== %s (%d records) ===' % (m, len(rows)))
            for rid, text in rows:
                print('%-55s %s' % (rid, text))
            print()
    else:
        for rid, text in load(src):
            print('%-55s %s' % (rid, text))
