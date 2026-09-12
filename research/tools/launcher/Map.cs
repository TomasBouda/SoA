// The map of the running mission, in a window of its own.
//
// The game draws the debug overlays over the terrain, which is of little use
// while it runs full screen. But the overlays read a plain array - one dword
// per map cell - and so can anything else: GameLink.ReadMap copies the whole
// array out of the running game several times a second and this window paints
// it. Nothing is written back, nothing is injected; the game does not know.
//
// The bits are the ones the overlays ask for, each with its own query method in
// the exe (the addresses are in _research/architecture.md):
//
//     0x00000008  air
//     0x000000F0  an object stands here, the bits are its size
//     0x00000F00  which party the unit standing here belongs to
//     0x00010000  a structure
//     0x00060000  the ground type, two bits
//     0x00200000  smoke
//
// One dword is one world unit, so a campaign map is 1200x1200 of them - the
// 75x75 cells of the .mis file times the sixteen units a cell is across.
//
// The terrain, the structures and the objects are there from the start. The
// units are not: they are in the array only where the party can see them at
// that moment and go again when it walks away, which map_bits.py --watch
// confirmed by counting what appears and disappears between two readings. So
// the unit layer is live line of sight, not a map that fills in as it is
// explored.
//
// The height is not in that array; it comes from the grid the path manager
// keeps for itself, which is the coarse one: one value to sixteen units, which
// GameLink reads once per mission. It is drawn the way a relief map is - the
// ground type gives the colour, the height gives the brightness and the slope
// towards the north-west is lit - with the heights interpolated so the shading
// does not come out in squares of sixteen.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using System.Threading;

internal sealed class MapWindow : Window
{
    private static readonly Brush Bg = Brush("#FF191B20");
    private static readonly Brush Panel = Brush("#FF23262E");
    private static readonly Brush Line = Brush("#FF33384A");
    private static readonly Brush Dim = Brush("#FF8E93A3");
    private static readonly Brush Accent = Brush("#FFC8A24A");
    private static readonly Brush Bad = Brush("#FFE06C60");

    private static SolidColorBrush Brush(string hex)
    {
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
    }

    private Image _image;
    private ScrollViewer _view;
    private WriteableBitmap _bitmap;

    // Zero means the whole map fits the window; anything else is that many
    // screen pixels to a world unit. A campaign map is 1200 across, so a window
    // shows it at about half - the wheel is the way to get in closer.
    private double _zoom;
    private Point _drag;
    private bool _dragging;
    private TextBlock _status;
    private TextBlock _hover;
    private CheckBox _party, _structures, _objects, _air, _extra, _relief;
    private WrapPanel _legend;

    // Which party the player is. Read from the game rather than assumed,
    // because it is not the same number in every mission.
    private int _mine;
    private int _legendMine = -1;

    // The units read out of the objects rather than out of the cell array.
    // Finding them means walking the game's whole memory, so it is done rarely
    // and only their positions are read on every tick.
    private List<GameLink.Unit> _units = new List<GameLink.Unit>();
    private bool _scanning;
    private int _ticks;

    // The nibble at 0x00000F00 is the number of the party the unit belongs to,
    // which is what the game's own name for the overlay - "Shows/Hides party
    // information" - said all along. It took a while to believe: the values a
    // mission shows (1, 2, 3, 4, 5, 6, 8, 9) all break down into 1|2|4|8, so
    // they read as four flags for a while, and a Hammer and the soldiers next
    // to it seemed to carry different ones.
    //
    // What settled it was counting the classes against the numbers in a
    // running mission (tools/find_units.py): the class of a unit object is its
    // type, and one class turns up under four different numbers. A type cannot
    // be both, so the number is the party. In one campaign mission there were
    // eight of them, the player being 2 - which one the player is depends on
    // the mission, so they are drawn by number and named by nobody.
    //
    // A cell takes the numbers of everything standing on it ORed together, so
    // where two parties touch, the colour is of neither. That is rare: a cell
    // is one world unit.
    private static readonly uint[] Parties =
    {
        0xFF000000,   // 0 - nothing stands here
        0xFF7FE06C,   // 1
        0xFF5AB6E0,   // 2
        0xFFE0B84A,   // 3
        0xFFE06C60,   // 4
        0xFFB98CE0,   // 5
        0xFFE08A4A,   // 6
        0xFF6CE0D2,   // 7
        0xFFE0D96C,   // 8
        0xFFE06CB0,   // 9
        0xFF8CA0E0,   // 10
        0xFF9CE08C,   // 11
        0xFFC0C0C0,   // 12
        0xFFE0A0A0,   // 13
        0xFFA0E0E0,   // 14
        0xFFFFFFFF,   // 15
    };

    private GameLink.MapSnapshot _map;

    // Armed, the next click on the map calls the air strike on that point
    // instead of starting a drag. It disarms itself after one strike, and Esc
    // disarms it, so a stray click cannot bomb the party twice.
    private bool _strikeArmed;
    private Button _strike;
    private TextBlock _note;

    // Where the bombs were sent, so the map can show it. A marker stays for
    // about as long as the plane is out - it comes back to the hangar after
    // half a minute or so - and then goes on its own.
    private struct Strike { public float X, Y; public DateTime When; }
    private readonly List<Strike> _strikes = new List<Strike>();
    private static readonly TimeSpan StrikeShown = TimeSpan.FromSeconds(45);

    public MapWindow()
    {
        Title = "Mission map";
        Width = 720;
        Height = 780;
        Background = Bg;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Content = BuildLayout();

        // The array is 5.8 MB on a campaign map, so this reads a little slower
        // than it could - often enough to watch the party move, rare enough not
        // to be a cost.
        InputBindings.Add(new KeyBinding(new Command(Copy), Key.C, ModifierKeys.Control));
        InputBindings.Add(new KeyBinding(new Command(() => ArmStrike(false)), Key.Escape, ModifierKeys.None));

        var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(600) };
        timer.Tick += (s, e) => Refresh();
        timer.Start();
        Loaded += (s, e) => { Refresh(); Scan(true); };
    }

    // ----------------------------------------------------------------- layout

    private UIElement BuildLayout()
    {
        var root = new Grid { Margin = new Thickness(14) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // header
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // layers
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // zoom
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // status

        var header = new StackPanel();
        header.Children.Add(new TextBlock
        {
            Text = "MISSION MAP",
            Foreground = Accent,
            FontSize = 17,
            FontWeight = FontWeights.Bold
        });
        header.Children.Add(new TextBlock
        {
            Text = "What the engine walks on, read straight out of the running game. "
                 + "Nothing is written back, unless you arm the air strike. Units show "
                 + "only where the party can see right now.",
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 3, 0, 10)
        });
        Grid.SetRow(header, 0);
        root.Children.Add(header);

        var layers = new WrapPanel { Margin = new Thickness(0, 0, 0, 8) };
        _party = Layer(layers, "Units", true);
        _structures = Layer(layers, "Structures", true);
        _objects = Layer(layers, "Objects", true);
        _air = Layer(layers, "Air", false);
        _extra = Layer(layers, "Smoke", false);
        _relief = Layer(layers, "Relief", true);
        // There was an "All units" layer here that drew the units read out of
        // the objects. It went: the party layer already draws everything the
        // cell array knows, and a second set of dots over the top of it said
        // nothing a person could use. The units themselves are still read -
        // they are what the hover line names and what the inspector opens -
        // they are simply not painted anymore.
        _legend = new WrapPanel { VerticalAlignment = VerticalAlignment.Center };
        layers.Children.Add(_legend);
        Grid.SetRow(layers, 1);
        root.Children.Add(layers);

        var tools = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            Margin = new Thickness(0, 0, 0, 8),
        };
        Tool(tools, "Fit", "The whole map in the window", () => { _zoom = 0; Rescale(); });
        Tool(tools, "1:1", "One world unit to a pixel", () => { _zoom = 1; Rescale(); });
        Tool(tools, "-", "Zoom out", () => Zoom(1 / 1.4, null));
        Tool(tools, "+", "Zoom in", () => Zoom(1.4, null));
        Tool(tools, "Copy", "The whole map to the clipboard, at full size (Ctrl+C)", Copy);
        Tool(tools, "Rescan", "Look for units again - they are only searched for "
                            + "every ten seconds", () => Scan(true));
        // The strike is a research toy and it is armed on purpose: one click
        // to arm, one on the map to bomb, and the party is the likeliest thing
        // under the pointer.
        _strike = Tool(tools, "Air strike", "Arms an air strike: the next click on the map "
                                           + "sends a plane from the hangar to bomb that point. "
                                           + "Needs a MiG with bombs in the hangar.",
                       () => ArmStrike(!_strikeArmed));
        tools.Children.Add(new TextBlock
        {
            Text = "wheel zooms, dragging moves",
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(8, 0, 0, 0),
            VerticalAlignment = VerticalAlignment.Center,
        });
        Grid.SetRow(tools, 2);
        root.Children.Add(tools);

        _image = new Image
        {
            Stretch = Stretch.Uniform,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            SnapsToDevicePixels = true,
        };
        RenderOptions.SetBitmapScalingMode(_image, BitmapScalingMode.NearestNeighbor);
        _image.MouseMove += ShowCellUnderPointer;
        _image.MouseLeave += (s, e) => _hover.Text = "";
        // Not on the image: the pan below captures the mouse on the first
        // click, and from then on every button event is routed to the scroll
        // viewer, so the image never saw a second one and ClickCount never
        // reached two. The double click is caught where the capture is.

        _view = new ScrollViewer
        {
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Background = Panel,
            Padding = new Thickness(6),
            Content = _image,
        };
        _view.PreviewMouseWheel += (s, e) =>
        {
            Zoom(e.Delta > 0 ? 1.25 : 1 / 1.25, e.GetPosition(_image));
            e.Handled = true;
        };
        _view.PreviewMouseLeftButtonDown += (s, e) =>
        {
            if (_strikeArmed)
            {
                StrikeAt(e.GetPosition(_image));
                e.Handled = true;
                return;
            }
            if (e.ClickCount >= 2)
            {
                // A double click opens the unit under it rather than starting
                // another drag.
                OpenUnitUnderPointer(e.GetPosition(_image));
                e.Handled = true;
                return;
            }
            _drag = e.GetPosition(_view);
            _dragging = true;
            _view.CaptureMouse();
        };
        _view.PreviewMouseMove += (s, e) =>
        {
            if (!_dragging) return;
            Point now = e.GetPosition(_view);
            _view.ScrollToHorizontalOffset(_view.HorizontalOffset - (now.X - _drag.X));
            _view.ScrollToVerticalOffset(_view.VerticalOffset - (now.Y - _drag.Y));
            _drag = now;
        };
        _view.PreviewMouseLeftButtonUp += (s, e) =>
        {
            _dragging = false;
            _view.ReleaseMouseCapture();
        };

        var frame = new Border
        {
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Child = _view,
        };
        Grid.SetRow(frame, 3);
        root.Children.Add(frame);

        var bottom = new StackPanel { Margin = new Thickness(0, 8, 0, 0) };
        _status = new TextBlock { Foreground = Dim, FontSize = 11 };
        _hover = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            FontFamily = new FontFamily("Consolas"),
            Margin = new Thickness(0, 2, 0, 0),
        };
        _note = new TextBlock { Foreground = Accent, FontSize = 11, Margin = new Thickness(0, 2, 0, 0) };
        bottom.Children.Add(_status);
        bottom.Children.Add(_hover);
        bottom.Children.Add(_note);
        Grid.SetRow(bottom, 4);
        root.Children.Add(bottom);
        return root;
    }

    private Button Tool(Panel into, string text, string tip, Action click)
    {
        var button = new Button
        {
            Content = text,
            MinWidth = 44,
            Height = 22,
            FontSize = 11,
            Background = Panel,
            Foreground = Dim,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Margin = new Thickness(0, 0, 6, 0),
            ToolTip = tip,
        };
        button.Click += (s, e) => click();
        into.Children.Add(button);
        return button;
    }

    // ------------------------------------------------------------ the strike

    private void ArmStrike(bool armed)
    {
        _strikeArmed = armed;
        _strike.Foreground = armed ? Bad : Dim;
        _strike.BorderBrush = armed ? Bad : Line;
        _note.Text = armed
            ? "armed - click the map to bomb that point; Esc puts it away"
            : "";
        _note.Foreground = Accent;
    }

    /// Calls the air strike on the point under the pointer, once, and disarms.
    private void StrikeAt(Point where)
    {
        ArmStrike(false);
        GameLink.MapSnapshot map = _map;
        if (map == null || _image.ActualWidth <= 0) return;
        float x = (float)(where.X / _image.ActualWidth * map.Width);
        float y = (float)(where.Y / _image.ActualHeight * map.Height);
        if (x < 0 || y < 0 || x >= map.Width || y >= map.Height) return;
        uint answer;
        string bad = GameLink.AirStrike(x, y, out answer);
        _note.Text = bad ?? string.Format(CultureInfo.InvariantCulture,
            "a plane is on its way to {0}, {1} - one bomb, and it lands back in the hangar after",
            (int)x, (int)y);
        _note.Foreground = bad == null ? Accent : Bad;
        if (bad != null) return;
        _strikes.Add(new Strike { X = x, Y = y, When = DateTime.Now });
        Radio.Call();
        Paint();
    }

    /// The target of every strike still in the air: a ring with a cross
    /// through it, drawn last so nothing covers it. Two units wide so it
    /// survives the window showing the map at half size.
    private void PaintStrikes(uint[] pixels, GameLink.MapSnapshot map)
    {
        _strikes.RemoveAll(s => DateTime.Now - s.When > StrikeShown);
        const uint colour = 0xFFE06C60;
        foreach (Strike strike in _strikes)
        {
            int cx = (int)strike.X, cy = (int)strike.Y;
            for (int d = -12; d <= 12; d++)
            {
                if (Math.Abs(d) < 4) continue;          // the middle stays open
                for (int t = 0; t <= 1; t++)
                {
                    Plot(pixels, map, cx + d, cy + t, colour);
                    Plot(pixels, map, cx + t, cy + d, colour);
                }
            }
            for (double a = 0; a < Math.PI * 2; a += 0.05)
            {
                Plot(pixels, map, cx + (int)Math.Round(Math.Cos(a) * 8), cy + (int)Math.Round(Math.Sin(a) * 8), colour);
                Plot(pixels, map, cx + (int)Math.Round(Math.Cos(a) * 9), cy + (int)Math.Round(Math.Sin(a) * 9), colour);
            }
        }
    }

    private static void Plot(uint[] pixels, GameLink.MapSnapshot map, int x, int y, uint colour)
    {
        if (x < 0 || y < 0 || x >= map.Width || y >= map.Height) return;
        pixels[y * map.Width + x] = colour;
    }

    // ------------------------------------------------------- zoom and copying

    /// Applies the zoom. At zero the image is left to fit the window, which is
    /// what the scroll viewer does on its own when the image has no size of its
    /// own to insist on.
    private void Rescale()
    {
        GameLink.MapSnapshot map = _map;
        if (map == null) return;
        if (_zoom <= 0)
        {
            _image.Width = double.NaN;
            _image.Height = double.NaN;
            _view.ScrollToHorizontalOffset(0);
            _view.ScrollToVerticalOffset(0);
        }
        else
        {
            _image.Width = map.Width * _zoom;
            _image.Height = map.Height * _zoom;
        }
        // How far the party has to be spread depends on how small it is drawn.
        Paint();
    }

    /// Zooms about a point of the image, so what is under the pointer stays
    /// under it. `at` is in image coordinates, or null for the middle.
    private void Zoom(double by, Point? at)
    {
        GameLink.MapSnapshot map = _map;
        if (map == null) return;

        double was = _zoom > 0 ? _zoom : (_image.ActualWidth > 0
                                          ? _image.ActualWidth / map.Width : 0.5);
        double now = Math.Max(0.1, Math.Min(16, was * by));
        Point point = at ?? new Point(_image.ActualWidth / 2, _image.ActualHeight / 2);
        double unitX = point.X / Math.Max(1, _image.ActualWidth) * map.Width;
        double unitY = point.Y / Math.Max(1, _image.ActualHeight) * map.Height;
        double keepX = _view.HorizontalOffset > 0 || _zoom > 0
                     ? point.X - _view.HorizontalOffset : point.X;
        double keepY = _view.VerticalOffset > 0 || _zoom > 0
                     ? point.Y - _view.VerticalOffset : point.Y;

        _zoom = now;
        Rescale();
        _view.UpdateLayout();
        _view.ScrollToHorizontalOffset(unitX * now - keepX);
        _view.ScrollToVerticalOffset(unitY * now - keepY);
    }

    /// The map on the clipboard, at its own size rather than the window's -
    /// 1200x1200 for a campaign mission, which is worth keeping.
    private void Copy()
    {
        if (_bitmap == null) return;
        try
        {
            Clipboard.SetImage(_bitmap);
            _hover.Text = "copied " + _bitmap.PixelWidth + " x " + _bitmap.PixelHeight
                        + " to the clipboard";
        }
        catch (Exception ex)
        {
            _hover.Text = "the clipboard refused it: " + ex.Message;
        }
    }

    private CheckBox Layer(Panel into, string text, bool on)
    {
        var box = new CheckBox
        {
            Content = text,
            IsChecked = on,
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 0, 14, 0),
            VerticalAlignment = VerticalAlignment.Center,
        };
        box.Checked += (s, e) => Paint();
        box.Unchecked += (s, e) => Paint();
        into.Children.Add(box);
        return box;
    }

    // ------------------------------------------------------------ the reading

    private void Refresh()
    {
        GameLink.MapSnapshot map;
        string failed = GameLink.ReadMap(out map);
        if (failed != null)
        {
            _status.Text = failed;
            _status.Foreground = Bad;
            return;
        }
        _map = map;
        _status.Foreground = Dim;

        // The units are read whether or not anything draws them: the hover
        // line names the one under the pointer and a double click opens it.
        // Their positions are cheap to refresh; finding them again means
        // walking the whole of the game's memory, so that is rare.
        GameLink.RefreshUnits(_units, map.Width, map.Height);
        if (_units.Count == 0 || ++_ticks >= 17) Scan(false);
        string relief = "no heights - the path grid does not line up";
        if (map.Heights != null)
        {
            int low = int.MaxValue, high = int.MinValue;
            foreach (int z in map.Heights)
            {
                if (z < low) low = z;
                if (z > high) high = z;
            }
            _low = low;
            _high = high;
            relief = "height " + low + " to " + high + " over "
                   + map.HeightWidth + " x " + map.HeightHeight + " cells";
        }
        _mine = GameLink.PlayerParty();
        ShowLegend(map);
        string units = ", " + _units.Count + " units"
                     + (_scanning ? " (looking)" : "");
        _status.Text = map.Width + " x " + map.Height + " world units ("
                     + ((map.Width + 15) / 16) + " x " + ((map.Height + 15) / 16)
                     + " map cells), " + relief + units;
        Paint();
    }

    /// Looks for the units again. It walks all the memory the game allocated,
    /// which takes a moment, so it runs on a thread of its own and the window
    /// keeps drawing what it has meanwhile.
    private void Scan(bool now)
    {
        GameLink.MapSnapshot map = _map;
        if (map == null || _scanning) return;
        if (!now && _ticks < 17 && _units.Count > 0) return;
        _scanning = true;
        _ticks = 0;
        int width = map.Width, height = map.Height;
        ThreadPool.QueueUserWorkItem(delegate
        {
            List<GameLink.Unit> found = GameLink.FindUnits(width, height);
            Dispatcher.BeginInvoke((Action)delegate
            {
                _units = found;
                _scanning = false;
                Paint();
            });
        });
    }

    /// The legend, rebuilt from the parties this mission actually has - which
    /// ones those are, and how many, is up to the mission.
    private void ShowLegend(GameLink.MapSnapshot map)
    {
        var present = new SortedSet<uint>();
        foreach (uint cell in map.Cells)
        {
            uint party = (cell >> 8) & 0xF;
            if (party != 0) present.Add(party);
        }
        foreach (GameLink.Unit unit in _units)
            if (unit.Party > 0) present.Add((uint)unit.Party);
        if (present.Count == _legend.Children.Count / 2 && _legendMine == _mine) return;
        _legendMine = _mine;

        _legend.Children.Clear();
        foreach (uint party in present)
        {
            uint colour = Parties[party];
            _legend.Children.Add(new Border
            {
                Width = 10,
                Height = 10,
                Background = new SolidColorBrush(Color.FromRgb(
                    (byte)(colour >> 16), (byte)(colour >> 8), (byte)colour)),
                Margin = new Thickness(6, 0, 3, 0),
                VerticalAlignment = VerticalAlignment.Center,
            });
            _legend.Children.Add(new TextBlock
            {
                Text = "party " + party + (party == (uint)_mine ? " (yours)" : ""),
                Foreground = Dim,
                FontSize = 11,
                VerticalAlignment = VerticalAlignment.Center,
            });
        }
    }

    // Colours. The ground type carries the picture, everything else is painted
    // over it so a single glance says what is where.
    private static readonly uint[] Ground =
    {
        0xFF2B3A2A, 0xFF3D5233, 0xFF56663C, 0xFF6E7350,
    };
    private const uint ColourObject = 0xFF7A5A3A;
    private const uint ColourStructure = 0xFF9AA0AE;
    private const uint ColourAir = 0xFF35506E;
    private const uint ColourSmoke = 0xFFC8A24A;

    private int _low, _high;

    /// The height at a point of the fine map, taken from the coarse grid and
    /// interpolated, so the shading comes out smooth instead of in squares.
    private static double HeightAt(GameLink.MapSnapshot map, double x, double y)
    {
        double u = x / 16.0 - 0.5, v = y / 16.0 - 0.5;
        int x0 = (int)Math.Floor(u), y0 = (int)Math.Floor(v);
        double fx = u - x0, fy = v - y0;
        int x1 = x0 + 1, y1 = y0 + 1;
        if (x0 < 0) x0 = 0;
        if (y0 < 0) y0 = 0;
        if (x1 > map.HeightWidth - 1) x1 = map.HeightWidth - 1;
        if (y1 > map.HeightHeight - 1) y1 = map.HeightHeight - 1;
        if (x0 > map.HeightWidth - 1) x0 = map.HeightWidth - 1;
        if (y0 > map.HeightHeight - 1) y0 = map.HeightHeight - 1;

        double top = map.Heights[y0 * map.HeightWidth + x0] * (1 - fx)
                   + map.Heights[y0 * map.HeightWidth + x1] * fx;
        double bottom = map.Heights[y1 * map.HeightWidth + x0] * (1 - fx)
                      + map.Heights[y1 * map.HeightWidth + x1] * fx;
        return top * (1 - fy) + bottom * fy;
    }

    /// Multiplies the three channels of a colour, keeping it in range.
    private static uint Shade(uint colour, double factor)
    {
        uint b = (uint)Math.Max(0, Math.Min(255, (colour & 0xFF) * factor));
        uint g = (uint)Math.Max(0, Math.Min(255, ((colour >> 8) & 0xFF) * factor));
        uint r = (uint)Math.Max(0, Math.Min(255, ((colour >> 16) & 0xFF) * factor));
        return 0xFF000000u | (r << 16) | (g << 8) | b;
    }

    private void Paint()
    {
        GameLink.MapSnapshot map = _map;
        if (map == null) return;
        if (_bitmap == null || _bitmap.PixelWidth != map.Width || _bitmap.PixelHeight != map.Height)
        {
            _bitmap = new WriteableBitmap(map.Width, map.Height, 96, 96, PixelFormats.Bgra32, null);
            _image.Source = _bitmap;
        }

        bool party = _party.IsChecked == true;
        bool structures = _structures.IsChecked == true;
        bool objects = _objects.IsChecked == true;
        bool air = _air.IsChecked == true;
        bool extra = _extra.IsChecked == true;

        bool relief = _relief.IsChecked == true && map.Heights != null;
        double span = _high - _low;
        if (span < 1) span = 1;

        var pixels = new uint[map.Width * map.Height];
        for (int y = 0; y < map.Height; y++)
        {
            for (int x = 0; x < map.Width; x++)
            {
                int i = y * map.Width + x;
                uint cell = map.Cells[i];
                uint colour = Ground[(cell >> 17) & 3];
                if (air && (cell & 0x8) != 0) colour = ColourAir;
                if (objects && (cell & 0xF0) != 0) colour = ColourObject;
                if (structures && (cell & 0x10000) != 0) colour = ColourStructure;
                if (extra && (cell & 0x200000) != 0) colour = ColourSmoke;

                if (relief)
                {
                    // Height as brightness, plus the drop towards the
                    // north-west as a light - the same trick a paper relief
                    // map uses, and enough to read a valley from a ridge.
                    double here = HeightAt(map, x, y);
                    double level = 0.72 + 0.5 * ((here - _low) / span);
                    double back = HeightAt(map, x - 8, y - 8);
                    double slope = (here - back) / 40.0;
                    if (slope > 0.35) slope = 0.35;
                    if (slope < -0.35) slope = -0.35;
                    colour = Shade(colour, level + slope);
                }

                pixels[i] = colour;
            }
        }

        // The party is a handful of units on a map of a million cells, and the
        // window shows the map at half its size or less - a single cell would
        // fall through the scaling. So it goes on last, unshaded and spread out
        // enough to survive it.
        if (party)
        {
            double drawn = _image.ActualWidth > 0 ? _image.ActualWidth : map.Width / 2.0;
            int spread = Math.Max(0, (int)(map.Width / drawn));
            for (int y = 0; y < map.Height; y++)
            {
                for (int x = 0; x < map.Width; x++)
                {
                    uint whose = (map.Cells[y * map.Width + x] >> 8) & 0xF;
                    if (whose == 0) continue;
                    uint colour = Parties[whose];
                    for (int dy = -spread; dy <= spread; dy++)
                    {
                        int py = y + dy;
                        if (py < 0 || py >= map.Height) continue;
                        for (int dx = -spread; dx <= spread; dx++)
                        {
                            int px = x + dx;
                            if (px < 0 || px >= map.Width) continue;
                            pixels[py * map.Width + px] = colour;
                        }
                    }
                }
            }
        }
        if (_strikes.Count > 0) PaintStrikes(pixels, map);
        _bitmap.WritePixels(new Int32Rect(0, 0, map.Width, map.Height), pixels, map.Width * 4, 0);
    }

    // ------------------------------------------------------------- the pointer

    /// A double click on a unit opens it in the inspector. A single click is
    /// left alone because that is how the map is dragged.
    private void OpenUnitUnderPointer(Point where)
    {
        GameLink.Unit unit = UnitUnderPointer(where);
        if (unit == null)
        {
            _hover.Text = _units.Count == 0
                ? "no units have been found yet - press Rescan, and only a running "
                + "mission has any"
                : "no unit there - the inspector opens on a double click on one";
            return;
        }
        new InspectWindow(unit.Address) { Owner = this }.Show();
    }

    /// The unit nearest the pointer, within the few world units a unit covers.
    private GameLink.Unit UnitUnderPointer(Point p)
    {
        GameLink.MapSnapshot map = _map;
        if (map == null || _image.ActualWidth <= 0) return null;
        double x = p.X / _image.ActualWidth * map.Width;
        double y = p.Y / _image.ActualHeight * map.Height;
        foreach (GameLink.Unit unit in _units)
            if (Math.Abs(unit.X - x) <= 3 && Math.Abs(unit.Y - y) <= 3)
                return unit;
        return null;
    }

    private void ShowCellUnderPointer(object sender, System.Windows.Input.MouseEventArgs e)
    {
        GameLink.MapSnapshot map = _map;
        if (map == null || _image.ActualWidth <= 0) return;
        Point p = e.GetPosition(_image);
        int x = (int)(p.X / _image.ActualWidth * map.Width);
        int y = (int)(p.Y / _image.ActualHeight * map.Height);
        if (x < 0 || y < 0 || x >= map.Width || y >= map.Height) { _hover.Text = ""; return; }

        uint cell = map.Cells[y * map.Width + x];
        var what = new List<string>();
        if ((cell & 0xF00) != 0)
        {
            uint party = (cell >> 8) & 0xF;
            what.Add("party " + party + (party == (uint)_mine ? " (yours)" : ""));
        }
        foreach (GameLink.Unit unit in _units)
        {
            if (Math.Abs(unit.X - x) > 3 || Math.Abs(unit.Y - y) > 3) continue;
            what.Add("unit " + unit.Address.ToString("X8") + " of party " + unit.Party
                     + ", class " + unit.VTable.ToString("X8"));
            break;
        }
        if ((cell & 0x10000) != 0) what.Add("structure");
        if ((cell & 0xF0) != 0) what.Add("object size " + ((cell >> 4) & 0xF));
        if ((cell & 0x8) != 0) what.Add("air");
        if ((cell & 0x200000) != 0) what.Add("smoke");
        what.Add("ground " + ((cell >> 17) & 3));
        if (map.Heights != null)
            what.Add("height " + (int)HeightAt(map, x, y));
        _hover.Text = string.Format("{0,3} {1,3}   {2:X8}   {3}", x, y, cell,
                                    string.Join(", ", what.ToArray()));
    }
}

/// The radio call that goes with an air strike. The game has no chatter of
/// its own - its sounds are engines, bombs and explosions - so the build packs
/// the ones made by tools/radio_clip.py into the exe as SoA.Radio.a, .b, .c:
/// an observer calling the strike and the pilot answering, through a radio's
/// narrow band. One is picked at random, and not the one played last, so two
/// strikes in a row never say the same thing. It plays on the Windows side,
/// over whatever the game is doing, and a kit built without the clips simply
/// stays quiet.
internal static class Radio
{
    private const string Prefix = "SoA.Radio.";
    private static readonly Random Dice = new Random();
    private static string _last;

    public static void Call()
    {
        try
        {
            var names = new List<string>();
            foreach (string name in typeof(Radio).Assembly.GetManifestResourceNames())
                if (name.StartsWith(Prefix, StringComparison.Ordinal) && name != _last) names.Add(name);
            if (names.Count == 0 && _last != null) names.Add(_last);
            if (names.Count == 0) return;
            string chosen = names[Dice.Next(names.Count)];
            _last = chosen;
            System.IO.Stream stream = typeof(Radio).Assembly.GetManifestResourceStream(chosen);
            if (stream == null) return;
            var player = new System.Media.SoundPlayer(stream);
            player.Play();      // asynchronous; the stream is read on this thread first
        }
        catch { }
    }
}

/// A command that runs a delegate, so a key can be bound to a method.
internal sealed class Command : System.Windows.Input.ICommand
{
    private readonly Action _run;

    public Command(Action run) { _run = run; }

    public event EventHandler CanExecuteChanged
    {
        add { }
        remove { }
    }

    public bool CanExecute(object parameter) { return true; }

    public void Execute(object parameter) { _run(); }
}
