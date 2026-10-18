"""The Founder's third yacht: a brick-built superyacht at anchor on open sea, late afternoon.
He stands on the aft deck; behind him, a huge LED wall rises out of the deck (two hatches drop
away, then it climbs up on chrome pylons). His first two yachts sit on the horizon.

  blender -b --factory-startup --python video/yacht_set.py -- --out video/build/yacht_stills \\
      [--preview] [--flat] [--res 1080] [--only stage_up,side]

Layout, in studs (one stud = 0.136 units, see bricks.py), plates for heights. The yacht runs
along y: the stern (transom) at y = -60, the bow tip at y = 72. The main deck's top is z = 0.
Everyone on the aft deck faces -y, toward the stern (where the camera comes in from).
  y -64..-60   swim platform, just above the water
  y -60..-24   aft deck: the Founder, the LED wall's deck slot, loungers, a bar table
  y -24..44    the superstructure: three decks, stepped back, a radar mast on top
  y  44..72    foredeck with a helipad
"""
import math
import os
import subprocess
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402
from bricks import BR, P, PL, Kit  # noqa: E402
from office_set import camera, fly_pose as _fly_pose, glass_material, picture, place_figure, wall_run  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "build", "yacht")

STERN, BOW, BEAM = -60, 72, 18            # transom y, bow tip y, half-beam (studs)
DEPTH = 26                                # hull depth below the deck, plates
WATER = -16.5 * PL                        # sea level (world z)
FOUNDER = (0.0, -44.0)                    # where the Founder stands: centred, well out in front of the wall
SY = -32                                  # the LED wall's front face (y, studs)
SW = 16                                   # its width, studs: all of it in the stage shot, behind him
LED_Z0 = 0.03                             # its bottom edge when raised (world z): just above the deck
LED_W = SW * P
LED_ASPECT = 2.0                          # 18:9 (its graphics are rendered at 2:1)
LED_H = LED_W / LED_ASPECT
LED_DROP = LED_Z0 + LED_H + 0.08          # how far it sits below the raised position when stowed

# colours
HULL, HULL_TOP, PIN, ANTIFOUL = "#1b2742", "#f2f2ee", "#c9a24a", "#7a2b2b"
WHITE, WHITE2, TRIMG = "#f4f4f0", "#e3e5e8", "#9aa1ab"
TEAK = ("#a8743f", "#9a6a38", "#b27e48")
WINDOW, CUSHION, CHROME = "#26394d", "#f1ede2", "#d7dde3"


def hw(y, d=0):
    """Hull half-width (studs) at y, d plates below the deck: full beam aft, tapering to a fine
    bow; the sides tuck in going down and the bow rakes back."""
    y = y + 0.5 * d
    u = max(0.0, (y - 18) / (BOW - 18))
    w = BEAM * max(0.0, 1 - u ** 1.8) if u < 1 else 0.0
    if y < STERN + 3:   # rounded transom corners
        w -= 0.6 * (STERN + 3 - y) / 3
    return max(0.0, w - 0.14 * d)


def textures():
    """The transom's name plate and a stand-in picture for the LED wall."""
    os.makedirs(TEX, exist_ok=True)
    name = os.path.join(TEX, "name.png")
    if not os.path.exists(name):
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new("RGBA", (2400, 600), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        f1 = ImageFont.truetype("/usr/share/fonts/opentype/urw-base35/C059-BdIta.otf", 300)
        f2 = ImageFont.truetype("/usr/share/fonts/opentype/urw-base35/URWGothic-Demi.otf", 110)
        dr.text((1200, 230), "Severance", font=f1, fill=(214, 178, 96, 255), anchor="mm")
        dr.text((1200, 500), "GEORGE TOWN", font=f2, fill=(214, 178, 96, 255), anchor="mm")
        im.save(name)
    ph = os.path.join(TEX, "led_placeholder.png")
    if not os.path.exists(ph):
        src = os.path.join(HERE, "build", "screen_v1c1.mkv")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "42.3", "-i", src, "-frames:v", "1",
                        "-vf", "crop=iw:iw/2", ph], check=True)     # a 16:9 frame cropped to 2:1


# ---------------------------------------------------------------- materials
def sea_material():
    """Deep blue-green water with small moving waves (the noise's W is keyed by animate_sea)."""
    m = bpy.data.materials.new("sea")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (0.01, 0.06, 0.09, 1)
    bs.inputs["Roughness"].default_value = 0.06
    bs.inputs["IOR"].default_value = 1.33
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 2.2, 1.0)    # longer crests across x
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.name = "waves"
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 2.2
    nz.inputs["Detail"].default_value = 8.0
    nz.inputs["Roughness"].default_value = 0.55
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    bump.inputs["Distance"].default_value = 0.05
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (0.02, 0.12, 0.2, 1)
    return m


def animate_sea(m, n, fps, speed=0.12):
    w = m.node_tree.nodes["waves"].inputs["W"]
    for f, v in ((1, 0.0), (n, speed * n / fps)):
        w.default_value = v
        w.keyframe_insert("default_value", frame=f)
    for fc in m.node_tree.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def decal_material(name, path):
    """A printed, transparent image (the gold name on the transom)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bs.inputs["Alpha"])
    bs.inputs["Metallic"].default_value = 0.8
    bs.inputs["Roughness"].default_value = 0.25
    m.surface_render_method = "BLENDED"
    m.diffuse_color = (0.8, 0.65, 0.3, 1)
    return m


def led_material(path, movie=False, offset=0, strength=2.0):
    """The LED wall: a flawless, seamless picture (or video), lit from within."""
    m = bpy.data.materials.new("led")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    if movie:
        tex.image.source = "MOVIE"
        iu = tex.image_user
        iu.frame_duration = tex.image.frame_duration
        iu.frame_start, iu.frame_offset, iu.use_auto_refresh = 1 + offset, 0, True
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- the yacht
def build_hull(K):
    """Plate by plate, a shell along each side (thick enough where the outline steps that no gaps
    open), the transom across the stern; teak planks on deck; a white gunwale."""
    for d in range(1, DEPTH + 1):
        z = -d
        color = (HULL_TOP if d == 1 else PIN if d == 6 else ANTIFOUL if d >= 16 else HULL)
        rows = range(STERN, BOW + 1)
        ws = {y: int(round(hw(y + 0.5, d))) for y in range(STERN - 1, BOW + 2)}
        for y in rows:
            w = ws[y]
            if w <= 0:
                continue
            if y == STERN:
                K.piece(-w, y, z, 2 * w, 1, 1, color, studs=False)      # the transom
                continue
            t = max(1, w - min(ws[y - 1], ws[y + 1]) + 1)
            t = min(t, w)
            if t >= w:
                K.piece(-w, y, z, 2 * w, 1, 1, color, studs=False)
            else:
                K.piece(-w, y, z, t, 1, 1, color, studs=False)
                K.piece(w - t, y, z, t, 1, 1, color, studs=False)
    # deck planks: 1 x 6 tiles running fore and aft, staggered, inside the gunwale; the LED slot
    # is left open
    slot = (-SW / 2 - 1, SY - 1, SW / 2 + 1, SY + 2)
    for c in range(-BEAM, BEAM):
        y = STERN + 1
        k = (c * 7) % 6
        while y < BOW:
            inside = lambda yy: abs(c + 0.5) + 0.5 <= hw(yy + 0.5) - 1
            if not inside(y) or (slot[0] <= c < slot[2] and slot[1] <= y < slot[3]):
                y += 1
                continue
            L = 6 - k if k else 6
            k = 0
            n = 0
            while n < L and inside(y + n) and not (slot[0] <= c < slot[2] and slot[1] <= y + n < slot[3]):
                n += 1
            K.tile(c, y, -1, 1, n, TEAK[(c + y) % 3], kind="matte")
            y += n
    # gunwale: a white plate along the deck edge
    for y in range(STERN, BOW):
        w = int(round(hw(y + 0.5)))
        if w <= 0:
            continue
        if y == STERN:
            K.plate(-w, y, 0, 2 * w, 1, HULL_TOP, studs=False)
        else:
            K.plate(-w, y, 0, 1, 1, HULL_TOP, studs=False)
            K.plate(w - 1, y, 0, 1, 1, HULL_TOP, studs=False)
    # hull windows: a long dark band of glass on each side, in the navy
    for y0 in range(-44, 22, 9):
        for s in (-1, 1):
            w = hw(y0 + 3, 4) * P
            K.box(s * w - 0.005 if s > 0 else -w - 0.004, y0 * P, -4.6 * PL, s * w + 0.004 if s > 0 else -w + 0.005,
                  (y0 + 7) * P, -2.8 * PL, WINDOW, kind="chrome")
    # swim platform, just above the water, and the steps down to it
    K.box(-14 * P, (STERN - 4) * P, -15 * PL, 14 * P, STERN * P, -14 * PL, HULL)
    for x in range(-14, 14, 2):
        K.tile(x, STERN - 4, -14, 2, 4, TEAK[x % 3], kind="matte")


def glass_rail(K, axis, fixed, a0, a1, z, posts=6, h=7):
    """A frameless glass bulwark with a chrome top rail and posts, along x or y (studs), its
    bottom at plate z, h plates tall."""
    t0, t1 = (fixed + 0.42) * P, (fixed + 0.58) * P
    if axis == "y":
        K.box(t0, a0 * P, z * PL, t1, a1 * P, (z + h) * PL, "glass", kind="glass")
        K.box(t0 - 0.006, a0 * P, (z + h) * PL, t1 + 0.006, a1 * P, (z + h) * PL + 0.012, CHROME, kind="chrome")
    else:
        K.box(a0 * P, t0, z * PL, a1 * P, t1, (z + h) * PL, "glass", kind="glass")
        K.box(a0 * P, t0 - 0.006, (z + h) * PL, a1 * P, t1 + 0.006, (z + h) * PL + 0.012, CHROME, kind="chrome")
    a = a0
    while a <= a1 + 1e-6:
        cx, cy = ((fixed + 0.5) * P, a * P) if axis == "y" else (a * P, (fixed + 0.5) * P)
        K.cyl(cx, cy, z * PL, (z + h) * PL + 0.012, 0.011, CHROME, kind="chrome", sides=8)
        a += posts


def level(K, w0, y0, y1, taper, z0, z1, band, over=1, aft_doors=True, front_glass=False):
    """One deck of the superstructure, built row by row like the hull: full width w0 aft,
    curving in toward its front from y = taper. White brick walls with a long band of dark glass
    (plates band[0]..band[1]); glass doors across the aft end; a roof plate overhanging by
    `over` studs. Returns its half-width function."""
    def w(y):
        u = max(0.0, (y + 0.5 - taper) / (y1 - taper))
        return w0 * (1 - 0.5 * u ** 2)
    ws = {y: int(round(w(y))) for y in range(y0 - 1, y1 + 1)}
    b0, b1 = band

    def column(x, y, t, d, glass=True):
        """Wall from z0 to z1 at (x, y), t studs wide and d deep: bricks, the glass band."""
        for z in range(z0, z1, 3):
            top = min(z1, z + 3)
            if glass and b0 <= z < b1:
                continue
            K.piece(x, y, z, t, d, top - z, WHITE, studs=False)
        if glass:
            K.box((x + 0.05) * P, (y + 0.02) * P, b0 * PL, (x + t - 0.05) * P, (y + d - 0.02) * P, b1 * PL,
                  WINDOW, kind="chrome")

    for y in range(y0, y1):
        W = ws[y]
        if y == y0:   # the aft face: corners, glass doors between them, a header above
            column(-W, y, 2, 1, glass=False)
            column(W - 2, y, 2, 1, glass=False)
            top = b1 if aft_doors else b0
            K.box((-W + 2) * P, (y + 0.3) * P, (z0 if aft_doors else b0) * PL, (W - 2) * P, (y + 0.7) * P, b1 * PL,
                  WINDOW, kind="chrome")
            for x in range(-W + 2 + 4, W - 2, 4):     # door mullions
                K.box(x * P - 0.008, y * P + 0.02, (z0 if aft_doors else b0) * PL, x * P + 0.008, (y + 0.3) * P,
                      b1 * PL, TRIMG)
            for z in range(top, z1, 3):
                K.piece(-W + 2, y, z, 2 * W - 4, 1, min(3, z1 - z), WHITE, studs=False)
            if not aft_doors:
                for z in range(z0, b0, 3):
                    K.piece(-W + 2, y, z, 2 * W - 4, 1, min(3, b0 - z), WHITE, studs=False)
            continue
        if y == y1 - 1:   # the front face
            column(-W, y, 2 * W, 1, glass=front_glass)
            continue
        t = min(W, max(1, W - ws[y + 1] + 1))
        column(-W, y, t, 1)
        column(W - t, y, t, 1)
    # roof: one plate per row, overhanging; a grey fascia under its aft edge
    for y in range(y0 - over - 1, y1 + over):
        W = int(round(w(min(max(y, y0), y1 - 1)))) + over
        K.piece(-W, y, z1, 2 * W, 1, 1, WHITE, studs=False)
    W = ws[y0] + over
    K.box(-W * P, (y0 - over - 1) * P, z1 * PL - 0.012, W * P, (y0 - over - 1) * P + 0.012, z1 * PL, TRIMG)
    return w


def lounger(K, x, y, z=0, color=CUSHION):
    """A sun lounger 2 x 6 studs, backrest toward +y."""
    K.plate(x, y, z, 2, 6, WHITE2, studs=False)
    K.box((x + 0.1) * P, (y + 0.1) * P, (z + 1) * PL, (x + 1.9) * P, (y + 4.2) * P, (z + 1.8) * PL, color)
    K.box((x + 0.1) * P, (y + 4.2) * P, (z + 1) * PL, (x + 1.9) * P, (y + 5.9) * P, (z + 5.5) * PL, color)


def build_yacht(K):
    build_hull(K)
    level(K, 15, -24, 42, 18, 0, 15, (3, 12))            # main deck saloon
    level(K, 12, -14, 36, 12, 16, 31, (18, 28))          # upper deck
    level(K, 9, 0, 28, 8, 32, 44, (35, 42), front_glass=True)   # the bridge
    # radar mast: two raked legs, a crossbar, radomes, antennas
    for s in (-1, 1):
        for k, z in enumerate(range(45, 63, 3)):
            K.brick(s * 5 - (1 if s < 0 else 0), 12 + k // 2, z, 1, 3, WHITE, studs=False)
    K.piece(-6, 14, 63, 12, 4, 2, WHITE, studs=False)
    for x in (-4.5, 1.5):
        K.round(x, 14.5, 65, 3, 2, WHITE, studs=False)
        K.round(x + 0.25, 14.75, 67, 2.5, 1, WHITE, studs=False)
    K.box(-0.6 * P, 15.6 * P, 65 * PL, 0.6 * P, 16.4 * P, 66 * PL, TRIMG)
    K.box(-3.5 * P, 15.9 * P, 66 * PL, 3.5 * P, 16.1 * P, 66.6 * PL, "#2a2d33")       # radar bar
    for x in (-5.5, 5.5):
        K.cyl(x * P, 15.5 * P, 65 * PL, 78 * PL, 0.008, TRIMG, sides=6)
    # rails: the aft main deck, the side decks, the upper decks' aft ends
    # the stern is open (no rail: the stage shot's camera dollies across behind it), with steps
    # down to the platform
    for k in range(4):                          # steps down to the swim platform
        top = -2 - 3 * k
        K.piece(-6, STERN - 1 - k, -14, 12, 1, top + 14, HULL, studs=False)
        K.tile(-6, STERN - 1 - k, top, 12, 1, TEAK[k % 3], kind="matte")
    for s in (-1, 1):
        fx = (BEAM - 1) if s > 0 else -BEAM
        glass_rail(K, "y", fx, STERN + 0.5, 18, 1)
    for s in (-1, 1):
        glass_rail(K, "y", 15 if s > 0 else -16, -26, 18, 16, h=7)
        glass_rail(K, "y", 12 if s > 0 else -13, -16, 12, 32, h=7)
    glass_rail(K, "x", -27, -16, 16, 16, h=7)
    glass_rail(K, "x", -16, -13, 13, 32, h=7)
    # aft deck furniture: loungers to port, a bar table and stools to starboard
    for y in (-42, -35):          # along the port side, out of the stage shot
        lounger(K, -16, y)
        lounger(K, -13, y)
    bx, by = 13.5, -57.0          # out by the starboard rail, clear of the stage shot's dolly
    K.round(bx, by, 0, 2, 7, CHROME, studs=False, kind="chrome")          # bar table
    K.round(bx - 1, by - 1, 7, 4, 1, WHITE, studs=False)
    K.round(bx + 0.5, by + 0.5, 8, 1, 2.5, CHROME, studs=False, kind="chrome")    # champagne bucket
    K.cyl((bx + 1.2) * P, (by + 1.2) * P, 8 * PL, 11.5 * PL, 0.018, "#1f4a2e", sides=10)  # the bottle
    for x, y in ((bx + 2.6, by - 1.5), (bx + 2.6, by + 1.8), (bx + 0.5, by + 3.0)):   # stools
        K.round(x, y, 0, 1, 5, CHROME, studs=False, kind="chrome")
        K.round(x - 0.25, y - 0.25, 5, 1.5, 0.8, "#1b2742", studs=False)
    # upper aft deck: a hot tub
    K.round(-5, -25, 16, 10, 4, WHITE, studs=False)
    K.round(-4.5, -24.5, 19.9, 9, 0.3, "#3fb6d8", studs=False, kind="glass")
    # foredeck: a helipad
    K.round(-7, 43, 0, 14, 0.5, "#3b3f46", studs=False)
    for a in range(40):
        ang = math.tau * a / 40
        K.box((5.9 * math.cos(ang) - 0.25) * P, (50 + 5.9 * math.sin(ang) - 0.25) * P, 0.5 * PL,
              (5.9 * math.cos(ang) + 0.25) * P, (50 + 5.9 * math.sin(ang) + 0.25) * P, 0.62 * PL, "#f2c230")
    for x0, y0, x1, y1 in ((-2.4, 47.2, -1.6, 52.8), (1.6, 47.2, 2.4, 52.8), (-1.6, 49.6, 1.6, 50.4)):
        K.box(x0 * P, y0 * P, 0.5 * PL, x1 * P, y1 * P, 0.62 * PL, WHITE)
    # bow: anchor windlasses and a flagstaff at the stern
    for x in (-3, 2):
        K.round(x, 60, 0, 1, 2, TRIMG, studs=False)


def build_led(B, col, screen_video=None, screen_offset=0):
    """The LED wall and its lift, built raised; parented to an empty that lowers it into the hull.
    Two deck hatches cover its slot when it's stowed. Returns (rig, hatches, led plane)."""
    K = Kit(B)
    x0, x1, z0, z1 = -LED_W / 2, LED_W / 2, LED_Z0, LED_Z0 + LED_H
    y0 = SY * P
    K.box(x0 - 0.035, y0, z0 - 0.035, x1 + 0.035, y0 + 0.11, z1 + 0.035, "#141519")       # frame
    for k in range(1, 4):                                                                   # rear ribs
        x = x0 + LED_W * k / 4
        K.box(x - 0.03, y0 + 0.11, z0, x + 0.03, y0 + 0.17, z1, "#3a3e46")
    for s in (-1, 1):                                                                        # pylons
        cx = s * LED_W * 0.3
        K.box(cx - 0.06, y0 + 0.12, z0 - LED_DROP - 0.1, cx + 0.06, y0 + 0.26, z0 + 0.25, CHROME, kind="chrome")
    K.box(x0 + 0.1, y0 + 0.02, z0 - 0.09, x1 - 0.1, y0 + 0.2, z0 - 0.035, "#141519")       # base beam
    rig_mesh = K.build("led_wall")
    rig = bpy.data.objects.new("led_rig", None)
    col.objects.link(rig)
    rig_mesh.parent = rig
    textures()
    mat = (led_material(screen_video, movie=True, offset=screen_offset) if screen_video else
           led_material(os.path.join(TEX, "led_placeholder.png")))
    led = picture(col, "led", mat,
                  (0, y0 - 0.002, (z0 + z1) / 2), (LED_W, LED_H), "-y")
    led.parent = rig
    # the slot's dark well, and the two hatches over it
    K = Kit(B)
    sx0, sx1 = (-SW / 2 - 1) * P, (SW / 2 + 1) * P
    sy0, sy1 = (SY - 1) * P, (SY + 2) * P
    K.box(sx0, sy0, -1.0, sx1, sy1, -PL - 0.01, "#0c0d10", kind="matte")
    K.build("led_well")
    K = Kit(B)
    K.box(sx0 + 0.002, sy0 + 0.002, -PL, sx1 - 0.002, sy1 - 0.002, -0.003, TEAK[1], kind="matte")
    for k in range(1, 3):    # plank lines, so it reads as part of the deck
        y = sy0 + (sy1 - sy0) * k / 3
        K.box(sx0 + 0.004, y - 0.002, -0.0035, sx1 - 0.004, y + 0.002, -0.0025, "#5a3c20")
    hatches = [K.build("hatch")]
    return rig, hatches, led


def set_led(S, u):
    """Pose the LED wall for progress u (0 stowed .. 1 raised): the hatch drops and slides aft
    under the deck in the first 20%, then the wall climbs, slowing as it arrives."""
    h = min(1.0, max(0.0, u / 0.2))
    drop, slide = min(1.0, h / 0.3), max(0.0, (h - 0.3) / 0.7)
    for hatch in S["hatches"]:   # drops, then slides aft under the deck
        hatch.location = (0, -slide * 4.0 * P, -0.07 * drop)
    r = min(1.0, max(0.0, (u - 0.2) / 0.8))
    r = 1 - (1 - r) ** 2          # starts briskly (it's already rising as the verse begins), slows to a stop
    S["rig"].location = (0, 0, -LED_DROP * (1 - r))


def animate_led(S, t0, dur, start, n, fps):
    """Keyframe the rise: it starts at time t0 (s) and takes dur seconds."""
    for f in range(1, n + 1):
        t = start + (f - 1) / fps
        if t < t0 - 0.1 / fps and f > 1 and t + 1 / fps < t0:
            continue
        set_led(S, (t - t0) / dur)
        for ob in [S["rig"]] + S["hatches"]:
            ob.keyframe_insert("location", frame=f)
        if t > t0 + dur:
            break


def founder_spot():
    """Where the Founder stands: on the aft deck, in front of and right of the LED wall."""
    return (FOUNDER[0] * P, FOUNDER[1] * P, 0.0)


def build(sc, founder=True, others=True, screen_video=None, screen_offset=0):
    textures()
    col = sc.collection
    B = SL.Builder("fig", col)
    B.mats[("glass", "glass")] = glass_material()
    K = Kit(B)
    build_yacht(K)
    yacht = K.build("yacht")
    nm = decal_material("name", os.path.join(TEX, "name.png"))   # on both quarters, below the pinstripe
    for s, f in ((-1, "-x"), (1, "+x")):
        x = s * (int(round(hw(-51.5, 9))) * P + 0.003)
        picture(col, f"name{f}", nm, (x, -51.5 * P, -9.5 * PL), (1.2, 0.3), f)
    rig, hatches, led = build_led(B, col, screen_video, screen_offset)
    # the sea
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, WATER))
    sea = bpy.context.object
    sea.name = "sea"
    sm = sea_material()
    sea.data.materials.append(sm)
    # his first two yachts, out on the horizon (copies of this one)
    if others:
        for k, (loc, rot) in enumerate((((-32.0, 70.0, 0.0), 2.3), ((46.0, 120.0, 0.0), -0.9))):
            c = yacht.copy()
            col.objects.link(c)
            c.location, c.rotation_euler.z = loc, rot
    fig = place_figure(SL.build_founder, B, founder_spot()) if founder else None
    S = {"yacht": yacht, "rig": rig, "hatches": hatches, "led": led, "sea": sm, "founder": fig}
    lighting(sc)
    return S


SUN_DIR = (-0.55, -1.0, 0.36)   # toward the sun: low, behind the camera's left shoulder


def lighting(sc):
    """Late-afternoon sun from behind the camera, a clear sky."""
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    nt = sc.world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    d = SUN_DIR
    sky.sun_elevation = math.atan2(d[2], math.hypot(d[0], d[1]))
    sky.sun_rotation = math.atan2(d[0], d[1]) * -1 + math.pi / 2 * 0
    sky.sun_disc = True
    sky.altitude = 50
    sky.air_density, sky.dust_density, sky.ozone_density = 1.0, 0.4, 1.5
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.12
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy, ld.angle, ld.color = 4.5, math.radians(1.5), (1.0, 0.86, 0.68)
    sun = bpy.data.objects.new("sun", ld)
    sc.collection.objects.link(sun)
    SL.aim(sun, tuple(-c for c in d))


def setup_render(sc, res, preview):
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = res
    sc.render.resolution_x = res * 16 // 9
    sc.eevee.taa_render_samples = 1 if preview else 32
    sc.eevee.use_raytracing = not preview
    sc.eevee.use_fast_gi = not preview
    sc.eevee.shadow_pool_size = "1024"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -1.0
    sc.render.image_settings.file_format = "PNG"


# The stage shot: him head to toe (like the Manager's in the office), from further back with a
# long lens. The camera is low, looking up: the top of the LED wall at the top of the frame, his
# shoes at the bottom. (centre, distance, height, lens)
STAGE_CENTRE = (FOUNDER[0] * P, FOUNDER[1] * P + 0.8, 0.49)   # between him and the wall
STAGE_VIEW = (STAGE_CENTRE, 5.5, 0.18, 95)      # back, low and long: the wall looms behind him


def stage_pose(side=0.0, dist=None, dz=0.0):
    """Camera (location, target, lens) for the stage shot. The camera dollies sideways while
    staying aimed at the middle of the wall, so the wall holds still in frame and he slides across
    it: side is where he appears on the wall, -1 its left edge .. 0 centre .. 1 its right edge."""
    (cx, cy, cz), d0, h, lens = STAGE_VIEW
    d = d0 if dist is None else dist
    cam_y = cy - d
    ls, lf = SY * P - cam_y, FOUNDER[1] * P - cam_y     # camera to the wall, and to him
    tz = h + (cz - h) * ls / d                          # the aim point, on the wall
    x = side * LED_W / 2 / (1 - ls / lf)                # the dolly that puts him there
    return (cx + x, cam_y, h + dz), (cx, SY * P, tz + dz), lens


# Where he sits on the wall, to leave room for the graphics: (song time the move starts, side),
# each a 2 s dolly, eased in and out (smootherstep). He starts centred. (Examples for now, moving just before lines.)
DOLLY = [
    (79.6, -0.75),    # "So I'll keep a human handy..."   him on the left
    (84.4, 0.75),     # "One Kevin per division..."       right
    (93.0, 0.0),     # "Per division?..."                centre
    (98.2, -0.75),    # chorus: "We need a meat proxy..." left
    (106.0, 0.75),    # "The bot breaks fifty laws..."    right
    (115.4, 0.0),    # "Grease a couple senators..."     centre
]
DOLLY_MOVE = 2.0


FACE_TURN = 0.7    # after each dolly lands, he turns to face the camera over this many seconds


def face_yaw(side):
    """The turn (radians, about z) that has him facing the camera when it's dollied to `side`."""
    loc, _, _ = stage_pose(side)
    return math.atan2(loc[0] - FOUNDER[0] * P, FOUNDER[1] * P - loc[1])


def facing_at(t, moves=None):
    """His turn toward the camera at song time t: each turn starts once its dolly has landed."""
    moves = DOLLY if moves is None else moves
    a = 0.0
    for t0, side in moves:
        u = min(1.0, max(0.0, (t - t0 - DOLLY_MOVE) / FACE_TURN))
        a += (face_yaw(side) - a) * u * u * u * (u * (6 * u - 15) + 10)
    return a


def side_at(t, moves=None):
    moves = DOLLY if moves is None else moves
    s = 0.0
    for t0, side in moves:
        u = min(1.0, max(0.0, (t - t0) / DOLLY_MOVE))
        s += (side - s) * u * u * u * (u * (6 * u - 15) + 10)   # smootherstep: soft start and landing
    return s


# The opening zoom (times from the start of verse 2): from off the port quarter, close enough to
# read the screen, low over the water, in toward the stern, settling on the stage shot while he sings the first lines.
FLY = [
    (0.0, (-3.2, -17.5, 1.25), (0.0, -5.0, 0.55), 45),
    (3.5, (-2.0, -14.0, 0.8), (0.0, -5.3, 0.55), 50),
    (7.0, (-0.8, -11.6, 0.4), (0.05, -5.5, 0.5), 60),
    (11.0, *stage_pose()),
]
LED_RISE = (63.8, 9.5)    # (song time it starts, seconds it takes): the hatch is open and the wall
                          # just emerging when verse 2 starts (66.4); fully up by about 73


def fly_pose(t):
    return _fly_pose(t, FLY)


# check stills: (name, location, target, lens, LED progress)
STILLS = [
    ("approach", (-5.5, -34.0, 2.1), (0.0, -2.0, 0.6), 50, 0.0),
    ("closer", (-1.6, -15.0, 1.0), (0.2, -4.8, 0.7), 40, 0.0),
    ("stage_down", *stage_pose(), 0.0),
    ("stage_rising", *stage_pose(), 0.55),
    ("stage_up", *stage_pose(), 1.0),
    ("stage_left", *stage_pose(-0.75), 1.0),    # dollied over: him toward the wall's left end
    ("stage_right", *stage_pose(0.75), 1.0),     # ...and its right
    ("side", (24.0, -6.0, 3.2), (0.0, 0.5, 1.0), 35, 1.0),
    ("aerial", (-9.0, -17.0, 8.5), (0.0, -2.5, 0.5), 30, 1.0),
]


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "build", "yacht_stills"))
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--flat", action="store_true")
    ap.add_argument("--only", help="comma-separated still names")
    A = ap.parse_args(argv)
    res = A.res or (540 if A.preview or A.flat else 1080)
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    S = build(sc)
    setup_render(sc, res, A.preview)
    if A.flat:
        import lipsync_demo as LS
        LS.flat_look(sc)
    os.makedirs(A.out, exist_ok=True)
    for name, loc, tgt, lens, u in STILLS:
        if A.only and name not in A.only.split(","):
            continue
        set_led(S, u)
        camera(sc, loc, tgt, lens)
        sc.render.filepath = os.path.join(A.out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__":
    main()
