"""Prints the object identifiers together with their ordinal numbers.

The base cheats take the argument as an ordinal number, not as a name -
verified from tracefile.log, where CREATE_VEHICLE(0..22) succeeded and
CREATE_VEHICLE(UNIT_T55) failed. The indexes follow the order of the items
inside the object libraries.

Usage:
    python list_ids.py            everything
    python list_ids.py units      only units (cheat: vehicle <n>)
    python list_ids.py sets       only gear and ammunition (cheat: equipment <n>)
"""
import re
import sys
import zipfile

UBN = r'..\_patched\data.ubn'

LIBS = {
    'units': ('data/ObjData/Units.olb', 'UNIT_', 'vehicle <n>'),
    'sets': ('data/GameData/Data.set', 'SET_', 'equipment <n>'),
    'chars': ('data/ObjData/Characters.olb', 'CHAR_', '-'),
    'animals': ('data/ObjData/Animals.olb', 'ANIMAL_', '-'),
}


def ordered(z, member, prefix):
    """Order of first appearance, without the TRES_OBJECTS_* text resources."""
    d = z.read(member)
    out = []
    for m in re.finditer(prefix.encode() + rb'[A-Z0-9_]+', d):
        if d[max(0, m.start() - 13):m.start()] == b'TRES_OBJECTS_':
            continue
        s = m.group().decode()
        if s not in out:
            out.append(s)
    return out


def main():
    want = sys.argv[1].lower() if len(sys.argv) > 1 else None
    with zipfile.ZipFile(UBN) as z:
        for key, (member, prefix, cheat) in LIBS.items():
            if want and want != key:
                continue
            try:
                items = ordered(z, member, prefix)
            except KeyError:
                print('=== %s: %s not found ===' % (key, member))
                continue
            print('=== %s (%d items, cheat: %s) ===' % (key, len(items), cheat))
            for i, s in enumerate(items):
                print('  %3d  %s' % (i, s))
            print()


if __name__ == '__main__':
    main()
