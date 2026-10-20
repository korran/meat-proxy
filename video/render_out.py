"""Writing animation renders to video files, shared by every render script.

  render_movie(sc, target, fps, patch=None, t0=0.0)

- A full render goes to a temporary name next to the target and is renamed over it only when
  complete, so a render that's stopped (or crashes) never destroys the existing video.
- patch="START,END" (song seconds; t0 is the song time of frame 1) renders only those frames
  and splices them into the existing lossless (.mkv, FFV1) target, keeping its pixel format
  (including an alpha channel); the target is replaced only once the result has the same
  number of frames.

The scene's frame range (1 .. n) and its output format must be set up before calling.
"""
import os
import subprocess

import bpy


def count_frames(path):
    """(frame count, pixel format) of a video's first stream."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets,pix_fmt", "-of", "csv=p=0", path], capture_output=True, text=True)
    pix, n = r.stdout.strip().split(",")
    return int(n), pix


def splice(original, patch, first, fps):
    """Replace frames first .. first + len(patch) - 1 (1-based) of the lossless video `original`
    with the frames of `patch`, losslessly."""
    n, pix = count_frames(original)
    m, _ = count_frames(patch)
    a, b = first - 1, first - 1 + m                      # frames [a, b) are replaced
    if a < 0 or b > n:
        raise ValueError(f"patch frames {first}..{first + m - 1} don't fit in {original} ({n} frames)")
    parts, fc = [], ["[0:v]split=2[o1][o2]"]
    if a > 0:
        fc.append(f"[o1]trim=end_frame={a},setpts=PTS-STARTPTS[pa]")
        parts.append("[pa]")
    else:
        fc.append("[o1]nullsink")
    fc.append("[1:v]setpts=PTS-STARTPTS[pp]")
    parts.append("[pp]")
    if b < n:
        fc.append(f"[o2]trim=start_frame={b},setpts=PTS-STARTPTS[pc]")
        parts.append("[pc]")
    else:
        fc.append("[o2]nullsink")
    fc.append("".join(parts) + f"concat=n={len(parts)}:v=1:a=0,setpts=N/({fps}*TB)[v]")
    tmp = original + ".splicing.mkv"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", original, "-i", patch,
                    "-filter_complex", ";".join(fc), "-map", "[v]", "-c:v", "ffv1", "-pix_fmt", pix, "-r", str(fps),
                    tmp], check=True)
    got = count_frames(tmp)[0]
    if got != n:
        os.remove(tmp)
        raise RuntimeError(f"spliced video has {got} frames, expected {n}; original kept")
    os.replace(tmp, original)
    print(f"SPLICED frames {first}..{first + m - 1} into {original}")


def frame_range(patch, t0, fps, n):
    """'START,END' song seconds -> (first, last) frame (1-based, clamped to 1 .. n)."""
    a, b = (float(v) for v in patch.split(","))
    return max(1, int(round((a - t0) * fps)) + 1), min(n, int(round((b - t0) * fps)) + 1)


def render_movie(sc, target, fps, patch=None, t0=0.0):
    sc.render.use_file_extension = False
    root, ext = os.path.splitext(target)
    if patch:
        if ext != ".mkv" or not os.path.exists(target):
            raise SystemExit(f"--patch splices into an existing lossless .mkv; {target} isn't one")
        n = sc.frame_end
        f0, f1 = frame_range(patch, t0, fps, n)
        sc.frame_start, sc.frame_end = f0, f1
        sc.render.filepath = root + ".patch.mkv"
        bpy.ops.render.render(animation=True)
        splice(target, sc.render.filepath, f0, fps)
        os.remove(sc.render.filepath)
        sc.frame_start, sc.frame_end = 1, n
        return target
    sc.render.filepath = root + ".partial" + ext
    bpy.ops.render.render(animation=True)
    os.replace(sc.render.filepath, target)
    print("RENDER done ->", target)
    return target
