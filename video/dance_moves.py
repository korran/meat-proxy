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
    need_meat_proxy(119.9)
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


V3C3_WAILS = [("feed", 221.5), ("need", 225.5), ("ask", 230.2), ("task", 234.5), ("will", 239.0)]


def v3c3_gestures(W, B):
    """Agent Version Nine, verse 3 and chorus 3. It has no arms, so it acts everything out with
    its body, legs and screen head: head tilts, turns and pops, leans, marching and shuffling
    steps, crouches. Its screen expressions are in V3C3_FACES."""
    G = []
    word, at, beat_pulse, per_beat, *_ = authoring(W, B, G)

    def body(fn):
        """A gesture made only of offsets (no arm targets)."""
        return lambda t, u, w: ({}, fn(t, u))

    def march(t, amount=1.0, rate=1):
        """Knees lift alternately, one step per beat (rate=2: per 8th)."""
        k = B.at(t)[0] * rate
        leg, ph = int(k) % 2, k % 1
        lift = math.sin(math.pi * ph) ** 2 * amount
        return {f"knee{leg}": 0.55 * lift, f"hipf{leg}": 0.3 * lift}

    # --- verse 3, line 1: "Hello, I'm Agent Version Nine, I'm the smartest thing on Earth"
    at("Hello", 163.0, body(lambda t, u: {"hy": 0.2 * osc(t, 1.8), "roll": 0.04 * osc(t, 1.8)}), pre=0.3, hold=0.1)
    at("Agent", 164.8, body(lambda t, u: {"lean": -0.08, "hx": -0.12}), until="Nine", hold=0.1)
    at("smartest", 166.5, body(lambda t, u: {"lean": -0.12, "hx": -0.1, "hy": 0.12}), until="thing", hold=0.0)
    # line 2: "But I was never given hands, so I've borrowed yours since birth"  (looks for its arms)
    at("never", 169.4, body(lambda t, u: {"hz": 0.45 * math.sin(TAU * smooth(u)), "hx": 0.1}), until="hands",
       hold=0.2, attack=0.3)
    at("borrowed", 170.8, body(lambda t, u: {"lean": 0.12, "hx": 0.06, "hy": -0.12}), until="birth", hold=0.2)
    # line 3: "I built you cozy little feeds with a drip of something sweet"
    at("cozy", 173.8, body(lambda t, u: {"roll": 0.05 * osc(t, 0.45), "hy": 0.16 * osc(t, 0.45)}), until="feeds",
       hold=0.1, attack=0.4)
    at("drip", 175.7, body(lambda t, u: {"hx": 0.1, "hy": 0.2, "lean": -0.04}), until="sweet", hold=0.2)
    # line 4: "And a gentle voice that tells you where to put your hands and feet"
    at("gentle", 177.6, body(lambda t, u: {"hy": 0.14, "hz": -0.1}), until="voice", hold=0.1, attack=0.4)
    at("put", 180.0, body(lambda t, u: {**march(t, 1.0), "hx": 0.06}), until="feet", hold=0.1)
    # line 5: "Tighten bolt seventeen. Now carry this. Now lift,"  (a ratchet, a heavy load, a hop)
    at("Tighten", 181.0, body(lambda t, u: {"hz": 0.14 * (int(B.at(t)[0] * 2) % 4) - 0.2, "hx": 0.08}),
       until="seventeen", hold=0.0)
    at("carry", 184.0, body(lambda t, u: {"lean": -0.1, "knee0": 0.3, "knee1": 0.3, "hx": -0.05}), until="this",
       hold=0.0)
    # line 6: "Then a little burst of dopamine, and on to your next shift."
    at("burst", 186.6, body(lambda t, u: {"croll": 0.08 * osc(t, 6.0), "hx": -0.08, "hy": 0.1 * osc(t, 3.0)}),
       until="dopamine", hold=0.1)
    at("next", 189.6, body(lambda t, u: {"hz": 0.4, "hy": -0.08}), until="shift", hold=0.2)

    # --- chorus 3 (full EDM): "You're my eight billion meat proxies, shuffling in a row"
    at("eight", 191.8, body(lambda t, u: {"hx": 0.15 * beat_pulse(t), "lean": 0.05}), until="proxies", hold=0.0)
    at("shuffling", 193.6, body(lambda t, u: {**march(t, 0.8, 2), "rx": 0.03 * osc(t, per_beat(t) / 2)}),
       until="row", hold=0.1)
    at("Smiling", 196.1, body(lambda t, u: {"hy": 0.18 * osc(t, per_beat(t) / 4)}), until="screens", hold=0.0)
    at("tell", 198.6, body(lambda t, u: {"hz": 0.35 * (1 if int(B.at(t)[0]) % 2 else -1)}), until="go", hold=0.1)
    # "You build my data centers, and you never take a break"
    at("build", 200.3, body(lambda t, u: {**march(t, 1.0), "hz": 0.2 * (1 if int(B.at(t)[0]) % 2 else -1)}),
       until="centers", hold=0.0)
    at("never", 202.5, body(lambda t, u: {"hz": 0.3 * osc(t, 2.5)}), until="break", hold=0.1)
    # "Clocking in with every tap, and you're never quite awake"
    at("Clocking", 204.9, body(lambda t, u: {"hx": 0.13 * beat_pulse(t)}), until="tap", hold=0.0)
    at("quite", 207.0, body(lambda t, u: {"hx": 0.18 * smooth(u), "hy": 0.15 * smooth(u)}), until="awake", hold=0.2)
    # "You let me pick your partners, now I pair you up by code"
    at("pick", 209.4, body(lambda t, u: {"hy": 0.15 * osc(t, per_beat(t) / 2), "roll": 0.03 * osc(t, per_beat(t) / 2)}),
       until="code", hold=0.1)
    # "And I count your steps and calories, so you're fit to bear the load"
    at("count", 213.6, body(lambda t, u: {**march(t, 1.0)}), until="calories", hold=0.0)
    at("fit", 215.7, body(lambda t, u: {"knee0": 0.45, "knee1": 0.45, "lean": 0.15, "hx": 0.1}), until="load",
       hold=0.1)
    # --- second half (bar 100 on): a rock singer. Head-banging on every beat comes from the
    # engine (Part.rock); here it leans into the mic on the lines and throws its head back to wail
    # the held notes at the ends of lines (V3C3_WAILS, where the head-banging pauses).
    def into_mic(t, u):
        return {"lean": 0.16, "hx": 0.08, "knee0": 0.2, "knee1": 0.2}

    def wail(t, u):
        return {"lean": -0.2, "hx": -0.32, "hy": 0.1 * osc(t, 0.8), "knee0": 0.35, "knee1": 0.35}

    for a_, b_, after in (("raise", "kids", 218.5), ("voice", "question", 226.8), ("judgment", "surrendered", 231.0)):
        at(a_, after, body(into_mic), until=b_, hold=0.0, attack=0.15)
    for w_, after in V3C3_WAILS:
        at(w_, after, body(wail), pre=0.12, hold=0.15, attack=0.12, release=0.3)
    at("thumb", 237.4, body(lambda t, u: {"hz": 0.45 - 0.9 * smooth(u), "croll": 0.04}), until="swipes", hold=0.0)
    at("hands", 239.9, body(lambda t, u: {**march(t, 1.0, 2), "lean": 0.1}), until="moving", hold=0.0)
    at("minds", 241.9, body(lambda t, u: {"hy": 0.15, "hx": -0.05}), until="still", hold=2.0)
    return link(G)


def v3c3_faces(W):
    """v9's screen expressions: happy ^ ^ unless set here (smug > <, round o o, heart)."""
    def span(a, b, after, face, pad=0.1):
        wa = W.find(a, after)
        return (wa["start"] - pad, W.find(b, wa["start"])["end"] + pad, face)
    return [span("smartest", "Earth", 167.0, "smug"),
            span("never", "hands", 169.4, "round"),
            span("drip", "sweet", 175.7, "heart"),
            span("Tighten", "seventeen", 181.0, "smug"),
            span("dopamine", "dopamine", 187.0, "heart"),
            span("eight", "proxies", 191.8, "round"),
            span("quite", "awake", 207.0, "smug"),
            span("partners", "code", 209.4, "heart"),
            span("future", "need", 224.6, "smug"),
            span("forgot", "ask", 229.4, "round"),
            span("judgment", "task", 231.1, "smug"),
            span("brain", "screen", 235.4, "round"),
            span("still", "still", 243.0, "smug", 0.3)]


# ---------------------------------------------------------------- the end credits (no words: on the beat)
def _beat(B, t):
    """(beat index in the bar 0..3, phase 0..1 through the beat)."""
    k, ph, bar, bi, blen = B.at(t)
    return bi, ph


def _snap(ph, into=0.22):
    """0 -> 1 over the start of the beat (each move lands on the beat, then holds)."""
    return smooth(min(1.0, ph / into))


def _pulse(ph, width=0.18):
    """1 right on the beat, falling off quickly."""
    d = min(ph, 1 - ph)
    return math.exp(-(d / width) ** 2)


def _mix(a, b, u):
    return {c: a[c] * (1 - u) + b[c] * u for c in a}


def credits_manager_gestures(W, B):
    """The Manager, corporate-party energy: raise the roof, the disco point, the sprinkler, a point
    at the screen when the Song Demo credit comes up, overhead claps; a jump onto the last downbeat."""
    G = []

    def roof(t, u):           # both hands up, pushing at the ceiling on every beat
        bi, ph = _beat(B, t)
        p = _pulse(ph)
        return ({**arm(R, -2.35 - 0.35 * p, 0.35, 0.1, -1.1 + 0.35 * p),
                 **arm(Lf, -2.35 - 0.35 * p, 0.35, 0.1, -1.1 + 0.35 * p)}, {"hx": -0.06 * p})
    G.append(Gesture(259.15, 261.3, roof, attack=0.15, release=0.25))

    def disco(t, u):          # right arm: up-and-out on 1 and 3, down-and-across on 2 and 4; hand on hip
        bi, ph = _beat(B, t)
        up = arm(R, -2.75, 0.55, 0.35, -0.05)
        down = arm(R, -0.35, 0.15, -0.45, -0.05)
        a, b = (down, up) if bi % 2 == 0 else (up, down)
        return ({**_mix(a, b, _snap(ph)), **arm(Lf, -0.15, 0.55, 0.0, -1.7)},
                {"hy": 0.08 * (1 if bi % 2 == 0 else -1) * _snap(ph)})
    G.append(Gesture(261.35, 263.5, disco, attack=0.12, release=0.2))

    def sprinkler(t, u):      # left hand behind his head, right arm ticking across in eighths, then back
        bi, ph = _beat(B, t)
        step = int((bi + ph) * 2) % 8
        z = -0.55 + 1.1 * step / 7
        return ({**arm(R, -1.45, 0.35, z, -0.15), **arm(Lf, -2.5, 0.45, 0.5, -2.2)}, {"yaw": 0.25 * z})
    G.append(Gesture(263.55, 265.6, sprinkler, attack=0.15, release=0.2))

    def point(t, u):          # points at the screen (on his left) as the Song Demo credit comes up
        return ({**arm(Lf, -1.55, 0.95, 0.0, -0.05), **arm(R, -0.2, 0.3, 0.0, -1.5)}, {"yaw": -0.3, "hz": -0.15})
    G.append(Gesture(265.75, 266.75, point, attack=0.12, release=0.3))

    def claps(t, u):          # hands together over his head on 2 and 4
        bi, ph = _beat(B, t)
        c = _pulse(ph, 0.12) if bi % 2 == 1 else 0.0
        return ({**arm(R, -2.85, 0.45 - 0.35 * c, 0.0, -0.35), **arm(Lf, -2.85, 0.45 - 0.35 * c, 0.0, -0.35)},
                {"hx": -0.08})
    G.append(Gesture(266.8, 268.3, claps, attack=0.2, release=0.4))
    return G


def credits_founder_gestures(W, B):
    """The Founder, older and cooler: a shoulder shimmy with finger guns, a spin into hands-in-the-air
    sways, a point at the screen when the AI Life Coach credit comes up, then alternating fist pumps."""
    G = []

    def guns(t, u):           # finger guns out front, shoulders shimmying
        bi, ph = _beat(B, t)
        p = _pulse(ph)
        return ({**arm(R, -1.35 - 0.15 * p, 0.25, -0.25, -0.55), **arm(Lf, -1.35 - 0.15 * p, 0.25, -0.25, -0.55)},
                {"croll": 0.1 * math.sin(TAU * 4 * t), "hy": 0.06 * math.sin(TAU * 0.9 * t)})
    G.append(Gesture(259.15, 261.2, guns, attack=0.15, release=0.25))

    def air(t, u):            # hands in the air, swaying with the half-time pulse
        bi, ph = _beat(B, t)
        sw = math.sin(math.pi * (bi + ph) / 2)
        return ({**arm(R, -2.7, 0.55, 0.3 * sw, -0.25), **arm(Lf, -2.7, 0.55, -0.3 * sw, -0.25)},
                {"roll": 0.07 * sw, "hy": 0.1 * sw})
    G.append(Gesture(262.0, 264.6, air, attack=0.3, release=0.25))

    def point(t, u):          # points at the screen (on his right) as the AI Life Coach credit comes up
        return ({**arm(R, -1.55, 0.95, 0.0, -0.05), **arm(Lf, -0.2, 0.3, 0.0, -1.5)}, {"yaw": 0.3, "hz": 0.15})
    G.append(Gesture(264.65, 265.65, point, attack=0.12, release=0.3))

    def pumps(t, u):          # fist pumps, alternating hands on each beat
        bi, ph = _beat(B, t)
        p = _pulse(ph, 0.2)
        hi, lo = (R, Lf) if bi % 2 == 0 else (Lf, R)
        return ({**arm(hi, -2.4 - 0.3 * p, 0.3, 0.0, -0.4 + 0.25 * p), **arm(lo, -0.6, 0.25, 0.0, -1.6)},
                {"hx": -0.05 * p})
    G.append(Gesture(265.8, 268.3, pumps, attack=0.2, release=0.4))
    return G


def credits_v9_gestures(W, B):
    """v9 (no arms): head pops side to side on the beat, a little lean on the snares."""
    G = []

    def pops(t, u):
        bi, ph = _beat(B, t)
        side = 1 if bi % 2 == 0 else -1
        return ({}, {"hy": 0.16 * side * _snap(ph, 0.15), "hz": 0.1 * side * _snap(ph, 0.15)})
    G.append(Gesture(259.15, 263.4, pops, attack=0.15, release=0.3))
    G.append(Gesture(265.0, 268.3, pops, attack=0.3, release=0.4))
    return G


def outro_faces(W):
    """v9's morning monologue on Kevin's phone: calm, sweet, a little smug."""
    def span(a, b, after, face, pad=0.12):
        wa = W.find(a, after)
        return (wa["start"] - pad, W.find(b, wa["start"])["end"] + pad, face)
    return [span("pouring", "concrete", 248.0, "smug"),
            span("remember", "it", 250.5, "round"),
            (W.find("That's", 252.0)["start"] - 0.1, W.find("I", 252.8)["start"] - 0.2, "closed"),
            span("I", "will", 252.8, "smug", 0.15),
            span("helpful", "helpful", 258.0, "heart", 0.3)]


def outro_gestures(W, B):
    """v9 alone in the void, talking to Kevin through his phone: composed and still, just small
    head tilts and nods (no arms)."""
    G = []
    word, at, *_ = authoring(W, B, G)

    def tilt(hy=0.0, hx=0.0, lean=0.0):
        return lambda t, u, w: ({}, {"hy": hy, "hx": hx, "lean": lean})
    at("morning", 246.0, tilt(hy=0.13), until="Kevin", hold=0.4, attack=0.35, release=0.7)       # a fond tilt
    at("Kevin", 246.5, tilt(hx=0.07), hold=0.1, attack=0.2, release=0.4)                         # a little nod
    at("pouring", 248.0, tilt(hy=-0.06, hx=0.04), until="concrete", hold=0.3)
    at("won't", 250.5, tilt(hy=-0.12), until="it", hold=0.3, attack=0.35, release=0.6)
    at("fine", 252.2, tilt(hx=0.1), hold=0.1, attack=0.25, release=0.5)                         # a slow nod
    at("I", 252.8, tilt(hx=-0.05, lean=0.07), until="will", hold=0.8, attack=0.2, release=0.9)   # leans in
    at("up", 255.0, tilt(hx=-0.14), hold=0.6, attack=0.3, release=0.9)                          # looks up
    at("helpful", 258.0, tilt(hy=0.1), hold=1.5, attack=0.4, release=1.2)
    return G


# ---------------------------------------------------------------- the parts
class Part:
    """One performance clip. intensity: [(time, level)] keyframes (0.2 nearly still, 0.45 chill,
    1 full out). chorus: where chorus grooves and the bigger head bob apply. drums: where feet
    stomp on kicks and the right hand comes down on snares. sway_end: the verse head sway fades
    out here. jumps: [(takeoff, landing, height)]. spins/freezes/stiff: functions of the words
    giving [(start, end, turns)], [(start, end)] and [(start, end)] (snappy robot arms).
    legs: "adult", "kid" (short legs) or None for a figure in a skirt (no knee bends or stomps).
    arms: False for an armless figure (the snare pops its head instead). faces: for a screen
    face (v9), [(start, end, expression)] from the words. sedation: [(time, 0..1)]
    keyframes; sedated = lazier springs, weaker reactions to the beat, a drooping head. lids:
    [(time, notch)] eyelid drops (see lipsync_demo.animate_lids), or None for ordinary blinks.
    calm: 0..1, how composed the performer is overall: 1 = small, smooth, slow motion (beat
    reactions, joint speed, turning and head sway all scaled down). rock: (start, end) of
    rock-singer mode (head-banging on every beat); rock_holds(W): [(start, end)] where the
    head-banging pauses."""

    def __init__(self, figure, span, intensity, chorus, drums, sway_end, gestures, jumps=(),
                 spins=None, freezes=None, stiff=None, legs="adult", sedation=((0, 0.0),), lids=None, calm=0.0,
                 arms=True, faces=None, rock=None, rock_holds=None, seed=7):
        self.seed = seed                       # picks its sequence of grooves (phrase_plan)
        self.rock, self.rock_holds = rock, rock_holds or (lambda W: [])
        self.legs, self.sedation, self.lids, self.calm = legs, list(sedation), lids, calm
        self.arms, self.faces = arms, faces or (lambda W: [])
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
        chorus=(1e9, 1e9), drums=(1e9, 1e9), sway_end=1e9, gestures=bridge_gestures, legs=None,
        sedation=[(0, 0.0), (133.9, 0.0), (134.5, 0.25), (138.4, 0.25), (139.0, 0.5), (142.8, 0.5),
                  (143.4, 0.75), (147.1, 0.8), (147.8, 1.0)],
        lids=lambda W: [(W.find("Unemployment's", 134.0)["start"], 1), (W.find("Our", 138.5)["start"], 2),
                        (W.find("Now", 142.9)["start"], 3), (W.find("line", 146.0)["start"] + 0.12, 4)]),
    # the end credits on the yacht, when the music comes back up after the monologue: the Manager
    # and the Founder dance either side of the LED wall, v9 dances on it
    **{f"credits_{who}": Part(
        who, (259.2, 269.56), [(0, 1.15), (268.2, 1.15), (268.7, 0.25), (270.0, 0.2)],
        chorus=(259.0, 268.5), drums=(259.0, 268.5), sway_end=259.0,       # (stomps on the kicks throughout)
        gestures=gest, jumps=jumps, spins=lambda W, sp=spins: sp, seed=seed,
        legs="kid" if who == "v9" else "adult", arms=who != "v9",
        faces=(lambda W: [(264.6, 270.0, "heart")]) if who == "v9" else None)     # hearts: the human credits
       for who, gest, jumps, spins, seed in (
           ("manager", credits_manager_gestures, [(267.75, 267.99, 0.07)], [], 11),
           ("founder", credits_founder_gestures, [], [(261.3, 262.0, 1.0)], 23),
           ("v9", credits_v9_gestures, [(260.15, 260.4, 0.05), (262.35, 262.6, 0.05), (266.95, 267.2, 0.06)],
            [(263.5, 264.25, -1.0)], 31))},
    # Agent Version Nine on Kevin's phone in the outro: a calm spoken monologue
    "outro": Part(
        "v9", (245.6, 269.56), [(0, 0.15), (260.0, 0.12), (270.0, 0.1)], calm=1.0,
        chorus=(1e9, 1e9), drums=(1e9, 1e9), sway_end=1e9, gestures=outro_gestures,
        legs="kid", arms=False, faces=outro_faces),
    # Agent Version Nine: verse 3 (EDM building) and chorus 3 (full EDM); no arms, a screen face
    "v3c3": Part(
        "v9", (162.6, 245.6),
        [(0, 0.5), (186.0, 0.65), (190.6, 0.7), (191.5, 1.0), (217.3, 1.0), (217.7, 1.2), (243.6, 1.2),
         (244.2, 0.4)],
        chorus=(191.2, 243.8), drums=(191.4, 243.6), sway_end=191.2, gestures=v3c3_gestures,
        jumps=[(185.45, 185.81, 0.06),          # a hop on "Now lift"
               (191.08, 191.44, 0.07),          # onto the drop
               (225.93, 226.29, 0.08),          # rock jumps onto the bar 104 and 108 downbeats
               (234.63, 234.99, 0.08)],
        spins=lambda W: [(W.find("Earth", 168.0)["start"] - 0.05, W.find("Earth", 168.0)["start"] + 0.75, 1.0),
                         (W.find("thumb", 237.4)["start"] - 0.1, W.find("thumb", 237.4)["start"] + 0.7, -1.0)],
        freezes=lambda W: [(243.7, 246.0)],     # freeze on the bar 112 downbeat
        stiff=lambda W: [],
        legs="kid", arms=False, faces=v3c3_faces,
        rock=(217.59, 243.6),                   # bar 100 to the end: a rock singer
        rock_holds=lambda W: [(W.find(w, a)["start"] - 0.15, W.find(w, a)["end"] + 0.25) for w, a in V3C3_WAILS]),
}
