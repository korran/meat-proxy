"""The end credits (song 259.2 .. 269.56, when the music comes back up after v9's monologue): on
the Founder's yacht, the LED wall up, the Manager and the Founder (the Manager ten years later)
dancing either side of it while v9 dances on it, the credits paging in beside her
(credits_screen.py).

  blender -b --factory-startup --python video/credits_set.py -- --screen video/build/credits_screen.mkv \\
      --out video/build [--preview] [--res 1080] [--stills 260,265]

The dancing comes from dance_demo.py's engine (the parts credits_manager and credits_founder),
dumped as motion curves (DANCE_DUMP=video/build/credits_dance_<who>.json) and keyed here onto
both figures, since dance_demo itself performs one figure at a time.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dance_demo as DD  # noqa: E402
import lipsync_demo as LS  # noqa: E402
import style_lab as SL  # noqa: E402
import yacht_set as YS  # noqa: E402
from bricks import P  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
T0, T1, FPS = 259.2, 269.56, 60
TAU = 2 * math.pi
WALL_Y = YS.SY * P                       # the LED wall's front face
DANCERS = (("manager", -1.2), ("founder", 1.2))   # who, and x: at either edge of the wall, just in front
DANCE_Y = WALL_Y - 0.55
CAM = ((0.0, WALL_Y - 6.33, 0.75), (0.0, WALL_Y, YS.LED_Z0 + YS.LED_H / 2), 66)   # aimed at the wall's centre   # as the stage shot: off the stern, long lens; the wall and both of them
PUSH = 0.6                               # a slow push in over the shot...
CIRCLE = (0.5, 1.0, 0.25)                # ...going round a circle about its line to the wall (radius m, turns,
                                         # starting angle in turns: 0.25 = the top; once round, back to it) at a
                                         # steady pace, easing to a stop over the last STOP seconds; always aimed
                                         # at the wall's centre (so it stays centred)
STOP = 2.5


def performer(sc, who, spot, curves, frames):
    """Build `who` (as dance_demo does: a root at the feet, a chest pivot at the hips) at `spot`
    and key the dumped dance onto it."""
    THIGH, SHIN, hip_z = DD.LEG_DIMS["adult"]
    before = set(bpy.data.objects)
    Bld = SL.Builder("fig", sc.collection)
    top, head, mouths, eyes, blink = LS.singing_figure(Bld, sc, who)
    new = set(bpy.data.objects) - before
    legs = Bld.legs[-2:]

    def empty(prefix):
        return next(o for o in new if o.type == "EMPTY" and o.name.split(".")[0] == prefix)
    shoulders = {s: empty(f"shoulder{s}") for s in (DD.R, DD.Lf)}
    elbows = {s: empty(f"elbow{s}") for s in (DD.R, DD.Lf)}
    for sh in shoulders.values():
        sh.rotation_mode = DD.SHOULDER_ORDER
    place = bpy.data.objects.new(f"{who}_place", None)
    sc.collection.objects.link(place)
    root = bpy.data.objects.new(f"{who}_root", None)
    sc.collection.objects.link(root)
    for ob in new:
        if ob.parent is None and ob.type in ("MESH", "CURVE", "FONT", "EMPTY"):
            ob.parent = root
    bpy.context.view_layer.update()
    chest = bpy.data.objects.new(f"{who}_chest", None)
    sc.collection.objects.link(chest)
    chest.parent = root
    chest.location = (0, 0, hip_z)
    inv = Matrix.Translation((0, 0, hip_z)).inverted()
    for ob in list(root.children):
        if ob is chest:
            continue
        zc = ob.matrix_world.translation.z if ob.type == "EMPTY" else \
            (sum((ob.matrix_world @ Vector(v) for v in ob.bound_box), Vector()) / 8).z
        if zc > hip_z - 0.015 and not ob.name.startswith(("hip", "knee")):
            ob.parent = chest
            ob.matrix_parent_inverse = inv
    root.parent = place
    place.location = spot
    S, n = curves, len(curves["t"])
    for i in range(n):
        f = i + 1
        for leg, (hip, knee) in enumerate(legs):
            kn, hf = S[f"knee{leg}"][i], S[f"hipf{leg}"][i]
            hip.rotation_euler.x, knee.rotation_euler.x = -(kn / 2 + hf), kn + 2 * hf
            hip.keyframe_insert("rotation_euler", frame=f)
            knee.keyframe_insert("rotation_euler", frame=f)
        root.location = (S["rx"][i], 0.0, S["root_z"][i])
        root.rotation_euler = (0.0, S["roll"][i], S["yaw"][i] + S["spin"][i])
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        chest.rotation_euler = (-S["lean"][i], S["croll"][i], S["cyaw"][i])
        chest.keyframe_insert("rotation_euler", frame=f)
        for s in shoulders:
            shoulders[s].rotation_euler = (S[f"sx{s}"][i], -(SL.ARM_SLOPE + S[f"sab{s}"][i]) * s, S[f"sz{s}"][i] * s)
            shoulders[s].keyframe_insert("rotation_euler", frame=f)
            elbows[s].rotation_euler.x = min(0.05, S[f"el{s}"][i])
            elbows[s].keyframe_insert("rotation_euler", frame=f)
        head.rotation_euler = (S["hx"][i], S["hy"][i], S["hz"][i])
        head.keyframe_insert("rotation_euler", frame=f)
    LS.animate_mouths(mouths, frames)       # (mouths shut: nobody's singing)
    if blink:
        LS.animate_blinks(eyes, blink, n, FPS)
    return place


def progress(t, dur):
    """0 .. 1 along the camera move: a steady pace, then over the last STOP seconds slowing as
    1 - smootherstep, to exactly nothing at the end."""
    hold = dur - STOP
    total = hold + STOP * 0.5                 # (the slow-down covers half the ground a steady pace would)
    if t <= hold:
        return t / total
    u = min(1.0, (t - hold) / STOP)
    return (hold + STOP * (u - (u ** 6 - 3 * u ** 5 + 2.5 * u ** 4))) / total


def build(sc, screen_video):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    # the dancers first: building a figure hangs every loose object above its neck off its head
    # pivot (so it would pick up the yacht)
    frames = json.load(open(os.path.join(BUILD, "visemes_credits.json")))["frames"]
    for who, x in DANCERS:
        curves = json.load(open(os.path.join(BUILD, f"credits_dance_{who}.json")))
        performer(sc, who, (x, DANCE_Y, 0.0), curves, frames)
    S = YS.build(sc, founder=False, screen_video=screen_video, screen_offset=0)
    YS.set_led(S, 1.0)                       # the wall's up
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    (cx, cy, cz), tgt, lens = CAM
    n = len(frames)
    for i in range(n):
        t = T0 + i / FPS
        r, turns, a0 = CIRCLE
        p = progress(t - T0, T1 - T0)
        push = PUSH * p
        ang = TAU * (a0 + turns * p)
        cam.location = (cx + r * math.cos(ang), cy + push, cz + r * math.sin(ang))
        SL.aim(cam, tgt)
        cd.lens = lens
        cam.keyframe_insert("location", frame=i + 1)
        SL.key_rotation(cam, i + 1)
    return n


def split_screen_pass(sc, layer):
    """Set the scene up for one of the two passes of the LED wall (see --pass)."""
    led = bpy.data.objects["led"]
    em = next(n for n in led.data.materials[0].node_tree.nodes if n.type == "EMISSION")
    if layer == "main":
        em.inputs["Strength"].default_value = 0.0
        return
    em.inputs["Strength"].default_value = 1.0
    for ob in bpy.data.objects:
        if ob.type in ("MESH", "CURVE", "FONT") and ob is not led:
            ob.is_holdout = True
    if sc.world:
        sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", required=True, help="the LED wall's video (credits_screen.py), its first frame at 259.2")
    ap.add_argument("--out", default=BUILD)
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", help="song times (comma separated): just these frames as PNGs")
    ap.add_argument("--patch", help="START,END song seconds: re-render only these frames of the final")
    ap.add_argument("--pass", dest="layer", choices=("main", "screen"),
                    help="main: the LED wall dark; screen: only the wall, in plain sRGB (its pixels are the credits "
                         "video's own), everything else a holdout; added together in assembly. (The default for a "
                         "final is main; a preview without it draws the wall straight in.)")
    A = ap.parse_args(argv)
    res = A.res or (540 if A.preview else 1080)
    sc = bpy.context.scene
    n = build(sc, A.screen)
    LS.setup_look(sc, FPS, n, res, 32, 4, 1.0, A.preview, on_set=(0.0, DANCE_Y, 0.0))
    sc.render.motion_blur_position = "START"
    sc.eevee.use_raytracing = sc.eevee.use_fast_gi = not A.preview
    os.makedirs(A.out, exist_ok=True)
    split = A.layer or not A.preview
    A.layer = A.layer or "main"
    if split:
        split_screen_pass(sc, A.layer)
    if A.stills:
        for t in (float(v) for v in A.stills.split(",")):
            sc.frame_set(int(round((t - T0) * FPS)) + 1)
            sc.render.filepath = os.path.join(A.out, f"credits_{t:.1f}.png")
            bpy.ops.render.render(write_still=True)
            print("STILL", sc.render.filepath)
        return
    im = sc.render.image_settings
    im.file_format = "FFMPEG"
    sc.render.ffmpeg.audio_codec = "NONE"
    name = ("credits_screen" if A.layer == "screen" else "credits") + ("" if A.preview else "_final")
    if A.preview and A.layer != "screen":
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        target = os.path.join(A.out, name + ".mp4")
    else:       # lossless (the screen pass always: its pixels must stay the video's)
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MKV", "FFV1"
        im.color_mode = "RGB"
        target = os.path.join(A.out, name + ".mkv")
    import render_out
    render_out.render_movie(sc, target, FPS, A.patch, T0)


if __name__ == "__main__":
    main()
