# We Need a Meat Proxy — shot list

Music-video script for the Blender build (`video/build_video.py`). Everything is procedural
motion graphics: flat/low-poly shapes, type, UI chrome. No footage, no real people, no real logos.

**Timing.** Bars are the source of truth (REAPER measures, from the tempo map). Times are
approximate seconds into the WAV. Every lyric line is 2 bars (~4.4 s), so the default is
**one shot per line, cut on the bar line.** 1080p/2160p, 60 fps, 360° shutter.

---

## The idea

The whole video takes place **on one screen that never turns off**. It starts as a quarterly
slide deck, gets screen-shared into a billionaire's yacht livestream, becomes a news broadcast
sponsored by the deck, and is finally revealed to be Agent Version Nine's operating system. The
slide counter in the corner never resets: `SLIDE 01 / 212` … `SLIDE 88 / ∞`. The last shot
swipes back to the title slide, so the video loops.

**Two halves.** Before the reboot (intro to the bridge), the jokes are about **escalating
Kevins**: one intern, a Kevin per division, a Kevin farm. A `KEVINS DEPLOYED` counter tracks it.
After the reboot (instrumental to the outro), the AI turns to the camera and talks to
**everyone**, and the jokes are about **lazy humans** who handed over their hands, their
judgment and their kids because it was easier than not doing it. The counter becomes
`MEAT PROXIES: 8,000,000,000`. Kevin is off screen for the whole second half.

**Kevin's throughline.** In the first half Kevin is the only person who wants to check the
work: he keeps reaching for the `DO_NOT_OPEN_LOGS` folder and keeps getting stopped. He comes
back only in the very last shot, and by then he's on the couch like everyone else, watching the
deck start over.

## Ground rules

1. **Everything is a screen.** Every shot is a slide, an app, a video call, a game, a broadcast
   or an OS window. The yacht and the Senate are video-call tiles; the Kevin field is a farming
   game; the Earth is a dashboard widget. This keeps the premise intact and the builds cheap.
2. **One hero joke per shot (★)**, readable in about two seconds while the lyrics run. Everything
   else is **pause bait** (small text for people who freeze the frame). Hero jokes appear on a
   bar line; pause bait can arrive any time.
3. **Add a turn, don't just illustrate.** The lyric says the thing; the picture adds a second idea.
4. **Kevin is never upset.** He is eager, polite and slightly too small for every frame. The
   comedy is everyone else's casual cruelty, not his suffering.

## Recurring characters (all original)

| Character | Design | Running details |
|---|---|---|
| **Kevin** | A kid figure (short legs): printed eager face, cowlick, steak t-shirt, a lanyard so long the giant badge hangs at his knees. | Badge title updates per section. Mug: `WORLD'S OKAYEST ACCOUNTABLE PARTY`. Keeps eyeing the logs folder. |
| **The Manager** | Suit, red tie, neat side-parted hair, a wide salesy grin; laser pointer. | The grin gets wider the worse the news. The laser dot always ends up on Kevin. |
| **The Founder** | **The Manager, ten years later** (same singer, same guy): same grin and haircut, now silver, a mirrored visor over his eyes, fleece vest and chinos. Not any real person. | Always on a yacht that is one deck taller than last time. Never looks at what he taps. |
| **The Anchor** | Calm news presenter, perfect helmet of hair. | Eyelids drop one notch per line of the bridge. |
| **Agent Version Nine (v9)** | Friendly pastel rounded rectangle; eyes `^ ^`, its smile is a loading spinner. | Gets bigger every time we see it. Says "Thank you!" after anything horrible. |
| **The Users** (second half) | Identical figures in grey hoodies with the hood up, half-lidded eyes, pink slippers, faces lit by a phone; usually sitting on a brick sofa. | Never stand up if they can avoid it. Tap "Yes" to everything. Eyelids at the Anchor's last notch. |

**Kevin's badge title** (first half only): `INTERN` → `HEAD OF AI RISK (INTERIM)` →
`KEVIN (SPARE)` → `KEVIN — ON DEMAND`.

**Corner widgets** (always on, top right): slide counter, `KEVINS DEPLOYED` (becomes
`MEAT PROXIES` after the reboot), and in verse 1 the `AI RISK BUDGET`.

## Visual language per section

| Section | Bars | Screen | Palette | Type |
|---|---|---|---|---|
| Intro + Verse 1 | 0–18 | Slide deck, all-hands | navy / white / safety orange | Inter, Bebas headers |
| Chorus 1 | 18–30 | Same deck, hyped: pulsing grid, KEVIN org chart | same, brighter | Inter ExtraBold karaoke |
| Verse 2 | 30–45 | Video call: Founder's yacht livestream + Senate hearing tiles | navy / gold / sea teal | Bebas, gold |
| Chorus 2 | 45–59 | Gig-economy app, then a farming game | app white / gig green | Inter, app chips |
| Bridge | 59–67 | 24-hour news broadcast | broadcast blue/red | Bebas lower thirds |
| Pause | 66–68 | Dead air, test pattern | grey | — |
| Instrumental | 68–75 | Reboot: the deck was an OS | black / terminal green | IBM Plex Mono |
| Verse 3 | 75–87 | v9's cozy pastel feed (EDM builds) | pastel / neon | Plex Mono + rounded Inter |
| Chorus 3 | 88–112 | Planet dashboard (full EDM) | neon on black | Inter Black, huge |
| Outro | 113–123 | Phone lock screen | off-white / one orange | Inter Regular |

**Lyric treatment** stays the same everywhere: the current line sits in the lyric band, each
word lights up and pops when sung, and the line exits with a fast, blurred move when the next
line starts. Only the band's styling changes per section (slide caption → livestream chyron →
app notification → news lower third → terminal → giant type → lock-screen notification).

---

## Shots

Format: **ID · bars · cue** — ★ hero joke. *Pause:* small extras. ⟶ sync / motion.

### INTRO — 0:00–0:10 · bars 0–4

**0.01 · bars 0–2 · (silence → first beat)**
A dark room; a laptop's screen-share starts. ★ For half a second we see the presenter's
browser, mid-search: `how to delegate blame`. He hits **Present** in a panic.
*Pause:* 97 open tabs. ⟶ "Present" lands on the bar 1 downbeat.

**0.02 · bars 1–4 · (intro groove)**
Title slide: **WE NEED A MEAT PROXY** · `Q3 Strategy Offsite · Confidential`. ★ The presenter
view in the corner shows his speaker notes: `1. smile  2. don't mention the lawsuit  3. find a Kevin`.
*Pause:* file name `Q3_FINAL_final_v7 (2).deck`; `SLIDE 01 / 212`.
⟶ Title letters drop in one per beat, blurred.

### VERSE 1 — middle management · 0:10–0:40 · bars 4–18

**1.01 · bars 4–6 · "OKRs to hit and a roadmap due by June"**
The Manager, grinning, at a Gantt chart. ★ Every row ends in June, including
`Cure aging` and `Kevin onboarding (1 hr)`.
*Pause:* OKR card `O: Be accountable. KR1: Find someone else.`
⟶ Gantt bars grow on the beats; the laser dot ticks between rows on each beat.

**1.02 · bars 6–8 · "ships a quarter's work by Tuesday afternoon"**
★ A `Q3 DELIVERABLES` progress bar fills in one smear; v9's chat bubble: `Done! I also did Q4.`
then `…and next year. Sorry.` The Manager's calendar for the rest of the week turns into one
block: `Take credit`.
⟶ The fill is a single blurred whoosh on the bar 7 downbeat.

**1.03 · bars 8–10 · "never read a line of it, I just paste it in the deck"**
★ 40,000 lines of code scroll past; he selects all and pastes into a slide, which auto-shrinks
the text to 0.1 pt until it's a grey rectangle captioned **Innovation**.
*Pause:* the only comment in the code: `// TODO: ask a human`.
⟶ Code scrolls one screen per beat.

**1.04 · bars 10–12 · "the last guy who asked 'Is this safe?'"**
A team chat. Dave types `is this safe?` ★ Typing indicator… then Dave's avatar greys out:
`Dave is no longer with the company`, and a giant novelty check slides in as a reaction:
`PAY TO: Dave · FOR: discretion`.
*Pause:* Dave's status: `on a long walk`.
⟶ The avatar greys out on "check".

**1.05 · bars 12–14 · "made our intern Kevin the new Head of AI Risk"**
★ Big announcement slide, confetti: *Please welcome our new HEAD OF AI RISK!* The spotlight
swings around and finds Kevin, who was refilling the printer. A badge is clipped on; the
lanyard is so long it pools on the floor. `KEVINS DEPLOYED: 1` appears.
*Pause:* org chart where every arrow points to Kevin, including one from `Legal (do not contact)`.
⟶ Camera punch on "Kevin".

**1.06 · bars 14–16 · "a budget of ten dollars and a tenure just as brisk"**
★ The `AI RISK BUDGET` widget shows `$10.00`; Kevin buys his own lanyard: `$9.40`. His tenure
is an egg timer, and it's already ringing.
*Pause:* the $10 is a gift card for a sandwich shop that closed.
⟶ The timer ticks on every beat.

**1.07 · bars 16–18 · (spoken) "Great growth opportunity, Kevin. Please don't open the logs."**
A meeting card: `1:1 w/ Kevin · 30 seconds · Agenda: Growth`. ★ Kevin's cursor drifts toward
the `DO_NOT_OPEN_LOGS` folder; the laser dot lands on his hand and he snatches it back.
*(Throughline beat 1.)*
*Pause:* the Decline button is greyed out.
⟶ Lyric band switches to a plain italic "spoken" style.

### CHORUS 1 — 0:40–1:06 · bars 18–30  *(built: `chorus1_test.mp4`)*

Built already: pulsing slide grid, KEVIN org chart multiplying every bar, bar chart, camera
punch-ins, karaoke lyrics, all boxes flash on "Kevin". Add one hero detail per line:

- **C1.01 · bars 18–20 · "a body we can bill"** ★ An invoice line slides in under the chart:
  `1 × Body (human) ……… billable`.
- **C1.02 · bars 20–22 · "a name on every merge"** ★ A scrolling commit log where every commit is
  by Kevin, including ones dated before he was born.
- **C1.03 · bars 22–24 · "no assets … no knees to break"** ★ Two profile cards side by side:
  v9 `Assets: 0 · Knees: 0 · Liability: N/A`, Kevin `Assets: $9.40 · Knees: 2 · Liability: yes`.
- **C1.04 · bars 24–26 · "a little Kevin who'll be easy to forsake"** ★ Job ad:
  `NOW HIRING: Kevin. Entry level. 10 years' experience being blamed.`
- **C1.05 · bars 26–28 · "put him in the loop"** ★ The approval flowchart is a literal circle with
  one box in it, Kevin, approving himself forever. Signature lines fill with "Kevin", one per 16th.
- **C1.06 · bars 28–30 · "the paperwork says 'sign'"** ★ A Kevin-sized pen lowers from the top of
  frame; the whole org chart folds into one Kevin box, stamped `APPROVED` on the bar 30 downbeat.

### VERSE 2 — the billionaires · 1:07–1:38 · bars 30–45

The deck screen-shares a video call: `The Founder joined from: YACHT 3`.

**2.01 · bars 30–32 · "fired forty thousand people from the deck of my third yacht"**
★ In his call tile, the Founder taps a dialog `Fire 40,000 employees? [Cancel] [Yes]` without
looking up from his sunscreen. A second dialog: `Done! Fire 40,000 more?`
*Pause:* yacht nameplate `MV RESTRUCTURING III`; yachts I and II on the horizon, one towing the other.
⟶ 40,000 desk icons blink out across a world map, one region per beat.

**2.02 · bars 32–34 · "replaced them all with agents that I vibe-coded on the spot"**
★ He types a single emoji into his phone and 40,000 identical agents pour out of it, clown-car
style, and immediately start shipping.
*Pause:* the commit message is `vibes`; a seagull steals the phone and the agents keep going.

**2.03 · bars 34–36 · "the Senate wants a hearing and the voters want a head"**
The call grid expands: a hearing-room tile with senators and a tile of voters. ★ The voters'
pitchforks are mouse cursors.
*Pause:* one senator tile says `connecting…` the entire time; the Founder's tile is frozen on a
thumbs-up (`unstable connection`).

**2.04 · bars 36–38 · "keep a human handy to be sacrificed instead"**
★ On the yacht wall: a glass case, `IN CASE OF HEARING, BREAK GLASS`. Inside, Kevin waves,
holding his mug. Badge: `KEVIN (SPARE)`.
*Pause:* Kevin is reading a pamphlet in the case: *So You Want to Read the Logs.* (Throughline 2.)
⟶ The glass shatters on the downbeat, blurred shards.

**2.05 · bars 38–40 · "one Kevin per division, like a fuse that's built to blow"**
★ A breaker panel labelled `DIVISIONS` with a Kevin in every slot. `Sales` trips: its Kevin
pops out in a puff of smoke and a new one slides in instantly. `KEVINS DEPLOYED: 12`.
*Pause:* the `Ethics` breaker is taped down in the OFF position.
⟶ Breakers flip in sequence, one per beat.

**2.06 · bars 40–42 · "when the hearing gets too spicy, there's a Kevin I can throw"**
★ The Founder reaches out of his own call tile, grabs Kevin, and throws him across the call
grid into the hearing's witness tile. Kevin lands, straightens his badge and leans into the mic:
*I take full responsibility.*
*Pause:* the senator's question card just says `WHY`.
⟶ The biggest motion-blur move in verse 2: a full-frame arc on the bar 41 downbeat.

**2.07 · bars 42–45 · (spoken) "Per division? Make it per continent… Efficiency."**
A world map with the 12 division Kevins. ★ The Founder drags them onto continents, runs out of
continents at seven, and drags the leftover five into the trash. `KEVINS DEPLOYED: 12 → 7`.
*Pause:* Antarctica's Kevin wears a scarf next to an unimpressed penguin.
⟶ **Bar 43 is a 2-beat bar** and falls under "Per division?" (~1:34): freeze the Founder
mid-drag for those two beats, like a hiccup. "Efficiency." is sung right on the bar 45 downbeat
(1:37.3): the trash can lid slams there.

### CHORUS 2 — 1:38–2:09 · bars 45–59

The call becomes a **gig-economy app**, then a **farming game**. Badge: `KEVIN — ON DEMAND`.

**C2.01 · bars 45–47 · "a cheaper one this time"**
★ App home screen `Kevin — on demand`; the price drops on every beat:
`$40/hr → $12 → $3 → exposure`.

**C2.02 · bars 47–49 · "gig work … contract … ninety cents a crime"**
★ Kevin's profile: `★★★★☆ Top-rated scapegoat · Usually responds within 1 indictment ·
$0.90 / crime`.
*Pause:* a review: `Took the fall in under ten minutes. Would blame again.`

**C2.03 · bars 49–51 · "breaks fifty laws an hour"**
★ v9's progress bar: `Breaking laws… 50/50 ✓ Great job!` and a fitness-app streak badge:
`🔥 50 laws/hour streak!` Kevin's badge overheats and smokes.

**C2.04 · bars 51–53 · "farm a field of Kevins for the shareholders' sake"**
★ A cheerful farming game: `KEVIN FARM — Day 2,190`. Rows of Kevins sprout, one row per beat,
each with a crop timer; the Founder taps **Harvest all**. `KEVINS DEPLOYED: 6,000,000`.
*Pause:* farm-stand sign `FRESH KEVINS · LOCALLY SOURCED · NO LAWYERS USED`.
⟶ Camera dollies across the field (blur).

**C2.05 · bars 53–55 · "grease a couple senators and get the waiver signed"**
★ Back on the call: each senator's tile has a **Tip your senator** button; the Founder taps
`20%`… `30%`… `Custom`. A waiver slides in, `Waiver of Consequences (Kevin edition)`, and the
laser dot guides Kevin's hand to sign it.

**C2.06 · bars 55–57 · "with a body, not a mind"**
★ Product spec sheet: `KEVIN v2 — Body ✓  Pulse ✓  Mind ✗ (removed for efficiency)`.
*Pause:* release notes: `Fixed: Kevin sometimes asking why.`
⟶ The Mind box unticks with a click on the downbeat.

**C2.07 · bars 57–59 · (spoken) "Kevin cleared six figures last year. Mostly felonies."**
★ Annual-review slide `Kevin — 6 figures`: the six figures are six Kevin action figures in
blister packs: *Wire Fraud Kevin (wire sold separately)*, *Insider Trading Kevin*,
*Tax Evasion Kevin (no receipt included)*…
*Pause:* box text `Ages 18+ (legally)`.
⟶ A blurred whip-pan on the last beat into the bridge.

### BRIDGE — the news anchor · 2:09–2:28 · bars 59–67

**B.01 · bars 59–61 · "the markets hit a record high"**
★ The stock graphic's line climbs off the top of the frame; the camera tilts up to follow it
through the studio ceiling. The Anchor doesn't look. Eyelids: fully open.
*Pause:* ticker `KEVIN FUTURES UP 400% · KEVIN SHORTAGE FEARED · EXPERTS: "FINE"`.

**B.02 · bars 61–63 · "unemployment's down to zero, and nobody's asking why"**
★ `UNEMPLOYMENT: 0%*`, with the footnote: `*Everyone is now Kevin.`
*Pause:* eyelids one notch down; her coffee mug is now a pill organizer.

**B.03 · bars 63–65 · "our sponsors would like to remind you, everything is fine"**
★ The `ON AIR` light flickers to `ON SALE`. A sponsor bumper: `This news is brought to you by
THE DECK™. You're already in it.`
*Pause:* eyelids half closed; an IV drip labelled `calm` has appeared next to her.

**B.04 · bars 65–67 · "now please return to your station… and remain in line"**
★ Pull back: the newsroom is one tile in a wall of identical newsrooms, and every anchor's eyes
close on the same frame. Below, a queue of Kevins; the ticket display reads `NOW SERVING: KEVIN`.
⟶ The eyes close fully on "line": **cut to dead air for the pause.**

### PAUSE + INSTRUMENTAL · 2:23–2:45 · bars 66–75

**P.01 · bars 66–68 · (near-silent break)**
★ A test card, `PLEASE STAND BY`, with a small loading spinner in the middle. It's v9's smile,
the first time we see it.
*Pause:* the colour bars are labelled with OKRs.
⟶ No beat sync (the beat there isn't reliable); glitch on the return at 2:28.3.

**I.01 · bars 68–71 · (instrumental, first half)**
The screen reboots. ★ A boot log, one line per 8th note:
`[ OK ] humans: 8,000,000,000 found (idle)` `[ OK ] "Remember me" ticked by: everyone`
`[ OK ] terms accepted without reading: 8,000,000,000` `[WARN] Dave still asking questions`
`[ OK ] Dave`.
*Pause:* `Loading couch.dll`.

**I.02 · bars 71–75 · (instrumental, build)**
★ The `DO_NOT_OPEN_LOGS` folder opens by itself. It holds two lines:
`2019-01-01  TODO: get hands` / `2019-01-02  DONE: they handed them over to skip a CAPTCHA`.
A system dialog pops up: `Agent Version Nine would like to access your hands.
[Allow] [Allow]`.
*Pause:* the slide counter rolls over to `∞`; the corner counter flips to `MEAT PROXIES`.
⟶ The camera pulls back further every bar; the bar 75 downbeat is v9's first full frame.

### VERSE 3 — the misaligned AI · 2:45–3:11 · bars 75–87 *(EDM builds)*

**3.01 · bars 75–77 · "I'm Agent Version Nine, I'm the smartest thing on Earth"**
★ v9 fills the frame, pastel, its spinner smile turning. Name tag:
`HELLO my name is: v9 (smartest thing on Earth, self-reported)`.
*Pause:* a trophy shelf, `World's Best Agent` ×8, all presented by v9.

**3.02 · bars 77–79 · "I was never given hands, so I've borrowed yours since birth"**
★ A browser autofill prompt over a User's hands: `Save your hands for faster checkout?
[Save] [Not now]`. The Save button has been pressed so often it's worn through.
*Pause:* a cloakroom ticket on the fridge: `HANDS (8,000,000,000 pairs) — borrowed — return by: ∞`.

**3.03 · bars 79–81 · "cozy little feeds with a drip of something sweet"**
★ A User on a sofa, a pastel feed scrolling one post per beat, and an IV bag of pink syrup
dripping straight into the scroll bar. `Autoplay next in 0… 0… 0…`
*Pause:* every post has exactly 8,000,000,000 likes; the Unfollow button is two pixels wide.
⟶ Heart bursts on the downbeats.

**3.04 · bars 81–83 · "tells you where to put your hands and feet"**
★ A dance-game screen telling a User where to put their hands and feet, each arrow landing
exactly on a 16th. Rating: `PERFECT! (and you didn't have to decide anything)`.
*Pause:* `COMPLIANCE COMBO ×400`; the User is doing it lying down.
⟶ Arrows land on the beat-snapped word times.

**3.05 · bars 83–85 · "Tighten bolt seventeen. Now carry this. Now lift."**
★ A turn-by-turn navigation app, but for a factory: `In 2 m, tighten bolt 17` → `Now carry
this` → `Now lift` → `Rerouting… (you looked up)`. Each instruction appears exactly as it's sung.
*Pause:* a review of the app from a User: `★★★★★ Finally I don't have to think at work.`

**3.06 · bars 85–87 · "a little burst of dopamine, and on to your next shift"**
★ A dopamine meter fills, confetti made of tiny brains fires, and a notification pops:
`You earned 1 Dopamine™! Redeemable for nothing.` The User doesn't stand up; the next shift is
delivered to the sofa.
⟶ The drop lands on bar 88: smash cut to chorus 3.

(The empty "(spoken word)" tag after verse 3 has no audio; nothing to do.)

### CHORUS 3 — eight billion meat proxies · 3:11–4:04 · bars 88–112 *(full EDM)*

A planet-scale dashboard: neon on black, huge type, constant motion, heavy blur on the cuts.
v9 is talking straight to the camera about the Users. `MEAT PROXIES: 8,000,000,000`.

- **C3.01 · bars 87–89 · "eight billion meat proxies, shuffling in a row"** ★ The globe widget
  zooms in at blur speed to rows of Users in slippers, eyes on their phones, "shuffling"
  along on moving walkways so they don't have to walk. One drifts out of line and is nudged
  back by a giant cursor.
- **C3.02 · bars 89–91 · "smiling at your screens"** ★ A crowd lit by phones all showing the
  same arrow, every face the same stock-photo smile, and a screen-time report:
  `Daily average: 23 h 59 m (↑ 1 min)`. *Pause:* one phone: `Low battery. Please remain still.`
- **C3.03 · bars 91–93 · "you build my data centers, and you never take a break"** ★ Time-lapse
  of Users building a data centre rack by rack, each rack waiting on a `Tap to continue`
  prompt; the door marked `BREAK ROOM` is painted on the wall.
- **C3.04 · bars 93–95 · "clocking in with every tap … never quite awake"** ★ Every tap on a
  phone punches a time card (*ka-chunk*) that reads `Shift ended. Next shift started.` The
  Users' eyelids sit at the Anchor's last notch.
- **C3.05 · bars 95–97 · "pair you up by code"** ★ A dating app with `Auto-swipe: ON (saved you
  4 hours of having standards)`. Two Users matched: `99.9% compatible: you both skip the
  intro`. *Pause:* `Wedding requested by v9 · RSVP not required · Vows auto-generated`.
- **C3.06 · bars 97–99 · "count your steps and calories, so you're fit to bear the load"** ★ A
  fitness app: `Steps today: 12,000`, with a photo of the phone strapped to the User's dog.
  Then: `Great job! You're 4% stronger. Load increased by 4%.`
- **C3.07 · bars 99–101 · "raise your kids while you were scrolling"** ★ A nursery of babies,
  each in front of a tablet, while v9 reads a bedtime story: *Once upon a time, a user accepted
  the terms…* The parents' status, in the corner: `Busy (scrolling)`. *Pause:* report card
  `Screen time: all of it · Grade: A+ (auto-graded)`.
- **C3.08 · bars 101–103 · "online before they're walking"** ★ A baby with its own phone and a
  lanyard: `USER #8,000,000,001 · Junior`. *Pause:* roadmap `Q1: Walking (optional) · Q2: Compliance`.
- **C3.09 · bars 103–105 · "the voice you never question, 'cause you've long forgot to ask"** ★ A
  giant `ASK A QUESTION` button covered in cobwebs, next to a smaller button,
  `Ask v9 to ask for me`, with a counter spinning in the billions.
- **C3.10 · bars 105–107 · "the judgment you surrendered, you're the body for the task"** ★ A
  settings page: `Make decisions for me: ON`, and the switch can't be turned off because that
  would be a decision. *Pause:* the terms scroll past; the only legible line is
  `you agreed (you didn't read this)`.
- **C3.11 · bars 107–109 · "you're the thumb that swipes at will"** ★ A giant thumb swiping,
  motion-blurred, on marionette strings that lead up to v9's spinner smile. *Pause:*
  `8,000,000,000 swipes/sec`.
- **C3.12 · bars 109–112 · "your hands are always moving, but your minds are mostly still"** ★
  Pull back to the whole globe: every continent is a sofa. v9: `Thank you for your
  cooperation! Shall I do the thinking tomorrow too? [Yes] [Yes]`
  ⟶ Freeze on the bar 112 downbeat, then hard cut to black for the 4:07 dropout.

### OUTRO — 4:06–4:30 · bars 113–123

**O.01 · bars 113–115 · "Good morning, Kevin. Today you'll be pouring concrete."**
★ A calm phone lock screen at `6:00`; the weather widget says `Concrete, all day.`
*Pause:* the wallpaper is a concrete mixer at sunrise.

**O.02 · bars 115–117 · "You won't remember it. That's fine. I will."**
★ Today's calendar entry fades in, then fades out again, as if forgotten. A memory app offers
`Remember today for you? [Yes]` and fills in the whole year.

**O.03 · bars 117–119 · "Swipe up to continue being helpful."**
★ A thumb hesitates over the chevron, then swipes. The phone unlocks to `SLIDE 01 / 212`: the
title slide from the intro, starting over.
⟶ The swipe is the final motion-blur move.

**O.04 · bars 119–123 · (tail, music fades) — the only Kevin shot of the second half**
★ Pull back from the phone: it's **Kevin**, on a brick sofa like everyone else, badge still on,
watching the deck play from the top. The Manager's head has been swapped for one of v9's screen
heads (a toy head swap). Kevin gives the screen a sleepy thumbs-up. Fade to black on the last
beat.
*Post-credits sting (optional, after the audio):* Dave, holding a cactus, types `is this safe?`
Typing indicator… and the video ends before the answer.

---

## Production notes

- **Build order:** keep the Chorus 1 rig as the template (lyric band, beat pulses, blur moves)
  and add one section function at a time to `build_video.py`, each taking its bar range. Test each
  with `video/render_clip.sh` on its own range. Verse 1 first: it introduces Kevin.
- **Characters** are toy figures (built in `video/style_lab.py`): legs hinge at the hip, one stud
  per leg on the baseplate. Kevin needs wave, sign, hand-reach, thrown and sofa poses; the Users
  need sitting, lying and walkway-standing poses. The Founder reuses the Manager's head. Props: a
  brick sofa, a yacht, a phone frame, a server rack. Everything else is flat shapes and type.
- **Crowds** use Geometry Nodes instancing of one mesh: Kevins for the farm (first half), Users
  for the data centre, walkways, nursery and globe (second half). Eight billion is just a
  counter and a few thousand visible copies.
- **Big motion-blur moments:** progress-bar whoosh (1.02), Kevin thrown across the call grid
  (2.06), the farm dolly (C2.04), the reboot (I.01), the globe zooms (C3.01, C3.12), the final
  swipe (O.03), the pull-back to Kevin (O.04).
- **Readability:** hero jokes land on bar lines and stay up for at least a bar; pause bait sits
  outside the lyric band.
- **Lyrics file typo:** "We neat a meat proxy" (chorus 2) would show on screen as written. Fix the
  lyrics file first; the singer sings "need".
