"""Draws the inventory icon of the M34 white phosphorus grenade - a
grey-green can with a yellow band and a fuze with its lever, lying at the
angle the game's own grenade icons lie at - into a free corner of
items_4.png, the fourth icon sheet, and writes the sheet out as a loose file
for the game.

The sheets are 256 x 256 with the icons packed by hand, and free room is
scarce: the rectangles of Items.gui cover most of each sheet and what they
do not cover is mostly drawn on anyway (an unused pod on sheet 6, say). The
one hole a 38 x 30 icon fits into without lying inside another record's
rectangle or on another picture is on sheet 4, right of the ammunition box
under the M60: x 201..255, y 118..156. (The first try, sheet 6 at (84, 2),
looked empty and was inside the turret machine gun's 120 x 38 rectangle -
the M34 turned up in the middle of every tank's MG icon.) The icon is drawn
four times the size and shrunk, which is what gives it the soft edges the
originals have.

Usage:
    python m34_icon.py <out.png>            the icon alone, 38 x 30
    python m34_icon.py --sheet <out.png>    items_4.png with the icon in place
"""
import io
import math
import os
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GUI = os.path.join(ROOT, '_patched', 'gui.ubn')
SHEET_NUMBER = 4
SHEET = 'gui/GUI_Shared/Items/items_%d.png' % SHEET_NUMBER
AT = (208, 122)           # where the icon goes on the sheet
SIZE = (38, 30)           # the icon, like the other grenades'
S = 4                     # drawn this many times larger


def icon():
    W, H = SIZE[0] * S, SIZE[1] * S
    # the can, drawn upright on its own canvas and then turned
    cw, ch = 60 * S // 4, 112 * S // 4
    can = Image.new('RGBA', (cw + 40, ch + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(can)
    x0, y0 = 20, 40
    body = (0x8C, 0x99, 0x7E)
    dark = (0x5E, 0x68, 0x53)
    light = (0xB4, 0xBE, 0xA6)
    # the body with a rounded shading: light on the left, dark on the right
    for i in range(cw):
        t = i / (cw - 1)
        shade = 1.0 - 0.55 * abs(t - 0.32) ** 1.3
        c = tuple(int(body[k] * shade + light[k] * 0.25 * max(0, 1 - abs(t - 0.28) * 4)) for k in range(3))
        d.line([(x0 + i, y0), (x0 + i, y0 + ch)], fill=c + (255,))
    # the yellow band with the red letters of a real M34
    band = (y0 + int(ch * 0.30), y0 + int(ch * 0.44))
    for i in range(cw):
        t = i / (cw - 1)
        shade = 1.0 - 0.5 * abs(t - 0.32) ** 1.3
        c = (int(0xE0 * shade), int(0xC0 * shade), int(0x2A * shade))
        d.line([(x0 + i, band[0]), (x0 + i, band[1])], fill=c + (255,))
    d.rectangle([x0 + cw * 0.22, band[0] + (band[1] - band[0]) * 0.35, x0 + cw * 0.72, band[0] + (band[1] - band[0]) * 0.65],
                fill=(0xA0, 0x20, 0x18, 255))
    # the crimp lines top and bottom
    d.rectangle([x0, y0, x0 + cw, y0 + 3 * S // 2], fill=dark + (255,))
    d.rectangle([x0, y0 + ch - 3 * S // 2, x0 + cw, y0 + ch], fill=dark + (255,))
    # the fuze: a short dark neck, the safety lever down the side, the ring
    fx = x0 + cw // 2
    d.rectangle([fx - 6 * S // 4, y0 - 10 * S // 4, fx + 6 * S // 4, y0], fill=(0x3A, 0x3E, 0x36, 255))
    d.rectangle([fx - 3 * S // 4, y0 - 16 * S // 4, fx + 3 * S // 4, y0 - 10 * S // 4], fill=(0x55, 0x5A, 0x50, 255))
    d.line([(fx + 5 * S // 4, y0 - 8 * S // 4), (x0 + cw + 2 * S // 4, y0 + ch * 0.45)], fill=(0x50, 0x55, 0x4A, 255), width=3 * S // 4)
    d.ellipse([fx - 12 * S // 4, y0 - 24 * S // 4, fx - 2 * S // 4, y0 - 14 * S // 4], outline=(0x9A, 0x9A, 0x90, 255), width=S // 2)
    can = can.rotate(-52, resample=Image.BICUBIC, expand=True)
    # onto the icon canvas, centred, with a soft shadow under it like the originals
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    scale = min((W - 2 * S) / can.width, (H - S) / can.height)
    can = can.resize((int(can.width * scale), int(can.height * scale)), Image.LANCZOS)
    shadow = Image.new('RGBA', can.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 110), (0, 0), can.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(2 * S))
    px, py = (W - can.width) // 2, (H - can.height) // 2
    out.alpha_composite(shadow, (px + S, py + S))
    out.alpha_composite(can, (px, py))
    return out.resize(SIZE, Image.LANCZOS)


def sheet_with_icon():
    sheet = Image.open(io.BytesIO(zipfile.ZipFile(GUI).read(SHEET))).convert('RGBA')
    sheet.alpha_composite(icon(), AT)
    return sheet


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == '--sheet':
        sheet_with_icon().save(sys.argv[2])
        print('wrote', sys.argv[2])
    else:
        icon().save(sys.argv[1])
        print('wrote', sys.argv[1])


if __name__ == '__main__':
    main()
