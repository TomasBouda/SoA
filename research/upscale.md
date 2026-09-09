# Texture upscaling

Doubling the size of the game textures with Real-ESRGAN. Deployed and working —
but the visual gain is smaller than one would expect, and it is worth knowing
why.

## What is done

| set | source | enlarged | note |
|---|---|---|---|
| objects, buildings, units, characters | `textures.ubn` | **695** (458 PNG, 150 TGA, 87 BMP) | everything |
| ground and sky | `terrain.ubn` | **433** | `base/` and `skies/` |
| roads, tracks, surface variants | `terrain.ubn` | **43** | the sheets from `details.txt` |

Deployed as loose files in `_patched/textures/` and `_patched/terrain/` — the
engine reads them in preference to the archive, so the `.ubn` files stay
untouched. The tools: `tools/upscale_textures.py`, `tools/upscale_terrain.py`,
the model in `tools/esrgan.py` (RRDBNet written out directly, without
`basicsr`).

The speed is negligible: 0.07 s per texture on an RTX 3080 Ti, the whole run
under a minute. The added data comes to 266 MB (objects) + 65 MB (terrain).

## Why it does not look much better

**Mipmapping eats most of the gain.** The engine builds a pyramid of smaller
copies of every texture and at an ordinary camera distance it draws a lower
level. A 512² texture shown on screen at the same size as before is drawn from
the level corresponding to the original 256². The difference only shows once
the camera goes down very low. This holds for every upscale in every game.

**The ground surface stayed unchanged at first.** The detail textures — roads,
tracks, grass variants, dirt — are addressed by sheet coordinates and stayed
original for a long time even though they cover most of the screen. Sorted out
later, see below.

**The geometry is from 2002.** A sharper texture does not fix a vehicle having a
few hundred triangles.

## The terrain sheets: the coordinates are proportional

`details.txt` does not address regular halves but hand-cut rectangles packed
into shared 256×256 sheets:

```
14;...;standard/Asphaltstrasse.png;3;127;74;198
16;...;standard/Asphaltstrasse.png;77;130;109;251
```

It looks like absolute pixels, but **the engine divides them by a fixed sheet
size, not by the real size of the loaded image**. So they are proportional: an
enlarged sheet falls into place on its own and `details.txt` must not be
touched.

Verified in the game on both variants, on the same road in mission 3:

| what was deployed | how it turned out |
|---|---|
| sheets 2×, `details.txt` with recomputed coordinates | the road assembled from the wrong pieces — bends instead of straight runs |
| sheets 2×, `details.txt` left from the archive | a continuous, sharper road |

The recomputed coordinates overflow the edge of the sheet and reach into the
neighbouring cut — hence the bends. A test run with magenta lines around every
cut showed it plainly: the lines lay inside the tiles, not on their edges.

`tools/upscale_details.py` deploys it: 43 sheets from the `standard`, `desert`,
`winter`, `usa` and `unborn` folders, with `details.txt` left to the archive.

The `displace` folder stays out of this for a different reason — those are not
images to look at but data for deforming the terrain geometry, where the
artefacts of an upscaler would show up as waves in the ground.

### Two mistaken notes that held this up

Originally it said here that the engine builds its own sheet of fixed-size tiles
according to `TexGen.dat` and that the details therefore cannot be enlarged.
`TexGen.dat` is in fact readable text about scattering vegetation by the height
and the slope of the terrain — it has nothing to do with sheets, see
[architecture.md](architecture.md).

The second note claimed that enlarging the sheets themselves breaks the roads.
That variant is exactly the right one; what broke them was the accompanying
recomputation of the coordinates.

## The GUI: checked, enlarging it makes no sense

The interface in `gui.ubn` is assembled from 256×256 sheets that are the tiles
of larger areas. The `.gui` files hold a grid for them, the `.LAY` files place
the elements by pixel coordinates — the minimap is 134×134 for instance, the
inventory 134×538.

Enlarged sheets made no difference in the game whatsoever. Before drawing that
conclusion two other explanations had to be ruled out — and both turned out to
be real traps:

- **The tested file may not be drawn at all.** The first attempt enlarged
  `PANEL_MAIN.png`, but the left panel with the minimap and the slots is
  `PANEL_SELECTION.png`, the portraits are `Faces.png` and the bottom bar is
  `gfx_quickselect.png`. The only way to tell was to pull the images out of the
  archive and lay them out in an overview grid.
- **Warnings in the log prove nothing.** The rise of `LoadPNG: Warning: surface
  size don't match resource size` from ten to ninety comes while loading a
  mission, where 458 enlarged object textures are loaded - and those visibly
  work.

### The decisive test

A bold magenta cross was drawn across `PANEL_SELECTION.png` and `Faces.png` and
the files were deployed loose. It is visible in the game — across the whole
panel, at full width and in the right proportions.

Both conclusions follow at once:

1. **The game does read loose files for the GUI.** So the interface can be
   redrawn, recoloured or translated by slipping in an image of your own at the
   same size. That is a usable route to changing the look.
2. **The extra size is thrown away** - written here, and it is wrong. See
   *The portraits* below, where a screenshot settles it: the enlarged sheet is
   read, the source rectangles are taken proportionally, and the picture is
   drawn from the larger texture. What had been measured was that enlarged
   **panels** looked no different, which is a weaker claim - and a panel is a
   flat frame stretched over a large area, about the worst place to look for
   the difference.

### Changing the coordinates does not help either

There was one more route on offer: enlarge the images **and** the coordinates in
the `.LAY` files. A test ruled it out — doubling the size of the minimap made it
twice as large in the game and it grew over the neighbouring elements. The
coordinates are absolute in a fixed design space that the engine maps onto the
screen with a constant scale. The area and its presentation therefore grow by
the same amount and the result is **a larger UI at the same quality**, not a
sharper one.

A sharper interface would need that scale reduced with the elements left in
place, which means changing the exe. Through the data alone it cannot be done.
See [architecture.md](architecture.md).

## The levers that decide how much of the upscale is visible

- [x] **`TextureDetail`: zero is the highest quality.** The registry holds `0`,
      the same as `ObjectDetail`, and it was not clear whether that meant the
      highest or the lowest. The configuration dialog of the game shows the
      maximum, so the game does not shrink the textures on load and the
      enlargement is not thrown away.
- [x] **`Mipmapping = disabled` in `dgVoodoo.conf`** (previously `appdriven`).
      Deployed. The full resolution is always drawn, so it is sharper at a
      distance as well; the price is shimmering on distant surfaces. Mipmapping
      was exactly why so much of the upscale was being lost — the engine builds
      a pyramid of smaller copies of every texture and at an ordinary camera
      height it draws a lower level. It can be switched at run time in
      `dgVoodooCpl.exe`, so a comparison takes a moment.

Done:

- [x] **The detailed ground surface.** It turned out there was nothing to
      repack — it is enough to enlarge the sheets and leave `details.txt` alone.

## What else the wrapper can do for the look

The textures were the obvious lever and they gave less than expected. Reading
`dgVoodoo.conf` through properly turns up several more, and unlike an upscale
they are one line each and reversible.

**Already at the top.** Antialiasing is at 8x, anisotropic filtering at 16, the
dithering at high quality, and mipmapping is off - which is what finally lets
the upscaled textures show at all, since the pyramid was eating them.

**Taken up, offered in the launcher under *Look*.**

| setting | what it does |
|---|---|
| `PhongShadingWhenPossible` | the engine lights the corners of a triangle and smears the result across it; this lights every pixel instead. It shows most on the rounded things - hulls, helmets, barrels - which is exactly where per-vertex lighting looks worst on a low-poly model |
| `Bilinear2DOperations` | the interface is drawn for 640 by 480 and blown up with each pixel repeated, which is where its stair steps come from. This interpolates instead |

**Not taken up, worth a try.**

* `NPatchTesselationLevel` - the wrapper can round low-polygon geometry out
  with curved point-normal triangles. On models from 2002 this is the one
  change that could touch the thing an upscale cannot, which is the geometry.
  Whether this engine feeds it usable normals is unknown, and it is the sort of
  setting that either looks better or makes everything melt.
* `Resampling` - `bilinear` now, and `lanczos-3` is on offer. It only matters
  where the wrapper scales the final image, so windowed and forced resolutions.
* `Brightness`, `Color`, `Contrast` in `[General]`, all at 100. A blunt
  instrument next to correcting the pictures themselves, but it reaches the
  world as well as the interface, which nothing else here does.

## The portraits

The faces are the worst-served pictures in the game and the case where an
upscale should matter most. Each one is about 36 by 50 pixels, seven to a row on
a 256 by 256 sheet - `GUI_Mission/Faces/Faces.png` and `Faces2.png` in a
mission, `GUI_Bunker/Lazarettpanel/faces01..05.png` in the infirmary - and the
engine blows them up four or five times on a modern screen. A portrait is a
mosaic.

**The loader keeps the size it read.** At `0x621313`, after the comparison that
produces `LoadPNG: Warning: surface size don't match resource size`, the surface
description is filled from the picture's own width and height - `[ebp-0xC0]` and
`[ebp-0xC4]`, the values that failed the comparison - and not from the declared
ones. The warning is a warning and nothing else. So a larger sheet does survive
as far as the texture, which is not what the section above concluded.

Whether it survives as far as the screen depends on how the source rectangle is
taken when the face is drawn. Proportional coordinates and it works; pixel
coordinates in the old 256 space and the wrong quarter of the sheet appears,
which would be plain to see. The magenta cross came out "at full width and in
the right proportions" on an enlarged sheet, which points at proportional - but
that is an inference, not a measurement.

[tools/upscale_faces.py](tools/upscale_faces.py) enlarges the seven sheets and
nothing else. Real-ESRGAN doubles them; the alpha is resampled on its own and
put back, because it is what cuts each head out of its square and no model has
seen it. `--lanczos` does the same without the model, which is the fair
comparison. `--off` deletes them again.

### It works, and the numbers say why

A screenshot with the frames in place answers both questions at once.

**The mapping is proportional.** Every portrait comes up neatly inside its
frame - the big one in the selection panel and the small ones along the bottom
- each showing its own face. Pixel coordinates in the old 256 space would have
shown the top-left quarter of a face magnified, with a piece of frame across
it. They do not.

**And there is room for the detail.** Measured off the screenshot at 1920 by
1080, the selected character's portrait is drawn **75 by 94 screen pixels**:

| | |
|---|---|
| the cell in the original sheet | 32 x 48 |
| enlarged | 64 x 96 |
| drawn on screen | 75 x 94 |

So the engine was stretching a 32 by 48 picture over 75 by 94 - two and a third
times, which is exactly why a portrait was a mosaic - and now draws a 64 by 96
one into it at nearly one to one. That is the whole gain, and it is the largest
of any upscale in this project, because it is the only place where the source
was smaller than the area it had to fill.

Doubling is therefore the right amount at this resolution. Quadrupling would
only matter on a screen big enough to draw a portrait past 128 pixels across.

Deployed in package 1.13.0.

### Where the faces are, exactly

Not guessed at - `Mission.gui` declares `RES_MISSION_FACE1` to `55` and
`Bunker.gui` declares `RES_BUNKER_FACE1` upwards, and every record carries the
rectangle as four floats after the name, in the same shape `Items.gui` uses for
the item icons:

| | |
|---|---|
| cell | 32 by 48 |
| pitch | 33 by 49 - one pixel between them |
| first cell | at (1, 1) |
| per sheet | 7 across, 5 down, so 35 |

55 faces in a mission, so the second sheet is two thirds empty, which is why it
looks wrong at a glance and is not.

The first attempt at the frame diagnostic divided the sheet by seven and five -
36.6 by 51.2 - and the frames walked away from the faces a pixel at a time.
Visible immediately in the sheet, and it would have made the answer in the game
unreadable, since a frame that does not fit its face cannot tell whether the
face was fetched correctly.

### Which model, and one face at a time

The first deployment used the photographic model and the faces came out ugly -
mushy, with invented skin texture, looking unwell. The reason was written in
`tools/esrgan.py` before any of this started: on small stylised pictures the
photographic model invents detail and deforms the features, and the model
trained on drawn content keeps the shapes. The default was simply never
changed.

Laid side by side over six faces, the order is not close:

| | |
|---|---|
| as the game has it | blocks |
| `--lanczos` | soft, faithful, invents nothing |
| `--model photo` | invents pores and wrinkles that were never there |
| `--model anime` | keeps the shapes, sharpens the edges, reads as a portrait |

`anime` is the default now. `--lanczos` remains the conservative choice: at the
size a portrait is actually drawn, 75 by 94, the two are closer than the sheets
suggest, and lanczos cannot be accused of making anything up.

Two other things were wrong and are fixed with it:

* **Face by face, not sheet by sheet.** A sheet is 35 heads with transparent
  gutters between them; a model run over the whole thing takes a neighbour's
  ear as context for this one's jaw. Each cell is now taken out on its own -
  the rectangles above say exactly where - and put back.
* **Face by face lost what is not a face.** Building the enlarged sheet on a
  blank canvas and pasting only the 35 declared cells onto it drops everything
  else - and `Faces.png` has 1151 opaque pixels outside the grid, the widest of
  them the helmeted Unborn soldier in the bottom right corner, which reaches to
  x 254 where the last cell ends at 231. He came out sliced in half. The sheet
  is now enlarged whole first and the faces laid over it, so nothing can go
  missing whether or not anyone thought to look for it.
* **The transparent surround was black.** `convert('RGB')` lays transparency
  onto black, so every head went into the model wearing a black halo which the
  model dutifully sharpened into a dark rim. The edge colour is spread outwards
  first, so there is nothing there to sharpen.

## The rest of the interface: measured, not attempted

Left where it stands, but with the numbers written down so it need not be
measured again.

**The mission screen is designed for 800 by 600**, not the 640 by 480 the main
menu uses - `LAY_MISSION_MOVIECUT2` runs from 0,540 to 800,600 and the quick
selection bar to 794,592. Each screen has its own design space.

**The panel art is declared 1:1 with that space.** `LAY_MISSION_INVENTORYPANEL`
is 126 by 218 and its source `RES_MISSION_PANEL_MAIN_2` is 126 by 218. So on a
1920 by 1080 screen every panel is magnified 2.4 across and 1.8 down:

| | source | on screen |
|---|---|---|
| minimap | 126 x 126 | 302 x 227 |
| selection panel | 126 x 166 | 302 x 299 |
| inventory | 126 x 218 | 302 x 392 |
| a portrait | 32 x 48 | 75 x 94 |

The portraits sit in exactly the same ratio as the panels, and enlarging them
worked. That makes the older conclusion - that enlarging the interface is
pointless - suspect for the same reason the portrait one was: it was judged by
eye on panels, before it was known that a larger sheet is read at all.

**Two things would have to happen.** The 37 interface sheets enlarged the way
the faces were, per element and with the model for drawn content; and
`hud_contrast.py` folded into the same tool, because the two write the same
files and cannot both own them.

**And one question first.** 2.4 across against 1.8 down is not the same number.
If that is what the engine really does, the whole interface is stretched by a
third on a 16:9 screen and no amount of sharpening addresses it. Measuring it
off a portrait gave an answer in between, which proves nothing: the rectangle a
panel sits a face in need not have the shape of the source cell. The clean test
is the one that settled the portraits - put a **circle** on a panel sheet and
photograph it. A circle means the shape is kept; an ellipse means it is not,
and then the stretch is the problem, not the resolution.
