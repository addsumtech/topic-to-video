# TallyLedger

**Identity:** a ruled ledger sheet where each row's count is marked off in tally strokes, in gates of five with the fifth struck across. The rows fill one after another, then the sheet is double-ruled off with a total.

**Use when:** the figure is one that somebody actually counted (civic, historical, survey counts) and the shape of the count matters: which row carries most of it, and how the parts make up the whole. **Not when:** the counts span orders of magnitude (the small rows cannot be drawn at the big rows' stroke; use a bar or table register), or the number is live telemetry (a counter register).

**Motion core:** the kicker fades in over 0.02–0.16 and the ruled lines draw across over 0.08–0.30. Rows start at 0.20, staggered over the next 0.48, each fading in its label and figure while its strokes appear one by one. The double rule, total, legend and note land together at 0.78–0.94.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | small spaced caps above the sheet | leaving the demo `THE COUNT` prints English on any film |
| `rows` | 1–5 rows of `{label, count}` | each row draws round(count ÷ stroke) strokes, so the rows' lengths are the comparison. Row height is capped, so one or two rows sit at the top of the sheet and five fill it. `count` may be a number or a figure string; the figure at the right is printed exactly as written. Labels wrap in a column a fifth of the width |
| `perStroke` | how many one stroke stands for | larger means fewer, sparser strokes. If the largest row would need more than 40 strokes, the stroke is coarsened on a 1-2-5 ladder, and the legend prints the stroke actually used |
| `strokeUnit` | what one stroke means, printed in the legend ("500 bicycles") | it makes the legend a sentence about the subject. Once it is set, the ladder is disabled (those words would become false at another scale) and an over-40 row throws with the `perStroke` that would fit. Empty at a stroke of 1 means no legend |
| `total` | the figure the ledger closes on, big in the accent under a double rule | copy, printed exactly as written. Empty removes the whole foot |
| `totalLabel` | the small caps word beside the total | shown only with a `total`. The default is the English word `total` |
| `note` | a mono line at the foot of the sheet | a source line. It sits just under the legend and has no height reserved, so keep it to one line |
| `legendLabel` | the words before the stroke's value, like `one stroke =` or `每一笔 =` | shown whenever there is a legend. The English default prints on a Chinese film unless set |

**Known traps:**
- Rows past 40 strokes used to be cut to 40 in silence, so counts of 45 and 200 drew identical tallies. Now the stroke coarsens and the legend says so, or, with `strokeUnit` written, the register throws.
- `total` is never summed from the rows. A total that disagrees with them is drawn anyway.
- Three English defaults (`kicker`, `legendLabel`, `totalLabel`) print on a non-English film unless each is set.
- Widely spread counts cannot share a tally: a non-zero row that rounds to zero strokes throws rather than drawing an empty row beside a real figure.

**Refuses:** `rows` not an array, empty, or more than 5; a row with no `label`; a `count` that is missing, not a single number, or negative; `perStroke` not a number above 0; a largest row over 40 strokes when `strokeUnit` is set; a non-zero count that would draw no strokes.

**Reference:** `remotion/src/shots/TallyLedger.tsx`
