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
