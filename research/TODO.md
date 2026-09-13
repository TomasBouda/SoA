# What to look into next

A running list. None of it is needed to play. Roughly ordered by what would pay
off most for the least work.

## The mission format, where mis.py stopped

[tools/mis.py](tools/mis.py) reads the header, the terrain and the object table;
about 80 % of a campaign mission is still unmapped, see
[missions.md](missions.md).

- [~] **The units, characters and scripts.** Partly mapped now: the tail opens
      with the camera's matrix, then the parties - whose records shrink by eight
      bytes each in turn, which is a triangular table of who stands with whom -
      and then the characters at a nearly fixed stride, each a name followed by
      a zero, eight `0xFF` bytes and a run of numbers. `mis.py --people` lists
      them. Which number is which skill is **not** known and the alignment
      differs between the test and campaign missions, so nothing is labelled.
      See [missions.md](missions.md). The rest of the original entry stands:
- [ ] **The units, characters and scripts.** That is the whole remaining tail,
      2 to 3 MB per campaign mission. Start from
      [Melkij's PHP parser](https://github.com/Melkij/soa-game-revers-eng) - it
      already reaches the script sections and its `struct/` names the fields.
- [ ] **Which zlib chunk is which layer.** A 75x75 map carries 265 chunks of
      32 KB. Somewhere in there are the heightmap, the texture assignment and
      the passability grid. Finding the heightmap gives a map preview for free -
      render it to PNG and the whole campaign can be looked at from above.
- [ ] **Decode the object record.** The 44 bytes are read, but only the
      coordinates are certain. The `u32` attributes decide which library the
      index belongs to; cross-checking against [object-ids.md](object-ids.md)
      would turn the table into "this mission places 30 pine trees and 4 tanks".
- [ ] **Find the unused content.** With the object tables parsed this becomes a
      set operation: every index every mission places, subtracted from the
      libraries. What is left is content that shipped and is never seen -
      `UnbornKnight`, the tiger, the animations from the demo.
- [ ] **Unpack `missions.ubn` into a folder** so the editor can open the
      campaign missions.

## Characters: ranks, skills and experience

What is known is in [architecture.md](architecture.md); the promotion rule is
not.

- [ ] **What triggers a promotion.** Watch the rank field
      (`+0x24` of the character record) with
      [tools/scan_memory.py](tools/scan_memory.py) across a mission and see what
      moves it - kills, mission completion, or the experience counters.
- [ ] **What the rank affects.** If nothing but the display reads it, say so;
      the way to tell is to raise it in memory and watch accuracy and damage.
- [ ] **What the three counters at `+0x73`, `+0x8D`, `+0xE6` are.** They grow
      only for soldiers who go on missions and grow by nearly the same amount
      for everybody, so they look like participation, not kills. Three counters
      side by side suggests three separate skills.
- [x] ~~**A save inspector.**~~ [tools/read_save.py](tools/read_save.py) and
      the launcher's Saves window read a `.sav` and name the mission, the
      parties in order and the people in it - see [saves.md](saves.md). What
      they do **not** do yet is reach the character records, which is what
      would answer the three questions above; the world past the header has not
      been taken apart.

## Trading

The mechanism is in [trading.md](trading.md); two numbers in it come from the
constructor and may be overwritten.

- [ ] **The per-mission trade factor.** The editor sets a Trade Factor per
      trader, so it lives in the `.mis` - which lands in the mission format work
      above. The default is 1.5; whether the campaign ships something else is
      unknown.
- [ ] **What "Trader Attitude" changes.** The game option (easy / normal / hard)
      most likely writes the tolerance at `+0x0C`, but that is a guess. The
      registry value plus a memory watch settles it.

## Data formats still open

- [ ] **Field 1 of `Data.set`.** The second number of every record, right next
      to the trade value, has its own getter in the same three classes
      (`fld [settings+0x50]`) and no other reader that a byte search finds.
      Values: 6 for most hand weapons, 1 for vehicles, 0 for mounted guns,
      0.75 to 30 for ammunition. Size in the storage? Weight?
- [ ] **The `.sav` container.** The header is understood, and so is enough to
      change a soldier's weapon: **equipment is written as the numbers the
      catalog uses, in plain dwords, and what a character carries lies inside
      the record that opens with his `TRES_` key**. The same numbers appear
      elsewhere in the file - the depot end of a trade changes with him - and
      only the copy inside his record is the one the game reads.
      `tools/edit_save.py --who` walks a character's record and `--find` names
      the owner of every copy.

      What is missing is **where inside the record the inventory begins**. The
      record is not a fixed size; the offset that works for one soldier lands on
      nothing for the rest. The way to it is more controlled pairs: swap a
      weapon on two or three soldiers in turn and see whether the offsets fall
      at a regular stride. See [saves.md](saves.md).
- [ ] **`TexGen.dat`.** Open text, describes how vegetation is scattered by
      height, slope and compass direction. Writing a generator for it would let
      a whole map be planted by script; see [architecture.md](architecture.md).

## Terrain

- [x] ~~**Export the height map from the launcher.**~~ `heightmap` in the
      console writes the terrain of the running mission as a grey picture, and
      it works: a 1201 by 1201 PNG with 92 distinct greys came out of
      Mission 3. That settles what `[world+0x18]` and `[world+0x1C]` are - the
      fine grid, one pixel per map cell, not the coarse 75 by 75 height grid.
      `heightmap(name, low, high)` chooses the file and the bounds.

- [ ] **Import one back.** `LoadHeightMap` needs an object built from the
      parameters first, so it is not a straight call. The editor's
      *Imp. Height Data* does the same job through a panel, which is the door
      to use until the harder call is worked out. A height map made in Python -
      noise, erosion, or real elevation data - would then be a map.
- [x] ~~**Is there a replay system?**~~ **There is.** `replay` in the console
      read the global at `0x874AE0` in a running game and it is not null. The
      object whose absence `EventRecorder` and `Replay` complain about is
      therefore built in the shipped game. What it can do is unknown - the commands
      that drive it need the command tree, which never opens, so the next step
      is finding what that object is and whether recording can be started the
      way everything else here is: by calling it.

## Translating the game

- [x] ~~**Can it be translated at all?**~~ Yes, and with no change to the exe.
      The text is UTF-8 - the game's own German lines say so, and the exe
      converts with code page 65001 - so writing UTF-8 is the whole trick. The
      options screen is translated and renders its diacritics with `soa.exe`
      untouched, and the layout holds: Czech is longer than English and nothing
      overran a panel. See [translation.md](translation.md).
- [ ] **Translate the rest.** 43 files, 3042 records, about 74 standard pages,
      of which 1219 lines are spoken. The plumbing is finished and checked -
      `tools/translate.py --check` reads every resource and writes it back byte
      for byte - so what is left is the writing. `_research/translation/cs.tsv`
      is where it goes.
- [ ] **Dub it.** Each spoken line names its own mp3 in the record, so the
      mapping from text to audio needs no work: 1787 files, 93 MB, under
      `Missions/Campaign/Mission_N/SpeechEN/`. Loose files override, so
      replacing them needs no repacking.
- [x] ~~**Anything baked into the pictures.**~~ The start screen ring is:
      `LAY_START_WELCOMEBUTTONS.lay` gives every button a picture id and no
      text, so the words are painted into the artwork and left in English by
      decision - see [translation.md](translation.md). Whether any other screen
      does the same is still open, and the way to find out is to translate one
      and see what stays English.
- [ ] **Anything baked into the pictures, elsewhere.** Whether a button anywhere
      its label as part of the panel art rather than as a string. The options
      screen had none, which proves nothing about the rest.

## Waiting to be tried

- [x] ~~**Does the game accept an edited save?**~~ **It does** - no checksum, no
      validation, no complaint. The question was only ever which byte to edit,
      and the first answer was wrong: 0x5FA looked like the professor's rifle
      and is not his at all. Writing a Dragunov there produced a soldier holding
      a Dragunov, which read as a success and was not - he had been holding one
      already. An M60 written to the same place changed nothing, and that is
      what exposed it. His weapon lives inside the record that opens with
      `TRES_PROF_DR_SERGEJ_PETROW`; 0x5FA is the depot side of the same swap.

- [x] ~~**Confirm the record boundary with a write.**~~ **Confirmed.**
      `M4_B_rpg.sav` is `M4_B_edit` with an RPG7 written at 0x232E, inside the
      professor's record, and he loads carrying a bazooka. A weapon he could not
      already have had, which is what the previous test lacked.

- [x] ~~**The same in a mission save.**~~ **It works there too.** The professor
      was given a Dragunov in `QuickSave.sav`, three megabytes in, and carried it
      into the mission - so the live object on the map holds no weapon of its
      own. Mission and bunker saves are written identically.

- [x] ~~**Editing an inventory from the launcher.**~~ The Saves window lists
      what everybody carries and swaps one item for anything in the catalog.
      `launcher/Inventory.cs` has the format: each item is a slot, a catalog
      number and an identifier, read backwards from the serialiser's marker,
      and the four slots are the pack, the weapon, ammunition and the vest.

- [x] ~~**The saves window.**~~ Works.
- [x] ~~**The object inspector.**~~ Works, once the double click reached it -
      the pan was capturing the mouse and the image never saw a second click.

## The game while it runs

- [x] ~~**Find out how the console opens.**~~ It does not. The command tree is
      built at startup and the commands carry names, descriptions and typed
      parameters, but no action in the 67-entry input table opens a line, there
      is no layout for a console, no Windows console is allocated and the parser
      is called only from inside its own module. The full command list and the
      evidence are in [architecture.md](architecture.md).
- [ ] **A height map generator - through the editor.** The editor's File menu
      has *Imp. Height Data* and *Exp. Height Data*, which are the same
      operations as the console's `LoadHeightMap` / `SaveHeightMap`. Export the
      height map of an existing mission first to learn the bitmap format, then
      generate one in Python (Perlin noise, erosion, or real DEM data) and
      import it. No console needed.
- [ ] **Importing objects.** *Import Objects* sits in the same menu and the
      console's `ObjectMgr.Load` takes a `string fileName`. That file format
      plus a height map is a whole map generated from a script.
- [x] ~~**A test that says whether anything broke - the half without the
      game.**~~ [tools/check.py](tools/check.py) runs on every build: it
      compares every address the launcher calls or reads against the sixteen
      bytes pinned for it in `addresses.json`, checks that each patch
      signature matches exactly one place and that applying and reverting a
      group gives the file back byte for byte, and that the catalog still
      agrees with `Data.set` and its vehicle numbers have no gaps. Breaking one
      byte of the cheat dispatcher on a copy makes it say so, which is the
      point.
- [x] ~~**The game sometimes hangs when it is closed hard.**~~ Not ours: the
      unpatched game does it too. The focus patch was the obvious suspect,
      since it changes what the window does on `WM_KILLFOCUS` and on
      deactivation, which is the path a hard close goes through - but it
      happens without it, so it is the engine, and it is left alone.
- [x] ~~**The half of the test that needs the game.**~~ `Play.exe -selftest`
      starts the game, waits for the base screen, sends a base cheat with an
      argument and reads back that it took, loads a known mission, reads the
      map and the units out of the objects, sends a mission cheat, quick saves
      and quick loads, then closes the game and writes `selftest.txt`. It goes
      through the launcher's own GameLink rather than a copy, so what is tested
      is what ships - which is the point, since the bug that prompted all this
      was in the launcher and not in the exe.
- [ ] **Drive the game from outside, so a test starts itself.** Every change
      to the launcher now ends the same way: start the game, click through the
      menu, get into a mission, and only then see whether it works. Loading a
      save straight away would cut all of that out, and a fixed save would make
      two runs comparable instead of merely similar. Three leads, cheapest
      first:
the console window can now `quicksave` and `quickload`
      inside a mission, and `mission(number)` picks which mission the bunker
      will start - both checked against the game. What is left is the click in
      between: `mission(4)` selects it but *Start mission* still has to be
      pressed, so the chain from the main menu to a running mission is not
      closed. The button sends a message like every other; finding which one,
      and how to put it on the queue, would close it - and that same queue is
      the polite way to ask for a quick load, which currently runs on a thread
      of its own.
      One attempt is already spent: `0x511F10` looked like the button and is
      the application setting itself up, so calling it starts the game over -
      see [architecture.md](architecture.md) for why the reasoning looked sound.
      Where the search stopped: the bunker object in the global `0x8759CC`
      carries a couple of dozen methods, called from the screen code around
      `0x419F00` to `0x41C200` - `0x5251C0`, `0x525100`, `0x525160`,
      `0x525370`, `0x5255A0`, `0x525600`, `0x525730`, `0x524E30` among them -
      and one of them is what *Start mission* calls. Calling it would skip the
      queue altogether. Two more places react to the same message numbers as
      the quick keys (`0x517A40` for `0x424` and `0x425`), which is where the
      queue itself would be found if it is wanted for its own sake.
      The command line has no switch for a save, only `RECORD` and `REPLAY`,
      which would make a whole run reproducible once a mission can be reached
      without clicking.
- [x] ~~**Completion in the console window.**~~ The console suggests every
      command it knows while one is being typed, with a line of description
      each, and the item numbers behind `equipment(` and `vehicle(` come
      straight from catalog.txt. Arrows walk back through what was sent.
- [x] ~~**Call the command tree by injection** - for the overlays.~~ It turned
      out the command tree is not needed: every overlay is an object that is a
      vtable and nothing else, hung on the renderer at `+0xB240`, and one call
      turns the drawing on. Eight of them are in the console window of the
      launcher, see [architecture.md](architecture.md). What is left of this
      item:
- [x] ~~**Height in the map window.**~~ The path manager keeps a grid of its
      own with the height of every cell; the map window reads it once per
      mission and shades the picture with it.
- [x] ~~**Friend from foe on the map.**~~ It was in the cell array the whole
      time: the nibble at `0x00000F00` is the number of the party, not a kind.
      The map window colours by it.
- [x] ~~**Which party number is the player's.**~~ `GameLink.PlayerParty()`
      answers it: the UI player object at vtable `0x7CFE38` holds its units at
      `+0x78`, and a unit's stamp carries the party in its nibble. The map
      window marks that party "(yours)" in the legend, and the saves window
      says the first party in a mission save is the player's - the two agree.

- [x] ~~**Draw the map from the objects.**~~ The map window reads the units by
      the signature the objects answer to, so the whole mission shows at once
      whatever the party can see. The cell array stays for the terrain, the
      structures and the ground.
- [ ] **Reveal ground at chosen coordinates (a recon flight).** The point is
      to call the air strike and see what is at the target. Tried and
      rejected in one session, written up in
      [architecture.md](architecture.md): the vision circles at `+0xC4` read
      like the lever and draw a ring, but reveal nothing, and writing into
      that list corrupts the object (the game crashes later inside `free`
      from the destructor). `EVisibleTo` was never caught running, so the
      per-frame fog is decided elsewhere; the binoculars are passive. The
      Since then, measured properly (camera in free mode over the place,
      counting the orange enemy markers in a screenshot): a soldier
      **walking** there reveals it, 55 marker pixels against none. Writing
      his coordinates does not, nor does raising the perception stat, which
      the game restores by itself. So the observer has to be really there.
      Two leads left: how the engine itself puts a unit at a place, and the
      per-player grid at `+0x60` of the manager's objects - one cell per 64
      units, three floats, seen when the first two sum above zero
      (`0x6AF530` reads it), the only thing addressed by coordinates that
      has not been written to.

- [ ] **The sight range is computed, not stored - so it needs a code patch.**
      Seeing everything in the launcher works; seeing it in the game means
      reaching how far a unit sees, and that turned out not to be a field at
      all. The experiment: read a soldier's object, take two snapshots seven
      seconds apart while he stands still to learn which of his words move on
      their own (sixteen of them do), then give him binoculars and compare
      with that noise filtered out. Five words changed and all five are the
      inventory - the list at `+0x28`, a pointer to the item at `+0x338`, a
      count at `+0x3DC` that went down by one. No number anywhere went up.
      So the game walks the equipment when it needs the range rather than
      keeping a total, which is also why searching for a value between the
      measured bounds found nothing.
      The bounds themselves, for whoever patches that function: a vehicle saw
      a unit 68 away and not one 81.4 away, a soldier on foot did not see one
      84.4 away, and the same soldier did see it once he was given binoculars.
      So the plain range is somewhere around 70 to 80 world units - four to
      five map cells - and binoculars take it past 84.4.
      What is ruled out along the way: `Data.set` does not carry it either -
      the night vision gear and the binoculars have a trade value and a size
      and nothing else - and the exe names neither item, so the bonus is
      applied by index. `data.ubn` holds no other table.
      Which leaves the function that does the computing. `patch_exe.py` is the
      right vehicle for changing it: signatures rather than offsets, an `.orig`
      kept, and a switch to put it back. Worth doing after the test above, not
      before.

- [ ] **The campaign interface for a mission started from outside.** Loading a
      mission or a save through the network path works and plays, but the game
      builds the interface a network game has: Escape opens the wrong menu and
      the panel down the right side stays empty. The world is fine, so this is
      one flag or one layout chosen by which kind of game the engine thinks it
      is in. Finding it would make a mission started from outside
      indistinguishable from one started by clicking - which matters for
      playing, not for testing.
- [ ] **Reach the base screen from outside.** The self test drives everything
      else by itself, but not this: `loadmission` will load
      `Missions\Bunker_Light.Mis` and the world appears - 400 units across -
      while the pointer at `0x8759D4` that the base cheats need stays null. So
      the bunker as a *screen* is more than the bunker as a *map*, and the base
      cheats are only covered when the game happens to be sitting there
      already. Worth finding, because it is the last thing in the test that
      needs a person.
- [x] ~~**Which party is the player's.**~~ Read rather than assumed: the
      player's own party object - `Y2KKIUIPlayer`, vtable `0x7CFE38`, one of it
      in a mission - holds no party number at all, but at `+0x78` it points at
      an array of its units. Ask one of those units and its stamp says the
      party. The map window says which one is yours in the legend and under
      the pointer.

- [ ] **What else the unit object holds.** Position at `+0x54` and `+0x58` and
      the stamp at `+0x150` are known; a name, health, the weapon carried and
      the current order are all in there somewhere. The map could label its
      markers, and the save inspector further up this list wants the same
      fields.
- [ ] **Why a mission loaded through the network path shows everything.**
      `loadmission` reaches a mission by the road a multiplayer host takes, and
      a mission started that way draws every unit on the minimap instead of
      only what the party can see. That is the admin mode this list had given
      up on, arrived at from the side. The reason is a guess - probably no
      player party is set, so there is nobody for the sight to be computed for.
      Worth settling, because a switch that does only that, in a mission
      started normally, is what was wanted in the first place.
- [ ] **See the whole map at once.** The terrain, the structures and the
      objects are in the cell array from the start, but the units are there
      only where the party can see **right now** - walk away and they go
      again. `map_bits.py --watch` measured it: this is live line of sight, not
      a fog lifted once and for all. Which makes the map window awkward for the
      one thing it is best at, looking at a mission as a whole. Two ways round it, and they
      answer different questions:
      **from the mission file** - `mis.py` already reads the object table, so
      the launcher could lay the contents of the `.mis` under the live picture.
      That gives everything the mission starts with, works with the game
      closed and touches nothing - but it is the starting placement, not where
      anybody is now;
      **from the engine** - `Landscape.ShowVisMap` reads a visibility map of
      its own (`0x6D8022`, through the manager the world keeps), and since
      sight is decided somewhere it can be widened. That is the admin mode, and
      it is what would make the other debug overlays worth looking at. The
      third way, once the unit objects are found for the item above, is to read
      the units straight out of the mission and ignore visibility altogether.

- [ ] **Passability in the map window.** What `ShowPathMap` draws is a
      comparison between the height of the walk grid and the height of the
      terrain, for a given unit size (`0x685203`). Drawing that would say what
      is actually walkable, not just what the ground is.
- [ ] **`ShowVisMap` and `ShowKIMap`.** These two ask the visibility and the AI
      manager for a map before they build the overlay (`0x880FB0`, `0x6AE9B0`),
      so they need a second object and a pointer, not just a vtable.
- [ ] **The replay commands.** These do need the command tree, or at least
      their own case bodies read the same way the overlays were (`AirStrike`
      was, and turned out to be a game feature - see *Air support* below).
      `Replay.Jump` and `Replay.SpeedFactor` would make a recorded run a proper
      benchmark.
- [ ] **`RECORD` and `REPLAY`.** The command line takes both and the game writes
      `replay.log.gz` next to the exe. A deterministic recording would give
      reproducible crash reports and a repeatable benchmark for graphics
      settings, without playing the same stretch by hand every time. The replay
      commands (`Jump`, `SpeedFactor`, `AbortReplay`) live in the console, so
      driving a replay finely needs the injection above.

## Editing and making maps

- [~] **The scripting vocabulary is out of the executable now.** 20 triggers
      and 42 events, against the ten the editor's text resources named -
      `CY2KKITrigger_*` and `CY2KKIEvent_*`, in two unbroken blocks, listed in
      [editor-scripting.md](editor-scripting.md) by `gen_editor_docs.py`. A
      script element is stored in a `.mis` as a **number**, since none of those
      words appears in one, and the order the classes lie in is very probably
      that numbering - but it is not proven, and the document says so beside
      every index.

- [ ] **Learn the editor and write down what it can do.** The whole mission
      editor ships inside the retail game - code, layouts, artwork, text - and
      the 1.1.1 patch updated it. Its button is in the main menu, visible,
      labelled EDITOR, and it works. `LAY_EDITOR_MAIN.lay` alone lists 72
      panels, so this is a large tool and worth a document of its own. Of
      particular interest: the file menu offers importing and exporting a
      height map, which is the seam a script could work through. See
      [editor.md](editor.md).
- [ ] **Generate a map without the editor.** Finish the `.mis` format through
      `Y2K_LS_Serialize.cpp` and write the file directly. The only way to make
      maps from a script rather than by hand - terrain out of noise or real
      elevation data, objects scattered by rule. The editor is then the way to
      open a generated map and see whether it is right.

## The 3D models

- [x] ~~**Read `.diff3D`.**~~ **Done.** 1241 of the 1253 models in
      `objects.ubn` come out, and the eleven that do not are camera paths with
      no geometry in them. `tools/diff3d.py` reads them and draws them; see
      [models.md](models.md). Same serialiser as the saves, vertices of forty
      bytes, faces of twenty, and every file still carrying the path of the
      `.ASE` its authors exported it from.

- [x] ~~**Get the parts into their places.**~~ **Done.** The file carries a tree
      and it is the last thing in it: a table of `type | children | offset |
      size` chunks written depth first, where the second field is a child count.
      A part's place is its own matrix multiplied out through every parent above
      it. The wheels of a vehicle hang off the root and its doors off the body,
      so a door takes three matrices and a wheel takes one - which is why no
      rule about *which* parts to transform could ever have worked. Every mesh
      in 401 models comes out placed and named. See [models.md](models.md).

- [x] ~~**The animation tracks.**~~ **Solved.** A `0x10001` chunk is two lists of
      keys behind one header that describes both: n keys of 40 bytes - a time, a
      position and the tangents either side of it - and n+1 of 84 - a time, a
      quaternion and a 4x4 matrix. Times are milliseconds, keys every 100 of
      them. Every animation measured closes on the byte. They belong to the
      *dummy* nodes, which is where a character carries a weapon.

- [x] ~~**The body's animation.**~~ **Solved, out of the loader.** The mesh chunk
      header is forty bytes and its sixth field is the frame count - one for a
      crate, 29 for a walking antelope. It had been sitting in front of the face
      list the whole time; `diff3dLoader.cpp` at `0x6392F0` reads `0x28` bytes
      and then refuses to go on unless four of the fields hold, which is what
      named them. Frame zero is the static mesh; every frame after it is a
      sixteen byte header carrying the time in milliseconds, then the vertex
      list again at 24 bytes each - a position and a normal, since the colour
      and the texture coordinates do not change. 110 animated meshes and 3317
      frames read out of 221 models. `--frame N` draws one.
      See [models.md](models.md).
- [x] ~~**A model viewer in the launcher.**~~ The **Models** button: 1253 models
      with a search box, one drawn beside them with its own textures, dragged to
      turn. WPF's own 3D, so nothing was added to the package but code.
      `launcher/Models.cs` is the reader ported to C# and was run against the
      Python one over the whole archive - they agree to the decimal. It carries
      a small Targa decoder because WPF has none and 150 textures are `.tga`.

## Publishing

- [x] ~~**Put part of the project on GitHub, publicly.**~~ **Done** -
      [github.com/TomasBouda/SoA](https://github.com/TomasBouda/SoA), a separate
      repository rather than a branch, so nothing of the game's can be pushed to
      it by accident. 261 files: the documents, the tools, the launcher, the
      translation and the catalog. `_patched` and the saves stayed home.

- [x] ~~**A landing page, published from the repository.**~~ In `docs/`, one
      file, with the rendered models and the portraits before and after. GitHub
      Pages has to be switched on in the repository settings - Settings, Pages,
      deploy from `main` and the `/docs` folder.

- [x] ~~**Publish the kit.**~~ Release `v1.16.3`, 2.8 MB, the launcher with no
      game in it.

- [x] ~~**An extras archive for people without a GPU.**~~ `SoA-Textures-1.16.3.zip`
      on the release, 316 MB, 1230 loose files. Plainly, not as delta patches:
      the deltas were the cleaner artifact in principle but save nothing, since
      an enlarged picture is a different bitstream from the one it came from.
      The pack needs the game, is no substitute for it, and the readme inside it
      says so and points at `-Generate` for anybody who would rather make their
      own than take it on trust.

## Content and looks

- [x] ~~**Can the font be changed?**~~ Yes, and it is cheap: the game asks
      Windows for "Tahoma" by name in nine sizes and bakes each into a
      texture, so another name is another font everywhere, laid out right
      because the game measures what it was given. Two drop-downs in the
      launcher's Patches window, `patch_exe.py --font`. See
      [architecture.md](architecture.md), "The fonts come from Windows".
      Still open:
      - [ ] a font shipped with the package - a TTF the launcher registers
            for the game's process with `AddFontResourceEx(FR_PRIVATE)`,
            so a look does not depend on what the machine has;
      - [ ] the loading screen's briefing has a fixed line spacing and a
            taller face overlaps its lines there - the nine sizes could
            be scaled with the face, or that one drawn smaller;
      - [ ] where the Arial default of `bmfont.cpp` reaches the screen, if
            anywhere.

- [x] ~~**Can a weapon be added?**~~ Yes: the M34 white phosphorus grenade,
      item 150, is in the package - a pack of three, thrown like the hand
      grenade, a circle of fire where it lands. The data is four loose files
      ([tools/mod_m34.py](tools/mod_m34.py)); the exe names its five thrown
      weapons by number in a dozen places and each had to learn the sixth
      ([tools/m34_patch.py](tools/m34_patch.py)). See
      [architecture.md](architecture.md), "A new weapon". Still open around
      it:
      - [ ] the Object Information screen (the base's encyclopedia) is a
            fixed list with 3D models and does not know it;
      - [ ] the stock room's 3D shelves do not show it
            (`Y2KBunkerLayoutStorage`, number → shelf slot);
      - [ ] the enemy AI never throws one (`Y2KKIAdd`, 0x573F50, has the
            same five numbers);
      - [ ] **the flame after the burst.** The burning damage is there and
            the trace shows `CY2K_FX_FireShape01` ticking for the M34 as it
            does for the Molotov, but nothing is drawn where the M34 lands
            while the Molotov leaves a flame for many seconds. Something in
            how the effect is parametrised - the radius (5 against 2.5),
            the height of the burst, the projectile - hides it; the FX
            requests are built in `0x5E4110`'s neighbourhood with
            positional parameters (`0x67e290`). Filming throws with the
            camera on the thrower is too slow a way to bisect this; see
            the test mission below;
      - [ ] **a test mission.** Every check of the M34 so far went through
            the base screen, the Equip window and a real mission with
            enemies wandering about. A small flat map with the squad, a
            few targets and nothing else, loaded straight from the menu
            (`mission_cheat.load_save` already does that for a save), and
            a console command that makes items with the factory
            (`0x5DFAB0`) and puts them in a soldier's hand through the
            game's own `Commando_ChangeEquipment` (slot 0x330), would make
            an experiment a minute instead of five. The mission format is
            the obstacle (see "The mission format, where mis.py stopped");
            a save of a real mission with everything but the squad killed
            off may do instead;
      - [ ] a second new weapon would show what is M34-specific in the
            patch and what is general - the caves compare with one number
            each; a table of new numbers would take several;
      - [x] ~~the throw played the rifle animation~~ - a table per character
            class picks the attack animation by item number; five bytes;
      - [ ] the kit cannot have it: the launcher patches the player's exe
            and the data files are the package's. The launcher could carry
            the four files and write them beside the game.

- [x] ~~**Enlarge the portraits.**~~ Done and measured. The faces are 32 by 48
      in the sheet and the game draws the selected one at 75 by 94 on a 1920 by
      1080 screen, so it was magnifying by two and a third - which is why a
      portrait was a mosaic. The doubled sheets are read, the source rectangles
      are proportional, and a 64 by 96 face now fills that area almost one to
      one. See [upscale.md](upscale.md). It also overturns what was written
      there about the interface: the extra size is **not** thrown away.


- [ ] **Is the interface stretched on 16:9?** The mission screen is designed
      for 800 by 600 and its panels are declared 1:1 with that space, so at
      1920 by 1080 they are magnified 2.4 across and 1.8 down - two different
      numbers. If that is real, the interface is a third too wide and no
      sharpening touches it. One screenshot settles it: put a circle on a panel
      sheet and see whether it comes back a circle. See
      [upscale.md](upscale.md).
- [ ] **Enlarge the rest of the interface.** The panels magnify by the same
      amount the portraits did, and the portraits came out well. It needs
      `hud_contrast.py` folded into the same tool first - the two write the
      same files. Worth doing after the question above, because a stretched
      interface is not worth sharpening.
- [ ] **The size of the game window.** Windowed mode works (see
      [architecture.md](architecture.md)), but the window keeps the size it was
      created with - the chosen resolution only decides what is rendered into
      it.

      **Resizing the window from outside was tried and taken out again.** The
      launcher grew a *Window size* setting that waited for the game's window
      and resized it: first as soon as the window existed, then - when that
      left a small picture in a large frame - a second time once the game
      reached its menu, with the size set twice a pixel apart so that Windows
      would actually send `WM_SIZE`. The frame grows either way and the
      picture does not follow properly; the mode stays what it was and the
      result looks wrong. Dragging the window by hand does work, so something
      in that path is different from `SetWindowPos`, and `KeepWindowAspectRatio`
      being on in `dgVoodoo.conf` means the wrapper is adjusting the window
      itself as well. Three attempts went into this and none of them produced
      a picture worth keeping, so the setting was removed rather than left in
      half working.

      What is left is the other route: give the game's own resize block the
      display mode instead of the monitor rectangle, which needs a code cave.
      Forcing `Resolution` in dgVoodoo was already tried - the image follows,
      the window does not.
- [x] ~~**The GUI is moddable.**~~ [tools/hud_contrast.py](tools/hud_contrast.py)
      takes the 47 pictures that make up the mission interface out of
      `gui.ubn`, pulls their dark and light apart and lifts them a little, and
      writes them back as loose files, which the engine reads in preference to
      the archive. The alpha channel is left exactly as it was - it is what
      gives the panels their shape. `--preview` writes a before-and-after sheet
      so it can be judged first, `--apply` deploys it, `--off` deletes the loose
      folder and the game is back on the archive. Faces, item icons and the
      minimap symbol are left out: they are photographs and pictograms, and
      contrast only spoils them. **Deployed at the default 1.35 and +10** in
      package 1.12.0. It writes into `_patched`, not into the built package:
      every build wipes the output folder and copies it again from there, so a
      loose file put straight into the package would vanish at the next build
      without a word - which is how it was nearly left the first time.
- [x] **Air support.** A shipped feature, not a console leftover: the
      context menu's air strike button calls the same launch (`0x6B9030`)
      the `AirStrike` console command does, and needs a plane with bombs in
      the hangar - but the button only appears in a mission whose designer
      placed target markers, and none of ours has them. So
      [tools/airstrike_inject.py](tools/airstrike_inject.py) calls the launch
      with points of its own, verified live: plane, bomb, dead unit. The
      launcher has it too, since 1.18.1: `airstrike(x, y)` in the console and
      an *Air strike* button in the map window that arms one click. See
      [architecture.md](architecture.md).
- [x] **Air strike from the context menu.** `patch_exe.py --airstrike-menu`,
      in the package and the launcher's Patches window: the button's condition
      becomes "a plane with bombs in the hangar", the case notes the click's
      point, and an empty waypoint list gets it before the launch - a
      mission's own markers still win; a launch that flew puts a red ping
      on the minimap until the plane lands and plays one of the three radio
      calls, which sit in sounds.ubn. Verified live. See
      [architecture.md](architecture.md).
- [x] **Camera zoom.** The limits are two immediates in the camera's
      constructor and the wheel slid at both because the clamp put only z
      back; `patch_exe.py --camera` fixes both, in the package since 1.19.0,
      and `--fast-camera` makes Shift move it five times as fast (1.20.0).
      See [architecture.md](architecture.md).
- [x] **Pause and give orders.** The "turn-based patch" of the 1.0 readme,
      never in 1.1.2: `patch_exe.py --active-pause`, in the package since
      1.21.0 and in the launcher's Patches window. See
      [architecture.md](architecture.md).
- [ ] **Multiplayer over LAN.** The internet server list is dead, LAN should
      still work, nobody has tried. Two sandboxes on one host would do.
- [ ] **`querschlaeger1.wav`.** The ricochet sound is referenced and shipped
      nowhere; unlike the body hit sounds there is nothing in the archives to
      put in its place. Either leave it silent or accept a substitute.

## The AI at the controls

- [~] **A program that plays.** `tools/play_bot.py` reads the squad and
      sends it places through the game's mailbox (`--mailbox`, 1.22.0):
      the projection comes from the Direct3D matrices, orders from the
      right click's own function, verified exact; every other order is a
      virtual call on the unit through the mailbox's fourth request - the
      slots named by the game's own trace, after a first table had "attack"
      on the grenade slot. It reads the players, their diplomacy (0 neutral,
      1 enemy, 2 friend) and every unit's health, and its first plan
      (`--hunt`) closes on the nearest enemy soldier and shoots him, keeping
      away from armour. `mission_cheat.py` sends the mission cheats
      (endlessmunition is a toggle - read the byte first) and loads a save
      with no menu; `menu_bot.py` does the menus when there is no mission
      yet. Open: a plan with cover, vehicles and anti-tank weapons in it,
      and a sight test - the map cells carry the party of a unit whether
      the player can see it or not, so they are not one.

What the first plan taught, in the order it should be fixed:

- [ ] **Know what the squad carries.** Read each soldier's weapons and
      the inventory of the squad's vehicles (the weapon objects hang on the
      unit at `+0x334..+0x340`, the character at `+0x320`), so a plan knows
      who has an anti-tank weapon, who is a medic, what the BMP and the
      Hind can do - and never sends rifles against armour again.
- [ ] **Use the squad's own vehicles.** GetIn/GetOut work as orders; a tank
      or the helicopter is what the plan should answer enemy armour with,
      and the air strike from the launcher is the other answer.
- [ ] **A real test of sight.** The map cells carry a unit's party whether
      the player can see it or not, so they are no sight test; an attack on a
      unit out of sight is taken and does nothing. `Landscape.ShowVisMap iX
      iY` says a visibility map per player exists - find it, or the flag on
      the unit that says who sees it.
- [ ] **The air strike is the AI's too.** A plan may call one on enemy
      armour or a dug-in group when the hangar has a plane with bombs
      (`airstrike_inject.py` is the call; the radio call and the map marker
      are the launcher's): worth the bomb when rifles cannot do it, and never
      on the squad's own position.
- [ ] **Cover and posture.** Kneel or lie down when shooting, stand to run,
      keep the squad together, and give the plan a reason to be somewhere:
      the mission goals (`Mission Goals` in the Esc menu reads them from
      somewhere) rather than the nearest enemy.

## Solved, kept for reference

- [x] ~~The error codes of the game~~ - HRESULTs with a 12-bit facility;
      [tools/decode_error.py](tools/decode_error.py) decodes them and walks a
      whole log, see [architecture.md](architecture.md).
- [x] ~~Finish taking `Data.set` apart~~ - the records are bounded by their
      identifiers, see [dataset-format.md](dataset-format.md). It did not
      unlock the weapon-to-carrier link: that link is not in the data at all.
- [x] ~~What an item is worth in a trade~~ - field 0 of the record, and the
      trader wants more than 1.2 times what he gives, see
      [trading.md](trading.md).
- [x] ~~Try `Mipmapping = disabled` in dgVoodoo~~ - deployed, full resolution at
      a distance as well, the price is shimmering.
- [x] ~~Check `TextureDetail` in `soa.exe -o`~~ - the registry holds 0 and the
      dialog shows the maximum, so zero is the highest quality.
- [x] ~~Repack the terrain sheets so the detailed ground can be enlarged~~ -
      there is nothing to repack, the coordinates are proportional; enlarge the
      sheets and leave `details.txt` to the archive.

## Other people's work to build on

Melkij (reverse engineering SKAITER) has two projects for the same game on
GitHub:

* [soa-game-revers-eng](https://github.com/Melkij/soa-game-revers-eng) - a
  parser of the `.mis` mission format in PHP. `struct/` holds the structure
  definitions including `BinaryFile.php` and `Trs.php`, `testmis/` holds a few
  hundred test missions. According to the README the missions parse into
  meaningful structures up to the script sections; the scripts, the dialogues
  and part of the binary blocks stay unknown.
* [SOA-scripts](https://github.com/Melkij/SOA-scripts) - helper scripts around
  the missions and background generation, plus `tech.lst`.

It touches neither `Data.set` nor the memory at run time, but for the mission
format it is the best available springboard - and `.mis` shares its container
family with `.sav`, so whatever is learned there helps the save inspector too.
