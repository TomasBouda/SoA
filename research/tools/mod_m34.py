r"""A new weapon for the game: the M34 white phosphorus grenade.

What the game needs to know about a thrown weapon it reads from four files,
and every one of them can be replaced by a loose file beside the game (the
precedence of loose files over the archives, architecture.md). The exe is
the other half: it names its five thrown weapons by number in a dozen
switches and tables, and m34_patch.py adds the sixth to each - the records
here are nothing without those bytes, and the bytes are dangerous without
these records (the trader would make an item with no settings). The build
puts both in together.

    Data\GameData\Data.set                         two records more: the weapon and its round
    Data\GUIData\TextResource_eng\TRES_EQUIPMENT.trs  four texts: name and hint of each
    Data\GUIData\Items.gui                         one icon record, RES_M34
    GUI\GUI_Shared\Items\items_4.png               the sheet, with the icon drawn in (m34_icon.py)

The records are copies of the Molotov's - the one thrown weapon that burns -
with the numbers changed: weapon 150, round 151 (both free below the
"max used object settings id" of 252 the game logs) and the damage, the
radius and the stack of three the M34's own. It flies like the hand
grenade (an arc, a bounce, a fuze of a few seconds - that is the exe's
choice of projectile) and bursts into the round's fire effect. Each file is
the archive's original with the new records appended and its count bumped;
nothing else in them moves.

Usage:
    python mod_m34.py <game folder>       writes the four files under it
"""
import io
import os
import struct
import sys
import zipfile

import m34_icon
import m34_patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATA = os.path.join(ROOT, '_patched', 'data.ubn')

WEAPON, ROUND = m34_patch.NEW, m34_patch.ROUND      # 150 and 151
WEAPON_ID, ROUND_ID = 'SET_M34', 'SET_MUN_M34'
TEXTS = {
    'TRES_EQUIPMENT_M34': 'M34 WP Grenade',
    'TRES_EQUIPMENT_M34_HINT': 'M34, white phosphorus',
    'TRES_EQUIPMENT_AMMO_M34': 'M34 WP x 3',
    'TRES_EQUIPMENT_AMMO_M34_HINT': 'white phosphorus grenades, three to a pack',
}


def s(text):
    b = text.encode('latin1')
    return bytes([len(b)]) + b


def f(x):
    return struct.pack('<f', x)


def i(x):
    return struct.pack('<i', x)


# ---- Data.set ---------------------------------------------------------------

def round_record():
    """Type 1, the round: what weapons.md names the fields."""
    fields = [
        f(40.0),      # value
        f(3.0),       # weight
        i(120), i(180),   # vs soldiers, min and max per hit
        i(30), i(50),     # vs a vehicle's hit points
        i(20), i(40),     # vs armour - phosphorus does little to steel
        i(60),        # penetrates below: only what has next to no armour left
        f(5.0),       # blast radius - the Molotov's 2.5 doubled
        i(1),         # effect 1: fire, it burns where it lands
        i(1),         # f11, 1 like every other round
        f(3.0),       # weight again, as the game stores it
        i(3),         # stack: three to a pack
        i(0),         # flight 0: ballistic, an arc like the other grenades
        i(7),         # projectile speed, the grenades' 7
    ]
    return i(1) + i(ROUND) + s('M34 Phosphorgranate (Mun)') + s('TRES_EQUIPMENT_AMMO_M34') \
        + s('TRES_EQUIPMENT_AMMO_M34_HINT') + s(ROUND_ID) + b''.join(fields)


def weapon_record():
    """Type 2, the grenade as a weapon: the Molotov's record, field for field,
    with the round pointed at ours."""
    fields = [
        f(40.0), f(3.0),           # value, weight
        i(23), i(3),               # range, minimum range - a throw
        f(0.0), i(0), f(0.4),      # rate of fire (none), -, aim time
        i(0), i(0), i(0), i(0),    # four zeros
        f(3.0), i(1),              # weight again, 1
        i(0), f(0.0), f(5.0), f(30.0),   # f13-f16 as the Molotov has them - the last three are floats
        i(1), i(ROUND),            # one kind of ammunition: ours
        i(1000), i(1),             # projectile speed, salvo
    ]
    return i(2) + i(WEAPON) + s('M34 Phosphorgranate') + s('TRES_EQUIPMENT_M34') \
        + s('TRES_EQUIPMENT_M34_HINT') + s(WEAPON_ID) + b''.join(fields)


def data_set(original):
    version, count = struct.unpack_from('<II', original, 0)
    if WEAPON_ID.encode() in original:
        raise SystemExit('Data.set already holds ' + WEAPON_ID)
    return struct.pack('<II', version, count + 2) + original[8:] + round_record() + weapon_record()


# ---- TRES_EQUIPMENT.trs -------------------------------------------------------

def texts(original):
    version, count = struct.unpack_from('<II', original, 16)
    if b'TRES_EQUIPMENT_M34' in original:
        raise SystemExit('the texts already hold TRES_EQUIPMENT_M34')
    out = original[:16] + struct.pack('<II', version, count + len(TEXTS)) + original[24:]
    n = count
    for key, text in TEXTS.items():
        n += 1
        out += struct.pack('<I', n) + s(key) + s('leer') + s(text) + s('leer')
    return out


# ---- Items.gui ----------------------------------------------------------------

def gui(original):
    """One record more, RES_M34, on the sheet where m34_icon.py draws it. The
    records start after the sheet list: a count, then for each a zero, an
    ordinal, the name, a one, the rectangle, 0, 0, 1.0, 1.0 and the sheet's
    id (5000 + its number - 1)."""
    if b'RES_M34' in original:
        raise SystemExit('Items.gui already holds RES_M34')
    pos = 24
    for _ in range(2):                         # set id, resource root
        pos += 1 + original[pos]
    sheets = struct.unpack_from('<I', original, pos)[0]
    pos += 4
    for _ in range(sheets):
        pos += 4
        pos += 1 + original[pos]
        pos += 16
    count_at = pos
    count = struct.unpack_from('<I', original, count_at)[0]
    # the last ordinal in the file, to number ours after it
    last = 0
    p = count_at + 4
    while p < len(original):
        p += 4
        last = struct.unpack_from('<I', original, p)[0]
        p += 4
        p += 1 + original[p]
        p += 4 + 16 + 16 + 4
    # the exe's icon map is taught this ordinal by m34_patch.py; the two
    # must not drift apart
    if last + 1 != m34_patch.ORDINAL:
        raise SystemExit('Items.gui ends at %d, m34_patch.ORDINAL is %d' % (last, m34_patch.ORDINAL))
    l, t = m34_icon.AT
    r, b = l + m34_icon.SIZE[0], t + m34_icon.SIZE[1]
    record = (struct.pack('<II', 0, last + 1) + s('RES_M34') + struct.pack('<I', 1)
              + struct.pack('<4f', l, t, r, b) + struct.pack('<II', 0, 0) + struct.pack('<2f', 1.0, 1.0)
              + struct.pack('<I', 5000 + m34_icon.SHEET_NUMBER - 1))
    return original[:count_at] + struct.pack('<I', count + 1) + original[count_at + 4:] + record


def write(game, rel, data):
    path = os.path.join(game, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(data)
    print('wrote', path)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    game = sys.argv[1]
    z = zipfile.ZipFile(DATA)
    write(game, os.path.join('Data', 'GameData', 'Data.set'), data_set(z.read('data/GameData/Data.set')))
    write(game, os.path.join('Data', 'GUIData', 'TextResource_eng', 'TRES_EQUIPMENT.trs'),
          texts(z.read('data/GUIData/TextResource_eng/TRES_EQUIPMENT.trs')))
    write(game, os.path.join('Data', 'GUIData', 'Items.gui'), gui(z.read('data/GUIData/Items.gui')))
    buf = io.BytesIO()
    m34_icon.sheet_with_icon().save(buf, 'PNG')
    write(game, os.path.join('GUI', 'GUI_Shared', 'Items', 'items_%d.png' % m34_icon.SHEET_NUMBER), buf.getvalue())


if __name__ == '__main__':
    main()
