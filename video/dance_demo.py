"""Dance demo: the Manager grooving and gesturing through verse 1, then going big in chorus 1.

  tools/rpp_lyrics.py assets/audio/we_need_a_meat_proxy.rpp --format json > video/build/lyrics.json
  python3 tools/lipsync.py video/build/lyrics.json assets/audio/stems/we_need_a_meat_proxy_vocals.wav \
      --start 9.6 --end 66.6 > video/build/visemes_v1c1.json
  python3 tools/music_features.py assets/audio/stems/we_need_a_meat_proxy_drums.wav \
      assets/audio/we_need_a_meat_proxy.wav > video/build/music.json
  blender -b --factory-startup --python video/dance_demo.py -- --visemes video/build/visemes_v1c1.json \
      --lyrics video/build/lyrics.json --music video/build/music.json --out video/build/dance_frames
  (add --preview for a quick check: no motion blur, 540p, written straight to dance_frames.mp4)

How it stays musical and alive:
  - Every joint is a spring chasing a target pose, so moves have weight: they lag a little,
    overshoot and settle, instead of snapping between poses.
  - The drums drive the body: each real kick/snare hit (from the drum stem) kicks the knees
    and chest, so syncopations and fills show up in the dance. The head bobs on the half-time
    beats (1 and 3), much harder in the chorus.
  - Secondary motion: the arms and head are pushed around by the body's own acceleration.
  - The groove changes every two bars (sway, bounce, step-touch, lean back; in the chorus stomp,
    twist, hop, head-bang) and he turns to face a new direction.
  - Arms are kept off the face and out of the body: every frame, the hand and forearm
    positions are worked out and the arm is nudged outward if they would collide.
  - Gestures act out the lyrics on the words they belong to (ticking off OKRs, a handshake,
    pointing out Kevin, wagging a finger at "don't open the logs", freezing on "holding still",
    robot arms for "the bot", signing on "sign").
  - Exact-timed layers, added after the springs: in the verse the head sways side to side on
    the half-time pulse (arriving on beats 1 and 3); in the chorus a foot stomps down on every
    kick and the right hand comes down on every snare, whatever it is doing (beat times from the REAPER tempo map,
    hits from the drum stem).
  - Section energy: chill in the verse, nearly still for the spoken line, big in the chorus.
"""
import bisect
import json
import math
import os
import random
import re
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lipsync_demo as LS  # noqa: E402
import style_lab as SL  # noqa: E402

THIGH, SHIN = 0.10, 0.14            # adult leg: hip to knee, knee to floor
LEG = THIGH + SHIN
TAU = math.pi * 2
R, Lf = -1, 1                       # his right arm is on the -x side (screen left)

# spring per channel: (frequency Hz, damping ratio). Lower frequency = heavier, lazier.
SPRINGS = {
    "knee0": (4.0, 0.45), "knee1": (4.0, 0.45), "hipf0": (4.5, 0.55), "hipf1": (4.5, 0.55),
    "rx": (2.0, 0.7), "rz": (8.0, 0.7), "roll": (2.2, 0.5), "yaw": (1.5, 0.6),
    "lean": (3.0, 0.45), "cyaw": (2.4, 0.5), "croll": (3.5, 0.4),
    "hx": (3.4, 0.38), "hy": (2.5, 0.5), "hz": (2.0, 0.6),
}
for _s in (R, Lf):
    SPRINGS.update({f"sx{_s}": (3.0, 0.5), f"sab{_s}": (3.0, 0.5), f"sz{_s}": (3.0, 0.55), f"el{_s}": (3.8, 0.42)})
ARM_CH = [c for c in SPRINGS if c[:2] in ("sx", "sa", "sz", "el")]
LEG_CH = ("knee0", "knee1", "hipf0", "hipf1")


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def noise(t, seed):
    """Smooth, slow pseudo-random wobble in about [-1, 1]."""
    return (0.5 * math.sin(1.31 * t + seed) + 0.3 * math.sin(2.87 * t + 2.1 * seed)
            + 0.2 * math.sin(0.61 * t + 3.7 * seed))


def arm(s, x, ab=0.1, z=0.0, el=-0.5):
    """Arm target. x: raise (negative = forward/up), ab: out to the side, z: swing a raised arm
    outward (+) or across the body (-), el: elbow bend (negative)."""
    return {f"sx{s}": x, f"sab{s}": ab, f"sz{s}": z, f"el{s}": el}


class Beats:
    def __init__(self, beats):
        self.b = sorted(beats, key=lambda b: b["t"])
        self.t = [b["t"] for b in self.b]

    def at(self, t):
        """(continuous beat count, phase in beat, bar, beat-in-bar 0..3, beat length)"""
        k = max(0, min(bisect.bisect_right(self.t, t) - 1, len(self.t) - 2))
        t0, t1 = self.t[k], self.t[k + 1]
        return k + (t - t0) / (t1 - t0), (t - t0) / (t1 - t0), self.b[k]["bar"], self.b[k]["beat"] - 1, t1 - t0


# ---------------------------------------------------------------- song structure
def intensity(t):
    """How hard he dances: chill verse, nearly still for the spoken line, big chorus."""
    pts = [(0, 0.45), (36.6, 0.45), (37.2, 0.22), (40.3, 0.2), (41.4, 1.0), (63.3, 1.0), (63.8, 0.55),
           (65.4, 0.6), (65.6, 1.0), (99, 1.0)]
    for (t0, a), (t1, b) in zip(pts, pts[1:]):
        if t0 <= t < t1:
            return a + (b - a) * smooth((t - t0) / (t1 - t0))
    return 1.0


CHORUS_T = (40.9, 66.2)
VERSE_VARIANTS = ["sway", "bounce", "step", "lean"]
CHORUS_VARIANTS = ["stomp", "twist", "hop", "bang"]
FACING = [0.0, -0.32, 0.22, -0.12, 0.35, -0.25, 0.1]


def phrase_plan(first_bar, last_bar):
    """A groove variant and a facing direction per two-bar phrase, never the same twice in a row."""
    rng = random.Random(7)
    plan, prev, prevf = {}, None, None
    for p in range(first_bar // 2, last_bar // 2 + 2):
        opts = CHORUS_VARIANTS if p >= 9 else VERSE_VARIANTS
        v = rng.choice([o for o in opts if o != prev])
        f = rng.choice([x for x in FACING if x != prevf])
        plan[p] = (v, f)
        prev, prevf = v, f
    return plan


# ---------------------------------------------------------------- base groove (legs, body, idle arms)
def groove_pose(t, B, variant, facing, I):
    k, ph, bar, bi, blen = B.at(t)
    pos = bi + ph
    side = 1 if pos < 2 else -1                     # weight on one foot for beats 1-2, the other for 3-4
    sw = {"sway": 1.0, "bounce": 0.35, "step": 0.7, "lean": 0.5, "stomp": 0.8, "twist": 0.3,
          "hop": 0.6, "bang": 0.4}[variant]
    base_knee = 0.1 + 0.18 * I
    p = {"knee0": base_knee, "knee1": base_knee, "hipf0": 0.0, "hipf1": 0.0,
         "rx": 0.014 * sw * side * (0.5 + I), "rz": 0.0, "roll": 0.035 * sw * side * (0.6 + I),
         "yaw": facing + 0.06 * sw * side, "lean": 0.03 + 0.06 * I, "cyaw": -0.08 * sw * side,
         "croll": 0.0, "hx": 0.0, "hy": 0.0, "hz": -0.55 * facing}
    free = 1 if side > 0 else 0                      # the unweighted leg relaxes
    p[f"knee{free}"] += 0.12 * sw
    # idle arms swing gently against the weight shift (the springs and body motion do the rest)
    for s in (R, Lf):
        p.update(arm(s, -0.18 - 0.1 * I + 0.1 * sw * side * s, 0.08 + 0.05 * I, 0.0, -0.55 - 0.35 * I))
    tap = lambda c: math.exp(-((pos - c) / 0.22) ** 2)  # noqa: E731  (pulse centred on beat c)
    if variant == "step":       # step-touch: the free foot taps on 2 and 4
        lift = tap(1.0) + tap(3.0)
        p[f"hipf{free}"] += 0.22 * lift
        p[f"knee{free}"] += 0.35 * lift
    elif variant == "lean":     # leaned back, cool, head tilted
        p["lean"] -= 0.1
        p["hy"] += 0.08
        for s in (R, Lf):
            p[f"el{s}"] -= 0.25
    elif variant == "stomp":    # (the feet stomp on the kick drum, see stomps())
        p["lean"] += 0.05
        for s in (R, Lf):       # elbows bent, fists pumping in opposition to the knees
            up = 0.5 + 0.5 * math.cos(math.pi * (k + (0.0 if s == side else 1.0)))
            p.update(arm(s, -0.7 - 0.5 * up, 0.22, 0.0, -1.6 + 0.2 * up))
    elif variant == "twist":    # the twist: hips swivel on every beat, knees low
        sgn = 1 if int(k) % 2 == 0 else -1
        p["yaw"] += 0.38 * sgn
        p["cyaw"] -= 0.3 * sgn
        p["knee0"] += 0.25
        p["knee1"] += 0.25
        for s in (R, Lf):
            p.update(arm(s, -0.9, 0.35, 0.5 * sgn * s, -1.3))
    elif variant == "hop":      # arms flung up on 1 and 3 (the feet stomp on the kicks)
        for s in (R, Lf):
            p.update(arm(s, -1.0 - 0.6 * (tap(0.0) + tap(2.0)), 0.5, 0.3, -0.9))
    elif variant == "bang":     # head-bang: deep bend, chest forward, arms low and loose
        p["lean"] += 0.12
        p["knee0"] += 0.2
        p["knee1"] += 0.2
        for s in (R, Lf):
            p.update(arm(s, -0.35, 0.3, 0.0, -0.4))
    # keep the arms a little alive even when held
    for s in (R, Lf):
        p[f"sx{s}"] += 0.04 * noise(t * 1.3, 3 * s)
        p[f"el{s}"] += 0.05 * noise(t * 1.7, 5 * s)
    return p


# ---------------------------------------------------------------- arm reach: keep hands off the face
TOP = SL.FIG["z_adult"] + SL.FIG["torso_h"]
HIP = SL.FIG["z_adult"]


def _rot(v, rx, ry, rz, order="XYZ"):
    """Rotate v by Blender euler angles, applied in the given order."""
    x, y, z = v
    for ax in order:
        if ax == "X":
            y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        elif ax == "Y":
            x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        else:
            x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return x, y, z


# Shoulders rotate out to the side first (Y), then swing forward/up (X), then turn (Z). That way
# "out to the side" means out at any height; with the X-first order a raised arm swung inward.
SHOULDER_ORDER = "YXZ"


def arm_points(s, x, ab, z, el):
    """Elbow, mid-forearm and hand positions (chest space) for an arm pose."""
    sh = (0.154 * s, 0.0, TOP - 0.035)
    ry, rz = -(SL.ARM_SLOPE + ab) * s, z * s
    u = _rot((0, 0, -0.115), x, ry, rz, SHOULDER_ORDER)
    f = _rot(_rot((0, 0, -0.133), el, 0, 0), x, ry, rz, SHOULDER_ORDER)
    e = tuple(a + b for a, b in zip(sh, u))
    return [e, tuple(a + 0.5 * b for a, b in zip(e, f)), tuple(a + b for a, b in zip(e, f))]


def blocked(p):
    """Is this point inside the head or torso, or hovering in front of the face?"""
    px, py, pz = p
    if TOP - 0.015 < pz < TOP + 0.28:
        if math.hypot(px, py) < 0.14:
            return True
        if abs(px) < 0.15 and -0.3 < py < 0 and pz > TOP + 0.03:
            return True
    if HIP - 0.02 < pz < TOP + 0.01:
        hw = 0.15 - 0.03 * (pz - HIP) / SL.FIG["torso_h"]
        if abs(px) < hw - 0.005 and abs(py) < 0.08:
            return True
    return False


def clear_arm(s, x, ab, z, el):
    """Nudge an arm pose outward (and straighten the elbow a little) until it clears the body."""
    for k in range(0, 30):
        a2, e2 = ab + 0.05 * k, el * (1 - 0.025 * k)
        if not any(blocked(p) for p in arm_points(s, x, a2, z, e2)):
            return a2, e2
    return ab + 1.5, el * 0.25


# ---------------------------------------------------------------- lyric gestures
class Words:
    def __init__(self, lyrics):
        self.w = [w for line in lyrics["lines"] for w in line["words"]]

    def find(self, text, after=0.0):
        key = re.sub(r"[^a-z]", "", text.lower())
        for w in self.w:
            if w["start"] >= after - 0.01 and re.sub(r"[^a-z]", "", w["text"].lower()) == key:
                return w
        raise KeyError(text)


class Gesture:
    """Targets for some channels between start and end, faded in and out. `fn(t, u)` returns
    (targets, offsets): targets replace the groove, offsets add to it. u = 0..1 through it."""

    def __init__(self, start, end, fn, attack=0.22, release=0.4):
        self.start, self.end, self.fn, self.attack, self.release = start, end, fn, attack, release

    def weight(self, t):
        if t < self.start or t > self.end + self.release:
            return 0.0
        if t < self.start + self.attack:
            return smooth((t - self.start) / self.attack)
        if t > self.end:
            return 1 - smooth((t - self.end) / self.release)
        return 1.0


def link(G):
    """Gestures close together flow straight into each other instead of dropping to idle between."""
    G.sort(key=lambda g: g.start)
    for g, nxt in zip(G, G[1:]):
        gap = nxt.start - g.end
        if gap < 0.8:
            g.release = max(g.release, gap + nxt.attack + 0.05)
    return G


def osc(t, hz, phase=0.0):
    return math.sin(TAU * (hz * t + phase))


def choreography(W, B):
    """Gestures for verse 1 and chorus 1, tied to the words they act out. Poses open out to the
    sides so they read from the front (arms pointing straight at the camera look stubby)."""
    G = []

    def word(text, after=0.0):
        return W.find(text, after)

    def at(text, after, fn, pre=0.2, hold=0.2, until=None, attack=0.22, release=0.4):
        w = word(text, after)
        end = word(until, w["start"])["end"] if until else w["end"]
        G.append(Gesture(w["start"] - pre, end + hold, lambda t, u, w=w: fn(t, u, w), attack, release))
        return w

    def beat_pulse(t, width=0.18):
        """1 right on each beat, falling off quickly (for pumps and chops)."""
        k, ph, *_ = B.at(t)
        d = min(ph, 1 - ph)
        return math.exp(-(d / width) ** 2)

    def per_beat(t):
        return 1 / B.at(t)[4]

    # --- verse 1, line 1: "I've got OKRs to hit and a roadmap due by June"
    def okrs(t, u, w):  # counts the letters off on his fingers, a flick for each
        n = min(2, int(u * 3))
        flick = math.exp(-((u * 3 - n - 0.2) / 0.2) ** 2)
        return ({**arm(R, -0.95, 0.4, 0.15, -1.25 + 0.3 * flick), **arm(Lf, -0.75, 0.35, 0.1, -1.4)},
                {"hx": 0.1, "hz": -0.08})
    at("OKRs", 10.5, okrs, hold=0.1)
    at("roadmap", 12.0, lambda t, u, w: ({**arm(R, -1.2, 0.35, -0.2 + 1.2 * smooth(u), -0.25)},
                                         {"hz": -0.2 + 0.45 * smooth(u)}), hold=0.1)
    at("June", 13.2, lambda t, u, w: ({**arm(R, -2.2, 0.6, 0.1, -0.15)}, {"hx": -0.1, "hy": 0.08}),
       hold=0.1, release=0.6)

    # line 2: "The agent ships a quarter's work by Tuesday afternoon"
    at("ships", 15.3, lambda t, u, w: ({**arm(R, -1.15, 0.45, 0.3, -1.3 + 1.05 * smooth(u * 1.6)),
                                        **arm(Lf, -1.15, 0.45, 0.3, -1.3 + 1.05 * smooth(u * 1.6))},
                                       {"lean": 0.08}), hold=0.0)
    at("quarter's", 15.9, lambda t, u, w: ({**arm(R, -0.95, 0.85, 0.25, -0.35), **arm(Lf, -0.95, 0.85, 0.25, -0.35)},
                                           {"hx": -0.08, "lean": -0.05}), until="work", hold=0.0)
    at("Tuesday", 17.0, lambda t, u, w: ({**arm(Lf, -0.95, 0.4, -0.15, -1.45)},
                                         {"hx": 0.25, "hz": 0.3, "hy": 0.05}), until="afternoon", hold=0.15)

    # line 3: "I've never read a line of it, I just paste it in the deck"
    at("never", 19.2, lambda t, u, w: ({**arm(R, -0.95, 0.45, -0.2 + 1.0 * smooth(u * 1.5), -0.6)},
                                       {"hy": 0.08 * osc(t, 3.0), "hz": 0.12 * osc(t, 2.5)}), until="read", hold=0.0)
    at("paste", 21.4, lambda t, u, w: ({**arm(R, -1.7 + 0.9 * smooth(u * 3), 0.4, 0.15, -1.0 + 0.5 * smooth(u * 3))},
                                       {"lean": 0.1 * smooth(u * 3), "hx": 0.1}), pre=0.28, hold=0.25)

    # line 4: 'And the last guy who asked "Is this safe?" got a handshake and a check'
    at("Is", 24.2, lambda t, u, w: ({**arm(R, -0.55, 0.65, 0.35, -1.15), **arm(Lf, -0.55, 0.65, 0.35, -1.15)},
                                    {"hy": 0.2, "lean": -0.06, "hx": -0.08}), until="safe", hold=0.1)
    at("handshake", 25.8, lambda t, u, w: ({**arm(R, -0.95, 0.35, 0.3, -0.6 + 0.22 * osc(t, per_beat(t)))},
                                           {"lean": 0.05, "hz": -0.1}), until="check", hold=0.1)

    # line 5: "So I made our intern Kevin the new Head of AI Risk"
    at("intern", 28.1, lambda t, u, w: ({**arm(Lf, -1.2, 0.65, 0.85, -0.08)}, {"hz": 0.5, "hx": 0.05}),
       until="Kevin", hold=0.1)
    at("Head", 29.6, lambda t, u, w: ({**arm(R, -1.95, 0.35 + 0.45 * smooth(u * 1.3), 0.2, -0.2),
                                       **arm(Lf, -1.95, 0.35 + 0.45 * smooth(u * 1.3), 0.2, -0.2)},
                                      {"hx": -0.1, "lean": -0.06}), until="Risk", hold=0.1, release=0.5)

    # line 6: "With a budget of ten dollars and a tenure just as brisk"
    at("ten", 32.6, lambda t, u, w: ({**arm(R, -0.95, 0.4, 0.15, -1.5 + 0.08 * osc(t, 7.0))},
                                     {"hx": 0.06, "hy": -0.1}), until="dollars", hold=0.05)
    at("brisk", 35.2, lambda t, u, w: ({**arm(R, -1.35 - 0.25 * smooth(u * 3), 0.85, 0.5, -1.6)},
                                       {"hz": -0.25, "hy": 0.08}), pre=0.15, hold=0.25)

    # spoken: "Great growth opportunity, Kevin. Please don't open the logs."
    at("growth", 37.0, lambda t, u, w: ({**arm(Lf, -0.65, 0.6, 0.6, -0.3 - 0.25 * max(0.0, osc(t, 2.2)))},
                                        {"hz": 0.45, "hx": 0.18, "roll": 0.04}), until="Kevin", hold=0.0)
    at("Please", 38.9, lambda t, u, w: ({**arm(R, -1.45, 0.7, 0.2 + 0.18 * osc(t, 4.0), -1.35)},
                                        {"hy": 0.06 * osc(t, 2.0), "hx": 0.06}), until="logs", hold=0.15)

    # --- chorus 1
    def need_meat_proxy(after):
        # "We NEED a MEAT PROX-Y": arms up in a V on "need", then punches out on the hits
        at("need", after, lambda t, u, w: ({**arm(R, -2.85, 0.45, 0.0, -0.08), **arm(Lf, -2.85, 0.45, 0.0, -0.08)},
                                           {"hx": -0.15, "lean": -0.08}), pre=0.22, hold=0.0)
        m = word("meat", after)
        p = word("proxy", after)
        hits = [(m["start"], R), (p["start"], Lf), ((p["start"] + p["end"]) / 2, R)]

        def punches(t, u, w):
            out = {}
            for s in (R, Lf):
                ext = max((math.exp(-((t - h - 0.06) / 0.1) ** 2) for h, hs in hits if hs == s), default=0.0)
                out.update(arm(s, -0.95 - 0.4 * ext, 0.45, 0.3, -1.6 + 1.45 * ext))
            return out, {"lean": 0.08, "hx": 0.1}
        G.append(Gesture(m["start"] - 0.18, p["end"], lambda t, u: punches(t, u, None)))

    need_meat_proxy(40.5)
    at("body", 42.3, lambda t, u, w: ({**arm(R, -0.4, 0.65, 0.0, -0.3), **arm(Lf, -0.4, 0.65, 0.0, -0.3)},
                                      {"hx": 0.1, "lean": -0.05}), hold=0.0)
    at("bill", 43.3, lambda t, u, w: ({**arm(R, -0.95, 0.4, 0.15, -1.5 + 0.1 * osc(t, 7.0)),
                                       **arm(Lf, -0.8, 0.4, 0.0, -1.3)}, {"hy": -0.12}), hold=0.1)
    at("name", 44.4, lambda t, u, w: ({**arm(R, -1.05, 0.4, 0.1 + 0.2 * osc(t, 4.5), -1.0 + 0.15 * osc(t, 4.5, 0.25)),
                                       **arm(Lf, -0.8, 0.4, -0.05, -1.35)}, {"hx": 0.18}), until="merge", hold=0.0)
    # "a pulse that's holding still": palms out, "hold it"... then everything freezes
    at("pulse", 46.6, lambda t, u, w: ({**arm(R, -1.1, 0.5, 0.3, -1.45), **arm(Lf, -1.1, 0.5, 0.3, -1.45)},
                                       {"hx": 0.05}), until="still", hold=0.0, release=0.15)

    # "the bot's got no assets": deliberately robotic arms, snapping between poses on the 8ths
    def robot(t, u, w):
        k, ph, *_ = B.at(t)
        e = int(k * 2) % 4
        down_fwd = (-0.1, 0.3, 0.0, -1.57)    # upper arm down, forearm straight out front
        side = (-0.1, 1.45, 0.0, -0.05)       # whole arm straight out to the side
        up = (-2.95, 0.35, 0.0, -0.05)       # straight up
        poses = [(down_fwd, side), (side, down_fwd), (down_fwd, down_fwd), (side, up)]
        a, b = poses[e]
        return ({**arm(R, *a), **arm(Lf, *b)}, {"hz": 0.3 * (1 if e % 2 else -1)})
    at("bot's", 48.7, robot, until="assets", hold=0.0, attack=0.06)
    # "no knees to break": bends down and slaps his knees on the beat
    at("knees", 51.2, lambda t, u, w: ({**arm(R, -0.5, 0.3, 0.0, -0.35 + 0.3 * beat_pulse(t)),
                                        **arm(Lf, -0.5, 0.3, 0.0, -0.35 + 0.3 * beat_pulse(t)),
                                        "lean": 0.38, "knee0": 0.75, "knee1": 0.75}, {"hx": 0.15}),
       pre=0.35, until="break", hold=0.0)
    # "hire a little Kevin": palm down at kid height, out to his side
    at("little", 53.8, lambda t, u, w: ({**arm(Lf, -0.45, 0.65, 0.6, -0.6)}, {"hz": 0.4, "hx": 0.22}),
       until="Kevin", hold=0.05)
    # "easy to forsake": a toss over the shoulder, then he spins away on the long note
    at("easy", 55.4, lambda t, u, w: ({**arm(R, -0.6 - 2.0 * smooth(u * 2.2 - 0.5), 0.55, 0.2, -0.35)},
                                      {"hz": -0.25}), until="to", hold=0.0)
    # "put him in the loop": finger twirling a loop overhead, on the beat
    at("loop", 58.4, lambda t, u, w: ({**arm(R, -2.85 + 0.12 * osc(t, per_beat(t)), 0.3,
                                             0.25 * osc(t, per_beat(t), 0.25), -0.2)},
                                      {"hx": -0.12}), pre=0.4, hold=0.0)
    # "put his name on every line": karate chops down on the beats
    at("name", 59.6, lambda t, u, w: ({**arm(R, -1.6 + 0.8 * beat_pulse(t, 0.22), 0.45, 0.2, -0.75),
                                       **arm(Lf, -0.8, 0.45, 0.0, -1.35)}, {"hx": 0.12 * beat_pulse(t)}),
       until="line", hold=0.0)
    need_meat_proxy(62.0)
    # "and the paperwork says SIGN": holds the paper up... then a big signature, ending on the hit
    at("paperwork", 64.1, lambda t, u, w: ({**arm(R, -1.0, 0.45, 0.05, -1.2), **arm(Lf, -1.0, 0.45, 0.05, -1.2)},
                                           {"hx": 0.18}), until="says", hold=0.0)

    def sign(t, u, w):
        sw = smooth(u * 1.4)
        # the pen swings out to the side first, then up into a V, so it never crosses his face
        return ({**arm(R, -1.1 - 1.7 * sw, 0.4 + 0.1 * sw, -0.3 + 0.8 * smooth(u * 3) + 0.15 * osc(t, 6.0) * (1 - sw),
                       -1.0 + 0.92 * sw),
                 **arm(Lf, -0.3, 0.55, 0.0, -1.7)}, {"hx": -0.15 * sw, "lean": -0.08 * sw})
    at("sign", 65.3, sign, pre=0.12, hold=0.6, release=0.6)
    return link(G)


# ---------------------------------------------------------------- whole-body events (no springs)
def jumps(W):
    """(takeoff, landing, height) for jumps: into the chorus, and onto the final 'sign' hit."""
    return [(41.02, 41.40, 0.075), (65.12, 65.52, 0.085)]


def spins(W):
    """(start, end, turns): a full spin on the long 'forsake'."""
    w = W.find("forsake", 56.0)
    return [(w["start"] + 0.35, w["start"] + 1.15, 1.0)]


def freezes(W):
    """Time ranges where he freezes dead still ('holding still')."""
    w = W.find("holding", 47.0)
    return [(w["start"] + 0.05, W.find("still", 47.0)["end"] - 0.02)]


# ---------------------------------------------------------------- layers timed exactly to the music
# These are added after the springs, so their timing is exact to the frame.
DRUM_T = (41.3, 63.4)  # kick stomps and air drums: the chorus, up to the break before "sign"


def head_sway(t, B):
    """Verse: the head sways on the half-time pulse (half the beat rate, ~54 BPM), landing on one
    side on beat 1 and the other on beat 3. Each move accelerates into the beat and stops on it
    with a small overshoot that settles quickly, then holds before setting off again."""
    k, ph, bar, bi, blen = B.at(t)
    pos = bi + ph                          # 0..4 through the bar
    side = 1 if pos < 2 else -1            # where it landed (beat 1 or beat 3)
    dt = (pos % 2) * blen                  # seconds since it landed
    settle = 0.14 * math.exp(-dt / 0.07) * math.sin(math.pi * dt / 0.16)
    x = min(1.0, max(0.0, ((pos % 2) / 2 - 0.4) / 0.6))
    go = 1 - math.cos(math.pi * x / 2)    # eases out of the hold, fastest arriving on the beat
    return side * (1 - 2 * go + settle)


def stomps(hits, J, times, fps):
    """Foot lift per leg per frame: in the chorus a foot comes down exactly on every kick, the feet
    alternating. Returns ([lift0, lift1], impact frames)."""
    n, start = len(times), times[0]
    lift = [[0.0] * n, [0.0] * n]
    last, foot, impacts = [-9.0, -9.0], 1, []
    for h in hits:
        t = h["t"]
        if h["kind"] != "kick" or not DRUM_T[0] <= t <= DRUM_T[1]:
            continue
        if any(a - 0.3 <= t <= b + 0.15 for a, b, _ in J):  # not while jumping
            continue
        f = 1 - foot
        # lift only once the other foot has landed, and not before this foot came down last time
        d = min(0.28, 0.85 * (t - last[f]), t - last[foot])
        if d < 0.12:            # too fast to stomp this one
            continue
        foot = f
        amp = 0.75 + 0.25 * min(1.0, h["strength"])
        i0, i1 = max(0, math.ceil((t - d - start) * fps)), min(n - 1, math.floor((t - start) * fps))
        for i in range(i0, i1 + 1):
            u = (times[i] - (t - d)) / d
            lift[foot][i] = max(lift[foot][i], amp * math.sin(math.pi * min(1.0, u) ** 1.6))
        last[foot] = t
        impacts.append(t)
    return lift, impacts


def snare_hit(t, snares):
    """The right hand's snare accent, -1 (lifted) .. +1 (struck down): a slow wind-up, a strike
    that accelerates down and lands exactly on each snare hit, then an unhurried recovery. It is
    added on top of whatever the hand is doing, so he can gesture and still hit every snare."""
    j = bisect.bisect_left(snares, t)
    dn = snares[j] - t if j < len(snares) else 9.0       # time to the next hit
    dp = t - snares[j - 1] if j > 0 else 9.0             # time since the last one
    strike, wind_t = 0.09, 0.45
    if dn <= strike:                                     # strike: accelerates down onto the hit
        return -1 + 2 * (1 - dn / strike) ** 1.6
    wind = -smooth((wind_t - dn) / (wind_t - strike)) if dn <= wind_t else 0.0
    # after the hit the hand drifts back up, rises a little past rest, and settles
    after = math.exp(-dp / 0.25) * math.cos(min(math.pi, dp * math.pi / 0.6))
    return wind + after * (1 + wind)


# ---------------------------------------------------------------- springs
def spring_track(target, f, z, fps, impulses=None, forces=None, stiff=None, sub=4):
    """A damped spring (frequency f Hz, damping ratio z) chasing a target track, one value per
    frame. impulses: {frame: velocity kick}. forces: extra acceleration per frame (inertia).
    stiff: per-frame frequency multiplier (stiffer = snappier, and more damped)."""
    n = len(target)
    x, v = target[0], 0.0
    out = [0.0] * n
    dt = 1.0 / (fps * sub)
    for i in range(n):
        t0 = target[i]
        t1 = target[i + 1] if i + 1 < n else t0
        m = stiff[i] if stiff else 1.0
        w = TAU * f * m
        zz = min(1.0, z * (1.0 + 0.6 * (m - 1.0))) if m > 1 else z
        if impulses and i in impulses:
            v += impulses[i]
        a_ext = forces[i] if forces else 0.0
        for j in range(sub):
            tg = t0 + (t1 - t0) * j / sub
            a = w * w * (tg - x) - 2 * zz * w * v + a_ext
            v += a * dt
            x += v * dt
        out[i] = x
    return out


# ---------------------------------------------------------------- build and bake
def main():
    A = LS.parse_args(lambda ap: (ap.add_argument("--lyrics", required=True),
                                  ap.add_argument("--music", required=True)))
    D = json.load(open(A.visemes))
    Ly = json.load(open(A.lyrics))
    M = json.load(open(A.music))
    fps, start, frames = D["fps"], D["start"], D["frames"]
    n = len(frames)
    times = [start + i / fps for i in range(n)]
    end = times[-1]
    B = Beats([b for b in Ly["beats"] if start - 3.0 <= b["t"] <= end + 3.0])
    W = Words(Ly)
    G = choreography(W, B)
    J, SP, FZ = jumps(W), spins(W), freezes(W)
    plan = phrase_plan(int(B.b[0]["bar"]), int(B.b[-1]["bar"]))
    mf = M["frames"]

    def mfeat(key, t):
        return mf[key][min(len(mf[key]) - 1, int(round(t * M["fps"])))]

    def frozen(t):
        return max((smooth((t - a) / 0.08) * (1 - smooth((t - b) / 0.12)) for a, b in FZ), default=0.0)

    # 1. targets per channel per frame
    T = {c: [0.0] * n for c in SPRINGS}
    stiff = [1.0] * n
    hold = None
    for i, t in enumerate(times):
        k, ph, bar, bi, blen = B.at(t)
        pos = bi + ph
        I = intensity(t)
        pidx = bar // 2
        v, facing = plan.get(pidx, ("sway", 0.0))
        if CHORUS_T[0] <= t < CHORUS_T[1] and v in VERSE_VARIANTS:
            v = CHORUS_VARIANTS[pidx % 4]
        elif not (CHORUS_T[0] <= t < CHORUS_T[1]) and v in CHORUS_VARIANTS:
            v = VERSE_VARIANTS[pidx % 4]
        p = groove_pose(t, B, v, facing, I)
        # crossfade into the next phrase's groove over the last beat of the phrase
        into = (bar % 2) * 4 + pos
        if into > 7.0:
            v2, f2 = plan.get(pidx + 1, (v, facing))
            in_ch = CHORUS_T[0] <= t + blen < CHORUS_T[1]
            if in_ch and v2 in VERSE_VARIANTS:
                v2 = CHORUS_VARIANTS[(pidx + 1) % 4]
            elif not in_ch and v2 in CHORUS_VARIANTS:
                v2 = VERSE_VARIANTS[(pidx + 1) % 4]
            q = groove_pose(t, B, v2, f2, I)
            u = smooth(into - 7.0)
            p = {c: p[c] * (1 - u) + q[c] * u for c in p}
        # lyric gestures on top
        for g in G:
            w = g.weight(t)
            if w <= 0:
                continue
            tg, off = g.fn(t, (t - g.start) / max(1e-3, g.end - g.start))
            if f"sx{R}" in tg and f"sx{Lf}" in tg:  # two hands: the left trails the right a little
                lag = 0.07
                tl, _ = g.fn(t - lag, (t - lag - g.start) / max(1e-3, g.end - g.start))
                wl = g.weight(t - lag)
                for c in (f"sx{Lf}", f"sab{Lf}", f"sz{Lf}", f"el{Lf}"):
                    p[c] = p[c] * (1 - wl) + tl[c] * wl
                tg = {c: v for c, v in tg.items() if not c.endswith(f"{Lf}") or c.startswith(("knee", "hip"))}
            for c, val in tg.items():
                p[c] = p[c] * (1 - w) + val * w
            for c, val in off.items():
                p[c] += val * w
        # freeze: the upper body holds whatever pose it had when the freeze began (the feet keep
        # stomping on the kicks)
        fz = frozen(t)
        if fz > 0.99 and hold is None:
            hold = {c: T[c][i - 1] for c in T}
        if fz < 0.5:
            hold = None
        if hold is not None:
            p = {c: p[c] if c in LEG_CH else p[c] * (1 - fz) + hold[c] * fz for c in p}
        for s_ in (R, Lf):
            p[f"sab{s_}"], p[f"el{s_}"] = clear_arm(s_, p[f"sx{s_}"], p[f"sab{s_}"], p[f"sz{s_}"], p[f"el{s_}"])
        for c in T:
            T[c][i] = p[c]

    # stiffen the arms while the robot gesture runs (find it by its timing)
    rb = W.find("bot's", 48.7)
    ra = W.find("assets", rb["start"])
    for i, t in enumerate(times):
        if rb["start"] - 0.1 <= t <= ra["end"]:
            stiff[i] = 2.6

    # 2. impulses from the music (velocity kicks, applied a little early so the peak lands on time)
    imp = {c: {} for c in SPRINGS}

    def kick(c, t, dv, lead=0.05):
        f = int(round((t - lead - start) * fps))
        if 0 <= f < n:
            imp[c][f] = imp[c].get(f, 0.0) + dv * (1 if c in LEG_CH else 1 - frozen(t))

    for b in B.b:
        t = b["t"]
        if not (start - 0.2 <= t <= end):
            continue
        I = intensity(t)
        strong = b["beat"] in (1, 3)             # half-time: the head goes down on 1 and 3
        drum = max((h["strength"] for h in M["hits"] if abs(h["t"] - t) < 0.05), default=0.0)
        in_ch = CHORUS_T[0] <= t < CHORUS_T[1]
        if strong:
            kick("hx", t, (3.2 + 9.0 * (I - 0.45) / 0.55 if in_ch else 3.4) * (0.75 + 0.25 * min(1.0, drum)), 0.06)
            kick("knee0", t, 1.6 + 2.6 * I)
            kick("knee1", t, 1.6 + 2.6 * I)
            if in_ch:
                kick("lean", t, 1.2)
        else:
            kick("hx", t, 0.5 + (0.8 if in_ch else 0.0), 0.06)
            kick("knee0", t, 0.5 + 0.6 * I)
            kick("knee1", t, 0.5 + 0.6 * I)
    for h in M["hits"]:
        t = h["t"]
        if not (start <= t <= end):
            continue
        I = intensity(t)
        on_beat = any(abs(b["t"] - t) < 0.06 for b in B.b)
        s = h["strength"] * I
        if h["kind"] == "kick" and not on_beat:   # syncopated kicks: extra bounce
            kick("knee0", t, 1.8 * s)
            kick("knee1", t, 1.8 * s)
            kick("hx", t, 1.6 * s, 0.06)
        if h["kind"] == "snare":                  # snare: the chest pops and shoulders shimmy
            kick("lean", t, -1.0 * s)
            kick("croll", t, 1.4 * s * (1 if int(t * 4) % 2 else -1))
    # hi-hats: a small shoulder shimmy in the verse
    hat_th = 0.45
    for i in range(1, n - 1):
        t = times[i]
        hv = mfeat("hat", t)
        if hv > hat_th and hv >= mfeat("hat", t - 1 / fps) and hv > mfeat("hat", t + 1 / fps):
            kick("croll", t, 0.5 * min(1.0, hv) * (1 if int(t * 8) % 2 else -1) * (1.2 - intensity(t)), 0.03)

    # 3. jumps and spins are scripted (no spring on the flight itself)
    rz_extra = [0.0] * n
    spin = [0.0] * n
    for i, t in enumerate(times):
        for a, b_, hgt in J:
            if a - 0.18 <= t < a:                    # crouch to take off
                u = (t - a + 0.18) / 0.18
                T["knee0"][i] += 0.5 * math.sin(math.pi * u * 0.5)
                T["knee1"][i] += 0.5 * math.sin(math.pi * u * 0.5)
            if a <= t <= b_:
                u = (t - a) / (b_ - a)
                rz_extra[i] = hgt * 4 * u * (1 - u)
                tuck = math.sin(math.pi * u)
                T["knee0"][i] += 0.9 * tuck
                T["knee1"][i] += 0.9 * tuck
                T["hipf0"][i] += 0.45 * tuck
                T["hipf1"][i] += 0.45 * tuck
        for a, b_, turns in SP:
            if t >= a:
                spin[i] += TAU * turns * smooth((t - a) / (b_ - a))
    for a, b_, hgt in J:                             # land hard into a squat
        kick("knee0", b_, 9.0, 0.0)
        kick("knee1", b_, 9.0, 0.0)
        kick("hx", b_, 6.0, 0.0)
        kick("lean", b_, 3.0, 0.0)

    # 4. simulate the body, then the arms and head with inertia from the body's motion
    S = {}
    for c in SPRINGS:
        if c in ARM_CH or c in ("hx",):
            continue
        f, z = SPRINGS[c]
        S[c] = spring_track(T[c], f, z, fps, imp[c])

    lift, stomp_hits = stomps(M["hits"], J, times, fps)
    for leg in (0, 1):
        for i in range(n):
            e = lift[leg][i]
            S[f"knee{leg}"][i] += 0.95 * e
            S[f"hipf{leg}"][i] += 0.5 * e

    def extents(i):
        ex = []
        for leg in (0, 1):
            kn, hf = S[f"knee{leg}"][i], S[f"hipf{leg}"][i]
            h = -(kn / 2 + hf)
            ex.append(THIGH * math.cos(h) + SHIN * math.cos(h + kn + 2 * hf))
        return max(ex)

    root_z = [-(LEG - extents(i)) + S["rz"][i] + rz_extra[i] for i in range(n)]

    def accel(sig, limit):
        """Acceleration of a motion track, smoothed and limited (hard landings shouldn't whip the
        head and arms around)."""
        a = [0.0] * n
        for i in range(1, n - 1):
            a[i] = (sig[i + 1] - 2 * sig[i] + sig[i - 1]) * fps * fps
        a = [sum(a[max(0, i - 2):i + 3]) / len(a[max(0, i - 2):i + 3]) for i in range(n)]
        return [limit * math.tanh(x / limit) for x in a]

    az = accel(root_z, 2.5)
    aroll = accel(S["roll"], 6.0)
    ayaw = accel(S["yaw"], 12.0)
    alean = accel(S["lean"], 10.0)
    for c in ARM_CH:
        f, z = SPRINGS[c]
        s = int(c[-2:]) if c[-2] == "-" else int(c[-1])
        if c.startswith("el"):        # body drops -> forearms swing up (bend more)
            force = [-60.0 * a for a in az]
        elif c.startswith("sab"):     # body rolls -> arms swing out/in
            force = [-0.5 * s * a for a in aroll]
        elif c.startswith("sz"):      # body twists -> raised arms trail behind
            force = [-0.35 * s * a for a in ayaw]
        else:                         # body pitches/drops -> arms lag
            force = [0.4 * a + 25.0 * b for a, b in zip(alean, az)]
        S[c] = spring_track(T[c], f, z, fps, imp[c], force, stiff)
    f, z = SPRINGS["hx"]
    snares = [h["t"] for h in M["hits"] if h["kind"] == "snare" and DRUM_T[0] <= h["t"] <= DRUM_T[1]]
    # around each hit, hold the hand's underlying motion steady, so the strike sets the low point
    # (otherwise the body's own drop on beat 3 keeps swinging the arm down after the hit)
    for c in (f"sx{R}", f"el{R}"):
        base = S[c][:]
        for hit in snares:
            ih = int(round((hit - start) * fps))
            if not 0 <= ih < n:
                continue
            for i in range(max(0, ih - 12), min(n, ih + 30)):
                dt = times[i] - hit
                w = smooth((dt + 0.2) / 0.1) if dt < 0 else 1 - smooth((dt - 0.15) / 0.35)
                S[c][i] = base[i] * (1 - w) + base[ih] * w
    for i, t in enumerate(times):
        te = next((a for a, b in FZ if a <= t <= b + 0.1), t)   # frozen mid-beat, hand and all
        o = snare_hit(te, snares)
        if o:   # struck down = arm lowers and the elbow opens; lifted = the reverse
            S[f"sx{R}"][i] += 0.38 * o
            S[f"el{R}"][i] += 0.7 * o
            S["lean"][i] += 0.05 * o          # the chest dips into the hit
            S["croll"][i] += 0.04 * o * R     # and the shoulders tip toward the hitting hand
    for s in (R, Lf):  # keep the simulated arms clear of the head and body as well
        d_ab, d_el = [0.0] * n, [0.0] * n
        for i in range(n):
            a2, e2 = clear_arm(s, S[f"sx{s}"][i], S[f"sab{s}"][i], S[f"sz{s}"][i], S[f"el{s}"][i])
            d_ab[i], d_el[i] = a2 - S[f"sab{s}"][i], e2 - S[f"el{s}"][i]
        for d in (d_ab, d_el):   # spread each correction a little earlier and later, then smooth it
            big = [max(d[max(0, i - 5):i + 6], key=abs) for i in range(n)]
            d[:] = [sum(big[max(0, i - 4):i + 5]) / len(big[max(0, i - 4):i + 5]) for i in range(n)]
        S[f"sab{s}"] = [a + b for a, b in zip(S[f"sab{s}"], d_ab)]
        S[f"el{s}"] = [a + b for a, b in zip(S[f"el{s}"], d_el)]
    for s in (R, Lf):  # joint limits
        S[f"el{s}"] = [max(-2.5, min(0.05, v)) for v in S[f"el{s}"]]
        S[f"sab{s}"] = [max(-0.05, v) for v in S[f"sab{s}"]]
    S["hx"] = spring_track(T["hx"], f, z, fps, imp["hx"], [40.0 * a - 0.3 * b for a, b in zip(az, alean)])
    for i, t in enumerate(times):  # a small nod into each snare hit
        S["hx"][i] += 0.05 * max(0.0, snare_hit(next((a for a, b in FZ if a <= t <= b + 0.1), t), snares))
    S["hx"] = [0.55 * math.tanh(v / 0.55) for v in S["hx"]]  # neck limit

    # 5. build the figure and bake
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    Bld = SL.Builder("fig", sc.collection)
    top, head, mouths, eyes, blink = LS.singing_manager(Bld, sc)
    legs = Bld.legs[-2:]
    shoulders = {s: find_empty(f"shoulder{s}") for s in (R, Lf)}
    for sh in shoulders.values():
        sh.rotation_mode = SHOULDER_ORDER
    elbows = {s: find_empty(f"elbow{s}") for s in (R, Lf)}
    root = bpy.data.objects.new("root", None)
    sc.collection.objects.link(root)
    for ob in list(sc.collection.objects):
        if ob is not root and ob.parent is None and ob.type in ("MESH", "CURVE", "FONT", "EMPTY"):
            ob.parent = root
    bpy.context.view_layer.update()
    hip_z = SL.FIG["z_adult"]
    chest = bpy.data.objects.new("chest", None)
    sc.collection.objects.link(chest)
    chest.parent = root
    chest.location = (0, 0, hip_z)
    inv = Matrix.Translation((0, 0, hip_z)).inverted()
    for ob in list(root.children):
        if ob is chest:
            continue
        if ob.type == "EMPTY":
            zc = ob.matrix_world.translation.z
        else:
            zc = (sum((ob.matrix_world @ Vector(v) for v in ob.bound_box), Vector()) / 8).z
        if zc > hip_z - 0.015 and not ob.name.startswith(("hip", "knee")):
            ob.parent = chest
            ob.matrix_parent_inverse = inv
    SL.fig_baseplate(Bld, nx=16, ny=11)

    LS.animate_mouths(mouths, frames)
    LS.animate_blinks(eyes, blink, n, fps)
    cam = LS.add_camera(sc, (0.7, -2.9, 0.66), (0, 0, 0.45), 50)
    cam_bump = spring_track([0.0] * n, 3.0, 0.5, fps,
                            {int(round((b["t"] - start) * fps)): 0.25 * intensity(b["t"]) ** 2
                             for b in B.b if b["beat"] in (1, 3) and CHORUS_T[0] <= b["t"] < CHORUS_T[1]})

    level = 0.0
    for i, fr in enumerate(frames):
        level += (fr["level"] - level) * 0.25
        t, f = times[i], i + 1
        for leg, (hip, knee) in enumerate(legs):
            kn, hf = S[f"knee{leg}"][i], S[f"hipf{leg}"][i]
            hip.rotation_euler.x, knee.rotation_euler.x = -(kn / 2 + hf), kn + 2 * hf
            hip.keyframe_insert("rotation_euler", frame=f)
            knee.keyframe_insert("rotation_euler", frame=f)
        root.location = (S["rx"][i], 0.0, root_z[i])
        root.rotation_euler = (0.0, S["roll"][i], S["yaw"][i] + spin[i])
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        chest.rotation_euler = (-S["lean"][i], S["croll"][i], S["cyaw"][i])
        chest.keyframe_insert("rotation_euler", frame=f)
        for s in (R, Lf):
            shoulders[s].rotation_euler = (S[f"sx{s}"][i], -(SL.ARM_SLOPE + S[f"sab{s}"][i]) * s, S[f"sz{s}"][i] * s)
            shoulders[s].keyframe_insert("rotation_euler", frame=f)
            elbows[s].rotation_euler.x = min(0.05, S[f"el{s}"][i])
            elbows[s].keyframe_insert("rotation_euler", frame=f)
        sway = head_sway(t, B) * (1 - smooth((t - 40.4) / 0.6))
        head.rotation_euler = (S["hx"][i] + 0.05 * level, S["hy"][i] + 0.075 * sway, S["hz"][i] + 0.05 * sway)
        head.keyframe_insert("rotation_euler", frame=f)
        # camera: gentle drift in the verse; in the chorus a slow orbit and a bump on 1 and 3
        tt = t - start
        ang = 0.25 + 0.05 * math.sin(tt * 0.3)
        dist = 2.9 - 0.25 * smooth(tt / 25.0)
        if CHORUS_T[0] <= t:
            ang += 0.35 * math.sin(TAU * (t - 40.9) / 26.0) * smooth((t - 40.9) / 2.0)
            dist -= 0.15 * smooth((t - 40.9) / 3.0)
        dist -= cam_bump[i]
        cam.location = (dist * math.sin(ang), -dist * math.cos(ang), 0.66 + 0.04 * math.sin(tt * 0.4))
        SL.aim(cam, (S["rx"][i] * 0.5, 0, 0.45 + 0.4 * (root_z[i] + 0.0)))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)

    if os.environ.get("DANCE_DUMP"):  # motion curves for checking timing outside Blender
        json.dump({"t": times, "root_z": root_z, **S}, open(os.environ["DANCE_DUMP"], "w"))
        return
    LS.setup_look(sc, fps, n, A.res, A.samples, A.blur_steps, A.shutter, A.preview)
    LS.render(sc, A.out, frames, fps, start, A.stills, A.preview)


def find_empty(prefix):
    return next(ob for ob in bpy.data.objects if ob.type == "EMPTY" and ob.name.split(".")[0] == prefix)


main()
