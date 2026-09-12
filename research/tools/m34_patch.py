r"""The exe side of the M34 white phosphorus grenade: every place soa.exe
names its five thrown weapons by number, taught a sixth.

mod_m34.py writes the data - the records in Data.set, the texts, the icon -
and none of it would matter without these bytes, because the engine does
not learn what a thrown weapon is from Data.set. It knows five of them by
number (131 knife, 132 hand grenade, 136 Molotov, 146 smoke, 147 stun) in
switch statements and lookup tables spread over the code, and a number
outside those falls off the end of every one of them. Item 150 has to be
added to each:

    the factory's class table (0x5DFC64)   which constructor a number gets:
                                           150 a thrown weapon, 151 a round
    the thrown weapon's constructor        makes the round by a switch on the
    (0x5E6720)                             number; a sixth case makes 151
    CanUse (0x700650)                      two lists of what a soldier may
                                           hold, on foot and in a vehicle
    the animation event table (0x6F9CD0)   a byte per number: 1 means the
                                           animation's event is a throw, not
                                           a shot - without it the arm swings
                                           and nothing leaves the hand
    the attack animation tables            a byte per number in each
    (0x703B5C and four more)               character class: 4 the throw, 5 a
                                           rifle shot - without it the M34 is
                                           fired from the shoulder
    Throw (0x5E6980)                       the projectile type by number; off
                                           the table it is uninitialised
    the icon map ([tools]+4, 0x56EC70)     number -> record of Items.gui;
                                           without it the row has no icon
    the HUD size map ([tools]+0x14,        number -> size class of the
    0x56FE10)                              inventory cell; without it the
                                           soldier panel draws a null image
                                           and the game dies
    the trader's restock (0x525B70)        one M34 beside the other grenades
    the re-arm chain (0x6F8E29)            after the last of a kind is thrown
                                           the hand looks for the next kind
    the projectile's tick and removal      the smoke bits a smoke grenade lays
    (0x5C8B80, 0x5C8E20)                   in the map, laid by the M34 while
                                           it burns and taken away after

The code that does not fit in a byte or two goes into caves in the zero
padding at the end of .text, behind the air strike's, at 0x7B4B00 on. Each
cave is a copy of the case beside it with the numbers changed, and jumps
back into the original where that case would have continued.

Everything here is by file offset, not signature: the caves have nothing
to anchor on and the tables are data, and the build this was made against
is the only one (1.1.2.178).

    python m34_patch.py          disassembles the caves, as a check
    python m34_patch.py --cs     prints the sites as C# for Patches.cs
"""
import struct

NEW, ROUND = 150, 151          # the weapon and its round, as mod_m34.py numbers them
ORDINAL = 10210                # the icon record of the weapon in Items.gui
PROJECTILE = 0x13895           # the hand grenade's projectile: an arc, a bounce, a fuze;
                               # 0x13896 would be the Molotov's, bursting where it lands


def jmp(frm, to):
    return b'\xE9' + struct.pack('<i', to - (frm + 5))


def jcc(cc, frm, to):
    return b'\x0F' + bytes([cc]) + struct.pack('<i', to - (frm + 6))


def call(frm, to):
    return b'\xE8' + struct.pack('<i', to - (frm + 5))


JE, JNE, JA, JBE = 0x84, 0x85, 0x87, 0x86
NOP = bytes([0x90])


def cave_canuse(at, true, false):
    """cmp eax,0x93 ; je true ; cmp eax,NEW ; je true ; jmp false"""
    c = b'\x3D\x93\x00\x00\x00' + jcc(JE, at + 5, true)
    c += b'\x3D' + struct.pack('<I', NEW) + jcc(JE, at + 16, true)
    c += jmp(at + 22, false)
    assert len(c) == 27
    return c


def cave_projectile(at):
    """The switch on number-131 in the thrown weapon's Throw (0x5E6980):
    above 0x10 it would leave the projectile type uninitialised."""
    c = b'\x83\xF8\x10' + jcc(JA, at + 3, at + 14)                  # cmp eax,0x10 ; ja L
    c += jmp(at + 9, 0x5E69DC)                                      # back into the switch
    assert len(c) == 14
    c += b'\x83\xF8' + bytes([NEW - 131]) + jcc(JNE, at + 17, 0x5E6A0E)   # cmp eax,19 ; jne the default
    c += b'\xBE' + struct.pack('<I', PROJECTILE) + jmp(at + 28, 0x5E6A12)  # mov esi,type ; jmp
    assert len(c) == 33
    return c


def cave_round(at):
    """The thrown weapon's constructor (0x5E6720) makes the round by a switch
    on the number; the sixth case, a copy of the Molotov's with our numbers."""
    c = jcc(JBE, at, 0x5E6776)                                      # in the table: back
    c += b'\x83\xF8' + bytes([NEW - 131]) + jcc(JNE, at + 9, 0x5E68DE)   # not ours: no round
    c += b'\x6A\x3C' + call(at + 17, 0x758CBC) + b'\x83\xC4\x04'    # push 0x3c ; call new ; add esp,4
    c += b'\x89\x44\x24\x18'                                        # mov [esp+0x18],eax
    c += b'\x85\xC0' + b'\xC6\x44\x24\x10\x02'                      # test eax,eax ; mov byte [esp+0x10],2
    c += jcc(JE, at + 36, 0x5E68C2)                                 # je no memory
    c += b'\x68' + struct.pack('<I', ROUND) + b'\x8B\xC8' + call(at + 49, 0x5E05C0)   # push ROUND ; mov ecx,eax ; call the round's ctor
    c += b'\x89\x86\xF4\x00\x00\x00' + jmp(at + 60, 0x5E67B2)      # mov [esi+0xf4],eax ; jmp the return
    assert len(c) == 65, len(c)
    return c


def cave_icon(at):
    """The tail of the icon map's builder (0x56EC70 fills [tools]+4 with
    number -> icon record): one entry more before it returns. Entered with
    eax pointing at the last entry's value and the frame still whole."""
    c = b'\xC7\x00\xD6\x27\x00\x00'                                 # mov [eax],0x27d6  (the displaced store)
    c += b'\xC7\x44\x24\x0C' + struct.pack('<I', NEW)              # mov [esp+0xc],NEW  (the key slot)
    c += b'\x8D\x44\x24\x0C' + b'\x50' + b'\x8B\xCE'                # lea eax,[esp+0xc] ; push eax ; mov ecx,esi
    c += call(at + 21, 0x432A80)                                    # call map[]
    c += b'\xC7\x00' + struct.pack('<I', ORDINAL)                  # mov [eax],ORDINAL
    c += b'\x5F\x5E\x83\xC4\x18\xC3'                                # pop edi ; pop esi ; add esp,0x18 ; ret
    assert len(c) == 38, len(c)
    return c


def cave_size(at):
    """The tail of the second map's builder (0x56FE10 fills [tools]+0x14 with
    number -> the size class of the HUD's inventory cell): 150 is a small
    thing like the Molotov, class 0. Entered before the epilogue, eax at
    the last entry's value, ebx its value."""
    c = b'\x89\x18'                                                 # mov [eax],ebx  (the displaced store)
    c += b'\xC7\x44\x24\x14' + struct.pack('<I', NEW)              # mov [esp+0x14],NEW  (the key slot)
    c += b'\x8D\x44\x24\x14' + b'\x50' + b'\x8B\xCE'                # lea eax,[esp+0x14] ; push eax ; mov ecx,esi
    c += call(at + 17, 0x570E50)                                    # call map[]
    c += b'\xC7\x00\x00\x00\x00\x00'                                # mov [eax],0
    c += b'\x5F\x5E\x5D\x5B\x83\xC4\x18\xC3'                        # pop edi ; pop esi ; pop ebp ; pop ebx ; add esp,0x18 ; ret
    assert len(c) == 36, len(c)
    return c


def cave_trader(at):
    """The trader's restock (0x525B70) makes one of each grenade and ten of
    each consumable; at its tail, one M34 more. esi is the stock list, ebx
    the trader; the frame is the loop's, so [esp+0x84] is its item slot."""
    c = b'\x68' + struct.pack('<I', NEW) + call(at + 5, 0x5DFAB0) + b'\x83\xC4\x04'   # push NEW ; call factory ; add esp,4
    c += b'\x89\x84\x24\x84\x00\x00\x00'                            # mov [esp+0x84],eax
    c += b'\x8D\x84\x24\x84\x00\x00\x00'                            # lea eax,[esp+0x84]
    c += b'\x8B\x4E\x08' + b'\x50\x6A\x01\x51' + b'\x8B\xCE'          # mov ecx,[esi+8] ; push eax ; push 1 ; push ecx ; mov ecx,esi
    c += call(at + 36, 0x680830)                                    # call add
    c += b'\x8B\xCB' + b'\xC6\x43\x14\x01' + call(at + 47, 0x524440)  # mov ecx,ebx ; mov byte [ebx+0x14],1 ; call  (the displaced tail)
    c += jmp(at + 52, 0x526443)
    assert len(c) == 57, len(c)
    return c


def cave_smoke_on(at):
    """The projectile's tick after landing (0x5C8B80): a round with the fire
    effect burns for fifteen seconds, an explosion every hundred
    milliseconds, and returns; a smoke grenade lays the smoke bit
    (0x200000) into the map cells around it instead. Ours does both: at
    the end of a burn tick, if the round is 151, fall into the smoke loop
    (0x5C8D60) rather than returning. edi is the round's settings, its
    number at +8; ebx is zero, which the loop wants too."""
    c = b'\x89\x9E\x88\x01\x00\x00'                                 # mov [esi+0x188],ebx  (the displaced store)
    c += b'\x81\x7F\x08' + struct.pack('<I', ROUND) + jcc(JE, at + 13, 0x5C8D60)   # cmp [edi+8],ROUND ; je the smoke loop
    c += b'\x5F\x5E\x5D\x5B\x83\xC4\x18\xC3'                        # pop edi ; pop esi ; pop ebp ; pop ebx ; add esp,0x18 ; ret
    assert len(c) == 27, len(c)
    return c


def cave_smoke_off(at):
    """The projectile's removal (0x5C8E20) clears the smoke bits for the two
    smoke types; for the hand grenade's type with our round in it too, or
    the M34's smoke would stay on the map for good. ecx is the settings,
    checked for null the way the original does a few bytes on."""
    c = b'\x3D\x9A\x38\x01\x00' + jcc(JE, at + 5, 0x5C8E51)           # cmp eax,0x1389a ; je clear
    c += b'\x3D' + struct.pack('<I', PROJECTILE) + jcc(JNE, at + 16, 0x5C8F07)   # cmp eax,our type ; jne no
    c += b'\x85\xC9' + jcc(JE, at + 24, 0x5C8F07)                      # test ecx,ecx ; je no
    c += b'\x81\x79\x08' + struct.pack('<I', ROUND) + jcc(JNE, at + 37, 0x5C8F07)   # cmp [ecx+8],ROUND ; jne no
    c += jmp(at + 43, 0x5C8E51)
    assert len(c) == 48, len(c)
    return c


def cave_reequip(at):
    """After the last grenade of a kind is thrown (0x6F8E29) the hand looks
    for the next kind in the pack; ours comes after the stun grenade."""
    c = b'\x81\x7B\x14\x93\x00\x00\x00' + jcc(JE, at + 7, at + 33)  # cmp [ebx+0x14],0x93 ; je L
    c += b'\x68\x93\x00\x00\x00' + b'\x8B\xCE' + call(at + 20, 0x5860E0)   # push 0x93 ; mov ecx,esi ; call find
    c += b'\x85\xC0' + jcc(JNE, at + 27, 0x6F900A)                  # test eax,eax ; jne found
    assert len(c) == 33
    c += b'\x81\x7B\x14' + struct.pack('<I', NEW) + jcc(JE, at + 40, 0x6F901A)   # L: cmp [ebx+0x14],NEW ; je none
    c += b'\x68' + struct.pack('<I', NEW) + b'\x8B\xCE' + call(at + 53, 0x5860E0)
    c += b'\x85\xC0' + jcc(JNE, at + 60, 0x6F900A)
    c += jmp(at + 66, 0x6F901A)
    assert len(c) == 71, len(c)
    return c


CAVES = {
    'canuse_a': 0x7B4B00, 'canuse_b': 0x7B4B20, 'projectile': 0x7B4B40, 'round': 0x7B4B80,
    'icon': 0x7B4BD0, 'reequip': 0x7B4C00, 'size': 0x7B4C50, 'trader': 0x7B4C80,
    'smoke_on': 0x7B4CD0, 'smoke_off': 0x7B4D00,
}


def patches():
    """(name, VA, original, patched) for the sites, and (name, VA, bytes) for the caves."""
    sites = [
        # the attack animation is chosen by a table per character class,
        # indexed by the number of the item in hand: 4 is the throw, 5 the
        # rifle shot that everything unknown gets (Con_Man 0x703192,
        # Con_Woman 0x705972, Monk 0x708232, Nitro_Man 0x70ABC9, Mutant
        # 0x58E482 - the same table in each, at these five addresses)
        ('the man throws 150 instead of shooting it', 0x703B5C + NEW - 54, b'', b''),
        ('the woman throws 150 instead of shooting it', 0x70633C + NEW - 54, b'', b''),
        ('the monk throws 150 instead of shooting it', 0x708BFC + NEW - 54, b'', b''),
        ('the nitro man throws 150 instead of shooting it', 0x70B5D4 + NEW - 54, b'', b''),
        ('the mutant throws 150 instead of shooting it', 0x58EE4C + NEW - 54, b'', b''),
        ('the factory makes 150 a thrown weapon and 151 a round',
         0x5DFC64 + NEW - 1, b'\x06\x06', b'\x04\x00'),
        ('the animation event of 150 is the throw',
         0x6F9CD0 + NEW - 39, b'\x02', b'\x01'),
        ('CanUse: 150 is in the grenade list a soldier in a vehicle may use',
         0x700762, b'\x3D\x93\x00\x00\x00' + jcc(JNE, 0x700767, 0x700859),
         jmp(0x700762, CAVES['canuse_a']) + b'\x90' * 6),
        ('CanUse: 150 is in the grenade list a soldier on foot may use',
         0x7007CE, b'\x3D\x93\x00\x00\x00' + jcc(JNE, 0x7007D3, 0x700859),
         jmp(0x7007CE, CAVES['canuse_b']) + b'\x90' * 6),
        ('the projectile of 150 is chosen',
         0x5E69D7, b'\x83\xF8\x10\x77\x32', jmp(0x5E69D7, CAVES['projectile'])),
        ('the constructor of 150 makes it a round',
         0x5E6770, jcc(JA, 0x5E6770, 0x5E68DE), jmp(0x5E6770, CAVES['round']) + b'\x90'),
        ('the icon map knows 150',
         0x56FE01, b'\x5F\xC7\x00\xD6\x27\x00\x00\x5E\x83\xC4\x18\xC3', jmp(0x56FE01, CAVES['icon']) + b'\x90' * 7),
        ('the HUD knows the size of 150',
         0x570E42, bytes.fromhex('5f5e89185d5b83c418c3'), jmp(0x570E42, CAVES['size']) + b'\x90' * 5),
        ('the trader stocks one M34 with the other grenades',
         0x526438, bytes.fromhex('8bcbc6431401e8fddfffff'), jmp(0x526438, CAVES['trader']) + NOP * 6),
        ('the M34 lays smoke while it burns',
         0x5C8D52, bytes.fromhex('899e880100005f5e5d5b83c418c3'), jmp(0x5C8D52, CAVES['smoke_on']) + NOP * 9),
        ('the M34 takes its smoke away when it is done',
         0x5C8E46, bytes.fromhex('3d9a3801000f85b6000000'), jmp(0x5C8E46, CAVES['smoke_off']) + NOP * 6),
        ('the hand re-arms with 150 when the other grenades are gone',
         0x6F8FF1, b'\x81\x7B\x14\x93\x00\x00\x00\x74\x20', jmp(0x6F8FF1, CAVES['reequip']) + b'\x90' * 4),
    ]
    caves = [
        ('canuse_a', CAVES['canuse_a'], cave_canuse(CAVES['canuse_a'], 0x70076D, 0x700859)),
        ('canuse_b', CAVES['canuse_b'], cave_canuse(CAVES['canuse_b'], 0x7007D9, 0x700859)),
        ('projectile', CAVES['projectile'], cave_projectile(CAVES['projectile'])),
        ('round', CAVES['round'], cave_round(CAVES['round'])),
        ('icon', CAVES['icon'], cave_icon(CAVES['icon'])),
        ('reequip', CAVES['reequip'], cave_reequip(CAVES['reequip'])),
        ('size', CAVES['size'], cave_size(CAVES['size'])),
        ('trader', CAVES['trader'], cave_trader(CAVES['trader'])),
        ('smoke_on', CAVES['smoke_on'], cave_smoke_on(CAVES['smoke_on'])),
        ('smoke_off', CAVES['smoke_off'], cave_smoke_off(CAVES['smoke_off'])),
    ]
    # the caves must not overlap
    spans = sorted((va, va + len(b)) for _, va, b in caves)
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        assert a1 <= b0, 'caves overlap'
    return sites, caves


GROUP = 'm34'


def entries():
    """The patch_exe.py table rows: (group, name, file offset, original, patched)."""
    sites, caves = patches()
    rows = [(GROUP, name, va - 0x400000, orig, patched) for name, va, orig, patched in sites]
    for name, va, code in caves:
        rows.append((GROUP, 'the %s code, in the padding of .text' % name, va - 0x400000, bytes(len(code)), code))
    return rows


def as_cs():
    """The same rows as the Sites of an ExePatch in launcher/Patches.cs."""
    out = []
    for group, name, off, orig, patched in entries():
        out.append('                At(0x%06X, "%s", "%s"),' % (off, orig.hex().upper(), patched.hex().upper()))
    return '\n'.join(out)


if __name__ == '__main__':
    import sys
    if '--cs' in sys.argv:
        print(as_cs())
        raise SystemExit
    import capstone
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    sites, caves = patches()
    for name, va, b in caves:
        print('--', name)
        for i in cs.disasm(b, va):
            print('  %08X  %-8s %s' % (i.address, i.mnemonic, i.op_str))
