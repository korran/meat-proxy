"""What plays on the big screen in the office: the lyrics, highlighted word by word with expressive
typography, and graphics that go with each line, in the style of the Manager's slide deck.

A flat 2D scene (orthographic camera looking down at the XY plane, flat emissive colours), built
and keyframed from the lyric word timings and the beat table, rendered at 60 fps with motion
blur. Rendered on its own for review (with the song) and later used as the TV's video texture.

  blender -b --factory-startup --python video/screen_graphics.py -- \\
      --lyrics video/build/lyrics.json --music video/build/music.json \\
      --start 0 --end 66.6 --out video/build/screen_v1c1 [--res 540] [--stills 12,30]
  ffmpeg -i video/build/screen_v1c1.mp4 -ss 0 -t 66.6 -i assets/audio/we_need_a_meat_proxy.wav \\
      -map 0:v -map 1:a -c:v copy -c:a aac video/build/screen_v1c1_review.mp4
  Final (for the TV texture): --res 1080 --final --lossless  (writes screen_v1c1.mkv, FFV1)

The screen is 16 x 9 units (x -8..8, y -4.5..4.5). Lyrics sit in the lower part, graphics above.
"""
import argparse
import json
import math
import os
import re
import sys

import bpy
from mathutils import Vector

FPS = 60
W, H = 16.0, 9.0
BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
ITALIC = "/usr/share/fonts/opentype/inter/Inter-ExtraBoldItalic.otf"
MONO = "/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Bold.ttf"
# display faces for the lyrics
BEBAS = "/usr/share/fonts/opentype/bebas-neue/BebasNeue-Bold.otf"            # tall condensed caps
IMPACT = "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf"
GOTHIC = "/usr/share/fonts/opentype/urw-base35/URWGothic-Demi.otf"          # geometric
SERIF_BI = "/usr/share/fonts/opentype/urw-base35/C059-BdIta.otf"            # bold book italic
SERIF_I = "/usr/share/fonts/opentype/urw-base35/P052-Italic.otf"            # elegant italic
SCRIPT = "/usr/share/fonts/opentype/urw-base35/Z003-MediumItalic.otf"       # calligraphic (signatures)
GOTHIC_O = "/usr/share/fonts/opentype/urw-base35/URWGothic-DemiOblique.otf"
CAPS_FONTS = (BEBAS, IMPACT, GOTHIC_O)

NAVY, NAVY2, INK = "#121a3d", "#2a2f66", "#0b1028"
WHITE, DIM, LILAC = "#ffffff", "#4f5a8c", "#9fb3ff"
CORAL, YELLOW, MINT, RED, PAPER = "#ff6a5c", "#ffd166", "#3ddc97", "#ff3b3b", "#f4f1e8"


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def fr(t):
    """Song time -> frame (frame 1 is the clip start)."""
    return round((t - T0) * FPS) + 1


T0 = 0.0
_mats = {}


def flat(color, own=False):
    """A flat (emission) material; own=True gives the object its own copy, so its colour can be
    animated."""
    if not own and color in _mats:
        return _mats[color]
    m = bpy.data.materials.new(f"flat_{color}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*srgb(color), 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    if not own:
        _mats[color] = m
    return m


def key_color(ob, t, color):
    em = ob.data.materials[0].node_tree.nodes["Emission"]
    em.inputs["Color"].default_value = (*srgb(color), 1)
    em.inputs["Color"].keyframe_insert("default_value", frame=fr(t))


# ---------------------------------------------------------------- primitives
COL = None


def link(ob, parent=None):
    COL.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def group(name, x=0.0, y=0.0, parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = (x, y, 0)
    return link(e, parent)


def text(body, size, x, y, color, font=BOLD, align="LEFT", parent=None, own=False, z=0.02, name="txt"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.size = size
    cu.align_x = align
    ob = bpy.data.objects.new(name, cu)
    ob.location = (x, y, z)
    cu.materials.append(flat(color, own))
    return link(ob, parent)


def rect(w, h, x, y, color, r=0.0, parent=None, z=0.0, own=False, name="rect", anchor="center"):
    """A (rounded) rectangle. anchor: 'center' or 'left' (grows rightward when scaled in x)."""
    x0 = -w / 2 if anchor == "center" else 0.0
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x0, -h / 2, 0), (x0 + w, -h / 2, 0), (x0 + w, h / 2, 0), (x0, h / 2, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new(name, me)
    ob.location = (x, y, z)
    me.materials.append(flat(color, own))
    if r > 0:
        b = ob.modifiers.new("round", "BEVEL")
        b.affect, b.width, b.segments = "VERTICES", min(r, w / 2 - 1e-4, h / 2 - 1e-4), 8
    return link(ob, parent)


def circle(rad, x, y, color, parent=None, z=0.0, own=False, name="circle", ring=0.0):
    n = 48
    me = bpy.data.meshes.new(name)
    if ring:
        V = [(rad * math.cos(math.tau * i / n), rad * math.sin(math.tau * i / n), 0) for i in range(n)]
        V += [((rad - ring) * math.cos(math.tau * i / n), (rad - ring) * math.sin(math.tau * i / n), 0) for i in range(n)]
        F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    else:
        V = [(rad * math.cos(math.tau * i / n), rad * math.sin(math.tau * i / n), 0) for i in range(n)]
        F = [tuple(range(n))]
    me.from_pydata(V, [], F)
    ob = bpy.data.objects.new(name, me)
    ob.location = (x, y, z)
    me.materials.append(flat(color, own))
    return link(ob, parent)


def poly(pts, color, parent=None, z=0.0, name="poly", width=0.0):
    """A filled polygon, or (width > 0) a polyline of that thickness."""
    me = bpy.data.meshes.new(name)
    if width:
        V, F = [], []
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            dx, dy = x1 - x0, y1 - y0
            ln = math.hypot(dx, dy) or 1
            nx, ny = -dy / ln * width / 2, dx / ln * width / 2
            k = len(V)
            V += [(x0 + nx, y0 + ny, 0), (x1 + nx, y1 + ny, 0), (x1 - nx, y1 - ny, 0), (x0 - nx, y0 - ny, 0)]
            F.append((k, k + 1, k + 2, k + 3))
    else:
        V, F = [(x, y, 0) for x, y in pts], [tuple(range(len(pts)))]
    me.from_pydata(V, [], F)
    ob = bpy.data.objects.new(name, me)
    ob.location = (0, 0, z)
    me.materials.append(flat(color))
    return link(ob, parent)


_caps = {}


def cap_height(font):
    """Height of a capital letter in this font at size 1 (for stacking rows tightly)."""
    if font not in _caps:
        ob = text("H", 1.0, 0, -50, WHITE, font, name="capprobe")
        bpy.context.view_layer.update()
        _caps[font] = ob.dimensions.y
        bpy.data.objects.remove(ob)
    return _caps[font]


def width_of(ob):
    bpy.context.view_layer.update()
    return ob.dimensions.x


# ---------------------------------------------------------------- animation helpers
def key(ob, t, loc=None, scale=None, rot=None):
    f = fr(t)
    if loc is not None:
        ob.location = (*loc[:2], ob.location.z) if len(loc) == 2 else loc
        ob.keyframe_insert("location", frame=f)
    if scale is not None:
        ob.scale = (scale, scale, 1) if isinstance(scale, (int, float)) else scale
        ob.keyframe_insert("scale", frame=f)
    if rot is not None:
        ob.rotation_euler.z = rot
        ob.keyframe_insert("rotation_euler", index=2, frame=f)


def pop_in(ob, t, dur=0.22, over=1.12, frm=0.0):
    """Scale up from nothing with a little overshoot."""
    key(ob, t - 0.001 if t > T0 else t, scale=frm)
    key(ob, t + dur * 0.65, scale=over)
    key(ob, t + dur, scale=1.0)


def pop_out(ob, t, dur=0.18):
    key(ob, t, scale=1.0)
    key(ob, t + dur, scale=0.0)


def slide(ob, t0, t1, a, b):
    key(ob, t0, loc=a)
    key(ob, t1, loc=b)


def grow_x(ob, t0, t1, a=0.0, b=1.0):
    key(ob, t0, scale=(a, 1, 1))
    key(ob, t1, scale=(b, 1, 1))


def hide_until(ob, t):
    """Kept at zero scale until t (for objects that should simply appear)."""
    key(ob, T0, scale=0.0)
    key(ob, t - 0.001, scale=0.0)


def ease_all():
    """Every keyframe eases in and out; colour changes and appearances snap."""
    for ob in bpy.data.objects:
        ad = ob.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    for m in bpy.data.materials:
        ad = m.node_tree.animation_data if m.node_tree else None
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


# ---------------------------------------------------------------- lyrics
def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


# words with their own typography: font, colour once sung, highlight colour, size factor, pill
EMPHASIS = {
    "okrs": dict(font=GOTHIC, sung=INK, now=INK, k=1.0, pill=YELLOW),
    "june": dict(sung=CORAL, now=YELLOW, k=1.1),
    "tuesday": dict(sung=MINT, now=YELLOW, k=1.1),
    "deck": dict(sung=LILAC, now=YELLOW, k=1.0),
    "safe": dict(font=SERIF_BI, sung=YELLOW, now=YELLOW, k=1.0),
    "check": dict(sung=MINT, now=YELLOW, k=1.1),
    "kevin": dict(font=SCRIPT, sung=CORAL, now=YELLOW, k=1.12),
    "risk": dict(sung=RED, now=YELLOW, k=1.1),
    "ten": dict(sung=MINT, now=YELLOW, k=1.15),
    "dollars": dict(sung=MINT, now=YELLOW, k=1.0),
    "brisk": dict(font=SERIF_BI, sung=LILAC, now=YELLOW, k=1.0),
    "logs": dict(font=MONO, sung=RED, now=YELLOW, k=1.0),
    "bill": dict(sung=MINT, now=YELLOW, k=1.1),
    "merge": dict(font=MONO, sung=LILAC, now=YELLOW, k=1.0),
    "still": dict(font=SERIF_BI, sung=LILAC, now=YELLOW, k=1.0),
    "assets": dict(sung=YELLOW, now=YELLOW, k=1.0),
    "knees": dict(sung=YELLOW, now=YELLOW, k=1.0),
    "forsake": dict(font=SERIF_BI, sung=CORAL, now=YELLOW, k=1.15),
    "loop": dict(font=MONO, sung=LILAC, now=YELLOW, k=1.0),
    "sign": dict(font=SCRIPT, sung=CORAL, now=YELLOW, k=1.25, pill=None),
}


def lyric_line(ln, t_out, rows_y=(-1.45, -2.75), size=0.9, words=None, spoken=False):
    """One lyric line in the lower part of the screen. The words rise in (dim) just before the
    line, each lights up and pops as it is sung, then stays white (or its own colour); the line
    flies up and out at t_out. spoken: italic, and words only appear as they are spoken."""
    words = words if words is not None else ln["words"]
    if not words:
        return
    t_in = words[0]["start"] - 0.35
    line = group("line", 0, 0)
    x0, xmax = -7.2, 7.2
    x, row, placed = x0, 0, []
    gap = size * 0.34
    for w in words:
        body = w["text"].replace("’", "'").replace("“", "“").strip()
        e = EMPHASIS.get(norm(body), {})
        font = ITALIC if spoken else e.get("font", BOLD)
        s = size * e.get("k", 1.0)
        piv = group("word", 0, 0, line)
        ob = text(body, s, 0, 0, DIM if not spoken else WHITE, font, parent=piv, own=True)
        wd = width_of(ob)
        pad = s * 0.3 if e.get("pill") else 0.0      # room for the pill around it
        if x + wd + 2 * pad > xmax and x > x0:
            x, row = x0, row + 1
        x += pad
        piv.location = (x + wd / 2, rows_y[min(row, len(rows_y) - 1)], 0)
        ob.location = (-wd / 2, -s * 0.36, 0.02)
        if e.get("pill"):
            pill = rect(wd + s * 0.5, s * 1.15, 0, 0, e["pill"], r=s * 0.4, parent=piv, z=0.01)
        placed.append((piv, ob, w, e))
        x += wd + gap + pad
    # enter: rise in staggered (spoken: each word appears as it's said)
    for k, (piv, ob, w, e) in enumerate(placed):
        ty = piv.location.y
        ta = w["start"] - 0.06 if spoken else t_in + 0.03 * k
        key(piv, T0, loc=(piv.location.x, ty - 0.5), scale=0.0)
        key(piv, ta, loc=(piv.location.x, ty - 0.5), scale=0.0)
        key(piv, ta + 0.22, loc=(piv.location.x, ty), scale=1.0)
        # sung: highlight and pop, then settle to its sung colour
        if not spoken:
            key_color(ob, T0, DIM)
            key_color(ob, w["start"] - 0.02, e.get("now", CORAL))
            key_color(ob, max(w["end"], w["start"] + 0.12), e.get("sung", WHITE))
        key(piv, w["start"] - 0.02, scale=1.0)
        key(piv, w["start"] + 0.07, scale=1.1)
        key(piv, w["start"] + 0.22, scale=1.0)
    # leave: the whole line flies up and shrinks away
    key(line, t_out - 0.001, loc=(0, 0), scale=1.0)
    key(line, t_out + 0.2, loc=(0, 1.2), scale=(1.0, 0.0, 1.0))


def split_line(words):
    """Split a line's words into two phrases: at a comma near the middle if there is one,
    otherwise at the word boundary nearest the middle of the line's time."""
    n = len(words)
    if n < 4:
        return [words]
    best, cost = n // 2, 9.0
    t_mid = (words[0]["start"] + words[-1]["end"]) / 2
    for i in range(2, n - 1):
        c = abs(words[i]["start"] - t_mid) / max(0.5, words[-1]["end"] - words[0]["start"])
        if words[i - 1]["text"].rstrip().endswith((",", ".", "?", "”")):
            c -= 0.25
        if c < cost:
            best, cost = i, c
    return [words[:best], words[best:]]


STYLES = ["poster", "ragged", "tilt", "mixed"]
TOP, BOTTOM, MAXW = -0.35, -3.85, 13.6   # the lyric area (lower part of the screen)


def phrase(words, t_in, t_out, style, spoken=False, idx=0):
    """One phrase (half a line), set big. style:
      poster  rows in heavy caps, each scaled to fill the width (so rows differ in size)
      ragged  left-aligned; the key word much bigger than the rest
      tilt    like poster, slightly rotated, sliding in from the side
      mixed   faces alternate word by word (condensed caps, book italic, mono)
    Words wait dim, light up and pop as they are sung, then settle to white or their colour.
    Spoken phrases: italic, each word appears as it is said."""
    if not words:
        return
    g = group("phrase", 0, 0)
    caps = style in ("poster", "tilt")
    items = []
    for k, w in enumerate(words):
        body = w["text"].replace("\u2019", "'").strip()
        e = EMPHASIS.get(norm(body), {})
        if spoken:
            font = SCRIPT if norm(body) == "kevin" else SERIF_I
        elif style == "mixed":
            font = e.get("font") or (BEBAS, SERIF_BI, MONO)[k % 3]
        elif style == "poster":
            font = e.get("font", BEBAS)
        elif style == "tilt":
            font = e.get("font", GOTHIC_O)
        else:
            font = e.get("font", GOTHIC)
        if font in CAPS_FONTS:
            body = body.upper()
        kk = e.get("k", 1.0) * (1.9 if style == "ragged" and e else 1.0)
        piv = group("word", 0, 0, g)
        ob = text(body, 1.0, 0, 0, WHITE if spoken else DIM, font, parent=piv, own=True)
        items.append(dict(piv=piv, ob=ob, w=w, e=e, k=kk, wd=width_of(ob) * kk, cap=cap_height(font) * kk))
    for it in items:
        it["ob"].scale = (it["k"], it["k"], 1)
    gap = 0.3
    natural = sum(it["wd"] for it in items) + gap * (len(items) - 1)
    # rows: one if it fits big enough, else the most balanced two (or three) rows
    def rows_for(n):
        if n == 1:
            return [items]
        best = None
        for cut in range(1, len(items)):
            a, b = items[:cut], items[cut:]
            if n == 3 and len(b) > 1:
                for cut2 in range(1, len(b)):
                    r = [a, b[:cut2], b[cut2:]]
                    m = max(sum(i["wd"] for i in x) for x in r)
                    best = min(best or (m, r), (m, r), key=lambda v: v[0])
            elif n == 2:
                r = [a, b]
                m = max(sum(i["wd"] for i in x) for x in r)
                best = min(best or (m, r), (m, r), key=lambda v: v[0])
        return best[1] if best else [items]
    n_rows = 1 if natural * 1.25 <= MAXW else (2 if natural <= 2 * MAXW / 1.05 or len(items) < 4 else 3)
    rows = rows_for(min(n_rows, len(items)))
    # sizes per row
    sizes = []
    for r in rows:
        rw = sum(i["wd"] for i in r) + gap * (len(r) - 1)
        if style in ("poster", "tilt"):
            sizes.append(min(2.2, MAXW / rw))
        else:
            sizes.append(None)
    if None in sizes:
        common = min(1.7, min(MAXW / (sum(i["wd"] for i in r) + gap * (len(r) - 1)) for r in rows))
        sizes = [common] * len(rows)
    # stack the rows by their cap heights, with a tight gap (caps have no descenders to clear)
    caps_h = [max(i["cap"] for i in r) for r in rows]
    gap_y = 0.32
    height = sum(c * s_ for c, s_ in zip(caps_h, sizes)) + gap_y * sum(sizes[1:]) * 0.7
    shrink = min(1.0, (TOP - BOTTOM) / height)
    sizes = [s_ * shrink for s_ in sizes]
    height *= shrink
    y = TOP - (TOP - BOTTOM - height) / 2           # top of the first row
    for n_, (r, s_, c) in enumerate(zip(rows, sizes, caps_h)):
        if n_:
            y -= gap_y * s_ * 0.7
        base = y - c * s_                               # this row's baseline
        rw = (sum(i["wd"] for i in r) + gap * (len(r) - 1)) * s_
        x = -rw / 2 if style in ("poster", "tilt") else -MAXW / 2
        for it in r:
            wd = it["wd"] * s_
            it["piv"].location = (x + wd / 2, base + it["cap"] * s_ / 2, 0)
            it["piv"].scale = (s_, s_, 1)
            it["ob"].location = (-it["wd"] / 2, -it["cap"] / 2, 0.02)
            if it["e"].get("pill"):
                rect(it["wd"] + 0.35, it["cap"] * 1.6, 0, 0, it["e"]["pill"], r=0.3, parent=it["piv"], z=0.01)
            it["size"] = s_
            x += wd + gap * s_
        y = base
    # animate
    side = -1 if idx % 2 else 1
    for k, it in enumerate(items):
        piv, w, e, s_ = it["piv"], it["w"], it["e"], it["size"]
        px, py = piv.location.x, piv.location.y
        ta = w["start"] - 0.06 if spoken else t_in + 0.04 * k
        start_loc = (px + 2.5 * side, py) if style == "tilt" else (px, py - 0.6)
        key(piv, T0, loc=start_loc, scale=0.0)
        key(piv, ta, loc=start_loc, scale=0.0)
        key(piv, ta + 0.2, loc=(px, py), scale=s_)
        if not spoken:
            key_color(it["ob"], T0, DIM)
            key_color(it["ob"], w["start"] - 0.02, e.get("now", CORAL))
            key_color(it["ob"], max(w["end"], w["start"] + 0.12), e.get("sung", WHITE))
        key(piv, w["start"] - 0.02, scale=s_)
        key(piv, w["start"] + 0.07, scale=s_ * 1.08)
        key(piv, w["start"] + 0.22, scale=s_)
    # pivot the phrase on its own centre (so the tilt doesn't push one end off the bottom)
    cy = (TOP + BOTTOM) / 2
    for it in items:
        for fc in it["piv"].animation_data.action.fcurves:
            if fc.data_path == "location" and fc.array_index == 1:
                for kp in fc.keyframe_points:
                    kp.co.y -= cy
                    kp.handle_left.y -= cy
                    kp.handle_right.y -= cy
    if style == "tilt":
        g.rotation_euler.z = 0.045 * side
    key(g, t_out - 0.001, loc=(0, cy), scale=1.0)
    key(g, t_out + 0.18, loc=(0, cy + 1.0), scale=(1.0, 0.0, 1.0))


def lyric_phrases(ln, t_out, words=None, spoken=False, counter=[0]):
    """A line as two phrases, one at a time, each in the next typographic style."""
    words = words if words is not None else ln["words"]
    parts = split_line(words)
    for k, part in enumerate(parts):
        t_in = part[0]["start"] - 0.3
        t_end = parts[k + 1][0]["start"] - 0.3 if k + 1 < len(parts) else t_out
        style = "mixed" if spoken else STYLES[counter[0] % len(STYLES)]
        phrase(part, t_in, t_end, style, spoken, counter[0])
        counter[0] += 1


# ---------------------------------------------------------------- deck chrome and background
def background():
    me = bpy.data.meshes.new("bg")
    me.from_pydata([(-W, -H, 0), (W, -H, 0), (W, H, 0), (-W, H, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("bg", me)
    ob.location.z = -0.5
    m = bpy.data.materials.new("bg")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    rm = nt.nodes.new("ShaderNodeMapRange")
    rm.inputs["From Min"].default_value, rm.inputs["From Max"].default_value = 4.5, -4.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*srgb(NAVY), 1)
    ramp.color_ramp.elements[1].color = (*srgb(NAVY2), 1)
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], rm.inputs["Value"])
    nt.links.new(rm.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    me.materials.append(m)
    return link(ob)


def chrome(lines, beats):
    """Header, a slide counter that ticks over with every line, and an accent bar that pulses on
    the half-time beats."""
    text("Q3 STRATEGY OFFSITE  ·  CONFIDENTIAL", 0.26, -7.2, 3.95, LILAC, SEMI)
    circle(0.09, 7.2, 4.04, CORAL)
    for k, ln in enumerate(lines):
        t_a = ln["start"] - 0.35
        t_b = lines[k + 1]["start"] - 0.35 if k + 1 < len(lines) else END + 1
        c = text(f"SLIDE {k + 2:02d} / 212", 0.24, 7.2, -4.2, "#7f8fc8", SEMI, align="RIGHT")
        hide_until(c, t_a)
        pop_in(c, t_a, 0.15)
        key(c, t_b - 0.001, scale=1.0)
        key(c, t_b, scale=0.0)
    bar = rect(1.2, 0.07, -7.2, -4.12, CORAL, anchor="left")
    for b in beats:
        if b["beat"] in (1, 3):
            key(bar, b["t"] - 0.001, scale=(1.0, 1.0, 1.0))
            key(bar, b["t"] + 0.06, scale=(1.9, 1.6, 1.0))
            key(bar, b["t"] + 0.35, scale=(1.0, 1.0, 1.0))


# ---------------------------------------------------------------- graphics for each line
def at(ln, word, k=0):
    """Start time of the k-th occurrence of `word` in the line."""
    hits = [w for w in ln["words"] if norm(w["text"]) == norm(word)]
    return hits[min(k, len(hits) - 1)]["start"]


def card(w, h, x, y, parent, color=NAVY2, edge=None):
    if edge:
        rect(w + 0.08, h + 0.08, x, y, edge, r=0.22, parent=parent, z=-0.01)
    return rect(w, h, x, y, color, r=0.18, parent=parent)


def show(g, t_in, t_out, dur=0.25):
    pop_in(g, t_in, dur)
    pop_out(g, t_out)


def g_okrs(ln, t_out):
    """OKR cards pop in; a roadmap bar races to a JUNE flag."""
    g = group("okrs", 0, 2.2)
    t0 = at(ln, "OKRs")
    for k, label in enumerate(("OKR 1  Synergy ↑", "OKR 2  Velocity ↑↑", "OKR 3  Kevins: TBD")):
        c = group("okr", -4.8 + 4.8 * k, 0.75, g)
        card(4.2, 1.0, 0, 0, c)
        rect(0.34, 0.34, -1.75, 0, YELLOW, r=0.06, parent=c, z=0.01)
        text(label, 0.32, -1.4, -0.12, WHITE, SEMI, parent=c)
        pop_in(c, t0 + 0.14 * k)
    road = group("road", -6.3, -0.75, g)
    rect(12.6, 0.12, 0, 0, "#3a4280", anchor="left", parent=road)
    fill = rect(12.6, 0.12, 0, 0, CORAL, anchor="left", parent=road, z=0.01)
    t_r, t_j = at(ln, "roadmap"), at(ln, "June")
    key(fill, T0, scale=(0.0, 1, 1))
    key(fill, t_r, scale=(0.0, 1, 1))
    key(fill, t_j, scale=(1.0, 1, 1))
    for m, mon in enumerate(("JAN", "FEB", "MAR", "APR", "MAY")):
        text(mon, 0.24, 0.1 + 2.5 * m, -0.45, LILAC, SEMI, parent=road)
    flag = group("june", 12.6, 0, road)
    rect(0.07, 1.0, 0, 0.5, WHITE, parent=flag)
    poly([(0.04, 1.0), (1.2, 0.8), (0.04, 0.6)], CORAL, parent=flag)
    text("JUNE", 0.26, 0.18, 0.72, WHITE, BLACK, parent=flag)
    key(flag, T0, loc=(12.6, 3.0), scale=0.0)
    key(flag, t_j - 0.15, loc=(12.6, 3.0), scale=0.0)
    key(flag, t_j, loc=(12.6, 0.0), scale=1.0)
    key(flag, t_j + 0.08, loc=(12.6, 0.12), scale=1.0)
    key(flag, t_j + 0.18, loc=(12.6, 0.0), scale=1.0)
    show(g, ln["start"] - 0.3, t_out)


def g_ships(ln, t_out):
    """Q3 deliverables: the progress bar crawls, then slams to 100% on 'Tuesday'."""
    g = group("ships", 0, 2.0)
    card(11.0, 2.6, 0, 0, g, edge="#3a4280")
    text("Q3 DELIVERABLES", 0.34, -5.0, 0.7, LILAC, BLACK, parent=g)
    text("assigned to: agent", 0.26, 5.0, 0.72, "#7f8fc8", SEMI, align="RIGHT", parent=g)
    rect(10.0, 0.42, -5.0, -0.15, INK, r=0.2, anchor="left", parent=g)
    bar = rect(10.0, 0.42, -5.0, -0.15, CORAL, r=0.2, anchor="left", parent=g, z=0.01)
    t_s, t_t = at(ln, "ships"), at(ln, "Tuesday")
    key(bar, T0, scale=(0.02, 1, 1))
    key(bar, t_s, scale=(0.02, 1, 1))
    key(bar, t_t - 0.1, scale=(0.12, 1, 1))
    key(bar, t_t + 0.08, scale=(1.0, 1, 1))
    done = group("done", 0, -0.85, g)
    text("100%  ✓  Done! (also did Q4)", 0.36, 0, -0.12, MINT, BLACK, align="CENTER", parent=done)
    pop_in(done, t_t + 0.1)
    show(g, ln["start"] - 0.3, t_out)


def g_paste(ln, t_out):
    """A wall of code nobody reads, then ⌘V into the deck."""
    g = group("paste", 0, 2.0)
    code = group("code", -3.6, 0, g)
    card(6.4, 3.2, 0, 0, code, color=INK, edge="#3a4280")
    t0, t_p = ln["start"], at(ln, "paste")
    import random
    rng = random.Random(4)
    for k in range(12):
        y = 1.3 - 0.235 * k
        w = rng.uniform(1.5, 5.4)
        ind = 0.4 * rng.randint(0, 3)
        c = rect(w - ind, 0.11, -2.9 + ind, y, rng.choice((LILAC, "#59638f", MINT, CORAL, "#59638f")), anchor="left",
                 parent=code)
        grow = t0 + 0.12 * k
        key(c, T0, scale=(0.0, 1, 1))
        key(c, grow, scale=(0.0, 1, 1))
        key(c, grow + 0.1, scale=(1.0, 1, 1))
    deck = group("deck", 3.8, 0, g)
    card(4.6, 2.9, 0, 0, deck, color=PAPER)
    text("Q3 Strategy", 0.3, -1.95, 0.95, INK, BLACK, parent=deck)
    blob = rect(3.9, 1.6, 0, -0.35, "#59638f", r=0.08, parent=deck, z=0.01)
    key(blob, T0, scale=0.0)
    key(blob, t_p + 0.15, scale=0.0)
    key(blob, t_p + 0.3, scale=1.0)
    keycap = group("cmdv", 0.2, 0.0, g)
    card(1.7, 1.5, 0, 0, keycap, color=WHITE, edge="#7f8fc8")
    text("⌘V", 0.62, 0, -0.22, INK, BLACK, align="CENTER", parent=keycap)
    key(keycap, T0, scale=0.0)
    key(keycap, t_p - 0.001, scale=0.0, rot=0.3)
    key(keycap, t_p + 0.1, scale=1.25, rot=-0.08)
    key(keycap, t_p + 0.22, scale=1.0, rot=0.0)
    key(keycap, t_p + 0.7, scale=1.0)
    key(keycap, t_p + 0.85, scale=0.0)
    show(g, t0 - 0.3, t_out)


def g_check(ln, t_out):
    """'Is this safe?' in a speech bubble; the answer is a cheque, stamped SEVERANCE."""
    g = group("check", 0, 2.0)
    bub = group("bubble", -3.6, 0.4, g)
    card(4.6, 1.3, 0, 0, bub, color=WHITE)
    poly([(-1.4, -0.6), (-0.6, -0.6), (-1.7, -1.2)], WHITE, parent=bub)
    text("Is this safe?", 0.5, 0, -0.17, INK, ITALIC, align="CENTER", parent=bub)
    pop_in(bub, at(ln, "Is"))
    pop_out(bub, at(ln, "got") - 0.15)
    chq = group("cheque", 1.0, 0.0, g)
    card(8.2, 2.9, 0, 0, chq, color=PAPER)
    rect(8.2, 0.35, 0, 1.05, "#cfe7d5", parent=chq, z=0.01)
    text("PAY TO:  the last guy who asked", 0.3, -3.8, 0.25, INK, SEMI, parent=chq)
    text("$ 50,000.00", 0.62, 3.8, -0.45, INK, BLACK, align="RIGHT", parent=chq)
    text("memo: thanks, bye", 0.26, -3.8, -1.05, "#59638f", ITALIC, parent=chq)
    t_c = at(ln, "got")                # the cheque arrives with "got", the stamp on "handshake"
    t_h = at(ln, "handshake")
    key(chq, T0, loc=(12.0, 0.0))
    key(chq, t_c - 0.2, loc=(12.0, 0.0))
    key(chq, t_c + 0.05, loc=(1.0, 0.0))
    stamp = group("stamp", 2.0, -0.1, chq)
    rect(3.6, 0.95, 0, 0, RED, r=0.1, parent=stamp, z=0.03)
    rect(3.3, 0.7, 0, 0, PAPER, r=0.06, parent=stamp, z=0.04)
    text("SEVERANCE", 0.46, 0, -0.17, RED, BLACK, align="CENTER", parent=stamp, z=0.05)
    key(stamp, T0, scale=0.0)
    key(stamp, t_h - 0.001, scale=0.0)
    key(stamp, t_h + 0.1, scale=2.2, rot=-0.15)
    key(stamp, t_h + 0.22, scale=1.0, rot=-0.22)
    show(g, ln["start"] - 0.3, t_out)


def g_org(ln, t_out):
    """Org chart: KEVIN (intern) drops in, then gets stamped HEAD OF AI RISK."""
    g = group("org", 0, 2.1)
    top = group("me", 0, 1.1, g)
    card(3.6, 0.9, 0, 0, top, edge=LILAC)
    text("ME  ·  VP of Vision", 0.32, 0, -0.12, WHITE, SEMI, align="CENTER", parent=top)
    rect(0.06, 0.8, 0, 0.25, LILAC, parent=g)
    t_k, t_h = at(ln, "Kevin"), at(ln, "Head")
    kev = group("kev", 0, -0.55, g)
    card(4.4, 1.5, 0, 0, kev, color=CORAL)
    text("KEVIN", 0.6, 0, 0.0, WHITE, BLACK, align="CENTER", parent=kev)
    text("intern", 0.3, 0, -0.5, INK, SEMI, align="CENTER", parent=kev)
    key(kev, T0, loc=(0, 3.5), scale=0.0)
    key(kev, t_k - 0.12, loc=(0, 3.5), scale=0.0)
    key(kev, t_k + 0.08, loc=(0, -0.55), scale=1.0)
    tag = group("tag", 3.1, -0.2, g)
    rect(3.6, 0.6, 0, 0, YELLOW, r=0.12, parent=tag, z=0.02)
    text("HEAD OF AI RISK", 0.3, 0, -0.11, INK, BLACK, align="CENTER", parent=tag, z=0.03)
    key(tag, T0, scale=0.0)
    key(tag, t_h - 0.001, scale=0.0, rot=0.4)
    key(tag, t_h + 0.12, scale=1.3, rot=0.05)
    key(tag, t_h + 0.24, scale=1.0, rot=0.12)
    for x in (-5.0, 5.0):   # empty seats in the org chart
        e = group("empty", x, -0.55, g)
        card(2.6, 1.0, 0, 0, e, color="#232a5c")
        text("(agent)", 0.28, 0, -0.1, "#59638f", SEMI, align="CENTER", parent=e)
    show(g, ln["start"] - 0.3, t_out)


def g_budget(ln, t_out):
    """A $10 budget, and a stopwatch for the tenure that's spinning already."""
    g = group("budget", 0, 2.0)
    money = group("money", -3.0, 0, g)
    text("BUDGET", 0.3, 0, 1.0, LILAC, BLACK, align="CENTER", parent=money)
    big = text("$10", 1.9, 0, -0.7, MINT, BLACK, align="CENTER", parent=money)
    text(".00", 0.6, 1.75, -0.65, MINT, BLACK, parent=money)
    t_d = at(ln, "ten")
    key(money, T0, scale=0.0)
    key(money, t_d - 0.001, scale=0.0)
    key(money, t_d + 0.12, scale=1.2)
    key(money, t_d + 0.3, scale=1.0)
    watch = group("watch", 3.6, -0.1, g)
    circle(1.25, 0, 0, WHITE, parent=watch)
    circle(1.1, 0, 0, INK, parent=watch, z=0.01)
    rect(0.4, 0.3, 0, 1.38, WHITE, parent=watch)
    hand = group("hand", 0, 0, watch)
    rect(0.07, 0.95, 0, 0.42, CORAL, parent=hand, z=0.02)
    circle(0.1, 0, 0, CORAL, parent=watch, z=0.03)
    text("TENURE", 0.3, 0, -1.75, LILAC, BLACK, align="CENTER", parent=watch)
    t_t = at(ln, "tenure")
    pop_in(watch, t_t - 0.1)
    key(hand, t_t, rot=0.0)
    key(hand, t_out + 0.3, rot=-math.tau * 6)     # spinning: the tenure is running out fast
    show(g, ln["start"] - 0.3, t_out)


def g_logs(ln, t_out):
    """Spoken: a growth arrow shoots up; then the folder nobody may open."""
    g = group("logs", 0, 2.0)
    arrow = group("growth", -4.2, -1.3, g)
    pts = [(0, 0), (1.2, 0.5), (2.0, 0.3), (3.4, 2.4)]
    poly(pts, MINT, parent=arrow, width=0.16)
    poly([(3.0, 2.55), (3.6, 2.7), (3.55, 2.05)], MINT, parent=arrow)
    t_g = at(ln, "growth")
    key(arrow, T0, scale=0.0)
    key(arrow, t_g - 0.001, scale=(0.0, 0.0, 1.0))
    key(arrow, t_g + 0.3, scale=(1.0, 1.0, 1.0))
    fold = group("folder", 3.0, 0.1, g)
    rect(1.6, 0.5, -1.4, 1.2, YELLOW, r=0.12, parent=fold)
    card(4.6, 2.8, 0, 0, fold, color=YELLOW)
    text("DO_NOT_OPEN_LOGS", 0.36, 0, -0.1, INK, MONO, align="CENTER", parent=fold)
    lock = group("lock", 0, -0.85, fold)
    circle(0.32, 0, 0.3, INK, parent=lock, z=0.01, ring=0.09)
    rect(0.9, 0.62, 0, -0.05, INK, r=0.08, parent=lock, z=0.02)
    t_p = at(ln, "Please")
    key(fold, T0, scale=0.0)
    key(fold, t_p - 0.001, scale=0.0)
    key(fold, t_p + 0.15, scale=1.15)
    key(fold, t_p + 0.3, scale=1.0)
    t_o = at(ln, "open")
    key(fold, t_o, rot=0.0)
    key(fold, t_o + 0.06, rot=0.06)
    key(fold, t_o + 0.12, rot=-0.06)
    key(fold, t_o + 0.18, rot=0.04)
    key(fold, t_o + 0.26, rot=0.0)
    show(g, ln["start"] - 0.3, t_out)


def hook(ln, t_out, n=5):
    """WE NEED A / MEAT PROXY: huge words slamming in on the beat (upper part of the screen)."""
    g = group("hook", 0, 0)
    words = ln["words"][:n]
    rows = [(words[:3], 2.55, 1.15, WHITE), (words[3:], 0.75, 1.75, CORAL)]
    for ws, y, size, col in rows:
        objs, x = [], 0.0
        for w in ws:
            piv = group("hw", 0, y, g)
            ob = text(w["text"].strip(",.").upper(), size * 1.25, 0, 0, col, BEBAS, parent=piv)
            wd = width_of(ob)
            objs.append((piv, ob, wd, w))
            x += wd + size * 0.3
        x = -x / 2 + size * 0.15
        for piv, ob, wd, w in objs:
            piv.location.x = x + wd / 2
            ob.location = (-wd / 2, -size * 0.36, 0.02)
            x += wd + size * 0.3
            key(piv, T0, scale=0.0)
            key(piv, w["start"] - 0.03, scale=2.4)
            key(piv, w["start"] + 0.09, scale=0.94)
            key(piv, w["start"] + 0.2, scale=1.0)
            key(piv, w["start"] - 0.031, scale=0.0)
    show(g, words[0]["start"] - 0.3, t_out, 0.01)
    return g


def g_bill(ln, t_out):
    hook(ln, at(ln, "body") - 0.15)
    g = group("invoice", 0, 2.0)
    card(9.6, 3.0, 0, 0, g, color=PAPER)
    text("INVOICE", 0.5, -4.3, 0.8, INK, BLACK, parent=g)
    text("#0001", 0.3, 4.3, 0.85, "#59638f", MONO, align="RIGHT", parent=g)
    text("1 × human body (accountable)", 0.34, -4.3, -0.1, INK, SEMI, parent=g)
    text("BILLABLE", 0.62, 4.3, -1.05, MINT, BLACK, align="RIGHT", parent=g)
    show(g, at(ln, "body") - 0.05, t_out)


def g_merge(ln, t_out):
    """Every merge approved by Kevin; then a pulse that holds still."""
    g = group("merge", 0, 2.0)
    t_m = at(ln, "merge")
    for k in range(4):
        r = group("row", -2.6, 1.15 - 0.62 * k, g)
        card(9.2, 0.5, 0, 0, r, color=INK)
        text(f"✓ Merged #{4812 + k * 37}  —  approved by", 0.28, -4.3, -0.1, MINT, MONO, parent=r)
        text("Kevin", 0.3, 4.3, -0.1, CORAL, BLACK, align="RIGHT", parent=r)
        pop_in(r, t_m - 0.2 + 0.14 * k, 0.18)
    ecg = group("ecg", 4.6, -0.05, g)
    card(4.2, 2.4, 0, 0, ecg, color=INK, edge="#3a4280")
    line = group("line", -1.9, -0.2, ecg)
    pts = [(0, 0), (0.6, 0), (0.8, 0.7), (1.0, -0.5), (1.2, 0), (3.8, 0)]
    poly(pts, MINT, parent=line, width=0.07)
    text("♥  54 bpm", 0.32, 0, 0.75, MINT, BLACK, align="CENTER", parent=ecg)
    t_p = at(ln, "pulse")
    key(line, T0, scale=(0.0, 1, 1))
    key(line, t_p, scale=(0.0, 1, 1))
    key(line, at(ln, "still") + 0.3, scale=(1.0, 1, 1))
    key(ecg, T0, scale=0.0)
    pop_in(ecg, t_p - 0.15)
    show(g, ln["start"] - 0.3, t_out)


def g_table(ln, t_out):
    """BOT vs KEVIN: assets and knees."""
    g = group("table", 0, 2.0)
    for k, (head, col) in enumerate((("BOT", LILAC), ("KEVIN", CORAL))):
        h = group("head", 1.2 + 3.6 * k, 1.05, g)
        card(3.2, 0.8, 0, 0, h, color=col)
        text(head, 0.42, 0, -0.15, INK if k else INK, BLACK, align="CENTER", parent=h)
        pop_in(h, ln["start"] + 0.12 * k)
    # both rows are up from the start of the line; the knees values land a beat before "knees",
    # so there's time to read the gag
    for r_, (label, vals, word) in enumerate((("ASSETS", ("0", "$9.40"), "assets"), ("KNEES", ("0", "2"), "it's"))):
        y = 0.0 - 1.0 * r_
        row = group("row", 0, y, g)
        text(label, 0.42, -6.0, -0.15, WHITE, BLACK, parent=row)
        rect(12.0, 0.04, 0, -0.5, "#3a4280", parent=row)
        for k, v in enumerate(vals):
            c = group("cell", 1.2 + 3.6 * k, 0, row)
            text(v, 0.5, 0, -0.18, YELLOW if k else "#59638f", BLACK, align="CENTER", parent=c)
            pop_in(c, at(ln, word) + 0.15 + 0.25 * k)
        pop_in(row, ln["start"] + 0.25 + 0.2 * r_, 0.18)
    show(g, ln["start"] - 0.3, t_out)


def g_hire(ln, t_out):
    """A job ad for a little Kevin."""
    g = group("hire", 0, 2.0)
    card(9.0, 3.2, 0, 0, g, color=WHITE)
    rect(9.0, 0.8, 0, 1.2, CORAL, parent=g, z=0.01)
    text("NOW HIRING:  a little Kevin", 0.42, -4.1, 1.05, WHITE, BLACK, parent=g, z=0.02)
    reqs = (("Has a pulse", "hire"), ("Can sign things", "little"), ("Easy to forsake", "forsake"))
    for k, (req, word) in enumerate(reqs):
        r = group("req", -3.9, 0.2 - 0.62 * k, g)
        text(req, 0.36, 0.0, -0.13, INK, SEMI, parent=r)
        text("✓✓✓" if word == "forsake" else "✓", 0.44, 7.6, -0.15, MINT, BLACK, align="RIGHT",
             parent=r)
        pop_in(r, at(ln, word), 0.2)
    show(g, ln["start"] - 0.3, t_out)


def g_loop(ln, t_out):
    """The loop (with Kevin riding round it), then his name on every line."""
    g = group("loop", 0, 2.0)
    lp = group("ring", -3.6, 0, g)
    circle(1.4, 0, 0, LILAC, parent=lp, ring=0.12)
    for k, a in enumerate((0.0, 2.1, 4.2)):
        b = group("agent", 1.4 * math.cos(a), 1.4 * math.sin(a), lp)
        card(1.2, 0.5, 0, 0, b, color=INK, edge=LILAC)
        text("agent", 0.22, 0, -0.08, LILAC, MONO, align="CENTER", parent=b)
    rider = group("rider", 0, 0, lp)
    circle(0.28, 1.4, 0, CORAL, parent=rider, z=0.03)
    text("K", 0.3, 1.4, -0.11, WHITE, BLACK, align="CENTER", parent=rider, z=0.04)
    t_l = at(ln, "loop")
    key(rider, t_l, rot=0.0)
    key(rider, t_out + 0.3, rot=math.tau * 2.5)
    pop_in(lp, t_l - 0.2)
    sig = group("sigs", 3.6, 0, g)
    card(5.0, 3.2, 0, 0, sig, color=PAPER)
    t_n = at(ln, "name")
    for k in range(5):
        y = 1.1 - 0.52 * k
        rect(3.6, 0.03, 0.25, y - 0.12, "#59638f", parent=sig, z=0.01)
        s = group("sig", -2.0, y, sig)
        text("x", 0.26, 0, -0.1, "#59638f", SEMI, parent=s, z=0.02)
        text("Kevin", 0.36, 0.45, -0.08, "#2a4fb8", ITALIC, parent=s, z=0.02)
        pop_in(s, t_n + 0.16 * k, 0.15)
    key(sig, T0, scale=0.0)
    pop_in(sig, t_n - 0.25)
    show(g, ln["start"] - 0.3, t_out)


def g_sign(ln, t_out):
    hook(ln, at(ln, "and") - 0.15)
    g = group("contract", 0, 2.0)
    card(7.0, 3.3, 0, 0, g, color=PAPER)
    text("ACCOUNTABILITY AGREEMENT", 0.32, -3.1, 1.15, INK, BLACK, parent=g)
    for k in range(4):
        rect(5.6 - 0.8 * (k % 2), 0.08, -3.1, 0.55 - 0.32 * k, "#c9c3b3", anchor="left", parent=g, z=0.01)
    rect(3.2, 0.04, -0.9, -1.0, INK, parent=g, z=0.01)
    arrow = group("arrow", -4.8, -0.95, g)
    poly([(-1.2, 0.18), (0.0, 0.18), (0.0, 0.42), (0.6, 0.0), (0.0, -0.42), (0.0, -0.18), (-1.2, -0.18)], CORAL,
         parent=arrow)
    text("SIGN HERE", 0.26, -1.15, 0.5, CORAL, BLACK, parent=arrow)
    t_a, t_s = at(ln, "paperwork"), at(ln, "sign")
    for k in range(6):   # bounce on the beats
        tb = t_a + 0.27 * k
        key(arrow, tb, loc=(-4.8, -0.95))
        key(arrow, tb + 0.13, loc=(-4.5, -0.95))
    stamp = group("stamp", -0.9, -0.6, g)
    rect(3.0, 1.2, 0, 0, CORAL, r=0.12, parent=stamp, z=0.03)
    text("SIGN", 0.8, 0, -0.28, WHITE, BLACK, align="CENTER", parent=stamp, z=0.04)
    key(stamp, T0, scale=0.0)
    key(stamp, t_s - 0.001, scale=0.0)
    key(stamp, t_s + 0.1, scale=2.0, rot=0.2)
    key(stamp, t_s + 0.22, scale=1.0, rot=0.08)
    show(g, at(ln, "and") - 0.05, t_out)


# lines (by their first words) -> graphic, and how the lyric is set
LINES = [
    ("I've got OKRs", g_okrs, {}), ("The agent ships", g_ships, {}), ("I've never read", g_paste, {}),
    ("And the last guy", g_check, {}), ("So I made", g_org, {}), ("With a budget", g_budget, {}),
    ("Great growth", g_logs, {"spoken": True}),
    ("We need a meat proxy, a body", g_bill, {"skip": 5}), ("A name on every", g_merge, {}),
    ("The bot's got", g_table, {}), ("So we'll hire", g_hire, {}), ("Put him in", g_loop, {}),
    ("We need a meat proxy, and", g_sign, {"skip": 5}),
]


# ---------------------------------------------------------------- the intro title
def title(beats):
    """The title slide builds on the beats, then flies away for the first lyric."""
    g = group("title", 0, 0)
    bt = [b["t"] for b in beats if b["t"] >= 1.7]
    rows = [(("WE", "NEED", "A"), 1.25, 1.9, WHITE, bt[0:3]), (("MEAT", "PROXY"), 0.0, 2.1, CORAL, bt[4:6])]
    for words, y, size, col, times in rows:
        x = -7.0
        for w, t in zip(words, times):
            piv = group("tw", 0, y, g)
            ob = text(w, size, 0, 0, col, BLACK, parent=piv)
            wd = width_of(ob)
            piv.location.x = x + wd / 2
            ob.location = (-wd / 2, -size * 0.36, 0.02)
            x += wd + size * 0.28
            key(piv, T0, loc=(piv.location.x, y + 6), scale=1.0)
            key(piv, t - 0.18, loc=(piv.location.x, y + 6))
            key(piv, t, loc=(piv.location.x, y - 0.1))
            key(piv, t + 0.1, loc=(piv.location.x, y))
    ul = rect(6.0, 0.12, -7.0, -1.1, CORAL, anchor="left", parent=g)
    key(ul, T0, scale=(0.0, 1, 1))
    key(ul, bt[8], scale=(0.0, 1, 1))
    key(ul, bt[8] + 0.4, scale=(1.0, 1, 1))
    tag = group("tag", 0, -1.85, g)
    text("Agents do the work. Someone has to sign it.", 0.42, -7.0, -0.15, "#d7defa", SEMI, parent=tag)
    key(tag, T0, loc=(0, -2.6), scale=(1, 0, 1))
    key(tag, bt[12] - 0.001, loc=(0, -2.6), scale=(1, 0, 1))
    key(tag, bt[12] + 0.3, loc=(0, -1.85), scale=(1, 1, 1))
    t_out = LYRICS_START - 0.5
    key(g, t_out, loc=(0, 0), scale=1.0)
    key(g, t_out + 0.25, loc=(0, 4.0), scale=(1.0, 0.0, 1.0))


# ---------------------------------------------------------------- build and render
END = 999.0
LYRICS_START = 0.0


def build(lyrics, start, end):
    global T0, END, LYRICS_START, COL
    T0, END = start, end
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    COL = sc.collection
    lines = [ln for ln in lyrics["lines"] if start - 1 <= ln["start"] < end]
    beats = [b for b in lyrics["beats"] if start - 1 <= b["t"] <= end + 1]
    LYRICS_START = lines[0]["start"] if lines else end
    background()
    chrome(lines, beats)
    if start < LYRICS_START:
        title(beats)
    for k, ln in enumerate(lines):
        nxt = lines[k + 1]["start"] if k + 1 < len(lines) else end + 1
        t_out = min(nxt - 0.3, ln["end"] + 1.2)
        spec = next(((fn, opt) for pre, fn, opt in LINES
                     if norm(ln["text"]).startswith(norm(pre))), (None, {}))
        fn, opt = spec
        words = ln["words"][opt.get("skip", 0):]
        lyric_phrases(ln, t_out, words=words, spoken=opt.get("spoken", False))
        if fn:
            fn(ln, t_out)
    ease_all()
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type, cam_d.ortho_scale = "ORTHO", W
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = (0, 0, 10)
    link(cam)
    sc.camera = cam


def setup(sc, res, n, preview):
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y, sc.render.resolution_x = res, res * 16 // 9
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, n
    sc.eevee.taa_render_samples = 1 if preview else 8
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 1.0          # 360-degree shutter
    sc.eevee.motion_blur_steps = 4 if preview else 8
    sc.eevee.use_raytracing = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.film_transparent = False


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--music")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=66.6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", type=int, default=540)
    ap.add_argument("--stills", help="comma-separated song times to render as PNGs instead")
    ap.add_argument("--final", action="store_true", help="more samples")
    ap.add_argument("--noblur", action="store_true", help="no motion blur (much quicker, for review)")
    ap.add_argument("--lossless", action="store_true",
                    help="write lossless FFV1 video (out.mkv), for use as the TV's texture in the 3D scene")
    A = ap.parse_args(argv)
    sc = bpy.context.scene
    build(json.load(open(A.lyrics)), A.start, A.end)
    n = int(round((A.end - A.start) * FPS))
    setup(sc, A.res, n, not A.final)
    sc.render.use_motion_blur = not A.noblur
    if A.stills:
        os.makedirs(A.out, exist_ok=True)
        for t in [float(v) for v in A.stills.split(",")]:
            sc.frame_set(fr(t))
            sc.render.filepath = os.path.join(A.out, f"still_{t:06.2f}.png")
            bpy.ops.render.render(write_still=True)
        return
    im = sc.render.image_settings
    im.file_format = "FFMPEG"
    if A.lossless:
        im.color_mode = "RGB"
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
        sc.render.filepath = A.out + ".mkv"
    else:
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        sc.render.ffmpeg.constant_rate_factor = "HIGH"
        sc.render.filepath = A.out + ".mp4"
    sc.render.use_file_extension = False
    bpy.ops.render.render(animation=True)
    print("RENDER done ->", sc.render.filepath)


if __name__ == "__main__":
    main()
