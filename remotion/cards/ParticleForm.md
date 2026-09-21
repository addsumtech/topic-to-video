# ParticleForm

**Identity:** about 150 dots fly in from a scatter across the frame and assemble into one giant checkmark, which swells in a single pulse, with a word fading in beneath it. On the film's own ground, in the film's accent.

**Use when:** a payoff beat whose claim is "all those moving parts resolved into one finished result" — completion, success, done. **Not when:** the result is anything other than a success (the shape is always a checkmark), or the beat has content beyond one word.

**Motion core:** the dots travel from their scatter onto the tick over 0.1–0.72, eased and each with a small head-start difference; the whole tick pulses with an overshoot over 0.72–0.86; the label fades in as the assembly passes 70–90% of its way.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the word under the checkmark | a fixed 70px centred line with no fit: one word ("Done.", "完成") sits as a stamp; a phrase runs wide and may wrap |

**Known traps:**
- Omitting `label` prints the demo `Done.`.
- The dark ground and the pale label used to be fixed, so on a light film the frame stayed dark and the film's own accent was drawn on a night nobody asked for — measured under the light probe at frame Y=0.005, with 25% of its marks under 3:1. What this register measures is position, not brightness, so it follows the film: the ground is `bgGrad`/`bg`, the label `fg`, and the every-seventh sparkle is the accent stepped 0.4 toward `fg` instead of a second pale blue.
- The label used to land inside the caption band at 1:1; the whole composition now slides up by exactly what does not fit, so on short frames the tick sits higher.

**Reference:** `remotion/src/shots/ParticleForm.tsx`
