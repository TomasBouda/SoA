# The missing body hit sounds

Since release the game has never played the sounds of a hit on a human body. It
reports it in `tracefile.log`:

```
SoundObject.cpp(149) : TRACE_ERROR: Sound not found. 'SchussTreffer_Körper_1.wav'
SoundObject.cpp(150) : TRACE_ERROR: Error: ASSERT_HRESULT(0x80004005)
```

## The cause

The files **are** in `sounds.ubn` — the bug is in how the packing tool wrote
them into the archive. A ZIP carries the file name twice, in the central
directory and in the local header, and here those two copies do not match:

| place | umlaut byte | encoding |
|---|---|---|
| central directory of the archive | `0x94` | cp437 (DOS) |
| local header of the same entry | `0xF6` | cp1252 (Windows) |
| what `soa.exe` asks for | `0xF6` | cp1252 (Windows) |

So the tool wrote each copy of the name in a different code page. The archive
reader in the game starts from the central directory, so it looks for `0xF6`,
finds `0x94`, and the file does not exist.

The mismatch is fundamental enough that even Python refuses to extract the
entry:

```
zipfile.BadZipFile: File name in directory 'SchussTreffer_K\x94rper_1.wav'
and header b'SchussTreffer_K\xf6rper_1.wav' differ.
```

It affects five files, `SchussTreffer_Körper_1.wav` through `_5.wav`.

## The fix

`tools/fix_sounds.py` pulls the data out of the archive by hand (it goes around
the name check, reads the local header and decompresses the content) and saves
it loose next to the game under the name the game looks for:

```
_patched/Sounds/InGame/weapons/SchussTreffer_Körper_1.wav ... _5.wav
```

To run it:

```bash
cd _research
python tools/fix_sounds.py
```

### Verified

It works. After the loose files were deployed, every
`Sound not found. 'SchussTreffer_Körper_*'` line disappeared from
`tracefile.log`, even though there was plenty of shooting in that run. A
23-year-old bug is fixed.

A side finding that comes in useful elsewhere: **the engine reads loose files
next to the game and prefers them over the archive.** Any asset can therefore
be replaced or added without touching the `.ubn`, which matters —
`sounds.ubn` is 125 MB and repacking it for five files would be awkward.

## Unrelated, but from the same log

- `Sound not found. 'querschlaeger1.wav'` — this file is in none of the
  archives at all, so it is not an encoding problem but an asset that never
  made it into the game. Querschläger = a ricochet.
- `Error: LoadPNG(filename: 'C:\Game\Multiplayer\Pictures\') failed` — the path
  ends with a slash and no file name, the game is missing the name of the
  avatar image.
