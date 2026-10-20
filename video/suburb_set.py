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
OPPOSITE = (TARGET[0], TARGET[1] - 1, TARGET[2], 1)   # the house across the street from it...
OPPOSITE_BACK = 11                     # ...set further back (studs), so the drone can come down low early
SHOT_START = 148.6                     # song time the shot starts (the bridge ends)
SHOT_LEN = 19.6                        # ...and its length: still pushing into the iPad as v9's first line
                                       # starts (165.3); the cut to cyberspace comes at 168.2

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
    back = OPPOSITE_BACK if (bx, by, lot, row) == OPPOSITE else 0
    hy = ly + (9 if face < 0 else LOT_D - 9 - HOUSE_D - back)   # set back from the front
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
IPAD_SCREEN = (0.16, 0.09, 0.07)      # the iPad's screen: width, height (16:9, the frame's shape), centre up the slab
CASE_RIM, CASE_COLOR = 0.034, "#2ec4c4"   # the foam case's rim width, and its colour (turquoise: clear of the pink rug)
TODDLER = (13.0, 4.0)                  # where she sits in the house (studs from its corner), facing +y
TODDLER_TURN = math.radians(40)        # turned to her left (with the iPad), so from the window the screen
                                       # shows over her left shoulder
TODDLER_SCALE = 0.62
TODDLER_Z = 2.3 * PL - (0.24 - 0.0725) * TODDLER_SCALE   # sitting on the rug (her hip axle's underside on it)
IPAD_LAP = (0.0, 0.115, 0.286)         # the iPad's bottom edge, held up in her hands over her lap (offset from her)
IPAD_CANT = math.radians(-12)          # and tipped a little toward her left (round its own up axis)
IPAD_TILT = -1.3                       # lying back in her lap, its screen facing up (toward her face)


def _turn():
    from mathutils import Matrix
    return Matrix.Rotation(TODDLER_TURN, 3, "Z")


def ipad_rot():
    """The iPad's rotation: canted toward her left, tilted back, then turned with her."""
    from mathutils import Matrix
    return _turn() @ Matrix.Rotation(IPAD_TILT, 3, "X") @ Matrix.Rotation(IPAD_CANT, 3, "Z")


def ipad_base(hx, hy):
    return Vector(((hx + TODDLER[0]) * P, (hy + TODDLER[1]) * P, 0.0)) + _turn() @ Vector(IPAD_LAP)


USER_LAP_ARM = ((-0.25, SL.ARM_SLOPE, 0.4), -1.05)   # the User's free arm (shoulder rotation, elbow bend): resting by their lap


def build_interior(B, col, hx, hy, screen_video=None, screen_offset=0):
    """Inside the target house (front wall at hy, facing -y): a wood floor and a rug, the User on
    the sofa against the back wall facing the window, their toddler on the rug (her back to the
    window) with the iPad in her lap, a lamp."""
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
    # their free hand (the phone's in the other) rests in their lap, not held out in front
    for o in user.children_recursive:
        if o.type == "EMPTY" and o.name.split(".")[0] == "shoulder-1":
            o.rotation_euler = USER_LAP_ARM[0]
        elif o.type == "EMPTY" and o.name.split(".")[0] == "elbow-1":
            o.rotation_euler.x = USER_LAP_ARM[1]
    # the toddler, facing the iPad (+y)
    tod = place_figure(build_toddler, B, ((hx + TODDLER[0]) * P, (hy + TODDLER[1]) * P, TODDLER_Z))
    tod.rotation_euler.z = math.pi + TODDLER_TURN
    tod.scale = (TODDLER_SCALE,) * 3
    bpy.context.view_layer.update()
    neck_z = TODDLER_Z + (SL.FIG["z_adult"] + SL.FIG["torso_h"]) * TODDLER_SCALE
    head = [ob for ob in tod.children_recursive if ob.type != "EMPTY" and
            (sum((ob.matrix_world @ Vector(c) for c in ob.bound_box), Vector()) / 8).z > neck_z]
    # the iPad in her lap: its bottom edge on her thighs, leaning back, the screen up toward her face
    pad = bpy.data.objects.new("ipad", None)
    col.objects.link(pad)
    pad.location = ipad_base(hx, hy)
    # her hands' places on the case, set while it's held square...
    from mathutils import Matrix
    pad.rotation_mode = "QUATERNION"
    pad.rotation_quaternion = (_turn() @ Matrix.Rotation(IPAD_TILT, 3, "X")).to_quaternion()
    bpy.context.view_layer.update()
    kids = tod.children_recursive
    grips = []
    for side in ("-1", "1"):
        hand = next(o for o in kids if o.type != "EMPTY" and o.name.split(".")[0] == f"hand{side}")
        sh = next(o for o in kids if o.type == "EMPTY" and o.name.split(".")[0] == f"shoulder{side}")
        el = next(o for o in kids if o.type == "EMPTY" and o.name.split(".")[0] == f"elbow{side}")
        grips.append((hand, sh, el, pad.matrix_world.inverted() @ hand.matrix_world.translation))
    # ...then it's canted, and each arm swings at the shoulder and bends at the elbow until its hand
    # is back on its place
    pad.rotation_quaternion = ipad_rot().to_quaternion()
    bpy.context.view_layer.update()
    for hand, sh, el, local in grips:
        want = pad.matrix_world @ local

        def miss(ob, v):
            ob.rotation_euler.x = v
            bpy.context.view_layer.update()
            return (hand.matrix_world.translation - want).length
        for _ in range(6):                      # (alternate golden-section searches on the two joints)
            for ob in (sh, el):
                v0 = ob.rotation_euler.x
                lo, hi = v0 - 0.5, v0 + 0.5
                for _ in range(30):
                    m1, m2 = hi - (hi - lo) * 0.618, lo + (hi - lo) * 0.618
                    if miss(ob, m1) < miss(ob, m2):
                        hi = m2
                    else:
                        lo = m1
                miss(ob, (lo + hi) / 2)
        print(f"GRIP {hand.name}: off by {(hand.matrix_world.translation - want).length * 1000:.1f} mm")
    K = Kit(B)
    sw, sh, sz = IPAD_SCREEN
    # a thin black bezel round the screen, in a chunky turquoise foam kids' case: a raised rim she
    # holds it by, and a carry handle on the far edge
    bz = 0.008
    K.box(-sw / 2 - bz, 0.0, sz - sh / 2 - bz, sw / 2 + bz, 0.008, sz + sh / 2 + bz, "#141518")
    body = K.build("ipad_body")
    body.parent = pad
    rim = CASE_RIM
    W, H = sw + 2 * (bz + rim), sh + 2 * (bz + rim)
    parts = [B.box("case_back", (0, 0.016, sz), (W, 0.02, H), CASE_COLOR, bevel=0.01, kind="matte")]
    for sx in (-1, 1):                                                       # the rim's sides...
        parts.append(B.box(f"case_side{sx}", (sx * (W - rim) / 2, -0.001, sz), (rim, 0.022, H), CASE_COLOR,
                           bevel=0.009, kind="matte"))
    for sz_ in (-1, 1):                                                      # ...top and bottom
        parts.append(B.box(f"case_end{sz_}", (0, -0.001, sz + sz_ * (H - rim) / 2), (W - 2 * rim + 0.004, 0.022, rim),
                           CASE_COLOR, bevel=0.009, kind="matte"))
    top_z = sz + H / 2
    for sx in (-1, 1):                                                       # the handle
        parts.append(B.box(f"case_post{sx}", (sx * 0.055, 0.008, top_z + 0.018), (0.024, 0.02, 0.04), CASE_COLOR,
                           bevel=0.008, kind="matte"))
    parts.append(B.box("case_grip", (0, 0.008, top_z + 0.04), (0.134, 0.02, 0.022), CASE_COLOR, bevel=0.009,
                       kind="matte"))
    for ob in parts:
        ob.parent = pad
    if screen_video:   # the cyberspace shot itself, in sync (the push-in lands on it, then cuts to it)
        from office_set import movie_material
        mat = movie_material("ipad_img", screen_video, screen_offset, 1.5)   # (brighter: it goes through this shot's look again)
    else:
        mat = image_material("ipad_img", os.path.join(TEX, "ipad_v9.png"), 1.6)
    scr = picture(col, "ipad_screen", mat, (0, -0.001, sz), (sw, sh), "-y")
    scr.parent = pad
    glow = bpy.data.lights.new("ipadglow", "AREA")
    glow.energy, glow.size, glow.color = 1.5, 0.18, (0.75, 0.7, 1.0)
    go = bpy.data.objects.new("ipadglow", glow)
    col.objects.link(go)
    go.parent = pad
    go.location = (0, -0.05, sz)
    go.rotation_euler.x = -math.pi / 2                                      # facing out of the screen, at the toddler
    return {"user": user, "toddler": tod, "ipad": pad, "screen": scr, "head": head}


TODDLER_SHIRT, TODDLER_HAIR = "#ff8fc0", "#e2b85c"


def heart(cx, cz, size):
    """A heart outline (for printing on the shirt), centred at (cx, cz), about `size` across."""
    k = size / 34.0
    pts = []
    for i in range(24):
        t = math.tau * i / 24
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + k * x, cz + k * y))
    return pts


def build_toddler(B):
    """A two-year-old: short legs out in front (sitting on the floor), a big head with pigtails, a
    pink tee scattered with little white hearts, arms resting on the knees, eyes on the screen."""
    top = SL.fig_torso(B, SL.fig_adult_legs(B, "#4fb3f0", "#f4f4f0"), TODDLER_SHIRT)   # (full-length legs)
    z0 = top - SL.FIG["torso_h"]
    for k, (u, v, sz) in enumerate(((-0.08, 0.2, 0.05), (0.06, 0.24, 0.042), (0.0, 0.12, 0.055),
                                    (-0.09, 0.06, 0.04), (0.09, 0.09, 0.046), (-0.03, 0.22, 0.034),
                                    (0.05, 0.03, 0.036))):
        before = set(bpy.data.objects)
        SL.print_poly(B, f"heart{k}", heart(u, z0 + v, sz), "white")
        for ob in set(bpy.data.objects) - before:   # and on the back (turned round the torso's axis)
            back = ob.copy()
            B.col.objects.link(back)
            back.rotation_euler.z += math.pi
    SL.fig_arms(B, top, TODDLER_SHIRT, "fig_skin", poses=("forward", "forward"), long_sleeve=False)
    c, cyl = SL.fig_head(B, top, "fig_skin")
    SL.face_eyes(B, c, cyl)
    SL.face_mouth(B, c, "flat")
    B.sphere("hair", (0, 0.02, c + 0.075), (0.104, 0.104, 0.045), TODDLER_HAIR, kind="glossy")
    B.sphere("fringe", (0.0, -0.07, c + 0.085), (0.08, 0.03, 0.025), TODDLER_HAIR, kind="glossy")
    for sx in (-1, 1):                          # pigtails, tied with pink bobbles
        B.sphere(f"tie{sx}", (0.1 * sx, 0.03, c + 0.055), (0.022, 0.022, 0.022), "#ff5fa8", kind="glossy")
        B.sphere(f"pigtail{sx}", (0.135 * sx, 0.04, c + 0.02), (0.035, 0.035, 0.06), TODDLER_HAIR, kind="glossy",
                 rot=(0, 0.5 * sx, 0))
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
EASE_MID, EASE_LAST = 0.4, 1.3         # ...down to EASE_MID of its speed, then over the last 1.3 s to EASE_END
EASE_TIME, EASE_END = 5.0, 0.015            # ...easing in over the last 5 s almost to a stop (the screen fills the frame)
TL = (0.0, 10.0)           # time-lapse (s from the shot's start): houses go, datacenters rise
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
    a = IPAD_TILT
    base = ipad_base(hx, hy)
    sz = IPAD_SCREEN[2]
    centre = base + ipad_rot() @ Vector((0.0, -0.001, sz))
    normal = ipad_rot() @ Vector((0.0, -1.0, 0.0))
    return centre, normal


END_LENS = 110.0                              # the landing lens: long, so the camera stops above her head
IPAD_FILL = IPAD_SCREEN[0] / 2 * END_LENS / 18    # the distance at which the screen fills the frame


def drone_path():
    """(time s from the shot's start, camera, look-at, lens)."""
    win, (hx, hy) = target_window()
    ipad, nrm = ipad_screen()
    tod = Vector(((hx + TODDLER[0]) * P, (hy + TODDLER[1]) * P, 0.0))
    end = ipad + nrm * IPAD_FILL    # where the screen exactly fills the frame: up and to her left
    lx = end.x                      # the line the camera comes in on, over her left shoulder
    inside = Vector((lx, win.y + 0.3, max(end.z + 0.06, win.z + 0.1)))  # just through the window, high
    over = inside.lerp(end, (tod.y - 0.12 - inside.y) / (end.y - inside.y))   # by her shoulder, on a steady descent
    lined = Vector((lx, win.y - 1.0, inside.z + 0.12))   # lined up on the window, still descending
    W = COLS * PITCH_X * P
    D = ROWS * PITCH_Y * P
    return [
        (0.0, (2.0, -12.0, 16.0), (14.0, D * 0.5, 0.0), 28),
        (4.5, (14.0, -11.0, 15.0), (26.0, D * 0.5, 0.0), 28),
        (8.9, (30.0, -10.0, 12.0), (42.0, D * 0.5, 0.0), 28),
        (10.2, tuple(win + Vector((-4.5, -9.0, 5.5))), tuple(win + Vector((0, 0, 0.5))), 30),   # clear of the roofs
        (11.6, (lx, win.y - 4.2, win.z + 0.75), (lx, win.y, win.z), 30),   # low early (past the house across the street,
                                                                           # set back for it): the User's face shows
        (12.9, tuple(lined), tuple(ipad), 32),                              # lined up, into the room
        (14.8, tuple(inside), tuple(ipad), 33),                              # through the window
        (16.3, tuple(over), tuple(ipad), 34),
        (SHOT_LEN, tuple(end), tuple(ipad), END_LENS),     # the screen exactly fills the frame
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
    # Sideways, the curve from the flyover onto the straight line in would swing past the line and
    # come back. Instead the camera settles onto it: its offset from the line only ever shrinks
    # (a running minimum, floored at zero), smoothed along the path's length (which keeps it
    # shrinking, and leaves the rest of the path's shape alone), so it glides on with no overshoot.
    # The same for height: the flight only ever comes down.
    import numpy as np
    xyz = np.array([tuple(p) for p, _, _ in samples])
    arc_ = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))])

    def settle(off, sig=0.6):           # off: distance still to go, ending at 0; sig: metres along the path
        run = np.maximum(0.0, np.minimum.accumulate(off))
        step = 0.002                    # (smoothed on an even grid along the path, mirrored past both
        grid = np.arange(0.0, arc_[-1] + step, step)      # ends so the window never narrows and the
        g = np.interp(grid, arc_, run)                    # end stays exactly where it is)
        r = int(3 * sig / step)
        g = np.pad(g, r, mode="reflect", reflect_type="odd")
        k = np.exp(-0.5 * (np.arange(-r, r + 1) * step / sig) ** 2)
        g = np.convolve(g, k / k.sum(), mode="valid")
        return np.interp(arc_, grid, g)
    lx, lz = pts[-1][1][0], pts[-1][1][2]
    sm = settle(lx - xyz[:, 0])
    zs = lz + settle(xyz[:, 2] - lz)
    samples = [(Vector((lx - o, p.y, z)), g, l) for o, z, (p, g, l) in zip(sm, zs, samples)]
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
    def ease(t):              # a long, gentle slow-down (so it has time in the room), then a short
        def e(span, to):      # final one, so it's still pushing in when v9 starts singing
            u = min(1.0, max(0.0, (t - (T - span)) / span))
            return 1 - (1 - to) * u * u * u * (u * (6 * u - 15) + 10)
        return e(EASE_TIME, EASE_MID) * e(EASE_LAST, EASE_END / EASE_MID)
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
    # From PITCH_HOLD on, the view only ever tilts down (it would level out as the camera drops to
    # the window, then have to tip back down): its pitch is held at its lowest so far, smoothed.
    import numpy as np
    pit = np.array([math.asin(max(-1.0, min(1.0, d.z))) for d in dirs])
    j0 = int(PITCH_HOLD * rate)
    held = pit.copy()
    held[j0:] = np.minimum.accumulate(pit[j0:])
    sg = 0.45 * rate
    r = int(3 * sg)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sg) ** 2)
    k /= k.sum()
    padded = np.concatenate([np.full(r, held[0]), held, np.full(r, held[-1])])
    soft = np.convolve(padded, k, mode="valid")
    w = np.clip((np.arange(N) - (j0 - r)) / max(1, r), 0.0, 1.0)      # (the flyover before is left alone)
    new = pit * (1 - w) + soft * w
    for j in range(N):
        h = Vector((dirs[j].x, dirs[j].y, 0.0)).normalized()
        dirs[j] = (h * math.cos(new[j]) + Vector((0.0, 0.0, math.sin(new[j])))).normalized()
    lens = smooth(smooth([r[2] for r in raw], 0.5, False), 0.5, False)
    # From BLEND_START to the end, the view glides from following the path to the final view (square
    # on to the screen, its edges level, filling the frame, which matches the cyberspace shot it cuts
    # to) in one long eased blend: the turn down, the roll and the zoom all come from it, so none of
    # them overshoots, and they settle together, at rest, on the last frame.
    q_end = end_view()
    win, _ = target_window()
    jw = next(j for j in range(N) if pos[j].y >= win.y)           # when it's at the window
    t_blend = jw / rate - BLEND_LEAD
    from mathutils import Matrix
    ipad_c, _ = ipad_screen()
    up_end = q_end @ Vector((0.0, 1.0, 0.0))
    ss5 = lambda u: u * u * u * (u * (6 * u - 15) + 10)       # (no jolt at either end)
    ds = []
    for j in range(N):
        t = j / rate
        # the aim: eases from the flyover's onto the screen's centre, then stays on it (so the
        # screen stays centred all the way in, and the last frame is square on to it)
        a = ss5(min(1.0, max(0.0, (t - AIM_FROM) / (AIM_TO - AIM_FROM))))
        ds.append(dirs[j].lerp((ipad_c - pos[j]).normalized(), a).normalized())
    # (it levels off once, gently, as it drops toward the window: that keeps the User's face in frame)
    out = []
    for j in range(N):
        t = j / rate
        d = ds[j]
        # the roll and the zoom ease toward the final view's
        b = ss5(min(1.0, max(0.0, (t - t_blend) / (T - t_blend))) ** BLEND_LATE)
        up = Vector((0.0, 0.0, 1.0)) * (1 - b) + up_end * b
        right = d.cross(up).normalized()
        q = Matrix((right, right.cross(d), -d)).transposed().to_quaternion()
        l = math.exp(math.log(lens[j]) * (1 - b) + math.log(END_LENS) * b)
        out.append((pos[j], q, l))
    return [j / rate for j in range(N)], out


AIM_FROM, AIM_TO = 11.1, 15.0   # the aim eases onto the screen over this
PITCH_HOLD = 8.9            # from here on the view only tilts down
BLEND_LATE = 1.4            # (>1: the roll and zoom settle later, still going as v9 starts singing)
BLEND_LEAD = 6.5            # the blend to the final view starts this long before the window


def end_view():
    """The landing camera's rotation: looking straight into the screen, its edges level in frame."""
    from mathutils import Matrix
    _, nrm = ipad_screen()
    up = (ipad_rot() @ Vector((0.0, 0.0, 1.0))).normalized()     # the screen's own up, along the slab
    fwd = -nrm
    right = fwd.cross(up).normalized()
    return Matrix((right, right.cross(fwd), -fwd)).transposed().to_quaternion()


HEAD_HIDE = 0.0          # (the camera stays above her head now; nothing is hidden)


def head_visible(S, cam_loc):
    """False once the camera is (nearly) where her eyes are, at the end of the push-in: her head
    would be behind or around the lens, so it's hidden from the camera only (it still casts
    shadows and blocks nothing on the screen pass)."""
    _, (hx, hy) = target_window()
    eye = Vector(((hx + TODDLER[0]) * P, (hy + TODDLER[1]) * P,
                  TODDLER_Z + (SL.FIG["z_adult"] + SL.FIG["torso_h"] + 0.12) * TODDLER_SCALE))
    return (Vector(cam_loc) - eye).length > HEAD_HIDE


def set_head(S, visible, frame=None):
    for ob in S["interior"]["head"]:
        ob.visible_camera = visible
        if frame is not None:
            ob.keyframe_insert("visible_camera", frame=frame)


def drone_pose(t):
    global _DRONE
    if _DRONE is None:
        _DRONE = _drone_table()
    times, samples = _DRONE
    t = min(max(t, 0.0), times[-1])
    import bisect
    i = min(len(times) - 2, max(0, bisect.bisect_right(times, t) - 1))
    f = (t - times[i]) / max(1e-9, times[i + 1] - times[i])
    (p0, q0, l0), (p1, q1, l1) = samples[i], samples[i + 1]
    p = p0.lerp(p1, f)
    q = q0.slerp(q1, f)
    return tuple(p), tuple(p + q @ Vector((0.0, 0.0, -1.0))), l0 + (l1 - l0) * f


def drone_quat(t):
    """The camera's rotation at time t (quaternion)."""
    global _DRONE
    if _DRONE is None:
        _DRONE = _drone_table()
    times, samples = _DRONE
    t = min(max(t, 0.0), times[-1])
    import bisect
    i = min(len(times) - 2, max(0, bisect.bisect_right(times, t) - 1))
    f = (t - times[i]) / max(1e-9, times[i + 1] - times[i])
    return samples[i][1].slerp(samples[i + 1][1], f)


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
STILLS = [("start", 0.2), ("lapse_a", 3.3), ("lapse_b", 6.7), ("lapse_end", 9.6), ("approach", 13.4),
          ("window", 15.0), ("room", 15.9), ("ipad", 16.6), ("front", -1),
          ("end_a", 17.4), ("end_b", 18.0), ("end_c", 18.7), ("end_d", 19.55)]


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
    ap.add_argument("--patch", help="START,END song seconds: re-render only these frames of a final (lossless) "
                                    "pass and splice them into the existing video")
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
    if A.screen and A.fly and not (A.preview or A.flat):    # (stills and previews show the screen lit)
        split_screen_pass(sc, A.layer)
    if A.fly:
        n = int(round(T * fps))
        animate_lapse(S, sc, SHOT_START, n, fps)
        for f in range(1, n + 1):
            loc, tgt, lens = drone_pose((f - 1) / fps)
            cam.location = loc
            cam.rotation_mode = "QUATERNION"
            cam.rotation_quaternion = drone_quat((f - 1) / fps)
            cam.data.lens = lens
            cam.keyframe_insert("location", frame=f)
            SL.key_rotation(cam, f)
            cam.data.keyframe_insert("lens", frame=f)
            set_head(S, head_visible(S, loc), f)
        sc.frame_start, sc.frame_end, sc.render.fps = 1, n, fps
        sc.render.image_settings.file_format = "FFMPEG"
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        final = "_final" if not (A.preview or A.flat) else ""
        if A.layer == "screen" or final:     # lossless (the screen's pixels stay the video's exactly)
            sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
            sc.render.image_settings.color_mode = "RGB"
            sc.render.ffmpeg.audio_codec = "NONE"
        if A.layer == "screen":
            target = os.path.join(A.out, f"drone_screen{final}.mkv")
        else:
            target = os.path.join(A.out, "drone_final.mkv" if final else "drone.mp4")
        if A.patch and not target.endswith(".mkv"):
            sys.exit("--patch needs a lossless (.mkv) render: drop --preview / --flat")
        import render_out
        render_out.render_movie(sc, target, fps, A.patch, SHOT_START)
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
        if t < 0:
            SL.aim(cam, tgt)
        else:
            cam.rotation_mode = "QUATERNION"
            cam.rotation_quaternion = drone_quat(t)
        cam.data.lens = lens
        set_head(S, head_visible(S, loc))
        sc.frame_set(max(1, int(round(t * fps)) + 1))     # (so the iPad shows the right frame)
        sc.render.filepath = os.path.join(A.out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__":
    main()
