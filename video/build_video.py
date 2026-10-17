"""Build and render the lyric video in Blender.

Run headless:
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --format json > video/build/lyrics.json
  blender -b --factory-startup --python video/build_video.py -- \
      --json video/build/lyrics.json --start 39.4 --end 66.6 --out video/build/frames

Times are seconds into the song's WAV (as exported by rpp_lyrics.py). Frame 1
is --start. Rendered frames are PNGs; mux them with the audio using ffmpeg
(see video/render_clip.sh).
"""
import argparse
import json
import math
import random
import sys

import bpy

FONTS = {
    "lyric": "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf",
    "label": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "head": "/usr/share/fonts/opentype/bebas-neue/BebasNeue-Regular.otf",
    "mono": "/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-SemiBold.ttf",
}

# palette (linear RGB)
NAVY = (0.006, 0.010, 0.030)
GRID = (0.10, 0.18, 0.45)
DIM = (0.30, 0.34, 0.48)
WHITE = (0.95, 0.95, 0.97)
ACCENT = (1.00, 0.30, 0.06)
KEVIN = (0.25, 0.45, 1.00)

W, H = 16.0, 9.0  # visible area in scene units (orthographic camera)


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--blur-steps", type=int, default=8)
    ap.add_argument("--shutter", type=float, default=1.0,
                    help="shutter in frames: 1.0 = 360 degrees (sports-broadcast look), 0.5 = 180 (film)")
    ap.add_argument("--res", type=int, default=1080,
                    help="output height in pixels, 16:9 (e.g. 1080, 1440, 2160)")
    ap.add_argument("--percent", type=int, default=100, help="resolution percentage (for previews)")
    ap.add_argument("--no-glow", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="build the scene only (and save --blend)")
    ap.add_argument("--blend", help="save the built scene to this .blend file")
    ap.add_argument("--stills", help="render only these times (seconds, comma separated) as PNGs")
    return ap.parse_args(argv)


A = args()
DATA = json.load(open(A.json))
FPS = A.fps


def F(t):
    """Frame number for a time in seconds."""
    return (t - A.start) * FPS + 1


# ---------------------------------------------------------------- helpers

def emission_material(name, color, strength=1.0, alpha=1.0, moving=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    # Blended surfaces fade smoothly but write no motion vectors, so fast movers would show
    # as stacked copies instead of a smooth smear. Dithered ones blur properly.
    m.surface_render_method = "DITHERED" if moving else "BLENDED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    mix.inputs["Fac"].default_value = alpha
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m, em, mix


def key(target, path, t, value, index=-1):
    setattr_path(target, path, value)
    target.keyframe_insert(path, frame=F(t), index=index)


def setattr_path(target, path, value):
    if path == "default_value":
        target.default_value = value
    else:
        setattr(target, path, value)


def key_color(em, t, color, strength):
    key(em.inputs["Color"], "default_value", t, (*color, 1))
    key(em.inputs["Strength"], "default_value", t, strength)


def key_alpha(mix, t, a):
    key(mix.inputs["Fac"], "default_value", t, a)


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def text(body, font, size, x=0.0, z=0.0, depth=0.0, align="CENTER", mat=None, name="text"):
    cu = bpy.data.curves.new(name, type="FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(FONTS[font], check_existing=True)
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    ob = link(bpy.data.objects.new(name, cu))
    ob.rotation_euler = (math.pi / 2, 0, 0)  # face the camera (looking along +Y)
    ob.location = (x, depth, z)
    if mat:
        cu.materials.append(mat)
    return ob


def quad(name, x0, z0, x1, z1, depth, mat):
    """Flat rectangle in the XZ plane facing the camera; origin at (0, 0)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)], [], [(0, 1, 2, 3)])
    ob = link(bpy.data.objects.new(name, me))
    ob.location.y = depth
    me.materials.append(mat)
    return ob


def ease_all(ob_or_tree):
    ad = getattr(ob_or_tree, "animation_data", None)
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        for kp in fc.keyframe_points:
            if kp.interpolation != "CONSTANT":
                kp.interpolation = "BEZIER"
                kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"


# ---------------------------------------------------------------- scene

def setup_scene():
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    height = A.res
    sc.render.resolution_x, sc.render.resolution_y = height * 16 // 9, height
    sc.render.resolution_percentage = A.percent
    px_scale = height * A.percent / 100 / 1080  # pixel-based settings were tuned at 1080p
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = int(math.ceil((A.end - A.start) * FPS))
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = A.shutter
    sc.eevee.motion_blur_steps = A.blur_steps
    # px; the 32 px default turns fast moves into stacked copies. Scales with resolution.
    sc.eevee.motion_blur_max = int(160 * px_scale)
    sc.eevee.taa_render_samples = A.samples
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = A.out.rstrip("/") + "/f_####"
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (*NAVY, 1)

    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = W
    co = link(bpy.data.objects.new("cam", cam))
    co.location = (0, -30, 0)
    co.rotation_euler = (math.pi / 2, 0, 0)
    sc.camera = co

    if not A.no_glow:
        sc.use_nodes = True
        nt = sc.node_tree
        nt.nodes.clear()
        rl = nt.nodes.new("CompositorNodeRLayers")
        gl = nt.nodes.new("CompositorNodeGlare")
        gl.glare_type = "FOG_GLOW"
        gl.quality = "HIGH"
        gl.threshold = 0.6
        gl.size = max(6, min(9, 8 + round(math.log2(px_scale))))  # glow radius is 2^size px
        gl.mix = -0.55
        co_ = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
        nt.links.new(gl.outputs["Image"], co_.inputs["Image"])
    return sc, cam


def in_clip(t, pad=1.0):
    return A.start - pad <= t <= A.end + pad


# ---------------------------------------------------------------- background

def build_background(cam):
    beats = [b for b in DATA["beats"] if in_clip(b["t"])]
    bars = [b for b in DATA["bars"] if in_clip(b["t"])]

    # slide grid that pulses on beats
    gm, gem, _ = emission_material("grid", GRID, 0.35)
    for i in range(-8, 9):
        quad(f"gv{i}", i - 0.006, -H / 2, i + 0.006, H / 2, 20, gm)
    for j in range(-4, 5):
        quad(f"gh{j}", -W / 2, j - 0.006, W / 2, j + 0.006, 20, gm)
    for b in beats:
        down = b["beat"] == 1
        key_color(gem, b["t"] - 0.02, GRID, 0.35)
        key_color(gem, b["t"], GRID, 1.6 if down else 0.9)
        key_color(gem, b["t"] + 0.28, GRID, 0.35)

    # header bar
    hm, _, _ = emission_material("header", WHITE, 0.9)
    am, aem, _ = emission_material("accentbar", ACCENT, 1.2)
    text("Q3 STRATEGY  —  AI RISK", "head", 0.62, -7.4, 3.95, 0, "LEFT", hm, "header")
    quad("accent", -7.4, 3.52, -3.6, 3.57, 1, am)
    sm, _, _ = emission_material("slidenum", DIM, 1.0)
    for i, b in enumerate(bars):
        nxt = bars[i + 1]["t"] if i + 1 < len(bars) else A.end + 5
        ob = text(f"SLIDE {b['bar']:02d} / ∞", "mono", 0.28, 7.4, 3.95, 0, "RIGHT", sm, f"slide{b['bar']}")
        ob.hide_render = True
        ob.keyframe_insert("hide_render", frame=F(A.start - 5))
        ob.hide_render = False
        ob.keyframe_insert("hide_render", frame=F(b["t"]))
        ob.hide_render = True
        ob.keyframe_insert("hide_render", frame=F(nxt))

    # bar chart that jumps on the beat
    rnd = random.Random(7)
    cm, cem, _ = emission_material("chart", ACCENT, 0.9, moving=True)
    base_z, x0 = -4.05, 4.2
    for k in range(10):
        ob = quad(f"bar{k}", -0.13, 0, 0.13, 1, 2, cm)
        ob.location.x, ob.location.z = x0 + k * 0.34, base_z
        for b in beats:
            h = rnd.uniform(0.15, 1.0) * (1.4 if b["beat"] == 1 else 1.0)
            ob.scale = (1, 1, 0.08)
            ob.keyframe_insert("scale", frame=F(b["t"] - 0.03))
            ob.scale = (1, 1, h * 1.15)
            ob.keyframe_insert("scale", frame=F(b["t"] + 0.05))
            ob.scale = (1, 1, h)
            ob.keyframe_insert("scale", frame=F(b["t"] + 0.2))
        ease_all(ob)
    text("HEADCOUNT EFFICIENCY", "mono", 0.18, x0 - 0.13, base_z - 0.22, 2, "LEFT", sm, "chartlabel")

    # Kevin org chart: boxes multiply on every bar, flash on "Kevin"
    km, kem, _ = emission_material("kevin", KEVIN, 0.55, 0.55)
    cols = 8
    row_z = [2.9, 2.05, 1.2, -1.95, -2.8, -3.65]  # rows keep clear of the lyric band (z -1.4 .. 0.7)
    slots = [(c, r) for r in range(len(row_z)) for c in range(cols)]
    rnd.shuffle(slots)
    counts = [1, 2, 3, 5, 8, 13, 21, 34, 48]
    shown = 0
    # dark strip behind the lyrics so they stay readable over the org chart
    bm, _, _ = emission_material("lyricband", NAVY, 1.0, 0.82)
    quad("lyricband", -W, -1.42, W, 0.72, 5, bm)
    for i, b in enumerate(bars):
        target = counts[min(i, len(counts) - 1)]
        for s in range(shown, min(target, len(slots))):
            c, r = slots[s]
            x = -6.6 + c * (13.2 / (cols - 1))
            z = row_z[r]
            t0 = b["t"] + (s - shown) * 0.02
            box = quad(f"kbox{s}", -0.72, -0.3, 0.72, 0.3, 10, km)
            inner = quad(f"kin{s}", -0.68, -0.26, 0.68, 0.26, 9.9, bpy.data.materials["grid"])
            lab = text("KEVIN", "label", 0.22, 0, 0, 9.8, "CENTER", km, f"klab{s}")
            for ob, dz in ((box, 0), (inner, 0), (lab, 0)):
                ob.location.x, ob.location.z = x, z + dz
                ob.scale = (0.001, 0.001, 0.001)
                ob.keyframe_insert("scale", frame=F(t0 - 0.01))
                ob.location.z = z + 0.9
                ob.keyframe_insert("location", frame=F(t0 - 0.01))
                ob.scale = (1.08, 1.08, 1.08)
                ob.keyframe_insert("scale", frame=F(t0 + 0.09))
                ob.location.z = z
                ob.keyframe_insert("location", frame=F(t0 + 0.09))
                ob.scale = (1, 1, 1)
                ob.keyframe_insert("scale", frame=F(t0 + 0.25))
                ease_all(ob)
        shown = max(shown, min(target, len(slots)))

    # camera punch-in on every bar line
    co = bpy.context.scene.camera
    for b in bars:
        key(cam, "ortho_scale", b["t"] - 0.01, W)
        key(cam, "ortho_scale", b["t"] + 0.06, W * 0.965)
        key(cam, "ortho_scale", b["t"] + 0.6, W)
    ease_all(cam)
    return kem


# ---------------------------------------------------------------- lyrics

def norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def build_lyrics(kevin_em):
    lines = [l for l in DATA["lines"] if l["end"] > A.start - 1 and l["start"] < A.end + 1]
    all_lines = DATA["lines"]
    size, max_w, gap = 0.62, 13.6, 0.2
    for li, line in enumerate(lines):
        gi = all_lines.index(line)
        nxt = all_lines[gi + 1]["start"] if gi + 1 < len(all_lines) else line["end"] + 1
        t_in = line["start"] - 0.35
        t_out = min(nxt - 0.12, line["end"] + 0.8)

        objs = []
        for wi, w in enumerate(line["words"]):
            m, em, mix = emission_material(f"w{gi}_{wi}", DIM, 1.0, 0.0, moving=True)
            ob = text(w["text"], "lyric", size, 0, 0, 0, "CENTER", m, f"w{gi}_{wi}")
            objs.append((ob, em, mix, w))
        bpy.context.view_layer.update()

        # lay out: wrap into rows no wider than max_w, centered
        rows, row, row_w = [], [], 0.0
        for item in objs:
            wdt = item[0].dimensions.x
            if row and row_w + gap + wdt > max_w:
                rows.append((row, row_w))
                row, row_w = [], 0.0
            row_w += (gap if row else 0) + wdt
            row.append((item, wdt))
        rows.append((row, row_w))
        lead = size * 1.3
        z_top = -0.35 + (len(rows) - 1) * lead / 2
        for ri, (row, row_w) in enumerate(rows):
            x = -row_w / 2
            for (ob, em, mix, w), wdt in row:
                ob.location.x = x + wdt / 2
                ob.location.z = z_top - ri * lead
                x += wdt + gap

        for ob, em, mix, w in objs:
            x, z = ob.location.x, ob.location.z
            ts, te = w["start"], w["end"]
            # line enters from below, dimmed
            key_alpha(mix, t_in - 0.01, 0.0)
            key_alpha(mix, t_in + 0.25, 0.45)
            ob.location.z = z - 0.7
            ob.keyframe_insert("location", frame=F(t_in))
            ob.location.z = z
            ob.keyframe_insert("location", frame=F(t_in + 0.22))
            # word lights up and pops when sung
            key_color(em, ts - 0.04, DIM, 1.0)
            key_alpha(mix, ts - 0.04, 0.45)
            key_color(em, ts, ACCENT, 2.2)
            key_alpha(mix, ts, 1.0)
            key_color(em, min(ts + 0.3, max(te, ts + 0.15)), WHITE, 1.0)
            ob.scale = (0.86, 0.86, 0.86)
            ob.keyframe_insert("scale", frame=F(ts - 0.03))
            ob.scale = (1.14, 1.14, 1.14)
            ob.keyframe_insert("scale", frame=F(ts + 0.05))
            ob.scale = (1, 1, 1)
            ob.keyframe_insert("scale", frame=F(ts + 0.22))
            # line leaves fast (upwards and slightly left) so it smears with motion blur
            key_alpha(mix, t_out, 1.0)
            key_alpha(mix, t_out + 0.16, 0.0)
            ob.keyframe_insert("location", frame=F(t_out))
            ob.location = (x - 0.6, 0, z + 3.2)
            ob.keyframe_insert("location", frame=F(t_out + 0.16))
            ob.location = (x, 0, z)
            ease_all(ob)
            ease_all(em.id_data)
            if "kevin" in norm(w["text"]):
                key_color(kevin_em, ts - 0.02, KEVIN, 0.55)
                key_color(kevin_em, ts + 0.02, (0.7, 0.85, 1.0), 3.0)
                key_color(kevin_em, ts + 0.7, KEVIN, 0.55)


# ---------------------------------------------------------------- main

sc, cam = setup_scene()
kevin_em = build_background(cam)
build_lyrics(kevin_em)
ease_all(kevin_em.id_data)
ease_all(bpy.data.materials["grid"].node_tree)
print(f"BUILD frames 1-{sc.frame_end} ({A.start:.2f}-{A.end:.2f}s), objects {len(bpy.data.objects)}")
if A.blend:
    bpy.ops.wm.save_as_mainfile(filepath=A.blend)
if A.stills:
    for t in [float(x) for x in A.stills.split(",")]:
        f = F(t)
        sc.frame_set(int(f), subframe=f - int(f))
        sc.render.filepath = f"{A.out.rstrip('/')}/still_{t:07.3f}.png"
        bpy.ops.render.render(write_still=True)
        print(f"STILL {t:.3f}s -> {sc.render.filepath}")
elif not A.no_render:
    bpy.ops.render.render(animation=True)
    print("RENDER done")
