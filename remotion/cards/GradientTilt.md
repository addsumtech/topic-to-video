# GradientTilt

**Identity:** a row of bars stands at one even height under a flat line (a uniform field); then the line tilts into a ramp and the bars follow it, short on the left ("low freq") to tall on the right ("high freq"), over the coil relation `B = B₀ + G·x`.

**Use when:** showing how a gradient makes position readable as frequency (MRI spatial encoding), or any uniform field made to carry position. **Not when:** showing columns precessing at their own rates during readout (FrequencyEncode), a stepped phase encode (PhaseEncodeStep), or any bar chart — the bar heights are not data.

**Motion core:** the title fades up over the first quarter. The coil formula fades in over 0.05–0.3. The tilt runs 0.18–0.72: "uniform field" fades out as "low freq" / "high freq" fade in. After that the frame holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the 40px title at the top | a short claim sits on one line. Long copy wraps downward (not fitted) |
| `cols` | how many bars span the ramp (default 11) | few bars read as chunky steps, many as a smooth ramp of thin bars. Each bar is its column minus 6px |
| `accent` | every other bar, and the "low freq" label | the colour of one half of the alternating bars |
| `accent2` | the other bars, and the "high freq" label | the colour of the other half |

**Known traps:**
- The labels on the diagram ("uniform field", "low freq", "high freq", "position →", the coil formula) are fixed English text and print on every film, whatever its language.
- `cols` below 2 breaks the ramp: each bar's position is `i / (cols - 1)`, so a single bar divides by zero.
- The bar heights are fixed (uniform at half height, then a ramp from 0.15 to 0.95), so the bars cannot show a measured field.
- The ink is the film's: the field line and the relation take the DNA's `fg`, the axis words take `dim`, the bars' zero line takes `line`, and `accent`/`accent2` fall back to the film's two accents before their own cyan and violet. A prop still wins, and with no DNA every original literal prints as before. Until this was done the field line vanished on a light-ground film (measured median 1.36:1).

**Reference:** `remotion/src/shots/GradientTilt.tsx`
