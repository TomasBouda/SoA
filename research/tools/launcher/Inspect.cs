// One object of the running game, word by word, refreshed while you watch.
//
// The map window shows where things are; this shows what they are made of.
// Double-clicking a unit on the map opens it here, and the same window takes a
// typed address, so anything found by other means - find_units.py, a vtable
// scan, a pointer read out of another object - can be looked at too.
//
// It reads and never writes. The columns are the same three readings that
// diff_memory.py prints, for the same reason: a word is an int, a float or a
// pointer, and which of the three it is only becomes clear from what the
// numbers do. Words that changed since the last refresh are marked, because a
// field that moves while a unit walks is a field worth a name.
//
// The few offsets we do have names for are labelled from GameLink.UnitFields.
// Everything else is deliberately left bare.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

internal sealed class InspectWindow : Window
{
    private static readonly Brush Bg = Brush("#FF191B20");
    private static readonly Brush Panel = Brush("#FF23262E");
    private static readonly Brush Line = Brush("#FF33384A");
    private static readonly Brush Text = Brush("#FFE6E8EE");
    private static readonly Brush Dim = Brush("#FF8E93A3");
    private static readonly Brush Accent = Brush("#FFC8A24A");
    private static readonly Brush Moved = Brush("#FF7FB2E5");

    private static SolidColorBrush Brush(string hex)
    {
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
    }

    private readonly TextBox _address;
    private readonly TextBlock _status;
    private readonly StackPanel _rows;
    private readonly ComboBox _size;
    private readonly CheckBox _onlyMoved;
    private readonly DispatcherTimer _timer;

    private uint _at;
    private readonly HashSet<int> _everMoved = new HashSet<int>();

    public InspectWindow(uint address)
    {
        Title = "Object";
        Width = 460;
        Height = 620;
        Background = Bg;
        Foreground = Text;
        FontFamily = new FontFamily("Segoe UI");
        WindowStartupLocation = WindowStartupLocation.CenterOwner;

        var root = new DockPanel { Margin = new Thickness(14) };

        var top = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 0, 10) };
        top.Children.Add(new TextBlock
        {
            Text = "at",
            Foreground = Dim,
            FontSize = 12,
            Margin = new Thickness(0, 0, 8, 0),
            VerticalAlignment = VerticalAlignment.Center
        });
        _address = new TextBox
        {
            Width = 100,
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            FontFamily = new FontFamily("Consolas"),
            Text = address.ToString("X8"),
            VerticalContentAlignment = VerticalAlignment.Center,
            Height = 26
        };
        _address.KeyDown += (s, e) =>
        {
            if (e.Key == System.Windows.Input.Key.Return) Retarget();
        };
        top.Children.Add(_address);

        _size = new ComboBox { Width = 92, Height = 26, Margin = new Thickness(8, 0, 0, 0) };
        foreach (string s in new[] { "0x100", "0x200", "0x400", "0x800" }) _size.Items.Add(s);
        _size.SelectedIndex = 1;
        _size.SelectionChanged += (s, e) => { _now = null; _everMoved.Clear(); Refresh(); };
        top.Children.Add(_size);

        _onlyMoved = new CheckBox
        {
            Content = "only what moves",
            Foreground = Dim,
            FontSize = 12,
            Margin = new Thickness(10, 0, 0, 0),
            VerticalAlignment = VerticalAlignment.Center,
            ToolTip = "Hide every word that has held still since this window opened. "
                    + "What is left is the part of the object that is alive."
        };
        _onlyMoved.Checked += (s, e) => Draw();
        _onlyMoved.Unchecked += (s, e) => Draw();
        top.Children.Add(_onlyMoved);

        DockPanel.SetDock(top, Dock.Top);
        root.Children.Add(top);

        _status = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 8, 0, 0),
            TextWrapping = TextWrapping.Wrap
        };
        DockPanel.SetDock(_status, Dock.Bottom);
        root.Children.Add(_status);

        _rows = new StackPanel();
        var scroll = new ScrollViewer
        {
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Background = Panel,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Padding = new Thickness(8),
            Content = _rows
        };
        root.Children.Add(scroll);

        Content = root;
        _at = address;

        // Twice a second is enough to see a field follow a unit across the map
        // without the list flickering so much it cannot be read.
        _timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(500) };
        _timer.Tick += (s, e) => Refresh();
        _timer.Start();
        Closed += (s, e) => _timer.Stop();

        Refresh();
    }

    private void Retarget()
    {
        uint parsed;
        string text = _address.Text.Trim().Replace("0x", "").Replace("0X", "");
        if (!uint.TryParse(text, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out parsed))
        {
            _status.Text = "That is not a hexadecimal address.";
            return;
        }
        _at = parsed;
        _now = null;
        _everMoved.Clear();
        Refresh();
    }

    private byte[] _now;

    private void Refresh()
    {
        int size = int.Parse(((string)_size.SelectedItem).Substring(2),
                             NumberStyles.HexNumber, CultureInfo.InvariantCulture);
        byte[] raw = GameLink.ReadObject(_at, size);
        if (raw == null)
        {
            _status.Text = GameLink.FindGame() == null
                ? "The game is not running."
                : "Nothing readable at " + _at.ToString("X8") + ".";
            return;
        }
        if (_now != null && _now.Length == raw.Length)
            for (int i = 0; i + 3 < raw.Length; i += 4)
                if (BitConverter.ToUInt32(raw, i) != BitConverter.ToUInt32(_now, i))
                    _everMoved.Add(i);
        _now = raw;
        Draw();
    }

    private void Draw()
    {
        byte[] raw = _now;
        if (raw == null) return;
        bool onlyMoved = _onlyMoved.IsChecked == true;

        _rows.Children.Clear();
        int shown = 0;
        for (int off = 0; off + 3 < raw.Length; off += 4)
        {
            if (onlyMoved && !_everMoved.Contains(off)) continue;
            shown++;
            _rows.Children.Add(RowFor(raw, off));
        }
        _status.Text = string.Format(
            "{0} words, {1} of them have moved since this opened.{2}",
            raw.Length / 4, _everMoved.Count,
            onlyMoved && shown == 0 ? "  Nothing has moved yet - give it a moment." : "");
    }

    private UIElement RowFor(byte[] raw, int off)
    {
        uint v = BitConverter.ToUInt32(raw, off);
        int i = BitConverter.ToInt32(raw, off);
        float f = BitConverter.ToSingle(raw, off);

        string reading;
        if (v > 0x10000 && v < 0x7F000000 && (v & 3) == 0)
            reading = "-> " + v.ToString("X8");
        else if (Math.Abs(f) > 1e-3 && Math.Abs(f) < 1e7)
            reading = f.ToString("0.###", CultureInfo.InvariantCulture);
        else
            reading = i.ToString(CultureInfo.InvariantCulture);

        string label;
        GameLink.UnitFields.TryGetValue((uint)off, out label);

        var line = new TextBlock
        {
            FontFamily = new FontFamily("Consolas"),
            FontSize = 12,
            Margin = new Thickness(0, 1, 0, 1),
            Foreground = _everMoved.Contains(off) ? Moved : (label != null ? Accent : Text),
            Text = string.Format("+{0:X3}  {1:X8}  {2,-16} {3}",
                                 off, v, reading, label ?? "")
        };
        return line;
    }
}
