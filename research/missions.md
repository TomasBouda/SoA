# Mission files (.mis)

What a mission is made of, from the outside in. This page deliberately stays on
the structure - sizes, formats, offsets. It says nothing about what happens in
the missions, and the briefings, dialogues and goal texts are not quoted here on
purpose.

## What is in missions.ubn

145 MB packed, 171 MB unpacked, 1827 members:

| kind | count | size | what it is |
|---|---|---|---|
| `.mis` | 26 | 48.3 MB | the missions themselves |
| `.mp3` | 1724 | 73.6 MB | spoken lines (1637 campaign, 87 tutorial) |
| `.bik` | 12 | 48.5 MB | Bink videos |
| `.trs` | 16 | 0.3 MB | the texts of a mission, one file per mission and language |
| `.wav` | 2 | 0.7 MB | two tutorial sounds |

The `.mis` files split into 13 campaign missions (`Mission_1` … `Mission_9b`,
four of them as a/b pairs), a demo mission, a tutorial, four multiplayer maps
and six leftovers from development (`hard_test`, `Mission_usa`, `Bunker_light`
and friends) that the campaign never uses.

## The container

A `.mis` belongs to the same family as the saves - the magic GUID starts with
`0x38`, see [architecture.md](architecture.md). The header:

```
+0x00  16 B  magic GUID
+0x10  u32   version: 3, 5, 6, 8, 9 or 10 (10 = campaign and tutorial)
+0x14  u32   2
+0x18  u32   sub-version, 3 to 7
+0x1C  u32   map width    ) big endian, unlike the rest of the file
+0x20  u32   map height   )
+0x24  u32   number of parties
+0x28        per party: u32 kind + a length-prefixed name
```

The party names are the designer's working labels; a multiplayer map has one
party per player slot, named with a single byte.

## The terrain is zlib

Right after the header comes a row of deflate streams, each one `u32 packed
length` + a `78 da` zlib block, and every so often a few bytes of bookkeeping
slip in between two of them. Unpacked they are 32 KB each, and the count grows
with the map:

| map | chunks | unpacked |
|---|---|---|
| 20x20 | 18 | 0.5 MB |
| 25x25 | 30 | 0.9 MB |
| 30x30 | 42-44 | 1.3 MB |
| 35x35 | 59 | 1.8 MB |
| 40x40 | 76 | 2.3 MB |
| 75x75 | 265 | 8.2 MB |

A campaign mission therefore carries about 8 MB of terrain in 3.4 MB of file.
The heightmap, the texture assignment and the passability of the ground all live
in here; which chunk is which layer is not sorted out yet.

## The object table

After the terrain follows a table of fixed 44-byte records, one per object
placed in the map. Every record ends with sixteen `0xFF` bytes, which is what
makes the table easy to find and to walk:

```
u32     index into an object library
u32     attributes (the library and flags; not decoded)
float   x
float   y
float   three more (height, scale, rotation - not confirmed)
16 B    0xFF
```

**One map cell is 16 world units.** The objects of every single mission reach
from 0 to roughly 16 times the map size in both axes - a 75x75 mission spans
1200x1200 units. That holds for all 20 missions where the table parses, which is
what makes it more than a guess.

How many objects a mission places:

| mission | map | terrain | objects |
|---|---|---|---|
| Mission_1 | 75x75 | 265 chunks | 4318 |
| Mission_2 | 75x75 | 265 | 3461 |
| Mission_3 | 75x75 | 265 | 4674 |
| Mission_4 | 75x75 | 265 | 4861 |
| Mission_5a / 5b | 75x75 | 265 | 4889 / 4914 |
| Mission_6a / 6b | 75x75 | 265 | 3453 / 3518 |
| Mission_7 | 75x75 | 265 | 4235 |
| Mission_8a / 8b | 75x75 | 265 | 2694 / 4991 |
| Mission_9a / 9b | 75x75 | 265 | 5346 / 5917 |
| Tutorial | 40x40 | 76 | 1258 |
| Fabric_Area (mp) | 35x35 | 59 | 1223 |
| comegetsome (mp) | 25x25 | 30 | 548 |

## What is still unmapped

The rest of the file - 2.2 to 3.0 MB in a campaign mission, that is 80 % of it -
holds the units, the characters, their inventories and the mission script. It is
binary and indexed by number, not by name: a whole campaign mission contains
only a few dozen readable strings.

Two things are worth knowing before continuing:

* the scripting system is documented from the other side already, from the
  editor and the exe - 20 triggers, 42 events and 21 building blocks, see
  [editor-scripting.md](editor-scripting.md)
* [Melkij's PHP parser](https://github.com/Melkij/soa-game-revers-eng) already
  takes a `.mis` apart down to the script sections and its `struct/` directory
  names the fields, so it is the natural next step rather than starting over

## The tool

[tools/mis.py](tools/mis.py) reads all of the above:

```bash
python tools/mis.py                    # a summary of every mission in the archive
python tools/mis.py Mission_3          # one mission in detail
python tools/mis.py comegetsome --ids  # plus the histogram of object indexes
```

It reports the unmapped remainder as "tail", so it stays visible how much of the
format is still unknown.

## What the compression is

The compressed chunks are ordinary zlib. The exe carries zlib 1.1.3 statically
- both banners are in it - and the landscape reader calls `inflateInit2` with
15 window bits, then `inflate`, then `inflateEnd`. Nothing of the game's own is
mixed in, which is why Python reads them with `zlib.decompress` and no
arguments. The class that wraps it is `InflateReadStream`, over the same
`ReadStream` base that `ZipReadStream` and the plain file reader use, so a
member of a `.ubn` and a chunk of a `.mis` arrive through the same door.

The reader itself lives in `Y2K_LS_Serialize.cpp`, at `0x681850`, `0x681950`,
`0x681BB0` and `0x682050`; see [classes.md](classes.md).

## The tail: what is mapped now

Everything past the object table was one undivided "tail" - up to 2.7 MB of it
in a campaign mission. Three things in it are now readable.

**It opens with a 4x4 matrix** - where the camera starts - followed by
`FF FF FF FF 01`, the serialiser's object prefix, the same one the saves use.

**Then the parties**, one record each ending in a length-prefixed name. Their
records shrink by eight bytes in turn: 116, 108, 100, 92, 84, 76, 68 in an eight
party mission. That is what a triangular table of who stands with whom looks
like - the first party needs a relation to seven others and the last to none -
and it is the reason the record is not a fixed size.

**Then the characters**, at a nearly fixed stride: 357 bytes in one mission, 417
in another. Each is a length-prefixed name the mission author typed, then a zero
byte, eight bytes of `0xFF`, and then a run of numbers. That signature is what
makes them findable, and `mis.py --people` lists them:

    0xD06     Mirek Ralenko        6    77     6    50    65    68     1     0
    0xE69     Akim Boressenko      6    78     6    50    62    68     0     0

Four of those numbers sit between 50 and 78 in every character of every mission
looked at, which is what a skill out of a hundred looks like. Two more move
together and by party, so they are more likely to say which face and body the
man is drawn with.

**One of them is named now.** The last is a **special skill**, an index into the
seven the editor's own resources list, in this order:

    0 light weapon   1 heavy weapon   2 demolition   3 sniper
    4 heal           5 thief          6 athlet       7 none

That order comes from `RES_EDITOR_QUICKSELECT_SPECIALSKILL_*` in `Editor.gui`,
and it holds a small surprise: **the bunker's help text names only six**, leaving
the thief out. The thief exists in the editor and is not among the things a
soldier can be taught.

Over 581 characters in every mission in the archive the field never leaves 0 to
7. A soldier carries **two** special skills - the infirmary panel has
`SPECIALSKILL1` and `SPECIALSKILL2` - and in versions 3 to 6 both sit at the end
of the record. In 9 and 10 only the last is reliably placed, so `--people` names
that one and leaves the other alone.

**The alignment moves with the version.** Versions 9 and 10 carry one field more
at the front, a constant 4, and everything behind it shifts. Read on the older
alignment a skill lands where a number in the sixties belongs, and that is how
the shift gave itself away.

### The numbers in front, and what the code does with them

`Y2KRPG_Character.cpp` - in a directory the compiler recorded as `UnbornStats` -
is the class that reads these. Its reader at `0x603E90` takes them one dword at
a time into the object at **+8, +0xC, +0x10, +0x14, +0x1C, +0x20, +0x24**, then a
single byte at +0x28 and one more dword at +0x58. That is the file order, so the
fifth, sixth and seventh numbers in the record are the object's `+0x1C`, `+0x20`
and `+0x24`.

**They are not fixed attributes.** The update at `0x6041C0` moves them up and
down by small amounts as the game runs, according to flags on the same object:

    if [+0x4C]   +0x1C += 2   +0x20 += 4
    if [+0x50]   +0x1C += 1   +0x20 += 2
    if [+0x48]   +0x1C -= 3
    ...          +0x24 -= 5  or  += 5

Two of them move together and always in the same direction, and a third flag
lowers one of them on its own. Values in the sixties nudged by two and four, up
when something is set and down when something else is, is what aim under a
posture looks like - kneeling helps, being hurt does not.

**That is as far as this goes and no further.** The game never shows these
numbers to the player: nothing in any layout or text resource labels them, so
there is no screen to read the answer off. Naming one of them accuracy would be
a guess dressed as a finding, and this project has been caught by one of those
before. What is established is where they live, in what order they are read, and
that they are combat values the game adjusts rather than identity the author
typed.

The way to settle it is the one that has worked twice already in this project:
read the code that loads them, rather than stare at the numbers.

## The scripts, and reading a mission as prose

Past the characters and the unnamed objects, the end of the tail holds what the
mission author wrote. `mis.py --names` prints it in order, and mission one comes
out like this:

    base/start          large outpost       valley         waypoint east
    small outpost       wolves and bear     holzlager      timer 1 .. Timer 8

    start mission -> start tutorial dialog
    end dialog -> start first ping
    bear in small outpost killed -> wait 5 sec.
    waited for 5 sec. -> tutorial dialog (3.)
    entered large outpost -> 4. Dia
    east box taken -> timer 5
    valley destroyed -> mission won

The first block is the **regions** drawn in the editor, timers among them. The
second is the **scripts**, and their names are the designers' notes to
themselves - read in order they are a plain-language account of how the mission
works, arrows and all. After them come the dialogs each one plays and the music
tracks: `CD Track 20.mp3`, `ambiente_abends.mp3`.

**The encoding is not decoded.** A script record is short - the name, then a
handful of numbers in the two thousands that reference the placed objects and
the regions - and the numbering of the triggers and events is not among them
anywhere obvious. `editor-scripting.md` has the 20 triggers and 42 events out of
the executable, in the order they lie there; matching them to what the file
stores is where this stops.

What is usable today is the account in prose. For a mission nobody has
documented in twenty years, being able to read `valley destroyed -> mission won`
out of the file is worth more than it sounds.
