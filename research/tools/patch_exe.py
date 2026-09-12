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

**The camera** cannot get far from the ground: the constructor in Y2KApp.cpp
(0x6DC6E0) sets the height it may fly between to 2 and 30 world units -

    006DC6F5  mov dword ptr [esi+0x5C], 2.0     ; lowest
    006DC70A  mov dword ptr [esi+0x60], 30.0    ; highest
    006DC72C  mov byte ptr [esi+0x70], 1        ; and the clamp is on

- and the clamp (0x6E0720, called from the camera's Tick every frame) is what
stops the mouse wheel. The wheel moves the camera along its view direction
(+0x24..+0x2C), all three axes, and the clamp then puts only z back:

    006E08FA  mov eax, [esi+0x60]              ; z = highest
    006E08FD  mov [edi+8], eax

so x and y keep the step the wheel gave them and the camera slides across the
map at either limit - forward at the bottom, backward at the top. The camera
patch has three parts: the two limits become 1.5 and 150, and both clamp
branches jump into a piece of code in the zero padding at the end of .text
(0x7B45D0) that first pulls x and y back along the view direction by the same
amount it is about to pull z, so the camera stops on the limit instead of
sliding along it. The division by dir.z is guarded against a horizontal view,
which the mission camera never has. Verified live: the wheel goes much
further out, closer in, and stands still at both ends.

**Shift moves the camera faster.** There is no key for it in the game: the
speed of every camera motion is fixed where the motions are set up (0x6DCA1F,
0.025 world units a millisecond for panning) and the input table has no
modifier. The camera applies its motions once a frame in 0x6E05E0, where it
loads the frame time as an integer of milliseconds:

    006E062D  fild qword ptr [esp+0x10]    ; the frame time
    006E0631  mov ebx, [esp+0x20]

The speed patch jumps from there into a few bytes at 0x7B4650 that ask
GetKeyState(VK_SHIFT) - the game reads its keys through Windows messages, so
that answers - and multiply the frame time by five when the key is down. Every
motion the camera makes that frame is five times as long; the acceleration
ramp is not touched, it lives in 0x6DCB10 with a time of its own. Shift is
already the key that queues orders, which is no conflict: that needs a click,
this needs a pan.

**Pause and give orders.** The readme of 1.0 mentions a separate download, a
"patch to allow turn-based play" - pause in single player and issue orders.
It never reached 1.1.2: the pause key (AK_PAUSE, 0x419) puts the mission into
state 0xD, which is the modal MissionBreakPanel, and that panel swallows
everything but the key that closes it. The active pause is built here instead,
in the mission's Tick (0x5E9650), which hands the frame time in `edi` to
everything in turn:

    005E96A4  the landscape          0x6886D0(dt)
    005E9707  the interface          [+0x270]->Tick(dt)
    005E9713  the objects            [+0x250] 0x5A7D80(dt)   <- the simulation
    005E971F  the rockets            [+0x248] 0x6E8BB0(dt)
    005E9738  the weather            [+0x23C]->Tick(dt)
    005E975E  the camera             [+0x238]->Tick(dt)
    005E976A  the minimap            [+0x240]->Tick(dt)
    005E977D  the message list       [+0x27C] 0x6A29C0(dt)
    005E9789  the mission's own      0x5F0DF0(dt), 0x5F1390(dt)

A byte in the padding at the end of .text says whether the game is paused -
and since .text is mapped read-only, the patch also sets IMAGE_SCN_MEM_WRITE
on the section in the PE header, or the first write would be the crash the
first try was. The camera and Shift patches only read their padding.
Where the Tick loads `edi` (0x5E9699) a detour keeps the real time beside
that byte and makes `edi` zero while it is set, so the objects, the rockets,
the weather, the landscape and the mission's timers stand still. The
interface, the camera, the minimap and the message list are given the real
time through detours of their own - and so does the player library inside
the object manager's tick (0x5A7DE3), which is where selection, the context
menu and the path preview live - so the game can still be looked at, scrolled
and clicked: units are selected and ordered as usual, and the orders run when
time resumes. The pause key's single-player branch (0x5EA29D), which
would open the panel, flips the byte instead; the multiplayer branch is left
alone.

**The mailbox.** Two things a right click does are worth calling from
outside: asking the landscape what is under a point of the screen
(0x686A90, with the renderer's own view and projection matrices) and giving
the selected units an order at a world point (0x5DAC80). Neither can be
called from a foreign thread with any reliability - the matrices belong to
the frame - so the mailbox patch lets the game make the call itself: a few
bytes in the padding hold a request (1 = pick, 2 = order, 4 = a thiscall on any object with up to
twelve arguments - which is every order a unit takes, see architecture.md -
3 = the view and projection matrices
out of the Direct3D device, which is where they live), a point, and the
answer, and a detour right after the mission has let the camera render
(0x5E93A1) - the one moment the renderer's matrices are certainly the
camera's; served from the Tick it found nothing - answers whatever request
is there, on the game's thread, once a frame. Nothing in the game writes the
request; tools/ui_inject.py does.

**The M34 grenade.** A sixth thrown weapon, item 150 with its round 151:
the data is mod_m34.py's (Data.set, the texts, the icon, all loose files),
the bytes are m34_patch.py's, which lists every table and switch in the exe
that names the five grenades by number and adds the sixth to each - the
factory, the thrown weapon's constructor, CanUse, the animation event table,
the projectile switch, the two maps behind the icons and the HUD, the
trader's restock and the re-arm chain. The exe patch is useless without the
files, and worse than useless: the trader would make an item with no
settings. The build writes them; the launcher greys the box out when they
are not there.

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
    python patch_exe.py --camera          a camera that zooms further, closer, and stands still at the limits
    python patch_exe.py --stock-camera    back to the original
    python patch_exe.py --fast-camera     Shift moves the camera five times as fast
    python patch_exe.py --slow-camera     back to the original
    python patch_exe.py --active-pause    the pause key stops time but not the player
    python patch_exe.py --break-panel     back to the original pause panel
    python patch_exe.py --mailbox         the game answers pick and order requests from outside
    python patch_exe.py --no-mailbox      back to the original
    python patch_exe.py --airstrike-menu  the air strike button in every mission, on the point clicked
    python patch_exe.py --no-airstrike-menu  back to the designer's markers only
    python patch_exe.py --m34             the M34 white phosphorus grenade, item 150 (needs mod_m34.py's files)
    python patch_exe.py --no-m34          back to five thrown weapons
    python patch_exe.py --exe <path>      a different copy of the game
"""
import argparse
import os
import shutil

import m34_patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Where the game is. `SOA_SOURCE` lets the package builder point every
# tool at one installation, so a package can be generated from a plain
# retail copy instead of from this project's own working folder.
DEFAULT_EXE = os.path.join(os.environ.get('SOA_SOURCE',
                                          os.path.join(ROOT, '_patched')), 'soa.exe')


def h(text):
    return bytes.fromhex(text)


# group, name, anchor (unique, never written to - or a file offset, for a
# place in the padding that has no bytes of its own to anchor on), original
# bytes, patched bytes
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
    # The camera: the two limits in the constructor, then the two branches of
    # the clamp, then the code they jump to. The anchors of the branches are
    # long because the two branches are each other's mirror image.
    ('camera', 'the camera may come down to 1.5',
     h('C746300000A041'), h('C7465C00000040'), h('C7465C0000C03F')),
    ('camera', 'the camera may go up to 150',
     h('8B56248B462889118B562C'), h('C746600000F041'), h('C7466000001643')),
    ('camera', 'the lower clamp pulls x and y back too',
     h('D94708D85E5CDFE0F6C401740D8A467084C07406'), h('8B565C895708'), h('E9263D0D0090')),
    ('camera', 'the upper clamp pulls x and y back too',
     h('D94708D85E60DFE0F6C441750D8A467084C07406'), h('8B4660894708'), h('E9D13C0D0090')),
    ('camera', 'the code both clamps jump to, in the padding of .text',
     h('F0EAFF8D4DF0E9D922FAFFB8585A8100E9A948FAFF'),
     h('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'), h('000000000000000000000000000000' 'D9462CD9E1D81DAC857C00DFE0F6C441751ED94708D86660D9C0D84E24D8762CD82FD91FD84E28D8762CD86F04D95F048B4660894708E9F5C2F2FFD9462CD9E1D81DAC857C00DFE0F6C441751ED94708D8665CD9C0D84E24D8762CD82FD91FD84E28D8762CD86F04D95F048B565C895708E9A0C2F2FF')),
    # Shift makes the camera fast: a detour where the frame time is loaded,
    # and the code it jumps to, placed in the padding right behind the
    # camera's - by offset, since padding has nothing to anchor on.
    ('speed', 'Shift moves the camera five times as fast',
     h('84DB0F84E7000000896C2410C744241400000000'), h('DF6C24108B5C2420'), h('E91E400D00909090')),
    ('speed', 'the code behind it, in the padding of .text',
     0x3B4650, h('0000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
     h('51526A10FF15A0627B005A59DF6C241066A900807406D80D75467B008B5C2420E9C0BFF2FF0000A040')),
    ('pause', 'the .text section may be written to (its padding holds the byte)',
     h('2E7465787400000000403B000010000000403B0000100000000000000000000000000000'),
     h('20000060'), h('200000E0')),
    ('pause', 'the mission tick keeps the real frame time and zeroes it while paused',
     h('8B865002000057'), h('8B7C24148A4810'), h('E9F2AF1C009090')),
    ('pause', 'the interface still gets the real time',
     h('518B8E4C0200005250E899BF0100'), h('8B8E70020000578B11FF5254'), h('E9A4AF1C0090909090909090')),
    ('pause', 'the camera and the minimap still get the real time',
     h('8B8E38020000E8826B0F00'), h('8B8E38020000578B01FF500C8B8E40020000578B11FF520C'), h('E96DAF1C0090909090909090909090909090909090909090')),
    ('pause', 'the message list still gets the real time',
     h('8A463A84C0750C'), h('8B8E7C02000057E837920B00'), h('E97EAF1C0090909090909090')),
    ('pause', 'the pause key flips the byte instead of opening the panel',
     h('84C074098BCEE805B40000EB0D'), h('6A006A006A0D8BCEE8E6580000'), h('E97EA41C009090909090909090')),
    ('pause', 'the players - selection, menus, path previews - still get the real time',
     h('8B01FF5004578BCEE86D0C0000'), h('8B4E2C57E874D80100'), h('E948C9200090909090')),
    ('pause', 'the byte and the code, in the padding of .text',
     0x3B4680, h('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
     h('000000000000000000000000000000008B7C2414893D84467B00803D80467B0000740233FF8A4810E9F34FE3FF0000008B8E70020000FF3584467B008B11FF5254E94D50E3FF000000000000000000008B8E38020000FF3584467B008B01FF500C8B8E40020000FF3584467B008B11FF520CE97F50E3FF0000000000000000008B8E7C020000FF3584467B00E8AFE2EEFFE97350E3FF00000000000000000000803580467B0001E97E5BE3FF000000008B4E2CFF3584467B00E8220FE1FFE9A936DFFF')),
    ('mailbox', 'the mission serves the mailbox right after the camera has rendered',
     h('3BC78944240C7C4F'), h('8B8D340200008B11FF5210'), h('E97AB41C00909090909090')),
    ('mailbox', 'the mailbox and its code, in the padding of .text',
     0x3B4750, h('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
     h('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000803D50477B0001757331C0A374477B00A378477B00A37C477B006870477B00FF3558477B00FF3554477B008B0D980F8800E83A22EDFFA174477B008B0D78477B002BC8C1E904890D5C477B0085C074238B10891560477B008B5004891564477B008B5008891568477B0050E8701DFAFF83C404C60550477B0000EBAD803D50477B000275306A006A006A036A00FF3558477B00FF3554477B008B0D845A87008B4918E8B963E2FFA35C477B00C60550477B0000EB74803D50477B0003752DA1145B87006890477B006A02508B08FF5130A1145B870068D0477B006A03508B08FF5130C60550477B0000EB3E803D50477B000475358B0D5C477B008D048D60477B0085C9740883E804FF3049EBF48B0D54477B008B01030558477B00FF10A35C477B00C60550477B00008B8D340200008B11FF5210E9534AE3FF')),
    # The air strike from the context menu in every mission: the button's
    # condition becomes "a plane with bombs in the bunker", the button's case
    # notes the click's point, an empty waypoint list gets that point right
    # before the launch (designer markers still win), a launch that flew puts
    # a red ping on the minimap and plays a radio call, and the plane's
    # landing takes the ping off. See architecture.md, "The air strike is a
    # shipped feature".
    ('airstrike', 'the button asks for a plane with bombs instead of a designer marker',
     h('C20800909090909090909090'), h('53558BA998010000'), h('E90B521300909090')),
    ('airstrike', 'the button case notes where the click was',
     h('00FF249528CD4C00'), h('A1845A87008B481885C9'), h('E9D0852E009090909090')),
    ('airstrike', 'an empty waypoint list gets the click; a launch that flew pings and calls',
     h('4533FFE931FFFFFF'), h('8D5424288BCB52E8B3C80D00'), h('E969821D0090909090909090')),
    ('airstrike', 'the plane landing takes the ping off the minimap',
     h('9090909090909090'), h('A08812860083EC10'), h('E9F9050700909090')),
    ('airstrike', 'the point, the clip name and the code, in the padding of .text',
     0x3B4980, h('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
     h('00000000000000000000000000000000726164696F5F616972737472696B655F612E77617600000000000000000000008B8548010000A380497B008B854C010000A384497B00C70588497B0000000000A1845A87008B481885C9E9067AD1FF8B44242C3B44243075116880497B006A01508D4C2434E876ACEFFF8D5424288BCB52E82A46F0FF85C0755F8B0DA45A870085C9741B68114A0000680000FF00FF3584497B00FF3580497B00E841C7E3FFA0A9497B00FEC03C03720230C0A2A9497B000461A2A0497B006A0083EC108BCC68A8497B006890497B00E82213C5FF8B0DAC0F8800E81723EFFFE90F7DE2FF518B0DA45A870085C9740A68114A0000E84DC7E3FF59A08812860083EC10E9E7F9F8FF')),
]


# The M34's rows come from m34_patch.py, which is where their story is; they
# are by file offset, like the caves, because the tables they change are data.
PATCHES += m34_patch.entries()


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
    if isinstance(anchor, int):
        return anchor if data[anchor:anchor + len(a)] in (a, b) else None
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
    ap.add_argument('--camera', action='store_true',
                    help='the camera zooms further out and closer in, and stands '
                         'still at both limits instead of sliding')
    ap.add_argument('--stock-camera', action='store_true', help='back to the original')
    ap.add_argument('--fast-camera', action='store_true',
                    help='Shift moves the camera five times as fast')
    ap.add_argument('--slow-camera', action='store_true', help='back to the original')
    ap.add_argument('--active-pause', action='store_true',
                    help='the pause key stops time but not the player: units can be '
                         'selected and ordered while the game stands still')
    ap.add_argument('--break-panel', action='store_true', help='back to the original pause panel')
    ap.add_argument('--mailbox', action='store_true',
                    help='the game answers pick and order requests written into its mailbox')
    ap.add_argument('--no-mailbox', action='store_true', help='back to the original')
    ap.add_argument('--airstrike-menu', action='store_true',
                    help='the context menu offers an air strike on any point of any mission, '
                         'as long as a plane with bombs is in the hangar')
    ap.add_argument('--no-airstrike-menu', action='store_true', help='back to the original')
    ap.add_argument('--m34', action='store_true',
                    help='the M34 white phosphorus grenade, a sixth thrown weapon - '
                         'with the data files mod_m34.py writes beside the game')
    ap.add_argument('--no-m34', action='store_true', help='back to the original')
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
    if args.camera:
        wanted['camera'] = True
    if args.stock_camera:
        wanted['camera'] = False
    if args.fast_camera:
        wanted['speed'] = True
    if args.slow_camera:
        wanted['speed'] = False
    if args.active_pause:
        wanted['pause'] = True
    if args.break_panel:
        wanted['pause'] = False
    if args.mailbox:
        wanted['mailbox'] = True
    if args.no_mailbox:
        wanted['mailbox'] = False
    if args.airstrike_menu:
        wanted['airstrike'] = True
    if args.no_airstrike_menu:
        wanted['airstrike'] = False
    if args.m34:
        wanted['m34'] = True
    if args.no_m34:
        wanted['m34'] = False
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
