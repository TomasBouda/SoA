// What is in the saves, without loading them.
//
// A .sav is not compressed and not obfuscated: the same sixteen-byte magic as
// the layouts and the text resources with a class byte in front, a version, a
// flag saying whether it was taken in the bunker or out on a mission, and then
// strings written with a length byte each. That is enough to tell one save
// from another at a glance - which mission, how far in, who was still alive.
//
// The reader is the same one as tools/read_save.py, ported; saves.md has the
// format. Names come out readable because every TRES key in the save resolves
// through the .trs files in the archives, which are simpler still.
//
// It writes in one place only: the item in an equipment slot, through
// Inventory, which has the format and the reasoning behind it. Everything else
// is read. Loading a save is the game's own job and goes through GameLink, the
// same way the console does it.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

internal sealed class SavesWindow : Window
{
    private static readonly Brush Bg = Brush("#FF191B20");
    private static readonly Brush Panel = Brush("#FF23262E");
    private static readonly Brush Line = Brush("#FF33384A");
    private static readonly Brush Text = Brush("#FFE6E8EE");
    private static readonly Brush Dim = Brush("#FF8E93A3");
    private static readonly Brush Accent = Brush("#FFC8A24A");
    private static readonly Brush Bad = Brush("#FFE06C60");

    private static SolidColorBrush Brush(string hex)
    {
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
    }

    private readonly ListBox _list;
    private readonly StackPanel _detail;
    private readonly TextBlock _status;
    private readonly Button _load;
    private readonly string _gameDir;
    private ListBox _gear;
    private ComboBox _swap;
    private Button _change;

    private static Dictionary<string, string> _text;

    public SavesWindow()
    {
        Title = "Saves";
        Width = 900;
        Height = 620;
        Background = Bg;
        Foreground = Text;
        FontFamily = new FontFamily("Segoe UI");

        _gameDir = GamePath.In();

        var root = new DockPanel { Margin = new Thickness(14) };

        _status = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 10, 0, 0),
            TextWrapping = TextWrapping.Wrap
        };
        DockPanel.SetDock(_status, Dock.Bottom);
        root.Children.Add(_status);

        var buttons = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            HorizontalAlignment = HorizontalAlignment.Right,
            Margin = new Thickness(0, 10, 0, 0)
        };
        _load = new Button
        {
            Content = "Load it in the game",
            Padding = new Thickness(14, 6, 14, 6),
            IsEnabled = false,
            ToolTip = "Hands the file to the game the way its own quick load does. "
                    + "It only works while a mission is running, because the function "
                    + "that loads a save belongs to the mission."
        };
        _load.Click += (s, e) => Load();
        buttons.Children.Add(_load);
        var refresh = new Button
        {
            Content = "Refresh",
            Padding = new Thickness(14, 6, 14, 6),
            Margin = new Thickness(8, 0, 0, 0)
        };
        refresh.Click += (s, e) => Fill();
        buttons.Children.Add(refresh);
        DockPanel.SetDock(buttons, Dock.Bottom);
        root.Children.Add(buttons);

        _list = new ListBox
        {
            Width = 280,
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            Margin = new Thickness(0, 0, 14, 0)
        };
        _list.SelectionChanged += (s, e) => Show(_list.SelectedItem as Save);
        DockPanel.SetDock(_list, Dock.Left);
        root.Children.Add(_list);

        _detail = new StackPanel { Margin = new Thickness(4) };
        root.Children.Add(new ScrollViewer
        {
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Content = _detail
        });

        Content = root;
        Fill();
    }

    // ----------------------------------------------------------------- the list

    private void Fill()
    {
        _list.Items.Clear();
        string folder = Path.Combine(_gameDir, "SaveGames");
        string[] files;
        try { files = Directory.GetFiles(folder, "*.sav", SearchOption.AllDirectories); }
        catch (Exception) { files = new string[0]; }

        var found = new List<Save>();
        foreach (string f in files)
        {
            try { found.Add(new Save(f)); }
            catch (Exception) { }
        }
        found.Sort((a, b) => b.When.CompareTo(a.When));
        foreach (Save s in found) _list.Items.Add(s);

        _status.Text = found.Count == 0
            ? "No saves under " + folder + "."
            : found.Count + " saves, newest first.";
        if (found.Count > 0) _list.SelectedIndex = 0;
    }

    // --------------------------------------------------------------- the detail

    private void Show(Save save)
    {
        _detail.Children.Clear();
        _load.IsEnabled = save != null;
        if (save == null) return;

        _detail.Children.Add(new TextBlock
        {
            Text = save.Name,
            Foreground = Accent,
            FontSize = 20,
            Margin = new Thickness(0, 0, 0, 2)
        });
        _detail.Children.Add(new TextBlock
        {
            Text = save.When.ToString("d MMMM yyyy, HH:mm", CultureInfo.InvariantCulture)
                 + "   -   " + save.Size,
            Foreground = Dim,
            FontSize = 12,
            Margin = new Thickness(0, 0, 0, 12)
        });

        if (!save.Ok)
        {
            _detail.Children.Add(new TextBlock
            {
                Text = "This does not look like a save.",
                Foreground = Bad,
                FontSize = 13
            });
            return;
        }

        BitmapImage picture = save.Picture();
        if (picture != null)
            _detail.Children.Add(new Image
            {
                Source = picture,
                MaxWidth = 400,
                HorizontalAlignment = HorizontalAlignment.Left,
                Margin = new Thickness(0, 0, 0, 14)
            });

        Field("taken", save.AtBase ? "in the bunker" : "on a mission");
        if (save.Mission != null) Field("mission", save.Mission);
        if (save.Parties.Count > 0)
        {
            var parties = new StringBuilder();
            for (int i = 0; i < save.Parties.Count; i++)
            {
                if (i > 0) parties.Append(", ");
                parties.Append(save.Parties[i]);
                if (i == 0) parties.Append(" (yours)");
            }
            Field("parties", parties.ToString());
        }

        Dictionary<string, string> text = Names();
        List<string> people = save.People();
        Dictionary<string, int> things = save.Things();

        // The characters have records of their own, so they belong with the
        // people rather than among the things, and their keys can be named
        // from the record instead of being printed raw.
        var isPerson = new Dictionary<string, bool>();
        foreach (Person who in Inventory.People(save))
            if (!isPerson.ContainsKey(who.Key))
            {
                isPerson[who.Key] = true;
                string named = Save.NameOf(who.Key, text);
                if (named == null) named = who.Name;
                if (!people.Contains(named)) people.Add(named);
            }

        var kinds = new List<string>();
        foreach (string key in things.Keys)
        {
            if (isPerson.ContainsKey(key)) continue;
            string named = Save.NameOf(key, text);
            string shown = named ?? key;
            if (!kinds.Contains(shown)) kinds.Add(shown);
        }
        kinds.Sort(StringComparer.CurrentCultureIgnoreCase);

        if (kinds.Count > 0)
        {
            Heading(kinds.Count + " kinds of thing in it");
            var line = new StringBuilder();
            foreach (string k in kinds)
            {
                if (line.Length > 0) line.Append(",   ");
                line.Append(k);
            }
            _detail.Children.Add(new TextBlock
            {
                Text = line.ToString(),
                Foreground = Text,
                FontSize = 13,
                TextWrapping = TextWrapping.Wrap,
                MaxWidth = 480,
                Margin = new Thickness(0, 0, 0, 4)
            });
            _detail.Children.Add(new TextBlock
            {
                Text = "Kinds, not counts. A vehicle is written into the save once for "
                     + "each weapon it can mount - four times for a T-55, three for a "
                     + "BMP-1 - so counting the mentions would report seven helicopters "
                     + "where there is one. What is in the save is exact; how many of "
                     + "each is not known, so it is not claimed.",
                Foreground = Dim,
                FontSize = 11,
                TextWrapping = TextWrapping.Wrap,
                MaxWidth = 480
            });
        }
        if (people.Count > 0)
        {
            people.Sort(StringComparer.CurrentCultureIgnoreCase);
            Heading(people.Count + " people by name");
            foreach (string p in people)
                _detail.Children.Add(new TextBlock
                {
                    Text = "   " + p,
                    Foreground = Text,
                    FontSize = 13,
                    Margin = new Thickness(0, 1, 0, 1)
                });
        }
        Equipment(save);
    }

    // -------------------------------------------------------------- equipment

    /// What everybody in the save carries, and a way to change one of them.
    private void Equipment(Save save)
    {
        _gear = null;
        _swap = null;
        _change = null;

        if (Inventory.Items().Count == 0)
        {
            Heading("what they carry");
            _detail.Children.Add(new TextBlock
            {
                Text = "There is no catalog here, so the numbers in the save cannot be "
                     + "given names - and an equipment slot is nothing but a number.",
                Foreground = Dim,
                FontSize = 12,
                TextWrapping = TextWrapping.Wrap,
                MaxWidth = 480
            });
            return;
        }

        List<Carried> carried = Inventory.All(save);
        if (carried.Count == 0)
        {
            Heading("what they carry");
            _detail.Children.Add(new TextBlock
            {
                Text = "Nothing this reader recognises. Early saves and the ones taken "
                     + "before a squad exists genuinely hold none.",
                Foreground = Dim,
                FontSize = 12,
                TextWrapping = TextWrapping.Wrap,
                MaxWidth = 480
            });
            return;
        }

        Heading(carried.Count + " things they carry");
        _gear = new ListBox
        {
            Height = 190,
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            FontFamily = new FontFamily("Consolas"),
            FontSize = 12
        };
        foreach (Carried c in carried) _gear.Items.Add(c);
        _gear.SelectionChanged += (s, e) => Offer();
        _detail.Children.Add(_gear);

        var row = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            Margin = new Thickness(0, 8, 0, 0)
        };
        _swap = new ComboBox { Width = 330, IsEnabled = false };
        row.Children.Add(_swap);
        _change = new Button
        {
            Content = "Put that there instead",
            Padding = new Thickness(14, 4, 14, 4),
            Margin = new Thickness(8, 0, 0, 0),
            IsEnabled = false
        };
        _change.Click += (s, e) => Change();
        row.Children.Add(_change);
        _detail.Children.Add(row);

        _detail.Children.Add(new TextBlock
        {
            Text = "The save is copied to .bak before the first change, so the way back "
                 + "is always to the file the game itself wrote. A save already loaded "
                 + "has to be loaded again for the change to show.",
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            MaxWidth = 480,
            Margin = new Thickness(0, 6, 0, 0)
        });
    }

    /// Fill the dropdown for whatever is selected, the items that suit the slot
    /// first and the current one chosen.
    private void Offer()
    {
        if (_swap == null || _change == null) return;
        var chosen = _gear.SelectedItem as Carried;
        _swap.Items.Clear();
        _swap.IsEnabled = chosen != null;
        _change.IsEnabled = chosen != null;
        if (chosen == null) return;

        var offer = new List<Choice>();
        foreach (KeyValuePair<int, string> p in Inventory.Items())
            offer.Add(new Choice
            {
                Number = p.Key,
                Name = p.Value,
                Fits = Inventory.LikelySlot(p.Key) == chosen.Slot
            });
        offer.Sort((a, b) => a.Fits != b.Fits
                           ? (a.Fits ? -1 : 1)
                           : string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));
        foreach (Choice c in offer)
        {
            _swap.Items.Add(c);
            if (c.Number == chosen.Item) _swap.SelectedItem = c;
        }
        if (_swap.SelectedItem == null && _swap.Items.Count > 0) _swap.SelectedIndex = 0;
    }

    private void Change()
    {
        var save = _list.SelectedItem as Save;
        var chosen = _gear.SelectedItem as Carried;
        var pick = _swap.SelectedItem as Choice;
        if (save == null || chosen == null || pick == null) return;
        if (pick.Number == chosen.Item)
        {
            _status.Text = chosen.Owner + " already carries a " + pick.Name + ".";
            _status.Foreground = Dim;
            return;
        }

        string failed = Inventory.Write(save.Path, chosen.Offset, pick.Number);
        if (failed != null)
        {
            _status.Text = "Could not write it: " + failed;
            _status.Foreground = Bad;
            return;
        }
        _status.Text = chosen.Owner + " had " + chosen.Name + " and now has "
                     + pick.Name + ", at 0x" + chosen.Offset.ToString("X") + " of "
                     + save.Name + ". The old file is beside it as .bak.";
        _status.Foreground = Accent;

        // The file on disk has moved on, so read it again rather than showing
        // what was true a moment ago.
        int index = _list.SelectedIndex;
        int line = _gear.SelectedIndex;
        try
        {
            var again = new Save(save.Path);
            _list.Items[index] = again;
            _list.SelectedIndex = index;
            if (_gear != null && line >= 0 && line < _gear.Items.Count)
                _gear.SelectedIndex = line;
        }
        catch (Exception) { }
    }

    private void Heading(string what)
    {
        _detail.Children.Add(new TextBlock
        {
            Text = what,
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 14, 0, 4)
        });
    }

    private void Field(string label, string value)
    {
        var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 1, 0, 1) };
        row.Children.Add(new TextBlock
        {
            Text = label,
            Foreground = Dim,
            FontSize = 13,
            Width = 90,
            TextAlignment = TextAlignment.Right,
            Margin = new Thickness(0, 0, 10, 0)
        });
        row.Children.Add(new TextBlock
        {
            Text = value,
            Foreground = Text,
            FontSize = 13,
            TextWrapping = TextWrapping.Wrap,
            MaxWidth = 420
        });
        _detail.Children.Add(row);
    }

    private void Load()
    {
        var save = _list.SelectedItem as Save;
        if (save == null) return;
        uint got;
        string failed = GameLink.LoadSave(save.Path, out got);
        if (failed != null)
        {
            _status.Text = failed;
            _status.Foreground = Bad;
            return;
        }
        _status.Text = "Handed " + save.Name + " to the game.";
        _status.Foreground = Dim;
    }

    // ------------------------------------------------------------------ the text

    /// Every key the game can show, read once out of the archives. The
    /// description resources are skipped: they carry biographies under the same
    /// keys as the names, and a name is what a list wants.
    private Dictionary<string, string> Names()
    {
        if (_text != null) return _text;
        var all = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        string[] archives;
        try { archives = Directory.GetFiles(_gameDir, "*.ubn"); }
        catch (Exception) { archives = new string[0]; }
        foreach (string archive in archives)
        {
            try
            {
                using (ZipArchive zip = ZipFile.OpenRead(archive))
                    foreach (ZipArchiveEntry entry in zip.Entries)
                    {
                        string low = entry.FullName.ToLowerInvariant();
                        if (!low.EndsWith(".trs")) continue;
                        if (low.Contains("description") || low.Contains("desciption")) continue;
                        using (var memory = new MemoryStream())
                        using (Stream open = entry.Open())
                        {
                            open.CopyTo(memory);
                            foreach (KeyValuePair<string, string> pair in Save.ReadText(memory.ToArray()))
                                all[pair.Key] = pair.Value;
                        }
                    }
            }
            catch (Exception) { }
        }
        _text = all;
        return _text;
    }
}

/// One save file, read far enough to say what it is.
internal sealed class Save
{
    // Every file this engine serialises opens with the same sixteen bytes bar
    // the first, which says which class wrote it: 0x38 a save, 0x40 a text
    // resource, 0x41 a layout.
    private static readonly byte[] MagicTail =
    {
        0xF9, 0xB3, 0x0A, 0x62, 0x93, 0xD1, 0x11, 0x9A,
        0x2B, 0x08, 0x00, 0x00, 0x30, 0x05, 0x12
    };

    private readonly byte[] _raw;
    private List<KeyValuePair<int, string>> _strings;

    public readonly string Path;
    public readonly string Name;
    public readonly DateTime When;
    public readonly string Size;
    public readonly bool Ok;
    public readonly bool AtBase;
    public string Mission;
    public readonly List<string> Parties = new List<string>();

    public Save(string path)
    {
        Path = path;
        Name = System.IO.Path.GetFileNameWithoutExtension(path);
        When = File.GetLastWriteTime(path);
        _raw = File.ReadAllBytes(path);
        Size = _raw.Length > 1048576
             ? (_raw.Length / 1048576.0).ToString("0.0", CultureInfo.InvariantCulture) + " MB"
             : (_raw.Length / 1024.0).ToString("0", CultureInfo.InvariantCulture) + " kB";

        Ok = _raw.Length > 0x40 && _raw[0] == 0x38;
        for (int i = 0; Ok && i < MagicTail.Length; i++)
            if (_raw[1 + i] != MagicTail[i]) Ok = false;
        if (!Ok) return;

        // 1 means the bunker, 0 out on a mission. The sizes agree: a bunker
        // save is a few kilobytes, a mission save carries the landscape.
        AtBase = BitConverter.ToUInt32(_raw, 0x14) == 1;
        ReadHead();
    }

    public override string ToString()
    {
        return Name + "        " + When.ToString("d MMM HH:mm", CultureInfo.InvariantCulture);
    }

    /// The thumbnail the game writes beside a named save. The quick save has
    /// none, so this is often nothing.
    public BitmapImage Picture()
    {
        string png = System.IO.Path.ChangeExtension(Path, ".png");
        if (!File.Exists(png)) return null;
        try
        {
            var image = new BitmapImage();
            image.BeginInit();
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.UriSource = new Uri(png);
            image.EndInit();
            image.Freeze();
            return image;
        }
        catch (Exception) { return null; }
    }

    // ------------------------------------------------------------- the format

    /// A string as the game writes it: one length byte, then the characters. A
    /// length of 0xFF means a two-byte length follows instead, which is how the
    /// long descriptions in the text resources fit.
    private static string ReadString(byte[] raw, ref int i)
    {
        int n = raw[i++];
        if (n == 0xFF)
        {
            n = BitConverter.ToUInt16(raw, i);
            i += 2;
        }
        if (i + n > raw.Length) throw new IndexOutOfRangeException();
        string s = Encoding.GetEncoding(28591).GetString(raw, i, n);
        i += n;
        return s;
    }

    private void ReadHead()
    {
        try
        {
            if (AtBase)
            {
                // The bunker save names the mission it will start next.
                int i = 0x20;
                Mission = ReadString(_raw, ref i);
                return;
            }
            // A mission save opens with the parties, in the order the mission
            // declares them, each followed by a number that has been 2 in every
            // save looked at so far. That number is what ends the list: the
            // names are whatever the mission author typed, `Blade???` among
            // them, so they cannot be told apart by their spelling.
            int at = 0x30;
            while (at < _raw.Length)
            {
                int j = at;
                string name = ReadString(_raw, ref j);
                if (j + 4 > _raw.Length) break;
                uint n = BitConverter.ToUInt32(_raw, j);
                j += 4;
                if (name.Length == 0 || n != 2) break;
                Parties.Add(name);
                at = j;
            }
            // One field of a shape not yet worked out sits between the parties
            // and the two paths that follow - the mission's text file and the
            // mission itself. Rather than guess at it, walk strings forward
            // until the text file turns up; it is within a few dozen bytes.
            while (at < Math.Min(_raw.Length, 0x400))
            {
                int j = at;
                string s = ReadString(_raw, ref j);
                if (s.EndsWith(".trs", StringComparison.OrdinalIgnoreCase))
                {
                    Mission = ReadString(_raw, ref j);
                    return;
                }
                at = s.Length > 0 ? j : at + 1;
            }
        }
        catch (Exception) { }
    }

    /// The bytes themselves, for the one reader that needs them: the equipment
    /// in a character's record is not a string and cannot be found through the
    /// string walk.
    public byte[] Raw { get { return _raw; } }

    /// The strings with their offsets, which is how a character's record is
    /// bounded - it opens with his TRES_ key and runs to the next one.
    public List<KeyValuePair<int, string>> AllStrings() { return Strings(); }

    /// Every length-prefixed string in the file, with its offset.
    private List<KeyValuePair<int, string>> Strings()
    {
        if (_strings != null) return _strings;
        var found = new List<KeyValuePair<int, string>>();
        var latin = Encoding.GetEncoding(28591);
        int i = 0;
        while (i < _raw.Length - 1)
        {
            int n = _raw[i];
            if (n >= 3 && n <= 64 && i + 1 + n <= _raw.Length)
            {
                bool printable = true;
                for (int k = 1; k <= n; k++)
                    if (_raw[i + k] < 32 || _raw[i + k] >= 127) { printable = false; break; }
                if (printable)
                {
                    found.Add(new KeyValuePair<int, string>(i, latin.GetString(_raw, i + 1, n)));
                    i += 1 + n;
                    continue;
                }
            }
            i++;
        }
        _strings = found;
        return found;
    }

    /// Tell a real name from four bytes of terrain that happen to be printable.
    ///
    /// The middle of a mission save is the landscape, and in three megabytes of
    /// it a byte will regularly be followed by its own count of printable
    /// characters purely by chance. Those look like `Kgb!a`; the real names
    /// look like `Natasha Romanova`. Letters and a vowel separate them.
    private static bool LooksLikeAName(string s)
    {
        if (s.Length < 3) return false;
        int letters = 0, vowels = 0;
        foreach (char c in s)
        {
            if (char.IsLetter(c) || c == ' ' || c == '_' || c == '-' || c == '.' || c == '\'') letters++;
            if ("aeiouyAEIOUY".IndexOf(c) >= 0) vowels++;
        }
        return vowels > 0 && letters >= s.Length * 0.85;
    }

    private static readonly Regex Person = new Regex(@"^[A-Z][a-z]+ [A-Z][a-z]");

    /// The characters the mission author gave a name of their own.
    public List<string> People()
    {
        var seen = new List<string>();
        foreach (KeyValuePair<int, string> pair in Strings())
        {
            string s = pair.Value;
            if (!LooksLikeAName(s) || s.StartsWith("TRES_")) continue;
            if (s == "unknown name" || s == "empty" || s == "leer" || s == "Name") continue;
            if (Parties.Contains(s)) continue;
            if (s.EndsWith(".mis", StringComparison.OrdinalIgnoreCase)) continue;
            if (s.EndsWith(".trs", StringComparison.OrdinalIgnoreCase)) continue;
            if (Person.IsMatch(s) && !seen.Contains(s)) seen.Add(s);
        }
        return seen;
    }

    /// Everything the game names for its interface, counted.
    public Dictionary<string, int> Things()
    {
        var count = new Dictionary<string, int>();
        foreach (KeyValuePair<int, string> pair in Strings())
        {
            string s = pair.Value;
            if (!s.StartsWith("TRES_") || !LooksLikeAName(s)) continue;
            count[s] = count.ContainsKey(s) ? count[s] + 1 : 1;
        }
        return count;
    }

    /// A name for a TRES key, or nothing.
    ///
    /// The same key often carries both a name and a biography, in different
    /// text resources, and which one we get depends on the order they were
    /// read. A biography runs to several lines, so it is easy to refuse - and
    /// refusing is right, because the key itself already reads as a name.
    public static string NameOf(string key, Dictionary<string, string> text)
    {
        string found;
        if (text.TryGetValue(key, out found)) return AsName(found);
        foreach (string prefix in new[] { "TRES_OBJECTS_", "TRES_EQUIPMENT_" })
        {
            if (!key.StartsWith(prefix)) continue;
            string tail = key.Substring(prefix.Length);
            foreach (KeyValuePair<string, string> pair in text)
                if (pair.Key.EndsWith(tail, StringComparison.OrdinalIgnoreCase))
                    return AsName(pair.Value);
        }
        return null;
    }

    private static string AsName(string s)
    {
        if (string.IsNullOrEmpty(s) || s.Length > 60
            || s.IndexOf('\n') >= 0 || s.IndexOf('\r') >= 0) return null;
        s = s.Trim();
        return s.Length == 0 ? null : s;
    }

    /// One text resource: the magic, a version, a count, then that many records
    /// of an ordinal, the key, a string, the text, and one more string that a
    /// version 0 file does not have.
    public static IEnumerable<KeyValuePair<string, string>> ReadText(byte[] raw)
    {
        var out_ = new List<KeyValuePair<string, string>>();
        if (raw.Length < 24 || raw[0] != 0x40) return out_;
        int i = 16;
        uint version = BitConverter.ToUInt32(raw, i); i += 4;
        uint count = BitConverter.ToUInt32(raw, i); i += 4;
        for (uint n = 0; n < count; n++)
        {
            try
            {
                i += 4;
                string key = ReadString(raw, ref i);
                ReadString(raw, ref i);
                string text = ReadString(raw, ref i);
                if (version >= 1) ReadString(raw, ref i);
                out_.Add(new KeyValuePair<string, string>(key, text));
            }
            catch (Exception) { break; }
        }
        return out_;
    }
}
