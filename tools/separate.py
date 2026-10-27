#!/usr/bin/env python3
"""Separate the song into stems (vocals, drums, bass, other) with Demucs (htdemucs), at the
song's own 48 kHz so every stem lines up sample for sample with it.

  python3 tools/separate.py assets/audio/we_need_a_meat_proxy_mix.wav assets/audio/stems \
      --prefix we_need_a_meat_proxy_mix_

writes assets/audio/stems/we_need_a_meat_proxy_mix_{vocals,drums,bass,other}.wav. Needs torch,
demucs and scipy (pip install demucs scipy); runs on the CPU (a few minutes).
"""
import argparse
import os
import time

import numpy as np
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model
from scipy.io import wavfile
from scipy.signal import resample_poly


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song", help="the song (16-bit WAV, 48 kHz)")
    ap.add_argument("outdir")
    ap.add_argument("--prefix", default="", help="put before each stem's name")
    A = ap.parse_args()
    sr, x = wavfile.read(A.song)
    if sr != 48000:
        raise SystemExit(f"{A.song}: expected 48 kHz, got {sr}")
    x = x.astype(np.float32) / 32768
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    model = get_model("htdemucs")
    model.eval()
    y = resample_poly(x, 147, 160, axis=0).astype(np.float32)      # 48 kHz -> 44.1 kHz (the model's rate)
    wav = torch.from_numpy(y.T.copy())
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    t = time.time()
    with torch.no_grad():
        out = apply_model(model, wav[None], device="cpu", shifts=1, split=True, overlap=0.25, progress=False)[0]
    out = out * ref.std() + ref.mean()
    print(f"separated in {time.time() - t:.0f} s:", ", ".join(model.sources))
    os.makedirs(A.outdir, exist_ok=True)
    for name, src in zip(model.sources, out):
        a = resample_poly(src.numpy().T, 160, 147, axis=0)[:len(x)]   # back to 48 kHz, the song's length
        path = os.path.join(A.outdir, f"{A.prefix}{name}.wav")
        wavfile.write(path, 48000, (np.clip(a, -1, 1) * 32767).astype(np.int16))
        print("->", path)


if __name__ == "__main__":
    main()
