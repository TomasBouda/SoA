"""Put a translation into the game's text resources.

The game keeps every line it shows in `.trs` files - 43 of them once the 1.1.1
patch has overridden the originals, 3042 records, about 134 000 characters. The
format is simple enough to write as well as read, and loose files beat the
archive, so a translation is deployed by dropping files next to the game.

    python translate.py --check                    read and rewrite all of them
    python translate.py --list TRES_OPTIONS        the keys of one file
    python translate.py --apply my-translation.tsv  write it into _patched
    python translate.py --off                      take the translation away

A translation file is tab separated: the resource name, the key, the new text.
Lines beginning with # are ignored, and `\\n` in the text becomes a newline, the
way the game stores it.

Before any of this is believed, `--check` reads every text resource and writes
it out again with nothing changed. The result has to be byte for byte what it
was; anything else means the writer is losing something, and a translation
built on a writer that loses things is worse than none.

The characters
--------------
The game asks Windows for its font with `fdwCharSet = 1`, DEFAULT_CHARSET,
which follows the machine's locale - on an English Windows that is code page
1252 and Czech loses its diacritics. `patch_exe.py --east-europe` changes those
ten bytes to 238, EASTEUROPE_CHARSET, and because the bitmap font is generated
from that Windows font at run time the change reaches every line the game
draws.

Text is written as UTF-8, which is what the game already stores. It was not
obvious - the strings are length-prefixed bytes and look like a single-byte
code page - but the German lines give it away: Aussenposten is spelled with
C3 9F where the sharp s belongs. The exe converts with code page 65001 at
0x50DC36 and 0x65B073 among others. Written as code page 1250 instead, every
accented character is an invalid sequence and comes out of the conversion as a
question mark, which is exactly what the first attempt put on the screen.
"""
import argparse
import io
import os
import struct
import sys
import zipfile

SOURCE = os.environ.get('SOA_SOURCE', r'F:\Games\SoA\_patched')
GAME = os.environ.get('SOA_GAME', r'F:\Games\SoA-Package\Game')

MAGIC = bytes([0x40, 0xF9, 0xB3, 0x0A, 0x62, 0x93, 0xD1, 0x11,
               0x9A, 0x2B, 0x08, 0x00, 0x00, 0x30, 0x05, 0x12])

# The archives the game mounts, later ones overriding earlier ones. The patch
# comes last because that is what it is for.
ARCHIVES = ('data.ubn', 'missions.ubn', '1.1.0.71-1.1.1.118.ubn')


# What a record looks like depends on the version, and it took a round trip
# over every file to find that out. Version 4 - which is what the mission
# scripts use, the half of the text that is actually spoken - carries two
# fields the interface resources do not: the sound file the line is read from
# and who reads it.
#
#   version 0     ordinal, key, german, text
#   version 1, 2  ordinal, key, german, text, reserve
#   version 3     ordinal, and five strings
#   version 4     ordinal, key, sound, text, speaker, party, and a dword
#
# The shapes were not guessed at: each was found by walking every file of that
# version with every plausible number of fields and keeping the one that ends
# exactly at the last byte, in every file, with no slack.
#
# The translatable string is the third in every one of them.
SHAPE = {0: (3, 0), 1: (4, 0), 2: (4, 0), 3: (5, 0), 4: (5, 4)}
TEXT = 2


class Record(object):
    __slots__ = ('ordinal', 'strings', 'tail')

    def __init__(self, ordinal, strings, tail):
        self.ordinal = ordinal
        self.strings = strings
        self.tail = tail

    @property
    def key(self):
        return self.strings[0]

    @property
    def text(self):
        return self.strings[TEXT]

    @text.setter
    def text(self, value):
        self.strings[TEXT] = value


def read(raw):
    """(version, [Record], whatever is left over) - nothing dropped."""
    if raw[:16] != MAGIC:
        raise ValueError('not a text resource')
    pos = 16
    version, count = struct.unpack_from('<II', raw, pos)
    pos += 8
    if version not in SHAPE:
        raise ValueError('text resource version %d is not known' % version)
    n_strings, n_tail = SHAPE[version]

    rows = []
    for _ in range(count):
        if pos + 4 > len(raw):
            break
        ordinal = struct.unpack_from('<I', raw, pos)[0]
        pos += 4
        strings = []
        for _ in range(n_strings):
            n = raw[pos]
            pos += 1
            if n == 0xFF:
                n = struct.unpack_from('<H', raw, pos)[0]
                pos += 2
            strings.append(raw[pos:pos + n])
            pos += n
        tail = raw[pos:pos + n_tail]
        pos += n_tail
        rows.append(Record(ordinal, strings, tail))
    return version, rows, raw[pos:]


def write(version, rows, leftover=b''):
    """The bytes back again, in the shape they came in."""
    out = bytearray(MAGIC)
    out += struct.pack('<II', version, len(rows))
    for r in rows:
        out.extend(struct.pack('<I', r.ordinal))
        for s in r.strings:
            if len(s) >= 0xFF:
                out.append(0xFF)
                out.extend(struct.pack('<H', len(s)))
            else:
                out.append(len(s))
            out.extend(s)
        out.extend(r.tail)
    out.extend(leftover)
    return bytes(out)


def resources(game=GAME):
    """{lower path: (archive, member)} with the patch having the last word."""
    found = {}
    for archive in ARCHIVES:
        path = os.path.join(game, archive)
        if not os.path.exists(path):
            continue
        with zipfile.ZipFile(path) as z:
            for member in z.namelist():
                if member.lower().endswith('.trs'):
                    found[member.lower()] = (path, member)
    return found


def raw_of(archive, member):
    with zipfile.ZipFile(archive) as z:
        return z.read(member)


def check(game=GAME):
    """Read every resource and write it out again unchanged."""
    same = differ = failed = 0
    for key, (archive, member) in sorted(resources(game).items()):
        try:
            original = raw_of(archive, member)
            version, rows, tail = read(original)
            again = write(version, rows, tail)
        except Exception as e:
            print('   could not be read: %-58s %s' % (member, e))
            failed += 1
            continue
        if again == original:
            same += 1
        else:
            differ += 1
            print('   DIFFERS: %-58s %d bytes in, %d out'
                  % (member, len(original), len(again)))
    print('\n%d files come back byte for byte, %d differ, %d could not be read'
          % (same, differ, failed))
    return differ == 0 and failed == 0


def find(game, name):
    for key, (archive, member) in resources(game).items():
        if os.path.splitext(os.path.basename(member))[0].lower() == name.lower():
            return archive, member
        if name.lower() in key:
            return archive, member
    return None, None


def show(game, name, longest=False):
    archive, member = find(game, name)
    if member is None:
        raise SystemExit('no text resource called %s' % name)
    version, rows, _ = read(raw_of(archive, member))
    print('%s - version %d, %d records\n' % (member, version, len(rows)))
    order = sorted(rows, key=lambda r: -len(r.text)) if longest else rows
    for r in order:
        print('%s\t%s\t%s' % (os.path.splitext(os.path.basename(member))[0],
                              r.key.decode('latin1'),
                              r.text.decode('cp1252', 'replace').replace('\n', '\\n')))


def export(game, name, path):
    """A translation file for one resource, ready to be filled in.

    Every line carries the original above it as a comment, so whoever is
    translating sees what it says without going back to the game, and the line
    below it is the same key with the text still in English - overwrite it.
    """
    archive, member = find(game, name)
    if member is None:
        raise SystemExit('no text resource called %s' % name)
    version, rows, _ = read(raw_of(archive, member))
    stem = os.path.splitext(os.path.basename(member))[0]
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# %s - %d records, version %d\n' % (member, len(rows), version))
        f.write('# Overwrite the third column. Keep the tabs.\n\n')
        for r in rows:
            text = r.text.decode('utf-8', 'replace').replace('\n', '\\n')
            f.write('%s\t%s\t%s\n'
                    % (stem, r.key.decode('latin1'), text))
    print('wrote %s - %d lines' % (path, len(rows)))


def speech(game, name):
    """The dubbing worksheet for one mission: line, speaker, and its sound file.

    Version 4 records carry the file each line is read from and the name of
    whoever reads it, so the mapping a dub needs is already in the data. The
    paths are relative to the mission folder, which is where a replacement
    goes - loose, beating the archive like everything else here.
    """
    archive, member = find(game, name)
    if member is None:
        raise SystemExit('no text resource called %s' % name)
    version, rows, _ = read(raw_of(archive, member))
    if version != 4:
        raise SystemExit('%s has no speech in it (version %d)' % (member, version))
    folder = member.rsplit('/', 2)[0]
    print('%s%s%d lines, %s spoken' % (member, '\t',
          len(rows), sum(1 for r in rows if r.strings[1] not in (b'', b'leer'))))
    for r in rows:
        snd = r.strings[1].decode('latin1')
        if not snd or snd.lower() == 'leer':
            continue
        print('%s%s%s/%s%s%s%s%s'
              % (r.key.decode('latin1'), '\t', folder, snd.replace(chr(92), '/'), '\t',
                 r.strings[3].decode('utf-8', 'replace'), '\t',
                 r.text.decode('utf-8', 'replace').replace(chr(10), ' ')))


def dub(game, into, name, key, mp3):
    """Put a recording where the game will find it instead of the original."""
    archive, member = find(game, name)
    if member is None:
        raise SystemExit('no text resource called %s' % name)
    version, rows, _ = read(raw_of(archive, member))
    for r in rows:
        if r.key.decode('latin1') != key:
            continue
        snd = r.strings[1].decode('latin1')
        if not snd or snd.lower() == 'leer':
            raise SystemExit('%s has no sound file' % key)
        folder = member.rsplit('/', 2)[0]
        rel = (folder + '/' + snd.replace(chr(92), '/')).split('/')
        target = os.path.join(into, *rel)
        if not os.path.isdir(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))
        shutil.copyfile(mp3, target)
        print('%s -> %s' % (mp3, target))
        print('the game reads this in preference to the archive')
        return
    raise SystemExit('%s has no record called %s' % (member, key))


def load_translation(path):
    """{(resource, key): text as UTF-8, which is what the game stores}"""
    out = {}
    with io.open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            resource, key, text = parts[0], parts[1], '\t'.join(parts[2:])
            out[(resource.lower(), key)] = text.replace('\\n', '\n').encode('utf-8')
    return out


def apply(path, game=GAME, into=SOURCE):
    table = load_translation(path)
    print('%d lines of translation' % len(table))
    touched = changed = 0
    used = set()
    wanted = set(r for r, _ in table)
    for key, (archive, member) in sorted(resources(game).items()):
        stem = os.path.splitext(os.path.basename(member))[0].lower()
        if stem not in wanted:
            continue
        version, rows, tail = read(raw_of(archive, member))
        hits = 0
        for r in rows:
            where = (stem, r.key.decode('latin1'))
            new = table.get(where)
            if new is not None:
                r.text = new
                used.add(where)
                hits += 1
        if not hits:
            continue
        target = os.path.join(into, *member.split('/'))
        folder = os.path.dirname(target)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(target, 'wb') as f:
            f.write(write(version, rows, tail))
        print('   %-58s %d of %d lines' % (member, hits, len(rows)))
        touched += 1
        changed += hits
    # Not len(table) - changed: a resource can exist twice over, once in its
    # own archive and once rewritten by the 1.1.1 patch, and a single line of
    # translation is then applied to both. Counting that way made the
    # arithmetic go negative and report minus one line missing. What is worth
    # knowing is which lines matched no record at all - a key mistyped, or a
    # resource whose name is not what it was thought to be.
    orphans = sorted(k for k in table if k not in used)
    print('\n%d files written, %d lines replaced' % (touched, changed))
    if orphans:
        print('%d lines matched no record:' % len(orphans))
        for resource, key in orphans[:12]:
            print('   %s\t%s' % (resource, key))
        if len(orphans) > 12:
            print('   and %d more' % (len(orphans) - 12))


def off(into=SOURCE):
    removed = 0
    for root, _dirs, files in os.walk(into):
        for f in files:
            if f.lower().endswith('.trs'):
                os.remove(os.path.join(root, f))
                removed += 1
    print('removed %d translated files' % removed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=GAME, help='where the archives are')
    ap.add_argument('--into', default=SOURCE, help='where the loose files go')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--list', metavar='NAME')
    ap.add_argument('--longest', action='store_true',
                    help='with --list, longest lines first - where the layout breaks')
    ap.add_argument('--export', nargs=2, metavar=('NAME', 'FILE'),
                    help='write a fillable translation file for one resource')
    ap.add_argument('--speech', metavar='NAME',
                    help='the dubbing worksheet for one mission')
    ap.add_argument('--dub', nargs=3, metavar=('NAME', 'KEY', 'MP3'),
                    help='install a recording over one spoken line')
    ap.add_argument('--apply', metavar='FILE')
    ap.add_argument('--off', action='store_true')
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

    if args.check:
        raise SystemExit(0 if check(args.game) else 1)
    if args.list:
        show(args.game, args.list, args.longest)
    elif args.speech:
        speech(args.game, args.speech)
    elif args.dub:
        dub(args.game, args.into, args.dub[0], args.dub[1], args.dub[2])
    elif args.export:
        export(args.game, args.export[0], args.export[1])
    elif args.apply:
        apply(args.apply, args.game, args.into)
    elif args.off:
        off(args.into)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
