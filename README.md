# Play Soldiers of Anarchy on Windows 11

*Soldiers of Anarchy* is a squad tactics game from 2002. On a modern machine it
barely starts: it asks for a display mode nobody has any more, and if it does
come up it is a small blurry window with the interface drawn for 800 by 600.

This makes it play properly. **Two downloads, and a copy of the game you already
own.**

## [→ Download](https://github.com/TomasBouda/SoA/releases/latest)

| | |
|---|---|
| **SoA-Kit** &middot; 2.8 MB | The launcher. Start `Play.exe`, point it at your `soa.exe` once, press Play. It puts the graphics wrapper in place, sets the game up and starts it full screen. |
| **SoA-Textures** &middot; 316 MB, optional | 1230 sharper pictures the game reads instead of its own. Unzip into the folder with `soa.exe`; delete four folders to undo it. |

Neither contains the game and neither can replace it.

## What the launcher gives you

**It makes the game start.** The wrapper, the display mode, the settings, the
keys on WASD - all of it done for you instead of read off a forum thread.

**Sharper portraits.** A soldier's face is 32 by 48 pixels and the game draws it
at 75 by 94, which is why every portrait was a mosaic. In the textures download.

**Five sounds that were missing.** The game asks for them and they were never on
the disc. Put back from what is in its own archives.

**A save browser that edits.** See what is in a save without loading it, and
swap what a soldier carries for anything in the game - four slots: the pack, the
weapon, the ammunition, the vest.

**Every item in the game, described.** The catalog, built out of the game's own
data: what each weapon and vehicle is, what it costs, what it is worth.

**A console into the running game.** Its own log and its own cheats, and it can
be driven from your phone on the same network - because leaving full screen to
type something loses the window.

**The map of the mission you are playing**, read out of the game's memory.

**All 1253 3D models**, drawn with their textures and turned under the mouse.

## What you need

A copy of the game, patched to **1.1.2.178** (the last official patch). The
launcher still starts on another build and says plainly which of its windows
will not work rather than pretending.

Windows 10 or 11. Nothing to install - the launcher is one exe.

## Make the textures yourself instead

If you would rather not take a 316 MB download on trust, the tools that made it
are here and they run against your own copy:

    build-package.ps1 -Variant full -Generate -Source "C:\your\game"

Under two minutes on a graphics card. It wants Python and torch, which is the
only reason the download exists at all.

## The rest of this repository

Getting the game to this point meant taking a good deal of it apart, and that is
written down: [what is in the models](research/models.md), which nobody had
described - 1253 files, now readable with their textures and their parts in the
right places - [what is in a save](research/saves.md), [how the engine is put
together](research/architecture.md), and
[how it was translated](research/translation.md) with no patch to the executable
at all.

[research/TODO.md](research/TODO.md) is the more useful half: as much of it
records something that was tried and did not work, and why it looked as though
it had, as records what is still open.

**The game is not in this repository** - no archives, no executable, no data.
The tools work against a copy you install yourself.
