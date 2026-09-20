# ParticleForm

**Identity:** about 150 glowing dots fly in from a scatter across the frame and assemble into one giant checkmark, which swells in a single pulse, with a word fading in beneath it.

**Use when:** a payoff beat whose claim is "all those moving parts resolved into one finished result" — completion, success, done. **Not when:** the result is anything other than a success (the shape is always a checkmark), or the beat has content beyond one word.

**Motion core:** the dots travel from their scatter onto the tick over 0.1–0.72, eased and each with a small head-start difference; the whole tick pulses with an overshoot over 0.72–0.86; the label fades in as the assembly passes 70–90% of its way.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the word under the checkmark | a fixed 70px centred line with no fit: one word ("Done.", "完成") sits as a stamp; a phrase runs wide and may wrap |

**Known traps:**
- Omitting `label` prints the demo `Done.`.
- Only the dots follow the DNA (its `accent`); the dark ground and the pale label are fixed, so the frame stays dark on a light-DNA film.
- The label used to land inside the caption band at 1:1; the whole composition now slides up by exactly what does not fit, so on short frames the tick sits higher.

**Reference:** `remotion/src/shots/ParticleForm.tsx`
