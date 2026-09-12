// Launcher for Soldiers of Anarchy - a WPF desktop application.
//
// Why a custom launcher: the game remembers its resolution in the registry and
// never adapts to the monitor. Carry the settings to another machine, or swap
// the display, and it starts in a mode that does not fit. The launcher also
// gathers in one place things that are otherwise scattered: window mode and
// antialiasing live in dgVoodoo.conf, controls and detail levels in the
// registry.
//
// The interface is written in code rather than XAML so that it compiles with
// the plain csc.exe shipped in .NET Framework 4.8, which is part of Windows.
// The package therefore needs no runtime installed and the launcher is a few
// tens of kilobytes.
//
// build-package.ps1 does the compiling.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Markup;
using System.Windows.Media;
using Microsoft.Win32;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        // The window itself is not up for about half a second - a tenth of
        // that is .NET starting, the rest is WPF drawing its first frame - so
        // something has to say that the click was noticed. This goes up after
        // about fifty milliseconds because it is a plain Win32 window of the
        // built-in STATIC class: no WPF, no controls of our own, nothing to
        // load. It closes itself when the real window has drawn.
        Splash.Show();

        // Config.cmd starts the launcher with -o. In that case no launcher
        // window appears - the game's own settings dialog opens directly.
        bool optionsOnly = Array.Exists(args, a =>
            a.Equals("-o", StringComparison.OrdinalIgnoreCase) ||
            a.Equals("/o", StringComparison.OrdinalIgnoreCase));
        // The catalog can also start on its own so it can be attached to a
        // game that is already running.
        bool catalog = Array.Exists(args, a =>
            a.Equals("-catalog", StringComparison.OrdinalIgnoreCase) ||
            a.Equals("-katalog", StringComparison.OrdinalIgnoreCase));

        // The checks that need the game. Play.exe -selftest drives the whole
        // way through and writes selftest.txt next to itself.
        if (Array.Exists(args, a => a.Equals("-selftest", StringComparison.OrdinalIgnoreCase)))
        {
            Splash.Hide();
            Environment.Exit(SelfTest.Run());
        }

        var app = new Application();
        if (catalog)
        {
            var only = new CatalogWindow();
            only.ContentRendered += (s, e) => Splash.Hide();
            app.Run(only);
            return;
        }

        var window = new LauncherWindow();
        window.ContentRendered += (s, e) => Splash.Hide();
        if (optionsOnly) { Splash.Hide(); window.RunOptionsDialog(); }
        else app.Run(window);
    }
}

internal sealed class LauncherWindow : Window
{
    private const string RegKey = @"Software\Silver Style Entertainment\Soldiers of Anarchy";
    private const string LayersKey = @"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers";

    private readonly string _here = AppDomain.CurrentDomain.BaseDirectory;
    // Not readonly: in the kit the game can be pointed at while the launcher
    // is open, and all three then move.
    private string _gameDir;
    private string _exe;
    private string _conf;

    private ComboBox _resolution;
    private ComboBox _mode;
    private Button _findGame;
    private CheckBox _skipIntro;
    private CheckBox _phong;
    private CheckBox _smooth2d;
    private ComboBox _antialias;
    private ComboBox _mipmapping;
    private TextBlock _status;
    private Button _play;
    private List<string> _resolutions;
    private string _desktopResolution;

    // Colours kept together so they are not repeated on every element.
    private static readonly Brush Bg = Brush("#FF191B20");
    private static readonly Brush Panel = Brush("#FF23262E");
    private static readonly Brush Line = Brush("#FF33384A");
    private static readonly Brush Text = Brush("#FFE2E4EA");
    private static readonly Brush Dim = Brush("#FF8E93A3");
    private static readonly Brush Accent = Brush("#FFC8A24A");
    private static readonly Brush AccentDark = Brush("#FF9C7C2E");

    // The stock ComboBox template ignores the background we set and draws its
    // own chrome, which left light grey text on white. Hence a dark template of
    // our own, loaded from a XAML string - System.Xaml is referenced anyway.
    internal const string ComboXaml = @"
<Style xmlns='http://schemas.microsoft.com/winfx/2006/xaml/presentation'
       xmlns:x='http://schemas.microsoft.com/winfx/2006/xaml'
       TargetType='ComboBox'>
  <Setter Property='Foreground' Value='#FFE2E4EA'/>
  <Setter Property='FontSize' Value='13'/>
  <Setter Property='Template'>
    <Setter.Value>
      <ControlTemplate TargetType='ComboBox'>
        <Grid>
          <ToggleButton Name='Toggle' Focusable='false' ClickMode='Press'
                        IsChecked='{Binding IsDropDownOpen, Mode=TwoWay, RelativeSource={RelativeSource TemplatedParent}}'>
            <ToggleButton.Template>
              <ControlTemplate TargetType='ToggleButton'>
                <Border Name='Chrome' Background='#FF23262E' BorderBrush='#FF33384A'
                        BorderThickness='1' CornerRadius='3'>
                  <Path HorizontalAlignment='Right' VerticalAlignment='Center'
                        Margin='0,0,12,0' Fill='#FF8E93A3' Data='M0,0 L9,0 L4.5,5 Z'/>
                </Border>
                <ControlTemplate.Triggers>
                  <Trigger Property='IsMouseOver' Value='True'>
                    <Setter TargetName='Chrome' Property='BorderBrush' Value='#FFC8A24A'/>
                  </Trigger>
                </ControlTemplate.Triggers>
              </ControlTemplate>
            </ToggleButton.Template>
          </ToggleButton>
          <ContentPresenter Margin='12,0,32,0' VerticalAlignment='Center'
                            IsHitTestVisible='False'
                            Content='{TemplateBinding SelectionBoxItem}'/>
          <Popup Placement='Bottom' Focusable='False' AllowsTransparency='True'
                 IsOpen='{TemplateBinding IsDropDownOpen}'>
            <Border Background='#FF23262E' BorderBrush='#FF33384A' BorderThickness='1'
                    MinWidth='{Binding ActualWidth, RelativeSource={RelativeSource TemplatedParent}}'>
              <ScrollViewer MaxHeight='260'><ItemsPresenter/></ScrollViewer>
            </Border>
          </Popup>
        </Grid>
      </ControlTemplate>
    </Setter.Value>
  </Setter>
  <Style.Resources>
    <Style TargetType='ComboBoxItem'>
      <Setter Property='Foreground' Value='#FFE2E4EA'/>
      <Setter Property='Padding' Value='12,7,12,7'/>
      <Setter Property='Template'>
        <Setter.Value>
          <ControlTemplate TargetType='ComboBoxItem'>
            <Border Name='B' Background='Transparent' Padding='{TemplateBinding Padding}'>
              <ContentPresenter/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property='IsHighlighted' Value='True'>
                <Setter TargetName='B' Property='Background' Value='#FF2E3340'/>
              </Trigger>
              <Trigger Property='IsSelected' Value='True'>
                <Setter Property='Foreground' Value='#FFC8A24A'/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
  </Style.Resources>
</Style>";

    private static SolidColorBrush Brush(string hex)
    {
        var b = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
        b.Freeze();
        return b;
    }

    public LauncherWindow()
    {
        // Where the game is comes from GamePath: beside the launcher in the
        // full package, wherever it was found or pointed at in the kit.
        _gameDir = GamePath.In();
        _exe = GamePath.Exe;
        _conf = Path.Combine(_gameDir, "dgVoodoo.conf");

        Title = "Soldiers of Anarchy";
        Width = 460;
        // The height follows the content. With a fixed one the PLAY button was
        // cut off by the bottom edge as soon as anything in the layout grew.
        SizeToContent = SizeToContent.Height;
        ResizeMode = ResizeMode.NoResize;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Background = Bg;
        FontFamily = new FontFamily("Segoe UI");
        UseLayoutRounding = true;

        Content = BuildLayout();
        LoadCurrentState();
        WarnAboutVersion();

        // Windows paints the title bar according to the system theme, so a
        // light bar would sit above our dark window. We switch it by hand; on
        // older builds the attribute does not exist and the call is ignored.
        // Called twice on purpose: some Windows builds only apply the DWM
        // attribute once the window is actually visible.
        SourceInitialized += (s2, e2) => UseDarkTitleBar();
        Loaded += (s2, e2) => UseDarkTitleBar();
    }

    private const int DwmUseImmersiveDarkMode = 20;

    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

    private void UseDarkTitleBar()
    {
        try
        {
            IntPtr hwnd = new WindowInteropHelper(this).Handle;
            if (hwnd == IntPtr.Zero) return;
            int on = 1;
            // 20 is the current attribute index, 19 was used by older Windows 10 builds.
            if (DwmSetWindowAttribute(hwnd, DwmUseImmersiveDarkMode, ref on, sizeof(int)) != 0)
                DwmSetWindowAttribute(hwnd, 19, ref on, sizeof(int));
        }
        catch { }
    }

    // ----------------------------------------------------------------- layout

    private UIElement BuildLayout()
    {
        var root = new Grid { Margin = new Thickness(0) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // toolbar
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // header
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // body
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // status

        root.Children.Add(Toolbar());
        UIElement header = Header();
        Grid.SetRow(header, 1);
        root.Children.Add(header);

        var body = new StackPanel { Margin = new Thickness(26, 20, 26, 4) };
        body.Children.Add(Row("Resolution", _resolution = Combo()));
        body.Children.Add(Row("Display", _mode = Combo()));
        body.Children.Add(Row("Antialiasing", _antialias = Combo()));
        body.Children.Add(Row("Mipmaps", _mipmapping = Combo()));
        body.Children.Add(Row("At startup", _skipIntro = new CheckBox
        {
            Content = "Skip the logos and the intro",
            IsChecked = true,
            Foreground = Text,
            FontSize = 12,
            VerticalAlignment = VerticalAlignment.Center,
            ToolTip = "The game queues three videos before its menu. Skipping them "
                    + "is a patch in soa.exe, written when Play is pressed.",
        }));
        // Two things the wrapper can do that the engine of 2002 could not.
        // Both are one line in dgVoodoo.conf and both are reversible, which is
        // why they are offered rather than simply switched on.
        var look = new StackPanel { Orientation = Orientation.Horizontal };
        look.Children.Add(_phong = new CheckBox
        {
            Content = "Smoother lighting",
            Foreground = Text,
            FontSize = 12,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(0, 0, 18, 0),
            ToolTip = "The engine lights each corner of a triangle and smears the "
                    + "result across it. The wrapper can light every pixel instead, "
                    + "which shows most on the rounded things - vehicle hulls, "
                    + "helmets, barrels. (PhongShadingWhenPossible)",
        });
        look.Children.Add(_smooth2d = new CheckBox
        {
            Content = "Smoother interface",
            Foreground = Text,
            FontSize = 12,
            VerticalAlignment = VerticalAlignment.Center,
            ToolTip = "The interface is drawn for 640 by 480 and blown up to the "
                    + "screen with each pixel repeated, which is where its stair "
                    + "steps come from. This makes the wrapper interpolate them "
                    + "instead. (Bilinear2DOperations)",
        });
        body.Children.Add(Row("Look", look));
        body.Children.Add(Buttons());
        Grid.SetRow(body, 2);
        root.Children.Add(body);

        _status = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(26, 10, 26, 16),
            TextWrapping = TextWrapping.Wrap
        };
        Grid.SetRow(_status, 3);
        root.Children.Add(_status);
        return root;
    }

    /// The title block. The windows it used to carry buttons for are in the
    /// toolbar above it now: five of them stacked down the right made the
    /// header taller than the settings underneath it.
    private UIElement Header()
    {
        var wrap = new Border
        {
            Background = Panel,
            BorderBrush = Line,
            BorderThickness = new Thickness(0, 0, 0, 1),
            Padding = new Thickness(26, 16, 26, 14)
        };
        var st = new StackPanel();
        st.Children.Add(new TextBlock
        {
            Text = "SOLDIERS OF ANARCHY",
            Foreground = Accent,
            FontSize = 19,
            FontWeight = FontWeights.SemiBold
        });
        st.Children.Add(new TextBlock
        {
            Text = DetectVersion() + "   ·   package " + BuildInfo.Package,
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 3, 0, 0)
        });
        wrap.Child = st;
        return wrap;
    }

    /// The windows that stand beside the game, in a strip across the top.
    ///
    /// Save settings sits apart on the right because it is the odd one out:
    /// the others only open something, that one writes the package.
    private UIElement Toolbar()
    {
        var wrap = new Border
        {
            Background = Bg,
            BorderBrush = Line,
            BorderThickness = new Thickness(0, 0, 0, 1),
            Padding = new Thickness(20, 8, 20, 8)
        };
        var row = new DockPanel { LastChildFill = false };

        Place(row, ToolButton("Catalog",
            "Every item and vehicle in the game, with what the game says about it",
            OpenCatalog), Dock.Left);
        Place(row, ToolButton("Console",
            "The game's log, and the base cheats sent into the running game",
            OpenConsole), Dock.Left);
        Place(row, ToolButton("Map",
            "The map of the running mission, read out of the game",
            OpenMap), Dock.Left);
        Place(row, ToolButton("Saves",
            "What is in the saves, read without loading them",
            OpenSaves), Dock.Left);
        Place(row, ToolButton("Models",
            "The game's 3D models, read out of objects.ubn and drawn with their "
            + "own textures",
            OpenModels), Dock.Left);
        Place(row, ToolButton("Patches",
            "The changes made to soa.exe - focus, the log, the camera, the fonts - "
            + "each with a box to switch it on or off",
            OpenPatches), Dock.Left);

        _findGame = ToolButton("Find the game...",
            "Point the launcher at soa.exe. Only needed when the game is not in "
            + "a Game folder beside the launcher.", FindGame);
        _findGame.Visibility = Visibility.Collapsed;
        Place(row, _findGame, Dock.Right);

        Button settings = ToolButton("Save settings",
            "Takes whatever the game is set to right now and stores it "
            + "in the package as the default.", SaveSettings);
        settings.Margin = new Thickness(6, 0, 0, 0);
        Place(row, settings, Dock.Right);

        wrap.Child = row;
        return wrap;
    }

    private static void Place(DockPanel row, UIElement what, Dock side)
    {
        DockPanel.SetDock(what, side);
        row.Children.Add(what);
    }

    private Button ToolButton(string text, string tip, Action run)
    {
        var b = new Button
        {
            Content = text,
            Height = 26,
            FontSize = 11,
            Padding = new Thickness(10, 0, 10, 0),
            Margin = new Thickness(0, 0, 6, 0),
            Background = Panel,
            Foreground = Dim,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            ToolTip = tip
        };
        b.Click += (s2, e2) => run();
        return b;
    }

    /// Reads the game's current settings from the registry and stores them in
    /// settings.reg next to the launcher. The game keeps everything there that
    /// its dialog and the game itself can change - detail levels, filters,
    /// volumes, key bindings. Display values are dropped: the launcher manages
    /// those and they would not fit another machine.
    private void SaveSettings()
    {
        string target = Path.Combine(_here, "settings.reg");
        string temp = Path.Combine(Path.GetTempPath(),
                                   "soa-settings-" + Guid.NewGuid().ToString("N") + ".reg");
        try
        {
            var psi = new ProcessStartInfo("reg.exe",
                "export \"HKCU\\" + RegKey + "\" \"" + temp + "\" /y")
            {
                UseShellExecute = false,
                CreateNoWindow = true
            };
            int code = 1;
            using (Process p = Process.Start(psi))
            {
                if (p != null) { p.WaitForExit(); code = p.ExitCode; }
            }
            if (code != 0 || !File.Exists(temp))
            {
                _status.Text = "Could not read the settings from the registry.";
                _status.Foreground = Accent;
                return;
            }

            // The file is UTF-16. We drop the display values, which belong to
            // one particular monitor.
            string[] lines = File.ReadAllLines(temp, System.Text.Encoding.Unicode);
            var kept = new List<string>();
            int dropped = 0;
            foreach (string line in lines)
            {
                string head = line.TrimStart();
                if (head.StartsWith("\"DisplayMode") || head.StartsWith("\"DDDevice")
                    || head.StartsWith("\"D3DDevice")) { dropped++; continue; }
                kept.Add(line);
            }
            File.WriteAllLines(target, kept, System.Text.Encoding.Unicode);

            // The fingerprint has to be updated as well, otherwise the next
            // start would import the file back over what is in the registry -
            // the import is driven by exactly that fingerprint.
            using (RegistryKey k = Registry.CurrentUser.CreateSubKey(RegKey))
                if (k != null) k.SetValue("SettingsFingerprint", Fingerprint(target), RegistryValueKind.String);

            int values = 0;
            foreach (string line in kept)
                if (line.StartsWith("\"")) values++;
            _status.Text = "Saved to settings.reg: " + values + " values"
                         + (dropped > 0 ? " (" + dropped + " display ones left out)" : "") + ".";
            _status.Foreground = Dim;
        }
        catch (Exception ex)
        {
            _status.Text = "Saving failed: " + ex.Message;
            _status.Foreground = Accent;
        }
        finally
        {
            try { if (File.Exists(temp)) File.Delete(temp); }
            catch { }
        }
    }

    private void OpenCatalog()
    {
        foreach (Window w in Application.Current.Windows)
            if (w is CatalogWindow) { w.Activate(); return; }
        new CatalogWindow().Show();
    }

    private void OpenPatches()
    {
        foreach (Window w in Application.Current.Windows)
            if (w is PatchesWindow) { w.Activate(); return; }
        new PatchesWindow(_exe).Show();
    }

    private void OpenMap()
    {
        foreach (Window w in Application.Current.Windows)
            if (w is MapWindow) { w.Activate(); return; }
        new MapWindow().Show();
    }

    private void OpenConsole()
    {
        foreach (Window w in Application.Current.Windows)
            if (w is ConsoleWindow) { w.Activate(); return; }
        new ConsoleWindow().Show();
    }

    /// Ask where the game is, then carry on as though it had been there all
    /// along.
    private void FindGame()
    {
        if (!GamePath.Ask())
        {
            _status.Text = "No soa.exe was chosen.";
            _status.Foreground = Accent;
            return;
        }
        _gameDir = GamePath.In();
        _exe = GamePath.Exe;
        _conf = Path.Combine(_gameDir, "dgVoodoo.conf");
        _play.IsEnabled = true;
        _status.Foreground = Dim;
        LoadCurrentState();
        WarnAboutVersion();
    }

    /// Everything the launcher reaches into the game for is tied to the
    /// addresses of one build, so a different one is worth saying out loud.
    private void WarnAboutVersion()
    {
        if (!GamePath.Found) return;
        if (GamePath.Version() == GamePath.KnownVersion) return;
        string trouble = GamePath.Trouble();
        if (trouble == null) return;
        _status.Text = trouble;
        _status.Foreground = Accent;
    }

    private void OpenSaves()
    {
        foreach (Window w in Application.Current.Windows)
            if (w is SavesWindow) { w.Activate(); return; }
        new SavesWindow().Show();
    }

    private void OpenModels()
    {
        foreach (Window w in Application.Current.Windows)
            if (w is ModelsWindow) { w.Activate(); return; }
        new ModelsWindow().Show();
    }

    private UIElement Row(string label, UIElement control)
    {
        var st = new StackPanel { Margin = new Thickness(0, 0, 0, 14) };
        st.Children.Add(new TextBlock
        {
            Text = label,
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(2, 0, 0, 5)
        });
        st.Children.Add(control);
        return st;
    }

    private ComboBox Combo()
    {
        return new ComboBox
        {
            Height = 32,
            Style = (Style)XamlReader.Parse(ComboXaml)
        };
    }

    private UIElement Buttons()
    {
        var g = new Grid { Margin = new Thickness(0, 6, 0, 0) };
        g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        g.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        _play = new Button
        {
            Content = "PLAY",
            Height = 42,
            FontSize = 15,
            FontWeight = FontWeights.SemiBold,
            Background = Accent,
            Foreground = Bg,
            BorderBrush = AccentDark,
            BorderThickness = new Thickness(1),
            Cursor = Cursors.Hand
        };
        _play.Click += (s, e) => Play();
        Grid.SetColumn(_play, 0);
        g.Children.Add(_play);

        var settings = new Button
        {
            Content = "Game settings",
            Height = 42,
            Width = 130,
            FontSize = 12,
            Margin = new Thickness(10, 0, 0, 0),
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Cursor = Cursors.Hand,
            ToolTip = "Opens the game's own settings dialog (soa.exe -o)"
        };
        settings.Click += (s, e) => ShowGameOptions();
        Grid.SetColumn(settings, 1);
        g.Children.Add(settings);
        return g;
    }

    // ------------------------------------------------------------ current state

    private void LoadCurrentState()
    {
        if (!File.Exists(_exe))
        {
            // The full package always has the game beside it, so this is the
            // kit talking, and it can be answered rather than only reported.
            _status.Text = "The game was not found. Use Find the game to point "
                         + "the launcher at soa.exe; it is remembered afterwards.";
            _status.Foreground = Accent;
            _play.IsEnabled = false;
            if (_findGame != null) _findGame.Visibility = Visibility.Visible;
            return;
        }
        if (_findGame != null) _findGame.Visibility = Visibility.Collapsed;

        int dw, dh;
        bool haveDesktop = GetDesktopResolution(out dw, out dh);

        // Common resolutions plus the real one, so an unusual format can be
        // picked as well.
        var list = new List<string> { "1024x768", "1280x720", "1280x1024", "1366x768",
            "1600x900", "1680x1050", "1920x1080", "2560x1080", "2560x1440", "3840x2160" };
        string desktop = haveDesktop ? dw + "x" + dh : null;
        if (desktop != null && !list.Contains(desktop)) list.Add(desktop);
        list.Sort(CompareResolutions);

        _resolutions = list;
        _desktopResolution = desktop;

        _mode.Items.Add("Windowed");
        _mode.Items.Add("Full screen");
        // Which mode the game is in is decided by the exe, not by the wrapper,
        // so that is what the list starts on. dgVoodoo.conf only follows.
        _mode.SelectedIndex = IsExeWindowed(_exe) ? 0 : 1;

        _skipIntro.IsChecked = GameSkipsIntro(_exe);
        _mode.SelectionChanged += (s2, e2) => FillResolutions();
        FillResolutions();

        foreach (string a in new[] { "off", "2x", "4x", "8x" }) _antialias.Items.Add(a);
        string aa = ReadConf("Antialiasing", SectionDirectX);
        int idx = Array.IndexOf(new[] { "off", "2x", "4x", "8x" }, aa);
        _antialias.SelectedIndex = idx >= 0 ? idx : 3;

        // Mipmapping decides how much of the upscaled textures is ever seen.
        // The engine builds a pyramid of smaller copies of every texture and at
        // a normal camera height draws a lower level, so the extra resolution
        // is thrown away. With mipmaps off the full resolution is always drawn;
        // the price is shimmering in the distance.
        _mipmapping.Items.Add("Off (sharper)");
        _mipmapping.Items.Add("As the game asks (calmer)");
        _mipmapping.SelectedIndex = ReadConf("Mipmapping", SectionDirectX) == "appdriven" ? 1 : 0;

        _phong.IsChecked = ReadConf("PhongShadingWhenPossible", SectionDirectX) == "true";
        _smooth2d.IsChecked = ReadConf("Bilinear2DOperations", SectionDirectX) == "true";

        bool wrapper = File.Exists(Path.Combine(_gameDir, "ddraw.dll"));
        if (!wrapper)
        {
            _status.Text = "Careful: ddraw.dll is missing, the game will run without dgVoodoo and may not work.";
            return;
        }

        // If the controls are not on WASD it should show before someone finds
        // out in game that the camera will not move. AK68_1 is the first slot
        // of the action that holds W (virtual key 0x57) after the import.
        _status.Text = CameraOnWasd()
            ? "dgVoodoo in place, controls on WASD."
            : "dgVoodoo in place. Controls will be set when the game starts.";
    }

    private static int CompareResolutions(string a, string b)
    {
        int aw = int.Parse(a.Split('x')[0], CultureInfo.InvariantCulture);
        int bw = int.Parse(b.Split('x')[0], CultureInfo.InvariantCulture);
        return aw != bw ? aw.CompareTo(bw) : a.CompareTo(b);
    }

    private string DetectVersion()
    {
        if (!File.Exists(_exe)) return "game not found";
        try
        {
            FileVersionInfo v = FileVersionInfo.GetVersionInfo(_exe);
            return "version " + v.FileVersion;
        }
        catch { return string.Empty; }
    }

    // ----------------------------------------------------------------- start

    private void Play()
    {
        try
        {
            string res = ((string)_resolution.SelectedItem ?? "").Split(' ')[0];
            string[] parts = res.Split('x');
            if (parts.Length == 2)
                SetDisplayMode(int.Parse(parts[0], CultureInfo.InvariantCulture),
                               int.Parse(parts[1], CultureInfo.InvariantCulture));

            WriteConf("FullScreenMode", _mode.SelectedIndex == 1 ? "true" : "false", SectionGeneral);
            WriteConf("Antialiasing", new[] { "off", "2x", "4x", "8x" }[_antialias.SelectedIndex], SectionDirectX);
            WriteConf("Mipmapping", _mipmapping.SelectedIndex == 1 ? "appdriven" : "disabled", SectionDirectX);
            WriteConf("PhongShadingWhenPossible", _phong.IsChecked == true ? "true" : "false", SectionDirectX);
            WriteConf("Bilinear2DOperations", _smooth2d.IsChecked == true ? "true" : "false", SectionDirectX);
            FirstRunSetup();

            // Windowed or not is decided inside soa.exe, so the mode is written
            // into the exe itself before it starts.
            string patched = ApplyWindowMode(_exe, _mode.SelectedIndex == 0,
                                             _skipIntro.IsChecked == true);
            if (patched != null)
            {
                _status.Text = "The window mode could not be set: " + patched;
                _status.Foreground = Accent;
                return;
            }

            StartGame(false);

            // Only this window closes. With the catalog open the application
            // keeps running and stays at hand next to the game.
            bool othersOpen = false;
            foreach (Window w in Application.Current.Windows)
                if (w is CatalogWindow || w is ConsoleWindow || w is MapWindow
                    || w is SavesWindow || w is ModelsWindow || w is PatchesWindow)
                    othersOpen = true;
            if (othersOpen) Application.Current.ShutdownMode = ShutdownMode.OnLastWindowClose;

            Close();
        }
        catch (Exception ex)
        {
            _status.Text = "Error: " + ex.Message;
            _status.Foreground = Accent;
        }
    }

    // The game's settings dialog picks its own resolution and would overwrite
    // our values anyway, so nothing is written before it opens - only the
    // controls and detail levels are imported if this is the first run.
    private void ShowGameOptions()
    {
        try
        {
            FirstRunSetup();
            StartGame(true);
            Close();
        }
        catch (Exception ex)
        {
            _status.Text = "Error: " + ex.Message;
            _status.Foreground = Accent;
        }
    }

    private Process StartGame(bool optionsOnly)
    {
        var psi = new ProcessStartInfo(_exe)
        {
            // Without this the game does not find its .ubn archives and exits
            // with 0x80070002.
            WorkingDirectory = _gameDir,
            UseShellExecute = false
        };
        if (optionsOnly) psi.Arguments = "-o";
        return Process.Start(psi);
    }

    // ------------------------------------------------------- the window mode

    // Whether the game runs in a window is not a setting - it is decided inside
    // soa.exe by the flag at +0xC5 of the application object, which picks the
    // style passed to CreateWindowEx. That one follows the mode picked here and
    // goes both ways. tools/patch_exe.py explains it and does the same from
    // the command line.
    //
    // The size of the window is not among them: the game only resizes it in the
    // full screen path, and the rectangle it uses there is the whole monitor.
    //
    // mov byte ptr [ebp+0xC5], 1  ->  0 : an overlapped window, not a popup.
    // This one follows the mode picked in the launcher, both ways.
    private static readonly PatchSite WindowShapePatch = new PatchSite
    {
        Anchor = new byte[] { 0x8D, 0x85, 0x9C, 0x00, 0x00, 0x00,
                              0xC6, 0x85, 0xC5, 0x00, 0x00, 0x00 },
        Offset = -1, Count = 1,
        Original = new byte[] { 0x01 },
        Patched = new byte[] { 0x00 },
    };

    // A jump over the three videos the game queues at startup - the two logos
    // and the intro - so it goes straight to the menu. This one follows a box
    // in the launcher, because somebody may want to watch them.
    //
    // The rest of the patches - focus, the log, the camera, the character set
    // - are in Patches.cs, behind the Patches button, each with its own box.
    private static readonly PatchSite IntroPatch = new PatchSite
    {
        Anchor = new byte[] { 0xC7, 0x00, 0xF8, 0x86, 0x7C, 0x00, 0x89, 0x58, 0x14,
                              0x89, 0x58, 0x18, 0xA3, 0xFC, 0x5A, 0x87, 0x00,
                              0x8B, 0xF0, 0xEB, 0x02, 0x33, 0xF6 },
        Offset = -1, Count = 1,
        Original = new byte[] { 0x8A, 0x44, 0x24, 0x13, 0x83 },
        Patched = new byte[] { 0xE9, 0xAC, 0x00, 0x00, 0x00 },
    };

    /// The window mode, for anything outside this window that needs it - the
    /// self test runs the game windowed so it does not take the screen.
    internal static bool GameIsWindowed(string exePath) { return IsExeWindowed(exePath); }

    internal static string SetGameWindowed(string exePath, bool windowed)
    {
        return ApplyWindowMode(exePath, windowed, GameSkipsIntro(exePath));
    }

    /// Whether soa.exe currently skips the logos and the intro. A build we do
    /// not know counts as skipping, which is what the box defaults to.
    internal static bool GameSkipsIntro(string exePath)
    {
        try
        {
            if (!File.Exists(exePath)) return true;
            byte[] data = File.ReadAllBytes(exePath);
            int pos = Patches.Find(data, IntroPatch);
            return pos < 0 || Patches.Matches(data, pos, IntroPatch.Patched);
        }
        catch (Exception) { return true; }
    }

    /// Whether soa.exe currently makes a window. Unknown builds count as full
    /// screen, which is what the game does on its own.
    private static bool IsExeWindowed(string exePath)
    {
        try
        {
            if (!File.Exists(exePath)) return false;
            byte[] data = File.ReadAllBytes(exePath);
            int pos = Patches.Find(data, WindowShapePatch);
            return pos >= 0 && Patches.Matches(data, pos, WindowShapePatch.Patched);
        }
        catch (Exception) { return false; }
    }

    /// Puts soa.exe into the picked mode. Returns null on success, a message otherwise.
    private static string ApplyWindowMode(string exePath, bool windowed, bool skipIntro)
    {
        if (!File.Exists(exePath)) return "soa.exe was not found";
        byte[] data;
        try { data = File.ReadAllBytes(exePath); }
        catch (Exception ex) { return ex.Message; }

        bool changed = false;
        int shape = Patches.Find(data, WindowShapePatch);
        if (shape < 0) return "this is not the build of soa.exe we know";
        byte[] wanted = windowed ? WindowShapePatch.Patched : WindowShapePatch.Original;
        if (!Patches.Matches(data, shape, wanted))
        {
            Array.Copy(wanted, 0, data, shape, wanted.Length);
            changed = true;
        }

        int intro = Patches.Find(data, IntroPatch);
        if (intro < 0) return "this is not the build of soa.exe we know";
        byte[] wantedIntro = skipIntro ? IntroPatch.Patched : IntroPatch.Original;
        if (!Patches.Matches(data, intro, wantedIntro))
        {
            Array.Copy(wantedIntro, 0, data, intro, wantedIntro.Length);
            changed = true;
        }

        if (!changed) return null;
        try { File.WriteAllBytes(exePath, data); }
        catch (Exception ex) { return ex.Message; }
        return null;
    }

    // The -o mode: neither the resolution nor dgVoodoo.conf is touched, the
    // game's dialog handles that. Errors go to a message box because the
    // launcher's status line is not visible.
    public void RunOptionsDialog()
    {
        try
        {
            FirstRunSetup();
            StartGame(true);
        }
        catch (Exception ex)
        {
            MessageBox.Show("The settings dialog could not be started: " + ex.Message,
                "Soldiers of Anarchy", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    /// Fills the resolution list. In windowed mode only sizes that really fit
    /// on screen are offered: a window as large as the desktop is still a
    /// window, but its caption sits past the edge and it looks like full
    /// screen - which is exactly why "windowed" seemed not to work.
    private void FillResolutions()
    {
        if (_resolutions == null) return;

        string previous = _resolution.SelectedItem as string;
        bool windowed = _mode.SelectedIndex == 0;

        // Room for the frame, the caption and the taskbar.
        int maxWidth = (int)SystemParameters.WorkArea.Width - 16;
        int maxHeight = (int)SystemParameters.WorkArea.Height - 40;

        var offered = new List<string>();
        foreach (string r in _resolutions)
        {
            string[] c = r.Split('x');
            int w = int.Parse(c[0], CultureInfo.InvariantCulture);
            int h = int.Parse(c[1], CultureInfo.InvariantCulture);
            if (windowed && (w > maxWidth || h > maxHeight)) continue;
            offered.Add(r);
        }
        if (offered.Count == 0) offered.Add(_resolutions[0]);

        _resolution.Items.Clear();
        foreach (string r in offered)
            _resolution.Items.Add(r == _desktopResolution ? r + "   (desktop)" : r);

        // Keep the earlier choice if it still fits; otherwise take the largest.
        int index = -1;
        if (previous != null)
            index = offered.IndexOf(previous.Split(' ')[0]);
        if (index < 0 && !windowed && _desktopResolution != null)
            index = offered.IndexOf(_desktopResolution);
        if (index < 0) index = offered.Count - 1;
        _resolution.SelectedIndex = index;

        if (windowed && _desktopResolution != null && !offered.Contains(_desktopResolution))
            SetStatus("Windowed fits " + offered[offered.Count - 1]
                      + " at most; the desktop is " + _desktopResolution + ".");
    }

    private void SetStatus(string text)
    {
        if (_status != null) _status.Text = text;
    }

    private static bool CameraOnWasd()
    {
        using (RegistryKey k = Registry.CurrentUser.OpenSubKey(RegKey + @"\Settings"))
            return k != null && (k.GetValue("AK68_1") as int?) == 0x57;
    }

    private void SetDisplayMode(int w, int h)
    {
        using (RegistryKey k = Registry.CurrentUser.CreateSubKey(RegKey + @"\Settings"))
        {
            if (k == null) return;
            k.SetValue("DisplayModeWidth", w, RegistryValueKind.DWord);
            k.SetValue("DisplayModeHeight", h, RegistryValueKind.DWord);
            k.SetValue("DisplayModeBPP", 32, RegistryValueKind.DWord);
            k.SetValue("DisplayModeRefreshRate", 0, RegistryValueKind.DWord);
            k.SetValue("DisplayModeFlags", 0, RegistryValueKind.DWord);
        }
    }

    /// Fingerprint of settings.reg. It tells whether the file has already been
    /// applied on this machine. The earlier test was whether TextureDetail was
    /// missing under Settings, but the game writes that value itself when it
    /// first exits - so the import never ran again after the first start and
    /// the game kept its default keys.
    private static string Fingerprint(string file)
    {
        using (MD5 md5 = MD5.Create())
        using (FileStream fs = File.OpenRead(file))
            return BitConverter.ToString(md5.ComputeHash(fs)).Replace("-", "");
    }

    private void FirstRunSetup()
    {
        string reg = Path.Combine(_here, "settings.reg");
        if (!File.Exists(reg)) return;

        string fingerprint = Fingerprint(reg);
        string applied = null;
        using (RegistryKey k = Registry.CurrentUser.OpenSubKey(RegKey))
            if (k != null) applied = k.GetValue("SettingsFingerprint") as string;

        if (applied != fingerprint)
        {
            var psi = new ProcessStartInfo("reg.exe", "import \"" + reg + "\"")
            {
                UseShellExecute = false,
                CreateNoWindow = true
            };
            int code = 1;
            using (Process p = Process.Start(psi))
            {
                if (p != null) { p.WaitForExit(); code = p.ExitCode; }
            }
            // Failure has to speak up. While the import was silent the game
            // simply started with default keys and it took a long time to find.
            if (code != 0)
                MessageBox.Show(
                    "Controls and detail levels could not be imported from settings.reg " +
                    "(reg.exe exited with code " + code + ").\n\n" +
                    "The game will run, but with default keys.",
                    "Soldiers of Anarchy", MessageBoxButton.OK, MessageBoxImage.Warning);
            else
                using (RegistryKey k = Registry.CurrentUser.CreateSubKey(RegKey))
                    if (k != null) k.SetValue("SettingsFingerprint", fingerprint, RegistryValueKind.String);
        }

        using (RegistryKey k = Registry.CurrentUser.CreateSubKey(RegKey))
            if (k != null) k.SetValue("INSTALLDIR", _gameDir, RegistryValueKind.String);

        // Old games do not get along with the Windows fullscreen optimisations.
        using (RegistryKey k = Registry.CurrentUser.CreateSubKey(LayersKey))
            if (k != null) k.SetValue(_exe, "~ DISABLEDXMAXIMIZEDWINDOWEDMODE", RegistryValueKind.String);
    }

    // -------------------------------------------------------- dgVoodoo.conf

    // The same key appears in several sections of dgVoodoo.conf: Antialiasing
    // exists once for [Glide] and once for [DirectX]. The game runs on DirectX,
    // so reads and writes always stay inside the given section - without that
    // the launcher would show the Glide value, which the game never uses.
    private const string SectionGeneral = "[General]";
    private const string SectionDirectX = "[DirectX]";

    private static bool SectionRange(string text, string section, out int start, out int end)
    {
        start = 0;
        end = text.Length;
        // Lines end with CRLF and $ in .NET matches just before \n, so the \r
        // has to be swallowed by the character class - otherwise the section
        // header is not found at all and reading fails silently.
        Match head = Regex.Match(text, @"(?m)^[ \t]*" + Regex.Escape(section) + @"[ \t\r]*$");
        if (!head.Success) return false;
        start = head.Index + head.Length;
        Match next = Regex.Match(text.Substring(start), @"(?m)^[ \t]*\[[^\]\r\n]+\][ \t\r]*$");
        end = next.Success ? start + next.Index : text.Length;
        return true;
    }

    private string ReadConf(string key, string section)
    {
        if (!File.Exists(_conf)) return null;
        string text = File.ReadAllText(_conf);
        int start, end;
        if (!SectionRange(text, section, out start, out end)) return null;
        Match m = Regex.Match(text.Substring(start, end - start),
            @"(?m)^" + Regex.Escape(key) + @"\s*=\s*(\S+)");
        return m.Success ? m.Groups[1].Value : null;
    }

    private void WriteConf(string key, string value, string section)
    {
        if (!File.Exists(_conf)) return;
        string text = File.ReadAllText(_conf);
        int start, end;
        if (!SectionRange(text, section, out start, out end)) return;
        string body = text.Substring(start, end - start);
        string updated = Regex.Replace(body,
            @"(?m)^(" + Regex.Escape(key) + @"\s*=\s*)(\S+)", "${1}" + value);
        if (updated == body) return;
        File.WriteAllText(_conf, text.Substring(0, start) + updated + text.Substring(end));
    }

    // --------------------------------------------------- desktop resolution

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
    private struct DEVMODE
    {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmDeviceName;
        public short dmSpecVersion, dmDriverVersion, dmSize, dmDriverExtra;
        public int dmFields;
        public int dmPositionX, dmPositionY, dmDisplayOrientation, dmDisplayFixedOutput;
        public short dmColor, dmDuplex, dmYResolution, dmTTOption, dmCollate;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmFormName;
        public short dmLogPixels;
        public int dmBitsPerPel, dmPelsWidth, dmPelsHeight, dmDisplayFlags, dmDisplayFrequency;
        public int dmICMMethod, dmICMIntent, dmMediaType, dmDitherType, dmReserved1, dmReserved2;
        public int dmPanningWidth, dmPanningHeight;
    }

    [DllImport("user32.dll", CharSet = CharSet.Ansi)]
    private static extern bool EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode);

    // The monitor's real mode, independent of the Windows display scaling.
    private static bool GetDesktopResolution(out int w, out int h)
    {
        w = h = 0;
        var dm = new DEVMODE();
        dm.dmSize = (short)Marshal.SizeOf(typeof(DEVMODE));
        if (!EnumDisplaySettings(null, -1, ref dm)) return false;
        w = dm.dmPelsWidth;
        h = dm.dmPelsHeight;
        return w > 0 && h > 0;
    }
}


/// A window that says the launcher is coming, before there is anything to show.
///
/// It has to be up long before WPF is ready, so it is Win32 and nothing else:
/// the STATIC class the system registers for everybody, one CreateWindowEx, a
/// font, and a string. No bitmap to load, no class to register, no message loop
/// to run - the launcher's own loop starts a moment later and the window is
/// gone by then.
internal static class Splash
{
    private const int WS_POPUP = unchecked((int)0x80000000);
    private const int WS_VISIBLE = 0x10000000;
    private const int WS_BORDER = 0x00800000;
    private const int SS_CENTER = 0x00000001;
    private const int SS_CENTERIMAGE = 0x00000200;
    private const int WS_EX_TOOLWINDOW = 0x00000080;
    private const int SM_CXSCREEN = 0;
    private const int SM_CYSCREEN = 1;
    private const int WM_SETFONT = 0x0030;

    private static IntPtr _window;
    private static IntPtr _font;

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateWindowExW(int exStyle, string className, string title,
                                                 int style, int x, int y, int width, int height,
                                                 IntPtr parent, IntPtr menu, IntPtr instance,
                                                 IntPtr param);

    [DllImport("user32.dll")]
    private static extern bool DestroyWindow(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool UpdateWindow(IntPtr window);

    [DllImport("user32.dll")]
    private static extern int GetSystemMetrics(int index);

    [DllImport("user32.dll")]
    private static extern IntPtr SendMessage(IntPtr window, int message, IntPtr w, IntPtr l);

    [DllImport("gdi32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr CreateFontW(int height, int width, int escapement,
                                             int orientation, int weight, uint italic,
                                             uint underline, uint strikeOut, uint charSet,
                                             uint outPrecision, uint clipPrecision,
                                             uint quality, uint pitchAndFamily, string face);

    [DllImport("gdi32.dll")]
    private static extern bool DeleteObject(IntPtr handle);

    public static void Show()
    {
        try
        {
            const int width = 320, height = 96;
            int x = (GetSystemMetrics(SM_CXSCREEN) - width) / 2;
            int y = (GetSystemMetrics(SM_CYSCREEN) - height) / 2;
            // Not topmost: the first run can put a message box up while the
            // launcher is still building, and it has to be readable.
            _window = CreateWindowExW(WS_EX_TOOLWINDOW, "STATIC",
                                      "Soldiers of Anarchy\n\nstarting the launcher",
                                      WS_POPUP | WS_VISIBLE | WS_BORDER | SS_CENTER
                                      | SS_CENTERIMAGE,
                                      x, y, width, height,
                                      IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero);
            if (_window == IntPtr.Zero) return;
            _font = CreateFontW(-15, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI");
            if (_font != IntPtr.Zero)
                SendMessage(_window, WM_SETFONT, _font, (IntPtr)1);
            UpdateWindow(_window);
        }
        catch (Exception) { }
    }

    public static void Hide()
    {
        try
        {
            if (_window != IntPtr.Zero) DestroyWindow(_window);
            if (_font != IntPtr.Zero) DeleteObject(_font);
        }
        catch (Exception) { }
        _window = IntPtr.Zero;
        _font = IntPtr.Zero;
    }
}
