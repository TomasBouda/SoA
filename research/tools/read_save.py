"""Read a Soldiers of Anarchy save and say what is in it.

Saves are not compressed and not obfuscated. A `.sav` is the game's own
serialiser writing objects one after another, and the pieces that matter -
which mission, which parties, who is in the squad, what is on the map - are
plain enough to pull out without understanding every field.

    python read_save.py                            list the saves
    python read_save.py QuickSave                  what is in that one
    python read_save.py M3 --roster                every name in it
    python read_save.py M3 --strings               everything, unfiltered

Names come out readable because the game keeps its display text in `.trs`
files inside `data.ubn`, in a format as simple as the save's own, and this
reads those too. Without the archives it still works and shows the raw keys.

Nothing here writes. Editing a save is a different job and wants the format
understood field by field first.
"""
import argparse
import glob
import os
import re
import struct
import sys
import zipfile

import trs

# The text resources hold characters the Windows console cannot encode, and a
# tool that dies on a name it cannot print is no use. Replace them instead.
try:
    sys.stdout.reconfigure(errors='replace')
except Exception:
    pass

GAME = os.environ.get('SOA_GAME', r'F:\Games\SoA-Package\Game')

# Every file the game serialises starts with the same sixteen bytes bar the
# first, which says which class wrote it: 0x38 a save, 0x40 a text resource,
# 0x41 a layout.
MAGIC_TAIL = bytes.fromhex('F9B30A6293D1119A2B080000300512')


def pstr(raw, i):
    """A string as the game writes it: one length byte, then the characters.

    A length of 0xFF means a two-byte length follows instead, which is how the
    long descriptions in the text resources fit. See tools/trs.py, where the
    same rule was worked out.
    """
    n = raw[i]
    i += 1
    if n == 0xFF:
        n = struct.unpack_from('<H', raw, i)[0]
        i += 2
    return raw[i:i + n].decode('latin1'), i + n


def u32(raw, i):
    return struct.unpack_from('<I', raw, i)[0], i + 4


# ------------------------------------------------------------------ the text

def load_text(game=GAME):
    """Every key the game can show, from every archive, patches last."""
    out = {}
    order = ['data.ubn', 'gui.ubn', 'missions.ubn']
    for path in sorted(glob.glob(os.path.join(game, '*.ubn'))):
        name = os.path.basename(path)
        if name not in order:
            order.append(name)
    for name in order:
        path = os.path.join(game, name)
        if not os.path.exists(path):
            continue
        try:
            z = zipfile.ZipFile(path)
        except Exception:
            continue
        for member in z.namelist():
            low = member.lower()
            if not low.endswith('.trs'):
                continue
            # The description resources hold biographies and equipment blurbs
            # under the same keys as the names, and they would win by being
            # read later. We want the name.
            if 'description' in low or 'desciption' in low:
                continue
            try:
                out.update(dict(trs.parse(z.read(member))))
            except Exception:
                pass
    return out


# ------------------------------------------------------------------ the save

VOWELS = set('aeiouyAEIOUY')


def looks_like_a_name(s):
    """Tell a real name from four bytes of terrain that happen to be printable.

    The middle of a mission save is the landscape, and in three megabytes of it
    a byte will regularly be followed by its own count of printable characters
    purely by chance. Those look like `Kgb!a` and `2"z>`; the real names look
    like `Natasha Romanova` and `TRES_OBJECTS_UNIT_BTR_80`. Letters and a vowel
    are enough to separate them.
    """
    if len(s) < 3:
        return False
    letters = sum(c.isalpha() or c in " _-.'" for c in s)
    if letters < len(s) * 0.85:
        return False
    return any(c in VOWELS for c in s)


class Save(object):
    def __init__(self, path):
        self.path = path
        self.raw = open(path, 'rb').read()
        self.ok = len(self.raw) > 0x40 and self.raw[0] == 0x38 and self.raw[1:16] == MAGIC_TAIL
        self.version = struct.unpack_from('<I', self.raw, 0x10)[0] if self.ok else 0
        # 1 means the save was taken in the bunker, 0 out on a mission. The
        # sizes agree: a bunker save is a few kilobytes, a mission save carries
        # the whole landscape and runs to megabytes.
        self.at_base = self.ok and struct.unpack_from('<I', self.raw, 0x14)[0] == 1
        self.mission = None
        self.text_file = None
        self.parties = []
        if self.ok:
            self._read_head()

    def _read_head(self):
        raw = self.raw
        if self.at_base:
            # The bunker save names the mission it will start next.
            try:
                self.mission, _ = pstr(raw, 0x20)
            except IndexError:
                pass
            return
        # A mission save opens with the parties, in the order the mission
        # declares them, each followed by a number that has been 2 in every
        # save looked at so far. That number is what ends the list: the party
        # names themselves are whatever the mission author typed, `Blade???`
        # among them, so they cannot be told apart by their spelling.
        i = 0x30
        while i < len(raw):
            try:
                name, j = pstr(raw, i)
                n, j = u32(raw, j)
            except (IndexError, struct.error):
                break
            if not name or n != 2:
                break
            self.parties.append(name)
            i = j
        # One field of a shape not yet worked out sits between the parties and
        # the two paths that follow - the mission's text file and the mission
        # itself. Rather than guess at it, walk strings forward until the two
        # paths turn up; they are within a few dozen bytes.
        while i < min(len(raw), 0x400):
            try:
                s, j = pstr(raw, i)
            except IndexError:
                break
            if s.lower().endswith('.trs'):
                self.text_file = s
                try:
                    self.mission, _ = pstr(raw, j)
                except IndexError:
                    pass
                return
            i = j if s else i + 1

    def strings(self, lo=3, hi=64):
        """Every length-prefixed string in the file, with its offset."""
        raw, out, i = self.raw, [], 0
        while i < len(raw) - 1:
            n = raw[i]
            if lo <= n <= hi:
                s = raw[i + 1:i + 1 + n]
                if len(s) == n and all(32 <= b < 127 for b in s):
                    out.append((i, s.decode('latin1')))
                    i += 1 + n
                    continue
            i += 1
        return out


# ---------------------------------------------------------------- the report

def as_name(s, width=44):
    """A name, or nothing.

    The same key often carries both a name and a biography, in different text
    resources, and which of the two we get depends on the order the archives
    are read. A biography runs to several lines and starts `Born: 1980`, so it
    is easy to refuse; and refusing is right, because the key itself
    (TRES_BORIS_KERKOWITSCH) already reads as a name.
    """
    if not s or chr(10) in s or chr(13) in s or len(s) > width:
        return None
    return s.strip() or None


def name_of(key, text):
    """A display name for a TRES key, if the archives gave us one."""
    if key in text:
        return as_name(text[key])
    for prefix in ('TRES_OBJECTS_', 'TRES_EQUIPMENT_'):
        if key.startswith(prefix):
            tail = key[len(prefix):]
            for other in text:
                if other.endswith(tail):
                    return as_name(text[other])
    return None


def size_of(n):
    return '%.1f MB' % (n / 1048576.0) if n > 1048576 else '%.0f kB' % (n / 1024.0)


def unique(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def report(save, text, roster=False):
    print(os.path.basename(save.path))
    print('   %-14s %s' % ('file', size_of(len(save.raw))))
    if not save.ok:
        print('   this does not look like a save')
        return
    print('   %-14s %d' % ('version', save.version))
    print('   %-14s %s' % ('taken', 'in the bunker' if save.at_base else 'on a mission'))
    if save.mission:
        print('   %-14s %s' % ('mission', save.mission))
    if save.text_file:
        print('   %-14s %s' % ('its text', save.text_file))
    if save.parties:
        print('   %-14s %s' % ('parties', ', '.join(save.parties)))
        print('   %-14s %s' % ('', 'the first of them is yours'))

    people, things, other = [], {}, []
    for _off, s in save.strings():
        if not looks_like_a_name(s):
            continue
        if s.startswith('TRES_'):
            things[s] = things.get(s, 0) + 1
        elif s in ('unknown name', 'empty', 'leer', 'Name'):
            continue
        elif s in save.parties or s.endswith('.mis') or s.endswith('.trs'):
            continue
        elif re.match(r'^[A-Z][a-z]+ [A-Z][a-z]', s):
            people.append(s)
        else:
            other.append(s)

    if things:
        print('\n   objects named in the save')
        for key in sorted(things, key=lambda k: (-things[k], k)):
            print('      %3d x  %-32s %s' % (things[key], key, name_of(key, text) or ''))
    if people:
        seen = unique(people)
        print('\n   %d people by name' % len(seen))
        for p in seen:
            print('      %s' % p)
    if roster and other:
        seen = unique(other)
        print('\n   %d other names' % len(seen))
        for p in seen:
            print('      %s' % p)


def saves_in(game):
    out = []
    for dirpath, _dirs, files in os.walk(os.path.join(game, 'SaveGames')):
        for f in files:
            if f.lower().endswith('.sav'):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save', nargs='?', help='a save, by name or by path')
    ap.add_argument('--game', default=GAME, help='the game folder')
    ap.add_argument('--roster', action='store_true', help='also the names that are not people')
    ap.add_argument('--strings', action='store_true', help='every string, unfiltered')
    args = ap.parse_args()

    found = saves_in(args.game)
    if not args.save:
        if not found:
            raise SystemExit('no saves under %s' % os.path.join(args.game, 'SaveGames'))
        print('%d saves under %s\n' % (len(found), os.path.join(args.game, 'SaveGames')))
        for p in found:
            size = os.path.getsize(p)
            print('   %-28s %8s   %s'
                  % (os.path.splitext(os.path.basename(p))[0], size_of(size),
                     'bunker' if size < 100000 else 'mission'))
        print('\ngive one of these names to see inside it')
        return

    path = args.save
    if not os.path.exists(path):
        want = os.path.splitext(os.path.basename(args.save))[0].lower()
        hit = [p for p in found
               if os.path.splitext(os.path.basename(p))[0].lower() == want]
        if not hit:
            hit = [p for p in found if want in os.path.basename(p).lower()]
        if not hit:
            raise SystemExit('no save called %s' % args.save)
        path = hit[0]

    save = Save(path)
    if args.strings:
        for off, s in save.strings():
            print('%08X  %s' % (off, s))
        return
    report(save, load_text(args.game), args.roster)


if __name__ == '__main__':
    main()
