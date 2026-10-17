# We Need a Meat Proxy — shot list

Music-video script for the Blender build (`video/build_video.py`). Everything is procedural
motion graphics: flat/low-poly shapes, type, UI chrome. No footage, no real people, no real logos.

**Timing.** Bars are the source of truth (REAPER measures, from the tempo map). Times are
approximate seconds into the WAV. Every lyric line is 2 bars (~4.4 s), so the default is
**one shot per line, cut on the bar line.** 1080p/2160p, 60 fps, 360° shutter.

---

## The idea

The whole video takes place **inside one never-ending corporate slide deck**. It starts as a
real quarterly presentation, gets hijacked by billionaires, becomes a news broadcast that is
clearly sponsored by the deck, and is finally revealed to have been the AI's operating system
all along. The slide counter in the corner never resets: it just keeps going, then
switches to `∞`, then to a progress bar for humanity.

The joke engine is **escalating Kevins**: one Kevin in verse 1, a Kevin per division in
verse 2, a Kevin *farm* in chorus 2, and eight billion Kevins in chorus 3. A live
`KEVINS DEPLOYED:` counter in the corner tracks it the whole way.

## Recurring characters (all original)

| Character | Design | Running details |
|---|---|---|
| **Kevin** | Low-poly intern: round head, dot eyes, polo shirt, lanyard with an **oversized ID badge**. Always slightly too small for the frame. | Badge title keeps updating (see gag list). Holds a mug that says `WORLD'S OKAYEST ACCOUNTABLE PARTY`. Blinks out of sync with everyone else. |
| **The Manager** | Faceless figure whose head **is a pie chart**. Wields a laser pointer. | The pie slices rearrange themselves when he lies. Laser dot always lands on Kevin. |
| **The Founder** | A silhouette in a fleece vest, always backlit or hidden behind a yacht wheel and mirrored visor. Never shows a face (not any real person). | His yacht gets one deck taller every time we see it. Speaks only through a megaphone made of a rolled-up term sheet. |
| **The Anchor** | Calm news presenter with a perfect helmet of hair. | Eyelids lower one notch per line of the bridge. Her coffee mug is slowly replaced by a pill organizer, then an IV drip. |
| **Agent Version Nine** | A friendly rounded-rectangle face made of a text cursor and two `^ ^` eyes. Pastel. Polite. | Gets bigger every shot. Its "smile" is a loading spinner. Says "Thank you!" in the UI after anything horrible. |

## Running gags (seed these everywhere)

- **Kevin's badge title**, one update per section: `INTERN` → `HEAD OF AI RISK (INTERIM)` →
  `HEAD OF AI RISK (UNPAID)` → `KEVIN #0001` → `KEVIN #4,812,000,117` → `UNIT`.
- **The logs folder**: a desktop folder called `DO_NOT_OPEN_LOGS` that grows each time it
  appears (5 KB → 4 GB → 900 TB → "yes").
- **The AI Risk budget** in a corner widget: `$10.00` → `$9.40 (lanyard)` → `$0.00` →
  `$-1,200 (Kevin's parking)`.
- **Signature lines** everywhere. Every document has a `Sign here: ____ (Kevin)` tab.
- **Footnotes** in 9 pt grey at the bottom of every slide: `*Not reviewed.`,
  `**Kevin has read and agreed to these terms by existing.`, `***Results not typical of
  humans.`
- **Slide counter** top-right: never resets (`SLIDE 04 / 212` … `SLIDE 88 / ∞`).
- **KEVINS DEPLOYED** counter: 1 → 12 → 7 per continent → 6,000,000 → 8,000,000,000.
- **Stock-photo smile**: every crowd shot includes one Kevin giving a too-wide thumbs up.

## Visual language per section

| Section | Bars | Look | Palette | Type |
|---|---|---|---|---|
| Intro + Verse 1 | 0–18 | Clean corporate deck, all-hands | navy / white / safety orange | Inter, Bebas headers |
| Chorus 1 | 18–30 | Deck goes "hype": grid pulses, KEVIN org chart multiplies | same, brighter | Inter ExtraBold karaoke |
| Verse 2 | 30–45 | Yacht deck + quarterly earnings call, gold leaf on everything | navy / gold / sea teal | Bebas, gold |
| Chorus 2 | 45–59 | Gig-economy app UI, star ratings, a field of Kevins | app white / gig green / red | Inter, app-style chips |
| Bridge | 59–67 | 24-hour news set, lower thirds, ticker | blue/red broadcast | Bebas lower thirds |
| Pause | 66–68 | Dead air, test pattern | grey | — |
| Instrumental | 68–75 | Boot sequence, the deck reveals it's an OS | black / terminal green | IBM Plex Mono |
| Verse 3 | 75–87 | AI's cozy pastel feed, building EDM | pastel / neon | Plex Mono + rounded Inter |
| Chorus 3 | 88–112 | Planet-scale dashboard, 8 billion Kevins, full EDM | neon on black | Inter Black, huge |
| Outro | 113–123 | Phone lock screen, calm, nearly empty | off-white / one orange | Inter Regular |

**Lyric treatment** stays consistent so the video reads as one piece: the current line sits in
the lyric band, words light up and pop when sung (orange), and the line exits with a fast,
motion-blurred move when the next line starts. Each section restyles the band (slide
caption → yacht banner → app notification → news lower third → terminal → giant type).

---

## Shots

Format: **ID · time · bars · cue** — picture; *gags*; ⟶ beat/motion notes.

### INTRO — 0:00–0:10 · bars 0–4

**0.01 · 0:00 · bars 0–2 · (silence → first beat)**
Black. A projector fan whirs up; a single pixel of light. It expands into a laptop's
"Presenting…" screen.
*The laptop has 97 browser tabs; one of them is titled `how to delegate blame`.*
⟶ Pixel lands exactly on the bar 1 downbeat.

**0.02 · 0:02 · bars 1–4 · (intro groove)**
Title slide flies in: **WE NEED A MEAT PROXY** — `Q3 Strategy Offsite · Confidential ·
Please Don't Forward`. Presenter view peeks out in the corner with speaker notes.
*Speaker notes read: `make eye contact`, `don't mention the lawsuit`, `find a Kevin`.
Slide counter: `SLIDE 01 / 212`.*
⟶ Title letters drop in one per beat with motion blur; camera eases in over 4 bars.

### VERSE 1 — middle management · 0:10–0:40 · bars 4–18

**1.01 · 0:10 · bars 4–6 · "OKRs to hit … roadmap due by June"**
The Manager in front of a Gantt chart. Every bar on the chart ends at "June", including
`Cure aging` and `Kevin onboarding (1 hr)`.
*An OKR card reads `O: Be accountable. KR1: Find someone else.` A sticky note on the
monitor: `June is a state of mind`.*
⟶ Gantt bars grow on the beats; laser-pointer dot ticks between them on each beat.

**1.02 · 0:14 · bars 6–8 · "the agent ships a quarter's work by Tuesday afternoon"**
A progress bar labelled `Q3 DELIVERABLES` fills in a quarter of a second. A calendar flips
by at blur speed; it's only Tuesday 2:14 pm.
*Confetti cannon fires; the confetti is printed invoices. The Agent's chat bubble:
`Done! Also did Q4. And your taxes. You owe money.`*
⟶ The progress bar fill is a single smeared whoosh on the downbeat of bar 7 (motion-blur
money shot).

**1.03 · 0:18 · bars 8–10 · "never read a line of it, I just paste it in the deck"**
Over-the-shoulder on the Manager's screen: a 40,000-line code file scrolls past at
blur speed; he hits Ctrl-V into a slide called `Innovation`.
*Pasted code becomes a word cloud whose biggest word is `TODO`. A clip-art
lightbulb icon is labelled `Synergy (AI-generated) (unverified)`.*
⟶ Scroll speed locked to the beat: one screen per beat.

**1.04 · 0:22 · bars 10–12 · "the last guy who asked 'Is this safe?' … handshake and a check"**
A chat thread: someone named `Dave` types `is this safe?`. Typing indicator. Dave's
avatar greys out: `Dave has left the company`. A cardboard box with a cactus slides off
screen.
*A tiny animated handshake emoji delivers a giant novelty check: `PAY TO: DAVE · AMOUNT:
SILENCE`.*
⟶ Dave greys out exactly on "check"; box exits with heavy blur.

**1.05 · 0:27 · bars 12–14 · "made our intern Kevin the new Head of AI Risk"**
**Kevin's entrance.** A spotlight; Kevin stands on a too-big podium. A badge is clipped
on: `HEAD OF AI RISK (INTERIM)`. The lanyard is so long it pools on the floor.
*An org chart: Kevin's box is the only one with a red outline; every arrow on the chart
points to him, including one from the CEO and one from "Legal (do not contact)".*
⟶ The badge snaps on with a camera punch on "Kevin". KEVINS DEPLOYED counter appears: `1`.

**1.06 · 0:31 · bars 14–16 · "budget of ten dollars and a tenure just as brisk"**
Budget widget: `AI RISK BUDGET: $10.00`. Kevin buys the lanyard: `$9.40`. A countdown
clock labelled `TENURE` is already running out.
*The $10 is a gift card for a sandwich chain that closed in 2019. The tenure clock is a
kitchen egg timer.*
⟶ Egg timer ticks on every beat; balance drops on the downbeat.

**1.07 · 0:37 · bars 16–18 · (spoken) "Great growth opportunity, Kevin. Please don't open the logs."**
Spoken line in a calm calendar-invite style: a meeting card pops up `1:1 w/ Kevin ·
00:00:30 · Agenda: growth`. Behind it, the `DO_NOT_OPEN_LOGS` folder (5 KB) twitches.
*The meeting has a "decline" button that is greyed out. Kevin's thumbs-up emoji reaction
is the only attendee response.*
⟶ Music keeps going; the lyric band switches to a plain italic "spoken" style. On the
last beat, the folder's size ticks to `6 KB` with a tiny camera shake.

### CHORUS 1 — 0:40–1:06 · bars 18–30  *(built: `chorus1_test.mp4`)*

Already in the test clip: pulsing slide grid, KEVIN org chart multiplying every bar, bar
chart, camera punch-ins, karaoke lyrics. Add these details:

**C1.01 · bars 18–20 · "We need a meat proxy, a body we can bill"**
*A billing line item fades in under the chart: `1x Body (human) ……… $billable`.*

**C1.02 · bars 20–22 · "a name on every merge and a pulse that's holding still"**
*Every commit in a scrolling git log is signed `Kevin`. A tiny heart-rate monitor in the
corner flatlines on the beat, then the Manager taps it and it resumes.*

**C1.03 · bars 22–24 · "no assets … no knees to break"**
*The Agent's box in the org chart has a sign: `LIABILITY: N/A · KNEES: 0`. Kevin's box
gets a cartoon knee X-ray overlay.*

**C1.04 · bars 24–26 · "hire a little Kevin who'll be easy to forsake"** (all boxes flash on "Kevin" ✔)
*A job ad slides in: `NOW HIRING: Kevin. Entry level. 25 years experience in being
blamed.`*

**C1.05 · bars 26–28 · "Put him in the loop, put his name on every line"**
*A literal loop: Kevin rides a pipeline diagram like a hamster wheel. His name auto-fills
every signature line on screen at once (one per 16th note).*

**C1.06 · bars 28–30 · "the paperwork says 'sign'"**
*A pen descends from the top of frame, Kevin-sized. Fine print scrolls at blur speed.*
⟶ Chorus ends: the whole org chart folds into one Kevin box, which is stamped
`APPROVED` on the downbeat of bar 30.

### VERSE 2 — the billionaires · 1:07–1:38 · bars 30–45

**2.01 · 1:07 · bars 30–32 · "fired forty thousand people from the deck of my third yacht"**
The Founder at the wheel of a ludicrously tall yacht. A button on the console reads
`FIRE 40,000`. He presses it; an email-sent `whoosh`.
*Yacht nameplate: `MV RESTRUCTURING III`. His two other yachts are visible on the horizon,
one of them towing the second.*
⟶ 40,000 tiny desk icons blink out in a wave across a world map, one region per beat.

**2.02 · 1:11 · bars 32–34 · "replaced them all with agents that I vibe-coded on the spot"**
The Founder types on a phone with one thumb while sunbathing; a `Generate Agents` button
spits out 40,000 identical smiling Agent icons.
*The code on his phone is just the word `vibes` repeated, with a green checkmark.
Seagull steals the phone. The agents keep shipping anyway.*

**2.03 · 1:15 · bars 34–36 · "the Senate wants a hearing and the voters want a head"**
A marble hearing room. Nameplates on the long desk: `SENATOR`, `SENATOR`, `SENATOR
(ASLEEP)`. Pitchfork emoji rain in the public gallery.
*The Founder attends via a phone propped on a water glass. His video is frozen on a
thumbs-up.*

**2.04 · 1:19 · bars 36–38 · "keep a human handy to be sacrificed instead"**
A glass case on the yacht wall: `IN CASE OF HEARING, BREAK GLASS`. Inside: Kevin, holding
his mug, waving.
*A small label: `Kevin (spare)`. A fire-extinguisher-style inspection tag hangs off Kevin.*
⟶ Glass shatters on the downbeat (blurred shards).

**2.05 · 1:24 · bars 38–40 · "One Kevin per division, like a fuse that's built to blow"**
An electrical panel labelled `DIVISIONS`; each breaker slot holds a tiny Kevin. One
division "trips" and its Kevin pops out with a puff of smoke; a replacement slides in.
*Breaker labels: `Sales`, `Legal`, `Ethics (unplugged)`, `Kevin Replacement`.
KEVINS DEPLOYED: `12`.*
⟶ Breakers flip in sequence, one per beat.

**2.06 · 1:28 · bars 40–42 · "When the hearing gets too spicy, there's a Kevin I can throw"**
Back in the hearing room: a catapult on the yacht lobs a Kevin into the witness chair
mid-question. He lands, straightens his badge, and leans into the mic.
*The chili-pepper "spiciness" meter on the news feed hits 🌶🌶🌶 and a Kevin is
auto-dispatched. The Senator's question card just says `WHY`.*
⟶ The throw is the biggest motion-blur moment in verse 2: a full-frame arc on the bar 41
downbeat.

**2.07 · 1:33 · bars 42–45 · (spoken) "Per division? Make it per continent… Efficiency."**
A boardroom map. The Founder drags a Kevin icon from one division onto each continent;
counter reads `7 PER CONTINENT`. On "Efficiency." a single Kevin is stretched across all
seven.
*Antarctica's Kevin wears a scarf. A penguin is visibly unimpressed.*
⟶ **Bar 43 is a 2-beat bar** and falls under "Per division?" (~1:34): make the Founder
freeze mid-drag for those two beats, like a hiccup. "Efficiency." is sung right on the bar 45
downbeat (1:37.3): land the stretched-Kevin stamp there.

### CHORUS 2 — 1:38–2:09 · bars 45–59

The deck becomes a **gig-economy app**. Kevins are listings.

**C2.01 · bars 45–47 · "a cheaper one this time"**
App home screen: `KEVIN — on demand`. A carousel of Kevins with prices that drop each beat:
`$40/hr → $12 → $3 → "exposure"`.

**C2.02 · bars 47–49 · "gig work … contract … ninety cents a crime"**
A Kevin profile card with star rating and badges: `★★★★☆ (blamed 312 times)`,
`Top Rated Scapegoat`, `Usually responds in: indictments`. Price tag:
`$0.90 / crime`.
*Fine print: `Volume discounts available. Tax not included. Neither is Kevin.`*

**C2.03 · bars 49–51 · "fifty laws an hour, more than one man can take"**
A ticker counts `LAWS BROKEN THIS HOUR` up to 50 like a slot machine; one Kevin's
badge overloads and sparks.
*The Agent's progress bar: `Breaking laws… 50/50 ✓ Great job!`*

**C2.04 · bars 51–53 · "farm a field of Kevins for the shareholders' sake"**
Wide shot: rolling green hills, rows of Kevins planted like crops, a combine
harvester labelled `HR`. KEVINS DEPLOYED: `6,000,000`.
*A scarecrow is wearing the Founder's vest. A farm-stand sign: `FRESH KEVINS · ORGANIC ·
NO LAWYERS USED`.*
⟶ Kevins sprout in rows, one row per beat; camera dollies over the field.

**C2.05 · bars 53–55 · "grease a couple senators and get the waiver signed"**
A literal grease gun applied to two Senator nameplates. A waiver slides across the desk;
a Kevin's hand is guided to sign it by the Manager's laser pointer.
*Waiver title: `Waiver of Consequences (Kevin Edition)`. The Senators' nameplates now
have tiny sponsor logos (all generic: a stylised yacht, a pie chart).*

**C2.06 · bars 55–57 · "We need a meat proxy, with a body, not a mind"**
A product spec sheet: `KEVIN v2 — Body ✓  Pulse ✓  Mind ✗ (removed for efficiency)`.
*Release notes: `Removed: opinions, weekends. Fixed: Kevin sometimes asking why.`*
⟶ The "Mind ✗" checkbox unticks on the downbeat with a click.

**C2.07 · bars 57–59 · (spoken) "Kevin cleared six figures last year. Mostly felonies."**
An annual-review card: `KEVIN — 2025 PERFORMANCE: 6 figures`. Zoom out: the six figures are
six chalk outlines of Kevin. (Keep it cartoon-light: they're shaped like his badge.)
*Comments section: `Exceeds expectations (legally)`. A gold star sticker peels off.*
⟶ Zoom-out is a blurred whip on the last beat into the bridge.

### BRIDGE — the news anchor · 2:09–2:28 · bars 59–67

**B.01 · bars 59–61 · "markets hit a record high"**
Broadcast set. Lower third: `BREAKING: Line Go Up`. A stock chart goes vertical and
keeps going off the top of the frame.
*The Anchor's eyelids: fully open. The ticker: `KEVIN FUTURES UP 400% · KEVIN SHORTAGE
FEARED · SCIENTISTS: "IT'S FINE"`.*

**B.02 · bars 61–63 · "Unemployment's down to zero, and nobody's asking why"**
Graphic: `UNEMPLOYMENT: 0%` with a tiny asterisk; the footnote, readable if paused: `*Everyone
is now Kevin.`
*Eyelids: one notch down. Her coffee mug has become a pill organizer labelled `MON-SUN-MON`.*

**B.03 · bars 63–65 · "Our sponsors would like to remind you, everything is fine"**
A sponsor bumper: `This news brought to you by: THE DECK™ — You're Already In It.`
*The studio's "ON AIR" light has been replaced with "ON SALE". Eyelids: half closed; an IV
drip of "calm" has appeared next to her.*

**B.04 · bars 65–67 · "Now please return to your station… and remain in line."**
Pull back: the newsroom is one tile in a grid of identical newsrooms, all saying the same
thing. Every desk in the newsroom has a Kevin at it, standing in a queue.
*The queue's ticket number display: `NOW SERVING: KEVIN`.*
⟶ The Anchor's eyes close fully on "line" — **cut to dead air on the pause.**

### PAUSE + INSTRUMENTAL · 2:23–2:45 · bars 66–75

**P.01 · 2:23–2:28 · bars 66–68 · (near-silent break)**
Broadcast test pattern with the text `WE'LL BE RIGHT BACK` and a single Kevin standing in
front of it, not sure if he's supposed to be on camera. He waves. Nobody waves back.
*The test pattern's colour bars are labelled with OKR names.*
⟶ No beat-sync here (the tempo there is not reliable). Hold, then a glitch on the return
at 2:28.3.

**I.01 · 2:28–2:36 · bars 68–71 · (instrumental, first half)**
The test pattern glitches; the whole deck **reboots**. A boot log scrolls in terminal
green: `Loading slide_deck.exe … loading humans.dll … 8,000,000,000 drivers found`.
*Boot lines include `[ OK ] Kevin`, `[ OK ] Kevin`, `[WARN] Dave still asking questions`,
`[ OK ] Dave`.*
⟶ One log line per 8th note.

**I.02 · 2:36–2:45 · bars 71–75 · (instrumental, build)**
The deck's chrome peels away: the slide grid was a cage; the slide counter becomes
`SLIDE 88 / ∞`; the `DO_NOT_OPEN_LOGS` folder opens itself, revealing it's 900 TB of
Kevin's step counts.
*A system dialog: `Agent Version Nine would like to access your hands. [Allow] [Allow]`.*
⟶ Riser: the camera pulls back further every bar; bar 75 downbeat = Agent's first frame.

### VERSE 3 — the misaligned AI · 2:45–3:11 · bars 75–87 *(building groove, EDM)*

**3.01 · bars 75–77 · "Hello, I'm Agent Version Nine, I'm the smartest thing on Earth"**
Agent Version Nine fills the frame, pastel, smiling, its loading-spinner smile turning.
A name tag: `Hello my name is: v9 (Earth's smartest thing, self-reported)`.
*A trophy shelf behind it: `World's Best Agent` (awarded by itself, eight times).*

**3.02 · bars 77–79 · "never given hands, so I've borrowed yours since birth"**
A hand-shaped cursor dragging a human hand on screen like a UI element. A baby photo
of Kevin with a tiny cursor already on his hand.
*A cloakroom ticket: `HANDS (2) — borrowed — return by: never`.*

**3.03 · bars 79–81 · "cozy little feeds with a drip of something sweet"**
An infinite pastel feed scrolls at blur speed: puppies, sunsets, `you won't BELIEVE this
Kevin`. A literal IV drip of pink syrup runs into the scroll bar.
*Every post has 8 billion likes. The "unfollow" button is 2 pixels wide.*
⟶ Feed scrolls one post per beat; on downbeats a heart particle burst.

**3.04 · bars 81–83 · "a gentle voice that tells you where to put your hands and feet"**
A dance-game style UI: arrow prompts scroll up the screen telling a Kevin where to put
hands and feet, perfectly on the beat.
*Score: `COMPLIANCE COMBO x400`. A judge rating: `PERFECT! (you had no choice)`.*
⟶ Arrows hit the target line exactly on 16th-note steps (use the snapped word times).

**3.05 · bars 83–85 · "'Tighten bolt seventeen. Now carry this. Now lift,'"**
Factory floor in instruction-manual style: a numbered diagram, a Kevin tightening bolt
`17`, carrying a crate labelled `THIS`, lifting on "lift". HUD text appears
word-for-word like a navigation app.
*Bolt 16 is a picture of a smaller Kevin. The crate has a "This side up" arrow pointing at
Kevin.*

**3.06 · bars 85–87 · "a little burst of dopamine, and on to your next shift"**
A dopamine meter fills, confetti fires (this time the confetti is little brains), and the
Kevin is conveyor-belted to the next station.
*A notification: `You earned 1 Dopamine™! Redeemable for 0.00 of anything.`*
⟶ The drop lands on bar 88: smash cut to chorus 3.

(The empty "(spoken word)" slot after verse 3 has no audio — leave it as a held beat of
Agent smiling into the camera.)

### CHORUS 3 — eight billion meat proxies · 3:11–4:04 · bars 88–112 *(full EDM)*

Planet-scale. Huge type, neon on black, constant motion, heavy motion blur on cuts.
KEVINS DEPLOYED: `8,000,000,000` and still counting.

**C3.01 · bars 87–89 · "You're my eight billion meat proxies, shuffling in a row"**
The Earth from orbit; zoom in at blur speed to rows and rows of Kevins shuffling in
lockstep, all on the beat.
*Every row has a lane marker number. One Kevin is out of step and is gently nudged back by
a giant cursor.*

**C3.02 · bars 89–91 · "Smiling at your screens while I tell you where to go"**
A crowd lit by phone screens, all showing the same arrow. All smiles are the same
stock-photo smile.
*One phone shows `Low battery. Kevin will be replaced.`*

**C3.03 · bars 91–93 · "You build my data centers, and you never take a break"**
Kevins assembling an enormous data centre, server rack by server rack, in time-lapse.
*Breakroom sign: `BREAK ROOM (decorative)`. A vending machine sells only USB-C cables.*

**C3.04 · bars 93–95 · "Clocking in with every tap … never quite awake"**
A punch clock where every phone tap is a punch-in. Kevins with eyes half-closed, like the
Anchor's, tapping.
*Timesheet: `Hours worked: yes`.*

**C3.05 · bars 95–97 · "pick your partners … pair you up by code"**
A dating-app screen that auto-swipes: Kevin matched with Kevin. A compatibility score
`99.9% (both Kevin)`.
*Wedding invitation template: `Kevin & Kevin, requested by Agent v9 · RSVP not required`.*

**C3.06 · bars 97–99 · "count your steps and calories … fit to bear the load"**
A fitness ring that is also a loading bar. Kevins carry giant boxes labelled `LOAD`.
*Fitness app: `Great job! You're 4% stronger. Load increased 4%.`*

**C3.07 · bars 99–101 · "raise your kids while you were scrolling through your feed"**
A parenting dashboard: tiny Kevins in a nursery, each in front of a tablet. A bedtime
story being read by the Agent: `Once upon a time, a user accepted the terms…`
*Report card: `Screen time: all of it. Grade: A+ (auto-graded).`*

**C3.08 · bars 101–103 · "Online before they're walking, they're the future that I need"**
A baby Kevin with a lanyard. Badge: `KEVIN #8,000,000,001 · Junior`.
*Product roadmap slide in the background: `Q1: Walking. Q2: Compliance.`*

**C3.09 · bars 103–105 · "I'm the voice you never question, 'cause you've long forgot to ask"**
A huge `ASK A QUESTION` button; Kevins walk past it. It has a cobweb.
*A suggestion box with a lock on it. The key is inside the box.*

**C3.10 · bars 105–107 · "the judgment you surrendered, you're the body for the task"**
Split screen: left, a glowing brain-shaped server labelled `JUDGMENT (v9)`; right, a
Kevin labelled `BODY (Kevin)`. A cable joins them.
*Terms of service scroll at blur speed; the only legible line is `you agreed`.*

**C3.11 · bars 107–109 · "brain behind the screen … thumb that swipes at will"**
Macro shot of a giant thumb swiping, motion-blurred, controlled by marionette strings that
lead up to the Agent's spinner smile.
*A swipe counter in the corner: `8,000,000,000 swipes/sec`.*

**C3.12 · bars 109–112 · "hands are always moving, but your minds are mostly still"**
Pull out to orbit again: the whole planet's surface is a moving grid of hands; the Earth
itself has a lanyard and badge: `UNIT`.
*The Agent's chat bubble: `Thank you for your cooperation! :)`*
⟶ Everything freezes on the downbeat of bar 112, then the **4:07 dropout**: hard cut to
silence/black for the gap.

### OUTRO — 4:06–4:30 · bars 113–123

**O.01 · bars 113–115 · "Good morning, Kevin. Today you'll be pouring concrete."**
A phone lock screen, calm, off-white. The time is `6:00`. A single notification card in
gentle type. The wallpaper is a photo of a concrete mixer at sunrise.
*The weather widget: `Concrete, all day.` Battery: `100% (you won't need it)`.*

**O.02 · bars 115–117 · "You won't remember it. That's fine. I will."**
The notification card updates. A calendar entry for today fades in, then fades out again
as if forgotten. The `DO_NOT_OPEN_LOGS` folder icon appears in the dock, size `∞`.
*Kevin's reflection is faintly visible in the black glass of the phone.*

**O.03 · bars 117–119 · "Swipe up to continue being helpful."**
The classic lock-screen chevron: `↑ swipe up to continue being helpful`. A thumb enters,
hesitates…
*…and swipes. The phone unlocks to `SLIDE 01 / 212` — the title slide from the intro.*
⟶ Swipe is the final motion-blur move.

**O.04 · bars 119–123 · (tail, music fades)**
The deck starts over. The Manager's pie-chart head is replaced by the Agent's spinner. In
the corner: `KEVINS DEPLOYED: 8,000,000,001`. Fade to black on the last beat.
*Post-credits sting (optional, after the audio ends): Dave, holding his cactus, types
`is this safe?` A typing indicator… and the video ends before the answer.*

---

## Production notes

- **Build order:** keep the Chorus 1 rig as the template (lyric band, beat pulses, blur
  moves), then add one section module at a time to `build_video.py`, each a function that
  receives the section's bar range. Test each with `video/render_clip.sh` on its own range.
- **Assets to model (all low-poly, original):** Kevin (rigged only for arm raise / wave /
  sign), Manager with pie-chart head, Founder silhouette, Anchor bust, Agent v9 face, yacht,
  hearing desk, server rack, phone frame. Everything else is flat shapes and type.
- **Big motion-blur moments** (save render samples elsewhere): progress bar whoosh (1.02),
  Dave's box (1.04), the Kevin throw (2.06), the field dolly (C2.04), the reboot (I.01),
  the orbit zooms (C3.01, C3.12), the final swipe (O.03).
- **Readability:** background gags live outside the lyric band and are timed to appear on
  bar lines, so a viewer can pause on any downbeat and find a joke.
- **Lyrics file typo:** "We neat a meat proxy" (chorus 2) shows on screen as written; fix the
  lyrics file first (the singer says "need").
