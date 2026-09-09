// The catalog, out of the launcher itself.
//
// It used to sit beside Play.exe as catalog.txt and a folder of 156 pictures,
// which is 2.6 MB of loose files in a package where nothing else is loose. Now
// the full package builds them into a zip and the compiler puts that inside the
// exe, so the package is Play.exe and the game and nothing in between.
//
// Loose files still win where they exist. That is deliberate and it is the same
// rule the game itself follows for its archives: a file next to the program
// beats the one packed inside it. It leaves room for a catalog made on the
// player's own machine - which is how the kit will have to get one, since the
// catalog is built out of the game's data and may not be handed to anybody.
//
// A kit therefore carries no catalog resource at all, and the window simply
// finds nothing until something generates one.

using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Reflection;

internal static class CatalogData
{
    // The name the build gives the embedded zip: /resource:catalog.zip,SoA.Catalog
    private const string Resource = "SoA.Catalog";

    private static Dictionary<string, byte[]> _packed;
    private static bool _looked;

    /// Everything in the embedded zip by its name inside it, or an empty set
    /// when the exe carries none - which is what a kit looks like.
    private static Dictionary<string, byte[]> Packed()
    {
        if (_looked) return _packed;
        _looked = true;
        _packed = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
        try
        {
            using (Stream raw = Assembly.GetExecutingAssembly()
                                        .GetManifestResourceStream(Resource))
            {
                if (raw == null) return _packed;
                using (var zip = new ZipArchive(raw, ZipArchiveMode.Read))
                    foreach (ZipArchiveEntry entry in zip.Entries)
                    {
                        using (var memory = new MemoryStream())
                        using (Stream open = entry.Open())
                        {
                            open.CopyTo(memory);
                            _packed[entry.FullName.Replace('\\', '/')] = memory.ToArray();
                        }
                    }
            }
        }
        catch (Exception) { }
        return _packed;
    }

    private static string Beside(string name)
    {
        return Path.Combine(AppDomain.CurrentDomain.BaseDirectory,
                            name.Replace('/', Path.DirectorySeparatorChar));
    }

    /// One file of the catalog, loose copy first. Null when there is none.
    public static byte[] Read(string name)
    {
        string path = Beside(name);
        if (File.Exists(path))
        {
            try { return File.ReadAllBytes(path); }
            catch (Exception) { }
        }
        byte[] found;
        return Packed().TryGetValue(name, out found) ? found : null;
    }

    /// The lines of catalog.txt, or nothing at all.
    public static string[] Lines()
    {
        byte[] raw = Read("catalog.txt");
        if (raw == null) return new string[0];
        // The file is written UTF-8 by tools/gen_catalog.py, with or without a
        // byte order mark depending on which run wrote it.
        string text = new System.Text.UTF8Encoding(false).GetString(raw).TrimStart('﻿');
        return text.Replace("\r\n", "\n").Split('\n');
    }

    /// One picture out of the catalog folder.
    public static byte[] Picture(string file)
    {
        return string.IsNullOrEmpty(file) ? null : Read("catalog/" + file);
    }

    /// Whether there is a catalog to show at all.
    public static bool Present { get { return Read("catalog.txt") != null; } }
}
