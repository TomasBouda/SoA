// A console for the running game: its log on the way out, base cheats on the
// way in.
//
// The game has a command console of its own, with typed commands and help
// texts, but nothing in the shipped build opens a line to type them into - no
// action in the input table, no layout, no Windows console. See
// _research/architecture.md. What can be done instead is the two halves that
// are reachable:
//
//   out  the game writes tracefile.log next to the exe and says there what it
//        loaded, what it failed to find and why it stopped. This window tails
//        that file and translates the ASSERT_HRESULT numbers on the way.
//   in   the cheats go into the process through GameLink, the same way the
//        catalog adds items. The base ones need the base screen, the mission
//        ones a running mission.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;

using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;

internal sealed class ConsoleWindow : Window
{
    private const int MaxLines = 3000;

    private readonly string _log =
        GamePath.In("tracefile.log");

    private long _offset;
    private bool _locked;
    private StackPanel _lines;
    private ScrollViewer _scroll;
    private TextBox _input;
    private TextBox _filter;
    private CheckBox _problemsOnly;
    private TextBlock _status;
    private readonly List<KeyValuePair<string, Brush>> _all =
        new List<KeyValuePair<string, Brush>>();

    private static readonly Brush Bg = Brush("#FF191B20");
    private static readonly Brush Panel = Brush("#FF23262E");
    private static readonly Brush Line = Brush("#FF33384A");
    private static readonly Brush Text = Brush("#FFE2E4EA");
    private static readonly Brush Dim = Brush("#FF8E93A3");
    private static readonly Brush Accent = Brush("#FFC8A24A");
    private static readonly Brush Bad = Brush("#FFE06C60");
    private static readonly Brush Warn = Brush("#FFD8A657");
    private static readonly Brush Mine = Brush("#FF7FB069");

    private static SolidColorBrush Brush(string hex)
    {
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
    }

    public ConsoleWindow()
    {
        Title = "Game console";
        Width = 900;
        Height = 620;
        Background = Bg;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Content = BuildLayout();

        var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(500) };
        timer.Tick += (s, e) => { ReadNewLines(); ShowState(); };
        timer.Start();

        Loaded += (s, e) =>
        {
            Add("Log: " + _log, Dim);
            Add("Type a base cheat and press Enter, or \"help\" for the list.", Dim);
            ReadNewLines();
            ShowState();
            _input.Focus();
        };
    }

    // ----------------------------------------------------------------- layout

    private UIElement BuildLayout()
    {
        var root = new Grid { Margin = new Thickness(14) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // header
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // filter
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // input
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // status

        var header = new StackPanel();
        header.Children.Add(new TextBlock
        {
            Text = "GAME CONSOLE",
            Foreground = Accent,
            FontSize = 17,
            FontWeight = FontWeights.Bold
        });
        header.Children.Add(new TextBlock
        {
            Text = "The game's log as it is written, and cheats sent into the running "
                 + "game - the base ones on the base screen, the mission ones in a mission.",
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 3, 0, 10)
        });
        root.Children.Add(header);

        var bar = new Grid();
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(bar, 1);

        _filter = Field();
        _filter.ToolTip = "Show only the lines that contain this text";
        _filter.TextChanged += (s, e) => Redraw();
        bar.Children.Add(_filter);

        _problemsOnly = new CheckBox
        {
            Content = "problems only",
            Foreground = Dim,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(12, 0, 12, 0)
        };
        _problemsOnly.Checked += (s, e) => Redraw();
        _problemsOnly.Unchecked += (s, e) => Redraw();
        Grid.SetColumn(_problemsOnly, 1);
        bar.Children.Add(_problemsOnly);

        _phone = Button("Phone");
        _phone.ToolTip = "Answer on the local network so the console can be used "
                       + "from a phone, without leaving the game.";
        _phone.Click += (s, e) => TogglePhone();
        Grid.SetColumn(_phone, 2);
        bar.Children.Add(_phone);

        var clear = Button("Clear");
        clear.Click += (s, e) => { _all.Clear(); Redraw(); };
        Grid.SetColumn(clear, 3);
        bar.Children.Add(clear);
        root.Children.Add(bar);

        _lines = new StackPanel { Margin = new Thickness(8, 6, 8, 6) };
        _scroll = new ScrollViewer
        {
            Content = _lines,
            Background = Panel,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
            Margin = new Thickness(0, 10, 0, 10)
        };
        Grid.SetRow(_scroll, 2);
        root.Children.Add(_scroll);

        var send = new Grid();
        send.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        send.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetRow(send, 3);

        _input = Field();
        _input.FontFamily = new FontFamily("Consolas");
        _input.PreviewKeyDown += OnInputKey;
        _input.TextChanged += (s, e) =>
        {
            if (!_sending && _input.IsKeyboardFocusWithin) Suggest();
        };
        _input.LostKeyboardFocus += (s, e) => _popup.IsOpen = false;

        _choices = new ListBox
        {
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            FontFamily = new FontFamily("Consolas"),
            FontSize = 12,
            MaxHeight = 260,
        };
        _choices.MouseDoubleClick += (s, e) => Take();
        _popup = new Popup
        {
            PlacementTarget = _input,
            Placement = PlacementMode.Top,
            StaysOpen = true,
            AllowsTransparency = true,
            Child = _choices,
        };
        send.Children.Add(_input);

        var go = Button("Send");
        go.Margin = new Thickness(10, 0, 0, 0);
        go.Click += (s, e) => Send();
        Grid.SetColumn(go, 1);
        send.Children.Add(go);
        root.Children.Add(send);

        _status = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(2, 8, 0, 0),
            TextWrapping = TextWrapping.Wrap
        };
        Grid.SetRow(_status, 4);
        root.Children.Add(_status);
        return root;
    }

    private TextBox Field()
    {
        return new TextBox
        {
            Height = 30,
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            CaretBrush = Text,
            Padding = new Thickness(8, 5, 8, 5),
            FontSize = 13
        };
    }

    private Button Button(string caption)
    {
        return new Button
        {
            Content = caption,
            Height = 30,
            Width = 90,
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Cursor = Cursors.Hand
        };
    }

    // -------------------------------------------------------------- the log

    /// Reads whatever the game has appended since the last look. The file is
    /// opened with every kind of sharing, otherwise the game could not write
    /// into it while this window is open.
    private void ReadNewLines()
    {
        try
        {
            if (!File.Exists(_log)) return;
            using (var stream = new FileStream(_log, FileMode.Open, FileAccess.Read,
                                               FileShare.ReadWrite | FileShare.Delete))
            {
                // A new run of the game starts the log again from the top.
                if (stream.Length < _offset)
                {
                    _offset = 0;
                    _all.Clear();
                    Add("--- the game started again ---", Accent);
                }
                _locked = false;
                if (stream.Length == _offset) return;
                stream.Seek(_offset, SeekOrigin.Begin);
                using (var reader = new StreamReader(stream, Encoding.Default))
                {
                    string line;
                    while ((line = reader.ReadLine()) != null)
                        Add(Decorate(line), ColourOf(line));
                    _offset = stream.Position;
                }
            }
        }
        catch (IOException)
        {
            // Either the game is writing at this very moment, in which case the
            // next tick will do - or this copy of soa.exe still opens the log
            // with no sharing at all and nothing can read it while the game
            // runs. The launcher patches that on PLAY; a game started straight
            // from soa.exe keeps its log to itself.
            if (_locked) return;
            _locked = true;
            Add("The log cannot be read while the game holds it. Start the game "
                + "through the launcher - it lets the log be shared.", Warn);
        }
    }

    private static Brush ColourOf(string line)
    {
        if (line.IndexOf("TRACE_ERROR", StringComparison.Ordinal) >= 0
            || line.IndexOf("Error:", StringComparison.Ordinal) >= 0) return Bad;
        if (line.IndexOf("TRACE_WARNING", StringComparison.Ordinal) >= 0
            || line.IndexOf("Warning:", StringComparison.Ordinal) >= 0) return Warn;
        return Text;
    }

    private static bool IsProblem(string line)
    {
        Brush b = ColourOf(line);
        return b == Bad || b == Warn;
    }

    /// The game reports failures as ASSERT_HRESULT(0x...). Those numbers say
    /// nothing on their own, so the name goes right behind them - see
    /// tools/decode_error.py for the whole story.
    private static string Decorate(string line)
    {
        Match m = Regex.Match(line, @"ASSERT_HRESULT\(0x([0-9A-Fa-f]+)\)");
        if (!m.Success) return line;
        uint code;
        if (!uint.TryParse(m.Groups[1].Value, NumberStyles.HexNumber,
                           CultureInfo.InvariantCulture, out code)) return line;
        string name = DescribeHResult(code);
        return name == null ? line : line + "   = " + name;
    }

    // The DirectDraw codes we have actually met. The facility is 0x876 and the
    // low 16 bits are a decimal number from the DirectX headers, which is why
    // 0x887601C2 is 450 and not what it looks like.
    private static readonly Dictionary<int, string> DirectDraw = new Dictionary<int, string>
    {
        { 450, "DDERR_SURFACELOST" }, { 255, "DDERR_NOTFOUND" },
        { 380, "DDERR_OUTOFVIDEOMEMORY" }, { 430, "DDERR_SURFACEBUSY" },
        { 540, "DDERR_WASSTILLDRAWING" }, { 120, "DDERR_INVALIDMODE" },
        { 130, "DDERR_INVALIDOBJECT" }, { 150, "DDERR_INVALIDRECT" },
        { 587, "DDERR_WRONGMODE" }, { 694, "DDERR_D3DNOTINITIALIZED" },
    };

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern int FormatMessage(int flags, IntPtr source, uint messageId,
                                            int languageId, StringBuilder buffer, int size,
                                            IntPtr arguments);

    private static string DescribeHResult(uint code)
    {
        if ((code & 0x80000000) == 0) return "not an error";
        // The facility takes 12 bits here, not the 11 the documentation gives:
        // MAKE_DDHRESULT uses 0x876, which spills into bit 27.
        int facility = (int)((code >> 16) & 0xFFF);
        int number = (int)(code & 0xFFFF);
        if (facility == 0x876)
        {
            string name;
            return DirectDraw.TryGetValue(number, out name)
                ? name : "DirectDraw/Direct3D, number " + number;
        }
        var buffer = new StringBuilder(512);
        int n = FormatMessage(0x1000, IntPtr.Zero, code, 0, buffer, buffer.Capacity, IntPtr.Zero);
        return n > 0 ? buffer.ToString().Trim() : null;
    }

    // ------------------------------------------------------- from the phone

    // The remote answers on its own thread and reaches in through these. There
    // is no second copy of the command handling: a command sent from a phone
    // goes through the same Send() a typed one does and shows up in the window
    // exactly as if it had been typed there.
    private Remote _remote;
    private Button _phone;
    private int _produced;

    private void TogglePhone()
    {
        if (_remote != null)
        {
            _remote.Stop();
            _remote = null;
            _phone.Content = "Phone";
            Add("The phone console is off.", Dim);
            return;
        }
        _remote = new Remote(RunFromPhone, TailSince, Commands);
        string failed = _remote.Start();
        if (failed != null)
        {
            _remote = null;
            Add("  the phone console could not start: " + failed, Bad);
            return;
        }
        _phone.Content = "Phone off";
        Add("The phone console is on, listening on port " + _remote.Port + ".", Mine);
        System.Collections.Generic.List<string> addresses = Remote.LocalAddresses();
        if (addresses.Count == 0)
            Add("    no network address was found - is this machine on a network?", Bad);
        else if (addresses.Count == 1)
            Add("    http://" + addresses[0] + ":" + _remote.Port, Mine);
        else
        {
            Add("    this machine has more than one address; try them in order:", Mine);
            foreach (string a in addresses)
                Add("        http://" + a + ":" + _remote.Port, Mine);
        }
        Add("The code is " + _remote.Code + ".", Mine);
        Add("If the phone cannot reach it, the cause is almost always Windows: "
            + "an inbound connection is refused unless the network is set to "
            + "private and the firewall lets Play.exe through. The port is "
            + _remote.Port + ", not necessarily the one you saw last time - it "
            + "moves up when something else has taken it.", Dim);
    }

    /// A command from the phone, run on the window's own thread so that it takes
    /// exactly the path a typed one does. Returns what it printed.
    private string[] RunFromPhone(string command)
    {
        string[] said = null;
        Dispatcher.Invoke((Action)delegate
        {
            int before = _produced;
            _input.Text = command;
            Send();
            said = TailSince(before);
        });
        return said ?? new string[0];
    }

    /// The lines printed since the counter stood at `since`. The stored list is
    /// trimmed as it grows, so the counter counts everything ever printed and
    /// the slice is worked back from the end of what is still held.
    private string[] TailSince(int since)
    {
        string[] taken = null;
        Dispatcher.Invoke((Action)delegate
        {
            int wanted = _produced - since;
            if (wanted <= 0) { taken = new string[0]; return; }
            if (wanted > _all.Count) wanted = _all.Count;
            var lines = new List<string>(wanted);
            for (int i = _all.Count - wanted; i < _all.Count; i++)
                lines.Add(_all[i].Key);
            taken = lines.ToArray();
        });
        return taken ?? new string[0];
    }

    private void Add(string text, Brush colour)
    {
        _produced++;
        _all.Add(new KeyValuePair<string, Brush>(text, colour));
        if (_all.Count > MaxLines) _all.RemoveRange(0, _all.Count - MaxLines);
        if (Passes(text)) Append(text, colour);
        else Redraw();
    }

    private bool Passes(string text)
    {
        if (_problemsOnly.IsChecked == true && !IsProblem(text) && !text.StartsWith("> ")) return false;
        string want = (_filter.Text ?? "").Trim();
        return want.Length == 0
               || text.IndexOf(want, StringComparison.CurrentCultureIgnoreCase) >= 0;
    }

    private void Append(string text, Brush colour)
    {
        bool atBottom = _scroll.VerticalOffset >= _scroll.ScrollableHeight - 24;
        _lines.Children.Add(new TextBlock
        {
            Text = text,
            Foreground = colour,
            FontFamily = new FontFamily("Consolas"),
            FontSize = 12,
            TextWrapping = TextWrapping.NoWrap
        });
        if (_lines.Children.Count > MaxLines) _lines.Children.RemoveAt(0);
        if (atBottom) _scroll.ScrollToEnd();
    }

    private void Redraw()
    {
        _lines.Children.Clear();
        foreach (KeyValuePair<string, Brush> line in _all)
            if (Passes(line.Key))
                _lines.Children.Add(new TextBlock
                {
                    Text = line.Key,
                    Foreground = line.Value,
                    FontFamily = new FontFamily("Consolas"),
                    FontSize = 12,
                    TextWrapping = TextWrapping.NoWrap
                });
        _scroll.ScrollToEnd();
    }

    // ------------------------------------------------------------- the input

    private void ShowState()
    {
        Process game = GameLink.FindGame();
        if (game == null)
        {
            _status.Text = "The game is not running - the log is still shown, "
                         + "cheats need a running game.";
            _status.Foreground = Dim;
            return;
        }
        _status.Text = "The game is running (pid " + game.Id + ").";
        _status.Foreground = Dim;
    }

    // ------------------------------------------------------------ completion

    // The console knows every command it can send and, through catalog.txt,
    // every item number behind equipment( and vehicle(. So it offers them while
    // they are typed rather than making anyone remember - including the shape
    // with the brackets, which the game insists on and which was got wrong once
    // already.
    private Popup _popup;
    private ListBox _choices;

    // What has been sent, newest last, and where the arrows are in it. The
    // arrows walk the suggestions while those are up and the history when they
    // are not, which is the way a shell behaves.
    private readonly List<string> _history = new List<string>();
    private int _historyAt = -1;

    // Set while the input line is being cleared after sending, so that the
    // clearing does not count as typing and bring the suggestions back up.
    private bool _sending;
    private List<KeyValuePair<string, string>> _items;   // "217" -> "Night Vision Gear"

    /// Everything that can be typed, with a word about each.
    private IEnumerable<KeyValuePair<string, string>> Commands()
    {
        foreach (KeyValuePair<string, GameLink.Cheat> c in GameLink.Cheats)
            yield return new KeyValuePair<string, string>(
                c.Key + (c.Value.TakesArgument ? "(" : ""),
                c.Value.What + " - on the base screen");
        foreach (KeyValuePair<string, GameLink.Cheat> c in GameLink.MissionCheats)
            yield return new KeyValuePair<string, string>(
                c.Key + (c.Value.TakesArgument ? "(" : ""),
                c.Value.What + " - inside a mission");
        foreach (KeyValuePair<string, GameLink.Overlay> o in GameLink.Overlays)
            yield return new KeyValuePair<string, string>(
                o.Key + (o.Value.TakesUnitSize ? "(" : ""), "overlay - " + o.Value.What);
        yield return new KeyValuePair<string, string>("overlayoff", "turns the overlay off");
        yield return new KeyValuePair<string, string>(
            "loadmission(", "loads a .mis by name - not certain outside a network game");
        yield return new KeyValuePair<string, string>(
            "loadsave(", "loads a save - needs a mission running, like quickload");
        yield return new KeyValuePair<string, string>(
            "campaignui", "load missions the single player way - campaignui(0) undoes it");
        yield return new KeyValuePair<string, string>(
            "netgame", "reads the two flags the interface asks about");
        yield return new KeyValuePair<string, string>(
            "screenshot", "photographs the game - works on the menus too, where F12 does not");
        yield return new KeyValuePair<string, string>(
            "heightmap", "writes the terrain as a grey picture - heightmap(name) to choose one");
        yield return new KeyValuePair<string, string>(
            "replay", "says whether the game built itself a replay system");
        yield return new KeyValuePair<string, string>("quicksave", "into QuickSave.sav");
        yield return new KeyValuePair<string, string>("quickload", "from QuickSave.sav");
        yield return new KeyValuePair<string, string>(
            "exit", "closes this window - quitter is the one that quits the game");
        yield return new KeyValuePair<string, string>("help", "everything, in the window");
    }

    /// The item numbers, read from the same catalog.txt the catalog window uses.
    private List<KeyValuePair<string, string>> Items(string command)
    {
        if (_items == null)
        {
            _items = new List<KeyValuePair<string, string>>();
            try
            {
                string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory,
                                           "catalog.txt");
                foreach (string line in File.ReadAllLines(path))
                {
                    if (line.StartsWith("#")) continue;
                    string[] parts = line.Split('\t');
                    if (parts.Length < 4) continue;
                    _items.Add(new KeyValuePair<string, string>(
                        parts[0] + " " + parts[1], parts[3]));
                }
            }
            catch (Exception) { }
        }
        var wanted = new List<KeyValuePair<string, string>>();
        foreach (KeyValuePair<string, string> item in _items)
        {
            int space = item.Key.IndexOf(' ');
            if (item.Key.Substring(0, space) != command) continue;
            wanted.Add(new KeyValuePair<string, string>(
                item.Key.Substring(space + 1), item.Value));
        }
        return wanted;
    }

    /// Works out what to offer for the text as it stands.
    private void Suggest() { Suggest(false); }

    /// Works out what to offer. With `asked` false this is someone typing, and
    /// an empty line means nothing to offer; with it true they pressed Tab and
    /// want to see everything.
    private void Suggest(bool asked)
    {
        string typed = _input.Text ?? "";
        if (!asked && typed.Trim().Length == 0)
        {
            _popup.IsOpen = false;
            return;
        }
        var found = new List<string>();

        // Inside brackets the numbers are what is wanted, and only for the two
        // commands that have a catalog behind them.
        Match inside = Regex.Match(typed, @"^\s*([A-Za-z_]+)\s*\(\s*([^)]*)$");
        if (inside.Success)
        {
            string command = inside.Groups[1].Value.ToLowerInvariant();
            string sofar = inside.Groups[2].Value.Trim();
            if (command == "loadsave")
            {
                try
                {
                    foreach (string file in Saves())
                    {
                        string only = Path.GetFileName(file);
                        if (sofar.Length > 0
                            && only.IndexOf(sofar, StringComparison.OrdinalIgnoreCase) < 0)
                            continue;
                        found.Add(inside.Groups[1].Value + "(" + only + ")");
                    }
                }
                catch (Exception) { }
                _choices.ItemsSource = found;
                if (found.Count > 0) _choices.SelectedIndex = 0;
                _popup.IsOpen = found.Count > 0 && _input.IsKeyboardFocusWithin;
                return;
            }
            if (command == "loadmission")
            {
                foreach (string mission in GameLink.Missions)
                {
                    if (sofar.Length > 0
                        && mission.IndexOf(sofar, StringComparison.OrdinalIgnoreCase) < 0)
                        continue;
                    found.Add(inside.Groups[1].Value + "(" + mission + ")");
                }
                _choices.ItemsSource = found;
                if (found.Count > 0) _choices.SelectedIndex = 0;
                _popup.IsOpen = found.Count > 0 && _input.IsKeyboardFocusWithin;
                return;
            }
            foreach (KeyValuePair<string, string> item in Items(command))
            {
                if (sofar.Length > 0
                    && !item.Key.StartsWith(sofar, StringComparison.Ordinal)
                    && item.Value.IndexOf(sofar, StringComparison.OrdinalIgnoreCase) < 0)
                    continue;
                found.Add(inside.Groups[1].Value + "(" + item.Key + ")   " + item.Value);
                if (found.Count >= 40) break;
            }
        }
        else
        {
            string sofar = typed.Trim().ToLowerInvariant();
            foreach (KeyValuePair<string, string> c in Commands())
            {
                if (sofar.Length > 0 && !c.Key.StartsWith(sofar, StringComparison.Ordinal))
                    continue;
                found.Add(c.Key + "   " + c.Value);
                if (found.Count >= 40) break;
            }
        }

        _choices.ItemsSource = found;
        if (found.Count > 0) _choices.SelectedIndex = 0;
        _popup.IsOpen = found.Count > 0 && _input.IsKeyboardFocusWithin;
    }

    /// Puts the highlighted suggestion into the input line. The text before the
    /// two spaces is the command; what follows is only there to be read.
    private void Take()
    {
        var chosen = _choices.SelectedItem as string;
        if (chosen == null) return;
        int gap = chosen.IndexOf("   ", StringComparison.Ordinal);
        string command = gap > 0 ? chosen.Substring(0, gap) : chosen;
        _input.Text = command;
        _input.CaretIndex = command.EndsWith("(") ? command.Length : command.Length;
        _popup.IsOpen = false;
        if (command.EndsWith("(")) Suggest();
    }

    private void OnInputKey(object sender, KeyEventArgs e)
    {
        if (_popup.IsOpen)
        {
            if (e.Key == Key.Down)
            {
                _choices.SelectedIndex = Math.Min(_choices.Items.Count - 1,
                                                  _choices.SelectedIndex + 1);
                _choices.ScrollIntoView(_choices.SelectedItem);
                e.Handled = true;
                return;
            }
            if (e.Key == Key.Up)
            {
                _choices.SelectedIndex = Math.Max(0, _choices.SelectedIndex - 1);
                _choices.ScrollIntoView(_choices.SelectedItem);
                e.Handled = true;
                return;
            }
            if (e.Key == Key.Tab)
            {
                Take();
                e.Handled = true;
                return;
            }
            if (e.Key == Key.Escape)
            {
                _popup.IsOpen = false;
                e.Handled = true;
                return;
            }
        }
        else if (e.Key == Key.Tab || (e.Key == Key.Space
                                      && Keyboard.Modifiers == ModifierKeys.Control))
        {
            Suggest(true);
            e.Handled = true;
            return;
        }
        else if (e.Key == Key.Up || e.Key == Key.Down)
        {
            // No suggestions up, so the arrows walk what has been sent.
            if (_history.Count > 0)
            {
                if (_historyAt < 0) _historyAt = _history.Count;
                _historyAt += e.Key == Key.Up ? -1 : 1;
                if (_historyAt < 0) _historyAt = 0;
                if (_historyAt >= _history.Count)
                {
                    _historyAt = _history.Count;
                    _sending = true;
                    _input.Text = "";
                    _sending = false;
                }
                else
                {
                    _sending = true;
                    _input.Text = _history[_historyAt];
                    _sending = false;
                }
                _input.CaretIndex = _input.Text.Length;
            }
            e.Handled = true;
            return;
        }
        if (e.Key == Key.Return)
        {
            // Enter takes the suggestion when the list is up and only sends the
            // line when it is not, so nothing is sent by accident.
            if (_popup.IsOpen) Take();
            else Send();
            e.Handled = true;
        }
    }


    /// Every .sav under Game/SaveGames. The game keeps them one folder
    /// deeper, per profile, which is why looking straight in SaveGames finds
    /// nothing - that is what made the first try at loadsave fail.
    private static string[] Saves()
    {
        string folder = GamePath.In("SaveGames");
        try { return Directory.GetFiles(folder, "*.sav", SearchOption.AllDirectories); }
        catch (Exception) { return new string[0]; }
    }

    /// The full path of a save by name, whichever profile it is in. Anything
    /// with a separator in it is taken as a path and used as given.
    private static string FindSave(string name)
    {
        if (name.IndexOf(Path.DirectorySeparatorChar) >= 0 || name.IndexOf('/') >= 0)
            return File.Exists(name) ? name : null;
        if (!name.EndsWith(".sav", StringComparison.OrdinalIgnoreCase)) name += ".sav";
        foreach (string file in Saves())
            if (string.Equals(Path.GetFileName(file), name,
                              StringComparison.OrdinalIgnoreCase))
                return file;
        return null;
    }

    private static string Flag(int value)
    {
        return value < 0 ? "nothing (the object is not there)" : value.ToString();
    }

    private void Send()
    {
        string typed = (_input.Text ?? "").Trim();
        if (typed.Length == 0) return;
        _popup.IsOpen = false;
        _sending = true;
        _input.Clear();
        _sending = false;
        if (_history.Count == 0 || _history[_history.Count - 1] != typed)
            _history.Add(typed);
        _historyAt = _history.Count;
        Add("> " + typed, Mine);

        if (typed.Equals("help", StringComparison.OrdinalIgnoreCase))
        {
            Add("Base cheats - the game only takes these on the base screen:", Dim);
            foreach (KeyValuePair<string, GameLink.Cheat> c in GameLink.Cheats)
                Add(string.Format("    {0,-24} {1}",
                                  c.Key + (c.Value.TakesArgument ? "(number)" : ""),
                                  c.Value.What), Dim);
            Add("    the numbers for equipment and vehicle are in the catalog window", Dim);
            Add("", Dim);
            Add("Mission cheats - these only work while a mission is running:", Dim);
            foreach (KeyValuePair<string, GameLink.Cheat> c in GameLink.MissionCheats)
                Add(string.Format("    {0,-24} {1}",
                                  c.Key + (c.Value.TakesArgument ? "(number)" : ""),
                                  c.Value.What), Dim);
            Add("", Dim);
            Add("Debug overlays - drawn over the terrain during a mission:", Dim);
            foreach (KeyValuePair<string, GameLink.Overlay> o in GameLink.Overlays)
                Add(string.Format("    {0,-24} {1}",
                                  o.Key + (o.Value.TakesUnitSize ? "(unit size)" : ""),
                                  o.Value.What), Dim);
            Add("    overlayoff turns whichever is drawn off", Dim);
            Add("", Dim);
            Add("quicksave and quickload work on Game\\SaveGames\\QuickSave.sav, "
                + "the same", Dim);
            Add("file the game's own keys use. They need a running mission.", Dim);
            return;
        }

        // Written the way the game itself takes them: name(number), or just the
        // name for the ones that expect nothing.
        Match m = Regex.Match(typed, @"^([A-Za-z_]+)\s*(\(([^)]*)\))?\s*$");
        if (!m.Success)
        {
            Add("  I do not understand that. Try \"help\".", Warn);
            return;
        }
        string name = m.Groups[1].Value;
        bool hasArgument = m.Groups[2].Success;
        // Two shapes are needed. The base dispatcher insists the text it gets
        // starts with a bracket - it checks that byte itself at 0x52F533 and
        // refuses everything else - so it gets "(3)". The overlays and the
        // mission handler want the number alone.
        string brackets = hasArgument ? m.Groups[2].Value : "";
        string argument = hasArgument ? m.Groups[3].Value : "";

        GameLink.Cheat cheat;
        if (GameLink.Cheats.TryGetValue(name, out cheat))
        {
            if (cheat.TakesArgument && !hasArgument)
            {
                Add("  " + name + " wants a number in brackets, like " + name + "(3).", Warn);
                return;
            }
            uint got;
            string failed = GameLink.RunCheat(cheat.Number, brackets, out got);
            if (failed != null) { Add("  " + failed, Bad); return; }
            Add(got == 0
                    ? "  the game refused it - some things only work on a particular base screen"
                    : "  done (the game returned " + got + ")",
                got == 0 ? Warn : Mine);
            return;
        }

        if (name.Equals("loadmission", StringComparison.OrdinalIgnoreCase))
        {
            if (!hasArgument)
            {
                Add("  loadmission wants the path of a .mis in brackets, "
                    + "the way the game writes it:", Warn);
                Add(@"  loadmission(Missions\Campaign\Mission_3\Mission_3.mis)", Warn);
                return;
            }
            uint got;
            string failed = GameLink.LoadMission(argument, out got);
            if (failed != null) { Add("  " + failed, Bad); return; }
            Add("  asked the game to load " + argument, Mine);
            return;
        }

        if (name.Equals("exit", StringComparison.OrdinalIgnoreCase)
            || name.Equals("quit", StringComparison.OrdinalIgnoreCase))
        {
            // This window, not the game - quitter is the cheat that ends the
            // game, and it would be a poor surprise to have them share a word.
            Close();
            return;
        }

        if (name.Equals("campaignui", StringComparison.OrdinalIgnoreCase))
        {
            if (hasArgument)
            {
                int on;
                if (!int.TryParse(argument, out on))
                {
                    Add("  campaignui wants 0 or 1 in brackets, or nothing to read it.", Warn);
                    return;
                }
                GameLink.LoadAsCampaign = on != 0;
            }
            Add("  loading a mission asks for it "
                + (GameLink.LoadAsCampaign ? "the way single player does"
                                           : "the way a network host does")
                + " - it takes effect on the next loadmission", Mine);
            return;
        }

        if (name.Equals("netgame", StringComparison.OrdinalIgnoreCase))
        {
            int set = -1;
            if (hasArgument && !int.TryParse(argument, out set))
            {
                Add("  netgame wants 0 or 1 in brackets, or nothing to just read.", Warn);
                return;
            }
            int[] flags;
            string failed = GameLink.NetworkFlags(set, out flags);
            if (failed != null) { Add("  " + failed, Bad); return; }
            Add("  the network object says " + Flag(flags[0])
                + ", the session object says " + Flag(flags[1]), Mine);
            Add("  either one being 1 makes the interface the network one", Dim);
            return;
        }

        if (name.Equals("loadsave", StringComparison.OrdinalIgnoreCase))
        {
            if (!hasArgument)
            {
                Add("  loadsave wants the name of a save in brackets, like "
                    + "loadsave(QuickSave.sav).", Warn);
                return;
            }
            // A bare name means the game's own SaveGames folder; the loader
            // itself wants the whole path, which is what quick load hands it.
            string save = FindSave(argument);
            if (save == null)
            {
                Add("  no save of that name under Game, SaveGames or a profile folder in it.", Warn);
                return;
            }
            uint got;
            string failed = GameLink.LoadSave(save, out got);
            if (failed != null) { Add("  " + failed, Bad); return; }
            Add("  asked the game to load " + save, Mine);
            return;
        }

        if (name.Equals("quicksave", StringComparison.OrdinalIgnoreCase)
            || name.Equals("quickload", StringComparison.OrdinalIgnoreCase))
        {
            bool saving = name.Equals("quicksave", StringComparison.OrdinalIgnoreCase);
            uint got;
            string failed = saving ? GameLink.QuickSave(out got) : GameLink.QuickLoad(out got);
            if (failed != null) { Add("  " + failed, Bad); return; }
            Add(saving ? "  saved to Game\\SaveGames\\QuickSave.sav"
                       : "  loaded Game\\SaveGames\\QuickSave.sav", Mine);
            return;
        }

        if (name.Equals("screenshot", StringComparison.OrdinalIgnoreCase))
        {
            uint shot;
            string bad = GameLink.Screenshot(out shot);
            if (bad != null) { Add("  " + bad, Bad); return; }
            Add("  taken - Game\\shot0000.png and upwards, counting to the first free name.", Mine);
            return;
        }

        if (name.Equals("heightmap", StringComparison.OrdinalIgnoreCase))
        {
            // The bounds decide what the grey is stretched between. Zero and a
            // hundred cover the campaign maps, whose coarse height grid runs
            // well inside that, and they can be given if a map needs more.
            float low = 0, high = 100;
            string[] bounds = (argument ?? "").Split(',');
            string file = bounds.Length > 0 && bounds[0].Trim().Length > 0
                        ? bounds[0].Trim() : "heightmap.png";
            if (bounds.Length >= 3)
            {
                float.TryParse(bounds[1].Trim(), NumberStyles.Float,
                               CultureInfo.InvariantCulture, out low);
                float.TryParse(bounds[2].Trim(), NumberStyles.Float,
                               CultureInfo.InvariantCulture, out high);
            }
            if (file.IndexOf(Path.DirectorySeparatorChar) < 0 && file.IndexOf('/') < 0)
                file = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, file);
            uint wrote;
            string bad = GameLink.SaveHeightMap(file, low, high, out wrote);
            if (bad != null) { Add("  " + bad, Bad); return; }
            Add("  wrote " + file, Mine);
            Add("  heights stretched between " + low.ToString(CultureInfo.InvariantCulture)
                + " and " + high.ToString(CultureInfo.InvariantCulture)
                + " - heightmap(name, low, high) to change that.", Dim);
            return;
        }

        if (name.Equals("replay", StringComparison.OrdinalIgnoreCase))
        {
            bool? has = GameLink.HasReplaySystem();
            if (has == null) { Add("  the game is not running.", Bad); return; }
            Add(has.Value
                ? "  there is a replay system - the global at 0x874AE0 is not null."
                : "  no replay system - the global at 0x874AE0 is null, which is what "
                + "EventRecorder and Replay complain about.", has.Value ? Mine : Dim);
            return;
        }

        if (name.Equals("overlayoff", StringComparison.OrdinalIgnoreCase))
        {
            string off = GameLink.ShowOverlay(null, 0);
            Add(off ?? "  off", off == null ? Mine : Bad);
            return;
        }

        GameLink.Overlay overlay;
        if (GameLink.Overlays.TryGetValue(name, out overlay))
        {
            int unitSize = 1;
            if (hasArgument && !int.TryParse(argument, out unitSize))
            {
                Add("  " + name + " wants a number in brackets, like " + name + "(2).", Warn);
                return;
            }
            // The game builds the overlay object and hangs it on the renderer;
            // this does the same from outside. It runs in the middle of the
            // render loop, so it is the one thing here that can take the game
            // down - worth a save first.
            string failed = GameLink.ShowOverlay(name, unitSize);
            if (failed != null) { Add("  " + failed, Bad); return; }
            Add("  on - " + overlay.What + "; overlayoff turns it back", Mine);
            return;
        }

        GameLink.Cheat mission;
        if (GameLink.MissionCheats.TryGetValue(name, out mission))
        {
            if (mission.TakesArgument && !hasArgument)
            {
                Add("  " + name + " wants something in brackets, like " + name + "(1).", Warn);
                return;
            }
            uint got;
            // The whole line goes in as it was typed - the handler in the game
            // matches the name itself.
            string failed = GameLink.RunMissionCheat(typed, out got);
            if (failed != null) { Add("  " + failed, Bad); return; }
            Add((got & 0xFF) == 0
                    ? "  the game did not take it"
                    : "  done",
                (got & 0xFF) == 0 ? Warn : Mine);
            return;
        }

        Add("  \"" + name + "\" is not a cheat I know. Try \"help\".", Warn);
    }
}
