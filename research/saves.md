# What is in a save

Saves live in `Game\SaveGames\<profile>\`, one `.sav` each and, for the ones
made from the game's own save screen, a `.png` thumbnail beside it. The quick
save is `QuickSave.sav` and has no thumbnail; it is a single file, overwritten
every time.

Nothing is compressed and nothing is obfuscated. A `.sav` is the game's
serialiser writing its objects one after another, and the first few hundred
bytes are readable straight away. [tools/read_save.py](tools/read_save.py)
reads them.

## The shape of it

Every file this engine serialises opens with the same sixteen bytes bar the
first, which says which class wrote it - a GUID with the class byte in front:

| first byte | what wrote it |
|---|---|
| `0x38` | a save |
| `0x40` | a text resource, `.trs` |
| `0x41` | a layout, `.lay` |

Strings are written with a single length byte in front, so a name is `07`
followed by `Spieler`. That one rule is most of the format.

    +0x00  16   the magic above
    +0x10   4   version, 10 in every save seen
    +0x14   4   where it was taken: 1 in the bunker, 0 on a mission
    +0x18   4   5 in a bunker save, 10 in a mission save

A **bunker save** is a few kilobytes and carries the mission it will start
next, as a string at `+0x20`.

A **mission save** is megabytes, because it holds the landscape. It carries,
in order: the parties as `name` + a number that has been 2 throughout, then a
field whose shape is not worked out yet, then the mission's text file and the
mission itself. The **first party in the list is the player's**, which agrees
with what the running game says.

After that comes the world, and it has not been taken apart. What can still be
had from it without doing so is the names: characters written by the mission
author appear as themselves, and everything the game names for the interface
appears as a `TRES_` key that the text resources translate.

## The text resources

`.trs` files are simpler still - the magic, a version, a count, then that many
records of `id`, `key`, a string, the text, a string. `read_save.py` loads every
one in every archive so it can print `APC BTR` where the save says
`TRES_OBJECTS_UNIT_BTR_80`. The two spare strings are `leer` throughout, German
for empty, so they are probably a second language that was never filled in.

## Two readers

[tools/read_save.py](tools/read_save.py) is the one to reach for when
poking at the format; the launcher carries the same reader ported to C# in
`launcher/Saves.cs`, behind the **Saves** button, where it lists the saves
newest first and shows the thumbnail the game writes beside each named one.
The two were checked against each other over every save on this machine and
agree, including the one that is short and holds no names at all.

## Counting what is in a save, and why it is not done

The obvious thing to do with a list of names is count them, and the count is
wrong. A vehicle is written into the save **once for each weapon it can mount**,
in a tight run a hundred and fifty bytes apart, so a single helicopter reports
itself seven times and a bunker save with one Mi-24 in the garage says seven.

The runs give it away and the catalog confirms it: the T-55 mentions itself four
times and the catalog lists four weapons that mount on a T-55, the BMP-1 three
against three. Grouping the runs brings 82 down to 29 in one mission save, which
is better and still not a number worth printing - the HUMVEE is written singly
and does not group at all.

So the saves window shows **kinds, not counts**. What is in the save is exact;
how many of each is not known, and a wrong number reads as a fact.

The characters are the exception. They have records of their own, bounded by
their `TRES_` keys, so they are counted exactly and listed as people rather than
among the things.

## What this is good for

Telling saves apart without loading them, mainly - which mission, how far in,
who was still alive. It also settles questions that would otherwise need the
game running: the party order, for one.

Writing a save is a different job. The world would have to be understood field
by field first, and there is no reason to attempt it while the game's own
editor can make and change maps.

## Changing a save

Reading the world out of a save was never done - the header is understood and
the rest is not - so a field is found the other way round: make the game change
one thing, and look at what moved.

[tools/diff_save.py](tools/diff_save.py) compares two saves and reports every
stretch that differs **against the nearest name before it**, which is what makes
the output usable: `+0x42 of Boris Kerkowitsch` says something, offset 0x5ED
does not. A save is much kinder to this than memory, because nothing in a file
drifts on its own - no timers, no animation - so every difference is something
that actually happened.

It wants a **controlled pair**: two saves taken minutes apart with one
deliberate change between them and nothing else. Two saves from different
sittings differ in hundreds of places and in length, and the tool says so
rather than pretending the offsets still line up.

The bunker is the place to do it. A bunker save is about ten kilobytes and
holds the whole squad, against three megabytes for a mission save, most of
which is landscape.

The record layout, as far as it is visible: names sit at a regular stride -
`unknown name` every 0x97 bytes in one save - so the file is a run of records
with the named ones being characters and the rest the things nobody named.

## Equipment in a save, and changing it

**Known.** Equipment is written as the same numbers the catalog uses, in plain
little-endian dwords, and **a character carries what is written inside the
record that opens with his `TRES_` key** - `TRES_PROF_DR_SERGEJ_PETROW` and so
on, one record running to the next such key. That is the field the game reads
when it puts a rifle in a soldier's hands.

**The trap, and it cost two loads to see.** The same item numbers appear in
several places in one save. Swapping a weapon at the depot moves it between the
character and the store, so a controlled pair shows *both* ends changing, and
the two candidates look equally convincing - the same three-item row, the same
neighbours, the same distance past a name reading `Prof. Petrow`.

Only one of them is the soldier. Writing a Dragunov into the other one and
loading it produced a soldier holding a Dragunov, which read as a success and
was not: he had been holding a Dragunov all along. The check that settled it was
to write something he could not already have been holding - an M60 - into the
same place. He still held the Dragunov. The field was never his.

What separates the two is the record boundary. The copy that mattered lay
between `TRES_PROF_DR_SERGEJ_PETROW` and the next character's key; the copy that
did nothing lay before every character record, among the vehicles.

### One item, as it is written

Each item a character carries is three dwords followed by a zero byte and the
serialiser's `FF FF FF FF 01`:

    <slot>  <the catalog number>  <an identifier>  00  FF FF FF FF 01

Nothing in the record says where its equipment begins, so the way to the items
is **backwards from that marker**. Reading forwards from the record instead
produced the earlier mess of coincidences: in three megabytes of landscape a
small number that matches the catalog turns up constantly.

**The slots came out of the data.** Every entry in twenty saves falls into one of
four values, and each holds exactly one kind of thing - which is the check that
says the reading is right, because nothing forced it to come out that way:

| slot | what is ever in it |
|---|---|
| 1 | the pack - medipacks, binoculars, tank mines, explosives, FLY pills |
| 2 | the weapon - UZI, MP5, shotgun, AK74, Beretta, M60, crossbow |
| 4 | ammunition, every kind |
| 8 | armour, and only the light and heavy vest |

The third dword is not a count and not condition. A soldier's items hold values
within a few of each other - 400, 408, 410 for one man in one save, 47, 55, 57 in
an earlier one - so it goes up as the game runs. An identifier, most likely.

**Mission saves are written identically.** `TRES_PROF_DR_SERGEJ_PETROW` opens a
record at 0x365E05 of a three megabyte mission save exactly as it does at 0x2289
of a bunker save, and **editing it works there too** - the professor was given a
Dragunov in a quick save and carried it into the mission. So the live object on
the map does not hold a weapon of its own.

**Not known: where inside the record the equipment begins.** The record is not a
fixed size and the marker is what finds the items, not an offset.

[tools/edit_save.py](tools/edit_save.py) reads it:

    edit_save.py QuickSave --who Petrow      what he carries, with offsets
    edit_save.py M4_B --find Dragunov        every copy, and whose record it is in
    edit_save.py M4_B --set 0x232E M60       change the one that is his

`--find` names the owning record for every hit and says plainly when a hit is in
none - *the depot or a vehicle* - which is the distinction that was missing.

Writing goes to a copy unless `--in-place` is given, and that keeps a `.bak`.

### The game accepts an edited save

No checksum, no validation, no complaint: an edited save loads and plays. The
question was only ever which byte to edit.

### In the launcher

The **Saves** window lists everything everybody in the save carries, and one of
them can be swapped for anything in the catalog: pick the line, pick the
replacement, write it. `launcher/Inventory.cs` holds the format; the window does
nothing but show it.

The dropdown puts the items that suit the slot first - what has ammunition is a
weapon, what is in the ammunition group is ammunition, a vest says so in its
name - but it never refuses the rest, because that ordering is a guess from the
catalog's columns and the game may well allow what the guess does not.

The save is copied to `.bak` before the first change and not again, so the way
back is always to the file the game itself wrote rather than to an earlier edit.

### A marker for the inventory: looked for, not found

The bytes before a confirmed slot are `01 01 00 00 00 00 01` followed by three
dwords, which looked like an inventory header worth searching for.

**It is not one.** That sequence occurs 85 times in one bunker save, and most of
the hits are plainly something else: from 0x3EBD onwards the third dword counts
steadily up - 182, 183, 184 and so on to 213 - which is an index into a table,
not equipment. The sequence is a common serialisation prefix and nothing more.

**What would settle the layout**: controlled pairs on *different* soldiers.
Three confirmed offsets either fall at a regular stride, in which case the record
size is known and the rest follows, or they do not - which is worth knowing too.
The record boundary above is enough to change a weapon; it is not enough to read
an inventory.
