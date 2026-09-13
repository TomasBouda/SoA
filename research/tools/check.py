"""Does the package still do what it claims? Checks that need no running game.

The launcher patches three places in soa.exe, injects code into the running
game and reads its memory at fixed addresses. All of it is tied to one build,
1.1.2.178, and all of it fails quietly: a patch that lands in the wrong place,
an address that moved, a table that changed - none of that says anything until
somebody plays far enough to notice.

This is the half that can run on every build, in a second, with nothing
started:

    patches      each signature is unique in the exe, and applying and
                 reverting a group gives back a byte-identical file
    addresses    every address the launcher calls or reads still holds the
                 bytes it held when it was read out of the disassembly
    catalog      catalog.txt still agrees with Data.set

The addresses are pinned in addresses.json rather than in this file, so that
adding one is a --record away and the difference shows up in the repository as
data rather than as code.

The other half - start the game, reach the base, send a cheat, load a save,
read the map - needs the game driven from outside, which is a TODO of its own.

Usage:
    python check.py                 run every check
    python check.py --record        write addresses.json from the exe as it is
    python check.py --exe <path>    check another copy
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DEFAULT_EXE = os.path.join(ROOT, '_patched', 'soa.exe')
PINNED = os.path.join(HERE, 'addresses.json')
IMAGE_BASE = 0x400000

# What the launcher and the tools reach into the game for. The comment is what
# breaks if the address moves.
ADDRESSES = [
    (0x0052F4A0, 'the base cheat dispatcher', 'the catalog and the console'),
    (0x00405D80, 'the tsString constructor', 'every cheat sent into the game'),
    (0x005ECA70, 'the mission cheat handler', 'the mission cheats'),
    (0x00663B80, 'the overlay switch', 'the debug overlays'),
    (0x00758CBC, 'operator new', 'read by the overlay code'),
    (0x00578800, 'the getter that returns a stamp', 'finding the units'),
    (0x006C3FD0, 'the routine that stamps into the cell array', 'the map'),
    (0x005E7B50, 'the mission constructor', 'finding the mission'),
    (0x005E9910, 'the mission message handler', 'the mission cheats'),
    (0x00675FD0, 'the path grid lookup', 'the height on the map'),
    (0x00685570, 'the ShowGround query', 'the ground bits of a cell'),
    (0x00684E90, 'the ShowParty query', 'the party bits of a cell'),
    (0x005F23D0, 'quick save', 'the quicksave command'),
    (0x005F26F0, 'quick load', 'the quickload command'),
    (0x0060BC60, 'load a mission by name', 'the loadmission command'),
    (0x005F2C10, 'load a saved game', 'the loadsave command'),
    (0x004E83E8, 'the START_MISSION packet handler', 'where loadmission was found'),
]

# Tables and vtables, which are data rather than code but pin just as much.
TABLES = [
    (0x0085CF10, 0x6C, 'the mission cheat table'),
    (0x00446DB8, 0x10C, 'the base cheat table'),
    (0x007D0568, 0x20, 'the mission vtable'),
    (0x007D31A4, 0x18, 'the ShowPathMap overlay vtable'),
    (0x007C8820, 0x18, 'the ShowStructures overlay vtable'),
]


def say(text, kind='INFO'):
    colour = {'OK': '\033[92m', 'FAIL': '\033[91m', 'INFO': '\033[90m'}.get(kind, '')
    print('  %s%-5s\033[0m %s' % (colour, kind, text))


def read_exe(path):
    if not os.path.exists(path):
        raise SystemExit('%s does not exist' % path)
    return bytearray(open(path, 'rb').read())


def offset(address):
    """File offset of a virtual address. Every section of this exe is mapped
    where it lies, so the image base is all that has to come off."""
    return address - IMAGE_BASE


def check_addresses(data, pinned, failures):
    for address, what, why in ADDRESSES + [(a, w, 'a table') for a, _, w in TABLES]:
        key = '%08X' % address
        here = bytes(data[offset(address):offset(address) + 16]).hex().upper()
        if key not in pinned:
            say('%s (%s) is not pinned - run --record' % (key, what), 'FAIL')
            failures.append(key)
            continue
        if pinned[key]['bytes'] != here:
            say('%s (%s) changed - %s stops working' % (key, what, why), 'FAIL')
            say('   pinned %s' % pinned[key]['bytes'], 'INFO')
            say('   found  %s' % here, 'INFO')
            failures.append(key)
    if not failures:
        say('%d addresses still hold what they held' % len(pinned), 'OK')


def check_patches(exe, failures):
    """Each signature unique, and a round trip byte for byte."""
    sys.path.insert(0, HERE)
    import patch_exe

    data = read_exe(exe)
    for group, name, anchor, original, patched in patch_exe.PATCHES:
        found = 0
        start = 0
        if isinstance(anchor, int):
            # A place in the padding, given by offset: there is nothing to be
            # unique about, only the bytes to be what they should.
            found = 1 if bytes(data[anchor:anchor + len(original)]) in (original, patched) else 0
            anchor = None
        while anchor is not None:
            i = data.find(anchor, start)
            if i < 0:
                break
            start = i + 1
            after = data[i + len(anchor):i + len(anchor) + len(original)]
            if bytes(after) in (original, patched):
                found += 1
        if found != 1:
            say('the signature for "%s" matches %d places, not one' % (name, found), 'FAIL')
            failures.append(name)
    if not failures:
        say('%d patch signatures, each unique' % len(patch_exe.PATCHES), 'OK')

    # The launcher carries the same table in C# (Patches.cs), typed in by
    # hand, and once drifted: a cave regenerated in patch_exe.py and not
    # copied over left the launcher showing the mailbox as off and ready
    # to write the old bytes. Every group the launcher knows has to hold
    # patch_exe's bytes exactly. (window, focus, intro and log live in
    # App.cs and are checked through the addresses above.)
    import re
    cs = open(os.path.join(HERE, 'launcher', 'Patches.cs'), encoding='utf-8').read()
    # Two characters and up: the M34's table bytes are a byte or two.
    hexes = set(re.findall(r'"([0-9A-F]{2,})"', cs))
    stale = [name for group, name, anchor, original, patched in patch_exe.PATCHES
             if group not in ('window', 'focus', 'intro', 'log')
             and (original.hex().upper() not in hexes or patched.hex().upper() not in hexes)]
    for name in stale:
        say('Patches.cs does not hold the bytes of "%s" - the launcher is out of step' % name, 'FAIL')
    failures.extend(stale)
    if not stale:
        say('the launcher and patch_exe.py hold the same bytes', 'OK')

    # The fonts are a value, not a toggle, so the launcher has their places
    # rather than their bytes: every push and cave offset patch_exe.py knows.
    missing = [key for key, slot in patch_exe.FONT_SLOTS.items()
               if any('0x%X' % at not in cs for at in slot['pushes'] + [slot['cave']])]
    for key in missing:
        say('Patches.cs does not hold the offsets of the %s font - the launcher is out of step' % key, 'FAIL')
    failures.extend(missing)
    if not missing:
        say('the launcher and patch_exe.py agree on where the fonts are', 'OK')

    # The round trip: on a copy, so the real exe is never touched. Which way
    # round each group starts is read off the file first, so that the copy ends
    # the way it began whatever state it was in.
    work = os.path.join(tempfile.gettempdir(), 'soa-check.exe')
    shutil.copyfile(exe, work)
    before = hashlib.sha256(open(work, 'rb').read()).hexdigest()

    groups = {'window': ('--windowed', '--fullscreen'),
              'focus': ('--keep-focus', '--minimise'),
              'log': ('--share-log', '--lock-log')}
    was = {}
    for group, name, anchor, original, patched in patch_exe.PATCHES:
        pos = patch_exe.locate(data, anchor, original, patched)
        if pos is not None:
            was[group] = bytes(data[pos:pos + len(patched)]) == patched

    def run(*switch):
        subprocess.check_output([sys.executable, os.path.join(HERE, 'patch_exe.py'),
                                 '--exe', work] + list(switch))

    for group, (there, back) in groups.items():
        run(there); run(back); run(there); run(back)
        run(there if was.get(group) else back)
    fonts = {key: patch_exe.font_of(data, slot) for key, slot in patch_exe.FONT_SLOTS.items()}
    if None not in fonts.values():
        run('--font', 'Check font', '--bitmap-font', 'Check font')
        run('--default-fonts')
        run('--font', fonts['screens'], '--bitmap-font', fonts['bitmap'])
    after = hashlib.sha256(open(work, 'rb').read()).hexdigest()
    orig = work + '.orig'
    if os.path.exists(orig):
        os.remove(orig)
    os.remove(work)
    if before != after:
        say('applying and reverting the patches does not give the file back', 'FAIL')
        failures.append('round trip')
    else:
        say('the patches apply and revert byte for byte', 'OK')


def check_catalog(failures):
    catalog = os.path.join(HERE, 'launcher', 'catalog.txt')
    if not os.path.exists(catalog):
        say('catalog.txt is missing', 'FAIL')
        failures.append('catalog')
        return
    sys.path.insert(0, HERE)
    import dataset

    try:
        # with the M34: the catalog lists what the game with the package's
        # loose Data.set has, which is the archive's records and the two
        # mod_m34.py appends
        records = dataset.load(with_m34=True)
    except Exception as problem:
        say('Data.set could not be read: %s' % problem, 'FAIL')
        failures.append('dataset')
        return
    known = {r['id'] for r in records}

    # Two kinds of row. The equipment comes out of Data.set and its identifier
    # has to be in there; the vehicles are a list of their own (UNIT_...) that
    # the cheat takes by number, so for those the numbers are what matters -
    # they have to run from zero without a gap or a repeat, because that is
    # what the cheat indexes.
    missing, vehicles, equipment = [], [], 0
    for line in open(catalog, encoding='utf-8'):
        if line.startswith('#'):
            continue
        parts = line.rstrip(chr(10)).split(chr(9))
        if len(parts) < 3:
            continue
        if parts[0] == 'vehicle':
            vehicles.append(int(parts[1]))
        else:
            equipment += 1
            if parts[2] not in known:
                missing.append(parts[2])

    if missing:
        say('%d equipment items of catalog.txt are not in Data.set, first %s'
            % (len(missing), missing[0]), 'FAIL')
        failures.append('catalog')
    else:
        say('%d equipment items, all of them in Data.set' % equipment, 'OK')

    if sorted(vehicles) != list(range(len(vehicles))):
        say('the vehicle numbers are not 0..%d without gaps' % (len(vehicles) - 1), 'FAIL')
        failures.append('vehicles')
    else:
        say('%d vehicles, numbered 0..%d' % (len(vehicles), len(vehicles) - 1), 'OK')


def record(data):
    pinned = {}
    for address, what, _ in ADDRESSES:
        pinned['%08X' % address] = {
            'what': what,
            'bytes': bytes(data[offset(address):offset(address) + 16]).hex().upper(),
        }
    for address, stride, what in TABLES:
        pinned['%08X' % address] = {
            'what': what,
            'stride': stride,
            'bytes': bytes(data[offset(address):offset(address) + 16]).hex().upper(),
        }
    with open(PINNED, 'w', encoding='utf-8') as f:
        json.dump(pinned, f, indent=2, sort_keys=True)
        f.write('\n')
    print('%d addresses pinned in %s' % (len(pinned), PINNED))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', default=DEFAULT_EXE)
    ap.add_argument('--record', action='store_true',
                    help='write addresses.json from the exe as it is now')
    args = ap.parse_args()

    data = read_exe(args.exe)
    if args.record:
        record(data)
        return

    if not os.path.exists(PINNED):
        raise SystemExit('%s is missing - run --record once first' % PINNED)
    pinned = json.load(open(PINNED, encoding='utf-8'))

    print('%s' % args.exe)
    failures = []
    print('\naddresses')
    check_addresses(data, pinned, failures)
    print('\npatches')
    check_patches(args.exe, failures)
    print('\ncatalog')
    check_catalog(failures)

    print()
    if failures:
        raise SystemExit('%d checks failed' % len(failures))
    print('everything the package relies on is still where it was.')


if __name__ == '__main__':
    main()
