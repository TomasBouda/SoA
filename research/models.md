# The 3D models

`objects.ubn` holds **1253 `.diff3D` files, 225 MB** - every soldier, vehicle,
building, tree and animal the game draws. It was the last big closed box in the
game's data and nothing about the format was written down anywhere.

[tools/diff3d.py](tools/diff3d.py) reads it. **1241 of the 1253 come out**; the
eleven that do not are the `Camera` folder, which holds camera paths and has no
geometry in it at all, and one file whose name the archive spells two different
ways.

## It is the same serialiser as everything else

The sixteen byte magic that opens a save opens a model too, with `0x34` in front
instead of `0x38`. Strings are length-prefixed the same way, which is why the
node names and the texture names come out readable without any work.

The models were exported from 3ds Max and **every file still carries the path of
the `.ASE` it came from** - `C:\proof\equipment\ammobox.ASE`,
`C:\proof\units\rager\rager_h.ASE`. The authors' own directory layout is still
in there, `proof` and all.

## A vertex is forty bytes, a face is twenty

A vertex is a Direct3D vertex of its day:

    x y z   nx ny nz   diffuse   specular   u v

A face is two fields and three indices:

    flags   ?   i0 i1 i2

**Neither field is understood and neither is named.** The second one looked like
a material id - a crate has 3 on its sides and 5 on its lid, which fits
beautifully - right up until a night sight turned up with floats in the same
place. Both were tried as validity tests while writing the reader and **both cost
models that read perfectly well**: requiring the first to be zero threw away 178
of them. They are carried through unread.

## How the reader finds a mesh, and why that way

**Backwards from the vertices**, because they are the one thing in the file that
announces itself. The exporter wrote white into every vertex's diffuse colour, so
a vertex list appears as `FF FF FF FF` repeating on a forty byte stride, and
nothing else in the file does that for long.

From that anchor the rest is arithmetic. The two counts - faces, then vertices -
are written together some way in front of the face list, and how far in front
varies between files: fifty two bytes usually, eighty where the node carries an
extra block. Rather than decide which, the reader looks for the vertex count
written as a dword anywhere earlier in the file and asks, of each place it
occurs, whether the number in front of it makes the arithmetic close - face list,
then twenty bytes nobody has explained, then the vertices, landing exactly on the
byte the anchor found.

Searching for the number rather than walking a window is what makes it work on
the large models. The first version looked eight kilobytes back, which is plenty
for a crate and nowhere near enough for a car: the Rager's body is 644 vertices
and 506 faces, so its header sits twenty thousand bytes in front of them, and
four of its nine parts were quietly missing until that was fixed.

**The node header itself is still not understood** and the reader does not
pretend to walk it. That is the honest state of it: enough is known to get the
geometry out, not enough to describe the file.

## Every part is named

The strings in front of a mesh are the node names its authors gave it, and the
reader hands each mesh the last one written before it. That is what turns a list
of vertex counts into something readable:

    0 licht              22 vertices    14 faces
    1 tuer_fahrer        28 vertices    16 faces
    5 karosse_sort0     644 vertices   506 faces
    6 wheel_axle         68 vertices   128 faces
    7 wheel_steer_r      34 vertices    64 faces

`--hide licht,glow,effekt` leaves the lamps and exhaust plumes out of a picture,
which is how the vehicle above was drawn.

## A weapon is stored three times over

`ak74.diff3D` holds `ak74_0`, `ak74_1` and `ak74_2` - **the same 99 vertices and
53 faces in three different places**. They are not levels of detail, which would
differ in size; they are the poses the engine picks between, and `_0` is the one
carrying the muzzle flash as a child, so it is the one in hand. Drawn all at once
a rifle comes up as three rifles lying across each other.

Telling those apart from parts that merely share a name takes the tree, not the
name. A weapon's poses are **the only children the root has** and they all share
one base name; a truck's `wheel_axle_1` and `wheel_axle_2` are two among nine
other parts that are nothing like them - and going by the name alone would have
quietly hidden one of the truck's axles. Only the first pose is drawn; `--poses`
and a box in the browser show the rest.

## In the launcher

The **Models** button opens the browser: the 1253 models down the side with a
search box, one drawn in the panel beside it, dragged to turn and the wheel to
come closer. It draws with WPF's own 3D, so the launcher shows a textured model
with nothing installed and no dependency added.

`launcher/Models.cs` is this reader ported to C# and `ModelsWindow.cs` is only
the window. The two readers were run against each other over the whole archive
and **agree to the decimal** on every part of every vehicle checked - the same
test the save readers get, and worth having, because a format read by guesswork
in two languages is two chances to have guessed differently.

It carries a Targa decoder of its own. WPF has none and 150 of the game's
textures are `.tga`, so there is a short one for the two kinds the game ships -
24 and 32 bit, plain or run length encoded - which returns nothing rather than
rubbish for anything else.

The lamps, glows and effect markers are hidden unless asked for, for the reason
that made them worth noticing in the first place: a lamp is a flat quad lying
across the whole car and it reads as a broken model.

## What is not done yet

## Where a part goes

**The file carries a tree, and it is the last thing in it.** A table of chunks
sits at the end - `type | children | offset | size`, sixteen bytes each - and the
chunks are written **depth first**, so a chunk is followed by its own children,
as many as its second field says. That second field is a **child count**;
reading it as anything else is what kept the parts in the wrong places for so
long.

Types: `0x10000` a node, `0x10002` a mesh, `0x10003` the materials. A node chunk
is the 104 byte header - a matrix and two bounding spheres - with its name
straight after it, and a mesh belongs to the node it hangs off.

The Rager comes out like this, and it reads exactly as a modeller would have
built it:

    root
    |-- main
    |   |-- karosse_sort0        the body, and its own mesh last of its children
    |   |   |-- licht            the lamps
    |   |   |-- effekt_*, glow_* exhaust and glows, no geometry
    |   |   |-- tuer_fahrer      four doors, one mesh each
    |   |   \-- (the body mesh)
    |   \-- dmyi_*               where the crew sit
    |-- effekt_staub_*           dust
    \-- wheel_axle, wheel_steer_r, wheel_steer_l

**A part's place is its own matrix multiplied out through every parent above
it**, and that is the piece that was missing. Look at where the wheels hang: off
the **root**, while the doors hang off the body. So a door takes three matrices
and a wheel takes one, and **no single rule about which parts to transform could
ever have got both right** - which is exactly what the three earlier attempts
kept running into.

Every mesh in 401 models tested comes out placed and named this way.

### Three readings that were wrong

Kept because each looked right and cost an afternoon:

* **Apply every node's matrix once.** The doors leave the car - they were
  missing their two parents.
* **Apply it only to the parts modelled around the origin.** Fixes the wheels
  sitting inside the body and puts the Rager's front wheels a hundred units in
  front of it.
* **Chain it through a tree guessed from the bounding spheres.** A node's second
  sphere is its bounds in its parent's space, so containment should name the
  parent - and it does give a plausible tree. Too many nodes share a radius for
  it to give the right one, and the model scatters.

The tree was never going to come out of the geometry. It came out of the engine:
`diff3dLoader.cpp` reads a node with `push 0x68` - 104 bytes - tests a flags byte
for a matrix, the spheres and the name, then **calls itself** for each child and
hands the result to `objects.cpp` to be added to the parent. Following that back
into the file is what found the table.

## Textures

Every model names its textures with no path, and `textures.ubn` holds 714 of
them - 458 `.png`, 150 `.tga`, 87 `.bmp` - so they are matched on the file name
alone. The `Winter` folder holds a second copy of many under the same name and
the ordinary one wins.

`--png` draws with them, sampled through the texture coordinates in the vertices,
z buffered and lit by one light. `--plain` turns the textures off.

### Which texture a face uses

**The first field of a face is a material index.** The material list follows the
exporter's own line - the `.ASE` path - as a count and then that many materials,
each written as `1`, a flag and the name of its texture, or as a bare `0` when it
has none. Every number arrives wrapped as `0C 00 00 00 | 00 00 00 00 | value`,
which is how they are told apart from the string that follows.

**The materials without a texture are the whole difficulty.** Counting texture
names alone very nearly works, and then fails silently: the M60 has seven
materials and six names, with the nameless one third in the list, so every
material after it would be off by one and the rifle would be drawn with its own
muzzle flash. Parsing the list properly, **1228 of the 1241 models have every
face naming a material that exists**, one points past the end and twelve have no
material list at all.

It reads sensibly, which is the other half of the check. The AK-74's body uses
`equipment.tga` and its muzzle flash uses `flash_2.bmp`; the Rager's `licht` node
uses `carlight.bmp` and its body uses `rager.png`.

The second field of a face is still not understood. It holds small bitmasks in
some models - 3 on the sides of a crate and 5 on its lid - and arbitrary 32 bit
values in others, which is what 3ds Max smoothing groups look like when they are
assigned by hand and when they are auto-generated. That is a guess and it is not
relied on anywhere.

* **The node transforms** - and it turns out they are not needed for placement.
  The first look at a rendered vehicle showed flat panels lying under it and the
  obvious conclusion was that the parts were each in their own coordinate system
  and wanted a matrix applied. They are not. **The panels are its lights**: the
  model's first node is called `licht`, it has `glow_bremslicht_1` and
  `_2` beside it, and one of its two textures is `carlight.bmp`. Hidden, the
  Rager assembles into a pickup - `karosse_sort0`, four doors, `wheel_axle`,
  `wheel_steer_l` and `_r` - with no transform applied at all.

  So the geometry is already in one shared space, and the per-node matrix is
  presumably for the parts that move rather than for putting them where they
  belong. That is worth knowing before anybody spends an afternoon on it.
## The animation tracks

A `0x10001` chunk hangs off a node and holds its movement over time. **These are
solved**, and they are keyframes rather than baked frames - the shape 3ds Max
writes, which fits everything else about these files.

Two lists behind one header, and the header describes both, which is what makes
it checkable:

    header 32 | kind | where the second list starts
              | n keys of 40 bytes  |  n+1 keys of 84 bytes

* **40 bytes**: a time, a position, and two more triples - the tangents either
  side of the key.
* **84 bytes**: the same moments as whole transforms - a time, a quaternion, and
  a 4x4 matrix.

The two lengths and the header have to add up to the size of the chunk, and in
every animation measured they do to the byte. **The times are milliseconds** and
the keys fall every 100 of them: a walking antelope is 29 keys over 2.8 seconds,
a soldier standing and gesturing is 198 over 19.7.

The second list always holds exactly one key more than the first. Whether that
is a closing sample or an interval count is not known.

**Whose movement it is** matters: the tracks belong to the *dummy* nodes -
`dmyp_middle`, `dmyw_001`, `dmyw_002` - which is where a character carries a
weapon and where the game hangs things off him. The body itself is not in them.

## The body's animation

**Solved, and the loader is what solved it** - the same lesson as the node tree,
which also did not come out of staring at the bytes.

`diff3dLoader.cpp` reads a mesh chunk at `0x6392F0`, and the first thing it does
is `push 0x28` and then check what came back. **The mesh chunk header is forty
bytes**, and the four fields the loader refuses to go on without name themselves
once you see them beside a model you know:

    +0   40          the header's own size
    +4   3           a kind
    +8   1
    +12  faces
    +16  vertices
    +20  frames      1 for a crate, 29 for a walking antelope
    +24  a sphere - radius, then centre

That `frames` field is the whole answer, and it had been sitting in front of the
face list all along.

**Frame zero is the static mesh** - the 40 byte vertices, with the colour and the
texture coordinates. Every frame after it is a sixteen byte header - its own
size, **the time in milliseconds**, a one, and the step - and then the vertex
list again at **24 bytes each: a position and a normal, and nothing else**,
because the colour and the coordinates do not change.

A walking antelope is 29 frames at 100 ms, running 0 to 2800, and the count
matches the 29 keys of the dummy track exactly. Walking the 28 stored frames
ends one byte short of the end of the chunk, which is the alignment byte in
front of the first header - the frame headers do not start on the byte the
vertex list ended on, and skipping up to three is what makes the walk close.

    python diff3d.py laufen --png deer.png --frame 14

Over 221 models: 110 animated meshes, 3317 frames, every one of them with as
many vertices as its mesh.

* **A model viewer in the launcher.**
* **A model viewer in the launcher.** Everything it needs is now here except
  the window: WPF draws 3D without any dependency, so a tree of the 1253 models
  with one turning under the mouse is a self-contained piece of work.
* **The textures.** Every model names its own - `rager.png`, `equipment.tga` -
  and they are ordinary pictures in `textures.ubn`. Nothing maps a face to one
  of them yet, which is the second field of a face and the reason it was worth
  looking at.

## Using it

    python diff3d.py ammobox                 what is in it
    python diff3d.py bmp1_h --png bmp.png    a picture, with its texture on it
    python diff3d.py bmp1_h --png b.png --hide licht,glow,effekt,flash
    python diff3d.py rager_h --obj car.obj   as a Wavefront .obj
    python diff3d.py --check                 read every model in the archive

The picture is the check that matters. A model that parses into nonsense looks
like nonsense immediately, and no amount of counting vertices says as much as one
picture of a crate that is shaped like a crate.
