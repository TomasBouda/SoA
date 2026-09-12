// The keys editor: every action the game can bind, with its two keys,
// read from and written to the registry the game reads at startup.
//
// The game keeps its bindings under
// HKCU\Software\Silver Style Entertainment\Soldiers of Anarchy\Settings as
// AK<id>_1 and AK<id>_2, the id in hexadecimal (the format string is
// "AK%X_1" at 0x866C98), one DWORD each: a virtual-key code, or 0x80000000
// plus a mouse button - 0 left, 1 right, 2 middle, 3 wheel down, 4 wheel
// up - or 0xFFFFFFFF for nothing. The 67 actions and their defaults are the
// exe's own table at 0x865820, generated into KeysData.cs.
//
// The game reads the keys when it starts and writes its own when it exits,
// so the editor works on a closed game: with soa.exe running the rows are
// shown but locked, or a change would be undone the moment the game closes.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Microsoft.Win32;

internal sealed class KeyAction
{
    public readonly uint Id;
    public readonly string Name;      // AK_PANLEFT
    public readonly string Text;      // what the game's own key help calls it
    public readonly uint Default1, Default2;
    public readonly string Group;

    public KeyAction(uint id, string name, string text, uint default1, uint default2, string group)
    {
        Id = id; Name = name; Text = text; Default1 = default1; Default2 = default2; Group = group;
    }

    public string RegName(int slot) { return "AK" + Id.ToString("X") + "_" + slot; }
}

internal static class KeyNames
{
    public const uint None = 0xFFFFFFFF;
    public const uint Mouse = 0x80000000;

    private static readonly Dictionary<uint, string> Named = new Dictionary<uint, string>
    {
        { 0x08, "Backspace" }, { 0x09, "Tab" }, { 0x0D, "Enter" }, { 0x10, "Shift" }, { 0x11, "Ctrl" },
        { 0x12, "Alt" }, { 0x13, "Pause" }, { 0x14, "Caps Lock" }, { 0x1B, "Esc" }, { 0x20, "Space" },
        { 0x21, "Page Up" }, { 0x22, "Page Down" }, { 0x23, "End" }, { 0x24, "Home" }, { 0x25, "Left" },
        { 0x26, "Up" }, { 0x27, "Right" }, { 0x28, "Down" }, { 0x2C, "Print Screen" }, { 0x2D, "Insert" },
        { 0x2E, "Delete" }, { 0x6A, "Num *" }, { 0x6B, "Num +" }, { 0x6D, "Num -" }, { 0x6E, "Num ." },
        { 0x6F, "Num /" }, { 0x90, "Num Lock" }, { 0x91, "Scroll Lock" }, { 0xA0, "Left Shift" },
        { 0xA1, "Right Shift" }, { 0xA2, "Left Ctrl" }, { 0xA3, "Right Ctrl" }, { 0xA4, "Left Alt" },
        { 0xA5, "Right Alt" }, { 0xBA, ";" }, { 0xBB, "=" }, { 0xBC, "," }, { 0xBD, "-" }, { 0xBE, "." },
        { 0xBF, "/" }, { 0xC0, "`" }, { 0xDB, "[" }, { 0xDC, "\\" }, { 0xDD, "]" }, { 0xDE, "'" },
        { Mouse + 0, "Left click" }, { Mouse + 1, "Right click" }, { Mouse + 2, "Middle click" },
        { Mouse + 3, "Wheel down" }, { Mouse + 4, "Wheel up" },
    };

    public static string Of(uint code)
    {
        if (code == None) return "-";
        string s;
        if (Named.TryGetValue(code, out s)) return s;
        if (code >= 0x30 && code <= 0x39) return ((char)code).ToString();
        if (code >= 0x41 && code <= 0x5A) return ((char)code).ToString();
        if (code >= 0x60 && code <= 0x69) return "Num " + (code - 0x60);
        if (code >= 0x70 && code <= 0x87) return "F" + (code - 0x6F);
        if (code >= Mouse) return "Mouse " + (code - Mouse);
        return "0x" + code.ToString("X");
    }
}

internal sealed class KeysWindow : Window
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

    private const string RegKey = @"Software\Silver Style Entertainment\Soldiers of Anarchy\Settings";

    private sealed class Slot
    {
        public KeyAction Action;
        public int Number;          // 1 or 2
        public Button Button;
        public uint Code;
    }

    private readonly List<Slot> _slots = new List<Slot>();
    private readonly Dictionary<KeyAction, Button> _resets = new Dictionary<KeyAction, Button>();
    private Slot _listening;
    private TextBlock _status;
    private bool _locked;

    public KeysWindow()
    {
        Title = "Keys";
        Width = 600;
        Height = 760;
        MinWidth = 520;
        MinHeight = 400;
        Background = Bg;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Content = BuildLayout();
        Loaded += (s, e) => Refresh();
        Activated += (s, e) => { if (_listening == null) Refresh(); };   // the game may have written its own
        PreviewKeyDown += OnKey;
        PreviewMouseDown += OnMouse;
        PreviewMouseWheel += OnWheel;
        Deactivated += (s, e) => StopListening();
    }

    private UIElement BuildLayout()
    {
        var root = new DockPanel { Margin = new Thickness(22, 16, 22, 14) };

        var head = new StackPanel();
        DockPanel.SetDock(head, Dock.Top);
        head.Children.Add(new TextBlock
        {
            Text = "KEYS",
            Foreground = Accent,
            FontSize = 17,
            FontWeight = FontWeights.Bold,
        });
        head.Children.Add(new TextBlock
        {
            Text = "Every action the game can bind, with its two keys. Click a key, press the "
                 + "one you want - a mouse button and the wheel count too - Delete to clear it, "
                 + "Esc to keep it. Written the moment it is pressed, into the registry the game "
                 + "reads when it starts; the game has to be closed, it writes its own keys back "
                 + "when it exits.",
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 3, 0, 10),
        });
        root.Children.Add(head);

        var foot = new DockPanel { Margin = new Thickness(0, 8, 0, 0) };
        DockPanel.SetDock(foot, Dock.Bottom);
        Button defaults = Small("Restore the game's defaults", "Every action back to the keys the game shipped with");
        defaults.Click += (s, e) => RestoreDefaults();
        DockPanel.SetDock(defaults, Dock.Right);
        foot.Children.Add(defaults);
        _status = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(0, 0, 12, 0),
        };
        foot.Children.Add(_status);
        root.Children.Add(foot);

        var list = new StackPanel();
        string group = null;
        foreach (KeyAction a in KeysData.All)
        {
            if (a.Group != group)
            {
                group = a.Group;
                list.Children.Add(new TextBlock
                {
                    Text = group.ToUpperInvariant(),
                    Foreground = Accent,
                    FontSize = 11,
                    FontWeight = FontWeights.SemiBold,
                    Margin = new Thickness(0, 10, 0, 4),
                });
            }
            list.Children.Add(Row(a));
        }
        var scroll = new ScrollViewer
        {
            Content = list,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
        };
        root.Children.Add(scroll);
        return root;
    }

    private UIElement Row(KeyAction a)
    {
        var grid = new Grid { Margin = new Thickness(0, 0, 0, 3) };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(130) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(130) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(30) });

        var label = new TextBlock
        {
            Text = Pretty(a.Text),
            Foreground = Text,
            FontSize = 12,
            VerticalAlignment = VerticalAlignment.Center,
            ToolTip = a.Name + "  (AK" + a.Id.ToString("X") + ")",
        };
        grid.Children.Add(label);

        for (int n = 1; n <= 2; n++)
        {
            var slot = new Slot { Action = a, Number = n };
            var b = new Button
            {
                Height = 24,
                FontSize = 11,
                Margin = new Thickness(6, 0, 0, 0),
                Background = Panel,
                Foreground = Text,
                BorderBrush = Line,
                BorderThickness = new Thickness(1),
                Tag = slot,
                HorizontalContentAlignment = HorizontalAlignment.Center,
            };
            b.Click += (s, e) => StartListening((Slot)((Button)s).Tag);
            slot.Button = b;
            _slots.Add(slot);
            Grid.SetColumn(b, n);
            grid.Children.Add(b);
        }

        var reset = new Button
        {
            Content = new TextBlock { Text = "\uE72C", FontFamily = new FontFamily("Segoe MDL2 Assets"), FontSize = 11 },
            Width = 24,
            Height = 24,
            Margin = new Thickness(6, 0, 0, 0),
            Background = Panel,
            Foreground = Dim,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            ToolTip = "Back to the game's default, " + KeyNames.Of(a.Default1)
                    + (a.Default2 == KeyNames.None ? "" : " and " + KeyNames.Of(a.Default2)),
            Visibility = Visibility.Hidden,
        };
        reset.Click += (s, e) => { Write(a, 1, a.Default1); Write(a, 2, a.Default2); Refresh(); };
        _resets[a] = reset;
        Grid.SetColumn(reset, 3);
        grid.Children.Add(reset);
        return grid;
    }

    private Button Small(string text, string tip)
    {
        return new Button
        {
            Content = text,
            Height = 26,
            FontSize = 11,
            Padding = new Thickness(10, 0, 10, 0),
            Background = Panel,
            Foreground = Dim,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            ToolTip = tip,
        };
    }

    /// "PAN LEFT" the way the game's help shows it, "Pan left" here.
    private static string Pretty(string text)
    {
        string lower = text.ToLowerInvariant();
        return char.ToUpperInvariant(lower[0]) + lower.Substring(1);
    }

    // ------------------------------------------------------------ registry

    private static uint Read(KeyAction a, int slot)
    {
        using (RegistryKey k = Registry.CurrentUser.OpenSubKey(RegKey))
        {
            object v = k == null ? null : k.GetValue(a.RegName(slot));
            if (v is int) return unchecked((uint)(int)v);
            return slot == 1 ? a.Default1 : a.Default2;
        }
    }

    private static void Write(KeyAction a, int slot, uint code)
    {
        using (RegistryKey k = Registry.CurrentUser.CreateSubKey(RegKey))
            if (k != null) k.SetValue(a.RegName(slot), unchecked((int)code), RegistryValueKind.DWord);
    }

    private void Refresh()
    {
        _locked = Process.GetProcessesByName("soa").Length > 0;
        foreach (Slot s in _slots)
        {
            s.Code = Read(s.Action, s.Number);
            s.Button.Content = KeyNames.Of(s.Code);
            s.Button.IsEnabled = !_locked;
        }
        foreach (KeyValuePair<KeyAction, Button> kv in _resets)
        {
            bool changed = Read(kv.Key, 1) != kv.Key.Default1 || Read(kv.Key, 2) != kv.Key.Default2;
            kv.Value.Visibility = changed ? Visibility.Visible : Visibility.Hidden;
            kv.Value.IsEnabled = !_locked;
        }
        MarkConflicts();
        _status.Text = _locked
            ? "The game is running - close it first, it writes its own keys back when it exits."
            : "Read from the registry. The game takes the keys when it starts.";
        _status.Foreground = _locked ? Bad : Dim;
    }

    /// The same key on two actions: both turn red. The game does not stop
    /// it, it just answers both, which is rarely what anyone wants.
    private void MarkConflicts()
    {
        var owners = new Dictionary<uint, int>();
        foreach (Slot s in _slots)
            if (s.Code != KeyNames.None)
                owners[s.Code] = owners.ContainsKey(s.Code) ? owners[s.Code] + 1 : 1;
        foreach (Slot s in _slots)
        {
            bool twice = s.Code != KeyNames.None && owners[s.Code] > 1;
            s.Button.Foreground = twice ? Bad : Text;
            s.Button.ToolTip = twice ? KeyNames.Of(s.Code) + " is bound to more than one action" : null;
        }
    }

    // ----------------------------------------------------------- listening

    private void StartListening(Slot slot)
    {
        if (_locked) return;
        StopListening();
        _listening = slot;
        slot.Button.Content = "press a key...";
        slot.Button.Foreground = Accent;
        slot.Button.BorderBrush = Accent;
        _status.Text = "Listening for " + Pretty(slot.Action.Text) + ": a key, a mouse button or the wheel. Delete clears, Esc keeps.";
        _status.Foreground = Accent;
    }

    private void StopListening()
    {
        if (_listening == null) return;
        Slot s = _listening;
        _listening = null;
        s.Button.BorderBrush = Line;
        Refresh();
    }

    private void Take(uint code)
    {
        Slot s = _listening;
        if (s == null) return;
        _listening = null;
        s.Button.BorderBrush = Line;
        Write(s.Action, s.Number, code);
        Refresh();
        _status.Text = Pretty(s.Action.Text) + " is now " + KeyNames.Of(code) + (s.Number == 2 ? " (second key)" : "") + ".";
    }

    private void OnKey(object sender, KeyEventArgs e)
    {
        if (_listening == null) return;
        e.Handled = true;
        Key key = e.Key == Key.System ? e.SystemKey : e.Key;
        if (key == Key.Escape) { StopListening(); return; }
        if (key == Key.Delete || key == Key.Back) { Take(KeyNames.None); return; }
        int vk = KeyInterop.VirtualKeyFromKey(key);
        // the game binds the plain modifier, not its left or right half
        if (vk == 0xA0 || vk == 0xA1) vk = 0x10;
        if (vk == 0xA2 || vk == 0xA3) vk = 0x11;
        if (vk == 0xA4 || vk == 0xA5) vk = 0x12;
        if (vk > 0) Take((uint)vk);
    }

    private void OnMouse(object sender, MouseButtonEventArgs e)
    {
        if (_listening == null) return;
        // the right and middle buttons bind wherever they are pressed; the
        // left one only on the button that is listening - anywhere else it
        // is a click, on another key button or on nothing
        var over = e.OriginalSource as DependencyObject;
        while (over != null && !(over is Button)) over = VisualTreeHelper.GetParent(over);
        if (e.ChangedButton == MouseButton.Left)
        {
            if (over == _listening.Button) { e.Handled = true; Take(KeyNames.Mouse + 0); }
            else if (over is Button && ((Button)over).Tag is Slot) { }        // its Click starts listening there
            else StopListening();
            return;
        }
        e.Handled = true;
        switch (e.ChangedButton)
        {
            case MouseButton.Right: Take(KeyNames.Mouse + 1); break;
            case MouseButton.Middle: Take(KeyNames.Mouse + 2); break;
            default: StopListening(); break;
        }
    }

    private void OnWheel(object sender, MouseWheelEventArgs e)
    {
        if (_listening == null) return;
        e.Handled = true;
        Take(e.Delta < 0 ? KeyNames.Mouse + 3 : KeyNames.Mouse + 4);
    }

    private void RestoreDefaults()
    {
        if (_locked) return;
        if (MessageBox.Show(this, "Every action back to the keys the game shipped with?", "Keys",
                            MessageBoxButton.OKCancel, MessageBoxImage.Question) != MessageBoxResult.OK)
            return;
        foreach (KeyAction a in KeysData.All)
        {
            Write(a, 1, a.Default1);
            Write(a, 2, a.Default2);
        }
        Refresh();
        _status.Text = "The game's defaults are back.";
    }
}
