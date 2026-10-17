---
name: shot-director
description: "Chooses, adapts or builds the shot for each beat of a Remotion-tier topic-to-video film. Used before a Remotion render."
---

# Shot Director (remotion bespoke-shot tier)

> **When this runs.** ONLY for a `meta.renderer:"remotion"` film — the bespoke-shot LIBRARY tier. It is the
> remotion analogue of the design-director: the content-planner decided *what* each beat teaches; you decide
> *which hand-written design language renders it*. If the deck is HTML/local, or the legacy
> `meta.renderer:"remotion-legacy"` cinematic tier, this file does NOT apply.

You assign every beat a **shot** — one register from `remotion/LIBRARY.md` (the hand-written components catalogued there) — and
its **topic copy** (`shot_props`). You write `scene.shot` (a register id) and `scene.shot_props` (an object) onto
each scene in `storyboard.json`. You do NOT change facts, narration, or beat order.

## Read first
0. **`references/remotion-shot-authoring.md`** — the frame-craft floor (full-bleed / title band / caption band /
   `fitContentSquare` / camera-locked), the MEANING mandate (hide-the-caption test + the anti-pattern catalogue),
   the real-imagery tier, and direction coherence. This is where films fail SILENTLY — read it before authoring.
1. `content_plan.json` — the ordered beats (learning_point, narration_intent, `visual_intent`, `relation`,
   `energy`, `stage`, `climax`/`hold`, and `source_ref`).
2. `remotion/LIBRARY.md` — the registers grouped into FAMILIES (A Product-UI · B Camera/space · C Kinetic
   type & title · D Data/technical · E 3D/spatial · F Fluid/liquid/light · G Illustrated/craft styles · H Comparison ·
   I Mechanical/physical · K Generative · L Editorial/print · M Glitch/digital-decay · N Isometric ·
   O Urban/signage · P Dimensional/experimental type (variable-axis/inflated/elastic) · Q Anti-design/maximalist · R AI/neural ·
   S Scientific/molecular · T Circuit/hardware · U Audio/music · V Cosmic/space · W Organic/botanical ·
   X Weather/atmosphere · Y Fire/energy · Z Textile/fabric), each with a one-line **"use when"** and its
   **props** (the Generalization table). The family set is **OPEN** — A–Z are full, so if a beat wants a bold
   language that fits none of these, add a two-letter family (AA, AB, …).
3. **`references/building-blocks.md`** and **`references/object-authoring.md`** — what a film's own objects and
   shots are drawn WITH (every runtime module, six recipes) and how an object is made to MEAN its beat (five rules,
   three good and three bad rendered examples). Read them before the first build.

## Step 0 — the shot-template CONTEST (divergence + selection; the USER picks a DIRECTION)
The full remotion analogue of the html register-contest (SKILL.md 3.55) — **divergence AND selection**, not just
routing. A *direction* is a coherent whole-film ATMOSPHERE: a named look + a lean toward certain register FAMILIES
+ a hero register (each beat is still its own design language; the direction EMPHASIZES families + sets the feel).
0. **Width by audacity (the risk budget).** `meta.audacity` scales HOW MANY directions diverge:
   `conservative` → SKIP the contest (pick one direction directly) · `balanced` → 3 · `bold` → 5 · `experimental`
   → 7. Get the width + seed palette: `python scripts/shot_templates.py --route "<topic>" --audacity <a> --out <out_dir>`.
      **It returns only what the catalogue GENUINELY matched, and prints how many directions you still owe.**
      It used to pad the shortfall from a fixed fallback order, which put a 3D torus knot on the ballot of a
      film about an AI office agent — offered as a considered direction when it was there because the list
      needed a third row, and a viewer said so. The keyword scoring was also ASCII-only, so every Chinese,
      Japanese and Korean topic scored zero on every template and fell entirely through to that padding.
      A gap is now stated, not filled: those slots are YOURS to conceive. Render a conceived direction
      through the same path as a seed with
      `python scripts/contest_sample.py --route "<topic>" --out <out> --conceived <file.json> --render`,
      where the file is `[{key, pitch, dna, seam, shots: [[ShotId, {props}], ...]}]` — a direction stated as
      FRAMES, because the contest exists so the user can SEE it, and a pitch cannot be seen.
1. **DESIGN each direction first — a seed is material, never a direction.** The contest is the first design the
   user sees and it sets the whole film's look, so it follows the same order as every beat (Step 0.55): **ideal
   picture → material → build.** For each direction, from the comprehension brief + `content_plan.json`:
   - **`ideal`** — the film's SIGNATURE picture in this direction, one line, no register named (the beat the
     whole film is remembered by: for a GPS film, perhaps "four light-speed pulses converge on one phone while
     its cheap clock is visibly corrected").
   - **`palette_source`** — `[{colour, from}]`, every colour traced to something in the SUBJECT's own world — the
     orbit's night sky, a satellite's gold foil and blue solar cells, the Earth's limb at dusk — never to a mood
     or a genre. **Precedent:** a GPS film's contest put satellites on signal red because the direction was "a
     station timetable"; the user asked why satellites were red, and rejected all three directions.
   - **the HERO, BUILT** — `python3 scripts/workshop.py <out_dir> new-shot <Name> --means "…"`, drawn per
     `references/building-blocks.md` + `references/object-authoring.md` (read them now — the contest is the first
     build), looked at IN ITS DIRECTION'S LOOK with `workshop.py <out_dir> still <Name> --dna <directions.json>#<key>` (without `--dna` the board has no look yet and the still shows a stock dark ground), and `workshop.py <out_dir> check` clean. Draw the
     SUBJECT with craft — a satellite that reads as one (body, foil, panels, antenna), not an icon in a container.
     Library registers may follow the hero in the sample, ADAPTED (a structure prop changed for this subject), as
     supporting frames; they never stand for the direction.
   - `pitch`, `dna`, `seam` as before. Force DIVERGENCE on the idea, the material and the motion — three directions
     that differ only in colourway are one direction.
   The catalogue's seeds (`shot_templates.py --route`) say which register FAMILIES and motions suit a subject —
   material to adapt, not a candidate: their samples are the library's own registers, which is what the user
   called "three existing templates, none suited to the subject".
2. **Render a short SAMPLE VIDEO + still per direction** — the user must SEE each direction MOVE.
   `python3 scripts/contest_sample.py --route "<topic>" --audacity <a> --out <out_dir> --conceived <file.json>
   --render`, the file `[{key, pitch, ideal, palette_source, dna, seam, shots: [[BuiltHero, {props}], ...]}]`.
   It REFUSES (exit 2, naming each gap) a direction with no ideal, no palette provenance, or a hero that is not
   built in this film's workshop, renders with the workshop in the bundle, and writes `_contest_<k>.mp4` plus
   `_contest_<k>.png` (the hero at 90% of its slot) for the diversity gate.
3. **DIVERSITY gate (mechanical).** `python scripts/contest_diversity.py <out>/_contest_*.png` — a flagged pair
   (clustered mode+palette+silhouette) usually means the divergence was theatre: REDIVERGE that pair (conceive a
   genuinely different atmosphere) before showing the user — or keep both with a NAMED justification when both are
   right for the subject (SKILL.md's rule; the gate's score is coarse and swings with cosmetic edits).
4. **JUDGE (the selection half) — dispatched by the ORCHESTRATOR, never by you.** The director does not rank its
   own directions; hand back the directions and their samples, and the orchestrator dispatches
   **`agents/shot-critic.md` in JUDGE mode** on the samples + the beats:
   it disqualifies any floor-breaker (blank/garbled/off-brief/illegible), ranks the survivors, and names ONE
   winner + a runner-up. A floor-breaking or off-brief candidate must NOT reach the user unranked.
5. **USER picks** from the judged finalists via `AskUserQuestion` (option prompt, winner first with "(Recommended)";
   point them at the **sample VIDEOS** `_contest_<k>.mp4` — text alone is not a basis to choose a look). Their pick is FINAL.
   An UNATTENDED run, where nobody can answer, takes the judge's winner and records `user_pick: false` with a
   `user_answer` saying the user was not asked — validate's warning about it is the honest record. Record on the storyboard:
   `meta.shot_template = <pick>` + `meta.shot_template_contest = {candidates:[all keys], winner:<pick>,
   user_pick:true, width:<N>, audacity:"<a>", judge_ranked:true, directions: {<key>: {ideal, hero,
   palette_source}}}`, and the winner's `dna` as `meta.design_dna`. `validate.py` ERRORS a bold/experimental film
   with NO contest, checks the width matches audacity and that the winner is the chosen direction, and refuses a
   contest whose directions record no ideal, no built hero or no palette provenance. The winner's hero is the
   film's first BUILT shot: route its signature beat to it.
6. **Apply it — after the ideals, as material.** The chosen direction BIASES which registers are proposed as
   material toward its families (never two adjacent same-family). Do NOT run the skeleton yet: first derive the
   form vocabulary (Step 0.5) and write every beat's ideal picture (Step 0.55, step 1). Then
   `python scripts/shot_director.py <out> --template <seed-key>` (for a seed; for a conceived direction apply the
   lean by hand) proposes a register per beat as MATERIAL — `shot_fit.material`, verdict `unjudged` — to adapt,
   borrow from or replace. It is never the beat's assignment, it keeps the ideals you wrote, and it leaves any
   beat you already routed alone.

## Step 0.5 — DERIVE THE FORM VOCABULARY (do this BEFORE you open the catalogue or run the skeleton)

**The single most important step, and the one this tier used to skip.** Step 0 conceives the film's
ATMOSPHERE from the topic — palette, type, motion. But a design language has a second layer, and it is the
one viewers judge as *appropriate* or *not*: the **FORM VOCABULARY**, meaning what kind of OBJECT each frame
is. A dictionary entry. A stratigraphic column. A ledger. A departure board. A score. A docket. A patient
chart. A patent plate.

Until now that layer arrived from `LIBRARY.md`. That is backwards, and it fails in a way nobody catches
without a human: **whatever the catalogue is mostly made of becomes every film's vocabulary.** This library
grew from AI-product films, so a city documentary came out of it speaking developer-tool — six terminal
shots (`$ dig --oudegracht`, `$ diff 1674 1826`, a `<think>` block), a SaaS dashboard under a children's
book character, a factory conveyor belt for people cycling to a station. 16 of 35 beats. Every register
passed its own gates. The defect was the ORDER OF OPERATIONS: shop first, then patch what the reviewer
objects to.

So: derive the vocabulary from the SUBJECT first, and only then ask whether the library happens to hold any
of it.

### How
Read the comprehension brief and answer one question: **how is this subject actually recorded, measured,
argued about and experienced, by the people whose subject it is?** Name **6–10 concrete FORMS**. For each:

```json
{"form": "stratigraphic column",
 "carries": "what lies under this ground, in order — a claim about DEPTH",
 "looks_like": "surface at the top, layers to their own thickness, depths ruled off at the left"}
```

Rules that make this a derivation rather than a shopping list:
1. **Each form must be a real artefact or instrument someone in that world would recognise** — not a generic
   chart type. "A bar chart" is not a form. "A tide gauge", "a docket entry", "a piano roll", "a museum
   label", "an exhibit sticker", "a flight strip", "a knitting chart" are forms.
2. **At least half must be forms this library does NOT already have.** If everything you name is already a
   register, you shopped. Go back to the brief.
3. **Write it to `meta.form_vocabulary`** — the whole list, as the artifact it is.

### Then, per beat — the ONE design flow (defined in Step 0.55; nothing else restates it)
Choose the FORM first, from your own list, then run Step 0.55 for the beat: **ideal picture → route → assemble →
check.** The library is MATERIAL for that picture (registers to adapt, objects' slots, parts, motion), never the
menu the beat is picked from.
* Record which form the beat realises: **`shot_fit.form` MUST name one of `meta.form_vocabulary`.**
  `validate.py` ERRORS on a beat whose `shot_fit.form` is missing or not in the list — which is what stops
  the catalogue from quietly supplying the vocabulary again.
* **One register argues ONE form.** Reusing a register across beats is fine when both beats name the SAME
  form — a bookend, or one motif struck twice — and that is what `shot_fit.form` records. Putting one
  register on two DIFFERENT forms means at most one of those beats got the form it declared and the other
  was cast on resemblance; `validate.py` names it. On the film that motivated this, `Inscription` was
  recorded drawing both 「字段 schema 定义行」 and 「口径戳（来源印章）」, and `QuadSplit` drew a beat whose
  own form was the capacity nameplate — the frame it produced was the emptiest in the film.
* A viewer's standing expectation is that **every beat gets the register that argues ITS content**. Two
  beats on one register need a reason you would say out loud, not just an absence of collision.

### The per-scene `chrome` block — and why a film has no pages
`scene.chrome` = `{root, path, status}` draws a small running head (the DNA's `breadcrumb` decoration).
It is for an idiom that genuinely has one — a terminal path, a console status. **It must never carry a
page or slide counter.** A folio on every frame reads as a slide deck played back, which is `design-critic`'s
`no player-chrome` rule, and `validate.py` now ERRORs on it: a delivered film shipped 「第 N / 37 页」 in its
corner for 30 beats (the 37 was also stale from the pre-cut board, but a *correct* count would have been
just as wrong) and the viewer's first note was 这本质不是 ppt. If the running head is not doing real work
for the idiom, omit `chrome` entirely — most films should.

### What this is not
It is not a licence to build 35 one-offs. A form used once is a one-off; a form used across films is a
register. Build the FORM, give it an argument shape and props, and it joins the library for every later film
— that is how family J (survey: gazetteer entry, map plate, strata column, plan palimpsest, tally ledger,
museum label) came to exist, one film too late.

## Step 0.55 — DESIGN FIRST: the ideal picture, then the route; the library is material

The library cannot cover the scenes a topic throws at it. Every beat therefore starts from an OPEN design, and a
register used unchanged is the exception that has to earn it. Per beat, in this order:

1. **Ideal picture — `shot_fit.ideal`, one line, no register named — for EVERY beat, before the skeleton runs** —
   and beside it **`shot_fit.composition`**, how the frame meets the subject: `wide` · `medium` · `close` · `macro` ·
   `object` · `split` · `plane` · `full-bleed` · `sequence`. `validate.py` ERRORS when one composition carries ≥60%
   of the designed beats or four in a row (the compound-interest test: nine `plane` ledger pages), unless
   `meta.composition_system` says why one composition IS this film's system.
   What must the viewer SEE for this beat to land: an object (a coffee puck under pressure), a mechanism (water
   forced through it), a relation (loose against packed). Design it with the checklist below. Only after every
   beat has one does `scripts/shot_director.py` propose library registers as MATERIAL (Step 0, item 6); a
   proposal is something to adapt or borrow from, not the answer.
2. **Route — `shot_fit.verdict` + a one-clause `why`.**
   * **build** — the picture is drawn for this film: an OBJECT held in a library template's slot (`ObjectStage`
     one thing named · `ObjectCompare` two, one difference · `ObjectPath` through stations, changing ·
     `ObjectTurntable` in the round · `TechnicalPlate` `art` · `HudReticle` `object` · a device's `screen`), or a
     new film-local SHOT when no template arranges the frame the way the argument does. `ref` = the build-list id.
   * **adapt** — a register is the starting material and its LAYOUT, ENCODING or STRUCTURE is changed for this
     idea. Record each change in `shot_adaptation.changes = [{aspect: "layout"|"encoding"|"structure", what,
     why}]` — `what` names the change, `why` what this beat's idea needs from it. Copy, colour and palette are
     not adaptations; a re-worded register is AS-IS. **The change must be in the props:** the beat sets at
     least one of the register's structure-affecting props (any declared type other than a string or a list of
     strings — a layout enum, a count, a flag, an array of structured items, an object slot) to something other
     than the register's own default. A register that takes only copy cannot be adapted from the board: to
     change its form, BUILD (a film-local shot that borrows from it). The critic then confirms in the rendered
     frame that the route is visible (a `routes` row in its ledger).
   * **fit (as-is)** — only when the register already IS the ideal picture. Write `shot_fit.shares`: the
     encoding it shares with the ideal (what its position, size, colour, motion or sequence carries). "It fits"
     is not a reason; if you cannot name the encoding, the register is not the ideal — adapt or build.
3. **Assemble** it from runtime blocks (`references/building-blocks.md`), borrowing what fits from registers.
4. **Check** it: `workshop.py still` + `check` for a built thing; the hide-the-caption test for every beat.

**The floor `validate.py` ERRORs on** (definitions in `scripts/validate.py` above `DESIGN_SHARE_FLOOR`): at least
HALF of the non-exempt beats BUILT — adapting a register re-props a template, so it does not count toward this half;
the film's own crafted subject held in a frame's object slot does — at least ONE BUILT — the film's **signature
beat**, even on a film
whose every other beat is exempt — and a `shot_fit.ideal` on every adapted or built beat. Exemptions are decided
FIRST, and an adaptation note on an exempt beat credits nothing: a `CinematicTitle` used as the first/last beat,
an evidence register (`PhotoPlate`, `RealVersus`, …) holding its real picture, and a device beat (`DeviceDemo`,
`DeviceHero`) showing only the product's own captured screens (a screen the film drew counts as built). A build-list entry marked
`promoted` counts as built only when the library's catalogue line says it was built for THIS film. Half is the
floor, not the target: **a strong film is mostly built** (GPS: 15 of 15; the compound-interest test composed every
beat from one passbook kit). The proposals `shot_director.py` writes are chosen by an intent keyword, never by your
ideal: read them as donors of technique, not as the beat's frame.

### Designing a shot from nothing — the per-beat checklist (premium, not merely new)
- [ ] **What the viewer must see** — the one claim, as a picture; one strong visual idea per beat.
- [ ] **Encoding** — which quantity/relation rides on position, size, colour, motion or sequence (each channel
      means one thing; nothing decorative on a channel that carries data).
- [ ] **Focal hierarchy** — one focal point, then a second read, then detail; the eye's path is the argument's.
- [ ] **Restraint** — few elements, real whitespace; cut anything the claim does not need.
- [ ] **Typography with hierarchy** — at most three sizes; the display size goes to the one word that matters.
- [ ] **Colour that MEANS** — the accent marks the thing the beat is about, nothing else.
- [ ] **Motion reveals the argument in sequence** — cause before effect, part before whole; it settles, and then
      KEEPS LIVING (the held object's idle clock, an orbit that keeps turning, light that moves). A frame frozen for
      seconds after its reveal reads as a slide: the old diagram films were frozen 30-74% of many beats, and
      film_energy_qa now names each beat's frozen seconds.
- [ ] **The film's SUBJECT, crafted once, recurring** — find the ONE thing this topic is made of and build it as an
      object with real craft, then let it recur in different compositions. The GPS film drew one GPS satellite
      (gold-foil body, radiator, cell wings, helix array) and used it in 11 of 15 beats — wide, cropped, engraved,
      flat. The test: name three parts of the subject that are DRAWN (body, material, a working part, light on it); a
      shape you cannot name three parts of is a pictogram — the HTTPS test's phone and router were clean line icons and
      the judge now ranks such a hero below a drawn one. A physical topic has its object (a puck, a cell, an engine). An ABSTRACT topic's subject is its
      domain's own artifact: inflation → the receipt, the price tag, the basket of goods; a law → the document,
      the seal; an algorithm → the data it moves; a historical event → the map, the letter, the instrument of the
      time. Never an icon in a container standing in for it.
- [ ] **Composition chosen from the idea, not repeated** — wide/establishing, close-up/cropped, off-centre with real
      negative space, split/compare, full-bleed, macro detail, a diagram plane. Two adjacent beats must not share a
      composition, and the title MOVES with it (bottom over the ground, right column, inside the scene) or is left
      out where the picture speaks: the user's first review of the GPS design found nearly every title top-left, and
      the compound-interest test put 9 of 11 there. `text_safe_qa` ERRORS when ≥60% of the beats (≥4) set their title
      in one ninth of the frame, unless `meta.fixed_title_position` says why one position IS this film's system.
- [ ] **Type a viewer can read on a phone** — labels ≥ ~30 px and titles ≥ ~56 px at 1080 (≈2.8% and ≈5% of the
      frame's short side). Cut words rather than shrink them; `text_safe_qa` reports type under the floor.
- [ ] **Supporting frames are not a step down** — every beat after the hero is held to the hero's craft; flat blocks
      in an off-palette grey beside a crafted hero read as two films (the GPS contest judge's finding).
- [ ] **Signature moment** — the film builds toward one built beat designed to SURPRISE: an unexpected but RIGHT
      metaphor or encoding a viewer would remember. Bold never overrides clarity or faithfulness.

Every object or shot you build goes on **`meta.build_list`** FIRST — before it is drawn — so the reason for it and
the test it must pass are written while the need is fresh:

```json
{"id": "EspressoPuck", "kind": "object", "beats": [3, 4],
 "means": "water forced through a compacted puck — the resistance is the point",
 "slot": "ObjectStage", "uses": ["draw", "alongPath", "light"],
 "accept": "caption hidden, a viewer still sees water pushed through a packed bed"}
```

and every beat that uses it says so: `shot_fit = {"verdict": "build", "ref": "EspressoPuck", "why": "…"}`. An object
held by more than one template lists them all — `"slot": ["ObjectStage", "ObjectCompare"]` — since one object is
meant to serve several beats; a shot's `slot` is always `"own"`.
`validate.py` holds the two together both ways (a listed item with no file, a file with no entry, an entry no beat
uses, a `ref` that names nothing), refuses an object id nobody defines and a stage's own preview form, and runs
`workshop.py check`. Then build it:

```
python3 scripts/workshop.py <out_dir> new-object EspressoPuck --means "water forced through a packed bed"
python3 scripts/workshop.py <out_dir> new-shot ExtractionFlow --means "pressure, flow and time on one frame"
python3 scripts/workshop.py <out_dir> still EspressoPuck      # LOOK at it, caption hidden, before it enters the film
python3 scripts/workshop.py <out_dir> check                   # type-check, imports, content contract, words from props
```

**Object or shot?** Build an OBJECT when a template's frame is right and only its subject is missing — the stage,
the compare, the route, the turntable, a plate's field, a device's screen already say what the beat's FORM is.
Build a SHOT when the form itself is new. An object is reusable across the film's beats (the same puck loose on
beat 3 and tamped on beat 4, through its `props`) and across templates; a shot is one composition. A film-local
shot declares `GROUND` (the DNA token its ground is painted from — the caption's ink is picked from it and
`shot_proof.py` measures the claim) and `PROVENANCE` (its idiom world).

**Do not settle.** Step 0.5 already requires half the form vocabulary to be forms the library lacks;
each of those is a build-list entry, or a written reason it is not. A topic the library has never met with an empty
build list is the signature of assembling from what exists — the critic's S14 and S15 look for exactly that. What
the film builds stays in its workshop; at delivery the USER decides what is promoted into the library
(`scripts/promote.py`).

## Step 0.6 — Extract the Design DNA (the GLOBAL visual system every shot inherits)
The chosen template is **NOT a set of reusable frames — it is the whole film's visual system.** Before authoring a
single shot, expand the template into an explicit **Design DNA** and write it to `meta.design_dna` (a reviewable
artifact, not just a label). The DNA is the *shared grammar* every shot wears; a library register contributes its
STRUCTURE (composition + motion + information hierarchy), the DNA contributes the VISUAL IDENTITY. Required keys
(match `remotion/src/runtime/dna.tsx` `DesignDNA`): `id` · `fontDisplay`/`fontMono`/`fontBody` · `bg`/`bgGrad`/
`fg`/`dim`/`accent`/`accent2`/`onAccent`/`surface`/`surfaceBorder`/`line` · `radius`/`borderWidth` · `motion`
(`type`/`execute`/`smooth`/`mechanical`) · `decoration` (`prompt`/`status`/`breadcrumb`/`cursor`/`scanline`/`grid`/
`line-numbers`) · `uppercaseLabels`/`labelSpacing` · `atoms` (the FORM each content atom speaks — see
`remotion/src/runtime/atoms.tsx`). Optional, and read by the renderer when present: `motif` (`{kind, ink,
opacity, scale}` — the subject's material, opacity kept near 0.05), `finish` (`"none"` turns the film finish off) and `seam` (the film's own cut, e.g.
`{type:'wipe', direction:'from-bottom'}`; the contest direction's `seam` is the PITCH of it, this is what renders).
**A CJK film names the bundled faces** — `"Noto Sans SC"` / `"Noto Serif SC"` — in every font stack; system faces
alone may be missing where the film renders, and validate warns. A **built-in preset** exists for known templates (terminal →
`TERMINAL_DNA`), auto-applied by `render_remotion.py` when you set `meta.shot_template` and author no `design_dna`;
authoring the explicit block is preferred (it's the reviewable Design DNA and lets you tune tokens). **The DNA is
provided to the Film at render (a `DesignDNAContext`) and every migrated register reads it via `useDNA()`**, so one
DNA makes 19 different compositions read as one visual universe — the remotion analogue of the html tier's
`theme.css`. `validate.py` warns when a themed film has neither an explicit `design_dna` nor a preset-mapped template.

**Start from the DECK, not from a preset, whenever the film came from a pptx.** The deck already carries a visual
identity — its theme's twelve scheme colours and major/minor typefaces, its master ground, and the look its
slides actually render — and a preset paints over all of it with a direction's generic palette. Run
`python3 scripts/dna_from_deck.py <out_dir>` (it finds the deck through `meta.source`; `--pptx` names one; `--mode
dark|light` overrides the frames' reading; `--dry-run` only prints). It writes a complete `meta.design_dna` object
whose `provenance` says where every token came from: the ground from the rendered frames (a theme's lt1 is
white even when every slide sits on a dark picture), the ink pushed to WCAG 7:1, a CUSTOM theme's accent1/most-
distant accent nudged to 3:1, the typefaces CLASSIFIED (Lora → serif → Playfair Display + Source Serif 4;
Calibri → humanist → Inter; Consolas → mono → JetBrains Mono, with the terminal grammar) onto the faces
`fonts.ts` bundles, and the atoms/radius/label grammar following that class. An Office-DEFAULT theme (Office
blue, Calibri) never chose its colours, so there the frames decide and the note says so. Then RETUNE the object
like any authored DNA — it is the starting point that already looks like the client, not the end of the
judgement. `validate.py` warns when a pptx with a custom theme ships under a preset. Verified on real decks: a
Philips-blue research template came out Philips blue with white type and an orange counter-accent, rendered
through BentoReveal and SwissEditorial without a line of authoring.

**A COMPLETE worked block — copy this shape and retune every value to the topic** (a partial DNA no longer crashes
the render — Film normalises it through the neutral preset — but every key you omit silently borrows a neutral
value, and `validate.py` will name what is missing):

```json
"design_dna": {
  "id": "terminal",
  "fontDisplay": "\"JetBrains Mono\", \"Noto Sans SC\", \"PingFang SC\", ui-monospace, monospace",
  "fontMono": "\"JetBrains Mono\", \"Noto Sans SC\", \"PingFang SC\", ui-monospace, monospace",
  "fontBody": "\"JetBrains Mono\", \"Noto Sans SC\", \"PingFang SC\", ui-monospace, monospace",
  "bg": "#080b11", "bgGrad": "radial-gradient(120% 120% at 50% 0%, #0d141c, #05070b 72%)",
  "fg": "#d7e3ef", "dim": "#5d7186", "accent": "#37d68a", "accent2": "#7ee0ff", "onAccent": "#03130c",
  "surface": "#0d1219", "surfaceBorder": "#1d2a36", "line": "#16202b",
  "radius": 4, "borderWidth": 1,
  "motion": "execute",
  "decoration": ["prompt", "status", "breadcrumb", "cursor", "scanline", "grid"],
  "uppercaseLabels": true, "labelSpacing": "0.12em",
  "uniformType": true,
  "atoms": {"bar":"block","figure":"mono","list":"tree","label":"prompt","divider":"scanline","marker":"caret"}
}
```

`atoms` declares which FORM this system speaks for each content part (see `remotion/src/runtime/atoms.tsx`);
an omitted atom renders its neutral form, so a partial declaration is valid.

**Every family named in `fontDisplay`/`fontMono`/`fontBody` must be one `remotion/src/runtime/fonts.ts` actually
loads** — `Space Grotesk`, `Playfair Display`, `JetBrains Mono`, `Bangers`, `Inter`, `Source Serif 4`, `IBM Plex
Sans`, `IBM Plex Mono`, `Bodoni Moda`, `Baloo 2`. A family outside that list silently falls back to the browser's
generic (a test, `test_every_declared_family_is_actually_loaded`, catches this in the built-in presets, but a
hand-authored `design_dna` is not covered by it). Every stack must also end with the CJK chain shown above plus a
generic family, exactly as `TERMINAL_DNA` does — none of the ten loaded faces covers CJK, so a stack without the
chain silently drops Chinese text to a system default. See `references/remotion-shot-authoring.md` §C3 for how
this reaches the shots.

Two keys are BEHAVIOUR-bearing, not decoration, so choose them deliberately:
- **`id`** selects the film's native SEAM grammar (`terminal` → a console screen-clear sweep · `product`/`apple` →
  a slide push · `editorial`/`blueprint` → a sheet wipe · anything else → the safe cross-fade). Use a known id
  unless you want the neutral seam.
  This reaches EVERY UNMARKED cut, which is nearly all of them, so read Rule 5 before you lean on it: a native
  cut on all of them erases the ~2–3 marked ones, and the plain cross-fade is the CORRECT default for most
  films rather than a decision left unmade. `"seam": {"type": "fade"}` opts a preset id back out.
- **`uniformType`** — `true` forces ONE font across every shot (right for a mono/terminal world; it is the single
  strongest style signal). Leave it out for a MIXED-type system (editorial serif + sans, product geometric), where
  each element picks `fontDisplay`/`fontBody` itself.

All six selectable directions map to a built-in preset (`terminal-technical`, `kinetic-editorial`, `product-demo`,
`cinematic-craft`, `data-story`, `retro-playful`), so `meta.shot_template` alone already themes the film.
**Consistency ≠ repetition:** the DNA does NOT make every frame a terminal window — a beat may be a big metric, a
chart, a diagram; it just inherits the type/palette/container/motion/annotation grammar. Prefer subtle structural
consistency over repetitive decoration (a shot needs 2–3 recognizable DNA cues, not a forced terminal box).

## Step 0.7 — Style Assimilation + the three-layer model (run per shot, for ANY chosen style)
The template is a GRAMMAR, not a layout template — and the trap cuts BOTH ways: too weak = reskin a generic
register (a gauge tinted to the accent); too strong = make EVERY beat the same explicit style CONTAINER (for
terminal, a black window box; for editorial, an identical magazine spread). Split the style into **three layers**
(§C2): **(1) Surface** — only 2-3 ANCHOR beats show the explicit container (terminal window / glass hero /
drawing sheet). **(2) Grammar** — every OTHER beat inherits the DNA (type, palette, the style's syntax/marks,
status/annotation cues) on OPEN canvas, with a layout chosen PER CONTENT so beats don't all look alike. **(3)
Motion** — reveal as the style's native ACTION → RESULT (terminal: `$ cmd` runs → output grows; product: a soft
scale-in; blueprint: a measured draw-on). Then **ASSIMILATE each shot**: translate its content idea into the DNA
across ≥2-3 of {typography · layout (the style's logic, not a generic slide) · components (panels/labels/
dividers/status primitives) · motion (enter/transform per the motion grammar) · transition · narrative metaphor (can
the content be *expressed through* the design concept?)}, and **reject any shot that could be dropped unchanged
into a different style without anyone noticing.** The terminal worked example of all three layers (`TermFrame`,
the native seams, the reveal character) is `references/remotion-shot-authoring.md` §C2. For terminal use the `Term*`
family + `TermFrame` (default OPEN, `framed` only on anchors); for a style with no family yet, build style-native
shots the same way OR use the library registers reading the DNA tokens — never a reskinned generic component.
This is style-AGNOSTIC: it holds for terminal, editorial, product/apple, blueprint, or any `meta.design_dna`.

## The mandate — clear AND bold AND meaningful
For each beat ask *"what is the clearest hand-written LANGUAGE for THIS idea?"* — answered by the ideal picture
and route of Step 0.55 (the one place the flow is defined), never by "which card layout". Whatever register the
route lands on, its props come from the beat's own content so it speaks the topic, not WorkBuddy. **Lean toward
the chosen `meta.shot_template`'s families** (Step 0) while keeping the family-variety rule, and **COHERE with the
chosen direction** — carry its palette/motion/motif across beats (`references/remotion-shot-authoring.md` §C).

**Every shot must ENCODE its beat, not decorate it — the check of Step 0.55, applied to EVERY beat.** *Hide the
caption — does the visual still carry THIS specific idea, and only this one?* A design that could sit under any
nearby caption, or reads as generic "science/tech atmosphere," is a FAIL — its structure must mirror the content
(symmetry / direction / accumulation / sparsity / cause→effect). The traps that shipped (radial-burst-for-RF,
waveform-for-FID, mandala-for-k-space, glitch-for-aliasing, a diagram where an equation is clearer, colored blocks
instead of a real image) are the anti-pattern table in `references/remotion-shot-authoring.md` §B. When NO
register encodes a topic-specific idea, the route is **build** (Step 0.55, in the film's workshop) — never force
a near-miss, which hits a ceiling and drags in leftover demo copy. On a concrete topic reach for the real-imagery
tier (Rule 1 and §B). And **audit ALL beats** with the hide-the-caption test, not just the flagged ones.

**ADAPT = KEEP THE STYLE, REDESIGN THE REST — never text-swap a register's demo (临场设计优化; worked examples in
`references/remotion-shot-authoring.md` §B2).** A register is a STYLE (its vibe, motion, material, typographic
attitude) wrapped around DEMO scaffolding — placeholder mini-widgets, generic glyphs, demo-length labels, a stock
module count and layout. **Keep the style — and keep any stock module that ALREADY encodes THIS topic's content —
and treat the REST of the demo scaffolding as a mannequin to rebuild.** The DEFAULT posture on EVERY beat, EVERY
topic is to redesign both the CONTENT *and* the register's own MODULES/COMPONENTS so its structure *represents
THIS topic's content* — not merely to change the words: motifs that MEAN the item, modules re-shaped to the
content's real relationship (parallel questions stack; a "loop" is a cycle; a hierarchy nests), components
added/dropped so the beat's idea is the thing on screen, and sizes set for the REAL copy (§A.12). Litmus: *would
this beat look the same on a totally different topic with only the words changed?* If yes, you text-swapped.
**Judgment, not reflex — don't blindly rewrite what already fits.** Changing a module that already carries THIS
beat's content, only to look different, is as wrong as text-swapping. Decide per module: does it carry the DEMO's
meaning or THIS topic's? When the fix is a pure demo-length assumption (a fixed label width, an un-padded box), FIX
the shared register at the source so every future film benefits; when the stock modules cannot carry the idea at
all, write an in-style variant (its VIBE, composed around the real content) as a workshop shot — the **build**
route, and the NORMAL move, not a last resort.

**Record it per scene in `shot_adaptation` = `{kept, redesigned, topic_idea, changes, theme_cues}`** — `kept` the
style + the modules that already fit, `redesigned` the modules/components + content you rebuilt, `topic_idea` the
topic-specific idea the shot now encodes, `changes` the `[{aspect, what, why}]` that make the beat count as ADAPTED
(Step 0.55), and `theme_cues` on a DNA-themed film (Output). It is a REQUIRED artifact (validate.py WARNs when it's
missing or `shot_props` is empty; shot-critic S10 checks the note against the rendered frame): writing it forces
the redesign to be a decision, not a reflex.

**Check every chosen shot with its ACTUAL props before trusting it** (`npx remotion still … --props='<real
props>'`, or `workshop.py <out_dir> still` for a built one). **On a non-16:9 film (`meta.aspect` != 16:9):
still-render EVERY chosen shot AT that aspect** (`--props '{"aspect":"9:16",…}'`) and fix/swap any that don't
reflow — a multi-column layout must STACK in portrait, wide elements must not run off-frame
(`references/remotion-shot-authoring.md` §A.11).

**BOLDNESS is not optional — it scales with `meta.audacity`.** Clarity is the floor, not the ceiling: reach past
the OBVIOUS register for the surprising-but-apt one, especially on the hero + climax beats (the signature moment
of the Step 0.55 checklist). At `bold`/`experimental`, a mix of safe/expected registers is a FAILURE the
shot-critic (S8) sends back — commit registers that are memorable and unmistakably THIS film. For each beat,
briefly note the `rejected_default` (the obvious register you passed over) so the choice is a decision, not a
reflex.

## Rules (all six bind)
0. **Route every beat — `shot_fit` is Step 0.55's record, not a second definition.** Write
   `shot_fit = {ideal, verdict: "fit"|"adapt"|"build", why, shares?}` on every scene exactly as Step 0.55 defines
   the three routes. **The line between `adapt` and `build` is the frame, not the effort:** `adapt` keeps a
   register's frame and changes its layout, encoding or structure for this beat (recorded in
   `shot_adaptation.changes`); `build` is needed when no template arranges the frame the way the argument runs (a
   new shot) or the frame is right and only the subject is missing (an object). A register you could use only by
   **swapping its words** is neither — that is `fit` (as-is), and it must name the encoding it `shares` or it is
   not the ideal.

   **Building happens in the film's own workshop, and is cheap on purpose** — the `workshop.py` commands are in
   Step 0.55 above (`new-object` · `new-shot` · `still` · `check`). Nothing it builds touches the library: every
   render of THIS film sees it and no other film does; at delivery the user decides what is promoted
   (`scripts/promote.py`, which registers and measures it). Never write a register straight into the library
   mid-film (`register_shot.py`): that costs a full registration and measurement, which is why, when it was
   the only way to build, nothing was ever built and every beat got the closest existing register.

   **A new register must be REUSABLE, not a one-off.** It carries an ARGUMENT SHAPE — "two populations a
   measure cannot separate", "correlated vs independent failure" — with the topic arriving entirely through
   props, so the next film making that kind of claim can reach for it and the library compounds. Its
   DEFAULTS stay generic demo copy. `shot_proof.py` ERRORS if a register hardcodes this film's own prose.
   Give it a family letter; if it fits none of A–Z, open a two-letter one (AA, AB, …) — the set is open.
   A film-local shot is held to the same rule — its topic arrives through props — which is what makes it promotable.

   **A THIN FAMILY is a build signal, not a menu.** LIBRARY.md opens with a generated family census: nine
   of the twenty-five families hold ONE register. So "vary the family" quietly pushes every film toward the
   four big ones (D, A, C, G), and when a beat's argument wants a thin family there is nothing to choose
   between — its single member either carries the argument or it does not. If it does not, that is the
   clearest build case there is, and settling for the only member is how a beat ends up with a design that
   is merely ADJACENT to its meaning. Notice which of the two reasons put you in a family: because it fits,
   or because it was stocked.

   `validate.py` warns when no beat records `shot_fit` (the judgement was never made, so "no register can
   draw this" could never surface) and when EVERY beat records `fit` (on a topic-specific film, the
   signature of matching the catalogue rather than judging it). `critic_brief.py` reports, to the reviewer,
   whether the film built anything at all and which thin families it leaned on.

0. **Fill the SKELETON first, then pick the cards.** Every beat already declares an `energy` (low / medium /
   high / peak) and the library's sweep measures a motion per register (`remotion/register_energy.json`,
   `motion_p75`). Read the beat's energy BEFORE choosing its register: a `high` or `peak` beat never takes a
   register from the library's stillest third; the `peak` beat takes the film's LIVELIEST register, above the
   delivery motion floor — the summit belongs to the argument's peak and nowhere else; a `low` beat (the sparse
   hold, the close) never takes one from the liveliest third; and kinetic registers ALTERNATE with steady ones,
   never three in a row (a mature peer library's case: "连续高能量读作嘈杂" — consecutive high energy reads as
   noise; alternation and breathing beats ARE the rhythm). Measured on a delivered 30-beat film whose director
   could not see energy: the plan's climax landed on a register under the motion floor, four HIGH beats on the
   stillest fifth, and the film's visual summit on a MEDIUM beat nine minutes early. After assigning, run
   `python3 scripts/energy_skeleton.py <out_dir>`: it prints the declared skeleton against the measured curve
   and names in-band, unused alternatives for each mismatch (`validate.py` repeats them as warnings). Its
   findings are candidates — a beat's real motion also depends on props, ground, camera and length — so check
   the beat, then swap the register or re-declare the energy; never leave the two disagreeing.
1. **Match intent → register.** `statement`→a title/kinetic register (CinematicTitle, FocalIsolation,
   KineticManifesto, LiquidChrome, BrutalistType, SwissEditorial); `sequence`→ExplodedSchematic/TimelineTravel/
   CommandSummon; `structure`→CollaborativeCursors/KnowledgeGraph/MapRoutes/DataOrrery/WireGlobe/BlueprintGrid;
   `list`→BlockAssembly/TemporalAccelerate; `metric`→ChartLive/BlueprintGrid(counter)/PhysicsStack. The `climax`
   beat gets a payoff register (ParticleForm/RadialBurst/LightTrails/SpotlightStage/LiquidFill); the `close`/`hold`
   beat gets a premium title (LiquidChrome/HoloFoil/CinematicTitle/SwissEditorial). Use the "use when" as the map.

   **A CONCRETE topic can want a real PHOTOGRAPH as the register itself, not as a texture behind one.** When the
   beat's claim is *look at the actual thing*, reach for **PhotoPlate** (LIBRARY 171): the photograph IS the
   frame, and the film's own numbered marks sit at points IN it, arriving as the narration names them — so the
   picture carries the argument instead of illustrating it. The library's other image registers answer different
   questions: **ScanReconstruct** = revealed by its own process · **MuseumLabel** = the object beside its
   catalogue label · **RealVersus** = A against B. Decide this HERE, at register selection: on a delivered film
   about a physical city, with license-clean photographs available, real images occupied 5.3% / 8.5% / 16.3% of
   the frame — the evidence shipped as a footnote to a drawing of itself. Fetch with `python3
   scripts/imagefetch.py "<subject>" <out_dir>/media/<name>.jpg` (license-clean Wikimedia; it writes the sidecar
   `<name>.jpg.json` beside the file, naming the real author + licence). **Take the credit FROM that sidecar —
   never type one from memory** (`imagefetch.attribution_line()` builds it): `validate.py` ERRORS on a beat
   showing an image whose sidecar author it does not credit, because a wrong CC-BY line credits someone else's
   photograph to a stranger.
2. **Give the film somewhere for the LIGHT to go — `scene.ground`, on 3-6 beats** (library registers; a beat on
   this film's OWN shot cannot take a declared ground — its shot draws its light itself: a flash, a dawn, a daylit
   frame, built into the shot on the beats where the argument turns, and film_energy_qa's LIGHT and LIGHT ARC
   measure either kind after the render). A register holds ONE
   ground by design; a film's light comes from moving BETWEEN beats, and if no beat re-grounds, the film runs
   on one flat exposure from first frame to last. That is what ships today: swept across the library, 142 of
   152 registers measure under the delivery gate's light floor (median luminance span 0.016 against a floor of
   0.135, and reference launch films at 0.27-0.90). `validate.py` now warns when a film of 8+ beats declares
   none, and again when it declares fewer than three (one bright passage is an exposure change, not an arc).
   **The vocabulary needs no setup:** `ground: 0` is the film's own ground, `1` its opposite key (a dark film
   gets a lit frame, and every register re-inks itself for it — type, dim and accent are all re-derived), and
   `2`+ one chromatic ground per accent; or name a preset (`paper`, `gallery`, `clay`, `olive`), a `#hex`, or
   an inline `{bg}`. A beat can also RAMP within itself — `ground: {from: 0, to: 1, at: [0.3, 0.7]}` — which
   is the move for a before/after or a covered/uncovered beat, where the light and the argument become the
   same fact. **Only a register that FOLLOWS a ground may carry one** — 103 of the 152 do (the allow list is
   `GROUND_FOLLOWS_MEASURED` in `remotion/src/runtime/shotLuma.ts`); a register that paints its own fixed
   luminance would leave the frame half your ground and half its own, so `validate.py` ERRORS on it by name
   before the render rather than the runtime throwing minutes in. Move the ground to a neighbouring beat.
   **Measured end to end** on a six-beat film: two ground declarations took its luminance span from 0.103
   (under the delivery floor of 0.135) to 0.871 — the top of the reference launch films' 0.27-0.90 — with the
   anti-gaming step axis going 0.0 -> 0.185, i.e. the light genuinely moves rather than one bright passage
   inflating the range. **Move on the beats where the ARGUMENT turns** (a payoff, a section break, the reveal), never on
   a schedule, and name the move in that beat's `shot_adaptation`. A film that genuinely means to stay
   monotone declares `meta.energy_waiver` with a reason — silence is not a decision.
2. **Vary the FAMILY across the film — never two ADJACENT beats from the same family.** This is what stops the
   film reading as one look. Spread across ≥6 families in a ≥10-beat film; feature the 3D register (MaterialHero)
   and one illustrated/craft style at most once or twice.
2b. **On a CJK film, check the TYPE after you fill the props — `python3 scripts/cjk_type_qa.py <out_dir>`.**
   The library is authored with short English demo copy, and a face set at `line-height: 0.82` is confident
   Latin typography and a COLLISION in Chinese: Latin glyphs sit inside their em box, CJK glyphs fill it.
   `text_safe_qa` cannot see this — nothing is cut off; the copy sits inside the frame and is unreadable —
   which is how two registers shipped a pile of overlapping type in a delivered film while every gate was
   green. The gate renders each of your beats with ITS OWN copy and asks the DOM. A `leading` finding is a
   defect (an element's own wrapped lines colliding is never intended); an `overlap` finding is a candidate,
   since some registers stack type on purpose. The fix is usually not a different register: pass the copy
   through `leading(text, latin)` from `runtime/cjkType.ts`, which raises the floor ONLY for CJK so the
   register's Latin typography is untouched.
3. **Fill props from the beat, faithfully.** Put the beat's real nouns into the register's props (its wordmark,
   `items`, `hub`, chat `messages`, `nodes`, etc. — see the LIBRARY props table). **Any register that shows a
   NUMBER (ChartLive `endVal`, BeforeAfterSlider `metric`, VelocitySnap `metric`, BlueprintGrid counter) MUST be
   given a SOURCED figure that traces to the beat's `source_ref` — NEVER leave the shot's illustrative demo
   default, and never invent a statistic.** If a beat has no real number, pick a non-number register.
4. **Copy stays in the beat's language** (the deck's language — English or 中文) and stays SHORT (a register's
   label/title is a few words, not the whole narration — the narration is the voiceover + caption).
5. **MARK ~2–3 chapter-break seams — the rest ride the default (set nothing).** Every seam is a gentle
   luminance-safe cross-fade by default; that already reads well and needs no authoring. On the FEW beats that
   open a new chapter, set `transition_style` on the INCOMING scene so the cut CLAIMS the relationship — chosen
   from the beats' `relation`, never decoration: a reveal / new-topic → `clock` or `wipe` (the frame opens); a
   forward push / building energy → `slide` (push); a payoff where the outgoing FORM becomes the incoming one
   (a solid → its particles) → `dissolve`; a CONTINUITY beat where the two shots should read as one continuous
   move (a chart collapses and the human takeaway grows from the same line, a converge → resolve) → `carry` (a
   collapse-to-line match-cut — the ONE mark that also works across a dark↔light seam, its neutral line being the
   luminance bridge).

   **The rest of the vocabulary, one word per relation** (the same words the html tier uses, so a film that
   changes tier keeps its seams — `references/motion-grammar.md` holds the full table):
   `push` a lateral step in a sequence (next page, next step) · `lift` the same move turned 90°, a reading-flow
   progression down one document · `fadethrough` the same reset as a fade with the emphasis moved onto what
   ARRIVES (leaves in 30% of the seam, the new content gets 70%) · `drift` a cross-fade that also travels ~24px
   in the reading direction, direction without loudness · `blur` a rack-defocus coda where both beats go soft at
   the middle — attention letting go of one thing and settling on another, budget **ONE per film** (a quote, a
   closer). `drift` and `blur` survive the dark↔light guard (a translation adds no light and a Gaussian
   redistributes it); `fadethrough` does not, because leaving fast is how a dark ground becomes a light one in
   0.15s. A seam word this renderer cannot resolve is now an ERROR in `validate.py`, never a quiet fade.

   Two constraints: **budget ≤~3 marks** in a
   ≥10-beat film (marking every seam is as monotonous as marking none, and the shot-critic S2 flags it), and a
   mark only "takes" on a **same-luminance** seam — a dark↔light cut is auto-forced back to the safe fade
   (Film's pickPresentation guards against a bright edge slamming over a dark scene), so don't spend a mark
   there. No spins, ever. (Mechanism: `render_remotion.py` maps `transition_style` → the Film `transitionIn`.)

   **The film's NATIVE cut is OPT-IN, and NOT setting it is the right answer for most films.**
   `meta.design_dna.seam` — and a preset `meta.design_dna.id`, Step 0.6 — replaces every UNMARKED cut with the
   design system's own move. Measured on a delivered film: it turned 31 of 34 cuts kinetic, so the 3 deliberate
   marks read exactly like the 31 that meant nothing — the film LOST its punctuation to the feature meant to give
   it a voice. A plain cross-fade on the unmarked cuts is the CORRECT default and a finished decision, not a
   missing one. Declare a `seam` only for a world with a genuine native ACTION (a terminal clearing its screen);
   on a preset id whose world has none, opt back out with `"seam": {"type": "fade"}`. `validate.py` warns when a
   declared seam swamps the marks.

   **Mark by MEANING — completeness is not your problem.** `python3 scripts/seam_plan.py <out_dir>` runs after
   you, as a verify-and-fill pass: it derives marks from each beat's `relation`, and SKIPS any beat you already
   marked (an explicit mark always wins, so it never competes with you). It exists because a delivered 35-beat
   film used none of the vocabulary — all 34 seams the anonymous default — and it mirrors the renderer's
   luminance guard: on a dark↔light seam it marks the `carry` instead, the one cut whose bridge line survives
   that guard, rather than a kinetic mark Film.tsx would silently downgrade to a fade.

## Order the items the way the voice says them

A register shows its list (labels, parts, questions, marks) in prop order. Write each list in the order the
narration names its items, and put a caption or note the voice says first where the register can show it.
Registers that import `runtime/cue` (OpenQuestions, TechnicalPlate, ObjectStage, PhotoPlate, KSpaceToPicture, and
every workshop shot scaffolded since) bring each named item in on its word themselves; for any other register,
an item said before the ones shown ahead of it stays late, and `text_safe_qa --sync` reports it as an ERROR.

## Device beats — when the narration performs something in the product

Cast `DeviceDemo` when the beat says how the product is USED ("search last week's feedback, open the summary,
scroll to the pattern") AND the film has the product's real screens (screenshots or a recording in the out
dir). Write `shot_props.steps` as a script: open with `{"screen": {"image": "..."}}`, then one step per action
the narration names, each with `"at": {"cue": "<the words>"}`. Target by text where you can
(`{"tap": {"text": "反馈汇总"}}`), by `[x, y]` otherwise — fractions of the VISIBLE screen, not of the image. Put
each action's words about 0.75 s or more into its line. On a recording, only `mark`. The whole format is the
**Step script** section of `remotion/cards/DeviceDemo.md`. Cast `DeviceHero` for "this is the product" with one
screen. Never invent a screen: with no real screenshots, choose an interface register instead and say so.
After `tts.py`, `python3 scripts/validate.py <out_dir>` checks every device beat the way the render will meet
it — the script's shape, its screenshots, every text target, the time each step needs — and names every
problem before a render.

## The camera — a move needs a CAUSE (per beat, budget 2–4)
A scene may carry **`camera` = `{move: "push"|"pull"|"hold", amount: 0.045}`**. This is not a Ken Burns drift:
the tier's earlier camera was a film-wide sinusoidal wander with no relationship to anything being said, and
motion with no cause reads as a wobble the moment a viewer notices it — which is why it was switched off
entirely, an over-correction. So derive the move from what the beat is FOR:
- **`payoff` → `push`** — the beat where the argument lands: look closer at what is here.
- **`close`, and the OPENING beat → `pull`** — here is the whole of it, from either end of the film.
- **everything else HOLDS** (set nothing). Budget **2–4 moving beats in a whole film, spaced apart** — a film
  whose camera always moves has no camera, exactly as a film that marks every seam has no punctuation.

**Spend a push only on a frame that HOLDS something to look closer AT.** A shot reveals over roughly t 0.05–0.45,
which is why the move runs 0.28–0.88 — it rides `useT()`, so it never runs over a cut and it lands on SETTLED
content, and `amount` is clamped to what the caption band can absorb. A push into two rows of text magnifies
nothing; a push into a photograph, a plate, a schematic with detail in it is the beat worth spending on. Check
what the beat's shot actually holds before marking it. `seam_plan.py` fills these on the same rule and skips any
beat you authored.

## Color-arc (a SOFT sequencing pass — after fit/family/boldness are settled)
Each shot has a ground LUMINANCE (dark / mid / light — `remotion/src/runtime/shotLuma.ts`). A film that flips
**dark↔light on nearly every beat STROBES**: even though each seam is smooth (the renderer forces a gentle fade
across a jump), the whole-film brightness *pulse* reads restless. So sequence a luminance **ARC, not a strobe** —
let brightness move in short **runs/gradients** (a few darks, then lift into the lighter beats, or the reverse),
reserving a hard dark↔light flip for a **deliberate jolt** (a reveal, a tonal turn). This is a TIE-BREAK only: it
never overrides register FIT, family variety, faithfulness, or boldness — when two equally-apt registers fit a
beat, prefer the one whose ground continues the run. `validate.py` warns when >60% of seams hard-flip (a strobe);
the deterministic fallback assigner already softens streaks. (The MARKED **carry** seam is the clean way to make
a *needed* dark↔light turn read as continuity rather than a flip — see Rule 5.)

## Output
Edit `storyboard.json`: set `meta.renderer:"remotion"` and, on every scene:
- **`shot`** — a valid id from `remotion/src/shots/*.tsx` (or a workshop shot).
- **`shot_props`** — an object of TOPIC copy, never `{}` (which ships the register's demo mannequin). **Fill EVERY
  copy prop the register has, or set the ones you want blank to `""` (`[]` for a list).** Every register carries
  illustrative defaults so it can be previewed standalone, and an omitted prop PRINTS them: a delivered Chinese
  film gave BentoReveal its own `title`/`hero`/`heroKicker` and no `items`, so six of the frame's seven cells read
  *Throughput / Coverage / Trend / Signals / Team / Auto-sync* — English demo labels presented as that product's
  own. `validate.py` now ERRORS on it and names the exact copy; `python3 scripts/demo_copy_qa.py <out_dir>` lists
  it, and `--library` shows what each register would print.
- **`shot_fit` = `{ideal, verdict: "fit"|"adapt"|"build", why, shares?}`** (Step 0.55 — `shares` on every as-is
  beat, `ref` on every beat that uses a built item, `form` from `meta.form_vocabulary`).
- **`shot_adaptation` = `{kept, redesigned, topic_idea, changes, theme_cues}`** (REQUIRED — The mandate above;
  `changes` on every adapted beat). On a DNA-themed film, **`theme_cues`** are the 2-3 concrete cues that tie THIS
  shot to the global visual system (e.g. `["mono heading","▸ prompt","terminal grid","green accent"]`) so the
  Design DNA verifiably runs through every frame.
- On the FEW beats that earn them, `transition_style` (Rule 5) and `camera` (the camera section);
  `python3 scripts/seam_plan.py <out_dir>` then fills the beats you left and skips every one you authored.
- A short `shot_rationale` (why this register, which family) is encouraged, for the critic.

On a film that builds, also write **`meta.build_list`** (Step 0.55). `validate.py` ERRORs below the design-first
floor (half built, one built — on a film made before that rule, with no ideal on any beat, one error that
asks the user instead, and a keep recorded per beat with `validate.py <out_dir> --keep-design`: SKILL.md step 10), on
an as-is beat that does not earn it, on a missing/unknown `shot`, a
number-bearing register left on its demo default, or ANY copy prop left to its demo default on a partly-filled
beat, and WARNs on empty `shot_props` or a missing `shot_adaptation` (a raw text-swap); `render_remotion.py`
renders the chosen shots through the data-driven `Film`. Keep a family-variety pass at the end: scan the shot
sequence and swap any adjacent same-family pair for an equally-fitting register from a different family.
