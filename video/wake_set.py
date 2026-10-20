"""The outro: first person. Kevin (grown up) wakes in his childhood bedroom. Black, then his
eyelids crack open on a fuzzy brick ceiling in the cold before dawn; his arm comes up into view
holding his phone, where v9 (in the void) gives her calm little morning monologue with big
one-word captions.

  blender -b --factory-startup --python video/wake_set.py -- --out video/build/wake_stills \\
      [--preview] [--res 1080] [--only open,phone]
  ... -- --fly --screen video/build/wake_phone.mkv [--preview] [--pass main|screen] [--patch A,B]
                                     the whole shot (song 245.6 .. 259.2)

The world: Kevin lies on his back in bed, head toward +y, face up. His upper body is a normal
minifig (built facing -y, standing), turned to lie down, so its arm poses work as usual; only his
right arm is seen. The camera is at his eyes, looking up at the ceiling and a little toward his
feet, the top of the picture toward the top of his head. The eyelids are two dark shapes just in
front of the lens: a separate soft-edged overlay (wake_lids.py), laid over this in assembly.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402
from bricks import P, PL, Kit  # noqa: E402
from office_set import image_material, picture  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build", "wake")

EYE_Z = 0.42                       # his eyes, lying on the bed (world)
# the room, in studs (x, y) and plates (z): the walls' inner faces, the ceiling's underside
SX0, SX1, SY0, SY1, CZ = -6, 6, -15, 2, 24
WIN_S = (-10, -3, 12, 21)          # the window in the x0 wall: y0, y1 (studs), z0, z1 (plates)
CEIL = CZ * PL
ROOM = (SX0 * P, SX1 * P, SY0 * P, SY1 * P)   # x0 (the window's side), x1, y0 (his feet's end), y1 (behind his head)
WIN = (WIN_S[0] * P, WIN_S[1] * P, WIN_S[2] * PL, WIN_S[3] * PL)
FIG_EYE = Vector((0.0, -0.075, 0.70))   # his eyes in figure space (standing, facing -y)
SLEEVE, SKIN = "#5a6f8c", "fig_skin"     # a faded blue long-sleeved tee
PHONE = (0.105, 0.011, 0.19)       # phone: width, thickness, height (a big one)
SCREEN = (0.095, 0.1689)           # its screen (9:16)
LOOK_TILT = math.radians(30)       # the view tips this far from straight up toward his feet...
LOOK_SIDE = math.radians(16)       # ...and turns this far toward the window (his head's on one side)
LENS = 21
FUZZY_FOCUS = 0.08                 # (just woken: focused on nothing, so the room is a blur)
SUN_SOFT = 2.0                     # the light's apparent size (degrees): soft-edged stripes
SUN_ELEV, SUN_AZ = math.radians(-24), math.radians(-12)  # the light comes up from below the window, a little from his feet
FSTOP_GROGGY, FSTOP_AWAKE = 0.7, 2.4   # very shallow focus just woken; awake, the room is soft but reads
PHONE_AT = (0.035, -0.01, -0.36)   # the screen's centre in camera space (right, up, -ahead)
PHONE_ROLL = math.radians(-6)      # (a little off level, held in one hand)
PHONE_TILT = math.radians(10)
GRIP_SPIN = math.radians(120)       # turns his forearm round the phone's edge (out to the lower right)


def lying():
    """Figure space -> world: turned to lie on his back, his eyes at (0, 0, EYE_Z)."""
    R = Matrix.Rotation(-math.pi / 2, 4, "X")     # figure -y (front) -> world +z, figure +z -> world +y
    T = Matrix.Translation(Vector((0.0, 0.0, EYE_Z)) - (R @ FIG_EYE))
    return T @ R


def poster_image():
    """A faded childhood poster: a rocket in a starry sky."""
    from PIL import Image, ImageDraw
    path = os.path.join(BUILD, "poster.png")
    if os.path.exists(path):
        return path
    os.makedirs(BUILD, exist_ok=True)
    W, H = 300, 420
    im = Image.new("RGB", (W, H), (44, 62, 112))
    d = ImageDraw.Draw(im)
    import random
    rng = random.Random(2)
    for _ in range(60):
        x, y = rng.randrange(W), rng.randrange(H)
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(230, 226, 200))
    d.polygon([(150, 70), (185, 160), (185, 300), (115, 300), (115, 160)], fill=(236, 232, 224))   # body
    d.polygon([(150, 70), (178, 140), (122, 140)], fill=(205, 70, 60))                            # nose
    d.polygon([(115, 240), (80, 320), (115, 300)], fill=(205, 70, 60))                            # fins
    d.polygon([(185, 240), (220, 320), (185, 300)], fill=(205, 70, 60))
    d.ellipse((132, 175, 168, 211), fill=(120, 170, 220), outline=(90, 90, 100), width=4)          # window
    d.polygon([(122, 300), (178, 300), (150, 380)], fill=(250, 190, 80))                          # flame
    d.rectangle((0, 0, W - 1, H - 1), outline=(240, 236, 226), width=10)
    im = Image.blend(im, Image.new("RGB", (W, H), (200, 196, 186)), 0.25)                           # (faded)
    im.save(path)
    return path


def build_room(B):
    """All bricks and plates on the stud grid: brick walls (running bond), a ceiling of plates
    (seen from underneath), a window framed in tiles with blinds, a lamp of round plates, a shelf."""
    from office_set import wall_run
    x0, x1, y0, y1 = ROOM
    WALL, TRIM = "#c4ccd6", "#f2f2ee"
    K = Kit(B)
    # the ceiling: smooth 1x4 tiles (no studs), in running bond, their seams showing from below
    for col_i, x in enumerate(range(SX0 - 1, SX1 + 1)):
        y = SY0 - 1 - (2 if col_i % 2 else 0)
        while y < SY1 + 1:
            a, b = max(y, SY0 - 1), min(y + 4, SY1 + 1)
            if b > a:
                K.piece(x, a, CZ, 1, b - a, 1, "#e2dccd", studs=False)
            y += 4
    # the walls, one stud thick, outside the room's inner faces; the top course is the trim
    wy0, wy1, wz0, wz1 = WIN_S
    wall_run(K, "y", SX0 - 1, SY0 - 1, SY1 + 1, 0, CZ - 3, WALL, openings=[(wy0, wy1, wz0, wz1)])
    wall_run(K, "y", SX1, SY0 - 1, SY1 + 1, 0, CZ - 3, WALL)
    wall_run(K, "x", SY0 - 1, SX0, SX1, 0, CZ - 3, WALL)
    wall_run(K, "x", SY1, SX0, SX1, 0, CZ - 3, WALL)
    for args in (("y", SX0 - 1, SY0 - 1, SY1 + 1), ("y", SX1, SY0 - 1, SY1 + 1),
                 ("x", SY0 - 1, SX0, SX1), ("x", SY1, SX0, SX1)):
        wall_run(K, *args, CZ - 3, CZ, TRIM)
    # the window: a frame of white tiles round the opening (sill, head, jambs)
    K.piece(SX0 - 1, wy0 - 1, wz0 - 1, 2, wy1 - wy0 + 2, 1, TRIM, studs=False)           # sill
    K.piece(SX0 - 1, wy0 - 1, wz1, 1, wy1 - wy0 + 2, 1, TRIM, studs=False)               # head
    for wy in (wy0 - 1, wy1):
        K.piece(SX0 - 1, wy, wz0, 1, 1, wz1 - wz0, TRIM, studs=False)                  # jambs
    # half-open blinds: the dawn comes through them in stripes across the ceiling
    z = wz1 * PL - 0.03
    while z > wz0 * PL + 0.02:
        K.box(x0 + 0.01, wy0 * P, z - 0.004, x0 + 0.03, wy1 * P, z + 0.004, "#e8e4da")
        z -= 0.034
    # a lamp of round plates under the ceiling, over the bed
    K.round(-1.5, -6.5, CZ - 1, 3, 1, "#efe9dc", studs=False)
    K.round(-1, -6, CZ - 2, 2, 1, "#fff6e0", studs=False)
    # a shelf (a plate on brackets) high on the right wall, with an old trophy and some books
    K.piece(SX1 - 2, -9, CZ - 7, 2, 6, 1, "#8a6a4a", studs=True)
    for yy in (-9, -4):
        K.piece(SX1 - 1, yy, CZ - 9, 1, 1, 2, "#8a6a4a", studs=False)
    K.round(SX1 - 2, -8, CZ - 6, 1, 1, "#d9a520")
    K.round(SX1 - 2, -8, CZ - 5, 1, 3, "#d9a520", studs=False)
    K.round(SX1 - 2, -8, CZ - 2, 1, 1, "#d9a520")
    for k, (col_, h) in enumerate((("#3a5fa0", 4), ("#c8323c", 5), ("#3a8a4a", 4), ("#e8b04a", 5))):
        K.piece(SX1 - 2, -6 + k, CZ - 6, 2, 1, h, col_, studs=False)
    picture(B.col, "poster", image_material("poster", poster_image(), 0.0, emit=False),
            (0.0, y0 + 0.002, (CZ - 9) * PL), (0.26, 0.364), "+y")       # on the wall at his feet
    room = K.build("room")
    # glow-in-the-dark stars stuck on the ceiling years ago, mostly faded
    import random
    rng = random.Random(4)
    m = bpy.data.materials.new("glowstar")
    m.use_nodes = True
    em = m.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.75, 1.0, 0.7, 1)
    em.inputs["Strength"].default_value = 0.35
    m.node_tree.links.new(em.outputs[0], m.node_tree.nodes["Material Output"].inputs["Surface"])
    for k in range(26):
        cx, cy = rng.uniform(x0 + 0.2, x1 - 0.2), rng.uniform(y0 + 0.3, y1 - 0.1)
        if math.hypot(cx, cy + 5 * P) < 0.3:          # (clear of the lamp)
            continue
        r = rng.uniform(0.025, 0.05)
        a0 = rng.uniform(0, math.tau)
        verts = [(cx + (r if i % 2 == 0 else r * 0.45) * math.cos(a0 + i * math.pi / 5),
                  cy + (r if i % 2 == 0 else r * 0.45) * math.sin(a0 + i * math.pi / 5), CEIL - 0.001) for i in range(10)]
        me = bpy.data.meshes.new(f"star{k}")
        me.from_pydata(verts, [], [tuple(range(10))])
        me.materials.append(m)
        ob = bpy.data.objects.new(f"star{k}", me)
        B.col.objects.link(ob)
    return room


def build_lights(sc):
    w = bpy.data.worlds.new("dawn")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.02, 0.03, 0.06, 1)
    bg.inputs["Strength"].default_value = 1.0
    x0 = ROOM[0]
    DAWN_SUN, DAWN_SKY = 3.0, 2
    wy0, wy1, wz0, wz1 = WIN
    wy = (wy0 + wy1) / 2
    # the sunrise, reflected up off something shiny outside below the window: far-away, parallel
    # light (a soft-edged disc, so the slats cast soft stripes) coming up onto the ceiling
    ld = bpy.data.lights.new("dawn", "SUN")
    ld.energy, ld.color, ld.angle = DAWN_SUN, (1.0, 0.66, 0.42), math.radians(SUN_SOFT)
    lo = bpy.data.objects.new("dawn", ld)
    sc.collection.objects.link(lo)
    el, az = SUN_ELEV, SUN_AZ               # elevation; azimuth (0: straight in through the window)
    to_sun = Vector((-math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), math.sin(el)))
    lo.rotation_mode = "QUATERNION"
    lo.rotation_quaternion = (-to_sun).to_track_quat("-Z", "Y")
    # the sky through the window: a glowing pane outside, and its cool light into the room
    m = bpy.data.materials.new("sky")
    m.use_nodes = True
    em = m.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.78, 0.62, 1)
    em.inputs["Strength"].default_value = 1.2
    m.node_tree.links.new(em.outputs[0], m.node_tree.nodes["Material Output"].inputs["Surface"])
    sky = picture(sc.collection, "sky", m, (x0 - 0.35, wy, (wz0 + wz1) / 2), (1.6, 1.0), "+x")
    sky.visible_shadow = False                                  # (the sun shines through it)
    kd = bpy.data.lights.new("skylight", "AREA")
    kd.shape, kd.size, kd.size_y = "RECTANGLE", wy1 - wy0, wz1 - wz0
    kd.energy, kd.color = DAWN_SKY, (0.62, 0.72, 1.0)
    ko = bpy.data.objects.new("skylight", kd)
    sc.collection.objects.link(ko)
    ko.location = (x0 + 0.12, wy, (wz0 + wz1) / 2)
    SL.aim(ko, (x0 + 1.0, wy, (wz0 + wz1) / 2 + 0.1))
    # a dim fill so the room isn't black
    fd = bpy.data.lights.new("fill", "AREA")
    fd.size, fd.energy, fd.color = 2.0, 1.5, (0.5, 0.55, 0.75)
    fo = bpy.data.objects.new("fill", fd)
    sc.collection.objects.link(fo)
    fo.location = (0.0, -0.9, 0.05)
    SL.aim(fo, (0.0, -0.9, CEIL))


def build_kevin(B, screen_mat):
    """His right arm holding the phone (the rest of him is out of view), turned to lie in bed."""
    before = set(bpy.data.objects)
    top = SL.FIG["z_adult"] + SL.FIG["torso_h"]
    sh, el, hand = SL.make_arm(B, -1, top, SLEEVE, SKIN, long_sleeve=True)
    SL.pose_arm(sh, el, -1, "phone")
    root = bpy.data.objects.new("kevin", None)
    B.col.objects.link(root)
    for ob in set(bpy.data.objects) - before:
        if ob.parent is None and ob is not root:
            ob.parent = root
    root.matrix_world = lying()
    bpy.context.view_layer.update()
    SL.held_slab(B, hand, "phone", PHONE, "#18191e")
    slab = bpy.data.objects["phone"]
    bpy.data.objects["phone_grip"].rotation_euler.z = GRIP_SPIN   # (held up out of his fist, toy style)
    scr = picture(B.col, "phone_screen", screen_mat, (0, 0, 0), SCREEN, "-y")
    scr.parent = slab
    scr.location = (0.0, -PHONE[1] / 2 - 0.0008, 0.0)
    # the screen's light on his hand and sleeve
    gd = bpy.data.lights.new("phoneglow", "AREA")
    gd.size, gd.energy, gd.color = 0.08, 0.6, (0.8, 0.82, 1.0)
    go = bpy.data.objects.new("phoneglow", gd)
    B.col.objects.link(go)
    go.parent = slab
    go.location = (0.0, -0.03, 0.0)
    go.rotation_euler = (math.pi / 2, 0.0, 0.0)          # facing out of the screen (-y)
    return {"root": root, "shoulder": sh, "elbow": el, "hand": hand, "phone": slab, "screen": scr}


def phone_target(cam_matrix, offset=(0.0, 0.0, 0.0), roll=0.0):
    """Where the phone's screen should be: PHONE_AT in camera space (x right, y up, -z ahead),
    facing the eye, upright in the picture (turned by PHONE_ROLL + roll)."""
    C = cam_matrix.to_3x3()
    right, up, back = C.col[0], C.col[1], C.col[2]
    rot = Matrix.Rotation(PHONE_ROLL + roll, 3, back)
    r, u = rot @ right, rot @ up
    tilt = Matrix.Rotation(PHONE_TILT, 3, r)               # (its top leans back a little)
    u, n = tilt @ u, tilt @ back
    pos = cam_matrix.translation + C @ (Vector(PHONE_AT) + Vector(offset))
    # the screen's own axes: +x right, +z up, -y out of the screen (toward the eye)
    M = Matrix((r, -n, u)).transposed().to_4x4()
    M.translation = pos
    return M


def hold_at(kev, target):
    """Move Kevin (his arm and the phone) so the phone's screen sits at `target`."""
    bpy.context.view_layer.update()
    S, K = kev["screen"].matrix_world.copy(), kev["root"].matrix_world.copy()
    kev["root"].matrix_world = target @ S.inverted() @ K


def build(sc, screen_image=None, screen_video=None):
    col = sc.collection
    B = SL.Builder("fig", col)
    build_room(B)
    build_lights(sc)
    if screen_video:          # the phone video (wake_phone.py), its first frame on frame 1
        from office_set import movie_material
        mat = movie_material("phone_img", screen_video, 0, 1.0)
    else:
        mat = image_material("phone_img", screen_image or os.path.join(BUILD, "phone_placeholder.png"), 1.0)
    kev = build_kevin(B, mat)
    cam = camera_rig(sc, kev)
    bpy.context.view_layer.update()
    hold_at(kev, phone_target(cam.matrix_world))
    return {"kevin": kev, "cam": cam}


def camera_rig(sc, kev):
    cd = bpy.data.cameras.new("cam")
    cd.lens = LENS
    cd.clip_start = 0.005
    cd.dof.use_dof = True
    cd.dof.focus_object = kev["screen"]
    cd.dof.aperture_fstop = 0.6
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (0.0, 0.0, EYE_Z)
    fwd = Vector((-math.sin(LOOK_SIDE), -math.sin(LOOK_TILT), math.cos(LOOK_SIDE) * math.cos(LOOK_TILT))).normalized()
    up = Vector((0.0, 1.0, 0.0))
    right = fwd.cross(up).normalized()
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = Matrix((right, right.cross(fwd), -fwd)).transposed().to_quaternion()
    return cam


# ---------------------------------------------------------------- the shot
T0, T1, FPS = 245.6, 259.2, 60         # (the end credits cut in when the music comes back up)
RISE = (247.2, 248.8)                  # the phone comes up into view (song time)...
LOWER = (1e9, 1e9 + 1)                 # ...(and could sink again; not before the cut)
FOCUS_PULL = (247.9, 249.3)            # groggy focus (on nothing) -> on the phone
FOCUS_LOSE = (1e9, 1e9 + 1)            # ...(and back to nothing)
RISE_FROM = Vector((0.09, -0.3, 0.06))  # where the phone comes up from (camera space, below the frame)
LOWER_TO = Vector((0.05, -0.2, 0.05))


def ss5(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def arm_pose(t):
    """The phone's offset from PHONE_AT (camera space) and its extra roll at song time t: up from
    below the frame, a slow hand-held wobble (a few mm, about a degree: it stays readable), down."""
    up = ss5((t - RISE[0]) / (RISE[1] - RISE[0]))
    down = ss5((t - LOWER[0]) / (LOWER[1] - LOWER[0]))
    held = ss5((t - RISE[0]) / 2.5)            # (the wobble settles in as he takes hold)
    wob = Vector((0.004 * math.sin(0.53 * t) + 0.0018 * math.sin(1.31 * t + 1.0),
                  0.0035 * math.sin(0.43 * t + 2.0) + 0.0015 * math.sin(1.19 * t + 0.3),
                  0.004 * math.sin(0.37 * t + 0.7))) * held
    roll = held * math.radians(1.1 * math.sin(0.47 * t + 0.5) + 0.45 * math.sin(1.07 * t))
    off = RISE_FROM * (1 - up) + LOWER_TO * down + wob
    roll += math.radians(-14) * (1 - up) + math.radians(-8) * down
    return off, roll


def focus_at(t, phone_dist):
    """(focus distance, f-stop): groggy (focused on nothing, very shallow) .. on the phone."""
    u = ss5((t - FOCUS_PULL[0]) / (FOCUS_PULL[1] - FOCUS_PULL[0])) * (1 - ss5((t - FOCUS_LOSE[0]) / (FOCUS_LOSE[1] - FOCUS_LOSE[0])))
    return FUZZY_FOCUS + (phone_dist - FUZZY_FOCUS) * u, FSTOP_GROGGY + (FSTOP_AWAKE - FSTOP_GROGGY) * u


def animate(S, sc):
    """Key the arm (and phone) and the focus for the whole shot."""
    kev, cam = S["kevin"], S["cam"]
    cd = cam.data
    cd.dof.focus_object = None
    n = int(round((T1 - T0) * FPS))
    root = kev["root"]
    root.rotation_mode = "QUATERNION"
    bpy.context.view_layer.update()
    M = cam.matrix_world.copy()
    for f in range(1, n + 1):
        t = T0 + (f - 1) / FPS
        off, roll = arm_pose(t)
        hold_at(kev, phone_target(M, off, roll))
        root.keyframe_insert("location", frame=f)
        SL.key_rotation(root, f)
        dist = (Vector(PHONE_AT) + off).length
        cd.dof.focus_distance, cd.dof.aperture_fstop = focus_at(t, dist)
        cd.dof.keyframe_insert("focus_distance", frame=f)
        cd.dof.keyframe_insert("aperture_fstop", frame=f)
    sc.frame_start, sc.frame_end, sc.render.fps = 1, n, FPS
    return n


def split_screen_pass(sc, layer):
    """Set the scene up for one of the two passes of the phone screen: main (the screen dark, its
    glow light still on his hand) or screen (only the screen, in plain sRGB so its pixels are the
    video's own, everything else a holdout); the two are added together in assembly."""
    scr = bpy.data.objects["phone_screen"]
    em = next(n for n in scr.data.materials[0].node_tree.nodes if n.type == "EMISSION")
    if layer == "main":
        em.inputs["Strength"].default_value = 0.0
        return
    em.inputs["Strength"].default_value = 1.0
    for ob in bpy.data.objects:
        if ob.type in ("MESH", "CURVE", "FONT") and ob is not scr:
            ob.is_holdout = True
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
    sc.eevee.bokeh_max_size = 400.0
    sc.render.use_motion_blur = not preview
    sc.render.motion_blur_shutter = 1.0
    sc.render.motion_blur_position = "START"      # (the phone's video sampled from its own frame only)
    sc.eevee.motion_blur_steps = 4
    if not preview:
        rt = sc.eevee.ray_tracing_options
        rt.resolution_scale, rt.use_denoise = "1", True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.8
    sc.render.image_settings.file_format = "PNG"


# check stills: (name, phone in view, focus on it (else fuzzy, on the ceiling))
STILLS = [("ceiling", False, False), ("phone_fuzzy", True, False), ("phone", True, True)]


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "build", "wake_stills"))
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--fly", action="store_true", help="render the whole shot")
    ap.add_argument("--screen", help="the phone's video (wake_phone.py; its first frame at song 245.6)")
    ap.add_argument("--pass", dest="layer", choices=("main", "screen"),
                    help="render one of the two passes (the default for a final; a preview without it draws the "
                         "screen straight in)")
    ap.add_argument("--patch", help="START,END song seconds: re-render only these frames of a final pass")
    A = ap.parse_args(argv)
    res = A.res or (540 if A.preview else 1080)
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    S = build(sc, screen_video=A.screen)
    setup_render(sc, res, A.preview)
    if A.fly:
        animate(S, sc)
        split = A.screen and (A.layer or not A.preview)
        A.layer = A.layer or "main"
        if split:
            split_screen_pass(sc, A.layer)
        im = sc.render.image_settings
        im.file_format = "FFMPEG"
        final = "" if A.preview else "_final"
        if final or A.layer == "screen":
            sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
            im.color_mode = "RGB"
        else:
            sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        sc.render.ffmpeg.audio_codec = "NONE"
        os.makedirs(A.out, exist_ok=True)
        name = ("wake_screen" if A.layer == "screen" else "wake") + final
        target = os.path.join(A.out, name + (".mkv" if sc.render.ffmpeg.format == "MKV" else ".mp4"))
        import render_out
        render_out.render_movie(sc, target, FPS, A.patch, T0)
        return
    os.makedirs(A.out, exist_ok=True)
    cd = S["cam"].data
    for name, phone, on_phone in STILLS:
        if A.only and name not in A.only.split(","):
            continue
        for ob in S["kevin"]["root"].children_recursive:
            ob.hide_render = not phone
        cd.dof.focus_object = S["kevin"]["screen"] if on_phone else None
        cd.dof.focus_distance = FUZZY_FOCUS
        cd.dof.aperture_fstop = FSTOP_AWAKE if on_phone else FSTOP_GROGGY
        sc.render.filepath = os.path.join(A.out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__":
    main()
