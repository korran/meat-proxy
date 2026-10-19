#!/usr/bin/env python3
"""Splice the whole music video from the rendered sections, over the song.

  python3 video/assemble.py [--out video/build/full_song.mp4] [--res 1080] [--list]

Each section in SECTIONS is a rendered video, the song time its first frame shows, and the stretch
of the song it covers. A section can have a transparent overlay video laid on top (the news
broadcast graphics) and can dissolve in from the section before it (the drone's push into the
iPad, which lands on a picture of the cyberspace shot). Stretches with nothing rendered yet are
black. Everything is scaled to the output size at 60 fps; frames are renumbered so ffmpeg never
repeats or drops one. The song plays underneath.

The newest render of each section is listed first; the first that exists is used (so a final
render takes over from a preview as soon as it's there).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
B = os.path.join(HERE, "build")
SONG = os.path.join(ROOT, "assets", "audio", "we_need_a_meat_proxy.wav")
FPS = 60

# (name, [candidate files, best first], song time of the file's first frame, section start, end,
#  overlay file or None, dissolve in from the previous section, seconds)
SECTIONS = [
    ("intro, verse 1, chorus 1 (office)", ["office_v1c1_final.mkv", "office_v1c1_final.mp4"], 0.0, 0.0, 66.4, None, 0),
    ("verse 2, chorus 2 (yacht)", ["yacht_v2c2_final.mkv", "yacht_v2c2_preview.mp4"], 66.4, 66.4, 129.4, None, 0),
    ("bridge (SINN)", ["news_bridge_final.mkv", "news_bridge_preview.mp4"], 129.4, 129.4, 148.6,
     ["news_overlay_bridge_final.mkv", "news_overlay_bridge.mkv"], 0),
    # the drone shot's iPad screen is its own pass (in plain sRGB, so its pixels are the cyberspace
    # video's own), added on top: the push-in lands on exactly the frame the cut goes to
    ("instrumental (drone)", ["drone_final.mkv", "suburb_stills/drone.mp4"], 148.6, 148.6, 166.2,
     ["drone_screen_final.mkv", "suburb_stills/drone_screen.mkv"], 0),
    ("verse 3, chorus 3 (cyberspace)", ["cyber_v3c3_final.mkv", "cyber_v3c3_preview.mp4"], 162.6, 166.2, 245.6,
     None, 0),
    ("outro", [], 245.6, 245.6, None, None, 0),
]


ADD = {"instrumental (drone)": True}       # sections whose second file is added, not laid over


def pick(cands):
    for c in cands or []:
        p = os.path.join(B, c)
        if os.path.exists(p):
            return p
    return None


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(B, "full_song.mp4"))
    ap.add_argument("--res", type=int, default=1080)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--list", action="store_true", help="just show what would be used")
    A = ap.parse_args()
    W, H = A.res * 16 // 9, A.res
    song_len = duration(SONG)

    inputs, chains, plan = [], [], []
    for k, (name, cands, f0, s0, s1, over, fade) in enumerate(SECTIONS):
        s1 = song_len if s1 is None else s1
        src = pick(cands)
        ov = pick(over) if over else None
        # with a dissolve, this section starts `fade` early, overlapping the one before
        a = s0 - fade
        plan.append((name, src, ov, s0, s1, fade))
        lab = f"s{k}"
        if src:
            if a < f0 - 1e-6:
                sys.exit(f"{name}: needs footage from {a:.2f} s, but {src} starts at {f0:.2f} s")
            inputs.append(src)
            i = len(inputs) - 1
            f = (f"[{i}:v]trim=start={a - f0:.4f}:end={s1 - f0:.4f},setpts=N/({FPS}*TB),"
                 f"scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS}")
            if ov and ADD.get(name):         # an additive pass
                inputs.append(ov)
                j = len(inputs) - 1
                chains.append(f"{f},format=gbrp[{lab}b]")
                chains.append(f"[{j}:v]trim=start={a - f0:.4f}:end={s1 - f0:.4f},setpts=N/({FPS}*TB),"
                              f"scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS},format=gbrp[{lab}o]")
                chains.append(f"[{lab}b][{lab}o]blend=all_mode=addition,format=yuv420p,settb=1/{FPS}[{lab}]")
            elif ov:
                inputs.append(ov)
                j = len(inputs) - 1
                chains.append(f"{f}[{lab}b]")
                chains.append(f"[{j}:v]trim=start={a - f0:.4f}:end={s1 - f0:.4f},setpts=N/({FPS}*TB),"
                              f"scale={W}:{H}:flags=lanczos,format=rgba[{lab}o]")
                chains.append(f"[{lab}b][{lab}o]overlay=eof_action=pass,format=yuv420p,settb=1/{FPS}[{lab}]")
            else:
                chains.append(f"{f},format=yuv420p,settb=1/{FPS}[{lab}]")
        else:   # nothing rendered yet: black
            chains.append(f"color=c=black:s={W}x{H}:r={FPS}:d={s1 - a:.4f},format=yuv420p,setsar=1,settb=1/{FPS}[{lab}]")

    for name, src, ov, s0, s1, fade in plan:
        print(f"{s0:7.2f}-{s1:7.2f}  {name:34s} {os.path.relpath(src, B) if src else '(black)'}"
              + (f" + {os.path.relpath(ov, B)}" if ov else "") + (f"  (dissolves in over {fade} s)" if fade else ""))
    if A.list:
        return

    # join: a plain concat, or a dissolve (xfade) where a section asks for one
    cur, cur_len = "s0", plan[0][4] - plan[0][3]
    for k in range(1, len(plan)):
        nxt = f"s{k}"
        name, src, ov, s0, s1, fade = plan[k]
        out = f"j{k}"
        if fade:
            chains.append(f"[{cur}][{nxt}]xfade=transition=fade:duration={fade}:offset={cur_len - fade:.4f}[{out}]")
            cur_len += (s1 - s0)
        else:
            chains.append(f"[{cur}][{nxt}]concat=n=2:v=1:a=0,settb=1/{FPS}[{out}]")
            cur_len += (s1 - s0)
        cur = out
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-i", SONG, "-filter_complex", ";".join(chains), "-map", f"[{cur}]", "-map", f"{len(inputs)}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(A.crf), "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", A.out]
    subprocess.run(cmd, check=True)
    print("->", A.out, f"({duration(A.out):.2f} s; the song is {song_len:.2f} s)")


if __name__ == "__main__":
    main()
