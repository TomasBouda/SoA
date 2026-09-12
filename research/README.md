# Research into the game data

Aside from the working setup — nothing here is needed to play. It is an
examination of what lies in the game data and the tools that can read it.

```
architecture.md            how the game is put together inside — start here
classes.md                 the classes and what is known about each, by hand
map.md                     which code belongs to which source file, by tool
behavior.md                behavioural analysis of the running game (a malware check)
cheats.md                  cheats and console commands
object-ids.md              object identifiers with their ordinal numbers
dataset-format.md          the format of Data.set, the library of gear and ammo
weapons.md                 what every round, weapon and vehicle does in numbers: damage, blast radius, armour, range
trading.md                 what an item is worth and what the trader demands
missions.md                the structure of the mission files (.mis)
editor.md                  the mission editor the game still carries, and how to reach it
saves.md                   what is in a .sav, and the text resources that name it
translation.md             what it would take to translate the game, and what is proven
packaging.md               the three packages and what each may carry
sound-fix.md               the fix for the missing hit sounds
upscale.md                 enlarging the textures, what worked and what did not
tools/trs.py               parser for the text resources (.trs)
tools/dataset.py           parser for Data.set
tools/mis.py               reader for the mission files (.mis)
tools/gen_editor_docs.py   generator of the mission editor reference
tools/gen_ids_doc.py       generator of the identifier lists
tools/gen_weapons_doc.py   writes weapons.md - damage, blast radius, armour, range, out of Data.set
tools/gen_weapons_web.py   the same as one web page with the game's pictures, sortable (the Arsenal artifact)
tools/gen_catalog.py       generator of the launcher catalog (items, names, images)
tools/list_ids.py          prints the identifiers to the console
tools/map_exe.py           maps the code to the original source files
tools/find_units.py        finds the units of a running mission in memory
tools/map_bits.py          what the bits of the map cell array hold
tools/translate.py         reads and writes the text resources, and deploys a translation
tools/read_save.py         reads a save: which mission, which parties, who is in it
tools/diff_save.py         compares two saves and names whose record changed
tools/edit_save.py         finds an item in a save and changes it for another
tools/hud_contrast.py      makes the mission interface easier to read, as loose files
tools/upscale_faces.py     enlarges the portrait sheets, which are 36x50 pixels a face
tools/diff_memory.py       watches one object in the running game across a change
tools/check.py             checks the package still does what it claims
tools/fix_sounds.py        the fix for the missing hit sounds
tools/fix_missing_sounds.py  fills in the sounds that were never shipped
tools/scan_memory.py       searching for values in the memory of the running game
tools/trainer_inject.py    calls the base cheat inside the game process
tools/airstrike_inject.py  calls an air strike on a point of the running mission
tools/play_bot.py          a program that plays: the squad, the enemies, the orders, a first plan
tools/ui_inject.py         the mailbox: what is under a screen point, orders, the matrices - asked of the game
tools/menu_bot.py          clicks the game from its menus into a saved game
tools/mission_cheat.py     the mission cheats (endlessmunition ...) and loading a save, with no menu
tools/add_sounds.py        puts sounds of our own into sounds.ubn, by hand, so the game finds them by name
tools/launch_game.ps1      starts the game through the launcher, windowed, and waits for soa.exe
tools/radio_clip.py        makes the radio call the launcher plays with it
tools/decode_error.py      translates the HRESULT codes from tracefile.log
tools/extract_icon.py      pulls the icon out of a PE file into an .ico
tools/monitor-run.ps1      behavioural analysis of the running game
tools/build-package.ps1    builds the standalone package that runs without a sandbox
tools/launcher/App.cs      the launcher in C#, sets the resolution from the desktop
tools/launcher/Saves.cs    the saves window: what is in a save, without loading it
tools/launcher/Catalog.cs  the base catalog for adding gear and vehicles
tools/launcher/Patches.cs  the patches window: the changes in soa.exe, each with a box to switch it
tools/launcher/Keys.cs     the keys window: every action the game can bind, edited into the registry
tools/gen_keys_cs.py       writes launcher/KeysData.cs, the 67 actions out of the exe and TRES_ACTIONS.trs
tools/sandbox/             verification of the package on clean Windows
tools/upscale_textures.py  enlarging the object textures
tools/upscale_terrain.py   enlarging the terrain textures
tools/upscale_details.py   enlarging the detail sheets (roads, tracks)
tools/import_texture.py    taking in repainted base textures from a model
tools/esrgan.py            Real-ESRGAN with no dependency on basicsr
editor-scripting.md        the generated mission editor reference
```

## The mission editor

The game ships a full editor reachable from the main menu, and no documentation
for it was ever released. [`editor-scripting.md`](editor-scripting.md) is an
attempt to reconstruct one from the game data: **20 trigger types**, **42
events** and **21 script building blocks**, 26 of them with a human description
and their parameter types.

It is assembled from two sources that complement each other:

- the class names in `soa.exe` (`CY2KKITrigger_*`, `CY2KKIEvent_*`) give the
  **complete list** but say nothing about what an element does on their own
- the text resources of the editor hold messages such as *"You have deleted an
  Object, that you have used in a "move unit"-event as a parameter"*, which
  **name the element in human terms and give away the parameters it takes**

To regenerate after a change in the data:

```bash
python tools/gen_editor_docs.py
```

## The .trs format

The text resources are a simple container from the same family as the saves
(`.sav`) and the GUI layouts (`.lay`) — they differ only in the first byte of
the magic GUID:

```
16 B   magic GUID (starts with 0x40 in a .trs)
u32    version (2)
u32    record count
        then for every record:
u32    ordinal number
str    resource id ("TRES_...")
str    German text (always "leer" in the English build)
str    text
str    reserve

str = 1 B length + bytes (latin1)
```

To print any resource:

```bash
python tools/trs.py ../_patched/data.ubn TRES_EDITOR
python tools/trs.py ../_patched/data.ubn TRES_OBJECTS
```

## What turned up along the way

- **Air support.** The game carries models of the MiG-23 (`Flogger`) and the
  MiG-29 (`Fulcrum`), and they are not decoration: a plane with bombs in the
  hangar enables the *Air Strike* button of the mission context menu, see
  [architecture.md](architecture.md). You never fly it, it flies for you.
- **UnbornKnight.** Among the characters there is a model called `UnbornKnight`
  and among the events `KnightCamouflageState` — *"change knight camouflage
  state"*. So it is a real game entity with camouflage, not a forgotten
  leftover. "Unborn" was the code name of the project, the paths in the sources
  lead into `y2k_source\unborn`.
- **German developer comments.** The saved games still hold the names of the
  trigger groups from the editor exactly as the authors named them: *"tiere
  allg"*, *"baer b woelfen + Scamps"*, *"Haendler + Dorfbewohner"*, *"woelfe
  bei haendler"*.
- **Cheats.** The complete table is in [cheats.md](cheats.md) — they are typed
  with Enter during a mission, the patch did not remove them.
- **Animations from the demo.** `AniData` holds `Conklave_Frau_demo.adt` and
  `Nitro_Mann_demo.adt` next to the final versions.

## Where next

A running list of ideas is in [TODO.md](TODO.md) — from machine map generation
through the command console to the unused content.
