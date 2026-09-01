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
