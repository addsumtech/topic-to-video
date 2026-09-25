# Motion Grammar

## Ken Burns (the only motion type in v1)

Every slide has a `motion` object:

```json
"motion": {
  "type": "kenburns",
  "from": [x, y, zoom],
  "to":   [x, y, zoom]
}
```

`[x, y, zoom]`:
- `x`, `y` are **normalized pan anchors in 0.0 – 1.0** — the point of the frame
  the camera keeps centered as it zooms. `0.5, 0.5` = dead center, `0, 0` =
  top-left, `1, 1` = bottom-right. (At `zoom == 1.0` the anchor has no effect;
  it only matters once you zoom in.)
- `zoom` is a scale multiplier (`1.0` = no zoom). Animating from the `from`
  zoom to the `to` zoom over the slide is the Ken Burns push.

**Default (from `storyboard.py`):**
```json
"motion": { "type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12] }
```

This is a gentle centered 1.0 → 1.12 zoom — barely noticeable, but it kills the
"static screenshot" look.

### Motion guidelines

| Situation | Recommendation |
|---|---|
| Default, nothing to highlight | Keep the centered default: `[0.5,0.5,1.0] → [0.5,0.5,1.12]` |
| Narration calls out a region | Move the `to` anchor toward that region (e.g. top-right ≈ `[0.8, 0.2, …]`) and zoom in so it lands centered |
| Diagram with fine text | Don't zoom past 1.25 — text softens at zoompan's scale limit |
| Zoom delta | Keep ≤ 0.20; larger values cause visible jitter in ffmpeg zoompan |

Zoom toward a region **only when the narration explicitly references it.**
Unmotivated motion is distracting.

---

## Shot grammar — shot SIZE by narrative FUNCTION (image / Remotion tier)

A beat's Ken Burns framing should follow its narrative JOB, not be uniform. The design-director emits a
`shot` per image beat and maps it to `motion.from/to/zoom`; the renderer already honours any anchor+zoom.

| Beat's job | Shot | Ken Burns `from → to` |
|---|---|---|
| Section opener / establishing | **wide, held** | `[0.5,0.5,1.0] → [0.5,0.5,1.04]` (barely moves — let the viewer take the frame in) |
| Explaining, neutral | **medium push** | the centered default `→ [0.5,0.5,1.12]` |
| Key term / the one number, spoken | **close push on it** | `to` = that region's center, zoom `~1.22` — lands as the word is said (pair with a `cue`) |
| Climax / payoff | **big slow push** | a larger delta (`~1.2`) + `intensity:bold`, longest hold — the loudest move of the deck |
| Calm close / hold | **slow drift** | tiny delta (`~1.05`) + `intensity:subtle` |

## Motion INTENSITY — the visual-energy amplitude dial (`meta.intensity` + per-beat)

`meta.intensity` (`subtle` | `balanced` default | `bold`) — and a per-scene `slide.intensity` the
design-director derives from the beat's `energy` — scales the Ken Burns **move** (the renderer multiplies
the zoom-delta + pan by `subtle≈0.6 / balanced=1.0 / bold≈1.5`, then **clamps** the amplified result back
under the ≤0.20 zoom-delta / ≤1.25 absolute-zoom / on-canvas-pan caps, so a bold beat can never lurch past
the gate). This turns the fixed 1.0→1.12 default into an expressive dial: a calm intro can drift while the
payoff pushes hard, so one video builds an arc. On the HTML tier (no Ken Burns) the SAME per-beat
`energy`/intensity should steer the design-director's `motion_intent` verb, reveal stagger, and transition
length instead — bold ⇒ snappier reveals + a longer dip into the beat; subtle ⇒ gentle staggered fades.
Author a deliberate arc rather than one flat intensity across every beat, and keep motion motivated.

## Iceberg pan (the `.iceberg` form)
An `.iceberg` beat is motion-native: on the HTML tier the `.mass` `.ib-point`s reveal on their cues; on an
image/Remotion iceberg, use a slow **downward** Ken Burns (`from [0.5,0.35,1.05] → to [0.5,0.75,1.05]`) so
the camera sinks past the waterline and literally uncovers the hidden mass as the narration names it.

---

## Coordinate-target zoom (framing a named region)

The `to` anchor IS the point the camera keeps centered as it zooms — so to land a
specific region (a stat, a figure panel, a callout) dead-center at the end of the
push, **set `to`'s `[x, y]` to that region's center** and raise the zoom.

If the region is a box `[x0, y0, x1, y1]` (the same normalized frame coords a
callout uses), its center is:

```
x = (x0 + x1) / 2
y = (y0 + y1) / 2
```

Use that as `to`'s anchor. Example — frame the top-right box `[0.62, 0.05, 0.95, 0.38]`
(center `≈ 0.785, 0.215`):

```json
"motion": { "from": [0.5, 0.5, 1.0], "to": [0.785, 0.215, 1.18] }
```

**Motivated-motion rule:** if a slide carries a callout, the camera should *agree*
with it — `motion.to` should sit near the callout's center. `validate.py` warns
whenever `motion.to` is far from the callout center, whether the camera holds at the
default `[0.5, 0.5]` or pans somewhere else entirely (the highlight and the push
disagree). Either move `to` toward the callout, or — for a deliberately static frame —
drop the callout.

**Timed callout (`cue` / `at`) — sync the highlight to the voice.** A callout is shown for
the whole slide by default. To make it *appear* at the moment its region is spoken, add a
`cue` — an anchor phrase the narration actually says (`"cue": "the second peak"`); the
renderer resolves its spoken time (edge word-timings when present, else the text-position
estimate) and the highlight fades in there and **holds to the clip end** (a highlight that
vanishes mid-clip reads as a glitch). Use `at` (a `0..1` fraction of the clip) to override the
time manually. This is a **timed appearance only — the camera is NOT re-aimed mid-clip** (a
mid-shot pan toward a late highlight lurches; keep the single motivated settle above). Keep it
off by default and one callout per slide. `validate.py` warns when a `cue` isn't found in the
narration (can't be timed) or resolves past ~85% of the line (appears too late to help).

---

## Motion verbs (shared vocabulary)

When you describe how a beat should move (the planner's `motion_intent`, an HTML
page's reveal, or a Ken Burns choice), reach for a **verb with a physical
character** rather than "it animates in". The verb tells the author which reveal /
easing / zoom to pick, and keeps narration emphasis and on-screen motion aligned.

| Character | Verbs | Fits |
|---|---|---|
| Impact / weight | SLAMS, DROPS, STAMPS, PUNCHES | a result, a headline number landing |
| Directional | SLIDES, WIPES, PUSHES, CUTS | a transition, swapping one idea for the next |
| Reveal / build | DRAWS, FILLS, GROWS, COUNTS UP, ASSEMBLES | a chart drawing, a metric counting up, a list building |
| Organic / ambient | FLOATS, DRIFTS, BREATHES, PULSES | a hero/title beat, an atmospheric hold |
| Mechanical | TYPES ON, SNAPS, LOCKS IN, STEPS | code/terminal text, a precise stepwise reveal |

Keep it honest: the free tiers express these through the programmatic renderers'
built-in reveals, the HTML tier's CSS reveals, and the Ken Burns push — not arbitrary
keyframing. Pick the verb that the available motion can actually deliver; don't promise
a SLAM the renderer can't land. The concrete "headline number landing": a `chart` scene
with `props.kind:"counter"` **and `props.climax:true`** counts up, reaches the true final
value at ~68% of the scene, then holds it static — that's the deliverable form of
SLAMS/COUNTS UP for the payoff beat.

### Intent → motion (pick by what the beat is DOING)
Start from the beat's *job*, not a menu of effects. Each row is deliverable by the free tiers:

| Intent | Deliverable motion | Use when | Avoid |
|---|---|---|---|
| Reveal causality / a sequence | staggered `.reveal-up` per step + `.draw` on a connector | a `.flow` / chain / pipeline | fading every step in at once (hides the order) |
| Emphasize a metric | `chart` counter count-up + hold (`props.climax`) | the KPI / result beat | an endless zoom, a number that never settles |
| Compare two states | reveal A, then B; `.defocus` the non-focal side | before→after, A vs B | a spin/wipe between them |
| Build a diagram | reveal nodes → each connector WITH its destination node (`.arrow`/`.hs-connect` gets `reveal` + the LATER node's `data-cue-index`) → the focal `.on` last | `.hubspoke` / `.quadrant` / `.timeline` | everything appearing together — worst case a **static connector that paints before its nodes** (validate ERRORs) |
| Draw a line/fill | `.reveal-wipe` (clip-path) or `.draw` (SVG stroke-on) | a `.rule` / `.segbar` / `.meter .fill` | on text rows/cards (meaningless there) |
| Hold / breathe | a living backdrop (`.bg-live`/`.bg-drift`) whisper | a sparse hero / the closer | any second moving thing on the page |
| Reset attention | a dip through the theme bg at the cut | a section seam (`new-topic`) | a decorative transition with no meaning |

One intent per beat; the motion serves the idea, never decorates it.

## Living backdrop (ambient motion — the deliverable FLOATS/DRIFTS/BREATHES)

The "Organic / ambient" verbs above (FLOATS, DRIFTS, BREATHES) are delivered by an **ambient
backdrop**, not by a GIF. A GIF/video background is non-deterministic under our capture (each frame
reloads at `?p=`, so a GIF freezes at frame 0 or jitters on wall-clock time) — so the alive-but-still
look comes from a slow, **seek-frozen** motion on a full-bleed backdrop:

- **`.bg-live`** (slow Ken-Burns push) / **`.bg-drift`** (slow lateral parallax) on a `.bg-soft`/`.bg-photo`
  — see `references/html-pages.md` "Living backdrop". These are AMBIENT: `seek.js` drives them by
  PROGRESS (0→1 across the whole scene) and excludes them from the reveal-stagger envelope, so a living
  backdrop spans the scene *and* never disturbs a reveal's freeze time.
- The classic **`.kenburns`** hero push and the foreground **`.reveal-wipe`** mask sweep round out the set.

**The one rule that keeps it tasteful: a moving backdrop is the loudest thing on screen.** The eye
locks onto motion (see Visual Hierarchy — "the first moving object becomes the focus"), so the backdrop
must be a WHISPER (`.bg-live` a ~6% push, `.bg-drift` a ~3% lateral parallax — felt, not seen) and it is
the page's ONE continuous ambient motion. Content reveals settle in and then hold, so they don't
compete — but never stack a SECOND loud/continuous motion on a living backdrop (a `.kenburns` hero push
or a `.reveal-wipe` panel — pick one). Off under reduced motion. This is the deterministic, on-taste
answer to "can the background move?".

## Transition rhythm (semantic — the relationship between two beats picks the cut)

One transition shape everywhere is smooth but monotone; random effect variety is slop. The rule
(after the Semantic Transition principle): **classify the RELATIONSHIP between consecutive beats,
then select; never choose randomly; when uncertain, prefer a short fade over a fancy effect.**
The planner emits each beat's `relation` (to the PREVIOUS beat); map it to per-scene overrides
(`slide.transition`: `dip` both edges · `in` / `out` one edge · `none`; `slide.transition_seconds`;
falling back to `meta.transition`):

| `relation` (A → B) | What to set | Why |
|---|---|---|
| `continuation` (same topic, more info) | B: `"none"` (hard cut) | momentum — the continuity hook carries the viewer; B's own progressive reveals ARE the "reveal" transition |
| `new-topic` (a section seam) | A: `"out"` · B: `"in"` | a breath through the theme bg signals "new chapter" |
| `payoff` (into the climax) | A: out edge · B: `"in"`, `transition_seconds: 0.3` | a longer breath sets up the key number/beat |
| `close` (into the final hold) | A: out edge · B: `"dip"`, `transition_seconds: 0.4` | the in-edge is the exhale; the out-edge doubles as the video's end fade-out |

**A dip needs BOTH sides of the cut.** An in-edge whose predecessor ends hard renders as a
smash-cut-to-blank (B's first frame is fully bg); an out-edge into a hard-opening scene is a
fade-down-then-pop. So every `"in"` composes with the PREVIOUS scene's out edge: upgrade the
predecessor `"none"`→`"out"`, `"in"`→`"dip"` (`validate.py` warns on unpaired edges). At 0.2s per
edge a seam is a composed ~0.4s dip through the bg — deliberately heavier than the guide's
180–250ms crossfade, because a section seam is a chapter breath and a true crossfade is not
deliverable per-clip. Scene 1 gets `"in"` — its fade-up IS the video's opening (only `"dip"` when
scene 2 is `new-topic`). The FINAL scene must carry an out edge — it IS the video's end fade
(`validate.py` warns if the closer ends hard).

**Tier caveat (continuation):** the hard cut is right for html/programmatic scenes, whose reveals
carry the motion. On the IMAGE tier (narrated slides) each clip ends at ~1.12 zoom while the next
starts at 1.0 — a raw cut pops ~12% in scale; keep the meta dip (or a subtle `"in"` ~0.15s, the
guide's "subtle fade-in" for same-topic) between image slides instead.

**Pace caveat (continuation) — the hard-cut default assumes a PUNCHY pace.** On a deliberately CALM,
unhurried register (a low `meta.tts_speed`, a high average scene length, an explainer that lingers),
an all-hard-cut deck reads as STIFF — each scene snaps to the next with no give, and any tail silence
turns the snap into an abrupt "obvious gap" (a real deck shipped this and the viewer said exactly that).
There, make continuation cuts a UNIFORM LIGHT dip: `meta.transition: "dip"`, `meta.transition_seconds:
~0.25`, and still mark the 3–5 real section seams with a heavier dip (`transition_seconds: ~0.4`) so
the chapter breaths stay distinct. That is documentary-smooth, not monotone — the seams give it rhythm,
and marking them keeps `validate.py`'s uniform-seam warning quiet (it fires only when NO scene sets its
own transition, i.e. when the rhythm was never authored at all). The dividing line is PACE, not tier:
a light dip on FAST continuation cuts is the "nervous blink" to avoid; the same dip on calm 8-second
scenes is a gentle cross-fade. If you slow the voice to fix "too fast," soften the cuts to match — the
two decisions travel together.

**Honest deliverables:** the per-clip render (`-c copy` concat) cannot see the neighboring clip, so
morph / shared-element / cross-clip pans are NOT deliverable — for a drill-down or comparison
relation, put the semantics INSIDE the scene (the timeline archetype's left-to-right reveals, a
counter animating its own number, a `.defocus` comparison) and use the short fade at the cut, per
the guide's own fallback. Edge dips are LINEAR (ffmpeg's fade has no easing) — accepted: at ≤0.45s
a dip-to-color reads the same eased or not, and custom easing would break the simple deterministic
filter chain. No wipes/pushes/spins/page-curls — effect variety without meaning is the exact slop
this doctrine avoids. Keep seams ≤0.35s, the closer ≤0.45s (`validate.py` warns past 0.5, flags
unknown `transition` values, and lints unpaired seam edges + a hard-ending closer).


### Transition STYLE — the seam vocabulary (one style per deck, from the register)
The semantic EDGES (`transition`: dip/in/out/none, mapped from each beat's `relation`) say WHERE the
seams are; **`transition_style`** says what a seam LOOKS like. Every style is TWO SELF-CONTAINED halves
meeting at the byte-identical theme-bg frame (the same construction as an NLE's Dip-to-Color), so the
`-c copy` concat, per-clip cache and A/V gate always hold. A transition is a CLAIM about how two beats
relate — never decoration:

| style | what | says | fits |
|---|---|---|---|
| **cut** (`transition:"none"`) | nothing — the concat IS the cut, resting on the 0.42s audio breath | same thought, next beat (neutral momentum) | the DEFAULT between continuation beats, all registers |
| **dip** | fade to/from the deck's own bg | topic reset / chapter breath | the quiet workhorse; restrained registers; the fallback |
| **fadethrough** | dip with studio timing — exit FAST (≤0.15s), entrance takes the full d | same reset, emphasis lands on the NEW content (Material fade-through 30/70) | the upgraded default for precise/clinical registers |
| **drift** | dip + ~24px eased drift in the deck's direction | "the page breathes away" — direction without loudness | canvas/editorial; restrained-drift, floaty-organic |
| **push** | the page slides out LEFT over bg, next in from RIGHT | lateral sequence — next page / next step | step-by-step decks; snappy-kinetic, weighty-mechanical |
| **lift** | vertical page-turn: out UP, in from BELOW | reading-flow progression down one document | canvas/document/editorial reading registers |
| **wipe** | a bg sheet sweeps L→R: covers the still page, uncovers the next | directional replacement without travel ("and next…") | graphic registers: swiss/terminal/editorial; process decks |
| **blur** | rack-defocus into the dip; the entrance refocuses | attention shift / reflective coda | at most ONCE per deck (quote/closer), contemplative registers |

**The remotion tier speaks the SAME WORDS** (`transition_in: {"type": "..."}` or `transition_style`, resolved
by `render_remotion.seam_type`), plus four that only a compositor can draw. The table above is the shared half:
`cut` · `dip`→`fade` · `fadethrough` · `drift` · `push` · `lift` · `wipe` · `blur`. The four that are remotion-only
are the DEPTH seams and the film's native action — `carry` (a collapse-to-line match-cut), `focus` (the cut
happens at the focal plane), `through-dark` (the leaving beat's light goes out, the next comes forward out of
black), `portal` (the camera passes through the frame), plus `clock` and `dissolve`.

**`return` is the one seam an author does not spell.** It is written as an ARGUMENT — `relation: 'return'`
with `returns_to: <beat>` — and the direction is derived from where that beat sits on the film's board
(`scripts/film_board.py`). It is the only word in this vocabulary that claims a PLACE rather than a
relationship: *this is where we were*. `carry` looks similar and is not, because it carries an ELEMENT
across a cut rather than saying the two frames are the same location.

Geometrically it IS a push, and that is a measured limit rather than a shortcut. Two full-frame pictures
offset by anything less than one frame leave a strip exactly that wide covered by neither — rendered and
measured at left-edge luminance 9.5 against a centre of 74.6, which reads as a curtain — and a diagonal
offset leaves two corners bare. So the pan is a unit step along one axis; the distance a film reaches back
is not expressible in twelve frames and is not pretended at. A return that claims nothing (a forward
reference, or the cell the film is already standing in) is an ERROR in `validate`, not a quiet cut.

Until 2026-09-20 the two tiers disagreed: `fadethrough`, `drift` and `blur` had no remotion picture at all, and
`push`/`lift` were spelled only in the html vocabulary, so `transition_in: {"type": "push"}` fell through to an
anonymous fade. A relation one tier can claim and the other cannot is a vocabulary hole, and a seam that goes
quiet is the worst kind of bug — the board says one thing, the film does another, and every gate is green.
`validate.py` now ERRORS on a seam word the renderer cannot resolve.

**Taste + rhythm rules (from the research consensus):**
- **Cut is the default; styled seams are punctuation.** Budget ~2–3 marked transitions per video
  (section seams + one payoff). If a viewer notices the mechanism, it failed the invisibility test.
- **Exit fast, enter slow** — emphasis always belongs to the NEW content.
- **Duration norms:** seam ≤0.35s · payoff in-edge 0.3s · closer ≤0.45s (`validate` warns past 0.5).
  Duration scales with the size of the move and the narrative distance.
- **Direction is grammar:** ONE push/wipe/lift/drift direction per deck (= reading direction). The
  REVERSED direction is reserved to mean "going back" (recap/callback), used at most once.
- **Meet at the theme bg, never generic black** — the background is the persistent container;
  continuity comes from what does NOT move.
- ONE style + one easing family per deck, chosen from the `design_register.motion_personality`
  (`meta.transition_style`); a per-scene `slide.transition_style` only for a justified narrative
  exception (climax entrance kept on dip for weight; one blur coda).

**Authoring techniques that need NO renderer code (doc-only, stronger than any filter):**
- **Match-cut / anchor continuity** (at most ONE per deck): pin a shared anchor (title block, motif,
  diagram) at IDENTICAL coordinates/size in scene A's final frame and scene B's first frame, then hard
  cut — "this IS that", the strongest continuity claim available. Plan it in the storyboard, not a filter.
- **Jump-cut data progression:** for enumerated states (a chart stepping, a checklist filling), keep
  the layout constant and hard-cut between states — the visible skip IS the message.
- **Verbal J-cut:** a real audio J-cut is impossible (per-clip audio), so author the anticipation in
  WORDS — end scene A's narration with a forward hook naming scene B's subject; it rides the breath
  across the cut. (The scriptwriter owns this; see narration-writing.md.)

**Rejected on taste or feasibility (do not re-litigate):** true crossfade/morph/Magic-Move and any
cross-clip pixel filter (impossible under `-c copy`); audio J/L-cuts (per-clip audio); whip-pan blur,
curtain/barn-door, CRT-off, desaturate-dip (feasible but off-brand/loud); iris/3D-cube/blinds/
checkerboard/"random" (novelty — the audience notices the mechanism instead of the content).
zoom-dip (depth seams) is DEFERRED, not rejected — it needs composition with each scene's authored
Ken Burns curve; do not fake it with a crop hack.

## Reduced motion (accessibility variant)

With `meta.reduced_motion` (or `render.py --reduced-motion`) the renderer forces `to == from`
(a static frame — no zoom/pan) and HTML reveals become opacity-only cross-fades; the
programmatic renderers drop their rise/slide offsets too. Author `motion` normally — the
variant neutralizes it at render time, and `validate.py` skips its zoom warnings when the
flag is set. It's an authoring-time opt-in (a baked mp4 can't read the viewer's OS setting).

---

## Callouts

Callouts are static overlays drawn on top of the zoomed slide (they do not
zoom with the Ken Burns effect — they stay fixed in frame).

```json
"callouts": [
  {
    "at": 0.0,
    "box": [x0, y0, x1, y1],
    "style": "highlight",
    "label": "Peak SNR"
  }
]
```

### Coordinate system

All four values in `box` are **normalized 0.0 – 1.0** of the output frame
(not the original slide image). `[0, 0, 1, 1]` = full frame.
`[0.1, 0.4, 0.6, 0.7]` = a horizontal band across the left half.

### Styles

| Style | Visual | Use when |
|---|---|---|
| `highlight` | Translucent yellow fill + yellow outline | "Look at this region broadly" |
| `box` | Solid red outline, no fill | Precise UI element or number |
| `arrow` | Red outline on the target box | Pointing to a single feature |

`arrow` and `box` use the same rendering (red outline); the distinction is
semantic — use `arrow` when your narration says "here" or "this arrow shows".

**Cap at ONE primary callout per slide.** Multiple callouts compete for
attention and dilute the message.

### `at` / `cue` fields (timed appearance)

Omit BOTH for the default whole-slide highlight. `at` (a `0..1` fraction of the clip) or `cue`
(a phrase the narration says) makes the callout TIMED: it appears at that moment and holds to
the clip end — see "Timed callout" above for the full contract. Keep `at` inside `[0, 0.85]`
(`at ≥ 1` lands exactly at clip end — the callout never shows).

---

## Full Example

A slide where the narration says "notice the reconstruction error in the top-right corner":

```json
{
  "index": 3,
  "narration": "Notice the reconstruction error in the top-right corner — it disappears entirely after the compressed-sensing pass.",
  "motion": {
    "type": "kenburns",
    "from": [0.5, 0.5, 1.0],
    "to": [0.8, 0.2, 1.18]
  },
  "callouts": [
    {
      "at": 0.0,
      "box": [0.62, 0.05, 0.95, 0.38],
      "style": "box",
      "label": "Recon error"
    }
  ]
}
```

The camera starts centered and drifts the anchor to the top-right
(`x=0.8, y=0.2`) while zooming to 1.18, so the highlighted corner ends up
centered in frame as the narration points to it.

---

## PUBLISHED SPEC NUMBERS (distilled 2026-08-24)

Everything below is a NUMBER a published design system actually ships, with the source. Sources are
captured under `<research>/sources/` (see `scripts/sources.py`). Where nothing is published, that is
recorded too — an honest gap beats a confident invention, and two of the gaps below are load-bearing.

### Durations
- Entrance / on-screen move: **250–500 ms**, scaling with the transition's AREA (not just distance).
  Full-screen 400–500 ms; small local 200–250 ms. *(Material, published)*
- **An exit is always SHORTER than its matching entrance.** Material ships the pairs 500/200 and
  400/200 ms. *(Material, published)*
- Carbon's named steps: 70 (button) → 110 (fade) → 150 (default) → 240 (toast) → 400 (large expand) →
  700 ms (hero). Scaling with distance is non-linear and the formula is **not disclosed**. *(Carbon, published)*
- Micro-interaction ceiling: **90–120 ms**. *(Carbon, published)*
- **Apple's HIG Motion page publishes no durations or curves at all** — it is qualitative only. Do not
  cite "Apple does it this way" for a number; there is no number to cite.

### Easing — and why it is asymmetric
- Entering uses a DECELERATE curve (arrives at speed, settles): Material `cubic-bezier(0.05,0.7,0.1,1)`;
  Carbon `(0,0,0.38,0.9)`. *(published)*
- Exiting FOREVER uses an ACCELERATE curve (leaves at speed) — it signals "not retrievable":
  Material `cubic-bezier(0.3,0,0.8,0.15)`; Carbon `(0.2,0,1,0.9)`. *(published)*
- Exiting but RETRIEVABLE (a drawer) uses the entrance-style settle curve instead, implying recall.
  Material and Carbon state this independently. *(published)*

### Stagger
- **20 ms between successive item entrances** — the same number from two independent primary sources
  (Material's Choreography spec, Carbon's table-row spec). *(published)*
- **The whole staggered sequence must finish within 500 ms.** With more items, shrink the per-item
  offset to hold that ceiling — do not extend the sequence. *(Carbon, published)*
- Published reveal ORDER: static shell → static body → dynamic data → primary action → data-viz.
  *(Carbon, published)*

### Seams
- A shot must be SETTLED before a dissolve runs over it. Implemented in `runtime/motion.ts` `useT`,
  which holds t=0 through the incoming dissolve and t=1 through the outgoing one — measured effect:
  seam frame-to-frame variance fell from CV 0.244 to 0.016.
- **A caption must never straddle a cut.** Start and end it on the shot's first/last frame; split the
  line or move its start to the cut. *(BBC, published)*
- A caption may not lead speech by >1.5 s, hang >1.5 s after it, or trail the audio by >2 s.
  *(BBC, published)*
- Two-axis moves: stagger the horizontal and vertical starts so the path resolves as a rounded corner.
  Pure diagonal motion is called out as harsh. *(Carbon, published)*
- Frame margins: action-safe **3.5%** per side, title/graphics-safe **5%** — SMPTE ST 2046-1 and EBU R95
  agree exactly. At 1920×1080 that is 67/38 px and 96/54 px. These are a guide for TYPE, not a prohibition on
  imagery: `scripts/frame_safe_qa.py` used to gate the 3.5% border and was measured to be inverted (it blocked
  full-bleed technique and missed every real cut). `scripts/text_safe_qa.py` now asks the DOM whether any type is
  actually cut; graphics may bleed. *(published; the gate note updated 2026-09-01)*

### Restraint — the gap
**No system surveyed (Material, Carbon, Fluent, Apple) publishes a numeric cap on how many elements may
animate at once, or a motion budget per screen.** All four give qualitative guidance only ("if the motion
is noticed, remove it"). So this cannot be turned into a threshold gate from published sources; the
nearest enforceable proxies are the 500 ms stagger ceiling and the published reveal order above.
