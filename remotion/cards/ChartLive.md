# ChartLive

**Identity:** a glowing line draws itself left to right across an unlabelled gridded plot, a soft area filling down to zero beneath it and a bright dot riding its tip, while the headline figure above counts up in step. With no series, the figure and its label stand alone, centred.

**Use when:** the beat is one sourced headline figure, optionally with the sourced series behind it (a trend over ordered points). **Not when:** the points need axis labels or dates (the gridlines are unlabelled), several series must be compared (use `ChartRace` for ranked rows), or the film has no real series. Give the figure alone then; never invent a curve.

**Motion core:** the draw and the count share one clock, 0.12–0.60 (ease-out); the tip dot shows only while drawing. From 0.60 the figure and line hold, settled, for the last 40% of the beat.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `endVal` | the headline figure: a number or the written figure | a string that is exactly one number counts up with its own decimals, sign and grouping; anything else prints as written. It's sized to the width, from 48 to 210px, so short figures are huge. Omitted: no figure |
| `unit` | the smaller accent unit after the figure | drawn at 100/210 of the figure size; no default for a film (`68` stays `68`) |
| `label` | the line under the figure | fitted to the width, up to 42px |
| `series` | the line's points, in order (numbers or one-number strings) | 2–240 points on a zero-based scale; the area fills to zero, not to the frame. `[]` or omitted: no plot, and the headline centres in the zone |

**Known traps:**
- The curve used to be one hardcoded twelve-step climb, shipped under a real figure's label (`68× Hy3 call volume`) as though it were that figure's history. The line now comes only from `series`.
- If `label` is omitted, the demo `tasks handled this month` prints even when a film passed `endVal` or `series`. That's deliberate, so the demo-copy gate lists it. The demo `128` / `k` / rising series appear only when NO content prop is passed.
- The counter used to round (2.5 → `3`) and defaulted the unit to `k`, so `68` printed as `68k`. It now lands on the film's own string.
- The plot used to sit under the figure's corner, so a falling series ran through the figure. The plot now starts below the headline block.
- The ground, the gridlines and the figure ink are fixed dark green / mint; only the accent follows the DNA.

**Refuses:** `series` that is not an array; a `series` with 1 point or more than 240; a point that is not one number.

**Reference:** `remotion/src/shots/ChartLive.tsx`
