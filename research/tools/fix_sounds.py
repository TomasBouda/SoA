"""Fix for the missing body hit sounds.

The game reports 'Sound not found. SchussTreffer_Koerper_1.wav' (with an
umlaut) even though the files are in sounds.ubn. The cause is a 2002 bug in the
archive:

  central directory of the archive: SchussTreffer_K\\x94rper_1.wav (0x94 = 'o' in cp437, DOS)
  local header of the same entry:   SchussTreffer_K\\xf6rper_1.wav (0xf6 = 'o' in cp1252, Windows)
  what the exe asks for:            SchussTreffer_K\\xf6rper_1.wav

So the packing tool wrote each copy of the name in a different code page. The
archive reader in the game starts from the central directory, which is why it
never finds the file.

The script pulls the data out (zipfile refuses because of that mismatch, so it
is read by hand) and saves it loose next to the game under the name the game
looks for.

Usage:  python fix_sounds.py [target_folder]
"""
import os
import struct
import sys
import zipfile
import zlib

UBN = r'..\_patched\sounds.ubn'
DEFAULT_OUT = r'..\_patched'
NEEDLE = b'SchussTreffer_K\x94rper'


def raw_extract(path, info):
    """Read an entry without checking that the directory and header names match."""
    with open(path, 'rb') as f:
        f.seek(info.header_offset)
        head = f.read(30)
        if head[:4] != b'PK\x03\x04':
            raise ValueError('bad local header')
        namelen, extralen = struct.unpack_from('<HH', head, 26)
        f.seek(info.header_offset + 30 + namelen + extralen)
        blob = f.read(info.compress_size)
    if info.compress_type == zipfile.ZIP_STORED:
        return blob
    return zlib.decompress(blob, -15)


def main():
    out_root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    z = zipfile.ZipFile(UBN)
    n = 0
    for info in z.infolist():
        raw = info.orig_filename.encode('cp437')
        if NEEDLE not in raw:
            continue
        fixed = raw.replace(b'\x94', b'\xf6').decode('cp1252')
        dest = os.path.join(out_root, fixed.replace('/', os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        data = raw_extract(UBN, info)
        with open(dest, 'wb') as f:
            f.write(data)
        print('  %-36s %7d B' % (os.path.basename(fixed), len(data)))
        n += 1
    print('files fixed: %d' % n)
    if n:
        print('target: %s' % os.path.abspath(os.path.join(out_root, 'Sounds', 'InGame', 'weapons')))


if __name__ == '__main__':
    main()
