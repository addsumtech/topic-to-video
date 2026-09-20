# SpeedLimit

**Identity:** a vertical bar rises inside a track toward one or two dashed ceilings, jams against the lowest one, turns warning red and shudders; then a verdict and the remaining lever appear to its left.

**Use when:** the claim is "you can't just go faster" — a quantity that is capped by one hard limit (and optionally a second one above it), and the answer is a different lever. **Not when:** there are three or more limits (a list or comparison register), or the quantity has real values to plot (a chart register).

**Motion core:** the title eases up from faint over the first quarter; the binding ceiling fades in 0.05–0.30, the second 0.10–0.35; the bar rises 0.12–0.62 and stops at the lowest ceiling, where it turns red and keeps shaking; the verdict fades in 0.66–0.86 and the `instead` line 0.72–0.90.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the title across the top | fixed-size, not fitted: one line reads as the question; long copy wraps; omitted, the demo `You can't just go faster` prints |
| `quantity` | the name under the track — what is being pushed | fitted to the frame width; empty draws nothing; omitted, the MRI demo `gradient speed` prints |
| `limits` | 1–2 ceilings, each a string or `{label, level?}` | without levels the ORDER is the claim: the first is drawn lower and binds, the second sits above it. With `level` (0 = foot, 1 = top) on every ceiling they sit where the film says and the lowest binds — a lower binding level stops the bar sooner. The binding ceiling is red with a heavier line, the other pink. Labels sit right of the track, sized down to fit the room. Omitted, the MRI demo ceilings print |
| `verdict` | the bold line left of the track once the bar jams | fitted to the room left of the track; empty draws nothing; omitted, the demo `blocked` prints |
| `instead` | the accent line under the verdict — the lever that is left | as `verdict`; omitted, the demo `→ skip k-space lines instead` prints |
| `accent` | the bar before it jams, the track edge and the `instead` line | plumbing — the DNA accent does NOT replace it |

**Known traps:**
- It was built for one MRI beat and every word was hardwired; a film about a battery or a road speed limit got an MRI slew-rate ceiling and was told to skip k-space lines. All five copy props now exist, but each still defaults to that MRI copy — set every one.
- The ceilings' heights were fixed, so the frame asserted which limit binds first; now the order (or the levels) you pass is that claim — make sure it is true.
- Label room was a literal sized for Inter; in a monospaced DNA face the labels ran off both edges. The room is measured with the DNA's own face now.
- The warning red, the second ceiling's pink, the track fill and the title colour are fixed literals; only the ground follows the DNA.

**Refuses:** zero or more than 2 ceilings; a ceiling with no label; `level` on some ceilings but not all; a level not strictly between 0.05 and 0.95; two levels less than 0.08 apart.

**Reference:** `remotion/src/shots/SpeedLimit.tsx`
