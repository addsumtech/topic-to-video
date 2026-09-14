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
member is now a hard case — `_LABEL_V` 6/6/7/8 glyphs, `_MED_V` 26/28/27/26, `_TITLE_V` 7-8, `_LONG_V`
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

**B4 · Kinsoku is implemented in half.** `wrapLines` now glues a closing mark to the glyph before it, so a
line cannot OPEN with one (`a8ded7b`). The other half of the rule — a line may not END with an opening
bracket or quote — is not implemented. It is left out deliberately: no string in the CJK fixture contains
one, so adding it today could be neither verified against a rendered frame nor shown to be load-bearing by
a mutation, and an unverified rule in the denominator of every Chinese reserve is worse than a known gap.
> **Acceptance:** a fixture string carrying an opening bracket, a rendered frame showing the browser's own
> break, and a test that goes red when the rule is disabled — in that order.

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

**C3 · `stage3d` reaches 2 of 164 registers.** `SpatialSlides` and `WordTunnel`. A stage with two things on
it is not yet a language.

## D · Decided, deliberately not changed

**D1 · `register_energy`'s whole-module dep-hash.** Editing `layout.ts` marks 104 registers stale when 3-6
rows actually move, costing ~15 minutes each time. Hashing per-symbol would miss a module-level constant
read inside a function it hashes — `INK_BLOCK_FACTOR` inside `inkBlockH` is exactly that shape — and a
staleness gate that can silently miss is worse than a slow one. **Not changing it. The cost is time; the
alternative risks correctness.**

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
