"""Parser for data/GameData/Data.set - the library of gear, weapons and ammo.

The format is described in detail in ../dataset-format.md.

Format:
    header    4 dwords: 7, record count (133), 1, 1
    record    strings up to the one starting with SET_, followed by a block
              of numbers (ammunition has 18 fields, small arms 23; the length
              is found by trying)

    string = 1 B length + bytes (latin1); an empty string has length 0
    the four strings are: German name, text id, hint id, SET identifier

Vehicles kept as equipment have no text id and carry the name directly
instead - which is why the name list must not be built by looking for the
"nearest id", see gen_ids_doc.py.

The meaning of the fields is not certain; a few can be told apart by how they
behave across groups. The rest is printed as p07, p08 and so on, so that at
least the differences are visible.

Usage:
    python dataset.py                      overview of every item
    python dataset.py --fields             which fields differ between groups
    python dataset.py --filter HELI        only items whose id contains HELI
    python dataset.py --raw SET_HELI_TOW   raw dump of a single record
"""
import argparse
import os
import re
import struct
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
UBN = os.path.join(ROOT, '_patched', 'data.ubn')
MEMBER = 'data/GameData/Data.set'

# Field 0 is certain: it is the trade value. The trader code multiplies exactly
# this member (settings +0x4C) - see ../trading.md. The rest is named after what
# held for every item where it can be checked against the in-game descriptions,
# hence the question marks.
FIELDS = {0: 'value', 1: 'size?', 2: 'range?', 3: 'kind?'}


def _try_record(d, p, setid_end):
    """Read two ints and four strings from p; must end exactly on the SET id."""
    if p + 8 > len(d):
        return None
    kind, ident = struct.unpack_from('<2i', d, p)
    q = p + 8
    strings = []
    for _ in range(4):
        if q >= len(d):
            return None
        n = d[q]
        q += 1
        if q + n > len(d):
            return None
        s = d[q:q + n]
        # The German names carry umlauts, so high bytes are fine; only control
        # characters are a problem. This is where the parser used to stop, on
        # the item "Armbrustkoecher".
        if n and not all(c >= 32 for c in s):
            return None
        strings.append(s.decode('latin1'))
        q += n
    if q != setid_end or not strings[3].startswith('SET_'):
        return None
    return kind, ident, strings, q


def load(path=UBN):
    """Parse the whole library.

    The length of the number block depends on the item type and is written
    nowhere, so it cannot be looked up in advance. There is a way around it:
    the SET_ identifiers can be found in the file directly and every record
    ends with one. So for each of them we try which start position lets us read
    "two ints and four strings" ending exactly on it. That bounds the record
    from both sides and the number block is whatever lies between the end of
    one record and the start of the next.

    The first int is the type (0 to 3, see the factory at 0x5BEA20), the second
    is the item NUMBER - and that is what the equipment cheat takes as its
    argument, not the position in the file. The highest one is 252, which
    matches the message the game itself prints, "max used object settings
    id: 252".
    """
    d = zipfile.ZipFile(path).read(MEMBER)
    version, count = struct.unpack_from('<2I', d, 0)

    setids = [(m.start(), m.end()) for m in re.finditer(rb'SET_[A-Z0-9_]+', d)]
    records = []
    previous_end = 8
    for i, (setid_start, setid_end) in enumerate(setids):
        found = None
        for p in range(previous_end, setid_start):
            found = _try_record(d, p, setid_end)
            if found:
                break
        if not found:
            raise ValueError('cannot bound record %d' % i)
        kind, ident, strings, strings_end = found

        # The number block ends where the next record begins.
        nxt = len(d)
        if i + 1 < len(setids):
            for p in range(setid_end, setids[i + 1][0]):
                if _try_record(d, p, setids[i + 1][1]):
                    nxt = p
                    break
        fields = (nxt - strings_end) // 4

        records.append({
            'type': kind, 'number': ident,
            'name': strings[0], 'text': strings[1], 'hint': strings[2],
            'id': strings[3], 'fields': fields,
            'ints': struct.unpack_from('<%di' % fields, d, strings_end),
            'floats': struct.unpack_from('<%df' % fields, d, strings_end),
        })
        previous_end = setid_end

    if len(records) != count:
        raise ValueError('the header promises %d records, found %d'
                         % (count, len(records)))
    return records


def number(z, i):
    """A field is either an integer or a float - whichever makes sense."""
    c, f = z['ints'][i], z['floats'][i]
    if c and abs(c) > 0x30000000:
        return '%g' % f
    return str(c)


def overview(records, wanted=None):
    print('%-5s %-4s %-30s %-30s %s' % ('num', 'type', 'identifier', 'name', 'fields'))
    for z in records:
        if wanted and wanted.upper() not in z['id'].upper():
            continue
        print('%-5d %-4d %-30s %-30s %d' % (
            z['number'], z['type'], z['id'], z['name'][:30], z['fields']))


def field_report(records):
    """Show which fields tell the groups apart - a carrier link would hide there."""
    groups = {
        'helicopter systems': [z for z in records if z['id'].startswith('SET_HELI')],
        'tank guns': [z for z in records if '125MMGUN' in z['id'] or '73MMGUN' in z['id']],
        'small arms': [z for z in records if z['id'] in (
            'SET_M60', 'SET_AK74', 'SET_UZI', 'SET_MP5', 'SET_RPK', 'SET_DRAGUNOV')],
        'ammunition': [z for z in records if z['id'].startswith('SET_MUN_')],
    }
    print('%-6s %s' % ('field', '  '.join('%-26s' % n for n in groups)))
    most = max(z['fields'] for z in records)
    for i in range(most):
        row = []
        for name, group in groups.items():
            values = sorted({number(z, i) for z in group if i < z['fields']})
            row.append('%-26s' % (','.join(values[:3]) + ('...' if len(values) > 3 else '')))
        label = FIELDS.get(i, 'p%02d' % i)
        print('%-6s %s' % (label, '  '.join(row)))


def raw(records, ident):
    for z in records:
        if z['id'].upper() == ident.upper():
            print('identifier: %s' % z['id'])
            print('name:       %s' % z['name'])
            print('text:       %s' % (z['text'] or '(empty)'))
            print('hint:       %s' % (z['hint'] or '(empty)'))
            print('fields:     %d' % z['fields'])
            for i in range(z['fields']):
                print('  %-9s int %-12d float %g' % (
                    FIELDS.get(i, 'p%02d' % i), z['ints'][i], z['floats'][i]))
            return
    raise SystemExit('%s is not in the library' % ident)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--filter')
    ap.add_argument('--fields', action='store_true')
    ap.add_argument('--raw', metavar='SET_ID')
    args = ap.parse_args()

    records = load()
    if args.raw:
        raw(records, args.raw)
    elif args.fields:
        field_report(records)
    else:
        overview(records, args.filter)


if __name__ == '__main__':
    main()
