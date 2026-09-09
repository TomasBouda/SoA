"""Find an item in a save and change it for another.

What is known, and what is not
------------------------------
**Known:** equipment is written into a save as the same numbers the catalog
uses, in plain little-endian dwords, and **a character's own equipment sits
inside the record that begins with his `TRES_` key** - `TRES_PROF_DR_SERGEJ_-
PETROW` and so on. That is the field the game reads when it puts a rifle in a
soldier's hands, and it was established the hard way: a save with a different
weapon written outside that record loaded and changed nothing.

**Why it matters.** A bunker save holds the same item numbers in more than one
place. Swapping a weapon at the depot moves it between the character and the
store, so *both* ends change and a diff shows two candidate offsets that look
equally good. Only the one inside the character's record is what he carries.

**Not known:** where inside the record the equipment begins. The record is not
a fixed size and no offset works for every character, so nothing here walks to
it; it is searched for instead.

    python edit_save.py M4_B --who Petrow          his record, and the items in it
    python edit_save.py M4_B --find Dragunov       every copy, and whose it is
    python edit_save.py M4_B --set 0x232E M60      change the one that is his

`--set` writes a copy and leaves the original alone unless `--in-place` is
given, and even then it keeps a .bak. A save is hours of somebody's evening.
"""
import argparse
import io
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import read_save as R

CATALOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'launcher', 'catalog.txt')


def catalog():
    """{number: name} and {lowered name: number} for the equipment."""
    by_number, by_name = {}, {}
    try:
        for line in io.open(CATALOG, encoding='utf-8'):
            c = line.rstrip('\n').split('\t')
            if len(c) > 4 and c[0] == 'equipment':
                by_number[int(c[1])] = c[3]
                by_name[c[3].lower()] = int(c[1])
                by_name[c[2].lower()] = int(c[1])
    except Exception:
        pass
    return by_number, by_name


def as_number(what, by_name):
    if what.lower() in by_name:
        return by_name[what.lower()]
    try:
        return int(what, 0)
    except ValueError:
        raise SystemExit('no item called %s, and it is not a number either' % what)


def marks(save):
    return [(o, t) for o, t in save.strings() if R.looks_like_a_name(t)]


def owner_of(landmarks, offset):
    found = None
    for at, name in landmarks:
        if at > offset:
            break
        found = (at, name)
    return found


def people(save):
    """The characters, as (start, end, key) - the record each one owns.

    A character's record opens with his `TRES_` key and runs to the next one.
    That boundary is what separates his own equipment from every other copy of
    the same item numbers in the file, and it is the only structure in a save
    that has been shown to matter: written inside the record the change takes,
    written outside it the game ignores it.

    `TRES_OBJECTS_UNIT_` keys are vehicles and weapons, not people, so they are
    not boundaries.
    """
    keys = [(o, t) for o, t in save.strings()
            if t.startswith('TRES_') and not t.startswith('TRES_OBJECTS_')]
    out = []
    for i, (at, key) in enumerate(keys):
        end = keys[i + 1][0] if i + 1 < len(keys) else len(save.raw)
        out.append((at, end, key))
    return out


def person_at(records, offset):
    for start, end, key in records:
        if start <= offset < end:
            return key
    return None


def pretty(key):
    """`TRES_NAME_HELENA_MARKOVA` as something a person would write."""
    name = key[len('TRES_'):]
    if name.startswith('NAME_'):
        name = name[len('NAME_'):]
    return ' '.join(w.capitalize() for w in name.split('_'))


# What a character carries, and how it is written.
#
# Each item is one entry inside the character's record: three dwords - the slot
# it occupies, the number the catalog uses, and an identifier - followed by a
# zero byte and the serialiser's `FF FF FF FF 01`. Reading it backwards from
# that marker is what makes it findable, since nothing about the record says
# where its equipment begins.
#
# The slots came out of the data rather than out of a guess: every entry in
# twenty saves falls into four values, and each holds exactly one kind of thing.
MARKER = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0x01])
SLOTS = {1: 'gear', 2: 'weapon', 4: 'ammunition', 8: 'armour'}


def inventory(save, start, end, by_number):
    """[(offset of the item number, slot, item, id)] for one character.

    An entry is accepted only when its slot is one of the four and its number
    is in the catalog. Both are needed: the marker is a general serialisation
    prefix and occurs on plenty of things that are not equipment.
    """
    raw = save.raw
    found = []
    at = raw.find(MARKER, start, end)
    while at >= 0:
        if at >= 13 and raw[at - 1] == 0:
            slot, item, ident = struct.unpack_from('<3I', raw, at - 13)
            if slot in SLOTS and item in by_number:
                found.append((at - 9, slot, item, ident))
        at = raw.find(MARKER, at + 1, end)
    return found


def who(save, wanted, by_number):
    """One character's record and everything in it."""
    records = [r for r in people(save) if wanted.lower() in r[2].lower()
               or wanted.lower() in pretty(r[2]).lower()]
    if not records:
        print('No character whose key mentions %s. The save has:' % wanted)
        for _, _, key in people(save):
            print('   %s   (%s)' % (pretty(key), key))
        return []
    found = []
    for start, end, key in records:
        print('%s   %s   0x%X to 0x%X' % (pretty(key), key, start, end))
        items = inventory(save, start, end, by_number)
        for off, slot, item, ident in items:
            print('   0x%-8X %-11s %3d = %-24s #%d'
                  % (off, SLOTS[slot], item, by_number[item], ident))
        if not items:
            print('   carries nothing this reader recognises')
        found.extend(items)
    return found


def find(save, number, by_number, context=4):
    """Every dword equal to `number`, with what is around it.

    Two things separate a live slot from a chance match: whose record it falls
    in, and what surrounds it. A copy outside every character's record is the
    depot or a vehicle - swapping a weapon at the depot changes both ends, so
    those copies look just as convincing as the real one and are not it.
    """
    raw = save.raw
    landmarks = marks(save)
    records = people(save)
    want = struct.pack('<I', number)
    hits = []
    start = 0
    while True:
        i = raw.find(want, start)
        if i < 0:
            break
        start = i + 1
        hits.append(i)

    print('%s: %d places hold %d (%s)\n'
          % (os.path.basename(save.path), len(hits), number,
             by_number.get(number, 'not in the catalog')))
    for at in hits:
        who = owner_of(landmarks, at)
        where = ('%s +0x%X' % (who[1], at - who[0])) if who else 'before any name'
        around = []
        plausible = 0
        for k in range(-context, context + 1):
            off = at + k * 4
            if off < 0 or off + 4 > len(raw):
                continue
            v = struct.unpack_from('<I', raw, off)[0]
            name = by_number.get(v)
            if 0 < v < 200:
                plausible += 1
            piece = str(v) if name is None else '%d=%s' % (v, name)
            around.append(('[%s]' if off == at else '%s') % piece)
        print('0x%-8X %-34s %s' % (at, where, ' '.join(around)))
        owner = person_at(records, at)
        print('%-11s %-34s %s' % ('', '',
              ('carried by %s' % pretty(owner)) if owner
              else 'in no character record - the depot or a vehicle'))
        print('%-11s %-34s %d of the %d around it look like items'
              % ('', '', plausible, context * 2 + 1))
    if not hits:
        print('Nothing holds that number. Is the item the one you think it is?')
    return hits


def put(save, offset, number, into, in_place, by_number):
    raw = bytearray(save.raw)
    if offset + 4 > len(raw):
        raise SystemExit('0x%X is past the end of the file' % offset)
    was = struct.unpack_from('<I', raw, offset)[0]
    struct.pack_into('<I', raw, offset, number)
    target = save.path if in_place else (into or save.path + '.edited')
    if os.path.exists(target):
        backup = target + '.bak'
        if not os.path.exists(backup):
            shutil.copyfile(target, backup)
            print('kept the old one as %s' % os.path.basename(backup))
    with open(target, 'wb') as f:
        f.write(raw)
    print('0x%X: %d (%s) -> %d (%s)'
          % (offset, was, by_number.get(was, '?'), number, by_number.get(number, '?')))
    print('written to %s' % target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--game', default=R.GAME)
    ap.add_argument('--who', metavar='NAME',
                    help='one character: his record, and the equipment in it')
    ap.add_argument('--find', metavar='ITEM', help='an item name or a number')
    ap.add_argument('--set', nargs=2, metavar=('OFFSET', 'ITEM'))
    ap.add_argument('--out', help='where to write, with --set')
    ap.add_argument('--in-place', action='store_true',
                    help='change the save itself; it is copied to .bak first')
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

    path = args.save
    if not os.path.exists(path):
        want = os.path.splitext(os.path.basename(path))[0].lower()
        hit = [p for p in R.saves_in(args.game)
               if os.path.splitext(os.path.basename(p))[0].lower() == want]
        if not hit:
            raise SystemExit('no save called %s' % args.save)
        path = hit[0]

    by_number, by_name = catalog()
    save = R.Save(path)
    if args.who:
        who(save, args.who, by_number)
    elif args.find:
        find(save, as_number(args.find, by_name), by_number)
    elif args.set:
        put(save, int(args.set[0], 0), as_number(args.set[1], by_name),
            args.out, args.in_place, by_number)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
