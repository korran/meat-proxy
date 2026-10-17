#!/usr/bin/env python3
"""Extract lyric timing from the REAPER project.

Reads the word items on the lyrics track (one item per word, the word in the
item notes), the line regions and the tempo map, and prints them as CSV, LRC
or JSON.

Times are seconds into the song's audio file by default, i.e. the project
time minus where the song's audio item starts. Use --project-time for raw
REAPER project time.

With --grid N each word also gets a beat-snapped time ("q_start"/"q_end")
on an N-per-bar-of-4/4 grid (8 = eighths, 16 = sixteenths) plus its
bar/beat/step position. The sung times are kept alongside. JSON output
always includes the snapped times and the beat/bar grid, for beat-synced
visuals.

Examples:
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --lines
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --lines --format lrc > song.lrc
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --grid 16
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --format json > lyrics.json
"""
import argparse
import bisect
import csv
import json
import math
import re
import sys

MARKER = re.compile(r'^MARKER (\d+) (-?[\d.]+) "(.*?)" (\d+)')


def parse(path, lyrics_track, audio_name):
    words, regions, audio = [], {}, None
    tempo, measure_offset = [], 0
    stack, track_name, item = [], None, None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            s = raw.strip()
            if s.startswith("<"):
                tag = s[1:].split()[0]
                stack.append(tag)
                if tag == "TRACK":
                    track_name = None
                elif tag == "ITEM":
                    item = {"track": track_name, "pos": 0.0, "len": 0.0, "notes": [], "file": None}
                continue
            if s == ">":
                tag = stack.pop() if stack else None
                if tag == "ITEM" and item is not None:
                    if item["track"] == lyrics_track and item["notes"]:
                        words.append((item["pos"], item["pos"] + item["len"], " ".join(item["notes"])))
                    if audio is None and item["file"] and item["file"].endswith(audio_name):
                        audio = (item["pos"], item["len"])
                    item = None
                continue
            top = stack[-1] if stack else None
            if top == "TRACK" and s.startswith("NAME "):
                track_name = s[5:].strip().strip('"')
            elif top == "ITEM" and item is not None:
                if s.startswith("POSITION "):
                    item["pos"] = float(s.split()[1])
                elif s.startswith("LENGTH "):
                    item["len"] = float(s.split()[1])
            elif top == "NOTES" and item is not None and s.startswith("|"):
                item["notes"].append(s[1:].strip())
            elif top == "SOURCE" and item is not None and s.startswith("FILE "):
                item["file"] = s[5:].strip().strip('"')
            elif top == "TEMPOENVEX" and s.startswith("PT "):
                p = s.split()
                ts = int(p[4]) if len(p) > 4 else 0
                tempo.append((float(p[1]), float(p[2]), int(p[3]) if len(p) > 3 else 1,
                              (ts & 0xFFFF, ts >> 16) if ts else None))
            elif top == "REAPER_PROJECT":
                if s.startswith("PROJOFFS "):
                    measure_offset = int(float(s.split()[2]))
                m = MARKER.match(s)
                if m and int(m.group(4)) & 1:  # flag bit 1 = region; start and end share an index
                    regions.setdefault(int(m.group(1)), []).append((float(m.group(2)), m.group(3)))
    lines = []
    for k in sorted(regions):
        if len(regions[k]) >= 2:
            (start, text), (end, _) = regions[k][0], regions[k][1]
            lines.append((start, end, text))
    return sorted(words), sorted(lines), audio, sorted(tempo), measure_offset


def beat_grid(tempo, end_time, measure_offset):
    """Project times of every beat up to end_time, from REAPER tempo markers.

    Shape 0 markers ramp linearly in BPM to the next marker; shape 1 markers
    hold. Assumes x/4 time signatures (one beat = one quarter note).
    Returns a list of (time, bar, beat_in_bar, beats_in_bar).
    """
    if not tempo:
        sys.exit("error: project has no tempo markers")
    if tempo[0][0] > 0:
        tempo = [(0.0, tempo[0][1], 1, tempo[0][3])] + tempo
    out, beats_per_bar = [], 4
    bar, pos = measure_offset + 1, 0  # REAPER shows measure 1 at time 0, shifted by PROJOFFS
    frac = 0.0  # beats already elapsed past the last whole beat at the segment start
    for i, (t0, b0, shape, ts) in enumerate(tempo):
        if ts:
            beats_per_bar = ts[0]
            if pos:  # a time signature always starts a new bar
                bar, pos = bar + 1, 0
        last = i + 1 == len(tempo)
        t1 = end_time if last else tempo[i + 1][0]
        b1 = b0 if (shape == 1 or last) else tempo[i + 1][1]
        dur = t1 - t0
        a = (b1 - b0) / dur if dur > 0 else 0.0  # BPM change per second
        total = dur * (b0 + b1) / 120.0  # beats in this segment
        n = 0.0 if frac == 0 else 1.0 - frac  # first whole beat offset into the segment
        while n < total - 1e-9 or (last and n <= total):
            q = n * 60.0
            dt = q / b0 if abs(a) < 1e-12 else 2 * q / (b0 + math.sqrt(b0 * b0 + 2 * a * q))
            out.append((t0 + dt, bar, pos + 1, beats_per_bar))
            pos += 1
            if pos >= beats_per_bar:
                bar, pos = bar + 1, 0
            n += 1.0
        frac = (frac + total) % 1.0
        if abs(frac - 1.0) < 1e-9 or abs(frac) < 1e-9:
            frac = 0.0
    return out


def snap(words, grid, steps_per_beat):
    """Snap word starts/ends to grid steps, keeping order and one word per step."""
    times = [g[0] for g in grid]
    steps = []  # (time, bar, beat, step)
    for i, (t, bar, beat, _) in enumerate(grid[:-1]):
        nxt = times[i + 1]
        for k in range(steps_per_beat):
            steps.append((t + (nxt - t) * k / steps_per_beat, bar, beat, k + 1))
    st = [s[0] for s in steps]

    def nearest(t):
        j = bisect.bisect_left(st, t)
        if j == 0:
            return 0
        if j >= len(st):
            return len(st) - 1
        return j if st[j] - t < t - st[j - 1] else j - 1

    out, prev = [], -1
    for i, (start, end, text) in enumerate(words):
        a = max(nearest(start), prev + 1)
        a = min(a, len(steps) - 1)
        out.append([a, end, text, start])
        prev = a
    for i, w in enumerate(out):
        a, end, text, start = w
        nxt_start = words[i + 1][0] if i + 1 < len(words) else None
        nxt_q = out[i + 1][0] if i + 1 < len(out) else len(steps) - 1
        if nxt_start is not None and nxt_start - end < 0.02:  # word runs into the next one
            b = nxt_q
        else:
            b = min(max(nearest(end), a + 1), nxt_q)
        w.append(b)
    return [(steps[a], st[min(b, len(st) - 1)], start, end, text) for a, end, text, start, b in out]


def lrc_time(t):
    t = max(t, 0.0)
    return f"[{int(t // 60):02d}:{t % 60:05.2f}]"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rpp", help="REAPER project file")
    what = ap.add_mutually_exclusive_group()
    what.add_argument("--words", action="store_true", help="word timing (default)")
    what.add_argument("--lines", action="store_true", help="line timing from regions")
    ap.add_argument("--format", choices=["csv", "lrc", "json"], default="csv")
    ap.add_argument("--grid", type=int, choices=[4, 8, 16, 32],
                    help="also give beat-snapped word times on this grid (steps per 4/4 bar); json defaults to 16")
    ap.add_argument("--track", default="Lyrics (words)", help="name of the word track")
    ap.add_argument("--audio", default="we_need_a_meat_proxy.wav",
                    help="audio file whose item start is time zero")
    ap.add_argument("--project-time", action="store_true", help="output REAPER project time instead")
    args = ap.parse_args()

    words, lines, audio, tempo, measure_offset = parse(args.rpp, args.track, args.audio)
    if args.project_time:
        offset = 0.0
    elif audio is None:
        sys.exit(f"error: no item using {args.audio!r} found; pass --audio or --project-time")
    else:
        offset = audio[0]
    if not words and not args.lines:
        sys.exit(f"error: no lyric items on track {args.track!r} found")
    if not lines and (args.lines or args.format == "json"):
        sys.exit("error: no lyric regions found")

    grid_n = args.grid or (16 if args.format == "json" else None)
    if grid_n:
        end = max([w[1] for w in words] + ([audio[0] + audio[1]] if audio else [])) + 4.0
        grid = beat_grid(tempo, end, measure_offset)
        snapped = snap(words, grid, grid_n // 4)
    r = lambda t: round(t - offset, 4)

    if args.format == "json":
        lines_out = []
        for ls, le, text in lines:
            lines_out.append({"text": text, "start": r(ls), "end": r(le), "words": []})
        for (q, q_end, start, end, text) in snapped:
            li = max(0, bisect.bisect_right([l[0] for l in lines], start + 1e-6) - 1)
            lines_out[li]["words"].append({
                "text": text, "start": r(start), "end": r(end),
                "q_start": r(q[0]), "q_end": r(q_end),
                "bar": q[1], "beat": q[2], "step": q[3]})
        for l in lines_out:
            if l["words"]:
                l["q_start"], l["q_end"] = l["words"][0]["q_start"], l["words"][-1]["q_end"]
        doc = {
            "audio": args.audio,
            "time": "project seconds" if args.project_time else "seconds into the audio file",
            "grid": f"{grid_n} steps per 4/4 bar ({grid_n // 4} per beat)",
            "beats": [{"t": r(t), "bar": b, "beat": k} for t, b, k, _ in grid
                      if -0.5 <= t - offset <= (audio[0] + audio[1] - offset if audio else 1e9)],
            "lines": lines_out,
        }
        doc["bars"] = [{"bar": b["bar"], "t": b["t"]} for b in doc["beats"] if b["beat"] == 1]
        json.dump(doc, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return

    rows = lines if args.lines else words
    if args.format == "lrc":
        for start, _, text in rows:
            print(f"{lrc_time(start - offset)}{text}")
        return
    w = csv.writer(sys.stdout)
    if args.lines or not grid_n:
        w.writerow(["start_s", "end_s", "line" if args.lines else "word"])
        for start, end, text in rows:
            w.writerow([f"{start - offset:.3f}", f"{end - offset:.3f}", text])
    else:
        w.writerow(["start_s", "end_s", "q_start_s", "q_end_s", "bar", "beat", "step", "word"])
        for q, q_end, start, end, text in snapped:
            w.writerow([f"{start - offset:.3f}", f"{end - offset:.3f}", f"{q[0] - offset:.3f}",
                        f"{q_end - offset:.3f}", q[1], q[2], q[3], text])


if __name__ == "__main__":
    if hasattr(__import__("signal"), "SIGPIPE"):  # exit quietly when piped into head etc.
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
