# RankRace

**Identity:** the film's series as horizontal bars stepping period by period through the values the film gives: each period HELD with every figure exactly as written, each move a continuous slide in which bars grow, shrink and overtake, the scale following the current leader, and the periods on a timeline whose playhead walks between their ticks.

**Use when:** a ranking changed over time and WHEN the order changed is the story. **Not when:** there is one period (`ChartRace`, `PhysicsStack`), one quantity moving (`FlowCounter`), or the order is not the point (a line chart).

**Motion core:** bars and timeline fade in at 0.02–0.10; from 0.08 to 0.90 the clip alternates HOLD (0.85 parts) and MOVE (1 part) — n periods give n holds and n−1 eased moves; during a move each bar's slot follows a soft rank of the current values and lands exactly on the arriving ranking; the leader at a hold carries a glow.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | one line in the title band | empty draws nothing |
| `periods` | 2–8 period labels in time order, printed as written | every label is shown when they all fit along the timeline; otherwise the current one, and the first and last only where they clear it |
| `series` | 2–12 series: `label`, one `values` number ≥ 0 per period, optional `display` strings per period | labels share one column sized to the widest; values one unit |
| `unit` | appended to each value when there is no `display` | don't also write it into the values |
| `show` | bars on screen, 2–8 (default up to 8) | the rest wait below the last slot and fade in as they rise into it |
| `note` | a mono line under the timeline | a source or reading note |

**Known traps:**
- Positions are the film's values at a period or a straight line between two consecutive ones — nothing in between is data, and the period label is never counted through.
- During a move a figure counts between the two given values in the arriving value's written form; a pair that is not each one number in the same form shows the arriving string.
- Hues tell series apart and mean nothing else.
- The demo's series and periods are named by role only.

**Refuses:** `periods` without `series` or the reverse (either alone would be drawn against the demo's other half); fewer than 2 or more than 8 periods; fewer than 2 or more than 12 series; a period without a label; a series without a label, with a different number of values than periods, or with a value that is not a number ≥ 0; a `display` list of the wrong length; a series label wider than the label column.

**Reference:** `remotion/src/shots/RankRace.tsx`
