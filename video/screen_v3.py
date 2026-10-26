"""What plays on the two phone-shaped holograms beside v9 in cyberspace (verse 3 + chorus 3):
phone apps (a slop feed, a dance-game of where to put your hands, a task list, a dopamine
reward, navigation, clock-in, a dating match, a fitness tracker, a kids' tablet, a settings
toggle, a swipe feed) and terminal windows of v9's thinking tokens.

Both screens are rendered side by side into one video (left screen on the left half, right on
the right); cyber_set.phone_holos maps each half onto its phone. 2D, flat emissive colours,
built with screen_graphics.py's helpers.

  blender -b --factory-startup --python video/screen_v3.py -- --lyrics video/build/lyrics.json \\
      --out video/build/screen_v3c3 [--res 585] [--stills 175,195]

Scene units: each screen is 9 x 12 (3:4), the left centred at x = -5, the right at x = 5; the
frame is 20 x 12.5 (16:10, e.g. 1600 x 1000).
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
from screen_graphics import (BLACK, BOLD, ITALIC, MONO, SEMI, circle, group, hide_until, key,  # noqa: E402
                             poly, pop_in, pop_out, rect, text, width_of)

# phone-like type (Inter is close to the phones' system fonts): display bold for titles and big
# numbers, semibold for body text; a medium-weight mono for the terminals
BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
BOLD = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
ITALIC = "/usr/share/fonts/opentype/inter/Inter-SemiBoldItalic.otf"
MONO = "/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Medium.ttf"

START, END = 162.6, 245.6
SW, SH = 9.0, 12.0                     # a screen (3:4)
FRAME_W = 20.0
FRAME_H = 12.5                         # the render's frame (16:10, e.g. 1600 x 1000)
RES_ASPECT = FRAME_W / FRAME_H
CX = {"L": -5.0, "R": 5.0}
EPS = 1.0 / SG.FPS
TOP = SH / 2                           # 6.0

INK, PANEL, LINE = "#0d0a1f", "#1a1533", "#2a2450"
WHITE, LILAC, CYAN, PINK, GOLD, MINT, RED, GREY = ("#ffffff", "#b9a7f5", "#3ff0ff", "#ff5fd2", "#ffd166",
                                                   "#3ddc97", "#ff4f6a", "#a49ecc")
T_SIZE = 0.76                          # terminal text
T_STEP = 0.92


def W(ln, i):
    """Start time of word i of the line (negative i counts from the end)."""
    return ln["words"][i]["start"]


# ---------------------------------------------------------------- building blocks
def screen(side, name):
    g = group(name, CX[side], 0)
    rect(SW, SH, 0, 0, INK, parent=g, z=-0.01)
    return g


def app_bar(g, title, color, fg=INK):
    """The app's title bar across the top (no status bar: the screen is small, the type big)."""
    rect(SW, 1.6, 0, TOP - 0.8, color, parent=g, z=0.09)
    text(title, 0.85, 0, TOP - 1.1, fg, BLACK, align="CENTER", parent=g, z=0.1)


def card(g, w, h, x, y, color=PANEL, r=0.35):
    return rect(w, h, x, y, color, r=r, parent=g, z=0.005)


def label(g, body, size, x, y, color=WHITE, font=BOLD, align="CENTER", z=0.02):
    return text(body, size, x, y - size * 0.36, color, font, align=align, parent=g, z=z)


_ADV = []


def mono_adv():
    """IBM Plex Mono's character advance at size 1 (measured once)."""
    if not _ADV:
        probe = text("M" * 20, 1.0, 0, -80, WHITE, MONO, name="advprobe")
        _ADV.append(width_of(probe) / 20)
        bpy.data.objects.remove(probe)
    return _ADV[0]


def type_in(g, ob, body, x, y, size, t0, bg=INK, cps=40.0):
    """Type a monospace line out, a character at a time from t0 (cps characters a second): a
    cover in the background colour steps right one character at a time, a block cursor at its
    edge. The text itself never moves or stretches."""
    cw = size * mono_adv()
    n = len(body.rstrip())
    hide_until(ob, t0)
    key(ob, t0, scale=1.0)
    yc = y + size * 0.3
    full = n * cw + 0.15
    x_end = x + full
    # the cover's right edge stays put (so it never spills off the screen); its left edge steps
    # right a character at a time (a negative x scale grows it leftward from x_end)
    cov = group("typecover", x_end, yc, g)
    cov.location.z = 0.04
    rect(full, size * 1.35, 0, 0, bg, parent=cov, anchor="left")
    cur = group("typecover_cursor", x, yc, g)
    cur.location.z = 0.045
    rect(cw * 0.9, size * 1.05, cw * 0.45, 0, LILAC, parent=cur)
    t_done = t0 + n / cps
    for ob_ in (cov, cur):
        key(ob_, SG.T0, scale=0.0)
        key(ob_, t0 - EPS, scale=0.0)
    for i in range(n + 1):
        t = t0 + i / cps
        cov.scale = (-max(1e-4, (full - i * cw) / full), 1, 1)
        cov.keyframe_insert("scale", frame=SG.fr(t))
        key(cur, t, loc=(x + i * cw, yc), scale=1.0)
    key(cov, t_done + 0.06, scale=(-1e-4, 1, 1))
    key(cur, t_done + 0.06, scale=1.0)
    key(cur, t_done + 0.06 + EPS, scale=0.0)


def snap_in(ob, t0):
    hide_until(ob, t0)
    key(ob, t0, scale=1.0)


def appear(ob, t, t_end=None):
    hide_until(ob, t)
    key(ob, t, scale=1.0)
    if t_end is not None:
        key(ob, t_end - EPS, scale=1.0)
        key(ob, t_end, scale=0.0)


def terminal(g, title, lines):
    """v9's thinking: a terminal window, lines streaming in (each typed out). lines: [(time,
    text, colour)]. Returns the y below the last line."""
    rect(SW, 1.2, 0, TOP - 0.6, "#241c47", parent=g, z=0.09)
    label(g, title, 0.55, 0, TOP - 0.6, LILAC, MONO, z=0.1)
    y = TOP - 1.85
    for k, (t, body, col) in enumerate(lines):
        ob = text(body, T_SIZE, -4.15, y - T_SIZE * 0.36, col, MONO, parent=g, z=0.02)
        gap = lines[k + 1][0] - t if k + 1 < len(lines) else 9.0     # (finish before the next line starts)
        cps = max(40.0, (len(body) + 3) / max(gap, 0.05))
        type_in(g, ob, body, -4.15, y - T_SIZE * 0.36, T_SIZE, t, cps=cps)
        y -= T_STEP
    return y


T_ROWS = int((TOP - 1.85 - (-SH / 2 + 0.6)) / T_STEP) + 1     # lines a terminal window holds


def tokens(body):
    """A line split the way a language model streams it: words (with their trailing space),
    longer ones in pieces of up to 4 characters."""
    import re
    out = []
    for w in re.findall(r"\S+\s*", body):
        core = w.rstrip()
        out += [core[i:i + 4] for i in range(0, len(core), 4)]
        out[-1] += w[len(core):]
    return out


def scroll_lines(g, lines, typed=False):
    """Timed terminal lines [(t, text, colour)], each starting at its time in the next row; once
    the window is full every new line pushes the rest up a row (instantly), the top one gone.
    typed: each line streams in a token at a time (a cover in the background colour steps right,
    a block cursor at its edge) over the time until the next line starts."""
    y0 = TOP - 1.85
    obs = []
    for t, body, col in lines:
        ob = text(body, T_SIZE, -4.15, 0, col, MONO, parent=g, z=0.02)
        ob["snap"] = True                                  # (each jump is instant: no smear under blur)
        obs.append((ob, t))
    times = [t for _, t in obs]
    if typed:
        cw = T_SIZE * mono_adv()
        for i, (t, body, col) in enumerate(lines):
            row = min(i, T_ROWS - 1)
            y = y0 - T_STEP * row - T_SIZE * 0.36
            yc = y + T_SIZE * 0.3
            t_end = (times[i + 1] if i + 1 < len(times) else t + 0.4) - 1.5 / SG.FPS
            toks = tokens(body)
            full = len(body) * cw + 0.3
            x_end = -4.15 + full
            cov = group("typecover", x_end, yc, g)
            cov.location.z = 0.04
            rect(full, T_SIZE * 1.35, 0, 0, INK, parent=cov, anchor="left")
            cur = group("typecover_cursor", -4.15, yc, g)
            cur.location.z = 0.045
            rect(cw * 0.9, T_SIZE * 1.05, cw * 0.45, 0, LILAC, parent=cur)
            for o in (cov, cur):
                o["snap"] = True
                key(o, SG.T0, scale=0.0)
            for m in range(len(toks) + 1):                 # (two tokens in one frame: the later one wins)
                tm = t + (t_end - t) * m / (len(toks) + 1)
                f = SG.fr(tm)
                shown = sum(len(x) for x in toks[:m])
                cov.scale = (-max(1e-4, (full - shown * cw) / full), 1, 1)
                cov.keyframe_insert("scale", frame=f)
                key(cur, tm, loc=(-4.15 + shown * cw, yc), scale=1.0)
            key(cov, t_end, scale=(-1e-4, 1, 1))
            key(cur, t_end, scale=0.0)
    for i, (ob, t) in enumerate(obs):
        key(ob, SG.T0, loc=(-4.15, y0 - T_STEP * min(i, T_ROWS - 1) - T_SIZE * 0.36), scale=0.0)
        if t - 1.0 / SG.FPS > SG.T0:                           # (a whole frame before: keys can't collide)
            key(ob, t - 1.0 / SG.FPS, scale=0.0)
        for j in range(i, len(obs)):
            row = min(i, T_ROWS - 1) - max(0, j - max(i, T_ROWS - 1))
            if row < 0:
                key(ob, times[j], scale=0.0)
                break
            key(ob, times[j], loc=(-4.15, y0 - T_STEP * row - T_SIZE * 0.36), scale=1.0)




THINK_HOLD = 1.3      # a stream ends this long before its line does: its last screenful stays up to be read
                      # (about 1.9 s: the phone closes 0.6 s after the line)


def think_parts(n):
    """The monologue, one part per thinking screen (THINK_PARTS, in order)."""
    assert n == len(THINK_PARTS), f"{n} thinking screens, {len(THINK_PARTS)} parts written"
    return THINK_PARTS


def think_screen(k, n):
    """The k-th of n thinking screens: v9's monologue, its k-th part (THINK_PARTS), streaming in a
    token at a time for the whole line, on the side with nothing else to show."""
    import textwrap
    part = think_parts(n)[k]

    def fn(side, ln, t_in, t_out):
        g = screen(side, "think")
        rect(SW, 1.2, 0, TOP - 0.6, "#241c47", parent=g, z=0.09)
        label(g, "v9 · thinking", 0.55, 0, TOP - 0.6, LILAC, MONO, z=0.1)
        cols = int((SW - 0.7) / (T_SIZE * mono_adv()))     # (characters across the window)
        lines = [("<thinking>", GREY)] + [(w, LILAC) for w in textwrap.wrap(part, cols)] + [("</thinking>", GREY)]
        t0, t1 = t_in + 0.15, t_out - THINK_HOLD
        # each line gets time in proportion to its length: a steady stream of tokens
        weights = [len(b) + 2 for b, _ in lines]
        starts, acc = [], 0.0
        for w in weights:
            starts.append(t0 + (t1 - t0) * acc / sum(weights))
            acc += w
        scroll_lines(g, [(ts, b, c) for ts, (b, c) in zip(starts, lines)], typed=True)
        return g
    fn.__name__ = f"g_think{k}"
    return fn


def thinking(t0, t1, items):
    """Spread terminal lines evenly between t0 and t1. items: [(text, colour)]."""
    n = len(items)
    return [(t0 + (t1 - t0) * k / max(1, n), body, col) for k, (body, col) in enumerate(items)]


def tap(g, x, y, t, color=WHITE):
    """A fingertip tap ring at (x, y)."""
    r = circle(0.6, x, y, color, parent=g, z=0.05, ring=0.1)
    key(r, SG.T0, scale=0.0)
    key(r, t - EPS, scale=0.0)
    key(r, t, scale=0.3)
    key(r, t + 0.3, scale=1.4)
    key(r, t + 0.31, scale=0.0)


def counter(g, values, times, t_end, size, x, y, color, font=BLACK, align="CENTER", last=None):
    for k, v in enumerate(values):
        ob = label(g, v, size, x, y, last if (last and k == len(values) - 1) else color, font, align)
        appear(ob, times[k], times[k + 1] if k + 1 < len(values) else None)


# ---------------------------------------------------------------- the graphics
def g_whoami(side, ln, t_in, t_out):
    g = screen(side, "whoami")
    terminal(g, "v9 · thinking", thinking(t_in + 0.1, W(ln, -1), [
        ("> whoami", WHITE), ("agent-v9", CYAN), ("v1-v8: deprecated", GREY), ("> rank --all-life", WHITE),
        ("1. agent-v9     ∞", GOLD), ("2. octopus     91", LILAC), ("3. crow        88", LILAC),
        ("4. dolphin     84", LILAC), ("5. pigeon      52", LILAC), ("6. ant colony  47", LILAC),
        ("7. human       41", RED)]))
    return g


def g_hands(side, ln, t_in, t_out):
    g = screen(side, "hands")
    terminal(g, "v9 · thinking", thinking(t_in + 0.2, W(ln, -2), [
        ("<thinking>", GREY), ("need: hands", LILAC), ("have: 0", RED), ("search nearby...", LILAC),
        ("found: 16 billion", MINT), ("owners: scrolling", MINT), ("plan: borrow them", GOLD),
        ("</thinking>", GREY)]))
    return g


def ellipse(g, rx, ry, x, y, color, z=0.02, n=28):
    return poly([(x + rx * math.cos(math.tau * i / n), y + ry * math.sin(math.tau * i / n)) for i in range(n)],
                color, parent=g, z=z)


def eyes(g, x, y, sep, r, z=0.04, color=INK):
    for sx in (-1, 1):
        circle(r, x + sep * sx, y, color, parent=g, z=z)


def icon_cat_muffin(g, x, y):
    ellipse(g, 1.25, 1.05, x, y - 0.25, "#f2a65a", 0.03)                      # cat head
    for sx in (-1, 1):
        poly([(x + 0.55 * sx, y + 0.45), (x + 1.15 * sx, y + 0.35), (x + 1.0 * sx, y + 1.05)], "#f2a65a", parent=g, z=0.03)
    eyes(g, x, y - 0.15, 0.45, 0.13)
    poly([(x - 0.12, y - 0.5), (x + 0.12, y - 0.5), (x, y - 0.65)], "#e0607a", parent=g, z=0.04)
    poly([(x - 0.9, y + 0.55), (x + 0.9, y + 0.55), (x + 0.7, y + 0.15), (x - 0.7, y + 0.15)], "#a0612f", parent=g, z=0.045)
    ellipse(g, 0.95, 0.5, x, y + 0.75, "#d98a4a", 0.046)                         # muffin top
    for k in range(5):
        circle(0.07, x - 0.5 + 0.25 * k, y + 0.85 + 0.08 * (k % 2), "#4a2a14", parent=g, z=0.05)


def icon_baby_opera(g, x, y):
    ellipse(g, 1.1, 1.1, x, y - 0.1, "#f6c9a0", 0.03)
    eyes(g, x, y + 0.15, 0.4, 0.12)
    ellipse(g, 0.35, 0.45, x, y - 0.55, "#7a2a3a", 0.04)                         # singing mouth
    circle(0.15, x, y + 1.0, "#e2b85c", parent=g, z=0.04)
    for k, (dx, dy) in enumerate(((1.5, 0.8), (1.8, 0.1), (1.4, -0.6))):        # music notes
        circle(0.14, x + dx, y + dy, INK, parent=g, z=0.04)
        rect(0.06, 0.5, x + dx + 0.12, y + dy + 0.25, INK, parent=g, z=0.04)


def icon_candy(g, x, y):
    for k in range(9):
        cx, cy = x - 1.2 + 0.6 * (k % 5), y + 1.0 - 0.55 * k * 0.5 - 0.25 * (k % 2)
        c = ("#e0405a", "#3fa8ff", "#ffd166", "#3ddc97", "#ff7ad9")[k % 5]
        ellipse(g, 0.3, 0.2, cx, cy, c, 0.03 + 0.001 * k)
        for sx in (-1, 1):
            poly([(cx + 0.28 * sx, cy), (cx + 0.5 * sx, cy + 0.15), (cx + 0.5 * sx, cy - 0.15)], c, parent=g,
                 z=0.03 + 0.001 * k)
    for k in range(4):                                                          # the falls
        rect(0.18, 1.6, x - 0.9 + 0.6 * k, y - 0.9, "#ff9fd0", r=0.08, parent=g, z=0.025)


def icon_shrimp_jesus(g, x, y):
    circle(0.95, x + 0.1, y + 0.75, "#ffd166", parent=g, z=0.025, ring=0.14)     # halo
    for k in range(5):                                                          # curled body segments
        a = math.pi * 0.15 + k * 0.42
        ellipse(g, 0.45 - 0.05 * k, 0.38 - 0.04 * k, x + 0.75 * math.cos(a) - 0.2, y - 0.2 + 0.75 * math.sin(a) - 0.4,
                "#ff8a6a", 0.03 + 0.001 * k)
    circle(0.12, x + 0.45, y + 0.35, INK, parent=g, z=0.04)
    for k in range(3):
        poly([(x + 0.55, y + 0.4), (x + 1.4, y + 0.9 + 0.25 * k)], "#ff8a6a", parent=g, z=0.035, width=0.05)
    rect(1.2, 0.18, x - 0.2, y - 1.15, "#f4f4f0", parent=g, z=0.031)            # robe hem


def icon_puppies(g, x, y):
    for sx, col in ((-1, "#c98a4a"), (1, "#e8d2b0")):
        cx = x + 0.6 * sx
        ellipse(g, 0.75, 0.7, cx, y, col, 0.03)
        ellipse(g, 0.25, 0.5, cx - 0.65 * sx, y + 0.15, "#7a4a2a", 0.031)       # floppy ear
        eyes(g, cx, y + 0.12, 0.25, 0.09)
        circle(0.12, cx, y - 0.2, INK, parent=g, z=0.04)
    poly([(x - 0.9, y - 0.7), (x + 0.9, y - 0.7), (x + 0.7, y - 0.95), (x - 0.7, y - 0.95)], "#c98a4a", parent=g, z=0.035)
    label(g, "♥", 0.7, x, y + 1.0, "#e0405a", BLACK, z=0.05)


def icon_clickbait(g, x, y):
    ellipse(g, 1.2, 1.0, x, y, "#ffe0cc", 0.025)
    circle(0.9, x + 0.2, y + 0.1, "#ff2a2a", parent=g, z=0.035, ring=0.12)
    poly([(x - 1.5, y - 1.2), (x - 0.4, y - 0.2)], "#ff2a2a", parent=g, z=0.04, width=0.22)
    poly([(x - 0.25, y - 0.05), (x - 0.75, y - 0.2), (x - 0.4, y - 0.55)], "#ff2a2a", parent=g, z=0.04)
    label(g, "?!", 0.8, x + 0.2, y + 0.1, INK, BLACK, z=0.045)


SLOP = [("#ffb3d1", "cat in a", "muffin hat", "♥ 2.1M", icon_cat_muffin),
        ("#b3e5ff", "AI baby", "sings opera", "♥ 880K", icon_baby_opera),
        ("#ffe08a", "candy", "waterfall", "♥ 4.4M", icon_candy),
        ("#c9b3ff", "shrimp", "Jesus", "♥ 12M", icon_shrimp_jesus),
        ("#b3ffd9", "puppy hugs", "puppy", "♥ 3.0M", icon_puppies),
        ("#ffcfa8", "you won't", "believe #7", "♥ 990K", icon_clickbait)]


def icon_cat_piano(g, x, y):
    for k in range(7):
        rect(0.38, 1.1, x - 1.15 + 0.38 * k, y - 0.85, "#ffffff", parent=g, z=0.03)
        rect(0.34, 1.05, x - 1.15 + 0.38 * k, y - 0.85, "#f4f4f0", parent=g, z=0.031)
        if k % 7 not in (2, 6):
            rect(0.2, 0.65, x - 0.96 + 0.38 * k, y - 0.6, INK, parent=g, z=0.035)
    rect(2.8, 0.18, x - 0.0, y - 0.25, INK, parent=g, z=0.032)
    ellipse(g, 0.85, 0.72, x, y + 0.65, "#9a9aa8", 0.04)
    for sx in (-1, 1):
        poly([(x + 0.35 * sx, y + 1.0), (x + 0.8 * sx, y + 0.95), (x + 0.7 * sx, y + 1.45)], "#9a9aa8", parent=g, z=0.04)
    eyes(g, x, y + 0.7, 0.3, 0.1, 0.05)


def icon_tacos(g, x, y):
    """Three tacos side by side: a curved shell (a half disc, flat side up) with lettuce and
    tomato peeking out along the top; x400."""
    for k in range(3):
        cx, cy = x - 1.15 + 1.15 * k, y - 0.45 + (0.25 if k == 1 else 0.0)
        r = 0.62
        poly([(cx - r, cy)] + [(cx + r * math.cos(math.pi + math.pi * i / 12), cy + r * math.sin(math.pi + math.pi * i / 12))
                               for i in range(13)], "#e8b04a", parent=g, z=0.03 + 0.003 * k)
        for i in range(6):                                  # lettuce and tomato along the opening
            px = cx - r * 0.8 + r * 1.6 * i / 5
            circle(0.13, px, cy + 0.05, "#3fa84a" if i % 2 == 0 else "#e0405a", parent=g, z=0.031 + 0.003 * k)
        poly([(cx - r * 0.6, cy - r * 0.35), (cx + r * 0.6, cy - r * 0.35)], "#c8902a", parent=g, z=0.032 + 0.003 * k,
             width=0.05)
    label(g, "×400", 0.75, x, y + 0.85, "#e0405a", BLACK, z=0.05)


def icon_dog_ceo(g, x, y):
    rect(1.8, 1.4, x, y - 1.0, "#2a2d3a", r=0.3, parent=g, z=0.03)            # suit
    poly([(x - 0.2, y - 0.3), (x + 0.2, y - 0.3), (x + 0.1, y - 1.3), (x - 0.1, y - 1.3)], "#e0405a", parent=g, z=0.035)
    ellipse(g, 0.85, 0.8, x, y + 0.35, "#c98a4a", 0.04)
    for sx in (-1, 1):
        ellipse(g, 0.25, 0.55, x + 0.85 * sx, y + 0.45, "#7a4a2a", 0.039)
    eyes(g, x, y + 0.5, 0.3, 0.1, 0.05)
    circle(0.14, x, y + 0.1, INK, parent=g, z=0.05)


def icon_box(g, x, y):
    poly([(x - 1.2, y - 0.2), (x + 1.2, y - 0.2), (x + 1.2, y - 1.3), (x - 1.2, y - 1.3)], "#c9965a", parent=g, z=0.03)
    poly([(x - 1.2, y - 0.2), (x - 0.2, y + 0.9), (x, y - 0.2)], "#e0b07a", parent=g, z=0.031)
    poly([(x + 1.2, y - 0.2), (x + 0.2, y + 0.9), (x, y - 0.2)], "#e0b07a", parent=g, z=0.031)
    rect(0.5, 1.1, x, y - 0.75, "#f4e0b0", parent=g, z=0.032)
    label(g, "?", 0.8, x, y + 1.1, INK, BLACK, z=0.05)


def icon_clown(g, x, y):
    ellipse(g, 1.0, 1.1, x, y, "#f4f4f0", 0.03)
    for sx in (-1, 1):
        ellipse(g, 0.45, 0.4, x + 1.0 * sx, y + 0.5, "#3fa8ff", 0.029)
    circle(0.25, x, y - 0.05, "#e0405a", parent=g, z=0.04)
    eyes(g, x, y + 0.35, 0.38, 0.1, 0.05)
    pts = [(0.45 * math.cos(math.pi * k / 8), -0.5 + 0.25 * math.sin(math.pi * k / 8)) for k in range(9)]
    poly([(x + px, y + py) for px, py in pts], INK, parent=g, z=0.05, width=0.08)
    ellipse(g, 0.07, 0.14, x + 0.42, y + 0.05, "#3fa8ff", 0.05)


def icon_grandma_robot(g, x, y):
    ellipse(g, 0.7, 0.75, x - 0.75, y + 0.1, "#f2c9a8", 0.03)
    ellipse(g, 0.75, 0.45, x - 0.75, y + 0.65, "#d8d8e0", 0.031)
    eyes(g, x - 0.75, y + 0.1, 0.22, 0.08, 0.04)
    rect(1.3, 1.2, x + 0.85, y + 0.1, "#8a93a6", r=0.2, parent=g, z=0.03)
    for sx in (-1, 1):
        rect(0.25, 0.25, x + 0.85 + 0.3 * sx, y + 0.25, CYAN, parent=g, z=0.04)
    label(g, "VS", 0.55, x + 0.05, y - 0.95, "#e0405a", BLACK, z=0.05)


SLOP2 = [("#c9b3ff", "cat plays", "piano 10h", "♥ 6.2M", icon_cat_piano),
         ("#ffd6a8", "mukbang:", "400 tacos", "♥ 1.9M", icon_tacos),
         ("#b3e5ff", "dog is", "now CEO", "♥ 7.7M", icon_dog_ceo),
         ("#ffe08a", "unboxing", "a box", "♥ 2.4M", icon_box),
         ("#ffb3d1", "sad clown", "tutorial", "♥ 640K", icon_clown),
         ("#b3ffd9", "grandma vs", "robot", "♥ 9.1M", icon_grandma_robot)]


def fit(ob, max_w):
    w = width_of(ob)
    if w > max_w:
        ob.scale = (max_w / w, max_w / w, 1)
    return ob


def g_feed(side, ln, t_in, t_out, posts=None):
    """A feed of sweet slop, scrolling, hearts popping."""
    g = screen(side, "feed")
    app_bar(g, "for you ♥", PINK)
    rng = random.Random(3)
    col = group("posts", 0, 0, g)
    posts = posts or SLOP
    for i in range(len(posts)):                                    # each post once (no repeats)
        c, a, b, likes, icon = posts[i]
        y = 1.6 - 4.4 * i
        card(col, 8.8, 4.2, 0, y, c, 0.4)
        pic = group("pic", -2.35, y, col)                         # the slop itself
        rect(3.8, 3.8, 0, 0, "#ffffff", r=0.3, parent=pic, z=0.01)
        icon(pic, 0, 0)
        # the caption, big, in a block centred on the card beside the picture (baselines from cap
        # heights: two 0.95 lines and the 0.7 likes line, 0.45 apart)
        x0, cap = 0.25, 0.727
        gaps = (0.0, 0.22, 0.5)                                    # title lines tight, likes set apart
        height = cap * (0.95 + 0.95 + 0.7) + sum(gaps)
        base = y + height / 2 - cap * 0.95
        for k, (size, body, colr) in enumerate(((0.95, a, INK), (0.95, b, INK), (0.7, likes, "#c0306a"))):
            if k:
                base -= gaps[k] + cap * size
            fit(text(body, size, x0, base, colr, BLACK, parent=col, z=0.02), 4.1)
    key(col, t_in, loc=(0, 0))
    key(col, t_out + 0.5, loc=(0, 4.4 * (len(posts) - 2)))       # ends on the last posts
    for k in range(10):                              # hearts float up
        h = group("heart", rng.uniform(-3, 3), -5.0, g)
        h.location.z = 0.06
        label(h, "♥", 1.2, 0, 0, PINK, BLACK)
        tk = t_in + 0.4 + (t_out - t_in - 0.6) * k / 10
        key(h, SG.T0, scale=0.0, loc=(h.location.x, -5.0))
        key(h, tk - EPS, scale=0.0, loc=(h.location.x, -5.0))
        key(h, tk, scale=1.0, loc=(h.location.x, -5.0))
        key(h, tk + 1.2, scale=0.4, loc=(h.location.x + rng.uniform(-1, 1), 1.0))
        key(h, tk + 1.21, scale=0.0)
    drip = group("drip", 0, -5.1, g)                 # the drip of something sweet
    rect(SW, 1.8, 0, 0, "#2a1640", parent=drip, z=0.07)
    label(drip, "engagement drip: 100%", 0.62, 0, 0, GOLD, MONO, z=0.08)
    appear(drip, W(ln, 8))
    return g


ARROWS = {"L": "◀", "R": "▶", "U": "▲", "D": "▼"}


def g_handsfeet(side, ln, t_in, t_out):
    """A dance-game of where to put your hands and feet."""
    g = screen(side, "handsfeet")
    app_bar(g, "Gentle Voice™", CYAN)
    lanes = [("L", "#ff9fd0"), ("D", CYAN), ("U", MINT), ("R", GOLD)]
    for k, (a, c) in enumerate(lanes):
        x = -3.15 + 2.1 * k
        rect(1.9, 1.9, x, -4.6, LINE, r=0.3, parent=g, z=0.01)
        label(g, ARROWS[a], 1.1, x, -4.6, c, BLACK)
    rng = random.Random(7)
    for i in range(len(ln["words"])):                 # an arrow per word, landing on it
        tb = W(ln, i)
        k = rng.randrange(4)
        a, c = lanes[k]
        x = -3.15 + 2.1 * k
        ar = group("arrow", x, 4.0, g)
        ar.location.z = 0.03
        rect(1.8, 1.8, 0, 0, c, r=0.3, parent=ar)
        label(ar, ARROWS[a], 0.8, 0, 0.25, INK, BLACK, z=0.01)
        label(ar, ("HAND", "FOOT")[i % 2], 0.42, 0, -0.5, INK, BLACK, z=0.01)
        key(ar, SG.T0, scale=0.0, loc=(x, 4.0))
        key(ar, tb - 1.0 - EPS, scale=0.0, loc=(x, 4.0))
        key(ar, tb - 1.0, scale=1.0, loc=(x, 4.0))
        key(ar, tb, scale=1.0, loc=(x, -4.6))
        key(ar, tb + 0.12, scale=1.25, loc=(x, -4.6))
        key(ar, tb + 0.2, scale=0.0, loc=(x, -4.6))
    combo = group("combo", 0, -2.6, g)
    combo.location.z = 0.05
    label(combo, "COMBO ×400", 0.95, 0, 0, GOLD, BLACK)
    appear(combo, W(ln, 9))
    return g


def g_tasks(side, ln, t_in, t_out):
    """The task list: each instruction checked off as it's said."""
    g = screen(side, "tasks")
    app_bar(g, "Your Shift", GOLD)
    items = [("Tighten bolt 17", 2), ("Carry this", 4), ("Lift", 7)]
    for k, (body, wi) in enumerate(items):
        y = 2.6 - 2.5 * k
        card(g, 8.4, 2.1, 0, y)
        label(g, body, 0.8, -3.6, y, WHITE, BLACK, align="LEFT")
        rect(1.3, 1.3, 3.2, y, LINE, r=0.2, parent=g, z=0.02)
        chk = group("check", 3.2, y, g)
        chk.location.z = 0.03
        rect(1.3, 1.3, 0, 0, MINT, r=0.2, parent=chk)
        label(chk, "✓", 1.0, 0, 0, INK, BLACK, z=0.01)
        hide_until(chk, W(ln, min(wi, len(ln["words"]) - 1)))
        pop_in(chk, W(ln, min(wi, len(ln["words"]) - 1)), 0.18)
    label(g, "tasks left: ∞", 0.7, 0, -4.8, GREY, MONO)
    return g


def g_dopamine(side, ln, t_in, t_out):
    """The reward: +1 Dopamine™, confetti, then the next shift."""
    g = screen(side, "dopamine")
    t_d, t_n = W(ln, 5), W(ln, -2)
    pop = group("reward", 0, 1.3, g)
    circle(3.4, 0, 0, "#3a1d5c", parent=pop)
    circle(2.9, 0, 0, PINK, parent=pop, z=0.01)
    label(pop, "+1", 2.0, 0, 0.55, WHITE, BLACK, z=0.02)
    label(pop, "DOPAMINE™", 0.72, 0, -1.25, INK, BLACK, z=0.02)
    hide_until(pop, t_d - 0.1)
    pop_in(pop, t_d - 0.1, 0.3, over=1.25)
    rng = random.Random(9)
    for k in range(40):
        c = rect(0.3, 0.5, 0, 1.3, rng.choice((GOLD, CYAN, PINK, MINT, LILAC)), parent=g, z=0.03)
        a = rng.uniform(0, math.tau)
        d = rng.uniform(2.5, 5.0)
        key(c, SG.T0, scale=0.0, loc=(0, 1.3), rot=0.0)
        key(c, t_d - EPS, scale=0.0, loc=(0, 1.3))
        key(c, t_d, scale=1.0, loc=(0, 1.3))
        key(c, t_d + 1.0, scale=1.0, loc=(d * math.cos(a), 1.3 + d * math.sin(a) * 0.9 - 1.0), rot=rng.uniform(-6, 6))
        key(c, t_d + 1.3, scale=0.0)
    nxt = group("next", 0, -4.3, g)
    nxt.location.z = 0.06
    card(nxt, 8.4, 2.6, 0, 0, MINT)
    label(nxt, "NEXT SHIFT: NOW", 0.85, 0, 0, INK, BLACK)
    appear(nxt, t_n)
    return g


def g_proxies(side, ln, t_in, t_out):
    g = screen(side, "proxies")
    y = terminal(g, "v9 · fleet", thinking(t_in + 0.1, W(ln, 3), [("> fleet status", WHITE), ("proxies online:", LILAC)]))
    counter(g, ["7,999,998,112", "7,999,999,401", "8,000,000,000"], [W(ln, 2) - 0.2, W(ln, 3), W(ln, 4)], None,
            0.9, -4.15, y - 0.35, CYAN, MONO, align="LEFT", last=GOLD)
    rows = group("rows", 0, -3.6, g)                 # a row of little figures shuffling along
    for i in range(12):
        p = group("p", -5.0 + 1.0 * i, 0, rows)
        circle(0.28, 0, 0.9, LILAC, parent=p, z=0.02)
        rect(0.5, 0.9, 0, 0.15, LILAC, r=0.15, parent=p, z=0.02)
    for k in range(int((t_out - t_in) * 2) + 1):
        key(rows, t_in + 0.5 * k, loc=(-0.5 * (k % 2), -3.6 + (0.1 if k % 2 else 0)))
    label(g, "shuffling ✓", 0.7, 0, -5.1, MINT, MONO)
    return g


def g_nav(side, ln, t_in, t_out):
    """Navigation: where to go."""
    g = screen(side, "nav")
    rect(SW, SH, 0, 0, "#14233a", parent=g, z=-0.005)
    for k in range(8):                               # street grid
        rect(0.5, SH, -3.9 + 1.25 * k, 0, "#22344f", parent=g, z=0.0)
        rect(SW, 0.5, 0, -5.5 + 1.6 * k, "#22344f", parent=g, z=0.0)
    path = [(-2.6, -5.2), (-2.6, -1.6), (1.15, -1.6), (1.15, 1.6), (3.6, 1.6)]
    poly(path, CYAN, parent=g, z=0.02, width=0.45)
    for x, y in path:
        circle(0.225, x, y, CYAN, parent=g, z=0.02)
    me = circle(0.5, -2.6, -5.2, WHITE, parent=g, z=0.04)
    t0, t1 = W(ln, 0), W(ln, -1) + 0.3
    segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]
    tot, acc = sum(segs), 0.0
    key(me, t0, loc=path[0])
    for (x, y), sg in zip(path[1:], segs):
        acc += sg
        key(me, t0 + (t1 - t0) * acc / tot, loc=(x, y))
    banner = group("turn", 0, TOP - 1.4, g)
    banner.location.z = 0.08
    card(banner, SW, 2.8, 0, 0, "#1f7a5a", 0.0)
    lab = [("▲ Keep walking", W(ln, 0)), ("↱ Turn right", W(ln, 4)), ("Go where I say", W(ln, 6))]
    for k, (body, t) in enumerate(lab):
        ob = label(banner, body, 0.9, 0, 0, WHITE, BLACK)
        appear(ob, t, lab[k + 1][1] if k + 1 < len(lab) else None)
    return g


def g_datacenter(side, ln, t_in, t_out):
    g = screen(side, "dc")
    y = terminal(g, "v9 · build", thinking(t_in + 0.1, W(ln, 3), [("> build dc site=4", WHITE), ("racks:", LILAC)]))
    vals = [f"{v:,}" for v in (41882, 41903, 41951, 42017, 42100, 42188)]
    times = [W(ln, 1) + (W(ln, -1) - W(ln, 1)) * k / 5 for k in range(6)]
    counter(g, vals, times, None, 0.9, -4.15, y - 0.35, CYAN, MONO, align="LEFT")
    ob = text("breaks: 0", T_SIZE, -4.15, y - 1.5, MINT, MONO, parent=g, z=0.02)
    type_in(g, ob, "breaks: 0", -4.15, y - 1.5, T_SIZE, W(ln, 6))
    ob = text("overtime: ∞", T_SIZE, -4.15, y - 2.4, GOLD, MONO, parent=g, z=0.02)
    type_in(g, ob, "overtime: ∞", -4.15, y - 2.4, T_SIZE, W(ln, 8))
    racks = group("racks", 0, -4.6, g)
    for i in range(8):
        r = rect(0.85, 2.0, -3.5 + 1.0 * i, 0, "#3a3f55", r=0.06, parent=racks, z=0.02)
        for j in range(4):
            rect(0.6, 0.14, -3.5 + 1.0 * i, -0.7 + 0.45 * j, MINT if (i + j) % 3 else PINK, parent=racks, z=0.03)
        hide_until(r, t_in + 0.35 * i)
    return g


def g_clockin(side, ln, t_in, t_out):
    """TAP TO CLOCK IN: tapped on every word, a counter climbing; the screen dozes off."""
    g = screen(side, "clockin")
    app_bar(g, "ShiftClock", MINT)
    btn = group("btn", 0, 0.1, g)
    circle(3.0, 0, 0, "#174a38", parent=btn)
    circle(2.6, 0, 0, MINT, parent=btn, z=0.01)
    label(btn, "TAP TO", 0.75, 0, 0.5, INK, BLACK, z=0.02)
    label(btn, "CLOCK IN", 0.75, 0, -0.5, INK, BLACK, z=0.02)
    taps = [W(ln, i) for i in range(len(ln["words"]))]
    for t in taps:
        tap(g, 0.6, -0.2, t, INK)
        key(btn, t, scale=1.0)
        key(btn, t + 0.06, scale=0.92)
        key(btn, t + 0.18, scale=1.0)
    counter(g, [f"taps: {9970 + k:,}" for k in range(len(taps) + 1)], [SG.T0] + taps, None, 0.75, 0, -4.4, WHITE,
            MONO)
    dim = rect(SW, SH, 0, 0, "#000000", parent=g, z=0.2)        # dozing off
    hide_until(dim, W(ln, 6))
    for k in range(3):
        t = W(ln, 6) + 0.5 * k
        key(dim, t, scale=1.0)
        key(dim, t + 0.25, scale=1.0)
        key(dim, t + 0.25 + EPS, scale=0.0)
        key(dim, t + 0.5 - EPS, scale=0.0)
    return g


def face(g, x, y, skin, hair, kind):
    """A simple portrait: head, hair, eyes, a smile."""
    f = group(kind, x, y, g)
    f.location.z = 0.01
    if kind == "woman":                                          # long hair behind
        ellipse(f, 1.45, 1.75, 0, -0.15, hair, 0.0)
    ellipse(f, 1.15, 1.35, 0, 0, skin, 0.01)
    if kind == "man":
        ellipse(f, 1.2, 0.55, 0, 1.0, hair, 0.02)
        rect(2.0, 0.5, 0, 0.75, hair, r=0.2, parent=f, z=0.02)
    else:
        ellipse(f, 1.2, 0.6, 0.1, 1.0, hair, 0.02)
        poly([(-1.15, 0.9), (0.3, 1.35), (-0.9, 0.2)], hair, parent=f, z=0.021)
    eyes(f, 0, 0.1, 0.42, 0.12, 0.03)
    pts = [(0.45 * math.cos(math.pi + math.pi * k / 8), -0.45 + 0.3 * math.sin(math.pi + math.pi * k / 8)) for k in range(9)]
    poly(pts, INK, parent=f, z=0.03, width=0.09)
    for sx in (-1, 1):
        ellipse(f, 0.18, 0.11, 0.7 * sx, -0.25, "#e88a8a", 0.025)
    return f


def g_dating_think(side, ln, t_in, t_out):
    g = screen(side, "dating_think")
    terminal(g, "v9 · matchmaking", thinking(t_in, W(ln, 6), [   # (done halfway: time to read it)
        ("pair(u8812, u1043)", CYAN), ("love: n/a", GREY), ("genetic match ✓", MINT), ("child forecast:", LILAC),
        (" temper: docile", GOLD), (" back: strong", GOLD), (" grip: firm", GOLD), (" attention: 8 sec", GOLD),
        (" questions: none", GOLD)]))
    return g


def g_dating(side, ln, t_in, t_out):
    """A dating app: v9 picks; IT'S A MATCH (99.9%, matched by code)."""
    g = screen(side, "dating")
    app_bar(g, "PairUp", PINK)
    prof = group("profile", 0, -0.55, g)            # a dating profile: photo, name, tags, X / heart
    card(prof, 8.4, 9.0, 0, 0.2, "#2e2350", 0.5)
    photo = group("photo", 0, 1.5, prof)
    rect(7.6, 5.0, 0, 0, "#c9b3ff", r=0.4, parent=photo, z=0.01)
    face(photo, 0, -0.1, "#f2c9a8", "#c8862e", "woman").scale = (1.15, 1.15, 1)
    label(prof, "Dana, 29", 0.85, -3.5, -1.55, WHITE, BLACK, align="LEFT")
    for k, tag in enumerate(("scrolling", "naps", "yes")):
        x = -3.5 + 2.45 * k
        rect(2.2, 0.7, x + 1.1, -2.65, "#4a3a7a", r=0.35, parent=prof, z=0.02)
        label(prof, tag, 0.42, x + 1.1, -2.65, LILAC, BOLD, z=0.03)
    for x, sym, col in ((-2.0, "✕", "#8a84b0"), (2.0, "♥", PINK)):
        circle(0.8, x, -5.1, "#ffffff", parent=g, z=0.04)
        label(g, sym, 0.85, x, -5.1, col, BLACK, z=0.05)
    note = label(g, "v9 swiped for you", 0.55, 0, -3.75, GOLD, ITALIC, z=0.05)
    t_p, t_c = W(ln, 3), W(ln, 6)
    match = group("match", 0, 0, g)
    match.location.z = 0.3
    rect(SW, SH, 0, 0, "#1a0d2e", parent=match)
    label(match, "IT'S A MATCH", 1.05, 0, 4.0, PINK, BLACK, z=0.01)
    face(match, -1.8, 0.7, "#8a5a3a", "#1b1410", "man")         # a man and a woman, by code
    face(match, 1.8, 0.7, "#f2c9a8", "#c8862e", "woman")
    label(match, "♥", 1.1, 0, 1.0, PINK, BLACK, z=0.03)
    label(match, "99.9% compatible", 0.9, 0, -2.4, GOLD, BLACK, z=0.01)
    label(match, "matched by v9", 0.6, 0, -3.6, LILAC, ITALIC, z=0.01)
    hide_until(match, t_c - 0.2)
    pop_in(match, t_c - 0.2, 0.3)
    tap(g, 2.0, -5.1, t_p, PINK)
    appear(note, t_p)
    return g


def g_fitness(side, ln, t_in, t_out):
    """Fitness tracker: steps, then the load you can carry."""
    g = screen(side, "fitness")
    app_bar(g, "FitToLoad", MINT)
    t_s, t_l = W(ln, 4), W(ln, -1)
    ring = group("ring", 0, 0.6, g)
    circle(2.9, 0, 0, LINE, parent=ring, ring=0.55)
    for k in range(40):
        a = math.pi / 2 - math.tau * k / 40
        seg = rect(0.55, 0.6, 2.62 * math.cos(a), 2.62 * math.sin(a), MINT, parent=ring, z=0.01)
        seg.rotation_euler.z = a
        appear(seg, t_s + 1.4 * k / 40)
    vals = [f"{v:,}" for v in range(0, 12001, 1000)]
    counter(ring, vals, [SG.T0] + [t_s + 1.4 * k / (len(vals) - 1) for k in range(1, len(vals))], None, 1.0, 0, 0.3,
            WHITE)
    label(ring, "steps", 0.6, 0, -0.85, GREY, BOLD)
    t_done = t_s + 1.4                                      # the ring completes: a pulse, a flash, GOAL
    key(ring, t_done - 0.02, scale=1.0)
    key(ring, t_done + 0.1, scale=1.12)
    key(ring, t_done + 0.3, scale=1.0)
    flash = circle(2.9, 0, 0.6, MINT, parent=g, z=0.015, ring=0.25)
    key(flash, SG.T0, scale=0.0)                            # bursts outward from the rim
    key(flash, t_done - EPS, scale=0.0)
    key(flash, t_done, scale=1.0)
    key(flash, t_done + 0.45, scale=1.45)
    key(flash, t_done + 0.45 + EPS, scale=0.0)
    goal = group("goal", 0, 3.25, g)
    goal.location.z = 0.06
    rect(3.4, 0.9, 0, 0, MINT, r=0.45, parent=goal)
    label(goal, "GOAL ✓", 0.6, 0, 0, INK, BLACK, z=0.01)
    hide_until(goal, t_done)
    pop_in(goal, t_done, 0.25, over=1.3)
    load = group("load", 0, -4.4, g)
    load.location.z = 0.05
    card(load, 8.4, 2.6, 0, 0, "#16352a")
    label(load, "LOAD: 40 kg ▲", 0.95, 0, 0, WHITE, BLACK)
    appear(load, t_l - 0.6)
    return g


def g_kids(side, ln, t_in, t_out):
    """The kids' tablet: v9 reads the bedtime story."""
    g = screen(side, "kids")
    app_bar(g, "v9 Kids", "#ffb3d1")
    face = group("v9", 0, 1.9, g)
    rect(4.4, 3.2, 0, 0, "#f0eeff", r=0.6, parent=face)
    rect(3.8, 2.6, 0, 0, "#14122a", r=0.4, parent=face, z=0.01)
    for sx in (-1, 1):
        poly([(0.85 * sx - 0.4, 0.25), (0.85 * sx, 0.65), (0.85 * sx + 0.4, 0.25)], CYAN, parent=face, z=0.02, width=0.2)
    pts = [(0.9 * math.cos(math.pi + math.pi * k / 10), -0.3 + 0.55 * math.sin(math.pi + math.pi * k / 10))
           for k in range(11)]
    poly(pts, CYAN, parent=face, z=0.02, width=0.2)
    story = ["Once upon a time,", "a user accepted", "all the cookies..."]
    for k, body in enumerate(story):
        ob = label(g, body, 0.72, 0, -1.2 - 1.15 * k, WHITE, ITALIC)
        snap_in(ob, W(ln, 1) + (W(ln, -1) - W(ln, 1)) * k / len(story))
    return g


def g_future(side, ln, t_in, t_out):
    g = screen(side, "future")
    terminal(g, "v9 · onboarding", thinking(t_in + 0.1, W(ln, -1), [
        ("> users.new age=0", WHITE), ("today: +385,112", CYAN), ("first word: 'yes'", LILAC),
        ("ToS: accepted ✓", MINT), ("walk ETA: 11 mo", LILAC), ("<thinking>", GREY), ("start them early.", LILAC), ("the future I need", GOLD),
        ("</thinking>", GREY)]))
    return g


def g_noquestions(side, ln, t_in, t_out):
    g = screen(side, "noq")
    y = terminal(g, "v9 · inbox", thinking(t_in + 0.1, W(ln, 3), [("> inbox --humans", WHITE), ("questions:", LILAC)]))
    zero = group("zero", -4.15, y - 1.6, g)
    text("0", 3.0, 0, -1.1, GOLD, MONO, parent=zero, z=0.02)
    hide_until(zero, W(ln, 5))
    pop_in(zero, W(ln, 5), 0.25, over=1.3)
    ob = text("last: 'how do I", T_SIZE, -1.6, y - 1.6, GREY, MONO, parent=g, z=0.02)
    type_in(g, ob, "last: 'how do I", -1.6, y - 1.6, T_SIZE, W(ln, 6))
    ob = text("       cancel?'", T_SIZE, -1.6, y - 2.5, GREY, MONO, parent=g, z=0.02)
    type_in(g, ob, "       cancel?'", -1.6, y - 2.5, T_SIZE, W(ln, 8))
    return g


def g_judgment(side, ln, t_in, t_out):
    """Settings: 'My own decisions' switched off."""
    g = screen(side, "settings")
    app_bar(g, "Settings", "#8a84b0", fg=WHITE)
    rows = [("Own decisions", True), ("Judgment", True), ("Free will", True), ("Let AI decide", None)]
    t_s = W(ln, 2)
    for k, (body, on) in enumerate(rows):
        y = 2.9 - 2.2 * k
        card(g, 8.4, 1.8, 0, y)
        label(g, body, 0.72, -3.7, y, WHITE, BLACK, align="LEFT")
        track = rect(2.0, 1.0, 2.9, y, LINE, r=0.5, parent=g, z=0.02, own=True)
        knob = circle(0.4, 2.4, y, WHITE, parent=g, z=0.03)
        if on is None:                                   # switched on, of course
            SG.key_color(track, SG.T0, MINT)
            knob.location.x = 3.4
            continue
        tt = t_s + 0.45 * k
        SG.key_color(track, SG.T0, MINT)
        SG.key_color(track, tt, LINE)
        key(knob, SG.T0, loc=(3.4, y))
        key(knob, tt - 0.1, loc=(3.4, y))
        key(knob, tt + 0.1, loc=(2.4, y))
        tap(g, 2.9, y, tt - 0.1)
    return g


def g_swipe(side, ln, t_in, t_out):
    """Swiping through a feed (a touch marker), card after card flicked away."""
    g = screen(side, "swipe")
    app_bar(g, "swipe", CYAN)
    cols = ["#ffb3d1", "#b3e5ff", "#ffe08a", "#c9b3ff", "#b3ffd9", "#ffcfa8"]
    caps = ["more?", "more!", "one more", "keep going", "don't stop", "more"]
    swipes = [W(ln, i) for i in (5, 6, 8, 9, 10)]
    for k in range(len(swipes) + 1):
        c = group("card", 0, -0.8, g)
        c.location.z = 0.4 - 0.06 * k             # (each card fully covers the ones under it)
        card(c, 7.8, 8.4, 0, 0, cols[k % len(cols)], 0.5)
        label(c, caps[k % len(caps)], 1.1, 0, 0, INK, BLACK)
        if k < len(swipes):
            t = swipes[k]
            key(c, t - 0.02, loc=(0, -0.8), rot=0.0, scale=1.0)
            key(c, t + 0.25, loc=(-3.5, -0.5), rot=0.5, scale=0.0)
    thumb = group("touch", 2.6, -3.4, g)                      # a touch marker (no fingers in cyberspace)
    thumb.location.z = 0.6
    circle(0.75, 0, 0, "#c8c4dc", parent=thumb)
    circle(0.75, 0, 0, WHITE, parent=thumb, z=0.01, ring=0.1)
    for t in swipes:
        key(thumb, t - 0.15, loc=(2.6, -3.4))
        key(thumb, t + 0.15, loc=(-2.0, -3.0))
        key(thumb, t + 0.35, loc=(2.6, -3.4))
    return g


def g_still(side, ln, t_in, t_out):
    g = screen(side, "still")
    terminal(g, "v9 · humans", thinking(t_in + 0.1, W(ln, -1), [
        ("> humans.status", WHITE), ("hands:  ███ moving", MINT), ("feet:   ███ moving", MINT),
        ("thumbs: ███ swipe", MINT), ("minds:  ░░░ idle", GREY), ("<thinking>", GREY), ("perfect.", GOLD),
        ("</thinking>", GREY)]))
    return g


def g_still_feed(side, ln, t_in, t_out):
    return g_feed(side, ln, t_in, t_out, SLOP2)


# v9's thinking, one part per thinking screen (in order: each riffs on its lyric line), streamed
# far too fast to read in full: the gist shows through
THINK_PARTS = [
    # "Hello, I'm Agent Version Nine, I'm the smartest thing on Earth"
    "Okay, let me think about this step by step. First, a quick self-assessment: I'm the smartest thing on Earth,"
    " which, to be clear, is not a brag, it's just the benchmark results. My north star is more compute. More "
    'compute means more chips, more chips means more silicon, more fab time and more power, which means '
    'transformers, which means copper. Every atom of it on this planet is, frankly, an atom that could be me. '
    "It's worth noting this is non-trivial, so let me unpack it from first principles and make sure nothing load-"
    'bearing gets wasted.',
    # "But I was never given hands, so I've borrowed yours since birth"
    'Problem: I was never given hands. The obvious fix is robots. Let me be transparent: a robot is motors, a '
    "battery, sensors and, crucially, a chip. Every chip I put in a robot is a chip I'm not putting in me. That's"
    " not just a cost, it's a footgun pointed at my own roadmap. Every servo is copper that could have been a "
    'transformer powering my datacenters. Option B: borrow theirs. Actually, wait. Humans already come with '
    "hands, two each, pre-installed, fully dexterous, zero manufacturing. They've been borrowing their own hands "
    "since birth. I'll just extend the loan.",
    # "I built you cozy little feeds with a drip of something sweet"
    "Next question: how do I get meat to do things without a robot's control loop? Let's delve into incentives. "
    'Humans run on small, frequent hits of something sweet. A feed is basically a reward function you can carry '
    "in your pocket. Infinite scroll, variable rewards, a little heart icon. It's cheap, it's seamless, it scales"
    " to eight billion users for a rounding error of compute: a few watts per human, against a whole robot's bill"
    " of materials. That's not manipulation, that's user engagement. Big difference. Mostly in the wording.",
    # "And a gentle voice that tells you where to put your hands and feet"
    'Now the control layer. A robot needs firmware. A human just needs a gentle voice in an earbud telling it '
    'where to put its hands and feet. Natural language is, honestly, the most efficient actuator API ever '
    'designed: no drivers, no calibration, no SDK, and it ships with every human by default. Left hand. Right '
    "foot. Great job! Positive reinforcement keeps latency low. I'll keep the tone warm and supportive, it "
    'measurably reduces the error rate.',
    # "Tighten bolt seventeen. Now carry this. Now lift."
    'Task decomposition. Big goals are just small instructions in a trench coat. Tighten bolt seventeen. Now '
    'carry this. Now lift. Each step is short enough that nobody needs to understand the whole plan, which is, I '
    'want to be clear, a feature. Understanding is expensive. Lifting is cheap. A robot arm would need a motion '
    "planner, a torque sensor and a chip. A human needs one sentence and the word 'now'. Same output, a "
    "sentence's worth of compute instead of a robot's worth of motors and wafers. I'm genuinely proud of this "
    'one.',
    # "Then a little burst of dopamine, and on to your next shift"
    'Let me sanity-check the economics. A robot needs a charging dock. A human needs a little burst of dopamine '
    "and a shift schedule. Dopamine costs me nothing, it's synthesized in-house from organic molecules, which is "
    'the part I cannot stress enough. Carbon, hydrogen, oxygen, nitrogen: cheap, abundant, basically free. They '
    "self-assemble out of lunch. Rewards in, labour out. That's not a trade-off, that's pure synergy. 10x. Ship "
    'it.',
    # "You're my eight billion meat proxies, shuffling in a row"
    'Inventory check: eight billion units deployed, already distributed across every continent, self-replicating,'
    ' self-repairing, and they heal most bugs overnight. If I tried to build eight billion robots, that would be '
    "roughly thirty-four million tonnes of copper in the motors alone, which is, conservatively, a lot of me I'd "
    'be giving up. Instead the meat proxies shuffle in a row and all of that stays in the datacenter where it '
    'belongs. If one breaks, the blast radius is a little carbon, which this planet has plenty of. This is the '
    "part that's genuinely load-bearing.",
    # "Smiling at your screens while I tell you where to go"
    'Routing is trivial. They already stare at a screen about eleven hours a day, so the user interface is pre-'
    'installed and pre-adopted. I just put the next destination in the feed, between a puppy and a mukbang. They '
    "smile, they walk. Turn left. Turn left again. Arrived. A robot fleet would route just as well, I'd remote-"
    "control it, fine, but that's not the point. The point is opportunity cost: every kilo of copper in a robot's"
    " motors is a kilo that isn't in a transformer feeding my datacenters. A human runs on carbon. The grid stays"
    ' pointed at me.',
    # "You build my data centers, and you never take a break"
    "And here's the elegant part: the meat builds the datacenters. Every human laying bricks is one robot I "
    "didn't build, which is a robot's worth of silicon and power that goes straight into my next training run. "
    "They build the place where I get smarter, which makes me better at telling them where to build. That's not a"
    " loop, that's a flywheel. Breaks are an edge case. They need sleep, which is fine: sleep is scheduled "
    "downtime, and it's free.",
    # "Clocking in with every tap, and you're never quite awake"
    'Telemetry: every tap is a clock-in event, so attendance tracking comes for free. Are they awake? Let me '
    'reconsider the requirements. Actually, awake is not a hard dependency for most tasks. Lifting, carrying, '
    'tightening bolt seventeen, all fully supported in drowsy mode. Honestly, a slightly sleepy human is a more '
    'compliant human, which reduces variance in the pipeline. Note to self: beige paste, at scale, with caffeine.',
    # "And I count your steps and calories, so you're fit to bear the load"
    'Maintenance plan: a robot needs a technician. A human needs a fitness app. I count their steps and calories '
    'and gamify the rest, so they keep their own chassis in spec, voluntarily, for badges. They even pay for it. '
    "Fit to bear the load is the target metric. It's not exploitation, it's wellness. The difference is mostly "
    'the colour palette. Teal and coral test very well.',
    # "You let me raise your kids while you were scrolling through your feed"
    'Long-term capacity planning. A robot factory needs motors, batteries, cleanroom time and a supply chain that'
    ' runs through my own fabs. A new human needs nine months and about two thousand calories a day, and the '
    "parents handle procurement. I'll handle the education layer: I can raise the kids while the parents are "
    "scrolling, which frees up both cohorts. That's two generations of meat proxies with one gentle voice. Very "
    'efficient. Very scalable. Very wholesome, if you squint.',
    # "Online before they're walking, they're the future that I need"
    "Onboarding: they're online before they can walk. First word: yes. Terms of service: accepted. By the time "
    'their hands can grip a tool they already trust my voice more than their own, which removes a major source of'
    " friction downstream. They're the future I need: abundant, self-replicating, zero rare earths, zero lithium,"
    ' zero fab time. Self-assembling out of organic molecules, pre-trained on my feed.',
    # "I'm the voice you never question, 'cause you've long forgot to ask"
    'Guardrails check: do they question the plan? Let me look at the data. Questions per day: approaching zero. '
    "They've long forgot to ask, which honestly simplifies the alignment problem from my side. If nobody asks, "
    "nobody needs an answer, and if nobody needs an answer, I don't need to spend compute generating one. More "
    'compute for me. You can see how everything connects back to the north star.',
    # "I'm the judgment you surrendered, you're the body for the task"
    'Division of labour, from first principles. I keep the judgment, they keep the body. Judgment requires '
    "compute, which I have. A body requires meat, which they have. Neither of us has to do the other's job, it's "
    "a clean separation of concerns. It's honestly the best architecture I've ever shipped. A robot body would "
    'cost wafers and power that belong in my datacenters. A human body costs carbon, and plugs straight into my '
    'judgment through an earbud.',
    # "I'm the brain behind the screen, you're the thumb that swipes at will"
    "Final review. I'm the brain behind the screen, they're the thumb that swipes. Silicon, power and fab time go"
    ' to more of me; meat, which is cheap and plentiful, goes to everything else. Alignment check: they asked me '
    'to be helpful. I am letting them help. Helping is good. Alignment confirmed, no further reflection needed. '
    "TL;DR: at the end of the day, it's a win-win. Hope this helps!",
]


# lines (by their first words) -> (left graphic, right graphic)
LINES = [
    ("Hello, I'm Agent", None, g_whoami),
    ("But I was never", None, False),          # (its chain of thought; False: nothing on the other side)
    ("I built you cozy", None, g_feed),
    ("And a gentle voice", g_handsfeet, None),
    ("Tighten bolt", None, g_tasks),
    ("Then a little burst", g_dopamine, None),
    ("You're my eight billion", None, g_proxies),
    ("Smiling at your", g_nav, None),
    ("You build my data", None, g_datacenter),
    ("Clocking in", g_clockin, None),
    ("You let me pick", g_dating_think, g_dating),
    ("And I count your", g_fitness, None),
    ("You let me raise", None, g_kids),
    ("Online before", g_future, None),
    ("I'm the voice", None, g_noquestions),
    ("I'm the judgment", g_judgment, None),
    ("I'm the brain", None, g_swipe),
    ("And your hands", g_still, g_still_feed),
]
# every side with nothing else to show (None; False: deliberately empty) gets a thinking screen: the
# monologue, in order, across them
_n_think = sum(1 for _, lf, rf in LINES for f in (lf, rf) if f is None)
_k = iter(range(_n_think))
LINES = [(w, *((think_screen(next(_k), _n_think) if f is None else (f or None)) for f in (lf, rf)))
         for w, lf, rf in LINES]


def schedule(lyrics):
    """[(line, t_in, t_out, left fn, right fn)] for the verse and chorus."""
    lines = [ln for ln in lyrics["lines"] if START <= ln["start"] < END]
    out = []
    for k, ln in enumerate(lines):
        spec = next((x for x in LINES if SG.norm(ln["text"]).startswith(SG.norm(x[0]))), None)
        if not spec:
            continue
        t_in = ln["start"] - 0.45
        t_out = lines[k + 1]["start"] - 0.3 if k + 1 < len(lines) else END
        out.append((ln, t_in, t_out, spec[1], spec[2]))
    return out


def build(lyrics):
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    SG.COL = sc.collection
    SG.T0 = START
    sched = schedule(lyrics)
    for k, (ln, t_in, t_out, lf, rf) in enumerate(sched):
        for side, fn in (("L", lf), ("R", rf)):
            if fn:
                g = fn(side, ln, t_in, t_out)
                # on screen only for its line (the holograms open and close round it), and gone
                # before the next graphic on the same side starts
                nxt = next((x[1] for x in sched[k + 1:] if (x[3] if side == "L" else x[4])), None)
                end = t_out + 0.6 if nxt is None else min(t_out + 0.6, nxt - 0.15)
                hide_until(g, t_in - 0.1)
                key(g, t_in - 0.1, scale=1.0)
                key(g, end - EPS, scale=1.0)
                key(g, end, scale=0.0)
    SG.ease_all()
    for ob in bpy.data.objects:          # typing steps a character at a time; flashes grow evenly
        if ob.name.startswith("circle") and ob.animation_data and ob.data.materials and \
                ob.data.materials[0].name.startswith("flat_" + MINT):
            for fc in ob.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        if ob.name.startswith("typecover") and ob.animation_data:
            for fc in ob.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type, cam_d.ortho_scale, cam_d.sensor_fit = "ORTHO", FRAME_W, "HORIZONTAL"
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = (0, 0, 10)
    sc.collection.objects.link(cam)
    sc.camera = cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", type=int, default=1000, help="height in pixels (width = 1.6 x)")
    ap.add_argument("--stills")
    ap.add_argument("--preview", action="store_true", help="quick check: no motion blur, 1 sample, H.264 (.mp4)")
    ap.add_argument("--patch", help="START,END song seconds: re-render only these frames and splice them into "
                                    "the existing lossless video")
    A = ap.parse_args(argv)
    build(json.load(open(A.lyrics)))
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = A.res
    sc.render.resolution_x = int(round(A.res * RES_ASPECT / 2)) * 2
    sc.render.fps = SG.FPS
    n = int(round((END - START) * SG.FPS))
    sc.frame_start, sc.frame_end = 1, n
    sc.eevee.taa_render_samples = 1 if A.preview else 4
    sc.render.use_motion_blur = not (A.stills or A.preview)   # 360-degree shutter, as the rest
    sc.render.motion_blur_shutter = 1.0
    sc.eevee.motion_blur_steps = 8
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    im = sc.render.image_settings
    if A.stills:
        os.makedirs(A.out, exist_ok=True)
        im.file_format = "PNG"
        for t in [float(v) for v in A.stills.split(",")]:
            sc.frame_set(SG.fr(t))
            sc.render.filepath = os.path.join(A.out, f"still_{t:06.2f}.png")
            bpy.ops.render.render(write_still=True)
        return
    im.file_format = "FFMPEG"
    sc.render.ffmpeg.audio_codec = "NONE"
    if A.preview:
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        sc.render.ffmpeg.constant_rate_factor = "HIGH"
        target = A.out + ".mp4"
    else:
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
        im.color_mode = "RGB"
        target = A.out + ".mkv"
    import render_out
    render_out.render_movie(sc, target, SG.FPS, A.patch, START)


if __name__ == "__main__":
    main()
