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
  ob = K.build("house", when=fn)               # ...whose pieces appear / disappear one by one

Pieces can be shown or hidden one at a time (time-lapse construction / demolition): build(when=fn)
calls fn with every piece's centre and bottom (a list of dicts) and expects a (frame on, frame off)
pair for each; a geometry-nodes modifier then shows each piece only from its "on" frame to its
"off" frame (a hidden piece collapses to a point: the vertex count never changes, so motion blur
still works).
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
        self.vpiece = {}         # (colour, kind) -> each vertex's piece number
        self.npieces = 0
        self._piece = None       # set while a piece (a brick and its studs) is being added

    def _tag(self, color, kind, n):
        """The last n vertices added belong to the current piece (or a new one)."""
        pid = self._piece
        if pid is None:
            pid = self.npieces
            self.npieces += 1
        self.vpiece.setdefault((color, kind or self.kind), []).extend([pid] * n)

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
        self._tag(color, kind, 8)

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
        self._tag(color, kind, 2 * s)

    # ---------------------------------------------------------------- pieces (studs, plates)
    def studs(self, x, y, z, w, d, color, kind=None):
        """Studs on top of a w x d area whose top is at plate height z."""
        for i in range(int(round(w))):
            for j in range(int(round(d))):
                self.cyl((x + i + 0.5) * P, (y + j + 0.5) * P, z * PL, z * PL + STUD_H, STUD_R, color, kind,
                         bottom=False)

    def piece(self, x, y, z, w, d, h, color, studs=True, kind=None):
        """A w x d (studs) piece h plates tall, its corner at stud (x, y), its bottom at plate z."""
        outer = self._piece
        if outer is None:                       # (the box and its studs are one piece)
            self._piece = self.npieces
            self.npieces += 1
        self.box(x * P + GAP, y * P + GAP, z * PL, (x + w) * P - GAP, (y + d) * P - GAP, (z + h) * PL - GAP / 2,
                 color, kind)
        if studs:
            self.studs(x, y, z + h - GAP / 2 / PL, w, d, color, kind)
        self._piece = outer

    def block(self, x, y, z, w, d, h, color, studs=False, kind=None, L=4, D=2):
        """A solid w x d x h (studs, plates) block built from ordinary pieces: L x D bricks (courses
        of 3 plates; a block under 3 plates tall is one course of plates that tall), laid along its
        longer side in rows, each row and course staggered by half a piece (running bond). So it
        goes up, or comes apart, piece by piece. studs: on the top course."""
        courses, zc = [], z
        while zc < z + h - 1e-6:
            hc = min(3.0 if h >= 3 else h, z + h - zc)
            courses.append((zc, hc))
            zc += hc
        along_x = w >= d
        lw, ld = (w, d) if along_x else (d, w)          # (length along the rows, across them)
        for ci, (zc, hc) in enumerate(courses):
            top = studs and ci == len(courses) - 1
            r, row = 0.0, 0
            while r < ld - 1e-6:
                rd = min(D, ld - r)
                a = -(L / 2) if (ci + row) % 2 else 0.0
                while a < lw - 1e-6:
                    a0, a1 = max(0.0, a), min(lw, a + L)
                    if a1 - a0 > 1e-6:
                        if along_x:
                            self.piece(x + a0, y + r, zc, a1 - a0, rd, hc, color, top, kind)
                        else:
                            self.piece(x + r, y + a0, zc, rd, a1 - a0, hc, color, top, kind)
                    a += L
                r += rd
                row += 1

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
        outer = self._piece
        if outer is None:
            self._piece = self.npieces
            self.npieces += 1
        self.cyl(cx, cy, z * PL, (z + h) * PL - GAP / 2, dia * P / 2 - GAP, color, kind, sides=self.sides * 2)
        if studs:
            if dia == 1:
                self.cyl(cx, cy, (z + h) * PL - GAP / 2, (z + h) * PL + STUD_H, STUD_R, color, kind, bottom=False)
            else:
                self.studs(x, y, z + h - GAP / 2 / PL, dia, dia, color, kind)
        self._piece = outer

    # ---------------------------------------------------------------- output
    def build(self, name, bevel=0.0045, collection=None, when=None):
        """Merge everything into one object (a material slot per colour). when: see the top."""
        verts, faces, mats, slots, vp = [], [], [], [], []
        for slot, ((color, kind), (V, F)) in enumerate(self.geo.items()):
            off = len(verts)
            verts += V
            faces += [tuple(i + off for i in f) for f in F]
            mats += [slot] * len(F)
            slots.append(self.B.mat(color, kind))
            vp += self.vpiece.get((color, kind), [0] * len(V))
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        if when is not None:
            n = self.npieces
            lo = [[1e9, 1e9, 1e9] for _ in range(n)]
            hi = [[-1e9, -1e9, -1e9] for _ in range(n)]
            for v, p in zip(verts, vp):
                for a in range(3):
                    lo[p][a] = min(lo[p][a], v[a])
                    hi[p][a] = max(hi[p][a], v[a])
            pieces = [dict(c=tuple((a + b) / 2 for a, b in zip(lo[p], hi[p])), lo=tuple(lo[p]), hi=tuple(hi[p]))
                      for p in range(n)]
            times = when(pieces)
            on = me.attributes.new("on", "FLOAT", "POINT")
            off_ = me.attributes.new("off", "FLOAT", "POINT")
            pc = me.attributes.new("pc", "FLOAT_VECTOR", "POINT")
            on.data.foreach_set("value", [times[p][0] for p in vp])
            off_.data.foreach_set("value", [times[p][1] for p in vp])
            pc.data.foreach_set("vector", [c for p in vp for c in pieces[p]["c"]])
        me.polygons.foreach_set("material_index", mats)
        for m in slots:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        (collection or self.B.col).objects.link(ob)
        if bevel:   # baked into the mesh once (a live modifier is recomputed on every frame)
            b = ob.modifiers.new("bevel", "BEVEL")
            b.width, b.segments = bevel, 2
            b.limit_method = "ANGLE"
            b.harden_normals = False
            dg = bpy.context.evaluated_depsgraph_get()
            baked = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            ob.modifiers.clear()
            old, ob.data = ob.data, baked
            bpy.data.meshes.remove(old)
            baked.name = name
        if when is not None:
            gn = ob.modifiers.new("piecewise", "NODES")
            gn.node_group = piecewise_group()
        self.geo, self.vpiece, self.npieces = {}, {}, 0
        return ob


def piecewise_group():
    """Geometry nodes: each piece shown only from its "on" frame to its "off" frame (otherwise
    collapsed to its centre, "pc"), by the scene's current frame."""
    ng = bpy.data.node_groups.get("piecewise")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("piecewise", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    st = N.new("GeometryNodeInputSceneTime")
    def attr(nm, typ):
        a = N.new("GeometryNodeInputNamedAttribute")
        a.data_type = typ
        a.inputs["Name"].default_value = nm
        return a
    a_on, a_off, a_pc = attr("on", "FLOAT"), attr("off", "FLOAT"), attr("pc", "FLOAT_VECTOR")
    def math_(op, a, b):
        m = N.new("ShaderNodeMath")
        m.operation = op
        for i, src in enumerate((a, b)):
            if isinstance(src, (int, float)):
                m.inputs[i].default_value = src
            else:
                L.new(src, m.inputs[i])
        return m.outputs[0]
    fr = math_("ADD", st.outputs["Frame"], 0.001)
    shown = math_("MULTIPLY", math_("GREATER_THAN", fr, a_on.outputs["Attribute"]),
                  math_("GREATER_THAN", a_off.outputs["Attribute"], fr))
    pos = N.new("GeometryNodeInputPosition")
    sub = N.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"
    L.new(pos.outputs[0], sub.inputs[0]); L.new(a_pc.outputs["Attribute"], sub.inputs[1])
    sca = N.new("ShaderNodeVectorMath"); sca.operation = "SCALE"
    L.new(sub.outputs[0], sca.inputs[0]); L.new(shown, sca.inputs["Scale"])
    add = N.new("ShaderNodeVectorMath"); add.operation = "ADD"
    L.new(sca.outputs[0], add.inputs[0]); L.new(a_pc.outputs["Attribute"], add.inputs[1])
    sp = N.new("GeometryNodeSetPosition")
    L.new(gi.outputs[0], sp.inputs["Geometry"]); L.new(add.outputs[0], sp.inputs["Position"])
    L.new(sp.outputs[0], go.inputs[0])
    return ng
