# BlueprintGrid

**Identity:** on a faint measured grid with corner crop marks, a schematic module draws itself in thin strokes (an outline, an accent header rule, three sub-blocks). Dimension lines with arrowheads land under it and beside it, a centre crosshair appears, and mono spec labels fade in. When the film gives a figure, it counts up in the top-right corner.

**Use when:** the beat is technical precision, a spec, or "engineered, measured, specified", with one or two short spec facts and at most one real measured figure. **Not when:** the subject needs to be depicted: the module is a generic box with three identical sub-blocks and never shows the film's thing.

**Motion core:** the unit/tag label fades 0.12–0.30; the module outline draws 0.10–0.42; the accent rule 0.34–0.50; the sub-blocks fade 0.40–0.70; the horizontal dimension 0.50–0.72, the vertical 0.58–0.80; the crosshair 0.66–0.84; the spec labels 0.60–0.86; the figure fades 0.55–0.78, counts up 0.55–0.72 and then holds on the film's own string.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `unit` | the module's name, after `◇`, above the box | fixed 24px mono, not fitted |
| `tag` | the grey word after `·` | a qualifier (`local-only`) |
| `spec1` | the note centred under the dimension line | `nowrap`, fitted to the room its anchor leaves (16–22px); a long note shrinks toward the 16px floor |
| `spec2` | the second note | goes beside the machine when it fits there at 16px or more; otherwise it moves under `spec1`, where it gets the full width |
| `metric` | the corner figure: a number or the written figure (`"62%"`, `"3–5"`) | `null` (default) leaves the corner empty. A string that is exactly one number counts up, and anything else prints as written, fitted to 40% of the width, up to 80px |
| `metricUnit` | the accent unit after the figure | drawn only when given |
| `metricLabel` | the small line under the figure | drawn only when given |
| `readout` | a measurement beside the crosshair | `''` (default) draws nothing, and it must be a real measurement |

**Known traps:**
- The corner used to count 0→100 with a hardcoded `%` on every film, including a beat arguing that the nave was never finished. 99.5 settled as `100%`. `metric` now has no default.
- The crosshair readout used to be the literal `x:960 y:540`, a screen coordinate posing as a measurement.
- Don't pass `"62%"` together with `metricUnit: "%"`. The unit is appended, so the corner prints `62%%`.
- Omitting copy prints the demo `workbuddy.unit`, `local-only`, `runs on your machine` and `0 cloud calls`.
- The spec, tag and figure-label greys are fixed, so they stay dark grey even when the drawing inverts on a dark DNA.

**Reference:** `remotion/src/shots/BlueprintGrid.tsx`
