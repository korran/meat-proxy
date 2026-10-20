#!/usr/bin/env python3
"""The end credits on the yacht's LED wall: on the verse 2 slides' blue, v9 dancing in the middle
(dance_demo.py --part credits_v9 --set void --wide --bare: just her, on a transparent background)
with the credits either side of her, paging in on alternating sides on the beat, each at its own
height (so it's clear when one changes); each snaps in, and the last pair holds to the end.

  python3 video/credits_screen.py --video video/build/credits_v9_preview.mkv --out video/build/credits_screen_preview.mp4
  python3 video/credits_screen.py --video video/build/credits_v9.mkv --out video/build/credits_screen.mkv   (lossless)

The video's first frame is song time T0 (when the music comes back up after the monologue).
"""
import argparse
import os
import subprocess

T0, T1 = 259.2, 269.56
STEP = 1.1                 # a new credit every half bar
FONT_DIR = "/usr/share/fonts/opentype/inter"
PW, PH = 2160, 1080        # layout units (the wall's graphics are 2:1)
COLS = (479, 1682)         # the two columns' centres: halfway between the screen's edges and her (she
                           # typically spans x 958 .. 1204, measured from her render)
NAVY, NAVY2 = "#121a3d", "#2a2f66"   # the slides' background: top, bottom (screen_v2.background)
LILAC, WHITE, GREY = "&HF5A7B9&", "&HFFFFFF&", "&HA8A0A0&"     # (ASS colours are BGR)

# (role, name, tag ("|" breaks it onto a second line), the name's height on the screen): each lands
# somewhere new on its side
CREDITS = [
    ("Lyrics", "Opus 5.5", None, 300),
    ("Script", "Opus 5.5", None, 640),
    ("Music Production", "Suno v6", None, 760),
    ("3D Modeling", "Opus 5.5", None, 320),
    ("Animation", "Opus 5.5", None, 520),
    ("AI Life Coach", "Kor Nielsen", "(dim-witted human)", 760),
    ("Song Demo", "Kor Nielsen", "(tasteless human)", 330),
    ("Involuntary Producer", "Joel Nielsen", "(lucky human, owns 5090,|bad at IT security)", 340),
]
# and along the bottom, under her, with the last credit, to the end
SOURCE = ("Source Code", "github.com/korran/meat-proxy", 990)
MONO_DIR = "/usr/share/fonts/truetype/ibm-plex"


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def schedule():
    """[(start, end, column, credit)] in song time: alternating sides, each up until that side's
    next credit (the last ones to the end)."""
    ev = []
    for k, c in enumerate(CREDITS):
        a = T0 + k * STEP
        nxt = T0 + (k + 2) * STEP if k + 2 < len(CREDITS) else T1
        ev.append((a, nxt, k % 2, c))
    return ev


def ass():
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PW}
PlayResY: {PH}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Credit,Inter,100,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for a, b, col, (role, name, tag, y) in schedule():
        x = COLS[col]
        sp = 11 if len(role) <= 16 else 4          # (long roles set tighter, clear of the dancer at the edge)
        lines.append((a, b, x, y - 100, f"{{\\b600\\fs58\\fsp{sp}\\c{LILAC}}}{role.upper()}"))
        lines.append((a, b, x, y, f"{{\\b900\\fs124\\c{WHITE}}}{name}"))
        for k, part in enumerate((tag or "").split("|") if tag else []):
            lines.append((a, b, x, y + 92 + 62 * k, f"{{\\b600\\i1\\fs60\\c{GREY}}}{part}"))
    role, url, y = SOURCE
    a = T0 + (len(CREDITS) - 1) * STEP
    lines.append((a, T1, PW // 2, y - 84, f"{{\\b600\\fs58\\fsp11\\c{LILAC}}}{role.upper()}"))
    lines.append((a, T1, PW // 2, y, f"{{\\fnIBM Plex Mono\\b700\\fs86\\c{WHITE}}}{url}"))
    body = "".join(f"Dialogue: 0,{ts(a - T0)},{ts(b - T0)},Credit,,0,0,0,,{{\\pos({x},{y})}}{txt}\n"
                   for a, b, x, y, txt in lines)
    return head + body


def background(path):
    """The slides' background: NAVY at the top to NAVY2 at the bottom (blended in linear light, as
    the slides' shader does)."""
    import numpy as np
    from PIL import Image

    def lin(h):
        c = np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])
        return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    u = np.linspace(0, 1, PH)[:, None, None]
    c = lin(NAVY) * (1 - u) + lin(NAVY2) * u
    c = np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
    Image.fromarray(np.repeat((c * 255 + 0.5).astype(np.uint8), PW, axis=1), "RGB").save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    A = ap.parse_args()
    sub = os.path.splitext(A.out)[0] + ".ass"
    open(sub, "w").write(ass())
    for a, b, col, (role, name, tag, y) in schedule():
        print(f"  {a:7.2f}-{b:7.2f}  {'LR'[col]} y{y}  {role}: {name} {(tag or '').replace('|', ' ')}")
    bg = os.path.splitext(A.out)[0] + "_bg.png"
    background(bg)
    enc = (["-c:v", "ffv1", "-pix_fmt", "bgr0"] if A.out.endswith(".mkv")
           else ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p"])
    tmp = A.out + ".partial" + os.path.splitext(A.out)[1]
    # (at 60 fps, as the video: Blender plays a movie on a screen one frame per scene frame)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "60",
                    "-i", bg, "-i", A.video,
                    # (both renumbered frame by frame: her render's timestamps are rounded to the
                    # millisecond, so matching them by time repeats and drops a third of her frames)
                    "-filter_complex", f"[0:v]setpts=N/(60*TB)[b];"
                                       f"[1:v]setpts=N/(60*TB),scale={PW}:{PH}:flags=lanczos,format=rgba[v];"
                                       f"[b][v]overlay=shortest=1:format=auto,subtitles={sub}:fontsdir={FONT_DIR}",
                    "-r", "60", "-an", *enc, tmp], check=True)
    os.replace(tmp, A.out)
    print("->", A.out)


if __name__ == "__main__":
    main()
