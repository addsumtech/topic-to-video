# Open work — the goal, and how it is known to be finished

**THE GOAL.** Make "the library is green" a statement that means something, and clear every defect that
establishing it uncovers.

Today "green" mostly means *green under one aspect, one Design DNA, and a fixture that handed every prop the
same sentence*. That is not a small caveat. `TermThink` was repaired and verified on the morning of
2026-09-13 and found broken again the same afternoon the moment the fixture stopped feeding it one input;
`VariableTypeMorph` was clean at all five aspects under `product` while `editorial` sliced its word at both
edges. Until the axes below have actually been swept, nobody — me included — knows how much of the green is
real.

This file is the ledger. Each item carries the EVIDENCE that it is real, and an ACCEPTANCE line that can be
checked by running something rather than by asking someone. An item is struck through when its acceptance
command has been run and reported, never when it merely feels done.

---

## What a full sweep actually costs, and why the plan is not "run everything"

Measured: one library sweep is 163 registers at roughly 11s each when the machine is otherwise idle (~35
min), and closer to 30s each under load (~80 min). Sweeping every aspect against every DNA is 5 x 9 = 45
runs — upwards of 30 hours — and most of it would measure nothing new. The axes are not equally
informative, and the reason is in the fonts:

    DNA          Latin display face     CJK fallback
    terminal     JetBrains Mono         Noto Sans SC
    neutral      Inter                  Noto Sans SC
    editorial    Playfair Display       Noto Serif SC
    product      Space Grotesk          Noto Sans SC
    blueprint    JetBrains Mono         Noto Sans SC
    cinematic    Bodoni Moda            Noto Serif SC
    data         IBM Plex Sans          Noto Sans SC
    retro        Baloo 2                Noto Sans SC

Eight DNAs, **seven distinct Latin faces — and only two distinct CJK faces.** A Han glyph is one em in both
Noto cuts, so sweeping Chinese copy under nine DNAs re-measures the same widths eight times. The DNA axis
earns its cost on the LATIN sweep, which is exactly where `VariableTypeMorph` failed. So:

* **Chinese** varies over ASPECT (5), and over the two CJK faces — 10 runs, of which 1 is done.
* **Latin** varies over FACE (7), at the tightest frame — 7 runs.

That is 17 runs, not 45, and every one of them measures something the others cannot.

---

## A · Baselines never established

> **THE BASELINES BELOW WERE ESTABLISHED OVER 163 REGISTERS. THE LIBRARY HOLDS 178.**
> Every A item records its coverage as a number, and that number went stale silently as the library grew —
> the same shape `7a0183c` fixed for `LIBRARY.md`'s headline, one file over. Fifteen registers were added
> after the sweeps ran (`DollyZoom` the same day at 20:02, after A3 finished at 07:36; then `CompanionCard`,
> `FallbackPath`, `StateSheet`, `TermSpace`, `PlaneStack`, `TaskFold`, `CarryOver`, `SeamBetween`,
> `StatedBy`, `ViewSwitch`, `CraneUp`, `Escalation`, `HeldInstant`, `ShorteningHold` — list derived from
> `git log --diff-filter=A` per file, not from memory).
>
> **Covered 2026-09-23, 315 renders, ZERO findings and zero render failures at every step:**
>
>   * **A3** (Latin, nine presets at 1:1): 15 of 15 registers under terminal, neutral, editorial, product,
>     blueprint, cinematic, data, retro and un-themed — 135 renders.
>   * **A4** (`cjk_type_qa --all-aspects`): 16:9 / 9:16 / 1:1 / 4:5 / 4:3 all clean, nothing dropped.
>   * **A1** (`text_safe_qa --cjk`, sans face): 0 findings at each of the five aspects — 75 renders.
>   * **A2** (serif CJK, `--dna=editorial`): 0 findings at 1:1 and 9:16 — 30 renders.
>
> So the baselines now cover 178 of 178. What this does NOT re-establish is the 163 themselves: they passed
> on 2026-09-14 and the library has been edited heavily since, so a true re-baseline is a separate,
> ~1600-render job. The honest state is "the gap that opened since the baselines is closed", not "the
> baselines are fresh".

**~~A1 · Chinese x all five aspects, sans face.~~ DONE 2026-09-14 03:41.** `text_safe_qa --library --cjk
--all-aspects` on the frozen fixture: 16:9, 9:16, 1:1, 4:5 and 4:3, **163 registers, 0 findings each, and
zero render-failure lines** across 815 renders.
> **What establishing it cost, which is the point of having done it.** Three real defects and three
> instrument defects, none of which existed in a world swept only at 16:9 under `product`:
> `RealVersus` (line count by ratio, capped at 3, settled in two passes that do not converge);
> `wrapLines` missing kinsoku — a line may not OPEN with a closing mark, so every Chinese reserve in the
> library divided by a number one line short; `PlanPalimpsest`'s legend clamp with an upper bound and no
> lower one, feeding back into its own column width and lifting the block off the top of the frame.
> Instrument side: pools whose shortest member was soft (`_LABEL_V` at 4 glyphs, `_MED_V` at 8), roles
> matched on the whole name so 27 props were handed body copy where a label belongs, and a fixed scratch
> path that made two concurrent sweeps invent findings at about one register in twenty.
> **The zero render-failure count is itself evidence:** 815 renders, none flaky, against roughly one in
> twenty before the props-file race was fixed.

**~~A2 · Chinese under the SERIF CJK face.~~ DONE 2026-09-14 04:08.** `--dna=editorial` (Noto Serif SC) at
1:1 and 9:16: 163 registers, 0 findings each, 0 render failures. Both CJK faces the eight DNAs ship are now
swept — which is the whole DNA axis for Chinese, since the other six presets fall back to the same two cuts
and a Han glyph is one em in either.

**~~A3 · Latin across the display faces.~~ DONE 2026-09-14 07:36.** All NINE presets at 1:1, 1467 renders.
Two registers, six findings, both the same shape and both fixed: a size chosen for the FALLBACK named in a
font shorthand, while the face that renders is the DNA's. `SpeedLimit` reserved its labels' width as the
literal `W - 344` — how wide those words are in Inter — and ran off the frame under JetBrains Mono;
`AnalogTape` set its wordmark at a flat 168px, the size for the condensed Antonio in its own fallback list,
and Bodoni Moda cut it off 85px on BOTH sides of all three RGB-split copies.
> **The campaign verified its own fix:** `blueprint` shares JetBrains Mono with `terminal` and ran AFTER the
> `SpeedLimit` repair — 0 findings.

**~~A4 · `cjk_type_qa --all-aspects`, library-wide.~~ DONE 2026-09-14 09:17.** Five aspects, 163 registers.
Zero DREW ALMOST NOTHING. Five registers reported dropped strings; THREE were the instrument asking the
wrong question and are fixed, and the two that remain are the case the gate's own header calls "a report,
not a failure — a capped list, or a panel conditional on a prop":
> * `IsometricAssembly` — `items?: [string, string, string]` declares three slots and the fixture fed four.
> * `EdCompare` — `_ARRAY_SHAPES` is keyed by PROP NAME and one name serves registers with different
>   shapes, so `left` carried the union of EdCompare's `Col` and VersusSplit's. Each register is handed
>   only the keys its own type declares now, and the shared table is untouched.
> * `TermTree` — TRUNCATION IS NOT OMISSION. A terminal cuts a line and marks it; twelve glyphs of a
>   twenty-seven glyph note score 0.44 on a character-coverage test and read as missing. A prefix followed
>   by an ellipsis is the string, shown the way the medium shows it.
> **Explained and accepted:** `BlueprintGrid`'s `metricLabel` is gated on `specN` and `TermTable`'s
> `heroNote` on `hero` — both NUMBER props, which `cjk_props` skips by design because a number is not copy.
> The fixture therefore feeds copy into a panel it does not enable. Supplying numbers would need the
> name-based range heuristics to be right about an index versus a percentage, and a wrong one renders a
> different frame than the film would — a worse trade than two explained reports.

**~~A5 · `film_energy_qa` has never been run against a real film.~~ DONE 2026-09-14 18:02.** A five-beat
film was written with TRUE copy (the counts this campaign measured), narrated with edge-tts, rendered to
`out.mp4`, and put through the gate — which had, until today, only ever seen synthetic mp4s built by its own
tests. It deliberately cast `WordTunnel` and `RackFocus` so the two registers added this week got their first
end-to-end run. Measured: **41s · motion p75 0.0038 · ink 4.0% · light 0.540 · arc 5.1%** → one ERROR,
DENSITY, against floors of 0.0037 / 12% / 0.135 / 1.9%.
> **What running it once cost, which is again the point.** Two defects, one in the pipeline and one in the
> gate's own manners:
> * **`AcceptanceStamp` threw MID-RENDER** on a board `validate.py` had just called clean. Its type declares
>   `conditions?: [string, string]` and the beat supplied three — a full bundle, a failed render and an
>   automatic retry without `--gl` to learn something the DECLARATION already knew. The other half of this
>   defect is silent: `IsometricAssembly` declares three slots and A4 found a fixture feeding it four, which
>   it dropped without a word. So the board now reads the slot count (`demo_copy_qa.tuple_arity`, parsed
>   from the registers, three of them fixing four props today) and refuses a beat that does not match.
>   A claim is made only where every member of the type fixes the SAME length — `[string, string] | string[]`
>   fixes nothing, and AcceptanceStamp's own type said exactly that, so it was narrowed to what its runtime
>   has always enforced, and a test pins the type to the `throw` so the two cannot drift.
> * **The DENSITY error stopped at a number.** `density_advice.py` exists precisely to answer it — which
>   beats are starved, and what the same design family offers instead — and the gate never said so. It does
>   now. Run on this film it named all five beats and their denser neighbours in seconds.
> **And one thing found while reading the parser:** `_declared_types` required a `;` after every prop, so the
> LAST prop of every inline register (`framed?: boolean`) was dropped and fell back to the "string"
> assumption — the loosest reading of the one thing that function is strict about. It also could not read a
> NAMED props type, which is why AcceptanceStamp declared nothing at all to it. Both fixed; the demo-copy
> library it feeds is byte-identical across all 146 registers afterwards, which is how the fix was checked.

## B · Instrument work the baselines depend on

**~~B1 · `_MED_V` and `_LONG_V` are not hardened the way `_LABEL_V` was.~~ DONE.** Every pool's shortest
member is now a hard case — `_LABEL_V` 6/6/7/8 glyphs, `_MED_V` 26/28/27/26/27, `_TITLE_V` 7-8, `_LONG_V`
28/31/37 — and A3's 1467-render sweep at 1:1 across all nine presets ran against these pools. Original
text: `_MED_V` and `_LONG_V` were not hardened the way `_LABEL_V` was. `_LABEL_V` was rewritten so its
SHORTEST member is a hard case, because a pool with a soft member tests some registers softly at random,
depending on which ordinal their prop lands on. The other two pools still contain short members.
> **Acceptance:** every entry of each pool is at least as demanding as the one that exposed a real defect,
> and a re-sweep at 1:1 still reports 0 (or the defects it finds are fixed).

**~~B2 · `focusZ` is dead.~~ DONE (`8e3837c`).** `grep -r focusZ` now finds only the comment in
`validate.py` that records why the field was removed. Original text: `focusZ` is dead. It occurs exactly once in the repository, in `validate.py`'s NaN-guard list: a
check on a field no renderer has ever read. The branch it sits in is now refused outright (`8e3837c`).
> **Acceptance:** removed, and `grep -r focusZ` returns nothing.

**~~B3 · A transient render failure is reported as a FINDING.~~ DONE.** `text_safe_qa` retries a failed
render once and reports a still-failing one as `(render FAILED twice — nothing was measured on this frame:
…)`, which is a different sentence from a type finding. Original text: a transient render failure is
reported as a FINDING. The props-file race is fixed (`8e3837c`), but
a genuinely flaky render (a TCP reset) still lands in the report as though it were a type defect, and the
reader cannot tell without re-running it.
> **Acceptance:** a failed render is retried once before it is reported, and a still-failing one is reported
> as a FAILURE distinct from a finding.

**~~B4 · Kinsoku is implemented in half.~~ DONE 2026-09-15.** Both halves now: a closing mark is glued to
the glyph BEFORE it and an opening mark to the glyph AFTER it. Done in the order the acceptance demanded,
because the reason it was deferred was that it could not be verified — and now it can be.
> **The browser's own break, measured.** Chrome, the real bundled face (Noto Sans SC), 30px, a box exactly
> five glyphs wide, each glyph's line found by asking for its client rect:
> ```
> 一二三四五六七八九       -> 2 lines:  一二三四五 / 六七八九
> 一二三四「五六七八九      -> 3 lines:  一二三四 / 「五六七八 / 九
> 他说「先把这件事测一遍」再谈 -> 3 lines:  他说「先把 / 这件事测一 / 遍」再谈
> 一二三四五「            -> 2 lines:  一二三四五 / 「
> ```
> The same nine glyphs take one line MORE when an opening bracket falls where a line would have ended. The
> third case is the control — its bracket sits mid-line and costs nothing. `wrapLines` now reproduces the
> browser's line CONTENTS on all four, not merely its counts.
> **Straight ASCII quotes are deliberately excluded**, measured on the same page: `一二三四"五六七"八九`
> breaks mid-run, because a straight quote can open or close and the rule does not apply to it.
> **And the fixture now carries one** (`_MED_V`, `把「重复三次以上」的动作记下来…`): a rule no fixture
> exercises is a rule the library sweep cannot catch being wrong, which is exactly why this half waited.
> Five mutants — the rule disabled, the opening set emptied, a trailing mark dropped, the overflow yield
> removed, the closing glue disabled — are all caught.
> **AND THE SAFETY ARGUMENT FOR THE HALF THAT WAS ALREADY SHIPPING WAS FALSE.** "Gluing can only ever
> predict the same number of lines or more, never fewer" was written in the source as the whole reason this
> rule is safe in a reserve. A glued pair is unbreakable only while the column can HOLD it: in a narrower
> one the browser has no legal break left and breaks inside the pair anyway, and `wrapLines` did not —
> measured on the fixture strings at px=18 in a 36px column, gluing turned 25 predicted lines into 24.
> Predicting FEWER is the one direction a reserve must never be wrong in. Kinsoku yields to overflow now,
> and across 24,606 string x size combinations it never under-counts and adds a line in 1,034.
> **The first fixture written for this exercised nothing**, and the first test written for it passed anyway.
> The string opened `把「重复…`, two glyphs in — a line can only END there in a column narrower than two
> glyphs, which no register has; across every realistic size it changed the count in ZERO of them. And
> comparing against a naive per-glyph fill PASSED on that useless fixture, because its closing `」` was
> moving the count by itself. The control is now the same string with the opening mark swapped for an
> ordinary Han glyph — same length, same closing marks — so the only thing left is the opening rule.

**~~B5 · Six hashes updated without a measurement beside them.~~ NOT WHAT HAPPENED — and the real cause is
worse. DONE 2026-09-14.** The manifest was honest: every row had been freshly measured. The reason is that
`register_energy.py --only DollyZoom` was not a targeted run at all. Its parser reads
`a.startswith("--only=")`, so the SPACE spelling matched nothing, `only` fell through to `None`, and the
command ran a FULL 164-register sweep — about forty-five minutes of renders instead of one, twice in one
session, with no message. The only clue was a progress counter reading "measured 10/164" where a targeted
run prints 1/1. `measure_ground_luma` had it worse: it matched `--only` with `startswith` and then SET THE
FILTER TO NONE when the arg carried no `=`, so the flag did not narrow the sweep, it threw it away — that is
the other half-hour I spent today.
> **Reproduced and refuted in the right order.** The reading that produced the B5 entry — that the merge path
> writes hashes it did not measure — was tested by changing a module `RackFocus` depends on and running
> `--only=TermLog`: `RackFocus`'s hash was PRESERVED. The merge was innocent; my invocation was the bug.
> **Nine scripts parsed flags by hand and not one refused an argument it did not understand.** Three
> behaviours for the same typed flag: `register_energy` swept everything in silence, `cjk_type_qa`
> (argparse) accepted it, `text_safe_qa` crashed on `--only/storyboard.json` — only the crash was honest,
> and only by accident. `scripts/_common.argflag` / `argflag_list` / `refuse_unknown` are now the one reader
> and the one guard; `register_energy`, `measure_ground_luma`, `text_safe_qa`, `measure_ground_reach`,
> `band_debt`, `sfx` and `rhythm_qa` all take both spellings, refuse what they do not know (exit 2, naming
> the argument), and stop on a `--only` naming a register that does not exist. `tests/test_arg_flags.py`
> pins the FAMILY, including a check that no tenth script grows a private copy of the parser.

**~~B6 · A string `meta.design_dna` is invisible to `validate.py` — twice.~~ DONE 2026-09-14.** Fixed:
`_dna_named()` treats a string naming a known preset as themed, in both the warning branch and `_themed`.
The test is PARITY — the two writings of the same film must produce the same findings, which cannot be
satisfied by deleting the warning — and all three mutants (either branch reverted, or `_dna_named` saying
yes to any string) are caught. Original text: `coerceDna` resolves a preset
NAME at runtime, so `meta.design_dna: "product"` is a fully themed film. `validate.py` tests
`isinstance(design_dna, dict)`, so that film is judged un-themed. Isolated on two boards identical but for
that key:
> * it WARNS "remotion: NO Design DNA … every shot renders its ORIGINAL hardcoded identity" about a film
>   whose every shot does inherit the DNA — a gate crying wolf at a correct board;
> * and the worse half, because it is silent: `_themed` gates the DNA-coverage lints, so the same film skips
>   the `theme_cues` check (measured 0 findings against 1 for the identical board written with
>   `shot_template`) and the un-migrated-register lint. A themed film opts out of every themed-only check by
>   writing its DNA the shorter way.
>
> This is the shape `slide-maker`'s "opt-in gate is not a detector" already recorded: the check exists, and
> the deck that most needs it is the one it cannot see.
> **Acceptance:** `_themed` and the NO-Design-DNA branch both treat a STRING that names a known preset as
> themed; a board written each way produces the same findings; a test that goes red if either branch
> reverts.

**~~B9 · A PARSER THAT CANNOT READ A DECLARATION REPORTS NOTHING.~~ DONE
2026-09-15 for `cjk_type_qa`; the FAMILY is what is still open. The shape: every static reader in `scripts/`
answers "what does this register declare" with a regex, and each regex has a spelling it refuses. A refused
spelling is not an error — it is an empty result, which flows downstream as *this register declares nothing*
and then as *this register is fine*.

Four instances, all found within one day of each other, three by a NEW register happening to use a spelling
nobody had used before:

| reader | the spelling it refused | what the silence produced |
|---|---|---|
| `cjk_type_qa._one_prop` | a prop preceded by a JSDoc comment | 2 registers invisible, 25 read in part |
| `cjk_type_qa.prop_signature` | `React.FC<Props>` (a named alias) | `AcceptanceStamp` swept in English |
| `cjk_type_qa.prop_signature` | `React.FC<{...} >` (one space) | `MRIPipeline` swept in English |
| `cjk_type_qa._alias_fields` | `type X = A \| B` (a union) | `SplitFlap` swept on a BLANK board |
| `cjk_type_qa.prop_signature` | a `;` inside a comment (split ran first) | 9 more registers, 1 prop each |
| `shot_proof` / `demo_copy_qa` | comments inside the props block | (fixed earlier, same week) |

The fifth was found by the acceptance test itself, minutes after it was written, and it is the most
instructive of the five: the JSDoc fix stripped comments inside `_one_prop`, which is downstream of the
`;`-split that had already cut the chunk in the wrong place. **A fix applied one layer below the defect looks
identical to a fix.** Nothing said otherwise until a test compared this reader against the other three.

**The measurement it corrupted.** `prop_reach` feeds through this reader, so 24 of 166 registers were scored
on prop sets smaller than they declare — 79 props missing in all. The bias is one-directional — fewer words to change can only look
like less change — so it lands entirely on the FLOOR, which is the half of the table anyone actually reads.
Worse, a SENTENCE derived from the broken numbers was published in `LIBRARY.md` as a fact about the library
("a register whose only authorable prop is a `kicker` — MadeOf, InOrder, LastLeg, RestsOn"); those four
declare five, four, five and five. The table now carries a warning and `prop_reach` must be re-run.

**Two register defects the silence was hiding**, both fixed the moment the registers could be fed:
`SplitFlap`'s flip cascade was an unbounded sum that never completes past ~17 columns (more than half the
board still flickering random glyphs on the LAST frame), and `MapPlate` avoided its own centre mark with a
fixed 0.26 along the channel, which only clears a channel crossing the whole plate. Both are constants tuned
on the English demo input — the exact failure mode the working rules name.

> **Acceptance for the family, not the four instances:** one test that asks, of every `.tsx` in the shots
> folder, whether the reader sees at least what the file declares — so a NEW spelling fails on the day it
> lands instead of the day someone notices a register has been green about nothing.
> `tests/test_declaration_readers.py`
> then does it for ALL FOUR readers at once and adds the check that actually found the fifth blindness:
> the readers are compared AGAINST EACH OTHER, so one going blind to a spelling the others handle fails
> even when no register is reduced to zero. Measured after that test went green: all four readers see every
> register, and the only propless one is `LiquidMorph` — which that file names outright rather than allowing
> a pattern (`test_a_register_that_declares_nothing_is_NAMED_not_allowed_by_pattern`). **Closed.**
>
> *(Citation corrected 2026-09-23: this acceptance used to point at
> `tests/test_cjk_type_qa.py::test_every_register_the_library_ships_is_fed_its_own_props`, a test name that
> no longer exists anywhere under `tests/` — grep, zero hits. The guarantee moved into
> `test_declaration_readers.py`; the pointer did not follow it. An acceptance that names a test nobody can
> run is the same failure as a manifest nobody can tell is stale.)*


**B10 · A MEASUREMENT IS STALE WHEN ANY OF ITS INPUTS MOVED, and three instruments were watching one.**
Partly DONE 2026-09-15. The shape: every manifest in `remotion/` records a reading plus a hash of what it
read, and in each case the hash covered less than the reading depended on.

  * `prop_reach.json` hashed the register's SOURCE and not the PROPS it was fed — and the props come from
    `cjk_type_qa.cjk_props`, a generator, not a constant. When its reader stopped being blind, 24 of 166
    registers began receiving props they had never been given and every one of those numbers became
    meaningless while `--check` reported the manifest clean, because not one `.tsx` had changed. It hashes
    the fed props now (exact, and free — computing them needs no render). **DONE**, pinned by
    `tests/test_prop_reach_staleness.py`.
  * `GROUND_FOLLOWS_MEASURED` held an entry measured on an EMPTY PLATE. Six registers refuse to draw
    without a real artefact; `measure_ground_reach.py` never fed them one, so all six reported RENDER
    FAILED and none could ever be listed — while `validate.py` rejects any beat declaring a `ground` on a
    register that is not listed. An error with no fix, which is the catch-22 `test_provenance.py` records
    for provenance, sitting inside the luminance guard. With the fixture wired in, **PhotoPlate measures 51%
    of the frame moving** — the photograph holds the middle and does not change with the ground — and it had
    been LISTED as following since the original sweep, which ran before the evidence guard existed and
    therefore measured a frame with no photograph in it. **DONE**; PhotoPlate removed, StateSheet and
    FallbackPath added, pinned in `tests/test_register_schedules.py`.

> **`register_energy.json` — DONE 2026-09-22/23 (`eb67b85`, and the merge fix in `8c4df82`).** It now
> records a SECOND hash dimension, `_fed`, beside `_source`: `fed_hash(name)` over the evidence props and
> the BYTES of any file they name, so the day the fixture changes those rows report
> `"the artefact it was fed changed since it was measured (evidence fixture)"`. Two defects were found
> closing it, both by running the thing rather than reading it: a targeted `--only` re-measure REPLACED the
> whole `_fed` map instead of merging it, so re-measuring one evidence register evicted the other five and
> no sequence of targeted sweeps could reach zero stale rows; and containment was tested by banning the
> path separator, so `PageWrite` — whose entire evidence is `textures/demo-report.png` — had none of its
> picture's bytes in its hash. Pinned by `tests/test_energy_staleness.py`, including the change-an-input
> demonstration the acceptance asks for. `prop_reach` carries the same artefact dimension now, for the
> same reason: it overlays the fixture at render time and hashed only `cjk_props`.
>
> **What is still open is `_ground_reach.json`.** It carries NO input hash of any kind — its top-level keys
> are `rows`, `failed`, `universe`, `inkRefused`, `thresholds` (checked 2026-09-23) — and its `--check` is a
> DRIFT check that re-renders the library to compare the measured follow-set against
> `GROUND_FOLLOWS_MEASURED`. That answers "is the committed set still right" at the cost of a full sweep;
> it cannot answer "did an input move" at all, which is the cheap question the other two manifests can now
> be asked. **Acceptance:** it names every input its numbers depend on and `--check` fails when one moves —
> demonstrated by changing one input and watching the check go red, not by reading the code.


**~~B12 · A REVEAL THE SETTLED FRAME CANNOT SEE.~~ DONE (gated).** `useT()` returns exactly
`REDUCED_MOTION_T` (0.86) under reduced motion, and motion.ts says why that value was picked: it "lands in
the 'reveal complete, exit not begun' zone". A window that only OPENS at 0.86 is therefore at opacity
**exactly 0** in the frame `--reduced-motion` freezes on — and in every still the gates inspect, since
`shot_still_qa`, `ink_contrast_qa` and `cjk_type_qa` all capture the settled frame. The element is not dim
there; it does not exist. Its contrast is never measured, its type is never checked for overflow, and the
accessibility render ships the beat without it.

Found by rendering seven registers and LOOKING at them, not by any gate. Three (`AverageHides`, `CraneUp`,
`HeldInstant`) opened their closing line at `seg(t, 0.86, 0.96)` — the only 3 of 158 in the library, all
added this session. On `CraneUp` the kicker's fade-out also completed at 0.86, so the settled frame carried
**no words at all**. The other four opened at 0.82-0.84 = 20-40% opacity at that frame: a sentence the
viewer gets ~0.24s of at full strength before the outgoing dissolve starts. `AverageHides` was worse than a
faint note — its `gapIn` ran to 0.9, so the band that IS the register's argument stopped short of the tail
mark it measures to, in every frame any instrument ever saw.

All seven now complete by 0.84. The gate
(`tests/test_motion_timing.py::test_no_register_reveals_something_the_settled_frame_cannot_see`) asserts the
BINARY rule — no window may OPEN at or after the settled frame — and proves its own detector on a synthetic
violation first. Verified to go RED on the pre-fix source. The stronger "complete by 0.86" rule was
considered and rejected: it names **69 registers**, most of them slow settles that are 70%+ in and perfectly
visible. That is a redesign, not a gate.

**B11 · THE TYPE-OVERLAP DETECTOR IS BLIND TO ROTATION, and it now has a register that exercises it.** Open.
`runtime/textSafe.tsx` measures text with `Range.getClientRects()` and `getBoundingClientRect()` — both
AXIS-ALIGNED. A 2D-rotated label's box is larger than its glyphs and grows on the side it slopes toward.
Since 2026-09-16 TermSpace lays each console's words onto the window's own plane with a 2D affine (a viewer
said the upright text read as a sticker on tilted glass), and `cjk_type_qa --all-aspects` immediately
reported «交付可验收的成果» × «自动归档» as overlapping at 9:16, 1:1 and 4:5. Looked at on the frame: they
are the name and status lines of ONE window, one above the other, glyphs well clear. The name slopes down to
the right, its axis-aligned box grows downward on that side, and it intersects the line below. A false
positive, in a report tier ("candidate") rather than a failure, so nothing was blocked — but the memory entry
"DOM rects blind to rotation" already records that this class inverts in BOTH directions, so a real collision
between two tilted lines could equally be missed.
> **PART OF THIS LANDED, and the item did not say so.** `runtime/textSafe.tsx` grew a ROTATED TYPE section
> — `selfRotated()` reading the off-diagonals of `matrix()`/`matrix3d()` and the `rotate` longhand, plus a
> memoised ancestor walk — and the **`leading`** measure (one element's own wrapped lines) now bypasses
> client rects entirely for rotated type in favour of an orientation-free instrument, `metricLeading()`
> against resolved `line-height`. It was driven by a real defect: `CardStack3D`'s ±13° fan reporting a
> phantom 64px collision. The synthetic probes the acceptance asks for exist and are permanent
> (`TiltedTypeCleanProbe` / `TiltedTypeCollisionProbe`), and
> `tests/test_cjk_type_qa.py::test_the_rotation_guard_is_load_bearing_in_both_directions` mutates
> `selfRotated` to show the clean probe going falsely dirty and the colliding probe being MISSED — the
> "must be shown to miss it first" half, for `leading`. `charLines()` and the orphan detector were made
> rotation-aware too (median inter-character direction instead of axis-aligned grouping).
>
> **What is still open is the CROSS-ELEMENT pass**, which is the one this item is actually about.
> `textSafe.tsx` still intersects `a.r` and `b.r` — two `getBoundingClientRect` boxes — and its only
> concession to rotation is to tag the finding `rot: true`, in its own words "advisory either way; the flag
> says which numbers to discount". So the TermSpace false pair is LABELLED, not eliminated, and the other
> direction the memory entry warns about — a real collision between two tilted lines being missed here — is
> untouched. Worse, **nothing reads the flag**: grep across `scripts/` and `tests/` finds no consumer of
> `rot` (checked 2026-09-23), so the advice about which numbers to discount is written and never delivered.
> **The cheap half is DONE 2026-09-23.** `cjk_type_qa`'s overlap report now reads the flag and says, per
> register, how many of its pairs involve tilted type and that the boxes overstate them — pinned by
> `tests/test_cjk_type_qa.py::test_the_rotation_flag_on_an_overlap_is_read_by_something`, which checks
> BOTH ends (the reader exists, and the renderer still sets the field it reads). It cost a real detour
> before it existed: a 4:3 pair was rendered and inspected by hand that the tag would have qualified on
> sight. What remains is the expensive half below — labelling a false pair is not removing it, and the
> missed-collision direction is untouched.
>
> **Acceptance:** overlap is tested in each element's own local frame (un-apply its computed 2D transform to
> the other's corners, or test the rotated quads with a separating-axis check), demonstrated on TermSpace at
> 9:16 — the false pair disappears — AND on a synthetic probe where two tilted lines genuinely collide, which
> the axis-aligned version must be shown to miss or misplace first.


## C · Peer-library capability gaps still open

**~~C1 · The fake dolly-zoom.~~ DONE 2026-09-14.** `dollyAt` in `runtime/depth.tsx` (the move as a
primitive, so the next register wanting it does not hand-roll a second copy the way `SurfaceCarousel` once
did with `focusAt`) and `DollyZoom` as the register that argues with it. Verified on the rendered frame, not
from the source: the subject's ink box at frame 12 and at frame 168 is the SAME four numbers
`(696, 491, 1228, 578)` while the frame itself changed by 0.0045 mean — both halves of the claim measured.
0 findings from `text_safe_qa` at five aspects in English and in Chinese, nothing dropped by
`cjk_type_qa` at five aspects, `register_shot --check` clean, ground luminance MEASURED (`dark`, token `bg`),
energy 0.0042 motion / 2.2% ink.
> **What looking at it cost.** The first render was a subject floating in nothing: the room was built from
> `dna.line`, and that token is a hairline meant to sit ON a surface — every preset sets it a few levels off
> its own ground (product `#20242f` on `#060709`). Seen through the room's own defocus it is invisible, so
> the move the register exists to make had no room to make it in. Built from `dim` at an alpha instead — a
> mid-tone in every preset, because it has to stay readable — with a major line every fourth cell to give
> the swell something to count by. The type gates were green on that first frame; only looking found it.
> **And a literal union does not survive a props default.** `= {}` on the props object widens
> `direction?: 'in' | 'out'` to `string`, so the compiler cannot hold the prop to its own declared type.
> `in` and `out` are opposite arguments, so it throws rather than picking one.

**~~C2 · Depth seams — gap 3.~~ DONE 2026-09-14.** `ThroughDarkPresentation` and `PortalPresentation` in
`Film.tsx`, reachable from a board (`_KINETIC_TYPES` + `_TRANSITION_STYLE` aliases) and routed by the planner
(a CROSSING `new-topic` now takes the flight instead of collapsing to the carry with everything else — a
bridge line claims continuity, which is the opposite of what a chapter break across a light boundary says).
All three of the peer study's depth hand-offs now exist here.
> **MEASURED ON A RENDERED THREE-BEAT FILM.** Across the through-dark seam the frame's mean luminance ran
> 0.068 -> 0.016 -> 0.013 -> **0.010** (frame max 0.14 — the picture is black) -> 0.040 -> 0.070. A
> cross-fade between two dark beats holds near 0.07 the whole way, so the dip is the flight and not a fade
> wearing its name.
> **And the first portal run verified the GUARD, not the seam.** Beat 3 was an accent flood, so the seam
> crossed a dark/light boundary and was correctly rewritten to a fade — what got measured was a fade's
> smooth monotone ramp, 0.079 -> 0.566. Re-run between two dark beats it renders as a portal: the incoming
> beat at the centre at full size, the outgoing one still in the corners and scaled past the lens. Reporting
> the first run as "the portal works" would have been a claim resting on evidence that never touched it.
> **What is derived and what is borrowed.** The focus relay's parameters were quoted verbatim in the peer
> study; these two were recorded by NAME only and the library is no longer on disk, so their numbers are
> derived here and their headers say so rather than dressing them as measurements taken elsewhere.

**~~C3 · `stage3d` reaches 2 of 164 registers.~~ DONE 2026-09-15.** `TermSpace` is the third, and it is the
last of the peer library's 3D line this tier had no answer to: `basic-3d-scene` became `SpatialSlides`,
`flying-words` became `WordTunnel`, and `terminal-3d` had nothing. Several consoles posed in one ROOM, the
camera flying to each in turn, the screen being faced typing its status under a live caret while the ones
behind hold theirs settled — a 2x2 grid of terminals makes them peers on one plane; travel says they
coexist. 0 findings from `text_safe_qa` at five aspects in English and Chinese, nothing dropped by
`cjk_type_qa` at five aspects, ground luminance MEASURED (`dark`, token `bg`), energy 0.002 motion / 0.3%
ink. Original text: `stage3d` reaches 2 of 164 registers.
> **Overtaken 2026-09-23:** `stage3d` now reaches FIVE — `CraneUp`, `PlaneStack`, `SpatialSlides`,
> `TermSpace`, `WordTunnel`. `CraneUp` is the first register in the library whose camera changes ELEVATION
> and tilts, and it reuses this item's own hard-won lesson: the camera position is derived from the AIM
> (`cam = target + D · forward(rx)`), because raising `y` alone walks the subject out of frame for exactly
> the reason recorded below.
> **TWO DEFECTS NO GATE COULD SEE, both found by looking at the first render.** A console was drawn BLANK —
> the type was culled when its projected block left the safe box and the window was not, so a viewer saw an
> empty screen in the corner, a machine that had crashed rather than one the camera was passing. And the
> camera MISSED what it flew to: backing off as `z: pose.z + d` steps along world z, which is no longer
> behind a lens that has just taken the screen's own rotation — measured 163px off centre on a 1920 frame at
> ry 24deg. Surface and type share one fade now, and the lens backs off along its own forward axis.
> **AND THE OBVIOUS SHORTCUT IS REFUTED, measured before it was taken.** Five registers hand-roll their own
> 3D (`CubeRotate`, `CardFlip3D`, `CardStack3D`, `FractureIn`, `GlowPick`), and `CubeRotate` puts its TYPE
> directly on `rotateY()/translateZ()` faces — exactly what `stage3d`'s header forbids, so migrating it
> looked like reach and a defect fix in one. It is not a defect fix: at 3x nearest-neighbour zoom the front
> face's type is visibly crisp, and the A/B (`scripts/type_sharpness.py CubeRotate --ab=…`, removing the
> container's perspective so the same face composites in 2D) gains **6.6%** edge strength — against the 38%
> the peer-derived case recorded for `perspective(1200px) translateZ(50px)`, and part of even that 6.6% is
> the type being smaller once it is no longer magnified 1.187x. Converting healthy registers buys
> maintainability, not pixels. Reach has to come from registers whose ARGUMENT needs a posed stage.

## D · Decided, deliberately not changed

**~~D1 · `register_energy`'s whole-module dep-hash.~~ REVERSED 2026-09-22 (`4ae1fe8`).** This entry said
"not changing it": editing `layout.ts` marked 104 registers stale when 3-6 rows actually moved, and hashing
per-symbol looked like it would miss a module-level constant read inside a function it hashes —
`INK_BLOCK_FACTOR` inside `inkBlockH` was named as exactly that shape.

It was changed, and **the named risk does not materialise**, because the reachability walk follows an
identifier from the function into the constant rather than stopping at the function's own text. Verified
by experiment on 2026-09-23, both directions, rather than by reading the code:

  * `INK_BLOCK_FACTOR` 1.31 → 1.55 moves `Aliasing`'s hash (`5181181f…` → `3bfc3559…`). Caught.
  * appending an export nothing imports to `layout.ts` moves **0 of 178** rows. Narrowed.

The decision recorded here was the right one **for the implementation that existed when it was written**;
what changed is not the trade-off but the instrument. Left in D rather than deleted, because a decision
that was later reversed is more useful to the next reader than a decision that quietly vanishes.

**D2 · `ink_median`'s last digit is not reproducible** (+-0.001 across a recompile; appending a no-op export
to `layout.ts` moves `VoiceSignal` 0.245 -> 0.246). Harmless against a 0.12 floor. Recorded in `fead316` so
that a moved row is never read as evidence on its own. Treating it means coarsening the number or changing
the manifest format, for no decision it would change.

**D3 · The ink floor is a LIVE-ACTION number, and most of this library sits under it.** Measured from the
committed sweep: **123 of 163 registers** are under `INK_FLOOR` (12%) on their own standalone render, and the
median register is 5.0%. A film's ink is the median over its own frames, so clearing the floor takes a cast
that is more than half drawn from the library's densest quarter — which nothing in the authoring path says.
The floor is not being lowered and the instrument is not being changed: the reference films are not in the
repo (`--reference` re-measures them from a directory the user supplies), so any change to what `ink` MEANS
would silently invalidate the one calibration table this gate has, and a floor derived from the library's own
median would accept the 4.3% film this gate was built to catch. What was wrong was the MESSAGE, which stopped
at the number and left the author one move — the waiver. It now names `density_advice.py`, which reads the
same sweep and answers the question the number raises. **Not changing the floor. The cost is a red gate on
quiet films; the alternative is a gate that means nothing.**
