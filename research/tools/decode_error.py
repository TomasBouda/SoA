"""Translates the error codes of the game into something readable.

The game pours "Error: ASSERT_HRESULT(0x...)" messages into tracefile.log and
can end with a non-zero exit code itself. All of those codes are HRESULTs and
fall apart into three pieces:

    1  000 0000 0000 0111   0000 0000 0000 0010
    ^  ^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^
    |  facility (11 bits)   error code (16 bits)
    error yes/no

The facility says whose error it is:

    0x007  Win32. The low 16 bits are the ordinary Windows error number, so the
           system itself can translate it through FormatMessage.
    0x876  DirectDraw and Direct3D. The low 16 bits are the DECIMAL ordinal
           number from the header - 450 is DDERR_SURFACELOST, 255
           DDERR_NOTFOUND. This conversion is why the codes look nonsensical:
           0x887601C2 does not start with 450 but with 0x1C2, which is 450 only
           after the conversion.
    0x000  Generic COM codes (E_FAIL, E_OUTOFMEMORY), the system knows those too.

Usage:
    python decode_error.py 0x887601C2 0x80070002
        Translates the codes from the command line.

    python decode_error.py --log ..\\..\\_patched\\tracefile.log
        Goes through the log, finds every ASSERT_HRESULT and prints them
        together with the number of occurrences and the line where each first
        appeared.

The table of DirectDraw codes is copied from the numbering of the DirectX 7
headers. Whatever is not in it is marked as an unknown number instead of the
script inventing a meaning.
"""
import argparse
import ctypes
import os
import re
import sys

# MAKE_DDHRESULT(n) = 0x88760000 | n, where n is the decimal number from ddraw.h
DDERR = {
    5: 'DDERR_ALREADYINITIALIZED', 10: 'DDERR_CANNOTATTACHSURFACE',
    20: 'DDERR_CANNOTDETACHSURFACE', 40: 'DDERR_CURRENTLYNOTAVAIL',
    55: 'DDERR_EXCEPTION', 90: 'DDERR_HEIGHTALIGN',
    95: 'DDERR_INCOMPATIBLEPRIMARY', 100: 'DDERR_INVALIDCAPS',
    110: 'DDERR_INVALIDCLIPLIST', 120: 'DDERR_INVALIDMODE',
    130: 'DDERR_INVALIDOBJECT', 145: 'DDERR_INVALIDPIXELFORMAT',
    150: 'DDERR_INVALIDRECT', 160: 'DDERR_LOCKEDSURFACES',
    170: 'DDERR_NO3D', 180: 'DDERR_NOALPHAHW',
    181: 'DDERR_NOSTEREOHARDWARE', 182: 'DDERR_NOSURFACELEFT',
    205: 'DDERR_NOCLIPLIST', 210: 'DDERR_NOCOLORCONVHW',
    212: 'DDERR_NOCOOPERATIVELEVELSET', 215: 'DDERR_NOCOLORKEY',
    220: 'DDERR_NOCOLORKEYHW', 222: 'DDERR_NODIRECTDRAWSUPPORT',
    225: 'DDERR_NOEXCLUSIVEMODE', 230: 'DDERR_NOFLIPHW', 240: 'DDERR_NOGDI',
    250: 'DDERR_NOMIRRORHW', 255: 'DDERR_NOTFOUND', 260: 'DDERR_NOOVERLAYHW',
    270: 'DDERR_OVERLAPPINGRECTS', 280: 'DDERR_NORASTEROPHW',
    290: 'DDERR_NOROTATIONHW', 310: 'DDERR_NOSTRETCHHW',
    316: 'DDERR_NOT4BITCOLOR', 317: 'DDERR_NOT4BITCOLORINDEX',
    320: 'DDERR_NOT8BITCOLOR', 330: 'DDERR_NOTEXTUREHW',
    335: 'DDERR_NOVSYNCHW', 340: 'DDERR_NOZBUFFERHW', 350: 'DDERR_NOZOVERLAYHW',
    360: 'DDERR_OUTOFCAPS', 380: 'DDERR_OUTOFVIDEOMEMORY',
    382: 'DDERR_OVERLAYCANTCLIP', 384: 'DDERR_OVERLAYCOLORKEYONLYONEACTIVE',
    387: 'DDERR_PALETTEBUSY', 400: 'DDERR_COLORKEYNOTSET',
    410: 'DDERR_SURFACEALREADYATTACHED', 420: 'DDERR_SURFACEALREADYDEPENDENT',
    430: 'DDERR_SURFACEBUSY', 435: 'DDERR_CANTLOCKSURFACE',
    440: 'DDERR_SURFACEISOBSCURED', 450: 'DDERR_SURFACELOST',
    460: 'DDERR_SURFACENOTATTACHED', 470: 'DDERR_TOOBIGHEIGHT',
    480: 'DDERR_TOOBIGSIZE', 490: 'DDERR_TOOBIGWIDTH',
    510: 'DDERR_UNSUPPORTEDFORMAT', 520: 'DDERR_UNSUPPORTEDMASK',
    521: 'DDERR_INVALIDSTREAM', 537: 'DDERR_VERTICALBLANKINPROGRESS',
    540: 'DDERR_WASSTILLDRAWING', 542: 'DDERR_DDSCAPSCOMPLEXREQUIRED',
    560: 'DDERR_XALIGN', 561: 'DDERR_INVALIDDIRECTDRAWGUID',
    562: 'DDERR_DIRECTDRAWALREADYCREATED', 563: 'DDERR_NODIRECTDRAWHW',
    564: 'DDERR_PRIMARYSURFACEALREADYEXISTS', 565: 'DDERR_NOEMULATION',
    566: 'DDERR_REGIONTOOSMALL', 567: 'DDERR_CLIPPERISUSINGCLIPLIST',
    568: 'DDERR_NOCLIPPERATTACHED', 569: 'DDERR_NOHWND',
    570: 'DDERR_HWNDSUBCLASSED', 571: 'DDERR_HWNDALREADYSET',
    572: 'DDERR_NOPALETTEATTACHED', 573: 'DDERR_NOPALETTEHW',
    574: 'DDERR_BLTFASTCANTCLIP', 575: 'DDERR_NOBLTHW', 576: 'DDERR_NODDROPSHW',
    577: 'DDERR_OVERLAYNOTVISIBLE', 578: 'DDERR_NOOVERLAYDEST',
    579: 'DDERR_INVALIDPOSITION', 580: 'DDERR_NOTAOVERLAYSURFACE',
    581: 'DDERR_EXCLUSIVEMODEALREADYSET', 582: 'DDERR_NOTFLIPPABLE',
    583: 'DDERR_CANTDUPLICATE', 584: 'DDERR_NOTLOCKED',
    585: 'DDERR_CANTCREATEDC', 586: 'DDERR_NODC', 587: 'DDERR_WRONGMODE',
    588: 'DDERR_IMPLICITLYCREATED', 589: 'DDERR_NOTPALETTIZED',
    590: 'DDERR_UNSUPPORTEDMODE', 591: 'DDERR_NOMIPMAPHW',
    592: 'DDERR_INVALIDSURFACETYPE', 600: 'DDERR_NOOPTIMIZEHW',
    601: 'DDERR_NOTLOADED', 602: 'DDERR_NOFOCUSWINDOW',
    603: 'DDERR_NOTONMIPMAPCHAIN', 620: 'DDERR_DCALREADYCREATED',
    630: 'DDERR_NONONLOCALVIDMEM', 640: 'DDERR_CANTPAGELOCK',
    660: 'DDERR_CANTPAGEUNLOCK', 680: 'DDERR_NOTPAGELOCKED',
    690: 'DDERR_MOREDATA', 691: 'DDERR_EXPIRED', 692: 'DDERR_TESTFINISHED',
    693: 'DDERR_NEWMODE', 694: 'DDERR_D3DNOTINITIALIZED',
    695: 'DDERR_VIDEONOTACTIVE', 696: 'DDERR_NOMONITORINFORMATION',
    697: 'DDERR_NODRIVERSUPPORT', 699: 'DDERR_DEVICEDOESNTOWNSURFACE',
    # Direct3D 7 shares the same facility
    700: 'D3DERR_BADMAJORVERSION', 701: 'D3DERR_BADMINORVERSION',
    702: 'D3DERR_INVALIDCURRENTVIEWPORT', 703: 'D3DERR_INVALIDPRIMITIVETYPE',
    704: 'D3DERR_INVALIDVERTEXTYPE', 705: 'D3DERR_TEXTURE_BADSIZE',
    706: 'D3DERR_INVALIDRAMPTEXTURE', 707: 'D3DERR_MATERIAL_REVISION',
    708: 'D3DERR_INVALIDPALETTE', 709: 'D3DERR_ZBUFF_NEEDS_SYSTEMMEMORY',
    710: 'D3DERR_ZBUFF_NEEDS_VIDEOMEMORY', 711: 'D3DERR_SURFACENOTINVIDMEM',
}

# Codes we have already seen with this game, together with what caused them
SEEN = {
    0x887601C2: 'crash on first start, four render-to-texture methods in a row',
    0x887600FF: 'render-to-texture, the requested resource does not exist',
    0x80070002: 'the game was started with the wrong working directory and cannot find its .ubn archives',
    0x80070003: "the message Open file '' failed",
    0x80070005: "the message Open file '.' failed",
    0x80004005: 'a missing sound',
}


def system_message(code):
    """The text from Windows. It knows Win32 and the generic COM codes."""
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.FormatMessageW(
        0x1000, None, ctypes.c_uint(code), 0, buf, 1024, None)   # FROM_SYSTEM
    return buf.value.strip() if n else None


def decode(code):
    """Returns (name, description, facility)."""
    failed = bool(code & 0x80000000)
    # The documentation gives the facility 11 bits, but MAKE_DDHRESULT uses
    # 0x876, which does not fit into them and spills over into bit 27. That is
    # why 12 bits are masked: otherwise 0x8876xxxx yields 0x076 instead of
    # 0x876 and the table is never found.
    facility = (code >> 16) & 0xFFF
    number = code & 0xFFFF

    if not failed:
        return None, 'not an error, success with the value 0x%X' % code, facility

    if facility == 0x876:
        name = DDERR.get(number)
        if name:
            return name, 'DirectDraw/Direct3D, number %d' % number, facility
        return None, ('DirectDraw/Direct3D, number %d - not in the table' % number), facility

    text = system_message(code)
    if facility == 0x007:
        return None, text or ('Win32 error %d' % number), facility
    return None, text or 'facility 0x%03X, number %d' % (facility, number), facility


def show(code):
    name, description, facility = decode(code)
    headline = name or description
    print('0x%08X  %s' % (code, headline))
    if name:
        print('            %s' % description)
    print('            facility 0x%03X (%s)' % (
        facility, {0x007: 'Win32', 0x876: 'DirectDraw/Direct3D', 0x000: 'generic COM'}
        .get(facility, 'other')))
    if code in SEEN:
        print('            seen with this game: %s' % SEEN[code])
    print()


def scan_log(path):
    if not os.path.exists(path):
        raise SystemExit('the log %s does not exist' % path)
    found = {}
    with open(path, 'r', encoding='latin1', errors='replace') as f:
        for i, line in enumerate(f, 1):
            for m in re.finditer(r'ASSERT_HRESULT\(0x([0-9A-Fa-f]+)\)', line):
                code = int(m.group(1), 16)
                record = found.setdefault(code, [0, i, line.strip()])
                record[0] += 1
    if not found:
        print('there is no ASSERT_HRESULT in the log %s' % path)
        return
    print('log %s, distinct codes: %d' % (path, len(found)))
    print()
    for code, (count, line_number, text) in sorted(found.items(),
                                                   key=lambda x: -x[1][0]):
        print('%dx, first on line %d:' % (count, line_number))
        print('    %s' % text[:120])
        show(code)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('codes', nargs='*', help='codes, for example 0x887601C2 or 887601C2')
    ap.add_argument('--log', metavar='FILE', help='go through tracefile.log')
    ap.add_argument('--table', action='store_true',
                    help='print what is already known about the codes of this game')
    args = ap.parse_args()

    if args.table:
        for code in sorted(SEEN):
            show(code)
        return
    if args.log:
        scan_log(args.log)
        return
    if not args.codes:
        raise SystemExit('give a code, --log or --table')
    for text in args.codes:
        try:
            code = int(text, 16) if not text.isdigit() or len(text) == 8 else int(text)
        except ValueError:
            print('%s: cannot parse that' % text)
            continue
        show(code & 0xFFFFFFFF)


if __name__ == '__main__':
    main()
