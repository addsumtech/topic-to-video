# GaugeCluster

**Identity:** an instrument panel: up to two satellite gauges sweep their arcs, then the hero gauge sweeps a 270° arc, its needle rises and its figure counts up and locks.

**Use when:** live status / health — one KPI with up to two supporting readings, each a sourced fraction. **Not when:** there are more than three readings (TermBars), or the quantity has no full scale — without a fraction or a percentage the hero is an empty track.

**Motion core:** the title rises (0.03–0.16); the satellites sweep (from 0.10, staggered 0.06, done by ~0.42); the hero sweeps and counts 0.26–0.50; the second half holds, so the true figure is on screen at the mid-scene frame.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `value` | the hero's figure, as the film's string | printed as written once settled; a string that is one number counts up with the sweep. Fitted inside the dial |
| `unit` | the small accent suffix after the figure | `%` (or a `%` suffix on `value`) also lets a 0–100 value drive the hero arc |
| `fill` | the hero arc as a fraction 0–1 | wins over the percentage rule; with neither, the hero is an empty track with no needle |
| `label` | the mono caption under the hero | fitted to the dial's width |
| `gauges` | 0–2 satellites, each `{label, fill}` | two flank the hero; one sits to its right with the pair centred as a group; `[]` leaves the hero alone |
| `title` | the spaced caps above | fitted to 90% of the width; '' hides it |

**Known traps:**
- The readout once stripped the value to digits ('4.2' → 4, '1.5k' → 2) and the arc always read it as a percentage of 100, so '350' ms drew a full gauge. The figure is the film's string now, and the arc needs a stated fraction or percentage.
- Omitted `gauges` still draws the demo's two satellites ('latency' 0.62, 'load' 0.44) — pass `[]` for a hero alone. Omitted `label` and `title` print 'uptime' and 'System health'.
- The demo's 98% appears only when NO content prop is passed; pass anything without `value` and the hero shows no figure.
- The cluster was laid out in 1920-wide pixels and hung off the edges at 1:1, 4:5 and 9:16; it scales to the frame now.

**Refuses:** `gauges` that is not an array or has more than two entries; a gauge with no label; a `fill` (hero or satellite) that is not a number from 0 to 1.

**Reference:** `remotion/src/shots/GaugeCluster.tsx`
