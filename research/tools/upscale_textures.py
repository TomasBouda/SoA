"""Upscaling the game textures (Real-ESRGAN, optionally Topaz or Lanczos).

The engine reads loose files next to the game and prefers them over the archive
(verified while fixing the sounds), so the enlarged textures only have to be
put into _patched/textures/... and the .ubn stays untouched.

The procedure:
  1. extract the chosen subfolder from textures.ubn into a work folder
  2. enlarge it with the chosen engine (Real-ESRGAN on the GPU by default)
  3. check the dimensions and the presence of the alpha channel
  4. on request install the result as loose files next to the game

The format is preserved: PNG stays PNG, TGA stays TGA, BMP stays BMP. The
archive holds 458 PNG files (mostly RGBA), 150 TGA (all RGBA) and 87 BMP (all
RGB), and every dimension is a power of two.

The GUI is deliberately left out - that lives in gui.ubn and is drawn 1:1,
enlarging it would break the layout.

Usage:
    python upscale_textures.py Units              a pilot run on one folder
    python upscale_textures.py Units --install    and deploy it right away
    python upscale_textures.py ALL --install      everything
    python upscale_textures.py ALL --engine lanczos
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Where the game is. `SOA_SOURCE` lets the package builder point every
# tool at one installation, so a package can be generated from a plain
# retail copy instead of from this project's own working folder.
SOURCE = os.environ.get('SOA_SOURCE', os.path.join(ROOT, '_patched'))
UBN = os.path.join(SOURCE, 'textures.ubn')
WORK = os.path.join(ROOT, '_research', '_upscale')
GAME = SOURCE
TPAI = r'C:\Program Files\Topaz Labs LLC\Topaz Photo AI\tpai.exe'

EXTS = ('.png', '.tga', '.bmp')


def is_texture(name):
    return name.lower().endswith(EXTS)


def walk(root):
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if is_texture(fn):
                full = os.path.join(dirpath, fn)
                yield full, os.path.relpath(full, root)


def extract(folder):
    src = os.path.join(WORK, 'in')
    shutil.rmtree(src, ignore_errors=True)
    z = zipfile.ZipFile(UBN)
    n = 0
    for name in z.namelist():
        if name.endswith('/') or not is_texture(name):
            continue
        parts = name.split('/')
        if folder != 'ALL' and (len(parts) < 2 or parts[1].lower() != folder.lower()):
            continue
        dest = os.path.join(src, *parts[1:])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(z.read(name))
        n += 1
    return src, n


def run_esrgan(src, out, scale):
    """Real-ESRGAN on the GPU. The alpha goes around the model and is put back."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import time

    import esrgan
    n = 0
    t0 = time.time()
    for full, rel in walk(src):
        esrgan.upscale_image(full, os.path.join(out, rel), scale)
        n += 1
        if n % 100 == 0:
            print('  %d...' % n)
    print('  files enlarged: %d in %.1f s' % (n, time.time() - t0))
    return 0


def run_lanczos(src, out, scale):
    """The fallback without AI: plain resampling."""
    n = 0
    for full, rel in walk(src):
        dest = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        im = Image.open(full)
        if im.mode == 'P':
            im = im.convert('RGBA' if 'transparency' in im.info else 'RGB')
        im.resize((im.width * scale, im.height * scale), Image.LANCZOS).save(dest)
        n += 1
    print('  files resampled: %d' % n)
    return 0


def run_topaz(src, out, scale):
    """Needs a valid token; with a licence without an active subscription it
    reports 'Invalid auth token' even while the GUI runs."""
    os.makedirs(out, exist_ok=True)
    cmd = [TPAI, '-r', '-o', out, '--format', 'png',
           '--override', '--upscale', 'scale=%d' % scale, src]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print('  exit code: %d' % r.returncode)
    tail = ((r.stdout or '') + (r.stderr or ''))[-600:]
    if tail.strip():
        print('  ' + tail.strip().replace('\n', '\n  '))
    return r.returncode


def match_tga_header(src, out):
    """Match the TGA descriptor with the original.

    145 of the 150 original TGA files are 32 bpp but carry a zero alpha bit
    count in the descriptor byte - the original tool wrote it carelessly. The
    alpha is in the data and the game draws by it, so it evidently ignores that
    field. Even so we would rather carry it over unchanged so that the loading
    behaviour does not change.
    """
    n = 0
    for full, rel in walk(src):
        if not full.lower().endswith('.tga'):
            continue
        o = os.path.join(out, rel)
        if not os.path.exists(o):
            continue
        with open(full, 'rb') as f:
            orig = f.read(18)
        with open(o, 'r+b') as f:
            new = bytearray(f.read(18))
            if new[17] != orig[17]:
                new[17] = orig[17]
                f.seek(0)
                f.write(new)
                n += 1
    if n:
        print('  descriptor matched on %d TGA files' % n)
    return n


def verify(src, out, scale):
    ok = missing = wrong = alpha_lost = 0
    for full, rel in walk(src):
        o = os.path.join(out, rel)
        if not os.path.exists(o):
            missing += 1
            continue
        try:
            a, b = Image.open(full), Image.open(o)
        except Exception:
            wrong += 1
            continue
        if (b.width, b.height) != (a.width * scale, a.height * scale):
            wrong += 1
            continue
        if 'A' in a.getbands() and 'A' not in b.getbands():
            alpha_lost += 1
        ok += 1
    print('  fine: %d, missing: %d, wrong size: %d, alpha lost: %d'
          % (ok, missing, wrong, alpha_lost))
    return missing == 0 and wrong == 0 and alpha_lost == 0


def install(out):
    n = 0
    for full, rel in walk(out):
        dest = os.path.join(GAME, 'textures', rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(full, dest)
        n += 1
    print('  loose files installed: %d -> %s' % (n, os.path.join(GAME, 'textures')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', help='a subfolder of textures.ubn, or ALL')
    ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--engine', choices=('esrgan', 'topaz', 'lanczos'), default='esrgan')
    a = ap.parse_args()

    if a.engine == 'topaz' and not os.path.exists(TPAI):
        print('ERROR: tpai.exe not found: %s' % TPAI)
        return 1

    print('[1/4] extracting the textures from the archive')
    src, n = extract(a.folder)
    if not n:
        print('  there are no textures in the folder %r' % a.folder)
        return 1
    print('  files: %d' % n)

    out = os.path.join(WORK, 'out_%s_%dx' % (a.engine, a.scale))
    print('[2/4] upscaling %dx (%s)' % (a.scale, a.engine))
    shutil.rmtree(out, ignore_errors=True)
    runner = {'topaz': run_topaz, 'lanczos': run_lanczos, 'esrgan': run_esrgan}[a.engine]
    if runner(src, out, a.scale) not in (0, 1):
        return 1

    match_tga_header(src, out)

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
