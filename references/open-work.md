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

**A3 · Latin across the seven display faces.** The `--all-dna` flag exists (`fead316`) and has never been
run library-wide. This is the axis that hid `VariableTypeMorph`.
> **Acceptance:** `text_safe_qa --library --all-dna --aspect=1:1` reports 0 for every preset.

**A4 · `cjk_type_qa --all-aspects`, library-wide.** The flag was added in `5e08043` and proved on one
register. It is the only audit that can see a string a register declined to DRAW — `text_safe_qa` reports
type CUT OFF and therefore can only see ink that exists.
> **Acceptance:** `cjk_type_qa --library --all-aspects` reports no DREW ALMOST NOTHING and no dropped
> strings that are not explained.

**A5 · `film_energy_qa` has never been run against a real film.** It needs a real `out_dir`, which no
session has given it.
> **Acceptance:** one end-to-end render, then `film_energy_qa <out_dir>`, with its output read.

## B · Instrument work the baselines depend on

**B1 · `_MED_V` and `_LONG_V` are not hardened the way `_LABEL_V` was.** `_LABEL_V` was rewritten so its
SHORTEST member is a hard case, because a pool with a soft member tests some registers softly at random,
depending on which ordinal their prop lands on. The other two pools still contain short members.
> **Acceptance:** every entry of each pool is at least as demanding as the one that exposed a real defect,
> and a re-sweep at 1:1 still reports 0 (or the defects it finds are fixed).

**B2 · `focusZ` is dead.** It occurs exactly once in the repository, in `validate.py`'s NaN-guard list: a
check on a field no renderer has ever read. The branch it sits in is now refused outright (`8e3837c`).
> **Acceptance:** removed, and `grep -r focusZ` returns nothing.

**B3 · A transient render failure is reported as a FINDING.** The props-file race is fixed (`8e3837c`), but
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

## C · Peer-library capability gaps still open

**C1 · The fake dolly-zoom** — subject pinned while the background swells 1 -> 2.25. The last unbuilt piece
of the peer study's gap 2. Nothing in the library does it.

**C2 · Depth seams — gap 3, untouched.** Three of their six hand-off recipes are built on depth; only the
focus relay has been borrowed. `through-dark flight` and `portal wipe` do not exist here.

**C3 · `stage3d` reaches 2 of 163 registers.** `SpatialSlides` and `WordTunnel`. A stage with two things on
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
