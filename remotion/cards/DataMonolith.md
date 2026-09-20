# DataMonolith

**Identity:** a night skyline of glowing towers, one per item, rises from a perspective grid floor — each with a white cap and a soft reflection, labelled underneath and, when the film gives values, its figure written on top.

**Use when:** a handful of things compared by one sourced quantity, as architecture — scale, "how big each is". **Not when:** there is one number (EdStat, OdometerRoll), the values change over time or re-rank (ChartRace), or you have only names and want them to differ in size (without values every tower is the same height).

**Motion core:** the title rises (0.04–0.20); towers grow one after another (from 0.14, staggered 0.06), labels and values fading in behind them; after ~0.62 either a soft band of light sweeps across the caps left to right (no hero) or the hero tower pulses.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one tower each: a label, or `{label, value?, display?}` | 2–9; more makes every tower thinner. With values the heights are in proportion from zero and each figure is written above its tower (shrunk to the tower's width); with none, every tower stands the same height. Labels wrap in the tower's narrow column and the floor rises to keep them clear of the caption band. `display` changes only the written figure, never the height |
| `hero` | the index of the tower to single out | that tower takes the accent, a brighter label and a pulse, the rest take the second accent; omitted = one tone for all and the passing light instead |
| `title` | the small spaced caps above the skyline | fixed 30px, uppercase, not fitted |

**Known traps:**
- Heights used to be hashed from each tower's POSITION under the title "Everything, to scale" — a ranked chart of seven teams nobody measured, with the fourth forced tall and pulsing as the winner. Heights now come only from `value`.
- That default title still prints if `title` is omitted, and it claims "to scale" even over a skyline of equal-height names.
- Values are all-or-none and in one unit: "1.2M" and "800k" would be compared as 1.2 and 800, so mixed units throw.
- Alternating tones by index once split any list into two groups nobody named; non-hero towers now share one tone.

**Refuses:** fewer than 2 or more than 9 items; an item with no label; values on some items but not others; a value that is not one number ≥ 0; values in different units; every value 0; a `hero` that is not an index into the items.

**Reference:** `remotion/src/shots/DataMonolith.tsx`
