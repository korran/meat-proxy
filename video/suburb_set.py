"""The instrumental: a drone flies over a brick-built suburb while, in time-lapse, the houses are
knocked down and datacenters rise in their place; then it swings over to a house outside the
construction zone and flies in through its front window. Inside, the User is zonked out on the
sofa with their phone, and their toddler sits on the rug watching v9 smile from an iPad. The
camera pushes on into the iPad (the next shot, cyberspace, starts there).

  blender -b --factory-startup --python video/suburb_set.py -- --out video/build/suburb_stills \\
      [--preview] [--flat] [--res 1080] [--only wide,mid]
  ... -- --fly [--preview|--flat]      the whole drone shot as a silent video

Layout, in studs (one stud = 0.136 units, see bricks.py). A grid of COLS x ROWS blocks; each block
is two rows of four lots back to back (the south row faces -y, the north row +y), with roads
between blocks. Columns 0..ZONE_COLS-1 are the construction zone (every house there goes, a
datacenter per block); the last column survives behind a fence, and the drone ends at TARGET,
a house on its south side, through the picture window on its front (-y) wall.
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
from office_set import camera, fly_pose, glass_material, image_material, picture, place_figure, wall_run  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "build", "suburb")

LOT_W, LOT_D = 28, 30                  # a lot, studs
LOTS = 4                               # lots per row in a block
ROAD = 14                              # road width incl. sidewalks
BLK_W, BLK_D = LOT_W * LOTS, LOT_D * 2
PITCH_X, PITCH_Y = BLK_W + ROAD, BLK_D + ROAD
COLS, ROWS, ZONE_COLS = 4, 3, 3
HOUSE_W, HOUSE_D = 18, 14              # house footprint
WALL_H = 24                            # plates (8 bricks): one tall storey
TARGET = (3, 1, 0, 0)                  # (block col, block row, lot, row in block: 0 south) - the house we enter
SHOT_START = 148.6                     # song time the shot starts (the bridge ends)
SHOT_LEN = 17.6                        # ...and its length: still pushing into the iPad as v9's first line
                                       # starts (164.9); the cut to cyberspace comes at about 166.2

LAWN, LAWN2, ROAD_C, WALK, LINE = "#4f9a3e", "#5aa646", "#3a3d42", "#b8bcc3", "#e8c15a"
WALLS = ["#e6d3a3", "#a9c4dd", "#f2f2ee", "#a8bf9a", "#f0dc8c", "#d9a98c"]
ROOFS = ["#8a2f2a", "#4a4d55", "#6b4a2e", "#2f4b7c"]
TRIM, DOOR, GLASS_C = "#f4f4f0", "#6b3a22", "#9fd0f0"
DC_WALL, DC_RIB, DC_DARK, CRANE = "#c9cdd2", "#8a8f99", "#2b2f37", "#f2c230"


def block_origin(bx, by):
    return bx * PITCH_X, by * PITCH_Y


def lot_origin(bx, by, lot, row):
    """Corner of a lot (studs) and which way its front faces (-1: -y, +1: +y)."""
    ox, oy = block_origin(bx, by)
    return ox + lot * LOT_W, oy + row * LOT_D, (-1 if row == 0 else 1)


# ---------------------------------------------------------------- ground
def build_ground(K):
    """Lawns (plates, no studs except near the target house), roads with sidewalks and a dashed
    centre line."""
    W, D = COLS * PITCH_X + ROAD, ROWS * PITCH_Y + ROAD
    x0, y0 = -ROAD, -ROAD
    K.box(x0 * P, y0 * P, -0.06, (x0 + W) * P, (y0 + D) * P, -PL, ROAD_C)
    # farmland out to the horizon, round the suburb
    K.box(-400, -400, -0.09, 400, 400, -0.065, "#5f8f45", kind="matte")
    for bx in range(COLS):
        for by in range(ROWS):
            ox, oy = block_origin(bx, by)
            K.piece(ox - 2, oy - 2, -1, BLK_W + 4, BLK_D + 4, 1, WALK, studs=False)         # sidewalk ring
            for lot in range(LOTS):
                for row in range(2):
                    lx, ly, _ = lot_origin(bx, by, lot, row)
                    col = LAWN if (lot + row) % 2 else LAWN2
                    near = (bx, by) == TARGET[:2]
                    K.piece(lx, ly, 0, LOT_W, LOT_D, 1, col, studs=near)
    # dashed centre lines
    for by in range(ROWS + 1):
        y = by * PITCH_Y - ROAD / 2 - 0.25
        for x in range(-ROAD, COLS * PITCH_X, 8):
            K.box(x * P, y * P, -PL + 0.002, (x + 4) * P, (y + 0.5) * P, -PL + 0.004, LINE)
    for bx in range(COLS + 1):
        x = bx * PITCH_X - ROAD / 2 - 0.25
        for y in range(-ROAD, ROWS * PITCH_Y, 8):
            K.box(x * P, y * P, -PL + 0.002, (x + 0.5) * P, (y + 4) * P, -PL + 0.004, LINE)


def tree(K, x, y, s=1.0):
    K.round(x - 0.5, y - 0.5, 1, 1, 6, "#6b4a2e", studs=False)
    for k, (dz, d) in enumerate(((5, 5.0), (9, 4.0), (12.5, 2.6))):
        K.round(x - d * s / 2, y - d * s / 2, 1 + dz, d * s, 4, "#3f8f3c" if k % 2 else "#4fa34a", studs=False)


def car(K, x, y, color, along_y=True):
    """A little brick car, its corner at stud (x, y): 2 x 4, along y (or x)."""
    w, d = (2, 4) if along_y else (4, 2)
    K.plate(x, y, 1, w, d, "#2a2a30", studs=False)
    K.brick(x, y, 2, w, d, color, h=2, studs=False)
    if along_y:
        K.brick(x, y + 1, 4, 2, 2, color, h=2, studs=False)
        K.box((x + 0.1) * P, (y + 0.9) * P, 4.2 * PL, (x + 1.9) * P, (y + 1.0) * P, 5.8 * PL, GLASS_C, kind="glossy")
    else:
        K.brick(x + 1, y, 4, 2, 2, color, h=2, studs=False)
        K.box((x + 0.9) * P, (y + 0.1) * P, 4.2 * PL, (x + 1.0) * P, (y + 1.9) * P, 5.8 * PL, GLASS_C, kind="glossy")


# ---------------------------------------------------------------- houses
def build_house(B, bx, by, lot, row, rng, interior=False, name=None):
    """One house on its lot: brick walls with windows and a door on the front, a stepped gable
    roof, a chimney; the front yard, driveway, a tree and maybe a car. Built round its own
    centre so it can be animated. interior: the front picture window is open (no glass) for
    the drone to fly through, and the house is hollow (see build_interior)."""
    K = Kit(B)
    lx, ly, face = lot_origin(bx, by, lot, row)
    hx = lx + (LOT_W - HOUSE_W) // 2 - 2
    hy = ly + (9 if face < 0 else LOT_D - 9 - HOUSE_D)          # set back from the front
    wall, roof = rng.choice(WALLS), rng.choice(ROOFS)
    fy = hy if face < 0 else hy + HOUSE_D - 1                   # the front wall's row
    by_ = hy + HOUSE_D - 1 if face < 0 else hy                  # the back wall's row
    door = (hx + 4, hx + 7, 1, 19)
    pic = (hx + 9, hx + 16, 7, 19)                               # the picture window (studs x, plates z)
    wall_run(K, "x", fy, hx, hx + HOUSE_W, 1, 1 + WALL_H, wall, openings=[door, pic])
    side_win = [(hy + 4, hy + 10, 7, 16)]
    wall_run(K, "x", by_, hx, hx + HOUSE_W, 1, 1 + WALL_H, wall, openings=[(hx + 6, hx + 12, 7, 16)])
    wall_run(K, "y", hx, hy + 1, hy + HOUSE_D - 1, 1, 1 + WALL_H, wall, openings=side_win)
    wall_run(K, "y", hx + HOUSE_W - 1, hy + 1, hy + HOUSE_D - 1, 1, 1 + WALL_H, wall, openings=side_win)
    # door, window frames and glass
    yf0, yf1 = (fy + (0.0 if face < 0 else 0.85)) * P, (fy + (0.15 if face < 0 else 1.0)) * P
    K.box((hx + 4) * P, yf0, 1 * PL, (hx + 7) * P, yf1, 19 * PL, DOOR)
    x0, x1 = pic[0] * P, pic[1] * P
    for z in (7, 19):
        K.box(x0, yf0 - 0.01 * face * 0, z * PL - 0.012, x1, yf1, z * PL + 0.012, TRIM)
    for x in (x0, x1, (x0 + x1) / 2) if not interior else (x0, x1):
        K.box(x - 0.012, yf0, 7 * PL, x + 0.012, yf1, 19 * PL, TRIM)
    if not interior:
        K.box(x0, (fy + 0.45) * P, 7 * PL, x1, (fy + 0.55) * P, 19 * PL, GLASS_C, kind="glossy")
    for wx in (hx, hx + HOUSE_W - 1):
        K.box(wx * P + 0.02, (hy + 4) * P, 7 * PL, (wx + 1) * P - 0.02, (hy + 10) * P, 16 * PL, GLASS_C, kind="glossy")
    K.box((hx + 6) * P, (by_ + 0.45) * P, 7 * PL, (hx + 12) * P, (by_ + 0.55) * P, 16 * PL, GLASS_C, kind="glossy")
    # ceiling plate and a stepped gable roof (ridge along y, so the gables face the sides)
    K.piece(hx - 1, hy - 1, 1 + WALL_H, HOUSE_W + 2, HOUSE_D + 2, 1, TRIM, studs=False)
    z = 2 + WALL_H
    for k in range(HOUSE_W // 2):
        w = HOUSE_W + 2 - 2 * k
        if w <= 0:
            break
        K.piece(hx - 1 + k, hy - 1, z + k, w, HOUSE_D + 2, 1, roof, studs=w <= 2)
    K.brick(hx + HOUSE_W - 5, hy + HOUSE_D // 2, z, 2, 2, "#8a5a3b", h=10, studs=False)       # chimney
    # front path, driveway, a tree, maybe a car
    path_y0, path_y1 = (ly, hy) if face < 0 else (hy + HOUSE_D, ly + LOT_D)
    K.piece(hx + 4, path_y0, 1, 3, path_y1 - path_y0, 0.4, WALK, studs=False)
    dx = hx + HOUSE_W + 1
    K.piece(dx, ly if face < 0 else hy, 1, 5, (hy + HOUSE_D - ly) if face < 0 else (ly + LOT_D - hy), 0.4,
            "#8a8d93", studs=False)
    if rng.random() < 0.7:
        car(K, dx + 1.5, (ly + 3) if face < 0 else (ly + LOT_D - 7), rng.choice(("#c8323c", "#2f6fd6", "#f4f4f0",
                                                                                  "#1b1d22", "#3a8a4a")))
    tree(K, lx + 4, (ly + 4) if face < 0 else (ly + LOT_D - 4), rng.uniform(0.9, 1.25))
    # build round the house's centre
    ob = K.build(name or f"house_{bx}_{by}_{lot}_{row}")
    c = Vector(((hx + HOUSE_W / 2) * P, (hy + HOUSE_D / 2) * P, 0))
    ob.data.transform(__import__("mathutils").Matrix.Translation(-c))
    ob.location = c
    return ob, (hx, hy, face, wall)


# ---------------------------------------------------------------- the construction
def build_datacenter(B, bx, by):
    """A datacenter filling a block: ribbed grey walls, a dark louvred band, loading docks,
    rows of cooling units with fans on the roof, red aircraft lights. Built round its base
    centre (so it can grow up out of the ground)."""
    K = Kit(B)
    ox, oy = block_origin(bx, by)
    x0, y0, x1, y1 = ox + 4, oy + 4, ox + BLK_W - 4, oy + BLK_D - 4
    H = 66                                                        # plates (22 bricks): ~3.6 units
    K.box(x0 * P, y0 * P, 0, x1 * P, y1 * P, H * PL, DC_WALL)
    for x in range(int(x0) + 4, int(x1), 6):                      # ribs
        for yy, s in ((y0, -1), (y1, 1)):
            K.box((x - 0.4) * P, yy * P + s * 0.0, 0, (x + 0.4) * P, yy * P + s * 0.04, H * PL, DC_RIB)
    for yy in range(int(y0) + 4, int(y1), 6):
        for xx, s in ((x0, -1), (x1, 1)):
            K.box(xx * P, (yy - 0.4) * P, 0, xx * P + s * 0.04, (yy + 0.4) * P, H * PL, DC_RIB)
    for yy, s in ((y0, -1), (y1, 1)):                             # louvred band
        K.box(x0 * P, yy * P + s * 0.045, 40 * PL, x1 * P, yy * P + s * 0.05, 52 * PL, DC_DARK)
    for x in range(int(x0) + 8, int(x1) - 8, 14):                 # loading docks
        K.box(x * P, y0 * P - 0.05, 0, (x + 6) * P, y0 * P, 16 * PL, "#5a606b")
    for x in range(int(x0) + 4, int(x1) - 6, 9):                  # cooling units
        for y in range(int(y0) + 4, int(y1) - 6, 9):
            K.box(x * P, y * P, H * PL, (x + 6) * P, (y + 6) * P, (H + 6) * PL, "#aab0b8")
            for fx, fy in ((1.5, 1.5), (4.5, 1.5), (1.5, 4.5), (4.5, 4.5)):
                K.cyl((x + fx) * P, (y + fy) * P, (H + 6) * PL, (H + 6.3) * PL, 1.2 * P, DC_DARK, sides=12)
    for xx, yy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        K.cyl(xx * P, yy * P, H * PL, (H + 4) * PL, 0.03, "#ff2a2a", kind="glow", sides=8)
    ob = K.build(f"dc_{bx}_{by}")
    c = Vector(((x0 + x1) / 2 * P, (y0 + y1) / 2 * P, 0))
    ob.data.transform(__import__("mathutils").Matrix.Translation(-c))
    ob.location = c
    return ob


def build_crane(B, x, y, name):
    """A yellow tower crane: mast, slewing jib (a child, to spin), counter-jib and weights."""
    K = Kit(B)
    H = 9.5
    for k in range(4):
        cx, cy = (-0.12 if k % 2 else 0.12), (-0.12 if k < 2 else 0.12)
        K.box(cx - 0.02, cy - 0.02, 0, cx + 0.02, cy + 0.02, H, CRANE)
    for z in [0.5 * i for i in range(1, int(H / 0.5))]:
        K.box(-0.14, -0.14, z, 0.14, 0.14, z + 0.02, CRANE)
    K.box(-0.4, -0.4, 0, 0.4, 0.4, 0.15, "#7a7f88")
    mast = K.build(f"{name}_mast")
    K = Kit(B)
    K.box(-1.6, -0.1, 0, 5.5, 0.1, 0.22, CRANE)                    # jib + counter-jib
    K.box(-1.6, -0.25, -0.25, -0.9, 0.25, 0.05, "#7a7f88")        # counterweights
    K.box(-0.3, -0.3, 0.0, 0.3, 0.3, 0.5, CRANE)                   # cab and peak
    K.box(-0.05, -0.05, 0.5, 0.05, 0.05, 1.3, CRANE)
    K.box(3.5, -0.02, -2.5, 3.52, 0.02, 0.0, "#2a2a30")           # hook line
    jib = K.build(f"{name}_jib")
    jib.parent = mast
    jib.location = (0, 0, H)
    mast.location = (x * P, y * P, 0)
    return mast, jib


def build_rubble(B, name, colors, seed):
    """A pile of loose bricks (where a house was)."""
    K = Kit(B)
    rng = random.Random(seed)
    for _ in range(70):
        r = rng.random() ** 0.6 * 7
        a = rng.uniform(0, math.tau)
        x, y = r * math.cos(a) * 1.3, r * math.sin(a)
        z = max(0.0, (7 - r) * 1.2 + rng.uniform(-1, 1))
        w, d = rng.choice(((2, 4), (1, 4), (2, 2), (1, 2), (4, 2)))
        K.brick(x - w / 2, y - d / 2, z, w, d, rng.choice(colors), studs=rng.random() < 0.6)
    return K.build(name, bevel=0.0)


def build_fence(K, x0, y0, x1, y1):
    """Orange-and-white construction barriers round the zone."""
    for x in range(int(x0), int(x1), 4):
        for yy in (y0, y1):
            K.box(x * P, yy * P, 0, (x + 3.6) * P, yy * P + 0.03, 0.42, "#ff6a1f")
            K.box(x * P, yy * P - 0.001, 0.14, (x + 3.6) * P, yy * P + 0.031, 0.2, "#f4f4f0")
    for y in range(int(y0), int(y1), 4):
        for xx in (x0, x1):
            K.box(xx * P, y * P, 0, xx * P + 0.03, (y + 3.6) * P, 0.42, "#ff6a1f")
            K.box(xx * P - 0.001, y * P, 0.14, xx * P + 0.031, (y + 3.6) * P, 0.2, "#f4f4f0")


# ---------------------------------------------------------------- the house we enter
IPAD_SCREEN = (0.32, 0.18, 0.105)     # the iPad's screen: width, height (16:9, the frame's shape), centre height


def build_interior(B, col, hx, hy, screen_video=None, screen_offset=0):
    """Inside the target house (front wall at hy, facing -y): a wood floor and a rug, the User on
    the sofa against the back wall facing the window, their toddler on the rug facing the iPad
    (its back to the window), the iPad on a stand facing the toddler, a lamp."""
    K = Kit(B)
    K.piece(hx + 1, hy + 1, 1, HOUSE_W - 2, HOUSE_D - 2, 1, "#a8743f", studs=False)
    K.piece(hx + 6, hy + 4, 2, 9, 6, 0.3, "#c97a8a", studs=False)          # rug
    K.round(hx + 2, hy + HOUSE_D - 4, 2, 2, 1, "#2a2a30", studs=False)      # floor lamp
    K.cyl((hx + 3) * P, (hy + HOUSE_D - 3) * P, 3 * PL, 14 * PL, 0.012, "#8a8f99", sides=8)
    K.round(hx + 1.5, hy + HOUSE_D - 4.5, 14, 3, 3, "#f6e7c1", studs=False)
    K.build("interior")
    ld = bpy.data.lights.new("lamp", "POINT")
    ld.energy, ld.color, ld.shadow_soft_size = 18, (1.0, 0.82, 0.6), 0.1
    lo = bpy.data.objects.new("lamp", ld)
    col.objects.link(lo)
    lo.location = ((hx + 3) * P, (hy + HOUSE_D - 3) * P, 15.5 * PL)
    # the User on the sofa (built facing -y: toward the window)
    user = place_figure(SL.build_user, B, ((hx + 10.5) * P, (hy + HOUSE_D - 3.2) * P, 2 * PL))
    # the toddler, facing the iPad (+y)
    tod = place_figure(build_toddler, B, ((hx + 10.5) * P, (hy + 4.0) * P, 2.3 * PL))
    tod.rotation_euler.z = math.pi
    tod.scale = (0.62, 0.62, 0.62)
    # the iPad on a little stand, facing the toddler (-y)
    ipad = (hx + 10.5) * P, (hy + 6.6) * P
    K = Kit(B)
    K.box(ipad[0] - 0.12, ipad[1] - 0.02, 2 * PL, ipad[0] + 0.12, ipad[1] + 0.06, 2 * PL + 0.04, "#2a2a30")
    K.build("ipad_stand")
    pad = bpy.data.objects.new("ipad", None)
    col.objects.link(pad)
    pad.location = (ipad[0], ipad[1], 2 * PL + 0.04)
    pad.rotation_euler.x = -0.32                                            # leaning back
    K = Kit(B)
    sw, sh, sz = IPAD_SCREEN
    K.box(-sw / 2 - 0.02, 0.0, sz - sh / 2 - 0.02, sw / 2 + 0.02, 0.018, sz + sh / 2 + 0.02, "#1b1d22")
    body = K.build("ipad_body")
    body.parent = pad
    if screen_video:   # the cyberspace shot itself, in sync (the push-in lands on it, then cuts to it)
        from office_set import movie_material
        mat = movie_material("ipad_img", screen_video, screen_offset, 1.5)   # (brighter: it goes through this shot's look again)
    else:
        mat = image_material("ipad_img", os.path.join(TEX, "ipad_v9.png"), 1.6)
    scr = picture(col, "ipad_screen", mat, (0, -0.001, sz), (sw, sh), "-y")
    scr.parent = pad
    glow = bpy.data.lights.new("ipadglow", "AREA")
    glow.energy, glow.size, glow.color = 3.0, 0.25, (0.75, 0.7, 1.0)
    go = bpy.data.objects.new("ipadglow", glow)
    col.objects.link(go)
    go.parent = pad
    go.location = (0, -0.05, sz)
    go.rotation_euler.x = math.pi / 2
    return {"user": user, "toddler": tod, "ipad": pad, "screen": scr}


def build_toddler(B):
    """A two-year-old: short legs out in front (sitting on the floor), a big head, a striped tee,
    arms resting on the knees, wide eyes on the screen."""
    top = SL.fig_torso(B, SL.fig_kid_legs(B, "#4fb3f0", "#f4f4f0"), "#ffd166")
    z0 = top - SL.FIG["torso_h"]
    for k in range(3):
        SL.print_poly(B, f"stripe{k}", [(-0.15, z0 + 0.05 + 0.08 * k), (0.15, z0 + 0.05 + 0.08 * k),
                                        (0.15, z0 + 0.085 + 0.08 * k), (-0.15, z0 + 0.085 + 0.08 * k)], "#ff9f7a")
    SL.fig_arms(B, top, "#ffd166", "fig_skin", poses=("forward", "forward"), long_sleeve=False)
    c, cyl = SL.fig_head(B, top, "fig_skin")
    SL.face_eyes(B, c, cyl)
    SL.face_mouth(B, c, "flat")
    B.sphere("hair", (0, 0.02, c + 0.075), (0.104, 0.104, 0.045), "#e2b85c", kind="glossy")
    B.capsule("tuft", (0.0, -0.02, c + 0.11), (0.02, -0.04, c + 0.15), 0.012, "#e2b85c", kind="glossy")
    for hip, knee in B.legs[-2:]:               # sitting: legs straight out in front
        hip.rotation_euler.x = -math.pi / 2
        knee.rotation_euler.x = 0.0


def textures():
    """The iPad's picture: v9 smiling on a soft gradient (a stand-in for the first frame of the
    cyberspace shot)."""
    os.makedirs(TEX, exist_ok=True)
    path = os.path.join(TEX, "ipad_v9.png")
    if os.path.exists(path):
        return
    from PIL import Image, ImageDraw
    w, h = 1024, 728
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            u, v = x / w, y / h
            px[x, y] = (int(120 + 90 * u), int(90 + 60 * v), int(220 - 40 * u))
    dr = ImageDraw.Draw(im)
    cx, cy = w // 2, h // 2 + 60                           # v9: a lilac body under a screen head
    dr.rounded_rectangle([cx - 150, cy + 40, cx + 150, cy + 420], 40, fill=(185, 167, 245))
    dr.rounded_rectangle([cx - 190, cy - 300, cx + 190, cy + 20], 46, fill=(240, 238, 255))
    dr.rounded_rectangle([cx - 165, cy - 275, cx + 165, cy - 5], 30, fill=(20, 18, 40))
    for s in (-1, 1):                                       # happy ^ ^ eyes
        ex = cx + 75 * s
        dr.line([(ex - 34, cy - 160), (ex, cy - 195), (ex + 34, cy - 160)], fill=(160, 230, 255), width=16)
    dr.arc([cx - 90, cy - 170, cx + 90, cy - 50], 20, 160, fill=(160, 230, 255), width=16)
    im.save(path)


# ---------------------------------------------------------------- the set
def build(sc, seed=8, screen_video=None, screen_offset=0):
    textures()
    col = sc.collection
    B = SL.Builder("fig", col)
    B.mats[("glass", "glass")] = glass_material()
    rng = random.Random(seed)
    K = Kit(B)
    build_ground(K)
    ground = K.build("ground", bevel=0.0)
    houses, rubble, dcs, cranes = [], [], [], []
    interior = None
    for bx in range(COLS):
        for by in range(ROWS):
            for lot in range(LOTS):
                for row in range(2):
                    is_target = (bx, by, lot, row) == TARGET
                    ob, (hx, hy, face, wall) = build_house(B, bx, by, lot, row, rng, interior=is_target)
                    if is_target:
                        interior = build_interior(B, col, hx, hy, screen_video, screen_offset)
                    if bx < ZONE_COLS:
                        rb = build_rubble(B, f"rubble_{bx}_{by}_{lot}_{row}", [wall, "#8a8f99", "#6b4a2e"],
                                          bx * 100 + by * 10 + lot * 2 + row)
                        rb.location = ob.location
                        rb.scale = (0, 0, 0)
                        houses.append((ob, bx, by, lot))
                        rubble.append(rb)
            if bx < ZONE_COLS:
                dc = build_datacenter(B, bx, by)
                dc.scale.z = 0.0
                dcs.append((dc, bx, by))
                ox, oy = block_origin(bx, by)
                mast, jib = build_crane(B, ox + BLK_W * (0.3 + 0.4 * (by % 2)), oy + BLK_D + ROAD / 2 - 2,
                                        f"crane_{bx}_{by}")
                mast.scale = (0, 0, 0)
                cranes.append((mast, jib, bx, by))
    K = Kit(B)
    zx1 = ZONE_COLS * PITCH_X - ROAD / 2 - 1
    build_fence(K, -ROAD / 2 + 1, -ROAD / 2 + 1, zx1, ROWS * PITCH_Y - ROAD / 2 - 1)
    fence = K.build("fence", bevel=0.0)
    fence.scale = (1, 1, 0)
    lighting(sc)
    return {"houses": houses, "rubble": rubble, "dcs": dcs, "cranes": cranes, "fence": fence,
            "interior": interior, "ground": ground}


def lighting(sc):
    """A clear day: a Nishita sky and a sun (both animated in the time-lapse)."""
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    nt = sc.world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.name = "sky"
    sky.sky_type = "NISHITA"
    sky.sun_disc = False
    sky.sun_elevation, sky.sun_rotation = math.radians(40), math.radians(200)
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.12
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy, ld.angle, ld.color = 4.0, math.radians(2.0), (1.0, 0.93, 0.82)
    sun = bpy.data.objects.new("sun", ld)
    sc.collection.objects.link(sun)
    set_sun(sc, math.radians(40), math.radians(200))


def set_sun(sc, elev, rot):
    sky = sc.world.node_tree.nodes["sky"]
    sky.sun_elevation, sky.sun_rotation = elev, rot
    sun = bpy.data.objects["sun"]
    d = Vector((math.sin(rot) * math.cos(elev), math.cos(rot) * math.cos(elev), math.sin(elev)))
    SL.aim(sun, tuple(-d))


# ---------------------------------------------------------------- the time-lapse
SPEED_DECAY, SPEED_RATIO = 0.12, 60.0
EASE_TIME, EASE_END = 1.6, 0.015            # ...easing in over the last 1.6 s almost to a stop (the screen fills the frame)
TL = (0.0, 9.0)            # time-lapse (s from the shot's start): houses go, datacenters rise
TL_FROM = 0.25              # ...already this far along when the shot starts (much of it rubble)


def lapse_u(t):
    """Time-lapse progress at t seconds into the shot."""
    t0, t1 = TL
    return TL_FROM + (1 - TL_FROM) * min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def lapse_state(S, sc, u):
    """Pose everything for time-lapse progress u (0 the old suburb .. 1 all datacenters). Each
    block's turn comes in a wave along x (the way the drone flies): its houses collapse into
    rubble, the rubble is cleared, a crane goes up, the datacenter climbs floor by floor, the
    crane comes down. The fence goes up first."""
    S["fence"].scale.z = min(1.0, u / 0.05)
    nb = ZONE_COLS
    for ob, bx, by, lot in S["houses"]:
        w0 = 0.04 + 0.5 * (bx + by * 0.25 + lot * 0.06) / nb      # this house's turn
        k = (u - w0) / 0.06
        ob.scale = (1, 1, min(1.0, max(0.0, 1 - k))) if k < 1 else (0, 0, 0)
    for rb, (ob, bx, by, lot) in zip(S["rubble"], S["houses"]):
        w0 = 0.04 + 0.5 * (bx + by * 0.25 + lot * 0.06) / nb
        a, b = (u - w0) / 0.05, (u - w0 - 0.12) / 0.06
        s = min(1.0, max(0.0, a)) * (1 - min(1.0, max(0.0, b)))
        rb.scale = (s, s, s)
    for dc, bx, by in S["dcs"]:
        w0 = 0.04 + 0.5 * (bx + by * 0.25 + 0.3) / nb + 0.18
        g = min(1.0, max(0.0, (u - w0) / 0.22))
        floors = 11
        dc.scale.z = math.floor(g * floors + 1e-6) / floors + 0.0001     # floor by floor
    for mast, jib, bx, by in S["cranes"]:
        w0 = 0.04 + 0.5 * (bx + by * 0.25 + 0.3) / nb + 0.14
        up = min(1.0, max(0.0, (u - w0) / 0.04)) * (1 - min(1.0, max(0.0, (u - w0 - 0.32) / 0.04)))
        mast.scale = (up, up, up)
        jib.rotation_euler.z = (u - w0) * 40.0                        # swinging round (sped up)
    # the sun: days racing by
    days = 3.0
    ph = u * days
    rot = math.radians(200) + math.tau * ph
    elev = math.radians(14 + 42 * abs(math.cos(math.pi * ph)))      # starts (and ends) at midday
    set_sun(sc, elev, rot)


def animate_lapse(S, sc, start, n, fps):
    """Keyframe the time-lapse on every frame of the clip (song time `start` at frame 1)."""
    t0, t1 = TL
    sky = sc.world.node_tree.nodes["sky"]
    sun = bpy.data.objects["sun"]
    obs = [o for o, *_ in S["houses"]] + S["rubble"] + [d for d, *_ in S["dcs"]] + \
        [m for m, *_ in S["cranes"]] + [j for _, j, *_ in S["cranes"]] + [S["fence"]]
    for f in range(1, n + 1):
        t = start + (f - 1) / fps - SHOT_START
        lapse_state(S, sc, lapse_u(t))
        for ob in obs:
            ob.keyframe_insert("scale", frame=f)
        for _, j, *_ in S["cranes"]:
            j.keyframe_insert("rotation_euler", index=2, frame=f)
        sky.keyframe_insert("sun_elevation", frame=f)
        sky.keyframe_insert("sun_rotation", frame=f)
        sun.keyframe_insert("rotation_euler", frame=f)


# ---------------------------------------------------------------- the drone
def target_window():
    """The middle of the target house's picture window (world), and a point inside the room."""
    bx, by, lot, row = TARGET
    lx, ly, face = lot_origin(bx, by, lot, row)
    hx = lx + (LOT_W - HOUSE_W) // 2 - 2
    hy = ly + 9
    return Vector(((hx + 12.5) * P, hy * P, 13 * PL)), (hx, hy)


def ipad_screen():
    """The iPad screen's centre and its facing direction (world)."""
    _, (hx, hy) = target_window()
    a = -0.32
    base = Vector(((hx + 10.5) * P, (hy + 6.6) * P, 2 * PL + 0.04))
    sz = IPAD_SCREEN[2]
    centre = base + Vector((0, -0.001 * math.cos(a) - sz * math.sin(a), -0.001 * math.sin(a) + sz * math.cos(a)))
    normal = Vector((0, -math.cos(a), -math.sin(a)))
    return centre, normal


IPAD_FILL = IPAD_SCREEN[0] / 2 * 36 / 18      # the distance at which (with a 36 mm lens) the screen fills the frame


def drone_path():
    """(time s from the shot's start, camera, look-at, lens)."""
    win, (hx, hy) = target_window()
    ipad, nrm = ipad_screen()
    over = Vector(((hx + 11.85) * P, (hy + 3.3) * P, 2 * PL + 0.48))      # over the toddler's shoulder
    far = ipad - nrm * 2.5          # aim through the screen at a distant point (a near target swings the view)
    W = COLS * PITCH_X * P
    D = ROWS * PITCH_Y * P
    return [
        (0.0, (2.0, -12.0, 16.0), (14.0, D * 0.5, 0.0), 28),
        (4.0, (14.0, -11.0, 15.0), (26.0, D * 0.5, 0.0), 28),
        (8.0, (30.0, -10.0, 12.0), (42.0, D * 0.5, 0.0), 28),
        (9.2, tuple(win + Vector((-4.5, -9.0, 5.5))), tuple(win + Vector((0, 0, 0.5))), 30),   # clear of the roofs
        (10.4, tuple(win + Vector((-0.5, -4.2, 1.5))), tuple(win), 30),
        (11.6, tuple(win + Vector((0.0, -1.0, 0.08))), tuple(far), 32),
        (13.3, tuple(over), tuple(far), 34),
        (SHOT_LEN, tuple(ipad + nrm * IPAD_FILL), tuple(far), 36),     # the screen exactly fills the frame
    ]


def _centripetal(p0, p1, p2, p3, f):
    """Centripetal Catmull-Rom between p1 and p2 (f 0..1): no overshoot or loops, even where the
    points are very unevenly spaced."""
    def tj(ti, a, b):
        return ti + max((b - a).length, 1e-6) ** 0.5
    t0 = 0.0
    t1 = tj(t0, p0, p1)
    t2 = tj(t1, p1, p2)
    t3 = tj(t2, p2, p3)
    t = t1 + (t2 - t1) * f
    a1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
    a2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
    a3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
    b1 = a1 * ((t2 - t) / (t2 - t0)) + a2 * ((t - t0) / (t2 - t0))
    b2 = a2 * ((t3 - t) / (t3 - t1)) + a3 * ((t - t1) / (t3 - t1))
    return b1 * ((t2 - t) / (t2 - t1)) + b2 * ((t - t1) / (t2 - t1))


_DRONE = None


def _drone_table(n=6000):
    """Sample the path densely and give each sample a time: the camera moves at a speed
    proportional to its clearance (height above the ground, or its distance to the iPad at the
    end), so the motion on screen stays steady: fast high over the suburb, slowing smoothly all
    the way down into the room, with no sudden pushes. The waypoints' own times are ignored."""
    pts = drone_path()
    T = pts[-1][0]
    P_ = [Vector(p[1]) for p in pts]
    G_ = [Vector(p[2]) for p in pts]
    L_ = [p[3] for p in pts]
    m = len(pts)
    ext = lambda A: [A[0] * 2 - A[1]] + A + [A[-1] * 2 - A[-2]]
    PE, GE = ext(P_), ext(G_)
    ipad, _ = ipad_screen()
    samples = []
    for i in range(n + 1):
        x = i / n * (m - 1)
        k = min(int(x), m - 2)
        f = x - k
        pos = _centripetal(PE[k], PE[k + 1], PE[k + 2], PE[k + 3], f)
        tgt = _centripetal(GE[k], GE[k + 1], GE[k + 2], GE[k + 3], f)
        e = f * f * (3 - 2 * f)
        lens = L_[k] + (L_[k + 1] - L_[k]) * e
        samples.append((pos, tgt, lens))
    times = [0.0]
    for (a, _, _), (b, _, _) in zip(samples, samples[1:]):
        mid = (a + b) / 2
        clear = max(0.06, min(mid.z, 0.6 * (mid - ipad).length + 0.12))
        times.append(times[-1] + (b - a).length / clear ** 0.8)   # (lingers a little more up high)
    k = T / times[-1]
    times = [t * k for t in times]
    # Distance along the path over time, s(t), from one smooth, ever-decreasing speed curve:
    # v(t) = vT + (v0 - vT) (e^-kt - e^-kT) / (1 - e^-kT), with v0 = SPEED_RATIO vT, scaled so
    # the camera covers the whole path in T. It never speeds up and its deceleration changes
    # gently, from the high flyover all the way into the iPad.
    import bisect
    arc = [0.0]
    for (a_, _, _), (b_, _, _) in zip(samples, samples[1:]):
        arc.append(arc[-1] + (b_ - a_).length)
    rate = 120
    N = int(round(T * rate)) + 1
    k_, r_ = SPEED_DECAY, SPEED_RATIO
    eT = math.exp(-k_ * T)

    def shape(t):            # the speed curve with vT = 1, and its integral
        v = 1 + (r_ - 1) * (math.exp(-k_ * t) - eT) / (1 - eT)
        I = t + (r_ - 1) * ((1 - math.exp(-k_ * t)) / k_ - eT * t) / (1 - eT)
        return v, I
    def ease(t):              # the last second eases in: the speed glides down to EASE_END of itself
        u = min(1.0, max(0.0, (t - (T - EASE_TIME)) / EASE_TIME))
        return 1 - (1 - EASE_END) * u * u * u * (u * (6 * u - 15) + 10)
    acc_s = [0.0]
    for j in range(1, N):
        t0_, t1_ = (j - 1) / rate, j / rate
        acc_s.append(acc_s[-1] + 0.5 * (shape(t0_)[0] * ease(t0_) + shape(t1_)[0] * ease(t1_)) / rate)
    s_sm = [v * arc[-1] / acc_s[-1] for v in acc_s]

    def smooth(vals, sigma, extend=True):
        r = int(3 * sigma * rate)
        w = [math.exp(-0.5 * (d / (sigma * rate)) ** 2) for d in range(-r, r + 1)]

        def at(jj):
            return vals[min(N - 1, max(0, jj))]
        out = []
        for j in range(N):
            acc = vals[0] * 0
            ws = 0.0
            for d, wd in zip(range(-r, r + 1), w):
                acc = acc + at(j + d) * wd
                ws += wd
            out.append(acc / ws)
        return out

    def on_path(sv):
        i = min(len(arc) - 2, max(0, bisect.bisect_right(arc, sv) - 1))
        f = (sv - arc[i]) / max(1e-12, arc[i + 1] - arc[i])
        (p0, g0, l0), (p1, g1, l1) = samples[i], samples[i + 1]
        p = p0.lerp(p1, f)
        return p, (g0.lerp(g1, f) - p).normalized(), l0 + (l1 - l0) * f
    raw = [on_path(sv) for sv in s_sm]
    pos = [r[0] for r in raw]
    dirs = [d.normalized() for d in smooth(smooth([r[1] for r in raw], 0.8, False), 0.8, False)]
    lens = smooth(smooth([r[2] for r in raw], 0.5, False), 0.5, False)
    # the last second: aim and zoom lock exactly onto the screen (square on, filling the frame), so
    # the final frames match the cyberspace shot it cuts to
    ipad_c, ipad_n = ipad_screen()
    far = ipad_c - ipad_n * 2.5
    for j in range(N):
        u = min(1.0, max(0.0, (j / rate - (T - 1.0)) / 0.8))
        u = u * u * (3 - 2 * u)
        if u > 0:
            exact = (far - pos[j]).normalized()
            dirs[j] = dirs[j].lerp(exact, u).normalized()
            lens[j] = lens[j] + (36.0 - lens[j]) * u
    return [j / rate for j in range(N)], [(p, p + d, l) for p, d, l in zip(pos, dirs, lens)]


def drone_pose(t):
    global _DRONE
    if _DRONE is None:
        _DRONE = _drone_table()
    times, samples = _DRONE
    t = min(max(t, 0.0), times[-1])
    import bisect
    i = min(len(times) - 2, max(0, bisect.bisect_right(times, t) - 1))
    f = (t - times[i]) / max(1e-9, times[i + 1] - times[i])
    (p0, g0, l0), (p1, g1, l1) = samples[i], samples[i + 1]
    return tuple(p0.lerp(p1, f)), tuple(g0.lerp(g1, f)), l0 + (l1 - l0) * f


def split_screen_pass(sc, layer):
    """Set the scene up for one of the two passes of the iPad screen (see --pass)."""
    scr = bpy.data.objects["ipad_screen"]
    em = next(n for n in scr.data.materials[0].node_tree.nodes if n.type == "EMISSION")
    if layer == "main":                     # the screen goes dark; its glow light stays
        em.inputs["Strength"].default_value = 0.0
        return
    em.inputs["Strength"].default_value = 1.0
    for ob in bpy.data.objects:
        if ob.type in ("MESH", "CURVE", "FONT") and ob is not scr:
            ob.is_holdout = True            # in front of the screen: blocks it; elsewhere: black
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0


def setup_render(sc, res, preview):
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = res
    sc.render.resolution_x = res * 16 // 9
    sc.eevee.taa_render_samples = 1 if preview else 32
    sc.eevee.use_raytracing = not preview
    sc.eevee.use_fast_gi = not preview
    sc.eevee.shadow_pool_size = "1024"
    sc.render.use_motion_blur = not preview          # (as the performances: 360-degree shutter)
    sc.render.motion_blur_shutter = 1.0
    sc.eevee.motion_blur_steps = 4
    sc.eevee.motion_blur_max = int(160 * res / 1080)
    if not preview:
        rt = sc.eevee.ray_tracing_options
        rt.resolution_scale, rt.use_denoise = "1", True
        sc.eevee.shadow_ray_count, sc.eevee.shadow_step_count = 3, 12
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -1.0
    sc.render.image_settings.file_format = "PNG"


# check stills: (name, time s into the shot)
STILLS = [("start", 0.2), ("lapse_a", 3.0), ("lapse_b", 6.0), ("lapse_end", 8.6), ("approach", 10.6),
          ("window", 11.8), ("room", 12.6), ("ipad", 14.3), ("front", -1)]


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "build", "suburb_stills"))
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--flat", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--fly", action="store_true")
    ap.add_argument("--screen", help="the cyberspace shot, for the iPad (its first frame at --screen-start)")
    ap.add_argument("--screen-start", type=float, default=162.6)
    ap.add_argument("--pass", dest="layer", default="main", choices=("main", "screen"),
                    help="main: the shot, the iPad screen dark (its light still on the room); screen: only the "
                         "screen, on black, in plain sRGB (so its pixels are the video's own), everything else a "
                         "holdout; the two are added together in assembly")
    A = ap.parse_args(argv)
    res = A.res or (540 if A.preview or A.flat else 1080)
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    S = build(sc, screen_video=A.screen, screen_offset=int(round((A.screen_start - SHOT_START) * 60)))
    setup_render(sc, res, A.preview)
    if A.flat:
        import lipsync_demo as LS
        LS.flat_look(sc)
    os.makedirs(A.out, exist_ok=True)
    fps = 60
    T = drone_path()[-1][0]
    cam = camera(sc, *drone_path()[0][1:])
    cam.data.clip_start = 0.01
    if A.screen:
        split_screen_pass(sc, A.layer)
    if A.fly:
        n = int(round(T * fps))
        animate_lapse(S, sc, SHOT_START, n, fps)
        for f in range(1, n + 1):
            loc, tgt, lens = drone_pose((f - 1) / fps)
            cam.location = loc
            SL.aim(cam, tgt)
            cam.data.lens = lens
            cam.keyframe_insert("location", frame=f)
            SL.key_rotation(cam, f)
            cam.data.keyframe_insert("lens", frame=f)
        sc.frame_start, sc.frame_end, sc.render.fps = 1, n, fps
        sc.render.image_settings.file_format = "FFMPEG"
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        final = "_final" if not (A.preview or A.flat) else ""
        if A.layer == "screen" or final:     # lossless (the screen's pixels stay the video's exactly)
            sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
            sc.render.image_settings.color_mode = "RGB"
            sc.render.ffmpeg.audio_codec = "NONE"
        if A.layer == "screen":
            sc.render.filepath = os.path.join(A.out, f"drone_screen{final}.mkv")
        else:
            sc.render.filepath = os.path.join(A.out, "drone_final.mkv" if final else "drone.mp4")
        bpy.ops.render.render(animation=True)
        return
    t0, t1 = TL
    for name, t in STILLS:
        if A.only and name not in A.only.split(","):
            continue
        lapse_state(S, sc, lapse_u(max(t, 0.0)))
        if t < 0:      # a check view: the target house's front, from the street
            win, _ = target_window()
            loc, tgt, lens = tuple(win + Vector((0.6, -2.6, 0.5))), tuple(win), 30
        else:
            loc, tgt, lens = drone_pose(t)
        cam.location = loc
        SL.aim(cam, tgt)
        cam.data.lens = lens
        sc.render.filepath = os.path.join(A.out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__":
    main()
