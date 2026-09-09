# Translating the game

Everything the game says is in `.trs` files, the format is simple enough to
write as well as read, and loose files beat the archive - so a translation is
deployed by dropping files beside the game, with nothing repacked.

## How much there is

Once the 1.1.1 patch has overridden the originals, **43 files, 3042 records,
about 134 000 characters** - some 74 standard pages. Of that, **1219 lines are
spoken**, 129 000 characters, which is most of the words: the interface is
short labels, the missions are dialogue.

## The format, all four versions of it

A record is an ordinal, some strings and sometimes a tail, and how many of
each depends on the version in the header:

| version | record |
|---|---|
| 0 | ordinal, key, german, text |
| 1, 2 | ordinal, key, german, text, reserve |
| 3 | ordinal and five strings |
| 4 | ordinal, key, **sound file**, text, **speaker**, **party**, and a dword |

None of that was guessed. Each shape was found by walking every file of that
version with every plausible number of fields and keeping the one that ends
exactly at the last byte in every file, with no slack - 5 strings and a 4-byte
tail is the only shape that does it for the fourteen version 4 files, 5 strings
and nothing for the three version 3 ones.

The translatable string is the third in all four.

**Version 4 is the mission scripts**, and it carries the two things a dubbing
would need: the sound file each line is read from and the name of whoever reads
it.

`tools/translate.py --check` reads all 43 and writes them out again unchanged.
**All 43 come back byte for byte.** That test came first on purpose: a
translation built on a writer that quietly loses a field is worse than no
translation, and the first version of the reader did lose the mission files
entirely without saying so.

## The characters: UTF-8, and nothing else

**The text is UTF-8.** That is the whole answer, and the exe needs no patch at
all - proven on the options screen, translated and rendering its diacritics
with `soa.exe` untouched.

It was not obvious. The strings are length-prefixed bytes and look like a
single-byte code page, so the first attempt wrote code page 1250 and every
accented letter came out as a question mark. Two things say why:

* The game's own German lines are UTF-8 already - `Aussenposten` is stored with
  `C3 9F` where the sharp s belongs.
* The exe converts with code page `0xFDE9`, 65001, at `0x50DC36` and
  `0x65B073` among others. An isolated `0xEC` is not a valid UTF-8 sequence, so
  the conversion replaces it, and the replacement is what reached the screen.

The question mark had nothing to do with the font. That was measured before it
was abandoned: with EASTEUROPE_CHARSET the exe asks for a different font and
Arial genuinely carries the glyphs - Windows reports the width of `0xEC` as 9
under charset 238 against 3 under ANSI. The font was never the problem.

### The charset patch, kept but not needed

`patch_exe.py --east-europe` sets `fdwCharSet` to 238 at **ten sites** - one
Arial and nine sizes of Tahoma. They share their surroundings byte for byte, so
no anchor picks out one of them and the count is the safety check instead: ten,
or it is not this build. `--default-charset` puts it back, byte for byte.

It stays in the toolbox because it was written and verified, and because a
translation into a language UTF-8 alone does not carry through might want it.
For Czech it is not needed.

## The speech

1787 mp3 files, 93 MB, in `missions.ubn` mostly, under
`Missions/Campaign/Mission_N/SpeechEN/`. The 1219 spoken lines name 1142 of
them, so the mapping from a line of text to the file that reads it is already
in the data and needs no work.

Replacing them is the same loose-file trick as everything else here.

## Dubbing: which route, and one that does not work

**Text to speech is the route.** Every spoken line is already written down, so
a Czech recording is made from the Czech text and the original audio never
enters it. `translate.py --speech Mission_1` prints the worksheet - key, sound
file, speaker, text - and `translate.py --dub` puts a recording back where the
game will find it. `tools/dub.py --convert` puts it into the game's format
first: MPEG-1 layer 3, 64 kbit, 44100 Hz, mono.

**Cloning a voice is where the eleven second minimum bites**, since a line of
game dialogue is often one or two. `dub.py --sample` answers that by joining
everything one character says: in mission 1 the outpost comes to 235 seconds
across 55 lines, the trader 128, the base 100.

**Dubbing that joined sample does not work, and it looks as though it does.**
The obvious shortcut is to send the whole sample through a dubbing service and
cut the Czech back into lines where the originals joined. The durations agree
almost exactly - 60.34 seconds back against 60.73 - which is what makes it
convincing. It is wrong: the service re-times the speech inside the recording,
so the joins move even though the total does not. Cut at the old boundaries,
**14 of 16 pieces began or ended in the middle of a word**, and for the second
voice 18 of 18.

`dub.py --split` still exists, because the check that caught this is worth
having: it reads the first and last fraction of a second of every piece and
says how many are cut through speech. Above a quarter it stops recommending
them and says why. A tool that hands over sixteen broken files without comment
is worse than no tool.

So: the sample is for cloning, and then each line is spoken on its own.

## The one screen that stays English, on purpose

The ring of buttons on the start screen carries no text at all:
`LAY_START_WELCOMEBUTTONS.lay` gives every one of them a picture id and nothing
else, 4043 to 4048. The words are hand-lettered into the artwork - one sheet,
`gui/GUI_Start/ButtonsWelcome/start.png`, five curved banners.

Two of the five need nothing: MULTIPLAYER and EDITOR are the same word in
Czech. So it is three banners, not five, and the banners themselves would stay
- only the lettering changes.

**Left in English by decision.** The lettering is irregular and drawn along the
curve of each banner, and type set by machine does not look like it; a
replacement would most likely read as worse than the original. Five words that
a Czech player understands anyway are not worth that.

Everything behind those buttons is text and is translated.

## What the proof settled

One interface file - the options screen, 47 records, chosen because it has both
short labels and long descriptions - was translated and deployed. It renders,
the diacritics are right, and **the layout holds**: Czech runs longer than
English and nothing overran its panel.

So the plumbing is finished. What remains is the writing.

## What is not settled

* **Whether any other screen has its text painted in.** The start screen does,
  and is dealt with below; nothing else has been checked, and the way to check
  is to translate a screen and see what stays English.
* **Letter spacing.** On the screenshot some words looked as though they had a
  hair more space between letters. It may be the picture being scaled down. A
  full-size shot would say, but the game's own screenshot key does not work in
  the menus - see below.
* **The screenshot key.** `AK_SCREENSHOT` is bound to F12 and works inside a
  mission, not on the menu screens. Those have input handling of their own.
