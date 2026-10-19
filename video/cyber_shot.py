"""The camera and the 3D lyrics for verse 3 + chorus 3 in cyberspace (cyber_set.py), used by
dance_demo.py --set cyber.

Camera: waypoints round v9 (azimuth, elevation, distance, lens, aim height) at song times: slow
drifts through the verse, then in the chorus big moves (orbits right round her, overhead,
behind, below the platform, in close, far out). Interpolated with a Catmull-Rom spline in time
and smoothed, so it never jerks.

Lyrics: half a line at a time, as glass words (cyber_lyrics.lyric_words) hanging in world space
far out behind v9 (FAR from the camera), each phrase gliding in a straight line from where the
camera sees it as it appears to where it sees it as it leaves, so it stays in view: one row in the band of the frame away
from v9 (top if she sits low in the frame, bottom if high), or (short phrases, alternately) the
words stacked one under another beside her. Words wait faint, light up gold as they're sung, then
stay lit; the line flicks in before it starts and out as the next arrives. The sides of the
frame are left free (for the holograms to come).
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cyber_lyrics as CL  # noqa: E402

CHORUS = 191.2
# (song time, azimuth deg (0: in front of her, +: round to her left / screen right), elevation
# deg, distance, lens mm, aim height)
WAYPOINTS = [
    (162.6, 0, 6, 3.2, 40, 0.5),
    (169.0, 14, 10, 2.8, 42, 0.5),
    (175.5, -6, 5, 2.4, 46, 0.52),
    (181.5, -28, -6, 2.6, 42, 0.5),
    (187.5, -16, 3, 3.0, 38, 0.5),
    (191.2, -8, 8, 3.4, 34, 0.5),            # the chorus kicks in
    (193.9, 30, 36, 3.6, 30, 0.45),          # up high
    (198.3, 85, 6, 2.2, 34, 0.5),            # her side, close
    (202.6, 140, -22, 3.0, 28, 0.55),        # behind, low
    (207.0, 205, 14, 2.6, 32, 0.5),          # round the back
    (211.3, 290, -42, 2.6, 24, 0.6),         # below, looking up
    (215.6, 360, 62, 3.0, 28, 0.45),         # straight down on her
    (219.9, 345, 2, 1.55, 50, 0.6),          # in close (the rock section)
    (224.4, 400, -14, 2.0, 30, 0.55),
    (228.7, 470, 26, 3.8, 26, 0.45),
    (233.0, 505, -55, 3.2, 22, 0.6),         # dive under
    (237.4, 545, 10, 1.8, 45, 0.55),
    (241.8, 600, 30, 4.5, 30, 0.45),
    (245.6, 620, 8, 6.0, 30, 0.45),          # pulling away
]
ORBIT = 0.6                  # the chorus orbit, slowed: this fraction of the waypoints' turning
WAYPOINTS = [(t, (az if t <= CHORUS else -8 + ORBIT * (az + 8)), el, d, ln, tz)
             for t, az, el, d, ln, tz in WAYPOINTS]
SENSOR_W, SENSOR_H = 36.0, 20.25           # the camera's sensor (16:9, fit horizontally)


def _cr(p0, p1, p2, p3, s):
    return 0.5 * (2 * p1 + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3)


def _raw(t):
    W = WAYPOINTS
    t = min(max(t, W[0][0]), W[-1][0])
    k = max(i for i in range(len(W) - 1) if W[i][0] <= t) if t < W[-1][0] else len(W) - 2
    s = (t - W[k][0]) / (W[k + 1][0] - W[k][0])
    q = [W[max(0, k - 1)], W[k], W[k + 1], W[min(len(W) - 1, k + 2)]]
    return [_cr(*[p[i] for p in q], s) for i in range(1, 6)]


_TABLE = None


def _table(rate=60):
    """The raw spline sampled and smoothed in time (heavier in the verse)."""
    global _TABLE
    if _TABLE is None:
        t0, t1 = WAYPOINTS[0][0], WAYPOINTS[-1][0]
        n = int((t1 - t0) * rate) + 1
        raw = [_raw(t0 + j / rate) for j in range(n)]
        def smooth(sigma):
            r = int(3 * sigma * rate)
            w = [math.exp(-0.5 * (d / (sigma * rate)) ** 2) for d in range(-r, r + 1)]
            res = []
            for j in range(n):
                acc, ws = [0.0] * 5, 0.0
                for d, wd in zip(range(-r, r + 1), w):
                    v = raw[min(n - 1, max(0, j + d))]
                    acc = [a + wd * x for a, x in zip(acc, v)]
                    ws += wd
                res.append([a / ws for a in acc])
            return res
        calm, lively = smooth(0.9), smooth(0.35)     # verse / chorus, crossfaded over 2 s
        out = []
        for j in range(n):
            u = min(1.0, max(0.0, (t0 + j / rate - (CHORUS - 1.0)) / 2.0))
            u = u * u * (3 - 2 * u)
            out.append([a + (b - a) * u for a, b in zip(calm[j], lively[j])])
        _TABLE = (t0, rate, out)
    return _TABLE


def cam_pose(t):
    """Camera (location, aim point, lens) at song time t."""
    t0, rate, tab = _table()
    x = (t - t0) * rate
    j = min(len(tab) - 2, max(0, int(x)))
    f = min(1.0, max(0.0, x - j))
    az, el, d, lens, tz = [a + (b - a) * f for a, b in zip(tab[j], tab[j + 1])]
    a, e = math.radians(az), math.radians(el)
    tgt = Vector((0, 0, tz))
    loc = tgt + d * Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    return loc, tgt, lens


def cam_matrix(t):
    loc, tgt, lens = cam_pose(t)
    rot = (tgt - loc).to_track_quat("-Z", "Y").to_matrix().to_4x4()
    return Matrix.Translation(loc) @ rot, lens


def screen_y(t, p):
    """Where world point p sits in the frame at time t, vertically (-1 bottom .. 1 top)."""
    M, lens = cam_matrix(t)
    c = M.inverted() @ Vector(p)
    if c.z >= -1e-6:
        return 0.0
    return (c.y / -c.z) / (SENSOR_H / 2 / lens)


# ---------------------------------------------------------------- lyrics
COLORS = ["#3ff0ff", "#b9a7f5", "#ff5fd2"]
DIST = 1.15                  # how far in front of the camera a line sits


def split_line(words):
    """Two rows, split at a comma near the middle if there is one, else the middle word."""
    n = len(words)
    if n < 5:
        return [words]
    best, cost = n // 2, 9
    for i in range(2, n - 1):
        c = abs(i - n / 2) - (1.5 if words[i - 1]["text"].rstrip().endswith((",", ".")) else 0)
        if c < cost:
            best, cost = i, c
    return [words[:best], words[best:]]


def screen_x(t, p):
    """Where world point p sits in the frame at time t, horizontally (-1 left .. 1 right)."""
    M, lens = cam_matrix(t)
    c = M.inverted() @ Vector(p)
    if c.z >= -1e-6:
        return 0.0
    return (c.x / -c.z) / (SENSOR_W / 2 / lens)


def _clean(w):
    return w["text"].replace("\u2019", "'").replace("\u201c", "").replace("\u201d", "").strip()


def _animate_words(items, ws, all_words, t_in, t_out, start, end_t, f):
    for it, w in zip(items, ws):
        ob, mat, rest = it
        nxt = next((x["start"] for x in all_words if x["start"] > w["start"]), w["end"])
        t_end = max(nxt, w["start"] + 0.15)
        for t, lv, hv in ((t_in, 0.0, 0.0), (w["start"] - 0.03, 0.0, 0.0), (w["start"], 1.0, 1.0),
                          (t_end - 0.04, 1.0, 1.0), (t_end + 0.06, 1.0, 0.0)):
            ob["lit"], ob["hl"] = lv, hv
            ob.keyframe_insert('["lit"]', frame=max(1, f(t)))
            ob.keyframe_insert('["hl"]', frame=max(1, f(t)))
        for t, sc in ((w["start"] - 0.02, 1.0), (w["start"] + 0.07, 1.1), (w["start"] + 0.22, 1.0)):
            ob.scale = (sc, sc, sc)
            ob.keyframe_insert("scale", frame=max(1, f(t)))
        # only in the render while the phrase is up (hidden words still cost a lot)
        for t, hide in ((start, True), (t_in - 0.05, False), (t_out + 0.05, True)):
            ob.hide_render = hide
            ob.keyframe_insert("hide_render", frame=max(1, f(t)))


def _flick(root, t_in, t_out, f):
    base = root.scale.copy()
    for t, sc in ((t_in - 0.01, 0.0), (t_in, 0.0), (t_in + 0.18, 1.0), (t_out - 0.15, 1.0), (t_out, 0.0)):
        root.scale = base * max(sc, 1e-4)
        root.keyframe_insert("scale", frame=max(1, f(t)))


def _width(items):
    xs = [(it[0].location.x - it[0].dimensions.x / 2, it[0].location.x + it[0].dimensions.x / 2) for it in items]
    return max(b for _, b in xs) - min(a for a, _ in xs)


FAR = 9.0                    # how far from the camera the lyrics hang (well behind v9)


FOLLOW = 0.35                # how much of the camera's move a phrase follows (0: fixed in space)


def _place_world(root, local, s, t_in, t_out, f):
    """Put a phrase in world space, far out behind v9. It's set where the camera sees it (at
    `local`, scaled out to FAR) in the middle of its time on screen, and keeps that orientation;
    it moves in one straight line, FOLLOW of the way toward where it would have to be to stay
    put in the frame as it appears and as it leaves. So the camera visibly moves round and past
    it, while it drifts enough to stay in view."""
    far = local * (FAR / DIST)
    pos = {}
    for t in (t_in, (t_in + t_out) / 2, t_out):
        M, lens = cam_matrix(t)
        pos[t] = M @ far
    tm = (t_in + t_out) / 2
    M, _ = cam_matrix(tm)
    rot = M.to_quaternion()
    root.rotation_mode = "QUATERNION"
    root.rotation_quaternion = rot
    for t in (t_in, t_out):
        root.location = pos[tm] + FOLLOW * (pos[t] - pos[tm])
        root.keyframe_insert("location", frame=max(1, f(t)))
    k = FAR / DIST
    root.scale = (s * k, s * k, s * k)
    for fc in root.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def place_lyrics(col, lines, start, end, fps, cam=None, phones=None):
    """phones: [(t_in, t_out, left shown, right shown)] (the phone holograms); stacked phrases
    go on a side without a phone, and become a row if both are up."""
    """Build and animate every line between start and end (song seconds), half a line at a
    time: each half either as one row in the band away from v9, or (short halves, when there's
    room) its words stacked one under another beside her."""
    f = lambda t: int(round((t - start) * fps)) + 1
    count = 0
    for k, ln in enumerate(lines):
        halves = split_line(ln["words"])
        line_out = min(lines[k + 1]["start"] - 0.55 if k + 1 < len(lines) else end, ln["end"] + 1.4)
        color = COLORS[k % len(COLORS)]
        for h, ws in enumerate(halves):
            # each half comes in just before its first word and stays until the next half is
            # due, but always long enough to read its last (gold) word
            t_in = (ln["start"] - 0.45) if h == 0 else ws[0]["start"] - 0.12
            nxt_in = halves[h + 1][0]["start"] - 0.12 if h + 1 < len(halves) else line_out
            t_out = max(nxt_in, ws[-1]["start"] + 0.55)
            tm = (ws[0]["start"] + ws[-1]["end"]) / 2
            M, lens = cam_matrix(tm)
            fw, fh = DIST * SENSOR_W / lens, DIST * SENSOR_H / lens        # the frame at that distance
            vx = screen_x(tm, (0, 0, 0.45))
            vy = screen_y(tm, (0, 0, 0.45))
            bodies = [_clean(w) for w in ws]
            up = [(l_, r_) for a_, b_, l_, r_ in (phones or []) if a_ <= tm <= b_]
            busy_l = any(l_ for l_, _ in up)
            busy_r = any(r_ for _, r_ in up)
            stack = len(ws) <= 5 and abs(vx) < 0.4 and count % 2 == 1 and not (busy_l and busy_r)
            count += 1
            name = f"ly{k}_{h}"
            if stack:
                # words one under another, on the side away from her (or alternating if she's centred)
                side = -1 if vx > 0.08 else 1 if vx < -0.08 else (1 if k % 2 else -1)
                if busy_l:
                    side = 1
                elif busy_r:
                    side = -1
                size = 0.1 * fh
                rows = []
                for i, b in enumerate(bodies):
                    root, items = CL.lyric_words(col, [b], (0, 0, 0), (0, 0, 0), size, color, f"{name}_{i}")
                    rows.append((root, items))
                bpy.context.view_layer.update()
                widest = max(_width(items) for _, items in rows)
                s = min(1.0, 0.38 * fw / max(widest, 1e-6))
                gap = size * 1.25 * s
                y0 = gap * (len(rows) - 1) / 2
                x_c = side * 0.55 * fw / 2
                for i, ((root, items), w) in enumerate(zip(rows, ws)):
                    local = Vector((x_c, y0 - gap * i + 0.06 * fh, -DIST))
                    _place_world(root, local, s, t_in, t_out, f)
                    _flick(root, t_in + 0.05 * i, t_out, f)
                    _animate_words(items, [w], ln["words"], t_in, t_out, start, end, f)
            else:
                top = vy < 0.0                                # her middle high in the frame -> bottom
                size = 0.095 * fh
                root, items = CL.lyric_words(col, bodies, (0, 0, 0), (0, 0, 0), size, color, name)
                bpy.context.view_layer.update()
                s = min(1.0, 0.78 * fw / max(_width(items), 1e-6))
                local = Vector((0, (0.64 if top else -0.64) * fh / 2, -DIST))
                _place_world(root, local, s, t_in, t_out, f)
                _flick(root, t_in, t_out, f)
                _animate_words(items, ws, ln["words"], t_in, t_out, start, end, f)
    for ob in bpy.data.objects:                          # word states change crisply
        ad = ob.animation_data
        if ob.name.startswith("ly") and ad and ad.action:
            for fc in ad.action.fcurves:
                if fc.data_path in ('["lit"]', '["hl"]'):
                    for kp in fc.keyframe_points:
                        kp.interpolation = "LINEAR"
