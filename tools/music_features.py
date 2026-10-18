#!/usr/bin/env python3
"""Per-frame music features for animation: what the drums are doing and how loud the song is.

  python3 tools/music_features.py assets/audio/stems/we_need_a_meat_proxy_drums.wav \
      assets/audio/we_need_a_meat_proxy.wav --fps 60 > video/build/music.json

From the separated drum track:
  kick, snare, hat   onset strength per frame (rises in that band's energy), ~0..1
  hits               detected kick and snare hits: [{t, kind, strength}]
  drums              how busy the drums are right now (smoothed energy, ~0..1)
From the full mix:
  loud               smoothed loudness, ~0..1 (1 = the loudest parts of the song)
All levels are normalized over the whole song, so 0.5 means the same thing in every clip.
"""
import argparse
import json
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, find_peaks, sosfiltfilt

RATE = 200  # analysis frames per second


def load(path):
    sr, x = wavfile.read(path)
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(1)
    return sr, x / 32768.0


def band_env(x, sr, lo, hi):
    """RMS envelope of one frequency band at RATE frames per second."""
    if lo is None:
        sos = butter(4, hi, btype="low", fs=sr, output="sos")
    else:
        sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    y = sosfiltfilt(sos, x)
    hop = sr // RATE
    win = hop * 3
    return np.sqrt(np.convolve(y * y, np.ones(win) / win, "same")[::hop])


def onsets(env):
    """Rises in log energy, normalized so the strong hits of the song are ~1."""
    d = np.maximum(0.0, np.diff(np.log(env + 1e-3), prepend=0.0))
    d = np.convolve(d, np.ones(3) / 3, "same")
    ref = np.percentile(d[d > 0.005], 98) if np.any(d > 0.005) else 1.0
    return d / ref


def smooth_level(env, seconds):
    n = max(1, int(seconds * RATE))
    s = np.convolve(env, np.ones(n) / n, "same")
    return s / np.percentile(s, 97)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drums", help="separated drum track (WAV)")
    ap.add_argument("mix", help="the full song (WAV), same timing")
    ap.add_argument("--fps", type=int, default=60)
    args = ap.parse_args()

    sr, d = load(args.drums)
    bands = {"kick": band_env(d, sr, None, 90), "snare": band_env(d, sr, 180, 400),
             "hat": band_env(d, sr, 8000, 14000)}
    on = {k: onsets(v) for k, v in bands.items()}
    hop = sr // RATE
    drums = smooth_level(np.sqrt(np.convolve(d * d, np.ones(hop) / hop, "same")[::hop]), 0.8)
    srm, m = load(args.mix)
    hopm = srm // RATE
    loud = smooth_level(np.sqrt(np.convolve(m * m, np.ones(hopm) / hopm, "same")[::hopm]), 0.5)

    hits = []
    for kind in ("kick", "snare"):
        peaks, props = find_peaks(on[kind], height=0.35, distance=int(0.09 * RATE))
        for p, h in zip(peaks, props["peak_heights"]):
            # the hit starts where the rise starts, a few analysis frames before the peak
            hits.append({"t": round(max(0, p - 2) / RATE, 4), "kind": kind, "strength": round(min(1.5, float(h)), 3)})
    hits.sort(key=lambda h: h["t"])

    n = int(len(d) / sr * args.fps)
    idx = np.minimum((np.arange(n) / args.fps * RATE).astype(int), len(drums) - 1)
    frames = {k: [round(float(v), 3) for v in np.minimum(on[k][idx], 2.0)] for k in on}
    frames["drums"] = [round(float(v), 3) for v in np.minimum(drums[idx], 1.5)]
    frames["loud"] = [round(float(v), 3) for v in np.minimum(loud[np.minimum(idx, len(loud) - 1)], 1.5)]
    json.dump({"fps": args.fps, "frames": frames, "hits": hits}, sys.stdout)
    print()


if __name__ == "__main__":
    main()
