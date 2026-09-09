"""Small patches to soa.exe: the window, and letting the log be read.

Each patch is found by a unique signature, never by a hardcoded offset, so a
different build is left alone. They are applied and reverted in groups and a
round trip gives a byte-identical file. A `.orig` copy is kept next to the exe
the first time anything is written.

**The window** hangs on one byte of the application object, the flag at +0xC5,
written once and unconditionally at 0x6269B8. Right before CreateWindowExA
(0x628251):

    006281E5  cmp byte ptr [ebp+0xC5], 0
    006281ED  mov eax, 0x80000000      ; WS_POPUP
    006281F2  mov ecx, 0x00040008      ; WS_EX_APPWINDOW | WS_EX_TOPMOST
    ...
    0062820E  mov eax, 0x00CF0000      ; WS_OVERLAPPEDWINDOW  <- a normal window
    00628213  mov ecx, 0x00040000      ; WS_EX_APPWINDOW

With the flag at zero the game creates a window with a title bar and a
resizable frame, because the other member the branch tests, +0x80, is
initialised to zero anyway.

**Minimising on focus loss** is a group of its own, because it is not about the
window at all - the game does it in full screen too, and there it is what drops
the game into the taskbar the moment anything else is clicked. The message
handler at 0x628520 starts with:

    0062852A  cmp ebp, 8               ; WM_KILLFOCUS
    00628530  jne 0x62853F
    00628536  push 6                   ; SW_MINIMIZE
    00628539  call ShowWindow

That one is not guarded by the window flag at all - the game minimises itself
whenever it loses focus, in either mode. Turning the `jne` into `jmp` skips it.

That is not the only place, though. The deactivation branch of the same window
procedure does it a second time, and this one is the full screen path:

    00628638  call SetWindowLongA      ; drops the window out of the way
    00628641  cmp byte ptr [esi+0xC5], bl
    00628647  je 0x628E70              ; in a window: done
    0062864D  push 6                   ; SW_MINIMIZE
    00628654  call ShowWindow

`0F 84` (`je`) becomes `90 E9` - a `nop` and an unconditional `jmp`, which ends
on the same byte and so lands on the same target. Without this one the game
still drops into the taskbar in full screen the moment anything else is
clicked.

**The size of the window** cannot be fixed this way. The game only resizes it in
the full screen path (0x6282C5), and the rectangle it applies there comes from
`MonitorFromWindow` + `GetMonitorInfo` a few lines earlier - the whole monitor.
Letting that block run in a window was tried and it made the window cover the
screen.

**The three videos at startup** - the Silver Style logo, the publisher logo
and the intro - are put on a playlist one after another at 0x6D1D77. Each one
builds a tsString with the file name and hands it to 0x5198D0:

    006D1D9F  push 0x8676F0            ; SSE.bik
    006D1DA6  call 0x4027B0            ; the string
    006D1DAD  call 0x5198D0            ; add it to the list
    ... the same again for s_s_logo.bik and Game_Intro.bik
    006D1E28  push esi                 ; and play whatever is on the list

Jumping straight from the first of those to 0x6D1E28 leaves the list empty and
the game goes to the menu. The list object in `esi` is built before the jump
and each block cleans its own stack, so nothing is left behind. Five bytes
become `E9 AC 00 00 00`; the rest of the block is simply never reached.

**The log** is opened for writing with no sharing at all, so nothing can read it
while the game runs:

    00651DC4  push 0                   ; hTemplateFile
    00651DC6  push 0x80                ; FILE_ATTRIBUTE_NORMAL
    00651DCB  push 2                   ; CREATE_ALWAYS
    00651DCD  push 0                   ; security
    00651DCF  push 0                   ; dwShareMode = 0   <- nobody may open it
    00651DD1  push 0x40000000          ; GENERIC_WRITE
    00651DD7  call CreateFileA

Pushing 1 (FILE_SHARE_READ) instead lets a reader follow tracefile.log while the
game writes it, which is what the console window in the launcher does. The game
itself does not care - it only ever writes.

Usage:
    python patch_exe.py                   what the exe currently does
    python patch_exe.py --windowed        a normal window
    python patch_exe.py --fullscreen      back to the original window
    python patch_exe.py --keep-focus      do not minimise when focus is lost
    python patch_exe.py --minimise        back to the original
    python patch_exe.py --no-intro        skip the logos and the intro video
    python patch_exe.py --intro          play them again
    python patch_exe.py --share-log       let the log be read while it is written
    python patch_exe.py --lock-log        back to the original
    python patch_exe.py --exe <path>      a different copy of the game
"""
import argparse
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DEFAULT_EXE = os.path.join(ROOT, '_patched', 'soa.exe')


def h(text):
    return bytes.fromhex(text)


# group, name, anchor (unique, never written to), original bytes, patched bytes
PATCHES = [
    ('window', 'window shape',
     h('8D859C000000' 'C685C5000000'), h('01'), h('00')),
    ('focus', 'no minimising on focus loss',
     h('83FD08' '57' '8BF1'), h('75'), h('EB')),
    ('focus', 'no minimising on deactivation (full screen)',
     h('6AF0' '52' 'FF156C627B00' '389EC5000000'), h('0F84'), h('90E9')),
    ('intro', 'no logos and no intro video at startup',
     h('C700F8867C00' '895814' '895818' 'A3FC5A8700' '8BF0' 'EB02' '33F6'),
     h('8A44241383'), h('E9AC000000')),
    ('log', 'the log can be read while the game writes it',
     h('6880000000' '6A02' '6A00'), h('6A00'), h('6A01')),
]


# The character set, which is a patch of a different shape and cannot go in the
# table above.
#
# The game builds its font with CreateFontA and passes fdwCharSet = 1,
# DEFAULT_CHARSET, which follows the machine's locale. On an English Windows
# that is code page 1252 and Czech loses its diacritics; on a Czech one the
# same game would show them. 238 is EASTEUROPE_CHARSET and asks for them
# whatever the machine is set to.
#
# There are ten of these - one Arial and nine sizes of Tahoma - and they share
# their surroundings byte for byte, so no anchor can pick out one of them. The
# safety check is the count instead: ten sites, or the file is not the build
# this was written for. The pattern is `push 7` (OutputPrecision) followed by
# the charset push, which is the only place those two meet.
#
# Because the bitmap font is generated from the Windows font at run time -
# bmfont.cpp sits beside "Arial" in the string pool - the change reaches every
# line the game draws, not only the ones drawn through GDI.
CHARSET_ANCHOR = h('6A07')          # push 7
CHARSET_SITES = 10
DEFAULT_CHARSET = 0x01
EASTEUROPE_CHARSET = 0xEE


def charset_sites(data):
    """Offsets of the charset byte of every CreateFontA call."""
    out = []
    start = 0
    while True:
        i = data.find(CHARSET_ANCHOR, start)
        if i < 0:
            break
        start = i + 1
        p = i + len(CHARSET_ANCHOR)
        if data[p:p + 1] == h('6A') and data[p + 1] in (DEFAULT_CHARSET, EASTEUROPE_CHARSET):
            out.append(p + 1)
    return out


def set_charset(data, value):
    """All ten of them, or nothing. Returns how many were changed."""
    sites = charset_sites(data)
    if len(sites) != CHARSET_SITES:
        raise SystemExit('expected %d font character sets, found %d - a different build?'
                         % (CHARSET_SITES, len(sites)))
    changed = 0
    for at in sites:
        if data[at] != value:
            data[at] = value
            changed += 1
    return changed


def locate(data, anchor, a, b):
    """Offset of the patched bytes, or None when the anchor is not unique."""
    hits = []
    start = 0
    while True:
        i = data.find(anchor, start)
        if i < 0:
            break
        start = i + 1
        p = i + len(anchor)
        if data[p:p + len(a)] in (a, b):
            hits.append(p)
    return hits[0] if len(hits) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', default=DEFAULT_EXE)
    ap.add_argument('--windowed', action='store_true')
    ap.add_argument('--fullscreen', action='store_true')
    ap.add_argument('--no-intro', action='store_true')
    ap.add_argument('--intro', action='store_true')
    ap.add_argument('--keep-focus', action='store_true')
    ap.add_argument('--minimise', action='store_true')
    ap.add_argument('--share-log', action='store_true')
    ap.add_argument('--lock-log', action='store_true')
    ap.add_argument('--east-europe', action='store_true',
                    help='ask Windows for the central European characters, so a '
                         'Czech or Polish translation keeps its diacritics')
    ap.add_argument('--default-charset', action='store_true',
                    help='back to whatever the machine is set to')
    args = ap.parse_args()

    if not os.path.exists(args.exe):
        raise SystemExit('%s does not exist' % args.exe)
    data = bytearray(open(args.exe, 'rb').read())

    found = []
    for group, name, anchor, original, patched in PATCHES:
        pos = locate(data, anchor, original, patched)
        if pos is None:
            raise SystemExit('%s: signature "%s" not found - a different build?'
                             % (args.exe, name))
        found.append((group, name, pos, original, patched))

    sites = charset_sites(data)
    print('%s' % args.exe)
    if sites:
        now = 'east europe' if data[sites[0]] == EASTEUROPE_CHARSET else 'from the machine'
        print('  %d sites   %-8s %-44s %s'
              % (len(sites), 'charset', 'the character set the font is asked for', now))
    for group, name, pos, original, patched in found:
        state = 'patched' if data[pos:pos + len(patched)] == patched else 'original'
        print('  0x%06X  %-8s %-44s %s' % (pos, group, name, state))

    wanted = {}
    if args.windowed:
        wanted['window'] = True
    if args.fullscreen:
        wanted['window'] = False
    if args.no_intro:
        wanted['intro'] = True
    if args.intro:
        wanted['intro'] = False
    if args.keep_focus:
        wanted['focus'] = True
    if args.minimise:
        wanted['focus'] = False
    if args.share_log:
        wanted['log'] = True
    if args.lock_log:
        wanted['log'] = False
    charset = None
    if args.east_europe:
        charset = EASTEUROPE_CHARSET
    if args.default_charset:
        charset = DEFAULT_CHARSET
    if not wanted and charset is None:
        return

    backup = args.exe + '.orig'
    changed = 0
    if charset is not None:
        if not os.path.exists(backup):
            shutil.copyfile(args.exe, backup)
            print('  backup: %s' % backup)
        n = set_charset(data, charset)
        if n:
            print('  charset: %d of %d sites set to %s' % (
                n, CHARSET_SITES,
                'east europe' if charset == EASTEUROPE_CHARSET else 'the machine default'))
            changed += n
    for group, name, pos, original, patched in found:
        if group not in wanted:
            continue
        want = patched if wanted[group] else original
        if data[pos:pos + len(want)] == want:
            continue
        if not os.path.exists(backup):
            shutil.copyfile(args.exe, backup)
            print('  backup: %s' % backup)
        data[pos:pos + len(want)] = want
        changed += 1

    if not changed:
        print('  nothing to do')
        return
    with open(args.exe, 'wb') as f:
        f.write(data)
    print('  %d patch(es) rewritten' % changed)


if __name__ == '__main__':
    main()
