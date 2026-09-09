# Three packages

One source, three things to hand someone. What separates them is not features
but **who may have what**.

## What the kit carries

The kit is meant to be shared publicly and is small on purpose: the launcher,
the settings, the wrapper, and the item catalog inside the exe.

The catalog is the exception to the rule the kit started out with. It is
derived from the game's own data - the names and descriptions from the `TRES`
resources, the 156 icons cut out of the sheets in `gui.ubn` - so by that rule
it would have stayed out, and it was built that way first. The owner of the
project decided it goes in, and that is the decision that stands.

It does not generalise. The upscaled textures come to 266 MB and the repaired
sounds are the same kind of thing; whether either belongs in a public kit has
not been asked, and should be, separately.

## What each one is

| | `full` | `vanilla` | `kit` |
|---|---|---|---|
| the game | yes, with everything | yes, as it shipped | **no** |
| `soa.exe` | ours, patched | `soa.exe.orig`, untouched | none |
| dgVoodoo | yes | yes | yes, installed into the game folder |
| `settings.reg` | yes | yes | yes |
| launcher | yes | **no** | yes |
| upscaled textures, sound fix, HUD contrast | yes | no | not yet - a question of its own |
| catalog | **inside Play.exe** | - | **inside Play.exe** |
| `SelfTest.exe` | yes | - | **no**, it is ours to run |
| started by | `Play.exe` | `Game\soa.exe` | `Play.exe` |

**vanilla** is the game as it was, with two honest exceptions. The exe is the
one with the copy protection removed, because the protected one does not start
on Windows 11; and dgVoodoo is in, because without a wrapper there is no game
at all. It is therefore the closest thing to the original that still runs. It
carries no launcher, so the resolution is whatever the registry says and does
not follow the monitor.

The nine bytes between `soa.exe` and `soa.exe.orig` are exactly our patches -
the window mode, the two that stop it falling into the taskbar, the intro, and
the shared log.

## What has to be built

### 1. `-Variant` in build-package.ps1 - done

`-Variant full|vanilla|all`, `full` by default, each with a folder of its own -
`SoA-Package` and `SoA-Vanilla`. `kit` joins the list when there is one.

Vanilla turned out to be four folders not copied. Everything we added to the
game lives in a loose folder that overrides an archive - `textures`, `terrain`,
`Sounds`, `gui` - so leaving them out is the whole of it, and the package comes
to 622 MB against the full 1017 MB.

Because that is so easy to get silently wrong - a vanilla package with our
changes in it would merely look better than it should - the build checks
itself: none of the four folders present, the packed exe byte-identical to
`soa.exe.orig`, no launcher.

### 2. Settle what exe gets packed - done

The build copied `_patched\soa.exe` as it found it, and **the launcher
rewrites that file on every Play** according to the window mode chosen - so
what ended up in a package depended on how the game had last been started.

Now the full package runs `patch_exe.py` over its own copy after the copy and
before anything else, setting full screen, no intro, keeps focus, shared log.
That is the state a person meets the first time they open the launcher. The
source is not touched. Vanilla takes `soa.exe.orig` instead, which is the
shipped 1.1.2.178 with the copy protection off and none of our nine bytes.

### 3. The kit finds the game - done

`GamePath` is the one place that knows where the game is, and the five places
that used to build the path themselves now ask it. It looks in a `Game` folder
beside the launcher, then at what it was pointed at before, then at `INSTALLDIR`
in the registry, then at its own folder - and if none of those holds a
`soa.exe` the launcher says so and shows **Find the game...**, which asks for
the exe rather than for a folder, because pointing at a file is unambiguous.
The answer is remembered under `HKCU\...\Soldiers of Anarchy\Launcher`.

Version is checked too. Everything `GameLink` does is tied to the addresses of
1.1.2.178, so anything else gets said out loud rather than crashed into.

The kit builds at just under a megabyte: `Play.exe`, `settings.reg`, the
readme, and dgVoodoo in a folder of its own with the readme saying where the
three files go. Nothing from the game is in it - checked.

`SelfTest.exe` is **not** in it, and not in vanilla either. It is a tool for
working on this project: it starts the game and drives it about, which is not
something to leave lying in a package somebody else opens. The full package
keeps it, because that is where the work happens.

### 3b. The catalog moved inside the exe - done

It used to sit beside `Play.exe` as `catalog.txt` and a folder of 156 pictures,
2.6 MB of loose files in a package where nothing else is loose. The build zips
them and the compiler embeds that as a resource, so the full package's root is
now `Play.exe`, the game, a readme, the settings and a version file - nothing
in between. `Play.exe` went from 148 kB to 2.4 MB.

A loose `catalog.txt` still wins where one exists, which is the same rule the
game follows for its own archives and leaves the door open for step 4.

Only the full package gets the resource. A kit's exe carries none, which is
what makes the rule hold by construction rather than by remembering.

### 4. The kit builds its own catalog - not needed

The kit carries the catalog instead, in the same embedded resource the full
package uses. Building one on the player's machine would mean porting the 426
lines of `gen_catalog.py` - `Data.set`, `Units.olb`, the rectangles in
`Items.gui`, the cropping out of six sheets - and there is now no reason to.

The loose-file override survives, so a generated catalog would still win if one
ever appeared.

### 5. The kit offers the changes as operations

The interface contrast, the upscaled textures and the sound fix become things
the kit *does* to an installation, with an undo, rather than things it carries.
`hud_contrast.py` already works this way; the others would need the same
treatment.

### 6. A check and a readme for each

`check.py` verifies the packed exe for full; for vanilla it should confirm the
exe is byte-identical to the original and carries none of our patches; for the
kit there is no exe to check at build time, so it checks its own files and
leaves the exe to the runtime check from step 3.

## Order

Vanilla first, because it is nearly all exclusions. Then the exe question,
which is a real bug and cheap to fix while the packaging is open. Then the kit
in the order above; it is worth having after step 3 and better after 4.

## Settled

dgVoodoo may be carried. There is no licence file in `_sandbox/tools/dgVoodoo`,
only links to an online readme, and the question was put to the owner of the
project, who decided it goes in. The kit therefore ships the wrapper and
installs it into whatever game folder it is pointed at, rather than sending
people off to download it.

## Building a package from your own copy

The full package cannot be handed out: most of it is the game. What can be
handed out is **the way to make one**, and `-Generate` is that.

    build-package.ps1 -Variant full -Generate -Source <a retail installation>

It runs the tools that produce our changes against that installation first, then
packages it. Each of them writes **loose files beside the game's archives**,
which the engine reads in preference to them - so it adds to an installation and
takes nothing away, and every tool can undo its own work. `SOA_SOURCE` is how
they are all pointed at the same place.

The steps, in order: the sounds the game asks for and never shipped, the
interface with its dark and light pulled apart, the portraits, the object
textures, the terrain, and the detail textures of the ground - those last are
cut out of shared sheets rather than standalone, which is why they are a step of
their own and why leaving them out shows as a difference of 43 files.

**Measured, from a clean install:** 695 object textures in 54.6 seconds and 433
terrain textures in 40.4 seconds on an RTX 3080 Ti, and the whole run under two
minutes. The result matches the package built the ordinary way file for file -
695 textures, 476 terrain, 5 sounds, 54 interface pictures.

`-NoUpscale` leaves the two texture steps out. That is the only part wanting a
GPU and `torch`, and installing torch is 2.5 GB against 375 MB of textures it
would save downloading - so for anyone without one it is the wrong trade, and
everything else still runs.

### Why it is worth having

Somebody who owns the game can now reach the same package we have without being
given a single file of the game's. That is the whole answer to publishing: the
kit is on GitHub as a release, the tools are in the repository, and this turns
one into the other.

## Testing the release the way a stranger meets it

`_sandbox/KitTest.wsb` is a second sandbox, and deliberately not the one for
playing. **Nothing of the project is mapped into it** - no tools, no Python, no
dgVoodoo already beside the game, no registry settings. A clean Windows, a plain
installation, and the zip exactly as it comes off the release page, checked
against the published SHA-256 so it is the file a stranger downloads and not a
local copy of it.

`_sandbox/kit-test.cmd` lays it out and then gets out of the way: it installs
nothing and configures nothing, because anything it did for the kit would be a
thing the test no longer covers. Two details are deliberate:

* The game is copied to the local disk rather than played from the mapped
  folder - the game writes beside its own exe and every write through the
  sandbox's redirected filesystem is slow enough to freeze it while saving.
* **The wrapper is deleted from that copy.** The vanilla package carries
  dgVoodoo inside its Game folder, because without a wrapper there is no game on
  Windows 11 at all - but deploying it is one of the things the launcher is
  supposed to do, and finding it already there would quietly skip the test.

The order to try things in is printed when it starts: the launcher with no game
to find, then **Find the game...**, then the windows that work without the game
running, then Play, then the ones that need it running.

## What is published, and where the line runs

Two downloads on the release, and the difference between them is the whole
argument about what may be handed out.

**The kit, 2.8 MB.** The launcher and the wrapper. Every byte is ours bar
dgVoodoo and the catalog, and it needs a copy of the game to be any use.

**The textures, 316 MB, optional.** 1230 loose files - the enlarged object and
ground textures, the interface, the portraits and the five missing sounds. These
*are* derived from the game's own art, and they are published anyway on the
reasoning that a texture pack is not a substitute for the game: it needs one,
and it is the form modding has taken for twenty years. That is a decision, not a
rule, and it was the owner's to make.

**The game is not published and will not be.** That is the line: things that
need the game may go out, the thing itself may not.

Delta patches against the originals were the obvious cleaner artifact - they
carry none of the original and are useless without it - and they were dropped
after being thought through rather than after being built. An enlarged picture
is a different bitstream from the one it came from, so the delta comes out
about the size of the result and buys nothing but the argument.
