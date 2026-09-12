"""Puts sounds of our own into sounds.ubn, so the game can play them by name.

The game finds a sound by its bare file name, and the names it knows come
from the archive's directory: a loose file under Sounds\\ replaces an entry
of the same name (which is how the body hit sounds were fixed), but a new
name in a new folder is not found at all - the play call answers E_FAIL and
the log says "Sound not found. ''". So a new sound goes into the archive.

The .ubn files are plain ZIPs with stored entries, but not for Python's
zipfile to append to: it rewrites the central directory, and the five
SchussTreffer_Körper names come out as UTF-8 instead of the bytes the game
knows. So this appends by hand - the stored entries go in front of the old
central directory, the old directory is copied byte for byte, the new
entries and a fresh end record follow. An entry already there is skipped,
so the package build can run this every time.

Usage:
    python add_sounds.py <archive> <folder-in-archive> <wav>...
    python add_sounds.py F:\\Games\\SoA\\_patched\\sounds.ubn sounds/InGame/radio launcher/radio_airstrike_*.wav
"""
import glob
import os
import struct
import sys
import zlib

LOCAL, CENTRAL, END = b'PK\x03\x04', b'PK\x01\x02', b'PK\x05\x06'


def add(archive, folder, files):
    """Returns the names added; an empty list when every one was there."""
    data = open(archive, 'rb').read()
    eocd = data.rfind(END)
    if eocd < 0:
        raise SystemExit('%s is not a ZIP' % archive)
    count, cd_size, cd_start = struct.unpack_from('<HII', data, eocd + 10)
    cd = data[cd_start:cd_start + cd_size]
    have = set()
    p = 0
    while p < len(cd) and cd[p:p + 4] == CENTRAL:
        n, m, k = struct.unpack_from('<HHH', cd, p + 28)
        have.add(cd[p + 46:p + 46 + n])
        p += 46 + n + m + k
    body = bytearray(data[:cd_start])
    new_cd = bytearray()
    added = []
    for f in files:
        name = (folder.rstrip('/') + '/' + os.path.basename(f)).encode('ascii')
        if name in have:
            continue
        content = open(f, 'rb').read()
        crc = zlib.crc32(content) & 0xFFFFFFFF
        offset = len(body)
        head = struct.pack('<HHHHHIIIHH', 20, 0, 0, 0, 0x21, crc, len(content), len(content), len(name), 0)
        body += LOCAL + head + name + content
        new_cd += CENTRAL + struct.pack('<HHHHHHIIIHHHHHII', 20, 20, 0, 0, 0, 0x21, crc, len(content), len(content),
                                        len(name), 0, 0, 0, 0, 0, offset) + name
        added.append(name.decode())
    if not added:
        return []
    out = body + cd + new_cd
    total = count + len(added)
    out += END + struct.pack('<HHHHIIH', 0, 0, total, total, len(cd) + len(new_cd), len(body), 0)
    tmp = archive + '.new'
    open(tmp, 'wb').write(out)
    os.replace(tmp, archive)
    return added


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    archive, folder = sys.argv[1], sys.argv[2]
    files = [f for pattern in sys.argv[3:] for f in glob.glob(pattern)]
    if not files:
        raise SystemExit('no such files')
    added = add(archive, folder, files)
    print('%d added to %s' % (len(added), archive) if added else 'all %d already in %s' % (len(files), archive))


if __name__ == '__main__':
    main()
