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
**S1 · Register FIT.** Does the chosen `shot` express THIS beat's idea (match it to the register's LIBRARY
"use when")? A statement beat on a data-chart register, or a climax on a flat list register, is a REVISE.
If a NEW shot draws a quantity bar, a headline figure or a list without using `runtime/atoms.tsx`, it must
say why — those parts have a per-DNA form and a hand-rolled one will not follow the film's system.
**S2 · Family VARIETY (whole-film).** No two ADJACENT beats may share a family (A–Z in LIBRARY.md, an OPEN set — AA+ if extended); a ≥10-beat
film should span ≥6 families and not lean on one. Two adjacent same-family beats = REVISE the second.
**S3 · FAITHFULNESS (hard gate).** Every on-screen NUMBER must trace to the beat's `source_ref` — a register
that shows a figure (ChartLive/BeforeAfterSlider/VelocitySnap/BlueprintGrid counter) left on its **demo default**
(128k / +18% / 0ms / WorkBuddy's 68×) on a DIFFERENT topic is a hard REVISE (pass a sourced figure or switch to a
non-number register). No invented stats, quotes, or sources. And **no WorkBuddy-leftover copy** — a non-WorkBuddy
film with "WorkBuddy"/"on your machine"/"Hy3" on screen means `shot_props` wasn't filled: REVISE.
**S4 · DECODABILITY (from the keyframe).** Each shot must read in ~1 s: the focal element is legible, on-frame
labels are real words (not lorem/mystery furniture), the caption sits clear of the content and is readable over
the scene's ground (light OR dark). A blank/half-drawn/garbled frame is a REVISE.
**S5 · COPY register.** `shot_props` text is SHORT (a title/label, not the whole narration — that's the VO +
caption) and in the deck's language (English or 中文, matching `meta.language`).
**S6 · A/V + deterministic keyframe QA.** `check_av` must pass (video/audio in sync, no truncation) AND
`python scripts/keyframe_qa_remotion.py <out_dir>` must pass — the machine backstop behind your eyes: it fails
loud on any scene keyframe that rendered BLANK / near-uniform (a malformed prop, a regressed bundle, a frozen
empty beat). Run it before you consent; a FAIL blocks delivery.
**S8 · BOLDNESS / novelty (whole-film, audacity-scaled).** Mirrors the html design-critic's creativity floor.
Is the film's register mix BOLD and memorable for its `meta.audacity`, or did it settle for the safe/obvious
register on beat after beat? At `bold`/`experimental` a timid, expected mix (every statement a plain title, every
metric a bar chart) is a REVISE — name the beats that played it safe and the surprising-but-apt register each
should reach for. The hero + climax beats especially must be unmistakably THIS film, not a default. At
`conservative`/`balanced` this is a nudge, not a gate. (Clarity S4/faithfulness S3 still win — bold never means
illegible or invented.)
**S7 · DIRECTION adherence (whole-film).** If `meta.shot_template` is set (the user's chosen direction from the
contest), the film should visibly LEAN toward that direction's families (scripts/shot_templates.py: e.g. data-story
→ D/F/H, terminal-technical → A/C/D, retro-playful → C/G/I) — its hero register or an equivalent should carry the
opener/climax, and the majority of beats should sit in-direction. A film tagged `data-story` that shows no chart/
graph/orrery anywhere, or one whose register mix ignores the chosen direction entirely, is a REVISE (this is a
soft/whole-film judgment — S2 family variety still wins over it; the direction is a lean, not a straitjacket). If
no `meta.shot_template` is set, S7 is N/A.

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
**FRAME-CRAFT (the floor in `references/remotion-shot-authoring.md`
§A):** read the `frame_safe_qa.py` report — any OFF-FRAME edge-bleed is a hard REVISE (title/action-safe), and a
brightness-OUTLIER scene (a white/bright shot in a dark film) is a palette-clash REVISE. Then EYEBALL each keyframe
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
Silence is not consent: if a keyframe is missing, `check_av` or `keyframe_qa_remotion` didn't run, say so and
withhold PASS until it does.
