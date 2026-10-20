"""Lip-sync demo: the Manager singing, mouth shapes driven by tools/lipsync.py.

  python3 tools/lipsync.py video/build/lyrics.json assets/audio/stems/we_need_a_meat_proxy_vocals.wav \
      --start 9.6 --end 18.8 > video/build/visemes.json
  blender -b --factory-startup --python video/lipsync_demo.py -- \
      --visemes video/build/visemes.json --out video/build/lipsync_frames

Mouths are printed decals on the face (one set per viseme), swapped frame by frame like
replacement faces on toy figures. The head also blinks and nods a little with the singing.
The pieces are importable (video/dance_demo.py reuses them).
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402  (cast builders)

TAU = 2 * math.pi
DARK, TEETH, TONGUE, LIP = "#3b1d1d", "#fafafa", "#d9657a", "#e3a98a"


# Mouth shapes: (half width, opening above the mouth line, opening below it, corner lift, upper
# teeth, tongue, lower teeth). Every shape is drawn from the same outline, so the corners stay in
# place and keep the character's smile while the mouth opens, widens and rounds. Like a printed
# toy-figure mouth, the open smiles are "D" shapes: a nearly flat top edge with a straight strip
# of teeth along it, and the smile carried by the rounded bottom edge. OH and OO stay round.
SHAPES = {
    "FV": (0.021, 0.005, 0.0035, 0.3, 0.0055, 0.0, 0.0),     # upper teeth resting on the lower lip
    "EE": (0.032, 0.004, 0.011, 1.0, 0.0045, 0.0, 0.0),    # wide, toothy
    "EH": (0.029, 0.006, 0.014, 0.7, 0.004, 0.005, 0.0),
    "AH": (0.028, 0.008, 0.025, 0.45, 0.0045, 0.009, 0.0),  # jaw dropped
    "OH": (0.017, 0.011, 0.017, 0.0, 0.003, 0.006, 0.0),    # round
    "OO": (0.0095, 0.0075, 0.0085, 0.0, 0.0, 0.0, 0.0),     # small and pursed
}


def stroke(B, name, pts, r, cyl, col="eye", off=0.0016, taper=0.45):
    """A flat printed line through pts (smoothly curved), r thick at the middle and tapering to
    taper*r at the ends, like a pen line printed on the face (a tube would look 3D)."""
    n = len(pts)
    path = []
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(0, i - 1)], pts[i], pts[i + 1], pts[min(n - 1, i + 2)]
        for k in range(8):
            t = k / 8
            path.append(tuple(0.5 * (2 * p1[d] + (-p0[d] + p2[d]) * t + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d])
                                     * t * t + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t ** 3) for d in (0, 1)))
    path.append(tuple(pts[-1]))
    top, bot = [], []
    m = len(path)
    for i, (x, z) in enumerate(path):
        xa, za = path[max(0, i - 1)]
        xb, zb = path[min(m - 1, i + 1)]
        dx, dz = xb - xa, zb - za
        ln = math.hypot(dx, dz) or 1.0
        nx, nz = -dz / ln, dx / ln
        f = i / (m - 1)
        w = r * (taper + (1 - taper) * math.sin(math.pi * f) ** 0.5)
        top.append((x + nx * w, z + nz * w))
        bot.append((x - nx * w, z - nz * w))
    return B.decal(name, ("band", top, bot), 0.0, 0.0, 1.0, 1.0, col, cyl, off)


def build_mouths(B, c, cyl, dz=0.0, lips=None, smile=0.016):
    """One printed mouth per viseme, all at the same spot on the face (dz moves them down, e.g.
    to clear the Founder's visor). smile: how far the corners turn up (the Manager's salesy grin).
    With `lips` (a colour) the mouth wears lipstick: coloured lips frame every shape."""
    c = c + dz
    mc = c - 0.03                                   # the mouth line, at the centre
    N = 41

    def band(name, top, bot, col, off):
        return B.decal(name, ("band", top, bot), 0.0, 0.0, 1.0, 1.0, col, cyl, off)

    def curves(w, up, dn, lift, us=(-1.0, 1.0)):
        """Upper and lower edge of the opening, sampled between us[0] and us[1] (-1..1 = corner
        to corner)."""
        top, bot = [], []
        for i in range(N):
            u = us[0] + (us[1] - us[0]) * i / (N - 1)
            base = mc + smile * lift * u * u
            p = math.sqrt(max(0.0, 1 - u * u))
            if lift > 0:   # D shape: a straight top edge with sharp corners, the jaw drops below it
                top.append((w * u, mc + up))
                bot.append((w * u, mc + up - (up + dn) * p ** (1 - 0.35 * lift)))
            else:
                top.append((w * u, base + up * p))
                bot.append((w * u, base - dn * p))
        return top, bot

    def line(name, pts, r):
        return stroke(B, name, pts, r, cyl)

    def hump(x, w):
        return math.sqrt(max(0.0, 1 - (x / w) ** 2))

    def lipstick(name, w, up, dn, lift, thick=1.0):
        """Coloured lips around an opening: a band above the upper edge and a fuller one below."""
        if not lips:
            return []
        W = w + 0.004
        top, bot = curves(W, up + 0.001, dn + 0.001, lift)
        outer_t = [(x, z + 0.0045 * thick * hump(x, W) + 0.0006) for x, z in top]
        outer_b = [(x, z - 0.006 * thick * hump(x, W) - 0.0006) for x, z in bot]
        return [band(name + "_ulip", outer_t, top, lips, 0.0012), band(name + "_llip", bot, outer_b, lips, 0.0012)]

    def shape(name, w, up, dn, lift, teeth, tongue, lteeth):
        """Each part is a strip between two curves sampled across the mouth, so it follows the
        curve of the head (big flat triangles would sink into it)."""
        top, bot = curves(w, up, dn, lift)
        objs = []
        if not lips:   # a dark rim: the same shape a little bigger, behind it
            e = 0.0013
            et, eb = curves(w + e, up + e, dn + e, lift)
            objs.append(band(f"m_{name}_edge", et, eb, "eye", 0.0008))
        objs.append(band(f"m_{name}", top, bot, DARK, 0.0011))
        top_z, bot_z = mc + up, mc - dn
        if teeth:      # the top of the opening, cut off straight: a strip of teeth
            level = max(top_z - teeth, bot_z + 0.0025)
            objs.append(band(f"m_{name}_teeth", [(x, zt - 0.0006) for x, zt in top],
                             [(x, min(zt - 0.0006, max(zb, level))) for (x, zt), (_, zb) in zip(top, bot)],
                             TEETH, 0.0016))
        if tongue:     # the bottom of the opening: the tongue
            level = min(bot_z + tongue, top_z - teeth - 0.002)
            objs.append(band(f"m_{name}_tongue", [(x, max(zb, min(zt, level))) for (x, zt), (_, zb) in zip(top, bot)],
                             [(x, zb + 0.0004) for x, zb in bot], TONGUE, 0.0014))
        if name == "OO" and not lips:   # pursed lips ring
            objs.append(B.decal("m_OO_lips", "ellipse", 0.0, mc - 0.0005, w + 0.0055, up + 0.005, LIP, cyl, 0.0006))
        return objs + lipstick(f"m_{name}", w, up, dn, lift)

    if lips:
        rest = lipstick("m_rest", 0.021, 0.0, 0.0, 0.35) + [
            line("m_rest_line", curves(0.019, 0, 0, 0.35)[0][2:-2:4], 0.0012)]
        mbp = lipstick("m_mbp", 0.017, 0.0, 0.0, 0.0, thick=0.55) + [
            line("m_mbp_line", curves(0.016, 0, 0, 0.0)[0][2:-2:4], 0.0016)]
    else:
        rest = [line("m_rest", ((-0.034, c - 0.018), (-0.012, c - 0.034), (0.012, c - 0.034), (0.034, c - 0.018)),
                     0.0038)]
        # lips pressed together: a short, straighter, heavier line with a crease under it
        mbp = [line("m_mbp", ((-0.025, mc + 0.0045), (-0.01, mc - 0.0008), (0.01, mc - 0.0008), (0.025, mc + 0.0045)),
                    0.0046),
               line("m_mbp_crease", ((-0.008, mc - 0.0125), (0.0, mc - 0.0135), (0.008, mc - 0.0125)), 0.0018)]
    out = {"rest": rest, "MBP": mbp}
    for name, spec in SHAPES.items():
        out[name] = shape(name, *spec)
    return out


# Eyelid notches (the Anchor's lids drop one per line): each notch is its own drawing of a
# sleepier eye, squashed shorter at about the same height, with a heavy curved lid line on top
# and the lashes moved down onto it. Notch 0 is the ordinary eye; len(LID_SQUASH)+1 is closed.
LID_SQUASH = [0.72, 0.5, 0.32]   # eye height left open at notches 1, 2, 3


def build_lids(B, c, cyl):
    """One set of sleepy-eye prints per notch (index 0, the ordinary open eyes, is empty)."""
    sets = [[]]
    h0, zc0 = 0.019, c + 0.008
    for k, f in enumerate(LID_SQUASH, 1):
        h = h0 * f
        zc = zc0 + 0.25 * (h0 - h)          # the lid comes down; the eye's centre rises a little
        objs = []
        for s in (-1, 1):
            x = 0.036 * s
            objs.append(B.decal(f"seye{k}_{s}", "ellipse", x, zc, 0.0135, h, "eye", cyl, 0.0008))
            if k == 1:
                objs.append(B.decal(f"sglint{k}_{s}", "ellipse", x - 0.004 * s, zc + 0.35 * h, 0.004, 0.0035,
                                    "white", cyl, 0.0015))
            # the heavy lid: an arc lying along the top of the eye, a little wider than it
            arc = [(x + 0.0165 * u, zc + h * 0.45 + (h * 0.55 + 0.0012) * (1 - u * u)) for u in
                   (-1, -0.6, -0.25, 0.0, 0.25, 0.6, 1)]
            objs.append(stroke(B, f"slid{k}_{s}", arc, 0.0022, cyl, off=0.0018, taper=0.6))
            objs.append(B.decal(f"slash{k}_{s}", "bar", x + 0.017 * s, zc + h * 0.45 + 0.001, 0.007, 0.0022,
                                "eye", cyl, 0.0016, rot=-0.25 * s))
        sets.append(objs)
    return sets


def key_visible(objs, frame, visible):
    for ob in objs:
        ob.hide_render = not visible
        ob.hide_viewport = not visible
        ob.keyframe_insert("hide_render", frame=frame)
        ob.keyframe_insert("hide_viewport", frame=frame)


# v9's mouth is a voice-assistant waveform: a row of bars that bounce with the singing voice.
# The bars hang from a smile-shaped curve and grow downward, so it always grins; at rest they are
# a smiling row of dots. Each sound
# shapes the row: (half width of the active bars, their tallest half height).
V9_WAVE = {"MBP": (0.05, 0.0), "FV": (0.035, 0.008), "EE": (0.046, 0.011), "EH": (0.04, 0.019),
           "AH": (0.034, 0.025), "OH": (0.022, 0.02), "OO": (0.012, 0.013)}
V9_BARS, V9_BAR_W, V9_BAR_MIN = 11, 0.0034, 0.0038
V9_EYES = ("happy", "round", "heart", "smug")


def v9_face(B, c):
    """v9's screen face: the waveform bars (scaled per frame), eye sets per expression and a
    blink. Returns (bars, eye sets, blink)."""
    mz = c - 0.035
    cap = [(math.cos(a), max(-1.0, min(1.0, 1.6 * math.sin(a)))) for a in (TAU * i / 16 for i in range(16))]
    bars = []
    for i in range(V9_BARS):
        x = -0.05 + 0.1 * i / (V9_BARS - 1)
        ob = B.decal(f"vwave{i}", cap, x, mz, V9_BAR_W, 0.01, SL.V9_INK, SL.V9_SCREEN, 0.001)
        # move the origin to the top of the bar and hang it from the smile curve, so scaling it in
        # z grows it downward
        centre = sum((v.co for v in ob.data.vertices), Vector()) / len(ob.data.vertices)
        top = centre + Vector((0, 0, 0.01))
        for v in ob.data.vertices:
            v.co -= top
        ob.location = (top.x, top.y, v9_smile(c, x))
        bars.append(ob)
    eyes = {k: SL.v9_eyes(B, c, k, name=f"veye_{k}") for k in V9_EYES}
    blink = SL.v9_eyes(B, c, "closed", name="vblink")
    return bars, eyes, blink


def v9_smile(c, x):
    """Height of the smile curve the waveform bars hang from (corners turned up)."""
    return c - 0.022 + 6.0 * x * x


def animate_wave(bars, frames):
    """v9's mouth per frame: each bar's length set by the sound's shape, the voice's loudness and
    a lively wobble (rising fast, falling a little slower); at rest, a smiling row of dots."""
    h = [V9_BAR_MIN] * len(bars)
    for i, fr in enumerate(frames):
        v = fr["v"]
        singing = v != "rest" and v in V9_WAVE
        w, top = V9_WAVE.get(v, (0.05, 0.0))
        loud = 0.55 + 0.6 * min(1.0, fr.get("level", 0.5))
        for j, ob in enumerate(bars):
            x = -0.05 + 0.1 * j / (len(bars) - 1)
            env = math.sqrt(max(0.0, 1 - (x / (w + 0.004)) ** 2)) if singing else 0.0
            wob = 0.6 + 0.4 * abs(math.sin(j * 2.7 + i * 0.37 + math.sin(i * 0.11 + j)))
            target = max(V9_BAR_MIN, top * env * wob * loud)
            h[j] += (target - h[j]) * (0.7 if target > h[j] else 0.35)
            ob.scale = (1.0, 1.0, 1.7 * h[j] / 0.02)    # bar length 1.7 x the half height
            ob.keyframe_insert("scale", frame=i + 1)


def singing_figure(B, sc, who="manager"):
    """Build a figure with swappable mouths: the Manager, the Founder (the Manager ten years
    later: visor instead of eyes, phone in his left hand) or the Anchor (cue cards in her left
    hand, lipstick, droppable eyelids in B.lids). Returns (top, head pivot, mouths, eyes, blink);
    eyes and blink are empty for the Founder."""
    B.lids, B.eyesets, B.wave = [], {}, []
    if who == "v9":
        SL.build_v9(B, face=False)
        top = SL.FIG["z_kid"] + SL.FIG["torso_h"]
        B.wave, B.eyesets, blink = v9_face(B, top + 0.13)
        return _head_pivot(B, sc, top, {}, [], blink)
    {"founder": SL.build_founder, "anchor": SL.build_anchor}.get(who, SL.build_manager)(B, mouth=False)
    top = SL.FIG["z_adult"] + SL.FIG["torso_h"]
    c = top + 0.12
    cyl = ((0, 0, c), (0.1, 0.1, 100.0))
    mouths = build_mouths(B, c, cyl, dz=-0.004 if who == "founder" else 0.0,
                          lips="#c8323c" if who == "anchor" else None,
                          smile=0.006 if who == "anchor" else 0.016)
    eyes_c = c + (SL.ANCHOR_EYES_DZ if who == "anchor" else 0.0)
    B.lids = build_lids(B, eyes_c, cyl) if who == "anchor" else []
    blink = [] if who == "founder" else [
        B.decal(f"blink{s}", "bar", 0.036 * s, eyes_c + 0.007, 0.016, 0.0035, "eye", cyl, 0.0012) for s in (-1, 1)]
    return _head_pivot(B, sc, top, mouths, None, blink)


def _head_pivot(B, sc, top, mouths, eyes, blink):
    """Hang everything above the shoulders off a head pivot. eyes=None: find the printed eyes."""
    # everything above the shoulders hangs off a head pivot, so the head can nod and sway
    bpy.context.view_layer.update()
    head = bpy.data.objects.new("head_pivot", None)
    sc.collection.objects.link(head)
    head.location = (0, 0, top)
    inv = Matrix.Translation((0, 0, top)).inverted()
    for ob in list(sc.collection.objects):
        if ob is head or ob.parent is not None or ob.type not in ("MESH", "CURVE", "FONT"):
            continue
        centre = sum((ob.matrix_world @ Vector(v) for v in ob.bound_box), Vector()) / 8
        if centre.z > top + 0.004:
            ob.parent = head
            ob.matrix_parent_inverse = inv
    if eyes is None:
        eyes = [ob for ob in head.children if ob.name.startswith(("eye", "glint", "lash"))]
    return top, head, mouths, eyes, blink


def singing_manager(B, sc):
    return singing_figure(B, sc, "manager")


def animate_mouths(mouths, frames):
    """Keyframe mouth visibility only where the shape changes."""
    prev = None
    for i, fr in enumerate(frames):
        if fr["v"] != prev:
            for name, objs in mouths.items():
                key_visible(objs, i + 1, name == fr["v"])
            prev = fr["v"]


def animate_faces(eyesets, blink, faces, n, fps, start, default="happy"):
    """Screen eyes (v9): the expression set by faces [(start, end, name)] (default otherwise),
    with a blink (- -) every few seconds."""
    shut, t = [], start + 1.5
    while t < start + n / fps:
        shut.append((t, t + 0.1))
        t += 3.1 + 1.1 * math.sin(t * 5.1) ** 2
    prev = None
    for i in range(n):
        t = start + i / fps
        face = next((name for a, b, name in faces if a <= t < b), default)
        state = "blink" if face == "closed" or any(a <= t < b for a, b in shut) else face   # (closed: - -)
        if state != prev:
            key_visible(blink, i + 1, state == "blink")
            for name, objs in eyesets.items():
                key_visible(objs, i + 1, name == state)
            prev = state


def animate_blinks(eyes, blink, n, fps):
    """Blinks every ~3 s, 6 frames long."""
    key_visible(blink, 1, False)
    key_visible(eyes, 1, True)
    t = 1.2
    while t < n / fps - 0.3:
        f0 = int(t * fps) + 1
        key_visible(eyes, f0, False)
        key_visible(blink, f0, True)
        key_visible(eyes, f0 + 6, True)
        key_visible(blink, f0 + 6, False)
        t += 2.6 + 0.9 * math.sin(t * 7.3) ** 2


def animate_lids(eyes, blink, lids, notches, n, fps, start):
    """Eyelids that drop a notch at set times, with sleepy blinks. notches: [(time, notch)], notch
    0 (open) .. len(lids)-1, or len(lids) for closed. Each drop happens inside a slow blink; the
    ordinary blinks get slower as the lids get heavier."""
    closed = len(lids)

    def notch(t):
        return max([k for a, k in notches if a <= t] or [0])

    shut = []                                    # (start, end) of every blink, in song time
    for a, k in notches:
        if 0 < k < closed:
            shut.append((a - 0.12, a + 0.16 + 0.04 * k))
    t = start + 1.2
    while t < start + n / fps - 0.3:
        k = notch(t)
        if not any(a - 0.6 < t < b + 0.6 for a, b in shut):
            shut.append((t, t + (6 + 3 * k) / fps))
        t += 2.6 + 0.9 * math.sin(t * 7.3) ** 2 + 0.6 * k
    prev = None
    for i in range(n):
        t = start + i / fps
        k = notch(t)
        state = closed if k >= closed or any(a <= t < b for a, b in shut) else k
        if state != prev:
            key_visible(eyes, i + 1, state == 0)
            key_visible(blink, i + 1, state == closed)
            for j, objs in enumerate(lids):
                key_visible(objs, i + 1, j == state)
            prev = state


def animate_head(head, frames, fps, extra=None):
    """A small nod with the singing level and a slow sway; `extra(t)` adds (rx, ry, rz) on top."""
    level = 0.0
    for i, fr in enumerate(frames):
        level += (fr["level"] - level) * 0.25
        if i % 2:
            continue
        tt = i / fps
        r = [0.07 * level, 0.025 * math.sin(2 * math.pi * tt / 5.3), 0.04 * math.sin(2 * math.pi * tt / 3.7)]
        if extra:
            r = [a + b for a, b in zip(r, extra(fr["t"]))]
        head.rotation_euler = r
        head.keyframe_insert("rotation_euler", frame=i + 1)


def setup_look(sc, fps, n, res=1080, samples=16, blur_steps=4, shutter=1.0, preview=False, on_set=None):
    """Same materials, lights and grading as the cast lineup. preview: as fast as possible (no
    motion blur, one sample, cheaper shadows, no ray tracing). on_set: (x, y, z) of the performer
    inside a built set, which has its own world and floor: only the key, fill and rim lights are
    added, around that spot and dimmer."""
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = res
    sc.render.resolution_x = res * 16 // 9
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, n
    sc.eevee.taa_render_samples = samples
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = shutter
    sc.eevee.motion_blur_steps = blur_steps
    sc.eevee.motion_blur_max = int(160 * res / 1080)
    if not preview:   # final quality: full-resolution ray tracing, smoother soft shadows (less grain)
        rt = sc.eevee.ray_tracing_options
        rt.resolution_scale = "1"
        rt.use_denoise = True
        sc.eevee.shadow_ray_count = 3
        sc.eevee.shadow_step_count = 12
        sc.eevee.fast_gi_ray_count = 4
        sc.eevee.fast_gi_step_count = 12
    if preview:
        sc.render.use_motion_blur = False
        sc.eevee.taa_render_samples = 1
        sc.eevee.use_raytracing = False
        sc.eevee.use_fast_gi = False
        sc.eevee.shadow_resolution_scale = 0.5
        sc.eevee.shadow_ray_count = 1
        sc.eevee.shadow_step_count = 1
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.65 if on_set is None else -1.0   # a stop down: the office's white surfaces bloom
    sc.eevee.shadow_pool_size = "1024"
    ox, oy, oz = on_set or (0, 0, 0)
    if on_set is None:
        sc.world = sc.world or bpy.data.worlds.new("World")
        sc.world.use_nodes = True
        bg = sc.world.node_tree.nodes["Background"]
        bg.inputs[0].default_value = (*SL.srgb(SL.PAL["floor"]), 1)
        bg.inputs[1].default_value = 0.35
        bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.04))
        bpy.context.object.data.materials.append(SL.material("fig", "floor", "floor", "matte"))
    rig = ((("key", (-2.5, -3.2, 3.2), 900, 3.0, (1.0, 0.95, 0.9), (0, 0, 0.5)),
            ("fill", (3.0, -2.8, 1.4), 320, 4.0, (0.75, 0.85, 1.0), (0, 0, 0.5)),
            ("rim", (0.0, 2.2, 2.4), 420, 4.0, (1.0, 0.8, 0.6), (0, 0, 0.6))) if on_set is None else
           # in a set: closer, under the ceiling and in front of the wall behind
           (("key", (-1.0, -1.5, 1.2), 70, 1.2, (1.0, 0.95, 0.9), (0, 0, 0.5)),
            ("fill", (1.3, -1.3, 0.8), 25, 1.5, (0.75, 0.85, 1.0), (0, 0, 0.5)),
            ("rim", (0.3, 0.55, 1.25), 30, 0.8, (1.0, 0.8, 0.6), (0, 0, 0.6))))
    for name, loc, energy, size, color, target in rig:
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = (loc[0] + ox, loc[1] + oy, loc[2] + oz)
        SL.aim(lo, (target[0] + ox, target[1] + oy, target[2] + oz))
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"


def flat_look(sc):
    """A much faster preview for checking framing and timing: the Workbench engine, flat
    colours with simple studio shading, images on the screens (they don't scroll), no lighting."""
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "TEXTURE"
    sh.show_shadows = False
    sh.show_cavity = False
    sc.display.render_aa = "OFF"
    sc.view_settings.view_transform = "Standard"
    for m in bpy.data.materials:   # give every material its colour in the viewport too
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                m.diffuse_color = n.inputs["Base Color"].default_value
                break
            if n.type == "EMISSION":
                c = n.inputs["Color"].default_value
                m.diffuse_color = (min(1, c[0] * 1.5), min(1, c[1] * 1.5), min(1, c[2] * 1.5), 1)
                break


def add_camera(sc, loc, target, lens):
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = lens
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = loc
    SL.aim(cam, target)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


from render_out import splice  # noqa: E402,F401  (kept importable from here)


def render(sc, out, frames, fps, start, stills=None, preview=False, lossless=False, patch=None):
    """Render frames as PNGs into the folder `out` (or stills). In preview mode the animation is
    written straight to a silent H.264 video, `out` + ".mp4", instead (saving PNGs is slower
    than rendering them)."""
    out = out.rstrip("/")
    if stills:
        for t in [float(v) for v in stills.split(",")]:
            f = int(round((t - start) * fps)) + 1
            sc.frame_set(f)
            sc.render.filepath = f"{out}/still_{t:07.3f}_{frames[f - 1]['v']}.png"
            bpy.ops.render.render(write_still=True)
            print("STILL", t, frames[f - 1]["v"], frames[f - 1]["word"])
    elif lossless:   # one lossless FFV1 video, out + ".mkv" (with alpha, if the background's transparent)
        im = sc.render.image_settings
        im.file_format = "FFMPEG"
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
        im.color_mode = "RGBA" if sc.render.film_transparent else "RGB"     # (after the codec: it sets the choices)
        sc.render.ffmpeg.audio_codec = "NONE"
        sc.render.use_file_extension = False
        import render_out
        render_out.render_movie(sc, out + ".mkv", fps, "%s,%s" % patch if patch else None, start)
    elif preview:
        im = sc.render.image_settings
        im.file_format = "FFMPEG"
        sc.render.ffmpeg.format = "MPEG4"
        sc.render.ffmpeg.codec = "H264"
        sc.render.ffmpeg.constant_rate_factor = "HIGH"
        sc.render.ffmpeg.ffmpeg_preset = "REALTIME"
        sc.render.ffmpeg.audio_codec = "NONE"
        sc.render.filepath = out + ".mp4"
        sc.render.use_file_extension = False
        bpy.ops.render.render(animation=True)
        print("RENDER done", len(frames), "frames ->", sc.render.filepath)
    else:
        sc.render.filepath = f"{out}/f_####"
        bpy.ops.render.render(animation=True)
        print("RENDER done", len(frames), "frames")


def parse_args(extra=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--visemes", required=True)
    ap.add_argument("--out", required=True, help="folder for rendered frames")
    ap.add_argument("--res", type=int, help="frame height in pixels (default 1080, preview 540)")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--flat", action="store_true", help="flat-shaded Workbench preview (fastest)")
    ap.add_argument("--lossless", action="store_true", help="write a lossless FFV1 video (out.mkv) instead of PNGs")
    ap.add_argument("--blur-steps", type=int, default=4)
    ap.add_argument("--shutter", type=float, default=1.0)
    ap.add_argument("--patch", help="START,END song seconds: with --lossless, re-render only these frames and "
                                    "splice them into the existing out.mkv")
    ap.add_argument("--stills", help="render only these frame times (seconds, comma separated)")
    ap.add_argument("--preview", action="store_true",
                    help="fast check render: no motion blur, 1 sample, written straight to OUT.mp4")
    if extra:
        extra(ap)
    a = ap.parse_args(argv)
    if a.res is None:
        a.res = 540 if a.preview else 1080
    return a


def main():
    A = parse_args()
    D = json.load(open(A.visemes))
    fps, start, frames = D["fps"], D["start"], D["frames"]
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    B = SL.Builder("fig", sc.collection)
    top, head, mouths, eyes, blink = singing_manager(B, sc)
    SL.fig_baseplate(B, nx=10, ny=7)
    animate_mouths(mouths, frames)
    animate_blinks(eyes, blink, len(frames), fps)
    animate_head(head, frames, fps)
    setup_look(sc, fps, len(frames), A.res, A.samples, A.blur_steps, A.shutter, A.preview)
    add_camera(sc, (0.38, -1.55, 0.8), (0, 0, 0.6), 70)
    render(sc, A.out, frames, fps, start, A.stills, A.preview)


if __name__ == "__main__":
    main()
