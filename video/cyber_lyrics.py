"""3D lyrics for cyberspace (verse 3 + chorus 3): extruded words floating round v9 wherever the
camera can see them: beside her, above her, below the spire. Three looks (lyric3d's style):

  neon   chunky condensed letters, a glowing face (cyan to pink), dark glossy sides
  glass  see-through tinted letters with glowing edges (like the hologram panels)
  brick  letters built from glowing toy bricks (a 5 x 7 brick font)

  blender -b --factory-startup --python video/cyber_lyrics.py -- --out video/build/cyber_lyrics
      (a style study: the three looks round v9, from three camera angles)
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402
import cyber_set as CS  # noqa: E402
from bricks import P, PL, Kit  # noqa: E402
from office_set import camera  # noqa: E402

BEBAS = "/usr/share/fonts/opentype/bebas-neue/BebasNeue-Bold.otf"
BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"


def _neon_face(name, c0, c1):
    """Glowing face: a gradient across the word (object x), from c0 to c1."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*SL.srgb(c0), 1)
    ramp.color_ramp.elements[1].color = (*SL.srgb(c1), 1)
    nt.links.new(sep.outputs["X"], ramp.inputs["Fac"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 2.2       # (brighter washes out to white)
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(c0), 1)
    return m


def _dark_sides(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (*SL.srgb("#140f26"), 1)
    bs.inputs["Roughness"].default_value = 0.15
    bs.inputs["Coat Weight"].default_value = 0.6
    return m


def _glass(name, color):
    """Tinted see-through letters, their edges (facing away from the camera) glowing."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*SL.srgb(color), 1)
    st = nt.nodes.new("ShaderNodeMath")
    st.operation = "MULTIPLY_ADD"
    st.inputs[1].default_value = 6.0
    st.inputs[2].default_value = 0.6
    nt.links.new(lw.outputs["Facing"], st.inputs[0])
    nt.links.new(st.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    a = nt.nodes.new("ShaderNodeMath")
    a.operation = "MULTIPLY_ADD"
    a.inputs[1].default_value = 0.75
    a.inputs[2].default_value = 0.05
    nt.links.new(lw.outputs["Facing"], a.inputs[0])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(a.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(color), 1)
    return m


def _acrylic_face(name, color):
    """Edge-lit acrylic: the letter faces are tinted glass you can see through, brighter toward
    the top, with faint scanlines."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    grad = nt.nodes.new("ShaderNodeMapRange")           # brighter toward the top of the letters
    grad.inputs["To Min"].default_value, grad.inputs["To Max"].default_value = 0.5, 1.4
    nt.links.new(sep.outputs["Y"], grad.inputs["Value"])
    sc_ = nt.nodes.new("ShaderNodeMath")                # scanlines
    sc_.operation = "SINE"
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 260.0
    nt.links.new(sep.outputs["Y"], k.inputs[0])
    nt.links.new(k.outputs[0], sc_.inputs[0])
    scan = nt.nodes.new("ShaderNodeMapRange")
    scan.inputs["From Min"].default_value, scan.inputs["From Max"].default_value = -1.0, 1.0
    scan.inputs["To Min"].default_value, scan.inputs["To Max"].default_value = 0.75, 1.0
    nt.links.new(sc_.outputs[0], scan.inputs["Value"])
    st = nt.nodes.new("ShaderNodeMath")
    st.operation = "MULTIPLY"
    nt.links.new(grad.outputs[0], st.inputs[0])
    nt.links.new(scan.outputs[0], st.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*SL.srgb(color), 1)
    nt.links.new(st.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.42
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(color), 1)
    return m


def _edge_glow(name, color, strength=6.0, white=0.0):
    """The glowing letter edges: the letter's own colour, brighter (white > 0 pushes it toward
    white, like a hot edge)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    c = SL.srgb(color)
    em.inputs["Color"].default_value = (*[white + (1 - white) * v for v in c], 1)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*c, 1)
    return m


def _text_curve(col, body, size, font, depth, name):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.size = size
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.extrude = depth / 2
    cu.bevel_depth = depth * 0.06
    cu.space_character = 1.12
    cu.bevel_resolution = 2
    ob = bpy.data.objects.new(name, cu)
    col.objects.link(ob)
    return ob, cu


# a 5 x 7 pixel font for the brick letters (just the letters the study needs, plus a few)
FONT5 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    " ": ["00000"] * 7, ",": ["00000"] * 5 + ["00100", "01000"], "'": ["00100", "00100"] + ["00000"] * 5,
}


def brick_word(B, body, colors, name):
    """A word built from 1 x 1 bricks laid flat (studs up), one brick per pixel of FONT5; the
    letters lie in the x-y plane (read from above), centred on the origin. Returns the object."""
    K = Kit(B)
    body = body.upper()
    x = 0
    for k, ch in enumerate(body):
        g = FONT5.get(ch, FONT5[" "])
        col = colors[k % len(colors)]
        for r, row in enumerate(g):
            for c, px in enumerate(row):
                if px == "1":
                    K.brick(x + c, 6 - r, 0, 1, 1, col, kind="glow" if (r + c) % 3 else None)
        x += 6
    ob = K.build(name)
    w = (x - 1) * P
    import mathutils
    ob.data.transform(mathutils.Matrix.Translation((-w / 2, -3.5 * P, 0)))
    return ob


def lyric3d(col, B, body, style, loc, rot=(0, 0, 0), size=0.3, colors=("#3ff0ff", "#ff5fd2"), name="lyric"):
    """One floating 3D lyric. rot: (x, y, z) Euler; text reads along local x, facing local -y
    (brick style: lies flat, studs up, unless rotated)."""
    if style == "brick":
        ob = brick_word(B, body, list(colors), name)
        ob.scale = (size / (7 * P),) * 3
    else:
        ob, cu = _text_curve(col, body, size, BEBAS if style == "neon" else BLACK, size * (0.35 if style == "neon" else 0.22),
                             name)
        if style in ("neon", "glass"):
            # as a mesh: the faces looking out the front (and back) and the sides get their
            # own materials (neon: glowing face, dark sides; glass: see-through face, glowing edges)
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            col.objects.unlink(ob)
            ob = bpy.data.objects.new(name, me)
            col.objects.link(ob)
            if style == "neon":
                me.materials.append(_neon_face(f"{name}_face", *colors[:2]))
                me.materials.append(_dark_sides(f"{name}_side"))
            else:
                me.materials.append(_acrylic_face(f"{name}_face", colors[0]))
                me.materials.append(_edge_glow(f"{name}_edge", colors[0]))
            for poly in me.polygons:
                poly.material_index = 0 if abs(poly.normal.z) > 0.7 else 1
        else:
            cu.materials.append(_glass(f"{name}_glass", colors[0]))
        ob.rotation_euler = (math.pi / 2 + rot[0], rot[1], rot[2])     # stand up, facing -y
    ob.location = loc
    if style == "brick":
        ob.rotation_euler = rot
    return ob


def study(sc, out):
    """The three looks round v9, from three angles."""
    S = CS.build(sc, v9=True, holos=False)
    col = sc.collection
    B = SL.Builder("fig", col)
    # all glass: beside her, above her, below the spire
    lyric3d(col, B, "SMARTEST THING", "glass", (-0.78, 0.15, 0.64), (0, 0, 0.45), 0.2, ("#3ff0ff",), "beside")
    lyric3d(col, B, "ON EARTH", "glass", (-0.72, 0.18, 0.4), (0, 0, 0.45), 0.2, ("#ff5fd2",), "beside2")
    lyric3d(col, B, "HELLO, I'M", "glass", (0.0, 0.25, 1.35), (0.35, 0, 0), 0.22, ("#b9a7f5",), "above")
    lyric3d(col, B, "AGENT VERSION NINE", "glass", (0.0, 0.3, 1.08), (0.35, 0, 0), 0.2, ("#3ff0ff",), "above2")
    lyric3d(col, B, "NEVER GIVEN", "glass", (0.0, -0.1, -1.0), (-math.pi / 2, 0, 0), 0.34, ("#ff5fd2",), "below")
    lyric3d(col, B, "HANDS", "glass", (0.0, -0.75, -1.0), (-math.pi / 2, 0, 0), 0.5, ("#3ff0ff",), "below2")
    CS.setup_render(sc, 1080, False)
    os.makedirs(out, exist_ok=True)
    for name, loc, tgt, lens in (("beside", (0.9, -2.2, 0.75), (-0.25, 0.0, 0.5), 35),
                                  ("above", (0.25, -1.6, 0.15), (0.0, 0.1, 0.95), 26),
                                  ("below", (0.4, -0.9, 1.6), (0.0, 0.0, -1.1), 30)):
        camera(sc, loc, tgt, lens)
        sc.render.filepath = os.path.join(out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "cyber_lyrics"))
    A = ap.parse_args(argv)
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    study(sc, A.out)


if __name__ == "__main__" and "--lookbook" not in sys.argv and "--highlight" not in sys.argv:
    main()


# ---------------------------------------------------------------- glass variants (a look book)
def _mat(name, build):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    sh = build(nt)
    nt.links.new(sh, out.inputs["Surface"])
    return m


def _see_through(nt, emit_socket_or_color, strength, alpha):
    em = nt.nodes.new("ShaderNodeEmission")
    if isinstance(emit_socket_or_color, tuple):
        em.inputs["Color"].default_value = emit_socket_or_color
    else:
        nt.links.new(emit_socket_or_color, em.inputs["Color"])
    if isinstance(strength, (int, float)):
        em.inputs["Strength"].default_value = strength
    else:
        nt.links.new(strength, em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if isinstance(alpha, (int, float)):
        mix.inputs["Fac"].default_value = alpha
    else:
        nt.links.new(alpha, mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    return mix.outputs[0]


def _view_ramp(nt, colors, blend=0.5):
    """A colour that shifts with the viewing angle (iridescent)."""
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = blend
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].color = (*SL.srgb(colors[0]), 1)
    els[1].color = (*SL.srgb(colors[-1]), 1)
    for i, c in enumerate(colors[1:-1]):
        e = els.new((i + 1) / (len(colors) - 1))
        e.color = (*SL.srgb(c), 1)
    nt.links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
    return ramp.outputs["Color"]


VARIANTS = {
    # name: (face material builder(color), edge material builder(color), depth factor, font)
    "acrylic": (lambda c: _acrylic_face("f", c), lambda c: _edge_glow("e", c, 5.0, white=0.35), 0.22, BLACK),
    "acrylic_same": (lambda c: _acrylic_face("f", c), lambda c: _edge_glow("e", c, 3.2, white=0.0), 0.22, BLACK),
    "acrylic_same_hot": (lambda c: _acrylic_face("f", c), lambda c: _edge_glow("e", c, 6.0, white=0.0), 0.22, BLACK),
    "frosted": (lambda c: _mat("f", lambda nt: _see_through(nt, (*[0.75 + 0.25 * v for v in SL.srgb(c)], 1), 1.6, 0.82)),
                lambda c: _edge_glow("e", c, 7.0), 0.22, BLACK),
    "iridescent": (lambda c: _mat("f", lambda nt: _see_through(nt, _view_ramp(nt, ("#3ff0ff", "#b98cff", "#ff5fd2", "#ffd166")), 1.4, 0.45)),
                   lambda c: _mat("e", lambda nt: _see_through(nt, _view_ramp(nt, ("#ffffff", "#3ff0ff", "#ff5fd2"), 0.3), 6.0, 1.0)),
                   0.3, BLACK),
    "outline": (lambda c: _mat("f", lambda nt: _see_through(nt, (*SL.srgb(c), 1), 0.8, 0.12)),
                lambda c: _edge_glow("e", c, 9.0), 0.08, BLACK),
    "smoked": (lambda c: _mat("f", lambda nt: _see_through(nt, (0.02, 0.02, 0.05, 1), 0.2, 0.75)),
               lambda c: _edge_glow("e", c, 8.0), 0.3, BLACK),
    "block": (lambda c: _acrylic_face("f", c), lambda c: _edge_glow("e", c, 3.0), 0.7, BEBAS),
}


def glass_variant(col, body, variant, loc, rot, size, color, name):
    face, edge, depth, font = VARIANTS[variant]
    ob, cu = _text_curve(col, body, size, font, size * depth, name)
    cu.space_character = 1.16
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    col.objects.unlink(ob)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    me.materials.append(face(color))
    me.materials.append(edge(color))
    for poly in me.polygons:
        poly.material_index = 0 if abs(poly.normal.z) > 0.7 else 1
    ob.rotation_euler = (math.pi / 2 + rot[0], rot[1], rot[2])
    ob.location = loc
    return ob


def lookbook(out):
    """The same shot (two lines above v9, looking up) in each glass variant."""
    os.makedirs(out, exist_ok=True)
    for v in (sys.argv[sys.argv.index("--lookbook") + 1].split(",") if len(sys.argv) > sys.argv.index("--lookbook") + 1
              else VARIANTS):
        sc = bpy.context.scene
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        for m in list(bpy.data.materials):
            bpy.data.materials.remove(m)
        CS.build(sc, v9=True, holos=False)
        col = sc.collection
        glass_variant(col, "HELLO, I'M", v, (0.0, 0.25, 1.32), (0.35, 0, 0), 0.22, "#b9a7f5", "l1")
        glass_variant(col, "AGENT VERSION NINE", v, (0.0, 0.3, 1.05), (0.35, 0, 0), 0.2, "#3ff0ff", "l2")
        CS.setup_render(sc, 720, False)
        camera(sc, (0.25, -1.6, 0.15), (0.0, 0.1, 0.95), 26)
        sc.render.filepath = os.path.join(out, f"glass_{v}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__" and "--lookbook" in sys.argv:
    lookbook(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "cyber_lookbook"))


# ---------------------------------------------------------------- word states and highlights
HL_GOLD = "#ffd166"


def word_material(name, color, hl_color=HL_GOLD, white_hot=False):
    """Glass (acrylic face, same-colour hot edges) with two animatable inputs, 'lit' (0 a word
    not sung yet, faint .. 1 sung) and 'hl' (1 while it's being sung). hl_color: the highlight
    swaps to that colour; white_hot: it goes toward white."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    # 'lit' and 'hl' are read from each word object's own properties (one material serves a
    # whole line's colour; every word can still light up on its own)
    lit = nt.nodes.new("ShaderNodeAttribute")
    lit.attribute_type, lit.attribute_name = "OBJECT", '["lit"]'
    hl = nt.nodes.new("ShaderNodeAttribute")
    hl.attribute_type, hl.attribute_name = "OBJECT", '["hl"]'
    lit_out, hl_out = lit.outputs["Fac"], hl.outputs["Fac"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeVectorMath")             # front/back faces vs the edges (object space)
    nz.operation = "DOT_PRODUCT"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vt = nt.nodes.new("ShaderNodeVectorTransform")
    vt.vector_type, vt.convert_from, vt.convert_to = "NORMAL", "WORLD", "OBJECT"
    nt.links.new(geo.outputs["Normal"], vt.inputs[0])
    nt.links.new(vt.outputs[0], nz.inputs[0])
    nz.inputs[1].default_value = (0, 0, 1)
    face = nt.nodes.new("ShaderNodeMath")
    face.operation = "ABSOLUTE"
    nt.links.new(nz.outputs["Value"], face.inputs[0])
    isface = nt.nodes.new("ShaderNodeMath")
    isface.operation = "GREATER_THAN"
    isface.inputs[1].default_value = 0.7
    nt.links.new(face.outputs[0], isface.inputs[0])

    def val(op, a, b):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    base = (*SL.srgb(color), 1)
    target = (*SL.srgb(hl_color), 1) if hl_color else ((1, 1, 1, 1) if white_hot else base)
    colmix = nt.nodes.new("ShaderNodeMix")
    colmix.data_type = "RGBA"
    colmix.inputs["A"].default_value = base
    colmix.inputs["B"].default_value = target
    nt.links.new(val("MULTIPLY", hl_out, 0.85 if white_hot else 1.0), colmix.inputs["Factor"])
    # strengths: faces 0.25 (unsung) .. 1.0 (sung) .. 3.0 (highlight); edges 1.2 .. 6 .. 12
    f_str = val("ADD", val("MULTIPLY", lit_out, 0.75), 0.25)
    f_str = val("ADD", f_str, val("MULTIPLY", hl_out, 2.0))
    e_str = val("ADD", val("MULTIPLY", lit_out, 4.8), 1.2)
    e_str = val("ADD", e_str, val("MULTIPLY", hl_out, 6.0))
    strength = nt.nodes.new("ShaderNodeMix")
    strength.data_type = "FLOAT"
    nt.links.new(isface.outputs[0], strength.inputs["Factor"])
    nt.links.new(e_str, strength.inputs["A"])
    nt.links.new(f_str, strength.inputs["B"])
    # scanlines on the faces
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    sl = val("SINE", val("MULTIPLY", sep.outputs["Y"], 260.0), 0.0)
    scan = val("ADD", val("MULTIPLY", sl, 0.12), 0.88)
    st = val("MULTIPLY", strength.outputs["Result"], scan)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(colmix.outputs["Result"], em.inputs["Color"])
    nt.links.new(st, em.inputs["Strength"])
    # opacity: faces 0.12 (unsung) .. 0.42 (sung) .. 0.85 (highlight); edges 0.35 .. 1
    f_a = val("ADD", val("ADD", val("MULTIPLY", lit_out, 0.3), 0.12), val("MULTIPLY", hl_out, 0.43))
    e_a = val("ADD", val("MULTIPLY", lit_out, 0.65), 0.35)
    alpha = nt.nodes.new("ShaderNodeMix")
    alpha.data_type = "FLOAT"
    nt.links.new(isface.outputs[0], alpha.inputs["Factor"])
    nt.links.new(e_a, alpha.inputs["A"])
    nt.links.new(f_a, alpha.inputs["B"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(alpha.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = base
    return m


_WORD_MATS = {}


def lyric_words(col, words, loc, rot, size, color, name, hl_color=HL_GOLD, white_hot=False):
    """A line as separate glass words (each its own object and material, so each can light up),
    centred at loc. Returns [(word object, material, its rest location)]."""
    font = bpy.data.fonts.load(BLACK, check_existing=True)
    items, x = [], 0.0
    gap = size * 0.5               # (room for a highlighted word to pop)
    for k, body in enumerate(words):
        cu = bpy.data.curves.new(f"{name}{k}", "FONT")
        cu.body, cu.font, cu.size = body, font, size
        cu.align_x, cu.align_y = "LEFT", "CENTER"
        cu.extrude, cu.bevel_depth, cu.bevel_resolution = size * 0.11, size * 0.013, 2
        cu.space_character = 1.16
        tmp = bpy.data.objects.new("tmp", cu)
        col.objects.link(tmp)
        bpy.context.view_layer.update()
        w = tmp.dimensions.x
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
        col.objects.unlink(tmp)
        import mathutils
        me.transform(mathutils.Matrix.Translation((-w / 2, 0, 0)))      # origin at the word's centre (pops evenly)
        ob = bpy.data.objects.new(f"{name}{k}", me)
        col.objects.link(ob)
        key = (color, hl_color, white_hot)
        if key not in _WORD_MATS:
            _WORD_MATS[key] = word_material(f"word_{color}", color, hl_color, white_hot)
        mat = _WORD_MATS[key]
        me.materials.append(mat)
        ob["lit"], ob["hl"] = 1.0, 0.0
        items.append([ob, mat, x, w])
        x += w + gap
    total = x - gap
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    root.location = loc
    root.rotation_euler = (math.pi / 2 + rot[0], rot[1], rot[2])
    out = []
    for ob, mat, x0, w in items:
        ob.parent = root
        ob.location = (x0 + w / 2 - total / 2, 0, 0)
        out.append((ob, mat, ob.location.copy()))
    return root, out


def set_word(item, state, push=False, pop=1.0):
    """Pose a word: state 'unsung', 'now' (being sung) or 'sung'."""
    ob, mat, rest = item
    ob["lit"], ob["hl"] = {"unsung": (0.0, 0.0), "now": (1.0, 1.0), "sung": (1.0, 0.0)}[state]
    s = pop if state == "now" else 1.0
    ob.scale = (s, s, s)
    ob.location = rest + (Vector((0, 0, 0.09)) if (push and state == "now") else Vector((0, 0, 0)))


def highlight_study(out):
    """'HELLO, I'M AGENT' sung, 'VERSION' being sung, 'NINE' not yet: in four highlight looks."""
    os.makedirs(out, exist_ok=True)
    looks = {"A_fill": dict(pop=1.12), "B_gold": dict(hl_color=HL_GOLD, pop=1.08),
             "C_whitehot": dict(white_hot=True, pop=1.08), "D_push": dict(pop=1.12, push=True)}
    for name, opt in looks.items():
        sc = bpy.context.scene
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
        for m in list(bpy.data.materials):
            bpy.data.materials.remove(m)
        CS.build(sc, v9=True, holos=False)
        col = sc.collection
        _, l1 = lyric_words(col, ["HELLO,", "I'M"], (0.0, 0.25, 1.32), (0.35, 0, 0), 0.22, "#b9a7f5", "l1",
                            opt.get("hl_color"), opt.get("white_hot", False))
        _, l2 = lyric_words(col, ["AGENT", "VERSION", "NINE"], (0.0, 0.3, 1.05), (0.35, 0, 0), 0.2, "#3ff0ff", "l2",
                            opt.get("hl_color"), opt.get("white_hot", False))
        for it in l1:
            set_word(it, "sung")
        for it, st in zip(l2, ("sung", "now", "unsung")):
            # push: toward the camera, which is in front of and below the line (local -y is the
            # text's front; with the root's rotation local +z here is toward the viewer)
            set_word(it, st, push=opt.get("push", False), pop=opt.get("pop", 1.0))
        CS.setup_render(sc, 720, False)
        camera(sc, (0.25, -1.6, 0.15), (0.0, 0.1, 0.95), 26)
        sc.render.filepath = os.path.join(out, f"hl_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__" and "--highlight" in sys.argv:
    highlight_study(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "cyber_highlight"))
