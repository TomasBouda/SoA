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

    /// Writes the patch one way or the other. Null on success, otherwise why not.
    public static string Set(string exePath, ExePatch p, bool on)
    {
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
    private TextBlock _status;
    private bool _loading;

    public PatchesWindow(string exePath)
    {
        _exe = exePath;
        Title = "Game patches";
        Width = 560;
        SizeToContent = SizeToContent.Height;
        Background = Bg;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        ResizeMode = ResizeMode.NoResize;
        Content = BuildLayout();
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
            _status.Text = data == null
                ? "soa.exe was not found."
                : _exe;
            _status.Foreground = data == null ? Bad : Dim;
        }
        finally { _loading = false; }
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
