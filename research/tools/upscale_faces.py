"""Enlarge the portraits, which are the worst-served pictures in the game.

Every face in Soldiers of Anarchy is about 36 by 50 pixels. They live seven to
a row on 256 by 256 sheets - `Faces.png` and `Faces2.png` for a mission,
`faces01` to `faces05` for the infirmary - and on a modern screen the engine
blows them up by four or five times, which is why a portrait is a mosaic.

An earlier attempt to enlarge the interface concluded that the extra size is
thrown away (see upscale.md). Reading the loader says otherwise: at `0x621313`
the surface is built from the size of the picture that was **loaded**, not from
the size the resource declares, and a mismatch only writes
`LoadPNG: Warning: surface size don't match resource size` into the log. So the
larger sheet does survive as far as the texture. Whether it survives as far as
the screen depends on how the source rectangle is taken, and the only honest way
to find out is to look at a portrait in the game.

    python upscale_faces.py --preview faces.png    what it would look like
    python upscale_faces.py --apply                write them into _patched
    python upscale_faces.py --apply --frames       the same, with a frame per face
    python upscale_faces.py --off                  take them away again

Point `--game` at a built package's Game folder to put them straight into it
and skip the rebuild, which is what makes a before-and-after comparison quick:
the same save, two runs, the seven files there and then not there.

Real-ESRGAN on the GPU by default; `--lanczos` for plain resampling, which is
the fair comparison - if the model is only inventing skin texture, the two look
much the same at the size a portrait is actually shown.

Written into `_patched`, not into the built package: every build wipes the
output folder and copies it again from there.
"""
import argparse
import io
import os
import shutil
import sys
import zipfile

from PIL import Image, ImageDraw

SOURCE = os.environ.get('SOA_SOURCE', r'F:\Games\SoA\_patched')

# Every sheet of faces the game has. The mission ones are the portraits down
# the side of the screen; the infirmary ones are the same people, larger, in
# the bunker.
SHEETS = (
    'gui/GUI_Mission/Faces/Faces.png',
    'gui/GUI_Mission/Faces/Faces2.png',
    'gui/GUI_Bunker/Lazarettpanel/faces01.png',
    'gui/GUI_Bunker/Lazarettpanel/faces02.png',
    'gui/GUI_Bunker/Lazarettpanel/faces03.png',
    'gui/GUI_Bunker/Lazarettpanel/faces04.png',
    'gui/GUI_Bunker/Lazarettpanel/faces05.png',
)


def archive(game):
    return zipfile.ZipFile(os.path.join(game, 'gui.ubn'))


def original(game, name):
    with archive(game) as z:
        return Image.open(io.BytesIO(z.read(name))).convert('RGBA')


# The real geometry, read out of the game rather than guessed at. Mission.gui
# declares RES_MISSION_FACE1..55 and Bunker.gui RES_BUNKER_FACE1.., and every
# one of them is the same: a 32 by 48 cell, a pitch of 33 by 49, the first at
# (1, 1). Seven across and five down fills a 256 sheet with 35 faces, and the
# second sheet carries the remainder, which is why it is half empty.
#
# The first version of this drew a grid of width/7 by height/5 - 36.6 by 51.2 -
# and the frames walked away from the faces a pixel at a time, which is exactly
# what it looked like.
FACE_W, FACE_H = 32, 48
PITCH_X, PITCH_Y = 33, 49
ORIGIN_X, ORIGIN_Y = 1, 1
ACROSS, DOWN = 7, 5


def edge_filled(image, rounds=6):
    """Push the colour of the head outwards into the transparent surround.

    The model is given RGB only, and `convert('RGB')` lays the transparent
    pixels onto black - so every head goes into the model wearing a black
    halo, and the model duly sharpens it into a dark rim. Spreading the edge
    colour outwards first gives it nothing to sharpen. The alpha itself is
    untouched and put back afterwards.
    """
    rgb = image.convert('RGB').load()
    alpha = image.getchannel('A').load()
    w, h = image.size
    solid = [[alpha[x, y] > 8 for y in range(h)] for x in range(w)]
    out = Image.new('RGB', image.size)
    put = out.load()
    for x in range(w):
        for y in range(h):
            put[x, y] = rgb[x, y]
    for _ in range(rounds):
        grew = []
        for x in range(w):
            for y in range(h):
                if solid[x][y]:
                    continue
                near = [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if 0 <= x + dx < w and 0 <= y + dy < h and solid[x + dx][y + dy]]
                if not near:
                    continue
                r = g = b = 0
                for nx, ny in near:
                    c = put[nx, ny]
                    r += c[0]; g += c[1]; b += c[2]
                n = len(near)
                grew.append((x, y, (r // n, g // n, b // n)))
        if not grew:
            break
        for x, y, c in grew:
            put[x, y] = c
            solid[x][y] = True
    return out


def through_model(image, scale, model):
    """One RGBA picture through Real-ESRGAN, alpha carried round the outside."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import numpy
    import esrgan

    grown = esrgan.upscale_rgb(numpy.array(edge_filled(image)), model)
    out = Image.fromarray(grown)
    want = (image.width * scale, image.height * scale)
    if out.size != want:
        out = out.resize(want, Image.LANCZOS)
    out = out.convert('RGBA')
    out.putalpha(image.getchannel('A').resize(want, Image.LANCZOS))
    return out


def bigger(image, scale, how, per_face=True):
    """The sheet enlarged.

    Face by face rather than all at once, which matters more than it sounds.
    A sheet is 35 heads with transparent gutters between them, and a model run
    over the whole thing sees a neighbour's ear as context for this one's jaw
    and smears the cell edges. Each face is taken out on its own, with the
    gutter filled in around it, and put back where it came from.
    """
    if how == 'lanczos':
        return image.resize((image.width * scale, image.height * scale), Image.LANCZOS)
    if not per_face:
        return through_model(image, scale, how)

    # Start from the whole sheet and lay the faces over it, rather than
    # building on nothing: 1151 opaque pixels of Faces.png sit outside every
    # declared cell - the wide helmeted figure in the bottom right corner
    # reaches to x 254 where the grid stops at 231 - and a blank canvas simply
    # loses them. That is how the last soldier came out sliced off.
    out = through_model(image, scale, how)
    for row in range(DOWN):
        for col in range(ACROSS):
            l = ORIGIN_X + col * PITCH_X
            t = ORIGIN_Y + row * PITCH_Y
            cell = image.crop((l, t, l + FACE_W, t + FACE_H))
            if cell.getchannel('A').getbbox() is None:
                continue                      # an empty slot on the second sheet
            out.paste(through_model(cell, scale, how), (l * scale, t * scale))
    return out


def framed(image, scale):
    """The same sheet with a frame drawn round every face, where the game
    believes the face to be.

    This answers the question that has to be answered first, and answers it
    from a single screenshot: does the engine take its source rectangle in
    proportions or in pixels of the old 256 space?

    The frames are drawn at the true rectangles multiplied by the scale. If the
    engine works in proportions, every portrait in the game comes up neatly
    inside its frame. If it works in pixels, it reads the same small rectangle
    out of a sheet twice the size and shows the top-left quarter of a face
    magnified, with a piece of frame across it. Either way it is unmistakable.
    """
    out = image.copy()
    draw = ImageDraw.Draw(out)
    colours = [(255, 60, 60, 255), (60, 255, 90, 255), (80, 140, 255, 255),
               (255, 220, 40, 255), (255, 80, 255, 255)]
    for row in range(DOWN):
        for col in range(ACROSS):
            l = (ORIGIN_X + col * PITCH_X) * scale
            t = (ORIGIN_Y + row * PITCH_Y) * scale
            draw.rectangle((l, t, l + FACE_W * scale - 1, t + FACE_H * scale - 1),
                           outline=colours[row % len(colours)], width=2)
    return out


def on_a_board(image):
    """Alpha shows nothing on its own, so the heads go on a flat ground."""
    board = Image.new('RGBA', image.size, (40, 40, 46, 255))
    return Image.alpha_composite(board, image)


def preview(path, game, scale, how):
    """One row of faces as the game has them and as they would be, both blown
    up the way the screen blows them up - which is the only comparison that
    means anything."""
    sheet = original(game, SHEETS[0])
    grown = bigger(sheet, scale, how)
    # The first four heads. A face is a seventh of the sheet across and a fifth
    # of it down; the exact rectangles are the game's business, this is only to
    # look at.
    fw, fh = sheet.width // 7, sheet.height // 5
    faces = 4
    cell = 220
    out = Image.new('RGBA', (cell * faces, cell * 2 + 30), (24, 26, 32, 255))
    for i in range(faces):
        a = on_a_board(sheet.crop((i * fw, 0, (i + 1) * fw, fh)))
        b = on_a_board(grown.crop((i * fw * scale, 0, (i + 1) * fw * scale, fh * scale)))
        out.paste(a.resize((cell, cell), Image.NEAREST), (i * cell, 0))
        out.paste(b.resize((cell, cell), Image.LANCZOS), (i * cell, cell + 30))
    out.convert('RGB').save(path)
    print('wrote %s - top row as the game has it, bottom row %dx by %s'
          % (path, scale, how))


def apply(game, scale, how, frames=False, per_face=True):
    with archive(game) as z:
        for name in SHEETS:
            target = os.path.join(game, *name.split('/'))
            folder = os.path.dirname(target)
            if not os.path.isdir(folder):
                os.makedirs(folder)
            sheet = Image.open(io.BytesIO(z.read(name))).convert('RGBA')
            grown = bigger(sheet, scale, how, per_face)
            if frames:
                grown = framed(grown, scale)
            grown.save(target)
            print('   %s  %dx%d -> %dx%d'
                  % (name, sheet.width, sheet.height,
                     sheet.width * scale, sheet.height * scale))
    print('%d sheets written under %s' % (len(SHEETS), os.path.join(game, 'gui')))
    print('build the package for them to reach it')


def off(game):
    removed = 0
    for name in SHEETS:
        path = os.path.join(game, *name.split('/'))
        if os.path.exists(path):
            os.remove(path)
            removed += 1
        folder = os.path.dirname(path)
        if os.path.isdir(folder) and not os.listdir(folder):
            os.rmdir(folder)
    print('removed %d sheets; the game is back on the archive for the faces' % removed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=SOURCE, help='the package source')
    ap.add_argument('--scale', type=int, default=2, choices=(2, 4))
    ap.add_argument('--lanczos', action='store_true',
                    help='plain resampling instead of the model')
    ap.add_argument('--model', default='anime', choices=('anime', 'photo'),
                    help='anime keeps the shapes of a small stylised picture; '
                         'photo invents detail and deforms the features, which '
                         'is what it was trained to do')
    ap.add_argument('--whole-sheet', action='store_true',
                    help='run the model over the sheet instead of face by face')
    ap.add_argument('--preview', metavar='FILE')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--frames', action='store_true',
                    help='draw a frame round every face - tells from one '
                         'screenshot whether the bigger sheet maps correctly')
    ap.add_argument('--off', action='store_true')
    args = ap.parse_args()
    how = 'lanczos' if args.lanczos else args.model

    if args.off:
        off(args.game)
    elif args.preview:
        preview(args.preview, args.game, args.scale, how)
    elif args.apply:
        apply(args.game, args.scale, how, args.frames, not args.whole_sheet)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
