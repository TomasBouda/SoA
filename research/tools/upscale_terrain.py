"""Upscaling the terrain textures (terrain.ubn).

Only the ground (base/) and the sky (skies/) are enlarged here. The rest is
deliberately left at its original size for two reasons:

1. THE SHEETS. details.txt addresses the pieces of roads, tracks and surfaces
   by pixel coordinates inside shared images:

       ID;Name;Category;File;left;top;right;bottom
       16;...;standard/Asphaltstrasse.png;77;130;109;251

   Those are not regular halves but hand-cut rectangles packed into shared
   sheets. The addressing is proportional, so the sheets can be enlarged -
   that is what upscale_details.py does. This script does not touch the details
   so that both sets can be deployed and rolled back independently.

2. THE DISPLACE MAPS. terrain/displace/*.png are not images to look at but data
   for deforming the terrain geometry (displace.txt gives them min/max values).
   The artefacts of an upscaler would show up as waves in the ground.

base.txt holds no coordinates, which is why the ground is safe. The sky is not
addressed by coordinates anywhere either.

Usage:
    python upscale_terrain.py             only enlarge and check
    python upscale_terrain.py --install   and deploy next to the game
"""
import argparse
import os
import shutil
import sys
import zipfile

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Where the game is. `SOA_SOURCE` lets the package builder point every
# tool at one installation, so a package can be generated from a plain
# retail copy instead of from this project's own working folder.
SOURCE = os.environ.get('SOA_SOURCE', os.path.join(ROOT, '_patched'))
UBN = os.path.join(SOURCE, 'terrain.ubn')
WORK = os.path.join(ROOT, '_research', '_upscale_terrain')
GAME = SOURCE

# Folders this script must NOT enlarge:
#   displace  - geometry data, not images
#   the rest  - the detail textures addressed by the coordinates in
#               details.txt. They can be enlarged, but only the sheets and
#               never details.txt itself, so they are handled separately by
#               upscale_details.py.
SKIP_DIRS = ('displace', 'standard', 'desert', 'winter', 'usa', 'unborn')


def extract():
    src = os.path.join(WORK, 'in')
    shutil.rmtree(src, ignore_errors=True)
    z = zipfile.ZipFile(UBN)
    imgs = skipped = 0
    for name in z.namelist():
        if name.endswith('/'):
            continue
        parts = name.split('/')
        dest = os.path.join(src, *parts[1:])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(z.read(name))
        if name.lower().endswith('.png'):
            if len(parts) > 2 and parts[1].lower() in SKIP_DIRS:
                skipped += 1
            else:
                imgs += 1
    return src, imgs, skipped


def upscale(src, out, scale):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import time

    import esrgan
    n = kept = 0
    t0 = time.time()
    for dirpath, _, files in os.walk(src):
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, src)
            dest = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            top = rel.split(os.sep)[0].lower()
            if fn.lower().endswith('.png') and top not in SKIP_DIRS:
                esrgan.upscale_image(full, dest, scale)
                n += 1
                if n % 100 == 0:
                    print('  %d...' % n)
            else:
                shutil.copyfile(full, dest)     # displace maps and txt unchanged
                kept += 1
    print('  enlarged: %d, left unchanged: %d, in %.1f s' % (n, kept, time.time() - t0))


def verify(src, out, scale):
    ok = bad = 0
    for dirpath, _, files in os.walk(src):
        for fn in files:
            if not fn.lower().endswith('.png'):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), src)
            top = rel.split(os.sep)[0].lower()
            o = os.path.join(out, rel)
            if not os.path.exists(o):
                bad += 1
                continue
            a, b = Image.open(os.path.join(dirpath, fn)), Image.open(o)
            want = (a.width, a.height) if top in SKIP_DIRS else (a.width * scale, a.height * scale)
            if (b.width, b.height) != want:
                bad += 1
                continue
            if 'A' in a.getbands() and 'A' not in b.getbands():
                bad += 1
                continue
            ok += 1
    print('  fine: %d, wrong: %d' % (ok, bad))
    return bad == 0


def install(out):
    """Installs the enlarged images only. The configuration files and the
    skipped folders are left to the archive so that nothing falls apart."""
    n = 0
    for dirpath, _, files in os.walk(out):
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, out)
            if not fn.lower().endswith('.png'):
                continue
            if rel.split(os.sep)[0].lower() in SKIP_DIRS:
                continue
            dest = os.path.join(GAME, 'terrain', rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(full, dest)
            n += 1
    print('  files installed: %d -> %s' % (n, os.path.join(GAME, 'terrain')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--install', action='store_true')
    a = ap.parse_args()

    print('[1/4] extracting the terrain from the archive')
    src, imgs, skipped = extract()
    print('  to enlarge: %d, left alone (displace and details): %d' % (imgs, skipped))

    out = os.path.join(WORK, 'out_%dx' % a.scale)
    shutil.rmtree(out, ignore_errors=True)
    print('[2/4] upscaling %dx' % a.scale)
    upscale(src, out, a.scale)

    print('[3/4] checking')
    good = verify(src, out, a.scale)

    print('[4/4] installing')
    if a.install and good:
        install(out)
    elif a.install:
        print('  SKIPPED - the check did not pass')
    else:
        print('  skipped (run with --install)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
