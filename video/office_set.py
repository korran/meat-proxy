"""The Manager's office: a huge open-plan floor built from toy bricks, after hours. 56 empty desks,
every monitor still running a coding agent, a 100" screen at the front with the Manager
standing beside it, night city through the windows. Built for the intro's camera fly-through.

  python3 video/office_textures.py video/build/office      (screen and poster images; run
                                                           automatically if they're missing)
  blender -b --factory-startup --python video/office_set.py -- --out video/build/office_stills \\
      [--preview] [--res 1080] [--fly]

Layout, in studs (one stud = 0.136 units, see bricks.py). The room runs x -40..40 (left to right
as seen from the back door) and y 0..92 (back wall to front wall); everyone faces +y, the front.
  y  0..12   back: door, printer, water cooler, filing cabinets
  y 12..68   7 rows of 8 desks (4 pairs, aisles between pairs, a wide centre aisle)
  y 68..92   front: a low stage, the big screen on the front wall, the Manager
Walls are 10 bricks tall; the side walls are mostly windows.
"""
import math
import os
import random
import subprocess
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402
from bricks import BR, P, PL, Kit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "build", "office")

X0, X1, Y0, Y1 = -40, 40, 0, 92          # inside of the walls, in studs
H = 30                                    # wall height, plates (10 bricks)
PAIRS = [-32, -16, 4, 20]                 # left edge of each pair of desks (two 6-stud desks)
ROWS = [12 + 8 * r for r in range(7)]     # each row: chair zone, then the desk at +5..+8
DESK_W, DESK_D = 6, 3
STAGE = (-18, 18, 76, 92)                 # x0, x1, y0, y1
SCREEN_X = (-7, 3)                        # the big screen's span on the front wall (studs)
MANAGER = (4.5, 87.5)                     # where the Manager stands (stud coords of his centre)
KEVIN = (8.5, 87.5)                       # Kevin, to the Manager's right (screen right)

# colours
CARPET, AISLE = "#4a5160", "#9aa1ad"
WALL, TRIM, WALL_DARK = "#b8bcc3", "#f4f4f2", "#a7acb3"
DESK_TOP, DESK_LEG, CHAIR, CHAIR_SEAT = "#eef0f2", "#5a606b", "#26292f", "#2f4b7c"
MON, KEYS = "#1b1d22", "#3a3e46"
CEIL, LIGHT = "#c3c7cd", "#f6f8ff"


def textures():
    if not os.path.exists(os.path.join(TEX, "monitor9_log.png")):
        subprocess.run(["python3", os.path.join(HERE, "office_textures.py"), TEX], check=True)


def image_material(name, path, strength=1.0, emit=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    if emit:
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = strength
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    else:
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Roughness"].default_value = 0.6
        nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
        nt.links.new(bs.outputs[0], out.inputs["Surface"])
    return m


LOG_LINE, LOG_H, SCREEN_H = 22, 3960, 512     # log strip line height and height, screen height (px)


def terminal_material(k, strength=1.6):
    """A monitor running the agent: the log strip (scrolling, wrapping) behind a fixed frame
    (title bar, prompt, status bar). The scroll position is the mapping node's Y location."""
    m = bpy.data.materials.new(f"terminal{k}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.name = "scroll"
    mp.inputs["Scale"].default_value = (1.0, SCREEN_H / LOG_H, 1.0)
    mp.inputs["Location"].default_value = (0.0, 1.0 - SCREEN_H / LOG_H, 0.0)
    log = nt.nodes.new("ShaderNodeTexImage")
    log.image = bpy.data.images.load(os.path.join(TEX, f"monitor{k}_log.png"), check_existing=True)
    log.extension = "REPEAT"
    frame = nt.nodes.new("ShaderNodeTexImage")
    frame.image = bpy.data.images.load(os.path.join(TEX, f"monitor{k}_frame.png"), check_existing=True)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], log.inputs["Vector"])
    nt.links.new(uv.outputs["UV"], frame.inputs["Vector"])
    nt.links.new(frame.outputs["Alpha"], mix.inputs["Factor"])
    nt.links.new(log.outputs["Color"], mix.inputs["A"])
    nt.links.new(frame.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def animate_terminals(mats, n, fps, seed=21):
    """Scroll each terminal like real output arriving: whole lines at a time, in bursts (a few
    lines a frame, sometimes a whole diff at once), with pauses while the agent 'thinks'."""
    for k, m in enumerate(mats):
        rng = random.Random(seed + k)
        sock = m.node_tree.nodes["scroll"].inputs["Location"]
        y0 = 1.0 - SCREEN_H / LOG_H
        lines, f, prev = rng.randint(0, 150), 1, None
        while f <= n:
            if rng.random() < 0.55:                           # a burst of output
                for _ in range(int(rng.uniform(0.1, 0.7) * fps / 2)):
                    lines += rng.choice((1, 1, 1, 2, 2, 3, 5))
                    if f > n:
                        break
                    sock.default_value[1] = y0 - lines * LOG_LINE / LOG_H
                    sock.keyframe_insert("default_value", index=1, frame=f)
                    f += 2                                     # a new chunk every other frame
            else:                                             # thinking...
                if rng.random() < 0.3:                        # ...then a big chunk lands at once
                    f += int(rng.uniform(0.15, 0.5) * fps)
                    lines += rng.randint(4, 9)
                    sock.default_value[1] = y0 - lines * LOG_LINE / LOG_H
                    sock.keyframe_insert("default_value", index=1, frame=min(f, n))
                f += int(rng.uniform(0.1, 0.9) * fps)
        for fc in m.node_tree.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def glass_material():
    m = bpy.data.materials.new("glass")
    m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (0.75, 0.85, 0.95, 1)
    bs.inputs["Roughness"].default_value = 0.04
    bs.inputs["Alpha"].default_value = 0.12
    m.surface_render_method = "BLENDED"
    return m


def picture(col, name, mat, centre, size, facing):
    """A flat picture (screen, poster) with its image filling it. facing: the direction its front
    looks, "-y", "+y", "-x" or "+x"."""
    w, h = size
    cx, cy, cz = centre
    if facing in ("-y", "+y"):
        s = 1 if facing == "-y" else -1
        verts = [(cx - s * w / 2, cy, cz - h / 2), (cx + s * w / 2, cy, cz - h / 2),
                 (cx + s * w / 2, cy, cz + h / 2), (cx - s * w / 2, cy, cz + h / 2)]
    else:
        s = 1 if facing == "+x" else -1
        verts = [(cx, cy - s * w / 2, cz - h / 2), (cx, cy + s * w / 2, cz - h / 2),
                 (cx, cy + s * w / 2, cz + h / 2), (cx, cy - s * w / 2, cz + h / 2)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


# ---------------------------------------------------------------- walls
def wall_run(K, axis, fixed, a0, a1, z0, z1, color, openings=(), thick=1, studs_top=False):
    """A running-bond wall of 1x4 bricks along x or y (axis), one stud thick at `fixed`, from a0 to
    a1 (studs) and z0 to z1 (plates, whole bricks). openings: [(a0, a1, z0, z1)] left empty."""
    for course, z in enumerate(range(z0, z1, 3)):
        free = []
        for a in range(a0, a1):
            if not any(o0 <= a < o1 and oz0 <= z < oz1 for o0, o1, oz0, oz1 in openings):
                free.append(a)
        # split the free cells into runs, then into bricks of up to 4 on the bond grid
        runs, start = [], None
        for a in free + [None]:
            if start is None:
                start = prev = a
            elif a is None or a != prev + 1:
                runs.append((start, prev + 1))
                start = prev = a
            else:
                prev = a
        off = 2 if course % 2 else 0
        top = studs_top and z + 3 >= z1
        for r0, r1 in runs:
            a = r0
            while a < r1:
                nxt = min(r1, a + 4 - ((a - a0 + off) % 4))
                if axis == "y":
                    K.brick(fixed, a, z, thick, nxt - a, color, studs=top)
                else:
                    K.brick(a, fixed, z, nxt - a, thick, color, studs=top)
                a = nxt


def build_room(K, col):
    # floor: dark studded baseplates; a smooth tiled centre aisle and stage
    K.box(X0 * P - 0.2, Y0 * P - 0.2, -0.03, X1 * P + 0.2, Y1 * P + 0.2, 0.0, CARPET)
    for x in range(X0, X1):
        for y in range(Y0, Y1):
            if -4 <= x < 4 and 6 <= y < STAGE[2]:
                continue
            if STAGE[0] <= x < STAGE[1] and y >= STAGE[2]:
                continue
            K.studs(x, y, 0, 1, 1, CARPET)
    for y in range(6, STAGE[2], 2):              # centre-aisle runner: 2x8 tiles
        K.tile(-4, y, 0, 8, 2, AISLE)
    for x in range(STAGE[0], STAGE[1], 4):       # stage: two plates, tiled
        for y in range(STAGE[2], STAGE[3], 4):
            K.plate(x, y, 0, 4, 4, WALL_DARK, studs=False)
            K.tile(x, y, 1, 4, 4, "#e6e8ec")

    # side walls: brick piers with tall windows between them, a sill and a header
    win = []
    for y in range(Y0 + 4, Y1 - 4, 10):
        win.append((y + 2, y + 9, 3, 27))
    for x, outward in ((X0 - 1, -1), (X1, 1)):
        wall_run(K, "y", x, Y0, Y1, 0, H, WALL, openings=win)
        for y0, y1, z0, z1 in win:                # white frames and a mullion
            K.box(x * P, y0 * P, z0 * PL, (x + 1) * P, y1 * P, z0 * PL + 0.02, TRIM)
            K.box(x * P, y0 * P, z1 * PL - 0.02, (x + 1) * P, y1 * P, z1 * PL, TRIM)
            for yy in (y0, (y0 + y1) / 2, y1):
                K.box(x * P + 0.03, yy * P - 0.012, z0 * PL, (x + 1) * P - 0.03, yy * P + 0.012, z1 * PL, TRIM)
            K.box((x + 0.45) * P, y0 * P, z0 * PL, (x + 0.55) * P, y1 * P, z1 * PL, "glass", kind="glass")
    # back wall with a door; front wall solid
    door = (-3, 3, 0, 21)
    wall_run(K, "x", Y0 - 1, X0 - 1, X1 + 1, 0, H, WALL, openings=[door])
    wall_run(K, "x", Y1, X0 - 1, X1 + 1, 0, H, WALL)
    K.box(-3 * P, (Y0 - 0.9) * P, 0, 3 * P, (Y0 - 0.1) * P, 21 * PL, "#8a5a3b")          # door
    K.box(-3.2 * P, (Y0 - 0.2) * P, 0, -2.8 * P, Y0 * P + 0.01, 21.4 * PL, TRIM)       # frame
    K.box(2.8 * P, (Y0 - 0.2) * P, 0, 3.2 * P, Y0 * P + 0.01, 21.4 * PL, TRIM)
    K.box(-3.2 * P, (Y0 - 0.2) * P, 21 * PL, 3.2 * P, Y0 * P + 0.01, 21.4 * PL, TRIM)
    K.round(1.6, Y0 - 0.2, 9, 1, 1, "#d8c27a", studs=False)                          # handle
    K.box(-1.2 * P, Y0 * P, 22.5 * PL, 1.2 * P, Y0 * P + 0.04, 24.5 * PL, "#2fd36b", kind="glow")  # EXIT

    # baseboards
    for x in (X0, X1 - 1):
        K.tile(x, Y0, 0, 1, Y1 - Y0, WALL_DARK)
    # columns: 2x2 brick stacks along the side margins
    for x in (X0 + 5, X1 - 7):
        for y in (20, 36, 52, 68):
            for z in range(0, H, 3):
                K.brick(x, y, z, 2, 2, WALL, studs=False)

    # ceiling: big plates seen from below, light panels in a grid
    for x in range(X0 - 1, X1 + 1, 8):
        for y in range(Y0 - 1, Y1 + 1, 8):
            K.piece(x, y, H, 8, 8, 1, CEIL, studs=False)
    lights = []
    rng = random.Random(5)
    for x in (-28, -12, 4, 20):
        for y in range(10, Y1, 12):
            on = (-12 <= x <= 4) or rng.random() < 0.35      # after hours: most side panels are off
            K.box((x + 1) * P, y * P, (H - 0.35) * PL, (x + 7) * P, (y + 3) * P, H * PL,
                  LIGHT if on else "#9aa0aa", kind="glow" if on else None)
            if on:
                lights.append(((x + 4) * P, (y + 1.5) * P, (H - 0.4) * PL))
    return lights


# ---------------------------------------------------------------- desks
def build_desk(K, x, y, rng):
    """One desk, its corner at stud (x, y): legs, a tiled top, a monitor (screen added later),
    keyboard, mouse and maybe a mug, plant, papers or second monitor. Returns screen centres."""
    for lx in (x, x + DESK_W - 1):                       # leg panels
        K.brick(lx, y, 0, 1, DESK_D, DESK_LEG, h=4, studs=False)
    K.plate(x, y, 4, DESK_W, DESK_D, DESK_LEG, studs=False)
    K.tile(x, y, 5, 3, DESK_D, DESK_TOP)
    K.tile(x + 3, y, 5, 3, DESK_D, DESK_TOP)
    K.box((x + 1) * P, (y + DESK_D - 0.2) * P, 0.5 * PL, (x + DESK_W - 1) * P, (y + DESK_D) * P - 0.003,
          4 * PL, DESK_LEG)                              # modesty panel at the front
    screens = []
    two = rng.random() < 0.12
    for k, mx in enumerate((x + 1.5, x + 4.5) if two else (x + 3,)):
        K.round(mx - 0.5, y + 1.5, 6, 1, 1, MON, studs=False)               # foot
        K.box((mx - 0.08) * P, (y + 1.9) * P, 7 * PL, (mx + 0.08) * P, (y + 2.05) * P, 9 * PL, MON)   # neck
        w = 2.4 if two else 2.8
        z0, z1 = 8.2 * PL, 8.2 * PL + w * P * 0.66
        K.box((mx - w / 2) * P, (y + 1.85) * P, z0, (mx + w / 2) * P, (y + 2.1) * P, z1, MON)
        screens.append(((mx * P, (y + 1.85) * P - 0.002, (z0 + z1) / 2), ((w - 0.2) * P, (z1 - z0) - 0.2 * P)))
    K.tile(x + 1.5, y + 0.3, 6, 3, 1, KEYS)                                    # keyboard
    K.round(x + 4.6, y + 0.3, 6, 1, 0.6, "#e9ebef", studs=False)            # mouse
    if rng.random() < 0.35:                                                  # coffee mug
        K.round(x + 0.3 if rng.random() < 0.5 else x + 5.0, y + 0.6, 6, 1, 2.2,
                rng.choice(("white", "#ff6a1f", "#3a6ed8")), studs=False)
    if rng.random() < 0.18:                                                  # a little plant
        px = x + 0.2 if rng.random() < 0.5 else x + 4.9
        K.round(px, y + 1.8, 6, 1, 2, "#b5653a", studs=False)
        K.round(px - 0.15, y + 1.65, 8, 1.3, 2, "#3f9c4a", studs=False)
        K.round(px, y + 1.8, 10, 1, 1.5, "#56b85e", studs=False)
    if rng.random() < 0.25:                                                  # paper stack
        for k in range(rng.randint(1, 4)):
            K.tile(x + 4.0 + 0.1 * rng.random(), y + 0.9 + 0.1 * rng.random(), 6 + 0.35 * k, 1.6, 1.2, "white")
    return screens


def chair_kit(B):
    """An office chair, centred on the origin, seat facing +y."""
    K = Kit(B)
    K.round(-1, -1, 0, 2, 0.6, CHAIR, studs=False)          # star base, as a round plate
    K.round(-0.5, -0.5, 0.6, 1, 2.2, "#8a8f98", studs=False)  # gas lift
    K.plate(-1, -1, 2.8, 2, 2, CHAIR_SEAT, studs=False)
    K.box(-1 * P + 0.004, -1 * P, 3.8 * PL, 1 * P - 0.004, -0.75 * P, 3.8 * PL + 2 * BR, CHAIR_SEAT)  # back
    K.box(-0.2 * P, -1 * P + 0.004, 3 * PL, 0.2 * P, -0.8 * P, 4.5 * PL, CHAIR)
    return K.build("chair_proto")


def place_figure(fn, B, loc):
    """Build a cast member (it is built at the origin, facing -y) and move it to loc."""
    before = set(bpy.data.objects)
    fn(B)
    root = bpy.data.objects.new(f"{fn.__name__}_root", None)
    B.col.objects.link(root)
    for ob in set(bpy.data.objects) - before:
        if ob.parent is None and ob is not root:
            ob.parent = root
    root.location = loc
    return root


# ---------------------------------------------------------------- the set
def movie_material(name, path, offset=0, strength=2.0):
    """A screen playing a video (e.g. the lossless screen graphics), its frame 1 on scene frame
    1 + offset."""
    m = image_material(name, path, strength)
    tex = next(n for n in m.node_tree.nodes if n.type == "TEX_IMAGE")
    img = tex.image
    img.source = "MOVIE"
    iu = tex.image_user
    iu.frame_duration = img.frame_duration
    iu.frame_start = 1 + offset
    iu.frame_offset = 0
    iu.use_auto_refresh = True
    return m


def build(sc, seed=11, manager=True, kevin=True, screen_video=None, screen_offset=0):
    textures()
    col = sc.collection
    B = SL.Builder("fig", col)
    B.mats[("glass", "glass")] = glass_material()
    K = Kit(B)
    rng = random.Random(seed)
    lights = build_room(K, col)
    screens = []
    for y in ROWS:
        for x0 in PAIRS:
            for x in (x0, x0 + DESK_W):
                screens += build_desk(K, x, y + 5, rng)
    # filing cabinets along the back wall, a printer, a water cooler
    for x in list(range(X0 + 1, -8, 3)) + list(range(10, X1 - 2, 3)):
        if X0 + 8 < x < X0 + 14:
            continue
        for z in range(0, 12, 3):
            K.brick(x, Y0, z, 2, 2, "#8e949d", studs=z == 9)
            K.box((x + 0.6) * P, (Y0 + 2) * P, (z + 1.3) * PL, (x + 1.4) * P, (Y0 + 2.08) * P, (z + 1.7) * PL,
                  "#c9ced6")
    K.brick(X0 + 9, Y0, 0, 4, 3, "#d9dbe0", h=6, studs=False)               # printer
    K.tile(X0 + 9, Y0, 6, 4, 3, "#3a3e46")
    K.brick(X1 - 6, Y0 + 1, 0, 2, 2, "white", h=9, studs=False)             # water cooler
    K.round(X1 - 6, Y0 + 1, 9, 2, 5, "#7fc6f2", studs=False, kind="glass")
    for x, y in ((X0 + 2, Y1 - 3), (X1 - 4, Y1 - 3), (X0 + 2, Y0 + 9), (X1 - 4, Y0 + 9)):   # big plants
        K.round(x, y, 0, 2, 6, "#b5653a", studs=False)
        for k, (dz, s) in enumerate(((6, 3.0), (11, 2.4), (15, 1.6))):
            K.round(x + 1 - s / 2, y + 1 - s / 2, dz, s, 5, "#3f9c4a" if k % 2 else "#56b85e", studs=False)
    # the big screen on the front wall: black bezel, the slide, a little soundbar
    sx0, sx1 = SCREEN_X
    zc, sw = 0.7, (sx1 - sx0) * P            # low on the wall: its bottom at about his waist
    sh = sw * 9 / 16
    K.box(sx0 * P - 0.03, Y1 * P - 0.05, zc - sh / 2 - 0.03, sx1 * P + 0.03, Y1 * P, zc + sh / 2 + 0.03, MON)
    K.box((sx0 + 3) * P, Y1 * P - 0.07, zc - sh / 2 - 0.08, (sx1 - 3) * P, Y1 * P, zc - sh / 2 - 0.05, MON)
    room = K.build("office")
    chair = chair_kit(B)
    chair.location = (0, 0, 0)
    chair.hide_render = True
    for y in ROWS:
        for x0 in PAIRS:
            for x in (x0, x0 + DESK_W):
                c = chair.copy()
                col.objects.link(c)
                c.hide_render = False
                c.location = ((x + 3 + rng.uniform(-0.8, 0.8)) * P, (y + 3.2 + rng.uniform(-0.6, 0.8)) * P, 0)
                c.rotation_euler.z = rng.uniform(-0.5, 0.5) + (math.pi if rng.random() < 0.08 else 0)
    # screens
    mons = [terminal_material(k) for k in range(10)]
    for k, (centre, size) in enumerate(screens):
        picture(col, f"screen{k}", mons[rng.randrange(len(mons))], centre, size, "-y")
    slide = (movie_material("slide", screen_video, screen_offset) if screen_video else
             image_material("slide", os.path.join(TEX, "slide.png"), 2.0))
    picture(col, "slide", slide,
            ((sx0 + sx1) / 2 * P, Y1 * P - 0.052, zc), (sw, sh), "-y")
    # posters on the back wall, night city outside the windows
    for k, x in enumerate((-20, -12, 12)):
        picture(col, f"poster{k}", image_material(f"poster{k}", os.path.join(TEX, f"poster{k}.png"), 0.6, emit=False),
                (x * P, Y0 * P + 0.004, 0.95), (0.42, 0.59), "+y")
    city = image_material("city", os.path.join(TEX, "skyline.png"), 1.3)
    for x, f in ((X0 * P - 3.0, "+x"), (X1 * P + 3.0, "-x")):
        picture(col, f"city{f}", city, (x, Y1 * P / 2, 1.0), (24.0, 6.0), f)
    # the Manager by the screen, on the stage
    mgr = place_figure(SL.build_manager, B, manager_spot()) if manager else None
    kev = None
    if kevin:   # Kevin waits on the stage, turned a little toward the Manager
        kev = place_figure(SL.build_kevin_fig, B, (KEVIN[0] * P, KEVIN[1] * P, 2 * PL))
        kev.rotation_euler.z = -0.35
    lighting(sc, lights)
    return {"room": room, "manager": mgr, "screen": (((sx0 + sx1) / 2 * P, Y1 * P, zc)), "terminals": mons, "kevin": kev}


def manager_spot():
    """Where the Manager stands: on the stage, beside the screen (world units)."""
    return (MANAGER[0] * P, MANAGER[1] * P, 2 * PL)


def lighting(sc, lights):
    """After hours: dim ceiling lights, the glow of every monitor, a cool night through the windows."""
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.02, 0.03, 0.07, 1)
    bg.inputs[1].default_value = 0.6
    for k, loc in enumerate(lights):
        ld = bpy.data.lights.new(f"ceil{k}", "AREA")
        ld.energy, ld.size, ld.color = 14, 0.8, (0.92, 0.95, 1.0)
        lo = bpy.data.objects.new(f"ceil{k}", ld)
        sc.collection.objects.link(lo)
        lo.location = loc
    for k, (x, y) in enumerate(((X0 * P - 0.8, 4.0), (X1 * P + 0.8, 7.0))):   # moonlight through the windows
        ld = bpy.data.lights.new(f"moon{k}", "AREA")
        ld.energy, ld.size, ld.color = 260, 6.0, (0.55, 0.65, 1.0)
        lo = bpy.data.objects.new(f"moon{k}", ld)
        sc.collection.objects.link(lo)
        lo.location = (x, y, 1.6)
        SL.aim(lo, (0, y, 0))
    ld = bpy.data.lights.new("screenglow", "AREA")    # the big screen lights the stage
    ld.energy, ld.size, ld.color = 40, 1.2, (0.6, 0.65, 1.0)
    lo = bpy.data.objects.new("screenglow", ld)
    sc.collection.objects.link(lo)
    lo.location = ((SCREEN_X[0] + SCREEN_X[1]) / 2 * P, Y1 * P - 0.3, 0.85)
    SL.aim(lo, (0, Y1 * P - 3, 0.3))


def preview_lights(on):
    """The ceiling lights cast no shadows: they point straight down, so their shadows barely
    show, but they're re-rendered whenever the camera moves (a preview is about five times slower
    with them) and they overflow EEVEE's shadow memory, which drops other shadows. The key, fill,
    rim, moon and screen lights keep theirs."""
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.name.startswith("ceil"):
            ob.data.use_shadow = False


def setup_render(sc, res, preview):
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = res
    sc.render.resolution_x = res * 16 // 9
    sc.eevee.taa_render_samples = 1 if preview else 32
    sc.eevee.use_raytracing = not preview
    sc.eevee.use_fast_gi = not preview
    sc.eevee.shadow_pool_size = "1024"
    preview_lights(preview)
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"


def camera(sc, loc, target, lens=28):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start = 0.02
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    cam.location = loc
    SL.aim(cam, target)
    sc.camera = cam
    return cam


# camera positions for the check stills: (name, location, target, lens)
STILLS = [
    ("door", (0.0, 0.5, 0.62), (0.0, 9.0, 0.45), 24),
    ("aisle", (0.25, 3.6, 0.42), (-0.6, 5.4, 0.42), 30),
    ("wide", (-4.8, 0.5, 1.45), (1.0, 7.5, 0.2), 20),
    ("front", (1.0, 9.6, 0.62), (0.3, 12.3, 0.72), 30),
]


# The stage shot: in close, looking at a point between the big screen and the Manager, so the
# screen fills much of the frame (it will carry lyrics and graphics). Kevin is out of frame.
# (centre, distance, height, lens)
STAGE_VIEW = ((0.15, 12.25, 0.58), 2.95, 0.55, 52)   # frames the screen's edges closely, and his feet
# The Kevin shot: dollied over to the right, looking back past Kevin at the Manager, with the
# screen behind the Manager. (location, target, lens)
KEVIN_SHOT = ((1.0, 9.5, 0.63), (0.47, 11.94, 0.55), 49)


def stage_pose(ang=0.0, dist=None, dz=0.0):
    """Camera (location, target, lens) for the stage shot, swung by `ang` around its centre."""
    (cx, cy, cz), d0, h, lens = STAGE_VIEW
    d = d0 if dist is None else dist
    return (cx + d * math.sin(ang), cy - d * math.cos(ang), h + dz), (cx, cy, cz), lens


# intro fly-through: (time s, camera location, look-at target, lens). From the back door, low
# down the centre aisle between the glowing monitors, a slow glide that is still settling onto
# the stage shot as the verse starts (the performance continues from there without a cut).
FLY = [
    (0.0, (0.0, 0.3, 0.78), (0.0, 6.0, 0.5), 22),
    (3.5, (0.05, 2.9, 0.52), (0.0, 9.0, 0.45), 24),
    (7.0, (-0.3, 5.6, 0.40), (0.25, 10.5, 0.5), 26),
    (10.5, (0.1, 7.9, 0.58), (0.05, 12.2, 0.6), 34),
    (14.0, *stage_pose()),
]


def fly_pose(t):
    """Camera (location, look-at target, lens) at time t of the fly-through: Catmull-Rom through
    the FLY points, eased so it glides in and settles at the end."""
    pts, T = FLY, FLY[-1][0]

    def cr(p0, p1, p2, p3, t):
        return [0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3)
                for a, b, c, d in zip(p0, p1, p2, p3)]

    u = min(1.0, max(0.0, t / T))
    u = u * u * (3 - 2 * u)       # eases out of the start and gently to a stop on the stage shot
    t = u * T
    k = max(0, min(len(pts) - 2, max(i for i in range(len(pts)) if pts[i][0] <= t)))
    s = (t - pts[k][0]) / (pts[k + 1][0] - pts[k][0])
    q = [pts[max(0, k - 1)], pts[k], pts[k + 1], pts[min(len(pts) - 1, k + 2)]]
    return cr(*[p[1] for p in q], s), cr(*[p[2] for p in q], s), cr(*[(p[3],) for p in q], s)[0]


def fly(sc, fps, seconds):
    """Keyframe the fly-through camera on every frame."""
    cam = camera(sc, FLY[0][1], FLY[0][2], FLY[0][3])
    n = int(round(seconds * fps))
    for f in range(n + 1):
        loc, tgt, lens = fly_pose(f / fps)
        cam.location = loc
        SL.aim(cam, tgt)
        cam.data.lens = lens
        cam.keyframe_insert("location", frame=f + 1)
        cam.keyframe_insert("rotation_euler", frame=f + 1)
        cam.data.keyframe_insert("lens", frame=f + 1)
    sc.frame_start, sc.frame_end = 1, n
    sc.render.fps = fps
    return cam


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "build", "office_stills"))
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--only", help="comma-separated still names")
    ap.add_argument("--fly", action="store_true", help="render the intro fly-through instead of stills")
    ap.add_argument("--fps", type=int, default=60)
    A = ap.parse_args(argv)
    res = A.res or (540 if A.preview else 1080)
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    S = build(sc)
    setup_render(sc, res, A.preview)
    os.makedirs(A.out, exist_ok=True)
    if A.fly:
        fly(sc, A.fps, FLY[-1][0])
        animate_terminals(S["terminals"], sc.frame_end, A.fps)
        sc.render.image_settings.file_format = "FFMPEG"
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        sc.render.ffmpeg.constant_rate_factor = "HIGH"
        sc.render.use_motion_blur = not A.preview
        sc.render.filepath = os.path.join(A.out, "fly.mp4")
        bpy.ops.render.render(animation=True)
        print("FLY", sc.render.filepath)
        return
    for name, loc, tgt, lens in STILLS:
        if A.only and name not in A.only.split(","):
            continue
        camera(sc, loc, tgt, lens)
        sc.render.filepath = os.path.join(A.out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__":
    main()
