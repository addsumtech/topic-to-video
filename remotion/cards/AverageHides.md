# AverageHides

**Identity:** an axis scaled to the far value. Most cases pile up around the number everyone quotes; a thin scatter strings out past it; the one nobody quotes sits far to the right, and a measured bar under the axis draws the distance between the two.

**Use when:** the beat is that a summary figure is not the experience — the median request, the average wait, the typical case — and the part it hides is the point. **Not when:** the beat is one headline number said plainly (`EdStat`, `TermCounter` — and those are the instrument this register exists to answer); not when two MEASURES are being compared for which separates two populations (`OverlapSeparation`, whose `spread` belongs to the populations, not to one quantity).

**Why the library could not say it:** asked of the PROPS rather than the prose — the reliable question, per this repo's own peer study — the library accepts a `label`, sometimes a `value`, and a handful of flags. There is no field anywhere for a quantity's spread. A film could say "it takes 200ms" and could compare two metrics, and could not say the thing that is true of every system it might describe.

**Motion core:** the axis draws 0.04–0.30, the crowd settles 0.20–0.52 (per-mark hash stagger, so it arrives as texture and not as an event), the quoted figure lands 0.40–0.58, the far one 0.60–0.80 with an `easeOutBack` drop, and the gap bar grows from the quoted mark to the far one 0.74–0.90. The order is the argument: you are shown the number, then where it does not reach.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `typical` | the number everyone quotes — `{label, value}` | `label` says what it MEANS to someone, which is the half a figure alone never carries |
| `tail` | the one it hides — `{label, value, share}` | `share` is the film's own words ("1 in 20"), never a fraction this computes |
| `unit` | what the axis measures, in the film's words | set beside both figures at a smaller size |
| `kicker` | the spaced label over the axis | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the axis, in the film's voice | where to say what the DISTANCE means, which the frame draws and does not name |

**Known traps:**
- **The geometry is not tuned; it is the ratio.** The axis is scaled to the far value, so a tail twenty times the typical value collapses the pile into a mark at the left and strands the tail at the right. That is the true picture and exactly what a bar chart of the average hides — and a film whose tail is close to its typical case gets a frame that says so instead.
- **A tail under `MIN_TAIL_RATIO` (1.5×) is refused.** That close, the quoted number IS a fair summary, and this frame would manufacture an alarm the beat did not make — a picture arguing something its narration did not, which is the worst outcome this repo recognises.
- **There is deliberately no share threshold.** `share` is the film's words because a fraction this register computed would be a statistic it was never given. An early draft exported a `MAX_TAIL_SHARE` that nothing could compare against — a header promising a rule the code does not have.
- Each figure is centred on its own tick and clamped **by its centre**, never by its box's left edge: clamping the edge slides the box while its text stays centred inside it, so the number drifts off the tick it names — measured at ~100px on the first render, with the far figure pointing at empty axis.
- The figures ride ABOVE the crowd. The first render put the quoted number inside the pile, printed on top of the cases it summarises, and neither read.
- **The gap is a REGION, not a rule.** This repo's peer study records that mechanism registers measured a median 2.4% ink because "relations are conventionally drawn as boxes and arrows, and a line has no area — the relation had to become a REGION". The span between the two numbers IS the claim, so it is given area, and the eye reads its SIZE rather than tracing a rule. Measured: light 0.004 → 0.010, past the library's light cut.
- **Measured thin, and recorded rather than tuned.** 1.9% ink and 0.0001 motion — the thinnest fifth on ink and under the motion floor. An axis, two figures and a crowd of small marks is what this register IS; the emptiness on either side of the band is the distance the beat is about. Cast it where the distance is the point, and intercut it with something dense.
- The pile is `@decor:` texture. It says "many cases", which is all a cloud of unlabelled marks can honestly say; this register is told no case count, no mean and no distribution shape, and draws none of them.

**Refuses:** a missing or non-positive `value` on either point; a missing `label` on either; a tail closer than `MIN_TAIL_RATIO` times the typical value.

**Reference:** `remotion/src/shots/AverageHides.tsx`
