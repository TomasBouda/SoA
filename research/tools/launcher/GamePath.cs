// Where the game is.
//
// In the full package the answer never changes: a Game folder beside the
// launcher. The kit has no game in it at all - it is meant to be handed to
// someone who owns their own copy - so it has to find one, and be told where
// if it cannot.
//
// Everything that reaches into the game asks here rather than building the
// path itself, which is why the five places that used to say `Game` no longer
// do: App, Console twice, Saves and SelfTest.
//
// The order it looks in:
//
//   1. a Game folder beside the launcher          the full package
//   2. what someone pointed it at before          remembered in our own key
//   3. INSTALLDIR under the game's registry key   a normal installation
//
// and if none of those has a soa.exe, it asks - once, and remembers the answer.

using System;
using System.Diagnostics;
using System.IO;
using Microsoft.Win32;

internal static class GamePath
{
    private const string RegKey = @"Software\Silver Style Entertainment\Soldiers of Anarchy";
    private const string LauncherKey = RegKey + @"\Launcher";

    /// The build every address in GameLink was read off. A different one will
    /// have moved them all, and calling into it would take the game down
    /// rather than fail politely, so it is worth saying so out loud.
    public const string KnownVersion = "1.1.2.178";

    private static string _folder;

    /// The game folder, or null if none has been found and nobody has said
    /// where it is.
    public static string Folder
    {
        get
        {
            if (_folder != null) return _folder;
            foreach (string candidate in Candidates())
                if (Holds(candidate)) { _folder = candidate; break; }
            return _folder;
        }
    }

    private static System.Collections.Generic.IEnumerable<string> Candidates()
    {
        string here = AppDomain.CurrentDomain.BaseDirectory;
        yield return Path.Combine(here, "Game");
        yield return Remembered();
        yield return Installed();
        // A kit unpacked straight into a game folder should work too.
        yield return here;
    }

    private static bool Holds(string folder)
    {
        return !string.IsNullOrEmpty(folder)
            && File.Exists(Path.Combine(folder, "soa.exe"));
    }

    private static string Remembered()
    {
        try
        {
            using (RegistryKey k = Registry.CurrentUser.OpenSubKey(LauncherKey))
                return k == null ? null : k.GetValue("GameFolder") as string;
        }
        catch (Exception) { return null; }
    }

    private static string Installed()
    {
        try
        {
            using (RegistryKey k = Registry.CurrentUser.OpenSubKey(RegKey))
                return k == null ? null : k.GetValue("INSTALLDIR") as string;
        }
        catch (Exception) { return null; }
    }

    /// Take the folder someone chose. Returns false if there is no game in it.
    public static bool Use(string folder)
    {
        if (!Holds(folder)) return false;
        _folder = folder;
        try
        {
            using (RegistryKey k = Registry.CurrentUser.CreateSubKey(LauncherKey))
                if (k != null) k.SetValue("GameFolder", folder, RegistryValueKind.String);
        }
        catch (Exception) { }
        return true;
    }

    /// Ask for soa.exe rather than for a folder: a file dialog is the one WPF
    /// has of its own, and pointing at the exe is less ambiguous than pointing
    /// at a folder that may or may not be the right one.
    public static bool Ask()
    {
        var dialog = new OpenFileDialog
        {
            Title = "Where is Soldiers of Anarchy?",
            Filter = "The game (soa.exe)|soa.exe|Any program|*.exe",
            CheckFileExists = true
        };
        if (dialog.ShowDialog() != true) return false;
        return Use(Path.GetDirectoryName(dialog.FileName));
    }

    public static bool Found { get { return Folder != null; } }

    public static string In(params string[] parts)
    {
        string folder = Folder ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Game");
        foreach (string p in parts) folder = Path.Combine(folder, p);
        return folder;
    }

    public static string Exe { get { return In("soa.exe"); } }

    /// What version the game says it is, or null if it will not say.
    public static string Version()
    {
        try
        {
            return Found ? FileVersionInfo.GetVersionInfo(Exe).FileVersion : null;
        }
        catch (Exception) { return null; }
    }

    /// Null when the game is one the launcher understands, otherwise what is
    /// wrong with it. Everything GameLink does is tied to the addresses of one
    /// build, so a different one is worth refusing rather than crashing into.
    public static string Trouble()
    {
        if (!Found) return "The game was not found. Point the launcher at soa.exe.";
        string version = Version();
        if (version == null) return "soa.exe is there but will not say what version it is.";
        if (version != KnownVersion)
            return "This is soa.exe " + version + ", and the launcher knows "
                 + KnownVersion + " - the last official patch. Starting the game will "
                 + "work; the catalog, the console and the map read addresses that "
                 + "only hold for that build, so they are switched off.";
        return null;
    }
}
