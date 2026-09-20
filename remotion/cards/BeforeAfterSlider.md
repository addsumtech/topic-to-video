# BeforeAfterSlider

**Identity:** one mock slide is shown twice, a dull grey "before" and a vivid, accented "after". A vertical handle wipes across it from left to right, turning the rough draft into the finished version in place, with before/after chips in the bottom corners.

**Use when:** the claim is that the SAME content was refined: the same heading, figure and chart, restyled from rough to finished. **Not when:** the before and after hold different content or numbers. Both halves print the same words, so use a versus register (e.g. `VersusSplit`) for that.

**Motion core:** the handle travels from 14% to 86% of the panel width over 0.12–0.90 with an ease in-out, so both states always stay visible. Nothing else enters or moves.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `heading` | the slide's heading (dim grey before, accent after) | fixed 92/96px, not fitted. The chart's height is budgeted for a one-line heading, so a heading that wraps pushes the chart and figure down toward the chips and the panel's clipped bottom edge |
| `metric` | the headline figure under the chart | fixed 84px, grey before and the second accent after |
| `sub` | the small line under the figure | fixed 34px dim |
| `beforeLabel` | the chip on the bottom-left | names the rough state |
| `afterLabel` | the accent chip on the bottom-right | names the finished state |
| `series` | the bars of the slide's chart (2–8 numbers, or figure strings in one unit) | omitted: no chart, and the figure moves up. Given: bars drawn from zero in proportion, packed together under the heading when there are few and filling the width when there are many |
| `highlight` | the index of the one bar painted in the second accent | `null` (default) singles out no bar |

**Known traps:**
- The chart used to be a module literal, five bars with the fourth painted "good" green under every film's metric, and it read as the data behind the number. Bars now come only from `series`, and emphasis only from `highlight`.
- Omitting copy prints the demo `Q3 Performance`, `+18%`, `vs Q2`, `Rough draft` and `Board-ready`.
- The panel was a fixed 1500×900. It hung 157px into the caption band, taking the chips and the figure with it. It's now sized to the content zone.

**Refuses:** `highlight` without `series`; `series` outside 2–8 values; a value that is not one number ≥ 0; values in mixed units; every value 0; `highlight` that is not an index into `series`.

**Reference:** `remotion/src/shots/BeforeAfterSlider.tsx`
