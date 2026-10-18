#!/usr/bin/env python3
"""Lip sync: one mouth shape (viseme) per video frame for the sung lyrics.

Combines two sources:
  1. What is being sung: each word's phonemes (CMU pronouncing dictionary; abbreviations
     like "OKRs" are spelled out; unknown words fall back to spelling rules), spread across
     the word's aligned time with vowels getting most of it, as they do in singing.
  2. How the voice is moving, from spectral analysis of the separated vocal track: loudness
     sets how open the mouth is (and silence closes it), and the first two formants refine
     the vowel shapes (F1 ~ jaw opening, F2 ~ wide "ee" vs round "oo").

Visemes: rest, MBP (lips together), FV (teeth on lip), EE, EH, AH (open), OH (round),
OO (small round).

  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --format json > video/build/lyrics.json
  python3 tools/lipsync.py video/build/lyrics.json assets/audio/stems/we_need_a_meat_proxy_vocals.wav \
      --start 9.6 --end 18.8 --fps 60 > video/build/visemes.json

Needs numpy and scipy; `pip install cmudict` for the dictionary (recommended).
"""
import argparse
import json
import math
import re
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import lfilter, resample_poly

try:
    import cmudict
    CMU = cmudict.dict()
except ImportError:  # spelling rules only
    CMU = {}

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
# phoneme -> viseme; diphthongs move between two shapes
PHONE_VISEME = {
    "AA": "AH", "AE": "EH", "AH": "AH", "AO": "OH", "AW": ("AH", "OO"), "AY": ("AH", "EE"),
    "EH": "EH", "ER": "OH", "EY": ("EH", "EE"), "IH": "EE", "IY": "EE", "OW": ("OH", "OO"),
    "OY": ("OH", "EE"), "UH": "OO", "UW": "OO",
    "B": "MBP", "M": "MBP", "P": "MBP", "F": "FV", "V": "FV", "W": "OO", "R": "OH",
    "SH": "OH", "ZH": "OH", "CH": "OH", "JH": "OH", "S": "EE", "Z": "EE",
    "TH": "EH", "DH": "EH", "L": "EH", "T": "EH", "D": "EH", "N": "EH", "K": "EH", "G": "EH",
    "NG": "EH", "HH": "EH", "Y": "EE",
}
VOWEL_VISEMES = {"EE", "EH", "AH", "OH", "OO"}

# crude spelling rules for words the dictionary doesn't know
SPELL = [("ee", "IY"), ("ea", "IY"), ("oo", "UW"), ("ou", "AW"), ("ow", "OW"), ("ai", "EY"), ("ay", "EY"),
         ("oa", "OW"), ("th", "TH"), ("sh", "SH"), ("ch", "CH"), ("ph", "F"), ("ng", "NG"), ("qu", "K"),
         ("a", "AE"), ("e", "EH"), ("i", "IH"), ("o", "AA"), ("u", "AH"), ("y", "IY"),
         ("b", "B"), ("c", "K"), ("d", "D"), ("f", "F"), ("g", "G"), ("h", "HH"), ("j", "JH"), ("k", "K"),
         ("l", "L"), ("m", "M"), ("n", "N"), ("p", "P"), ("r", "R"), ("s", "S"), ("t", "T"), ("v", "V"),
         ("w", "W"), ("x", "K"), ("z", "Z")]


def strip_stress(p):
    return re.sub(r"\d", "", p)


def phonemes(word):
    raw = re.sub(r"[^A-Za-z']", "", word)
    w = raw.lower().replace("’", "'")
    if not w:
        return []
    if w in CMU:
        return [strip_stress(p) for p in CMU[w][0]]
    base = w.rstrip("s")
    if raw.isupper() or (raw[:-1].isupper() and raw.endswith("s") and len(raw) <= 6):  # abbreviation
        out = []
        for ch in raw.lower():
            out += [strip_stress(p) for p in CMU.get(ch, [[ch.upper()]])[0]]
        return out
    if w.endswith("'s") and w[:-2] in CMU:
        return [strip_stress(p) for p in CMU[w[:-2]][0]] + ["Z"]
    if base in CMU and w.endswith("s"):
        return [strip_stress(p) for p in CMU[base][0]] + ["Z"]
    if "-" in word:
        return sum((phonemes(part) for part in word.split("-")), [])
    out, i = [], 0
    while i < len(w):
        for g, p in SPELL:
            if w.startswith(g, i):
                out.append(p)
                i += len(g)
                break
        else:
            i += 1
    return out


def phone_track(lyrics):
    """[(start, end, phone, word)] for every phoneme, spread over each word's sung time."""
    track = []
    for line in lyrics["lines"]:
        for wd in line["words"]:
            ph = phonemes(wd["text"])
            if not ph:
                continue
            weights = [3.0 if p in VOWELS else 1.0 for p in ph]
            total = sum(weights)
            t = wd["start"]
            dur = max(wd["end"] - wd["start"], 0.05)
            for p, wgt in zip(ph, weights):
                d = dur * wgt / total
                track.append((t, t + d, p, wd["text"]))
                t += d
    return track


def lpc(x, order):
    r = np.correlate(x, x, "full")[len(x) - 1:len(x) + order]
    if r[0] <= 0:
        return None
    a = np.zeros(order + 1)
    a[0] = 1.0
    e = r[0]
    for i in range(1, order + 1):
        k = -(r[i] + np.dot(a[1:i], r[i - 1:0:-1])) / e
        a[1:i + 1] = a[1:i + 1] + k * a[i - 1::-1][:i]
        e *= 1 - k * k
        if e <= 0:
            return None
    return a


def formants(frame, sr):
    x = lfilter([1, -0.63], [1], frame) * np.hamming(len(frame))
    a = lpc(x, 12)
    if a is None:
        return None, None
    roots = [r for r in np.roots(a) if np.imag(r) > 0]
    found = []
    for r in roots:
        f = math.atan2(np.imag(r), np.real(r)) * sr / (2 * math.pi)
        bw = -0.5 * sr / math.pi * math.log(abs(r))
        if 200 < f < 3500 and bw < 400:
            found.append(f)
    found.sort()
    f1 = next((f for f in found if 250 < f < 1000), None)
    f2 = next((f for f in found if f1 and f > f1 + 250 and f < 3000), None)
    return f1, f2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lyrics", help="lyrics JSON from tools/rpp_lyrics.py --format json")
    ap.add_argument("vocals", help="separated vocal track (WAV), same timing as the song")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--lead", type=float, default=0.033, help="mouth leads the sound by this many seconds")
    args = ap.parse_args()

    lyrics = json.load(open(args.lyrics))
    track = phone_track(lyrics)

    sr0, x = wavfile.read(args.vocals)
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(1)
    x /= 32768.0
    sr = 16000
    y = resample_poly(x, sr, sr0)
    end = args.end if args.end is not None else len(y) / sr
    win = int(0.03 * sr)

    # loudness over the whole song, so "open" means the same thing in every clip
    hop = int(sr / args.fps)
    allrms = np.sqrt(np.convolve(y * y, np.ones(win) / win, "same")[::hop])
    ref = np.percentile(allrms[allrms > 1e-4], 95) if np.any(allrms > 1e-4) else 1.0

    n = int(math.ceil((end - args.start) * args.fps))
    frames = []
    ti = 0
    for i in range(n):
        t = args.start + i / args.fps + args.lead  # look slightly ahead: the mouth leads the sound
        c = int(t * sr)
        seg = y[max(0, c - win // 2):c + win // 2]
        rms = float(np.sqrt(np.mean(seg * seg))) if len(seg) else 0.0
        level = min(1.0, rms / ref)
        while ti < len(track) and track[ti][1] <= t:
            ti += 1
        cur = track[ti] if ti < len(track) and track[ti][0] - 0.02 <= t < track[ti][1] else None
        f1 = f2 = None
        v, phone, word = "rest", None, None
        if cur:
            s0, s1, phone, word = cur
            v = PHONE_VISEME.get(phone, "EH")
            if isinstance(v, tuple):  # diphthong: first shape, then the second
                v = v[0] if t < (s0 + s1) / 2 else v[1]
            if phone in VOWELS and level > 0.2 and len(seg) == win:
                # formants only refine how open a vowel is; they never flip a rounded vowel to a
                # spread one or back (formant tracking on singing isn't reliable enough for that)
                f1, f2 = formants(seg, sr)
                if f1:
                    if v in ("EH", "AH"):
                        v = "AH" if f1 > 600 else "EH"
                    elif v in ("OH", "OO"):
                        v = "OH" if f1 > 500 else "OO"
            if v == "AH" and level < 0.3:
                v = "EH"  # quiet: not fully open
            if level < 0.06 and v not in ("MBP", "FV"):
                v = "rest"
        frames.append({"t": round(args.start + i / args.fps, 4), "v": v, "level": round(level, 3),
                       "phone": phone, "word": word, "f1": f1 and round(f1), "f2": f2 and round(f2)})

    # tidy: no single-frame flickers, but lip closures always last at least two frames
    labels = [f["v"] for f in frames]
    for i in range(1, len(labels) - 1):
        if labels[i] != labels[i - 1] and labels[i] != labels[i + 1]:
            if labels[i] == "MBP":
                labels[i + 1] = "MBP"
            else:
                labels[i] = labels[i - 1]
    for f, lab in zip(frames, labels):
        f["v"] = lab
    json.dump({"fps": args.fps, "start": args.start, "end": end, "visemes":
               ["rest", "MBP", "FV", "EE", "EH", "AH", "OH", "OO"], "frames": frames}, sys.stdout, indent=0)
    print()


if __name__ == "__main__":
    main()
