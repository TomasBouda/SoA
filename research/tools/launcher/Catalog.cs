// Catalog for adding equipment and vehicles in the base.
//
// The cheat is called directly inside the game process. Going through the
// keyboard does not work: the key that opens the command line is read via
// DirectInput, so the game would have to be focused - and it drops to the
// taskbar as soon as it loses focus.
//
// The called sequence is copied from the game itself. The developer cheats
// call the dispatcher with the literal string "(92)" and number 0xC, so the
// same thing with our own number is enough:
//
//     sub esp,0x10 / mov ecx,esp / push flag / push text / call 0x405D80
//     push number / mov ecx,[0x8759D4] / call 0x52F4A0 / ret 4
//
// tsString is built by the game itself through the constructor 0x405D80, so it
// is the game's own object and its destructor disposes of it properly. The
// global at 0x8759D4 is null until the base screen is running - while it is
// null the catalog refuses to continue, because the game would crash.
//
// The addresses are valid for soa.exe 1.1.2.178; ASLR is off, so they are
// stable.
//
// The item list lives in catalog.txt next to the exe, images in the catalog
// folder; both are produced by tools/gen_catalog.py from the game libraries.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;

internal sealed class CatalogItem
{
    public string Command;     // vehicle or equipment
    public int Number;
    public string Id;
    public string Name;
    public string Group;
    public string ImageFile;   // file in the catalog folder, or empty
    public int AmmoNumber;     // 0 = the weapon has no ammunition
    public string Carrier;     // UNIT_ identifier when this is vehicle armament
    public string Description;
    public string Stock;       // rounds per pickup, empty when not ammunition
    public string Value;       // what the item is worth when trading

    public string AsCommand
    {
        get { return Command + "(" + Number + ")"; }
    }
}

internal sealed class CatalogWindow : Window
{
    // Group names as written by tools/gen_catalog.py into catalog.txt.
    private const string GroupVehicles = "Vehicles";
    private const string GroupStoredVehicles = "Vehicles in storage";
    private const string GroupGear = "Gear and weapons";
    private const string GroupVehicleWeapons = "Vehicle weapons";
    private const string GroupAmmo = "Ammunition";

    private readonly List<CatalogItem> _all = new List<CatalogItem>();
    private TreeView _tree;
    private TextBox _search;
    private TextBlock _status;
    private CheckBox _withAmmo;

    private Image _detailImage;
    private TextBlock _detailName, _detailCommand, _detailDescription;

    private static readonly Brush Bg = Brush("#FF191B20");
    private static readonly Brush Panel = Brush("#FF23262E");
    private static readonly Brush Line = Brush("#FF33384A");
    private static readonly Brush Text = Brush("#FFE2E4EA");
    private static readonly Brush Dim = Brush("#FF8E93A3");
    private static readonly Brush Accent = Brush("#FFC8A24A");

    private static SolidColorBrush Brush(string hex)
    {
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
    }

    public CatalogWindow()
    {
        Title = "Base catalog";
        Width = 760;
        Height = 860;
        Background = Bg;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        // The catalog is meant to be used next to the running game, so it stays
        // above the other windows.
        Topmost = true;

        LoadCatalog();
        Content = BuildLayout();
        BuildTree(null);
    }

    private void LoadCatalog()
    {
        // Out of the exe, or out of a loose catalog.txt where one exists -
        // CatalogData decides, and prefers the loose one.
        foreach (string line in CatalogData.Lines())
        {
            if (line.Length == 0 || line[0] == '#') continue;
            string[] c = line.Split('\t');
            if (c.Length < 5) continue;
            int number;
            if (!int.TryParse(c[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out number))
                continue;
            int ammo = 0;
            if (c.Length > 6) int.TryParse(c[6], NumberStyles.Integer,
                                           CultureInfo.InvariantCulture, out ammo);
            _all.Add(new CatalogItem
            {
                Command = c[0], Number = number, Id = c[2], Name = c[3], Group = c[4],
                ImageFile = c.Length > 5 ? c[5] : "",
                AmmoNumber = ammo,
                Carrier = c.Length > 7 ? c[7] : "",
                // A newline is stored as two characters in the file.
                Description = c.Length > 8 ? c[8].Replace("\\n", "\n") : "",
                Stock = c.Length > 9 ? c[9] : "",
                Value = c.Length > 10 ? c[10] : ""
            });
        }
    }

    // ----------------------------------------------------------------- layout

    private UIElement BuildLayout()
    {
        var root = new Grid { Margin = new Thickness(18) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // header
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // search
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // detail
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // buttons
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // status

        var header = new StackPanel();
        header.Children.Add(new TextBlock
        {
            Text = "BASE CATALOG",
            Foreground = Accent,
            FontSize = 17,
            FontWeight = FontWeights.Bold
        });
        header.Children.Add(new TextBlock
        {
            Text = "Works on the base screen only, not during a mission. "
                 + "Weapons sit under their vehicle, ammunition under its weapon. "
                 + "\"Worth\" is the value the trader counts with.",
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 3, 0, 12)
        });
        root.Children.Add(header);

        _search = new TextBox
        {
            Height = 30,
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            CaretBrush = Text,
            Padding = new Thickness(8, 5, 8, 5),
            FontSize = 13,
            Margin = new Thickness(0, 0, 0, 10)
        };
        _search.TextChanged += (s, e) => BuildTree(_search.Text);
        Grid.SetRow(_search, 1);
        root.Children.Add(_search);

        _tree = new TreeView
        {
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            FontSize = 13
        };
        _tree.SelectedItemChanged += (s, e) => ShowDetail();
        _tree.MouseDoubleClick += (s, e) => Send();
        Grid.SetRow(_tree, 2);
        root.Children.Add(_tree);

        Grid.SetRow(Detail(), 3);
        root.Children.Add(Detail());

        var buttons = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            Margin = new Thickness(0, 12, 0, 0),
            HorizontalAlignment = HorizontalAlignment.Right
        };
        Grid.SetRow(buttons, 4);

        _withAmmo = new CheckBox
        {
            Content = "add ammunition too",
            Foreground = Dim,
            IsChecked = true,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(0, 0, 14, 0)
        };
        buttons.Children.Add(_withAmmo);

        var add = new Button
        {
            Content = "ADD TO BASE",
            Height = 38,
            Width = 220,
            Background = Accent,
            Foreground = Bg,
            FontWeight = FontWeights.Bold,
            BorderThickness = new Thickness(0)
        };
        add.Click += (s, e) => Send();
        buttons.Children.Add(add);
        root.Children.Add(buttons);

        _status = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 10, 0, 0),
            Text = _all.Count + " items. Pick one and press Add, or double-click it."
        };
        Grid.SetRow(_status, 5);
        root.Children.Add(_status);

        return root;
    }

    private UIElement _detail;

    private UIElement Detail()
    {
        if (_detail != null) return _detail;

        var frame = new Border
        {
            Background = Panel,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Padding = new Thickness(12),
            Margin = new Thickness(0, 10, 0, 0),
            Height = 170
        };
        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(230) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

        _detailImage = new Image
        {
            Stretch = Stretch.Uniform,
            StretchDirection = StretchDirection.Both,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(0, 0, 12, 0)
        };
        RenderOptions.SetBitmapScalingMode(_detailImage, BitmapScalingMode.HighQuality);
        grid.Children.Add(_detailImage);

        var texts = new StackPanel();
        _detailName = new TextBlock { Foreground = Text, FontSize = 15, FontWeight = FontWeights.SemiBold };
        _detailCommand = new TextBlock { Foreground = Accent, FontSize = 11, Margin = new Thickness(0, 2, 0, 6) };
        _detailDescription = new TextBlock
        {
            Foreground = Dim,
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            LineHeight = 15
        };
        texts.Children.Add(_detailName);
        texts.Children.Add(_detailCommand);
        texts.Children.Add(new ScrollViewer
        {
            Content = _detailDescription,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            MaxHeight = 112,
            Background = Brushes.Transparent,
            BorderThickness = new Thickness(0)
        });
        Grid.SetColumn(texts, 1);
        grid.Children.Add(texts);

        frame.Child = grid;
        _detail = frame;
        return _detail;
    }

    // ------------------------------------------------------------------- tree

    private static readonly Dictionary<string, BitmapImage> _cache =
        new Dictionary<string, BitmapImage>();

    private static BitmapImage Load(string file)
    {
        if (string.IsNullOrEmpty(file)) return null;
        BitmapImage ready;
        if (_cache.TryGetValue(file, out ready)) return ready;
        byte[] raw = CatalogData.Picture(file);
        if (raw == null) { _cache[file] = null; return null; }
        var bmp = new BitmapImage();
        bmp.BeginInit();
        // From memory either way: the picture may be inside the exe, and when
        // it is a loose file this also leaves it unlocked, so the generator can
        // overwrite it while the window is open.
        bmp.StreamSource = new MemoryStream(raw);
        bmp.CacheOption = BitmapCacheOption.OnLoad;
        bmp.EndInit();
        bmp.Freeze();
        _cache[file] = bmp;
        return bmp;
    }

    private UIElement Row(CatalogItem p, double size)
    {
        var strip = new StackPanel { Orientation = Orientation.Horizontal };
        var frame = new Border
        {
            // The icons are wide and short (a rifle is 115x30), so give them
            // room to stretch instead of squeezing them into a square.
            Width = size * 2.2,
            Height = size,
            Background = Bg,
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Margin = new Thickness(0, 2, 10, 2)
        };
        BitmapImage bmp = Load(p.ImageFile);
        if (bmp != null)
        {
            var image = new Image { Source = bmp, Stretch = Stretch.Uniform, Margin = new Thickness(3) };
            RenderOptions.SetBitmapScalingMode(image, BitmapScalingMode.HighQuality);
            frame.Child = image;
        }
        strip.Children.Add(frame);

        var texts = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
        texts.Children.Add(new TextBlock { Text = p.Name, Foreground = Text, FontSize = 13 });
        string second = p.AsCommand;
        if (!string.IsNullOrEmpty(p.Value)) second += "   ·   worth " + p.Value;
        texts.Children.Add(new TextBlock { Text = second, Foreground = Dim, FontSize = 10 });
        strip.Children.Add(texts);
        return strip;
    }

    private TreeViewItem Node(CatalogItem p, double size)
    {
        return new TreeViewItem
        {
            Header = Row(p, size),
            Tag = p,
            Foreground = Text,
            Padding = new Thickness(2)
        };
    }

    private TreeViewItem GroupNode(string name, int count)
    {
        return new TreeViewItem
        {
            Header = new TextBlock
            {
                Text = name + "   (" + count + ")",
                Foreground = Accent,
                FontWeight = FontWeights.SemiBold,
                FontSize = 13
            },
            Foreground = Text,
            IsExpanded = false
        };
    }

    private CatalogItem AmmoFor(CatalogItem weapon)
    {
        if (weapon.AmmoNumber <= 0) return null;
        return _all.FirstOrDefault(x => x.Command == "equipment" && x.Number == weapon.AmmoNumber);
    }

    private void AddWithAmmo(TreeViewItem parent, CatalogItem p)
    {
        var node = Node(p, 56);
        CatalogItem m = AmmoFor(p);
        if (m != null) node.Items.Add(Node(m, 44));
        parent.Items.Add(node);
    }

    /// Builds the tree. With a search term filled in a flat list is shown instead.
    private void BuildTree(string term)
    {
        _tree.Items.Clear();
        term = (term ?? "").Trim();

        if (term.Length > 0)
        {
            var found = _all.Where(p =>
                p.Name.IndexOf(term, StringComparison.CurrentCultureIgnoreCase) >= 0 ||
                p.Id.IndexOf(term, StringComparison.OrdinalIgnoreCase) >= 0).ToList();
            foreach (CatalogItem p in found)
                _tree.Items.Add(Node(p, 56));
            _status.Text = found.Count + " items found";
            return;
        }

        var vehicles = _all.Where(p => p.Command == "vehicle").ToList();
        var vehicleNode = GroupNode(GroupVehicles, vehicles.Count);
        foreach (CatalogItem v in vehicles)
        {
            var node = Node(v, 72);
            foreach (CatalogItem weapon in _all.Where(x => x.Carrier == v.Id))
                AddWithAmmo(node, weapon);
            CatalogItem stored = _all.FirstOrDefault(
                x => x.Group == GroupStoredVehicles && x.Name == v.Name);
            if (stored != null) node.Items.Add(Node(stored, 44));
            vehicleNode.Items.Add(node);
        }
        _tree.Items.Add(vehicleNode);

        var gear = _all.Where(p => p.Group == GroupGear).ToList();
        var gearNode = GroupNode(GroupGear, gear.Count);
        foreach (CatalogItem p in gear) AddWithAmmo(gearNode, p);
        _tree.Items.Add(gearNode);

        // Helicopter and other weapons without a carrier: which helicopter can
        // take them is nowhere in the data, so they stay together.
        var orphans = _all.Where(p => p.Group == GroupVehicleWeapons
                                      && string.IsNullOrEmpty(p.Carrier)).ToList();
        var orphanNode = GroupNode("Weapons with no listed carrier", orphans.Count);
        foreach (CatalogItem p in orphans) AddWithAmmo(orphanNode, p);
        _tree.Items.Add(orphanNode);

        var ammo = _all.Where(p => p.Group == GroupAmmo).ToList();
        var ammoNode = GroupNode("Ammunition on its own", ammo.Count);
        foreach (CatalogItem p in ammo) ammoNode.Items.Add(Node(p, 44));
        _tree.Items.Add(ammoNode);

        _status.Text = _all.Count + " items. Pick one and press Add, or double-click it.";
    }

    private CatalogItem Selected()
    {
        var node = _tree.SelectedItem as TreeViewItem;
        return node == null ? null : node.Tag as CatalogItem;
    }

    private void ShowDetail()
    {
        CatalogItem p = Selected();
        if (p == null)
        {
            _detailName.Text = "";
            _detailCommand.Text = "";
            _detailDescription.Text = "";
            _detailImage.Source = null;
            return;
        }
        _detailName.Text = p.Name;
        string line = p.AsCommand + "   ·   " + p.Id;
        CatalogItem m = AmmoFor(p);
        if (m != null) line += "   ·   ammo: " + m.Name;
        if (!string.IsNullOrEmpty(p.Stock)) line += "   ·   " + p.Stock + " per pickup";
        // The trade value: the trader wants about 1.2x this for what he gives.
        if (!string.IsNullOrEmpty(p.Value)) line += "   ·   trade value " + p.Value;
        _detailCommand.Text = line;
        _detailDescription.Text = string.IsNullOrEmpty(p.Description)
            ? "(the game has no description for this item)" : p.Description;
        _detailImage.Source = Load(p.ImageFile);
    }

    // ------------------------------------------------------------------- call

    private void Send()
    {
        CatalogItem p = Selected();
        if (p == null)
        {
            SetStatus("Pick an item first.", true);
            return;
        }

        string result = Add(p);
        if (result != null) { SetStatus(result, true); return; }

        string message = "Added: " + p.Name + "   (" + p.AsCommand + ")";

        // A weapon without ammunition is useless, so both go in at once.
        if (_withAmmo.IsChecked == true && p.AmmoNumber > 0)
        {
            CatalogItem m = _all.FirstOrDefault(x => x.Command == "equipment"
                                                     && x.Number == p.AmmoNumber);
            if (m != null)
            {
                string error = Add(m);
                message += error == null
                    ? "  +  " + m.Name
                    : "  (the ammunition could not be added)";
            }
        }

        SetStatus(message + ". If you cannot see it, leave the screen and come back - "
                  + "the list is only redrawn on entry.", false);
    }

    /// Calls the cheat for one item. Returns null on success, a message
    /// otherwise. The call itself lives in GameLink, the console window uses
    /// the same one.
    private string Add(CatalogItem p)
    {
        uint returned;
        string error = GameLink.RunCheat(
            p.Command == "vehicle" ? GameLink.CheatVehicle : GameLink.CheatEquipment,
            "(" + p.Number + ")", out returned);
        if (error != null) return error;
        if (returned == 0)
            return "The game refused: " + p.Name + " (" + p.AsCommand + "). "
                   + "Some things can only be added on a particular base screen.";
        return null;
    }

    private void SetStatus(string text, bool warning)
    {
        _status.Text = text;
        _status.Foreground = warning ? Accent : Dim;
    }
}
