# FunctionPlot

**Identity:** a function drawn the way a lecturer draws it: its typeset formula written on in the plot's corner, the axes ruled, the curve traced through the film's own samples from the first to the last, then a point that rides it with a dropline to the axis and a readout of the LAST SAMPLE IT HAS REACHED — so the readout ticks through the film's data rather than inventing values between them.

**Use when:** the SHAPE of a dependence is the point — where it rises, where it turns, where it dies away — and the rider makes each point of that shape a pair of numbers. Hide the caption and the curve still says "decays while it oscillates" or "grows faster and faster". **Not when:** comparing categories (a bar register), a history with events on it (a timeline / chart register), one number (a figure register).

**Motion core:** axes draw on t 0.06–0.24; the formula is written t 0.10–0.32; the curve traces t 0.20–0.50 (cubic in-out); the rider appears at 0.48 and travels by ARC LENGTH along the drawn polyline t 0.50–0.90, so its pace is even whatever the sample spacing; the readout is placed beside it with `placeLabel` (clamped into the plot) and above it unless the curve is too near the top.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | a small label over the title | context, never a second claim |
| `title` | the plot's headline | the film's own; the demo's title belongs to the demo data |
| `points` | the film's samples `[[x, y], …]`, at least 2, x increasing | the curve is the polyline through them — nothing fitted, nothing smoothed; dense samples draw a smooth curve |
| `tex` | the function's formula, in TeX | written in the top-right corner; a formula that only fits under 3% of the short side an em throws |
| `xRange` | the x axis's span | default exactly the data's; the ends are printed as written |
| `yRange` | the y axis's span | default exactly the data's; a dashed zero line when 0 is inside |
| `xLabel` | what the x axis measures | under the x axis |
| `yLabel` | what the y axis measures | in the plot's top-left |
| `xName` | the readout's x variable name | default `x` |
| `yName` | the readout's y variable name | default `y` |

**Known traps:**
- A readout interpolated between samples would print values the film never supplied; it shows the last sample passed, as written (`figureText`), and the dot rides the drawn line between them.
- The demo's data is COMPUTED in the source from the formula it is drawn under (y = e^(−x/2)·cos 2x, 121 samples, rounded to 3 decimals there), and the demo's formula, title and axis names are dropped the moment a film passes its own `points`.
- Two plots mounted at once (a seam) would clip each other's curve through one clipPath id: the id is per mount.

**Refuses:** fewer than 2 samples; a sample that is not two finite numbers; x not increasing; a range that is not `[lo, hi]` with hi > lo; data with no spread on an axis and no range given; no room for the plot under the heading; a formula too wide for the corner.

**Reference:** `remotion/src/shots/FunctionPlot.tsx` · runtime `mathMorph`

**Measured:** 5.7% ink (clip median) · 52.8% footprint · 0.0005 motion · reach 0.599 (product DNA, the demo at its own 8 s). QUIET: a thin curve and a small rider; intercut with a dense register.

**Review:** NOT critic-reviewed — built and looked at by its author: 16:9 Latin demo (trace, ride), 9:16 Chinese labels with the film's own samples, 1:1.

**Provenance:** scientific. **Family:** MA.
