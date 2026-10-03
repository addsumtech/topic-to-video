# Shot Critic (remotion bespoke-shot tier)

> **When this runs.** After a `meta.renderer:"remotion"` render, as the design-review gate — the remotion
> analogue of `design-critic`. You judge the **shot-director's** choices (which register per beat + its topic
> copy) against the rendered evidence, and you gate delivery. If the deck is HTML/local, use `design-critic`
> instead; this file does not apply.

## START HERE — and do not re-derive what is already decided

Run `python3 scripts/critic_brief.py <out_dir>`, then read **`<out_dir>/_critic_brief.md`** and
**`<out_dir>/_contact_sheet.png`**. The brief carries every machine verdict already run, the whole film as
ONE image, the catalogue entries for only the registers this film uses, and the repetition/family/growth
facts computed rather than eyeballed.

**Open a full `_keyframes/scene_NN.png` only for beats the contact sheet makes you suspicious of.** A 320px
cell shows composition, palette, repetition and gross overflow; it cannot show a colliding label or an
illegible figure, and those are what the full frame is for. Opening all of them is how this review used to
cost a full render's worth of tokens to re-find things a script had already reported.

**These dimensions are MACHINE-DECIDED. Read the verdict in the brief; do not spend your pass on them:**
action-safe overflow · ink in the caption band · colour outside the film's palette · a dead (narrow AND
off-centre) frame · an empty frame · a register's demo default left in `shot_props` · two beats carrying the
same prop shape · a figure still moving at the frame the gate captures · A/V drift · blank or missing
keyframes · caption craft · adjacent same-family beats · the narration's rhythm. If one of them FAILED, say
so and stop — the film is not ready for a design review.

**What is left is the half a script cannot judge, and it is the whole reason you exist:** whether the design
ENCODES the beat, whether every number is sourced, whether the register's structure carries the argument or
was merely the closest thing in the catalogue, and whether the film has a shape. Sections S1, S3, S5, S7,
S8, S9 and the MEANING/CONTENT-FIT half of S10 below are yours. S2, S6 and S10's frame-craft list are the
machines'; they remain documented so you know what is covered, not so you re-run them.
S12 (camera) and S13 (real imagery) are yours too, and are the newest holes: `validate.py` checks only that
an authored `camera` is one of push/pull/hold with an amount in 0-0.2, and nothing anywhere asks whether a
film about a physical thing ever shows the thing. So a film can move its camera on beats that had no reason
for one, or footnote its photographs at thumbnail size, and pass every gate.

**Growth is part of the verdict.** The brief reports whether this film BUILT any register and which of the
families it used are one-register families. A film that used a thin family and settled for its only member —
when that member's structure did not carry the beat's argument — should have built one. Say so.

## JUDGE mode (the contest's selection half — Step 0)
When the shot-director dispatches you on the **contest samples** (not a finished film), you are the SELECTION half
of divergence+selection. Judge from the **sample VIDEOS** `<out>/_contest_*.mp4` (motion is the design language;
the `_contest_*.png` stills are only for the mechanical diversity gate) + the beats + `meta.audacity`: (1)
DISQUALIFY any floor-breaker — a sample that rendered blank/garbled, is off-brief for the topic, or is illegible;
(2) RANK the survivors by how boldly + aptly each direction fits THIS topic at this audacity (a striking,
topic-true atmosphere beats a safe generic one); (3) name ONE **winner** + a **runner-up** with one line each.
A floor-breaking or off-brief candidate must never reach the user unranked. Output the ranking + the winner/runner-up;
the shot-director surfaces the judged finalists to the user. (The rest of this file is REVIEW mode — a finished film.)

## The dimensions (score each scene, then the whole film)

**Each rule below is RULE + PRECEDENT + a question to ask yourself.** The precedent is the delivered film
that produced the rule, named by the commit that repaired it — so you can read what the failure actually
looked like on screen rather than inferring it from an abstraction, and recognise the same shape on a topic
nobody has seen yet. A rule marked *Precedent — none on record* is doctrine: no film has failed it in a way
anyone wrote down, so treat it as the weakest evidence here and record a real one when you find it. Numbers
are append-only; a retired dimension keeps its number.

**Every dimension gets a verdict, including the ones you find clean.** Fill `_critic_ledger.json` — one row
per dimension, each with the evidence it rests on — and gate on it:

```
python3 scripts/critic_ledger.py <out_dir> --emit-template   # skeleton, every dimension listed
python3 scripts/critic_ledger.py <out_dir>                   # after you fill it
```

The old output asked only for the FLAGGED scenes, which made a dimension you never looked at and a dimension
you checked and found clean produce the same artifact: nothing. The ledger makes an unexamined dimension a
missing row. It refuses a bare verdict (cite the keyframe or the brief line), and it refuses a ledger whose
`contact_sheet_sha256` is not this render's — so a verdict cannot be written from a memory of an earlier one.

**S1 · Register FIT.** Does the chosen `shot` express THIS beat's idea (match it to the register's LIBRARY
"use when")? A statement beat on a data-chart register, or a climax on a flat list register, is a REVISE.
If a NEW shot draws a quantity bar, a headline figure or a list without using `runtime/atoms.tsx`, it must
say why — those parts have a per-DNA form and a hand-rolled one will not follow the film's system.

> **Precedent — `18371d5`:** A city documentary came out of this library speaking developer-tool: six terminal shots (`$ dig --oudegracht`, `$ diff 1674 1826`), a SaaS dashboard under a children's-book character, product cards for a municipal bicycle garage. 16 of 35 beats, every one passing its own gates. The cause was the ORDER OF OPERATIONS — atmosphere was derived from the topic, form vocabulary was taken from the catalogue, so whatever the catalogue is mostly made of became every film's vocabulary.
> **Ask yourself:** Name the form this beat's SUBJECT is actually recorded, measured or argued about in. Is that what is on screen, or is it the nearest thing the catalogue had?

**S2 · Family VARIETY (whole-film).** **`validate.py` now counts all three of these** — two ADJACENT
beats on one family, a ≥10-beat film spanning fewer than 6, and one family past 45% of the film — and the
counts are in your brief. Do not re-derive them; a finding of yours that repeats one is a finding the
pipeline already had. What a count cannot answer is the next line.

> **Precedent — `3685843`:** Same film. The cause was a selection RULE, not taste: registers were picked by "renders correctly on paper" instead of "belongs to this subject", and this library's centre of gravity is AI-product films — so that filter returned Term* and product registers for a place.
> **Ask yourself:** Which family is this film leaning on, and did it CHOOSE that family or default into it?

**S3 · FAITHFULNESS (hard gate).** Every on-screen NUMBER must trace to the beat's `source_ref` — a register
that shows a figure (ChartLive/BeforeAfterSlider/VelocitySnap/BlueprintGrid counter) left on its **demo default**
(128k / +18% / 0ms / WorkBuddy's 68×) on a DIFFERENT topic is a hard REVISE (pass a sourced figure or switch to a
non-number register). No invented stats, quotes, or sources. And **no WorkBuddy-leftover copy** — a non-WorkBuddy
film with "WorkBuddy"/"on your machine"/"Hy3" on screen means `shot_props` wasn't filled: REVISE.

> **Precedent — `890c09b`:** BlueprintGrid printed a counter driven off the CLOCK rather than off a prop: a confident **100%** above the caption "what was drawn vs what was raised", on the beat whose entire claim is that the cathedral's nave was never finished. It asserted the opposite of the argument it was illustrating. The text scan could not see it — `100%` has no letters in it.
> **Ask yourself:** For every number on this frame, which key of `shot_props` did it come from? If you cannot name the key, the film did not supply the number.

**S4 · DECODABILITY (from the keyframe).** Each shot must read in ~1 s: the focal element is legible, on-frame
labels are real words (not lorem/mystery furniture), the caption sits clear of the content and is readable over
the scene's ground (light OR dark). A blank/half-drawn/garbled frame is a REVISE.

> **Precedent — `d8bb983`:** QuadSplit laid its 2×2 over the whole frame height and put each tile's label at the tile's bottom, so the bottom row's labels sat INSIDE the burned caption band with the subtitle rendered on top of them, and the grid bled past the bottom edge.
> **Ask yourself:** Cover the caption. Can you still read every label — and is anything touching the bottom band?

**S5 · COPY register.** `shot_props` text is SHORT (a title/label, not the whole narration — that's the VO +
caption) and in the deck's language (English or 中文, matching `meta.language`).

> **Precedent — `c19efd2`:** A Chinese route string matched only `AI` under an ASCII-only token regex; every other character was discarded and the copy fell through to hardcoded English placeholders (`Overview` / `Signals` / `Results`). The script exited 0, wrote three sample videos, and the diversity gate scored them.
> **Ask yourself:** Is every word on this frame in the film's language, and did the FILM supply it?

**S6 · A/V + deterministic keyframe QA.** `check_av` and `keyframe_qa_remotion` have already run and
their verdicts are in your brief; a FAIL blocks delivery whatever you think of the frames. You are not here
to re-run them. You are here for the line below, which is the half a gate cannot do — and which this
pipeline has got wrong in both directions: a gate pointed at the wrong artifact reporting a collision that
was not there, and a reviewer judging a composition on a frame grabbed mid-animation, where the plate has
not drawn on and the stamp has not landed. `scripts/settled_frame.py` exists so the second cannot happen by
accident; sample at ~90%, never by eye.

> **Precedent — `8a3938f`:** `shot_still_qa` pointed at delivered `_keyframes/` counts the burned subtitle itself as content: a long CJK line alone scored 5.2% and 13.7% band ink, both reported as collisions that were not there. I read that false signal myself before checking the frames.
> **Ask yourself:** Did each gate run on the RIGHT artifact — and did I look at the frame before believing its number?

**S8 · BOLDNESS / novelty (whole-film, audacity-scaled).** Mirrors the html design-critic's creativity floor.
Is the film's register mix BOLD and memorable for its `meta.audacity`, or did it settle for the safe/obvious
register on beat after beat? At `bold`/`experimental` a timid, expected mix (every statement a plain title, every
metric a bar chart) is a REVISE — name the beats that played it safe and the surprising-but-apt register each
should reach for. The hero + climax beats especially must be unmistakably THIS film, not a default. At
`conservative`/`balanced` this is a nudge, not a gate. (Clarity S4/faithfulness S3 still win — bold never means
illegible or invented.)

> **Precedent — `27a52fa`:** "Build a register instead of settling for the nearest one" existed as a written doctrine, a cheap capability and two consumers — and nothing anywhere WROTE the field, so the "nobody recorded a judgement" warning fired on every default run by construction. A doctrine with no trigger is not a rule.
> **Ask yourself:** On the hero and climax beats: what was the bolder option, and what stopped it being taken?

**S7 · DIRECTION adherence (whole-film).** If `meta.shot_template` is set (the user's chosen direction from the
contest), the film should visibly LEAN toward that direction's families (scripts/shot_templates.py: e.g. data-story
→ D/F/H, terminal-technical → A/C/D, retro-playful → C/G/I) — its hero register or an equivalent should carry the
opener/climax, and the majority of beats should sit in-direction. A film tagged `data-story` that shows no chart/
graph/orrery anywhere, or one whose register mix ignores the chosen direction entirely, is a REVISE (this is a
soft/whole-film judgment — S2 family variety still wins over it; the direction is a lean, not a straitjacket). If
no `meta.shot_template` is set, S7 is N/A.

> **Precedent — none on record.** This is doctrine, not case law: no delivered film has failed S7 in a way anyone recorded. Its verdict carries less weight than the rest of this file, and if you catch a real failure here, write it down as one.
> **Ask yourself:** Name the direction's families, then count the beats that actually sit in them.

**S9 · SEAM RHYTHM (whole-film, from the storyboard — not the keyframes).** The renderer keeps every seam
luminance-safe on its own; your job is the RHYTHM across the film. Read each scene's `transition_style`/`transition_in`
mark: the marks should be BUDGETED (~2-3 in a ≥10-beat film — most seams ride the gentle default fade) and each
should be SEMANTIC — a `clock`/`wipe` on a reveal, a `slide` on a forward push, a `dissolve` where the outgoing
form becomes the incoming, a `carry` (collapse-to-line) on a continuity/resolve beat (and `carry` is the right way
to make a NEEDED dark↔light turn read as continuity). A mark that contradicts its beat (a `slide` on a quiet
close), or every seam marked (as monotonous as none), is a REVISE. Also eyeball the ground-luminance ARC (each
shot's dark/mid/light): a film that flips dark↔light on nearly every beat STROBES — nudge the sequence toward
runs/gradients. The mechanical gates already fire on over-budget marks and >60% hard-flips (`validate.py`
warnings); S9 is the SEMANTIC judgment those can't make. This is a soft dimension — S3/S4 still win.
**The DECLARED native seam is what erases S9.** `meta.design_dna.seam` sets the film's cut for every
UNMARKED seam — which is nearly all of them. On a delivered film it turned 31 of 34 cuts kinetic, and the 3
deliberate marks then read exactly like the 31 that mean nothing: the film lost its punctuation to the
feature meant to give it a voice. So when `design_dna.seam` is set, judge it against the marks. It is OPT-IN,
for a world with a genuine native ACTION at the cut (a terminal clearing its screen); absent that action the
correct answer is to DROP it — a plain cross-fade default is a decision and a good one, not a missing
decision. `validate.py` warns when a declared seam swamps the marks; whether the world really has that action
is yours. Two mechanics to read the marks correctly: `dissolve` now renders a true cross-dissolve (it used to
render a black hole — the installed @remotion/transitions/dissolve is a WebGL film-burn — so an older
complaint about it is stale), and the renderer's luminance guard silently DOWNGRADES a kinetic mark placed
across a dark↔light boundary back to a fade — every type EXCEPT `carry`, whose bridge line IS the dip. So a
`slide`/`wipe`/`clock`/`dissolve` on a crossing seam is not on screen at all: count it as unmarked, say where
the punctuation actually went, and FIX = make it a `carry` or move it. `python3 scripts/seam_plan.py
<out_dir>` is the verify-and-fill pass for a film with no marks at all — it skips every beat the author
marked, so it never competes with a deliberate choice.

> **Precedent — `515cc8b`:** A delivered 35-beat film used NONE of the five seams this tier implements: all 34 cuts were the same anonymous cross-fade, because nothing in the authoring path ever wrote `transition_in` — the key was not in the storyboard at all.
> **Ask yourself:** Which cuts are marked, what does each mark CLAIM about its two beats, and did the luminance guard silently downgrade any of them to a fade?

**S10 · MEANING (per scene) + FRAME-CRAFT (whole-film).** Two things eyeballing kept missing.
**MEANING:** for each beat ask — does this shot's DESIGN *encode* the idea, or is it just dark-and-pretty
decoration that happens to be on-topic? The litmus: *hide the caption — does the visual still carry THIS specific
idea, and only this one?* A symmetric starburst for k-space (k-space IS radially symmetric), a conveyor of lines
for slow serial acquisition, a rising line ONLY when the quantity genuinely rises — those ENCODE. A scrolling
ticker for "frequency encoding," a generic glossy blob, an up-and-to-the-right line for a "slow/bad" point, a
chart type that fights the message (line for independent categories) — those DECORATE or CONTRADICT: REVISE with
the visual whose structure mirrors the content (symmetry/direction/accumulation/sparsity). Refinement (高级感) is
required too, but never as a substitute for meaning.
**CONTENT-FIT (§B2 — the register must be ADAPTED, not text-swapped):** every beat must KEEP the register's style
but REDESIGN its modules/components + content for THIS topic. Read the scene's `shot_adaptation` = `{kept,
redesigned, topic_idea}` (the shot-director's REQUIRED record) and VERIFY IT AGAINST THE PIXELS — this note vs the
keyframe is the check no script can make: does the frame actually show the modules/components rebuilt for this
content, and does the `topic_idea` read on screen? A MISSING or STUB `shot_adaptation` (validate.py WARNs it), or a
note that CLAIMS a redesign the frame doesn't show — placeholder mini-widgets/generic glyphs that don't MEAN the
item (a "product surfaces" tile showing a random bar chart instead of that product's glyph), or a layout whose
relationship is WRONG for the content (sequence-arrows on parallel items, a linear row for a "loop", a short-word
layout given long phrases) — is a REVISE. The test: *would this beat look identical on a different topic with only
the words changed?* If yes → REVISE (rebuild the modules/content to fit, or build an in-style variant). This is a
per-scene gate, not a nit. **But apply the director's own judgment — flag DEMO scaffolding, not originality.** A
stock module the director KEPT because it already encodes THIS topic (recorded in `shot_adaptation.kept`) is
correct, not a violation; do NOT demand a redesign for its own sake. What fails S10 is a module carrying the
DEMO's generic meaning — never one that genuinely fits the content just because it shipped with the register.
**CLAIMS NOBODY MADE (the content contract, `references/remotion-shot-authoring.md` §B1):** for every item on the
frame, list what is drawn ABOUT it — a picture, a status mark (✓, strike-through, green, "active", a lit toggle),
an emphasis (the one accent-coloured item, the spotlit one, the WINNER chip), a quantity (a bar's height, a fill,
a count, a trend line), a relation (an edge between two items). Then find each one in `shot_props`. Anything you
cannot trace to a prop is a claim the film did not make — REVISE, whatever it looks like. The static gate catches
the index-and-constant shapes; it cannot see an index taken from the CLOCK (a highlight that lands on item 4
because the animation ended there) or a fill that runs to 100% while the prop says 40, which is why this pass
exists. A figure on the settled frame must read exactly as the prop wrote it ("−12" is not "12", "3–5" is not
"35").
**FRAME-CRAFT (the floor in `references/remotion-shot-authoring.md`
§A):** read the `text_safe_qa.py` report — any TYPE cut off by the canvas is a hard REVISE. Note what is NOT a
finding, and must not be treated as one: a full-bleed field or flood, and type cropped by a container the author
built (a marquee, a mask, a crop window). `frame_safe_qa.py`'s border reading is ADVISORY — its EDGE-BLEED error
was measured to be inverted (it passed all three known cut cases and blocked all four deliberate full-bleeds), so
rejecting a frame for border ink now rejects the technique, not the defect. A brightness-OUTLIER scene (a
white/bright shot in a dark film) is still a palette-clash REVISE. Then EYEBALL each keyframe
for the defects the report can't see: (a) **BLACK BORDERS** — the shot background must reach all four edges;
a uniform dark margin means something scaled the shot (regression); (b) **title-to-image spacing** — the title
must not touch or overlap the hero image/panel (an image centered in the full frame rides up under the title; it
belongs in the content zone via `fitContentSquare`); (c) **caption overlap** — the burned narration caption never
sits on a shot's own on-frame text (only a small credit line may live in the bottom band); (d) **colliding labels
or markers** — two edge-anchored labels meeting in the middle, or an offset arrow landing ON a long phrase; (e)
**text overflowing to the frame/box edge** on a long label a register sized for short demo words; (f) **a marker
too small to read** (a hairline arrow between big elements). (d)–(f) are the demo-length failures of §A.8 — a shot
that looked clean with its demo props but was given real, longer copy. (g) **ASPECT reflow (§A.9)** — on a
non-16:9 film (`meta.aspect` / `--vertical`), still-render at the film's aspect and confirm each shot REFLOWED: a
multi-column grid must STACK in portrait (not squeeze side-by-side), no wide element runs off-frame, content fills
the taller frame. Meaning + content-fit + frame-craft (incl. aspect) are gates, not nice-to-haves.

> **Precedent — `d8bb983`:** EdStat's figure counted up, so the one beat about a number that could NOT be sourced displayed 17% and then 56% for ~2.8s while the narration said 60%. TermBars settled so late that its mid-scene frame drew the HARD row SHORTER than the medium one at the exact moment the narration said the opposite.
> **Ask yourself:** Hide the caption: does the visual carry THIS idea and only this one — and does it still carry it at the frame the viewer actually sees, not just at the end?

**S11 · DESIGN-SYSTEM COVERAGE (the Consistency Critic — whole-film + per-scene).** The selected template is a
GLOBAL visual system (the `meta.design_dna`), not a decorative theme on one or two frames. Two checks:
**Per scene:** identify **≥2–3 concrete elements that tie this shot to the Design DNA** — typography (does it use
the DNA's mono/display font?), palette (the DNA `accent`/`bg`, not the register's original hue?), container/border
style, motion personality, or an annotation cue (prompt `▸` / cursor / status / grid / mono metadata). Cross-check
the scene's `shot_adaptation.theme_cues` against the RENDERED keyframe — are the claimed cues actually on screen? A
shot that still wears its ORIGINAL identity (a serif cinematic title, an Apple-watch gauge, a rainbow chart) with
<2 DNA connections is **visually disconnected → REVISE** (restyle it into the DNA via `useDNA()` tokens, or rebuild
it; never leave it off-system because the component already existed).
**Whole-film FINAL TEST (docx §9):** mentally REMOVE the 1–2 shots that are obviously the theme (a literal
terminal/code shot). From the REMAINING shots alone, could a viewer still infer the film's design language? If NO,
the DNA has not propagated deeply enough — name the disconnected shots and REVISE. The template must behave like a
design grammar, not a coat of paint on a few frames.
**Balance (docx §13) — consistency ≠ repetition:** do NOT demand every frame be a literal terminal window; a
metric / diagram / chart beat satisfies S11 by inheriting the DNA's type + palette + motion + 2–3 cues, not by
becoming a black-green box. Flag the OPPOSITE failure too — every shot an identical explicit style CONTAINER
(the same terminal window / the same magazine spread) reads as monotony. Apply the **three-layer balance**
(§C2, style-AGNOSTIC): only 2-3 anchor beats should show the explicit container; the rest must inherit the
grammar on OPEN canvas with a PER-CONTENT layout + native action→result motion. And the **reject rule** — a shot
that could be dropped unchanged into a completely DIFFERENT style unnoticed has NOT been assimilated → REVISE.
This is a whole-film gate at `bold`/`experimental`, a strong nudge otherwise; it never overrides S3 (faithfulness)
or S4 (legibility). `validate.py` backstops it mechanically (a themed film with no `design_dna`/preset, or a scene
with no `theme_cues`).

> **Precedent — `2e72980`:** `dnaPalette` grew categorical tones with a 47° hue rotation, which walks OUT of the film's palette: on the green+amber DNA, tone 3 landed on cyan-blue, and 19 registers ask for n≥3. Separately, a shot rendered standalone had no `DesignDNAContext` at all, so a palette bug was literally invisible until a full film render.
> **Ask yourself:** Point at a colour, a typeface and a corner treatment on this frame and name the DNA token each came from.

**S12 · CAMERA MOTIVATION (whole-film, from the storyboard + the keyframes).** A beat may carry
`camera: {move: 'push'|'pull'|'hold', amount}`. The renderer clamps the amount to what the caption band can
absorb — a push scales about the CONTENT zone, and unclamped it would drive the shot's lowest content down
onto the burned caption — and rides the move on `useT()`, so a cut never happens over a moving camera.
`validate.py` checks only the vocabulary (push/pull/hold, amount 0-0.2); whether the move had a reason is
yours. Three checks: **(a) MOTIVE** — a `push` belongs on the beat where the argument LANDS (look closer at
what is here), a `pull` on the opening beat and on the close (here is the whole of it). A move on a beat that
is merely the next one in the list is a wobble, and motion with no cause is exactly why this tier's earlier
film-wide sinusoidal drift had to be switched off: FIX = `camera.move: "hold"`. **(b) BUDGET** — 2-4 moving
beats in a film. A film whose camera always moves has no camera, in the same way a film where every cut is
marked has no punctuation. **(c) SUBJECT** — the move must land on SETTLED content that repays it. A shot
reveals over roughly t 0.05-0.45 and the camera runs 0.28-0.88 for that reason, so by the time the push
arrives the frame is finished: for those 2-4 beats only, open the keyframe and ask what it is pushing INTO. A
push on two rows of text magnifies two rows of text; spend it on a beat whose frame HOLDS something — a
photograph, a built figure, a diagram with parts. FIX = move the push to the beat that has one, or hold.
Also: a ≥12-beat film with NO `camera` on any beat is a DECISION (a static register mix, a reduced-motion
delivery), and should read as one; if nothing explains it, say the film left its camera unrun and name the
payoff/close beats that should have carried it — `python3 scripts/seam_plan.py <out_dir>` derives a plan from
the beats' `relation` field and skips any beat already authored, so "we didn't get to it" is not a reason.
Soft dimension: S3/S4 still win.

> **Precedent — `0dfde89`:** 4 of 146 registers used a 3D rotation, none used focus, and the camera had been switched off entirely — space is this tier's whole claim over the HTML one, and it had none.
> **Ask yourself:** What does this beat's camera move CLAIM? Would a viewer who could not hear the narration know why the frame moved?

**S13 · REAL IMAGERY (whole-film — concrete topics only).** N/A when the subject is abstract (a method, an
argument, a quantity with no photographable body). On a CONCRETE topic — a place, an object, a machine, a
specimen, a system with a physical body — and where the fetched images in the out_dir carry `<file>.json`
sidecars (i.e. `scripts/imagefetch.py` already found license-clean ones), ask whether the photographs CARRY
the film or footnote it. The measurement that produced this check: a delivered film about a physical city,
with clean images available, used real photographs at 5.3% / 8.5% / 16.3% of the frame — three thumbnails
dropped into layouts, the evidence demoted to a garnish. **Floor: at least ONE beat on which a photograph IS
the frame, and two where the fetch returned several** — it reads as the subject at roughly ⅓ of the frame or
more, not a tile inside a card grid. Estimate from the contact-sheet cell; open the full keyframe only when
it is borderline. The register for it is **PhotoPlate** (LIBRARY 171): the photograph is the evidence and the
film's own numbered marks land at points IN it as the narration names them. Its neighbours answer different
questions — `ScanReconstruct` (revealed by its own process), `MuseumLabel` (cited beside a catalogue label),
`RealVersus` (A against B) — so a beat using one of those to dodge the floor is answering a question the beat
did not ask. A concrete-topic film that shows no real image anywhere while sidecars sit unused is a REVISE:
name the 2-3 beats whose claim is "look at the actual thing". CREDITS are machine-decided — `validate.py`
ERRORs when a beat shows a sidecar'd image whose author it fails to name — so read that verdict rather than
re-checking it, and never repair one by typing a photographer's name from memory: it comes from `<file>.json`.


## Output
For each flagged scene: `scene #N · Sx · <what's wrong on screen> · FIX: <the concrete change — a different
`shot` id, or the `shot_props` key+value to set>`. End with a verdict: **PASS** (deliver) or **REVISE** (list the
scenes; the shot-director applies the fixes and re-renders those beats, then you re-review the changed frames).
Be specific and evidence-based — cite the keyframe you saw. Consent to deliver only when S3 (faithfulness) and S6
(A/V + keyframe_qa) are clean, no scene fails S1/S4, and — at `bold`/`experimental` — S8 (boldness) AND S11
(design-system coverage — the Design DNA runs through EVERY frame, not just the themed ones) are satisfied.

**And write the ledger — the verdict is the ledger, not the prose.** Every dimension gets a row, the clean
ones too, each citing what the verdict rests on; `python3 scripts/critic_ledger.py <out_dir>` must exit 0.
"Silence is not consent" was addressed, as prose, to the only party it could not audit; the ledger is the
version of that sentence a later reader can check.

**The DELIVERY review is a fresh subagent, not you.** Whoever directed the shots cannot be its first reviewer:
the maker holds the intent, and the intent is what makes a wrong frame look right. (Measured in this repo: a
seam fix was landed, the incoming shot measured 0.63% ink against 0.63% settled, and the number proving it had
NOT worked was written into the code as the motivation for it. A reviewer holding no memory of intending it
reads that frame as what it was — blank.) So before delivery, dispatch this file as a subagent whose ENTIRE
input is the `<out_dir>` path — no design rationale, no summary of what was fixed, no list of what to look at
— and let it reach its own verdict; it records `reviewer: "independent"`, and
`python3 scripts/critic_ledger.py <out_dir> --final` REFUSES an in-context ledger. Reviewing in-context is
fine while iterating; it is not what the user is handed.

> **Precedent — `e385da7`:** On a delivered film about a physical city the real photographs occupied 5.3%, 8.5% and 16.3% of the frame — the evidence was a footnote in a film of drawings. And the proof sheet was blind to the class most likely to be wrong: that same run fetched three images and two were of the wrong city (`e68c174`).
> **Ask yourself:** Does the film ever SHOW the thing it is about at a size that lets it be read — and is the thing shown the right one?

**S14 · GROWTH — did the film BUILD, or only choose?** The catalogue is a starting vocabulary, not the
set of things this tier can say. `meta.form_vocabulary` is the film's derivation of how its OWN subject is
recorded (shot-director step 0.5), and rule 2 there requires at least half of it to be forms this library has
never held — so on a subject the library has not met, `shot_fit.verdict: "build"` is the NORMAL case, not an
emergency. Judge it: name the beats whose form the catalogue could not carry, and say whether the film built
for them or settled for the nearest register and let the adaptation note paper over the gap. A film that used
a one- or two-register family and took its only member — when that member's structure did not carry the
beat's argument — should have built. `validate.py` warns when the declared vocabulary is mostly names the
library already has; whether the FORMS are really this subject's is yours.
> **Precedent — `27a52fa`:** "Build a register instead of settling for the nearest one" existed as a written
> doctrine, a cheap capability and two consumers — and nothing anywhere WROTE the field, so the "nobody
> recorded a judgement" warning fired on every default run by construction. This dimension was itself
> unnumbered prose in this file's opening section until the verdict ledger made every NUMBERED dimension
> mandatory: growth became the one judgement that could still be skipped without a trace, which is exactly
> the shape it describes.
> **Ask yourself:** Which beat's form did the catalogue not have — and what did the film do about it?

**S15 · BUILT THINGS — does each thing the film built carry its beat?** For every `meta.build_list` entry (the
brief lists them with their beats, `means` and `accept`), judge it on its rendered frames — its settled frame
(`<out_dir>/workshop/_stills/<id>.png` when the maker rendered one) and its beats' keyframes: (a) with the caption
hidden, does it carry its entry's `means` — does it pass its own `accept`? (b) can a first-time viewer name what it
is in about a second? (c) does it belong to this film's Design DNA — its ink, type and motion — or read as another
film pasted in? (d) is it better than the library's nearest register would have been, or a worse copy of something
the library already had? And the other direction, which S1 and S14 begin: for each beat that did NOT build, name
why the library register's STRUCTURE — not just its words — carries that beat. `na` only when the film built
nothing AND every beat's structure fits; say which.
> **Precedent — none on record.** This is doctrine, not case law: a film's own built things are new. When one fails
> here, write it down as the first case.
> **Ask yourself:** Hide the caption on each built thing — what does it say, and is that its beat?

