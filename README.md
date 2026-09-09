# Soldiers of Anarchy on Windows 11

*Soldiers of Anarchy* is a squad tactics game from 2002. It still runs on a
modern machine, but only just: it wants a display mode nobody has any more, its
interface was drawn for 800 by 600, and a good deal of what it can do was never
written down anywhere.

This is the work of getting it to run and look well, and of taking its data
apart far enough to change things. **The game itself is not here** - none of its
files, none of its archives, no executable. What is here is our own writing and
our own code, which needs a copy of the game you already own.

## What has come out of it

**A launcher.** One window that builds and starts a clean installation, with a
console into the running game, a map of the running mission read out of memory,
a browser for the saves that can change what a soldier carries, and a browser
for the game's 3D models.

**The model format, read.** `objects.ubn` holds 1253 `.diff3D` files - every
soldier, vehicle, building and tree the game draws - and nothing about the
format was documented anywhere. 1241 of them now come out with their textures
and their parts in the right places. [models.md](research/models.md) is the
whole of it, including three readings that were wrong and why each looked right.

**The saves, enough to edit them.** What a soldier carries is four slots inside
the record that opens with his `TRES_` key, and the launcher will swap one item
for another. [saves.md](research/saves.md) - including the false positive that
made an earlier answer look correct for two days.

**Czech, with no patch to the executable at all.** The text is UTF-8, which took
a while to believe. [translation.md](research/translation.md).

**Sharper portraits.** A face is 32 by 48 pixels and the game draws it at 75 by
94, which is why a portrait was a mosaic. [upscale.md](research/upscale.md).

## What is in here

| | |
|---|---|
| [research/](research) | What was worked out about the game, one document per subject |
| [research/tools/](research/tools) | The tools, in Python |
| [research/tools/launcher/](research/tools/launcher) | The launcher, C# against WPF, built by `csc` with no project file |
| [research/tools/build-package.ps1](research/tools/build-package.ps1) | Builds a package out of an installed game |
| [research/translation/](research/translation) | The Czech translation |
| [analysis/](analysis) | Readers for the installation disc and the executable |

The catalog - `catalog.txt` and its pictures - is derived from the game's own
data and is here because the launcher is no use without it. Everything else in
this repository was written for this project.

## What is deliberately not in here

The game. Its archives, its executable, the upscaled textures, the repaired
sounds and the saves all live in the private working repository, because they
are the game's and not ours to hand out. `build-package.ps1` makes a package
from a copy you install yourself.

## Where to start reading

[research/architecture.md](research/architecture.md) is how the engine is put
together. [research/TODO.md](research/TODO.md) is what is still open and what
has already been tried, which is the more useful half - a good number of entries
are there to stop somebody spending an afternoon the way we did.
