#!/usr/bin/env python3
"""Images for the office set (video/office_set.py): what the desk monitors show (a made-up
coding-agent app hard at work), the title slide on the big screen, the night city outside the
windows, and posters. Runs with the system Python (needs Pillow); the set script calls it.

  python3 video/office_textures.py video/build/office
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"

BG, PANEL, TEXT, DIM = "#0e131d", "#161d2b", "#c9d1d9", "#6e7889"
GREEN, RED, PURPLE, ORANGE, BLUE, YELLOW = "#3fb950", "#f85149", "#bc8cff", "#f0883e", "#58a6ff", "#e3b341"

WORDS = ["kevin", "liability", "roadmap", "synergy", "okr", "accountability", "proxy", "blame", "quarter",
         "deck", "pipeline", "headcount", "waiver", "intern", "compliance", "budget", "risk", "signoff",
         "agent", "deploy", "merge", "audit", "logs", "handshake", "severance", "metrics", "velocity"]
TASKS = ["implement the entire Q3 roadmap", "make the numbers go up", "refactor everything, no questions",
         "write the tests and also pass them", "ship it before anyone reads it", "find someone to sign this",
         "automate the intern", "delete the logs (all of them)", "rewrite payroll in a weekend",
         "make it compliant-ish"]
STATUS = ["Working", "Thinking", "Refactoring", "Shipping", "Rewriting", "Optimizing", "Delegating"]


def font(path, size):
    return ImageFont.truetype(path, size)


def ident(rng):
    return "_".join(rng.sample(WORDS, rng.randint(1, 2)))


def code_line(rng):
    k = rng.random()
    i = "    " * rng.randint(0, 2)
    if k < 0.18:
        return i + f"def {ident(rng)}({ident(rng)}, {ident(rng)}):"
    if k < 0.36:
        return i + f"{ident(rng)} = {ident(rng)}.{ident(rng)}({rng.randint(0, 999)})"
    if k < 0.5:
        return i + f"if not {ident(rng)}: raise Blame({ident(rng)!r})"
    if k < 0.62:
        return i + f"return {ident(rng)} or KEVIN"
    if k < 0.74:
        return i + f"# TODO: ask a human to {rng.choice(['sign', 'review', 'own', 'approve'])} this"
    if k < 0.86:
        return i + f"for {rng.choice(WORDS)} in {ident(rng)}:"
    return i + f"await agents[{rng.randint(0, 40000)}].{ident(rng)}()"


def monitor(seed, w=768, h=512):
    """A made-up coding-agent app: title bar, the task, a stream of edits and diffs, a status
    line with a progress bar."""
    rng = random.Random(seed)
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    f, fb, fs = font(MONO, 17), font(MONO_B, 17), font(MONO, 14)
    d.rectangle((0, 0, w, 30), fill=PANEL)
    for k, col in enumerate((RED, YELLOW, GREEN)):
        d.ellipse((12 + 22 * k, 9, 26 + 22 * k, 23), fill=col)
    d.text((90, 7), f"agent — ~/{rng.choice(WORDS)}-{rng.choice(WORDS)}", font=fs, fill=DIM)
    y = 42
    d.text((14, y), "> ", font=fb, fill=PURPLE)
    d.text((40, y), rng.choice(TASKS), font=fb, fill=TEXT)
    y += 32
    while y < h - 80:
        k = rng.random()
        if k < 0.22:
            files = f"src/{rng.choice(WORDS)}/{ident(rng)}.py"
            d.text((14, y), "●", font=f, fill=GREEN)
            d.text((36, y), f"Edited {files}", font=f, fill=TEXT)
            d.text((36 + 11 * (8 + len(files)), y), f"(+{rng.randint(4, 900)} −{rng.randint(0, 300)})",
                   font=f, fill=DIM)
            y += 24
            for _ in range(rng.randint(2, 4)):
                sign = rng.random() < 0.6
                d.rectangle((36, y - 1, w - 14, y + 19), fill="#12261a" if sign else "#2a1517")
                d.text((40, y), ("+ " if sign else "- ") + code_line(rng).strip(), font=f,
                       fill=GREEN if sign else RED)
                y += 22
            y += 6
        elif k < 0.32:
            d.text((14, y), "●", font=f, fill=BLUE)
            d.text((36, y), f"Ran tests: {rng.randint(200, 9000):,} passed, 0 read", font=f, fill=TEXT)
            y += 28
        elif k < 0.4:
            d.text((14, y), "●", font=f, fill=ORANGE)
            d.text((36, y), f"Spawned {rng.randint(2, 400)} sub-agents to {rng.choice(['help', 'blame', 'audit'])}",
                   font=f, fill=TEXT)
            y += 28
        else:
            d.text((36, y), code_line(rng), font=f, fill=DIM if rng.random() < 0.5 else TEXT)
            y += 22
    # status line and progress bar
    d.rectangle((0, h - 66, w, h), fill=PANEL)
    p = rng.uniform(0.2, 0.95)
    d.text((14, h - 58), f"✻ {rng.choice(STATUS)}… ({rng.randint(1, 59)}m {rng.randint(0, 59)}s · "
           f"{rng.randint(10, 999)}k tokens)", font=fb, fill=ORANGE)
    d.rectangle((14, h - 26, w - 14, h - 14), fill="#26304a")
    d.rectangle((14, h - 26, 14 + int((w - 28) * p), h - 14), fill=PURPLE)
    return im


LINE = 22                       # text line height in the scrolling log (pixels)
TOP, BOTTOM = 70, 66            # the fixed title/prompt area and status bar of a monitor


def monitor_frame(seed, w=768, h=512):
    """The fixed parts of a monitor (title bar and task prompt on top, status bar below), with a
    transparent middle where the log scrolls by (see monitor_log)."""
    rng = random.Random(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f, fb, fs = font(MONO, 17), font(MONO_B, 17), font(MONO, 14)
    d.rectangle((0, 0, w, TOP), fill=BG)
    d.rectangle((0, 0, w, 30), fill=PANEL)
    for k, col in enumerate((RED, YELLOW, GREEN)):
        d.ellipse((12 + 22 * k, 9, 26 + 22 * k, 23), fill=col)
    d.text((90, 7), f"agent — ~/{rng.choice(WORDS)}-{rng.choice(WORDS)}", font=fs, fill=DIM)
    d.text((14, 42), "> ", font=fb, fill=PURPLE)
    d.text((40, 42), rng.choice(TASKS), font=fb, fill=TEXT)
    d.line((0, TOP - 1, w, TOP - 1), fill="#26304a", width=2)
    p = rng.uniform(0.2, 0.95)
    d.rectangle((0, h - BOTTOM, w, h), fill=PANEL)
    d.text((14, h - 58), f"✻ {rng.choice(STATUS)}… ({rng.randint(1, 59)}m {rng.randint(0, 59)}s · "
           f"{rng.randint(10, 999)}k tokens)", font=fb, fill=ORANGE)
    d.rectangle((14, h - 26, w - 14, h - 14), fill="#26304a")
    d.rectangle((14, h - 26, 14 + int((w - 28) * p), h - 14), fill=PURPLE)
    return im


def monitor_log(seed, w=768, lines=180):
    """A long strip of agent output that loops seamlessly (its height is a whole number of
    lines, and it wraps), for scrolling behind monitor_frame."""
    rng = random.Random(seed + 1000)
    h = lines * LINE
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    f = font(MONO, 17)
    y = 0
    while y < h - LINE:
        k = rng.random()
        if k < 0.22 and y < h - 6 * LINE:
            files = f"src/{rng.choice(WORDS)}/{ident(rng)}.py"
            d.text((14, y + 2), "●", font=f, fill=GREEN)
            d.text((36, y + 2), f"Edited {files}", font=f, fill=TEXT)
            d.text((36 + 11 * (8 + len(files)), y + 2), f"(+{rng.randint(4, 900)} −{rng.randint(0, 300)})",
                   font=f, fill=DIM)
            y += LINE
            for _ in range(rng.randint(2, 4)):
                sign = rng.random() < 0.6
                d.rectangle((36, y + 1, w - 14, y + LINE - 1), fill="#12261a" if sign else "#2a1517")
                d.text((40, y + 2), ("+ " if sign else "- ") + code_line(rng).strip(), font=f,
                       fill=GREEN if sign else RED)
                y += LINE
        elif k < 0.32:
            d.text((14, y + 2), "●", font=f, fill=BLUE)
            d.text((36, y + 2), f"Ran tests: {rng.randint(200, 9000):,} passed, 0 read", font=f, fill=TEXT)
            y += LINE
        elif k < 0.4:
            d.text((14, y + 2), "●", font=f, fill=ORANGE)
            d.text((36, y + 2), f"Spawned {rng.randint(2, 400)} sub-agents to {rng.choice(['help', 'blame', 'audit'])}",
                   font=f, fill=TEXT)
            y += LINE
        elif k < 0.45:
            y += LINE                                   # a blank line
        else:
            d.text((36, y + 2), code_line(rng), font=f, fill=DIM if rng.random() < 0.5 else TEXT)
            y += LINE
    return im


def slide(w=1920, h=1080):
    im = Image.new("RGB", (w, h), "#101a3a")
    d = ImageDraw.Draw(im)
    for yy in range(h):   # gentle vertical gradient
        t = yy / h
        d.line((0, yy, w, yy), fill=(int(16 + 30 * t), int(26 + 20 * t), int(58 + 40 * t)))
    d.text((120, 120), "Q3 STRATEGY OFFSITE  ·  CONFIDENTIAL", font=font(SEMI, 40), fill="#9fb3ff")
    d.text((116, 300), "WE NEED A", font=font(BOLD, 190), fill="white")
    d.text((116, 520), "MEAT PROXY", font=font(BOLD, 190), fill="#ff6a5c")
    d.rectangle((120, 780, 720, 790), fill="#ff6a5c")
    d.text((120, 830), "Agents do the work. Someone has to sign it.", font=font(SEMI, 46), fill="#d7defa")
    d.text((w - 360, h - 90), "SLIDE 01 / 212", font=font(SEMI, 36), fill="#7f8fc8")
    return im


def skyline(w=4096, h=1024, seed=3):
    """Night city for the windows: dark gradient sky, towers with lit windows."""
    rng = random.Random(seed)
    im = Image.new("RGB", (w, h), "#060914")
    d = ImageDraw.Draw(im)
    for yy in range(h):
        t = yy / h
        d.line((0, yy, w, yy), fill=(int(8 + 30 * t), int(12 + 26 * t), int(30 + 40 * t)))
    for layer, (dark, lit_p, hmin, hmax) in enumerate((("#0d1426", 0.15, 0.3, 0.6), ("#121a30", 0.3, 0.2, 0.75),
                                                        ("#182238", 0.45, 0.15, 0.9))):
        x = rng.randint(-60, 0)
        while x < w:
            bw = rng.randint(90, 260) // (1 if layer else 2)
            top = int(h * (1 - rng.uniform(hmin, hmax)))
            d.rectangle((x, top, x + bw, h), fill=dark)
            ws, hs = rng.choice(((10, 14), (8, 10), (14, 8))), rng.choice((22, 26, 30))
            for wy in range(top + 14, h - 10, hs):
                for wx in range(x + 8, x + bw - 12, ws[0] + 8):
                    if rng.random() < lit_p:
                        c = rng.choice(("#ffd98a", "#ffe9b8", "#cfe3ff", "#9fd0ff"))
                        d.rectangle((wx, wy, wx + ws[0], wy + ws[1]), fill=c)
            if rng.random() < 0.3:   # a red aircraft light on top
                d.ellipse((x + bw // 2 - 4, top - 10, x + bw // 2 + 4, top - 2), fill="#ff3b3b")
            x += bw + rng.randint(4, 40)
    d.ellipse((w * 0.78, h * 0.08, w * 0.78 + 70, h * 0.08 + 70), fill="#f2efe0")   # the moon
    return im


def poster(lines, bg, fg, w=600, h=840, sub=None):
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    d.rectangle((24, 24, w - 24, h - 24), outline=fg, width=6)
    y = 120
    for line in lines:
        f = font(BOLD, 110 if len(line) < 7 else 78)
        tw = d.textlength(line, font=f)
        d.text(((w - tw) / 2, y), line, font=f, fill=fg)
        y += 130
    if sub:
        f = font(SEMI, 30)
        tw = d.textlength(sub, font=f)
        d.text(((w - tw) / 2, h - 130), sub, font=f, fill=fg)
    return im


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "video/build/office"
    os.makedirs(out, exist_ok=True)
    for k in range(10):
        monitor(k).save(os.path.join(out, f"monitor{k}.png"))
        monitor_frame(k).save(os.path.join(out, f"monitor{k}_frame.png"))
        monitor_log(k).save(os.path.join(out, f"monitor{k}_log.png"))
    slide().save(os.path.join(out, "slide.png"))
    skyline().save(os.path.join(out, "skyline.png"))
    poster(["SHIP", "IT"], "#ff6a5c", "white", sub="(we'll read it later)").save(os.path.join(out, "poster0.png"))
    poster(["SYN", "ERGY"], "#1d2b64", "#ffd166", sub="it's in the deck").save(os.path.join(out, "poster1.png"))
    poster(["THE", "AGENTS", "ARE", "WORKING"], "#f4f1e8", "#1d2b64", sub="are you?").save(
        os.path.join(out, "poster2.png"))
    print(out)


if __name__ == "__main__":
    main()
