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

### …and then the frames were compared, and the arc was taken off the default path

The numbers above are real and the film is NOT uniformly better. Rendered and put side by side against the
delivered version, **three of six sampled beats were WORSE**:

* the title card went from white type on near-black to black type on a washed pale ground — it lost its
  impact and reads as unfinished;
* a deliberately sparse terminal beat put its one line of type on a large WHITE field, where the emptiness is
  more glaring, not less;
* a beat whose register title already sat low enough to touch the burned caption became unreadable — two
  whites on near-black are still separable, the same two on a mid-blue ground are mush.

**The cause is structural, not tuning.** `light_plan.py` assigns a ground from the ARGUMENT — where the
content plan says the film turns — and knows nothing about whether the register on that beat was COMPOSED for
a light ground. `GROUND_FOLLOWS_MEASURED` checks that a declared ground reaches the caption band, the content
field and a fraction of moved pixels; it does not check that the frame still holds together. **A register can
follow a ground perfectly and be a worse picture on it.**

So the CAPABILITY stays (per-beat grounds, both exposure keys, 30 preset×key combinations with zero throws)
and the AUTOMATIC ASSIGNMENT came off the default path: `light_plan.py` proposes, prints that it is a
proposal, and `--write` refuses without `--accept-risk`. A pass that can move every number the right way while
making frames worse must not be one flag away from stamping a film.

A worked error from the same investigation, kept because it is the more useful half: seeing the title/caption
collision, I hypothesised that the camera PAN had pushed content down, and bounded the pan by the caption
slack. That bound is correct and stays — a pan really can close that gap — but it did **not** fix the frame.
The collision was already in the delivered film; only the new ground made it fatal. A fix that lands next to
a bug it does not fix is the easiest thing in the world to mistake for a fix. (`band_debt.json`, the sweep
that exists to catch exactly this, does not list that register.)

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

### What the library cannot SAY — the gap that is a capability gap, not a count gap

Clustering all 138 catalogued registers by the ARGUMENT their "use when" describes, and crossing that with
the measured density:

| argument shape | registers | median ink | over the 12% floor |
|---|---|---|---|
| process / pipeline | 12 | 4.0% | **0** |
| structure / what it is made of | **3** | 4.8% | **0** |
| cause / mechanism | 5 | 2.4% | **0** |
| comparison | 9 | 5.4% | 2 |
| quantity | 13 | 4.3% | 4 |
| collection | 17 | 4.8% | 4 |
| described by LOOK, not argument | 68 | 5.7% | **17** |

**The library is dense exactly where it says nothing and empty exactly where it says something.** Of the 32
registers that clear the floor, nine are described by MOOD — "calm premium ambient" (AuroraFlow 64%), "warm
storybook" (PaperCutout 34%), "playful / friendly" (CartoonPop 30%) — and get their pixels from a field or a
texture. Only FIVE were both dense and argumentative. Meanwhile the registers that carry a real subject are
the emptiest in the library: PhotoPlate 0.6% ("the photograph IS the evidence" — it renders an empty plate),
MuseumLabel 0.9%, AtomOrbital 1.2%, PositioningMatrix 0.7%.

By idiom world it says the same thing: `scientific` (23 registers) has **zero** over the floor, so does
`developer-tooling` (13); `photographic` (3) has a median of **0.0%**. The dense worlds are
`motion-graphics` (44, of which 15 clear) and `craft-handmade`. **Every world that carries real subject
matter is starved.**

So the answer to "should the library be bigger" is no in general — 88 of 149 already fail all three floors,
and adding breadth adds work — and yes very specifically: registers for the EXPLANATORY shapes whose density
comes from the content rather than from a field. `MadeOf` is the first (structure): the whole fills the
frame, every region's AREA is its share, and it measures 52.6% ink / 100% footprint / all three floors clear
as film. It is the sixth register in the library to clear all three, and the first for its shape. Process and
mechanism are still at zero.

**Asked structurally, the gap is worse than the prose suggested.** Clustering by keywords is unreliable in
both directions — a narrow vocabulary put "process" at 12 registers, a wide one at 39, and the wide one was
catching ANIMATION verbs ("assemble", "build", "then") rather than process arguments. Asked of the PROPS
instead — which registers accept an ordered list of steps — the library had **two**, and neither does this:
VoiceSignal's `phases` are audio segments and PhaseEncodeStep's `steps` is a count. A film that wanted to say
"this happens in five steps, and here they are" had no register to say it in at all.

`InOrder` fills that: the steps tile the zone, the one the film is on expands and the rest compress, and the
expansion TRAVELS as the narration advances — so the density, the motion and the argument are one object.
Measured as film: ink 37.9%, footprint 100%, motion 0.0079, light 0.153, all three floors clear.

`RestsOn` closes the third. MECHANISM was the hardest because it is a RELATION, relations are conventionally
drawn as boxes and arrows, and a line has no area — which is exactly why the five registers answering "why
does this happen" measured a median of 2.4% ink. The relation had to become a REGION, so here it is LOAD: the
phenomenon spans only as wide as the reason directly beneath it, each deeper reason is broader, and the stack
assembles from the root upward — which is both the explanatory order and where the motion comes from. Measured
as film: ink 47.6%, motion 0.0064, light 0.216.

**The library now has eight registers clearing all three floors, up from five, and all three explanatory
shapes have one.** The three additions differ in what their geometry MEANS, which is what stops them being
one register with three skins: MadeOf's axis is share (area = proportion), InOrder's is time (equal bands,
travelling focus), RestsOn's is depth of explanation (width = how foundational, built bottom-up). A film that
swapped one for another would be making a different claim.

The acceptance bar for any of these has to be BOTH: over the density floor **and** past the hide-the-caption
test. Otherwise what gets added is the tenth mood register, and those are exactly what pulls
`density_advice.py`'s suggestions off the argument.

### The rules that DO transfer, and what applying one actually cost

Density has no shared mechanism, but it has shared RULES, and they came out of measurement rather than taste.
They live in `runtime/dna.tsx` as `separated` / `separatedPair` / `readableOn` / `dimOn` / `contrastOf`, and
`register_energy.py` gained the axis that tells an author WHICH rule a register needs:

**Footprint — the ink's bounding box** — separates the two ways a frame is empty, which need opposite fixes:

| | ink | footprint | |
|---|---|---|---|
| TermTree | 1.1% | 9.0% | **small** — composed at a ninth of the frame |
| QuadSplit | 3.9% | 11.3% | small |
| TimelineTravel | 1.5% | 14.4% | small |
| GrantedTree | 1.8% | 18.6% | small |
| VersusSplit | 3.2% | 53.2% | **flat** — spans the frame, every region within 0.10 of the ground |
| CardStack3D | 2.9% | 57.1% | flat |

**A worked example, and it took five iterations.** VersusSplit already paints two halves; its own comment
records a previous author cutting the mix from 0.22 to 0.11 because a brighter frame would leave "the rest of
a dark film" behind — a premise this runtime has since falsified. Fixing it:

1. `separated()` each half from the ground → 3.2% → **3.3%**. Ink is measured against the frame's OWN median,
   and two halves covering the frame CREATE that median between them.
2. `separatedPair()` — separate from each other by twice the step → **51.1%**. And the right column's text
   dropped to 2.57:1, because the register reads its ink tokens once, for the ground it used to have.
3. `readableOn()` + a fixed 28% dim → still 2.63:1. A fraction is a bet on how light the ground is.
4. `dimOn()` with a 4.5:1 floor, picked against the half → better, still weak: a winning panel paints
   `${tone}2e` OVER its half, so the text sits on a composite the picker never saw. Pick against that.
5. The WINNER chip made from the accent → `separated()` THREW, correctly: the half had been mixed toward
   that same accent, so they are one tone. The chip steps toward whichever pole has headroom instead.

Final: **3.2% → 51.1%**, above Figma's 36.1%, with every primary element legible — and byte-identical with no
DNA, because `test_null_dna_preserves_every_original_colour` is a contract worth keeping and the derivation
belongs where a design system is present.

### The diagnostic was measuring a mode no film uses

Found by auditing my own work, and it is the most consequential correction in this file:
`register_energy.py` swept with NO `--props`, which renders the UN-THEMED fallback — the branch a register
takes when `useDNA()` returns null. That is the path `test_null_dna_preserves_every_original_colour`
deliberately freezes, so the three registers improved for themed films measured in the manifest exactly as
they had before the work. CardStack3D read **0.6%** in the committed sweep on the same day it measured
**32.2%** under `dna=product`, and nothing anywhere said the two numbers were about different renders.

Re-swept on the themed path (`--dna=product`, now the default; `--dna=none` measures the fallback):

| | un-themed (old basis) | themed (correct basis) |
|---|---|---|
| VersusSplit | 2.0% | **50.9%** |
| CardStack3D | 0.6% | **6.7%** |
| TermTree | 1.0% | 2.4% |
| library median | 4.8% | 4.8% |
| under all three floors | 92/149 | 88/149 |

The aggregate barely moves — most registers do not branch on the DNA for their density — but for anything
that HAS been worked on, the two bases differ by an order of magnitude, which is exactly when a diagnostic
is trusted most.

**A video median and a settled still answer different questions.** CardStack3D measures 6.7% as film and
32.2% as a still, because its cards fly in over the shot and the median frame has fewer of them. Neither is
wrong; the manifest records the film number, which is the one a viewer experiences.

**And a record nobody can tell is stale is a lie with a timestamp.** The manifest now carries each register's
source hash, `--check` reports which rows no longer describe their source without rendering anything, and
`density_advice.py` REFUSES to advise from a stale sweep — it would otherwise have named one of the densest
registers in the library as a starved beat's problem.

### Three registers done, and what each class actually buys

| register | class | before | after | |
|---|---|---|---|---|
| VersusSplit | flat | 3.2% | **51.1%** | two halves that separate from EACH OTHER |
| CardStack3D | flat | 2.9% | **32.2%** | a container fill that clears its own ground |
| TermTree | small | 1.1% | 2.4% | footprint 9.0% → 26.4%, and ink barely moves |

**The `flat` class closes; the `small` class does not close on its own.** Filling the frame fixed TermTree's
composition — a terminal tree set at a literal 40px occupied a ninth of a 1920-wide frame, and now it reads
at the scale the frame deserves — but ink went 1.1% → 2.4%, because text at reading size barely inks
anything. A text-dominant register needs BOTH: fill the frame AND put a surface under the type. That is the
rule the three of them together establish, and neither number alone would have found it.

Two more things the work turned up, both invisible from the outside:

* **The step must be measured against the frame's median, not the ground TOKEN, and those differ.** A
  register painting `bgGrad` (a radial field) had a median of 0.067 where its `bg` token is 0.027 — and the
  median then rose again as the cards themselves lifted it. Derived to exactly 0.10, a card face covering
  26% of the frame missed being counted by 0.007. `surfaceOn` therefore clears with 1.5x headroom.
* **A gradient is a surface only where all of it is one.** Fixing CardStack3D's first colour stop and leaving
  its second — a hardcoded near-black — moved it 2.9% → 3.1%. Both stops cleared: 32.2%.

That is what one register costs. There are roughly a hundred more, and `scripts/density_advice.py` says which
ones a given film is actually starved by.

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

## The motion axis: shake is the cheapest way to pass the motion gate

Measured on this repo's own renders, `film_energy_qa`'s motion score cannot tell the best use of movement
from the worst:

| film                         | motion_p75 |
|------------------------------|-----------:|
| locked camera                |     0.0036 |
| the same film, 1px jitter    |     0.0051 |
| the same film, 3px jitter    |     0.0077 |

The delivery floor is 0.0037. A film sitting under it clears it at **double** by vibrating, and the gate
turns greener as the defect arrives. That is why the camera has been locked by default since the shake
repair: the lock is a floor on shake AND a ceiling on motion, and the ceiling could not be raised while the
floor was assumed rather than measured.

`scripts/shake_qa.py` measures it. The discriminant is a RATIO, not a magnitude — over half-second windows,
does the frame TRAVEL (path ≈ net displacement) or VIBRATE (long path, no net)? Calibrated on eight rendered
controls:

| control                                   | wander p90 | windows shaking | verdict |
|-------------------------------------------|-----------:|----------------:|---------|
| locked camera                             |       1.15 |              2% | ok      |
| smooth pan (real travel)                  |       1.53 |              4% | ok      |
| chaotic generative content, locked camera |       3.22 |              3% | ok      |
| minimal title card, locked camera         |       1.05 |              0% | ok      |
| sub-pixel shake (0.5px)                   |      23.42 |             67% | SHAKE   |
| jitter 1px                                |      21.42 |             73% | SHAKE   |
| jitter 3px                                |      27.30 |             80% | SHAKE   |
| minimal title card + 1px                  |      17.65 |             78% | SHAKE   |

Global translation is the measured quantity, so content moving INSIDE a still frame is invisible to it by
design — which is also the finding that says where the motion axis can safely grow.

## Where the motion actually dies: reveal, then freeze

Frame difference by quarter of each register's own clip:

| register          | Q1     | Q2     | Q3     | Q4     | p75    |
|-------------------|--------|--------|--------|--------|--------|
| CinematicTitle    | 0.0015 | 0.0009 | 0.0001 | 0.0000 | 0.0003 |
| BentoReveal       | 0.0061 | 0.0006 | 0.0005 | 0.0002 | 0.0008 |
| ClayStack         | 0.0098 | 0.0121 | 0.0008 | 0.0002 | 0.0058 |
| ChartLive         | 0.0030 | 0.0055 | 0.0029 | 0.0000 | 0.0042 |
| KnowledgeGraph    | 0.0002 | 0.0004 | 0.0005 | 0.0003 | 0.0005 |
| MorphForms        | 0.0168 | 0.0309 | 0.0148 | 0.0151 | 0.0275 |

The deficit is not the camera and it is not the reveal — it is the HOLD. Most registers finish their
argument in the first half of the clip and then show a still photograph for the rest, while the narration
keeps going. MorphForms, the one that clears the floor comfortably, is the one that never stops developing.

A uniform drift added to all 152 registers would raise the number and would be decoration — the frame would
move without meaning anything, which this repo's own design rule forbids. The direction that is both safe
(invisible to shake_qa) and honest is per-register CONTINUING LIFE: a dashboard whose gauges keep reading, a
graph whose nodes keep orbiting, a field that keeps flowing. A frozen frame is a screenshot; this tier is
supposed to be film.

## What a mature peer library does that this one does not (measured, 2026-09-05)

`video-shotcraft` (218 implemented shots / 157 catalogue cards) was downloaded and compared item by item. It
runs the SAME stack — Remotion 4 + React, CSS 3D on both sides, no three.js in either shot library — so the
comparison is like for like rather than an impression.

| | video-shotcraft | this tier |
|---|---:|---:|
| shots | 218 | 152 |
| median lines per shot | 135 | 77 |
| any 3D | 38 (17%) | 11 (7%) |
| `perspective` | 34 | 10 |
| `rotateX` (pitch) | 24 | **2** |
| `blur()` | 76 (35%) | 17 (11%) |
| `spring` | 24 | **3** |
| seam vocabulary | 18 transition cards + 6 hand-off recipes | 5, all planar |

### The three capability gaps

1. **The camera has push and pull; it has no SPACE.** Their `basic-3d-scene` is one formula —
   `camera = stepTransform.inverse()` — with cards posed anywhere in 3D and the camera flying to align with
   each. Paging becomes travel through the idea's space. `cube-navigation`, `terminal-3d` and `flying-words`
   (keywords rushing past the lens down a z tunnel) build on it. Our `SceneCamera` is scale + 2D translate;
   `rotateX` appears in two registers in the whole library.
2. **Focus is not part of our language.** Theirs is structural: `depth-layer-moves` builds depth from three
   parallax coefficients (0.35 / 0.7 / 1.4) plus fore/background blur plus desaturation, with the rule
   "without the blur/saturation anchor it reads as stickers flying"; a fake dolly-zoom pins the subject while
   the background swells 1→2.25. Our blur is almost entirely frosted-glass panels; no register uses focus as
   an argument.
3. **Every seam we ship is planar.** Three of their six hand-off recipes are built on depth: through-dark
   flight, focus relay (the focal plane IS the cut point), portal wipe. Their stated bar: "no acclaimed
   launch film cuts bare, ever." ALL THREE have since been built — see Film.tsx FocusRelayPresentation,
   ThroughDarkPresentation and PortalPresentation. Only the focus relay's PARAMETERS were recorded in this
   study (their case law was quoted verbatim); the other two were recorded by name only and the library is
   no longer on disk, so their numbers are derived here and their headers say so.

### The form of their documentation is itself a capability

Every shot card is: one-line identity / when to use / duration / energy / motion core / **a parameter table
where each row carries the FEEL of turning that knob** / **known traps** / reference implementation. And
their `aesthetic-rules.md` is CASE LAW: every rule is (an executable sentence) + (the case: the user's own
words and the rework history) + (a self-check question), numbered R/Q/S/C/P, never renumbered, append-only,
and walked item by item at acceptance with a `N ✓` / `N ✗(where)` report. Deliberate violations must be
written down.

This repo has at least as much hard-won case knowledge — it is in commit messages and docstrings, where no
reviewer walks it. That is the gap worth closing next, and it is not a shot.

### Where this tier is ahead, for the record

`textShadow` 48 vs 9, `drop-shadow` 24 vs 13, `burst`/`trail` higher. More importantly it has things they do
not: a Design DNA carrying one visual system across a whole film, per-beat re-grounding (`light.tsx`), and
measured gates — `film_energy_qa`, `shake_qa` (+ `flicker`), `clock_qa`, `text_safe_qa`. Their equivalent of
Q3 ("keep the camera steady — no handheld shake") is a doctrine enforced by review; ours is an instrument
calibrated on eight controls. Their R2 ("uniform motion reads as cheap PowerPoint") was checked against this
library and found clean: zero raw-`t` lerps, 121 of 152 registers using an easing.


### Borrowed since, and how (2026-09-05)

Three pieces of the peer library's case law were taken as ESSENCE, each landing on the authoring path and
each verified on a real film rather than on its own exit code:

- **Depth** (`4b4e8ce`): the `focus` seam (a rack-focus relay between two beats) and the Plane anchors our
  planes lacked (desaturation, foreground defocus with a dead zone, drift per depth unit). Verified by direct
  pixel A/B, after two self-made depth metrics failed their positive controls and were dropped.
- **The sound sentence** (`5322966`): cues chosen by PICTURE KIND, never UI event — their "太像游戏了" case.
  The film's close lands riser → impact → sparkle instead of a bell; the SFX bus is split in-graph into a
  >800 Hz and a <110 Hz band so the impact's body survives while the voice band is untouched; a scored film
  also ships an `out.nobgm.mp4` twin. Auditioned by measurement on a 30-beat narrated film (riser in the seam
  pause, impact in the silence before the closing line, true peak −1.5 dBTP).
- **The energy skeleton** (`scripts/energy_skeleton.py`): their "fill the skeleton first, then pick the
  cards" and "连续高能量读作嘈杂". The plan already declared an energy per beat and the sweep already measured a
  motion per register; nothing read one against the other, and a delivered film's climax sat on a register
  under the motion floor. Now `validate.py` reports the mismatches with alternatives, and the deterministic
  director prefers an in-band register and gives the peak the liveliest (5 hard findings → 0 on that plan).

Their hold/rest rule (R1: ≥1s hold at the open and the sign-off; R3: "the first version is always too
fast") was measured rather than ported: interior seams already get a derived pause (tts.py), the ending hold
on the delivered film is 0.95s, and the first word arrives at 0.20s. Lengthening either is NOT a one-line
pad change — Film.tsx and the SRT mirror time each beat's caption chunks over the clip, not the speech, so a
longer tail would drag the last captions late. The correct version times captions over the speech span
(tts.py knows the pad it added); it is a follow-up with its own render check, not part of the skeleton.
- **The deck as the brand** (`scripts/dna_from_deck.py`, `scripts/pptx_theme.py`): their films are built from the
  product's own identity; ours painted every deck with a direction's preset. The pptx theme (scheme colours
  with sysClr resolved, major/minor faces, the master ground through its clrMap) and the rendered frames
  (pixel-weighted, spread through the deck; the accent from a hue histogram of the saturated pixels) now
  become a complete `meta.design_dna` with a provenance block. Verified by rendering: a Philips-blue research
  deck came out Philips blue with white type and an orange counter through BentoReveal and SwissEditorial; a
  violet-branded WorkBuddy deck (Office-default theme, so the frames decided) came out violet on warm white.
  Two sampler defects were caught by looking, not by tests: an unweighted palette read a white deck as dark,
  and a six-colour quantisation reported a violet brand as teal.
