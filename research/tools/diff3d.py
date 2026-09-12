"""Read the game's 3D models.

`.diff3D` is the last big closed box in the game's data: 1253 files and 225 MB
of `objects.ubn`, everything the engine draws that is not terrain or interface.
Nothing about it was documented anywhere, and this is what it turned out to be.

It is written by **the same serialiser as everything else here** - the sixteen
byte magic that opens a save opens a model too, with `0x34` in front instead of
`0x38`. Strings are length-prefixed the same way, which is how the texture names
and the node names come out readable.

The models were exported from 3ds Max: every file carries the path of the `.ASE`
it came from, `C:\\proof\\equipment\\ammobox.ASE` and the like, so the original
author's directory layout is still in there.

What a mesh is
--------------
A **vertex is 40 bytes** and is a Direct3D vertex of its day - position, normal,
a diffuse colour, a specular colour, and one pair of texture coordinates:

    x y z   nx ny nz   diffuse   specular   u v

A **node** is a matrix, two bounding spheres and a name, in that order, and the
file's own header at `0x34` has exactly the same shape. The matrix places the
part in the model and it has to be applied: the two spheres are the same bounds
before and after it, which is what proves the convention rather than assuming it.
Without it a vehicle's wheels sit inside its body, because a wheel is modelled
around the origin so that it can turn.

A **face is 20 bytes**: two fields and three indices.

    flags   ?   i0 i1 i2

Neither field is understood and neither is named. The second looked like a
material id - a crate has 3 on its sides and 5 on its lid, which fits beautifully
- until a night sight turned up with floats in the same place. Both were tried
as tests and both cost models that read perfectly well, so they are carried
through unread.

Both counts are written before the lists, as `faces | a field that has been
zero everywhere measured | vertices`, and that is what makes the blocks
findable: nothing else in the file has numbers that predict their own length
that exactly.

How this reads it, and why
--------------------------
Backwards from the vertices, because that is the one thing in the file that
announces itself. The exporter wrote white into every vertex's diffuse colour,
so a vertex list appears as `FF FF FF FF` repeating on a forty byte stride and
nothing else in the file does that for long.

From that anchor the rest follows by arithmetic. The two counts - faces, then
vertices - sit some way in front of the face list, and how far varies between
files: fifty two bytes usually, eighty where the node carries an extra block.
Rather than decide which, every position is tried and the one kept is where the
arithmetic closes exactly - face list, twenty bytes nobody has explained, then
the vertices, landing on the byte the anchor found. A wrong guess misses by more
than a byte practically always.

The node header itself is *not* understood, and this does not pretend to walk
it. `--check` runs the whole thing over every model in the archive and says how
many come out.

    python diff3d.py ammobox                 what is in it
    python diff3d.py ammobox --png box.png   a picture, to see whether it is right
    python diff3d.py ammobox --obj out.obj   as a Wavefront .obj
    python diff3d.py --check                 parse every model in the archive
"""
import argparse
import io
import os
import struct
import sys
import zipfile

GAME = os.environ.get('SOA_GAME', r'F:\Games\SoA-Package\Game')

# The magic every file this engine serialises opens with, bar the first byte,
# which says which class wrote it. A model is 0x34; a save is 0x38.
MAGIC_TAIL = bytes([0xF9, 0xB3, 0x0A, 0x62, 0x93, 0xD1, 0x11, 0x9A,
                    0x2B, 0x08, 0x00, 0x00, 0x30, 0x05, 0x12])
MODEL_CLASS = 0x34

VERTEX = 40
FACE = 20

# The diffuse colour the exporter wrote into every vertex.
WHITE = bytes([0xFF, 0xFF, 0xFF, 0xFF])


class Mesh(object):
    def __init__(self, at, faces, verts):
        self.at = at
        self.node = None            # the node name written in front of it
        self.frames = []            # [(time in ms, [(x, y, z, nx, ny, nz)])]
        self.variant = 0            # 0 unless this is a second pose of the same thing
        self.matrix = None          # the node's matrix, as written
        self.placed = False         # whether that matrix was applied
        self.faces = faces          # [(flags, material, i0, i1, i2)]
        self.verts = verts          # [(x, y, z, nx, ny, nz, diffuse, specular, u, v)]

    def __len__(self):
        return len(self.faces)


class Model(object):
    def __init__(self, path, raw):
        self.path = path
        self.raw = raw
        self.name = None            # the node the file opens with
        self.source = None          # the .ASE it was exported from
        self.textures = []          # the ones actually named, in order
        self.materials = []         # one per material, None where it has none
        self.tracks = []            # (node name, the animation track on it)
        self.meshes = []


def strings(raw, start=0):
    """Every length-prefixed string, the same convention the saves use."""
    out = []
    i = start
    while i < len(raw) - 1:
        n = raw[i]
        if 3 <= n <= 96 and i + 1 + n <= len(raw):
            body = raw[i + 1:i + 1 + n]
            if all(32 <= c < 127 for c in body):
                out.append((i, body.decode('ascii')))
                i += 1 + n
                continue
        i += 1
    return out


def looks_like_a_texture(text):
    low = text.lower()
    return low.endswith(('.bmp', '.tga', '.png', '.jpg'))


def vertex_blocks(raw):
    """Where the vertex lists are, found by their diffuse colour.

    Every vertex carries a diffuse colour and the exporter wrote white into it -
    `FF FF FF FF`, twenty four bytes into a forty byte record. So a vertex list
    shows up as that value repeating on a forty byte stride, and nothing else in
    the file does that for long. This is the anchor everything else hangs off,
    because it needs no knowledge of the node header at all.
    """
    hits = set()
    at = raw.find(WHITE)
    while at >= 0:
        hits.add(at)
        at = raw.find(WHITE, at + 1)
    found, used = [], set()
    for h in sorted(hits):
        if h in used or h < 24:
            continue
        n = 0
        while h + n * 40 in hits:
            used.add(h + n * 40)
            n += 1
        if n >= 4:
            found.append((h - 24, n))
    return found


def white_enough(raw, start, count):
    """Whether `count` vertices from `start` really are a vertex list.

    Not every vertex is white - a few carry a colour of their own - so this
    asks for most of them rather than all, and that tolerance is the difference
    between reading a model and rejecting it.
    """
    if start + count * VERTEX > len(raw):
        return False
    white = 0
    for k in range(count):
        if struct.unpack_from('<I', raw, start + k * VERTEX + 24)[0] == 0xFFFFFFFF:
            white += 1
    return white >= count * 0.8


def faces_fit(raw, at, n_faces, n_verts):
    faces = []
    for k in range(n_faces):
        off = at + k * FACE
        if off + FACE > len(raw):
            return None
        flags, material, i0, i1, i2 = struct.unpack_from('<5I', raw, off)
        if i0 >= n_verts or i1 >= n_verts or i2 >= n_verts:
            return None
        # Neither of the two fields is tested. Both were tried and both cost
        # models: requiring the first to be zero threw away 178 that read
        # perfectly well, and capping the second threw away more, because in
        # some models it holds a float. What is left - the arithmetic closing
        # on the byte the anchor found, and every index naming a vertex that
        # exists - is enough on its own.
        faces.append((flags, material, i0, i1, i2))
    return faces


def read_vertices(raw, at, count):
    verts = []
    for k in range(count):
        off = at + k * VERTEX
        x, y, z, nx, ny, nz = struct.unpack_from('<6f', raw, off)
        diffuse, specular = struct.unpack_from('<2I', raw, off + 24)
        u, v = struct.unpack_from('<2f', raw, off + 32)
        if x != x or abs(x) > 1e6 or abs(y) > 1e6 or abs(z) > 1e6:
            return None
        verts.append((x, y, z, nx, ny, nz, diffuse, specular, u, v))
    return verts


def mesh_from(raw, vert_start, count):
    """One mesh, worked out backwards from where its vertices begin.

    The two counts are written together - faces, then vertices - some way in
    front of the face list, and how far in front varies between files. Rather
    than decide how far, this looks for the vertex count written as a dword
    anywhere earlier in the file and asks, of each place it occurs, whether the
    number in front of it is a face count that makes the arithmetic close: face
    list, then twenty bytes nobody has explained, then the vertices, landing
    exactly on the byte the anchor found.

    Searching for the number rather than walking a window is what makes this
    work on the large models. The first version looked eight kilobytes back,
    which is plenty for a crate and nowhere near enough for a car: its body has
    644 vertices and over a thousand faces, so its header sits twenty thousand
    bytes in front of them.
    """
    want = struct.pack('<I', count)
    best = None
    at = raw.find(want, 0, vert_start - 32)
    while at >= 0:
        h = at - 4
        if h >= 0:
            n_faces = struct.unpack_from('<I', raw, h)[0]
            if 0 < n_faces <= 200000:
                face_start = vert_start - 20 - n_faces * FACE
                if h + 8 < face_start and face_start - h <= 512:
                    faces = faces_fit(raw, face_start, n_faces, count)
                    if faces is not None and white_enough(raw, vert_start, count):
                        verts = read_vertices(raw, vert_start, count)
                        if verts is not None and (best is None or n_faces > len(best.faces)):
                            best = Mesh(face_start, faces, verts)
                            best.header = h
                            best.vert_start = vert_start
        at = raw.find(want, at + 1, vert_start - 32)
    return best


def materials(raw, after):
    """The material list: the texture each one uses, or None where it has none.

    It follows the exporter's own line - the `.ASE` path - as a count and then
    that many materials. A material is written as `1`, a flag, and the name of
    its texture, or as a bare `0` when it has none, and the untextured ones are
    why counting texture names alone does not work: the M60 has seven materials
    and six names, with the nameless one third in the list, so everything after
    it would be off by one.

    Each of those numbers arrives wrapped as `0C 00 00 00 | 00 00 00 00 | value`
    - a class id, a field that is always zero, and the value - which is how they
    are told apart from the string that follows.
    """
    at = after

    def number():
        nonlocal_at = at
        if nonlocal_at + 12 > len(raw):
            return None, nonlocal_at
        a, b, c = struct.unpack_from('<3I', raw, nonlocal_at)
        if a != 12 or b != 0:
            return None, nonlocal_at
        return c, nonlocal_at + 12

    count, at = number()
    if count is None or not (0 < count <= 256):
        return []
    found = []
    for _ in range(count):
        has, after_has = number()
        if has is None:
            break
        at = after_has
        if has == 0:
            found.append(None)
            continue
        _flag, at = number()
        if at >= len(raw):
            break
        n = raw[at]
        if not (3 <= n <= 96 and at + 1 + n <= len(raw)):
            found.append(None)
            continue
        body = raw[at + 1:at + 1 + n]
        if not all(32 <= c < 127 for c in body):
            found.append(None)
            continue
        found.append(body.decode('ascii'))
        at += 1 + n
    return found


def read(path, raw=None):
    if raw is None:
        raw = open(path, 'rb').read()
    if len(raw) < 0x94 or raw[8] != MODEL_CLASS or raw[9:24] != MAGIC_TAIL:
        raise ValueError('%s is not a model' % os.path.basename(path))

    model = Model(path, raw)
    found = strings(raw, 0x90)
    for at, text in found:
        if model.name is None and at == 0x94:
            model.name = text
        elif text.lower().startswith('root node - '):
            model.source = text[len('root node - '):]
        elif looks_like_a_texture(text) and text not in model.textures:
            model.textures.append(text)

    ase = [(at, text) for at, text in found
           if text.lower().startswith('root node - ')]
    if ase:
        model.materials = materials(raw, ase[0][0] + 1 + len(ase[0][1]))

    # The node names, so a part can be called what its authors called it. They
    # are the strings that are neither a texture nor the exporter's own line,
    # and the one belonging to a mesh is the last one written before it. That
    # is what tells a door from a wheel from a light.
    labels = [(at, text) for at, text in found
              if not text.lower().startswith('root node - ')
              and not looks_like_a_texture(text)]
    for vert_start, count in vertex_blocks(raw):
        mesh = mesh_from(raw, vert_start, count)
        if mesh is None:
            continue
        model.meshes.append(mesh)

    place(model, raw)
    return model


def base_name(name):
    """`ak74_2` as `ak74`. A trailing number and nothing else."""
    if not name:
        return name
    cut = name.rstrip('0123456789')
    return cut[:-1] if cut.endswith('_') and cut != name else name


def variants(rows, parent, name):
    """The nodes that are the same thing again, as {chunk: which one}.

    A weapon is written three times over: `ak74_0`, `ak74_1`, `ak74_2`, the same
    99 vertices in three different places, which are the poses the engine picks
    between - `_0` is the one carrying the muzzle flash, so it is the one in
    hand. Drawn all at once a rifle comes up as three rifles.

    They are told apart from parts that merely share a name by **where they sit
    in the tree**: a weapon's variants are the only children the root has, while
    a truck's `wheel_axle_1` and `wheel_axle_2` are two among nine other parts
    that are nothing like them. Counting on the name alone would hide one of the
    truck's axles.
    """
    children = [i for i in range(len(rows))
                if parent[i] == 0 and rows[i][0] == CHUNK_NODE and name.get(i)]
    if len(children) < 2:
        return {}
    bases = set(base_name(name[i]) for i in children)
    if len(bases) != 1 or bases == {name[children[0]]}:
        return {}
    return dict((c, n) for n, c in enumerate(children))


# What one vertex costs in a frame after the first: a position and a normal,
# and nothing else. The colour and the texture coordinates are written once in
# frame zero and do not change, which is why a frame is 24 bytes a vertex
# against the 40 the first one takes.
FRAME_VERTEX = 24


def frames(raw, mesh, until):
    """Every frame after the first, from where the static mesh ends.

    A frame is a sixteen byte header - its own size, the time in milliseconds,
    a one, and the step between frames - and then the whole vertex list again
    at 24 bytes each. Times run from 100 in hundreds, and frame zero is the
    static mesh that has already been read.

    The header does not begin on the byte the vertex list ended on; there is a
    byte of alignment in front of it, and skipping up to three is what makes the
    walk close exactly on the end of the chunk.
    """
    found = []
    at = mesh.vert_start + len(mesh.verts) * VERTEX
    count = len(mesh.verts)
    while at < until - 16:
        head = None
        for skip in range(4):
            h = struct.unpack_from('<4I', raw, at + skip)
            if h[0] == 16 and h[2] == 1:
                head = (h[1], at + skip + 16)
                break
        if head is None:
            break
        when, data = head
        if data + count * FRAME_VERTEX > until:
            break
        verts = []
        for k in range(count):
            verts.append(struct.unpack_from('<6f', raw, data + k * FRAME_VERTEX))
        found.append((when, verts))
        at = data + count * FRAME_VERTEX
    return found


def track(raw, at, size):
    """One node's animation track, or None.

    A track chunk is two lists of keys behind one header, and the header
    describes both - which is what makes it checkable: the two lengths and the
    header have to add up to the size of the chunk, and in every animation
    measured they do, to the byte.

        header 32 | kind | where the second list starts
                  | n keys of 40 | n+1 keys of 84

    The first list is movement: a time, a position, and two more triples that
    are the tangents either side of it - the shape 3ds Max writes a spline key
    in. The second is the same moments as whole transforms: a time, a
    quaternion, and a 4x4 matrix, 84 bytes together.

    The second list always holds exactly one key more than the first. Whether
    that is a closing sample or an interval count is not known.
    """
    if at + 32 > len(raw):
        return None
    hsize, kind, part1, n1, r1, _, n2, r2 = struct.unpack_from('<8I', raw, at)
    if hsize != 32 or r1 != 40 or r2 != 84:
        return None
    if hsize + n1 * r1 != part1 or hsize + n1 * r1 + n2 * r2 != size:
        return None

    moves = []
    for k in range(n1):
        o = at + hsize + k * r1
        when = struct.unpack_from('<I', raw, o)[0]
        f = struct.unpack_from('<9f', raw, o + 4)
        moves.append((when, f[0:3], f[3:6], f[6:9]))
    poses = []
    for k in range(n2):
        o = at + part1 + k * r2
        when = struct.unpack_from('<I', raw, o)[0]
        turn = struct.unpack_from('<4f', raw, o + 4)
        where = struct.unpack_from('<16f', raw, o + 20)
        poses.append((when, turn, where))
    return {'kind': kind, 'moves': moves, 'poses': poses}


def place(model, raw):
    """Put every part where it belongs, through the tree in the chunk table.

    A node chunk is a 104 byte header - a matrix and two bounding spheres - with
    its name straight after it, and a mesh chunk belongs to the node it hangs
    off. A part's place in the model is its own matrix multiplied out through
    every parent above it, and *that* is the piece that was missing: the wheels
    of a vehicle hang off the root while its doors hang off the body, so the
    doors take one more matrix than the wheels do and no single rule about
    which parts to transform could ever have got both right.
    """
    rows = directory(raw)
    if not rows:
        return
    parent = hierarchy(rows)

    matrix, name = {}, {}
    for i, (kind, children, off, size) in enumerate(rows):
        if kind != CHUNK_NODE or off + 104 > len(raw):
            continue
        m = struct.unpack_from('<16f', raw, off + 8)
        if m[15] != 1.0 or not all(x == x and abs(x) < 1e6 for x in m):
            continue
        matrix[i] = m
        for at, text in strings(raw, off + 100):
            if at >= off + 104:
                name[i] = text
                break

    same = variants(rows, parent, name)

    def through(i):
        m = matrix.get(i)
        seen = {i}
        at = parent[i]
        while at is not None and at not in seen:
            seen.add(at)
            up = matrix.get(at)
            if up is not None:
                m = times(m, up) if m else up
            at = parent[at]
        return m

    for i, (kind, children, off, size) in enumerate(rows):
        if kind != CHUNK_TRACK:
            continue
        got = track(raw, off, size)
        if got is None:
            continue
        owner = parent[i]
        model.tracks.append((name.get(owner) if owner is not None else None, got))

    # A mesh chunk sits inside the node it belongs to, so the mesh found at an
    # offset is matched to the chunk that covers it.
    for mesh in model.meshes:
        owner = None
        for i, (kind, children, off, size) in enumerate(rows):
            if kind == CHUNK_MESH and off <= mesh.header < off + size:
                owner = parent[i]
                mesh.frames = frames(raw, mesh, off + size)
                break
        if owner is None:
            continue
        mesh.node = name.get(owner)
        at = owner
        while at is not None:
            if at in same:
                mesh.variant = same[at]
                break
            at = parent[at]
        m = through(owner)
        if m is None:
            continue
        mesh.matrix = m
        mesh.verts = [transform(m, v) for v in mesh.verts]
        # A frame's vertex carries only a position and a normal, so it is
        # padded out to what transform() expects and cut back afterwards.
        mesh.frames = [(when, [transform(m, tuple(v) + (0, 0, 0, 0))[:6] for v in verts])
                       for when, verts in mesh.frames]
        mesh.placed = True


CHUNK_NODE = 0x10000
CHUNK_TRACK = 0x10001
CHUNK_MESH = 0x10002
CHUNK_TYPES = (0x10000, 0x10001, 0x10002, 0x10003)


def directory(raw):
    """The table of chunks, which is the last thing in the file.

    Every chunk is `type | children | offset | size`, sixteen bytes, and they
    are written **depth first**: a chunk is followed by its own children, as
    many as its second field says. That field is a child count and reading it
    as anything else is what kept the parts in the wrong places.

    It is found by walking backwards from the end of the file for as long as the
    entries make sense, because nothing says where the table begins.
    """
    base = struct.unpack_from('<I', raw, 0)[0]
    rows = []
    at = len(raw) - 16
    while at >= 0:
        kind, children, off, size = struct.unpack_from('<4I', raw, at)
        if kind not in CHUNK_TYPES or base + off + size > len(raw):
            break
        rows.insert(0, (kind, children, base + off, size))
        at -= 16
    return rows


def hierarchy(rows):
    """{chunk index: parent index} out of the depth first order."""
    parent = {}
    stack = []                  # (index, how many children are still to come)
    for i, (kind, children, off, size) in enumerate(rows):
        while stack and stack[-1][1] == 0:
            stack.pop()
        if stack:
            parent[i] = stack[-1][0]
            stack[-1][1] -= 1
        else:
            parent[i] = None
        stack.append([i, children])
    return parent


def times(a, b):
    """a then b. Row vectors with the translation last, as the file writes it."""
    out = [0.0] * 16
    for r in range(4):
        for c in range(4):
            out[r * 4 + c] = sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4))
    return out


def modelled_at_the_origin(mesh, slack=0.2):
    """Whether this part sits around the origin rather than where it belongs.

    Most parts of a model are written where they go and need no transform at
    all - a door is already at the side of the car. A part that turns is not:
    a wheel is modelled around the origin so that it can spin about it, and
    only that kind needs its node matrix applied.

    Which is which is decided by measuring rather than by name, because the
    names are the modellers' own and in German.
    """
    lo = [min(v[k] for v in mesh.verts) for k in range(3)]
    hi = [max(v[k] for v in mesh.verts) for k in range(3)]
    size = max(hi[k] - lo[k] for k in range(3)) or 1.0
    return all(abs((lo[k] + hi[k]) / 2.0) < size * slack for k in range(3))


def transform(m, v):
    """A vertex through a node's matrix. Row vectors, translation in the last
    row, which is the order the file writes them in and the order 3ds Max used."""
    x, y, z = v[0], v[1], v[2]
    nx, ny, nz = v[3], v[4], v[5]
    return (x * m[0] + y * m[4] + z * m[8] + m[12],
            x * m[1] + y * m[5] + z * m[9] + m[13],
            x * m[2] + y * m[6] + z * m[10] + m[14],
            nx * m[0] + ny * m[4] + nz * m[8],
            nx * m[1] + ny * m[5] + nz * m[9],
            nx * m[2] + ny * m[6] + nz * m[10],
            v[6], v[7], v[8], v[9])


def bounds(model, hide=(), poses=False):
    lo = [1e30] * 3
    hi = [-1e30] * 3
    for mesh in model.meshes:
        if not wanted(mesh, hide, poses):
            continue
        for v in mesh.verts:
            for k in range(3):
                lo[k] = min(lo[k], v[k])
                hi[k] = max(hi[k], v[k])
    return lo, hi


def as_obj(model, out):
    """Wavefront .obj, which every 3D program on earth opens."""
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# %s\n' % os.path.basename(model.path))
        if model.source:
            f.write('# exported by its authors from %s\n' % model.source)
        for t in model.textures:
            f.write('# texture: %s\n' % t)
        base = 1
        for n, mesh in enumerate(model.meshes):
            f.write('o %s_%d\n' % (model.name or 'mesh', n))
            for v in mesh.verts:
                f.write('v %.6f %.6f %.6f\n' % (v[0], v[1], v[2]))
            for v in mesh.verts:
                f.write('vt %.6f %.6f\n' % (v[8], 1.0 - v[9]))
            for v in mesh.verts:
                f.write('vn %.6f %.6f %.6f\n' % (v[3], v[4], v[5]))
            for _, _, i0, i1, i2 in mesh.faces:
                a, b, c = i0 + base, i1 + base, i2 + base
                f.write('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % (a, a, a, b, b, b, c, c, c))
            base += len(mesh.verts)


def at_frame(mesh, which):
    """The mesh as it stands at frame `which`, or as it was modelled at 0."""
    if which <= 0 or which > len(mesh.frames):
        return mesh.verts
    moved = mesh.frames[which - 1][1]
    return [tuple(moved[k][:6]) + tuple(mesh.verts[k][6:])
            for k in range(min(len(moved), len(mesh.verts)))]


def wanted(mesh, hide, poses=False):
    if mesh.variant and not poses:
        return False
    if not hide or not mesh.node:
        return True
    low = mesh.node.lower()
    return not any(word in low for word in hide)


def texture(game, name):
    """One of the game's textures, by the name a model gives it.

    Models name their textures with no path - `rager.png`, `equipment.tga` -
    and `textures.ubn` holds them in folders, so they are matched on the file
    name alone. The `Winter` folder holds a second copy of many of them under
    the same name; the ordinary one wins, because a model that wanted the
    winter set would be a winter model.
    """
    from PIL import Image
    want = os.path.basename(name).lower()
    try:
        with zipfile.ZipFile(os.path.join(game, 'textures.ubn')) as z:
            hits = [i for i in z.infolist()
                    if os.path.basename(i.filename).lower() == want]
            hits.sort(key=lambda i: 'winter' in i.filename.lower())
            if not hits:
                return None
            with z.open(hits[0]) as f:
                return Image.open(io.BytesIO(f.read())).convert('RGB')
    except Exception:
        return None


def render(model, out, size=640, turn=35.0, tilt=25.0, hide=(), game=GAME,
           plain=False, poses=False, frame=0):
    """A picture of it, so that a mesh can be looked at rather than counted.

    A z buffer and one light. Triangles are filled from the model's texture
    where there is one, sampled through the texture coordinates that come out
    of the vertices, and shaded by the angle between the face and the light.

    Each face names the material it uses and the material list says which
    texture that is, so a rifle is drawn with the equipment sheet and its muzzle
    flash with the flash sheet.
    """
    import math
    import numpy
    from PIL import Image

    tris = []
    for mesh in model.meshes:
        if not wanted(mesh, hide, poses):
            continue
        verts = at_frame(mesh, frame)
        for material, _, i0, i1, i2 in mesh.faces:
            if max(i0, i1, i2) >= len(verts):
                continue
            tris.append((verts[i0], verts[i1], verts[i2], material))
    if not tris:
        return False

    # One texture per material, loaded once. A face says which material it uses
    # and the material list says which texture that is, so a gun is drawn with
    # its own sheet and its muzzle flash with the flash sheet, rather than
    # everything with whichever texture happened to be named first.
    sheets = {}
    if not plain:
        for n, named in enumerate(model.materials):
            if not named:
                continue
            picture = texture(game, named)
            if picture is not None:
                array = numpy.asarray(picture, dtype=numpy.float32)
                sheets[n] = (array, array.shape[1], array.shape[0])

    lo, hi = bounds(model, hide, poses)
    mid = [(lo[k] + hi[k]) / 2.0 for k in range(3)]
    span = max(hi[k] - lo[k] for k in range(3)) or 1.0

    a, b = math.radians(turn), math.radians(tilt)
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)

    def camera(v):
        # The models stand in z, so z is up here and y goes into the screen.
        x, y, z = v[0] - mid[0], v[1] - mid[1], v[2] - mid[2]
        x, y = x * ca - y * sa, x * sa + y * ca
        y, z = y * cb - z * sb, y * sb + z * cb
        return x, y, z

    scale = size * 0.42 / (span / 2.0)
    light = (0.45, -0.75, 0.5)

    canvas = numpy.zeros((size, size, 3), dtype=numpy.float32)
    canvas[:, :] = (25, 27, 32)
    depth_of = numpy.full((size, size), 1e30, dtype=numpy.float32)

    for tri in tris:
        p = [camera(v) for v in tri[:3]]
        ax, ay, az = (p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2])
        bx, by, bz = (p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2])
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length == 0.0:
            continue
        lit = abs(nx * light[0] + ny * light[1] + nz * light[2]) / length
        shade = 0.35 + 0.65 * min(1.0, lit)

        sx = [size / 2.0 + q[0] * scale for q in p]
        sy = [size / 2.0 - q[2] * scale for q in p]
        area = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])
        if abs(area) < 1e-9:
            continue

        x0 = max(0, int(math.floor(min(sx))))
        x1 = min(size - 1, int(math.ceil(max(sx))))
        y0 = max(0, int(math.floor(min(sy))))
        y1 = min(size - 1, int(math.ceil(max(sy))))
        if x1 < x0 or y1 < y0:
            continue

        xs = numpy.arange(x0, x1 + 1, dtype=numpy.float32) + 0.5
        ys = numpy.arange(y0, y1 + 1, dtype=numpy.float32) + 0.5
        gx, gy = numpy.meshgrid(xs, ys)
        w0 = ((sx[1] - gx) * (sy[2] - gy) - (sx[2] - gx) * (sy[1] - gy)) / area
        w1 = ((sx[2] - gx) * (sy[0] - gy) - (sx[0] - gx) * (sy[2] - gy)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue

        here = w0 * p[0][1] + w1 * p[1][1] + w2 * p[2][1]
        window = depth_of[y0:y1 + 1, x0:x1 + 1]
        nearer = inside & (here < window)
        if not nearer.any():
            continue

        sheet = sheets.get(tri[3])
        if sheet is not None:
            tex, tw, th = sheet
            u = w0 * tri[0][8] + w1 * tri[1][8] + w2 * tri[2][8]
            v = w0 * tri[0][9] + w1 * tri[1][9] + w2 * tri[2][9]
            col = numpy.mod((u * tw).astype(numpy.int32), tw)
            row = numpy.mod((v * th).astype(numpy.int32), th)
            colour = tex[row, col]
        else:
            colour = numpy.full(w0.shape + (3,), 200.0, dtype=numpy.float32)

        patch = canvas[y0:y1 + 1, x0:x1 + 1]
        patch[nearer] = colour[nearer] * shade
        window[nearer] = here[nearer]

    Image.fromarray(numpy.clip(canvas, 0, 255).astype('uint8')).save(out)
    return True


def models_in(game):
    """Every model in the archive, as (name inside it, bytes)."""
    with zipfile.ZipFile(os.path.join(game, 'objects.ubn')) as z:
        for info in z.infolist():
            if not info.filename.lower().endswith('.diff3d'):
                continue
            # One entry's name differs between the directory and its local
            # header, and z.read(name) refuses that. Opening the ZipInfo
            # itself does not go looking for the name again.
            try:
                with z.open(info) as f:
                    yield info.filename, f.read()
            except Exception:
                # One entry - a bear, sniffing - has an umlaut in its name and
                # the archive spells it one way in the directory and another in
                # the local header, which zipfile refuses to reconcile. It is
                # reported rather than hidden.
                yield info.filename, None


def find_one(game, wanted):
    if os.path.exists(wanted):
        return wanted, open(wanted, 'rb').read()
    want = wanted.lower().replace('\\', '/')
    for name, raw in models_in(game):
        low = name.lower()
        if low == want or os.path.basename(low) == want \
           or os.path.splitext(os.path.basename(low))[0] == want:
            return name, raw
    raise SystemExit('no model called %s' % wanted)


def check(game):
    """Parse every model in the archive and say how many come out whole."""
    whole = empty = broken = 0
    verts = faces = 0
    worst = []
    for name, raw in models_in(game):
        if raw is None:
            broken += 1
            worst.append((name, 'the archive spells its name two different ways'))
            continue
        try:
            model = read(name, raw)
        except Exception as e:
            broken += 1
            worst.append((name, str(e)))
            continue
        got = sum(len(m.verts) for m in model.meshes)
        if got == 0:
            empty += 1
            worst.append((name, 'parses, but no mesh was found in it'))
            continue
        whole += 1
        verts += got
        faces += sum(len(m.faces) for m in model.meshes)
    total = whole + empty + broken
    print('%d models' % total)
    print('   %d read, %d vertices and %d faces between them' % (whole, verts, faces))
    print('   %d parse but hold no mesh' % empty)
    print('   %d could not be read at all' % broken)
    if worst:
        print('\nthe first that did not come out:')
        for name, why in worst[:15]:
            print('   %-56s %s' % (name, why))
    return whole, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model', nargs='?', help='a name, or a path to a .diff3D')
    ap.add_argument('--game', default=GAME)
    ap.add_argument('--obj', metavar='FILE', help='write it as a Wavefront .obj')
    ap.add_argument('--png', metavar='FILE', help='draw it, to see whether it is right')
    ap.add_argument('--turn', type=float, default=35.0)
    ap.add_argument('--tilt', type=float, default=25.0)
    ap.add_argument('--frame', type=int, default=0,
                    help='which frame of the animation to draw, 0 being the pose '
                         'the model was built in')
    ap.add_argument('--poses', action='store_true',
                    help='draw every pose of a weapon, not just the one in hand')
    ap.add_argument('--plain', action='store_true',
                    help='no texture, just shaded surfaces')
    ap.add_argument('--hide', default='',
                    help='leave out nodes whose name holds any of these, comma '
                         'separated - "licht,glow,effekt" drops the lamps '
                         'off a vehicle')
    ap.add_argument('--check', action='store_true',
                    help='parse every model in the archive')
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

    if args.check:
        check(args.game)
        return
    if not args.model:
        print(__doc__)
        return

    name, raw = find_one(args.game, args.model)
    model = read(name, raw)
    print('%s' % name)
    print('   node        %s' % (model.name or '?'))
    if model.source:
        print('   exported from %s' % model.source)
    print('   textures    %s' % (', '.join(model.textures) or 'none named'))
    print('   %d meshes, %d vertices, %d faces'
          % (len(model.meshes),
             sum(len(m.verts) for m in model.meshes),
             sum(len(m.faces) for m in model.meshes)))
    for n, mesh in enumerate(model.meshes):
        print('      %2d %-24s %6d vertices %6d faces%s'
              % (n, mesh.node or '?', len(mesh.verts), len(mesh.faces),
                 '   (another pose of the same thing)' if mesh.variant else ''))
    moving = [m for m in model.meshes if m.frames]
    if moving:
        m = moving[0]
        print('   %d frames, %d to %d ms'
              % (len(m.frames) + 1, 0, m.frames[-1][0]))
    for who, got in model.tracks:
        print('   track on %-20s %d moves, %d poses, %d to %d'
              % (who or '?', len(got['moves']), len(got['poses']),
                 got['moves'][0][0] if got['moves'] else 0,
                 got['moves'][-1][0] if got['moves'] else 0))
    if model.meshes:
        lo, hi = bounds(model)
        print('   it measures %.1f x %.1f x %.1f'
              % (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    if args.obj:
        as_obj(model, args.obj)
        print('written to %s' % args.obj)
    if args.png:
        hide = tuple(w.strip().lower() for w in args.hide.split(',') if w.strip())
        if render(model, args.png, turn=args.turn, tilt=args.tilt, hide=hide,
                  game=args.game, plain=args.plain, poses=args.poses,
                  frame=args.frame):
            print('drawn into %s' % args.png)
        else:
            print('nothing to draw: no mesh came out of it')


if __name__ == '__main__':
    main()
