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
