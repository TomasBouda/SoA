# The classes of the game, and what is known about each

[map.md](map.md) is made by a tool and says only which code belongs to which of
the 538 source files. This is the other half, written by hand: what each class
appears to be, what has actually been established about it, and what is a guess.

The distinction matters more here than anywhere else in this repository. Three
explanations of one symptom were derived from the code today, each fitting, each
backed by the disassembly, and all three were refused by the running game. So
every row below says which it is:

* **known** — read out of memory or the log, in a running game, and it held
* **read** — read out of the code and consistent with everything seen, but not
  put to the test
* **guess** — the name and its neighbours suggest it

The addresses are for `soa.exe` 1.1.2.178, which has no ASLR, so they are the
same on every machine and every start.

---

## The state machine

The game is one application object holding a current state. `quellstateclasses`
holds exactly five, and the log announces each change with
`CDXAStateApp::EndLoadThread() : New state class.`

| class | file | what it is |
|---|---|---|
| start screen | `Y2KStart.cpp` | the menu. **known:** it also owns the loader that reads a `.mis`, `0x60BC60`, which is why loading a mission only works from the menu |
| the bunker | `Y2KBunker.cpp` | the base screen. **known:** `0x8759D4` holds it while it is up and is null otherwise, which is what the base cheats need |
| loading | `Y2KMissionLoad.cpp` | **known:** vtable `0x7D05E8`, constructor `0x5FB600`, and the application hangs it on itself at `+0x398` |
| the mission | `Y2KMission.cpp` | **known:** vtable `0x7D0568` with a second at `+8` of the object, `0x7D0564`; the mission cheats, quick save and quick load are its methods |
| the editor | `Y2KEditor.cpp` | **read:** the whole mission editor is in the shipped exe - 1249 source files under `quellui_editor`, a state class of its own, and `LAY_EDITOR_*` layouts for every one of its panels. The state factory builds it as **id 3**, `new(0x5F0)` with the constructor at `0x538BE0` |

### The state factory

`Y2KApp.cpp` holds a factory that makes a state from a number
(`0x6D3630`, its jump table at `0x6D37AC`):

| id | size | constructor | what it is |
|---|---|---|---|
| 2 | `0x28` | `0x6C2A40` | global effects |
| 3 | `0x5F0` | `0x538BE0` | **the editor** |
| 4 | `0x2C4` | `0x5E7620` | a mission |
| 5 | `0x7B0` | `0x515670` | the bunker |
| 6 | `0xDC` | `0x6082C0` | the start screen |

The factory itself is reached from a case of a larger switch in the same file:
`0x6D3533` reads a request id in `edi`, and `edi == 9` lands on `0x6D3548`,
which is the case that builds a state. So changing screen is a request with a
number, and the editor is one of the numbers - which is the shape of every
other door opened in this project so far.

## The world and what stands on it

| class | file | what is known |
|---|---|---|
| the world | — | **known:** the global `0x880F98`. Width in units at `+0x24`, height at `+0x28`, and at `+0x2C` one dword per world unit - the array every debug overlay reads. The renderer hangs at `+0x48` |
| the landscape | `Y2KLandscape.cpp` | **known:** owns the debug overlay at `+0x3EC`; the path manager with the height of every cell is at `[world+0x14]` |
| the base of everything on the map | `Y2KKIBasicObject.cpp` | **known:** a byte at `+0xF0` says whether the object is currently written into the cell array, and `0x57C110` is the switch that puts it there or takes it away: given false it clears the stamp and resets the mask and value, given true it recomputes the footprint through a virtual at `+0x130` and writes it back. Everything that appears on the map goes through it |
| where the writing happens | `ItemRegion.cpp` | **known:** `0x6C3350` holds both halves - `0x6C3FD0` clears an object out of the cell array and `0x6C4060` writes it in, `cell = (cell & mask) | value` with the size and the low bits taken as the larger of the two |
| map objects | `objects.cpp`, `objectsMgr.cpp` | **known:** position as two floats at `+0x54` and `+0x58`, and a stamp at `+0x150`. The stamp holds a keep-mask at `+0x14`, the value it writes into the cell array at `+0x18`, and its own position as ints at `+0x24` and `+0x28`. Three of those agreeing is a signature nothing else in the heap answers to |
| characters | `Y2KKIChar.cpp` | **read:** the class every soldier is. The sight range is not a field of it - giving a soldier binoculars changes only his inventory |
| vehicles | `Y2KKIUnit_*.cpp` | one file each: `HUMMER`, `T80`, `HIND`, `SHILKA`, twenty-odd of them. **known:** a Hummer's object class is `0x7DDAB8` |
| animals | `Y2KKIAnim_*.cpp` | `Antilope`, `Bear`, `Cow`, `Deer`, `Horse`, `Hyaene`, `Tiger`, `WildDog`, `Wulf`. **guess:** the tiger is among the content that ships and is never seen |
| the unborn knight | `Y2KKIChar_UnbornKnight.cpp` | a character class of its own, for something the campaign appears never to place |

## Players and parties

| class | file | what is known |
|---|---|---|
| a party | `Y2KKIPlayer.cpp` | **read:** vtables at `0x7CC408`, `0x7CE1E4`, `0x7CE67C` share its methods, so several kinds of party derive from it |
| the player's party | `Y2KKIUIPlayer.cpp` | **known:** vtable `0x7CFE38`, installed at `0x5D7F53`, and exactly one of it in a mission. It holds no party number anywhere in its first kilobyte - what it holds at `+0x78` is a pointer to an array of its own units, six and then zeros, which is the squad along the bottom of the screen. Read one of those and its stamp says which party the player is |
| the computer | `Y2KKIComputerPlayer.cpp` | **guess:** the AI side of a party |
| a network player | `Y2KKINetworkPlayer.cpp` | **guess:** a party driven from another machine |

**known:** the cell array gives each unit the number of its party in bits
`0x00000F00`. One class of unit object turns up under four different numbers, so
the number is the party and the class is the type.

**known:** which number the player is can be read rather than assumed - go
through the player's party object to its units and ask one of them. It has been
2 in all three missions looked at so far, but the map window now reads it each
time instead of trusting that.

## The interface

`quellui_mission` has 35 files, `quellui_bunker` 72, `quellui_start` 21 and
`quellui_editor` 138 - one file per panel, named after what it shows.

| class | file | what is known |
|---|---|---|
| the multiplayer statistics | `MissionMPStatisticPanel.cpp` | **read:** at `0x4D9520`. **guess:** the empty column down the right of a mission entered from outside, which a single player has never seen |
| the multiplayer waiting room | `MissionMPWaitingPanel.cpp` | **read:** at `0x4D9D90` |
| the callbacks | `Callbacks.cpp` | **known:** `0x4460EC` asks whether the game is a network game, twice: the byte at `[0x8739BC]+0x600`, or a session object at `0x875AA4` with a byte at `+0x84`. **known:** both read 0 in a mission loaded from outside, and the interface is wrong anyway, so neither decides it |

## Reading files

Four classes, and between them they explain how everything in this game is
stored.

| class | file | what is known |
|---|---|---|
| a stream | `ReadStream.cpp` | **read:** `0x74EF10` and two more; the base every reader derives from |
| a file | `Win32_FileReadStream.cpp` | **read:** `0x74FAF0` and five more; a plain file on disk |
| an archive member | `ZipReadStream.cpp` | **read:** `0x615590`, `0x616030`, `0x616120`; a member of a `.ubn`, which is a zip |
| a compressed stream | `InflateReadStream.cpp` | **known:** `0x74E4F0` and three more. **known:** the game carries zlib 1.1.3 statically - both banners are in the exe, `deflate 1.1.3 Copyright 1995-1998 Jean-loup Gailly` and `inflate 1.1.3 Copyright 1995-1998 Mark Adler` - and the landscape reader calls `inflateInit2` with 15 window bits at `0x77AEE0`, `inflate` at `0x77AF00`, `inflateEnd` at `0x77AD80`. Plain zlib, nothing of the game's own |

That last one settles a guess in [missions.md](missions.md): the compressed
chunks of a `.mis` are ordinary zlib streams at the default window size, which
is why Python's `zlib` reads them without argument.

The landscape serialiser itself is `Y2K_LS_Serialize.cpp` - `0x681850`,
`0x681950`, `0x681BB0`, `0x682050` and three more - and it is the file that
would finish the mission format. `0x681BB0` is the one that decompresses;
the field-by-field reading is in its neighbours.

## The application and DirectX

| class | file | what is known |
|---|---|---|
| the application | `DXAppMain.cpp` | **known:** the main loop is `0x627C10`. It times frames with `GetTickCount`, and when drawing a frame returns `DDERR_SURFACELOST` it clears a byte at `+0x84` and goes round again rather than treating it as an error (`0x627DAA`) |
| DirectDraw | `DXAppDirectDraw.cpp` | **known:** `0x624B80` builds or restores the surfaces and reports its failures as line 236, which is the error seen on a first start. It already forgives one DirectDraw error, `DDERR_NOEXCLUSIVEMODE`, and returns success; `DDERR_SURFACELOST` is not forgiven |
| Direct3D | `DXAppDirect3D.cpp` | the device, the z-buffer and the texture formats, all of which the log announces at startup |
| DirectSound | `DXAppDirectSound.cpp` | never looked at |
| the error names | `ErrorHandler.cpp` | **known:** `0x651E60` turns an HRESULT into the name the log prints, which is what `decode_error.py` reproduces |

## Data and scripts

| class | file | what is known |
|---|---|---|
| the item library | `Y2KKIObjectLibrary_DatSet.cpp` | **known:** reads `Data.set`, whose first field is the trade value |
| item settings | `Y2KKIObjectSettings.cpp` | **known:** the trade value is member `+0x4C` |
| the trader | `Y2KBunkerHaendler.cpp` | **known:** wants more than 1.2 times what he gives; the factor and tolerance come from the constructor at `0x524440` |
| mission scripts | `Y2KMissionSkriptLibrary.cpp`, `Y2KSkriptList.cpp` | never looked at; this is where the unread 80 % of a `.mis` is interpreted |
| unit behaviour | `quellscript`, 23 files | one per order: `ScriptAttack`, `ScriptClimb`, `ScriptGetIn`, `ScriptPickUp`, `ScriptFernglas`. **known:** `Fernglas` at `0x58FC60` and `0x58FCC0` is the *act* of looking through binoculars, not the passive sight range |
| saving the landscape | `Y2K_LS_Serialize.cpp` | never looked at; the way to finish the `.mis` format |
| terrain generation | `Y2K_LS_TerrainGenerator.cpp` | never looked at; what `TexGen.dat` feeds |
| the weather | `Y2KWeather.cpp` | never looked at |
| the random numbers | `synchedrand.cpp` | **guess:** a shared sequence, so a replay and a network game stay in step |

## The one that keeps getting away

Units are in the cell array only where the player can see them - measured, not
assumed: `map_bits.py --watch` counts them appearing and disappearing as the
party moves. The mechanism that does it is now known to be `0x57C110`, the
switch above. What is not known is who calls it for that reason.

Four attempts have gone into this and each failed differently, which is worth
writing down so the fifth starts somewhere new:

* the sight range is not a field of the character - giving a soldier binoculars
  changes only his inventory, measured with the noise filtered out
* it is not in `Data.set` - the night vision gear and the binoculars carry a
  trade value and a size and nothing else
* the exe does not name either item, so whatever grants the bonus works by
  index
* `Y2KKIChar_ScriptFernglas.cpp` is the *act* of looking through binoculars,
  an order like climbing or picking something up, not the passive range

The callers of `0x57C110` that have been looked at are a character being put on
the map and taken off it - placement, not sight. Somewhere there is another
caller, or a per-frame pass over the units that decides. That is where to
start.

## Where to look next

* **the sight range** - not in the character object and not in `Data.set`. The
  binoculars script is the act, not the stat, so what is left is the code that
  decides what a unit can see.
* **the mission format** - `Y2K_LS_Serialize.cpp` reads and writes exactly what
  `mis.py` cannot.
