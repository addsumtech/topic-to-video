# QuadSplit

**Identity:** the content zone splits into up to four panels that pop in one after another — each with a numbered tone chip, a picture and a label — and then (unless held) the other panels clear away and one hero panel expands to fill the frame.

**Use when:** "four things we rely on, then the one that matters" — or, with `hero: null`, simply "there are four of these", held as a 2×2. **Not when:** there are more than four items (use a list register), the items carry numbers (use a quantity register), or they are ordered steps.

**Motion core:** the heading fades in 0.04–0.16; panel *i* pops in (slight overshoot) over 0.12 + 0.09·*i* to 0.34 + 0.09·*i*, its picture drawing on from 0.16 + 0.09·*i*. With a hero: the heading fades out 0.66–0.74, the other panels clear 0.70–0.80, and the hero panel grows to fill the frame above the caption band (inside a safe margin) 0.72–0.97, its label re-fitted larger as it goes. Held (`hero: null`): nothing clears, the heading stays, and the 2×2 holds from about 0.6.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `panels` | one panel each: `label`, optional `icon` (from `runtime/icons`), optional `glyph` | laid out per count — 1 fills the zone, 2 sit side by side, 3 put the third across the bottom row, 4 make a 2×2. An `icon` wins over a `glyph`; with neither, the label takes the picture's room and prints larger. Labels are fitted to two lines at both tile and hero size. `glyph` is one of `checks`, `gutter`, `peers`, `review` (tests / run-vs-never-run code / cross-check / human review) or the neutral marks `bars`, `ring`, `dots`, `wave` (a run / a place / a field / a flow). Omitted, four demo panels (`Find it`, `Edit it`, …) print |
| `heading` | the spaced mono caps line above the grid | fitted to one line (max size 32px, ellipsis as a last resort), so a long heading prints smaller; omitted, the demo `Four ways it wins` prints |
| `hero` | the index of the panel that expands, or `null` to hold all four | omitted, a film's quad HOLDS (no panel is picked by position); only the standalone demo expands its first panel. Name the panel that matters to get the expansion |

**Known traps:**
- A delivered film said "four World Heritage sites sit inside this one city" and ended on a single card — the default `hero: 0` expands one panel. When the claim is the four together, pass `hero: null`.
- The neutral glyphs used to be a gauge, a column chart, a counter and a trend line with numbers made up by the clock (a 270° arc under "Castellum Traiectum"). They are now shapes with nothing to read off; a panel that has a quantity belongs in a quantity register.
- `gutter` used to draw seven code lines with a fixed split, five covered and two never run, on every film: a countable "5 of 7" (about 71%) coverage no prop supplied. It now draws one line of each state (a solid tick for a line the tests ran, a hollow amber tick for one they never ran), like a legend. It says "some code the tests never touch" and has no split to count. If the beat has a coverage figure, put it in the `label` as text or use a quantity register; the split is deliberately NOT a prop here.
- A panel with no glyph used to get one picked by index (a ring and a wave under 路飞 / 哆啦A梦). Now it draws no picture; an unknown glyph name throws.
- The grid and the expanded hero stop above the caption band with room for their drop shadow; a bottom row flush against it once put its shadow in the subtitle.

**Refuses:** a `hero` that is not a panel index or null; fewer than 1 or more than 4 panels; a `glyph` name outside the list above.

**Reference:** `remotion/src/shots/QuadSplit.tsx`
