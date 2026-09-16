// The patches in soa.exe that a player may switch, and the window that does.
//
// Every one of them is a few bytes found by a signature - the bytes around
// the place, never an address - so a build of the game we do not know is
// left alone rather than damaged. They are the same patches tools/patch_exe.py
// applies when the package is built; that script has the reading behind each
// of them, this file only has to know the bytes. Two of them, the window
// shape and the intro, are not here: they follow the main window's own
// controls and are written when Play is pressed.
//
// A patch is a group of sites and all of them flip together. A site is
// normally anchored on a signature; the second piece of code in the zero
// padding at the end of .text has only the first piece before it, which may
// or may not be there, so it is given by file offset instead - safe, because
// the bytes there are checked to be the zeros or the code before anything is
// written. The character set is the odd one out: ten identical sites, told
// apart by their count.
//
// The fonts are the other odd one: a name, not a box. The game asks Windows
// for "Tahoma" nine times (every screen) and for "Arial" once (baked into a
// texture), pushing the address of a string in .data each time. Another name
// goes into the zero padding at the end of .text and the pushes are pointed
// at it; the shipped name puts the pushes back and the padding to zero, so
// the default is the file as it came.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

internal struct PatchSite
{
    /// The bytes before the patched ones. Null when Offset is used.
    public byte[] Anchor;
    /// A place in the file for a site with no bytes to anchor on.
    public int Offset;
    /// How many places the anchor must match; one unless said otherwise.
    public int Count;
    public byte[] Original, Patched;
}

internal sealed class ExePatch
{
    public string Key, Name, Tip;
    public PatchSite[] Sites;
    /// A file beside soa.exe the patch cannot do without, and a text that
    /// must be in it; null for a patch that is bytes alone.
    public string NeedsFile, NeedsText;
}

/// One of the two fonts the game asks Windows for: where its pushes are,
/// what they pointed at as shipped, and where another name is kept.
internal sealed class FontSlot
{
    public string Key, Name, Tip, Shipped;
    /// File offsets of the four-byte address in each `push`.
    public int[] Pushes;
    /// The shipped address (the string in .data), and the padding a new name goes to.
    public byte[] ShippedPointer;
    public int Cave;
    public const int Room = 32;          // LF_FACESIZE: 31 characters and the terminator

    public byte[] CavePointer
    {
        get { return BitConverter.GetBytes(0x400000 + Cave); }
    }
}

internal static class Patches
{
    private static byte[] H(string hex)
    {
        var b = new byte[hex.Length / 2];
        for (int i = 0; i < b.Length; i++)
            b[i] = Convert.ToByte(hex.Substring(2 * i, 2), 16);
        return b;
    }

    private static PatchSite Site(string anchor, string original, string patched)
    {
        return new PatchSite { Anchor = H(anchor), Offset = -1, Count = 1,
                               Original = H(original), Patched = H(patched) };
    }

    private static PatchSite At(int offset, string original, string patched)
    {
        return new PatchSite { Anchor = null, Offset = offset, Count = 1,
                               Original = H(original), Patched = H(patched) };
    }

    public static readonly ExePatch[] All =
    {
        new ExePatch
        {
            Key = "focus", Name = "Stay open when another window is clicked",
            Tip = "The game minimises itself the moment it loses focus, in full screen "
                + "too - which drops it into the taskbar whenever the console or the "
                + "map is clicked. Two jumps in the window procedure, both made "
                + "unconditional.",
            Sites = new[]
            {
                Site("83FD08578BF1", "75", "EB"),
                Site("6AF052FF156C627B00389EC5000000", "0F84", "90E9"),
            },
        },
        new ExePatch
        {
            Key = "log", Name = "The log can be read while the game runs",
            Tip = "The game opens tracefile.log for itself alone. With FILE_SHARE_READ "
                + "in that CreateFileA the console window can follow the log live; "
                + "the game only ever writes and does not notice.",
            Sites = new[]
            {
                Site("68800000006A026A00", "6A00", "6A01"),
            },
        },
        new ExePatch
        {
            Key = "camera", Name = "A camera that zooms further out and closer in",
            Tip = "The camera may fly between 1.5 and 150 world units of height instead "
                + "of 2 and 30, and it stops at either limit instead of sliding across "
                + "the map: the two numbers in its constructor, and both branches of the "
                + "height clamp routed through a few bytes at the end of .text that pull "
                + "x and y back along the view direction first.",
            Sites = new[]
            {
                Site("C746300000A041", "C7465C00000040", "C7465C0000C03F"),
                Site("8B56248B462889118B562C", "C746600000F041", "C7466000001643"),
                Site("D94708D85E5CDFE0F6C401740D8A467084C07406", "8B565C895708", "E9263D0D0090"),
                Site("D94708D85E60DFE0F6C441750D8A467084C07406", "8B4660894708", "E9D13C0D0090"),
                Site("F0EAFF8D4DF0E9D922FAFFB8585A8100E9A948FAFF", "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "000000000000000000000000000000D9462CD9E1D81DAC857C00DFE0F6C441751ED94708D86660D9C0D84E24D8762CD82FD91FD84E28D8762CD86F04D95F048B4660894708E9F5C2F2FFD9462CD9E1D81DAC857C00DFE0F6C441751ED94708D8665CD9C0D84E24D8762CD82FD91FD84E28D8762CD86F04D95F048B565C895708E9A0C2F2FF"),
            },
        },
        new ExePatch
        {
            Key = "speed", Name = "Shift moves the camera five times as fast",
            Tip = "The game has no key for it: every camera motion has a fixed speed. "
                + "Where the camera loads the frame time to apply its motions, a detour "
                + "asks GetKeyState for Shift and multiplies the time by five while the "
                + "key is down - panning, the wheel and turning alike. Shift also queues "
                + "orders, which needs a click and so does not get in the way.",
            Sites = new[]
            {
                Site("84DB0F84E7000000896C2410C744241400000000", "DF6C24108B5C2420", "E91E400D00909090"),
                At(0x3B4650, "0000000000000000000000000000000000000000000000000000000000000000000000000000000000",
                   "51526A10FF15A0627B005A59DF6C241066A900807406D80D75467B008B5C2420E9C0BFF2FF0000A040"),
            },
        },
        new ExePatch
        {
            Key = "pause", Name = "Pause and give orders (the pause key)",
            Tip = "The pause key stops time but not the player: the world, the scripts and "
                + "the timers stand still while units can still be selected and ordered, "
                + "and the orders run when time resumes. The game's own pause is a panel "
                + "that swallows every click; this feeds zero time to the simulation and "
                + "the real time to the interface, the camera, the minimap and the players. "
                + "Multiplayer keeps its own pause.",
            Sites = new[]
            {
                Site("2E7465787400000000403B000010000000403B0000100000000000000000000000000000", "20000060", "200000E0"),
                Site("8B865002000057", "8B7C24148A4810", "E9F2AF1C009090"),
                Site("518B8E4C0200005250E899BF0100", "8B8E70020000578B11FF5254", "E9A4AF1C0090909090909090"),
                Site("8B8E38020000E8826B0F00", "8B8E38020000578B01FF500C8B8E40020000578B11FF520C", "E96DAF1C0090909090909090909090909090909090909090"),
                Site("8A463A84C0750C", "8B8E7C02000057E837920B00", "E97EAF1C0090909090909090"),
                Site("84C074098BCEE805B40000EB0D", "6A006A006A0D8BCEE8E6580000", "E97EA41C009090909090909090"),
                Site("8B01FF5004578BCEE86D0C0000", "8B4E2C57E874D80100", "E948C9200090909090"),
                At(0x3B4680, "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
                   "000000000000000000000000000000008B7C2414893D84467B00803D80467B0000740233FF8A4810E9F34FE3FF0000008B8E70020000FF3584467B008B11FF5254E94D50E3FF000000000000000000008B8E38020000FF3584467B008B01FF500C8B8E40020000FF3584467B008B11FF520CE97F50E3FF0000000000000000008B8E7C020000FF3584467B00E8AFE2EEFFE97350E3FF00000000000000000000803580467B0001E97E5BE3FF000000008B4E2CFF3584467B00E8220FE1FFE9A936DFFF"),
            },
        },
        new ExePatch
        {
            Key = "mailbox", Name = "A mailbox for tools outside the game",
            Tip = "A few bytes the game reads once a frame, right after the camera has "
                + "rendered: a request written there from outside - what is under a point "
                + "of the screen, send the selected units to a world point, hand over the "
                + "view and projection matrices - is answered on the game's own thread. "
                + "Nothing in the game writes it; the map window and the research tools "
                + "do. Harmless when nothing asks.",
            Sites = new[]
            {
                Site("3BC78944240C7C4F", "8B8D340200008B11FF5210", "E97AB41C00909090909090"),
                At(0x3B4750, "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
                   "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000803D50477B0001757331C0A374477B00A378477B00A37C477B006870477B00FF3558477B00FF3554477B008B0D980F8800E83A22EDFFA174477B008B0D78477B002BC8C1E904890D5C477B0085C074238B10891560477B008B5004891564477B008B5008891568477B0050E8701DFAFF83C404C60550477B0000EBAD803D50477B000275306A006A006A036A00FF3558477B00FF3554477B008B0D845A87008B4918E8B963E2FFA35C477B00C60550477B0000EB74803D50477B0003752DA1145B87006890477B006A02508B08FF5130A1145B870068D0477B006A03508B08FF5130C60550477B0000EB3E803D50477B000475358B0D5C477B008D048D60477B0085C9740883E804FF3049EBF48B0D54477B008B01030558477B00FF10A35C477B00C60550477B00008B8D340200008B11FF5210E9534AE3FF"),
            },
        },
        new ExePatch
        {
            Key = "airstrike", Name = "Air strike from the context menu",
            Tip = "The game's own air strike button appears only in missions whose designer "
                + "placed target markers, and none of the campaign's has them. With this, "
                + "the ring menu on open ground offers the jet in every mission whenever a "
                + "plane with bombs is in the hangar, the bomb falls where the click was, "
                + "a red ping marks the point on the minimap until the plane is back, and "
                + "the radio talks; a mission's own markers, when it has any, still take "
                + "precedence.",
            Sites = new[]
            {
                Site("C20800909090909090909090", "53558BA998010000", "E90B521300909090"),
                Site("00FF249528CD4C00", "A1845A87008B481885C9", "E9D0852E009090909090"),
                Site("4533FFE931FFFFFF", "8D5424288BCB52E8B3C80D00", "E969821D0090909090909090"),
                Site("9090909090909090", "A08812860083EC10", "E9F9050700909090"),
                At(0x3B4980, "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
                   "00000000000000000000000000000000726164696F5F616972737472696B655F612E77617600000000000000000000008B8548010000A380497B008B854C010000A384497B00C70588497B0000000000A1845A87008B481885C9E9067AD1FF8B44242C3B44243075116880497B006A01508D4C2434E876ACEFFF8D5424288BCB52E82A46F0FF85C0755F8B0DA45A870085C9741B68114A0000680000FF00FF3584497B00FF3580497B00E841C7E3FFA0A9497B00FEC03C03720230C0A2A9497B000461A2A0497B006A0083EC108BCC68A8497B006890497B00E82213C5FF8B0DAC0F8800E81723EFFFE90F7DE2FF518B0DA45A870085C9740A68114A0000E84DC7E3FF59A08812860083EC10E9E7F9F8FF"),
            },
        },
        new ExePatch
        {
            Key = "m34", Name = "The M34 white phosphorus grenade",
            Tip = "A sixth thrown weapon, item 150: a pack of three, thrown like a hand "
                + "grenade, bursting after a few seconds into a wide circle of fire that "
                + "burns for a while - deadly to men in the open, of little use against "
                + "armour. The trader stocks one with the other grenades. The game names "
                + "its five grenades by number in a dozen places - the factory, the hand, "
                + "the throw, the icons, the HUD, the trader - and each is taught the "
                + "sixth here. Needs the M34's records in Data.set, Items.gui and the "
                + "texts beside the game, which the package carries; without them the "
                + "box stays off.",
            NeedsFile = @"Data\GameData\Data.set", NeedsText = "SET_M34",
            Sites = new[]
            {
                At(0x303BBC, "05", "04"),
                At(0x30639C, "05", "04"),
                At(0x308C5C, "05", "04"),
                At(0x30B634, "05", "04"),
                At(0x18EEAC, "05", "04"),
                At(0x1DFCF9, "0606", "0400"),
                At(0x2F9D3F, "02", "01"),
                At(0x300762, "3D930000000F85EC000000", "E999430B00909090909090"),
                At(0x3007CE, "3D930000000F8580000000", "E94D430B00909090909090"),
                At(0x1E69D7, "83F8107732", "E964E11C00"),
                At(0x1E6770, "0F8768010000", "E90BE41C0090"),
                At(0x16FE01, "5FC700D62700005E83C418C3", "E9CA4D240090909090909090"),
                At(0x170E42, "5F5E89185D5B83C418C3", "E9093E24009090909090"),
                At(0x126438, "8BCBC6431401E8FDDFFFFF", "E943E82800909090909090"),
                At(0x1C8D52, "899E880100005F5E5D5B83C418C3", "E979BF1E00909090909090909090"),
                At(0x1C8E46, "3D9A3801000F85B6000000", "E9B5BE1E00909090909090"),
                At(0x2F8FF1, "817B14930000007420", "E90ABC0B0090909090"),
                At(0x3B4B00, "000000000000000000000000000000000000000000000000000000", "3D930000000F8462BCF4FF3D960000000F8457BCF4FFE93EBDF4FF"),
                At(0x3B4B20, "000000000000000000000000000000000000000000000000000000", "3D930000000F84AEBCF4FF3D960000000F84A3BCF4FFE91EBDF4FF"),
                At(0x3B4B40, "000000000000000000000000000000000000000000000000000000000000000000", "83F8100F8705000000E98E1EE3FF83F8130F85B71EE3FFBE95380100E9B11EE3FF"),
                At(0x3B4B80, "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "0F86F01BE3FF83F8130F854F1DE3FF6A3CE82641FAFF83C4048944241885C0C6442410020F84181DE3FF68970000008BC8E80ABAE2FF8986F4000000E9F11BE3FF"),
                At(0x3B4BD0, "0000000000000000000000000000000000000000000000000000000000000000000000000000", "C700D6270000C744240C960000008D44240C508BCEE896DEC7FFC700E22700005F5E83C418C3"),
                At(0x3B4C00, "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "817B14930000000F841400000068930000008BCEE8C714DDFF85C00F85E943F4FF817B14960000000F84EC43F4FF68960000008BCEE8A614DDFF85C00F85C843F4FFE9D343F4FF"),
                At(0x3B4C50, "000000000000000000000000000000000000000000000000000000000000000000000000", "8918C7442414960000008D442414508BCEE8EAC1DBFFC700000000005F5E5D5B83C418C3"),
                At(0x3B4C80, "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "6896000000E826AEE2FF83C404898424840000008D8424840000008B4E08506A01518BCEE887BBECFF8BCBC6431401E88CF7D6FFE98A17D7FF"),
                At(0x3B4CD0, "000000000000000000000000000000000000000000000000000000", "899E88010000817F08970000000F847D40E1FF5F5E5D5B83C418C3"),
                At(0x3B4D00, "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "3D9A3801000F844641E1FF3D953801000F85F141E1FF85C90F84E941E1FF817908970000000F85DC41E1FFE92141E1FF"),
            },
        },
        new ExePatch
        {
            Key = "render", Name = "A frame the graphics driver refuses is skipped, not fatal",
            Tip = "When the exclusive full screen is lost or comes back - an alt-tab, a "
                + "notification, a mode switch - dgVoodoo can answer one frame with "
                + "DDERR_NODRIVERSUPPORT, and the game's error handler answers that by "
                + "quitting: 'Program termination after error 0x887602F8' in "
                + "tracefile.log, most likely in the middle of loading a save. The frame "
                + "routine already skips a frame for DDERR_SURFACEBUSY; this makes it "
                + "skip one for that answer too and draw the next.",
            Sites = new[]
            {
                Site("8B078BCFFF503C8BF0", "81FEAE0176887507", "E920021900909090"),
                At(0x3B4E60, "0000000000000000000000000000000000000000000000000000",
                   "81FEAE017688740D81FEF80276887405E9D5FDE6FFE9C9FDE6FF"),
            },
        },
        new ExePatch
        {
            Key = "charset", Name = "Central European characters in the fonts",
            Tip = "The game builds its fonts from Windows fonts and asks for the machine's "
                + "default character set, so a Czech or Polish translation loses its "
                + "diacritics on an English Windows. This asks for the East European set "
                + "(238) in all ten CreateFontA calls instead.",
            Sites = new[]
            {
                new PatchSite { Anchor = H("6A07"), Offset = -1, Count = 10,
                                Original = H("6A01"), Patched = H("6AEE") },
            },
        },
    };

    public static readonly FontSlot[] Fonts =
    {
        new FontSlot
        {
            Key = "screens", Name = "The screens", Shipped = "Tahoma",
            Tip = "The menus, the trader, the equipment screen, the panels, the tooltips "
                + "and the briefings: nine CreateFontA calls in nine sizes, all for Tahoma.",
            Pushes = new[] { 0x2DA4E3, 0x2DA553, 0x2DA5B9, 0x2DA625, 0x2DA68D,
                             0x2DA6F9, 0x2DA763, 0x2DA7CD, 0x2DA833 },
            ShippedPointer = H("60808600"), Cave = 0x3B4E00,
        },
        new FontSlot
        {
            Key = "bitmap", Name = "The text system's own font", Shipped = "Arial",
            Tip = "Arial at 16 pixels, made once at start before the nine sizes above, "
                + "as the default of the routine that bakes a Windows font into a "
                + "texture. Rarely if ever on screen; here so that both names in the "
                + "exe can be set.",
            Pushes = new[] { 0x2311B7 },
            ShippedPointer = H("AC118600"), Cave = 0x3B4E20,
        },
    };

    /// The face a slot asks for: the shipped name, the one in the cave, or
    /// null when the pushes are neither - not this build, or damaged.
    public static string FontOf(byte[] data, FontSlot f)
    {
        bool shipped = true, cave = true;
        foreach (int at in f.Pushes)
        {
            if (!Matches(data, at, f.ShippedPointer)) shipped = false;
            if (!Matches(data, at, f.CavePointer)) cave = false;
        }
        if (shipped) return f.Shipped;
        if (!cave || f.Cave + FontSlot.Room > data.Length) return null;
        int end = f.Cave;
        while (end < f.Cave + FontSlot.Room && data[end] != 0) end++;
        return System.Text.Encoding.ASCII.GetString(data, f.Cave, end - f.Cave);
    }

    /// Points the slot at a face; the shipped name puts the file back as it
    /// came. Null on success, otherwise why not.
    public static string SetFont(string exePath, FontSlot f, string face)
    {
        face = (face ?? "").Trim();
        if (face.Length == 0 || face.Length >= FontSlot.Room)
            return "a font name is 1 to " + (FontSlot.Room - 1) + " characters";
        foreach (char c in face)
            if (c < ' ' || c > '~') return "a font name is plain characters only; \"" + face + "\" is not";
        if (!File.Exists(exePath)) return "soa.exe was not found";
        byte[] data;
        try { data = File.ReadAllBytes(exePath); }
        catch (Exception ex) { return ex.Message; }
        string now = FontOf(data, f);
        if (now == null) return "this is not the build of soa.exe we know";
        if (now == face) return null;

        bool asShipped = string.Equals(face, f.Shipped, StringComparison.OrdinalIgnoreCase);
        byte[] pointer = asShipped ? f.ShippedPointer : f.CavePointer;
        var cave = new byte[FontSlot.Room];
        if (!asShipped) System.Text.Encoding.ASCII.GetBytes(face).CopyTo(cave, 0);
        foreach (int at in f.Pushes) Array.Copy(pointer, 0, data, at, 4);
        Array.Copy(cave, 0, data, f.Cave, FontSlot.Room);
        try { File.WriteAllBytes(exePath, data); }
        catch (Exception ex) { return ex.Message; }
        return null;
    }

    public static bool Matches(byte[] data, int pos, byte[] want)
    {
        if (pos < 0 || pos + want.Length > data.Length) return false;
        for (int i = 0; i < want.Length; i++)
            if (data[pos + i] != want[i]) return false;
        return true;
    }

    /// Every place the site's anchor matches with the original or the patched
    /// bytes behind it. The search jumps to the next occurrence of the first
    /// byte rather than testing every position - soa.exe is four megabytes.
    public static List<int> FindAll(byte[] data, PatchSite s)
    {
        var found = new List<int>();
        if (s.Anchor == null)
        {
            if (Matches(data, s.Offset, s.Original) || Matches(data, s.Offset, s.Patched))
                found.Add(s.Offset);
            return found;
        }
        int last = data.Length - s.Anchor.Length - Math.Max(s.Original.Length, s.Patched.Length);
        byte first = s.Anchor[0];
        int at = 0;
        while (at <= last)
        {
            int i = Array.IndexOf(data, first, at, last - at + 1);
            if (i < 0) break;
            at = i + 1;
            if (!Matches(data, i, s.Anchor)) continue;
            int pos = i + s.Anchor.Length;
            if (Matches(data, pos, s.Original) || Matches(data, pos, s.Patched)) found.Add(pos);
        }
        return found;
    }

    /// Where a single-site patch sits, or -1 when the signature is missing or
    /// not unique.
    public static int Find(byte[] data, PatchSite s)
    {
        List<int> found = FindAll(data, s);
        return found.Count == 1 ? found[0] : -1;
    }

    /// True when every site is patched, false when every site is original,
    /// null when the build is not the one we know or the sites disagree.
    public static bool? IsOn(byte[] data, ExePatch p)
    {
        int on = 0, off = 0;
        foreach (PatchSite s in p.Sites)
        {
            List<int> found = FindAll(data, s);
            if (found.Count != s.Count) return null;
            foreach (int pos in found)
            {
                if (Matches(data, pos, s.Patched)) on++;
                else off++;
            }
        }
        if (on > 0 && off > 0) return null;
        return on > 0;
    }

    /// Whether the file the patch needs is beside the exe, with the text in
    /// it. True for a patch that needs none.
    public static bool HasFiles(string exePath, ExePatch p)
    {
        if (p.NeedsFile == null) return true;
        string path = Path.Combine(Path.GetDirectoryName(exePath) ?? "", p.NeedsFile);
        try
        {
            if (!File.Exists(path)) return false;
            byte[] data = File.ReadAllBytes(path);
            byte[] want = System.Text.Encoding.ASCII.GetBytes(p.NeedsText);
            for (int i = 0; i + want.Length <= data.Length; i++)
                if (Matches(data, i, want)) return true;
            return false;
        }
        catch (Exception) { return false; }
    }

    /// Writes the patch one way or the other. Null on success, otherwise why not.
    public static string Set(string exePath, ExePatch p, bool on)
    {
        if (on && !HasFiles(exePath, p)) return p.NeedsFile + " with the M34 in it is not beside soa.exe";
        if (!File.Exists(exePath)) return "soa.exe was not found";
        byte[] data;
        try { data = File.ReadAllBytes(exePath); }
        catch (Exception ex) { return ex.Message; }

        bool changed = false;
        foreach (PatchSite s in p.Sites)
        {
            List<int> found = FindAll(data, s);
            if (found.Count != s.Count) return "this is not the build of soa.exe we know";
            byte[] want = on ? s.Patched : s.Original;
            foreach (int pos in found)
            {
                if (Matches(data, pos, want)) continue;
                Array.Copy(want, 0, data, pos, want.Length);
                changed = true;
            }
        }
        if (!changed) return null;
        try { File.WriteAllBytes(exePath, data); }
        catch (Exception ex) { return ex.Message; }
        return null;
    }
}

/// The window: one box per patch, each written the moment it is ticked.
internal sealed class PatchesWindow : Window
{
    private static readonly Brush Bg = Brush("#FF191B20");
    private static readonly Brush Panel = Brush("#FF23262E");
    private static readonly Brush Line = Brush("#FF33384A");
    private static readonly Brush Text = Brush("#FFE2E4EA");
    private static readonly Brush Dim = Brush("#FF8E93A3");
    private static readonly Brush Accent = Brush("#FFC8A24A");
    private static readonly Brush Bad = Brush("#FFE06C60");

    private static SolidColorBrush Brush(string hex)
    {
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
    }

    private readonly string _exe;
    private readonly List<CheckBox> _boxes = new List<CheckBox>();
    private readonly List<ComboBox> _fonts = new List<ComboBox>();
    private TextBlock _status;
    private bool _loading;

    public PatchesWindow(string exePath)
    {
        _exe = exePath;
        Title = "Game patches";
        Width = 560;
        SizeToContent = SizeToContent.Height;
        // as tall as its content up to the screen, then it scrolls: with the
        // fonts under the boxes it is taller than a 1080 screen
        MaxHeight = Math.Max(400, SystemParameters.WorkArea.Height - 40);
        Background = Bg;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        ResizeMode = ResizeMode.NoResize;
        Content = new ScrollViewer
        {
            Content = BuildLayout(),
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
        };
        Loaded += (s, e) => Refresh();
    }

    private UIElement BuildLayout()
    {
        var root = new StackPanel { Margin = new Thickness(22, 16, 22, 14) };
        root.Children.Add(new TextBlock
        {
            Text = "GAME PATCHES",
            Foreground = Accent,
            FontSize = 17,
            FontWeight = FontWeights.Bold,
        });
        root.Children.Add(new TextBlock
        {
            Text = "A few bytes in soa.exe, each found by its surroundings and written "
                 + "the moment a box is ticked. Every one can be put back. The game "
                 + "has to be closed for the file to be written.",
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 3, 0, 12),
        });

        foreach (ExePatch p in Patches.All)
        {
            var frame = new Border
            {
                Background = Panel,
                BorderBrush = Line,
                BorderThickness = new Thickness(1),
                Padding = new Thickness(12, 8, 12, 8),
                Margin = new Thickness(0, 0, 0, 6),
            };
            var st = new StackPanel();
            var box = new CheckBox
            {
                Content = p.Name,
                Tag = p,
                Foreground = Text,
                FontSize = 12,
                ToolTip = p.Tip,
            };
            box.Checked += OnToggle;
            box.Unchecked += OnToggle;
            st.Children.Add(box);
            st.Children.Add(new TextBlock
            {
                Text = p.Tip,
                Foreground = Dim,
                FontSize = 11,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(22, 3, 0, 0),
            });
            frame.Child = st;
            root.Children.Add(frame);
            _boxes.Add(box);
        }

        root.Children.Add(new TextBlock
        {
            Text = "FONTS",
            Foreground = Accent,
            FontSize = 13,
            FontWeight = FontWeights.Bold,
            Margin = new Thickness(0, 10, 0, 2),
        });
        root.Children.Add(new TextBlock
        {
            Text = "The game takes its fonts from Windows by name. Pick one this machine "
                 + "has, or type a name; the shipped name puts the file back as it came. "
                 + "A name Windows does not have is answered with whatever it thinks "
                 + "closest, so the game still starts.",
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 0, 0, 8),
        });
        List<string> installed = InstalledFonts();
        foreach (FontSlot f in Patches.Fonts)
        {
            var frame = new Border
            {
                Background = Panel,
                BorderBrush = Line,
                BorderThickness = new Thickness(1),
                Padding = new Thickness(12, 8, 12, 8),
                Margin = new Thickness(0, 0, 0, 6),
            };
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(220) });
            var st = new StackPanel();
            st.Children.Add(new TextBlock
            {
                Text = f.Name + " (" + f.Shipped + " as shipped)",
                Foreground = Text,
                FontSize = 12,
            });
            st.Children.Add(new TextBlock
            {
                Text = f.Tip,
                Foreground = Dim,
                FontSize = 11,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 3, 12, 0),
            });
            grid.Children.Add(st);
            var combo = new ComboBox
            {
                Tag = f,
                IsEditable = true,
                FontSize = 12,
                VerticalAlignment = VerticalAlignment.Top,
                ToolTip = f.Tip,
            };
            foreach (string name in installed)
            {
                // each name drawn in its own face, so the list is its own preview
                combo.Items.Add(new ComboBoxItem
                {
                    Content = name,
                    FontFamily = new FontFamily(name),
                    FontSize = 13,
                });
            }
            combo.SelectionChanged += OnFontPicked;
            combo.LostKeyboardFocus += OnFontTyped;
            combo.KeyDown += (sender, e) => { if (e.Key == System.Windows.Input.Key.Enter) OnFontTyped(sender, e); };
            Grid.SetColumn(combo, 1);
            grid.Children.Add(combo);
            frame.Child = grid;
            root.Children.Add(frame);
            _fonts.Add(combo);
        }

        _status = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 6, 0, 0),
        };
        root.Children.Add(_status);
        return root;
    }

    /// The family names Windows has, the two shipped ones first.
    private static List<string> InstalledFonts()
    {
        var names = new SortedSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            foreach (FontFamily fam in Fonts.SystemFontFamilies)
            {
                string name = fam.Source;
                // a family from a file comes as "path#Name"; only the name is a face
                int hash = name.LastIndexOf('#');
                if (hash >= 0) name = name.Substring(hash + 1);
                if (name.Length > 0 && name.Length < FontSlot.Room) names.Add(name);
            }
        }
        catch (Exception) { }
        var list = new List<string>();
        foreach (FontSlot f in Patches.Fonts)
        {
            if (!list.Contains(f.Shipped)) list.Add(f.Shipped);
            names.Remove(f.Shipped);
        }
        list.AddRange(names);
        return list;
    }

    private static string ComboText(ComboBox combo)
    {
        var item = combo.SelectedItem as ComboBoxItem;
        return item != null ? (string)item.Content : combo.Text;
    }

    private static void ShowFont(ComboBox combo, string face)
    {
        combo.SelectedItem = null;
        foreach (ComboBoxItem item in combo.Items)
            if (string.Equals((string)item.Content, face, StringComparison.OrdinalIgnoreCase))
            {
                combo.SelectedItem = item;
                return;
            }
        combo.Text = face;
    }

    /// Reads the exe once and sets every box from it.
    private void Refresh()
    {
        _loading = true;
        try
        {
            byte[] data = null;
            try { if (File.Exists(_exe)) data = File.ReadAllBytes(_exe); }
            catch (Exception) { }
            foreach (CheckBox box in _boxes)
            {
                var p = (ExePatch)box.Tag;
                bool? on = data == null ? null : Patches.IsOn(data, p);
                box.IsEnabled = on != null;
                box.IsChecked = on == true;
                if (on == null)
                    box.ToolTip = p.Tip + "\n\n(not in this build of soa.exe, or the game was not found)";
            }
            foreach (ComboBox combo in _fonts)
            {
                var f = (FontSlot)combo.Tag;
                string face = data == null ? null : Patches.FontOf(data, f);
                combo.IsEnabled = face != null;
                ShowFont(combo, face ?? f.Shipped);
                if (face == null)
                    combo.ToolTip = f.Tip + "\n\n(not in this build of soa.exe, or the game was not found)";
            }
            _status.Text = data == null
                ? "soa.exe was not found."
                : _exe;
            _status.Foreground = data == null ? Bad : Dim;
        }
        finally { _loading = false; }
    }

    private void OnFontPicked(object sender, SelectionChangedEventArgs e)
    {
        if (_loading) return;
        var combo = (ComboBox)sender;
        if (combo.SelectedItem == null) return;
        WriteFont(combo, ComboText(combo));
    }

    private void OnFontTyped(object sender, RoutedEventArgs e)
    {
        if (_loading) return;
        var combo = (ComboBox)sender;
        string typed = combo.Text.Trim();
        if (typed.Length == 0) return;
        WriteFont(combo, typed);
    }

    private void WriteFont(ComboBox combo, string face)
    {
        var f = (FontSlot)combo.Tag;
        byte[] data = null;
        try { if (File.Exists(_exe)) data = File.ReadAllBytes(_exe); }
        catch (Exception) { }
        string now = data == null ? null : Patches.FontOf(data, f);
        if (now == null || string.Equals(now, face, StringComparison.Ordinal)) return;

        string failed = GameLink.FindGame() != null
            ? "The game is running - close it first, the file cannot be written while it runs."
            : Patches.SetFont(_exe, f, face);
        _loading = true;
        try
        {
            if (failed != null)
            {
                _status.Text = failed.StartsWith("The game") ? failed : "Not written: " + failed;
                _status.Foreground = Bad;
                ShowFont(combo, now);
                return;
            }
            ShowFont(combo, face);
        }
        finally { _loading = false; }
        _status.Text = f.Name + ": " + face
                     + (string.Equals(face, f.Shipped, StringComparison.OrdinalIgnoreCase) ? " (as shipped)" : "")
                     + " - written to soa.exe.";
        _status.Foreground = Accent;
    }

    private void OnToggle(object sender, RoutedEventArgs e)
    {
        if (_loading) return;
        var box = (CheckBox)sender;
        var p = (ExePatch)box.Tag;
        bool on = box.IsChecked == true;

        if (GameLink.FindGame() != null)
        {
            _status.Text = "The game is running - close it first, the file cannot be written while it runs.";
            _status.Foreground = Bad;
            _loading = true;
            box.IsChecked = !on;
            _loading = false;
            return;
        }

        string failed = Patches.Set(_exe, p, on);
        if (failed != null)
        {
            _status.Text = "Not written: " + failed;
            _status.Foreground = Bad;
            _loading = true;
            box.IsChecked = !on;
            _loading = false;
            return;
        }
        _status.Text = (on ? "On: " : "Off: ") + p.Name.ToLowerInvariant() + " - written to soa.exe.";
        _status.Foreground = Accent;
    }
}
