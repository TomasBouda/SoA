# Cheats and console commands

Pulled out of the string table in `soa.exe` (offset around `0x45D054` in version
1.1.2.178). Verified in all four available builds of the exe — the original
1.1.0.71 with SecuROM, the unlocked 1.1.0.71, 1.1.2.177 and the deployed
1.1.2.178. The patch did not remove them.

## Typing them in

Press **Enter** during a mission. A line opens that serves both as the chat and
as the console — in the key list that action is called `CHAT`.

The game answers with the messages `Cheat [%s] activated.` / `deactivated.` /
`succeeded.` / `failed.`, so it is possible to tell whether the code worked.

## Cheats

| code | effect |
|---|---|
| `immortalone` | invulnerability |
| `endlessmunition` | endless ammunition |
| `hittingandhealing` | hits and healing |
| `winmission` | instant mission victory |
| `speedhack` | speeds the game up |
| `quitter` | ends the mission |
| `sfxon` | turns the sound effects on |
| `sfxoff` | turns the sound effects off |
| `sfxdebug` | not mentioned anywhere else; it sits in the same table |

They live in a table of their own at `0x85CF10`, thirteen records of 0x6C bytes:
the name at the start of the record, and at `+0x64` the index the dispatcher
takes with `+0x68` saying whether an argument follows.

| # | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| | `quitter` | `hittingandhealing` | `endlessmunition` | `immortalone` | `winmission` | `speedhack` |

| # | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|
| | `kick` | `kickn` | `playerlist` | `nick` | `sfxon` | `sfxoff` | `sfxdebug` |

`kick`, `kickn` and `nick` are the ones with an argument.

The handler is at `0x5ECA70` - a thiscall taking a `tsString` by value, the same
shape as the base cheat dispatcher at `0x52F4A0`. It matches the typed text
against the table itself, so one call with the whole line is all it takes. It
ends in `ret 0x10`, so it disposes of the string; unlike the base dispatcher,
nothing has to be pushed after it.

The object it runs on is the mission itself. No global holds it - the base
cheats have theirs in `0x8759D4`, this one is only ever reached through its
vtable. So the launcher finds it the other way round: it walks the memory the
game allocated for itself and looks for what the constructor at `0x5E7B70`
writes into a mission - `0x7D0568` at the start of the object and `0x7D0564` at
`+8`, because the class inherits twice. The neighbouring `0x7D0560` is a
different class, a four-byte object the game builds while a mission loads
(`0x5E791C`), so looking for that one finds nothing usable. The members the
game itself reads on its way to the cheats (`+0x250`, `+0x260`, `+0x270`) have
to be pointers into readable memory as well.

That is what the console window in the launcher does, so these cheats can be
sent from outside like the base ones - see
[architecture.md](architecture.md#the-command-console).

## Multiplayer commands

They live in the same table but are not cheats:

| command | purpose |
|---|---|
| `kick` | kick a player |
| `kickn` | kick a player by number |
| `playerlist` | list the players |
| `nick` | change the nickname |

## Base cheats

They are typed the same way, but on the base screen. In the exe they form a
regular array of structures with a stride of 0x10C starting at `0x446DB8`
(version 1.1.2.178) — 15 items.

| code | effect | internal name |
|---|---|---|
| `soldierspawn` | a new character | `BUNKER_CHEAT_CREATE_CHARACTER` |
| `showtrader` | a trader with all the gear and vehicles | — |
| `allvehicles` | one vehicle of every kind | — |
| `equipment` | creates equipment (takes an argument) | `BUNKER_CHEAT_CREATE_EQUIPMENT(%s)` |
| `vehicle` | creates a vehicle (takes an argument) | `BUNKER_CHEAT_CREATE_VEHICLE(%s)` |
| `mission` | picks which mission the bunker will start (takes an argument) | `BUNKER_CHEAT_MISSION(%s)` |
| `quitter` | quits | `BUNKER_CHEAT_QUIT` |
| `getsetting` | reads a setting | — |

### The argument belongs in brackets

**This is the thing that made `vehicle` and `equipment` "not work".** They are
typed as

    vehicle(14)
    equipment(45)
    mission(3)

not as `vehicle 14`. The code checks it literally — after the cheat name it
compares the first character with `0x28`, that is `(`:

```
0052F533  cmp  byte ptr [ecx], 0x28   ; a '(' must follow
0052F536  jne  0x52F818               ; otherwise it ends
```

With the bracket missing it jumps to `0x52F818`, where it only cleans up the
strings and the function ends — **without any message at all**. From the
outside it looks as if the code had not been typed or as if the cheat did not
exist. The text between the brackets is then read with `sscanf` and the format
`%d`, so it has to be a number; `vehicle(T55)` fails, as an old log shows.

The format of the log messages gave this shape away the whole time:
`Cheat BUNKER_CHEAT_CREATE_VEHICLE(0) succeeded.` is exactly what gets typed.

The cheats without an argument — `quitter`, `soldierspawn`, `showtrader`,
`allvehicles` — take no brackets.

### Nothing has to be turned on

We looked for whether the cheats sit behind a switch. They do not: there is no
message about disabled cheats in the exe, nor a flag that would enable them.
The last two words of every structure are the ordinal number and a **"takes an
argument" flag**:

| code | index | takes an argument |
|---|---|---|
| `quitter`, `soldierspawn`, `showtrader`, `allvehicles` | 0, 1, 2, 14 | no |
| `getsetting`, `equipment`, `vehicle`, `mission` | 3–6 | yes |
| `ronny` … `sebastian` | 7–13 | yes |

That explains two earlier failures:

* **`mission` without a number does nothing visible.** It expects an argument
  in brackets, just like `vehicle` and `equipment`.
* **The developer codes expect an argument too**, and in brackets as well —
  they all read `%d` through the same `sscanf`.

And watch out for two mix-ups: the code is called `allvehicles`, not
`vehicles`, and the base cheats work **only on the base screen** — not during a
mission and not in the main menu.

### What `mission` actually does

It picks the mission, it does not start it. The handler reads the number,
checks the object in the global `0x8759CC` and calls `0x525B70` on it
(`0x52FD86`), which is what the bunker's own mission list writes when a mission
is chosen. Then *Start mission* launches whichever one was picked.

The briefing beside the button does **not** redraw, so the screen still
describes the mission that was there before and it looks as if nothing
happened. It has: pressing start goes to the mission that was asked for.

That makes the way into a mission from outside two steps, one of which still
needs a click: send `mission(4)`, then press start. Once inside,
`quicksave` and `quickload` take over.

### The developer codes

Seven names lie in the same table: `ronny`, `enrico`, `martin`, `alex`, `jan`,
`nils`, `sebastian`. They correspond to the trace flags `TRACE_RONNY`,
`TRACE_ENRICO`, `TRACE_MARTIN`, `TRACE_ALEX`, `TRACE_ALEX2`, `TRACE_JAN`,
`TRACE_NILS` and `TRACE_SEBASTIAN` — so every member of the team left their own
code in the finished game.

All fifteen have their own handler; the parser picks them through a jump table
at `0x535BE0`, indexed by the ordinal number from the cheat table:

| # | code | handler | # | code | handler |
|---|---|---|---|---|---|
| 0 | `quitter` | `0x52F866` | 8 | `enrico` | `0x530A76` |
| 1 | `soldierspawn` | `0x52F8AF` | 9 | `martin` | `0x53337E` |
| 2 | `showtrader` | `0x52FD86` | 10 | `alex` | `0x533645` |
| 3 | `getsetting` | `0x52FDDF` | 11 | `jan` | `0x53366C` |
| 4 | `equipment` | `0x52F975` | 12 | `nils` | `0x533693` |
| 5 | `vehicle` | `0x52FA2A` | 13 | `sebastian` | `0x53558A` |
| 6 | `mission` | `0x52FAFD` | 14 | `allvehicles` | `0x535856` |
| 7 | `ronny` | `0x530004` | | | |

The gaps between the addresses give away how much work stands behind each code:
`ronny`, `enrico`, `martin` and `sebastian` have hundreds of bytes to kilobytes
of code, while `alex`, `jan` and `nils` have some forty each. Those three only
read the number from the brackets and jump to the common end — they are
leftovers from debugging and do nothing.

**What exactly the others do is not verified.** At first I assumed they turn
tracing on; later it turned out that the trace categories are command line
arguments (see [architecture.md](architecture.md)). So these cheats do
something else, or they toggle the same categories at run time.

Sebastian is the one whose disk shows up in every path in the sources:
`D:\Sebastian\oldPC\C\Dev\builds\unborn\y2k_source\`.

## Cheat arguments

**The argument is an ordinal number, not a name.** Confirmed from
`tracefile.log`:

```
Info: Cheat BUNKER_CHEAT_CREATE_VEHICLE(0)  succeeded.
...
Info: Cheat BUNKER_CHEAT_CREATE_VEHICLE(22) succeeded.
Info: Cheat BUNKER_CHEAT_CREATE_VEHICLE(T55)      failed.
Info: Cheat BUNKER_CHEAT_CREATE_VEHICLE(UNIT_T55) failed.
```

The 0–22 series comes from `allvehicles`, which internally calls the same cheat
for every index. The indexes follow the order of the items in the object
libraries.

### `vehicle(0-22)`

Order taken from `data/ObjData/Units.olb`. The names are the ones the game shows to the player — next to the identifier the library also holds a reference into a text table.

| # | identifier | name in game |
|---|---|---|
| 0 | `UNIT_HUMMER` | HUMVEE |
| 1 | `UNIT_URAL` | URAL |
| 2 | `UNIT_FLOGGER` | MiG-27 |
| 3 | `UNIT_2S3` | HOW 2S3 |
| 4 | `UNIT_BTR80` | APC BTR |
| 5 | `UNIT_BM21` | BM-21 |
| 6 | `UNIT_BMP1` | ICV BMP |
| 7 | `UNIT_BULL` | BULL |
| 8 | `UNIT_HIND` | Mi-24 HIND |
| 9 | `UNIT_HIP` | Mi-8 HIP |
| 10 | `UNIT_FULCRUM` | MiG-29 |
| 11 | `UNIT_MD500` | MD-500 |
| 12 | `UNIT_OH58` | OH-58 |
| 13 | `UNIT_T80` | MBT T-80 |
| 14 | `UNIT_T55` | MBT T-55 |
| 15 | `UNIT_SHILKA` | AD SHILKA |
| 16 | `UNIT_M1A1` | MBT M1A1 |
| 17 | `UNIT_VULCAN` | AD M163 |
| 18 | `UNIT_WOLF` | WOLF |
| 19 | `UNIT_GAZ` | GAZ |
| 20 | `UNIT_GAZ2` | GAZ A |
| 21 | `UNIT_RAGER` | RAGER |
| 22 | `UNIT_EAGLE` | F-15 Eagle |
### `equipment(0-132)`

Order taken from `data/GameData/Data.set`, 133 items in total.

**Careful: the `equipment` cheat does not take this position.** It takes the item number stored inside the record, and the two differ - `SET_M60` is thirty-ninth here but has number 2. The numbers that actually work are in the launcher catalog (`tools/gen_catalog.py`, see [dataset-format.md](dataset-format.md)); the order below is only good for orientation.

**Small arms, gear and whole vehicles** (54):

| # | identifier | name in game |
|---|---|---|
| 39 | `SET_M60` | M60 |
| 40 | `SET_AK74` | AK74 |
| 41 | `SET_BERETTA` | Beretta |
| 42 | `SET_UZI` | UZI |
| 43 | `SET_MP5` | MP5 |
| 44 | `SET_RPK` | RPK |
| 45 | `SET_RPG7` | RPG7 Bazooka |
| 46 | `SET_SA7` | SA7 Grail |
| 47 | `SET_DRAGUNOV` | Dragunov |
| 78 | `SET_BOMBENAUFHAENGUNG` | ngung Bombe |
| 79 | `SET_ARMBRUST` | Crossbow |
| 80 | `SET_SHOTGUN` | Shotgun |
| 82 | `SET_MESSER` | Throwing Knife |
| 83 | `SET_HANDGRANATE` | Hand Grenade |
| 84 | `SET_MOLOTOW` | Molotov |
| 91 | `SET_NEBELGRANATE` | Nebelgranate |
| 92 | `SET_BETAEUBUNGSGRANATE` | ubungsgranate!TRES_EQUIPMENT_BETAEUBUNGSGRANATE!TRES_EQUIPMENT_BETAEUBUNGSGRANATE |
| 94 | `SET_M79` | M79 |
| 95 | `SET_2S3` | HOW 2S3 |
| 96 | `SET_BM21` | BM-21 |
| 97 | `SET_BMP1` | ICV BMP |
| 98 | `SET_BTR80` | APC BTR |
| 99 | `SET_BULL` | BULL |
| 100 | `SET_FLOGGER` | MiG-27 |
| 101 | `SET_FULCRUM` | MiG-29 |
| 102 | `SET_HIND` | Mi-24 HIND |
| 103 | `SET_HIP` | Mi-8 HIP |
| 104 | `SET_HUMMER` | HUMVEE |
| 105 | `SET_MD500` | MD-500 |
| 106 | `SET_M1A1` | MBT M1A1 |
| 107 | `SET_OH58` | OH-58 |
| 108 | `SET_SHILKA` | AD SHILKA |
| 109 | `SET_T55` | MBT T-55 |
| 110 | `SET_T80` | MBT T-80 |
| 111 | `SET_URAL` | URAL |
| 112 | `SET_VULKAN` | VULCAN |
| 113 | `SET_WOLF` | WOLF |
| 114 | `SET_RAGER` | RAGER |
| 115 | `SET_GAZ` | GAZ |
| 116 | `SET_GAZA` | Gaz 69 A |
| 117 | `SET_EAGLE` | F-15 Eagle |
| 119 | `SET_NACHTSICHTGERAET` | Night Vision Gear |
| 121 | `SET_FERNGLAS` | Binoculars |
| 122 | `SET_PANZERMINE` | Tank Mine |
| 123 | `SET_ALUKOFFER` | Case |
| 124 | `SET_SPRENGSATZ` | Explosive |
| 125 | `SET_MEDIKIT` | Medipack |
| 126 | `SET_CONTROLCHIP` | Controlchip |
| 127 | `SET_FLY` | FLY Pills |
| 128 | `SET_BOX` | Box |
| 129 | `SET_SUBSURFACEMINE` | Subsurfacemine |
| 130 | `SET_MINENKOEDER` | Mine Bait |
| 131 | `SET_PEILSENDER` | Bug |
| 132 | `SET_CRAWLERSENDER` | Crawler Sender |

**Weapon systems of vehicles and helicopters** (40):

| # | identifier | name in game |
|---|---|---|
| 48 | `SET_HUMVEE_M60` | HUMVEE M60 |
| 49 | `SET_HUMVEE_PLAMJA` | !HUMVEE Plamja Granatwerfer (40mm) |
| 50 | `SET_HUMVEE_TOW` | HUMVEE TOW |
| 51 | `SET_BTR80_MK` | 14,5mm Maschinenkanone |
| 52 | `SET_BMP1_73MMGUN` | 73mm Kanone |
| 53 | `SET_BMP1_ROHRMG` | rohrparalleles MG |
| 54 | `SET_BMP1_AT2` | AT2 Startschiene |
| 55 | `SET_VULCAN_MK` | Gattling Gun |
| 56 | `SET_T55_125MMGUN` | 125mm Kanone |
| 57 | `SET_T55_ROHRMG` | rohrparalleles MG |
| 58 | `SET_T55_TURMMG` | Turmmg |
| 59 | `SET_T80_125MMGUN` | 125mm Kanone |
| 60 | `SET_T80_ROHRMG` | rohrparalleles MG |
| 61 | `SET_T80_FLAMMENWERFER` | T80 Flammenwerfer |
| 62 | `SET_M1A1_125MMGUN` | 125mm Kanone |
| 63 | `SET_M1A1_ROHRMG` | rohrparalleles MG |
| 64 | `SET_M1A1_GRANATWERFER` | M1A1 Granatwerfer (40mm) |
| 65 | `SET_BM21_MLRS` | Katjuscha MLRS |
| 66 | `SET_2S3_152MMGUN` | 152mm Kanone |
| 67 | `SET_2S3_TURMMG` | Turmmg |
| 68 | `SET_SHILKA_MK` | 4x 14,5mm Machinenkanone |
| 69 | `SET_HELI_UV7` | UV-7 Launcher |
| 70 | `SET_HELI_TOW` | TOW Launcher |
| 71 | `SET_HELI_SA7` | SA-7 Launcher |
| 72 | `SET_HELI_AT6` | AT6 Launcher |
| 73 | `SET_HELI_UV32` | UV-32 Launcher |
| 74 | `SET_HELI_UB20` | UB-20 Launcher |
| 75 | `SET_HELI_AT2_4FACH` | AT2 Llauncher |
| 76 | `SET_HELI_AT6_4FACH` | 4x AT6 Launcher |
| 77 | `SET_HELI_BORDMG` | Gattling Gun |
| 81 | `SET_T80_TURMMG` | Turmmg |
| 85 | `SET_BTR80_NEBELWERFER` | Nebelwerfer |
| 86 | `SET_T55_NEBELWERFER` | Nebelwerfer |
| 87 | `SET_T80_NEBELWERFER` | Nebelwerfer |
| 88 | `SET_M1A1_NEBELWERFER` | Nebelwerfer |
| 89 | `SET_UNBORN_MINIGUN` | Unborn Minigun |
| 90 | `SET_UNBORN_ROCKETLAUNCHER` | Unborn Rocketlauncher |
| 93 | `SET_HELI_MK` | Hubschrauber MK |
| 118 | `SET_SCHUTZWESTE_LEICHT` | Schutzweste leicht |
| 120 | `SET_SCHUTZWESTE_SCHWER` | Schutzweste schwer |

**Ammunition** (39):

| # | identifier | name in game |
|---|---|---|
| 0 | `SET_MUN_MG` | 7,62mm x 50 |
| 1 | `SET_MUN_AK74` | 5,45mm x 30 |
| 2 | `SET_MUN_9MM` | 9mm x 20 |
| 3 | `SET_MUN_SHOTGUN` | 22mm Shells x 10 |
| 4 | `SET_MUN_ARMBRUST` | cher |
| 5 | `SET_MUN_MK` | 14,5mm x 250 |
| 6 | `SET_MUN_PLAMJA_BRAND` | Plamja Granate Brand (40 mm) TRES_EQUIPMENT_AMMO_PLAMJA_BRAND%TRES_EQUIPMENT_AMMO_PLAMJA_BRAND_HINT |
| 7 | `SET_MUN_PLAMJA_HE` | Plamja Granate HE (40mm) |
| 8 | `SET_MUN_73MMGUN_HEFRAG` | Panzergranate HE-FRAG (73mm) |
| 9 | `SET_MUN_73MMGUN_HEAT` | Panzergranate HEAT (73mm) |
| 10 | `SET_MUN_125MMGUN_APSFDS` | Panzergranate APSFDS (125mm) TRES_EQUIPMENT_AMMO_125MM_APFSDS%TRES_EQUIPMENT_AMMO_125MM_APFSDS_HINT |
| 11 | `SET_MUN_125MMGUN_HE` | Panzergranate HE-FRAG (125mm) TRES_EQUIPMENT_AMMO_125MM_HEFRAG%TRES_EQUIPMENT_AMMO_125MM_HEFRAG_HINT |
| 12 | `SET_MUN_125MMGUN_HEAT` | Panzergranate HEAT-FS (125mm) |
| 13 | `SET_MUN_152MMGUN_HE` | Artilleriegranate HE (152mm) |
| 14 | `SET_MUN_152MMGUN_NEBEL` | Artilleriegranate Nebel (152mm) |
| 15 | `SET_MUN_152MMGUN_LEUCHT` |  (152mm) TRES_EQUIPMENT_AMMO_152MM_LEUCHT%TRES_EQUIPMENT_AMMO_152MM_LEUCHT_HINT |
| 16 | `SET_MUN_152MMGUN_MINE` | Artilleriegranate Mine (152mm) |
| 17 | `SET_MUN_RPG7` | PG7 M HEAT |
| 18 | `SET_MUN_SA7` | FLK SA7 Grail |
| 19 | `SET_MUN_BM21_HEFRAG` | BB Rakete HE-FRAG (122mm) |
| 20 | `SET_MUN_BM21_RAUCH` | BB Rakete Rauch (122mm) |
| 21 | `SET_MUN_BM21_MINE` | BB Rakete Mine (122mm) |
| 22 | `SET_MUN_TOW` | TOW HEAT |
| 23 | `SET_MUN_AT2` | AT2 |
| 24 | `SET_MUN_AT6` | AT6 |
| 25 | `SET_MUN_UB20` | 80mm AS |
| 26 | `SET_MUN_UV32` | 57mm AS |
| 27 | `SET_MUN_250KGBOMBE` | 250kg Mehrzweckbombe |
| 28 | `SET_MUN_500KGBOMBE` | 500kg Mehrzweckbombe |
| 29 | `SET_MUN_FLAMMENWERFER` | Kanister Flammenwerfer |
| 30 | `SET_MUN_MESSER` | Knife |
| 31 | `SET_MUN_HANDGRANATE` | Handgrante (Mun) |
| 32 | `SET_MUN_MOLOTOW` | Molotow Cocktail (Mun) |
| 33 | `SET_MUN_PANZERNEBELGRANATE` | Panzernebelgranate$TRES_EQUIPMENT_AMMO_NEBELGRANATE40MM)TRES_EQUIPMENT_AMMO_NEBELGRANATE40MM_HINT |
| 34 | `SET_MUN_DRAGUNOV` | Sniper Munition |
| 35 | `SET_MUN_UNBORN_MINIGUN` | Unborn Rounds |
| 36 | `SET_MUN_UNBORN_ROCKETLAUNCHER` | Unborn Rocket |
| 37 | `SET_MUN_NEBELGRANATE` | Nebelgranate (Mun) TRES_EQUIPMENT_AMMO_NEBELGRANATE%TRES_EQUIPMENT_AMMO_NEBELGRANATE_HINT |
| 38 | `SET_MUN_BETAEUBUNGSGRANATE` | ubungsgranate (Mun)&TRES_EQUIPMENT_AMMO_BETAEUBUNGSGRANATE+TRES_EQUIPMNET_AMMO_BETAEUBUNGSGRANATE_HINT |
### `mission`

The log holds `Info: Cheat BUNKER_CHEAT_MISSION() succeded.` — so it succeeded
**even without an argument**. With a number it will most likely jump to a
particular mission (the campaign has 13 of them, see below).

### What else the log tells us

`tracefile.log` is valuable in other ways once tracing is on — a single run
showed:

- **missing sounds**: `Sound not found. 'querschlaeger1.wav'` and
  `Sound not found. 'SchussTreffer_Körper_1.wav'` — the second one has an
  umlaut in the name, so it will be an encoding problem, not a missing file
- **a broken path to the avatars**:
  `LoadPNG(filename: 'C:\Game\Multiplayer\Pictures\') failed`
- `VerifyFPU failed` at startup
- dgVoodoo works: both `dgVoodoo HAL` and `dgVoodoo TnL HAL` are enumerated and
  the game runs in 2560 × 1360 × 32 bpp

## A note on the search

The table did not show up in a text dump of the strings even though the codes
are there — it paid off to look for the pattern `immortalone` in the binary
directly and print its surroundings. The neighbouring strings belong to the
same array, so one known code revealed all the others.
