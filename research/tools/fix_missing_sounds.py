"""Adds the sounds the game asks for but that were never shipped.

Found through decode_error.py: tracefile.log holds 65 ASSERT_HRESULT errors
(0x80004005) from SoundObject.cpp and every one of them is preceded by the line

    Sound not found. 'explosion_house_1.wav'

Those names are in data/ObjData/Buildings.olb, but there are no such files in
sounds.ubn. Right next to them, however, lie ex_stadthaus_gross_1 to 6, that is
the explosion of a large town house - the .olb even references
ex_stadthaus_gross_2.wav one line above. It looks like a rename somebody never
finished: part of the references stayed on the old names and the matching files
never made it into the archive.

So the script creates the missing names as copies of the ones that did ship.
This is not an invented substitute for something else - it is the same sound
under the name the game looks for.

querschlaeger1.wav (a ricochet) cannot be filled in this way, there is no
matching sound in the archive. It stays silent and shows up in the log twice
per mission.

Usage:
    python fix_missing_sounds.py --install
    python fix_missing_sounds.py --uninstall
"""
import argparse
import os
import shutil
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Where the game is. `SOA_SOURCE` lets the package builder point every
# tool at one installation, so a package can be generated from a plain
# retail copy instead of from this project's own working folder.
SOURCE = os.environ.get('SOA_SOURCE', os.path.join(ROOT, '_patched'))
UBN = os.path.join(SOURCE, 'sounds.ubn')
# The built package too, but only when nobody named a source: with SOA_SOURCE
# set the caller is building somewhere else and writing into this machine's own
# package would be a surprise.
TARGETS = [SOURCE]
if 'SOA_SOURCE' not in os.environ:
    TARGETS.append(os.path.join(os.path.dirname(ROOT), 'SoA-Package', 'Game'))

# Loose files are looked up in the same structure the archive has. Verified
# earlier with the body hit sounds, which live in Sounds/InGame/weapons.
SUBFOLDER = os.path.join('Sounds', 'InGame', 'explosionen')

REPLACEMENTS = {
    'explosion_house_1.wav': 'sounds/InGame/explosionen/ex_stadthaus_gross_1.wav',
    'explosion_house_2.wav': 'sounds/InGame/explosionen/ex_stadthaus_gross_2.wav',
    'explosion_house_3.wav': 'sounds/InGame/explosionen/ex_stadthaus_gross_3.wav',
    'explosion_house_4.wav': 'sounds/InGame/explosionen/ex_stadthaus_gross_4.wav',
    'explosion_house_5.wav': 'sounds/InGame/explosionen/ex_stadthaus_gross_5.wav',
}


def install():
    z = zipfile.ZipFile(UBN)
    available = set(z.namelist())
    for root in TARGETS:
        if not os.path.isdir(root):
            print('skipping, does not exist: %s' % root)
            continue
        to = os.path.join(root, SUBFOLDER)
        os.makedirs(to, exist_ok=True)
        for name, source in REPLACEMENTS.items():
            if source not in available:
                print('  the source %s is MISSING too' % source)
                continue
            with open(os.path.join(to, name), 'wb') as f:
                f.write(z.read(source))
        print('deployed %d sounds into %s' % (len(REPLACEMENTS), to))


def uninstall():
    for root in TARGETS:
        to = os.path.join(root, SUBFOLDER)
        removed = 0
        for name in REPLACEMENTS:
            path = os.path.join(to, name)
            if os.path.exists(path):
                os.remove(path)
                removed += 1
        if removed:
            print('removed %d sounds from %s' % (removed, to))
        if os.path.isdir(to) and not os.listdir(to):
            os.rmdir(to)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--uninstall', action='store_true')
    args = ap.parse_args()
    if args.uninstall:
        uninstall()
    elif args.install:
        install()
    else:
        raise SystemExit('say --install or --uninstall')


if __name__ == '__main__':
    main()
