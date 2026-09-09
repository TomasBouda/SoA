"""Taking in repainted base terrain textures from a generative model.

An upscaler can only smooth out what is already in the image. It will not
conjure blades of grass or the grain of asphalt out of a 256x256 original,
because they are not there. A generative model can invent the detail - but it
brings three problems this script deals with:

1. COLOUR DRIFT. Repainted grass tends to be a different green than the other
   textures that stayed original. Side by side that shows more than the
   original blurriness, so the mean and the variance of every channel of the
   new image are matched to the values of the original.

2. TILING. base_5, base_7 and base_8 really are seamless - the opposite edges
   differ by 0.2 to 2.9, while random columns inside differ by 12.6.
   Repainting destroys that property and a grid appears across the whole map.
   The script covers the seam with a shifted copy of the image and prints the
   difference before and after, so it is visible whether that was enough.

3. SIZE. The models return whatever occurs to them. The result is resampled to
   the target size, 512x512 by default, that is twice the original.

4. DETAIL SCALE, and that is the biggest problem. The model gets a square and
   draws grass into it from close up, but the game covers a large area of
   terrain with that texture - its fine grain melts into a flat colour when
   displayed and the coarse mottling that gives the ground its look in the
   game disappears. That is why the default "detail" mode takes the better half
   from each side: the low frequencies from the original (mottling, colours,
   matching edges), the high ones from the model (the grain the original
   lacks). The "replace" mode uses the image from the model whole.

The detail sheets (roads, tracks) do not go through here. Of the 48 of them 47
have transparency and it carries the shape - the edge of a road dissolves into
the terrain exactly where details.txt points. The model returns an opaque image
with the content laid out differently, so it would break both.

Usage:
    python import_texture.py --export ..\\_repaint
        Extracts the 13 base textures from the archive and writes the brief for
        the model next to them.

    python import_texture.py --import ..\\_repaint\\base_1_new.png
                             --target base_1.png --install
        Takes in a repainted texture: matches the colours, covers the seam,
        resamples it, saves it next to the game and builds a comparison image.

    python import_texture.py --import-dir --install
        Takes in everything lying in _repaint\\new at once. It recognises the
        target texture from the file name, it is enough that it contains
        base_1, base_12 and so on.

    python import_texture.py --uninstall base_1.png
        Puts one texture back to the archive. Without a name it puts back every
        base texture.
"""
import argparse
import io
import os
import re
import shutil
import zipfile

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
UBN = os.path.join(ROOT, '_patched', 'terrain.ubn')
GAME = os.path.join(ROOT, '_patched', 'terrain', 'base')
PACKAGE = os.path.join(os.path.dirname(ROOT), 'SoA-Package', 'Game', 'terrain', 'base')
WORK = os.path.join(ROOT, '_research', '_repaint')
NEW = os.path.join(WORK, 'new')

TARGET_SIZE = 512
BLEND = 24

BRIEF = """Brief for an image model
========================

For every texture there is an original from 2002 here, 256x256. The goal is NOT
to invent a new surface but to draw the same surface properly - with the detail
that did not fit into 256 pixels.

The prompt that holds together best (replace NAME with the description below):

    Top-down seamless ground texture of NAME, photorealistic, even lighting,
    no shadows, no objects, no vignetting, uniform detail across the whole
    square, same colour palette as the reference image, 1024x1024.

The conditions that matter:

* TOP-DOWN VIEW, perfectly perpendicular. No perspective, no horizon.
* EVEN LIGHTING. No shadows, no darker corners - the texture is tiled in the
  game and every dark corner shows up across the whole map as a grid.
* NO OBJECTS. No extra stones, branches, flowers or tracks. The surface only.
* THE SAME COLOURS as the original. The script does match the colours, but once
  the model turns grass into a desert, matching no longer helps.

What is what:

    base_1   ordinary green grass, the most common surface in the campaign
    base_2   dark grass
    base_3   wasteland, dry ground
    base_4   concrete
    base_5   sandy ground           (seamless - watch the seam)
    base_6   mossy ground
    base_7   flooded ground         (seamless - watch the seam)
    base_8   icy waste              (seamless - watch the seam)
    base_9   dry grass
    base_10  red rock
    base_11  red rock, variant
    base_12  steppe
    base_13  sandy lawn

Then pour the finished image back in:

    python import_texture.py --import <file> --target base_1.png --install
"""


def from_archive(name):
    z = zipfile.ZipFile(UBN)
    return Image.open(io.BytesIO(z.read('terrain/base/' + name))).convert('RGB')


def seam(a):
    """How visible the seam is, in multiples of the usual difference of neighbouring rows.

    The bare difference of the opposite edges says nothing on its own: in a
    grainy texture two neighbouring columns differ as much as the outer ones do
    without there being a seam. So it is divided by the difference of
    neighbouring columns inside the image. A result around 1 means the
    transition across the edge looks like any other neighbourhood - that is,
    seamless. A number well above 1 means a visible grid across the whole map.
    """
    a = a.astype(float)
    edge = (np.abs(a[:, 0, :] - a[:, -1, :]).mean() + np.abs(a[0, :, :] - a[-1, :, :]).mean()) / 2
    inside = (np.abs(a[:, 1:, :] - a[:, :-1, :]).mean() + np.abs(a[1:, :, :] - a[:-1, :, :]).mean()) / 2
    return edge / inside if inside > 1e-6 else 0.0


def match_colours(new, reference):
    """The mean and the variance of every channel matched to the original."""
    n = new.astype(float)
    v = reference.astype(float)
    for k in range(3):
        sn = n[:, :, k].std()
        if sn < 1e-6:
            continue
        n[:, :, k] = (n[:, :, k] - n[:, :, k].mean()) * (v[:, :, k].std() / sn) + v[:, :, k].mean()
    return np.clip(n, 0, 255).astype(np.uint8)


def cover_seam(a, blend=BLEND):
    """Makes the texture tileable with a shifted copy of itself.

    Blending the opposite edges is not enough - the edges do get closer, but
    continuity does not follow from that. A shifted copy does it: an image
    shifted by half has continuous content where the original seam was, so
    covering a frame along the perimeter with it makes the wrap match on its
    own. The inside stays the original image, only the border band changes.
    """
    a = a.astype(float)
    h, w, _ = a.shape
    shifted = np.roll(np.roll(a, w // 2, axis=1), h // 2, axis=0)

    x = np.arange(w)
    y = np.arange(h)
    dx = np.minimum(x, w - 1 - x) / float(blend)
    dy = np.minimum(y, h - 1 - y) / float(blend)
    m = np.clip(np.minimum(dx[None, :], dy[:, None]), 0, 1)
    m = (m * m * (3 - 2 * m))[:, :, None]        # a smooth ramp instead of a kink

    return np.clip(a * m + shifted * (1 - m), 0, 255).astype(np.uint8)


def join_detail(new, original_enlarged, radius):
    """The structure from the original, the fine grain from the model.

    The model draws detail at the scale it is given - it gets a square and
    draws grass into it from close up. The game, however, covers a large area
    of terrain with that texture, so its fine grain melts together when
    displayed and a flat colour is left. The original texture on the other hand
    carries the coarse mottling that gives the ground its look in the game.

    So the better half is taken from each: the low frequencies (mottling,
    colours, matching edges) from the original, the high ones (the grain it
    lacks) from the model.
    """
    n = np.asarray(new, dtype=float)
    lo = np.asarray(new.filter(ImageFilter.GaussianBlur(radius)), dtype=float)
    base = np.asarray(original_enlarged, dtype=float)
    return np.clip(base + (n - lo), 0, 255).astype(np.uint8)


def comparison_image(original, accepted, to):
    """The original enlarged without smoothing next to the new image."""
    size = accepted.size
    left = original.resize(size, Image.NEAREST)
    canvas = Image.new('RGB', (size[0] * 2 + 8, size[1]), (24, 26, 32))
    canvas.paste(left, (0, 0))
    canvas.paste(accepted, (size[0] + 8, 0))
    canvas.save(to)


def export(to):
    os.makedirs(to, exist_ok=True)
    z = zipfile.ZipFile(UBN)
    n = 0
    for member in sorted(x for x in z.namelist()
                         if x.startswith('terrain/base/') and x.endswith('.png')):
        name = member.split('/')[-1]
        with open(os.path.join(to, name), 'wb') as f:
            f.write(z.read(member))
        n += 1
    with open(os.path.join(to, 'brief.txt'), 'w', encoding='cp1252') as f:
        f.write(BRIEF)
    os.makedirs(NEW, exist_ok=True)
    print('exported %d originals into %s' % (n, to))
    print('the brief for the model is in %s' % os.path.join(to, 'brief.txt'))
    print('put the finished images into %s and run --import-dir' % NEW)


def accept(file, target_name, size, install, no_colours, no_seam, mode):
    original = from_archive(target_name)
    new = Image.open(file).convert('RGB')
    print('original: %dx%d, incoming image: %dx%d' % (original.size + new.size))

    if new.size != (size, size):
        new = new.resize((size, size), Image.LANCZOS)
        print('resampled to %dx%d' % (size, size))

    a = np.asarray(new)
    o = np.asarray(original)
    original_enlarged = original.resize((size, size), Image.LANCZOS)

    seam_before = seam(a)
    seam_original = seam(o)

    if mode == 'detail':
        # The radius matches one pixel of the original: whatever is finer comes
        # from the model, whatever is coarser stays from the original.
        radius = max(2.0, size / float(original.width))
        a = join_detail(new, original_enlarged, radius)
        print('structure from the original, grain from the model (radius %.1f px)' % radius)
    elif not no_colours:
        # The original is only enlarged for the statistics, it does not enter
        # the result.
        a = match_colours(a, np.asarray(original_enlarged))
        print('colours matched to the original')

    if not no_seam:
        a = cover_seam(a)
        print('seam covered with a shifted copy (frame %d px)' % BLEND)

    seam_after = seam(a)
    print('seam (1.0 = indistinguishable): original %.2f, from the model %.2f -> after %.2f'
          % (seam_original, seam_before, seam_after))
    if seam_after > 1.5:
        print('  WARNING: the transition across the edge is %.1f times stronger than an'
              % seam_after)
        print('           ordinary neighbourhood. In the game that shows as a grid.')

    result = Image.fromarray(a)
    done = os.path.join(WORK, 'done')
    os.makedirs(done, exist_ok=True)
    finished = os.path.join(done, target_name)
    if mode == 'replace':
        finished = os.path.join(done, target_name.replace('.png', '_replace.png'))
    result.save(finished)
    comparison = os.path.join(done, os.path.basename(finished).replace('.png', '_comparison.png'))
    comparison_image(original, result, comparison)
    print('saved: %s' % finished)
    print('comparison (original left, new right): %s' % comparison)

    if install:
        for to in (GAME, PACKAGE):
            if not os.path.isdir(os.path.dirname(to)):
                continue
            os.makedirs(to, exist_ok=True)
            shutil.copyfile(finished, os.path.join(to, target_name))
            print('deployed: %s' % os.path.join(to, target_name))


def accept_folder(folder, size, install, no_colours, no_seam, mode):
    """Takes every image in the folder and derives the target from the file name.

    It is enough that the name contains base_1, base_12 and the like - whether
    the file is called base_1.png, base_1_v2.png or base_1 from chatgpt.png.
    """
    if not os.path.isdir(folder):
        raise SystemExit('the folder %s does not exist' % folder)
    files = sorted(f for f in os.listdir(folder)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')))
    if not files:
        raise SystemExit('there are no images in the folder %s' % folder)

    for f in files:
        m = re.search(r'base_(\d+)', f, re.I)
        if not m:
            print('skipping %s - the name does not say which texture it replaces' % f)
            continue
        target = 'base_%s.png' % m.group(1)
        print('')
        print('=== %s -> %s ===' % (f, target))
        accept(os.path.join(folder, f), target, size, install, no_colours, no_seam, mode)


def uninstall(name):
    """Puts a texture back to the one from upscale_terrain.py, or all the way to the archive."""
    source = os.path.join(ROOT, '_research', '_upscale_terrain', 'base')
    names = [name] if name else sorted(
        x for x in os.listdir(GAME) if x.endswith('.png')) if os.path.isdir(GAME) else []
    for j in names:
        replacement = os.path.join(source, j)
        for to in (GAME, PACKAGE):
            target = os.path.join(to, j)
            if not os.path.exists(target):
                continue
            if os.path.exists(replacement):
                shutil.copyfile(replacement, target)
                print('put back to the enlarged original: %s' % target)
            else:
                os.remove(target)
                print('removed, the game takes the archive: %s' % target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', metavar='FOLDER', nargs='?', const=WORK)
    ap.add_argument('--import', dest='input_file', metavar='FILE')
    ap.add_argument('--import-dir', dest='input_folder', metavar='FOLDER',
                    nargs='?', const=NEW,
                    help='take in every image in the folder, the target comes from the '
                         'name (without a path _repaint\\new is used)')
    ap.add_argument('--target', metavar='base_N.png')
    ap.add_argument('--size', type=int, default=TARGET_SIZE)
    ap.add_argument('--mode', choices=('detail', 'replace'), default='detail',
                    help='detail = structure from the original and grain from the model '
                         '(the default); replace = use the image from the model whole')
    ap.add_argument('--no-colours', action='store_true',
                    help='do not match the colours to the original')
    ap.add_argument('--no-seam', action='store_true',
                    help='do not bother with tiling')
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--uninstall', metavar='base_N.png', nargs='?', const='')
    args = ap.parse_args()

    if args.export:
        export(args.export)
    elif args.input_folder:
        accept_folder(args.input_folder, args.size, args.install,
                      args.no_colours, args.no_seam, args.mode)
    elif args.input_file:
        if not args.target:
            raise SystemExit('--target is missing, that is which texture gets replaced')
        accept(args.input_file, args.target, args.size, args.install,
               args.no_colours, args.no_seam, args.mode)
    elif args.uninstall is not None:
        uninstall(args.uninstall or None)
    else:
        raise SystemExit('give --export, --import, --import-dir or --uninstall')


if __name__ == '__main__':
    main()
