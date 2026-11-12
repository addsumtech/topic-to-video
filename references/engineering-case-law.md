# Engineering case law

Rules for whoever EDITS this library — the analogue of `agents/shot-critic.md`, which is case law for
whoever judges a finished film.

**Why this file exists.** This repository has a great deal of hard-won knowledge about its own failure
modes, and until now all of it lived in commit messages and docstrings, where no reviewer walks it. At the time of writing the commit bodies
carry about 112,000 words of it. A rule states what to do; the PRECEDENT states what went wrong,
and the precedent is the half that generalises to a case nobody has seen — "read a gate's count as
coverage" means little until you read that the ground-token check printed green over a 160-shot library
while skipping the three entries most likely to be wrong.

**The form, and why each part is load-bearing.**

* **An executable sentence.** A rule you cannot mechanically fail is a preference.
* **A precedent, named by the commit that repaired it.** `scripts/critic_ledger.py` parses the hashes out
  of this file and `tests/test_remotion.py` resolves every one of them against this repository's history,
  so a fabricated precedent cannot be committed — "never fabricate" is otherwise a standing rule that
  nothing enforces, and an invented incident reads exactly like a real one. A rule with no incident behind
  it says **Precedent — none on record** in as many words and is scored as weaker evidence. That admission
  is the honest form, not a hole to be filled with something plausible.
* **A question to ask yourself.** Phrased so that answering it requires looking at something, not
  remembering something.

**It is APPEND-ONLY.** Numbers are never reused and never renumbered — a precedent cited from a commit
message years from now has to still land on the rule it meant. Superseded rules are struck through and
kept.

**When to walk it.** Before committing a change to the renderer, the runtime or a gate, walk the rules
this change touches and report `En ✓` / `En ✗ (where)`. A deliberate violation is written down, not
silently taken.

---

**E1 · A RESERVE IS ARITHMETIC ABOUT A LAYOUT THE BROWSER PERFORMS, AND THE TWO CAN DISAGREE.** Any space
a shot holds back for something else — the caption band, a note under a headline, the row below — must be
counted by BREAKING the text in the measure the element is actually given. Never by dividing a total width
by a measure, and never as a fixed fraction of the frame.

> **Precedent — `75d1705`:** `fitBlockPx` counted lines as `ceil(totalWidth / measure)`. That ratio is only
> right when a glyph is small against the measure, and for CJK it never is: eleven Han glyphs in a 766px
> measure at 198px is four lines, and the ratio said three. The fit believed it had fitted and put the
> fourth line 117px inside the caption band. Twelve more registers in the same commit placed a bottom block
> by a flat fraction of `H` and reserved exactly the one line their English demo copy took.
> **Ask yourself:** Name the measure you counted in, then name the width the element is actually given by
> the browser. Are they the same number? (`KineticManifesto` failed because `maxWidth: 82%` plus padding on
> a flex item was not the number the fit had used.)

**E2 · AN ADVANCE IS A PROPERTY OF THE FACE, NOT OF THE CHARACTER.** A Han glyph is one em in a
proportional face and TWO CELLS in a monospace one. Any width estimate must be told which face draws it.

> **Precedent — `fead316`:** Every fitter in `runtime/layout` carried one Han advance, 1.05 — the
> proportional answer — so every Chinese string in a monospace register came out under-measured by 14%, and
> `white-space: pre`/`nowrap` meant none of them could wrap out of it. TermGitLog ran a commit message 345px
> off the frame, TensionScale centred a note 68px too wide on BOTH sides, BlueprintGrid clipped a spec by
> 288px. The same defect sat one level up in the PREDICTION path: `PhotoPlate` measured its callout chip
> with the proportional constant under a comment saying the chip's face is monospace, and `Film.tsx`
> predicted the caption's wrap the same way — under the terminal DNA the caption is set in the mono stack,
> so the caption the band was sized for was not the caption that got drawn.
> **Ask yourself:** Which face actually draws this string — the DNA's, not your fallback stack's? Did you
> hand the fitter that face's advance?

**E3 · THE INSTRUMENT IS WRONG BEFORE THE FILM IS.** When a gate reports a finding, ask the gate which
element it means and look at that element before changing anything.

> **Precedent — `6c98263`:** `frame_safe_qa`'s edge-bleed check blocked delivery on border ink and was
> backwards on both sides — the three registers genuinely cut by the canvas measured 1.00–4.40% against a
> 4.5% floor and all shipped, while four deliberately full-bleed registers (up to 35.2%) were blocked. It
> would also have refused 100% of the sampled frames of one reference launch film and 57% of two others,
> while passing every frame of a film that measures as inert. Zero true positives, four false ones.
> `d109ce0` is the same lesson three more times in one sitting: "the reading was wrong before the register
> was, and each corrected instrument then surfaced defects nobody could have seen through it."
> **Ask yourself:** Before you fix what the gate reported — what exactly does it say is wrong, and does
> that element actually look wrong when you render it?

**E4 · READ A GATE'S OWN COUNT AS COVERAGE.** A gate that prints a number has told you how much it looked
at. Compare it to how much exists.

> **Precedent — `d480b52`:** The ground-token drift check reported green across the library and was
> skipping the entries most likely to be wrong — it printed "matches (157 shots)" over a 160-shot library,
> and the three it could not classify were silently not judged.
> **Ask yourself:** How many items does this gate say it checked, and how many are there? What happens to
> the ones it cannot classify — are they judged, or dropped?

**E5 · A FIXTURE PROVES WHAT IT WAS GIVEN, AND NOTHING LONGER.** A synthetic input bounds the claim; the
register's real bound is wherever a film's own copy goes.

> **Precedent — `fead316`:** The CJK fixture hands every `word`-shaped prop a FOUR-glyph phrase. At 240px
> that is 960px, which clears a 1080-wide frame by sixty — so the sweep proved 28 literal-display-type
> registers survive four glyphs and reported all of them clean. Handed an eight-glyph phrase, `InflateType`
> sliced it 450px on the left and 461px on the right, and `ElasticType` 412px each side.
> **Ask yourself:** What is the most extreme value this fixture ever produces? Is that the register's limit
> or the fixture's? Run one input past it.

**E6 · AN AXIS THE SWEEP NEVER VARIES IS AN AXIS NOBODY TESTED.** Enumerate the values the renderer offers
on every axis a gate is sensitive to, and compare that list to the values the gate was actually run with.

> **Precedent — `ca0531c`:** `text_safe_qa --library --aspect=` had existed since the portrait work, and
> 1:1, 4:5 and 4:3 had never once been passed to it. Running them found 25 findings across 16 registers,
> 21 of them at 1:1 alone. `fead316` is the same hole on the DNA axis: `scan_library`'s own docstring says
> the Design DNA "sets the type family and therefore every metric this audit measures", and the sweep had
> only ever run `product` — one of nine. Under `editorial`'s serif, `VariableTypeMorph`'s one enormous word
> was sliced at BOTH edges of a 1:1 frame while the product sweep called it clean at all five aspects.
> **Ask yourself:** List the values this axis can take, from the renderer's own table, and the ones the
> sweep ran. Read the difference out loud.

**E7 · A RULE IS NOT LOAD-BEARING UNTIL A MUTATION PROVES IT.** Break the thing the rule forbids and watch
the test go red. A test that passes both ways pins nothing.

> **Precedent — `3dbf459`:** A fixture test asserted `isinstance(v, str)` and broke the day
> `MagazineSpread` grew a list prop. It had pinned a SHAPE, not the rule — which is that every value the
> fixture produces is CJK copy shaped from the register's own signature, and a list of strings is that too.
> **Ask yourself:** Write the mutation this test is supposed to catch, apply it, and run the test. Did it
> fail? If a positive control is not available, say so rather than assume.

**E8 · A CONSTANT SITTING WHERE A MEASUREMENT BELONGS IS A NUMBER THAT WAS RIGHT AT ONE RESOLUTION.** Every
length in a register is either derived from the frame or is a bet that the frame is 1920×1080.

> **Precedent — `fead316`:** `MagazineSpread` was composed entirely in 1920-tuned literals: at 1:1,
> `W - 2*150 - 640` left the headline a 140px ribbon setting one word per line, the 132px masthead ran into
> the issue line, and the deck — pinned at a flat 720 — ran straight across the hero plate and through its
> caption. `CommandSummon`'s command palette was 1180px wide on the four aspects that are 1080 wide, so its
> left edge was NEGATIVE before a character was typed into it. `MaterialHero` clamped each projected label
> to `band - pad`, where pad is 3.5% of the short side — a line and a quarter of the label's own type, while
> a Chinese label in that box wraps to three.
> **Ask yourself:** At which frame size was this number right? Compute it at the SMALLEST frame the renderer
> offers (min(W,H) is 1080 at every aspect) and say what it becomes.

**E9 · A SILENT DEFAULT IS THE DANGEROUS KIND OF WRONG.** A helper that cannot answer must fail loudly or
return something correct — never `undefined`, `None`, `0` or `''` into a consumer that will quietly accept
it.

> **Precedent — `fead316`:** `readableOn(bg, ...candidates)` called with no candidates returned
> `undefined`. React drops a style property whose value is undefined, so the element inherits — and a bare
> inherited `color` is black. `SourceDeal` wrote `readableOn(SURF)` as the repair for conclusions that were
> black on a dark surface, and the repair reproduced the defect its own comment describes: measured off the
> rendered frame, the pill label was **1.14:1** against its pill. No typecheck saw it — the signature says
> it returns `string` — and no text gate measures contrast.
> **Ask yourself:** What does this return when it cannot answer? Follow that value into its consumer and
> say what the consumer does with it.

**E10 · THE DOCUMENT THAT WOULD HAVE CAUGHT IT MUST POINT AT SOMETHING THAT STILL RUNS.** A rule is only as
live as the command the next author is told to run.

> **Precedent — `7fc5e24`:** The two documents a register author actually reads both told them to run
> `scripts/gen_dna_ground.py`, which had been retired for as long as the measured table existed and exits 2
> with its own obituary. The rule it was there to enforce was therefore unenforced for every author who
> followed the instructions.
> The guard that shipped with that repair named `gen_dna_ground.py` as a LITERAL — it caught the instance,
> not the class, so a second retirement would have been invisible to it.
> `test_no_author_facing_doc_points_at_a_script_that_does_not_run` now enforces the class: every
> `scripts/*.py` named in SKILL.md, `references/` or `agents/` must exist, and one whose module docstring
> opens with RETIRED may be NAMED (to say it is retired) but not prescribed. The signal is calibrated on
> that real stub rather than on the word appearing near the top of a file — the crude version flagged
> `shot_director.py` three times over a retired family LETTER in a comment, which is how a gate becomes
> noise nobody reads.
> **Ask yourself:** Run the command this document tells the next author to run. What is its exit code —
> and did you read the exit code of the command you meant, or of the last one in the pipe (E13)?

**E11 · A FIX IS NOT GENERAL UNTIL IT HAS MET AN INPUT IT WAS NOT TUNED ON.** The input you fixed it
against is the one input you know it handles.

> **Precedent — `0cda879`:** Sixteen registers repaired for the aspect sweep held under two DNAs and two
> aspects none of the work had been tuned on — and a stress harness then found that FOUR of those same
> fixes had been fitted to their demo props: a clamp with no floor put a label at y = −237, another divided
> a width by four, a third assumed a one-line banner, a fourth scaled by the wrong dimension. 18 findings
> that the fix's own case could not show.
> **Ask yourself:** Name one input this fix was not built around — a different language, aspect, DNA, or an
> empty/extreme value — and run it.

**E12 · PASSING GATES IS NOT CORRECT OUTPUT. RENDER IT AND LOOK.** Every gate measures what it can measure;
composition is mostly not that.

> **Precedent — `fead316`:** `MagazineSpread` carried ZERO text findings at all five aspects while its
> masthead sat on its issue line, its deck ran through the hero plate's caption, and its headline column
> was 140px wide — because nothing was cut off and nothing was in the band, which is all the type gate
> asks. `VariableTypeMorph` was likewise clean at all five aspects under `product` while `editorial` sliced
> its word at both edges. Both were found by rendering a still and looking at it, and both were verified
> the same way at all five aspects.
> **Ask yourself:** Have you looked at this frame — the actual PNG — since the change? At the narrowest
> aspect?

**E13 · THE EXIT CODE YOU READ MUST BE THE ONE YOU MEAN.** In a pipeline the status is the LAST command's;
`cmd | head` and `cmd; echo $?` both report the wrong process. Capture the output and test it, or check the
specific field.

> **Precedent — none on record.** This is doctrine, not case law: it happened twice in working sessions —
> most recently `npx tsc --noEmit | head -5 && echo TSC-CLEAN` printing TSC-CLEAN over a real type error —
> but neither produced a commit that repaired a shipped defect, so it is scored as weaker evidence than the
> rules above. If you catch a real failure here, write it down as one.
> **Ask yourself:** Which process produced the status you just read?

**E14 · A PICTURE BESIDE A LABEL IS A CLAIM ABOUT THAT LABEL.** Anything a register draws next to a film's
item that a viewer reads as information — a picture, a status, an emphasis, a quantity, a relation, a figure —
must come from a prop the film set. Not given, it is not drawn: no status, no emphasis, equal treatment, no
picture. Never a stand-in chosen by index, a hash, a constant or the clock; never a list cycled to fill slots;
never a film figure re-typed.

> **Precedent — `9588d4a`:** a user asked what a sparkline, a loading ring and a sine wave had to do with 路飞 and
> 哆啦A梦. `BentoReveal` picked each cell's widget by `kind={(i - 1) % 6}`, computed the bar heights from the
> index and the clock, and cycled the labels to fill six cells. A read of all 168 registers found the same
> class in about sixty: `k < 2 ? '✓'` marking a film's first two to-dos done, `const HERO = 2`, tower heights
> from `hash01(i)`, a hardcoded rising series under a sourced figure, `parseFloat(v.replace(/[^\d.]/g, ''))`
> printing "−12" as 12 and "3–5" as 35, `fill ?? 0.6` inventing a gauge reading. Every gate was green on every
> one of them, because every gate measured type. `scripts/content_contract_qa.py` now reads the source for
> those shapes and `tests/test_content_contract.py` holds the library to it.
> **Ask yourself:** For each thing this register draws about an item, which prop did it come from — and what
> does the frame show when the film leaves that prop out?

**E15 · A SEAM THAT FADES ITS LEAVING HALF MUST PAINT THE FILM'S GROUND UNDER IT.** Remotion's own `fade`
never shows this because only the ENTERING half carries an opacity and the beat being left stays opaque
beneath it. The moment a presentation fades BOTH halves — for a dip, a rack, a drift — whatever is behind the
sequences becomes visible at mid-seam, and that is black. Judge a new seam by measuring the frame's mean
luminance across it on a LIGHT film; a dark film cannot tell you.

> **Precedent — `688a603`:** `fadethrough` between two near-white beats (settled mean 222) measured
> 222 → **13.5** → 222 — a black hole between two cream frames, on a seam whose entire claim is "the same
> reset, emphasis on what arrives". The same measurement then found the identical hole in `focus`, a seam
> that had been shipping since `4b4e8ce` and had been reviewed by eye on dark films only. Both now paint the
> beat's own ground under the exiting half (`SeamGround`), and the same film measures a minimum of 222.
> This is the third time this repository has put a black hole in a seam: `@remotion/transitions/dissolve`
> rendered "a full black hole where the seam should be" between two cream shots, and the fix there was to
> stop using it. The defect is not a library's bug — it is what compositing two faded layers over nothing
> looks like.
> **Ask yourself:** On a light film, what is the lowest mean luminance any frame of this seam reaches?

**E16 · A SHARE CANNOT TELL A LOST SENTENCE FROM A SOFT RIM.** A gate that reduces a picture to "what
fraction of the ink failed" has thrown away the only thing that decides whether a reader lost anything:
WHERE the failures were. Scattered anti-aliased rims and a paragraph turning white-on-white produce the same
number, so any floor drawn on that number is drawn between two things it cannot distinguish. Measure the
SHAPE of the failure as well — close the failing marks so a word reads as one thing, label the connected
regions, and report the largest.

> **Precedent — `4b99a6c`:** `scripts/ink_contrast_qa.py` reported a register when its MEDIAN mark fell
> under 3:1 or when half its marks did. `StateSheet` (43% of marks failing: a dozen tiny mono captions
> keeping a soft rim, a dozen card borders losing their edge — a reader misses nothing) and `AnswerStream`
> (46%: the right half of a three-line answer turned white-on-white, and the words of the beat stopped
> existing) sat either side of no line at all. Five real registers shipped under that floor — `AnswerStream`,
> `TerrainFly`, `ExplodedSchematic`, `PixelBuild`, `InflateType` — one of them, at **49.45%**, by half a
> percentage point. Measured as the largest connected failing region the same six separate cleanly: the
> artefact 552 px, the five real ones 1526–20805. The same measure also caught the SECOND half of
> `FractureIn`'s defect: routing its literal ink through the DNA took it from 51% to 42% — passing — while
> a drop shadow tuned for a void (14px down, 40px blur, 38% black) went on filling the 6px gap under every
> tile, so a 5×5 grid read as five vertical strips. Scaling the shadow to the ground took it to 0.3%.
> **Ask yourself:** Of everything this gate reports as one number, what two pictures would score the same —
> and would a reader tell them apart in a second?

**E17 · A SEAM'S PRESENTATION RUNS ON EVERY FRAME OF ITS BEAT, NOT ONLY ON THE SEAM.** A TransitionSeries wraps
the WHOLE of each sequence in its exit presentation (at progress 0 until the seam begins) and in its entrance
presentation (at progress 1 after it ends). Anything a presentation paints, transforms or measures at progress 0
or 1 it does for the entire beat — including the frames in which that beat is the OTHER half of a different seam.
Gate everything on "am I in my seam" (the leaving half's own clock, the arriving half's progress below 1), and
look at the first and last frame of a cut, not only its middle.

> **Precedent — `2ba24a0`:** `SeamGround` painted the film's ground under every EXITING half, so a beat whose own
> exit was a whip carried an opaque full-frame ground from its first frame — on which it was still arriving over
> the beat before, and covered it: a paper beat cut to near-black on the first frame of a plain dissolve (frame
> mean 205 -> 9.7). On a product film every unmarked cut is that whip. It had shipped since the ground was added,
> found only by looking at a probe's seam frames one at a time; the same wrapping is why the first anchored seam
> looked for its partner on its beat's first frame and found nothing.
> **Ask yourself:** On a frame where this beat is not in this seam at all, what does this presentation draw?


**E18 · A STRUCTURE A GATE CANNOT JUDGE IS HANDED TO ONE THAT CAN — NEVER SKIPPED.** When a gate meets something its
model does not describe (a composited layer, an unknown kind, a renderer path it cannot read), it names it and passes
it to an instrument that measures the OUTPUT, and that instrument is on the delivery path. A `continue` with a comment
is a silent pass.

> **Precedent — `6fd5ab8`:** the type-glide census listed every line of type on a 3D or will-change layer with flag
> `c` and judged none of them ("listed for pixel checks, not judged" — no pixel check existed). A product film put its
> whole UI panel inside a 3D screen and re-laid it out at the camera's size every frame; every gate was green, and the
> viewer saw the type tremble. Measured from the delivered pixels against the census's own geometry: 0.2-0.6px RMS on
> every line of two beats, against 0.002px for the film's 2D type. The same panel drawn flat stepped exactly as much —
> the layer did not cause the defect, it hid it. `jitter_qa.py` now judges every line on every layer from the pixels.
> **Ask yourself:** Which items does this gate `continue` past? For each, which instrument judges it instead — and is
> that instrument a blocking gate, or a comment?

**E19 · A MEASUREMENT THAT FINDS A CONFIDENT ANSWER IN THE NOISE HAS MEASURED THE NOISE.** Before a reading is
believed, the thing it reads must be shown to be there: a correlation needs the signal's edges above the grain, a
census needs the frames to be the frames that were stored. A strong peak, or a matching count, is not that proof.

> **Precedent — `21c8784`:** `jitter_qa` read a line drawn at the ground's own grey — no type at all — as 29 pairs
> CLEAN: the film's static ±2 dither does not move, so the phase correlation locked onto it with a confident peak, and
> the detrend took the resulting constant error out. Faint type 4 grey levels over its ground half-read the dither the
> same way and measured 4.3 px of travel against a census that said 10.7 — also clean. The repair gates every window
> on its band-passed edges clearing the grain (skipped and counted otherwise) and reports a line whose pixels do not
> follow its geometry. The same sitting found the decoder's default constant-rate output inventing a frame at a
> clip seam (360 stored, 361 decoded), which would have compared every later pair with the wrong frame.
> **Ask yourself:** Feed the instrument an input that holds NO signal (a blank line, a grey frame, a census of another
> render). What does it say — and is that word distinguishable from "clean"?

---

## Run-time case notes — why the workflow says what it says

The E-rules above bind whoever EDITS the library. The notes below are the precedents behind rules that bind
a FILM RUN; the rule itself lives in `SKILL.md` at the step where it is acted on, in imperative form, and
points here for the why. They are numbered `W`, not `E`, so `critic_ledger.py` does not read them as library
rules; append-only, like the rest of this file.

**W1 · THE SCRIPT IS HEARD BEFORE IT IS SIGNED OFF** (SKILL.md step 5, `script_audition.py`).
> **Precedent — `164117a`:** a 37-beat script cleared every `voice_qa` metric (CV 0.45 · antithesis 8% ·
> connectives 38% · aphorism endings 5%), passed two independent content critics, was read end-to-end by its
> author — and the person it was made for said, on the first listen, 「脚本没有人的感觉，读起来也很机器」.
> Every check in this pipeline READS the narration; the defect is AUDIBLE. `references/anti-ai-voice.md`
> opened with "the last pass is always a human read-aloud" and nothing in the workflow produced anything to
> read aloud. The old instruction at that step was "do not synthesize audio until they sign off", which made
> the sign-off a reading of a document whose only destiny is to be heard. `1b1cfa0` then moved the voice
> question (⑤) to the audition: choosing an engine before hearing anything was the most abstract question in
> the interview, and the up-front interview shrank from two screens and seven questions to one screen.

**W2 · A CAPABILITY THE RUN NEVER CALLS IS ABSENT** (SKILL.md step 3.6 ③, `seam_plan.py`).
> **Precedent — `515cc8b`:** a 35-beat film shipped with all 34 of its cuts the same anonymous cross-fade and
> a camera that never moved, while every gate stayed green. The seam vocabulary was complete, tested and
> documented — and unreached, because nothing in the authoring path wrote `transition_in`. On screen,
> unreached is the same as absent. `6976ab5` put the planner on the workflow path.

**W3 · WARNINGS ARE TRIAGED OUT LOUD** (SKILL.md step 9a).
> **Precedent — `28db3e1`:** a deck was delivered "all green" carrying **94** warnings, including 28 pages
> flagged FLAT on a PAID image tier and every reveal-choreography defect on the deck. Grouped by kind the 94
> collapsed to ~10. Warnings do not block, which is exactly why they ship.

**W4 · A BOTH-TIERS GATE IS NEVER INTRODUCED BY A ONE-TIER SENTENCE** (SKILL.md step 9a, the `BOTH TIERS`
lead-ins; `tests/test_shared_gates_are_on_both_paths.py` holds it).
> **Precedent — `c898edb`:** the `voice_qa` instruction sat between "On a remotion deck…" and "For an
> HTML-tier deck…", so an html author reading down the page hit the remotion sentence, saw it was not their
> tier, and skipped the voice gate with it. A rule that exists and is not on its reader's path is not a rule.

**W5 · THE DELIVERY CRITERION NAMES EVERY GATE** (SKILL.md step 9f).
> **Precedent — `c819c84`:** the criterion named only `validate.py` and `check_av.py`, and a deck shipped
> "all green" while the gates that actually look at the pages were never consulted.

**W6 · THE DIRECTION ROUTER NEVER PADS THE BALLOT** (SKILL.md step 3.6 ①).
> **Precedent — `0252348`:** `shot_templates.py --route` padded a short match list from a fixed fallback
> order and put an unrelated direction on the ballot (a 3D craft look for an AI-office-agent film); its
> scoring was ASCII-only, so a CJK topic matched nothing and got the padding every time. It now returns only
> genuine keyword matches and prints the shortfall, which the shot-director fills by conceiving directions.

**W7 · THE REVIEW LEDGER HAS EVERY ROW, AND THE DELIVERY REVIEWER IS NOT THE MAKER** (SKILL.md step 9e).
> **Precedent — `c38f365`:** reporting only the FLAGGED beats made a dimension nobody looked at
> indistinguishable from one checked and found clean. And the maker holds the intent — the intent is what
> makes a wrong frame look right — so the delivery pass is a fresh subagent given only the out_dir path.

**W8 · A FILM IS SHOWN ONLY AFTER ITS DELIVERY GATES, AND A PICTURE MUST NOT DEPEND ON WHICH TAB OR BEAT DREW IT**
(SKILL.md 9d; `critic_brief.py --gates`, `motion_events_qa.py`).
> **Precedent — WorkBuddy re-light, 2026-11-11/12:** the film was handed over on a contact sheet with the delivery
> gates skipped, and the user found, by watching, a jitter at the end of beat 11. Four root causes, none of them
> visible on a still, three of them in the runtime every film shares:
> 1. **Coverage measured per render tab, before layout.** A framing is cached per tab; a tab whose FIRST frame was
>    beat 11's tail (under the seam into beat 12) measured the punch-in before its container had a size, and five
>    tabs cut to five framings, alternating frame by frame. Fix: `runtime/coverage.tsx` measures only laid-out
>    probes with fonts loaded (delayRender until then). Proof: every (beat, step) now logs ONE framing across all
>    ten tab×segment measurements.
> 2. **SVG ids are global.** Beats 9 and 10 both drew `url(#ws-pool)`; through the seam beat 10 resolved to beat 9's
>    lit gradient, and the light switched off in one frame when beat 9 unmounted. Fix: `runtime/idScope.tsx` scopes
>    every beat's ids (48 library files use literal ids; film shots will too).
> 3. **A carried cut runs the picture's clock ahead; voice-timed layers inherited it.** Coverage and the focus lead
>    stepped `cutFrame(TR) + CARRY_F` frames early — beat 17's close-up landed 0.3 s in, mid-entrance, against a
>    plan of 0.8 s. Fix: `PictureLeadContext`; both subtract it.
> 4. **A tilted clip's client rect is its axis-aligned box.** The type census judged lines sliding out under a tilted
>    window's edge as fully visible, and jitter_qa read their shrinking glyphs as a 4-6 px tremble. Fix: the glide
>    census measures visibility against the clip's projected quad (corner markers).
> Rule: run the tier's delivery gates (`critic_brief.py <out_dir> --gates`) and look at `_motion_events.jpg` BEFORE a
> film or a contact sheet goes to the user; a sheet of settled frames cannot show a single one of the four.
> 5. **…and so did everything timed to the beat's END.** A Sequence sized from `dur` unmounts `lead` frames before the
>    beat does: in the published topic-to-video promo six screens (beats 9, 12, 13, 15, 16, 23) went black for 8-10
>    frames before their cut, found while re-checking a frame the motion scan flagged. Every gate was green, and
>    the JUMP rule saw only one of the six (the rest switched inside the seam's pad). Fix: `usePictureEnd(dur)`
>    (runtime/motion) is the clock frame the beat really leaves at; ScreenVideo's last span and FilmScreen use it;
>    validate refuses a workshop Sequence sized from `dur` without it; motion_events_qa's BLANK lists a region that
>    switches to flat dark before a seam and holds to the cut (6/6 on the promo, 0 on eight other films).
> Rule for the next clock change: grep every consumer of the clock it shifts — the voice-timed ones (3) AND the
>    end-timed ones (5) — before shipping it.
> 6. **The suite mutated the installed skill while a plate was keyed.** `test_energy_staleness` rewrote
>    `runtime/dna.tsx` and dropped a `.bak` into `runtime/`, and `test_cjk_type_qa` rendered a broken `textSafe.tsx`,
>    all in the live tree, while an 83-minute plate took its key. That key matches no tree that ever existed. Fix:
>    those tests now mutate a copy, and `remotion_segments.code_hash` (every segment, plate and screen key) refuses
>    while another process holds the mutation sentinel. And a plate's screen code is the whole library, so any
>    runtime edit staled it: `blender_plate` now re-renders just the screen and re-keys the plate when the pictures
>    match within the render's measured noise (`SCREEN_NOISE_PX`; the screen render is not bit-deterministic).
> 7. **A full look at the film found what no gate measured.** A contact sheet (each beat at 30/60/90%) plus
>    the first and last second, both read by eye, turned up:
>    - **Both ends flashed.** A light DNA's veil was faded over a dark first and last beat: in from white, out to
>      white. The cause was Film's edge ground, blind to a register that paints its own ground. Fix: the veil takes
>      the beat's luminance (`veilFor`), and `flash_qa.edge_washes` measures it. The published ANC film has it too.
>    - **A caption letter sat on a dark bezel.** The Remotion tier had no caption-contrast gate at all.
>      `caption_contrast_qa` now reads it from the census lines (`check_remotion`): 6 of 6 films measured, one hit,
>      the real one.
>    - **A numbered set was cropped.** A punch-in dropped files 01 and 05 from an 01–08 grid. Answer: `coverage: false`
>      on the beat, with its reason.
>    - **A blank pill flew over a title.** The message's words had faded out before it flew, and its arc crossed the list
>      title. The jitter tracker read the occlusion as a tremble. The defect was the design, not the type.
>    - **Words sliced by the window edge in a glide.** Sidebar and request bubble. Fix: an element the closing view
>      crops fades before the edge reaches it.
>    Also from this round:
>    - **`jitter_qa`'s seams now own the carry's reach,** two frames past the seam on each side; the trembles there were
>      motion blur shifting a glyph's centroid.
>    - **`shot_proof` reads a wrapper shot's props** (`ComponentProps<typeof X>`).
>    - **`blender_plate --still 0` is refused.** It used to build the whole plate (41 min).
>    Rule: gates are a floor. Before a film goes out, LOOK at every beat at three points and at both ends.
> 8. **Gates that judged the board, not the film.** On the promo, four blocking errors were the gates' own:
>    - `shot_proof` checked a LivingMap beat's raw `{map, add}`. The register only ever sees the expanded
>      `nodes`/`before`/`after`.
>    - `shot_proof` read a developer's `requireEvidence(…, 'the real photograph …')` as copy welded into the register.
>    - `cjk_type` failed an English film's registers as "unfed" Chinese while listing them as setting no Chinese.
>    - `shot_still_qa` read a spotlit ground as 41.8% "ink" in an empty caption band. The band's ground is now a fitted
>      smooth surface; across 211 delivered stills one verdict moved, and it was that one.
>    Each was fixed where it measured. A gate that refuses correct films gets waived, and a waived gate stops
>    looking.
>    And a plate's key over-covers too: three ANC plates were staled by MacBook kit code their scenes never import.
>    `blender_plate --verify` asks the pictures (three stills against the delivered frames, within encode noise)
>    before an hour of Cycles.
>    A STALE FACT is a defect like any other: the promo said "224 shot designs" of a library of 225.
> 9. **A layer that measures the DOM per frame follows whatever is moving.** The promo's closing title popped 7% smaller
>    on isolated frames under its camera pull. The pops fell on the same frames in every render, so it was not a tab
>    race. A fonts wait was added first, on the coverage precedent, and the pops did not move: that hypothesis was
>    wrong (the wait stays, as a separate guard). The cause was SceneCamera's edge budget, re-measured on every
>    frame's own layout. Callback's cards fly in from beyond the frame, carrying live teasers of earlier beats, and
>    each time one's type came wholly inside near an edge, the cap clamped, then relaxed a frame later. A single-scene
>    render has no teasers (plain cards), so no proof sheet could show it. The jitter gate found it only once a cue
>    made the title visible during those frames. Fix: the budget is measured once, on a transparent copy frozen at
>    SETTLED_T. Rule: a camera, a framing, or anything else that moves the whole picture must be a smooth function of
>    time; derive it from the settled layout, never from the frame in flight.
>    (A "still layer" is not always the cure: carrying Callback's teaser cards as composited bitmaps through their landing
>    tilt raised their tiny type's tremble from 0.29 px to 0.35-0.71 px — a rotated, scaled bitmap samples worse than
>    re-set type. Measured and reverted, 2026-11-12.)
> 10. **Staging a film's interface as a lit object (Grok, 2026-11-12).**
>    - **A generic film-level stage was worse.** It tilted the whole frame, ground and all, like a screenshot, and
>      cut type to ~60%. Reverted.
>    - **What worked was film-local** (Grok's `kit/LitCanvas`). It shows the shot's CONTENT AREA at 90% as a lit window
>      standing on the film's own dark plate, with a held tilt, a light pool and a contact shadow. Each wrapped shot
>      declares `GROUND` = the plate, and its staged beats set `coverage: false`.
>    Four things the rollout surfaced:
>    - **Every render branch must be wrapped.** Three shots had an early-return state left on white, under a white
>      caption.
>    - **A CSS `filter` on an overflow-visible SVG inside the perspective parent rasterised as a black box** on some
>      frames (two flashes). The shadow belongs inside the SVG as a bounded SVG filter.
>    - **An eased tilt re-set all type every frame** (a shimmer). The window stands still.
>    - **Coverage read only library shots**, so it punched into a film's three.js Bots 1.3-1.7x past their pixels and
>      its probes ran the tab out of WebGL contexts. `coverage_plan._is_plate` now reads the workshop and follows
>      relative imports.
>    **And the user's verdict on it: too deliberate.** "感觉都是黑色背景用一个斜的页面展示内容，是不是有点过于特意和重复，原有的那种也不差". Sixteen beats in one staging read as a device, not a
>    film. Grok was reverted to its published cut: its light interface beats alternating with dark 3D beats were
>    already the rhythm. The lit window is an ACCENT, for a few beats where the interface itself is the subject.
>    It is never a pass over every interface beat, and it is never applied to a film that already has a working
>    contrast of its own. (WorkBuddy keeps its eight: the user chose that re-light and it is that film's night-desk
>    world.)
> 11. **A hypothesis about a gate must be measured before the gate is changed.** The waived jitter lines (the promo's
>    '>' at 0.18 px, its teaser label at 0.29, the 0.11-0.15 trembles on ANC's labels) were blamed on what moved
>    BEHIND them. A glyph-only re-read of the shift (everything beyond 6 px of the census box replaced) gave the SAME
>    numbers, to 1e-4 px: the tremble is on the glyph's own pixels. The change was reverted: no verdict moved on
>    three films, and it doubled the estimator's cost. These lines are real, sub-pixel, and below what the eye
>    sees. The lever is a VISIBILITY threshold the user's eye calibrates, not a better estimator.
> 12. **A cache key is as wide as what can actually reach the picture, measured, not as wide as the folder.** The segment
>    key hashed all of remotion/src, so a one-line edit to a module two registers import re-rendered every beat of
>    every film. Film reaches 132 of the library's 385 files without going through a register; the other 253
>    (225 registers, 25 runtime modules, 3 kits) can only change the beats whose registers reach them, because no
>    register-only module does anything on load (pinned). Proof was a render, not a test: on ANC an edit to
>    kineticWord re-rendered 3 beats (2:19 vs 6:56) and the joined film matched a cache-less render of the same code
>    to the run-to-run noise on every beat, while the edited beat moved 4.9, so a stale reuse would have shown.
