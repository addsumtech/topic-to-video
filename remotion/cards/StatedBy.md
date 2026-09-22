# StatedBy

**Identity:** one to three figures set on a plate, and a SOLID stamp struck across its foot rule naming who asserted them and when. The stamp lands last and overlaps the plate's own rule, so the reading is "…and this is who says so".

**Use when:** the beat quotes figures the film did NOT measure — a vendor-stated benchmark, a self-reported survey, a press release, a manufacturer's rating, a party's own count — and the provenance is the claim rather than a caption under it. "X says 98%" is a different sentence from "98%". **Not when:** the film measured the number itself, or the figure needs no speaker (that is `EdStat` / `TermCounter`), or there are four or more figures (that wants a table).

**Motion core:** the kicker fades 0.02–0.14. The plate draws on 0.04–0.24 (easeOutCubic). Each figure enters from 0.14, 0.10 apart, and — unless `roll:false` — counts toward its final string over 0.18→0.52, staggered the same way. The stamp is struck at 0.62–0.78 with an easeOutBack overshoot. The note fades in 0.76–0.88.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `figures` | 1 to `MAX_STATED_FIGURES` (3) figures, `{value, unit?, label?}` | `value` is printed through `runtime/figure` EXACTLY as the film wrote it — its sign, decimals, grouping and any trailing words ("1000 万", "98%", "0.5 秒", "−12", "90% 以上"). `unit` sets smaller beside it; `label` is the line under. One figure fills the plate; three divide it with hairlines |
| `stamp` | the attribution, `{label?, source?, date?}` | the register's argument. `label` is the assertion type ("厂商自述"), `source` the speaker or domain, `date` when. Its ink is measured against the block through `runtime/onAccent`, which is where a system's second accent can be type on a light film |
| `roll` | `false` holds every figure at its final string from frame one | default is to count up. Set it false for a beat whose point IS the number: parading invented intermediate digits is its own small lie |
| `kicker` | the spaced label over the plate | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the plate, in the film's own voice | the place to say what the figures are NOT (e.g. "不是独立实测") |

**Known traps:**
- `figureValue` is never used to redraw a value — only `figureText`/`figureAt`, so no digit the film did not write ever appears at the final frame. The roll is an animation toward the film's own string, not a re-rendering of it.
- Three is the plate. A fourth takes each figure under the size at which a big number is the first thing you see, which is the only reason to set a number big.
- The stamp lands LAST on purpose. Sampling this register at the middle of the clip shows a plate with no attribution — that is the animation, not a defect.

**Refuses:** no `figures`, or no figure with a `value`; more than `MAX_STATED_FIGURES`; a `stamp` with neither `label` nor `source` (a plate of figures with no stamp is a different register — `EdStat`).

**Reference:** `remotion/src/shots/StatedBy.tsx`
