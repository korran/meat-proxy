"""The yacht's LED wall during verse 2 and chorus 2 (the Founder): lyrics and a graphic per line,
on a 2:1 screen (18 x 9 units, x -9..9, y -4.5..4.5). Built with screen_graphics.py's helpers:

  blender -b --factory-startup --python video/screen_graphics.py -- --part v2c2 \\
      --lyrics video/build/lyrics.json --start 66.4 --end 129.8 --out video/build/screen_v2c2 \\
      [--res 540] [--noblur] [--stills 70,90]

The Founder stands in front of the wall, and the camera dollies to move him across it (see
yacht_set.DOLLY, which is made from the 'side' of each line below). Each line's lyrics take a band
across the top of the free part of the wall, its graphic the area below (screen_graphics.REG).
Kevin turns up a lot, as a little flat icon (kevin()).
"""
import math
import random

import screen_graphics as SG
from screen_graphics import (BLACK, BOLD, CORAL, DIM, INK, ITALIC, LILAC, MINT, MONO, NAVY2, PAPER, RED,
                             SCRIPT, SEMI, WHITE, YELLOW, BEBAS, at, card, circle, group, hide_until, key,
                             key_color, poly, pop_in, pop_out, rect, show, text, width_of)

GY0, GY1 = -4.05, 1.95            # the graphics area, below the lyrics (y)
GY = (GY0 + GY1) / 2
SKIN, HAIR, SHIRT, SHORTS, SNEAKER, LANYARD = "#f6c9a0", "#6b4128", "#4fb3f0", "#2b3a67", "#e5413b", "#ff6a1f"
STEAK, GREEN, DARKGREEN, GOLD, GREY = "#a33a2a", "#5fbf6a", "#2f7a3a", "#e8c15a", "#59638f"
LINE_BLUE = "#3a4280"
EPS = 1.0 / SG.FPS            # one frame: keys closer than this land on the same frame


def R():
    return SG.REG


# ---------------------------------------------------------------- helpers
def visible(ob, t_in, t_out=None):
    """Snap on at t_in (and off at t_out)."""
    hide_until(ob, t_in)
    key(ob, t_in, scale=1.0)
    if t_out is not None:
        key(ob, t_out - EPS, scale=1.0)
        key(ob, t_out, scale=0.0)


def sequence(obs, times, t_end):
    """Each object visible from its time until the next one's (a counter ticking over)."""
    for k, ob in enumerate(obs):
        visible(ob, times[k], times[k + 1] if k + 1 < len(obs) else t_end)


def shake(ob, t, amp=0.06, n=4, dt=0.05):
    key(ob, SG.T0, rot=0.0)
    key(ob, t - EPS, rot=0.0)
    for k in range(n):
        key(ob, t + dt * k, rot=amp * (1 if k % 2 else -1) * (1 - k / n))
    key(ob, t + dt * n, rot=0.0)


def stamp(parent, label, x, y, t, color=RED, size=0.5, rot=-0.18, bg=PAPER):
    """A rubber stamp that thumps down at t."""
    st = group("stamp", x, y, parent)
    w = len(label) * size * 0.62 + 0.5
    rect(w, size * 1.7, 0, 0, color, r=0.1, parent=st, z=0.05)
    rect(w - 0.22, size * 1.7 - 0.22, 0, 0, bg, r=0.06, parent=st, z=0.06)
    text(label, size, 0, -size * 0.36, color, BLACK, align="CENTER", parent=st, z=0.07)
    key(st, SG.T0, scale=0.0)
    key(st, t - EPS, scale=0.0, rot=rot + 0.25)
    key(st, t + 0.1, scale=2.0, rot=rot - 0.05)
    key(st, t + 0.22, scale=1.0, rot=rot)
    return st


def kevin(parent, x, y, s=1.0, z=0.0, name="kevin", split_head=False, charred=False, prison=False):
    """Kevin as a flat icon: sneakers, shorts, blue shirt with the steak, orange lanyard and badge,
    cowlick. Feet at (x, y), about 2.1 * s tall. Returns (group, [left leg, right leg], head lid);
    the legs pivot at the hip (for running). split_head: the top of his head is a separate piece.
    prison: black-and-white striped prison fatigues, with an inmate number."""
    g = group(name, x, y, parent)
    g.location.z = z
    c = (lambda col: "#2a2a30") if charred else (lambda col: col)
    STRIPE, BASE = "#15161b", "#f4f4f0"
    legs = []
    for sx in (-1, 1):
        lg = group("leg", 0.15 * s * sx, 0.62 * s, g)
        rect(0.24 * s, 0.5 * s, 0, -0.27 * s, BASE if prison else c(SKIN), parent=lg, z=0.001)
        if prison:
            for k in range(4):
                rect(0.24 * s, 0.06 * s, 0, (-0.1 - 0.12 * k) * s, STRIPE, parent=lg, z=0.0015)
        rect(0.3 * s, 0.13 * s, 0.03 * s * sx, -0.55 * s, c(SNEAKER), r=0.04 * s, parent=lg, z=0.002)
        legs.append(lg)
    rect(0.64 * s, 0.26 * s, 0, 0.66 * s, BASE if prison else c(SHORTS), r=0.03 * s, parent=g, z=0.003)
    poly([(-0.36 * s, 0.76 * s), (0.36 * s, 0.76 * s), (0.3 * s, 1.38 * s), (-0.3 * s, 1.38 * s)],
         BASE if prison else c(SHIRT), parent=g, z=0.004)
    for sx in (-1, 1):
        rect(0.17 * s, 0.22 * s, 0.4 * s * sx, 1.24 * s, BASE if prison else c(SHIRT), r=0.04 * s, parent=g,
             z=0.0035)
        rect(0.13 * s, 0.36 * s, 0.42 * s * sx, 0.97 * s, c(SKIN), r=0.05 * s, parent=g, z=0.003)
    if prison:   # stripes across the shirt (following its taper), the shorts and the sleeves
        for k in range(5):
            yy = 0.82 + 0.125 * k
            hw = 0.36 - 0.06 * (yy - 0.76) / 0.62
            rect(2 * hw * s, 0.06 * s, 0, yy * s, STRIPE, parent=g, z=0.0045)
        rect(0.64 * s, 0.06 * s, 0, 0.66 * s, STRIPE, parent=g, z=0.0032)
        for sx in (-1, 1):
            rect(0.17 * s, 0.06 * s, 0.4 * s * sx, 1.24 * s, STRIPE, parent=g, z=0.0037)
        rect(0.34 * s, 0.17 * s, 0, 1.12 * s, BASE, parent=g, z=0.005)
        text("4471", 0.13 * s, 0, 1.075 * s, STRIPE, BLACK, align="CENTER", parent=g, z=0.006)
    else:
        circle(0.09 * s, 0.13 * s, 1.08 * s, c(STEAK), parent=g, z=0.005)
        for sx in (-1, 1):
            poly([(0.14 * s * sx, 1.38 * s), (0.04 * s * sx, 0.95 * s)], c(LANYARD), parent=g, z=0.005,
                 width=0.045 * s)
        rect(0.22 * s, 0.15 * s, 0, 0.9 * s, c(WHITE), r=0.02 * s, parent=g, z=0.006)
    lid = None
    if split_head:   # the face, and a lid (top of the head and the hair) that can come off
        rect(0.6 * s, 0.34 * s, 0, 1.56 * s, c(SKIN), r=0.1 * s, parent=g, z=0.007)
        lid = group("lid", 0, 1.73 * s, g)
        rect(0.6 * s, 0.2 * s, 0, 0.0, c(SKIN), parent=lid, z=0.0072)
        rect(0.64 * s, 0.2 * s, 0, 0.17 * s, c(HAIR), r=0.08 * s, parent=lid, z=0.008)
        circle(0.075 * s, 0.13 * s, 0.29 * s, c(HAIR), parent=lid, z=0.0078)
    else:
        rect(0.6 * s, 0.52 * s, 0, 1.65 * s, c(SKIN), r=0.12 * s, parent=g, z=0.007)
        rect(0.64 * s, 0.2 * s, 0, 1.9 * s, c(HAIR), r=0.08 * s, parent=g, z=0.008)
        circle(0.075 * s, 0.13 * s, 2.02 * s, c(HAIR), parent=g, z=0.0078)
    for sx in (-1, 1):
        circle(0.045 * s, 0.12 * s * sx, 1.66 * s, "#1b1b22", parent=g, z=0.009)
    poly([(-0.1 * s, 1.53 * s), (0, 1.49 * s), (0.1 * s, 1.53 * s)], "#1b1b22", parent=g, z=0.009, width=0.03 * s)
    return g, legs, lid


def run_cycle(g, legs, t0, t1, x0, x1, y, rate=7.0, bob=0.08, amp=0.6):
    """Run from x0 to x1 (at height y) between t0 and t1: legs swinging, bobbing on each step
    (rate: steps per second)."""
    n = max(1, int((t1 - t0) * rate))
    for k in range(n + 1):
        u = k / n
        t = t0 + (t1 - t0) * u
        sgn = 1 if k % 2 else -1
        for i, lg in enumerate(legs):
            key(lg, t, rot=amp * sgn * (1 if i else -1))
        key(g, t, loc=(x0 + (x1 - x0) * u, y + (bob if k % 2 else 0.0)))


def person(parent, x, y, s, body, prop=None, z=0.0, skin=None, own=False):
    """A plain little person (the mob, the layoffs): head, body, legs; optional pitchfork or torch.
    Returns (group, legs, [head, body])."""
    g = group("person", x, y, parent)
    g.location.z = z
    skin = skin or SKIN
    legs = []
    for sx in (-1, 1):
        lg = group("leg", 0.12 * s * sx, 0.55 * s, g)
        rect(0.18 * s, 0.55 * s, 0, -0.28 * s, "#2b2f45", parent=lg, z=0.001)
        legs.append(lg)
    b = rect(0.6 * s, 0.75 * s, 0, 0.92 * s, body, r=0.14 * s, parent=g, z=0.002, own=own)
    h = circle(0.24 * s, 0, 1.55 * s, skin, parent=g, z=0.003, own=own)
    if prop == "fork":
        grp = group("fork", 0.38 * s, 0.9 * s, g)
        rect(0.06 * s, 1.9 * s, 0, 0.35 * s, "#8a5a3b", parent=grp, z=0.004)
        rect(0.5 * s, 0.06 * s, 0, 1.3 * s, "#c9ced6", parent=grp, z=0.004)
        for dx in (-0.22, 0, 0.22):
            rect(0.06 * s, 0.4 * s, dx * s, 1.5 * s, "#c9ced6", parent=grp, z=0.004)
    elif prop == "torch":
        grp = group("torch", 0.38 * s, 0.9 * s, g)
        rect(0.08 * s, 1.3 * s, 0, 0.3 * s, "#8a5a3b", parent=grp, z=0.004)
        fl = group("flame", 0, 1.05 * s, grp)
        poly([(-0.18 * s, 0), (0.18 * s, 0), (0.0, 0.55 * s)], "#ff8a1f", parent=fl, z=0.005)
        poly([(-0.09 * s, 0), (0.09 * s, 0), (0.0, 0.3 * s)], YELLOW, parent=fl, z=0.006)
    if prop:   # angry brows
        for sx in (-1, 1):
            br = rect(0.14 * s, 0.04 * s, 0.09 * s * sx, 1.62 * s, "#1b1b22", parent=g, z=0.004)
            br.rotation_euler.z = -0.5 * sx
    return g, legs, [h, b]


def yacht_icon(parent, x, y, s, color=WHITE):
    g = group("yacht", x, y, parent)
    poly([(-1.0 * s, 0), (0.85 * s, 0), (1.2 * s, 0.35 * s), (-1.05 * s, 0.35 * s)], "#1b2742", parent=g, z=0.01)
    rect(1.2 * s, 0.28 * s, -0.15 * s, 0.49 * s, color, r=0.05 * s, parent=g, z=0.01)
    rect(0.7 * s, 0.22 * s, -0.25 * s, 0.74 * s, color, r=0.05 * s, parent=g, z=0.01)
    rect(1.0 * s, 0.07 * s, -0.15 * s, 0.5 * s, "#26394d", parent=g, z=0.011)
    return g


def bill(parent, x, y, s=1.0, z=0.0):
    g = group("bill", x, y, parent)
    g.location.z = z
    rect(0.95 * s, 0.45 * s, 0, 0, GREEN, r=0.04 * s, parent=g, z=0.001)
    rect(0.8 * s, 0.32 * s, 0, 0, DARKGREEN, r=0.03 * s, parent=g, z=0.002)
    circle(0.12 * s, 0, 0, GREEN, parent=g, z=0.003)
    text("$", 0.2 * s, 0, -0.07 * s, DARKGREEN, BLACK, align="CENTER", parent=g, z=0.004)
    return g


def label(parent, body, x, y, size=0.34, color=WHITE, font=SEMI, align="CENTER", z=0.02):
    return text(body, size, x, y - size * 0.36, color, font, align=align, parent=parent, z=z)


# ---------------------------------------------------------------- graphics, line by line
def g_fired(ln, t_out):
    """LAYOFFS: a counter races to 40,000 while a crowd of little people greys out; on the right,
    yachts Nº1 and Nº2 (done) and Nº3 (this one)."""
    r = R()
    g = group("fired", 0, 0)
    lx = -5.6
    left = group("layoffs", lx, 0, g)
    label(left, "LAYOFFS", 0, 1.35, 0.36, LILAC, BLACK)
    t_f, t_t, t_p = at(ln, "fired"), at(ln, "thousand"), at(ln, "people")
    vals = ["0", "1,200", "4,800", "9,000", "15,500", "22,000", "28,400", "33,900", "37,600", "39,850", "40,000"]
    times = [t_f + (t_t + 0.35 - t_f) * k / (len(vals) - 1) for k in range(len(vals))]
    nums = [label(left, v, 0, 0.62, 1.0, CORAL if k == len(vals) - 1 else WHITE, BLACK) for k, v in enumerate(vals)]
    sequence(nums, times, t_out + 0.3)
    rng = random.Random(3)
    cols = ["#9fb3ff", "#ffd166", "#3ddc97", "#ff9f7a", "#c9a0ff"]
    for i in range(10):
        for j in range(4):
            px, py = -2.7 + i * 0.6, -0.95 - j * 0.85
            col = rng.choice(cols)
            _, _, parts = person(left, px, py, 0.42, col, own=True, z=0.01)
            tg = t_f + 0.2 + (t_p + 0.3 - t_f) * rng.random()      # fired: greyed out
            key_color(parts[1], SG.T0, col)
            key_color(parts[1], tg, "#3a4066")
            key_color(parts[0], SG.T0, SKIN)
            key_color(parts[0], tg, "#3a4066")
    right = group("yachts", 5.6, 0, g)
    label(right, "FLEET", 0, 1.35, 0.36, LILAC, BLACK)
    t_d, t_3 = at(ln, "deck"), at(ln, "third")
    for k, (x, lab) in enumerate(((-1.9, "Nº1"), (0.0, "Nº2"), (1.9, "Nº3"))):
        y = group("y", x, -0.6, right)
        yacht_icon(y, 0, 0, 0.75, WHITE if k == 2 else "#8790b8")
        label(y, lab, 0, -0.45, 0.34, YELLOW if k == 2 else LILAC, BLACK)
        if k < 2:
            label(y, "✓", 0.0, 1.25, 0.5, MINT, BLACK)
        pop_in(y, (t_d if k < 2 else t_3) + 0.12 * k)
    here = group("here", 1.9, -2.4, right)
    poly([(0, 0.5), (-0.25, 0.1), (0.25, 0.1)], CORAL, parent=here, z=0.01)
    label(here, "YOU ARE HERE", 0, -0.2, 0.28, CORAL, BLACK)
    pop_in(here, t_3 + 0.3)
    show(g, ln["start"] - 0.3, t_out)


def g_replaced(ln, t_out):
    """The crowd flips, one by one, into little agents; on the right, a vibe-coding session."""
    g = group("replaced", 0, 0)
    left = group("swap", -5.6, 0, g)
    label(left, "HEADCOUNT", 0, 1.35, 0.36, LILAC, BLACK)
    t_r, t_a = at(ln, "Replaced"), at(ln, "agents")
    rng = random.Random(8)
    for i in range(8):
        for j in range(4):
            px, py = -2.45 + i * 0.7, 0.35 - j * 1.05
            tf = t_r + (t_a + 0.3 - t_r) * (i + j * 8) / 32 + 0.1 * rng.random()
            hum = group("h", px, py, left)
            person(hum, 0, -0.35, 0.4, "#5a6290")
            bot = group("bot", px, py, left)
            rect(0.5, 0.42, 0, 0.0, LILAC, r=0.08, parent=bot, z=0.01)
            for sx in (-1, 1):
                rect(0.09, 0.09, 0.11 * sx, 0.03, INK, parent=bot, z=0.02)
            rect(0.04, 0.16, 0, 0.29, LILAC, parent=bot, z=0.01)
            circle(0.05, 0, 0.38, MINT, parent=bot, z=0.02)
            rect(0.36, 0.22, 0, -0.36, LILAC, r=0.05, parent=bot, z=0.01)
            key(hum, SG.T0, scale=(1, 1, 1))
            key(hum, tf - EPS, scale=(1, 1, 1))
            key(hum, tf + 0.08, scale=(0, 1, 1))
            key(bot, SG.T0, scale=(0, 1, 1))
            key(bot, tf + 0.08, scale=(0, 1, 1))
            key(bot, tf + 0.18, scale=(1, 1, 1))
    right = group("vibe", 5.55, -1.0, g)
    card(6.2, 5.0, 0, 0, right, color=INK, edge=LINE_BLUE)
    rect(6.2, 0.45, 0, 2.28, LINE_BLUE, parent=right, z=0.01)
    for k, col in enumerate((RED, YELLOW, MINT)):
        circle(0.08, -2.8 + 0.28 * k, 2.28, col, parent=right, z=0.02)
    label(right, "vibe_code.py", 0.3, 2.28, 0.24, LILAC, MONO)
    t_v = at(ln, "vibe-coded")
    rows = [("> make me agents", WHITE), ("> no bugs pls", WHITE), ("> make it scale", WHITE),
            ("✨ vibing...", YELLOW), ("✓ 40,000 agents", MINT), ("✓ shipped", MINT), ("  (untested)", GREY)]
    for k, (body, col) in enumerate(rows):
        ob = text(body, 0.36, -2.75, 1.45 - 0.55 * k, col, MONO, parent=right, z=0.02)
        pop_in(ob, ln["start"] + 0.3 + 0.42 * k, 0.12)     # from the start of the line: time to read
    show(g, ln["start"] - 0.3, t_out)


def g_senate(ln, t_out):
    """A subpoena from the Capitol; on the right, the voters' signs: they want a head."""
    g = group("senate", 0, 0)
    left = group("capitol", -5.6, -1.2, g)
    dome = group("dome", 0, 0.9, left)
    poly([(1.3 * math.cos(math.pi * k / 16), 1.3 * math.sin(math.pi * k / 16)) for k in range(17)], WHITE,
         parent=dome, z=0.01)
    rect(0.08, 0.6, 0, 1.55, WHITE, parent=dome, z=0.01)
    rect(3.6, 0.3, 0, 0.75, WHITE, parent=left, z=0.01)
    for k in range(7):
        rect(0.2, 1.4, -1.5 + 0.5 * k, 0.0, WHITE, parent=left, z=0.01)
    rect(4.2, 0.3, 0, -0.8, WHITE, parent=left, z=0.01)
    label(left, "U.S. SENATE", 0, -1.45, 0.34, LILAC, BLACK)
    pop_in(left, at(ln, "Senate") - 0.1)
    t_h = at(ln, "hearing")
    stamp(left, "SUBPOENA", 0.2, 0.4, t_h, RED, 0.48)
    right = group("signs", 5.6, -1.4, g)
    t_v, t_w, t_hd = at(ln, "voters"), at(ln, "want"), at(ln, "head")
    for k, (x, body, t) in enumerate(((-1.95, "A HEAD!", t_v), (0.0, "ONE (1)\nHEAD", t_w), (1.95, "HEADS\nPLS", t_hd))):
        sg = group("sign", x, 0, right)
        rect(0.1, 2.4, 0, -0.6, "#8a5a3b", parent=sg, z=0.01)
        card(1.8, 1.5, 0, 0.9, sg, color=PAPER)
        tx = text(body, 0.34, 0, 1.05, RED, BLACK, align="CENTER", parent=sg, z=0.02)
        pop_in(sg, t)
        for m in range(int((t_out - t) / 0.27)):      # bobbing on the beat
            tb = t + 0.3 + 0.27 * m
            key(sg, tb, loc=(x, 0.0 if (m + k) % 2 else 0.18))
    label(right, "THE VOTERS", 0, -2.35, 0.34, LILAC, BLACK)
    show(g, ln["start"] - 0.3, t_out)


def g_sacrifice(ln, t_out):
    """Kevin, kept handy in a break-glass case; on 'sacrificed' the glass shatters and a mob with
    pitchforks and torches chases him off the screen."""
    r = R()
    cx = r["cx"]
    g = group("sacrifice", 0, 0)
    case = group("case", cx + 1.5, -1.0, g)
    rect(3.0, 4.4, 0, 0, RED, r=0.12, parent=case, z=0.0)
    rect(2.6, 3.4, 0, -0.3, "#1a2350", r=0.06, parent=case, z=0.01)
    rect(3.0, 1.0, 0, 2.55, RED, r=0.12, parent=case, z=0.0)
    label(case, "IN CASE OF HEARING", 0, 2.75, 0.24, WHITE, BLACK, z=0.03)
    label(case, "BREAK GLASS", 0, 2.38, 0.3, YELLOW, BLACK, z=0.03)
    kv, legs, _ = kevin(g, cx + 1.5, -2.85, 1.35, z=0.02)
    glass = group("glass", cx + 1.5, -1.3, g)      # see-through: a pale frame and glints over him
    glass.location.z = 0.2
    for w_, h_, x_, y_ in ((2.6, 0.14, 0, 1.63), (2.6, 0.14, 0, -1.63), (0.14, 3.4, -1.23, 0), (0.14, 3.4, 1.23, 0)):
        rect(w_, h_, x_, y_, "#9fd0ff", parent=glass)
    for k in range(3):
        poly([(-0.9 + 0.5 * k, 1.2), (-0.78 + 0.5 * k, 1.2), (-1.1 + 0.5 * k, 0.5), (-1.22 + 0.5 * k, 0.5)], "#cfe6ff",
             parent=glass, z=0.002)
    t_k, t_s = at(ln, "keep"), at(ln, "sacrificed")
    for ob in (case, kv, glass):
        hide_until(ob, t_k - 0.1)
        pop_in(ob, t_k - 0.1)
    key(glass, t_s - EPS, scale=1.0)
    key(glass, t_s + 0.01, scale=0.0)
    rng = random.Random(5)
    for k in range(14):   # shards
        sh = group("shard", cx + 1.5 + rng.uniform(-1, 1), -1.3 + rng.uniform(-1.5, 1.5), g)
        sh.location.z = 0.25
        a = rng.uniform(0.15, 0.4)
        poly([(0, a), (-a * 0.7, -a * 0.5), (a * 0.8, -a * 0.3)], "#cfe6ff", parent=sh)
        hide_until(sh, t_s)
        key(sh, t_s, scale=1.0, rot=0.0, loc=(sh.location.x, sh.location.y))
        key(sh, t_s + 0.6, scale=0.6, rot=rng.uniform(-6, 6),
            loc=(sh.location.x + rng.uniform(-3.5, 3.5), sh.location.y + rng.uniform(-4, 1.5)))
        key(sh, t_s + 0.61, scale=0.0)
    key(case, t_s + 0.25, scale=1.0)
    key(case, t_s + 0.45, scale=0.0)
    # the chase: Kevin bolts left, the mob pours in from the right (from behind the Founder)
    t0, t1 = t_s + 0.2, t_out + 0.2
    key(kv, t0 - EPS, scale=(1, 1, 1))
    key(kv, t0 + 0.05, scale=(-1, 1, 1))     # turns to run left
    run_cycle(kv, legs, t0, t1, cx + 1.5, -11.5, -2.85, rate=9.0, bob=0.1, amp=0.7)
    for k in range(8):
        prop = "fork" if k % 3 != 1 else "torch"
        x0 = 9.8 + 1.15 * k + rng.uniform(-0.3, 0.3)
        y0 = -3.6 + rng.uniform(0, 0.9)
        p, plegs, _ = person(g, x0, y0, 1.05 + rng.uniform(-0.1, 0.15),
                             rng.choice(("#7a6a58", "#5b6b4a", "#8a5050", "#4f5a7a", "#6e5a7a")), prop,
                             z=0.03 + 0.003 * k)
        run_cycle(p, plegs, t0, t1 + 0.5, x0, x0 - 17.5, y0, rate=8.0, bob=0.12)
    show(g, ln["start"] - 0.3, t_out + 0.4, 0.01)


def g_fuse(ln, t_out):
    """One Kevin per division, wired up like fuses; one blows."""
    r = R()
    cx, w = r["cx"], r["w"]
    g = group("fuse", cx, 0)
    top = group("top", 0, 1.35, g)
    card(3.4, 0.7, 0, 0, top, edge=LILAC)
    label(top, "HOLDCO (me)", 0, 0, 0.32, WHITE, BLACK)
    pop_in(top, ln["start"] - 0.2)
    divs = ("CLOUD", "ADS", "ROBOTS", "LEGAL")
    sp = min(3.0, (w - 1.0) / 4)
    rect(sp * 3, 0.06, 0, 0.75, LILAC, parent=g, z=0.005)
    rect(0.06, 0.6, 0, 1.0, LILAC, parent=g, z=0.005)
    t_k, t_d, t_f, t_b = at(ln, "Kevin"), at(ln, "division,"), at(ln, "fuse"), at(ln, "blow,")
    kevs = []
    for k, d in enumerate(divs):
        x = (k - 1.5) * sp
        col = group("div", x, 0, g)
        rect(0.06, 0.4, 0, 0.55, LILAC, parent=col, z=0.005)
        card(2.3, 0.6, 0, 0.1, col, color=NAVY2)
        label(col, d, 0, 0.1, 0.3, LILAC, BLACK)
        pop_in(col, t_d - 0.3 + 0.1 * k)
        kv, _, _ = kevin(g, x, -2.55, 0.95, z=0.02)
        pop_in(kv, t_k + 0.12 * k)
        kevs.append(kv)
        tag = group("amp", x, -3.15, g)
        rect(1.0, 0.36, 0, 0, YELLOW, r=0.06, parent=tag, z=0.03)
        label(tag, "15A", 0, 0, 0.24, INK, BLACK, z=0.04)
        pop_in(tag, t_f + 0.1 * k)
    wire = rect(sp * 3 + 1.4, 0.07, 0, -1.65, "#c9ced6", parent=g, z=0.001)
    hide_until(wire, t_f)
    key(wire, t_f, scale=(0, 1, 1))
    key(wire, t_f + 0.3, scale=(1, 1, 1))
    # the second one blows: a flash, he's left charred and smoking
    x = -0.5 * sp
    boom = group("boom", x, -1.5, g)
    boom.location.z = 0.2
    pts = [((1.3 if k % 2 else 0.55) * math.cos(math.tau * k / 16), (1.3 if k % 2 else 0.55) * math.sin(math.tau * k / 16))
           for k in range(16)]
    poly(pts, YELLOW, parent=boom)
    poly([(p[0] * 0.55, p[1] * 0.55) for p in pts], WHITE, parent=boom, z=0.01)
    key(boom, SG.T0, scale=0.0)
    key(boom, t_b - EPS, scale=0.0)
    key(boom, t_b + 0.08, scale=1.4)
    key(boom, t_b + 0.3, scale=0.0)
    burnt, _, _ = kevin(g, x, -2.55, 0.95, z=0.025, charred=True)
    visible(burnt, t_b + 0.08)
    key(kevs[1], t_b + 0.08 - EPS, scale=1.0)
    key(kevs[1], t_b + 0.08, scale=0.0)
    for k in range(4):    # smoke puffs
        pf = circle(0.22 + 0.05 * k, x + 0.2 * (k % 2), -0.6, "#8a90a8", parent=g, z=0.03)
        hide_until(pf, t_b + 0.15 + 0.15 * k)
        key(pf, t_b + 0.15 + 0.15 * k, scale=0.3, loc=(x + 0.2 * (k % 2), -0.5))
        key(pf, t_b + 1.0 + 0.15 * k, scale=1.2, loc=(x - 0.3 + 0.4 * (k % 2), 0.4))
        key(pf, t_b + 1.01 + 0.15 * k, scale=0.0)
    show(g, ln["start"] - 0.3, t_out)


def g_throw(ln, t_out):
    """The hearing heats up (a spice meter), so a Kevin gets thrown in."""
    r = R()
    cx = r["cx"]
    g = group("throw", cx, 0)
    dais = group("dais", 1.2, -1.2, g)
    for k in range(3):     # senators behind the desk
        sn = group("sen", -2.0 + 2.0 * k, 0.6, dais)
        circle(0.42, 0, 0.55, SKIN, parent=sn, z=0.0)
        rect(0.9, 0.22, 0, 0.92, "#e8e8ec", r=0.1, parent=sn, z=0.01)
        rect(1.2, 0.8, 0, -0.2, "#2b2f45", r=0.2, parent=sn, z=0.0)
    card(7.0, 1.4, 0, -0.5, dais, color="#7a4a2a")
    rect(7.0, 0.16, 0, 0.2, "#9a6a3a", parent=dais, z=0.01)
    label(dais, "SENATE HEARING", 0, -0.55, 0.38, PAPER, BLACK)
    pop_in(dais, at(ln, "hearing") - 0.1)
    meter = group("meter", -4.4, -1.3, g)
    rect(0.6, 4.0, 0, 0, WHITE, r=0.3, parent=meter, z=0.0)
    circle(0.55, 0, -2.0, WHITE, parent=meter, z=0.0)
    circle(0.42, 0, -2.0, RED, parent=meter, z=0.02)
    fill = rect(0.36, 3.6, 0, -1.9, RED, anchor="center", parent=meter, z=0.01)
    t_sp = at(ln, "spicy,")
    key(fill, SG.T0, scale=(1, 0.05, 1), loc=(0, -1.9))
    key(fill, at(ln, "gets"), scale=(1, 0.05, 1), loc=(0, -1.9))
    key(fill, t_sp + 0.25, scale=(1, 1.0, 1), loc=(0, -0.1))
    for k in range(3):     # flames up the side
        fl = group("flame", 0.75, -1.0 + 1.0 * k, meter)
        poly([(-0.2, 0), (0.2, 0), (0.0, 0.6)], "#ff8a1f", parent=fl, z=0.02)
        poly([(-0.1, 0), (0.1, 0), (0.0, 0.32)], YELLOW, parent=fl, z=0.03)
        hide_until(fl, t_sp - 0.1 + 0.12 * k)
        pop_in(fl, t_sp - 0.1 + 0.12 * k)
    label(meter, "SPICY", 0, 2.4, 0.3, RED, BLACK)
    pop_in(meter, at(ln, "gets") - 0.15)
    shake(dais, t_sp + 0.1, 0.03, 6)
    t_k, t_th = at(ln, "Kevin"), at(ln, "throw.")
    kv, _, _ = kevin(g, -2.8, -3.9, 0.9, z=0.1)
    pop_in(kv, t_k)
    # thrown: a high arc, spinning, onto the hearing desk
    n = 10
    for k in range(n + 1):
        u = k / n
        key(kv, t_th + 0.6 * u, loc=(-2.8 + 4.0 * u, -3.9 + 4.6 * u * (1 - u) * 1.6 + 1.0 * u), rot=-math.tau * u)
    for k in range(3):
        ex = label(dais, "!", -2.0 + 2.0 * k, 1.7, 0.6, YELLOW, BLACK)
        pop_in(ex, t_th + 0.6 + 0.06 * k, 0.12)
    show(g, ln["start"] - 0.3, t_out)


CONTINENTS = [
    [(-6.5, 1.2), (-4.6, 1.6), (-3.8, 0.9), (-4.4, 0.2), (-5.2, -0.3), (-5.8, 0.3), (-6.6, 0.6)],
    [(-4.6, -0.5), (-3.9, -0.8), (-4.0, -1.9), (-4.5, -2.6), (-4.8, -1.6)],
    [(-2.1, 1.3), (-1.2, 1.5), (-0.9, 1.0), (-1.6, 0.7), (-2.2, 0.9)],
    [(-2.1, 0.5), (-0.9, 0.5), (-0.6, -0.4), (-1.2, -1.7), (-1.7, -1.2), (-2.3, -0.1)],
    [(-0.8, 1.6), (1.8, 1.7), (2.5, 1.0), (1.6, 0.2), (0.4, 0.3), (-0.6, 0.8)],
    [(1.4, -1.2), (2.4, -1.0), (2.6, -1.7), (1.6, -1.9)],
    [(-5.0, -3.0), (2.5, -3.0), (2.2, -3.3), (-4.7, -3.3)],
]


def g_continent(ln, t_out):
    """Spoken: 'Per division?' (four Kevins) ... 'Make it per continent' (a Kevin on every
    continent) ... 'Efficiency.' (stamped)."""
    r = R()
    cx = r["cx"]
    g = group("continent", 0, 0)
    row = group("row", cx, -1.0, g)
    for k in range(4):
        kv, _, _ = kevin(row, (k - 1.5) * 2.0, -1.6, 1.0)
    label(row, "PER DIVISION?", 0, 1.4, 0.5, WHITE, ITALIC)
    t_m, t_c, t_e = at(ln, "Make"), at(ln, "continent..."), at(ln, "Efficiency.")
    pop_in(row, ln["start"] - 0.1)
    pop_out(row, t_m - 0.2)
    world = group("world", cx + 2.0, -0.5, g)
    for pts in CONTINENTS:
        poly(pts, "#3a5aa8", parent=world, z=0.0)
    hide_until(world, t_m - 0.1)
    pop_in(world, t_m - 0.1, 0.3)
    centres = [(-5.3, 0.6), (-4.3, -1.3), (-1.6, 1.1), (-1.5, -0.4), (1.0, 1.0), (2.0, -1.45), (-1.2, -3.1)]
    for k, (x, y) in enumerate(centres):
        kv, _, _ = kevin(world, x, y - 0.45, 0.48, z=0.02)
        hide_until(kv, t_c + 0.12 * k)
        pop_in(kv, t_c + 0.12 * k, 0.18)
    stamp(world, "EFFICIENCY", -1.6, -1.0, t_e, MINT, 0.62, rot=0.12, bg=INK)
    show(g, ln["start"] - 0.3, t_out)


def hook2(ln, t_out, n=5):
    """WE NEED A / MEAT PROXY slammed in on the beat, filling the free area."""
    r = R()
    cx, w = r["cx"], r["w"]
    g = group("hook", 0, 0)
    words = ln["words"][:n]
    rows = [(words[:3], 0.95, WHITE), (words[3:], -1.6, CORAL)]
    for ws, y, col in rows:
        objs, x = [], 0.0
        for wd_ in ws:
            piv = group("hw", 0, y, g)
            ob = text(wd_["text"].strip(",.").upper(), 1.0, 0, 0, col, BEBAS, parent=piv)
            objs.append((piv, ob, width_of(ob), wd_))
        tot = sum(o[2] for o in objs) + 0.3 * (len(objs) - 1)
        s = min(3.2 if col == CORAL else 2.1, (w - 0.8) / tot)
        x = cx - tot * s / 2
        for piv, ob, wd, w_ in objs:
            piv.location.x = x + wd * s / 2
            ob.location = (-wd / 2, -0.36, 0.02)
            x += (wd + 0.3) * s
            key(piv, SG.T0, scale=0.0)
            key(piv, w_["start"] - 0.03 - EPS, scale=0.0)
            key(piv, w_["start"] - 0.03, scale=2.4 * s)
            key(piv, w_["start"] + 0.09, scale=0.94 * s)
            key(piv, w_["start"] + 0.2, scale=s)
    show(g, words[0]["start"] - 0.3, t_out, 0.01)
    return g


def g_cheaper(ln, t_out):
    """The hook, then Kevin's price tag gets slashed."""
    hook2(ln, at(ln, "a", 1) - 0.12)
    r = R()
    cx = r["cx"]
    g = group("price", cx, 0)
    kv, _, _ = kevin(g, -3.6, -3.9, 2.4, z=0.0)
    tag = group("tag", 1.6, -0.9, g)
    poly([(-2.8, 1.5), (2.2, 1.5), (3.1, 0.0), (2.2, -1.5), (-2.8, -1.5)], PAPER, parent=tag, z=0.01)
    circle(0.18, 2.3, 0, "#1a2350", parent=tag, z=0.02)
    label(tag, "KEVIN  (human)", -0.3, 1.0, 0.34, INK, BLACK)
    old = label(tag, "$85,000/yr", -0.3, 0.2, 0.62, GREY, BLACK)
    t_c = at(ln, "cheaper")
    strike = rect(3.9, 0.1, -0.3, 0.18, RED, parent=tag, z=0.03)
    key(strike, SG.T0, scale=(0, 1, 1))
    key(strike, t_c, scale=(0, 1, 1))
    key(strike, t_c + 0.2, scale=(1, 1, 1))
    new = group("new", -0.3, -0.75, tag)
    label(new, "$0.90", 0, 0, 0.95, RED, BLACK)
    hide_until(new, at(ln, "time,") - 0.1)
    pop_in(new, at(ln, "time,") - 0.1)
    ban = group("clear", 0.4, 1.75, tag)
    rect(3.0, 0.5, 0, 0, RED, r=0.08, parent=ban, z=0.04)
    label(ban, "CLEARANCE", 0, 0, 0.32, WHITE, BLACK, z=0.05)
    ban.rotation_euler.z = 0.08
    hide_until(ban, at(ln, "one") - 0.05)
    pop_in(ban, at(ln, "one") - 0.05)
    show(g, at(ln, "a", 1) - 0.1, t_out)


def g_gig(ln, t_out):
    """A gig app: Kevin takes jobs, contract terms, then the rate: ninety cents a crime."""
    r = R()
    cx = r["cx"]
    g = group("gig", cx, 0)
    ph = group("phone", -3.3, -1.05, g)
    rect(3.3, 5.8, 0, 0, "#0d0f1a", r=0.35, parent=ph, z=0.0)
    rect(3.0, 5.2, 0, 0, PAPER, r=0.18, parent=ph, z=0.01)
    rect(3.0, 0.75, 0, 2.2, "#2fbf71", r=0.18, parent=ph, z=0.02)
    label(ph, "KevinGig", 0, 2.2, 0.36, WHITE, BLACK, z=0.03)
    t_g, t_c, t_n = at(ln, "gig"), at(ln, "contract,"), at(ln, "ninety")
    jobs = [("Take the blame", "$0.90", t_g), ("Sign this (don't read)", "$0.90", t_g + 0.3),
            ("1099 · no benefits", "✓", t_c), ("Testify (Tues)", "$0.90", t_c + 0.3)]
    for k, (a, b, t) in enumerate(jobs):
        jb = group("job", 0, 1.3 - 1.0 * k, ph)
        rect(2.7, 0.82, 0, 0, WHITE, r=0.1, parent=jb, z=0.03)
        text(a, 0.2, -1.2, 0.08, INK, SEMI, parent=jb, z=0.04)
        text(b, 0.24, 1.2, -0.25, "#2fbf71", BLACK, align="RIGHT", parent=jb, z=0.04)
        pop_in(jb, t, 0.18)
    acc = group("accept", 0, -2.35, ph)
    rect(2.6, 0.5, 0, 0, "#2fbf71", r=0.25, parent=acc, z=0.03)
    label(acc, "ACCEPT ALL", 0, 0, 0.26, WHITE, BLACK, z=0.04)
    pop_in(acc, t_c + 0.5)
    pop_in(ph, ln["start"] - 0.2)
    big = group("rate", 2.6, 0.1, g)
    label(big, "$0.90", 0, 0.2, 1.5, YELLOW, BLACK)
    label(big, "PER CRIME", 0, -1.0, 0.5, WHITE, BLACK)
    hide_until(big, t_n)
    pop_in(big, t_n)
    tally = group("tally", 2.6, -2.6, g)
    label(tally, "earned today:", -0.2, 0.0, 0.3, LILAC, SEMI, align="RIGHT")
    vals = [f"${0.9 * k:.2f}" for k in range(1, 9)]
    t_a = at(ln, "crime,")
    nums = [text(v, 0.42, 0.0, -0.15, MINT, BLACK, parent=tally) for v in vals]
    sequence(nums, [t_a + 0.18 * k for k in range(len(vals))], t_out + 0.3)
    hide_until(tally, t_a)
    key(tally, t_a, scale=1.0)
    show(g, ln["start"] - 0.3, t_out)


CRIMES = [
    ("> agent run --goal 'beat Q3'", WHITE), ("✓ bribed 3 regulators", MINT), ("✓ hired a hitman (4.8★)", MINT),
    ("✓ laundered $2.1M via NFTs", MINT), ("✓ insider trading (vibes)", MINT), ("✓ forged 12 signatures", MINT),
    ("✓ blackmailed an auditor", MINT), ("✓ deleted the evidence", MINT), ("✓ tax evasion: automated", MINT),
    ("! 41 more...", YELLOW),
]


def g_crimes(ln, t_out):
    """The agent's run log, every line a crime, with a laws-broken counter; then all of it lands
    on one Kevin."""
    r = R()
    cx = r["cx"]
    g = group("crimes", cx, 0)
    term = group("term", -1.6, -1.05, g)
    card(8.6, 5.8, 0, 0, term, color=INK, edge=LINE_BLUE)
    rect(8.6, 0.45, 0, 2.68, LINE_BLUE, parent=term, z=0.01)
    label(term, "agent.log", -3.2, 2.68, 0.24, LILAC, MONO)
    t_b, t_h = at(ln, "breaks"), at(ln, "hour,")
    for k, (body, col) in enumerate(CRIMES):
        ob = text(body, 0.33, -4.0, 2.0 - 0.48 * k, col, MONO, parent=term, z=0.02)
        pop_in(ob, t_b - 0.35 + (t_h + 0.2 - t_b) * k / len(CRIMES), 0.1)
    cnt = group("count", 4.4, 1.15, g)
    label(cnt, "LAWS BROKEN", 0, 0.65, 0.28, LILAC, BLACK)
    label(cnt, "/ HOUR", 0, -0.75, 0.28, LILAC, BLACK)
    vals = [str(v) for v in (0, 4, 9, 15, 22, 28, 35, 41, 46, 50)]
    nums = [label(cnt, v, 0, -0.05, 0.9, RED if v == "50" else WHITE, BLACK) for v in vals]
    t_f = at(ln, "fifty")
    sequence(nums, [t_b + (t_f + 0.4 - t_b) * k / (len(vals) - 1) for k in range(len(vals))], t_out + 0.3)
    pop_in(cnt, t_b - 0.2)
    # "more than one man can take": a pile of crimes drops on Kevin
    t_m, t_t = at(ln, "more"), at(ln, "take,")
    kv, _, _ = kevin(g, 4.4, -3.95, 1.0, z=0.05)
    pop_in(kv, t_m - 0.1)
    for k in range(4):
        bx = group("box", 4.4 + random.Random(k).uniform(-0.2, 0.2), -1.55 + 0.42 * k, g)
        bx.location.z = 0.1
        rect(1.5, 0.4, 0, 0, RED, r=0.05, parent=bx, z=0.0)
        label(bx, ("FRAUD", "BRIBES", "MURDER", "TAX", "PERJURY", "ARSON")[k], 0, 0, 0.22, WHITE, BLACK)
        tk = t_m + 0.2 + 0.3 * k
        key(bx, SG.T0, loc=(bx.location.x, 5.5), scale=0.0)
        key(bx, tk - EPS, loc=(bx.location.x, 5.5), scale=1.0)
        key(bx, tk + 0.18, loc=(bx.location.x, -1.55 + 0.42 * k))
    t_sq = t_m + 0.2 + 0.3 * 3 + 0.18
    key(kv, t_sq, scale=1.0)
    key(kv, t_sq + 0.12, scale=(1.25, 0.75, 1))
    key(kv, t_sq + 0.3, scale=(1.15, 0.82, 1))
    show(g, ln["start"] - 0.3, t_out)


def g_field(ln, t_out):
    """A field of Kevins, row on row, sprouting across the whole wall; shareholder value up."""
    g = group("field", 0, 0)
    for k in range(6):    # furrows
        y = GY1 - 0.9 - k * 1.0
        rect(18.0, 0.5 + 0.08 * k, 0, y - 0.15, "#5a3a24" if k % 2 else "#6b4630", parent=g, z=0.0)
    t_f, t_k, t_s = at(ln, "field"), at(ln, "Kevins"), at(ln, "shareholders’")
    rng = random.Random(11)
    rows = [(GY1 - 1.05, 0.42, 21), (GY1 - 2.0, 0.52, 18), (GY1 - 3.05, 0.64, 15), (GY1 - 4.2, 0.8, 12),
            (GY1 - 5.5, 0.98, 10)]
    n = 0
    for r_, (y, s, cnt) in enumerate(rows):
        sp = 17.4 / cnt
        for i in range(cnt):
            x = -8.7 + sp * (i + 0.5) + rng.uniform(-0.1, 0.1)
            kv, _, _ = kevin(g, x, y, s, z=0.01 + 0.01 * r_)
            tp = t_f - 0.2 + (t_k + 0.5 - t_f) * rng.random()
            key(kv, SG.T0, scale=0.0, loc=(x, y - 0.6 * s))
            key(kv, tp, scale=(1.0, 0.0, 1.0), loc=(x, y - 0.6 * s))
            key(kv, tp + 0.15, scale=(1.0, 1.1, 1.0), loc=(x, y))
            key(kv, tp + 0.25, scale=1.0)
            n += 1
    sv = group("value", 6.2, 1.2, g)
    sv.location.z = 0.3
    card(4.6, 1.2, 0, 0, sv, color=INK, edge=MINT)
    label(sv, "SHAREHOLDER VALUE", 0, 0.22, 0.26, LILAC, BLACK, z=0.31)
    label(sv, "▲ 6,500%", 0, -0.27, 0.42, MINT, BLACK, z=0.31)
    hide_until(sv, t_s)
    pop_in(sv, t_s)
    show(g, ln["start"] - 0.3, t_out, 0.01)


def g_grease(ln, t_out):
    """Money pours into a briefcase for a couple of senators; then the waiver, signed."""
    r = R()
    cx = r["cx"]
    g = group("grease", cx, 0)
    bc = group("case", -1.6, -2.4, g)
    rect(4.6, 2.0, 0, 1.7, "#4a2d1a", r=0.15, parent=bc, z=0.0)        # the open lid, behind
    rect(4.2, 1.6, 0, 1.7, "#2a1a10", r=0.1, parent=bc, z=0.001)
    front = rect(4.8, 2.0, 0, -0.3, "#6b4226", r=0.15, parent=bc, z=0.3)
    rect(1.0, 0.25, 0, 0.75, GOLD, r=0.05, parent=bc, z=0.31)
    label(bc, "SEN. ×2", 0, -0.35, 0.4, GOLD, BLACK, z=0.31)
    pop_in(bc, ln["start"] - 0.2)
    t_g, t_s = at(ln, "Grease"), at(ln, "senators")
    rng = random.Random(21)
    for k in range(36):
        x = -1.6 + rng.uniform(-1.7, 1.7)
        b = bill(g, x, 5.2, 1.0, z=0.003 + 0.0002 * k)    # behind the lyrics, in front of the open lid
        tk = t_g + (t_s + 0.9 - t_g) * k / 36
        land = -2.0 + rng.uniform(-0.3, 0.6)
        rot = rng.uniform(-0.6, 0.6)
        key(b, SG.T0, loc=(x, 5.2), rot=rot)
        key(b, tk, loc=(x, 5.2), rot=rot)
        key(b, tk + 0.55, loc=(x + rng.uniform(-0.4, 0.4), land), rot=rot + rng.uniform(-1.5, 1.5))
    t_w, t_sg = at(ln, "waiver"), at(ln, "signed")
    doc = group("waiver", 3.3, -0.8, g)
    doc.location.z = 0.4
    rect(3.6, 4.6, 0, 0, PAPER, r=0.1, parent=doc, z=0.0)
    label(doc, "WAIVER", 0, 1.8, 0.5, INK, BLACK)
    label(doc, "of all laws, ever", 0, 1.3, 0.24, GREY, ITALIC)
    for k in range(5):
        rect(2.8 - 0.6 * (k % 2), 0.07, -1.4, 0.75 - 0.35 * k, "#c9c3b3", anchor="left", parent=doc, z=0.01)
    rect(2.4, 0.04, 0, -1.4, INK, parent=doc, z=0.01)
    key(doc, SG.T0, loc=(10.0, -0.8))
    key(doc, t_w - 0.25, loc=(10.0, -0.8))
    key(doc, t_w + 0.05, loc=(3.3, -0.8))
    sig = text("Sen. Kevin", 0.42, -1.1, -1.35, "#2a4fb8", SCRIPT, parent=doc, z=0.02)
    key(sig, SG.T0, scale=(0, 1, 1))
    key(sig, t_sg - 0.05, scale=(0, 1, 1))
    key(sig, t_sg + 0.35, scale=(1, 1, 1))
    stamp(doc, "APPROVED", 0.2, -0.2, t_sg + 0.45, MINT, 0.42, rot=-0.2)
    show(g, ln["start"] - 0.3, t_out)


def g_mind(ln, t_out):
    """The hook, then a diagram: Kevin's body (keep) and his mind (not required), lifted out."""
    hook2(ln, at(ln, "with") - 0.12)
    r = R()
    cx = r["cx"]
    g = group("mind", cx, 0)
    s = 2.3
    kv, _, lid = kevin(g, -1.4, -4.0, s, split_head=True)
    cut = group("cut", -1.4, -4.0 + 1.73 * s - 0.1 * s, g)
    for k in range(9):
        rect(0.14, 0.05, -0.75 * s / 2 * 1.3 + 0.24 * k, 0, RED, parent=cut, z=0.05)
    brain = group("brain", -1.4, -4.0 + 1.8 * s, g)
    for k, (bx, by, br) in enumerate(((-0.35, 0.0, 0.32), (0.0, 0.12, 0.36), (0.35, 0.0, 0.32), (-0.18, -0.15, 0.3),
                                      (0.2, -0.15, 0.3))):
        circle(br, bx, by, "#ff9fb3", parent=brain, z=0.005 + 0.001 * k)
    for k in range(3):
        poly([(-0.4 + 0.3 * k, 0.15), (-0.3 + 0.3 * k, -0.05), (-0.2 + 0.3 * k, 0.12)], "#d9667f", parent=brain,
             z=0.02, width=0.05)
    t_b, t_n, t_m = at(ln, "body,"), at(ln, "not"), at(ln, "mind.")
    pop_in(g, at(ln, "with") - 0.1, 0.01)
    hide_until(brain, t_n)
    key(brain, t_n, scale=1.0, loc=(-1.4, -4.0 + 1.8 * s))
    key(brain, t_m + 0.5, loc=(-1.4, -4.0 + 1.8 * s + 1.6))
    key(lid, t_n - EPS, loc=(0, 1.73 * s), rot=0.0)
    key(lid, t_n + 0.3, loc=(0.9, 1.73 * s + 0.9), rot=-0.5)
    body = group("lab_body", 2.4, -2.6, g)
    poly([(-2.3, 0.0), (-0.6, 0.0)], WHITE, parent=body, width=0.04)
    label(body, "BODY", 0.6, 0.25, 0.5, WHITE, BLACK)
    label(body, "✓ KEEP", 0.6, -0.4, 0.4, MINT, BLACK)
    hide_until(body, t_b)
    pop_in(body, t_b)
    mind = group("lab_mind", 2.4, 0.4, g)
    poly([(-2.6, -0.2), (-0.7, 0.0)], WHITE, parent=mind, width=0.04)
    label(mind, "MIND", 0.6, 0.25, 0.5, WHITE, BLACK)
    label(mind, "✗ NOT REQUIRED", 0.9, -0.4, 0.36, RED, BLACK)
    hide_until(mind, t_m - 0.1)
    pop_in(mind, t_m - 0.1)
    show(g, at(ln, "with") - 0.1, t_out)


def g_felonies(ln, t_out):
    """Spoken: Kevin's year: six figures... mostly felonies."""
    r = R()
    cx = r["cx"]
    g = group("felonies", cx, 0)
    kv, _, _ = kevin(g, -4.2, -3.9, 1.7)
    con, _, _ = kevin(g, -4.2, -3.9, 1.7, prison=True)     # 'Mostly felonies': in prison stripes
    cardg = group("card", 1.4, -0.9, g)
    card(8.0, 4.6, 0, 0, cardg, color=INK, edge=LINE_BLUE)
    label(cardg, "KEVIN · LAST YEAR", 0, 1.7, 0.36, LILAC, BLACK)
    t_6, t_mo, t_f = at(ln, "six"), at(ln, "Mostly"), at(ln, "felonies.")
    money = label(cardg, "$100,000+", 0, 0.2, 1.3, MINT, BLACK)
    hide_until(money, t_6)
    pop_in(money, t_6, 0.2)
    key(money, t_f - EPS, scale=1.0)
    key(money, t_f, scale=0.0)
    fel = group("fel", 0, 0.2, cardg)
    label(fel, "100,000+", 0, 0.0, 1.3, RED, BLACK)
    hide_until(fel, t_f)
    key(fel, t_f, scale=1.0)
    word = group("w", 0, -1.3, cardg)
    label(word, "FELONIES", 0, 0, 0.62, RED, BLACK)
    hide_until(word, t_f)
    pop_in(word, t_f, 0.2)
    six = label(cardg, "six figures!", 0, -1.3, 0.5, YELLOW, ITALIC)
    hide_until(six, at(ln, "figures") - 0.05)
    pop_in(six, at(ln, "figures") - 0.05)
    key(six, t_f - EPS, scale=1.0)
    key(six, t_f, scale=0.0)
    shake(cardg, t_f, 0.04, 6)
    key(kv, t_f - EPS, scale=1.0)
    key(kv, t_f, scale=0.0)
    hide_until(con, t_f)
    key(con, t_f, scale=(1.15, 0.9, 1))
    key(con, t_f + 0.12, scale=1.0)
    show(g, ln["start"] - 0.3, t_out + 0.5)


# ---------------------------------------------------------------- the deck chrome (bottom edge)
def chrome(lines, beats):
    """A small footer (the top of the wall carries the lyrics): deck title, slide counter, and an
    accent bar pulsing on the half-time beats."""
    text("INVESTOR UPDATE  ·  LIVE FROM THE YACHT", 0.24, -8.6, -4.33, "#7f8fc8", SEMI)
    for k, ln in enumerate(lines):
        t_a = ln["start"] - 0.35
        t_b = lines[k + 1]["start"] - 0.35 if k + 1 < len(lines) else SG.END + 1
        c = text(f"SLIDE {k + 31:02d} / 3", 0.24, 8.6, -4.33, "#7f8fc8", SEMI, align="RIGHT")
        hide_until(c, t_a)
        pop_in(c, t_a, 0.15)
        key(c, t_b - EPS, scale=1.0)
        key(c, t_b, scale=0.0)
    bar = rect(1.2, 0.07, -8.6, -4.0, CORAL, anchor="left")
    for b in beats:
        if b["beat"] in (1, 3):
            key(bar, b["t"] - EPS, scale=(1.0, 1.0, 1.0))
            key(bar, b["t"] + 0.06, scale=(1.9, 1.6, 1.0))
            key(bar, b["t"] + 0.35, scale=(1.0, 1.0, 1.0))


# Lines -> graphic, how the lyric is set, and where the Founder stands (side: -0.75 his left of
# the wall .. 0 centre .. 0.75 right; yacht_set.DOLLY moves the camera there just before the line).
LINES = [
    ("I fired forty", g_fired, {"side": 0}),
    ("Replaced them all", g_replaced, {"side": 0}),
    ("But the Senate", g_senate, {"side": 0}),
    ("So I'll keep", g_sacrifice, {"side": 0.75}),
    ("One Kevin per", g_fuse, {"side": -0.75}),
    ("When the hearing", g_throw, {"side": -0.75}),
    ("Per division", g_continent, {"side": 0.75, "spoken": True}),
    ("We need a meat proxy, a cheaper", g_cheaper, {"side": -0.75, "skip": 5}),
    ("Make him gig", g_gig, {"side": -0.75}),
    ("The bot breaks", g_crimes, {"side": 0.75}),
    ("So we'll farm", g_field, {"side": 0}),
    ("Grease a couple", g_grease, {"side": -0.75}),
    ("We need a meat proxy, with", g_mind, {"side": 0.75, "skip": 5}),
    ("Kevin cleared", g_felonies, {"side": 0.75, "spoken": True}),
]
