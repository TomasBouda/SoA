// The half of the test that needs the game running.
//
// tools/check.py is the other half and needs nothing started: it compares the
// addresses in soa.exe against what is pinned for them and checks the patches
// and the catalog. What it cannot see is whether any of it still *works* -
// whether a cheat is accepted, whether a mission loads, whether the map reads.
// Those only fail while the game is up, which is how the console spent a while
// sending arguments without their brackets and nobody noticed.
//
// This drives the whole way through, using the launcher's own GameLink rather
// than a copy of it, so what is tested is what ships:
//
//     start the game and wait for it to reach its menu
//     load a known mission and wait for its world
//     send a base cheat if the base screen happens to be up
//     read the map, and the units out of the objects
//     send a mission cheat
//     quick save, quick load
//     quit
//
// It is built twice from these same sources: as SelfTest.exe, a console
// program that prints as it goes and that a shell waits for, and inside
// Play.exe behind -selftest for anyone who would rather double-click. A window
// program cannot be waited for from a command line and has nowhere to print,
// which is the whole reason for the second executable.
//
// Either way it writes selftest.txt beside itself and returns 0 when
// everything passed. Nothing here is clever; it is meant to be read when it
// fails.
//
//     SelfTest.exe
//     Play.exe -selftest

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

internal static class SelfTest
{
    private const string Mission = @"Missions\Campaign\Mission_3\Mission_3.mis";

    // How long each wait is given. The game reaches the base screen in a few
    // seconds now that the logos and the intro are skipped, and a mission
    // loads in well under half a minute. A test that hangs for a minute before
    // admitting something is wrong is worse than one that gives up early - if
    // these ever turn out to be too tight, the report says which wait ran out.
    private const int WaitForMenu = 30;
    private const int WaitForMission = 45;

    // What the campaign mission should turn out to be, so that "it loaded" is
    // a claim about the right thing. The bunker is 400 across, which is how a
    // false pass was caught: the test thought a mission had loaded when what
    // had loaded was the base.
    private const int MissionWidth = 1200;

    /// True when this is SelfTest.exe rather than Play.exe -selftest, in which
    /// case there is a console to print to and nobody wants a message box.
    private static bool _console;

    [STAThread]
    public static int Main(string[] args)
    {
        _console = true;
        return Run();
    }

    private static readonly StringBuilder Report = new StringBuilder();
    private static int _failed;

    private static void Say(string line)
    {
        Report.AppendLine(line);
        if (_console) Console.WriteLine(line);
    }

    private static void Check(string what, bool ok, string detail)
    {
        if (!ok) _failed++;
        Say(string.Format("  {0,-6} {1}{2}", ok ? "OK" : "FAIL", what,
                          string.IsNullOrEmpty(detail) ? "" : " - " + detail));
    }

    /// Whether the mission asked for is really there.
    ///
    /// Each answer here was wrong before this one. The world exists about a
    /// second after loading starts; the cell array has its full size a moment
    /// later, while the terrain, the objects and the units are still coming.
    /// The height grid is the last of those to appear - it belongs to the path
    /// manager, which is built once the terrain is in - so it is what the test
    /// waits for. Everything the checks below look at is there by then.
    private static bool MissionReady()
    {
        GameLink.MapSnapshot map;
        return GameLink.ReadMap(out map) == null && map != null
               && map.Width == MissionWidth && map.Height == MissionWidth
               && map.Heights != null;
    }

    /// Waits for a condition, giving up after `seconds`. Returns how long it
    /// took, or -1.
    private static double Wait(Func<bool> until, int seconds)
    {
        var clock = Stopwatch.StartNew();
        while (clock.Elapsed.TotalSeconds < seconds)
        {
            if (until()) return clock.Elapsed.TotalSeconds;
            Thread.Sleep(250);
        }
        return -1;
    }

    public static int Run()
    {
        string here = AppDomain.CurrentDomain.BaseDirectory;
        string exe = GamePath.Exe;
        Say("Soldiers of Anarchy - the checks that need the game");
        Say(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
        Say("");

        // Run it in a window. A test that takes the whole screen for a minute
        // and a half is a test nobody runs twice.
        bool wasWindowed = LauncherWindow.GameIsWindowed(exe);
        if (!wasWindowed)
        {
            string trouble = LauncherWindow.SetGameWindowed(exe, true);
            Say(trouble == null ? "  put the game into a window for the test"
                                : "  could not put the game into a window: " + trouble);
        }

        Process game = GameLink.FindGame();
        bool ours = false;
        if (game == null)
        {
            if (!File.Exists(exe))
            {
                Say("  FAIL   " + exe + " is not there");
                return Finish(here, 1);
            }
            game = Process.Start(new ProcessStartInfo(exe)
            {
                WorkingDirectory = Path.GetDirectoryName(exe),
                UseShellExecute = false,
            });
            ours = true;
            Say("  started " + exe);
        }
        else
        {
            Say("  using the game already running, pid " + game.Id);
        }

        try
        {
            double took = Wait(() => GameLink.Ready(), WaitForMenu);
            Check("the game reaches its menu", took >= 0,
                  took >= 0 ? string.Format("after {0:N0} s", took)
                            : "not within " + WaitForMenu + " s");
            if (took < 0) return Finish(here, 1);

            uint returned;
            string failed = GameLink.LoadMission(Mission, out returned);
            Check("the mission is asked for", failed == null, failed);
            if (failed != null) return Finish(here, 1);

            took = Wait(MissionReady, WaitForMission);
            Check("the mission loads", took >= 0,
                  took >= 0 ? string.Format("after {0:N0} s", took)
                            : "not within " + WaitForMission + " s");
            if (took < 0) return Finish(here, 1);

            if (took >= 0)
            {
                GameLink.MapSnapshot map;
                failed = GameLink.ReadMap(out map);
                Check("the map reads", failed == null && map != null, failed);
                if (map != null)
                {
                    Check("the map is the one that was asked for",
                          map.Width == MissionWidth && map.Height == MissionWidth,
                          map.Width + " x " + map.Height + " world units");
                    Check("the height grid lines up", map.Heights != null,
                          map.Heights != null
                              ? map.HeightWidth + " x " + map.HeightHeight + " cells"
                              : "no heights");

                    // The units are placed after the terrain, so give the
                    // loading a moment to finish putting them down.
                    Thread.Sleep(2000);
                    List<GameLink.Unit> units = GameLink.FindUnits(map.Width, map.Height);
                    Check("units are found in the objects", units.Count > 0,
                          units.Count + " units");
                }

                failed = GameLink.RunMissionCheat("immortalone", out returned);
                Check("a mission cheat is accepted",
                      failed == null && (returned & 0xFF) != 0,
                      failed ?? ("the game returned " + (returned & 0xFF)));

                failed = GameLink.QuickSave(out returned);
                Check("quick save", failed == null, failed);
                Thread.Sleep(750);
                failed = GameLink.QuickLoad(out returned);
                Check("quick load", failed == null, failed);
                Thread.Sleep(750);
                Check("the mission is still there after loading it back",
                      GameLink.InMission(), "");
            }

            // The base screen is the one thing here with no way in from
            // outside. Loading Missions\Bunker_Light.Mis gives its world - the
            // map reads 400 across - but not the screen, and the pointer the
            // base cheats need stays null. So they are covered only when the
            // game is already sitting in the bunker.
            if (GameLink.AtBase())
            {
                failed = GameLink.RunCheat(GameLink.CheatGetSetting, "(0)", out returned);
                Check("a base cheat with an argument is accepted",
                      failed == null && returned != 0,
                      failed ?? ("the game returned " + returned));
            }
            else
            {
                Say("  --     the base cheats - skipped, nothing here can reach the base");
                Say("         screen; start the test with the game already in the bunker");
                Say("         and it covers them too");
            }
        }
        finally
        {
            if (ours && game != null && !game.HasExited)
            {
                // The game is left as it was found: started here, closed here.
                try
                {
                    game.CloseMainWindow();
                    if (!game.WaitForExit(10000)) game.Kill();
                    Say("  closed the game");
                }
                catch (Exception ex) { Say("  could not close the game: " + ex.Message); }
            }
            if (!wasWindowed)
            {
                LauncherWindow.SetGameWindowed(exe, false);
                Say("  put the window mode back to full screen");
            }
        }
        return Finish(here, _failed == 0 ? 0 : 1);
    }

    private static int Finish(string here, int code)
    {
        Say("");
        Say(_failed == 0 ? "everything the launcher does to the running game still works."
                         : _failed + " checks failed.");
        string path = Path.Combine(here, "selftest.txt");
        try { File.WriteAllText(path, Report.ToString()); }
        catch (Exception) { }
        if (!_console)
        {
            try
            {
                System.Windows.MessageBox.Show(Report.ToString(),
                    _failed == 0 ? "Self test passed" : "Self test failed");
            }
            catch (Exception) { }
        }
        return code;
    }
}
