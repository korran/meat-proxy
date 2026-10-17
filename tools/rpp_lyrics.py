#!/usr/bin/env python3
"""Extract lyric timing from the REAPER project.

Reads the word items on the lyrics track (one item per word, the word in the
item notes) and the line regions, and prints them as CSV or LRC.

Times are seconds into the song's audio file by default, i.e. the project
time minus where the song's audio item starts. Use --project-time for raw
REAPER project time.

Examples:
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --lines
  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --lines --format lrc > song.lrc
"""
import argparse
import csv
import re
import sys

MARKER = re.compile(r'^MARKER (\d+) (-?[\d.]+) "(.*?)" (\d+)')


def parse(path, lyrics_track, audio_name):
    words, regions, audio_offset = [], {}, None
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
                    if audio_offset is None and item["file"] and item["file"].endswith(audio_name):
                        audio_offset = item["pos"]
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
            elif top == "REAPER_PROJECT":
                m = MARKER.match(s)
                if m and int(m.group(4)) & 1:  # flag bit 1 = region; start and end share an index
                    regions.setdefault(int(m.group(1)), []).append((float(m.group(2)), m.group(3)))
    lines = []
    for k in sorted(regions):
        if len(regions[k]) >= 2:
            (start, text), (end, _) = regions[k][0], regions[k][1]
            lines.append((start, end, text))
    words.sort()
    lines.sort()
    return words, lines, audio_offset


def lrc_time(t):
    t = max(t, 0.0)
    return f"[{int(t // 60):02d}:{t % 60:05.2f}]"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rpp", help="REAPER project file")
    what = ap.add_mutually_exclusive_group()
    what.add_argument("--words", action="store_true", help="word timing (default)")
    what.add_argument("--lines", action="store_true", help="line timing from regions")
    ap.add_argument("--format", choices=["csv", "lrc"], default="csv")
    ap.add_argument("--track", default="Lyrics (words)", help="name of the word track")
    ap.add_argument("--audio", default="we_need_a_meat_proxy.wav",
                    help="audio file whose item start is time zero")
    ap.add_argument("--project-time", action="store_true", help="output REAPER project time instead")
    args = ap.parse_args()

    words, lines, offset = parse(args.rpp, args.track, args.audio)
    if args.project_time:
        offset = 0.0
    elif offset is None:
        sys.exit(f"error: no item using {args.audio!r} found; pass --audio or --project-time")

    rows = lines if args.lines else words
    if not rows:
        sys.exit("error: no lyric " + ("regions" if args.lines else f"items on track {args.track!r}") + " found")

    if args.format == "lrc":
        for start, _, text in rows:
            print(f"{lrc_time(start - offset)}{text}")
    else:
        w = csv.writer(sys.stdout)
        w.writerow(["start_s", "end_s", "line" if args.lines else "word"])
        for start, end, text in rows:
            w.writerow([f"{start - offset:.3f}", f"{end - offset:.3f}", text])


if __name__ == "__main__":
    main()
