# PositioningMatrix

**Identity:** a 2×2 map — two axes draw out through the centre with arrowheads and labels at their ends, then dots pop in one by one at the positions the film gives them, and a hero dot lands larger with a glowing ring, a brief pulse and its quadrant tinted.

**Use when:** the claim is WHERE things sit relative to two qualitative dimensions — "who leads", "where we are versus the field" — with 1–8 named items. Positions are qualitative; there is no numeric scale. **Not when:** the positions are measured values (use a chart register that takes numbers), or there is one axis only (a spectrum or ranking register).

**Motion core:** the title fades in 0.02–0.16; the axes draw from their origins 0.08–0.40; the end labels fade in 0.30–0.50; dots pop in place with a slight overshoot from 0.42, staggered so the last one has landed by the end (0.1 apart for four); the hero's quadrant tint fades in 0.50–0.70 and the hero pulses once, decaying, after it lands.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the spaced mono caps line at the top | a short heading; long copy is not fitted and wraps; omitted, the demo `The landscape` prints |
| `xAxis` | `[left end, right end]` labels of the horizontal axis | short words sit at the arrow tips; long labels run outward from the plot; omitted, demo `Simple` / `Powerful` print |
| `yAxis` | `[bottom end, top end]` labels of the vertical axis | as `xAxis`; omitted, demo `Manual` / `Automated` print |
| `items` | one dot each: `label`, `x` and `y` in 0..1 (y up), optional `hero: true` | 1–3 dots read as a sparse map, 6–8 as a crowded field. A hero is bigger, glowing, labelled in bold and tints its quadrant; several heroes tint several quadrants; a hero exactly on an axis (x or y = 0.5) tints none. Omitted, demo dots A/B/C/Us print |

**Known traps:**
- The top-right quadrant used to be tinted as the "winning corner" whatever the film said; the tint now follows the hero, and with no hero nothing is tinted.
- Items without coordinates used to be plotted dead centre; `x` and `y` are now required in 0..1, so a position the film never gave cannot be drawn.
- One-character labels (a Chinese name like 「我」) used to be hidden; every given label is drawn now.
- Labels never wrap and always sit to the right of their dot, so a long label on a dot near the right edge runs past the plot — and close dots put their labels on top of each other.
- The axes, labels and dot colours are fixed literals; only the ground follows the DNA.

**Refuses:** fewer than 1 or more than 8 items; an item whose `x` or `y` is missing, not a finite number, or outside 0..1.

**Reference:** `remotion/src/shots/PositioningMatrix.tsx`
