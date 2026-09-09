// The model browser: 1253 of them down the side, one turning under the mouse.
//
// It draws with WPF's own 3D, which needs nothing installed and is why the
// launcher can show a textured model without a single dependency. Diff3D does
// the reading and models.md explains the format; this is only the window.
//
// A part is drawn with the texture its material names, which is why a rifle
// comes up with a wooden stock rather than with its own muzzle flash smeared
// over it. Where a material has no texture the part is drawn in plain grey.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Media.Media3D;

internal sealed class ModelsWindow : Window
{
    private static readonly Brush Bg = Paint("#FF191B20");
    private static readonly Brush Panel = Paint("#FF23262E");
    private static readonly Brush Line = Paint("#FF33384A");
    private static readonly Brush Text = Paint("#FFE6E8EE");
    private static readonly Brush Dim = Paint("#FF8E93A3");
    private static readonly Brush Accent = Paint("#FFC8A24A");

    private static SolidColorBrush Paint(string hex)
    {
        return new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
    }

    private readonly string _gameDir;
    private readonly ListBox _list;
    private readonly TextBox _search;
    private readonly TextBlock _status;
    private readonly TextBlock _detail;
    private readonly Viewport3D _view;
    private readonly ModelVisual3D _stage = new ModelVisual3D();
    private readonly PerspectiveCamera _camera = new PerspectiveCamera();
    private readonly CheckBox _effects;
    private readonly CheckBox _poses;

    private List<string> _all = new List<string>();
    private GameModel _shown;
    private double _turn = 40, _tilt = 22, _distance = 400, _span = 100;
    private Point3D _middle;
    private Point _grabbed;
    private bool _dragging;

    public ModelsWindow()
    {
        Title = "Models";
        Width = 1080;
        Height = 700;
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

        var side = new DockPanel { Width = 320, Margin = new Thickness(0, 0, 14, 0) };
        _search = new TextBox
        {
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line,
            Padding = new Thickness(6, 4, 6, 4),
            Margin = new Thickness(0, 0, 0, 8)
        };
        _search.TextChanged += (s, e) => Fill();
        DockPanel.SetDock(_search, Dock.Top);
        side.Children.Add(_search);

        _effects = new CheckBox
        {
            Content = "Show lamps, glows and effect markers",
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 0, 0, 8)
        };
        _effects.Checked += (s, e) => Draw();
        _effects.Unchecked += (s, e) => Draw();
        DockPanel.SetDock(_effects, Dock.Bottom);
        side.Children.Add(_effects);

        _poses = new CheckBox
        {
            Content = "Show every pose a weapon is stored in",
            Foreground = Dim,
            FontSize = 11,
            Margin = new Thickness(0, 0, 0, 4),
            ToolTip = "A weapon is written three times over, the same mesh in the "
                    + "poses the engine picks between. Only the one in hand is drawn."
        };
        _poses.Checked += (s, e) => Draw();
        _poses.Unchecked += (s, e) => Draw();
        DockPanel.SetDock(_poses, Dock.Bottom);
        side.Children.Add(_poses);

        _list = new ListBox
        {
            Background = Panel,
            Foreground = Text,
            BorderBrush = Line
        };
        _list.SelectionChanged += (s, e) => Show(_list.SelectedItem as string);
        side.Children.Add(_list);
        DockPanel.SetDock(side, Dock.Left);
        root.Children.Add(side);

        var right = new DockPanel();
        _detail = new TextBlock
        {
            Foreground = Dim,
            FontSize = 12,
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 8, 0, 0)
        };
        DockPanel.SetDock(_detail, Dock.Bottom);
        right.Children.Add(_detail);

        _view = new Viewport3D { ClipToBounds = true };
        _view.Camera = _camera;
        _view.Children.Add(_stage);
        var frame = new Border
        {
            Background = Paint("#FF14161A"),
            BorderBrush = Line,
            BorderThickness = new Thickness(1),
            Child = _view
        };
        frame.MouseLeftButtonDown += (s, e) =>
        {
            _grabbed = e.GetPosition(frame);
            _dragging = true;
            frame.CaptureMouse();
        };
        frame.MouseLeftButtonUp += (s, e) => { _dragging = false; frame.ReleaseMouseCapture(); };
        frame.MouseMove += (s, e) =>
        {
            if (!_dragging) return;
            Point now = e.GetPosition(frame);
            _turn -= (now.X - _grabbed.X) * 0.5;
            _tilt = Math.Max(-89, Math.Min(89, _tilt + (now.Y - _grabbed.Y) * 0.5));
            _grabbed = now;
            Aim();
        };
        frame.MouseWheel += (s, e) =>
        {
            _distance *= e.Delta > 0 ? 0.88 : 1.14;
            _distance = Math.Max(_span * 0.4, Math.Min(_span * 12, _distance));
            Aim();
        };
        right.Children.Add(frame);
        root.Children.Add(right);

        Content = root;
        Load();
    }

    private void Load()
    {
        _all = Diff3D.Names(_gameDir);
        Fill();
        _status.Text = _all.Count == 0
            ? "No objects.ubn under " + _gameDir + "."
            : _all.Count + " models. Drag to turn one, the wheel to come closer.";
    }

    private void Fill()
    {
        string want = (_search.Text ?? "").Trim().ToLowerInvariant();
        _list.Items.Clear();
        foreach (string name in _all)
            if (want.Length == 0 || name.ToLowerInvariant().Contains(want))
                _list.Items.Add(name);
        if (_list.Items.Count > 0 && _shown == null) _list.SelectedIndex = 0;
    }

    private void Show(string name)
    {
        if (name == null) return;
        byte[] raw = Diff3D.Bytes(_gameDir, name);
        if (raw == null)
        {
            _status.Text = "Could not read " + name + " out of the archive.";
            return;
        }
        try { _shown = Diff3D.Read(name, raw); }
        catch (Exception e) { _shown = null; _status.Text = e.Message; return; }
        if (_shown == null) { _status.Text = name + " is not a model."; return; }

        int points = 0, faces = 0;
        foreach (ModelPart p in _shown.Parts) { points += p.Positions.Count; faces += p.Indices.Count / 3; }
        var said = new List<string>();
        said.Add(_shown.Parts.Count + " parts, " + points + " vertices, " + faces + " faces");
        if (_shown.Source != null) said.Add("exported from " + _shown.Source);
        var textures = new List<string>();
        foreach (string m in _shown.Materials) if (m != null && !textures.Contains(m)) textures.Add(m);
        if (textures.Count > 0) said.Add(string.Join(", ", textures.ToArray()));
        _detail.Text = string.Join("   -   ", said.ToArray());

        _turn = 40;
        _tilt = 22;
        Draw();
    }

    /// Effect markers carry no geometry worth looking at - a lamp is a flat
    /// quad lying across the whole car - so they are off unless asked for.
    private static bool IsEffect(string node)
    {
        if (string.IsNullOrEmpty(node)) return false;
        string low = node.ToLowerInvariant();
        return low.Contains("licht") || low.Contains("glow")
            || low.Contains("effekt") || low.Contains("flash") || low.StartsWith("dmy");
    }

    private void Draw()
    {
        _stage.Content = null;
        if (_shown == null) return;

        var group = new Model3DGroup();
        var cache = new Dictionary<int, Material>();
        var lo = new Point3D(1e30, 1e30, 1e30);
        var hi = new Point3D(-1e30, -1e30, -1e30);
        bool any = false;

        foreach (ModelPart part in _shown.Parts)
        {
            if (!(_effects.IsChecked ?? false) && IsEffect(part.Node)) continue;
            if (part.Variant > 0 && !(_poses.IsChecked ?? false)) continue;
            var mesh = new MeshGeometry3D
            {
                Positions = part.Positions,
                Normals = part.Normals,
                TextureCoordinates = part.Texture,
                TriangleIndices = part.Indices
            };
            Material material;
            if (!cache.TryGetValue(part.Material, out material))
            {
                material = Skin(part.Material);
                cache[part.Material] = material;
            }
            group.Children.Add(new GeometryModel3D(mesh, material)
            {
                BackMaterial = material
            });
            foreach (Point3D p in part.Positions)
            {
                lo = new Point3D(Math.Min(lo.X, p.X), Math.Min(lo.Y, p.Y), Math.Min(lo.Z, p.Z));
                hi = new Point3D(Math.Max(hi.X, p.X), Math.Max(hi.Y, p.Y), Math.Max(hi.Z, p.Z));
                any = true;
            }
        }
        if (!any) { _status.Text = "Nothing in it to draw."; return; }

        group.Children.Add(new AmbientLight(Color.FromRgb(90, 90, 96)));
        group.Children.Add(new DirectionalLight(Color.FromRgb(210, 208, 200),
                                                new Vector3D(-0.5, -0.8, -0.4)));
        group.Children.Add(new DirectionalLight(Color.FromRgb(70, 74, 84),
                                                new Vector3D(0.6, 0.5, 0.3)));
        _stage.Content = group;

        _middle = new Point3D((lo.X + hi.X) / 2, (lo.Y + hi.Y) / 2, (lo.Z + hi.Z) / 2);
        _span = Math.Max(hi.X - lo.X, Math.Max(hi.Y - lo.Y, hi.Z - lo.Z));
        if (_span <= 0) _span = 100;
        _distance = _span * 2.2;
        Aim();
        _status.Text = _shown.Name;
    }

    private Material Skin(int index)
    {
        string named = index >= 0 && index < _shown.Materials.Count
                     ? _shown.Materials[index] : null;
        BitmapSource picture = named == null ? null : Diff3D.Texture(_gameDir, named);
        if (picture == null)
            return new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(178, 174, 164)));
        var brush = new ImageBrush(picture)
        {
            ViewportUnits = BrushMappingMode.Absolute,
            TileMode = TileMode.Tile
        };
        brush.Freeze();
        return new DiffuseMaterial(brush);
    }

    /// The camera, turned round the model rather than the model round itself,
    /// so that nothing has to be rebuilt to look at it from somewhere else.
    private void Aim()
    {
        double a = _turn * Math.PI / 180.0, b = _tilt * Math.PI / 180.0;
        // The models stand in z, so z is up here and the camera swings in x and y.
        var eye = new Point3D(
            _middle.X + _distance * Math.Cos(b) * Math.Sin(a),
            _middle.Y - _distance * Math.Cos(b) * Math.Cos(a),
            _middle.Z + _distance * Math.Sin(b));
        _camera.Position = eye;
        _camera.LookDirection = _middle - eye;
        _camera.UpDirection = new Vector3D(0, 0, 1);
        _camera.FieldOfView = 45;
        _camera.NearPlaneDistance = Math.Max(0.1, _span * 0.01);
        _camera.FarPlaneDistance = _span * 40;
    }
}
