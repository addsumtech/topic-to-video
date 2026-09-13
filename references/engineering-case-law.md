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
