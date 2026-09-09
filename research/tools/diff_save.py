"""Compare two saves and say what changed, and whose it is.

Finding a field in a save by reading it is slow and mostly wrong. Making the
game change one thing and looking at what moved is fast and right, and a save
is far kinder to this than memory is: nothing drifts on its own, no timers, no
animation, so every difference between two saves is something that actually
happened.

    python diff_save.py before.sav after.sav
    python diff_save.py before.sav after.sav --context 24

The trick that makes the output readable is naming the owner. A save is a run
of records, most of them carrying a name - a character's, or `unknown name` for
the things nobody named - so every difference is reported against the nearest
name before it. `+0x42 of Boris Kerkowitsch` is a fact worth having; offset
0x5ED on its own is not.

How to use it for the inventory
-------------------------------
Save in the bunker. Swap one soldier's weapon for another and nothing else.
Save again under a different name. Then compare the two: the bytes that moved
are the inventory, and the numbers written there are the item numbers the
catalog lists. A bunker save is a few kilobytes and holds the whole squad,
which makes it the place to do this rather than a mission save of three
megabytes.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import read_save as R


def owners(save):
    """[(offset, name)] for every name-like string, in order.

    These are the landmarks. A difference is reported against the last one
    before it, which is nearly always the record it belongs to.
    """
    return [(o, t) for o, t in save.strings() if R.looks_like_a_name(t)]


def owner_of(marks, offset):
    found = None
    for at, name in marks:
        if at > offset:
            break
        found = (at, name)
    return found


def runs(a, b):
    """Stretches where the two differ, as (start, length)."""
    out = []
    n = min(len(a), len(b))
    i = 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        # A couple of equal bytes inside a changed field would otherwise split
        # it into pieces that read as separate findings.
        gap = 0
        while i < n and (a[i] != b[i] or gap < 3):
            gap = 0 if a[i] != b[i] else gap + 1
            i += 1
        out.append((start, i - gap - start))
    return out


def window(a, b):
    """(common prefix, common suffix) - where the change is actually cornered.

    Comparing byte by byte from the start is useless the moment a save grows or
    shrinks: everything after the first insertion reads as different even when
    it is the same data one step over. Measuring how far the two agree from
    each end corners the change between the two, and how wide that window is
    says whether this pair is worth reading at all.
    """
    n = min(len(a), len(b))
    pre = 0
    while pre < n and a[pre] == b[pre]:
        pre += 1
    suf = 0
    while suf < n - pre and a[len(a) - 1 - suf] == b[len(b) - 1 - suf]:
        suf += 1
    return pre, suf


def show(before, after, context):
    a, b = before.raw, after.raw
    print('%s  %d bytes' % (os.path.basename(before.path), len(a)))
    print('%s  %d bytes' % (os.path.basename(after.path), len(b)))

    pre, suf = window(a, b)
    span = max(len(a), len(b)) - pre - suf
    print('\nthey agree for the first %d bytes and the last %d,' % (pre, suf))
    print('so everything that changed is inside %d bytes from 0x%X' % (span, pre))
    if span > 4096 and not before.at_base:
        print("""
That window is too wide to read, and these are mission saves. A mission save
holds the whole world, and moving one thing rearranges a great deal of derived
state with it - object order, identifiers, whatever was counted. Two of them
are not a controlled pair however carefully they were made.

Do it in the bunker instead: save, swap the one weapon, save again. A bunker
save is a few kilobytes, holds the whole squad, and carries almost nothing that
changes on its own.
""")
    elif span > 4096:
        print("""
That is a wide window for a bunker pair. Something besides the one change
moved - time passing, money, a production finishing - so read the differences
below for the one that names a soldier and holds numbers the catalog knows,
and treat the rest as weather.
""")
    if len(a) != len(b):
        print('They are also not the same length, so something was added or')
        print('removed. Past the first difference the offsets below are only')
        print('true of the first file.')
    marks = owners(before)
    found = runs(a, b)
    print('\n%d stretches differ\n' % len(found))
    for start, length in found:
        who = owner_of(marks, start)
        where = ('%s +0x%X' % (who[1], start - who[0])) if who else 'before any name'
        print('%06X  %2d bytes   %s' % (start, length, where))
        lo = max(0, start - context)
        hi = min(len(a), start + length + context)
        for label, raw in (('was', a), ('now', b)):
            line = []
            for i in range(lo, hi):
                mark = '[' if i == start else (']' if i == start + length else '')
                line.append(mark + '%02X' % raw[i])
            print('     %s %s' % (label, ' '.join(line)))
        if length in (1, 2, 4):
            fmt = {1: 'B', 2: '<H', 4: '<I'}[length]
            import struct
            was = struct.unpack_from(fmt, a, start)[0]
            now = struct.unpack_from(fmt, b, start)[0]
            print('     as a number: %d -> %d' % (was, now))
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('before')
    ap.add_argument('after')
    ap.add_argument('--context', type=int, default=12,
                    help='bytes to show on either side (default 12)')
    ap.add_argument('--game', default=R.GAME)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

    def find(name):
        if os.path.exists(name):
            return name
        for p in R.saves_in(args.game):
            if os.path.splitext(os.path.basename(p))[0].lower() == name.lower():
                return p
        raise SystemExit('no save called %s' % name)

    show(R.Save(find(args.before)), R.Save(find(args.after)), args.context)


if __name__ == '__main__':
    main()
