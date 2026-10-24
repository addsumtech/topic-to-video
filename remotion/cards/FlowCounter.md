# FlowCounter

**Identity:** one figure set huge in lining tabular digits that rolls odometer-style from each value the film states to the next — the units wheel spins hardest and blurs with its speed, the high places turn only when they must, a column appears when the number grows into it — holding on each value long enough to read, with a step track underneath.

**Use when:** the claim is one quantity and how it moved — "1.2B, then 3.45B, then 12.8B" — and the distance travelled should be felt. **Not when:** several figures stand side by side (a stat or table register), the figure does not move (`EdStat`, `TermCounter`), or it is a ranking (`RankRace`).

**Motion core:** the figure fades in at 0.02–0.12 on its first value; from 0.08 to 0.86 the clip alternates HOLD (0.9 parts) and ROLL (1 part), so n steps give n holds and n−1 eased rolls, the last value holding to the end; each step's label crossfades at the middle of its roll and the track's line fills as it goes.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | a small mono line above the figure | tracked; empty draws nothing |
| `steps` | 1–5 steps: `value` (as the film writes it: "$1.2B", "4,096", "38%") and an optional `label` under it | one step is a figure that simply lands; more make the roll. Two steps that are each one number in the same prefix and suffix roll through the values between them; any other pair rises out and in |
| `note` | one supporting sentence under the track | wraps to three lines at most |

**Known traps:**
- Each settled value prints exactly as written; while rolling, the number is shown in the arriving value's written form (decimals, grouping), counting between the film's two numbers and never beyond them.
- Digits sit in cells as wide as the face's widest measured digit, so the line cannot jitter; lining figures are switched on for every element by `runtime/fonts.ts`.
- The figure is sized so the widest step fills at most 84% of the frame width, capped at 24% of the short side.
- With no `steps` the demo rolls 1,280 → 4,096 labelled only by role.

**Refuses:** no steps or more than 5; a step with no `value`.

**Reference:** `remotion/src/shots/FlowCounter.tsx`
