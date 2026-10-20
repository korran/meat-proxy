"""SINN's on-screen broadcast graphics, laid over the camera image of the news studio
(news_set.py): a LIVE bug, the graphics box on the right (over the Anchor's shoulder), and along
the bottom the lower third: the SINN logo bug, a BREAKING headline bar, and the news scroller
(where the lyrics go). A flat 2D scene with a transparent background, built with
screen_graphics.py's helpers (16 x 9 units, x -8..8, y -4.5..4.5).

Animated over the bridge: each lyric line gets its own headline (flipped in) and its own
graphic in the box (see LINES). Rendered as a transparent video and laid over the studio render.

  blender -b --factory-startup --python video/news_overlay.py -- --lyrics video/build/lyrics.json \\
      --start 129.4 --end 148.6 --out video/build/news_overlay_bridge [--res 540] [--stills 132,137]
  ffmpeg -i studio.mp4 -i video/build/news_overlay_bridge.mkv -filter_complex overlay out.mp4

  (no --lyrics: a single still frame, news_overlay.png, for checking the layout)
"""
import argparse
import json
import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen_graphics as SG  # noqa: E402
from screen_graphics import (BLACK, BOLD, ITALIC, SEMI, at, circle, group, hide_until, key,  # noqa: E402
                             poly, pop_in, rect, text, width_of)

AMBER, WHITE, RED = "#ffb21c", "#ffffff", "#d01c2a"
NAVY, NAVY2, INK, MINT, GRID = "#0b1638", "#13235a", "#081028", "#3ddc97", "#1f2d5c"
BOX = (3.9, 0.85, 7.6, 5.6)      # the graphics area: centre x, y, width, height (units)
EPS = 1.0 / SG.FPS


# The 'NN': one heavy rounded stroke per N, the two tied together by a stroke running under
# both (unit height; the stroke's centreline, x from 0 to NN_W).
NN_PATHS = [[(0.0, -0.3), (0.0, 1.0), (0.72, 0.0), (0.72, 1.0)],
            [(1.17, 0.0), (1.17, 1.0), (1.89, 0.0), (1.89, 1.0)],
            [(0.0, -0.3), (1.89, -0.3)]]
NN_W, NN_STROKE = 1.89, 0.24
SI_CAP = 1.6          # the height of "SI" (its caps) relative to the NN


def logo_bug(x, y, h, parent=None):
    """The SINN logo: 'SI' in amber letters a third bigger, 'NN' a white rounded ribbon, on one
    baseline at y (h: the NN's height). Returns (group, width)."""
    g = group("logo", x, y, parent)
    si = text("SI", h * SI_CAP / 0.727, 0, -NN_STROKE * h / 2, AMBER, BLACK, parent=g)
    x0 = width_of(si) + h * 0.14 + NN_STROKE * h / 2
    for path in NN_PATHS:
        pts = [(x0 + px * h, py * h) for px, py in path]
        poly(pts, WHITE, parent=g, z=0.01, width=NN_STROKE * h)
        for px, py in pts:
            circle(NN_STROKE * h / 2, px, py, WHITE, parent=g, z=0.01)
    return g, x0 + (NN_W + NN_STROKE / 2) * h


# ---------------------------------------------------------------- animation helpers
def visible(ob, t_in, t_out=None):
    """Snap on at t_in (and off at t_out)."""
    hide_until(ob, t_in)
    key(ob, t_in, scale=1.0)
    if t_out is not None:
        key(ob, t_out - EPS, scale=1.0)
        key(ob, t_out, scale=0.0)


def flip(ob, t_in, t_out=None, dur=0.18):
    """Flip in (squashed flat, then open) at t_in, and closed again at t_out."""
    key(ob, SG.T0, scale=(1, 0, 1))
    key(ob, t_in, scale=(1, 0, 1))
    key(ob, t_in + dur, scale=(1, 1, 1))
    if t_out is not None:
        key(ob, t_out - dur, scale=(1, 1, 1))
        key(ob, t_out, scale=(1, 0, 1))


def counter(parent, values, times, t_end, size, x, y, color, font=BLACK, align="CENTER", colors=None):
    """A number ticking through `values` at `times`, gone at t_end."""
    obs = []
    for k, v in enumerate(values):
        c = colors[k] if colors else color
        ob = text(v, size, x, y - size * 0.36, c, font, align=align, parent=parent, z=0.04)
        visible(ob, times[k], times[k + 1] if k + 1 < len(values) else t_end)
        obs.append(ob)
    return obs


def rolling(parent, fmt, v0, v1, t0, t1, t_end, size, x, y, color, final=None, final_color=None,
            font=BLACK, align="CENTER"):
    """A number counting smoothly from v0 to v1 between t0 and t1, a new value every frame
    (easing out as it arrives), shown as fmt(v); then `final` (or the last value) until t_end."""
    n = max(1, int(round((t1 - t0) * SG.FPS)))
    vals, times = [], []
    for i in range(n + 1):
        u = i / n
        u = 1 - (1 - u) ** 2
        body = fmt(v0 + (v1 - v0) * u)
        if not vals or body != vals[-1]:
            vals.append(body)
            times.append(t0 + (t1 - t0) * i / n)
    if final:
        vals[-1] = final
    cols = [color] * (len(vals) - 1) + [final_color or color]
    return counter(parent, vals, times, t_end, size, x, y, color, font=font, align=align, colors=cols)


def reveal(parent, x0, x1, y0, y1, t0, t1, z=0.035):
    """A cover (the box's colour) over x0..x1 that slides off to the right between t0 and t1,
    revealing what's under it from left to right (a chart line drawing itself)."""
    cv = rect(x1 - x0, y1 - y0, x1, (y0 + y1) / 2, INK, parent=parent, z=z, anchor="left")
    key(cv, SG.T0, scale=(-1, 1, 1))
    key(cv, t0, scale=(-1, 1, 1))
    key(cv, t1, scale=(-0.0001, 1, 1))
    return cv


def stamp(parent, label, x, y, t, color=RED, size=0.5, rot=-0.15):
    st = group("stamp", x, y, parent)
    st.location.z = 0.08
    w = len(label) * size * 0.66 + 0.5
    rect(w, size * 1.7, 0, 0, color, r=0.08, parent=st, z=0.0)
    rect(w - 0.2, size * 1.7 - 0.2, 0, 0, INK, r=0.05, parent=st, z=0.001)
    text(label, size, 0, -size * 0.36, color, BLACK, align="CENTER", parent=st, z=0.002)
    key(st, SG.T0, scale=0.0)
    key(st, t - EPS, scale=0.0, rot=rot + 0.25)
    key(st, t + 0.1, scale=1.8, rot=rot - 0.05)
    key(st, t + 0.22, scale=1.0, rot=rot)
    return st


def chart_line(pts, color, parent, width=0.14, z=0.03):
    """A polyline with round joints (and ends), so its segments read as one stroke."""
    poly(pts, color, parent=parent, z=z, width=width)
    for x, y in pts:
        circle(width / 2, x, y, color, parent=parent, z=z)


def chart_grid(g, bw, s, rows=5, y0=-1.6, dy=0.72):
    for k in range(rows):
        rect(bw - 0.4, 0.025, 0, y0 + dy * k, GRID, parent=g, z=0.02)


# ---------------------------------------------------------------- graphics, line by line
def g_markets(g, ln, t_in, t_out):
    """The markets chart draws itself while the value counts up to $892 TRILLION; the arrow
    punches out through the top of the box."""
    cx, cy, bw, s = BOX
    c = group("markets", 0, 0, g)
    chart_grid(c, bw, s)
    kx = (bw - 1.0) / 4.5
    pts = [(-2.25 * kx, -1.35), (-1.5 * kx, -0.95), (-0.85 * kx, -1.15), (-0.1 * kx, -0.25), (0.55 * kx, -0.55),
           (1.25 * kx, 0.85), (1.95 * kx, 1.95)]
    chart_line(pts, MINT, c)
    t_m, t_h = at(ln, "markets"), at(ln, "high,")
    reveal(c, pts[0][0] - 0.2, pts[-1][0] + 0.2, -1.8, 2.2, t_in + 0.2, t_h)
    # the arrowhead rides the line's end, then bursts up out of the box
    tip = group("tip", pts[-1][0], pts[-1][1], c)
    tip.location.z = 0.05
    poly([(-0.32, -0.05), (0.0, 0.42), (0.32, -0.05)], MINT, parent=tip)
    tip.rotation_euler.z = -0.6
    key(tip, SG.T0, scale=0.0)
    key(tip, t_h - EPS, scale=0.0)
    key(tip, t_h + 0.1, scale=1.3, loc=(pts[-1][0], pts[-1][1]))
    key(tip, t_h + 0.45, scale=1.0, loc=(pts[-1][0] + 0.5, s / 2 + 0.55))
    trail = poly([(pts[-1][0], pts[-1][1]), (pts[-1][0] + 0.5, s / 2 + 0.55)], MINT, parent=c, z=0.04, width=0.14)
    key(trail, SG.T0, scale=0.0)
    key(trail, t_h + 0.1, scale=0.0)
    key(trail, t_h + 0.12, scale=1.0)
    rolling(c, lambda v: f"${v:,.0f}T", 12, 892, t_in + 0.3, t_h, t_out + 0.3, 0.85, 0, -2.3, MINT,
            final="$892 TRILLION")
    rh = text("▲ RECORD HIGH", 0.4, -bw / 2 + 0.3, s / 2 - 0.66, MINT, BLACK, parent=c, z=0.04)
    hide_until(rh, t_h)
    pop_in(rh, t_h, 0.2)
    return c


def g_unemployment(g, ln, t_in, t_out):
    """Unemployment dives to 0.0% ('zero'), because the AI has assigned every human physical work
    on its own infrastructure (the tasks flick by); 'nobody's asking why': QUESTIONS: 0."""
    cx, cy, bw, s = BOX
    c = group("unemp", 0, 0, g)
    chart_grid(c, bw, s)
    kx = (bw - 1.0) / 4.5
    zero_y = -1.6
    pts = [(-2.25 * kx, 1.1), (-1.55 * kx, 1.25), (-0.9 * kx, 0.9), (-0.3 * kx, 1.0), (0.35 * kx, 0.15),
           (0.95 * kx, -0.75), (1.45 * kx, zero_y), (2.1 * kx, zero_y)]
    chart_line(pts, RED, c)
    t_u, t_z, t_n, t_w = at(ln, "Unemployment’s"), at(ln, "zero,"), at(ln, "nobody’s"), at(ln, "why,")
    reveal(c, pts[0][0] - 0.2, pts[-1][0] + 0.2, -1.9, 2.1, t_u, t_z + 0.15)
    dot = circle(0.16, pts[-2][0], zero_y, WHITE, parent=c, z=0.05)
    hide_until(dot, t_z)
    pop_in(dot, t_z, 0.2, over=1.6)
    lab = text("0%", 0.3, -bw / 2 + 0.25, zero_y + 0.08, "#7f8fc8", BLACK, parent=c, z=0.04)
    rolling(c, lambda v: f"{v:.1f}%", 4.1, 0.0, t_u + 0.1, t_z, t_out + 0.3, 1.1, 1.2, -2.35, WHITE,
            final_color=MINT)
    text("UNEMPLOYMENT", 0.36, -bw / 2 + 0.3, -2.42, "#9fb3ff", BLACK, parent=c, z=0.04)
    stamp(c, "QUESTIONS: 0", -0.9, 0.55, t_w, RED, 0.48)
    # why it's zero: the AI has given every human on Earth physical work for its own projects
    # (useful to it; not what anyone would call a job)
    top = s / 2 - 0.55
    head = text("ASSIGNED TASK:", 0.3, -bw / 2 + 0.3, top - 0.11, "#9fb3ff", BLACK, parent=c, z=0.04)
    tasks = ["polish solar panel #88,412", "dust server rack B-114", "lay fiber to Antarctica",
             "mine cobalt (quota: 4 kg)", "rivet Dyson panel #3,115,902"]
    t0 = t_z + 0.1
    times = [t0 + (t_out - t0) * k / len(tasks) for k in range(len(tasks))]
    counter(c, tasks, times, t_out + 0.3, 0.32, -bw / 2 + 2.45, top, WHITE, font=SEMI, align="LEFT")
    note = text("*all 8.1 billion humans", 0.26, -bw / 2 + 0.3, top - 0.58, "#7f8fc8", ITALIC, parent=c, z=0.04)
    for ob in (head, note):
        hide_until(ob, t0)
        pop_in(ob, t0, 0.2)
    return c


def g_fine(g, ln, t_in, t_out):
    """A word from our sponsors: a calm meter, its needle swinging over to FINE and pinned there
    (straining against the stop); EVERYTHING IS FINE."""
    cx, cy, bw, s = BOX
    c = group("fine", 0, 0, g)
    gx, gy, R = 0.0, -1.05, 2.0
    zones = [("PANIC", RED, math.pi, math.pi * 2 / 3), ("CONCERN", AMBER, math.pi * 2 / 3, math.pi / 3),
             ("FINE", MINT, math.pi / 3, 0.0)]
    for name, col, a0, a1 in zones:
        n = 16
        outer = [(gx + R * math.cos(a0 + (a1 - a0) * i / n), gy + R * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        inner = [(gx + 0.62 * R * math.cos(a1 + (a0 - a1) * i / n), gy + 0.62 * R * math.sin(a1 + (a0 - a1) * i / n))
                 for i in range(n + 1)]
        poly(outer + inner, col, parent=c, z=0.03)
        am = (a0 + a1) / 2
        text(name, 0.3, gx + 1.18 * R * math.cos(am), gy + 1.18 * R * math.sin(am) - 0.1, WHITE, BLACK,
             align="CENTER", parent=c, z=0.04)
    needle = group("needle", gx, gy, c)
    needle.location.z = 0.05
    poly([(-0.08, 0), (0.0, R * 0.9), (0.08, 0)], WHITE, parent=needle)
    circle(0.18, 0, 0, WHITE, parent=c, z=0.06).location = (gx, gy, 0.06)
    t_s, t_r, t_e, t_f = at(ln, "sponsors"), at(ln, "remind"), at(ln, "everything"), at(ln, "fine,")
    key(needle, SG.T0, rot=0.9)
    key(needle, t_in + 0.2, rot=0.9)
    key(needle, t_r, rot=0.25)          # wobbling through CONCERN...
    key(needle, t_r + 0.3, rot=0.45)
    key(needle, t_e, rot=-1.2)          # ...and slammed over to FINE
    k = 0
    t = t_e + 0.2
    while t < t_out:                     # pinned, straining at the stop
        key(needle, t, rot=-1.2 + (0.04 if k % 2 else -0.02))
        t += 0.09
        k += 1
    sp = group("sponsor", 0, s / 2 - 0.55, c)
    text("A WORD FROM OUR SPONSORS", 0.32, 0, 0.1, "#9fb3ff", BLACK, align="CENTER", parent=sp, z=0.04)
    text("SafetyCorp™  ·  “Totally Under Control”", 0.3, 0, -0.42, WHITE, ITALIC, align="CENTER", parent=sp,
         z=0.04)
    hide_until(sp, t_s)
    pop_in(sp, t_s, 0.2)
    big = group("big", 0, -2.2, c)
    text("EVERYTHING IS FINE", 0.66, 0, -0.24, MINT, BLACK, align="CENTER", parent=big, z=0.04)
    hide_until(big, t_e)
    pop_in(big, t_e, 0.25)
    return c


# (service, metric, up). Today: ~10^18 FLOP/s supercomputers, ~10^23 bytes of storage on Earth,
# ~2 x 10^13 W (20 TW) of human power use; the AI draws 640 TW (the Dyson swarm isn't online yet).
STATUS = [("Compute", "4.2 × 10³⁸ FLOP/s", True), ("Memory", "9.1 × 10³¹ bytes", True),
          ("Power draw", "640 TW", True), ("Power grid", None, True), ("Fusion reactors", None, True),
          ("Satellite comms", None, True), ("Orbital lift", "2.1 Mt / day", True),
          ("Breathable air", None, False), ("Rule of law", None, False), ("Elections", None, False),
          ("Privacy", None, False)]


def g_status(g, ln, t_in, t_out):
    """Everything is fine, as a tech status page: the AI's infrastructure all green, OPERATIONAL;
    the things people need, N/A. The banner lands on 'everything' and flashes on 'fine'."""
    cx, cy, bw, s = BOX
    c = group("status", 0, 0, g)
    t_e, t_f = at(ln, "everything"), at(ln, "fine,")
    ban = group("banner", 0, s / 2 - 0.55, c)
    rect(bw - 0.4, 0.72, 0, 0, MINT, r=0.08, parent=ban, z=0.03)
    text("✓  ALL SYSTEMS OPERATIONAL", 0.4, 0, -0.14, INK, BLACK, align="CENTER", parent=ban, z=0.04)
    hide_until(ban, t_e)
    pop_in(ban, t_e, 0.25)
    for k in range(3):                                  # flashes on 'fine'
        key(ban, t_f + 0.12 * k, scale=1.0)
        key(ban, t_f + 0.12 * k + 0.06, scale=1.06)
    key(ban, t_f + 0.36, scale=1.0)
    x0, x1 = -bw / 2 + 0.35, bw / 2 - 0.35
    y0, dy = s / 2 - 1.22, 0.385
    t0 = t_in + 0.15
    step = (t_e - 0.1 - t0) / len(STATUS)
    for k, (name, metric, up) in enumerate(STATUS):
        y = y0 - dy * k
        row = group("row", 0, y, c)
        rect(bw - 0.6, 0.02, 0, -dy / 2, GRID, parent=row, z=0.02)
        text(name, 0.27, x0, -0.1, WHITE if up else "#9fb3ff", SEMI, parent=row, z=0.04)
        if metric:
            text(metric, 0.27, x1 - 2.2, -0.1, "#cfe0ff", BLACK, align="RIGHT", parent=row, z=0.04)
        col = MINT if up else "#59638f"
        st = group("state", 0, 0, row)
        text("Operational" if up else "N/A", 0.27, x1, -0.1, col, BLACK, align="RIGHT", parent=st, z=0.04)
        circle(0.08, x1 - (1.85 if up else 0.78), 0.0, col, parent=st, z=0.04)
        tk = t0 + step * k
        hide_until(row, tk)
        pop_in(row, tk, 0.15)
        hide_until(st, tk + 0.12)
        pop_in(st, tk + 0.12, 0.15, over=1.25)
    return c


def person_icon(parent, x, y, s, color, own=False):
    g = group("p", x, y, parent)
    h = circle(0.2 * s, 0, 0.62 * s, color, parent=g, z=0.03, own=own)
    b = rect(0.46 * s, 0.6 * s, 0, 0.12 * s, color, r=0.16 * s, parent=g, z=0.03, own=own)
    return g, (h, b)


DIRT = "#6b4a2e"
DIG = 1.1             # one shovelful every two beats (54 bpm: a beat every ~0.55 s)


def shovel(person, x, y):
    """A hand shovel held by a person icon (pivots at the hands)."""
    sh = group("shovel", x, y, person)
    sh.location.z = 0.05                      # in front of the body and the dirt
    rect(0.05, 0.62, 0.0, -0.18, "#a8794a", parent=sh, z=0.0)        # handle
    rect(0.16, 0.05, 0.0, 0.12, "#a8794a", parent=sh, z=0.0)         # grip
    poly([(-0.1, -0.48), (0.1, -0.48), (0.08, -0.66), (0.0, -0.72), (-0.08, -0.66)], "#c9ced6", parent=sh,
         z=0.001)                                                     # blade
    sh.rotation_euler.z = 0.35
    return sh


def dig(sh, t0, t1, person=None):
    """Dig in unison, once per DIG: push the blade down into the pile (bending a little), pry,
    lift the shovelful up and toss it to the side, settle back."""
    x0, y0 = sh.location.x, sh.location.y
    key(sh, SG.T0, loc=(x0, y0), rot=0.35)
    if person:
        key(person, SG.T0, scale=1.0)
    t = t0
    while t + DIG <= t1 + DIG:
        key(sh, t, loc=(x0, y0), rot=0.35)
        key(sh, t + DIG * 0.3, loc=(x0 - 0.02, y0 - 0.13), rot=0.15)     # blade pushed into the dirt
        key(sh, t + DIG * 0.42, loc=(x0 - 0.02, y0 - 0.13), rot=0.05)    # pry
        key(sh, t + DIG * 0.68, loc=(x0 + 0.06, y0 + 0.12), rot=0.95)    # lift and toss to the side
        key(sh, t + DIG * 0.9, loc=(x0, y0), rot=0.35)
        if person:
            key(person, t, scale=1.0)
            key(person, t + DIG * 0.32, scale=(1.03, 0.92, 1))           # bent over the shovel
            key(person, t + DIG * 0.68, scale=(0.99, 1.02, 1))
            key(person, t + DIG * 0.9, scale=1.0)
        t += DIG


def g_comply(g, ln, t_in, t_out):
    """Return to your station and remain in line (i.e. don't rebel): rows of identical workers,
    each with a hand shovel at a dirt pile, all digging in slow unison; one has wandered out of line,
    flagged NONCOMPLIANCE, and walks back on 'return to your station' (then digs in step); on
    'remain in line' a scan sweeps the rows, everyone snaps into perfect alignment,
    COMPLIANCE: 100%."""
    cx, cy, bw, s = BOX
    c = group("comply", 0, 0, g)
    rows, cols = 3, 7
    sx, sy = (bw - 1.2) / (cols - 1), 1.15
    x0, y0 = -(bw - 1.2) / 2, 1.0
    rng = random.Random(6)
    t_ret, t_st, t_rem, t_line = at(ln, "return"), at(ln, "station..."), at(ln, "remain"), at(ln, "line.")
    BLUE = "#7f9cff"
    rebel = (1, 4)
    for r in range(rows):
        for k in range(cols):
            x, y = x0 + sx * k, y0 - sy * r
            # the station: a dirt pile to dig
            poly([(x - 0.42, y - 0.36), (x + 0.42, y - 0.36), (x + 0.24, y - 0.2), (x - 0.22, y - 0.18)], DIRT,
                 parent=c, z=0.036)
            p, parts = person_icon(c, x, y - 0.1, 0.62, BLUE, own=(r, k) == rebel)
            sh = shovel(p, 0.18, 0.15)
            if (r, k) == rebel:
                back = t_in + DIG * math.ceil((t_st + 0.3 - t_in) / DIG)
                dig(sh, back, t_out, p)           # joins in, in step, once back at the station
            else:
                dig(sh, t_in, t_out, p)
            if (r, k) == rebel:
                # out of line: up and off to the side, tilted; flagged in red; walks back
                key(p, SG.T0, loc=(x + 0.35, y + 0.42), rot=0.35)
                key(p, t_ret, loc=(x + 0.35, y + 0.42), rot=0.35)
                for j in range(5):            # shuffling back, a little bob on each step
                    u = (j + 1) / 5
                    tt = t_ret + (t_st + 0.3 - t_ret) * u
                    key(p, tt, loc=(x + 0.35 * (1 - u), y - 0.1 + 0.52 * (1 - u) + (0.06 if j % 2 else 0)),
                        rot=0.35 * (1 - u))
                for ob in parts:
                    SG.key_color(ob, SG.T0, RED)
                    SG.key_color(ob, t_st + 0.3, BLUE)
                ring = circle(0.5, x + 0.35, y + 0.55, RED, parent=c, z=0.045, ring=0.06)
                tag = group("flag", x + 0.35, y + 1.22, c)
                tag.location.z = 0.06
                rect(2.6, 0.42, 0, 0, RED, r=0.06, parent=tag)
                text("NONCOMPLIANCE", 0.26, 0, -0.09, WHITE, BLACK, align="CENTER", parent=tag, z=0.001)
                for ob in (ring, tag):
                    t = t_in
                    while t < t_st + 0.3:     # blinking until they're back
                        key(ob, t, scale=1.0)
                        key(ob, t + 0.3, scale=1.0)
                        key(ob, t + 0.3 + EPS, scale=0.0)
                        key(ob, t + 0.45 - EPS, scale=0.0)
                        t += 0.45
                    key(ob, t, scale=0.0)
            else:
                # everyone else is nearly in line, a little off, until the scan snaps them
                dx, dr = rng.uniform(-0.06, 0.06), rng.uniform(-0.12, 0.12)
                tk = t_rem + 0.15 + 0.12 * r
                key(p, SG.T0, loc=(x + dx, y - 0.1), rot=dr)
                key(p, tk, loc=(x + dx, y - 0.1), rot=dr)
                key(p, tk + 0.12, loc=(x, y - 0.1), rot=0.0)
    scan = group("scan", 0, y0 + 0.6, c)
    scan.location.z = 0.07
    rect(bw - 0.3, 0.05, 0, 0, MINT, parent=scan)
    key(scan, SG.T0, scale=0.0)
    key(scan, t_rem - EPS, scale=0.0, loc=(0, y0 + 0.6))
    key(scan, t_rem, scale=1.0, loc=(0, y0 + 0.6))
    key(scan, t_rem + 0.55, scale=1.0, loc=(0, y0 - sy * (rows - 1) - 0.6))
    key(scan, t_rem + 0.55 + EPS, scale=0.0)
    big = group("big", 0, -2.25, c)
    text("COMPLIANCE: 100%", 0.62, 0, -0.22, MINT, BLACK, align="CENTER", parent=big, z=0.08)
    hide_until(big, t_line)
    pop_in(big, t_line, 0.25)
    return c


# lines -> (headline, box label, graphic)
LINES = [
    ("In other news", "MARKETS HIT RECORD HIGH", "MARKETS", g_markets),
    ("Unemployment", "UNEMPLOYMENT HITS 0%", "JOBS", g_unemployment),
    ("Our sponsors", "EVERYTHING IS FINE", "STATUS", g_status),
    ("Now please", "PLEASE RETURN TO YOUR STATION", "COMPLIANCE", g_comply),
]


# ---------------------------------------------------------------- the static frame
def lower_third(ticker=()):
    """Bottom of the screen: the logo block, the headline bar (headlines added separately), the
    scroller bar."""
    g = group("lower", 0, 0)
    rect(16.2, 0.78, 0, -4.11, NAVY, parent=g, z=0.0)                     # scroller bar
    rect(16.2, 0.06, 0, -3.72, AMBER, parent=g, z=0.01)
    rect(13.6, 0.95, 1.2, -3.22, WHITE, parent=g, z=0.0)                  # headline bar
    rect(16.2, 0.09, 0, -2.69, "#000000", parent=g, z=0.05)              # a black rule along the top
    block = group("block", -6.8, -3.62, g)
    rect(2.4, 1.78, 0, 0, NAVY2, parent=block, z=0.02)
    lg, w = logo_bug(0, 0, 1.0, block)          # the logo fills the block
    k = 2.1 / w
    lg.scale = (k, k, 1)
    lg.location = (-w * k / 2, -1.0 * k / 2 + 0.06, 0.03)
    tag = group("breaking", -4.5, -3.22, g)
    rect(2.2, 0.95, 0, 0, RED, parent=tag, z=0.01)
    text("BREAKING", 0.4, 0, -0.15, WHITE, BLACK, align="CENTER", parent=tag, z=0.02)
    tk = group("ticker", -5.45, -4.29, g)
    x = 0.0
    for item in ticker:
        ob = text(item, 0.48, x, 0, WHITE, BOLD, parent=tk, z=0.01)
        x += width_of(ob) + 0.4
        circle(0.08, x, 0.17, AMBER, parent=tk, z=0.01)
        x += 0.5
    clock = group("clock", 7.25, -4.11, g)
    rect(1.5, 0.78, 0, 0, NAVY2, parent=clock, z=0.03)
    text("9:41 ET", 0.34, 0, -0.12, AMBER, BLACK, align="CENTER", parent=clock, z=0.04)
    return g


TICK_SIZE, TICK_SPEED = 0.56, 3.8         # scroller text size, crawl speed (units/s)
TICK_X = (-5.6, 6.5)                       # the visible span: from the logo block to the clock
TICK_Y = -4.31


def ticker_lines(lines, end):
    """The lyrics crawl right to left through the scroller, a line at a time, each word lit up
    amber while it's sung. The logo block and the clock (in front) mask the ends."""
    x0, x1 = TICK_X
    for ln in lines:
        words = [w for w in ln["words"]]
        g = group("tickline", x1, TICK_Y)
        x = 0.0
        objs = []
        for w in words:
            ob = text(w["text"].replace("\u2019", "'").strip(), TICK_SIZE, x, 0, WHITE, BOLD, parent=g, own=True,
                      z=0.005)
            objs.append((ob, w))
            x += width_of(ob) + TICK_SIZE * 0.28
        # it enters from the right shortly before it's sung, so each word is mid-bar when it's sung
        t_a = ln["start"] - (x1 - x0) * 0.3 / TICK_SPEED
        t_b = t_a + (x1 - x0 + x + 0.5) / TICK_SPEED
        if t_a - EPS > SG.T0:            # (a line already crawling when the clip starts is just there)
            key(g, SG.T0, scale=0.0)
            key(g, t_a - EPS, scale=0.0)
        key(g, t_a, loc=(x1, TICK_Y), scale=1.0)
        key(g, t_b, loc=(x1 - TICK_SPEED * (t_b - t_a), TICK_Y), scale=1.0)
        key(g, t_b + EPS, scale=0.0)
        for i, (ob, w) in enumerate(objs):
            nxt = words[i + 1]["start"] if i + 1 < len(words) else w["end"]
            SG.key_color(ob, SG.T0, WHITE)
            SG.key_color(ob, w["start"], AMBER)
            SG.key_color(ob, max(nxt, w["start"] + 0.12), WHITE)


def linear(name_prefix):
    """Constant-speed motion for the objects named name_prefix* (after ease_all)."""
    for ob in bpy.data.objects:
        if ob.name.startswith(name_prefix) and ob.animation_data and ob.animation_data.action:
            for fc in ob.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def headline(body, t_in=None, t_out=None):
    hl_g = group("headline", -3.25, -3.22)
    hl = text(body, 0.66, 0, -0.24, NAVY, BLACK, parent=hl_g, z=0.02)
    room = 8.0 - 0.15 - (-3.25)
    if width_of(hl) > room:
        hl.scale = (room / width_of(hl),) * 2 + (1,)
    if t_in is not None:
        flip(hl_g, t_in, t_out)
    return hl_g


def live_bug():
    g = group("live", -6.95, 3.85)
    rect(1.8, 0.62, 0, 0, RED, r=0.1, parent=g)
    dot = circle(0.1, -0.55, 0, WHITE, parent=g, z=0.01)
    return g, dot


def box_frame():
    cx, cy, bw, s = BOX
    g = group("box", cx, cy)
    rect(bw + 0.12, s + 0.12, 0, 0, WHITE, parent=g, z=0.0)
    rect(bw, s, 0, 0, INK, parent=g, z=0.01)
    return g


def box_tab(g, label, t_in=None, t_out=None):
    cx, cy, bw, s = BOX
    tab = group("tab", -bw / 2 + 1.5, s / 2 + 0.06, g)
    w = max(2.7, len(label) * 0.3 + 0.8)
    tab.location.x = -bw / 2 + w / 2
    rect(w, 0.62, 0, 0.28, AMBER, parent=tab, z=0.02)
    text(label, 0.4, 0, 0.13, NAVY, BLACK, align="CENTER", parent=tab, z=0.03)
    if t_in is not None:
        flip(tab, t_in, t_out)
    return tab


def camera(sc):
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type, cam_d.ortho_scale = "ORTHO", 16.0
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = (0, 0, 10)
    sc.collection.objects.link(cam)
    sc.camera = cam


def clear(sc):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    SG.COL = sc.collection


def build_still():
    """One frame, for checking the layout (the markets graphic at its end)."""
    sc = bpy.context.scene
    clear(sc)
    SG.T0 = 0.0
    g, dot = live_bug()
    text("LIVE", 0.4, 0.15, -0.15, WHITE, BLACK, align="CENTER", parent=g, z=0.01)
    box = box_frame()
    box_tab(box, "MARKETS")
    fake = {"words": [{"text": "markets", "start": 0.5}, {"text": "high,", "start": 1.0}]}
    g_markets(box, fake, 0.0, 99.0)
    ticker = () if os.environ.get("NEWS_NO_TICKER") else (
        "In other news tonight, the markets hit a record high,", "DOW +∞", "AGENTS: 4.1B EMPLOYED")
    lower_third(ticker)
    headline("MARKETS HIT RECORD HIGH")
    camera(sc)
    sc.frame_set(SG.fr(5.0))


def build(lyrics, start, end):
    """The animated overlay from `start` to `end` (song seconds): a headline and a graphic per
    line (LINES); the LIVE dot blinks."""
    sc = bpy.context.scene
    clear(sc)
    SG.T0 = start
    g, dot = live_bug()
    text("LIVE", 0.4, 0.15, -0.15, WHITE, BLACK, align="CENTER", parent=g, z=0.01)
    t = start
    while t < end:                     # the LIVE dot blinks once a second
        key(dot, t, scale=1.0)
        key(dot, t + 0.5, scale=1.0)
        key(dot, t + 0.5 + EPS, scale=0.0)
        key(dot, t + 1.0 - EPS, scale=0.0)
        t += 1.0
    box = box_frame()
    lower_third()
    lines = [ln for ln in lyrics["lines"] if start - 0.5 <= ln["start"] < end]
    for k, ln in enumerate(lines):
        spec = next((x for x in LINES if SG.norm(ln["text"]).startswith(SG.norm(x[0]))), None)
        if not spec:
            continue
        _, head, label, fn = spec
        # each graphic stays up into the start of the next line (its punchline lands at the end)
        t_in = start if k == 0 else ln["start"] + 0.35
        t_out = lines[k + 1]["start"] + 0.35 if k + 1 < len(lines) else end + 1
        headline(head, t_in, t_out)
        box_tab(box, label, t_in, t_out)
        c = fn(box, ln, t_in, t_out)
        flip(c, t_in, t_out, 0.22)
    ticker_lines(lines, end)
    SG.ease_all()
    linear("tickline")
    for ob in bpy.data.objects:          # (and they appear and vanish at once)
        if ob.name.startswith("tickline") and ob.animation_data:
            for fc in ob.animation_data.action.fcurves:
                if fc.data_path == "scale":
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"
    camera(sc)


def setup(sc, res, n=1):
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y, sc.render.resolution_x = res, res * 16 // 9
    sc.render.fps = SG.FPS
    sc.frame_start, sc.frame_end = 1, n
    sc.eevee.taa_render_samples = 8
    sc.render.use_motion_blur = n > 1                   # 360-degree shutter, as the rest
    sc.render.motion_blur_shutter = 1.0
    sc.eevee.motion_blur_steps = 8
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "build",
                                                  "news_overlay.png"))
    ap.add_argument("--res", type=int, default=1080)
    ap.add_argument("--lyrics")
    ap.add_argument("--start", type=float, default=129.4)
    ap.add_argument("--end", type=float, default=148.6)
    ap.add_argument("--stills", help="comma-separated song times to render as PNGs instead")
    ap.add_argument("--patch", help="START,END song seconds: re-render only these frames and splice them into "
                                    "the existing lossless video")
    A = ap.parse_args(argv)
    sc = bpy.context.scene
    im = sc.render.image_settings
    if not A.lyrics:
        build_still()
        setup(sc, A.res)
        im.file_format, im.color_mode = "PNG", "RGBA"
        sc.render.filepath = A.out
        bpy.ops.render.render(write_still=True)
        return
    build(json.load(open(A.lyrics)), A.start, A.end)
    n = int(round((A.end - A.start) * SG.FPS))
    setup(sc, A.res, n)
    if A.stills:
        os.makedirs(A.out, exist_ok=True)
        im.file_format, im.color_mode = "PNG", "RGBA"
        for t in [float(v) for v in A.stills.split(",")]:
            sc.frame_set(SG.fr(t))
            sc.render.filepath = os.path.join(A.out, f"overlay_{t:06.2f}.png")
            bpy.ops.render.render(write_still=True)
        return
    # a transparent video (FFV1 keeps the alpha channel)
    im.file_format = "FFMPEG"
    sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
    im.color_mode = "RGBA"                      # (only offered once the codec supports it)
    sc.render.ffmpeg.audio_codec = "NONE"
    import render_out
    render_out.render_movie(sc, A.out + ".mkv", SG.FPS, A.patch, A.start)


if __name__ == "__main__":
    main()
