# LightTrails

**Identity:** on a dark stage, glowing streaks of light cross the frame while a neon gradient stroke, led by a bright head, traces a giant checkmark. The finished mark blooms white, and a short line fades in beneath it.

**Use when:** "done in one motion": completion or approval, a task finished in one go. **Not when:** the claim is anything other than done (the mark is always a checkmark), or the completion carries a figure (LiquidFill).

**Motion core:** three ambient streaks cross the frame for the whole clip. The check is traced over 0.16–0.72 (easing in and out), with the head riding the tip of the stroke. The bloom comes in over 0.72–0.92 and the label over 0.74–0.94.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the 46px bold line near the bottom, kept above the caption band | a short phrase lands under the mark. Not fitted: long copy wraps across the frame |

**Known traps:**
- The head used to be placed by a hand split of the path at 0.4 when the elbow is at 33.6% of its length, so it lagged the stroke by up to 61px. Both are now read by arc length; keep `pointAt` if the path is edited.
- The checkmark is a fixed 660×460px shape around the centre and doesn't scale with the frame, so on a 1080-wide frame it fills most of the width.
- **Dark world** (`@dark-world` in the shot). This is light painting — the mark is the glowing trail a travelling head leaves — so it takes the film's ground only while that ground is DARK and keeps its own night when the film's ground is light. A light film therefore gets one deliberately dark beat here, which the seam guard and the caption ink already handle from the measured `SHOT_LUMA`. Don't put it next to a light beat expecting a soft cut.
- The stroke and streak colours are fixed (cyan to violet, with blue, purple and teal streaks). The DNA reaches only the background, and only while that background is dark.
- Leaving `label` unset prints `done in one motion`.

**Reference:** `remotion/src/shots/LightTrails.tsx`
