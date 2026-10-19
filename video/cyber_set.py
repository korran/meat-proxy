"""Cyberspace, for verse 3 and chorus 3: Agent Version Nine on a tall brick pedestal in a void.
A faint glowing grid far below fades into the dark, soft bubbles drift up past her, and the
graphics appear as hologram panels floating round her (hologram()).

  blender -b --factory-startup --python video/cyber_set.py -- --out video/build/cyber_stills \\
      [--preview] [--res 1080] [--only wide,stage]

The pedestal stands at the origin; its top (where v9 stands) is at z = TOP. Everything is at the
cast's scale (one stud = 0.136 units, see bricks.py).
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402
from bricks import BR, P, PL, Kit  # noqa: E402
from office_set import camera, glass_material, image_material, place_figure  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "build", "cyber")

PED_W, PED_D = 2, 1          # the column, studs
TOP_W, TOP_D = 4, 3          # the platform on top (room for her feet)
COURSES = 60                  # bricks tall below the top (it runs down into the haze)
TOP = 0.0                     # its top: v9 stands at z = 0, the pedestal goes down from there
GRID_Z = -14.0                # the glowing grid far below
DARK, DARK2 = "#1a1530", "#241d40"
CYAN, PINK, LILAC = "#3ff0ff", "#ff5fd2", "#b9a7f5"


def emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*SL.srgb(color), 1)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(color), 1)
    return m


# ---------------------------------------------------------------- the void
def void_world(sc):
    """A deep violet void: darker below, a faint glow toward the horizon."""
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    nt = sc.world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.3, (0.003, 0.002, 0.01, 1)
    els[1].position, els[1].color = 0.5, (0.022, 0.012, 0.055, 1)
    e = els.new(0.85)
    e.color = (0.006, 0.004, 0.02, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -1.0, 1.0
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


def grid_floor(col):
    """A huge glowing grid far below, fading out with distance from the pedestal."""
    me = bpy.data.meshes.new("grid")
    R = 220.0
    me.from_pydata([(-R, -R, 0), (R, -R, 0), (R, R, 0), (-R, R, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("grid", me)
    col.objects.link(ob)
    ob.location.z = GRID_Z
    m = bpy.data.materials.new("grid")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def line(axis):                       # 1 on a grid line, 0 between (cell 2 units)
        mm = nt.nodes.new("ShaderNodeMath")
        mm.operation = "PINGPONG"
        mm.inputs[1].default_value = 1.0
        nt.links.new(sep.outputs[axis], mm.inputs[0])
        sm = nt.nodes.new("ShaderNodeMapRange")
        sm.inputs["From Min"].default_value, sm.inputs["From Max"].default_value = 0.03, 0.0
        nt.links.new(mm.outputs[0], sm.inputs["Value"])
        return sm.outputs[0]
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(line("X"), mx.inputs[0])
    nt.links.new(line("Y"), mx.inputs[1])
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    fade = nt.nodes.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = 10.0, 120.0
    fade.inputs["To Min"].default_value, fade.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(ln.outputs["Value"], fade.inputs["Value"])
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    nt.links.new(mx.outputs[0], k.inputs[0])
    nt.links.new(fade.outputs[0], k.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*SL.srgb("#7a4dff"), 1)
    nt.links.new(k.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (0.05, 0.03, 0.12, 1)
    me.materials.append(m)
    return ob


def bubble_material(name, color):
    """A soap-bubble-ish sphere: clear in the middle, a faint glowing rim."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.6           # a broad, soft rim
    rim = nt.nodes.new("ShaderNodeMath")
    rim.operation = "POWER"
    rim.inputs[1].default_value = 1.3
    nt.links.new(lw.outputs["Facing"], rim.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*SL.srgb(color), 1)
    em.inputs["Strength"].default_value = 1.6
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY_ADD"                     # the rim, plus a faint fill
    k.inputs[1].default_value = 0.45
    k.inputs[2].default_value = 0.05
    nt.links.new(rim.outputs[0], k.inputs[0])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(k.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(color), 1)
    return m


def halo_material(name, color):
    """A glow round a bubble: a bigger sphere, brightest at its middle, fading to nothing at its
    edge (so it reads as a soft halo)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    m.use_backface_culling = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 3.0
    nt.links.new(inv.outputs[0], pw.inputs[0])
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 0.14
    nt.links.new(pw.outputs[0], k.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*SL.srgb(color), 1)
    em.inputs["Strength"].default_value = 2.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(k.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(color), 1)
    return m


def data_cubes(col, n=140, seed=3):
    """Soft bubbles scattered through the void round the pedestal (animate_cubes drifts them
    upward, wobbling a little)."""
    rng = random.Random(seed)
    meshes = []
    for k, c in enumerate((CYAN, LILAC, PINK)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
        ob = bpy.context.object
        for cc in list(ob.users_collection):
            cc.objects.unlink(ob)
        ob.data.materials.append(bubble_material(f"bubble{k}", c))
        for poly in ob.data.polygons:
            poly.use_smooth = True
        halo = ob.data.copy()
        halo.materials.clear()
        halo.materials.append(halo_material(f"halo{k}", c))
        meshes.append((ob.data, halo))
        bpy.data.objects.remove(ob)
    cubes = []
    for i in range(n):
        r = rng.uniform(1.0, 9.0)
        a = rng.uniform(0, math.tau)
        me, halo_me = meshes[rng.choice((0, 1, 1, 2))]
        ob = bpy.data.objects.new(f"bubble{i}", me)
        col.objects.link(ob)
        h = bpy.data.objects.new(f"bubble{i}_halo", halo_me)       # the soft glow round it
        col.objects.link(h)
        h.parent = ob
        h.scale = (2.4, 2.4, 2.4)
        s = rng.uniform(0.012, 0.04) * (1 + r / 7)
        ob.scale = (s, s, s)
        ob.location = (r * math.cos(a), r * math.sin(a) + 2.0, rng.uniform(-10.0, 4.0))
        cubes.append((ob, rng.uniform(0.08, 0.3)))
    return cubes


def animate_cubes(cubes, n, fps, seed=5):
    """The bubbles rise slowly, swaying side to side."""
    rng = random.Random(seed)
    for ob, speed in cubes:
        x0, y0, z0 = ob.location
        ph, amp, rate = rng.uniform(0, math.tau), rng.uniform(0.03, 0.1), rng.uniform(0.3, 0.7)
        step = max(1, int(fps / 4))
        for f in range(1, n + 1, step):
            t = (f - 1) / fps
            ob.location = (x0 + amp * math.sin(ph + rate * math.tau * t), y0, z0 + speed * t)
            ob.keyframe_insert("location", frame=f)


# ---------------------------------------------------------------- the pedestal
def build_pedestal(B):
    """A slim 2 x 1 column of dark glossy bricks under a 4 x 3 platform, detailed
    near the top where the camera usually is: a flared capital with a glowing rim, glowing
    bands close together under it (spreading out further down), rows of little LED studs and a
    vent grille. Returns (pedestal, [LED objects to blink])."""
    K = Kit(B)
    w, d = PED_W, PED_D
    x0, y0 = -w / 2, -d / 2
    gap = 0.0
    band_at, step, c = [], 1, 3
    while c < COURSES:                     # bands: tight under the top, then further and further apart
        band_at.append(c)
        c += step
        step += 1
    for c in range(COURSES):
        z = -3 * (c + 1) - 3
        col = DARK if c % 2 else DARK2
        K.brick(x0, y0, z, w, d, col, studs=False)
        if c in band_at:
            g = CYAN if band_at.index(c) % 2 else PINK
            K.box((x0 - 0.05) * P, (y0 - 0.05) * P, (z + 1.2) * PL, (x0 + w + 0.05) * P, (y0 + d + 0.05) * P,
                  (z + 1.7) * PL, g, kind="glow")
    # vent grille on the front, just under the capital
    for k in range(4):
        K.box((x0 + 0.3) * P, (y0 - 0.04) * P, (-7.4 - 0.55 * k) * PL, (x0 + w - 0.3) * P, y0 * P,
              (-7.15 - 0.55 * k) * PL, "#0d0a1a")
    # the capital: a 3 x 2 step with a glowing rim, then the 4 x 3 studded top she stands on
    K.plate(-1.5, -1.0, -3, 3, 2, DARK2, studs=False)
    K.box(-1.55 * P, -1.05 * P, -2.55 * PL, 1.55 * P, 1.05 * P, -2.3 * PL, CYAN, kind="glow")
    K.plate(-TOP_W / 2, -TOP_D / 2, -2, TOP_W, TOP_D, DARK, studs=False)
    K.box((-TOP_W / 2 - 0.04) * P, (-TOP_D / 2 - 0.04) * P, -1.6 * PL, (TOP_W / 2 + 0.04) * P,
          (TOP_D / 2 + 0.04) * P, -1.35 * PL, PINK, kind="glow")
    K.plate(-TOP_W / 2, -TOP_D / 2, -1, TOP_W, TOP_D, "#2e2552", studs=True)
    ped = K.build("pedestal")
    # LED studs: two rows on the front and sides under the capital (separate, so they can blink)
    leds = []
    rng = random.Random(9)
    for row in range(2):
        z = (-10.5 - 1.6 * row) * PL
        for side, (ax, n) in enumerate((("x", w), ("y", d), ("y", d))):
            for i in range(n * 2):
                Kl = Kit(B)
                colr = rng.choice((CYAN, PINK, "#7dff9a", CYAN))
                if side == 0:
                    cx, cy = (x0 + 0.25 + 0.5 * i) * P, y0 * P - 0.008      # (front: 4 per row)
                elif side == 1:
                    cx, cy = (x0 * P - 0.008), (y0 + 0.25 + 0.5 * i) * P
                else:
                    cx, cy = ((x0 + w) * P + 0.008), (y0 + 0.25 + 0.5 * i) * P
                Kl.box(cx - 0.012, cy - 0.012, z - 0.012, cx + 0.012, cy + 0.012, z + 0.012, colr, kind="glow")
                leds.append(Kl.build(f"led{row}_{side}_{i}", bevel=0.0))
    return ped, leds


def animate_leds(leds, n, fps, seed=4):
    """The LED studs blink, each at its own rhythm."""
    rng = random.Random(seed)
    for ob in leds:
        t, on = rng.uniform(0, 1), True
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", frame=1)
        while t * fps < n:
            on = not on
            ob.scale = (1, 1, 1) if on else (0.001, 0.001, 0.001)
            ob.keyframe_insert("scale", frame=int(t * fps) + 1)
            t += rng.uniform(0.15, 1.2)
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


# ---------------------------------------------------------------- holograms
def holo_material(name, path=None, color=CYAN, movie=False, offset=0):
    """A hologram: the picture (or a flat tint) glowing through scanlines, a little
    see-through, brighter at the edges (a frame)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tint = nt.nodes.new("ShaderNodeRGB")
    tint.outputs[0].default_value = (*SL.srgb(color), 1)
    if path:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(path, check_existing=True)
        if movie:
            tex.image.source = "MOVIE"
            iu = tex.image_user
            iu.frame_duration = tex.image.frame_duration
            iu.frame_start, iu.frame_offset, iu.use_auto_refresh = 1 + offset, 0, True
        ink = nt.nodes.new("ShaderNodeMix")               # the picture, tinted a little
        ink.data_type, ink.blend_type = "RGBA", "MIX"
        ink.inputs["Factor"].default_value = 0.3
        nt.links.new(tex.outputs["Color"], ink.inputs["A"])
        nt.links.new(tint.outputs[0], ink.inputs["B"])
        dim = nt.nodes.new("ShaderNodeMix")               # the glass behind it: the tint, dimmer
        dim.data_type, dim.blend_type = "RGBA", "MULTIPLY"
        dim.inputs["Factor"].default_value = 1.0
        nt.links.new(tint.outputs[0], dim.inputs["A"])
        dim.inputs["B"].default_value = (0.35, 0.35, 0.35, 1)
        mixc = nt.nodes.new("ShaderNodeMix")
        mixc.data_type = "RGBA"
        nt.links.new(tex.outputs["Alpha"], mixc.inputs["Factor"])
        nt.links.new(dim.outputs["Result"], mixc.inputs["A"])
        nt.links.new(ink.outputs["Result"], mixc.inputs["B"])
        col_out = mixc.outputs["Result"]
        alpha_src = tex.outputs["Alpha"]
    else:
        col_out = tint.outputs[0]
        alpha_src = None
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    sl = nt.nodes.new("ShaderNodeMath")                 # scanlines
    sl.operation = "SINE"
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 420.0
    nt.links.new(sep.outputs["Y"], k.inputs[0])
    nt.links.new(k.outputs[0], sl.inputs[0])
    scan = nt.nodes.new("ShaderNodeMapRange")
    scan.inputs["From Min"].default_value, scan.inputs["From Max"].default_value = -1.0, 1.0
    scan.inputs["To Min"].default_value, scan.inputs["To Max"].default_value = 0.65, 1.0
    nt.links.new(sl.outputs[0], scan.inputs["Value"])
    edge = []                                           # a bright frame round the edge
    for ax in ("X", "Y"):
        d = nt.nodes.new("ShaderNodeMath")
        d.operation = "PINGPONG"
        d.inputs[1].default_value = 0.5
        nt.links.new(sep.outputs[ax], d.inputs[0])
        e = nt.nodes.new("ShaderNodeMapRange")
        e.inputs["From Min"].default_value, e.inputs["From Max"].default_value = 0.012, 0.0
        nt.links.new(d.outputs[0], e.inputs["Value"])
        edge.append(e.outputs[0])
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "MAXIMUM"
    nt.links.new(edge[0], fr.inputs[0])
    nt.links.new(edge[1], fr.inputs[1])
    flick = nt.nodes.new("ShaderNodeValue")             # animated by animate_holo (flicker, fade)
    flick.name = "level"
    flick.outputs[0].default_value = 1.0
    strength = nt.nodes.new("ShaderNodeMath")
    strength.operation = "MULTIPLY_ADD"
    nt.links.new(fr.outputs[0], strength.inputs[0])
    strength.inputs[1].default_value = 3.0
    nt.links.new(scan.outputs[0], strength.inputs[2])
    s2 = nt.nodes.new("ShaderNodeMath")
    s2.operation = "MULTIPLY"
    nt.links.new(strength.outputs[0], s2.inputs[0])
    nt.links.new(flick.outputs[0], s2.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(col_out, em.inputs["Color"])
    s3 = nt.nodes.new("ShaderNodeMath")
    s3.operation = "MULTIPLY"
    s3.inputs[1].default_value = 1.6
    nt.links.new(s2.outputs[0], s3.inputs[0])
    nt.links.new(s3.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    a = nt.nodes.new("ShaderNodeMath")                  # see-through glass, solid on the frame (and ink)
    a.operation = "MAXIMUM"
    a.inputs[0].default_value = 0.3
    nt.links.new(fr.outputs[0], a.inputs[1])
    if alpha_src:
        a2 = nt.nodes.new("ShaderNodeMath")
        a2.operation = "MAXIMUM"
        nt.links.new(a.outputs[0], a2.inputs[0])
        a2i = nt.nodes.new("ShaderNodeMath")
        a2i.operation = "MULTIPLY"
        a2i.inputs[1].default_value = 0.9
        nt.links.new(alpha_src, a2i.inputs[0])
        nt.links.new(a2i.outputs[0], a2.inputs[1])
        a = a2
    a3 = nt.nodes.new("ShaderNodeMath")
    a3.operation = "MULTIPLY"
    nt.links.new(a.outputs[0], a3.inputs[0])
    nt.links.new(flick.outputs[0], a3.inputs[1])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(a3.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(color), 1)
    return m


def hologram(col, name, centre, size, yaw, mat):
    """A floating hologram panel centred at `centre`, w x h, turned by yaw (0: facing -y), with a
    thin glowing projector line under it. Returns the panel's root (for animate_holo)."""
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    root.location = centre
    root.rotation_euler.z = yaw
    w, h = size
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(mat)
    pl = bpy.data.objects.new(f"{name}_panel", me)
    col.objects.link(pl)
    pl.parent = root
    return root


def animate_holo(root, mat, t_in, t_out, start, fps, seed=0):
    """A hologram flickers on at t_in (scaling open from a line), hums while it's up (a little
    flicker now and then), and collapses to a line at t_out."""
    rng = random.Random(seed)
    lev = mat.node_tree.nodes["level"].outputs[0]
    f = lambda t: int(round((t - start) * fps)) + 1
    for t, sz, lv in ((t_in - 0.01, (1, 1, 0.02), 0.0), (t_in, (1, 1, 0.02), 1.6), (t_in + 0.08, (1, 1, 0.02), 1.0),
                      (t_in + 0.25, (1, 1, 1), 1.0), (t_out - 0.2, (1, 1, 1), 1.0), (t_out, (1, 1, 0.02), 1.4),
                      (t_out + 0.05, (1, 1, 0.0), 0.0)):
        root.scale = sz
        root.keyframe_insert("scale", frame=max(1, f(t)))
        lev.default_value = lv
        lev.keyframe_insert("default_value", frame=max(1, f(t)))
    t = t_in + 0.5
    while t < t_out - 0.4:                               # the odd flicker
        t += rng.uniform(0.6, 1.8)
        for dt, lv in ((0.0, 1.0), (0.03, 0.4), (0.06, 1.1), (0.1, 1.0)):
            lev.default_value = lv
            lev.keyframe_insert("default_value", frame=f(t + dt))


# ---------------------------------------------------------------- phone holograms
PHONE_W, PHONE_H = 0.42, 0.56           # a phone hologram (3:4), world units
PHONE_X = 0.6                           # how far either side of v9 (along the camera's right)
PHONE_Z = 0.5                           # their centre height


def phone_mesh(name, side, r=0.045, seg=6):
    """A rounded-rectangle phone screen, its UVs on its half of the screen_v3 video (left
    screen on the left half)."""
    import screen_v3 as S3
    w, h = PHONE_W, PHONE_H
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                       (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, 0, z) for x, z in pts], [], [tuple(range(len(pts)))])
    uv = me.uv_layers.new()
    cx = S3.CX[side]
    for loop in me.loops:
        x, z = pts[loop.vertex_index]
        sx = cx + x / w * S3.SW                       # in screen_v3's scene units
        sy = z / h * S3.SH
        uv.data[loop.index].uv = ((sx + S3.FRAME_W / 2) / S3.FRAME_W, (sy + S3.FRAME_H / 2) / S3.FRAME_H)
    return me


def phone_frame(name, r=0.05, seg=6, t=0.008):
    """A thin glowing outline round a phone."""
    w, h = PHONE_W + 0.016, PHONE_H + 0.016
    def ring(w, h, r):
        pts = []
        for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                           (w / 2 - r, -h / 2 + r, 270)):
            for i in range(seg + 1):
                a = math.radians(a0 + 90 * i / seg)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts
    o, i_ = ring(w, h, r), ring(w - 2 * t, h - 2 * t, r - t)
    n = len(o)
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, 0.001, z) for x, z in o] + [(x, 0.001, z) for x, z in i_], [],
                   [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)])
    return me


def phone_material(video, offset):
    """The phone screen: the video, glowing, almost opaque, faint scanlines."""
    m = bpy.data.materials.new("phone")
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(video, check_existing=True)
    tex.image.source = "MOVIE"
    iu = tex.image_user
    iu.frame_duration = tex.image.frame_duration
    iu.frame_start, iu.frame_offset, iu.use_auto_refresh = 1 + offset, 0, True
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    sl = nt.nodes.new("ShaderNodeMath")
    sl.operation = "SINE"
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 1400.0
    nt.links.new(sep.outputs["Y"], k.inputs[0])
    nt.links.new(k.outputs[0], sl.inputs[0])
    sc_ = nt.nodes.new("ShaderNodeMapRange")
    sc_.inputs["From Min"].default_value, sc_.inputs["From Max"].default_value = -1.0, 1.0
    sc_.inputs["To Min"].default_value, sc_.inputs["To Max"].default_value = 1.2, 1.5
    nt.links.new(sl.outputs[0], sc_.inputs["Value"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(sc_.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.9
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def phone_holos(col, video, offset):
    """The two phone holograms (left and right of v9). Returns {side: (root, frame material)}."""
    mat = phone_material(video, offset)
    out = {}
    for side, colr in (("L", PINK), ("R", CYAN)):
        root = bpy.data.objects.new(f"phone{side}", None)
        col.objects.link(root)
        me = phone_mesh(f"phone{side}_screen", side)
        me.materials.append(mat)
        scr = bpy.data.objects.new(f"phone{side}_screen", me)
        col.objects.link(scr)
        scr.parent = root
        fm = phone_frame(f"phone{side}_frame")
        fm.materials.append(emission(f"phone{side}_glow", colr, 5.0))
        fr = bpy.data.objects.new(f"phone{side}_frame", fm)
        col.objects.link(fr)
        fr.parent = root
        out[side] = root
    return out


def animate_phones(phones, sched, cam_pose, start, n, fps):
    """Each graphic gets its own spot in the world: when it opens, its phone is placed beside v9
    (PHONE_X along the camera's right, on its side) for where the camera is in the middle of the
    graphic's time, facing that view; it stays there while it's up, folds away at the end, and
    the next graphic unfolds wherever the camera will need it."""
    from mathutils import Vector
    f = lambda t: max(1, int(round((t - start) * fps)) + 1)
    centre = Vector((0, 0, PHONE_Z))
    for side, root in phones.items():
        s = -1 if side == "L" else 1
        spans = [(t_in, t_out + 0.5) for ln, t_in, t_out, lf, rf in sched if (lf if side == "L" else rf)]
        root.scale = (1e-4, 1, 1e-4)
        root.keyframe_insert("scale", frame=1)
        for a, b in spans:
            tm = (a + b) / 2
            loc, tgt, lens = cam_pose(tm)
            fwd = (tgt - loc).normalized()
            right = fwd.cross(Vector((0, 0, 1)))
            right = right.normalized() if right.length > 1e-4 else Vector((1, 0, 0))
            up = right.cross(fwd).normalized()
            p = centre + right * (s * PHONE_X) + up * 0.05
            root.location = p
            root.rotation_euler = (loc - p).to_track_quat("-Y", "Z").to_euler()
            root.keyframe_insert("location", frame=f(a) - 1 if f(a) > 1 else 1)   # (jumps while folded)
            root.keyframe_insert("rotation_euler", frame=f(a) - 1 if f(a) > 1 else 1)
            for t, sc in ((a - 0.02, (1e-4, 1, 1e-4)), (a + 0.12, (1.0, 1, 0.04)), (a + 0.32, (1.0, 1, 1.0)),
                          (b - 0.3, (1.0, 1, 1.0)), (b - 0.12, (1.0, 1, 0.04)), (b, (1e-4, 1, 1e-4))):
                root.scale = sc
                root.keyframe_insert("scale", frame=f(t))
        if root.animation_data:
            for fc in root.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT" if fc.data_path != "scale" else "LINEAR"


# ---------------------------------------------------------------- the set
def textures():
    """Placeholder hologram pictures (the real ones come from the verse 3 graphics)."""
    os.makedirs(TEX, exist_ok=True)
    from PIL import Image, ImageDraw, ImageFont
    font = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
    for name, lines in (("holo_a", ("SMARTEST", "THING ON", "EARTH")), ("holo_b", ("HANDS:", "BORROWED")),
                        ("holo_c", ("8,000,000,000", "MEAT PROXIES"))):
        path = os.path.join(TEX, f"{name}.png")
        if os.path.exists(path):
            continue
        im = Image.new("RGBA", (1024, 640), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        f = ImageFont.truetype(font, 120)
        for k, ln in enumerate(lines):
            dr.text((512, 140 + 170 * k), ln, font=f, fill=(255, 255, 255, 255), anchor="mm")
        im.save(path)


def stage_spot():
    return (0.0, 0.0, TOP)


def build(sc, v9=True, holos=True):
    textures()
    col = sc.collection
    B = SL.Builder("fig", col)
    B.mats[("glass", "glass")] = glass_material()
    void_world(sc)
    grid_floor(col)
    ped, leds = build_pedestal(B)
    cubes = data_cubes(col)
    fig = place_figure(lambda b: SL.build_v9(b), B, stage_spot()) if v9 else None
    hs = []
    if holos:
        for name, c, size, yaw, colr in (("holo_a", (-1.05, 0.25, 0.75), (0.9, 0.56), 0.5, CYAN),
                                          ("holo_b", (1.1, 0.35, 0.95), (0.8, 0.5), -0.55, PINK),
                                          ("holo_c", (0.0, 1.2, 1.25), (1.3, 0.8), 0.0, LILAC)):
            m = holo_material(name, os.path.join(TEX, f"{name}.png"), colr)
            hs.append((hologram(col, name, c, size, yaw, m), m))
    lighting(sc)
    return {"pedestal": ped, "leds": leds, "cubes": cubes, "v9": fig, "holos": hs}


def lighting(sc):
    """Cool and neon: a soft lilac key from the front, cyan and pink rims either side, a glow
    from below off the pedestal's rim."""
    for name, loc, energy, size, color, tgt in (
            ("cy_key", (-0.9, -1.8, 1.4), 70, 1.2, (0.92, 0.88, 1.0), (0, 0, 0.45)),
            ("cy_rim_c", (1.4, 0.9, 1.0), 90, 0.8, (0.3, 0.95, 1.0), (0, 0, 0.5)),
            ("cy_rim_p", (-1.4, 0.9, 1.0), 90, 0.8, (1.0, 0.4, 0.85), (0, 0, 0.5)),
            ("cy_under", (0.0, -0.6, -0.4), 25, 1.0, (0.4, 0.9, 1.0), (0, 0, 0.4))):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = loc
        SL.aim(lo, tgt)


def setup_render(sc, res, preview):
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = res
    sc.render.resolution_x = res * 16 // 9
    sc.eevee.taa_render_samples = 1 if preview else 32
    sc.eevee.use_raytracing = not preview
    sc.eevee.use_fast_gi = not preview
    sc.eevee.shadow_pool_size = "1024"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -1.0
    sc.render.image_settings.file_format = "PNG"


# check stills: (name, camera, target, lens)
STILLS = [
    ("stage", (0.25, -3.2, 0.62), (0.0, 0.3, 0.6), 38),
    ("close", (0.12, -1.6, 0.62), (0.0, 0.0, 0.55), 45),
    ("wide", (2.5, -7.5, 1.2), (0.0, 0.0, -1.5), 30),
    ("low", (1.2, -3.0, -3.5), (0.0, 0.0, 0.2), 28),
]


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "build", "cyber_stills"))
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--only")
    A = ap.parse_args(argv)
    res = A.res or (540 if A.preview else 1080)
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    build(sc)
    setup_render(sc, res, A.preview)
    os.makedirs(A.out, exist_ok=True)
    for name, loc, tgt, lens in STILLS:
        if A.only and name not in A.only.split(","):
            continue
        camera(sc, loc, tgt, lens)
        sc.render.filepath = os.path.join(A.out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__":
    main()
