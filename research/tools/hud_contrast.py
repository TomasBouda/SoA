"""Make the mission interface easier to read, without repacking anything.

The heads-up display of a 2002 game was drawn for a 640 by 480 screen sitting
close to the player. Stretched across a modern monitor its panels go muddy: the
art is dark, the contrast is low, and the small type on the buttons sinks into
the background. The pictures themselves are ordinary PNG files inside
`gui.ubn`, and the engine reads a loose file next to the game in preference to
the archive - proven twice, see architecture.md - so they can be replaced
without touching the archive at all.

    python hud_contrast.py --list                  what would be touched
    python hud_contrast.py --preview before.png    see it before deciding
    python hud_contrast.py --apply                 write the loose files
    python hud_contrast.py --off                   take them away again

Two knobs, both mild by default. `--contrast` pulls the dark and the light
apart around mid grey; `--brightness` lifts the whole thing. The alpha channel
is never touched: it is what gives the panels their shape, and a panel that
changes shape is a panel in the wrong place.

Undoing it is deleting files, which is why this is the safest kind of change
the game takes. Nothing here writes into an archive.
"""
import argparse
import io
import os
import shutil
import zipfile

from PIL import Image

# Written into the package's source, not the built package. Every build wipes
# the output folder and copies it again from here, so loose files put straight
# into the package survive until the next build and then vanish without a word.
# The upscaled terrain and textures live here for the same reason.
SOURCE = os.environ.get('SOA_SOURCE', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_patched'))
GAME = SOURCE

# What counts as the interface of a running mission. The shared panels are in
# because the mission screen borrows them - the inventory lists and the item
# icons are drawn from GUI_Shared.
FOLDERS = ('gui/GUI_Mission/', 'gui/GUI_Shared/')

# The pictures that are not interface and would only be spoiled. Faces are
# photographs of the characters, and the item icons read better as they are.
SKIP = ('Faces/', 'Items/', 'Fade/', 'MiniMap/')


def wanted(name):
    if not name.lower().endswith('.png'):
        return False
    if not any(name.startswith(f) for f in FOLDERS):
        return False
    return not any(s in name for s in SKIP)


def archive(game=GAME):
    return zipfile.ZipFile(os.path.join(game, 'gui.ubn'))


def names(game=GAME):
    with archive(game) as z:
        return sorted(n for n in z.namelist() if wanted(n))


def curve(value, contrast, brightness):
    """One channel, 0 to 255, pulled apart around mid grey and then lifted."""
    x = (value - 128.0) * contrast + 128.0 + brightness
    return 0 if x < 0 else 255 if x > 255 else int(x + 0.5)


def stronger(image, contrast, brightness):
    """The same picture with more contrast, its alpha exactly as it was."""
    image = image.convert('RGBA')
    table = [curve(v, contrast, brightness) for v in range(256)]
    r, g, b, a = image.split()
    r = r.point(table)
    g = g.point(table)
    b = b.point(table)
    return Image.merge('RGBA', (r, g, b, a))


def on_a_board(image):
    """Alpha does not show on its own, so put the picture on a checkerboard."""
    board = Image.new('RGBA', image.size)
    light, dark = (90, 90, 96, 255), (60, 60, 66, 255)
    pixels = board.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            pixels[x, y] = light if ((x // 8) + (y // 8)) % 2 else dark
    return Image.alpha_composite(board, image)


def preview(path, contrast, brightness, game=GAME, which=None):
    """A sheet of before and after, so it can be judged before it is deployed."""
    picked = [n for n in names(game) if which is None or which.lower() in n.lower()]
    if not picked:
        raise SystemExit('nothing matches')
    picked = picked[:6]
    cell = 200
    sheet = Image.new('RGBA', (cell * 2 + 30, cell * len(picked) + 10 * len(picked) + 10),
                      (24, 26, 32, 255))
    with archive(game) as z:
        for row, name in enumerate(picked):
            before = Image.open(io.BytesIO(z.read(name)))
            after = stronger(before, contrast, brightness)
            y = 10 + row * (cell + 10)
            sheet.paste(on_a_board(before).resize((cell, cell)), (10, y))
            sheet.paste(on_a_board(after).resize((cell, cell)), (20 + cell, y))
    sheet.convert('RGB').save(path)
    print('wrote %s - left is the game, right is %s contrast %+d brightness'
          % (path, contrast, brightness))
    for n in picked:
        print('   %s' % n)


def apply(contrast, brightness, game=GAME):
    written = 0
    with archive(game) as z:
        for name in names(game):
            target = os.path.join(game, *name.split('/'))
            folder = os.path.dirname(target)
            if not os.path.isdir(folder):
                os.makedirs(folder)
            stronger(Image.open(io.BytesIO(z.read(name))),
                     contrast, brightness).save(target)
            written += 1
    print('wrote %d loose pictures under %s' % (written, os.path.join(game, 'gui')))
    print('the game reads these in preference to gui.ubn; --off takes them away')
    print('build the package for them to reach it')


def off(game=GAME):
    folder = os.path.join(game, 'gui')
    if not os.path.isdir(folder):
        print('nothing to take away - %s does not exist' % folder)
        return
    shutil.rmtree(folder)
    print('removed %s; the game is back on the archive' % folder)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=GAME,
                    help='where to write - the package source by default, so a '
                         'rebuild keeps it')
    ap.add_argument('--contrast', type=float, default=1.35,
                    help='how far apart to pull dark and light (1.0 changes nothing)')
    ap.add_argument('--brightness', type=int, default=10,
                    help='how much to lift the whole picture, in levels')
    ap.add_argument('--list', action='store_true', help='what would be touched')
    ap.add_argument('--preview', metavar='FILE', help='write a before and after sheet')
    ap.add_argument('--only', help='limit the preview to names containing this')
    ap.add_argument('--apply', action='store_true', help='write the loose pictures')
    ap.add_argument('--off', action='store_true', help='remove them again')
    args = ap.parse_args()

    if args.off:
        off(args.game)
    elif args.list:
        found = names(args.game)
        print('%d pictures would be replaced:' % len(found))
        for n in found:
            print('   %s' % n)
    elif args.preview:
        preview(args.preview, args.contrast, args.brightness, args.game, args.only)
    elif args.apply:
        apply(args.contrast, args.brightness, args.game)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
