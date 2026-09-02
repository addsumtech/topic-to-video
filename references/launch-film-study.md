# What real product-launch films do — measured, not remembered

Four official launch films were downloaded and measured against a film this skill delivered, with **one
instrument** for all five (greyscale, 12 fps, long side 192 px, aspect preserved — `scripts/film_energy_qa.py`
`measure()`). Read this before arguing about whether a remotion cut is "cinematic": the arguments below are
settled by numbers that can be re-derived, and `film_energy_qa.py --reference <dir>` re-measures the films if
you have them.

| film | frame-diff p75 | median ink | luminance range |
|---|---|---|---|
| Apple · *Introducing iPhone 17 Pro* | 0.0357 | 24.3% | 0.270 |
| OpenAI · *Introducing the Codex Micro* | 0.0075 | 64.4% | 0.330 |
| Figma · *All the launches at Config 2025* | 0.0481 | 36.1% | **0.903** |
| Anthropic · *Keep thinking with Claude* | 0.0381 | 42.1% | 0.350 |
| **a 30-beat film this skill delivered** | **0.0023** | **4.3%** | **0.079** |

## Which of them you can actually reach

Three of the four are **live action**, or live action plus offline PBR renders. A DOM compositor cannot make
them and should not try; chasing them produces a worse film, not a better one.

**Figma's is the reachable target.** It is entirely generative — no camera, no footage — and unambiguously
launch-grade. It also sits at the TOP of the motion and luminance columns, which is the useful part: the gap
between our film and a launch film is not a gap in production budget.

Its three characteristic moves, in order of how much they cost you to adopt:

1. **Full bleed.** Colour and imagery run off every edge. Nothing sits politely inside a safe box.
2. **Type cropped by the frame.** A display word is allowed to be bigger than the picture of it.
3. **Colour beyond a two-accent palette.** Saturated, several hues, changing between beats.

All three were **forbidden here** until 2026-09-01. `frame_safe_qa`'s EDGE-BLEED check errored on border ink,
and `shot_proof` warned on off-palette. They are legal now (see the next section), so a register that wants
them may have them.

## The gate that was measuring backwards

`frame_safe_qa`'s action-safe ERROR asked how much ink sits in the outer border and blocked delivery on a high
answer. Measured against real cases it is **inverted on both sides**:

| | reading | its 4.5% ERROR floor |
|---|---|---|
| genuinely cut by the canvas (AtomOrbital / BlockAssembly / SwissEditorial with over-long copy) | 1.45% · 1.00% · 4.40% | all **pass** |
| deliberately full-bleed (FlowField / GameOfLife / AuroraFlow / HalftonePop) | 9.6% · 12.7% · 14.1% · 35.2% | all **blocked** |

It would also refuse **100%** of the sampled frames of OpenAI's film, **57%** of Figma's and **57%** of
Anthropic's — while passing all 30 frames of the inert film above, whose single high reading is a deliberate
marquee. Zero true positives, four false ones.

The inversion is structural, so no threshold fixes it: **a cut word makes a thin band (low coverage) and a
flood makes a solid field (high coverage)**, so coverage runs opposite to the defect. Two structural
statistics were tried on the same samples — run structure along the border, and row-occupancy of border ink —
and neither separated the classes (a cellular field sat inside the "cut" range; so did two reference films).

`scripts/text_safe_qa.py` asks the DOM instead, which knows to the pixel where the glyphs are.

### How it tells a technique from an accident, with no waiver to write

* Text clipped by an `overflow: hidden` ancestor **smaller than the frame** is INTENDED — a marquee, a mask, a
  crop window. The author built the container; the container is the intent.
* Text cut by the **canvas**, with no such ancestor, is a layout that did not fit.
* A layer that travels past the frame on purpose (a panning world, a conveyor, a character rain) marks itself
  `data-bleed` **with a written `data-bleed:` reason beside it** — a test refuses a bare one.
* **Full-bleed graphics are never a finding.** Only type can be destroyed by an edge.

Three false-positive classes were found by *looking at renders*, and each was fixed in the instrument rather
than waived — worth knowing because each will bite anything similar:

* Remotion's `AbsoluteFill` sets `overflow: hidden`, so the FRAME read as the author's own crop and the first
  version exempted all 148 registers.
* **Element boxes are not ink.** A centred word in a full-width box reports as cut while every letter is
  intact. A `Range` over the text nodes measures the glyph runs.
* A cut smaller than a third of a glyph destroys nothing: 27 findings on one ASCII character field, four on a
  glitch register's 5 px offsets.

## The library measured as film, not as stills (2026-09-01)

Every visual gate here reads a STILL. `scripts/register_energy.py` renders all 149 registers as VIDEO at their
own DURATION with their own default props and measures the same three axes:

| axis | library median | floor | under floor | reference |
|---|---|---|---|---|
| motion p75 | 0.0015 | 0.0037 | **102/149 (68%)** | Figma 0.0481 |
| median ink | 4.8% | 12% | **117/149 (79%)** | Apple 24.3% |
| luminance range | 0.013 | 0.135 | **143/149 (96%)** | Apple 0.270 |

**Under all three: 92. Under two: 34. Under one: 18. Clear: 5** — FractureIn, LastLeg, LowPolyForm, ClothWave,
CrashZoom. The inert film this skill shipped was therefore not a bad use of the library; it was a faithful one.

An independent seven-lens audit against the reference frames found the mechanical cause of the largest gap, and
it is not budget:

* **The ground is one film-wide constant, and it is always near-black.** `DesignDNA` carries a single `bg`, and
  the brightest ground the whole eight-preset vocabulary can name is relative luminance Y=0.0053. `SceneSpec`
  can declare a shot, props, a duration, a caption, a transition and a camera move — **no colour at all**.
  `bgLum`, the field named for this, is a hint the caption ink and the seam guard read; it never repaints a
  pixel. `Film.tsx` resolves the ground once outside the whole `TransitionSeries`, so a 30-beat film paints the
  same near-black thirty times. That is 0.079 against Figma's 0.903, from a missing field.
* It compounds: **applying a DNA deletes the library's light half.** SHOT_LUMA measures 112 dark / 35 light /
  2 mid, and every light register grounds on `bg`, so SwissEditorial — black type on cream by identity —
  renders white-on-near-black under `dna=product`.
* The frame is a polite box: `TITLE_BAND` reserves 176px and the caption band 200, leaving 65% of frame height,
  and `fitContentSquare` returns a 605px square on a 1920px frame.
* There is no hard cut: every seam is the same 12-frame dissolve, and an exposure change is treated as a hazard
  the seam logic suppresses.

The audit's full 17-item ranked plan, with per-item evidence and acceptance tests, is the source for the work
that follows; the four above are the ones that map onto the three measured axes.

## What was closed, measured end to end (2026-09-02)

The delivered 30-beat film, re-rendered with a light arc authored by `scripts/light_plan.py` and NO edit to
any register:

| | motion p75 | ink | luminance range | light arc |
|---|---|---|---|---|
| as delivered | 0.0023 | 4.3% | 0.079 | 0.0% |
| **+ an authored light arc** | 0.0022 | 5.2% | **0.899** | **14.3%** |
| floor | 0.0037 | 12% | 0.135 | 1.9% |
| Figma | 0.0481 | 36.1% | 0.903 | 42.5% |
| Anthropic | 0.0381 | 42.1% | 0.350 | 19.1% |
| Apple | 0.0357 | 24.3% | 0.270 | 3.8% |
| OpenAI | 0.0075 | 64.4% | 0.330 | 6.0% |

**Light is closed.** The arc now measures above Apple's and OpenAI's, and it is not gameable: the arc axis
exists precisely because the range is (a blank white rectangle appended to a film took its range from 0.097
to 0.910 while nothing in it changed). **Motion and density did not move** — a change of ground does not
touch either, and both remain 1.7x and 2.3x under their floors. One axis of three; the gate still fails the
film, correctly.

### Motion: what a camera can and cannot buy

Two hypotheses were MEASURED before either was built, and the first was refuted:

**Hard cuts are not the lever.** Removing cut frames from each film's frame-diff series barely moves p75 —
Figma 0.0481 → 0.0419, Anthropic 0.0381 → 0.0305, Apple 0.0357 → 0.0324, ours 0.0022 → 0.0018. Cuts are ~6%
of frames and sit above p75. Our film already cuts 32 times a minute against Apple's 27.8. **The gap is in
the other 94% of frames**: Figma's non-cut p75 is 0.0419 against our 0.0018, 23x. Building the per-seam
hard-cut primitive would have bought nothing.

**A camera is the lever, but only if it TRANSLATES.** Measured on the delivered film:

| | motion p75 |
|---|---|
| as delivered | 0.0023 |
| the existing scale-only camera, stamped on all 30 beats | 0.0029 |
| a lateral pan on all 30 beats | **0.0037** |
| floor | 0.0037 |
| Apple / Figma non-cut | 0.0324 / 0.0419 |

A scale about the content-zone centre barely moves the pixels near that centre, which is where a composed
frame's content sits; and an ease-in-out spends most of its frames at the flat ends. `SceneCamera` gained a
`pan`, budgeted from the overscan the push already buys so it cannot reveal an edge, travelling at constant
velocity through the middle and at rest at both ends.

**It lands the film EXACTLY on the floor, and that is all.** 0.0037 against Apple's 0.0324 non-cut — a tenth.
Passing this floor means "not a slideshow", never "launch-grade". And the pan is OFF unless a beat asks: this
codebase carries a recorded history of shake complaints (the whole-film ambient drift was made opt-in and
defaults to still for that reason), and nothing here can yet certify that a pan on every beat reads as a
camera rather than as restlessness. The number it produces is honest; whether it is *good* is a question the
instruments in this repo cannot answer, and it is left to a human eye rather than stamped on by default.

### The gate you cannot delegate

`film_energy_qa` says the arc landed. Opening the frames says something the numbers cannot: on the beat at
t=26s the hub label `全场景` went from **17.41:1** on the film's native dark to **1.07:1** on the light key —
it is a ghost. `KnowledgeGraph` hardcodes that label's colour instead of reading the DNA's ink, so it passed
the ground-reach sweep's three pixel criteria (the band, the field classification, the moved fraction) and
then lost a word.

That is the standing limit of the allow list, and it is written into `scripts/measure_ground_reach.py`: the
sweep measures whether a declared ground BECOMES THE FRAME, not whether every glyph on it survives. The
`INK_REFUSED` list beside it is HAND-WRITTEN, every entry carries its measurement, and a register's absence
from it means *not yet looked at* — never *checked and safe*. The entry above was found by rendering a whole
film and looking at it, which is how the next one should be expected to turn up too.

### Reverted rather than shipped

A parallel "frame law" change (opt-in full-bleed regions, a title band that could be declined, a declared-crop
audit) was built, reviewed, fixed and then **reverted**. After two rounds it still failed at its own
documented defaults — `grid`/`split` returned regions carrying a mask that faded their CONTENT to zero from
63% of frame height down, and an independent probe found `grid(1920,1080,2,2)` returning one cell instead of
four — while its crop path had *weakened* an existing delivery gate, and nothing used any of it. Full bleed
and frame-cropped type were already legal; what that change added was convenience, and an unused convenience
that is wrong at its defaults is debt, not capability.

## Density: why our frames are empty (measured 2026-09-02)

Five lenses — reference-frame segmentation, web research, our own library, and the image pipeline — produced
29 findings. Two of the most plausible were then REFUTED by experiment, which is the part worth keeping:

**Refuted: the containers are invisible.** All eight DNA presets define `surface` — the documented "container
fill" — within 0.083 of their own `bg` in the gate's colour model, every one under the 0.10 ink threshold
(editorial is 0.020). The theory was that every panel a register draws contributes nothing. Raising
`product`'s surface from Δ0.052 to Δ0.16 and re-rendering four container-bearing registers moved the ink by
**+0.0 to +0.8 points** (BentoReveal 23.3→23.4, TermTable 1.0→1.0). The containers are not invisible; they are
mostly small or absent. A change that would have altered every film's look was not made.

**Refuted: we show too few items.** TermTable with 2 stub rows measures 1.1%; with 5 real rows 4.0%; with 12
real rows across 4 columns **4.7%** — 4.3x for six times the content, and still under half the floor.

**What is actually true.** Text at reading size barely inks a frame. The reference films' ink is opaque
planes and photographs: median feature thickness figma 31.7px, apple 40.8px, openai 57.0px, against our
hairlines. And a full-bleed real photograph, measured on the same instrument, contributes **42.7%–83.0%** —
above Apple's 24.3% on its own. Only ~11 of 149 registers can hold an image at all, `remotion/public/` does
not exist in the checkout, and `PhotoPlate` measures 0.7% because it renders an empty plate.

### Four shared levers built, measured and refuted

Two more were tried after the two above, and the fourth is the instructive one:

* **A divided ground painted UNDER the shot: invisible.** 148 of 149 registers paint their own full-frame
  ground from `dna.bg`, so an underlay is covered. The per-beat ground works precisely because it changes
  `dna.bg` and the REGISTER repaints itself.
* **A divided ground sent through `bgGrad`** — the token 143 registers already pipe into a CSS background —
  **works on the number and fails on the frame.** One declaration took a beat from 5.7% to 14.4% ink, over
  the floor, with zero register edits. Then I looked at it: the register's card straddles the boundary and
  ignores it, so the second ground renders as a coloured MARGIN around a card. The declaration even carried
  a required `reason` ("left is what it does for you, right is what it leaves you") and the frame said none
  of it — a required reason cannot make 149 registers respect a line they do not know about. Reverted.

**There is no shared density lever.** The measured conclusion after four attempts is that density is
per-register composition work. What generalises is DIRECTION, not a mechanism, which is what
`scripts/density_advice.py` does: every family holds both starved and dense registers — F spans 1.3%
(DiffusionDenoise) to 63.9% (AuroraFlow), A spans 1.7% (GrantedTree) to 47.9% (LastLeg), G spans 0.0%
(ScanReconstruct) to 61.3% (PaperCutout) — so a starved beat usually has a denser neighbour on the same
shelf, the one substitution that does not change the film's visual language. On the delivered film it
reports 27 of 30 beats under the floor and names alternatives for 25 of them. It offers CANDIDATES: a
register is chosen because it encodes the beat's idea, and picking whatever measures densest is how a film
ends up carrying ink no viewer can decode.

So density is not a token problem and not a count problem. It is: **compose to FILL rather than to fit**
(`fitContentSquare` returns a 605px square on a 1920px frame; layout.ts reserves 35% of frame height and is
entirely exclusion zones), **give marks mass**, and **put real pictures in the frame**.

### The image channel's honest limit

`imagefetch.py` works on concrete subjects and fails on abstract ones, reproduced here: `"trust"` returns a
1911 political cartoon (*"GOOD TRUST" "BAD TRUST" in Tariff Alley*, from The Masses) and `"office worker
computer"` returns a 1970s archive photograph. A Wikidata `depicts` (P180) filter was proposed as the fix and
does not survive testing: the top entity for "trust" is **Q1641993, a French rock band**, so auto-resolution
would replace one wrong picture with a worse one; multi-word phrases resolve to nothing; and even with a
hand-verified QID the filtered search was not better (on Q161238 the plain search returned an angiogram and
an MRI slice, the filtered one a Bruker scanner and two menstrual-cup studies). `search(depicts=...)` exists
as a precise channel for a caller who has already judged the entity. Nothing resolves a term automatically,
and automatic relevance for an abstract term is **unsolved here** — which bounds how far this lever can go on
a topic like a specific software product, of which Commons has no pictures at all.

## The floors, and what passing them does not buy you

`scripts/film_energy_qa.py` errors below **half the lowest reference** on each axis — motion p75 ≥ 0.0037,
median ink ≥ 12%, luminance range ≥ 0.135. Half, deliberately: this is a floor, not a target, and clearing it
says only that the film is not a slideshow. A deliberately quiet film declares `meta.energy_waiver` **with a
reason**.

**Passing all three does not make a frame good, and the failure mode is specific enough to name.** Rebuilding
one beat to launch grade (`LastLeg`), every one of these went green *before* it was fixed:

* A lit rail and a pulsing field on a **static dark ground** — 15.3% ink but motion 0.0033 and light 0.075.
  Local animation on a still ground is what "it could have been HTML" looks like from the inside. **The ground
  itself has to move.**
* An inset lit panel with a glow: a card floating on a dark page, not ground.
* A field of rounded dashes carrying **49.8% ink that no viewer can decode**. Density wearing content's
  clothes — and the gate applauded it. Replaced with paragraph lines, which on that beat *are* the argument
  (the words the assistant produced; the last mile has none).
* Leg labels set as dark type on dark units at 26 px — unreadable.
* Two labels sharing a corner and overprinting.

So: run the gates to remove the floor cases, then judge the frame. The gates cannot see meaning, decodability,
or overlap. `agents/shot-critic.md` can.

## What to actually do in a shot

* **Let the light carry the argument.** If a beat has a before/after, a covered/uncovered, a known/unknown —
  make one side lit ground and the other dark, and let the boundary move. The luminance arc and the meaning
  become the same fact, which is also the cheapest way to clear the light floor honestly.
* **Move the ground, not just the objects on it.**
* **Fill the frame with the thing being claimed**, not with texture. If the density is not decodable it is
  lint, whatever it measures.
* **Let a display word be cropped**, and invert it across a boundary if the beat has one.
* **Never stop a full-bleed plane at the caption band** — that draws the caption BAR this project forbids
  (measured: 100% band coverage). Fade it out through the band so the subtitle sits on the film's own ground.

## The library is landscape-only until proven otherwise (measured 2026-09-01)

`text_safe_qa.py --library` is clean at 16:9 — 0 findings across 149 registers. At **9:16 it reports 68
findings across 24 registers**, and every single one is a LEFT or RIGHT cut; not one is top or bottom. That is
a single cause, not two dozen: horizontal layouts built at 1920 that do not narrow when the frame does.

Worst offenders: BeforeAfterSlider (9), AnswerStream (6), LiquidChrome (5), SplitFlap / KSpaceAnatomy /
ExplodedSchematic / CompressedSensingEq / ChatThread / CardFlip3D (4 each).

**The delivery path is already protected**: `scan_film` passes the board's `meta.aspect` into every beat's
audit, so a portrait film fails loudly on the beats it actually uses. What the sweep measures is the size of
the POOL a portrait film is choosing from — roughly one register in six is unsafe there. Treat "this register
reflows" as a claim to verify per beat, never as a property of the library.

    python3 scripts/text_safe_qa.py --library --aspect=9:16     # before promising a vertical film
