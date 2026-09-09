"""Generates object-ids.md and fills the vehicle and equipment lists into cheats.md.

The ordinal numbers are what the base cheats take as their argument - verified
from tracefile.log, where CREATE_VEHICLE(0..22) succeeded and
CREATE_VEHICLE(UNIT_T55) failed.

Every library uses its own prefix (UNIT_, SET_, ANIM_, ROCKET_, CHILD_,
UNBORN_...), so every one gets its own pattern - see LIBS. A generic pattern
does not work here: next to the identifiers Units.olb also holds sound and
effect names (T55_S, MD500_E) that would blow the list up from 23 to 43 and
throw the ordinal numbers off.
"""
import os
import re
import zipfile

import trs

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
UBN = os.path.join(ROOT, '_patched', 'data.ubn')
OUT = os.path.join(ROOT, '_research', 'object-ids.md')
CHEATS = os.path.join(ROOT, '_research', 'cheats.md')

# path fragments and other false hits
NOISE = {'GUI_E', 'GUI_EDITOR', 'DATA_ANIDATA'}

# Every library has its own pattern. A generic one does not work here: next to
# the identifiers Units.olb also holds sound and effect names (T55_S, MD500_E,
# BMP_L) that would blow the list up and throw the ordinal numbers off.
LIBS = [
    ('Units and vehicles', 'data/ObjData/Units.olb', '`vehicle <n>`', r'UNIT_[A-Z0-9_]+'),
    ('Equipment, weapons and ammunition', 'data/GameData/Data.set', '`equipment <n>`',
     r'SET_[A-Z0-9_]+'),
    ('Characters', 'data/ObjData/Characters.olb', '—',
     r'(?:CM|CW|UNBORN|NITRO|CHILD|MONK)_[A-Z0-9_]+'),
    ('Animals', 'data/ObjData/Animals.olb', '—', r'ANIM_[A-Z0-9_]+'),
    ('Rockets and bombs', 'data/ObjData/Rockets.olb', '—', r'(?:ROCKET|BOMB)_[A-Z0-9_]+'),
]


def texts(z, name):
    """Load the English texts of a .trs into a {TRES id: text} dictionary."""
    member = 'data/GUIData/TextResource_eng/%s.trs' % name
    try:
        return {i: t.strip() for i, t in trs.parse(z.read(member))}
    except Exception:
        return {}


def names(z, member, prefix, tres_prefix, tres_file, forward):
    """Pair identifiers with the names the game shows to the player.

    Next to an identifier the libraries hold either a reference into a text
    table or the finished name itself. For units the reference sits right after
    the identifier (UNIT_FLOGGER, then TRES_OBJECTS_UNIT_MIG_FLOGGER); in
    Data.set it sits before it instead, in the order German name, TRES id, TRES
    id with the _HINT suffix and only then the SET id.

    Vehicles kept as equipment have no TRES id at all - the record simply says
    "FLOGGER" and "FLOGGER". The search for the nearest reference therefore has
    to stay inside a single record, otherwise an item inherits the name of the
    previous one: on the first attempt SET_FLOGGER, SET_HIND and SET_M1A1 all
    came out as "M79". The record boundary is given by the neighbouring
    identifier.
    """
    d = z.read(member)
    table = texts(z, tres_file)

    strings = [(m.start(), m.group().decode('latin1'))
               for m in re.finditer(rb'[ -~]{3,}', d)]
    keys = [(m.start(), m.end(), m.group().decode())
            for m in re.finditer((prefix + r'[A-Z0-9_]+').encode(), d)]

    def readable(t):
        return (len(re.sub(r'[^A-Za-z]', '', t)) >= 2
                and '\\' not in t and '/' not in t and '.' not in t
                and not t.startswith(prefix) and not t.startswith('TRES'))

    out = {}
    for i, (start, end, key) in enumerate(keys):
        if key in out:
            continue
        if forward:
            edge = keys[i + 1][0] if i + 1 < len(keys) else len(d)
            window = [(o, t) for o, t in strings if end <= o < edge]
        else:
            edge = keys[i - 1][1] if i else 0
            window = [(o, t) for o, t in strings if edge <= o < start]

        ref = next((t for _, t in window
                    if t.startswith(tres_prefix) and not t.endswith('_HINT')), None)
        if ref and table.get(ref):
            out[key] = table[ref]
            continue
        # with no reference into the table we take the last readable string
        # of the record
        plain = [t for _, t in window if readable(t)]
        if plain:
            out[key] = plain[-1]
    return out


def ids(z, member, pattern=r'[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+'):
    d = z.read(member)
    out = []
    for m in re.finditer(pattern.encode(), d):
        s = m.group().decode()
        if s.startswith('TRES') or s in NOISE:
            continue
        if d[max(0, m.start() - 13):m.start()] == b'TRES_OBJECTS_':
            continue
        if s not in out:
            out.append(s)
    return out


def two_col(items):
    L = ['| # | identifier | # | identifier |', '|---|---|---|---|']
    half = (len(items) + 1) // 2
    for i in range(half):
        left = '%d | `%s`' % (i, items[i])
        right = ('%d | `%s`' % (i + half, items[i + half])) if i + half < len(items) else ' | '
        L.append('| %s | %s |' % (left, right))
    return L


def equipment_groups(sets):
    """Split the equipment into groups while keeping the original indexes."""
    mun, vehsys, rest = [], [], []
    for i, s in enumerate(sets):
        body = s[len('SET_'):]
        if body.startswith('MUN_'):
            mun.append((i, s))
        elif body.startswith('HELI_') or '_' in body:
            vehsys.append((i, s))
        else:
            rest.append((i, s))
    return mun, vehsys, rest


def grouped_table(pairs, item_names):
    L = ['| # | identifier | name in game |', '|---|---|---|']
    for i, key in pairs:
        L.append('| %d | `%s` | %s |' % (i, key, item_names.get(key, '—')))
    return L


def main():
    z = zipfile.ZipFile(UBN)

    # --- object-ids.md ---
    L = ['# Object identifiers', '']
    L += ['The ordinal numbers are what the base cheats take as their argument — verified',
          'from `tracefile.log`, where `CREATE_VEHICLE(0..22)` succeeded and',
          '`CREATE_VEHICLE(UNIT_T55)` failed. The order follows the order of the items',
          'inside the object libraries.', '']
    L += ['Generated by `tools/gen_ids_doc.py`. The cheats themselves are described in '
          '[cheats.md](cheats.md).', '']

    for title, member, cheat, pattern in LIBS:
        try:
            items = ids(z, member, pattern)
        except KeyError:
            continue
        L += ['---', '', '## %s' % title, '']
        L += ['Source: `%s` · cheat: %s · items: **%d**' % (member, cheat, len(items)), '']
        L += two_col(items) + ['']

    L += ['---', '', '## Other libraries', '']
    L += ['Too large to list:', '', '| library | items |', '|---|---|']
    for member in ('data/ObjData/Buildings.olb', 'data/ObjData/Buildings2.olb',
                   'data/ObjData/Vegetation.olb', 'data/ObjData/Additionals.olb'):
        try:
            L.append('| `%s` | %d |' % (member.split('/')[-1], len(ids(z, member))))
        except KeyError:
            pass
    L += ['']
    open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    print('written: %s' % OUT)

    # --- filling the lists into cheats.md ---
    unit_names = names(z, 'data/ObjData/Units.olb', 'UNIT_',
                       'TRES_OBJECTS_', 'TRES_OBJECTS', forward=True)
    set_names = names(z, 'data/GameData/Data.set', 'SET_',
                      'TRES_EQUIPMENT_', 'TRES_EQUIPMENT', forward=False)

    # A vehicle kept as equipment carries only a bare name in Data.set ("HIND"),
    # while the unit library knows the one the player sees for the same machine
    # ("Mi-24 HIND"). When the identifiers match, it is the same object.
    sets = ids(z, 'data/GameData/Data.set', r'SET_[A-Z0-9_]+')
    for key, name in unit_names.items():
        counterpart = 'SET_' + key[len('UNIT_'):]
        if counterpart in sets:
            set_names[counterpart] = name

    units = ids(z, 'data/ObjData/Units.olb', r'UNIT_[A-Z0-9_]+')
    V = ['### `vehicle(0-%d)`' % (len(units) - 1), '']
    V += ['Order taken from `data/ObjData/Units.olb`. The names are the ones the game '
          'shows to the player — next to the identifier the library also holds a '
          'reference into a text table.', '']
    V += grouped_table(list(enumerate(units)), unit_names) + ['']

    mun, vehsys, rest = equipment_groups(sets)
    E = ['### `equipment(0-%d)`' % (len(sets) - 1), '']
    E += ['Order taken from `data/GameData/Data.set`, %d items in total.' % len(sets), '']
    E += ['**Careful: the `equipment` cheat does not take this position.** It takes the item '
          'number stored inside the record, and the two differ - `SET_M60` is thirty-ninth '
          'here but has number 2. The numbers that actually work are in the launcher catalog '
          '(`tools/gen_catalog.py`, see [dataset-format.md](dataset-format.md)); the order '
          'below is only good for orientation.', '']
    E += ['**Small arms, gear and whole vehicles** (%d):' % len(rest), '']
    E += grouped_table(rest, set_names) + ['']
    E += ['**Weapon systems of vehicles and helicopters** (%d):' % len(vehsys), '']
    E += grouped_table(vehsys, set_names) + ['']
    E += ['**Ammunition** (%d):' % len(mun), '']
    E += grouped_table(mun, set_names) + ['']

    s = open(CHEATS, encoding='utf-8').read()
    i = s.index('### `vehicle')
    j = s.index('### `mission`')
    open(CHEATS, 'w', encoding='utf-8', newline='\n').write(
        s[:i] + '\n'.join(V) + '\n'.join(E) + s[j:])
    print('filled into cheats.md: %d vehicles (%d with a name), %d items (%d with a name)'
          % (len(units), sum(1 for u in units if u in unit_names),
             len(sets), sum(1 for x in sets if x in set_names)))


if __name__ == '__main__':
    main()
