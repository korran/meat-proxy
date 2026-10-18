"""Toy-brick building kit for sets, at the same scale as the minifig-style cast (style_lab.py).

One stud pitch P is the distance between a figure's leg centres (0.136 units). A plate is 0.4 P
tall and a brick is three plates (1.2 P), the classic toy proportions. Positions are in studs
(x, y; can be fractional) and plates (z), from the set's origin.

Pieces are collected per colour and merged into one mesh with a material slot per colour, with
a small gap around every piece (so the seams show) and a bevel modifier for moulded edges.
Thousands of bricks stay cheap to render this way.

  K = Kit(B)                                   # B: a style_lab.Builder (for materials)
  K.brick(0, 0, 0, 2, 4, "#c9cdd2")            # a 2x4 brick at stud (0, 0), plate 0
  K.plate(0, 0, 3, 2, 4, "white")              # a plate on top of it
  K.tile(...), K.round(...), K.box(...)        # tiles (no studs), round pieces, free boxes
  ob = K.build("wall")                         # one object
"""
import math

import bpy

P = 0.136          # stud pitch
PL = 0.4 * P       # plate height
BR = 3 * PL        # brick height
GAP = 0.0025       # gap left around each piece, so the seams show
STUD_R, STUD_H = 0.3 * P, 0.17 * P


class Kit:
    def __init__(self, B, kind="surface", stud_sides=12):
        self.B, self.kind, self.sides = B, kind, stud_sides
        self.geo = {}            # (colour, kind) -> (verts, faces)

    def _g(self, color, kind=None):
        return self.geo.setdefault((color, kind or self.kind), ([], []))

    # ---------------------------------------------------------------- primitives (world units)
    def box(self, x0, y0, z0, x1, y1, z1, color, kind=None):
        """A free box in world units (for parts that aren't on the grid)."""
        V, F = self._g(color, kind)
        n = len(V)
        V += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        F += [(n, n + 3, n + 2, n + 1), (n + 4, n + 5, n + 6, n + 7), (n, n + 1, n + 5, n + 4),
              (n + 1, n + 2, n + 6, n + 5), (n + 2, n + 3, n + 7, n + 6), (n + 3, n, n + 4, n + 7)]

    def cyl(self, cx, cy, z0, z1, r, color, kind=None, sides=None, bottom=True):
        V, F = self._g(color, kind)
        s = sides or self.sides
        n = len(V)
        for z in (z0, z1):
            for i in range(s):
                a = math.tau * i / s
                V.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        F += [(n + i, n + (i + 1) % s, n + s + (i + 1) % s, n + s + i) for i in range(s)]
        F.append(tuple(n + s + i for i in range(s)))
        if bottom:
            F.append(tuple(n + i for i in reversed(range(s))))

    # ---------------------------------------------------------------- pieces (studs, plates)
    def studs(self, x, y, z, w, d, color, kind=None):
        """Studs on top of a w x d area whose top is at plate height z."""
        for i in range(int(round(w))):
            for j in range(int(round(d))):
                self.cyl((x + i + 0.5) * P, (y + j + 0.5) * P, z * PL, z * PL + STUD_H, STUD_R, color, kind,
                         bottom=False)

    def piece(self, x, y, z, w, d, h, color, studs=True, kind=None):
        """A w x d (studs) piece h plates tall, its corner at stud (x, y), its bottom at plate z."""
        self.box(x * P + GAP, y * P + GAP, z * PL, (x + w) * P - GAP, (y + d) * P - GAP, (z + h) * PL - GAP / 2,
                 color, kind)
        if studs:
            self.studs(x, y, z + h - GAP / 2 / PL, w, d, color, kind)

    def brick(self, x, y, z, w, d, color, h=3, studs=True, kind=None):
        self.piece(x, y, z, w, d, h, color, studs, kind)

    def plate(self, x, y, z, w, d, color, studs=True, kind=None):
        self.piece(x, y, z, w, d, 1, color, studs, kind)

    def tile(self, x, y, z, w, d, color, kind=None):
        self.piece(x, y, z, w, d, 1, color, False, kind)

    def round(self, x, y, z, dia, h, color, studs=True, kind=None):
        """A round piece dia studs across, h plates tall, centred on stud cell (x, y)'s centre
        (for dia 2: on the corner between four cells)."""
        cx, cy = (x + dia / 2) * P, (y + dia / 2) * P
        self.cyl(cx, cy, z * PL, (z + h) * PL - GAP / 2, dia * P / 2 - GAP, color, kind, sides=self.sides * 2)
        if studs:
            if dia == 1:
                self.cyl(cx, cy, (z + h) * PL - GAP / 2, (z + h) * PL + STUD_H, STUD_R, color, kind, bottom=False)
            else:
                self.studs(x, y, z + h - GAP / 2 / PL, dia, dia, color, kind)

    # ---------------------------------------------------------------- output
    def build(self, name, bevel=0.0045, collection=None):
        """Merge everything into one object (a material slot per colour)."""
        verts, faces, mats, slots = [], [], [], []
        for slot, ((color, kind), (V, F)) in enumerate(self.geo.items()):
            off = len(verts)
            verts += V
            faces += [tuple(i + off for i in f) for f in F]
            mats += [slot] * len(F)
            slots.append(self.B.mat(color, kind))
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.polygons.foreach_set("material_index", mats)
        for m in slots:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        (collection or self.B.col).objects.link(ob)
        if bevel:
            b = ob.modifiers.new("bevel", "BEVEL")
            b.width, b.segments = bevel, 2
            b.limit_method = "ANGLE"
            b.harden_normals = False
        self.geo = {}
        return ob
