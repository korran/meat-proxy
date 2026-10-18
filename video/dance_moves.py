"""Choreography for the singing performances: per-part song structure and lyric gestures.

A "part" is one continuous performance clip (e.g. verse 1 + chorus 1 by the Manager). Each part
says who performs, how hard he dances when (intensity), where the chorus and the drum-driven
layers are, and which gestures act out which words. video/dance_demo.py is the engine that turns
this into motion. Times are seconds into the song's audio file.

Arm targets (see arm()): x raises the arm (negative = forward/up), ab swings it out to the side,
z swings a raised arm outward (+) or across the body (-), el bends the elbow (negative).
R is his right arm (screen left), Lf his left (the Founder's phone hand).
"""
import math
import re

TAU = math.pi * 2
R, Lf = -1, 1                       # his right arm is on the -x side (screen left)


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


def authoring(W, B, G):
    """Helpers for writing a part's gestures into the list G."""
    def word(text, after=0.0):
        return W.find(text, after)

    def at(text, after, fn, pre=0.2, hold=0.2, until=None, attack=0.22, release=0.4):
        """Gesture `fn(t, u, word)` from just before `text` (first match after `after`) to the
        end of that word, or of the word `until`."""
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

    def need_meat_proxy(after, need="need"):
        """'We NEED a MEAT PROX-Y': arms up in a V on 'need', then punches out on the hits."""
        at(need, after, lambda t, u, w: ({**arm(R, -2.85, 0.45, 0.0, -0.08), **arm(Lf, -2.85, 0.45, 0.0, -0.08)},
                                         {"hx": -0.15, "lean": -0.08}), pre=0.22, hold=0.0)
        m = word("meat", after)
        p = word("proxy", after)
        hits = [(m["start"], R), (p["start"], Lf), ((p["start"] + p["end"]) / 2, R)]

        def punches(t, u):
            out = {}
            for s in (R, Lf):
                ext = max((math.exp(-((t - h - 0.06) / 0.1) ** 2) for h, hs in hits if hs == s), default=0.0)
                out.update(arm(s, -0.95 - 0.4 * ext, 0.45, 0.3, -1.6 + 1.45 * ext))
            return out, {"lean": 0.08, "hx": 0.1}
        G.append(Gesture(m["start"] - 0.18, p["end"], punches))

    def robot(t, u, w):
        """Deliberately robotic arms, snapping between poses on the 8ths."""
        k, ph, *_ = B.at(t)
        e = int(k * 2) % 4
        down_fwd = (-0.1, 0.3, 0.0, -1.57)    # upper arm down, forearm straight out front
        side = (-0.1, 1.45, 0.0, -0.05)       # whole arm straight out to the side
        up = (-2.95, 0.35, 0.0, -0.05)        # straight up
        poses = [(down_fwd, side), (side, down_fwd), (down_fwd, down_fwd), (side, up)]
        a, b = poses[e]
        return ({**arm(R, *a), **arm(Lf, *b)}, {"hz": 0.3 * (1 if e % 2 else -1)})

    def sign(t, u, w):
        """A big signature: the pen swings out to the side first, then up into a V."""
        sw = smooth(u * 1.4)
        return ({**arm(R, -1.1 - 1.7 * sw, 0.4 + 0.1 * sw, -0.3 + 0.8 * smooth(u * 3) + 0.15 * osc(t, 6.0) * (1 - sw),
                       -1.0 + 0.92 * sw),
                 **arm(Lf, -0.3, 0.55, 0.0, -1.7)}, {"hx": -0.15 * sw, "lean": -0.08 * sw})

    return word, at, beat_pulse, per_beat, need_meat_proxy, robot, sign


def v1c1_gestures(W, B):
    """The Manager, verse 1 and chorus 1. Gestures tied to the words they act out. Poses open out to
    the sides so they read from the front (arms pointing straight at the camera look stubby)."""
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


def v2c2_gestures(W, B):
    """The Founder, verse 2 and chorus 2: a lounging billionaire who never looks at what he taps.
    His phone is in his left hand the whole time."""
    G = []
    word, at, beat_pulse, per_beat, need_meat_proxy, robot, sign = authoring(W, B, G)
    phone = arm(Lf, -0.85, 0.3, -0.2, -1.45)          # phone held up in front of his chest

    def tapping(t, rate=8.0, amount=0.1):            # right hand tapping/typing at the phone
        return arm(R, -0.8, 0.3, -0.3, -1.38 + amount * max(0.0, osc(t, rate)))

    # --- verse 2, line 1: "I fired forty thousand people from the deck of my third yacht"
    at("fired", 66.9, lambda t, u, w: ({**phone, **tapping(t, 3.0, 0.2)}, {"hz": 0.25, "hx": -0.05}), hold=0.0)
    at("forty", 67.5, lambda t, u, w: ({**arm(R, -1.0, 0.5, -0.3 + 1.2 * smooth(u * 1.2), -0.5), **phone},
                                       {"hz": 0.2, "hy": 0.06}), until="thousand", hold=0.0)
    at("deck", 69.6, lambda t, u, w: ({**arm(R, 0.25, 0.75, 0.0, -0.25), **arm(Lf, 0.25, 0.75, 0.0, -0.25)},
                                      {"lean": -0.1, "hy": 0.1, "hx": -0.08}), until="yacht", hold=0.25, release=0.5)

    # line 2: "Replaced them all with agents that I vibe-coded on the spot"
    at("Replaced", 71.3, lambda t, u, w: ({**arm(R, -1.1, 0.4, 0.7 - 1.1 * smooth(u * 1.3), -0.4), **phone},
                                          {"hz": -0.15}), until="all", hold=0.0)
    at("agents", 72.5, lambda t, u, w: ({**arm(R, -1.2, 0.6 + 0.3 * smooth(u * 2), 0.3, -0.6 + 0.4 * smooth(u * 2)),
                                         **arm(Lf, -1.2, 0.6 + 0.3 * smooth(u * 2), 0.3, -0.6 + 0.4 * smooth(u * 2))},
                                        {"hx": -0.06}), hold=0.0)
    at("vibe-coded", 73.4, lambda t, u, w: ({**phone, **tapping(t)},
                                            {"hy": 0.12 * osc(t, per_beat(t) / 2), "hz": -0.1, "hx": 0.1}),
       hold=0.05)
    at("spot", 74.9, lambda t, u, w: ({**arm(R, -0.75, 0.3, 0.1, -0.05)}, {"hx": 0.15}), hold=0.1)

    # line 3: "But the Senate wants a hearing and the voters want a head"
    at("Senate", 76.3, lambda t, u, w: ({**arm(R, -1.7, 0.8, 0.3, -2.0)}, {"hy": -0.12, "hz": -0.15}),
       until="hearing", hold=0.1)
    at("voters", 78.4, lambda t, u, w: ({**arm(R, -0.55, 0.65, 0.35, -1.15), **arm(Lf, -0.55, 0.65, 0.35, -1.15)},
                                        {"hy": 0.18, "lean": -0.05}), until="head", hold=0.1)

    # line 4: "So I'll keep a human handy to be sacrificed instead"
    at("keep", 80.7, lambda t, u, w: ({**arm(R, -0.15, 0.45, 0.0, -0.9 + 0.25 * beat_pulse(t))},
                                      {"hx": 0.06, "hz": -0.1}), until="handy", hold=0.0)
    at("sacrificed", 82.8, lambda t, u, w: ({**arm(R, -2.7, 0.55, 0.0, -0.15), **arm(Lf, -2.7, 0.55, 0.0, -0.15)},
                                            {"lean": -0.1, "hx": -0.25}), hold=0.0)
    at("instead", 83.8, lambda t, u, w: ({**arm(R, -0.9, 0.3, -0.2 + 0.2 * osc(t, 5.0), -1.3),
                                          **arm(Lf, -0.9, 0.3, -0.2 - 0.2 * osc(t, 5.0), -1.3)}, {"hx": 0.08}),
       hold=0.0)

    # line 5: "One Kevin per division, like a fuse that's built to blow"
    at("One", 84.7, lambda t, u, w: ({**arm(R, -2.0, 0.4, 0.1, -0.35)}, {"hx": -0.05}), until="Kevin", hold=0.0)
    at("division", 85.9, lambda t, u, w: ({**arm(R, -1.3 + 0.35 * beat_pulse(t), 0.4, -0.3 + 0.9 * u, -0.7)},
                                          {"hz": -0.2 + 0.4 * u}), until="division", hold=0.0)
    at("fuse", 87.0, lambda t, u, w: ({**arm(R, -0.75, 0.25, -0.35, -1.2), **arm(Lf, -0.75, 0.25, -0.35, -1.2)},
                                      {"hx": 0.15}), until="to", hold=0.0)
    at("blow", 88.3, lambda t, u, w: ({**arm(R, -1.7, 0.95, 0.4, -0.1), **arm(Lf, -1.7, 0.95, 0.4, -0.1)},
                                      {"lean": -0.12, "hx": -0.15}), pre=0.04, attack=0.08, hold=0.1)

    # line 6: "When the hearing gets too spicy, there's a Kevin I can throw"
    at("spicy", 90.4, lambda t, u, w: ({**arm(R, -1.45, 0.75, 0.25 + 0.2 * osc(t, 6.0), -1.55)}, {"hx": -0.1}),
       hold=0.0)
    at("Kevin", 91.5, lambda t, u, w: ({**arm(R, 0.5, 0.35, 0.0, -1.3)}, {"yaw": -0.35, "cyaw": -0.25, "lean": -0.05}),
       until="can", hold=0.0)
    at("throw", 92.5, lambda t, u, w: ({**arm(R, -2.3 + 0.9 * smooth(u * 2), 0.4, -0.1, -0.1)},
                                       {"yaw": 0.3, "lean": 0.15, "hx": 0.1}), pre=0.1, attack=0.1, hold=0.15)

    # spoken: "Per division? (2-beat bar: a hiccup freeze) Make it per continent... Efficiency."
    at("division", 93.6, lambda t, u, w: ({**arm(R, -0.8, 0.5, 0.3, -1.2)}, {"hy": 0.15}), hold=0.9, release=0.3)
    at("Make", 95.0, lambda t, u, w: ({**arm(R, -1.6 + 0.5 * math.cos(TAU * smooth(u)), 0.6 + 0.35 * math.sin(TAU * smooth(u)),
                                             0.2, -0.15)}, {"hz": 0.15 * math.sin(TAU * smooth(u))}),
       until="continent", hold=0.1)
    at("Efficiency", 97.0, lambda t, u, w: ({**arm(R, -1.4, 0.3, 0.2, -0.05)}, {"lean": -0.08, "hy": 0.15}),
       pre=0.12, attack=0.1, hold=0.3)

    # --- chorus 2
    need_meat_proxy(98.6)

    def cheaper(t, u, w):  # the price drops on every beat: palm-down hand stepping down
        kb = B.at(t)[0] - B.at(w["start"] - 0.2)[0]
        st = min(4.0, math.floor(kb) + smooth((kb % 1) / 0.25))
        return {**arm(R, -1.8 + 0.33 * st, 0.45, 0.2, -1.3)}, {"hx": 0.04 * st}
    at("cheaper", 100.4, cheaper, until="time", hold=0.0)
    at("gig", 102.5, lambda t, u, w: ({**arm(R, -1.3, 0.45, 0.35, -0.1)}, {"hz": -0.15}), until="work", hold=0.0)
    at("contract", 103.6, lambda t, u, w: ({**arm(Lf, -1.3, 0.45, 0.35, -0.1)}, {"hz": 0.15}), hold=0.0)
    at("ninety", 104.4, lambda t, u, w: ({**arm(R, -1.0, 0.4, 0.15, -1.5 + 0.1 * osc(t, 7.0))}, {"hy": -0.1}),
       until="cents", hold=0.0)
    at("crime", 105.6, lambda t, u, w: ({**arm(R, -1.05, 0.15, -0.4, -1.2), **arm(Lf, -1.05, 0.15, -0.4, -1.2)},
                                       {"hy": 0.1, "hx": 0.1, "lean": -0.05}), hold=0.0)
    at("bot", 106.5, robot, until="laws", hold=0.0, attack=0.06)
    at("one", 109.2, lambda t, u, w: ({**arm(R, -2.0, 0.4, 0.1, -0.35)}, {"hx": -0.05}), until="man", hold=0.0)
    at("take", 110.3, lambda t, u, w: ({**arm(R, -1.3, 0.85, 0.35, -0.6), **arm(Lf, -1.3, 0.85, 0.35, -0.6)},
                                      {"hz": 0.15 * osc(t, 3.0)}), hold=0.0)

    def sow(t, u, w):  # flinging seed out on every beat
        ph = B.at(t)[1]
        fl = math.exp(-((ph - 0.2) / 0.2) ** 2)
        return {**arm(R, -0.9 - 0.3 * fl, 0.35 + 0.6 * fl, 0.3, -1.3 + 0.9 * fl)}, {"hz": -0.1 * fl}
    at("farm", 111.2, sow, until="Kevins", hold=0.0)
    at("shareholders'", 113.3, lambda t, u, w: ({**arm(R, -1.5, 0.5, 0.2, -0.9 + 0.35 * osc(t, 2 * per_beat(t))),
                                                 **arm(Lf, -1.5, 0.5, 0.2, -0.9 + 0.35 * osc(t, 2 * per_beat(t), 0.5))},
                                                {"hx": -0.1}), hold=0.0)
    at("Grease", 115.7, lambda t, u, w: ({**arm(R, -0.95, 0.2, -0.35 + 0.12 * osc(t, 5.0), -1.3),
                                          **arm(Lf, -0.95, 0.2, -0.35 - 0.12 * osc(t, 5.0), -1.3)}, {"hx": 0.1}),
       hold=0.0)
    at("couple", 116.3, lambda t, u, w: ({**arm(R, -0.55 - 0.3 * smooth(u), 0.2, -0.2, -0.6)},
                                         {"hz": 0.3, "lean": 0.08}), until="senators", hold=0.0)
    at("signed", 118.9, sign, pre=0.15, hold=0.3, release=0.5)
    need_meat_proxy(119.9, need="neat")  # (sic: the lyric sheet says "neat")
    at("body", 122.1, lambda t, u, w: ({**arm(R, -0.4, 0.65, 0.0, -0.3), **arm(Lf, -0.4, 0.65, 0.0, -0.3)},
                                       {"hx": 0.1, "lean": -0.05}), hold=0.0)
    at("not", 122.9, lambda t, u, w: ({**arm(R, -1.45, 0.7, 0.2 + 0.18 * osc(t, 4.0), -1.35)},
                                      {"hz": 0.15 * osc(t, 2.5)}), until="mind", hold=0.2)

    # spoken: "Kevin cleared six figures last year. Mostly felonies."
    at("Kevin", 124.8, lambda t, u, w: ({**arm(Lf, -1.2, 0.65, 0.85, -0.08)}, {"hz": 0.45}), until="cleared", hold=0.0)
    at("six", 125.9, lambda t, u, w: ({**arm(R, -0.9, 0.7, 0.35, -1.0), **arm(Lf, -0.9, 0.7, 0.35, -1.0)},
                                      {"lean": -0.06, "hx": -0.08}), until="figures", hold=0.2)
    at("Mostly", 127.8, lambda t, u, w: ({**arm(R, -0.6, 0.6, 0.35, -1.2)}, {"hy": 0.2}), until="felonies",
       hold=0.4, release=0.6)
    return link(G)


def bridge_gestures(W, B):
    """The Anchor, the bridge: a calm newsreader who gets more sedated every line. Gestures start
    crisp and professional and get slower, lower and lazier. She never looks at what she's
    presenting. Cue cards in her left hand the whole time."""
    G = []
    word, at, beat_pulse, per_beat, need_meat_proxy, robot, sign = authoring(W, B, G)

    # resting pose between gestures: both hands low in front, at desk height, holding the cards
    G.append(Gesture(129.0, 150.0, lambda t, u: ({**arm(R, -0.3, 0.2, -0.35, -1.3),
                                                  **arm(Lf, -0.3, 0.2, -0.35, -1.3)}, {}), attack=0.01))

    # --- line 1 (wide awake): "In other news tonight, the markets hit a record high"
    taps = [word("other", 129.8)["start"], word("news", 129.8)["start"]]

    def cards(t, u, w):   # squares the cue cards on the desk: two taps, glancing down at them
        tap = sum(math.exp(-((t - a - 0.05) / 0.1) ** 2) for a in taps)
        return ({**arm(R, -0.4 + 0.08 * tap, 0.22, -0.4, -1.4), **arm(Lf, -0.4 + 0.08 * tap, 0.22, -0.4, -1.4)},
                {"hx": 0.06 * (1 - smooth((t - taps[-1]) / 0.6))})
    at("In", 129.8, cards, until="news", hold=0.0, attack=0.4, release=0.7)
    at("tonight", 130.9, lambda t, u, w: ({**arm(R, -0.35, 0.4, 0.25, -1.1)}, {"hy": 0.03}), hold=0.0,
       attack=0.45, release=0.6)

    def climb(t, u, w):   # traces the stock line rising off the top of the chart (she doesn't look)
        e = smooth(u)
        return ({**arm(R, -0.3 - 0.5 * e, 0.35 + 0.1 * e, -0.15 + 0.35 * e, -1.2 + 0.4 * e)}, {})
    at("markets", 131.7, climb, until="high", hold=0.3, attack=0.5, release=0.8)

    # --- line 2 (one notch down): "Unemployment's down to zero, and nobody's asking why"
    at("Unemployment's", 134.1, lambda t, u, w: ({**arm(R, -0.5 + 0.2 * smooth(u), 0.35, 0.1, -1.35)}, {}),
       until="down", hold=0.0, attack=0.5)
    at("zero", 135.4, lambda t, u, w: ({**arm(R, -0.5 + 0.1 * math.cos(TAU * smooth(u)), 0.4,
                                              0.2 + 0.13 * math.sin(TAU * smooth(u)), -1.3)}, {}), pre=0.25, hold=0.0)
    at("nobody's", 136.4, lambda t, u, w: ({**arm(R, -0.2, 0.4, 0.3, -1.4), **arm(Lf, -0.2, 0.35, 0.2, -1.4)},
                                           {"hy": 0.08, "hz": 0.04}), until="why", hold=0.3, attack=0.8, release=0.9)

    # --- line 3 (half closed): "Our sponsors would like to remind you, everything is fine"
    at("sponsors", 138.6, lambda t, u, w: ({**arm(R, -0.2, 0.6, 0.35, -0.95)}, {"hy": 0.03}),
       hold=0.3, attack=0.7, release=0.9)
    at("remind", 140.2, lambda t, u, w: ({**arm(R, -0.6, 0.4, 0.12 + 0.05 * osc(t, 1.0), -1.65)}, {"hy": -0.03}),
       until="you", hold=0.1, attack=0.7, release=0.9)

    def fine(t, u, w):    # palms-down "it's all fine", patting slowly on the beats, a slow nod
        pat = beat_pulse(t, 0.3)
        return ({**arm(R, -0.3, 0.35, 0.15, -1.3 + 0.07 * pat), **arm(Lf, -0.3, 0.3, 0.1, -1.3 + 0.07 * pat)},
                {"hx": 0.03 * pat})
    at("everything", 141.3, fine, until="fine", hold=0.3, attack=0.8, release=0.9)

    # --- line 4 (barely awake): "Now please return to your station... and remain in line"
    at("please", 143.1, lambda t, u, w: ({**arm(R, -0.35 + 0.15 * smooth(u), 0.65, 0.4, -0.7)}, {"hy": 0.06}),
       until="station", hold=0.4, attack=1.0, release=1.0)
    at("and", 146.0, lambda t, u, w: ({**arm(R, -0.25, 0.2, -0.45, -1.4), **arm(Lf, -0.25, 0.2, -0.45, -1.4)},
                                      {"hx": 0.04}), until="line", hold=3.0, attack=1.0)
    off = word("line", 146.0)["start"] + 0.25

    def nod_off(t, u, w):  # eyes shut: the head sinks, catches itself a little, sinks again
        d = t - off
        sink = smooth(d / 1.2) * (1 - 0.25 * math.exp(-((d - 1.2) / 0.3) ** 2))
        return {}, {"hx": 0.25 * sink, "hy": 0.08 * smooth(d / 1.5)}
    G.append(Gesture(off, off + 3.0, lambda t, u: nod_off(t, u, None), attack=0.01, release=0.5))
    return link(G)


# ---------------------------------------------------------------- the parts
class Part:
    """One performance clip. intensity: [(time, level)] keyframes (0.2 nearly still, 0.45 chill,
    1 full out). chorus: where chorus grooves and the bigger head bob apply. drums: where feet
    stomp on kicks and the right hand comes down on snares. sway_end: the verse head sway fades
    out here. jumps: [(takeoff, landing, height)]. spins/freezes/stiff: functions of the words
    giving [(start, end, turns)], [(start, end)] and [(start, end)] (snappy robot arms).
    legs: False for a figure in a skirt (no knee bends or stomps). sedation: [(time, 0..1)]
    keyframes; sedated = lazier springs, weaker reactions to the beat, a drooping head. lids:
    [(time, notch)] eyelid drops (see lipsync_demo.animate_lids), or None for ordinary blinks.
    calm: 0..1, how composed the performer is overall: 1 = small, smooth, slow motion (beat
    reactions, joint speed, turning and head sway all scaled down)."""

    def __init__(self, figure, span, intensity, chorus, drums, sway_end, gestures, jumps=(),
                 spins=None, freezes=None, stiff=None, legs=True, sedation=((0, 0.0),), lids=None, calm=0.0):
        self.legs, self.sedation, self.lids, self.calm = legs, list(sedation), lids, calm
        self.figure, self.span, self.levels = figure, span, intensity
        self.chorus, self.drums, self.sway_end = chorus, drums, sway_end
        self.gestures, self.jumps = gestures, list(jumps)
        self.spins = spins or (lambda W: [])
        self.freezes = freezes or (lambda W: [])
        self.stiff = stiff or (lambda W: [])

    def intensity(self, t):
        return _keys(self.levels, t)

    def sedated(self, t):
        return _keys(self.sedation, t)

    def in_chorus(self, t):
        return self.chorus[0] <= t < self.chorus[1]


def _keys(pts, t):
    """Smoothly interpolated keyframes [(time, value)]."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, a), (t1, b) in zip(pts, pts[1:]):
        if t0 <= t < t1:
            return a + (b - a) * smooth((t - t0) / (t1 - t0))
    return pts[-1][1]


def _between(W, a, b, after, pad=(0.0, 0.0)):
    wa = W.find(a, after)
    return wa["start"] + pad[0], W.find(b, wa["start"])["end"] + pad[1]


PARTS = {
    # the Manager: verse 1 (chill) and chorus 1
    "v1c1": Part(
        "manager", (9.6, 66.6),
        [(0, 0.45), (36.6, 0.45), (37.2, 0.22), (40.3, 0.2), (41.4, 1.0), (63.3, 1.0), (63.8, 0.55),
         (65.4, 0.6), (65.6, 1.0), (99, 1.0)],
        chorus=(40.9, 66.2), drums=(41.3, 63.4), sway_end=40.4, gestures=v1c1_gestures,
        jumps=[(41.02, 41.40, 0.075), (65.12, 65.52, 0.085)],
        spins=lambda W: [(W.find("forsake", 56.0)["start"] + 0.35, W.find("forsake", 56.0)["start"] + 1.15, 1.0)],
        freezes=lambda W: [_between(W, "holding", "still", 47.0, (0.05, -0.02))],
        stiff=lambda W: [_between(W, "bot's", "assets", 48.7, (-0.1, 0.0))]),
    # the Founder: verse 2 (drums in, lounging swagger), spoken "Per division?", chorus 2, spoken
    "v2c2": Part(
        "founder", (66.4, 129.8),
        [(0, 0.6), (93.0, 0.6), (93.6, 0.25), (98.2, 0.25), (99.54, 1.0), (123.6, 1.0), (124.4, 0.3), (140, 0.3)],
        chorus=(98.9, 124.2), drums=(99.4, 125.0), sway_end=93.0, gestures=v2c2_gestures,
        jumps=[(99.16, 99.53, 0.075), (123.2, 123.56, 0.07)],
        spins=lambda W: [(W.find("sake", 114.0)["start"] + 0.06, W.find("sake", 114.0)["start"] + 0.86, 1.0)],
        freezes=lambda W: [(94.3, 95.1)],   # bar 43, the 2-beat bar under "Per division?": a hiccup
        stiff=lambda W: [_between(W, "bot", "laws", 106.5, (-0.1, 0.0))]),
    # the Anchor: the bridge, increasingly sedated; her eyelids drop a notch per line and close on "line"
    "bridge": Part(
        "anchor", (129.4, 148.6),
        [(0, 0.2), (134.0, 0.17), (138.6, 0.13), (143.0, 0.08), (147.2, 0.03), (150, 0.02)], calm=1.0,
        chorus=(1e9, 1e9), drums=(1e9, 1e9), sway_end=1e9, gestures=bridge_gestures, legs=False,
        sedation=[(0, 0.0), (133.9, 0.0), (134.5, 0.25), (138.4, 0.25), (139.0, 0.5), (142.8, 0.5),
                  (143.4, 0.75), (147.1, 0.8), (147.8, 1.0)],
        lids=lambda W: [(W.find("Unemployment's", 134.0)["start"], 1), (W.find("Our", 138.5)["start"], 2),
                        (W.find("Now", 142.9)["start"], 3), (W.find("line", 146.0)["start"] + 0.12, 4)]),
}
