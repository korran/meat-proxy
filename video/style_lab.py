"""Character / style exploration: renders Kevin in several visual styles.

  blender -b --factory-startup --python video/style_lab.py -- --out video/build/style

Writes one PNG per style (kevin_<style>.png). video/style_sheet.py combines them
into a labelled contact sheet.
"""
import argparse
import math
import sys

import bpy
from mathutils import Vector

STYLES = ["flat", "toy", "lowpoly", "brick", "fig"]

FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def srgb(h):
    """'#rrggbb' -> linear RGB tuple."""
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


PAL = {
    "bg": "#0b1230", "floor": "#141d45", "ink": "#11131c",
    "skin": "#f4b892", "cheek": "#f08672", "hair": "#6b4128", "eye": "#1b1b22", "white": "#ffffff",
    "shirt": "#4fb3f0", "shirt_trim": "#2f86c4", "shorts": "#2b3a67", "sock": "#f4f4f0",
    "sneaker": "#e5413b", "sole": "#f4f4f0",
    "badge": "#f7f7f2", "badge_band": "#ff6a1f", "lanyard": "#ff6a1f", "mug": "#f3efe6",
    "steak": "#a33a2a", "fat": "#f3d9b6", "bone": "#fbf7ee", "grill": "#4a1d14",
    "plate": "#2c3c86", "fig_skin": "#f6c9a0",
}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="video/build/style")
    ap.add_argument("--styles", default=",".join(STYLES))
    ap.add_argument("--res", type=int, default=1080, help="output height in pixels")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--lineup", action="store_true", help="render the cast lineup (fig style) instead")
    ap.add_argument("--cam", help="lineup camera override: 'x,y,z:tx,ty,tz:lens' (for close-ups)")
    ap.add_argument("--name", default="cast_lineup", help="output file name (without .png)")
    return ap.parse_known_args(argv)[0]  # tolerate other scripts' args when imported


A = args()


# ------------------------------------------------------------------ materials

def material(style, name, color, kind="surface"):
    """kind: surface | glossy | ink"""
    m = bpy.data.materials.new(f"{style}_{name}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    col = srgb(PAL[color]) if color in PAL else srgb(color)
    if kind == "glow":
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*col, 1)
        em.inputs["Strength"].default_value = 4.0
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        return m
    if kind == "chrome":
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Base Color"].default_value = (*col, 1)
        bs.inputs["Metallic"].default_value = 1.0
        bs.inputs["Roughness"].default_value = 0.06
        nt.links.new(bs.outputs[0], out.inputs["Surface"])
        return m
    if style == "flat" or kind == "ink":
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*col, 1)
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    else:
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Base Color"].default_value = (*col, 1)
        if style == "toy":
            bs.inputs["Roughness"].default_value = 0.18 if kind == "glossy" else 0.32
            bs.inputs["Coat Weight"].default_value = 0.5 if kind == "glossy" else 0.25
            bs.inputs["Coat Roughness"].default_value = 0.08
            bs.inputs["Subsurface Weight"].default_value = 0.15 if color == "skin" else 0.0
        elif style in ("brick", "fig"):  # moulded ABS plastic
            bs.inputs["Roughness"].default_value = 0.2
            bs.inputs["Coat Weight"].default_value = 0.35
            bs.inputs["Coat Roughness"].default_value = 0.12
        else:  # lowpoly: matte
            bs.inputs["Roughness"].default_value = 0.85
        if kind == "matte":
            bs.inputs["Roughness"].default_value = 0.9
            bs.inputs["Coat Weight"].default_value = 0.0
        nt.links.new(bs.outputs[0], out.inputs["Surface"])
    return m


def outline_material(style):
    m = bpy.data.materials.get(f"{style}_outline")
    if m:
        return m
    m = material(style, "outline", "ink", "ink")
    m.use_backface_culling = True
    return m


# ------------------------------------------------------------------ geometry helpers

class Builder:
    def __init__(self, style, collection):
        self.style = style
        self.col = collection
        self.mats = {}
        self.legs = []  # hip pivots created by the leg builders, in creation order

    def mat(self, color, kind="surface"):
        key = (color, kind)
        if key not in self.mats:
            self.mats[key] = material(self.style, f"{color}_{kind}", color, kind)
        return self.mats[key]

    def _finish(self, ob, color, kind="surface", smooth=True, subdiv=True, outline=True):
        for c in ob.users_collection:
            c.objects.unlink(ob)
        self.col.objects.link(ob)
        ob.data.materials.append(self.mat(color, kind))
        if self.style == "lowpoly":
            smooth, subdiv = False, False
        for p in getattr(ob.data, "polygons", []):
            p.use_smooth = smooth
        if subdiv and self.style == "toy" and ob.type == "MESH":
            m = ob.modifiers.new("subsurf", "SUBSURF")
            m.levels = m.render_levels = 2
        if self.style == "flat" and outline and ob.type == "MESH":
            ob.data.materials.append(outline_material(self.style))
            s = ob.modifiers.new("outline", "SOLIDIFY")
            s.thickness = 0.014
            s.offset = 1.0
            s.use_flip_normals = True
            s.material_offset = 1
            s.use_rim = False
        return ob

    def sphere(self, name, loc, scale, color, kind="surface", rot=(0, 0, 0), segs=None, **kw):
        segs = segs or (12 if self.style == "lowpoly" else 48)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=max(6, segs // 2), radius=1,
                                             location=loc, rotation=rot)
        ob = bpy.context.object
        ob.name = name
        ob.scale = scale
        return self._finish(ob, color, kind, **kw)

    def box(self, name, loc, size, color, bevel=0.08, kind="surface", rot=(0, 0, 0), **kw):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
        ob = bpy.context.object
        ob.name = name
        ob.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        if bevel:
            b = ob.modifiers.new("bevel", "BEVEL")
            b.width = bevel
            b.segments = 2 if self.style == "lowpoly" else 6
            b.limit_method = "NONE"
        return self._finish(ob, color, kind, subdiv=False, **kw)

    def cylinder(self, name, loc, radius, depth, color, rot=(0, 0, 0), kind="surface", **kw):
        verts = 10 if self.style == "lowpoly" else 40
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
        ob = bpy.context.object
        ob.name = name
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = min(radius, depth) * 0.25
        b.segments = 2 if self.style == "lowpoly" else 4
        return self._finish(ob, color, kind, subdiv=False, **kw)

    def torus(self, name, loc, major, minor, color, rot=(0, 0, 0), **kw):
        bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc, rotation=rot,
                                         major_segments=12 if self.style == "lowpoly" else 48,
                                         minor_segments=6 if self.style == "lowpoly" else 16)
        ob = bpy.context.object
        ob.name = name
        return self._finish(ob, color, subdiv=False, **kw)

    def capsule(self, name, a, b, radius, color, **kw):
        """A limb from point a to point b."""
        a, b = Vector(a), Vector(b)
        d = b - a
        segs = 10 if self.style == "lowpoly" else 32
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=max(6, segs // 2), radius=1,
                                             location=(a + b) / 2)
        ob = bpy.context.object
        ob.name = name
        ob.scale = (radius, radius, d.length / 2 + radius)
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
        return self._finish(ob, color, **kw)

    def decal(self, name, shape, cx, cz, sx, sz, color, ellipsoid, offset, rot=0.0):
        """A flat print (ellipse or bar) laid onto the front of an ellipsoid (center, radii).

        Vertices are placed on the surface analytically, so the print follows the curve exactly.
        """
        c, r = ellipsoid
        pts2d, faces = [], []
        if isinstance(shape, tuple) and shape[0] == "raw":  # exact polygon, no smoothing
            ring = shape[1]
            pts2d.append((0.0, 0.0))
            pts2d += [(sx * u, sz * v) for u, v in ring]
            n = len(ring)
            faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
        elif isinstance(shape, tuple) and shape[0] == "band":  # strip between two curves (same length)
            top, bot = shape[1], shape[2]
            n = len(top)
            pts2d = [(sx * u, sz * v) for u, v in list(top) + list(bot)]
            faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
        elif isinstance(shape, list):  # closed outline in unit coordinates, fan-filled from its centre
            ring = smooth_closed(shape, 6)
            pts2d.append((0.0, 0.0))
            pts2d += [(sx * u, sz * v) for u, v in ring]
            n = len(ring)
            faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
        elif shape == "ellipse":
            # concentric rings, so a wide print bends with a curved surface instead of its long
            # fan triangles dipping under it (which showed the surface through as holes)
            n, rings = 48, 8
            pts2d.append((0.0, 0.0))
            for k in range(1, rings + 1):
                f = k / rings
                for i in range(n):
                    a = 2 * math.pi * i / n
                    pts2d.append((f * sx * math.cos(a), f * sz * math.sin(a)))
            faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
            for k in range(rings - 1):
                r0, r1 = 1 + k * n, 1 + (k + 1) * n
                faces += [(r0 + i, r1 + i, r1 + (i + 1) % n, r0 + (i + 1) % n) for i in range(n)]
        else:
            nx, nz = 12, 3
            for j in range(nz + 1):
                for i in range(nx + 1):
                    pts2d.append((sx * (2 * i / nx - 1), sz * (2 * j / nz - 1)))
            for j in range(nz):
                for i in range(nx):
                    k = j * (nx + 1) + i
                    faces.append((k, k + 1, k + nx + 2, k + nx + 1))
        verts = []
        cr, sr = math.cos(rot), math.sin(rot)
        for u, v in pts2d:
            x = cx + u * cr - v * sr
            z = cz + u * sr + v * cr
            if c == "plane":  # flat surface facing -Y at y = r
                y = r - offset
            else:
                dx, dz = (x - c[0]) / r[0], (z - c[2]) / r[2]
                y = c[1] - r[1] * math.sqrt(max(0.0, 1 - dx * dx - dz * dz)) - offset
            verts.append((x, y, z))
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        ob = bpy.data.objects.new(name, me)
        self.col.objects.link(ob)
        return self._finish(ob, color, "matte", subdiv=False, outline=False)

    def text(self, name, body, font, size, loc, color, rot=(math.pi / 2, 0, 0), align="CENTER"):
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = body
        cu.font = bpy.data.fonts.load(font, check_existing=True)
        cu.size = size
        cu.align_x = align
        cu.align_y = "CENTER"
        ob = bpy.data.objects.new(name, cu)
        self.col.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = rot
        cu.materials.append(self.mat(color, "ink" if self.style == "flat" else "surface"))
        return ob

    def tube(self, name, points, radius, color, closed=False, kind="surface"):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = radius
        cu.bevel_resolution = 1 if self.style == "lowpoly" else 4
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(points) - 1)
        for bp, co in zip(sp.bezier_points, points):
            bp.co = co
            bp.handle_left_type = bp.handle_right_type = "AUTO"
        sp.use_cyclic_u = closed
        ob = bpy.data.objects.new(name, cu)
        self.col.objects.link(ob)
        cu.materials.append(self.mat(color, kind))
        return ob


def smooth_closed(points, steps):
    """Catmull-Rom smoothing of a closed 2D outline."""
    out, n = [], len(points)
    for i in range(n):
        p0, p1, p2, p3 = (points[(i + k) % n] for k in (-1, 0, 1, 2))
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[d] + (-p0[d] + p2[d]) * t + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t2
                                    + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t3) for d in (0, 1)))
    return out


# cartoon steak outline (unit size, slightly kidney-shaped)
STEAK = [(-1.0, 0.1), (-0.9, 0.55), (-0.5, 0.8), (0.05, 0.68), (0.55, 0.85), (0.95, 0.55), (1.0, 0.0),
         (0.8, -0.5), (0.3, -0.75), (-0.3, -0.72), (-0.8, -0.45)]


def scaled(shape, k, dy=0.0):
    return [(u * k, v * k + dy) for u, v in shape]


# ------------------------------------------------------------------ Kevin (a kid)

HEAD_C, HEAD_R = Vector((0, 0, 1.02)), Vector((0.37, 0.33, 0.34))


def face(x, z, off=0.004):
    """Point on the front of the head ellipsoid at (x, z), pushed out by `off`."""
    dx, dz = x / HEAD_R.x, (z - HEAD_C.z) / HEAD_R.z
    y = -HEAD_R.y * math.sqrt(max(0.0, 1 - dx * dx - dz * dz))
    return (x, y - off, z)


def build_kevin(B):
    """Kevin faces -Y (towards the camera). Feet at z=0, about 1.45 units to the cowlick."""
    # sneakers, socks, legs
    for s in (-1, 1):
        x = 0.12 * s
        B.sphere(f"sole{s}", (x, -0.04, 0.03), (0.092, 0.148, 0.032), "sole")
        B.sphere(f"shoe{s}", (x, -0.04, 0.065), (0.085, 0.14, 0.06), "sneaker")
        B.cylinder(f"sock{s}", (x, 0, 0.12), 0.052, 0.05, "sock")
        B.capsule(f"leg{s}", (x, 0, 0.13), (x, 0, 0.25), 0.048, "skin")
        B.capsule(f"shortleg{s}", (0.11 * s, 0, 0.34), (0.12 * s, 0, 0.26), 0.085, "shorts")
    B.sphere("shorts", (0, 0, 0.36), (0.24, 0.18, 0.12), "shorts")
    # t-shirt torso, neckline, sleeves
    B.sphere("torso", (0, 0, 0.57), (0.26, 0.2, 0.25), "shirt")
    torso = ((0, 0, 0.57), (0.26, 0.2, 0.25))  # ellipsoid the shirt print sits on
    B.torus("neckline", (0, 0, 0.8), 0.09, 0.018, "shirt_trim")
    for s in (-1, 1):
        B.capsule(f"sleeve{s}", (0.19 * s, 0, 0.71), (0.28 * s, -0.02, 0.62), 0.075, "shirt")
    # arms: left relaxed, right holding the mug
    B.capsule("armL", (-0.29, -0.02, 0.6), (-0.31, -0.03, 0.45), 0.048, "skin")
    B.sphere("handL", (-0.315, -0.04, 0.41), (0.055, 0.055, 0.055), "skin")
    B.capsule("armR", (0.29, -0.02, 0.6), (0.28, -0.17, 0.5), 0.048, "skin")
    B.cylinder("mug", (0.2, -0.27, 0.53), 0.075, 0.15, "mug", kind="glossy")
    B.torus("mughandle", (0.28, -0.27, 0.53), 0.04, 0.012, "mug", rot=(math.pi / 2, 0, 0))
    B.sphere("handR", (0.275, -0.24, 0.5), (0.055, 0.055, 0.055), "skin")

    # steak print on the shirt (T-bone with grill marks)
    # cartoon steak print: dark outline, fat cap along the top, meat, grill marks, shine
    cx, cz, w, h, tilt = -0.02, 0.6, 0.13, 0.1, 0.12

    def at(u, v):  # steak-local offset -> shirt position, following the tilt
        return (cx + u * math.cos(tilt) - v * math.sin(tilt), cz + u * math.sin(tilt) + v * math.cos(tilt))

    # bone sticking out to the right, with the classic double knob
    bx, bz = at(w * 1.15, -h * 0.05)
    B.decal("bone_shaft", "bar", bx, bz, w * 0.32, h * 0.13, "bone", torso, 0.0025, rot=tilt)
    for k, dv in enumerate((0.16, -0.16)):
        kx, kz = at(w * 1.45, -h * 0.05 + h * dv)
        B.decal(f"bone_knob{k}", "ellipse", kx, kz, h * 0.17, h * 0.17, "bone", torso, 0.0025)
    B.decal("steak_outline", scaled(STEAK, 1.08, 0.03), cx, cz, w, h, "grill", torso, 0.003, rot=tilt)
    B.decal("steak_fat", scaled(STEAK, 1.0, 0.055), cx, cz, w, h, "fat", torso, 0.0035, rot=tilt)
    B.decal("steak_meat", STEAK, cx, cz, w, h, "steak", torso, 0.004, rot=tilt)
    for i, du in enumerate((-0.055, 0.0, 0.055)):
        B.decal(f"grill{i}", "bar", cx + du, cz - 0.005, 0.007, 0.045, "grill", torso, 0.005, rot=tilt - 0.75)
    B.decal("steak_shine", "ellipse", cx - 0.07, cz + 0.035, 0.022, 0.011, "fat", torso, 0.005, rot=tilt + 0.3)

    # head
    B.sphere("head", tuple(HEAD_C), tuple(HEAD_R), "skin")
    for s in (-1, 1):
        B.sphere(f"ear{s}", (0.36 * s, 0, 1.0), (0.055, 0.035, 0.075), "skin")
    B.sphere("hair", (0, 0.035, 1.13), (0.378, 0.343, 0.245), "hair")
    B.sphere("fringe", (0.05, -0.235, 1.235), (0.27, 0.1, 0.08), "hair", rot=(0, -0.12, 0), outline=False)
    B.capsule("cowlick", (0.04, 0.05, 1.33), (0.12, 0.03, 1.45), 0.032, "hair")
    # face: big low-set eyes with highlights, cheeks, button nose, eager brows and smile
    for s in (-1, 1):
        B.sphere(f"eye{s}", face(0.12 * s, 0.99), (0.047, 0.022, 0.062), "eye", outline=False)
        B.sphere(f"glint{s}", face(0.105 * s, 1.015, 0.018), (0.014, 0.008, 0.016), "white",
                 kind="ink", outline=False)
        B.sphere(f"cheek{s}", face(0.21 * s, 0.92), (0.06, 0.02, 0.036), "cheek", outline=False)
        B.box(f"brow{s}", face(0.12 * s, 1.11, 0.006), (0.075, 0.016, 0.018), "hair", bevel=0.007,
              rot=(0, -0.15 * s, 0), outline=False)
    B.sphere("nose", face(0, 0.95, -0.005), (0.026, 0.02, 0.022), "skin", outline=False)
    B.tube("smile", [face(-0.07, 0.905, 0.003), face(0, 0.875, 0.003), face(0.07, 0.905, 0.003)], 0.009, "eye")

    # very long lanyard, comically oversized badge down at the knees
    for s in (-1, 1):
        B.tube(f"lanyard{s}", [(0.075 * s, -0.11, 0.8), (0.12 * s, -0.215, 0.6),
                                (0.08 * s, -0.235, 0.36), (0.045 * s, -0.245, 0.28)], 0.011, "lanyard")
    B.box("badge", (0, -0.255, 0.2), (0.3, 0.014, 0.2), "badge", bevel=0.016, kind="glossy")
    B.box("badgeband", (0, -0.263, 0.268), (0.3, 0.004, 0.05), "badge_band", bevel=0.0, outline=False)
    B.text("badgename", "KEVIN", FONT_BOLD, 0.085, (0, -0.266, 0.19), "ink")
    B.text("badgetitle", "INTERN", FONT_SEMI, 0.036, (0, -0.266, 0.135), "ink")


# ------------------------------------------------------------------ Kevin as a brick-built toy figure
# Our own design (not a copy of any branded minifigure): rounded-square head with a printed
# face, boxy torso with shoulder studs, square arms with mitten hands, brick-column legs on
# plate feet, separate moulded hair with a single stud for the cowlick.

def stud(B, name, x, y, z, color, r=0.034, h=0.026):
    """A stud moulded onto the surface at height z: its base is sunk into the part below so
    only the top edge is rounded and there's no groove where it meets the surface."""
    sink = 0.25 * h
    return B.cylinder(name, (x, y, z + (h - sink) / 2), r, h + sink, color)


def build_kevin_brick(B):
    """Faces -Y. Feet at z=0."""
    for s in (-1, 1):
        x = 0.085 * s
        B.box(f"sole{s}", (x, -0.03, 0.012), (0.15, 0.23, 0.024), "sole", bevel=0.008)
        B.box(f"foot{s}", (x, -0.03, 0.045), (0.145, 0.22, 0.045), "sneaker", bevel=0.012)
        B.box(f"shin{s}", (x, 0, 0.15), (0.14, 0.14, 0.17), "skin", bevel=0.012)
        B.box(f"sock{s}", (x, 0, 0.085), (0.142, 0.142, 0.04), "sock", bevel=0.008)
        B.box(f"thigh{s}", (x, 0, 0.29), (0.15, 0.15, 0.12), "shorts", bevel=0.014)
    B.box("hips", (0, 0, 0.375), (0.33, 0.16, 0.07), "shorts", bevel=0.014)
    B.box("torso", (0, 0, 0.555), (0.36, 0.18, 0.29), "shirt", bevel=0.02)
    for s in (-1, 1):
        stud(B, f"shoulderstud{s}", 0.12 * s, 0, 0.7, "shirt")
    B.cylinder("neck", (0, 0, 0.72), 0.06, 0.04, "skin")
    # head, hair piece, cowlick stud
    B.box("head", (0, 0, 0.9), (0.34, 0.3, 0.31), "skin", bevel=0.07)
    B.box("hair", (0, 0.015, 1.03), (0.36, 0.33, 0.12), "hair", bevel=0.05, kind="glossy")
    B.box("fringe", (0.04, -0.15, 1.0), (0.26, 0.04, 0.06), "hair", bevel=0.018, kind="glossy",
          rot=(0, -0.08, 0))
    stud(B, "cowlick", 0.06, 0.01, 1.09, "hair", r=0.04, h=0.035)
    for s in (-1, 1):
        B.box(f"ear{s}", (0.175 * s, 0, 0.9), (0.025, 0.06, 0.08), "skin", bevel=0.01)
    # printed face on the flat front of the head
    face_y = -0.15
    for s in (-1, 1):
        B.decal(f"eye{s}", "ellipse", 0.075 * s, 0.9, 0.028, 0.038, "eye", ("plane", face_y), 0.001)
        B.decal(f"glint{s}", "ellipse", 0.066 * s, 0.914, 0.009, 0.011, "white", ("plane", face_y), 0.002)
        B.decal(f"cheek{s}", "ellipse", 0.118 * s, 0.85, 0.032, 0.02, "cheek", ("plane", face_y), 0.001)
        B.decal(f"brow{s}", "bar", 0.075 * s, 0.965, 0.034, 0.008, "hair", ("plane", face_y), 0.001,
                rot=0.12 * s)
    B.tube("smile", [(-0.045, face_y - 0.002, 0.84), (0, face_y - 0.002, 0.82), (0.045, face_y - 0.002, 0.84)],
           0.007, "eye")
    # arms: square section, sleeve then bare arm, mitten hands; right arm holds the mug out to the side
    B.box("sleeveL", (-0.225, 0, 0.64), (0.09, 0.1, 0.11), "shirt", bevel=0.014, rot=(0, -0.08, 0))
    B.box("armL", (-0.235, 0, 0.52), (0.08, 0.08, 0.15), "skin", bevel=0.012, rot=(0, -0.08, 0))
    B.box("handL", (-0.24, 0, 0.42), (0.09, 0.09, 0.08), "skin", bevel=0.03)
    B.box("sleeveR", (0.225, -0.01, 0.64), (0.09, 0.1, 0.11), "shirt", bevel=0.014, rot=(0.5, 0.2, 0))
    B.box("armR", (0.25, -0.08, 0.55), (0.08, 0.08, 0.15), "skin", bevel=0.012, rot=(0.9, 0.2, 0))
    B.box("handR", (0.27, -0.16, 0.5), (0.09, 0.09, 0.08), "skin", bevel=0.03)
    B.cylinder("mug", (0.355, -0.17, 0.53), 0.06, 0.12, "mug", kind="glossy")
    B.torus("mughandle", (0.42, -0.17, 0.53), 0.032, 0.01, "mug", rot=(math.pi / 2, 0, 0))
    # steak printed big on the flat shirt front
    front = ("plane", -0.09)
    cx, cz, w, h, tilt = -0.025, 0.565, 0.1, 0.075, 0.1

    def at(u, v):
        return (cx + u * math.cos(tilt) - v * math.sin(tilt), cz + u * math.sin(tilt) + v * math.cos(tilt))

    bx, bz = at(w * 1.15, -h * 0.05)
    B.decal("bone_shaft", "bar", bx, bz, w * 0.32, h * 0.13, "bone", front, 0.001, rot=tilt)
    for k, dv in enumerate((0.16, -0.16)):
        kx, kz = at(w * 1.45, -h * 0.05 + h * dv)
        B.decal(f"bone_knob{k}", "ellipse", kx, kz, h * 0.17, h * 0.17, "bone", front, 0.001)
    B.decal("steak_outline", scaled(STEAK, 1.08, 0.03), cx, cz, w, h, "grill", front, 0.0015, rot=tilt)
    B.decal("steak_fat", scaled(STEAK, 1.0, 0.055), cx, cz, w, h, "fat", front, 0.002, rot=tilt)
    B.decal("steak_meat", STEAK, cx, cz, w, h, "steak", front, 0.0025, rot=tilt)
    for i, du in enumerate((-0.04, 0.0, 0.04)):
        B.decal(f"grill{i}", "bar", cx + du, cz - 0.004, 0.005, 0.034, "grill", front, 0.003, rot=tilt - 0.75)
    B.decal("steak_shine", "ellipse", cx - 0.05, cz + 0.026, 0.016, 0.008, "fat", front, 0.003, rot=tilt + 0.3)
    # lanyard down to a printed badge tile at the knees
    for s in (-1, 1):
        B.tube(f"lanyard{s}", [(0.06 * s, -0.06, 0.72), (0.15 * s, -0.1, 0.62), (0.12 * s, -0.115, 0.4),
                                (0.05 * s, -0.12, 0.27)], 0.009, "lanyard")
    B.box("badge", (0, -0.125, 0.2), (0.24, 0.016, 0.15), "badge", bevel=0.01, kind="glossy")
    B.box("badgeband", (0, -0.134, 0.255), (0.24, 0.004, 0.035), "badge_band", bevel=0.0)
    B.text("badgename", "KEVIN", FONT_BOLD, 0.06, (0, -0.137, 0.195), "ink")
    B.text("badgetitle", "INTERN", FONT_SEMI, 0.026, (0, -0.137, 0.153), "ink")


PITCH = 0.136  # stud pitch = distance between a figure's leg centres (one stud per leg)


def fig_baseplate(B, nx=14, ny=9, color="plate"):
    """Studs at half-pitch in x and whole pitch in y, so a figure centred on a whole-pitch x
    position at y = 0 has exactly one stud under each leg (hidden inside the leg)."""
    p = PITCH
    B.box("baseplate", (0, 0, -0.02), (nx * p, ny * p, 0.04), color, bevel=0.008)
    for i in range(-nx // 2, nx // 2):
        for j in range(-(ny // 2), ny // 2 + 1):
            stud(B, f"bp{i}_{j}", (i + 0.5) * p, j * p, 0.0, color, r=0.3 * p, h=0.21 * p)


def baseplate(B, n=14, pitch=0.08, color="floor", r=0.024, h=0.018, clear=(0.2, -0.2, 0.12)):
    B.box("baseplate", (0, 0, -0.02), (n * pitch, n * pitch, 0.04), color, bevel=0.01)
    cx, y0, y1 = clear
    for i in range(n):
        for j in range(n):
            x, y = (i - (n - 1) / 2) * pitch, (j - (n - 1) / 2) * pitch
            if abs(x) < cx and y0 < y < y1:
                continue  # leave room under the feet
            stud(B, f"bp{i}_{j}", x, y, 0.0, color, r=r, h=h)


# ------------------------------------------------------------------ Kevin as a minifigure-style figure

def mesh_object(B, name, verts, faces, color, bevel=0.0, kind="surface"):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    B.col.objects.link(ob)
    if bevel:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = 5
        b.limit_method = "NONE"
    return B._finish(ob, color, kind, subdiv=False)


def trapezoid(B, name, z0, z1, w0, w1, d, color, bevel=0.012):
    """Box tapering from width w0 at z0 to w1 at z1, depth d, front face at y = -d/2."""
    v = []
    for z, w in ((z0, w0), (z1, w1)):
        v += [(-w / 2, -d / 2, z), (w / 2, -d / 2, z), (w / 2, d / 2, z), (-w / 2, d / 2, z)]
    f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_object(B, name, v, f, color, bevel)


def c_hand(B, name, loc, rot, color, gap_dir=-math.pi / 2, gap=0.55):
    """C-shaped hand: a torus with a slice removed, the open ends capped."""
    import bmesh
    from mathutils import Euler
    R, r = 0.026, 0.0135
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40, minor_segments=14,
                                     location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    cut = []
    for f in bm.faces:
        c = f.calc_center_median()
        da = (math.atan2(c.y, c.x) - gap_dir + math.pi) % (2 * math.pi) - math.pi
        if abs(da) < gap:
            cut.append(f)
    bmesh.ops.delete(bm, geom=cut, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
    B._finish(ob, color, subdiv=False)
    m = Euler(rot).to_matrix()
    caps = []
    for k, a in enumerate((gap_dir - gap, gap_dir + gap)):
        p = m @ Vector((R * math.cos(a), R * math.sin(a), 0)) + Vector(loc)
        caps.append(B.sphere(f"{name}_cap{k}", tuple(p), (r, r, r), color))
    return [ob] + caps


# ------------------------------------------------------------------ arms (shoulder + elbow joints)
# At rest an arm hangs straight down along the side of the torso. The hand's local frame is the
# grip: local Z runs through the C (what a held rod lines up with), local -Y points out through
# the C's opening, local +X points away from the body.

ARM_POSES = {  # shoulder (x, y, z) rotation, elbow bend. Negative x = forward.
    "down": ((0.0, 0.0, 0.0), -0.4),
    "forward": ((-0.55, 0.0, 0.0), -1.0),
    "hold": ((-0.45, 0.0, -0.4), -1.15),  # both hands together in front of the chest
    "phone": ((-1.5, 0.0, -0.3), -0.25),  # reaching out in front at chest height, as if reading a phone
}


def make_arm(B, s, top, sleeve, skin, long_sleeve=True):
    sz = top - 0.035           # shoulder joint height
    xa = 0.154 * s             # arm centre line: the arm's inner face touches the shoulder corner
    ez = sz - 0.115            # elbow
    fz = ez - 0.095            # end of forearm
    wz = fz - 0.018            # end of wrist peg
    arm_col = sleeve if long_sleeve else skin
    W, D = 0.062, 0.068  # one arm width/depth for every segment, so nothing bulges

    def axle(name, z, color):  # rounded joint exactly as thick as the arm: flush when it bends
        return B.cylinder(name, (xa, 0, z), D / 2, W, color, rot=(0, math.pi / 2, 0))

    upper = [axle(f"shoulderaxle{s}", sz, sleeve)]
    if long_sleeve:
        upper.append(B.box(f"upperarm{s}", (xa, 0, (sz + ez) / 2), (W, D, sz - ez), sleeve, bevel=0.018))
    else:
        cuff = sz - 0.05
        upper.append(B.box(f"sleeve{s}", (xa, 0, (sz + cuff) / 2), (W + 0.004, D + 0.004, sz - cuff),
                           sleeve, bevel=0.018))
        upper.append(B.box(f"upperarm{s}", (xa, 0, (cuff + ez) / 2), (W, D, cuff - ez), skin, bevel=0.018))
    fore = [axle(f"elbowaxle{s}", ez, arm_col),
            B.box(f"forearm{s}", (xa, 0, (ez + fz) / 2), (W, D, ez - fz), arm_col, bevel=0.018),
            B.cylinder(f"wrist{s}", (xa, 0, (fz + wz) / 2), 0.017, fz - wz + 0.006, skin)]
    hand = c_hand(B, f"hand{s}", (xa, 0, wz - 0.02), (math.pi / 2, 0, 0), skin)
    sh = pivot(B, f"shoulder{s}", (xa, 0, sz), upper)
    el = pivot(B, f"elbow{s}", (xa, 0, ez), fore + hand, parent=sh)
    return sh, el, hand[0]


ARM_SLOPE = math.atan2(0.03, 0.28)  # the torso tapers 0.03 per side over its 0.28 height


def pose_arm(sh, el, s, kind):
    """Pose an arm. The arm always leans out by the torso's side slope first, so it follows the
    body's contour; the pose's own rotations go on top of that."""
    (rx, ry, rz), bend = ARM_POSES[kind]
    sh.rotation_euler = (rx, ry - ARM_SLOPE * s, rz * s)
    el.rotation_euler.x = bend


def fig_arms(B, top, sleeve, skin, poses=("down", "down"), long_sleeve=True):
    """Both arms; returns the (left, right) hand objects."""
    hands = []
    for s, kind in zip((-1, 1), poses):
        sh, el, hand = make_arm(B, s, top, sleeve, skin, long_sleeve)
        pose_arm(sh, el, s, kind)
        hands.append(hand)
    return hands


def held_slab(B, hand, name, size, color, screen=None, look_at=None):
    """A flat accessory (phone, cue cards) held the way toy figures hold handled parts: a short
    stick on the slab's bottom edge slides straight down through the C hand, so the slab stands
    up out of the top of the fist. It can spin on its stick, and tilt a little where the stick
    meets the slab. The front (with an optional glowing screen) is the slab's -Y face. With
    `look_at` (a world point, e.g. the holder's face), spin and tilt are chosen so the front
    points at it."""
    from mathutils import Matrix
    w, t, h = size
    stick_col, stick_top = "#2a2a33", 0.016  # just above the C (the hand is ~0.0135 thick along the grip)
    grip = bpy.data.objects.new(f"{name}_grip", None)  # spins about the grip axis (local Z)
    grip.empty_display_size = 0.02
    B.col.objects.link(grip)
    in_hand(hand, [(grip, (0, 0, 0))])
    stick_len = stick_top + 0.018  # pokes out only a little below the fist
    in_hand(grip, [(B.cylinder(f"{name}_stick", (0, 0, 0), 0.011, stick_len, stick_col),
                    (0, 0, stick_top - stick_len / 2))])
    hinge = bpy.data.objects.new(f"{name}_hinge", None)  # tilts the slab about local X
    hinge.empty_display_size = 0.02
    B.col.objects.link(hinge)
    in_hand(grip, [(hinge, (0, 0, stick_top))])
    zc = h / 2 + 0.002
    slab = [(B.box(name, (0, 0, 0), (w, t, h), color, bevel=0.004), (0, 0, zc)),
            (B.box(f"{name}_collar", (0, 0, 0), (0.024, t + 0.004, 0.01), stick_col, bevel=0.002), (0, 0, 0.003))]
    if screen:
        slab.append((B.box(f"{name}_screen", (0, 0, 0), (w * 0.86, 0.002, h * 0.86), screen, kind="glow",
                           bevel=0.0), (0, -t / 2 - 0.0012, zc)))
    in_hand(hinge, slab)
    if look_at is None:
        return
    bpy.context.view_layer.update()
    H = hand.matrix_world.copy()
    target = Vector(look_at)
    best = None
    for i in range(72):
        spin = 2 * math.pi * i / 72
        for tilt in [math.radians(d) for d in range(-60, 65, 5)]:
            M = H @ Matrix.Rotation(spin, 4, "Z") @ Matrix.Translation((0, 0, stick_top)) @ Matrix.Rotation(tilt, 4, "X")
            centre = M @ Vector((0, 0, zc))
            front = (M.to_3x3() @ Vector((0, -1, 0))).normalized()
            score = front.dot((target - centre).normalized()) - 4 * max(0.0, centre.y + 0.1)  # stay in front of the body
            if best is None or score > best[0]:
                best = (score, spin, tilt)
    grip.rotation_euler.z, hinge.rotation_euler.x = best[1], best[2]


def in_hand(hand, items):
    """Parent props to a hand; `items` is [(object, local location)] in the hand's grip frame."""
    from mathutils import Matrix
    for ob, loc in items:
        ob.parent = hand
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = loc


def build_kevin_fig(B):
    """Faces -Y, feet at z=0. Short (kid) legs; about 0.78 units to the top of the hair."""
    skin = "fig_skin"
    # short legs (hinged at the hip) with printed sneakers, hip piece
    fig_kid_legs(B, "shorts", "sneaker")
    # tapered torso with the steak printed on the front
    trapezoid(B, "torso", 0.18, 0.46, 0.3, 0.24, 0.15, "shirt")
    front = ("plane", -0.075)
    cx, cz, w, h, tilt = -0.015, 0.34, 0.068, 0.05, 0.1

    def at(u, v):
        return (cx + u * math.cos(tilt) - v * math.sin(tilt), cz + u * math.sin(tilt) + v * math.cos(tilt))

    bx, bz = at(w * 1.15, -h * 0.05)
    B.decal("bone_shaft", "bar", bx, bz, w * 0.32, h * 0.13, "bone", front, 0.0008, rot=tilt)
    for k, dv in enumerate((0.16, -0.16)):
        kx, kz = at(w * 1.45, -h * 0.05 + h * dv)
        B.decal(f"bone_knob{k}", "ellipse", kx, kz, h * 0.17, h * 0.17, "bone", front, 0.0008)
    B.decal("steak_outline", scaled(STEAK, 1.08, 0.03), cx, cz, w, h, "grill", front, 0.0012, rot=tilt)
    B.decal("steak_fat", scaled(STEAK, 1.0, 0.055), cx, cz, w, h, "fat", front, 0.0016, rot=tilt)
    B.decal("steak_meat", STEAK, cx, cz, w, h, "steak", front, 0.002, rot=tilt)
    for i, du in enumerate((-0.027, 0.0, 0.027)):
        B.decal(f"grill{i}", "bar", cx + du, cz - 0.003, 0.0035, 0.023, "grill", front, 0.0024, rot=tilt - 0.75)
    B.decal("steak_shine", "ellipse", cx - 0.034, cz + 0.018, 0.011, 0.0055, "fat", front, 0.0024, rot=tilt + 0.3)
    # neck and cylindrical head with a printed face
    B.cylinder("neck", (0, 0, 0.475), 0.042, 0.03, skin)
    head = B.cylinder("head", (0, 0, 0.58), 0.1, 0.18, skin)
    head.modifiers["bevel"].width = 0.03
    head.modifiers["bevel"].segments = 6
    cyl = ((0, 0, 0.58), (0.1, 0.1, 100.0))  # the head's front, as a (very tall) ellipsoid = cylinder
    for s in (-1, 1):
        B.decal(f"eye{s}", "ellipse", 0.036 * s, 0.588, 0.0135, 0.019, "eye", cyl, 0.0008)
        B.decal(f"glint{s}", "ellipse", 0.032 * s, 0.595, 0.0045, 0.0055, "white", cyl, 0.0015)
        B.decal(f"cheek{s}", "ellipse", 0.06 * s, 0.558, 0.016, 0.01, "cheek", cyl, 0.0008)
        B.decal(f"brow{s}", "bar", 0.036 * s, 0.62, 0.016, 0.0038, "hair", cyl, 0.0008, rot=0.12 * s)
    sm = []
    for x, z in ((-0.024, 0.556), (0, 0.546), (0.024, 0.556)):
        sm.append((x, -math.sqrt(0.1 ** 2 - x * x) - 0.0015, z))
    B.tube("smile", sm, 0.0035, "eye")
    # moulded kid hair piece with a cowlick
    B.sphere("hair", (0, 0.012, 0.645), (0.113, 0.113, 0.07), "hair", kind="glossy")
    B.sphere("fringe", (0.02, -0.085, 0.652), (0.075, 0.03, 0.026), "hair", kind="glossy", rot=(0, -0.15, 0))
    B.capsule("cowlick", (0.015, 0.02, 0.7), (0.05, 0.01, 0.745), 0.014, "hair", kind="glossy")
    # arms: short sleeves, bare arms; right hand holds the mug by its handle
    _, hand = fig_arms(B, 0.46, "shirt", skin, poses=("down", "forward"), long_sleeve=False)
    in_hand(hand, [(B.cylinder("mughandle", (0, 0, 0), 0.0115, 0.055, "mug"), (0, 0, 0)),
                   (B.box("mugbridge", (0, 0, 0), (0.012, 0.03, 0.05), "mug", bevel=0.004), (0, -0.024, 0)),
                   (B.cylinder("mug", (0, 0, 0), 0.034, 0.065, "mug", kind="glossy"), (0, -0.05, 0))])
    # lanyard down to a printed badge tile in front of the short legs
    for s in (-1, 1):
        B.tube(f"lanyard{s}", [(0.035 * s, -0.045, 0.47), (0.085 * s, -0.08, 0.4), (0.07 * s, -0.085, 0.22),
                                (0.03 * s, -0.092, 0.13)], 0.0045, "lanyard")
    B.box("badge", (0, -0.096, 0.085), (0.15, 0.008, 0.1), "badge", bevel=0.006, kind="glossy")
    B.box("badgeband", (0, -0.1005, 0.122), (0.15, 0.002, 0.024), "badge_band", bevel=0.0)
    B.text("badgename", "KEVIN", FONT_BOLD, 0.036, (0, -0.1015, 0.082), "ink")
    B.text("badgetitle", "INTERN", FONT_SEMI, 0.016, (0, -0.1015, 0.055), "ink")


# ------------------------------------------------------------------ cast: shared figure parts
# All figures use the same body plan as Kevin. Coordinates are built at the origin facing -Y;
# build_at() moves everything a builder function created to its spot in the lineup.

FIG = {"z_adult": 0.29, "z_kid": 0.18, "torso_h": 0.28}


def pivot(B, name, loc, parts, parent=None):
    """A joint: an empty that `parts` hang from (keeping their rest positions)."""
    from mathutils import Matrix
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.04
    B.col.objects.link(e)
    e.location = loc
    if parent:
        e.parent = parent
        e.matrix_parent_inverse = Matrix.Translation(parent.location).inverted()
    inv = Matrix.Translation(loc).inverted()
    for ob in parts:
        ob.parent = e
        ob.matrix_parent_inverse = inv
    return e


def make_leg(B, s, x, hip, knee, pants, foot_parts):
    """One leg with a hip and a knee joint. Rotate hip.rotation_euler.x to swing the thigh
    (negative = forward) and knee.rotation_euler.x to bend the knee (positive = heel back).
    Rounded axles the full depth of the leg hide the corners when a joint bends."""
    axle = lambda name, z: B.cylinder(name, (x, 0, z), 0.0725, 0.128, pants, rot=(0, math.pi / 2, 0))
    thigh = [B.box(f"thigh{s}", (x, 0, (hip + knee) / 2), (0.13, 0.145, hip - knee), pants, bevel=0.008),
             axle(f"hipaxle{s}", hip)]
    shin_bottom = max(p.location.z + p.dimensions.z / 2 for p in foot_parts)
    shin = [B.box(f"shin{s}", (x, 0, (knee + shin_bottom) / 2), (0.13, 0.145, knee - shin_bottom), pants,
                  bevel=0.008), axle(f"kneeaxle{s}", knee)] + foot_parts
    h = pivot(B, f"hip{s}", (x, 0, hip), thigh)
    k = pivot(B, f"knee{s}", (x, 0, knee), shin, parent=h)
    B.legs.append((h, k))
    return h, k


def fig_adult_legs(B, pants, shoes):
    for s in (-1, 1):
        x = 0.068 * s
        shoe = B.box(f"shoe{s}", (x, -0.008, 0.02), (0.132, 0.162, 0.04), shoes, bevel=0.006)
        make_leg(B, s, x, hip=0.24, knee=0.14, pants=pants, foot_parts=[shoe])
    B.box("hips", (0, 0, 0.265), (0.27, 0.14, 0.05), pants, bevel=0.008)
    return FIG["z_adult"]


def fig_skirt(B, skirt, shoes):
    trapezoid(B, "skirt", 0.0, 0.24, 0.3, 0.27, 0.16, skirt)
    for s in (-1, 1):
        B.box(f"heel{s}", (0.06 * s, -0.08, 0.015), (0.09, 0.03, 0.03), shoes, bevel=0.005)
    B.box("hips", (0, 0, 0.265), (0.27, 0.14, 0.05), skirt, bevel=0.008)
    return FIG["z_adult"]


def fig_kid_legs(B, pants, shoes, sole="sole"):
    for s in (-1, 1):
        x = 0.068 * s
        feet = [B.box(f"sole{s}", (x, -0.008, 0.008), (0.132, 0.162, 0.016), sole, bevel=0.004),
                B.box(f"shoe{s}", (x, -0.008, 0.03), (0.13, 0.16, 0.03), shoes, bevel=0.006)]
        make_leg(B, s, x, hip=0.135, knee=0.09, pants=pants, foot_parts=feet)
    B.box("hips", (0, 0, 0.155), (0.27, 0.14, 0.05), pants, bevel=0.008)
    return FIG["z_kid"]


def fig_torso(B, z0, color):
    top = z0 + FIG["torso_h"]
    trapezoid(B, "torso", z0, top, 0.3, 0.24, 0.15, color)
    return top


def half_width(z0, z):
    """Half-width of the torso front at height z (it tapers from 0.15 to 0.12)."""
    return 0.15 - 0.03 * (z - z0) / FIG["torso_h"]


FRONT = ("plane", -0.075)


def print_poly(B, name, pts, color, off=0.001, surface=FRONT):
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    B.decal(name, ("raw", [(x - cx, z - cz) for x, z in pts]), cx, cz, 1, 1, color, surface, off)


def fig_head(B, top, skin):
    B.cylinder("neck", (0, 0, top + 0.015), 0.042, 0.03, skin)
    c = top + 0.12
    head = B.cylinder("head", (0, 0, c), 0.1, 0.18, skin)
    head.modifiers["bevel"].width = 0.03
    head.modifiers["bevel"].segments = 6
    return c, ((0, 0, c), (0.1, 0.1, 100.0))


def on_cyl(x, z, off=0.0015, r=0.1):
    return (x, -math.sqrt(r * r - x * x) - off, z)


def face_eyes(B, c, cyl, lids=False, lashes=False, glint=True, dz=0.0):
    c = c + dz   # dz moves the eyes up (+) or down
    for s in (-1, 1):
        B.decal(f"eye{s}", "ellipse", 0.036 * s, c + 0.008, 0.0135, 0.019, "eye", cyl, 0.0008)
        if glint:
            B.decal(f"glint{s}", "ellipse", 0.032 * s, c + 0.015, 0.0045, 0.0055, "white", cyl, 0.0015)
        if lids:  # heavy, half-closed lids and tired bags
            B.decal(f"lid{s}", "bar", 0.036 * s, c + 0.02, 0.017, 0.011, "fig_skin", cyl, 0.002)
            B.decal(f"lidline{s}", "bar", 0.036 * s, c + 0.009, 0.016, 0.0025, "eye", cyl, 0.0024)
            B.decal(f"bag{s}", "bar", 0.036 * s, c - 0.016, 0.012, 0.0018, "#b9886b", cyl, 0.0012)
        if lashes:
            B.decal(f"lash{s}", "bar", 0.043 * s, c + 0.026, 0.012, 0.003, "eye", cyl, 0.0016, rot=-0.35 * s)


def face_mouth(B, c, kind="smile"):
    if kind == "smile":
        pts = ((-0.024, c - 0.004 - 0.02), (0, c - 0.034), (0.024, c - 0.024))
    elif kind == "smirk":
        pts = ((-0.022, c - 0.03), (0.005, c - 0.032), (0.026, c - 0.02))
    else:  # flat
        pts = ((-0.018, c - 0.03), (0, c - 0.031), (0.018, c - 0.03))
    B.tube("mouth", [on_cyl(x, z) for x, z in pts], 0.0035, "eye")


# ------------------------------------------------------------------ cast members

def build_manager(B, mouth=True):
    top = fig_torso(B, fig_adult_legs(B, "#3a3f4a", "#15161b"), "#3a3f4a")
    z0 = top - FIG["torso_h"]
    print_poly(B, "shirt_v", [(-0.055, top - 0.003), (0.055, top - 0.003), (0, top - 0.15)], "white")
    print_poly(B, "tie", [(-0.012, top - 0.012), (0.012, top - 0.012), (0.02, top - 0.1), (0, top - 0.14),
                          (-0.02, top - 0.1)], "#c8323c", off=0.0016)
    for s in (-1, 1):
        print_poly(B, f"lapel{s}", [(0.055 * s, top - 0.003), (0.075 * s, top - 0.003), (0.012 * s, top - 0.17),
                                    (0.0 * s, top - 0.15)], "#2a2e37", off=0.0012)
    print_poly(B, "pocketsq", [(-0.11, top - 0.07), (-0.07, top - 0.07), (-0.08, top - 0.05), (-0.1, top - 0.05)],
               "#f2c14e", off=0.0012)
    fig_arms(B, top, "#3a3f4a", "fig_skin")
    manager_head(B, top, "#4a3326", mouth=mouth)


def manager_head(B, top, hair, visor=False, mouth=True):
    """The Manager's face: confident brows, a wide salesy grin, neat side-parted hair.
    The Founder is the same man later on: same grin and haircut, silver hair, a mirrored visor."""
    c, cyl = fig_head(B, top, "fig_skin")
    if visor:
        v = B.cylinder("visor", (0, 0, c + 0.01), 0.106, 0.048, "#c9d6e3", kind="chrome")
        v.modifiers["bevel"].width = 0.008
    else:
        face_eyes(B, c, cyl)
        for s in (-1, 1):
            B.decal(f"brow{s}", "bar", 0.037 * s, c + 0.042, 0.02, 0.0055, hair, cyl, 0.0008, rot=-0.12 * s)
    if mouth:  # leave it off when animated mouth shapes are added instead (video/lipsync_demo.py)
        grin = ((-0.034, c - 0.018), (-0.012, c - 0.034), (0.012, c - 0.034), (0.034, c - 0.018))
        B.tube("grin", [on_cyl(x, z) for x, z in grin], 0.0038, "eye")
    B.sphere("hair", (0, 0.012, c + 0.072), (0.108, 0.108, 0.05), hair, kind="glossy")
    B.capsule("part", (-0.05, -0.06, c + 0.098), (0.06, -0.03, c + 0.11), 0.02, hair, kind="glossy")


def build_founder(B, mouth=True):
    top = fig_torso(B, fig_adult_legs(B, "#c9b38a", "#f4f4f0"), "#8a8f99")
    z0 = top - FIG["torso_h"]
    hw0, hw1 = half_width(z0, z0) - 0.004, half_width(z0, top) - 0.004
    for s in (-1, 1):
        print_poly(B, f"vest{s}", [(hw0 * s, z0 + 0.004), (0.002 * s, z0 + 0.004), (0.002 * s, top - 0.08),
                                   (0.07 * s, top - 0.004), (hw1 * s, top - 0.004)], "#1f2a4d")
    print_poly(B, "zip", [(-0.003, z0 + 0.004), (0.003, z0 + 0.004), (0.003, top - 0.08), (-0.003, top - 0.08)],
               "#9aa3ad", off=0.0016)
    print_poly(B, "logo", [(0.07, top - 0.08), (0.1, top - 0.08), (0.1, top - 0.065), (0.07, top - 0.065)],
               "#f4f4f0", off=0.0016)
    _, hand = fig_arms(B, top, "#8a8f99", "fig_skin", poses=("down", "phone"))
    held_slab(B, hand, "phone", (0.07, 0.009, 0.125), "#15161b", screen="#bfe3ff",
              look_at=(0, -0.1, top + 0.13))  # at his face
    manager_head(B, top, "#b9bcc4", visor=True, mouth=mouth)  # the Manager, ten years later
    (lh, lk), (rh, rk) = B.legs[-2], B.legs[-1]
    lh.rotation_euler.x, lk.rotation_euler.x = 0.3, 0.45   # back leg: heel lifting
    rh.rotation_euler.x, rk.rotation_euler.x = -0.4, 0.15  # front leg: reaching forward


ANCHOR_EYES_DZ = 0.012   # her eyes sit a little higher (the fringe makes a low face look sleepy)


def build_anchor(B, mouth=True):
    top = fig_torso(B, fig_skirt(B, "#22305e", "#15161b"), "#c8323c")
    print_poly(B, "blouse", [(-0.05, top - 0.003), (0.05, top - 0.003), (0, top - 0.12)], "white")
    for s in (-1, 1):
        print_poly(B, f"lapel{s}", [(0.05 * s, top - 0.003), (0.07 * s, top - 0.003), (0.01 * s, top - 0.15),
                                    (0.0, top - 0.12)], "#a42830", off=0.0012)
    B.sphere("mic", (0.07, -0.08, top - 0.07), (0.012, 0.01, 0.014), "#15161b")
    _, hand = fig_arms(B, top, "#c8323c", "fig_skin", poses=("down", "phone"))
    held_slab(B, hand, "cuecards", (0.07, 0.01, 0.1), "white", look_at=(0, -0.1, top + 0.13))
    c, cyl = fig_head(B, top, "fig_skin")
    face_eyes(B, c, cyl, lashes=True, dz=ANCHOR_EYES_DZ)
    for s in (-1, 1):
        B.decal(f"cheek{s}", "ellipse", 0.06 * s, c - 0.022, 0.016, 0.01, "cheek", cyl, 0.0008)
        B.sphere(f"earring{s}", (0.1 * s, -0.01, c - 0.05), (0.012, 0.012, 0.012), "#e8c15a", kind="chrome")
    if mouth:  # leave it off when animated mouth shapes are added instead (video/lipsync_demo.py)
        B.decal("lips", "ellipse", 0, c - 0.03, 0.02, 0.008, "#c8323c", cyl, 0.0012)
    # big glossy helmet hair: covers the top, sides and back, frames the face
    B.sphere("hair", (0, 0.035, c + 0.06), (0.135, 0.13, 0.11), "#e2b85c", kind="glossy")
    for s in (-1, 1):
        B.sphere(f"hairside{s}", (0.1 * s, 0.045, c - 0.015), (0.048, 0.08, 0.085), "#e2b85c", kind="glossy")
    B.sphere("fringe", (-0.03, -0.075, c + 0.088), (0.085, 0.035, 0.026), "#e2b85c", kind="glossy", rot=(0, 0.25, 0))


def hood_material(B, color, inner):
    """Matte fabric; faces seen from behind (the inside of the hood) are a darker shade."""
    key = (f"hood:{color}:{inner}", "hood")
    if key in B.mats:
        return B.mats[key]
    m = bpy.data.materials.new(f"{B.style}_hood")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMixShader")
    for slot, col in ((1, color), (2, inner)):
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Base Color"].default_value = (*(srgb(PAL[col]) if col in PAL else srgb(col)), 1)
        bs.inputs["Roughness"].default_value = 0.9
        nt.links.new(bs.outputs[0], mix.inputs[slot])
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    B.mats[key] = m
    return m


def hood_shell(B, c, top, color, inner="#4b5260"):
    """A hood built as a hood: one piece of fabric spanning two edges, the neckline (an oval on
    the shoulders) and the face opening (an oval around the face). Neckline-front runs up to the
    chin, the sides to the sides of the face, and the back goes up over the back and top of the
    head to the forehead. Wherever the span would pass through the head it is pushed out to clear
    it, with a little slack, so it drapes like cloth. The rolled rim covers the front edge and the
    collar covers the neckline, so it is attached to the hoodie by construction."""
    H = Vector((0, 0, c))                  # head centre
    zn = top + 0.006                       # neckline height
    nrx, nry = 0.124, 0.084                # neckline oval (matches the torso top)
    ox, oz = 0.0, c - 0.008                # face opening: forehead to just above the neckline
    clear = Vector((0.118, 0.118, 0.13))   # clearance ellipsoid around the head

    def neckline(phi):
        return Vector((nrx * math.cos(phi), nry * math.sin(phi), zn))

    def opening(phi):
        """Face opening: phi +90deg = forehead, 0/180 = sides of the face, -90deg = the front of
        the neckline. The top half is an oval as wide as the head; below the cheeks the edges
        run down in a V to the neckline, so the hood is open at the chin and neck."""
        sn, cs = math.sin(phi), math.cos(phi)
        if sn >= 0:
            return Vector((ox + 0.1 * cs, -0.113 + 0.02 * cs * cs, oz + 0.094 * sn))
        t = -sn                                        # 0 at the cheeks, 1 at the neckline
        z = oz * (1 - t) + zn * t
        jaw = c - 0.075                                # full width down past the mouth to the jaw...
        wfac = min(1.0, max(0.0, (z - zn) / (jaw - zn)))
        wfac = wfac * wfac * (3 - 2 * wfac)            # ...then a smooth V below the chin
        x = ox + 0.1 * math.copysign(1.0, cs) * wfac * abs(cs) ** 0.25
        y = (-nry) * (1 - wfac) + (-0.093) * wfac
        return Vector((x, y, z))

    K, N = 28, 96
    verts = []
    for k in range(K + 1):
        f = k / K
        for j in range(N):
            phi = 2 * math.pi * j / N
            # travel round the head, not through it: interpolate direction and distance from the
            # head centre; paths whose ends are on opposite sides (the back, over the top) get
            # bowed up and over by a hint direction pointing up and outwards at this angle
            d1, d2 = neckline(phi) - H, opening(phi) - H
            u1, u2 = d1.normalized(), d2.normalized()
            w = max(0.0, -u1.dot(u2))
            hint = Vector((0.6 * math.cos(phi), 0.6 * math.sin(phi), 1.0)).normalized()
            u = (u1 * (1 - f) + u2 * f + hint * (2.2 * w * math.sin(math.pi * f))).normalized()
            dist = d1.length * (1 - f) + d2.length * f
            R = 1.0 / math.sqrt((u.x / clear.x) ** 2 + (u.y / clear.y) ** 2 + (u.z / clear.z) ** 2)
            R *= 1.0 + 0.07 * math.sin(math.pi * f)       # slack in the fabric mid-span
            r = 0.5 * (dist + R + math.sqrt((dist - R) ** 2 + 0.0006))  # soft max: never inside the head
            Q = H + u * r
            Q.z += 0.012 * math.sin(math.pi * f) * max(0.0, math.sin(phi))  # slight peak at the back
            verts.append(tuple(Q))
    faces = [(k * N + j, k * N + (j + 1) % N, (k + 1) * N + (j + 1) % N, (k + 1) * N + j)
             for k in range(K) for j in range(N)]
    me = bpy.data.meshes.new("hood")
    me.from_pydata(verts, [], faces)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    for fc in bm.faces:  # normals out, so the inside renders as back-facing (the darker shade)
        if fc.normal.dot(fc.calc_center_median() - H) < 0:
            fc.normal_flip()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    hood = bpy.data.objects.new("hood", me)
    B.col.objects.link(hood)
    me.materials.append(hood_material(B, color, inner))
    # soft rolled edge round the face opening
    rim = [tuple(opening(2 * math.pi * i / 64) + Vector((0, -0.002, 0))) for i in range(64)]
    B.tube("hood_rim", rim, 0.0095, color, closed=True, kind="matte")
    # collar on the shoulders, shaped like the torso top, covering the neckline edge
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.138, radius2=0.118, depth=0.04,
                                    location=(0, 0.0, top + 0.016))
    collar = bpy.context.object
    collar.name = "hoodcollar"
    collar.scale = (1.0, 0.7, 1.0)
    B._finish(collar, color, "matte", subdiv=False)


V9_INK = "#5b47c4"   # what v9's screen draws with


def build_v9(B, face=True):
    """The AI: pastel, a screen for a head, and no arms (it was never given hands). face=False
    leaves the screen blank (for animated eyes and mouths, see video/lipsync_demo.py)."""
    top = fig_torso(B, fig_kid_legs(B, "#b9a7f5", "#f6a6c8", sole="white"), "#b9a7f5")
    B.text("v9label", "AGENT v9", FONT_BOLD, 0.03, (0, -0.0765, top - 0.13), "#6a58c9")
    for s in (-1, 1):  # smooth shoulder caps where arms would be
        B.sphere(f"shoulder{s}", (0.12 * s, 0, top - 0.03), (0.03, 0.06, 0.03), "#b9a7f5")
    B.cylinder("neck", (0, 0, top + 0.015), 0.035, 0.03, "#9d8ae8")
    c = top + 0.13
    B.box("screenhead", (0, 0, c), (0.28, 0.1, 0.2), "#b9a7f5", bevel=0.03)
    B.box("screen", (0, -0.048, c), (0.235, 0.008, 0.155), "#f3f0ff", bevel=0.012, kind="glow")
    if face:
        v9_eyes(B, c, "happy")
        v9_spinner(B, c)
    B.capsule("antenna", (0.07, 0, c + 0.1), (0.09, 0, c + 0.15), 0.008, "#9d8ae8")
    B.sphere("antennaball", (0.09, 0, c + 0.16), (0.02, 0.02, 0.02), "#f6a6c8", kind="glossy")


V9_SCREEN = ("plane", -0.0525)


def v9_eyes(B, c, kind, name="eye"):
    """v9's screen eyes: happy ^ ^, round o o, hearts, smug > <, or closed - -."""
    objs = []
    for s in (-1, 1):
        x, z = 0.05 * s, c + 0.03
        if kind == "happy":
            for k in (-1, 1):
                objs.append(B.decal(f"{name}{s}{k}", "bar", x + 0.011 * k, z, 0.014, 0.004, V9_INK, V9_SCREEN, 0.001,
                                    rot=-0.75 * k))
        elif kind == "smug":       # > <  (each eye points in toward the nose)
            for k in (-1, 1):
                objs.append(B.decal(f"{name}{s}{k}", "bar", x + 0.004 * s, z + 0.007 * k, 0.012, 0.004, V9_INK,
                                    V9_SCREEN, 0.001, rot=0.6 * k * s))
        elif kind == "round":
            objs.append(B.decal(f"{name}{s}", "ellipse", x, z, 0.014, 0.017, V9_INK, V9_SCREEN, 0.001))
            objs.append(B.decal(f"{name}{s}g", "ellipse", x + 0.004, z + 0.006, 0.0045, 0.0055, "white", V9_SCREEN,
                                0.0015))
        elif kind == "heart":
            heart = [(0, -1), (-0.75, -0.1), (-0.95, 0.45), (-0.55, 0.9), (0, 0.5), (0.55, 0.9), (0.95, 0.45),
                     (0.75, -0.1)]
            objs.append(B.decal(f"{name}{s}", heart, x, z, 0.02, 0.018, "#f06292", V9_SCREEN, 0.001))
        else:  # closed
            objs.append(B.decal(f"{name}{s}", "bar", x, z - 0.004, 0.015, 0.004, V9_INK, V9_SCREEN, 0.001))
    return objs


def v9_spinner(B, c, phase=0, name="spin", n=9):
    """The loading-spinner smile: dots along an arc, fading toward one end (phase shifts the
    bright head of the spinner along the arc)."""
    objs = []
    for i in range(n):
        a = math.pi * (1.15 + 0.7 * i / (n - 1))
        shade = 0.25 + 0.75 * ((i - phase) % n) / (n - 1)
        col = "#%02x%02x%02x" % tuple(int(255 - (255 - v) * shade) for v in (91, 71, 196))
        objs.append(B.decal(f"{name}{i}", "ellipse", 0.05 * math.cos(a), c - 0.005 + 0.05 * math.sin(a), 0.007,
                            0.007, col, V9_SCREEN, 0.001))
    return objs


def build_user(B):
    """Hood up, half-lidded, blanket over the shoulders, both hands on the phone."""
    hood = "#6e7685"
    top = fig_torso(B, fig_adult_legs(B, "#7d808a", "#f6a6c8"), hood)
    z0 = top - FIG["torso_h"]
    print_poly(B, "pocket", [(-0.08, z0 + 0.03), (0.08, z0 + 0.03), (0.065, z0 + 0.1), (-0.065, z0 + 0.1)], "#5d6473")
    for s in (-1, 1):
        print_poly(B, f"string{s}", [(0.025 * s - 0.003, top - 0.01), (0.025 * s + 0.003, top - 0.01),
                                     (0.03 * s + 0.003, top - 0.1), (0.03 * s - 0.003, top - 0.1)], "white", off=0.0016)
    _, rhand = fig_arms(B, top, hood, "fig_skin", poses=("phone", "phone"))
    # phone clipped into the right hand by its peg, screen facing the User; left hand alongside
    held_slab(B, rhand, "phone", (0.08, 0.009, 0.135), "#15161b", screen="#bfe3ff",
              look_at=(0, -0.1, top + 0.128))  # screen pointed at their face
    c, cyl = fig_head(B, top, "fig_skin")
    face_eyes(B, c, cyl, lids=True, glint=False)
    face_mouth(B, c, "flat")
    hood_shell(B, c, top, hood)
    # sitting on a brick-built sofa: thighs forward, knees bent, feet dangling
    for hip, knee in B.legs[-2:]:
        hip.rotation_euler.x = -math.pi / 2
        knee.rotation_euler.x = math.pi / 2
    seat_top = 0.24 - 0.0725  # hip height minus half the leg's depth
    sofa, p = "#3f7f8c", PITCH
    # laid out on the stud grid: seat 2 studs wide between 1-stud armrests, 2 studs deep
    yc = 0.5 * p  # depth spans y = -0.5p .. 1.5p, so studs land on whole-pitch rows
    B.box("sofa_seat", (0, yc, seat_top / 2), (2 * p, 2 * p, seat_top), sofa, bevel=0.01)
    arm_top = 0.265
    for s in (-1, 1):
        B.box(f"sofa_arm{s}", (1.5 * p * s, yc, arm_top / 2), (p, 2 * p, arm_top), sofa, bevel=0.01)
        for j in (0, 1):
            stud(B, f"sofa_stud{s}{j}", 1.5 * p * s, j * p, arm_top, sofa, r=0.3 * p, h=0.21 * p)
    B.box("sofa_back", (0, 1.75 * p, 0.31), (4 * p, 0.5 * p, 0.29), sofa, bevel=0.012)
    # the phone's glow on the face
    ld = bpy.data.lights.new("phoneglow", "POINT")
    ld.energy, ld.color, ld.shadow_soft_size = 2.0, (0.6, 0.8, 1.0), 0.02
    lo = bpy.data.objects.new("phoneglow", ld)
    B.col.objects.link(lo)
    lo.location = (0, -0.2, top + 0.02)


def build_at(fn, B, x):
    before = set(bpy.data.objects)
    fn(B)
    for ob in set(bpy.data.objects) - before:
        if ob.parent is None:  # children follow their parent (leg parts hang off the hip pivots)
            ob.location.x += x


def name_sign(B, text, x):
    before = set(bpy.data.objects)
    B.box("sign", (0, -0.42, 0.04), (0.42, 0.02, 0.08), "white", bevel=0.006, kind="glossy")
    size = min(0.034, 0.39 / (0.66 * len(text)))  # shrink long names to fit the sign
    B.text("signtext", text, FONT_BOLD, size, (0, -0.4315, 0.04), "ink")
    for ob in set(bpy.data.objects) - before:
        ob.location.x += x


# ------------------------------------------------------------------ scene per style

def aim(ob, target):
    q = (Vector(target) - ob.location).to_track_quat("-Z", "Y")
    if ob.rotation_mode == "QUATERNION":
        ob.rotation_quaternion = q
    else:
        ob.rotation_euler = q.to_euler()


def key_rotation(ob, frame):
    """Keyframe an object's rotation as a quaternion kept continuous with its previous key.
    (Motion blur interpolates between keys; Euler angles can flip between equivalent values from
    one frame to the next, looking near straight up or down or across +-180 degrees, which
    smears the whole frame.) Leaves the object in quaternion mode."""
    from mathutils import Quaternion
    q = ob.rotation_quaternion.copy() if ob.rotation_mode == "QUATERNION" else ob.rotation_euler.to_quaternion()
    ob.rotation_mode = "QUATERNION"
    prev = ob.get("_last_q")
    if prev is not None and q.dot(Quaternion(prev)) < 0:
        q.negate()
    ob.rotation_quaternion = q
    ob.keyframe_insert("rotation_quaternion", frame=frame)
    ob["_last_q"] = tuple(q)


def render_style(style):
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    col = sc.collection
    B = Builder(style, col)
    if style == "brick":
        build_kevin_brick(B)
        baseplate(B)
    elif style == "fig":
        build_kevin_fig(B)
        fig_baseplate(B)
    else:
        build_kevin(B)

    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = A.res
    sc.render.resolution_x = A.res * 4 // 5  # portrait 4:5 card
    sc.eevee.taa_render_samples = A.samples
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*srgb(PAL["bg"]), 1)
    bg.inputs[1].default_value = 1.0 if style == "flat" else 0.8
    if style != "flat":
        # backdrop colour close to the unlit floor so there's no hard horizon line
        bg.inputs[0].default_value = (*srgb(PAL["floor"]), 1)
        bg.inputs[1].default_value = 0.35
    sc.view_settings.view_transform = "Standard" if style == "flat" else "AgX"
    sc.view_settings.look = "None" if style == "flat" else "AgX - Medium High Contrast"

    if style != "flat":
        bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
        floor = bpy.context.object
        floor.data.materials.append(material(style, "floor", "floor", "matte"))
        for name, loc, energy, size, color, target in (
            ("key", (-1.8, -2.4, 2.8), 300, 2.0, (1.0, 0.95, 0.9), (0, 0, 0.7)),
            ("fill", (2.4, -2.0, 1.2), 110, 3.0, (0.75, 0.85, 1.0), (0, 0, 0.7)),
            ("rim", (0.9, 1.6, 2.0), 140, 1.2, (1.0, 0.8, 0.6), (0, 0, 0.9)),
        ):
            ld = bpy.data.lights.new(name, "AREA")
            ld.energy, ld.size, ld.color = energy, size, color
            lo = bpy.data.objects.new(name, ld)
            col.objects.link(lo)
            lo.location = loc
            aim(lo, target)
    cam_d = bpy.data.cameras.new("cam")
    cam_o = bpy.data.objects.new("cam", cam_d)
    if style == "flat":
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = 1.95
        cam_o.location = (0, -6, 0.72)
        cam_o.rotation_euler = (math.pi / 2, 0, 0)
    elif style == "brick":
        cam_d.lens = 70
        cam_o.location = (0.75, -3.4, 1.05)
        aim(cam_o, (0, 0, 0.55))
    elif style == "fig":
        cam_d.lens = 70
        cam_o.location = (0.42, -2.0, 0.62)
        aim(cam_o, (0, 0, 0.37))
    else:
        cam_d.lens = 70
        cam_o.location = (0.9, -4.3, 1.3)
        aim(cam_o, (0, 0, 0.72))
    col.objects.link(cam_o)
    sc.camera = cam_o
    sc.render.filepath = f"{A.out.rstrip('/')}/kevin_{style}.png"
    bpy.ops.render.render(write_still=True)
    print("STYLE", style, "->", sc.render.filepath)


def render_lineup():
    style = "fig"
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    col = sc.collection
    B = Builder(style, col)
    cast = [("THE MANAGER", build_manager), ("THE MANAGER, 10 YEARS LATER", build_founder), ("KEVIN", build_kevin_fig),
            ("THE ANCHOR", build_anchor), ("AGENT v9", build_v9), ("A USER", build_user)]
    for k, (label, fn) in enumerate(cast):
        x = (-10 + 4 * k) * PITCH  # whole-stud positions, four studs apart
        build_at(fn, B, x)
        name_sign(B, label, x)
    fig_baseplate(B, nx=26, ny=7)

    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = A.res
    sc.render.resolution_x = A.res * 16 // 9
    sc.eevee.taa_render_samples = A.samples
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*srgb(PAL["floor"]), 1)
    bg.inputs[1].default_value = 0.35
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.65  # the white signs and pale figures were blowing out
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.04))
    bpy.context.object.data.materials.append(material(style, "floor", "floor", "matte"))
    for name, loc, energy, size, color, target in (
        ("key", (-2.5, -3.2, 3.2), 900, 3.0, (1.0, 0.95, 0.9), (0, 0, 0.4)),
        ("fill", (3.0, -2.8, 1.4), 320, 4.0, (0.75, 0.85, 1.0), (0, 0, 0.4)),
        ("rim", (0.0, 2.2, 2.4), 420, 4.0, (1.0, 0.8, 0.6), (0, 0, 0.5)),
    ):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        lo = bpy.data.objects.new(name, ld)
        col.objects.link(lo)
        lo.location = loc
        aim(lo, target)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 45
    cam_o = bpy.data.objects.new("cam", cam_d)
    cam_o.location = (0, -4.4, 1.05)
    aim(cam_o, (0, 0, 0.38))
    if A.cam:
        loc, tgt, lens = A.cam.split(":")
        cam_o.location = tuple(float(v) for v in loc.split(","))
        aim(cam_o, tuple(float(v) for v in tgt.split(",")))
        cam_d.lens = float(lens)
    col.objects.link(cam_o)
    sc.camera = cam_o
    sc.render.filepath = f"{A.out.rstrip('/')}/{A.name}.png"
    bpy.ops.render.render(write_still=True)
    print("LINEUP ->", sc.render.filepath)


if __name__ == "__main__":  # importable by other scripts (e.g. video/lipsync_demo.py)
    if A.lineup:
        render_lineup()
    else:
        for s in A.styles.split(","):
            render_style(s.strip())
