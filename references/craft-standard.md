# The craft standard — what a built shot is held to (remotion tier)

**Where it comes from (2026-11-12).** Two studies on the same instruments:
- **video-shotcraft's October redesign**: 150 shots, each with a before and an after, co-authored with Claude Opus 5.5
  under a written brief (`shot-polish/BRIEF.md`). Their user then picked per shot: 92 took the redesign, 50 the
  conservative polish, 8 the original, 66 were dropped. The first, conservative pass (shadows, grain, easing only) was
  judged "clean but flat". What landed was a REDESIGN of every shot, keeping only the technique.
- **20 official launch films** from ClickUp, Perplexity, Slack, Figma, Bear, Pitch, Miro, Superhuman and Loom (plus
  Notion, Framer and Raycast from the 2026-11-10 study).

Measured on the settled frame and the motion of each shot (the study's tools; for a film, `scripts/craft_qa.py` already
reports stills, motion accents and hierarchy by beat against 28 launch films):

| measure | peer before | peer after | our library (213) |
|---|---|---|---|
| content share of the frame (`ink_cover`) | 0.077 | **0.275** | 0.078 |
| subject extent (`ink_box`) | 0.43 | **0.70** | 0.30 |
| lit frames (surface_qa) | 0.00 | **0.25** | 0.00 |
| samples with a still stretch over 1 s | 75 % | **53 %** | 85 % |
| where a move peaks (0.5 = linear) | 0.43 | **0.35** | 0.41 |
| blank first frame | 17 % | **3 %** | 11 % |

On whole films, every 2 s (caption band excluded): content share / subject extent — **SaaS launch films 0.415 / 0.84**
(12 films), Notion · Framer · Raycast · Linear · Arc 0.21 / 0.59, **ours 0.154 / 0.49** (5 films; WorkBuddy v2 0.32 / 0.87
is the exception). An earlier corpus (skillry previews) put occupancy level with ours; against product launch films it
is not.

So the bar is not new techniques. It is every shot DESIGNED as a moment of a top launch film. Pause any frame and it is
a designed poster; play it and the rhythm has weight.

## The kit (use it; do not rebuild it per shot)
- `runtime/craftStage`: `LitStage` (a tinted gradient ground, one key light, a fill of the second accent, an optional
  horizon band and a vignette in the ground's own shade), `Dust`, `Orbs`, `Sheen` (once, on the hero only),
  `Sparkle`, `glow`, `softShadow`, `surface`.
- `runtime/craftType`: `TYPE_LADDER` (at 1080 lines: mega 260 · display 180 · h1 120 · h2 84 · h3 60 · body 40 ·
  small 32 · label 22), `typeStyle`, `TextReveal` (word or character, accent words, ghosted tail), `Kicker`.
- `runtime/craftMotion`: `EASE` named by meaning, `ramp`, `stagger` along a curve, `holdPush`, `follow`, and
  `TimeTable` / `at` / `fitTable`.
- `runtime/craftUi`: `AppWindow`, `Cursor` (with an optional name tag), `Chip`, `Button`, `Avatar`, `Sparkline`,
  `FileBadge`, `MetricTile`, `StepRow`, `PromptBox`, `Toast`. Every word and value is a prop; these parts never invent
  a number.

## The design note — written at the top of the shot BEFORE the code
1. **Look**: which world or ground, and where the key light falls (on the subject).
2. **Subject**: the one thing, and how big. A UI subject fills 50–75 % of the frame width, or is cropped oversized.
3. **Composition**: margins ≥ 96 px, a grid, one focal point, then a second read; whitespace that means something.
4. **Timing table**: prep → main action → follow-through → settled hold, in frames, and why. An entrance takes
   10–20 f and a big move 18–32 f; key information holds ≥ 20–30 f; something is on screen within 3 frames.
5. **Curves**: an entrance is snappy/expo (ease-out), an exit eases in, a re-position is swift, a seat overshoots at
   most once. A parent moves first and its children 2–4 f later. Nothing arriving moves linearly.
6. **Content**: the words, the files, the values, all believable and all from props. No skeleton bars where real
   content fits. No number the film cannot source: an example's categories, never invented findings.

## Type
- A beat's headline is ≥ `h1` (120); a type beat's line is `display`/`mega`; anything to be read is ≥ `small` (32).
  14–22 px is texture only: dimmed, never content.
- Set large type tight (negative tracking), set small caps open, and contrast weights (760–800 against 450–520). Use
  tabular, lining figures.
- Hierarchy: a kicker, then the headline, then a folio or detail. One accent word per line at most.

## Look, light, colour
- One look per beat, from the film's world. Darks are tinted, never `#000`; lights are tinted, never large pure `#fff`.
- The subject is LIT: a key pool on it, a two-layer soft shadow under it, a hairline edge and a top highlight on
  panels. The subject sits on top of the stage, never under its vignette.
- Neutral colours, one accent, and at most one point colour. The accent marks the thing the beat is about.

## Motion
- Nothing sits fully still for over 1 s. A settled hold pushes 1–3 % (`holdPush`) or its light breathes
  (`LitStage breathe`). Never a hand-held wobble.
- Stagger along a curve (dense then sparse, or accelerating), never a constant gap.
- Speed blur only on fast, large moves (`runtime/motionBlur SpeedBlur`). Nothing else gets blur.
- **One camera per frame.** A shot that frames, pushes and crops on purpose declares `export const CAMERA = 'directed'`,
  and the automatic coverage (`scripts/coverage_plan.py`) leaves it alone. Two cameras on one frame read as a zoom in and
  back out (WorkBuddy v3, 2026-11-12). A hero object shown across consecutive beats CONTINUES its framing; it never
  re-arrives (zooms out and back in) at every seam.
- Type stays put: lay a panel out once (`runtime/surfaceView`) and move it with one transform. Settled text carries
  no transform and no filter.

## A product film (the SaaS launch grammar, measured on 20 official films)
1. **One brand world**: one ground family and ONE recurring motif (Loom's pearls, Slack's sparkle, Perplexity's orbs)
   for the whole film.
2. **A hero object that persists**: the product's window stays, and the beats are its states, not new scenes
   (Loom keeps one card for 20 s).
3. **Type beats alternate with UI beats**. A type beat is display type on the brand ground, word by word, the key
   word in the accent, the tail ghosted (`TextReveal`). A UI beat is a short kicker above and the product below at
   about 55 % of the frame width, or a crop onto the component the voice names, oversized, with a cursor doing it.
4. **One small celebration moment** (a toast, a burst) and **a closing lockup** (mark + line).
5. **Rhythm**: in the lively films only 2–17 % of shots hold still for more than 1 s. Quiet brands (Notion,
   Perplexity) hold longer, by choice.

## The loop (per shot, at least two rounds)
Render the shot at 30 / 60 / 90 % (`workshop.py still`) and put it beside the previous version. Name the three weakest
things, fix them, and render again. Stop when the frame would not embarrass a launch film. A redesign is judged
against the old shot on a compare page where the USER picks per beat (`scripts/compare_page.py <out.html> --old=<dir> --new=<dir>`). A metric going up
supports the verdict; it is not the verdict.
