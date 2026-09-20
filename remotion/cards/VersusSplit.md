# VersusSplit

**Identity:** a head-to-head split screen. Two contenders slide in from opposite edges across a diagonal seam, a VS badge slams into the middle, attribute rows tick in on each side, and, only if the film names one, the winning side lights up with a glow, ✓ bullets and a WINNER chip.

**Use when:** the beat compares two things side by side (before/after, us/them, option A/B), with up to four attributes each, and the film may or may not give a verdict. **Not when:** the tension is meant to stay unresolved (use `TensionScale`), there are more than two sides, or there are more than four attributes (a table register).

**Motion core:** the title fades in over 0.02–0.16. The left side slides in over 0.08–0.42 and the right over 0.16–0.50 (easeOutExpo). The VS badge scales in with an overshoot and untwists over 0.46–0.64. Points tick in from 0.50 (left) and 0.56 (right), 0.08 apart. The WINNER chip fades in at 0.80–0.95.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `left` | the left contender, `{label, points?}` | `label` is a fixed 92px heavy word, not fitted. The panels are 58% wide and overlap at the seam, so a long label runs toward, and under, the VS badge. 0–4 `points` in 32px, each behind a `•` (a `✓` on the winning side) |
| `right` | the right contender, `{label, points?}` | as `left`, mirrored and right-aligned. Pass both sides or neither. Leaving both out prints the demo `Before` / `After` |
| `winner` | the verdict: `0` for left, `1` for right, omitted for none | with no verdict both sides stay neutral. A winner gets a tinted glow on its half, a glowing label, ✓ bullets, a WINNER chip, and the DNA's primary accent |
| `title` | the spaced mono caps across the top, centred on the seam | its ink is picked to read on both halves. The demo `The difference` prints if omitted |

**Known traps:**
- `winner` used to default to the right side, so every film got a WINNER chip and ✓ marks on whichever contender was written second: a verdict nobody made. It now defaults to none. Pass it only when the film concludes.
- One side alone used to be completed with the demo's "After · One command · Seconds · Always caught". It throws now.
- A fifth point used to be dropped by `.slice(0, 4)`. It throws now.
- `WINNER` and `VS` are the form's own English words and always print (WINNER only with a verdict). Labels and points are fixed pixel sizes, so long copy wraps rather than shrinks.

**Refuses:** only one of `left`/`right` passed; a side with no `label`; `points` that is not an array; more than 4 points on a side; an empty point; `winner` other than 0, 1 or omitted.

**Reference:** `remotion/src/shots/VersusSplit.tsx`
