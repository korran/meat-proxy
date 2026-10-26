#!/usr/bin/env python3
"""Splice the whole music video from the rendered sections, over the song.

  python3 video/assemble.py [--out video/build/full_song.mov] [--res 1080] [--list]

The output: H.264 (CRF 12); in a .mov the song's own 16-bit PCM (lossless, and YouTube takes it), in an
.mp4 (quick checks) AAC.

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
SONG = os.path.join(ROOT, "assets", "audio", "we_need_a_meat_proxy_mix.wav")   # (REAPER's render of the project)
FPS = 60

# (name, [candidate files, best first], song time of the file's first frame, section start, end,
#  layers on top: [("add" | "over", [candidate files])], dissolve in from the previous section, seconds)
# "add": a screen pass (in plain sRGB, so its pixels are its video's own) added on top; "over": a
# transparent overlay laid over it.
SECTIONS = [
    # the office TV's screen pass added (so the graphics are the video's own pixels)
    ("intro, verse 1, chorus 1 (office)", ["office_v1c1_final.mkv", "office_v1c1_final.mp4"], 0.0, 0.0, 66.4,
     [("add", ["office_v1c1_screen_final.mkv"])], 0),
    ("verse 2, chorus 2 (yacht)", ["yacht_v2c2_final.mkv", "yacht_v2c2_preview.mp4"], 66.4, 66.4, 129.4,
     [("add", ["yacht_v2c2_screen_final.mkv"])], 0),
    ("bridge (SINN)", ["news_bridge_final.mkv", "news_bridge_preview.mp4"], 129.4, 129.4, 148.6,
     [("over", ["news_overlay_bridge_final.mkv", "news_overlay_bridge.mkv"])], 0),
    # the drone shot's iPad screen: the push-in lands on exactly the frame the cut goes to
    ("instrumental (drone)", ["drone_final.mkv", "suburb_stills/drone.mp4"], 148.6, 148.6, 168.2,
     [("add", ["drone_screen_final.mkv", "suburb_stills/drone_screen.mkv"])], 0),
    ("verse 3, chorus 3 (cyberspace)", ["cyber_v3c3_final.mkv", "cyber_v3c3_preview.mp4"], 162.6, 168.2, 245.6,
     [], 0),
    # Kevin wakes (first person): his phone's screen pass added, his eyelids laid over everything
    ("outro: wake-up", ["wake_final.mkv", "wake.mp4"], 245.6, 245.6, 263.6468,
     [("add", ["wake_screen_final.mkv", "wake_screen.mkv"]), ("over", ["wake_lids.mkv", "wake_lids_540.mkv"])], 0),
    # the end credits: the LED wall's screen pass added (so the credits are the video's own pixels)
    ("outro: credits (yacht)", ["credits_final.mkv", "credits.mp4"], 263.6468, 263.6468, None,
     [("add", ["credits_screen_final.mkv", "credits_screen.mkv"])], 0),
]


PREVIEW = None       # --preview [T]: skip the finals of the sections from song time T on (their timing has
                     # changed since)


def pick(cands, at=0.0):
    for c in cands or []:
        if PREVIEW is not None and at >= PREVIEW - 1e-6 and "_final" in c:
            continue
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
    ap.add_argument("--out", default=os.path.join(B, "full_song.mov"))
    ap.add_argument("--res", type=int, default=1080)
    ap.add_argument("--crf", type=int, default=12, help="x264 quality (lower = better, bigger)")
    ap.add_argument("--list", action="store_true", help="just show what would be used")
    ap.add_argument("--from", dest="start", type=float, default=0.0,
                    help="only the sections from this song time on (e.g. 245.6: the outro), for a quick check")
    ap.add_argument("--preview", type=float, nargs="?", const=0.0, metavar="T",
                    help="use the previews even where there's a final (only from song time T on, if given)")
    A = ap.parse_args()
    global PREVIEW
    PREVIEW = A.preview
    W, H = A.res * 16 // 9, A.res
    song_len = duration(SONG)

    inputs, chains, plan = [], [], []
    secs = [sec for sec in SECTIONS if sec[3] >= A.start - 1e-6]
    for k, (name, cands, f0, s0, s1, layers, fade) in enumerate(secs):
        s1 = song_len if s1 is None else s1
        src = pick(cands, s0)
        found = [(mode, pick(c, s0)) for mode, c in layers]
        found = [(mode, p) for mode, p in found if p]
        # with a dissolve, this section starts `fade` early, overlapping the one before
        a = s0 - fade
        plan.append((name, src, [p for _, p in found] if src else [], s0, s1, fade))
        lab = f"s{k}"
        if src:
            if a < f0 - 1e-6:
                sys.exit(f"{name}: needs footage from {a:.2f} s, but {src} starts at {f0:.2f} s")
            inputs.append(src)
            i = len(inputs) - 1
            cur = f"{lab}_0"
            chains.append(f"[{i}:v]trim=start={a - f0:.4f}:end={s1 - f0:.4f},setpts=N/({FPS}*TB),"
                          f"scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS},format=gbrp[{cur}]")
            for m, (mode, path) in enumerate(found):
                inputs.append(path)
                j = len(inputs) - 1
                lay, nxt = f"{lab}_l{m}", f"{lab}_{m + 1}"
                f = (f"[{j}:v]trim=start={a - f0:.4f}:end={s1 - f0:.4f},setpts=N/({FPS}*TB),"
                     f"scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS}")
                if mode == "add":
                    chains.append(f"{f},format=gbrp[{lay}]")
                    chains.append(f"[{cur}][{lay}]blend=all_mode=addition,format=gbrp[{nxt}]")
                else:
                    chains.append(f"{f},format=rgba[{lay}]")
                    chains.append(f"[{cur}][{lay}]overlay=eof_action=pass:format=gbrp[{nxt}]")
                cur = nxt
            chains.append(f"[{cur}]format=yuv420p,settb=1/{FPS}[{lab}]")
        else:   # nothing rendered yet: black
            chains.append(f"color=c=black:s={W}x{H}:r={FPS}:d={s1 - a:.4f},format=yuv420p,setsar=1,settb=1/{FPS}[{lab}]")

    for name, src, ov, s0, s1, fade in plan:
        print(f"{s0:7.2f}-{s1:7.2f}  {name:34s} {os.path.relpath(src, B) if src else '(black)'}"
              + "".join(f" + {os.path.relpath(p, B)}" for p in ov) + (f"  (dissolves in over {fade} s)" if fade else ""))
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
    cmd += ["-ss", f"{A.start:.4f}", "-i", SONG, "-filter_complex", ";".join(chains), "-map", f"[{cur}]", "-map", f"{len(inputs)}:a",
            "-c:v", "libx264", "-preset", "slow", "-crf", str(A.crf), "-pix_fmt", "yuv420p", "-r", str(FPS),
            *(["-c:a", "pcm_s16le"] if A.out.endswith(".mov") else ["-c:a", "aac", "-b:a", "320k"]),
            "-shortest", "-movflags", "+faststart", A.out]
    subprocess.run(cmd, check=True)
    print("->", A.out, f"({duration(A.out):.2f} s; the song is {song_len:.2f} s)")


if __name__ == "__main__":
    main()
