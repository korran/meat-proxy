"""Kevin's eyelids, for the outro (first person): a black overlay with soft, gently curved edges,
transparent where his eyes are open. Laid over the wake shot in assembly.

  python3 video/wake_lids.py [--out video/build/wake_lids.mkv] [--res 1080] [--still OPENNESS,...]

The openness over time (song seconds) is LIDS below: 0 shut (pure black) .. 1 wide open (no lids
in the picture). The upper lid does most of the moving; the edges are soft (out of focus, right in
front of the eye), with a faint dark vignette along them.
"""
import argparse
import math
import os
import subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 60
T0, T1 = 245.6, 263.6468          # the outro's wake-up (the end credits cut in at 263.65)

# (song time, openness): eased between keys (smootherstep), so nothing jolts
LIDS = [
    (245.6, 0.0), (245.95, 0.0),
    (246.5, 0.32), (246.9, 0.22),             # a first crack, then they droop
    (247.05, 0.22), (247.7, 0.62),            # opening properly as the phone comes up, in time to read
                                              # "Good morning, Kevin" (248.3)
    (253.6, 0.66), (253.75, 0.02), (253.95, 0.68),   # a slow blink (after "...pouring concrete")
    (258.6, 0.7), (258.75, 0.02), (258.95, 0.72),    # another (after "I will")
    (263.6468, 0.72),
]


def openness(t):
    if t <= LIDS[0][0]:
        return LIDS[0][1]
    for (ta, a), (tb, b) in zip(LIDS, LIDS[1:]):
        if t <= tb:
            u = (t - ta) / (tb - ta)
            u = u * u * u * (u * (6 * u - 15) + 10)
            return a + (b - a) * u
    return LIDS[-1][1]


def frame(o, W, H, soft):
    """RGBA: black, alpha = how much lid covers each pixel, for openness o."""
    x = (np.arange(W) - W / 2) / (H / 2)                 # -1.78 .. 1.78 across, in half-heights
    y = (np.arange(H)[:, None] - H / 2) / (H / 2)        # -1 (top) .. 1 (bottom)
    # the lids' edges: the upper one comes down from the top, the lower one up from the bottom;
    # both bow a little (the opening is wider in the middle)
    top_edge = -(-0.06 + 1.25 * o) - 0.18 * o * (1 - (x / 1.9) ** 2)        # (y of the edge; up is -)
    bot_edge = (0.03 + 1.05 * o) + 0.1 * o * (1 - (x / 1.9) ** 2)
    s = soft * (0.6 + 0.4 * o)                            # (softer as they open)
    a_top = 1 / (1 + np.exp((y - top_edge) / s))          # 1 above the edge
    a_bot = 1 / (1 + np.exp(-(y - bot_edge) / s))         # 1 below it
    a = np.clip(a_top + a_bot - a_top * a_bot, 0, 1)
    # a faint shadow just inside the edges (lashes, out of focus)
    a = np.maximum(a, 0.35 * np.exp(-((y - top_edge) / (3 * s)) ** 2) * (y > top_edge))
    if o <= 0.001:
        a[:] = 1.0
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = (a * 255 + 0.5).astype(np.uint8)
    return rgba


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "build", "wake_lids.mkv"))
    ap.add_argument("--res", type=int, default=1080)
    ap.add_argument("--soft", type=float, default=0.07, help="edge softness (in half-heights)")
    ap.add_argument("--still", help="just write PNGs for these openness values (comma separated)")
    A = ap.parse_args()
    H = A.res
    W = H * 16 // 9
    if A.still:
        for v in A.still.split(","):
            Image.fromarray(frame(float(v), W, H, A.soft), "RGBA").save(f"{os.path.splitext(A.out)[0]}_{v}.png")
        return
    n = int(round((T1 - T0) * FPS))
    tmp = A.out + ".partial.mkv"
    p = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgra", tmp],
                         stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(frame(openness(T0 + f / FPS), W, H, A.soft).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg failed")
    os.replace(tmp, A.out)
    print("->", A.out, f"({n} frames)")


if __name__ == "__main__":
    main()
