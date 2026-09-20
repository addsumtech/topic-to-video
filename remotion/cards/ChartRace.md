# ChartRace

**Identity:** under an uppercase mono title, 2–6 horizontal bars grow from staggered starts and slide past one another as they overtake, their figures counting up beside them and the current leader glowing. Near the end every bar eases onto its exact final rank and settles on the film's own figure.

**Use when:** the beat is a ranking of 2–6 sourced quantities in one unit, and "who comes out ahead" is the point. **Not when:** there is one figure (use `ChartLive` or a number register), more than six rows, or the order over time is itself the data. The mid-race overtakes are staging from `delay`, not history.

**Motion core:** the title fades 0.03–0.16. The race runs 0.06–0.62, with each bar starting at its `delay` fraction of that window. Ranks slide continuously as bars overtake, and 0.50–0.62 eases every bar onto its final slot. From 0.62 every bar and figure is the film's, held for the last third.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `data` | the rows: `label`, `value`, optional `delay` (0–0.9), optional `display` | row height divides the zone, so two rows are fat bars and six are slim. Labels share one size, fitted to the left gutter. `delay` staggers the starts to stage overtakes, and `display` is how the settled figure reads (`4.6M 人`) |
| `title` | the spaced mono title above the bars | fitted to the width, up to 34px; `''` hides it |
| `unit` | appended to each row's `value` when it has no `display` | it's appended, so don't also write it into `value` |

**Known traps:**
- Omitting `data` prints the demo rows (`Alpha`, `Bravo`, `Charlie`, `Delta`, `Echo`) and the title `Who pulls ahead`.
- A `value` that already carries its unit (`"62%"`) plus `unit: "%"` settles as `62%%`.
- Fixed in the code: a seventh row used to be dropped silently, rounding printed 4.6 as `5`, and a rank taken from the raw gap left bars of 0.45/0.30/0.25 stacked on one slot. All three are handled now; the row limits throw.
- Labels are `nowrap` with a 14px floor. A very long label still shrinks every label, and at the floor it can run off the left edge.
- A tie has no leader glow. The bar tones follow the DNA, but the label and figure greys are fixed.

**Refuses:** fewer than 2 or more than 6 rows; a row with no `label`; a `value` that is not one number ≥ 0; a `delay` outside 0–0.9; values written in different units; every value 0.

**Reference:** `remotion/src/shots/ChartRace.tsx`
