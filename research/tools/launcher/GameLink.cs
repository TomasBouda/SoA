// Talking to the running game: the base cheats, called inside its process.
//
// The keyboard is no way in - the key that opens the game's input line goes
// through DirectInput, so the game would have to be focused, and the cheats
// only work on the base screen anyway. So the call is made directly.
//
// The sequence is copied from the game itself. Its own developer cheats call
// the dispatcher with the literal string "(92)" and the number 0xC, so the same
// thing with our own number and text is enough:
//
//     sub esp,0x10 / mov ecx,esp / push flag / push text / call 0x405D80
//     push number / mov ecx,[0x8759D4] / call 0x52F4A0 / ret 4
//
// tsString is built by the game's own constructor, so it is the game's object
// and its destructor disposes of it properly. The global at 0x8759D4 is null
// until the base screen is running - while it is null nothing is called,
// because the game would crash.
//
// The addresses are valid for soa.exe 1.1.2.178; ASLR is off, so they hold.
//
// Both the catalog and the console window go through here.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;

internal static class GameLink
{
    private const uint DISPATCHER = 0x0052F4A0;
    private const uint CTOR_TSSTRING = 0x00405D80;
    private const uint THIS_GLOBAL = 0x008759D4;

    public const int CheatQuit = 0;
    public const int CheatSoldier = 1;
    public const int CheatTrader = 2;
    public const int CheatGetSetting = 3;
    public const int CheatEquipment = 4;
    public const int CheatVehicle = 5;
    public const int CheatMission = 6;
    public const int CheatAllVehicles = 14;

    public struct Cheat
    {
        public int Number;
        public bool TakesArgument;
        public string What;
    }

    /// The base cheats by the name typed into the game's own input line, with
    /// the number the dispatcher takes, whether they expect an argument in
    /// brackets, and what they do. The developer names (ronny, enrico, ...)
    /// are indexes 7 to 13; what they do is not known, so they are not offered.
    public static readonly Dictionary<string, Cheat> Cheats =
        new Dictionary<string, Cheat>(StringComparer.OrdinalIgnoreCase)
    {
        { "soldierspawn", new Cheat { Number = CheatSoldier,
              What = "a new character joins the party" } },
        { "showtrader", new Cheat { Number = CheatTrader,
              What = "a trader with all the gear and vehicles" } },
        { "allvehicles", new Cheat { Number = CheatAllVehicles,
              What = "one vehicle of every kind" } },
        { "equipment", new Cheat { Number = CheatEquipment, TakesArgument = true,
              What = "creates the item with that number - the catalog lists them" } },
        { "vehicle", new Cheat { Number = CheatVehicle, TakesArgument = true,
              What = "creates the vehicle with that number" } },
        { "mission", new Cheat { Number = CheatMission, TakesArgument = true,
              What = "picks which mission Start mission will run" } },
        { "getsetting", new Cheat { Number = CheatGetSetting, TakesArgument = true,
              What = "reads a setting and writes it to the log" } },
        { "quitter", new Cheat { Number = CheatQuit,
              What = "quits the game" } },
    };

    // The mission cheats - immortalone, endlessmunition and the rest - have a
    // table of their own at 0x85CF10 (13 records of 0x6C bytes: the name, the
    // number at +0x64, the argument count at +0x68) and a handler of their own,
    // 0x5ECA70. It is a thiscall taking the typed line as a tsString by value
    // and matching the name itself, so the line goes in as it was typed:
    //
    //     sub esp,0x10 / mov ecx,esp / push flag / push text / call 0x405D80
    //     mov ecx,<mission> / call 0x5ECA70 / ret 4
    //
    // It ends with `ret 0x10`, so it disposes of the string itself - unlike the
    // base dispatcher, nothing has to be pushed afterwards.
    //
    // The base cheats have their object in a global at 0x8759D4; this one runs
    // on the mission object, and no global points at it. So the object is found
    // the other way round, by the vtables its constructor writes (0x5E7B70):
    // the mission inherits twice, so it carries 0x7D0568 at its start and
    // 0x7D0564 at +8. Both are looked for in the game's own heap. Outside a
    // mission the object does not exist and nothing is sent.
    // Quick save and quick load are methods of the mission object as well, so
    // the same door opens them. The message handler at 0x5E9910 dispatches
    // 0x424 to one and 0x425 to the other (0x5EA11A and 0x5EA138), both
    // thiscall and neither taking anything - which makes a mission repeatable:
    // save at a known spot and load it back as often as a test needs.
    // Quick load builds the path of QuickSave.sav and hands it to 0x5F2C10
    // (at 0x5F2934), another method of the mission object taking a tsString by
    // value. Give that one a different path and it loads a different save -
    // the full path, the way quick load assembles it: the save directory, a
    // backslash, the file name.
    private const uint LOAD_SAVE = 0x005F2C10;

    private const uint QUICK_SAVE = 0x005F23D0;
    private const uint QUICK_LOAD = 0x005F26F0;

    // Loading a mission by name. The game does this to itself when a host
    // starts one: packet 18, START_MISSION, whose handler at 0x4E83E8 reads a
    // name out of the packet, builds a tsString and calls 0x60BC60 on the
    // object in the global 0x875AEC. That function ends in ret 0x10, so it
    // takes the string by value like every other one here.
    //
    // The name is the path of a .mis, written the way the exe writes it -
    // Missions\Campaign\Mission_3\Mission_3.mis, capital M and backslashes.
    // Forward slashes get as far as the log line and then fail to open
    // (0x80070003), which is how the shape was settled.
    //
    // This is the only caller in the exe, so single player reaches a mission
    // some other way and what this does outside a network game is not certain.
    // It is here to be tried, not relied on.
    // The network object, and the byte that says the game is one. The
    // interface reads it - 0x4460EC and 0x4462CD, both in the screen code -
    // and the packet that starts a mission sets it at 0x4E83F8. A mission
    // reached from outside comes up with the network interface: Escape opens
    // the wrong menu and the panel down the right stays empty. Whether this
    // byte is what decides that is exactly what needs trying, so it is
    // readable and writable from the console rather than guessed at.
    // The interface asks twice, and either answer is enough (0x4460E7):
    //
    //     [0x8739BC]+0x600 != 0                     -> a network game
    //     [0x875AA4] != 0 and its byte at +0x84 != 0 -> a network game
    //
    // The first reads 0 in a mission loaded from outside and changing it does
    // nothing, so the second is what is left. Both are read and written here,
    // because a guess about which one costs another run of the game.
    private const uint NETWORK_GLOBAL = 0x008739BC;
    private const uint NETWORK_FLAG_AT = 0x600;
    private const uint SESSION_GLOBAL = 0x00875AA4;
    private const uint SESSION_FLAG_AT = 0x84;

    // The loader announces the mission to the application with a 1:
    //
    //     0060BCAC  mov ecx, [0x875B1C]
    //     0060BCB2  push 1
    //     0060BCB4  call 0x6D9B60
    //
    // which passes it to 0x5FBF70, and that, when it is not zero, calls a
    // method of the loading state with a 2. The interface a mission comes up
    // with follows from that - which is why clearing either network flag did
    // nothing, and why a mission loaded from outside has a panel a single
    // player has never seen.
    //
    // The byte is poked to zero for the length of the call and put straight
    // back, so the exe on disk is untouched and hosting a network game still
    // works. Whether this is really what chooses the interface is a question
    // for the running game, so the console can turn it off again.
    private const uint LOADER_MODE_BYTE = 0x0060BCB3;

    /// Whether to ask for a mission the way single player does. Off, because
    /// it was tried and the interface came up the same either way - the poke
    /// is kept for the next attempt rather than left switched on, since a
    /// change that does not do what it says is worse than no change.
    /// campaignui(1) turns it on.
    public static bool LoadAsCampaign;

    private const uint LOADER_GLOBAL = 0x00875AEC;
    private const uint LOAD_MISSION = 0x0060BC60;

    /// The base is a mission like any other - the exe builds this name at
    /// 0x52DEB0 - so loading it is how to get to the bunker without clicking.
    public const string Bunker = @"Missions\Bunker_Light.Mis";

    /// The campaign, as the exe spells it (the strings around 0x846884).
    public static readonly string[] Missions =
    {
        @"Missions\Campaign\Mission_1\Mission_1.mis",
        @"Missions\Campaign\Mission_2\Mission_2.mis",
        @"Missions\Campaign\Mission_3\Mission_3.mis",
        @"Missions\Campaign\Mission_4\Mission_4.mis",
        @"Missions\Campaign\Mission_5a\Mission_5a.mis",
        @"Missions\Campaign\Mission_5b\Mission_5b.mis",
        @"Missions\Campaign\Mission_6a\Mission_6a.mis",
        @"Missions\Campaign\Mission_6b\Mission_6b.mis",
        @"Missions\Campaign\Mission_7\Mission_7.mis",
        @"Missions\Campaign\Mission_8a\Mission_8a.mis",
        @"Missions\Campaign\Mission_8b\Mission_8b.mis",
        @"Missions\Campaign\Mission_9a\Mission_9a.mis",
        @"Missions\Campaign\Mission_9b\Mission_9b.mis",
        @"Missions\Tutorial\Tutorial.mis",
    };

    private const uint MISSION_HANDLER = 0x005ECA70;
    private const uint MISSION_VTABLE = 0x007D0568;
    private const uint MISSION_VTABLE_2 = 0x007D0564;
    private const uint MISSION_VTABLE_2_AT = 0x8;

    // Two vtables in the right places are already unlikely to turn up by
    // chance; on top of that the members the game reads on its way to the
    // cheats - 0x5E9968 and 0x5E9CCC - all have to be pointers into something
    // readable.
    private static readonly uint[] MISSION_MEMBERS = { 0x250, 0x260, 0x270 };
    private const uint MISSION_END = 0x274;

    /// The cheats the game takes during a mission, in the order of its table,
    /// with whether they expect an argument in brackets and what they do.
    public static readonly Dictionary<string, Cheat> MissionCheats =
        new Dictionary<string, Cheat>(StringComparer.OrdinalIgnoreCase)
    {
        { "quitter", new Cheat { What = "ends the mission" } },
        { "hittingandhealing", new Cheat { What = "hits and healing" } },
        { "endlessmunition", new Cheat { What = "ammunition never runs out" } },
        { "immortalone", new Cheat { What = "the party cannot be hurt" } },
        { "winmission", new Cheat { What = "the mission is won on the spot" } },
        { "speedhack", new Cheat { What = "runs the game faster" } },
        { "kick", new Cheat { TakesArgument = true, What = "multiplayer - kicks a player" } },
        { "kickn", new Cheat { TakesArgument = true,
              What = "multiplayer - kicks a player by number" } },
        { "playerlist", new Cheat { What = "multiplayer - lists the players" } },
        { "nick", new Cheat { TakesArgument = true,
              What = "multiplayer - changes the nickname" } },
        { "sfxon", new Cheat { What = "turns the sound effects on" } },
        { "sfxoff", new Cheat { What = "turns the sound effects off" } },
        { "sfxdebug", new Cheat { What = "in the table, mentioned nowhere else" } },
    };

    private const uint PROCESS_ALL = 0x1F0FFF;
    private const uint MEM_COMMIT_RESERVE = 0x3000;
    private const uint MEM_RELEASE = 0x8000;
    private const uint PAGE_EXECUTE_READWRITE = 0x40;

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(uint access, bool inherit, int pid);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr VirtualAllocEx(IntPtr process, IntPtr address, uint size,
                                                uint type, uint protection);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool VirtualFreeEx(IntPtr process, IntPtr address, uint size, uint type);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool WriteProcessMemory(IntPtr process, IntPtr address, byte[] data,
                                                  uint length, out UIntPtr written);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] data,
                                                 uint length, out UIntPtr read);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr CreateRemoteThread(IntPtr process, IntPtr attributes, uint stack,
                                                    IntPtr start, IntPtr parameter, uint flags,
                                                    IntPtr id);

    [DllImport("kernel32.dll")]
    private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);

    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);

    [DllImport("kernel32.dll")]
    private static extern bool GetExitCodeThread(IntPtr thread, out uint code);

    private const uint MEM_COMMIT = 0x1000;
    private const uint MEM_PRIVATE = 0x20000;
    private const uint PAGE_GUARD = 0x100;
    private const uint PAGE_NOACCESS = 0x01;
    private const uint PAGE_READONLY = 0x02;
    private const uint PAGE_READWRITE = 0x04;
    private const uint PAGE_WRITECOPY = 0x08;
    private const uint PAGE_EXECUTE_READ = 0x20;

    [StructLayout(LayoutKind.Sequential)]
    private struct MEMORY_BASIC_INFORMATION
    {
        public IntPtr BaseAddress, AllocationBase;
        public uint AllocationProtect;
        public IntPtr RegionSize;
        public uint State, Protect, Type;
    }

    [DllImport("kernel32.dll")]
    private static extern IntPtr VirtualQueryEx(IntPtr process, IntPtr address,
                                                out MEMORY_BASIC_INFORMATION info, uint length);

    /// Whether the base screen is up - the pointer the base cheats need.
    public static bool AtBase()
    {
        return ReadGlobal(THIS_GLOBAL) != 0;
    }

    /// Whether the game has got as far as its menu - the part that loads
    /// missions is built by then, and that is what LoadMission needs.
    public static bool Ready()
    {
        return Plausible(ReadGlobal(LOADER_GLOBAL));
    }

    /// Whether a mission is running - the world the map is read from.
    public static bool InMission()
    {
        return ReadGlobal(WORLD_GLOBAL) != 0;
    }

    private static uint ReadGlobal(uint address)
    {
        Process game = FindGame();
        if (game == null) return 0;
        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero) return 0;
        try { return ReadDword(process, address); }
        finally { CloseHandle(process); }
    }

    public static Process FindGame()
    {
        return Process.GetProcessesByName("soa").FirstOrDefault();
    }

    /// The raw bytes of one object in the running game, or null if they could
    /// not all be read. Used by the inspector window; nothing is written.
    public static byte[] ReadObject(uint address, int size)
    {
        Process game = FindGame();
        if (game == null) return null;
        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero) return null;
        try
        {
            var raw = new byte[size];
            UIntPtr read;
            if (!ReadProcessMemory(process, (IntPtr)address, raw, (uint)size, out read)
                || read.ToUInt32() != (uint)size)
                return null;
            return raw;
        }
        finally
        {
            CloseHandle(process);
        }
    }

    /// The offsets of a unit object we have names for, so the inspector can
    /// label them instead of leaving the reader to count. Everything else is
    /// shown as it is; that is the point of looking.
    public static readonly Dictionary<uint, string> UnitFields =
        new Dictionary<uint, string>
        {
            { 0x00, "class (vtable)" },
            { UNIT_X_AT, "x on the map" },
            { UNIT_Y_AT, "y on the map" },
            { UNIT_STAMP_AT, "stamp (party and footprint)" },
        };

    private static void Dword(List<byte> output, uint value)
    {
        output.AddRange(BitConverter.GetBytes(value));
    }

    private static byte[] Shellcode(uint textAddress, uint flagAddress, int cheatNumber)
    {
        var b = new List<byte>();
        b.AddRange(new byte[] { 0x83, 0xEC, 0x10 });          // sub esp, 0x10
        b.AddRange(new byte[] { 0x8B, 0xCC });                // mov ecx, esp
        b.Add(0x68); Dword(b, flagAddress);                   // push flag
        b.Add(0x68); Dword(b, textAddress);                   // push text
        b.Add(0xB8); Dword(b, CTOR_TSSTRING);                 // mov eax, ctor
        b.AddRange(new byte[] { 0xFF, 0xD0 });                // call eax
        b.Add(0x68); Dword(b, (uint)cheatNumber);             // push cheat number
        b.AddRange(new byte[] { 0x8B, 0x0D }); Dword(b, THIS_GLOBAL);   // mov ecx, [this]
        b.Add(0xB8); Dword(b, DISPATCHER);                    // mov eax, dispatcher
        b.AddRange(new byte[] { 0xFF, 0xD0 });                // call eax
        b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });          // ret 4
        return b.ToArray();
    }

    private static byte[] MissionShellcode(uint textAddress, uint flagAddress, uint mission)
    {
        return MissionShellcode(textAddress, flagAddress, mission, MISSION_HANDLER);
    }

    private static byte[] MissionShellcode(uint textAddress, uint flagAddress, uint mission,
                                           uint method)
    {
        var b = new List<byte>();
        b.AddRange(new byte[] { 0x83, 0xEC, 0x10 });          // sub esp, 0x10
        b.AddRange(new byte[] { 0x8B, 0xCC });                // mov ecx, esp
        b.Add(0x68); Dword(b, flagAddress);                   // push flag
        b.Add(0x68); Dword(b, textAddress);                   // push text
        b.Add(0xB8); Dword(b, CTOR_TSSTRING);                 // mov eax, ctor
        b.AddRange(new byte[] { 0xFF, 0xD0 });                // call eax
        b.Add(0xB9); Dword(b, mission);                       // mov ecx, the mission
        b.Add(0xB8); Dword(b, method);                        // mov eax, the method
        b.AddRange(new byte[] { 0xFF, 0xD0 });                // call eax - it ends in ret 0x10,
                                                              // so it drops the string itself
        b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });          // ret 4
        return b.ToArray();
    }

    private static uint ReadDword(IntPtr process, uint address)
    {
        var four = new byte[4];
        UIntPtr read;
        if (!ReadProcessMemory(process, (IntPtr)address, four, 4, out read)) return 0;
        return BitConverter.ToUInt32(four, 0);
    }

    private static bool Plausible(uint pointer)
    {
        return pointer >= 0x10000 && pointer < 0x80000000;
    }

    /// Whether the address still holds a mission: both vtables first, then the
    /// members the game reads on its way to the cheats. Each of them has to
    /// point at memory that can be read.
    private static bool LooksLikeMission(IntPtr process, uint address)
    {
        var head = new byte[MISSION_END];
        UIntPtr read;
        if (!ReadProcessMemory(process, (IntPtr)address, head, MISSION_END, out read)
            || read.ToUInt32() != MISSION_END)
            return false;
        if (BitConverter.ToUInt32(head, 0) != MISSION_VTABLE) return false;
        if (BitConverter.ToUInt32(head, (int)MISSION_VTABLE_2_AT) != MISSION_VTABLE_2)
            return false;
        var one = new byte[1];
        foreach (uint member in MISSION_MEMBERS)
        {
            uint pointer = BitConverter.ToUInt32(head, (int)member);
            if (!Plausible(pointer)) return false;
            if (!ReadProcessMemory(process, (IntPtr)pointer, one, 1, out read)
                || read.ToUInt32() != 1)
                return false;
        }
        return true;
    }

    private static bool Readable(uint protection)
    {
        if ((protection & (PAGE_GUARD | PAGE_NOACCESS)) != 0) return false;
        return (protection & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY
                              | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE)) != 0;
    }

    // The address found last time. A mission lives for a while, so the next
    // command only checks it instead of walking the heap again.
    private static uint _mission;

    /// The address of the running mission, or zero when there is none. Walks the
    /// memory the game allocated for itself and looks for the vtable; the image
    /// of the game is left out, so the mentions of the address in the code do
    /// not come up.
    public static uint FindMission(IntPtr process)
    {
        if (_mission != 0 && LooksLikeMission(process, _mission)) return _mission;
        _mission = 0;

        var buffer = new byte[0x100000];
        uint size = (uint)Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION));
        ulong at = 0x10000;
        MEMORY_BASIC_INFORMATION info;
        while (at < 0x7FFF0000
               && VirtualQueryEx(process, (IntPtr)(long)at, out info, size) != IntPtr.Zero)
        {
            ulong region = (ulong)info.RegionSize.ToInt64();
            if (region == 0) break;
            ulong start = (ulong)info.BaseAddress.ToInt64();
            if (info.State == MEM_COMMIT && info.Type == MEM_PRIVATE && Readable(info.Protect))
            {
                for (ulong page = start; page < start + region; page += (ulong)buffer.Length)
                {
                    uint length = (uint)Math.Min((ulong)buffer.Length, start + region - page);
                    UIntPtr read;
                    if (!ReadProcessMemory(process, (IntPtr)(long)page, buffer, length, out read))
                        continue;
                    int got = (int)read.ToUInt32();
                    for (int i = 0; i + 4 <= got; i += 4)
                    {
                        if (BitConverter.ToUInt32(buffer, i) != MISSION_VTABLE) continue;
                        uint candidate = (uint)(page + (ulong)i);
                        if (LooksLikeMission(process, candidate))
                        {
                            _mission = candidate;
                            return candidate;
                        }
                    }
                }
            }
            at = start + region;
        }
        return 0;
    }

    /// Writes the text, the shellcode built around it and a thread that runs it.
    /// Returns null on success; `returned` is what the called function gave back.
    private static string Inject(IntPtr process, string text,
                                 Func<uint, uint, byte[]> build, out uint returned)
    {
        byte[] raw = System.Text.Encoding.ASCII.GetBytes((text ?? "") + "\0");
        return Inject(process, raw, build, out returned);
    }

    /// The same with bytes rather than text, for a call whose argument is not
    /// a string. The data goes where the text would, at the first address the
    /// builder is given; it has 64 bytes before the flag byte.
    private static string Inject(IntPtr process, byte[] raw,
                                 Func<uint, uint, byte[]> build, out uint returned)
    {
        returned = 0;
        IntPtr memory = VirtualAllocEx(process, IntPtr.Zero, 0x1000, MEM_COMMIT_RESERVE,
                                       PAGE_EXECUTE_READWRITE);
        if (memory == IntPtr.Zero)
            return "Could not allocate memory in the game process.";
        try
        {
            uint baseAddress = (uint)memory.ToInt64();
            uint textAddress = baseAddress;
            uint flagAddress = baseAddress + 0x40;
            uint codeAddress = baseAddress + 0x80;

            byte[] code = build(textAddress, flagAddress);

            UIntPtr written;
            WriteProcessMemory(process, (IntPtr)textAddress, raw, (uint)raw.Length, out written);
            WriteProcessMemory(process, (IntPtr)flagAddress, new byte[] { 0 }, 1, out written);
            WriteProcessMemory(process, (IntPtr)codeAddress, code, (uint)code.Length, out written);

            IntPtr thread = CreateRemoteThread(process, IntPtr.Zero, 0, (IntPtr)codeAddress,
                                               IntPtr.Zero, 0, IntPtr.Zero);
            if (thread == IntPtr.Zero)
                return "Cannot create a thread in the game process (error "
                       + Marshal.GetLastWin32Error() + ").";
            WaitForSingleObject(thread, 5000);
            GetExitCodeThread(thread, out returned);
            CloseHandle(thread);
            return null;
        }
        finally
        {
            VirtualFreeEx(process, memory, 0, MEM_RELEASE);
        }
    }

    /// Runs one base cheat in the game. `text` is what the game would see after
    /// the cheat name, brackets included. Returns null on success, otherwise a
    /// message; `returned` is what the dispatcher gave back, zero meaning it
    /// refused.
    public static string RunCheat(int cheatNumber, string text, out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            // Outside the base screen the pointer is null and the call would
            // take the game down.
            if (ReadDword(process, THIS_GLOBAL) == 0)
                return "You are not in the base - switch to it and try again.";
            return Inject(process, text, (t, f) => Shellcode(t, f, cheatNumber), out returned);
        }
        finally
        {
            CloseHandle(process);
        }
    }

    /// The first object in the game's memory whose first word is `vtable`.
    /// Returns zero when there is none.
    private static uint FindByVTable(IntPtr process, uint vtable)
    {
        var buffer = new byte[0x100000];
        uint size = (uint)Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION));
        ulong at = 0x10000;
        MEMORY_BASIC_INFORMATION info;
        while (at < 0x7FFF0000
               && VirtualQueryEx(process, (IntPtr)(long)at, out info, size) != IntPtr.Zero)
        {
            ulong region = (ulong)info.RegionSize.ToInt64();
            if (region == 0) break;
            ulong start = (ulong)info.BaseAddress.ToInt64();
            if (info.State == MEM_COMMIT && info.Type == MEM_PRIVATE && Readable(info.Protect))
            {
                for (ulong page = start; page < start + region; page += (ulong)buffer.Length)
                {
                    uint length = (uint)Math.Min((ulong)buffer.Length, start + region - page);
                    UIntPtr read;
                    if (!ReadProcessMemory(process, (IntPtr)(long)page, buffer, length, out read))
                        continue;
                    int got = (int)read.ToUInt32();
                    for (int i = 0; i + 4 <= got; i += 4)
                        if (BitConverter.ToUInt32(buffer, i) == vtable)
                            return (uint)(page + (ulong)i);
                }
            }
            at = start + region;
        }
        return 0;
    }

    /// Asks the game to load a mission by the path of its .mis file. Returns
    /// null on success; what the game then does is its own business.
    public static string LoadMission(string name, out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            uint loader = ReadDword(process, LOADER_GLOBAL);
            if (!Plausible(loader))
                return "The part of the game that loads missions is not there yet.";

            var one = new byte[1];
            UIntPtr got;
            bool poked = false;
            if (LoadAsCampaign
                && ReadProcessMemory(process, (IntPtr)LOADER_MODE_BYTE, one, 1, out got)
                && got.ToUInt32() == 1 && one[0] == 1)
            {
                poked = WriteProcessMemory(process, (IntPtr)LOADER_MODE_BYTE, new byte[] { 0 },
                                           1, out got);
            }
            try
            {
                return Inject(process, name,
                              (t, f) => LoadShellcode(t, f, loader), out returned);
            }
            finally
            {
                if (poked)
                    WriteProcessMemory(process, (IntPtr)LOADER_MODE_BYTE, new byte[] { 1 },
                                       1, out got);
            }
        }
        finally
        {
            CloseHandle(process);
        }
    }

    private static byte[] LoadShellcode(uint textAddress, uint flagAddress, uint loader)
    {
        var b = new List<byte>();
        b.AddRange(new byte[] { 0x83, 0xEC, 0x10 });          // sub esp, 0x10
        b.AddRange(new byte[] { 0x8B, 0xCC });                // mov ecx, esp
        b.Add(0x68); Dword(b, flagAddress);                   // push flag
        b.Add(0x68); Dword(b, textAddress);                   // push text
        b.Add(0xB8); Dword(b, CTOR_TSSTRING);                 // mov eax, ctor
        b.AddRange(new byte[] { 0xFF, 0xD0 });                // call eax
        b.Add(0xB9); Dword(b, loader);                        // mov ecx, the loader
        b.Add(0xB8); Dword(b, LOAD_MISSION);                  // mov eax, the method
        b.AddRange(new byte[] { 0xFF, 0xD0 });                // call eax - ret 0x10
        b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });          // ret 4
        return b.ToArray();
    }

    /// Calls a method of the mission object that takes nothing - quick save and
    /// quick load. Returns null on success.
    ///
    /// This runs on a thread of its own inside the game while the game's own
    /// thread carries on, which is fine for the cheats but is asking more of
    /// saving and loading. The game does it from its message loop; there is no
    /// way to ask it politely from outside without finding that queue.
    public static string RunMissionCall(uint method, out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            uint mission = FindMission(process);
            if (mission == 0)
                return "No mission is running - this only works inside one.";
            var b = new List<byte>();
            b.Add(0xB9); Dword(b, mission);                   // mov ecx, the mission
            b.Add(0xB8); Dword(b, method);                    // mov eax, the method
            b.AddRange(new byte[] { 0xFF, 0xD0 });            // call eax
            b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });      // ret 4
            return RunCode(process, b.ToArray(), out returned);
        }
        finally
        {
            CloseHandle(process);
        }
    }

    /// Loads a saved game. `path` is the full path of the .sav, which is what
    /// the game builds for itself. Needs a mission running, like quick load -
    /// the loader is a method of the mission object.
    public static string LoadSave(string path, out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            uint mission = FindMission(process);
            if (mission == 0)
                return "No mission is running - loading a save needs one, the same "
                     + "way quick load does.";
            return Inject(process, path,
                          (t, f) => MissionShellcode(t, f, mission, LOAD_SAVE), out returned);
        }
        finally
        {
            CloseHandle(process);
        }
    }

    /// Reads or writes the two bytes the interface asks about. `set` is -1 to
    /// only read. `flags` comes back as the two values, -1 where the object
    /// behind one is not there.
    public static string NetworkFlags(int set, out int[] flags)
    {
        flags = new[] { -1, -1 };
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            uint[] holders = { ReadDword(process, NETWORK_GLOBAL),
                               ReadDword(process, SESSION_GLOBAL) };
            uint[] offsets = { NETWORK_FLAG_AT, SESSION_FLAG_AT };
            var one = new byte[1];
            UIntPtr got;
            for (int i = 0; i < 2; i++)
            {
                if (!Plausible(holders[i])) continue;
                if (set >= 0)
                {
                    one[0] = (byte)(set != 0 ? 1 : 0);
                    WriteProcessMemory(process, (IntPtr)(holders[i] + offsets[i]), one, 1,
                                       out got);
                }
                if (ReadProcessMemory(process, (IntPtr)(holders[i] + offsets[i]), one, 1, out got)
                    && got.ToUInt32() == 1)
                    flags[i] = one[0];
            }
            return null;
        }
        finally
        {
            CloseHandle(process);
        }
    }

    // ------------------------------------------------------- the height map

    // The Landscape command group has two that do real work rather than flip a
    // flag, and SaveHeightMap is the easy one. Its case body (0x6D7F74) is:
    //
    //     fild [ecx+0x34] / push        ; maxHeight, as a float
    //     fild [ecx+0x1C] / push        ; minHeight, as a float
    //     mov  ecx, [0x880F98]          ; the world
    //     push eax                      ; the file name
    //     call 0x6878A0
    //
    // so it is a thiscall on the world taking (char *name, float min, float
    // max) and ending in `ret 0xC`, which returns an int that is negative when
    // it failed. The name is a plain char pointer rather than a tsString, so
    // nothing has to be constructed for it.
    //
    // What it does: stops the renderer, builds a 32-bit off-screen surface of
    // [world+0x18] by [world+0x1C], writes each height scaled between the two
    // bounds into all three channels - so the picture comes out grey - hands
    // the surface to the application's picture writer, and starts the renderer
    // again. The exe carries libpng, so the format follows the name.
    //
    // LoadHeightMap is not this easy: its argument is an object built out of
    // the parsed parameters, and the editor's Imp. Height Data is the door to
    // use for that until it is worked out.
    private const uint SAVE_HEIGHT_MAP = 0x006878A0;

    /// Writes the terrain of the running mission to `path` as a grey picture,
    /// scaling the heights between the two bounds. Null means it worked.
    public static string SaveHeightMap(string path, float minHeight, float maxHeight,
                                       out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            // Outside a mission the world is null and the call would take the
            // game down.
            if (ReadDword(process, WORLD_GLOBAL) == 0)
                return "No mission is running - there is no terrain to write.";

            string failed = Inject(process, path,
                (t, f) => HeightMapShellcode(t, minHeight, maxHeight), out returned);
            if (failed != null) return failed;

            // The game reports failure as a negative int, the way DirectX does.
            if ((returned & 0x80000000) != 0)
                return "The game refused to write it (0x" + returned.ToString("X8")
                     + "). tracefile.log says why.";
            return null;
        }
        finally
        {
            CloseHandle(process);
        }
    }

    private static byte[] HeightMapShellcode(uint nameAddress, float minHeight, float maxHeight)
    {
        var b = new List<byte>();
        b.Add(0x68); Dword(b, BitConverter.ToUInt32(BitConverter.GetBytes(maxHeight), 0));
        b.Add(0x68); Dword(b, BitConverter.ToUInt32(BitConverter.GetBytes(minHeight), 0));
        b.Add(0x68); Dword(b, nameAddress);                            // push name
        b.AddRange(new byte[] { 0x8B, 0x0D }); Dword(b, WORLD_GLOBAL); // mov ecx, [world]
        b.Add(0xB8); Dword(b, SAVE_HEIGHT_MAP);                        // mov eax, SaveHeightMap
        b.AddRange(new byte[] { 0xFF, 0xD0 });                         // call eax
        b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });                   // ret 4
        return b.ToArray();
    }

    // --------------------------------------------------------- the air strike

    // The air strike is a shipped feature the campaign never shows: a plane
    // with bombs in the hangar, a list of target points, and one launch
    // (0x6B9030) that pulls the plane out of the bunker's unit list, sets it on
    // the first point and hands it the order. The game's own button only
    // appears in a mission whose designer placed target markers, which none of
    // ours did, so the launcher calls the launch itself with a point of its
    // own - which is exactly what the developers' AirStrike console command
    // did, with two fixed points. The recipe, read off that command (0x6D48AD)
    // and verified live:
    //
    //     vector<xyz> points;                 ; 16 bytes: alloc, first, last, end
    //     AirStrike strike;                   ; 4 bytes, the ctor writes a vtable
    //     points.insert(points.end(), 1, p);  ; 0x6AF670, thiscall, per point
    //     strike.Launch(&points);             ; 0x6B9030, thiscall, ret 4
    //     free(points.first);                 ; 0x756600
    //
    // The launch answers 0 when a plane went, 1 when nothing in the bunker was
    // an aeroplane with ammunition, and a negative HRESULT otherwise. It is
    // safe to call with an empty hangar. The bunker is the global 0x8759C0 and
    // a mission has to be running, or the plane has nowhere to go.
    private const uint BUNKER_GLOBAL = 0x008759C0;
    private const uint STRIKE_CTOR = 0x006B8D20;
    private const uint POINTS_INSERT = 0x006AF670;
    private const uint STRIKE_LAUNCH = 0x006B9030;
    private const uint GAME_FREE = 0x00756600;

    /// Sends a plane from the hangar to bomb the point, in world units. Null
    /// means it went; otherwise the reason it did not.
    public static string AirStrike(float x, float y, out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            if (ReadDword(process, BUNKER_GLOBAL) == 0)
                return "There is no bunker yet - the game has not got that far.";
            if (ReadDword(process, WORLD_GLOBAL) == 0)
                return "No mission is running - the plane would have nowhere to go.";

            // The point goes where the text would; the strike object sits
            // right behind it, both inside the 64 bytes the builder may use.
            var raw = new byte[16];
            Buffer.BlockCopy(BitConverter.GetBytes(x), 0, raw, 0, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(y), 0, raw, 4, 4);
            string failed = Inject(process, raw, (t, f) => AirStrikeShellcode(t, t + 12), out returned);
            if (failed != null) return failed;
            if (returned == 1)
                return "No aeroplane with bombs in the hangar - the game found nothing to send.";
            if ((returned & 0x80000000) != 0)
                return "The game refused (0x" + returned.ToString("X8") + ") - tracefile.log says why.";
            return null;
        }
        finally
        {
            CloseHandle(process);
        }
    }

    private static byte[] AirStrikeShellcode(uint pointAddress, uint strikeAddress)
    {
        var b = new List<byte>();
        b.AddRange(new byte[] { 0x83, 0xEC, 0x10 });                   // sub esp, 0x10
        b.AddRange(new byte[] { 0x31, 0xC0 });                         // xor eax, eax
        b.AddRange(new byte[] { 0x89, 0x04, 0x24 });                   // mov [esp], eax
        b.AddRange(new byte[] { 0x89, 0x44, 0x24, 0x04 });             // mov [esp+4], eax
        b.AddRange(new byte[] { 0x89, 0x44, 0x24, 0x08 });             // mov [esp+8], eax
        b.AddRange(new byte[] { 0x89, 0x44, 0x24, 0x0C });             // mov [esp+0xC], eax
        b.Add(0xB9); Dword(b, strikeAddress);                          // mov ecx, strike
        b.Add(0xB8); Dword(b, STRIKE_CTOR);                            // mov eax, ctor
        b.AddRange(new byte[] { 0xFF, 0xD0 });                         // call eax
        b.AddRange(new byte[] { 0x8B, 0x44, 0x24, 0x08 });             // mov eax, [esp+8]  ; end()
        b.Add(0x68); Dword(b, pointAddress);                           // push &point
        b.AddRange(new byte[] { 0x6A, 0x01 });                         // push 1
        b.Add(0x50);                                                   // push eax
        b.AddRange(new byte[] { 0x8D, 0x4C, 0x24, 0x0C });             // lea ecx, [esp+0xC] ; the vector
        b.Add(0xB8); Dword(b, POINTS_INSERT);                          // mov eax, insert
        b.AddRange(new byte[] { 0xFF, 0xD0 });                         // call eax          ; ret 0xC
        b.AddRange(new byte[] { 0x8D, 0x04, 0x24 });                   // lea eax, [esp]
        b.Add(0x50);                                                   // push eax          ; &points
        b.Add(0xB9); Dword(b, strikeAddress);                          // mov ecx, strike
        b.Add(0xB8); Dword(b, STRIKE_LAUNCH);                          // mov eax, launch
        b.AddRange(new byte[] { 0xFF, 0xD0 });                         // call eax          ; ret 4
        b.AddRange(new byte[] { 0x89, 0x44, 0x24, 0x0C });             // mov [esp+0xC], eax ; the answer, in the end slot
        b.AddRange(new byte[] { 0xFF, 0x74, 0x24, 0x04 });             // push [esp+4]      ; first
        b.Add(0xB8); Dword(b, GAME_FREE);                              // mov eax, free
        b.AddRange(new byte[] { 0xFF, 0xD0 });                         // call eax
        b.AddRange(new byte[] { 0x83, 0xC4, 0x04 });                   // add esp, 4
        b.AddRange(new byte[] { 0x8B, 0x44, 0x24, 0x0C });             // mov eax, [esp+0xC]
        b.AddRange(new byte[] { 0x83, 0xC4, 0x10 });                   // add esp, 0x10
        b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });                   // ret 4
        return b.ToArray();
    }

    // -------------------------------------------------------- the screenshot

    // The game can photograph itself, and its own key for it is F12 - but that
    // key goes through the mission input table, so it does nothing on the menu
    // screens, which have input handling of their own. That is a pity exactly
    // when a picture is most wanted, since the menus are where a translation
    // shows first.
    //
    // The function behind it needs no help. 0x6031B0 takes no arguments and
    // finds the application in the global 0x875B1C itself: it counts up
    // shot%04d.png until it finds a name nothing answers to, asks the renderer
    // for the picture and hands it to the same writer SaveHeightMap uses. It
    // ends in a plain `ret`, so there is nothing to clean up either.
    //
    // Called from outside it works wherever the game is - menu, bunker,
    // mission - which is more than its own key manages.
    private const uint SCREENSHOT = 0x006031B0;
    private const uint APPLICATION_GLOBAL = 0x00875B1C;

    /// Photographs the game into shot0000.png and upwards, beside soa.exe.
    public static string Screenshot(out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            if (!Plausible(ReadDword(process, APPLICATION_GLOBAL)))
                return "The game has not finished starting.";
            var b = new List<byte>();
            b.Add(0xB8); Dword(b, SCREENSHOT);              // mov eax, the function
            b.AddRange(new byte[] { 0xFF, 0xD0 });          // call eax
            b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });    // ret 4
            byte[] code = b.ToArray();
            return Inject(process, "", (t, f) => code, out returned);
        }
        finally
        {
            CloseHandle(process);
        }
    }

    // ---------------------------------------------------------- the recorder

    // EventRecorder and Replay answer `no replay system available` when the
    // global at 0x874AE0 is null (0x6D4BC1). The same global is read from the
    // state switch in Y2KApp.cpp, so it is not obviously absent from the
    // release build - but nobody has looked at a running game to see.
    private const uint RECORDER_GLOBAL = 0x00874AE0;

    /// Whether the game built itself a replay system. Null while it is not
    /// running.
    public static bool? HasReplaySystem()
    {
        if (FindGame() == null) return null;
        return ReadGlobal(RECORDER_GLOBAL) != 0;
    }

    public static string QuickSave(out uint returned)
    {
        return RunMissionCall(QUICK_SAVE, out returned);
    }

    public static string QuickLoad(out uint returned)
    {
        return RunMissionCall(QUICK_LOAD, out returned);
    }

    /// Runs one mission cheat. `line` goes in the way the game's own input line
    /// would take it, name and brackets together - the handler does the matching
    /// itself. The value returned is 1 when it recognised the line.
    public static string RunMissionCheat(string line, out uint returned)
    {
        returned = 0;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            uint mission = FindMission(process);
            if (mission == 0)
                return "No mission is running - these cheats only work inside one.";
            return Inject(process, line, (t, f) => MissionShellcode(t, f, mission), out returned);
        }
        finally
        {
            CloseHandle(process);
        }
    }



    // ------------------------------------------------------ the debug overlays

    // Landscape.ShowPathMap, ShowVisMap and the rest are console commands, and
    // the console never opens - but what they do turned out to be small enough
    // to do from outside without touching the command tree at all.
    //
    // Every one of them builds a tiny object that is nothing but a vtable
    // (0x6D7D30 and the cases after it), hangs it on the renderer and turns the
    // drawing on:
    //
    //     push 4 / call operator new / mov [obj], <vtable>
    //     mov [renderer+0xB240], obj
    //     mov ecx, renderer / push 1 / call 0x663B80
    //
    // where the renderer is [[0x880F98]+0x48] and 0x663B80 writes the byte at
    // +0xB23C that says whether to draw. So the launcher writes the object
    // itself into a page of its own in the game and calls that one function.
    // The object stays where it is - the game only ever frees the one it made
    // itself, which it keeps at +0x3EC of the landscape - so ours is a few
    // bytes that live until the game closes.
    private const uint WORLD_GLOBAL = 0x00880F98;
    private const uint RENDERER_AT = 0x48;
    private const uint OVERLAY_AT = 0xB240;
    private const uint OVERLAY_SWITCH = 0x00663B80;

    public struct Overlay
    {
        public uint VTable;
        public uint Size;
        public bool TakesUnitSize;
        public string What;
    }

    /// The overlays that can be turned on this way, by the name the game gives
    /// them. ShowVisMap and ShowKIMap are missing on purpose: those two ask the
    /// visibility and the AI manager for a map first, which is more than one
    /// object and a pointer.
    public static readonly Dictionary<string, Overlay> Overlays =
        new Dictionary<string, Overlay>(StringComparer.OrdinalIgnoreCase)
    {
        { "showstructures", new Overlay { VTable = 0x007C8820, Size = 4,
              What = "where the engine sees buildings" } },
        { "showair", new Overlay { VTable = 0x007D31D4, Size = 4,
              What = "the air layer" } },
        { "showparty", new Overlay { VTable = 0x007D31C8, Size = 4,
              What = "the party" } },
        { "showobjectsize", new Overlay { VTable = 0x007D31BC, Size = 4,
              What = "how big the engine thinks objects are" } },
        { "showpath", new Overlay { VTable = 0x007D31B0, Size = 4,
              What = "the paths being walked" } },
        { "showground", new Overlay { VTable = 0x007C882C, Size = 4,
              What = "the ground types" } },
        { "showpathmap", new Overlay { VTable = 0x007D31A4, Size = 12,
              TakesUnitSize = true,
              What = "what a unit of the given size can walk on" } },
        { "showsmoke", new Overlay { VTable = 0x007D31E0, Size = 4,
              What = "smoke" } },
    };

    // The page the overlay object lives in, and the game it belongs to.
    private static uint _overlayPage;
    private static int _overlayPid;

    /// Runs a piece of code in the game and waits for it.
    private static string RunCode(IntPtr process, byte[] code, out uint returned)
    {
        returned = 0;
        IntPtr memory = VirtualAllocEx(process, IntPtr.Zero, 0x1000, MEM_COMMIT_RESERVE,
                                       PAGE_EXECUTE_READWRITE);
        if (memory == IntPtr.Zero) return "Could not allocate memory in the game process.";
        try
        {
            UIntPtr written;
            WriteProcessMemory(process, memory, code, (uint)code.Length, out written);
            IntPtr thread = CreateRemoteThread(process, IntPtr.Zero, 0, memory,
                                               IntPtr.Zero, 0, IntPtr.Zero);
            if (thread == IntPtr.Zero)
                return "Cannot create a thread in the game process (error "
                       + Marshal.GetLastWin32Error() + ").";
            WaitForSingleObject(thread, 5000);
            GetExitCodeThread(thread, out returned);
            CloseHandle(thread);
            return null;
        }
        finally
        {
            VirtualFreeEx(process, memory, 0, MEM_RELEASE);
        }
    }

    private static byte[] SwitchCode(uint renderer, bool on)
    {
        var b = new List<byte>();
        b.Add(0xB9); Dword(b, renderer);                      // mov ecx, renderer
        b.AddRange(new byte[] { 0x6A, (byte)(on ? 1 : 0) });  // push 1 / 0
        b.Add(0xB8); Dword(b, OVERLAY_SWITCH);                // mov eax, the switch
        b.AddRange(new byte[] { 0xFF, 0xD0 });                // call eax - ret 4
        b.AddRange(new byte[] { 0xB8, 0x01, 0, 0, 0 });       // mov eax, 1
        b.AddRange(new byte[] { 0xC2, 0x04, 0x00 });          // ret 4
        return b.ToArray();
    }

    /// Turns one overlay on. `name` is null to turn whatever is drawn off.
    /// `unitSize` is only read by showpathmap. Returns null on success.
    public static string ShowOverlay(string name, int unitSize)
    {
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            uint world = ReadDword(process, WORLD_GLOBAL);
            if (world == 0) return "No mission is running - the overlays draw on the terrain.";
            uint renderer = ReadDword(process, world + RENDERER_AT);
            if (!Plausible(renderer)) return "The terrain is there but the renderer is not.";

            uint returned;
            UIntPtr written;
            if (name == null)
            {
                WriteProcessMemory(process, (IntPtr)(renderer + OVERLAY_AT), new byte[4], 4,
                                   out written);
                return RunCode(process, SwitchCode(renderer, false), out returned);
            }

            Overlay overlay;
            if (!Overlays.TryGetValue(name, out overlay))
                return "\"" + name + "\" is not an overlay I know.";

            if (_overlayPage == 0 || _overlayPid != game.Id)
            {
                IntPtr page = VirtualAllocEx(process, IntPtr.Zero, 0x1000, MEM_COMMIT_RESERVE,
                                             PAGE_EXECUTE_READWRITE);
                if (page == IntPtr.Zero) return "Could not allocate memory in the game process.";
                _overlayPage = (uint)page.ToInt64();
                _overlayPid = game.Id;
            }

            var body = new byte[overlay.Size];
            Array.Copy(BitConverter.GetBytes(overlay.VTable), body, 4);
            if (overlay.TakesUnitSize)
            {
                Array.Copy(BitConverter.GetBytes(unitSize), 0, body, 4, 4);
                Array.Copy(BitConverter.GetBytes(unitSize), 0, body, 8, 4);
            }
            WriteProcessMemory(process, (IntPtr)_overlayPage, body, overlay.Size, out written);
            WriteProcessMemory(process, (IntPtr)(renderer + OVERLAY_AT),
                               BitConverter.GetBytes(_overlayPage), 4, out written);
            return RunCode(process, SwitchCode(renderer, true), out returned);
        }
        finally
        {
            CloseHandle(process);
        }
    }



    // ---------------------------------------------------------------- the map

    // The engine keeps one dword per world unit in a plain array - the same one
    // the debug overlays read, which is how the bits below are known. The world
    // is the global at 0x880F98, null outside a mission:
    //
    //     [world+0x24]  width in units      [world+0x2C]  the array
    //     [world+0x28]  height in units     cell = array[y*width + x]
    //
    // A campaign map is 1200x1200 units - that is the 75x75 cells of the .mis
    // file times the sixteen units a cell is across - so the array is 5.8 MB.
    // Big, but it reads in one go and holds everything the overlays show.
    private const uint MAP_WIDTH_AT = 0x24;
    private const uint MAP_HEIGHT_AT = 0x28;
    private const uint MAP_CELLS_AT = 0x2C;

    // The height is not in that array. ShowPathMap is the one overlay that does
    // not read it - it asks the path manager at [world+0x14], which keeps a
    // grid of its own (0x675FD0): 76 bytes a cell, the array at
    // [[manager+0xC4]+4], as many cells across as the world is wide in units
    // (manager+0xC8) divided by 16. The height of a cell is the int at +0x40,
    // in world units - 0x675C20 is the getter and shifts it down by four.
    //
    // So this grid is the coarse one: one cell to sixteen units, which is the
    // cell of the .mis file. A campaign map is 75x75 of them.
    //
    // The terrain does not move during a mission, so this is read once and kept
    // until the array moves, which means a new mission.
    private const uint PATH_MANAGER_AT = 0x14;
    private const uint PATH_WORLD_WIDTH_AT = 0xC8;
    private const uint PATH_WORLD_HEIGHT_AT = 0xCC;
    private const uint PATH_ARRAY_AT = 0xC4;
    private const uint PATH_CELL = 76;
    private const uint PATH_CELL_HEIGHT_AT = 0x40;

    private static int[] _heights;
    private static uint _heightsFrom;

    /// One reading of the map. `Cells` is width*height dwords, row by row.
    public sealed class MapSnapshot
    {
        public int Width, Height;
        public uint[] Cells;
        /// The height grid, coarser than the map: one value to sixteen units.
        /// Null when the path manager has nothing that lines up.
        public int[] Heights;
        public int HeightWidth, HeightHeight;
    }

    /// The height of every cell, or null when the path manager has nothing that
    /// lines up with the map. Failure here is not an error - the map is drawn
    /// flat instead.
    private static void ReadHeights(IntPtr process, uint world, MapSnapshot map)
    {
        uint manager = ReadDword(process, world + PATH_MANAGER_AT);
        if (!Plausible(manager)) return;

        uint worldWidth = ReadDword(process, manager + PATH_WORLD_WIDTH_AT);
        uint worldHeight = ReadDword(process, manager + PATH_WORLD_HEIGHT_AT);
        int width = (int)((worldWidth + 15) / 16);
        int height = (int)((worldHeight + 15) / 16);
        // The same map, sixteen units to a cell - anything else is a grid that
        // belongs to something other than what was just read.
        if (width <= 0 || height <= 0
            || width != (map.Width + 15) / 16 || height != (map.Height + 15) / 16)
            return;

        uint container = ReadDword(process, manager + PATH_ARRAY_AT);
        if (!Plausible(container)) return;
        uint begin = ReadDword(process, container + 4);
        uint end = ReadDword(process, container + 8);
        if (!Plausible(begin) || end <= begin) return;
        if ((end - begin) / PATH_CELL < (uint)(width * height)) return;

        map.HeightWidth = width;
        map.HeightHeight = height;
        if (_heights != null && _heightsFrom == begin && _heights.Length == width * height)
        {
            map.Heights = _heights;
            return;
        }

        uint bytes = (uint)(width * height) * PATH_CELL;
        var raw = new byte[bytes];
        UIntPtr read;
        if (!ReadProcessMemory(process, (IntPtr)begin, raw, bytes, out read)
            || read.ToUInt32() != bytes)
            return;

        var heights = new int[width * height];
        for (int i = 0; i < heights.Length; i++)
            heights[i] = BitConverter.ToInt32(raw, (int)(i * PATH_CELL + PATH_CELL_HEIGHT_AT));
        _heights = heights;
        _heightsFrom = begin;
        map.Heights = heights;
    }

    /// Reads the whole map out of the running game. Returns null on success and
    /// leaves `map` filled, otherwise a message.
    public static string ReadMap(out MapSnapshot map)
    {
        map = null;
        Process game = FindGame();
        if (game == null) return "The game is not running.";

        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero)
            return "Cannot attach to the game process (error " + Marshal.GetLastWin32Error() + ").";
        try
        {
            uint world = ReadDword(process, WORLD_GLOBAL);
            if (world == 0) return "No mission is running.";

            uint width = ReadDword(process, world + MAP_WIDTH_AT);
            uint height = ReadDword(process, world + MAP_HEIGHT_AT);
            uint cells = ReadDword(process, world + MAP_CELLS_AT);
            if (width == 0 || height == 0 || width > 8192 || height > 8192)
                return "The map is not loaded yet.";
            if (!Plausible(cells)) return "The map is there but its cells are not.";

            uint bytes = width * height * 4;
            var raw = new byte[bytes];
            UIntPtr read;
            if (!ReadProcessMemory(process, (IntPtr)cells, raw, bytes, out read)
                || read.ToUInt32() != bytes)
                return "The map could not be read whole - it may be being loaded.";

            var snapshot = new MapSnapshot
            {
                Width = (int)width,
                Height = (int)height,
                Cells = new uint[width * height],
            };
            Buffer.BlockCopy(raw, 0, snapshot.Cells, 0, (int)bytes);
            ReadHeights(process, world, snapshot);
            map = snapshot;
            return null;
        }
        finally
        {
            CloseHandle(process);
        }
    }



    // ------------------------------------------------------------- the units

    // The cell array only carries a unit where the party can see it, so a map
    // drawn from it is a map of what the player knows. The objects behind it do
    // not come and go: every object standing on the map keeps its position as
    // two floats at +0x54 and +0x58 and a stamp at +0x150, and the stamp holds
    // the same position as ints at +0x24 and +0x28 with the value it writes at
    // +0x18 - whose 0xF00 is the number of the party it belongs to.
    //
    // Three fields agreeing - a vtable inside the exe, two floats inside the
    // map, and a stamp whose ints match those floats - is a signature nothing
    // else in the heap answers to. tools/find_units.py walked to it the long
    // way round, from the map to the stamps to the objects; this is the short
    // way, and it finds the units the map window cannot show.
    // Which party the player is changes from mission to mission, and the cell
    // array does not say. The player's own party object does, but not as a
    // number: its first kilobyte holds no such value anywhere. What it holds,
    // at +0x78, is a pointer to an array of its units - six of them and then
    // zeros, which is the squad along the bottom of the screen. Read one of
    // those units and its stamp says which party it belongs to.
    //
    // The object is the class the exe calls Y2KKIUIPlayer; there is exactly
    // one of it in a mission, and its vtable is 0x7CFE38.
    private const uint UIPLAYER_VTABLE = 0x007CFE38;
    private const uint UIPLAYER_UNITS_AT = 0x78;

    private const uint UNIT_X_AT = 0x54;
    private const uint UNIT_Y_AT = 0x58;
    private const uint UNIT_STAMP_AT = 0x150;
    private const uint STAMP_MASK_AT = 0x14;
    private const uint STAMP_VALUE_AT = 0x18;
    private const uint STAMP_X_AT = 0x24;
    private const uint STAMP_Y_AT = 0x28;

    public sealed class Unit
    {
        public uint Address;
        public uint VTable;
        public uint Stamp;
        public float X, Y;
        public int Party;
    }

    /// Which party the player is, or 0 when it cannot be told.
    public static int PlayerParty()
    {
        Process game = FindGame();
        if (game == null) return 0;
        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero) return 0;
        try
        {
            uint player = FindByVTable(process, UIPLAYER_VTABLE);
            if (player == 0) return 0;
            uint units = ReadDword(process, player + UIPLAYER_UNITS_AT);
            if (!Plausible(units)) return 0;

            // The first few entries are the squad; any of them will do, but a
            // dead one may have been cleared, so the first that leads to a
            // stamp with a party in it wins.
            for (uint i = 0; i < 8; i++)
            {
                uint unit = ReadDword(process, units + i * 4);
                if (!Plausible(unit)) continue;
                uint stamp = ReadDword(process, unit + UNIT_STAMP_AT);
                if (!Plausible(stamp)) continue;
                uint value = ReadDword(process, stamp + STAMP_VALUE_AT);
                int party = (int)((value >> 8) & 0xF);
                if (party != 0) return party;
            }
            return 0;
        }
        finally
        {
            CloseHandle(process);
        }
    }

    /// Every unit standing on the map, found by its own shape. Walks all the
    /// memory the game allocated for itself, so it takes a moment - the caller
    /// is meant to keep the result and only refresh the positions.
    public static List<Unit> FindUnits(int width, int height)
    {
        var units = new List<Unit>();
        Process game = FindGame();
        if (game == null) return units;
        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero) return units;
        try
        {
            var head = new byte[0x30];
            var buffer = new byte[0x100000];
            uint size = (uint)Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION));
            ulong at = 0x10000;
            MEMORY_BASIC_INFORMATION info;
            while (at < 0x7FFF0000
                   && VirtualQueryEx(process, (IntPtr)(long)at, out info, size) != IntPtr.Zero)
            {
                ulong region = (ulong)info.RegionSize.ToInt64();
                if (region == 0) break;
                ulong start = (ulong)info.BaseAddress.ToInt64();
                if (info.State == MEM_COMMIT && info.Type == MEM_PRIVATE && Readable(info.Protect))
                {
                    for (ulong page = start; page < start + region; page += (ulong)buffer.Length)
                    {
                        uint length = (uint)Math.Min((ulong)buffer.Length, start + region - page);
                        UIntPtr read;
                        if (!ReadProcessMemory(process, (IntPtr)(long)page, buffer, length,
                                               out read))
                            continue;
                        int got = (int)read.ToUInt32();
                        // An object needs its stamp pointer to be inside what
                        // was read; the few that straddle a chunk are lost, and
                        // the next scan a moment later picks them up.
                        for (int i = 0; i + (int)UNIT_STAMP_AT + 4 <= got; i += 4)
                        {
                            uint vtable = BitConverter.ToUInt32(buffer, i);
                            if (vtable <= 0x400000 || vtable >= 0x800000) continue;
                            float x = BitConverter.ToSingle(buffer, i + (int)UNIT_X_AT);
                            float y = BitConverter.ToSingle(buffer, i + (int)UNIT_Y_AT);
                            if (!(x >= 1f && x < width && y >= 1f && y < height)) continue;
                            uint stamp = BitConverter.ToUInt32(buffer, i + (int)UNIT_STAMP_AT);
                            if (!Plausible(stamp)) continue;

                            UIntPtr got2;
                            if (!ReadProcessMemory(process, (IntPtr)stamp, head, 0x30, out got2)
                                || got2.ToUInt32() != 0x30)
                                continue;
                            uint mask = BitConverter.ToUInt32(head, (int)STAMP_MASK_AT);
                            uint value = BitConverter.ToUInt32(head, (int)STAMP_VALUE_AT);
                            uint sx = BitConverter.ToUInt32(head, (int)STAMP_X_AT);
                            uint sy = BitConverter.ToUInt32(head, (int)STAMP_Y_AT);
                            if (mask < 0xF0000000 || (value & 0xF00) == 0) continue;
                            if (Math.Abs((double)sx - x) > 2 || Math.Abs((double)sy - y) > 2)
                                continue;

                            units.Add(new Unit
                            {
                                Address = (uint)(page + (ulong)i),
                                VTable = vtable,
                                Stamp = stamp,
                                X = x,
                                Y = y,
                                Party = (int)((value >> 8) & 0xF),
                            });
                        }
                    }
                }
                at = start + region;
            }
        }
        finally
        {
            CloseHandle(process);
        }
        return units;
    }

    /// Reads the positions of units already found. Anything that no longer
    /// looks like a unit - it died, or the memory was reused - is dropped, so
    /// the list stays honest between full scans.
    public static void RefreshUnits(List<Unit> units, int width, int height)
    {
        if (units.Count == 0) return;
        Process game = FindGame();
        if (game == null) { units.Clear(); return; }
        IntPtr process = OpenProcess(PROCESS_ALL, false, game.Id);
        if (process == IntPtr.Zero) return;
        try
        {
            var head = new byte[0x30];
            var body = new byte[8];
            for (int i = units.Count - 1; i >= 0; i--)
            {
                Unit unit = units[i];
                UIntPtr read;
                bool alive =
                    ReadDword(process, unit.Address) == unit.VTable
                    && ReadProcessMemory(process, (IntPtr)(unit.Address + UNIT_X_AT), body, 8,
                                         out read) && read.ToUInt32() == 8
                    && ReadProcessMemory(process, (IntPtr)unit.Stamp, head, 0x30, out read)
                    && read.ToUInt32() == 0x30;
                if (alive)
                {
                    float x = BitConverter.ToSingle(body, 0);
                    float y = BitConverter.ToSingle(body, 4);
                    uint value = BitConverter.ToUInt32(head, (int)STAMP_VALUE_AT);
                    if (x >= 1f && x < width && y >= 1f && y < height && (value & 0xF00) != 0)
                    {
                        unit.X = x;
                        unit.Y = y;
                        unit.Party = (int)((value >> 8) & 0xF);
                        continue;
                    }
                }
                units.RemoveAt(i);
            }
        }
        finally
        {
            CloseHandle(process);
        }
    }
}
