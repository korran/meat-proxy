"""Lip-sync demo: the Manager singing, mouth shapes driven by tools/lipsync.py.

  python3 tools/lipsync.py video/build/lyrics.json assets/audio/stems/we_need_a_meat_proxy_vocals.wav \
      --start 9.6 --end 18.8 > video/build/visemes.json
  blender -b --factory-startup --python video/lipsync_demo.py -- \
      --visemes video/build/visemes.json --out video/build/lipsync_frames

Mouths are printed decals on the face (one set per viseme), swapped frame by frame like
replacement faces on toy figures. The head also blinks and nods a little with the singing.
The pieces are importable (video/dance_demo.py reuses them).
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402  (cast builders)

DARK, TEETH, TONGUE, LIP = "#3b1d1d", "#fafafa", "#d9657a", "#e3a98a"


def build_mouths(B, c, cyl):
    """One printed mouth per viseme, all at the same spot on the face."""
    mc = c - 0.026

    def ell(name, z, sx, sz, col, off):
        return B.decal(name, "ellipse", 0.0, z, sx, sz, col, cyl, off)

    def line(name, pts, r):
        return B.tube(name, [SL.on_cyl(x, z) for x, z in pts], r, "eye")

    return {
        "rest": [line("m_rest", ((-0.034, c - 0.018), (-0.012, c - 0.034), (0.012, c - 0.034), (0.034, c - 0.018)),
                      0.0038)],
        "MBP": [line("m_mbp", ((-0.03, mc), (0.0, mc - 0.002), (0.03, mc)), 0.0044)],
        "FV": [ell("m_fv", mc + 0.001, 0.028, 0.0065, DARK, 0.001),
               ell("m_fv_teeth", mc + 0.0035, 0.02, 0.0032, TEETH, 0.0016)],
        "EE": [ell("m_ee", mc, 0.034, 0.009, DARK, 0.001),
               ell("m_ee_teeth", mc + 0.0045, 0.026, 0.0035, TEETH, 0.0016)],
        "EH": [ell("m_eh", mc - 0.002, 0.03, 0.014, DARK, 0.001),
               ell("m_eh_teeth", mc + 0.0085, 0.018, 0.0035, TEETH, 0.0016),
               ell("m_eh_tongue", mc - 0.01, 0.016, 0.0045, TONGUE, 0.0016)],
        "AH": [ell("m_ah", mc - 0.005, 0.031, 0.021, DARK, 0.001),
               ell("m_ah_teeth", mc + 0.012, 0.016, 0.004, TEETH, 0.0016),
               ell("m_ah_tongue", mc - 0.019, 0.018, 0.0065, TONGUE, 0.0016)],
        "OH": [ell("m_oh", mc - 0.003, 0.019, 0.019, DARK, 0.001),
               ell("m_oh_tongue", mc - 0.014, 0.009, 0.004, TONGUE, 0.0016)],
        "OO": [ell("m_oo_lips", mc - 0.002, 0.016, 0.016, LIP, 0.0008),
               ell("m_oo", mc - 0.002, 0.0095, 0.0105, DARK, 0.0014)],
    }


def key_visible(objs, frame, visible):
    for ob in objs:
        ob.hide_render = not visible
        ob.hide_viewport = not visible
        ob.keyframe_insert("hide_render", frame=frame)
        ob.keyframe_insert("hide_viewport", frame=frame)


def singing_manager(B, sc):
    """Build the Manager with swappable mouths. Returns (top, head pivot, mouths, eyes, blink)."""
    SL.build_manager(B, mouth=False)
    top = SL.FIG["z_adult"] + SL.FIG["torso_h"]
    c = top + 0.12
    cyl = ((0, 0, c), (0.1, 0.1, 100.0))
    mouths = build_mouths(B, c, cyl)
    blink = [B.decal(f"blink{s}", "bar", 0.036 * s, c + 0.007, 0.016, 0.0035, "eye", cyl, 0.0012) for s in (-1, 1)]
    # everything above the shoulders hangs off a head pivot, so the head can nod and sway
    bpy.context.view_layer.update()
    head = bpy.data.objects.new("head_pivot", None)
    sc.collection.objects.link(head)
    head.location = (0, 0, top)
    inv = Matrix.Translation((0, 0, top)).inverted()
    for ob in list(sc.collection.objects):
        if ob is head or ob.parent is not None or ob.type not in ("MESH", "CURVE", "FONT"):
            continue
        centre = sum((ob.matrix_world @ Vector(v) for v in ob.bound_box), Vector()) / 8
        if centre.z > top + 0.004:
            ob.parent = head
            ob.matrix_parent_inverse = inv
    eyes = [ob for ob in head.children if ob.name.startswith(("eye", "glint"))]
    return top, head, mouths, eyes, blink


def animate_mouths(mouths, frames):
    """Keyframe mouth visibility only where the shape changes."""
    prev = None
    for i, fr in enumerate(frames):
        if fr["v"] != prev:
            for name, objs in mouths.items():
                key_visible(objs, i + 1, name == fr["v"])
            prev = fr["v"]


def animate_blinks(eyes, blink, n, fps):
    """Blinks every ~3 s, 6 frames long."""
    key_visible(blink, 1, False)
    key_visible(eyes, 1, True)
    t = 1.2
    while t < n / fps - 0.3:
        f0 = int(t * fps) + 1
        key_visible(eyes, f0, False)
        key_visible(blink, f0, True)
        key_visible(eyes, f0 + 6, True)
        key_visible(blink, f0 + 6, False)
        t += 2.6 + 0.9 * math.sin(t * 7.3) ** 2


def animate_head(head, frames, fps, extra=None):
    """A small nod with the singing level and a slow sway; `extra(t)` adds (rx, ry, rz) on top."""
    level = 0.0
    for i, fr in enumerate(frames):
        level += (fr["level"] - level) * 0.25
        if i % 2:
            continue
        tt = i / fps
        r = [0.07 * level, 0.025 * math.sin(2 * math.pi * tt / 5.3), 0.04 * math.sin(2 * math.pi * tt / 3.7)]
        if extra:
            r = [a + b for a, b in zip(r, extra(fr["t"]))]
        head.rotation_euler = r
        head.keyframe_insert("rotation_euler", frame=i + 1)


def setup_look(sc, fps, n, res=1080, samples=16, blur_steps=4, shutter=1.0, preview=False):
    """Same materials, lights and grading as the cast lineup. preview: as fast as possible (no
    motion blur, one sample, cheaper shadows, no ray tracing)."""
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = res
    sc.render.resolution_x = res * 16 // 9
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, n
    sc.eevee.taa_render_samples = samples
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = shutter
    sc.eevee.motion_blur_steps = blur_steps
    sc.eevee.motion_blur_max = int(160 * res / 1080)
    if preview:
        sc.render.use_motion_blur = False
        sc.eevee.taa_render_samples = 1
        sc.eevee.use_raytracing = False
        sc.eevee.use_fast_gi = False
        sc.eevee.shadow_resolution_scale = 0.5
        sc.eevee.shadow_ray_count = 1
        sc.eevee.shadow_step_count = 1
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*SL.srgb(SL.PAL["floor"]), 1)
    bg.inputs[1].default_value = 0.35
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.65
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.04))
    bpy.context.object.data.materials.append(SL.material("fig", "floor", "floor", "matte"))
    for name, loc, energy, size, color, target in (
        ("key", (-2.5, -3.2, 3.2), 900, 3.0, (1.0, 0.95, 0.9), (0, 0, 0.5)),
        ("fill", (3.0, -2.8, 1.4), 320, 4.0, (0.75, 0.85, 1.0), (0, 0, 0.5)),
        ("rim", (0.0, 2.2, 2.4), 420, 4.0, (1.0, 0.8, 0.6), (0, 0, 0.6)),
    ):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = loc
        SL.aim(lo, target)
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"


def add_camera(sc, loc, target, lens):
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = lens
    cam = bpy.data.objects.new("cam", cam_d)
    cam.location = loc
    SL.aim(cam, target)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def render(sc, out, frames, fps, start, stills=None, preview=False):
    """Render frames as PNGs into the folder `out` (or stills). In preview mode the animation is
    written straight to a silent H.264 video, `out` + ".mp4", instead (saving PNGs is slower
    than rendering them)."""
    out = out.rstrip("/")
    if stills:
        for t in [float(v) for v in stills.split(",")]:
            f = int(round((t - start) * fps)) + 1
            sc.frame_set(f)
            sc.render.filepath = f"{out}/still_{t:07.3f}_{frames[f - 1]['v']}.png"
            bpy.ops.render.render(write_still=True)
            print("STILL", t, frames[f - 1]["v"], frames[f - 1]["word"])
    elif preview:
        im = sc.render.image_settings
        im.file_format = "FFMPEG"
        sc.render.ffmpeg.format = "MPEG4"
        sc.render.ffmpeg.codec = "H264"
        sc.render.ffmpeg.constant_rate_factor = "HIGH"
        sc.render.ffmpeg.ffmpeg_preset = "REALTIME"
        sc.render.ffmpeg.audio_codec = "NONE"
        sc.render.filepath = out + ".mp4"
        sc.render.use_file_extension = False
        bpy.ops.render.render(animation=True)
        print("RENDER done", len(frames), "frames ->", sc.render.filepath)
    else:
        sc.render.filepath = f"{out}/f_####"
        bpy.ops.render.render(animation=True)
        print("RENDER done", len(frames), "frames")


def parse_args(extra=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--visemes", required=True)
    ap.add_argument("--out", required=True, help="folder for rendered frames")
    ap.add_argument("--res", type=int, help="frame height in pixels (default 1080, preview 540)")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--blur-steps", type=int, default=4)
    ap.add_argument("--shutter", type=float, default=1.0)
    ap.add_argument("--stills", help="render only these frame times (seconds, comma separated)")
    ap.add_argument("--preview", action="store_true",
                    help="fast check render: no motion blur, 1 sample, written straight to OUT.mp4")
    if extra:
        extra(ap)
    a = ap.parse_args(argv)
    if a.res is None:
        a.res = 540 if a.preview else 1080
    return a


def main():
    A = parse_args()
    D = json.load(open(A.visemes))
    fps, start, frames = D["fps"], D["start"], D["frames"]
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    B = SL.Builder("fig", sc.collection)
    top, head, mouths, eyes, blink = singing_manager(B, sc)
    SL.fig_baseplate(B, nx=10, ny=7)
    animate_mouths(mouths, frames)
    animate_blinks(eyes, blink, len(frames), fps)
    animate_head(head, frames, fps)
    setup_look(sc, fps, len(frames), A.res, A.samples, A.blur_steps, A.shutter, A.preview)
    add_camera(sc, (0.38, -1.55, 0.8), (0, 0, 0.6), 70)
    render(sc, A.out, frames, fps, start, A.stills, A.preview)


if __name__ == "__main__":
    main()
