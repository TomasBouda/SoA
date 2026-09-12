# The `Data.set` format

The library of gear, weapons and ammunition: `data/GameData/Data.set` inside
`data.ubn`, 21,303 B. [tools/dataset.py](tools/dataset.py) parses all 133
records; this page records what is verified and how it was worked out, dead ends
included.

## What holds

```
header    4 dwords: 7, 133, 1, 1        (133 = the item count, matches the number of SET ids)
record    strings ended by the one starting with SET_, then a block of numbers
string    1 B length + bytes (latin1); an empty string has length 0
```

There are usually four strings: the German name, the text id, the hint id and
the `SET_` identifier. Vehicles kept as equipment have no text id and carry the
name directly instead — `FLOGGER`, `FLOGGER`, `SET_FLOGGER`. That is exactly why
the names must not be looked up as the "nearest id", see
[tools/gen_ids_doc.py](tools/gen_ids_doc.py).

The block of numbers follows immediately after the last string and is **not
aligned** — the strings have arbitrary lengths, so the dwords start at an
arbitrary address.

Two block lengths were measured by hand from a hex dump:

| item | fields | what looks meaningful in them |
|---|---|---|
| `SET_MUN_MG` (ammunition) | 18 | `15.0, 10.0, 12, 14, 2, 4, 4, 5, 5, 0, 2, 1, 10.0, 50, 1, 470, 1, 21` |
| `SET_MUN_AK74` (ammunition) | 18 | `5.0, 3.0, 9, 11, 2, 3, 3, 4, 4, 0, 2, 1, 3.0, 30, 1, 900, 1, 22` |
| `SET_M60` (weapon) | 23 | `50.0, 6.0, 35, 0, 650.0, -1, 0.6, …` |
| `SET_AK74` (weapon) | 23 | `10.0, 6.0, 25, 0, 650.0, -1, 0.7, …` |

The last record, `SET_CRAWLERSENDER`, has only **8 bytes** after the identifier
(`300.0`, `6.0`) and the file ends there.

## What the code says

The library is loaded by `Y2KKIObjectSettings.cpp`; in the exe that is the
function at `0x5BE8C0`, which opens `Data\GameData\Data.set` and hands it to the
parser at `0x5BE940`. That one reads like this:

```
5BE94E   read 4       version        (7)
5BE970   read 4       count          (133)
5BE98D   read 4       type           (1)   <- once, not per item
         loop over the count:
5BE989     read 4     item number
5BE99F     call 0x5BEA20              the factory: builds an object by type
5BE9B5     call [vtable+4]            the object reads its own fields
```

That explains why a flat parser fails: **every class reads its fields itself**.
The factory at `0x5BEA20` knows four types (`cmp eax, 3` and a jump table at
`0x5BECC0`) and they differ in the size of the object:

| type | constructor | object size |
|---|---|---|
| 0 | `0x5BEA57` | 0x54 B |
| 1 | `0x5BEADA` | 0x88 B |
| 2 | `0x5BEB3A` | 0xA4 B |
| 3 | `0x5BEBD0` | 0xB8 B |

`Data.set` uses type **1**, because that is what stands in the header once.

## Verified fields

**What the fields mean is on [weapons.md](weapons.md)** - the damage of the
ammunition (three ranges and a penetration threshold, read off `TakeDamage`
at `0x57CDB0` and checked with the gun), the blast radius, the weapons'
range and rate of fire, the vehicles' hit points and armour. The notes
below are the earlier findings that page rests on.

**Field 0 is the trade value.** In the loaded object it is member `+0x4C` and
the trader multiplies exactly that one - the unit value function at `0x725C90`
ends with `fmul dword ptr [eax + 0x4c]`, and three item classes expose the same
member in vtable slot `+0x28`, which is the slot the trade sums call. The
numbers agree with what one would expect: F-15 7000, T-55 3000, HUMVEE 500,
AK-74 20, Beretta 5, a Box 3. The whole mechanism is described in
[trading.md](trading.md).

**Field 13 is the stack size.** It matches the name the game shows:
`SET_MUN_MG` is called "7,62mm x 50" and holds 50, `SET_MUN_AK74` is
"5,45mm x 30" and holds 30. Both read by hand from a hex dump, not from the
parser, so it did not matter that the parser was not working at the time.

The last four fields of ammunition look like pairs of "count, value":
`1, 470, 1, 21` for the MG and `1, 900, 1, 22` for the AK74.

## How it was parsed in the end

The length of the number block cannot be guessed, and it does not have to be.
The `SET_` identifiers can be found in the file directly and **every record ends
with one**, so for each of them we try which start position lets us read "two
ints and four strings" ending exactly on it. That bounds the record from both
sides and the number block is simply whatever is left between the end of one
record and the start of the next.

The last obstacle was the umlauts: the "does this look like text" check took
ASCII only and stopped at the item `Armbrustköcher`. It is enough to allow high
bytes too, only control characters are a problem.

```
header    version (7), count (133)
record    type (0-3), item number, four strings, block of numbers
```

That parses all 133 records, and the file holds all four types from the factory,
not only type 1 — which is where the variable block length comes from:

| type | fields | items | what it is |
|---|---|---|---|
| 0 | 2 | 15 | odds and ends |
| 1 | 16 | 39 | ammunition |
| 2 | 20–24 | 56 | weapons and weapon systems |
| 3 | 24 | 23 | vehicles kept as equipment |

The field count is not measured from the code but as the gap between the end of
one record and the start of the next, which is why it varies for type 2. Either
there is padding there, or the boundary lands a few bytes off on some records —
it affects neither the item numbers nor the strings, those are anchored from
both sides.

### The item number is not the position

The second int of a record is the **item number** and that is exactly what the
`equipment` cheat takes as its argument. It has nothing to do with the position
in the file: `SET_MUN_MG` is first and has number 1, `SET_M60` is thirty-ninth
and has number 2, `SET_MEDIKIT` has 226. The highest is 252, which matches the
message the game writes into the log at startup:
`max used object settings id: 252`.

It came out through the trainer: the game refused `equipment(0)` (no item has
number 0) and `equipment(24)` added crossbow bolts instead of what the position
promised.

## What exactly `Load` reads

An object of type 1 has its vtable at `0x7CE3B0`; `Load` is slot `+4`, that is
`0x5BCBF0`. It first calls the base at `0x5BC970` and then reads its own fields.

**The base** branches by version (jump table `0x5BCAD4`, versions 3–7). For
version 7 it reads:

| order | what | where in the object |
|---|---|---|
| 1 | int | `+0x08` |
| 2–5 | four strings | `+0x0C`, `+0x1C`, `+0x2C`, `+0x3C` |
| 6 | int | `+0x4C` |
| 7 | int | `+0x50` |

That last read is done through `add edi, 0x50` instead of `lea`, so an automatic
pattern search misses it — watch out for that, it cost one missing dword.

**Type 1** then adds fourteen ints, guarded by the condition `3 ≤ version ≤ 7`:

```
+0x54 +0x58 +0x5C +0x60 +0x64 +0x68 +0x6C +0x84
+0x70 +0x74 +0x50 +0x78 +0x7C +0x80
```

## Where the flat model got stuck (superseded by the section above)

The model **`[2 ints][4 strings][16 ints]`** parses the first 41 records, that is
the whole of the ammunition, and gives meaningful values: the first int is
always 1, the second is the ordinal number of the item (1, 21, 22, 23, …). Field
13 of the block is the stack size, as the names confirm.

At the end of the ammunition the model runs off the rails. What was tried:

* **a backtracking search** over field counts 0–39 for every record, with the
  condition of getting through all 133 and ending exactly at the end of the file
  — no solution exists;
* the same with the assumption that the first int is the type 0–3 from the
  factory — also nothing.

From that it follows that past the ammunition the **number of strings** changes
as well, not only the number of ints. That fits the earlier observation that
vehicles kept as equipment hold only `FLOGGER`, `FLOGGER`, `SET_FLOGGER` in the
record.

The next step was the same one that worked at the beginning: take a hex dump
around the transition (records 39 to 42) and read it by hand. Automation gropes
around there without knowing the rule, because there are too many possibilities.

## There is no weapon-to-carrier link in the data

It was looked for twice and never found:

* **The fields of the vehicle records** (type 3) carry no references to weapons.
  The matches that can be found in them are coincidences — the same item comes
  out for every vehicle, because the value is 1.
* **`Units.olb`** does not hold the numbers of the weapons that belong on the
  OH-58 according to the game. There are only the hardpoints `dmyw_001` and
  `dmyw_002`, that is how many of them there are, not what may go on them.
* **The weapon fields** do not have it either. From playing, `SET_HELI_AT6` (89)
  and the helicopter machine gun (250) belong on the OH-58 while `SET_HELI_TOW`
  (87) does not — and there is nothing in their fields that would tell that pair
  apart from the rest.

That is why the catalog pairs the vehicle armament **by name**
(`SET_T55_ROHRMG` belongs to the T-55), which is a naming convention, not a
table. The helicopter weapons do not carry the name of the carrier, so they stay
in a group of their own.

## Why it matters

What is being looked for in here is the link between a weapon system and its
carrier — what an OH-58 can be armed with. Neither the texts nor `Units.olb`
hold a reference to a carrier, so it would have to be numeric and right here.
Until it is found, the only reliable answer stays the vehicle screen in the
base, where the slots themselves offer what belongs in them.
