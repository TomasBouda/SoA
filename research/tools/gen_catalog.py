"""Builds the catalog for the trainer - items, their numbers, names and images.

The numbers are the arguments of the base cheats. For vehicles it is the
position in Units.olb, for equipment it is NOT the position in Data.set but the
item number stored inside the record - and those differ. SET_M60 is the
thirty-ninth in order but has number 2; SET_MUN_MG is the first and has number
1, so equipment(0) matches nothing and the game refuses it.

Pairing
-------
A weapon knows its own ammunition: field 18 of the Data.set record is the
number of the ammunition item. SET_M60 has 1 (7.62mm), SET_AK74 has 21,
SET_DRAGUNOV has 142.

Vehicle armament is paired by name - SET_T55_125MMGUN, SET_T55_ROHRMG and
friends belong to the T-55. There is no table of those links in the data; the
vehicle fields carry no references to weapons at all (the matches that can be
found in them are coincidences).

Descriptions
------------
Equipment has a hint in TRES_EQUIPMENT (the key with the _HINT suffix),
vehicles have a pair of records in TRES_BUNKER_DESCRIPTIONS: _DATA (a table of
parameters) and _TEXT (a paragraph of prose). A newline is stored in the
catalog as \\n, because the file is line based.

Images
------
Gear has the icons the game shows in the inventory. Items.gui defines them: for
every item it holds a name (RES_AK74), a rectangle and a sheet number stored as
an id from 5000 to 5005 at the very END of the record - not the one right after
the name, which is easy to fall for. There are six sheets,
GUI_Shared/Items/items_1..6.png.

Vehicles have no inventory icon, they have photos in
GUI_Bunker/Einheiten_Bewaffnen. Whatever has neither falls back to the editor
previews.

Everything is converted to PNG into the catalog subfolder next to the launcher.

The output is tab separated, not JSON: the launcher is written against the .NET
Framework without third-party libraries, and taking this apart is a couple of
lines there.

Usage:
    python gen_catalog.py
"""
import io
import os
import re
import struct
import sys
import zipfile

from PIL import Image

import dataset
import gen_ids_doc as g
import trs

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
LAUNCHER = os.path.join(ROOT, '_research', 'tools', 'launcher')
CATALOG = os.path.join(LAUNCHER, 'catalog.txt')
IMAGES = os.path.join(LAUNCHER, 'catalog')
GUI = os.path.join(ROOT, '_patched', 'gui.ubn')
DATA = os.path.join(ROOT, '_patched', 'data.ubn')

# The icons are small in the sheets (the widest is 115x30), so they must not be
# scaled down - the cap is only there for the vehicle photos, which are larger.
MAX_SIZE = 256

# Which group an item belongs to. The order matters, the first match wins.
# These names are matched by the launcher (see launcher/Catalog.cs), so keep
# both sides in step.
GROUPS = [
    ('Ammunition', lambda i: i.startswith('SET_MUN_')),
    ('Vehicle weapons', lambda i: i.startswith('SET_HELI_') or
     any(v in i for v in ('_MK', '_GUN', '_MG', 'NEBELWERFER', 'FLAMMENWERFER',
                          '_TOW', '_AT2', '_AT6', '_UV7', '_UV32', '_UB20',
                          'PLAMJA', 'GRANATWERFER', 'ROHRMG', 'TURMMG'))),
    ('Gear and weapons', lambda i: True),
]
GROUP_VEHICLES = 'Vehicles'
GROUP_STORED_VEHICLES = 'Vehicles in storage'

# File names that do not match the identifier.
ALIASES = {
    'SET_DRAGUNOV': 'dragunow', 'SET_MEDIKIT': 'medipack',
    'SET_NACHTSICHTGERAET': 'nachtsicht', 'SET_SCHUTZWESTE_LEICHT': 'kugelweste',
    'SET_SCHUTZWESTE_SCHWER': 'splitterweste', 'SET_ALUKOFFER': 'koffer',
    'SET_HANDGRANATE': 'granate', 'SET_PANZERMINE': 'mine',
    'SET_SUBSURFACEMINE': 'suchmine', 'SET_BOX': 'ammobox',
    'SET_MUN_MG': 'mgshells', 'SET_MUN_AK74': 'akshells',
    'SET_MUN_9MM': '9mmshells', 'SET_MUN_SHOTGUN': 'shotgunshells',
    'SET_MUN_DRAGUNOV': 'snipershells', 'SET_MUN_ARMBRUST': 'koecher',
    'SET_MUN_RPG7': 'ammo_rpg7', 'SET_MUN_SA7': 'ammo_sa7',
    'SET_MUN_MESSER': 'messer', 'SET_MUN_HANDGRANATE': 'granate',
    'SET_MUN_MOLOTOW': 'molotow', 'SET_MUN_NEBELGRANATE': 'nebelgranate',
    'SET_MUN_BETAEUBUNGSGRANATE': 'betaeubungsgranate',
    'SET_MUN_PLAMJA_BRAND': 'plamjagranate_brand',
    'SET_MUN_PLAMJA_HE': 'plamjagranate_he',
    'UNIT_GAZ': 'gaz69', 'UNIT_GAZ2': 'gaz69a', 'UNIT_VULCAN': 'vulcan',
    'SET_GAZ': 'gaz69', 'SET_GAZA': 'gaz69a', 'SET_VULKAN': 'vulcan',
}


# The descriptions in TRES_BUNKER_DESCRIPTIONS are kept under German names that
# never meet the identifiers - "125 MM WUCHTGESCHOSS" is the sabot round of the
# tank, that is SET_MUN_125MMGUN_APSFDS. There is no way to pair that
# automatically, so here is the mapping. Without it ammunition was left with a
# single line of hint text such as "125mm MBT APFSDS grenade", which says
# nothing about how the round actually works.
DESCRIPTION_KEYS = {
    # tank and artillery ammunition
    'SET_MUN_125MMGUN_APSFDS': '125 MM WUCHTGESCHOSS',
    'SET_MUN_125MMGUN_HEAT': '125 MM PANZERBRECHENDES HOCHEXPLOSIVGESCHOSS',
    'SET_MUN_125MMGUN_HE': '125 MM SPLITTERNDES HOCHEXPLOSIVGESCHOSS',
    'SET_MUN_73MMGUN_HEAT': '73 MM PANZERBRECHENDES HOCHEXPLOSIVGESCHOSS',
    'SET_MUN_73MMGUN_HEFRAG': '73 MM HOCHEXPLOSIV SPLITTERGESCHOSS',
    'SET_MUN_152MMGUN_HE': '152 MM HOCHEXPLOSIVGESCHOSS',
    'SET_MUN_152MMGUN_NEBEL': '152 MM NEBELGESCHOSS',
    'SET_MUN_152MMGUN_LEUCHT': '152 MM LEUCHTGESCHOSS',
    'SET_MUN_152MMGUN_MINE': '152 MM MINENGESCHOSS',
    'SET_MUN_BM21_HEFRAG': '122MM HE-FRAG FLK',
    'SET_MUN_BM21_RAUCH': '122MM RAUCH FLK',
    'SET_MUN_BM21_MINE': '122MM MINE FLK',
    'SET_MUN_UB20': '80MM HOCHEXPLOSIV FLK',
    'SET_MUN_UV32': '57MM HOCHEXPLOSIV FLK',
    'SET_MUN_UV7': '57MM HOCHEXPLOSIV FLK',

    # guided missiles and bombs
    'SET_MUN_TOW': 'TOW FLK',
    'SET_MUN_AT2': 'AT2 SWATTER FLK',
    'SET_MUN_AT6': 'AT6 SPIRAL FLK',
    'SET_MUN_SA7': 'FLK SA7 GRAIL',
    'SET_MUN_RPG7': 'RPG7 GRANATE',
    'SET_MUN_250KGBOMBE': '250BOMBE',
    'SET_MUN_500KGBOMBE': '500BOMBE',

    # small arms ammunition and grenades
    'SET_MUN_MG': '7,65MM',
    'SET_MUN_AK74': '5,45MM',
    'SET_MUN_9MM': '9MM',
    'SET_MUN_MK': '14,5MM',
    'SET_MUN_SHOTGUN': 'SHOTGUNSHELLS',
    'SET_MUN_ARMBRUST': 'ARMBRUSTKOECHER',
    'SET_MUN_PLAMJA_BRAND': '40 MM BRANDGRANATE',
    'SET_MUN_PLAMJA_HE': '40 MM HOCHEXPLOSIVGRANATE',
    'SET_MUN_HANDGRANATE': 'HANDGRANATE',
    'SET_MUN_MOLOTOW': 'MOLOTOV',
    'SET_MUN_MESSER': 'MESSER',
    'SET_MUN_NEBELGRANATE': 'NEBELHANDGRANATE',
    'SET_MUN_PANZERNEBELGRANATE': 'NEBELGRANATE',
    'SET_MUN_BETAEUBUNGSGRANATE': 'BETAEUBUNGSHANDGRANATE',
    'SET_MUN_FLAMMENWERFER': 'KANISTER FLAMMENWERFER',

    # weapons and gear whose name missed as well
    'SET_RPG7': 'RPG-7',
    'SET_SA7': 'SA-7',
    'SET_SCHUTZWESTE_LEICHT': 'SCHUTZWESTE',
    'SET_SCHUTZWESTE_SCHWER': 'SPLITTERWESTE',
    'SET_PANZERMINE': 'MINE',
    'SET_HELI_UV7': 'HELIUV7',
    'SET_HELI_UV32': 'HELIUV32',
    'SET_HELI_UB20': 'HELIUB20',
    'SET_HELI_TOW': 'HELITOW',
    'SET_HELI_AT6': 'HELIAT6',
    'SET_HELI_AT6_4FACH': 'HELI4XAT6',
    'SET_HELI_SA7': 'HELISA7',
    'SET_HELI_MK': 'HELIMG',
    'SET_HELI_BORDMG': 'HELIMG',
    'SET_HUMVEE_TOW': 'HUMMERTOW',
    'SET_HUMVEE_M60': 'HUMMERMG',
    'SET_HUMVEE_PLAMJA': 'HUMMERPLAMJA',
}


def icons_from_items(zdata, zgui):
    """Return {RES name: (sheet, l, t, r, b)} from Items.gui.

    After the name a record holds one int, four floats with the rectangle, a
    couple of zeros, two ones and only then the sheet id. The first int looks
    like a sheet number, but it is the same for every item - taking it cuts
    everything out of the first sheet and most icons come out wrong.
    """
    d = zdata.read('data/GUIData/Items.gui')
    out = {}
    for m in re.finditer(rb'RES_[A-Z0-9_]+', d):
        p = m.end()
        if p + 40 > len(d):
            continue
        l, t, r, b = struct.unpack_from('<4f', d, p + 4)
        sheet_id = struct.unpack_from('<i', d, p + 36)[0]
        sheet = sheet_id - 4999
        if not (1 <= sheet <= 6) or r <= l or b <= t:
            continue
        out[m.group().decode()] = (sheet, l, t, r, b)
    return out


def load_sources(z):
    """Return {file name without extension: member in the archive}."""
    sources = {}
    for name in z.namelist():
        if not name.lower().endswith(('.png', '.tga')):
            continue
        if ('Einheiten_Bewaffnen' in name or 'Previews/Additionals' in name
                or 'Previews/Units' in name):
            base = os.path.splitext(name.split('/')[-1])[0].lower()
            sources.setdefault(base, name)
    return sources


def find_image(key, sources):
    """Try the alias, then the name without its prefix, then without underscores."""
    candidates = []
    if key in ALIASES:
        candidates.append(ALIASES[key].lower())
    bare = re.sub(r'^(SET_MUN_|SET_|UNIT_)', '', key).lower()
    candidates += [bare, bare.replace('_', '')]
    for c in candidates:
        if c in sources:
            return sources[c]
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    z = zipfile.ZipFile(g.UBN)
    zgui = zipfile.ZipFile(GUI)
    sources = load_sources(zgui)
    icons = icons_from_items(zipfile.ZipFile(DATA), zgui)
    sheets = {}
    for i in range(1, 7):
        sheets[i] = Image.open(io.BytesIO(
            zgui.read('gui/GUI_Shared/Items/items_%d.png' % i))).convert('RGBA')

    unit_names = g.names(z, 'data/ObjData/Units.olb', 'UNIT_',
                         'TRES_OBJECTS_', 'TRES_OBJECTS', forward=True)
    units = g.ids(z, 'data/ObjData/Units.olb', r'UNIT_[A-Z0-9_]+')

    records = dataset.load()
    by_number = dict((x['number'], x) for x in records)
    by_id = dict((x['id'], x) for x in records)
    texts = dict(trs.parse(z.read('data/GUIData/TextResource_eng/TRES_EQUIPMENT.trs')))
    bunker_texts = dict(trs.parse(
        z.read('data/GUIData/TextResource_eng/TRES_BUNKER_DESCRIPTIONS.trs')))

    # For ninety-seven objects TRES_BUNKER_DESCRIPTIONS holds a pair of records:
    # _DATA with a table of parameters and _TEXT with a paragraph of prose. The
    # keys are German names in capitals, so they are paired through a normalised
    # name.
    def normalise(t):
        return re.sub(r'[^A-Z0-9]', '', (t or '').upper())

    longer = {}
    for key, value in bunker_texts.items():
        if not (key.endswith('_DATA') or key.endswith('_TEXT')):
            continue
        base = normalise(key[len('TRES_'):].rsplit('_', 1)[0])
        if not base:
            continue
        text = value.strip()
        # "leer" is the German filler for an empty record, not content.
        if not text or text.lower() == 'leer':
            continue
        parts = longer.setdefault(base, {})
        parts['data' if key.endswith('_DATA') else 'text'] = text

    def equipment_description(x):
        short = (texts.get(x['hint'], '') or '').strip()
        candidates = []
        if x['id'] in DESCRIPTION_KEYS:
            candidates.append(DESCRIPTION_KEYS[x['id']])
        candidates += [x['name'], x['id'][len('SET_'):]]
        for candidate in candidates:
            parts = longer.get(normalise(candidate))
            if parts:
                long_text = '\n\n'.join(v for v in (parts.get('data'), parts.get('text')) if v)
                if long_text:
                    return long_text
        return short

    def vehicle_description(unit_id):
        # TRES_OBJECTS_UNIT_OH_58 -> TRES_OH58_DATA and _TEXT
        base = unit_id[len('UNIT_'):]
        parts = []
        for suffix in ('_DATA', '_TEXT'):
            key = 'TRES_' + base + suffix
            value = (bunker_texts.get(key) or '').strip()
            if value and value.lower() != 'leer':
                parts.append(value)
        return '\n\n'.join(parts)

    item_names = {}
    for x in records:
        english = texts.get(x['text'], '').strip()
        item_names[x['id']] = english or x['name'] or x['id']
    for key, name in unit_names.items():
        item_names[key] = name
        counterpart = 'SET_' + key[len('UNIT_'):]
        if counterpart in item_names:
            item_names[counterpart] = name

    # A weapon knows its ammunition through field 18.
    ammo_of = {}
    for x in records:
        if x['type'] == 2 and x['fields'] > 18:
            target = by_number.get(x['ints'][18])
            if target is not None and target['type'] == 1:
                ammo_of[x['id']] = target['id']
    # Several weapons share one kind of ammunition, so it cannot be hung under a
    # single one of them. Instead every weapon carries the number of its
    # ammunition item and the UI can add both.
    ammo_number = {}
    for weapon, ammo_id in ammo_of.items():
        ammo_number[weapon] = by_id[ammo_id]['number']

    # Vehicle armament is recognised by name: SET_T55_ROHRMG belongs to the T-55.
    # There is no link in the data, this is a naming convention.
    prefixes = {}
    for key in unit_names:
        prefixes[key[len('UNIT_'):]] = key
    prefixes['HUMVEE'] = 'UNIT_HUMMER'
    prefixes['VULKAN'] = 'UNIT_VULCAN'

    def carrier(key):
        rest = key[len('SET_'):]
        for prefix, unit in prefixes.items():
            if rest.startswith(prefix + '_'):
                return unit
        return ''

    whole_vehicles = {'SET_' + k[len('UNIT_'):] for k in unit_names}
    # SET_VULKAN and SET_GAZA are whole vehicles too, they are just spelled
    # differently than their units - without this they end up among the gear.
    whole_vehicles |= {'SET_VULKAN', 'SET_GAZA'}

    os.makedirs(IMAGES, exist_ok=True)
    for old in os.listdir(IMAGES):
        os.remove(os.path.join(IMAGES, old))

    items = []
    image_count = [0]

    def add(command, number, key, group, ammo='', belongs_to='', description='', stock='',
            value=''):
        image = ''
        im = None

        # The inventory icon first, that is the right one.
        res = 'RES_' + re.sub(r'^(SET_|UNIT_)', '', key)
        if res in icons:
            sheet, l, t, r, b = icons[res]
            im = sheets[sheet].crop((int(l), int(t), int(r), int(b)))
        else:
            source = find_image(key, sources)
            if source:
                im = Image.open(io.BytesIO(zgui.read(source))).convert('RGBA')

        if im is not None:
            image = key + '.png'
            if im.width > MAX_SIZE or im.height > MAX_SIZE:
                im.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
            im.save(os.path.join(IMAGES, image))
            image_count[0] += 1
        clean = (description or '').replace('\r', '').replace('\n', '\\n').replace('\t', ' ')
        items.append((command, number, key, item_names.get(key, key), group,
                      image, ammo, belongs_to, clean, stock, value))

    # The trade value is field 0 of the Data.set record - the trader multiplies
    # exactly this number, see ../trading.md. A unit has no record of its own,
    # it shares the value with its SET_ counterpart in the storage.
    # Two units are named differently in the two libraries.
    value_aliases = {'UNIT_VULCAN': 'SET_VULKAN', 'UNIT_GAZ2': 'SET_GAZA'}

    def trade_value(key):
        r = by_id.get(key)
        if r is None and key.startswith('UNIT_'):
            r = by_id.get(value_aliases.get(key, 'SET_' + key[len('UNIT_'):]))
        if r is None or r['fields'] < 1:
            return ''
        return '%g' % r['floats'][0]

    for i, key in enumerate(units):
        add('vehicle', i, key, GROUP_VEHICLES, description=vehicle_description(key),
            value=trade_value(key))

    for x in records:
        key = x['id']
        if key in whole_vehicles:
            group = GROUP_STORED_VEHICLES
        else:
            group = next(n for n, test in GROUPS if test(key))
        # For ammunition field 13 is the size of a pickup - checked against the
        # names ("7,62mm x 50" has 50, "5,45mm x 30" has 30).
        stock = str(x['ints'][13]) if x['type'] == 1 and x['fields'] > 13 else ''
        add('equipment', x['number'], key, group,
            str(ammo_number.get(key, '')), carrier(key), equipment_description(x), stock,
            trade_value(key))

    lines = ['# command\tnumber\tidentifier\tname\tgroup\timage'
             '\tammo_number\tcarrier\tdescription\tstock\tvalue']
    lines += ['%s\t%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' % p for p in items]
    with open(CATALOG, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(lines) + '\n')

    print('written %d items, %d of them with an image' % (len(items), image_count[0]))
    print('weapons with paired ammunition: %d' % len(ammo_of))
    print('weapons assigned to a vehicle: %d' % sum(1 for p in items if p[7]))
    print('items with a description: %d, of them longer: %d'
          % (sum(1 for p in items if p[8]),
             sum(1 for p in items if '\\n' in p[8])))
    counts = {}
    for p in items:
        counts[p[4]] = counts.get(p[4], 0) + 1
    for k, v in sorted(counts.items()):
        print('   %-22s %d' % (k, v))


if __name__ == '__main__':
    main()
