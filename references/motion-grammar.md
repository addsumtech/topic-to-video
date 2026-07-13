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

**Honest deliverables:** the per-clip render (`-c copy` concat) cannot see the neighboring clip, so
morph / shared-element / cross-clip pans are NOT deliverable — for a drill-down or comparison
relation, put the semantics INSIDE the scene (the timeline archetype's left-to-right reveals, a
counter animating its own number, a `.defocus` comparison) and use the short fade at the cut, per
the guide's own fallback. Edge dips are LINEAR (ffmpeg's fade has no easing) — accepted: at ≤0.45s
a dip-to-color reads the same eased or not, and custom easing would break the simple deterministic
filter chain. No wipes/pushes/spins/page-curls — effect variety without meaning is the exact slop
this doctrine avoids. Keep seams ≤0.35s, the closer ≤0.45s (`validate.py` warns past 0.5, flags
unknown `transition` values, and lints unpaired seam edges + a hard-ending closer).

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
