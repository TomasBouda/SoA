// What a soldier carries, read out of a save and written back.
//
// A character's record opens with his `TRES_` key and runs to the next one.
// Inside it, every item he carries is three dwords - the slot it occupies, the
// number the catalog uses, and an identifier - followed by a zero byte and the
// serialiser's `FF FF FF FF 01`. Nothing in the record says where its equipment
// begins, so the way to the items is backwards from that marker.
//
// The record boundary is the whole point. A save holds the same item numbers in
// several places: swap a weapon at the depot and it moves between the soldier
// and the store, so both ends change and both look equally convincing. Only the
// copy inside his record is what the game puts in his hands - established by
// writing a weapon he could not already have had into each in turn and seeing
// which one he came out holding.
//
// The four slots came out of the data rather than out of a guess. Every entry
// in twenty saves falls into one of four values and each holds exactly one kind
// of thing: 1 the pack - medipacks, binoculars, mines - 2 the weapon, 4
// ammunition, 8 the vest.
//
// It works the same in a mission save, where the records sit three megabytes in
// among the landscape but are written identically.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

/// One item a character carries.
internal sealed class Carried
{
    public int Offset;        // where the item number sits in the file
    public int Slot;
    public int Item;
    public uint Id;
    public string Owner;      // the character it belongs to, readably
    public string Name;       // what the catalog calls it

    public string Kind { get { return Inventory.KindOf(Slot); } }

    public override string ToString()
    {
        return Owner.PadRight(22) + "  " + Kind.PadRight(11) + "  " + Name;
    }
}

/// One item on offer in the dropdown. `Fits` is only about the order they are
/// shown in - the slot an item usually occupies, guessed from the catalog.
internal sealed class Choice
{
    public int Number;
    public string Name;
    public bool Fits;

    public override string ToString()
    {
        return (Fits ? "" : "- ") + Name;
    }
}

/// One character's record: where it starts, where it ends, and whose it is.
internal sealed class Person
{
    public int Start;
    public int End;
    public string Key;
    public string Name;

    public override string ToString() { return Name; }
}

internal static class Inventory
{
    private static readonly byte[] Marker = { 0xFF, 0xFF, 0xFF, 0xFF, 0x01 };

    public static string KindOf(int slot)
    {
        switch (slot)
        {
            case 1: return "in the pack";
            case 2: return "weapon";
            case 4: return "ammunition";
            case 8: return "armour";
            default: return "slot " + slot;
        }
    }

    // ------------------------------------------------------------- the catalog

    private static Dictionary<int, string> _items;
    private static Dictionary<int, int> _likely;

    /// The equipment the catalog knows, by number, and alongside it the slot
    /// each item most likely belongs in.
    ///
    /// Vehicles are left out: they are not carried and a soldier holding one
    /// would be nonsense. The slot is a guess from the catalog's own columns -
    /// what has ammunition is a weapon, what is in the ammunition group is
    /// ammunition, a vest says so in its name - and it only decides the order
    /// of a dropdown. Anything can still be written into any slot, because the
    /// game may well allow what this guess does not.
    public static Dictionary<int, string> Items()
    {
        if (_items != null) return _items;
        var found = new Dictionary<int, string>();
        var slots = new Dictionary<int, int>();
        foreach (string line in CatalogData.Lines())
        {
            if (line.Length == 0 || line[0] == '#') continue;
            string[] c = line.Split('\t');
            if (c.Length < 5 || c[0] != "equipment") continue;
            int number;
            if (!int.TryParse(c[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out number))
                continue;
            found[number] = c[3];
            int ammo = 0;
            if (c.Length > 6) int.TryParse(c[6], NumberStyles.Integer,
                                           CultureInfo.InvariantCulture, out ammo);
            slots[number] = c[4] == "Ammunition" ? 4
                          : c[3].IndexOf("Vest", StringComparison.OrdinalIgnoreCase) >= 0 ? 8
                          : ammo > 0 ? 2 : 1;
        }
        _likely = slots;
        _items = found;
        return _items;
    }

    public static int LikelySlot(int number)
    {
        Items();
        int slot;
        return _likely.TryGetValue(number, out slot) ? slot : 0;
    }

    // ------------------------------------------------------------- the records

    /// `TRES_NAME_HELENA_MARKOVA` as something a person would write.
    public static string Pretty(string key)
    {
        string name = key.Substring("TRES_".Length);
        if (name.StartsWith("NAME_", StringComparison.Ordinal))
            name = name.Substring("NAME_".Length);
        string[] words = name.Split('_');
        var built = new List<string>();
        foreach (string w in words)
        {
            if (w.Length == 0) continue;
            built.Add(char.ToUpperInvariant(w[0]) + w.Substring(1).ToLowerInvariant());
        }
        return string.Join(" ", built.ToArray());
    }

    /// The characters in a save, each with the stretch of file it owns.
    ///
    /// `TRES_OBJECTS_` keys name vehicles and weapons rather than people, so
    /// they are not boundaries.
    public static List<Person> People(Save save)
    {
        var keys = new List<KeyValuePair<int, string>>();
        foreach (KeyValuePair<int, string> pair in save.AllStrings())
            if (pair.Value.StartsWith("TRES_", StringComparison.Ordinal)
                && !pair.Value.StartsWith("TRES_OBJECTS_", StringComparison.Ordinal))
                keys.Add(pair);

        var found = new List<Person>();
        for (int i = 0; i < keys.Count; i++)
            found.Add(new Person
            {
                Start = keys[i].Key,
                End = i + 1 < keys.Count ? keys[i + 1].Key : save.Raw.Length,
                Key = keys[i].Value,
                Name = Pretty(keys[i].Value)
            });
        return found;
    }

    // -------------------------------------------------------------- the items

    /// What one character carries.
    ///
    /// An entry counts only when its slot is one of the four and its number is
    /// in the catalog. Both tests are needed: the marker is a general
    /// serialisation prefix and turns up on plenty of things that are not
    /// equipment, and in three megabytes of landscape it turns up often.
    public static List<Carried> Of(Save save, Person who)
    {
        var found = new List<Carried>();
        Dictionary<int, string> items = Items();
        byte[] raw = save.Raw;
        int at = IndexOf(raw, Marker, who.Start, who.End);
        while (at >= 0)
        {
            if (at >= 13 && raw[at - 1] == 0)
            {
                int slot = (int)BitConverter.ToUInt32(raw, at - 13);
                int item = (int)BitConverter.ToUInt32(raw, at - 9);
                uint id = BitConverter.ToUInt32(raw, at - 5);
                string name;
                if (KnownSlot(slot) && items.TryGetValue(item, out name))
                    found.Add(new Carried
                    {
                        Offset = at - 9,
                        Slot = slot,
                        Item = item,
                        Id = id,
                        Owner = who.Name,
                        Name = name
                    });
            }
            at = IndexOf(raw, Marker, at + 1, who.End);
        }
        return found;
    }

    /// Everything everybody in the save carries.
    public static List<Carried> All(Save save)
    {
        var found = new List<Carried>();
        foreach (Person who in People(save)) found.AddRange(Of(save, who));
        return found;
    }

    private static bool KnownSlot(int slot)
    {
        return slot == 1 || slot == 2 || slot == 4 || slot == 8;
    }

    private static int IndexOf(byte[] raw, byte[] want, int from, int until)
    {
        int last = Math.Min(until, raw.Length) - want.Length;
        for (int i = Math.Max(0, from); i <= last; i++)
        {
            bool same = true;
            for (int k = 0; k < want.Length; k++)
                if (raw[i + k] != want[k]) { same = false; break; }
            if (same) return i;
        }
        return -1;
    }

    // ------------------------------------------------------------- the writing

    /// Put another item in that slot. Null when it worked, otherwise why not.
    ///
    /// The save is copied to .bak first, once - a second edit keeps the first
    /// backup rather than overwriting it with an already-edited file, so the
    /// way back is always to the save the game itself wrote.
    public static string Write(string path, int offset, int item)
    {
        try
        {
            byte[] raw = File.ReadAllBytes(path);
            if (offset < 0 || offset + 4 > raw.Length)
                return "0x" + offset.ToString("X") + " is past the end of the file.";
            string backup = path + ".bak";
            if (!File.Exists(backup)) File.Copy(path, backup);
            byte[] value = BitConverter.GetBytes(item);
            Array.Copy(value, 0, raw, offset, 4);
            File.WriteAllBytes(path, raw);
            return null;
        }
        catch (Exception e) { return e.Message; }
    }
}
