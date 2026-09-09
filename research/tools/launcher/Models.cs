// The game's 3D models, read and drawn.
//
// `objects.ubn` holds 1253 `.diff3D` files - every soldier, vehicle, building,
// tree and animal the game draws. The format is the same serialiser as the
// saves with `0x34` in front of the magic instead of `0x38`, and models.md has
// the whole of it. This is that reader ported to C#, and a window to turn one
// under the mouse.
//
// The three things that matter, in the order they were hard to find:
//
// * A vertex is forty bytes - position, normal, diffuse, specular, one pair of
//   texture coordinates - and a face is twenty. The exporter wrote white into
//   every diffuse colour, so a vertex list shows up as `FF FF FF FF` repeating
//   on a forty byte stride, and that is the anchor everything hangs off.
// * The first field of a face is a material index. The material list follows
//   the exporter's `.ASE` line and some of its entries have no texture at all,
//   which is why counting texture names instead very nearly works and then
//   silently puts a rifle's muzzle flash on its stock.
// * **The file carries a tree and it is the last thing in it** - a table of
//   `type | children | offset | size` chunks written depth first. A part's
//   place is its own matrix multiplied out through every parent above it. The
//   wheels of a vehicle hang off the root and its doors off the body, so a door
//   takes three matrices and a wheel takes one.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Media.Media3D;

/// One drawable piece of a model, already placed.
internal sealed class ModelPart
{
    public string Node;
    public int Material;
    public int Variant;                         // 0 unless another pose of the same thing
    public Point3DCollection Positions = new Point3DCollection();
    public Vector3DCollection Normals = new Vector3DCollection();
    public PointCollection Texture = new PointCollection();
    public Int32Collection Indices = new Int32Collection();
}

internal sealed class GameModel
{
    public string Name;
    public string Source;                       // the .ASE it was exported from
    public List<string> Materials = new List<string>();   // null where untextured
    public List<ModelPart> Parts = new List<ModelPart>();
}

internal static class Diff3D
{
    private const int VertexSize = 40;
    private const int FaceSize = 20;
    private const int NodeHeader = 104;
    private const uint ChunkNode = 0x10000;
    private const uint ChunkMesh = 0x10002;

    private static readonly byte[] MagicTail =
    {
        0xF9, 0xB3, 0x0A, 0x62, 0x93, 0xD1, 0x11, 0x9A,
        0x2B, 0x08, 0x00, 0x00, 0x30, 0x05, 0x12
    };

    public static bool IsModel(byte[] raw)
    {
        if (raw.Length < 0x94 || raw[8] != 0x34) return false;
        for (int i = 0; i < MagicTail.Length; i++)
            if (raw[9 + i] != MagicTail[i]) return false;
        return true;
    }

    // ------------------------------------------------------------- the strings

    /// Every length-prefixed string with its offset, the same convention the
    /// saves use.
    private static List<KeyValuePair<int, string>> Strings(byte[] raw, int from)
    {
        var found = new List<KeyValuePair<int, string>>();
        int i = Math.Max(0, from);
        while (i < raw.Length - 1)
        {
            int n = raw[i];
            if (n >= 3 && n <= 96 && i + 1 + n <= raw.Length)
            {
                bool printable = true;
                for (int k = 1; k <= n; k++)
                    if (raw[i + k] < 32 || raw[i + k] >= 127) { printable = false; break; }
                if (printable)
                {
                    found.Add(new KeyValuePair<int, string>(
                        i, Encoding.ASCII.GetString(raw, i + 1, n)));
                    i += 1 + n;
                    continue;
                }
            }
            i++;
        }
        return found;
    }

    private static string NameAt(byte[] raw, int nodeStart)
    {
        foreach (KeyValuePair<int, string> pair in Strings(raw, nodeStart + 100))
            if (pair.Key >= nodeStart + NodeHeader) return pair.Value;
        return null;
    }

    // ------------------------------------------------------------ the geometry

    /// Where the vertex lists are, found by the white the exporter wrote into
    /// every diffuse colour. Nothing else in a file repeats on a forty byte
    /// stride for long.
    private static List<KeyValuePair<int, int>> VertexBlocks(byte[] raw)
    {
        var white = new HashSet<int>();
        for (int i = 0; i + 4 <= raw.Length; i++)
            if (raw[i] == 0xFF && raw[i + 1] == 0xFF && raw[i + 2] == 0xFF && raw[i + 3] == 0xFF)
                white.Add(i);

        var found = new List<KeyValuePair<int, int>>();
        var used = new HashSet<int>();
        var sorted = new List<int>(white);
        sorted.Sort();
        foreach (int h in sorted)
        {
            if (h < 24 || used.Contains(h)) continue;
            int n = 0;
            while (white.Contains(h + n * VertexSize)) { used.Add(h + n * VertexSize); n++; }
            if (n >= 4) found.Add(new KeyValuePair<int, int>(h - 24, n));
        }
        return found;
    }

    private static bool WhiteEnough(byte[] raw, int start, int count)
    {
        if (start < 0 || start + count * VertexSize > raw.Length) return false;
        int white = 0;
        for (int k = 0; k < count; k++)
            if (BitConverter.ToUInt32(raw, start + k * VertexSize + 24) == 0xFFFFFFFF) white++;
        return white >= count * 0.8;
    }

    /// One mesh, worked out backwards from where its vertices begin: the face
    /// list, then twenty bytes nobody has explained, then the vertices, landing
    /// exactly on the byte the anchor found.
    private static ModelPart MeshAt(byte[] raw, int vertStart, int count,
                                    out int header, out int material)
    {
        header = -1;
        material = 0;
        ModelPart best = null;
        byte[] want = BitConverter.GetBytes(count);

        for (int at = 0; at + 4 <= vertStart - 32; at++)
        {
            if (raw[at] != want[0] || raw[at + 1] != want[1]
                || raw[at + 2] != want[2] || raw[at + 3] != want[3]) continue;
            int h = at - 4;
            if (h < 0) continue;
            long faces = BitConverter.ToUInt32(raw, h);
            if (faces <= 0 || faces > 200000) continue;
            long faceStart = vertStart - 20 - faces * FaceSize;
            if (faceStart <= h + 8 || faceStart - h > 512) continue;

            bool ok = true;
            for (int k = 0; k < faces && ok; k++)
            {
                int off = (int)faceStart + k * FaceSize;
                if (off < 0 || off + FaceSize > raw.Length) { ok = false; break; }
                for (int e = 0; e < 3; e++)
                    if (BitConverter.ToUInt32(raw, off + 8 + e * 4) >= count) { ok = false; break; }
            }
            if (!ok || !WhiteEnough(raw, vertStart, count)) continue;
            if (best != null && best.Indices.Count / 3 >= faces) continue;

            var part = new ModelPart();
            for (int k = 0; k < count; k++)
            {
                int off = vertStart + k * VertexSize;
                part.Positions.Add(new Point3D(BitConverter.ToSingle(raw, off),
                                               BitConverter.ToSingle(raw, off + 4),
                                               BitConverter.ToSingle(raw, off + 8)));
                part.Normals.Add(new Vector3D(BitConverter.ToSingle(raw, off + 12),
                                              BitConverter.ToSingle(raw, off + 16),
                                              BitConverter.ToSingle(raw, off + 20)));
                part.Texture.Add(new Point(BitConverter.ToSingle(raw, off + 32),
                                           BitConverter.ToSingle(raw, off + 36)));
            }
            int first = BitConverter.ToInt32(raw, (int)faceStart);
            for (int k = 0; k < faces; k++)
            {
                int off = (int)faceStart + k * FaceSize;
                part.Indices.Add(BitConverter.ToInt32(raw, off + 8));
                part.Indices.Add(BitConverter.ToInt32(raw, off + 12));
                part.Indices.Add(BitConverter.ToInt32(raw, off + 16));
            }
            best = part;
            header = (int)faceStart;
            material = first;
        }
        return best;
    }

    // ---------------------------------------------------------------- the tree

    private struct Chunk
    {
        public uint Kind;
        public int Children;
        public int Offset;
        public int Size;
    }

    /// The table of chunks, which is the last thing in the file. It is found by
    /// walking backwards for as long as the entries make sense, because nothing
    /// says where it begins.
    private static List<Chunk> Directory(byte[] raw)
    {
        int at = raw.Length - 16;
        int baseAt = (int)BitConverter.ToUInt32(raw, 0);
        var rows = new List<Chunk>();
        while (at >= 0)
        {
            uint kind = BitConverter.ToUInt32(raw, at);
            if (kind != 0x10000 && kind != 0x10001 && kind != 0x10002 && kind != 0x10003) break;
            int children = (int)BitConverter.ToUInt32(raw, at + 4);
            long off = BitConverter.ToUInt32(raw, at + 8);
            long size = BitConverter.ToUInt32(raw, at + 12);
            if (baseAt + off + size > raw.Length || children < 0 || children > 4096) break;
            rows.Insert(0, new Chunk
            {
                Kind = kind,
                Children = children,
                Offset = baseAt + (int)off,
                Size = (int)size
            });
            at -= 16;
        }
        return rows;
    }

    /// Who is whose parent, from the depth-first order and the child counts.
    private static int[] Hierarchy(List<Chunk> rows)
    {
        var parent = new int[rows.Count];
        var stack = new List<int[]>();          // {index, children still to come}
        for (int i = 0; i < rows.Count; i++)
        {
            while (stack.Count > 0 && stack[stack.Count - 1][1] == 0)
                stack.RemoveAt(stack.Count - 1);
            if (stack.Count > 0)
            {
                parent[i] = stack[stack.Count - 1][0];
                stack[stack.Count - 1][1]--;
            }
            else parent[i] = -1;
            stack.Add(new[] { i, rows[i].Children });
        }
        return parent;
    }

    private static Matrix3D MatrixAt(byte[] raw, int nodeStart)
    {
        var f = new double[16];
        for (int k = 0; k < 16; k++) f[k] = BitConverter.ToSingle(raw, nodeStart + 8 + k * 4);
        if (f[15] != 1.0) return Matrix3D.Identity;
        return new Matrix3D(f[0], f[1], f[2], f[3],
                            f[4], f[5], f[6], f[7],
                            f[8], f[9], f[10], f[11],
                            f[12], f[13], f[14], f[15]);
    }

    // ----------------------------------------------------------- the materials

    /// The material list: the texture each one uses, or null where it has none.
    /// A material is `1`, a flag and a texture name, or a bare `0`. Every number
    /// arrives wrapped as `0C 00 00 00 | 00 00 00 00 | value`.
    private static List<string> Materials(byte[] raw, int at)
    {
        var found = new List<string>();
        int count;
        if (!Number(raw, ref at, out count) || count <= 0 || count > 256) return found;
        for (int i = 0; i < count; i++)
        {
            int has;
            if (!Number(raw, ref at, out has)) break;
            if (has == 0) { found.Add(null); continue; }
            int flag;
            if (!Number(raw, ref at, out flag)) break;
            if (at >= raw.Length) break;
            int n = raw[at];
            if (n < 3 || n > 96 || at + 1 + n > raw.Length) { found.Add(null); continue; }
            bool printable = true;
            for (int k = 1; k <= n; k++)
                if (raw[at + k] < 32 || raw[at + k] >= 127) { printable = false; break; }
            if (!printable) { found.Add(null); continue; }
            found.Add(Encoding.ASCII.GetString(raw, at + 1, n));
            at += 1 + n;
        }
        return found;
    }

    private static bool Number(byte[] raw, ref int at, out int value)
    {
        value = 0;
        if (at + 12 > raw.Length) return false;
        if (BitConverter.ToUInt32(raw, at) != 12 || BitConverter.ToUInt32(raw, at + 4) != 0)
            return false;
        value = (int)BitConverter.ToUInt32(raw, at + 8);
        at += 12;
        return true;
    }

    // ---------------------------------------------------------------- the whole

    /// `ak74_2` as `ak74`: a trailing number and nothing else.
    private static string BaseName(string name)
    {
        if (string.IsNullOrEmpty(name)) return name;
        int end = name.Length;
        while (end > 0 && name[end - 1] >= '0' && name[end - 1] <= '9') end--;
        if (end == name.Length || end == 0 || name[end - 1] != '_') return name;
        return name.Substring(0, end - 1);
    }

    /// The nodes that are the same thing again, as {chunk: which one}.
    ///
    /// A weapon is written three times over - `ak74_0`, `ak74_1`, `ak74_2`, the
    /// same 99 vertices in three places, which are the poses the engine picks
    /// between. Drawn all at once a rifle comes up as three rifles.
    ///
    /// They are told apart from parts that merely share a name by where they sit
    /// in the tree: a weapon's poses are the only children the root has, while a
    /// truck's `wheel_axle_1` and `wheel_axle_2` are two among nine other parts
    /// that are nothing like them. Going by the name alone would hide one of the
    /// truck's axles.
    private static Dictionary<int, int> Variants(byte[] raw, List<Chunk> rows, int[] parent)
    {
        var children = new List<int>();
        for (int i = 0; i < rows.Count; i++)
            if (parent[i] == 0 && rows[i].Kind == ChunkNode && NameAt(raw, rows[i].Offset) != null)
                children.Add(i);
        var found = new Dictionary<int, int>();
        if (children.Count < 2) return found;

        string first = NameAt(raw, rows[children[0]].Offset);
        string want = BaseName(first);
        if (want == first) return found;              // no trailing number at all
        foreach (int c in children)
            if (BaseName(NameAt(raw, rows[c].Offset)) != want) return found;
        for (int n = 0; n < children.Count; n++) found[children[n]] = n;
        return found;
    }

    public static GameModel Read(string name, byte[] raw)
    {
        if (!IsModel(raw)) return null;
        var model = new GameModel { Name = name };

        foreach (KeyValuePair<int, string> pair in Strings(raw, 0x90))
            if (pair.Value.StartsWith("root node - ", StringComparison.OrdinalIgnoreCase))
            {
                model.Source = pair.Value.Substring("root node - ".Length);
                model.Materials = Materials(raw, pair.Key + 1 + pair.Value.Length);
                break;
            }

        List<Chunk> rows = Directory(raw);
        int[] parent = rows.Count > 0 ? Hierarchy(rows) : new int[0];
        Dictionary<int, int> poses = rows.Count > 0
            ? Variants(raw, rows, parent) : new Dictionary<int, int>();

        foreach (KeyValuePair<int, int> block in VertexBlocks(raw))
        {
            int header, material;
            ModelPart part = MeshAt(raw, block.Key, block.Value, out header, out material);
            if (part == null) continue;
            part.Material = material;

            // A mesh chunk sits inside the node it belongs to, and a part's
            // place is its own matrix multiplied out through every parent above.
            int owner = -1;
            for (int i = 0; i < rows.Count; i++)
                if (rows[i].Kind == ChunkMesh
                    && rows[i].Offset <= header && header < rows[i].Offset + rows[i].Size)
                { owner = parent[i]; break; }

            if (owner >= 0)
            {
                if (rows[owner].Kind == ChunkNode)
                    part.Node = NameAt(raw, rows[owner].Offset);
                int up = owner;
                while (up >= 0)
                {
                    int which;
                    if (poses.TryGetValue(up, out which)) { part.Variant = which; break; }
                    up = parent[up];
                }
                Matrix3D place = Matrix3D.Identity;
                int at = owner;
                var seen = new HashSet<int>();
                while (at >= 0 && !seen.Contains(at))
                {
                    seen.Add(at);
                    if (rows[at].Kind == ChunkNode && rows[at].Offset + NodeHeader <= raw.Length)
                        place.Append(MatrixAt(raw, rows[at].Offset));
                    at = parent[at];
                }
                for (int k = 0; k < part.Positions.Count; k++)
                {
                    part.Positions[k] = place.Transform(part.Positions[k]);
                    part.Normals[k] = place.Transform(part.Normals[k]);
                }
            }
            model.Parts.Add(part);
        }
        return model;
    }

    // ------------------------------------------------------------- the archive

    public static List<string> Names(string game)
    {
        var found = new List<string>();
        try
        {
            using (ZipArchive zip = ZipFile.OpenRead(Path.Combine(game, "objects.ubn")))
                foreach (ZipArchiveEntry entry in zip.Entries)
                    if (entry.FullName.EndsWith(".diff3D", StringComparison.OrdinalIgnoreCase))
                        found.Add(entry.FullName);
        }
        catch (Exception) { }
        found.Sort(StringComparer.OrdinalIgnoreCase);
        return found;
    }

    public static byte[] Bytes(string game, string name)
    {
        try
        {
            using (ZipArchive zip = ZipFile.OpenRead(Path.Combine(game, "objects.ubn")))
                foreach (ZipArchiveEntry entry in zip.Entries)
                {
                    if (!string.Equals(entry.FullName, name, StringComparison.OrdinalIgnoreCase))
                        continue;
                    // One entry's name differs between the directory and its
                    // local header, and opening it by name refuses that.
                    using (var memory = new MemoryStream())
                    using (Stream open = entry.Open())
                    {
                        open.CopyTo(memory);
                        return memory.ToArray();
                    }
                }
        }
        catch (Exception) { }
        return null;
    }

    /// One of the game's textures, by the name a model gives it. Models name
    /// them with no path, so they are matched on the file name alone; the
    /// `Winter` copies lose, because a model that wanted them would be a winter
    /// model.
    public static BitmapSource Texture(string game, string named)
    {
        if (string.IsNullOrEmpty(named)) return null;
        string want = Path.GetFileName(named).ToLowerInvariant();
        try
        {
            using (ZipArchive zip = ZipFile.OpenRead(Path.Combine(game, "textures.ubn")))
            {
                ZipArchiveEntry best = null;
                foreach (ZipArchiveEntry entry in zip.Entries)
                {
                    if (Path.GetFileName(entry.FullName).ToLowerInvariant() != want) continue;
                    bool winter = entry.FullName.ToLowerInvariant().Contains("winter");
                    if (best == null || !winter) best = entry;
                    if (!winter) break;
                }
                if (best == null) return null;
                using (var memory = new MemoryStream())
                using (Stream open = best.Open())
                {
                    open.CopyTo(memory);
                    byte[] raw = memory.ToArray();
                    return want.EndsWith(".tga") ? Targa.Decode(raw) : Decode(raw);
                }
            }
        }
        catch (Exception) { return null; }
    }

    private static BitmapSource Decode(byte[] raw)
    {
        try
        {
            var image = new BitmapImage();
            image.BeginInit();
            image.StreamSource = new MemoryStream(raw);
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.EndInit();
            image.Freeze();
            return image;
        }
        catch (Exception) { return null; }
    }
}

/// A Targa reader, because WPF has none and 150 of the game's textures are one.
///
/// Only what the game ships: 24 and 32 bit colour, uncompressed or run length
/// encoded. Anything else comes back as nothing rather than as rubbish.
internal static class Targa
{
    public static BitmapSource Decode(byte[] raw)
    {
        try
        {
            if (raw.Length < 18) return null;
            int idLength = raw[0];
            int kind = raw[2];                       // 2 plain, 10 run length
            int width = BitConverter.ToUInt16(raw, 12);
            int height = BitConverter.ToUInt16(raw, 14);
            int depth = raw[16];
            int descriptor = raw[17];
            if ((kind != 2 && kind != 10) || (depth != 24 && depth != 32)) return null;
            if (width <= 0 || height <= 0 || width > 8192 || height > 8192) return null;

            int step = depth / 8;
            int at = 18 + idLength;
            var pixels = new byte[width * height * 4];
            int put = 0;
            while (put < pixels.Length && at < raw.Length)
            {
                if (kind == 2)
                {
                    if (at + step > raw.Length) break;
                    Put(pixels, ref put, raw, at, step);
                    at += step;
                }
                else
                {
                    int packet = raw[at++];
                    int run = (packet & 0x7F) + 1;
                    if ((packet & 0x80) != 0)
                    {
                        if (at + step > raw.Length) break;
                        for (int k = 0; k < run && put < pixels.Length; k++)
                            Put(pixels, ref put, raw, at, step);
                        at += step;
                    }
                    else
                    {
                        for (int k = 0; k < run && put < pixels.Length; k++)
                        {
                            if (at + step > raw.Length) break;
                            Put(pixels, ref put, raw, at, step);
                            at += step;
                        }
                    }
                }
            }

            // Targa counts its rows from the bottom unless bit 5 says otherwise.
            if ((descriptor & 0x20) == 0)
            {
                var flipped = new byte[pixels.Length];
                int stride = width * 4;
                for (int y = 0; y < height; y++)
                    Buffer.BlockCopy(pixels, (height - 1 - y) * stride, flipped, y * stride, stride);
                pixels = flipped;
            }

            BitmapSource made = BitmapSource.Create(width, height, 96, 96,
                PixelFormats.Bgra32, null, pixels, width * 4);
            made.Freeze();
            return made;
        }
        catch (Exception) { return null; }
    }

    private static void Put(byte[] into, ref int put, byte[] raw, int at, int step)
    {
        into[put++] = raw[at];
        into[put++] = raw[at + 1];
        into[put++] = raw[at + 2];
        into[put++] = step == 4 ? raw[at + 3] : (byte)255;
    }
}
