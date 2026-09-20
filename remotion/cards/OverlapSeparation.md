# OverlapSeparation

**Identity:** two panels with identical chrome and one shared axis each draw the same two populations as density curves — on the failing measure the curves pile on top of each other, the overlap floods a blended colour and a dashed threshold swings back and forth never finding a clean cut; on the passing measure the curves pull apart and the same search locks onto the empty gap.

**Use when:** the claim is "this measure cannot tell these two populations apart, that one can" — two measures scoring one pair of populations, with a real mean and spread for each. **Not when:** there is only one measure, the means and spreads are not known, or there are more than two populations; for a plain before/after use a versus register such as VersusSplit.

**Motion core:** kicker and title fade in over 0–0.14 and the shared legend over 0.08–0.22. Failing panel: card in from 0, curves grow over 0.06–0.28, the blended overlap floods in from 0.26, the threshold searches over 0.32–0.62 (a wide, decaying swing, dashed) with hatched wrong-side slices, its note at 0.40. Passing panel: card in from 0.04, curves grow over 0.36–0.56, overlap (only if any) from 0.56, a short search over 0.56–0.72 that locks solid, its note at 0.70. Settled from about 0.8.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | a small mono line at the very top | fitted to one line; empty draws nothing |
| `title` | the headline above the panels | one line, fitted to the width and capped at 40px, so a long title gets small rather than wrapping |
| `fail` | the measure that cannot separate: `{label, note, a: {label, mean, spread}, b: {…}}` | left panel in landscape, upper in portrait. Its `label` names the panel on one line; its `note` states the finding on up to two lines. Both are sized together with `pass`'s so neither panel reads as senior |
| `pass` | the measure that can: same shape as `fail` | right panel in landscape, lower in portrait. When both measures name the same two populations one legend sits above both panels; different labels give each panel its own legend |
| `domain` | the shared x-axis `[lo, hi]` | unset, a 0..1 score keeps 0..1 and anything else gets a padded, round-numbered range; five tick labels either way. A wider domain squeezes both pairs toward the middle |

**Known traps:**
- Missing pieces used to be filled from the demo — `mean ?? 0.52`, `spread ?? 0.17`, label `A` — and a film passing `fail` alone got the demo's "Execution" panel beside it as if measured. All of that now throws; omitting BOTH still draws the demo ("Surface similarity" vs "Execution", titled "Two measures, one set of cases").
- The threshold's behaviour is set by the slot: the `fail` panel never locks and the `pass` panel always locks. The slot is now checked against the data: the shot computes each pair's overlap (the share of area under both curves, the same region it floods with the blended hue) and THROWS when the `pass` pair overlaps at least as much as the `fail` pair, naming both percentages. It used to draw a solid lock over the more-overlapping pair without complaint.
- The check is relative, not absolute. A `pass` pair that still overlaps a lot (say 40%) but less than `fail` passes it and still locks solid, which overclaims a clean cut. The register is for a measure that separates cleanly; a merely better one still gets the lock, so do not cast it for that.
- The two panels share one y-scale only while their peaks are comparable; a very tight pair against a very wide one trips the legibility floor and the scales differ.
- A `domain` that is not two finite numbers with `hi > lo` is ignored silently and the automatic range is used.
- Spreads are floored at 2% of the largest spread so a zero-variance population still draws — a spread of 0 shows as a very narrow spike, not a line.

**Refuses:** only one of `fail` / `pass` given; any of the four populations missing, without a `label`, without `mean` or `spread`, with a non-finite `mean` or `spread`, or with a negative `spread`; a `pass` pair whose curves overlap at least as much as the `fail` pair's.

**Reference:** `remotion/src/shots/OverlapSeparation.tsx`
