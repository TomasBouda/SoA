"""Upscaling the detail textures of the terrain - roads, tracks, grass variants.

This is the part upscale_terrain.py left out for a long time. The details are
not standalone images: details.txt addresses hand-cut rectangles inside shared
256x256 sheets.

    ID;Name;Category;File;left;top;right;bottom
    16;...;standard\\Asphaltstrasse.png;77;130;109;251

The key finding: **those numbers are proportional, not absolute.** The engine
converts them into UV coordinates by dividing them by a fixed sheet size, not
by the real size of the loaded image, so an enlarged sheet falls into place on
its own and details.txt must not be touched. Verified in the game on both
variants:

  sheets 2x, details.txt recomputed     the road is assembled from the wrong
                                        pieces, bends instead of straight runs
  sheets 2x, details.txt from the archive   the road is continuous and sharper

Recomputed coordinates overflow the edge and reach into the neighbouring cut -
hence the bends. So the script enlarges the images only and leaves details.txt
to the archive.

The displace folder stays out of this as well: those are not images to look at
but data for deforming the terrain geometry, where the artefacts of an upscaler
would show up as waves in the ground.

Usage:
    python upscale_details.py --install
        Enlarges every sheet details.txt references and deploys them next to
        the game as loose files.

    python upscale_details.py --only Asphaltstrasse.png --marker --install
        A single sheet, with a magenta line around every cut. That is how to
        tell in the game whether the coordinates fit - the lines have to lie on
        the edges of the tiles.

    python upscale_details.py --uninstall
        Cleanup: removes the loose files, the game goes back to the archive.
"""
import argparse
import os
import shutil
import zipfile

from PIL import Image, ImageDraw

import esrgan

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Where the game is. `SOA_SOURCE` lets the package builder point every tool at
# one installation, so a package can be generated from a plain retail copy.
SOURCE = os.environ.get('SOA_SOURCE', os.path.join(ROOT, '_patched'))
UBN = os.path.join(SOURCE, 'terrain.ubn')
GAME = os.path.join(SOURCE, 'terrain')
WORK = os.path.join(ROOT, '_research', '_upscale_details')

SCALE = 2
MARKER = (255, 0, 255, 255)


def load_details(z):
    """Return the (file, l, t, r, b) records of details.txt in the archive."""
    raw = z.read('terrain/details.txt').decode('cp1252')
    records = []
    for line in raw.split('\n'):
        bare = line.strip()
        if not bare or bare.startswith(';'):
            continue
        parts = bare.split(';')
        if len(parts) < 8:
            continue
        file = parts[3].replace('\\', '/')
        l, t, r, b = (int(x) for x in parts[4:8])
        records.append((file, l, t, r, b))
    return records


def uninstall():
    removed = 0
    details = os.path.join(GAME, 'details.txt')
    if os.path.exists(details):
        os.remove(details)
        removed += 1
    for folder in ('standard', 'desert', 'winter', 'usa', 'unborn'):
        path = os.path.join(GAME, folder)
        if os.path.isdir(path):
            removed += len([f for f in os.listdir(path) if f.lower().endswith('.png')])
            shutil.rmtree(path)
    print('loose files removed: %d, the game goes back to the archive' % removed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', action='append', default=[],
                    help='only these sheets (file name, can be repeated)')
    ap.add_argument('--marker', action='store_true',
                    help='outline every cut with a magenta line')
    ap.add_argument('--model', default='photo', choices=('photo', 'anime'))
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--uninstall', action='store_true')
    args = ap.parse_args()

    if args.uninstall:
        uninstall()
        return

    z = zipfile.ZipFile(UBN)
    records = load_details(z)

    sheets = sorted({s for s, _, _, _, _ in records})
    if args.only:
        wanted = {o.lower() for o in args.only}
        sheets = [s for s in sheets if os.path.basename(s).lower() in wanted]
        if not sheets:
            raise SystemExit('none of the sheets %s is in details.txt' % args.only)
    print('sheets to enlarge: %d' % len(sheets))

    os.makedirs(WORK, exist_ok=True)
    src = os.path.join(WORK, '_src.png')
    enlarged = []
    for file in sheets:
        member = 'terrain/' + file
        if member not in z.namelist():
            print('  MISSING from the archive: %s' % file)
            continue
        with open(src, 'wb') as f:
            f.write(z.read(member))
        dest = os.path.join(WORK, file.replace('/', os.sep))
        esrgan.upscale_image(src, dest, scale=SCALE, model=args.model)

        if args.marker:
            im = Image.open(dest).convert('RGBA')
            draw = ImageDraw.Draw(im)
            for s, l, t, r, b in records:
                if s == file:
                    draw.rectangle([l * SCALE, t * SCALE, r * SCALE - 1, b * SCALE - 1],
                                   outline=MARKER)
            im.save(dest)

        enlarged.append(file)
        print('  %-34s %dx -> %s' % (os.path.basename(file), SCALE,
                                     '%dx%d' % Image.open(dest).size))
    if os.path.exists(src):
        os.remove(src)

    if args.install:
        for file in enlarged:
            target = os.path.join(GAME, file.replace('/', os.sep))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(os.path.join(WORK, file.replace('/', os.sep)), target)
        # details.txt is deliberately not copied - the coordinates are
        # proportional and a loose recomputed copy would break the roads.
        details = os.path.join(GAME, 'details.txt')
        if os.path.exists(details):
            os.remove(details)
        print('installed into %s (sheets: %d, details.txt stays with the archive)'
              % (GAME, len(enlarged)))


if __name__ == '__main__':
    main()
