#!/usr/bin/env python3
"""The video on Kevin's phone in the outro: v9's monologue (rendered by dance_demo.py --part outro
--set void, portrait) with TikTok-style captions burned in: one word at a time, big white
letters with a thick black outline, each snapping on as it's said.

  python3 video/wake_phone.py --video video/build/wake_v9_preview.mp4 --out video/build/wake_phone_preview.mp4
  python3 video/wake_phone.py --video video/build/wake_v9.mkv --out video/build/wake_phone.mkv   (lossless)

The video's first frame is song time T0 (the outro's start).
"""
import argparse
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
T0, T1 = 245.6, 283.01
FONT_DIR = "/usr/share/fonts/opentype/inter"
FONT = "Inter Black"
SIZE = 0.085            # letter height, as a fraction of the video's height
OUTLINE = 0.0062        # outline thickness, likewise
Y = 0.63                # the words' centre line, from the top (over her body, clear of her face)
HOLD = 0.35             # a word stays up this long after it's said if the next one is a while off


def clean(text):
    """The word as shown: no quotes or trailing punctuation (apostrophes stay)."""
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[“”\"]", "", text)
    return text.strip(" ,.!?;:")


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def captions(lyrics, W, H):
    words = [w for ln in json.load(open(lyrics))["lines"] for w in ln["words"] if T0 <= w["start"] < T1]
    ev = []
    for k, w in enumerate(words):
        a = w["start"] - T0
        nxt = words[k + 1]["start"] - T0 if k + 1 < len(words) else None
        b = w["end"] - T0 + HOLD
        if nxt is not None:
            b = min(max(b, w["end"] - T0), nxt)       # never overlapping the next word
        ev.append((a, b, clean(w["text"])))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{FONT},{round(SIZE * H / 0.72)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,{OUTLINE * H:.1f},0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{ts(a)},{ts(b)},Word,,0,0,0,,{{\\pos({W // 2},{round(Y * H)})}}{t}\n"
                   for a, b, t in ev)
    return head + body, ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lyrics", default=os.path.join(HERE, "build", "lyrics.json"))
    A = ap.parse_args()
    W, H = (int(v) for v in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                             "stream=width,height", "-of", "csv=p=0", A.video],
                                            capture_output=True, text=True).stdout.strip().split(","))
    ass, ev = captions(A.lyrics, W, H)
    sub = os.path.splitext(A.out)[0] + ".ass"
    open(sub, "w").write(ass)
    for a, b, t in ev:
        print(f"  {a + T0:7.2f}-{b + T0:7.2f}  {t}")
    vf = f"subtitles={sub}:fontsdir={FONT_DIR}"
    enc = (["-c:v", "ffv1", "-pix_fmt", "bgr0"] if A.out.endswith(".mkv")
           else ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p"])
    tmp = A.out + ".partial" + os.path.splitext(A.out)[1]
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", A.video, "-vf", vf, "-an", *enc, tmp],
                   check=True)
    os.replace(tmp, A.out)
    print("->", A.out)


if __name__ == "__main__":
    main()
