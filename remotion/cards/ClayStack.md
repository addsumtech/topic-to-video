# ClayStack

**Identity:** three matte clay blocks (wide, medium, narrow) drop from above one after another and settle into a little stack on a soft ground shadow. A fat clay checkmark pops onto the top, and a soft label fades in below.

**Use when:** the beat is a friendly "built up, piece by piece, and it's done" moment in a tactile, hand-made register. **Not when:** the pieces must be named or counted: there are always three unlabelled blocks, and the checkmark always says "done / approved".

**Motion core:** the blocks fall from 520px above and settle with an overshoot at 0.08–0.28, 0.24–0.44 and 0.40–0.60; the checkmark pops 0.60–0.82; the label fades 0.78–0.95. Then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the soft line under the stack | fixed 46px at line-height 1, centred, not fitted. A short phrase is the look, and long copy wraps into tightly stacked lines |

**Known traps:**
- `label` defaults to `built, piece by piece`, which prints on any film that omits it.
- The picture is fixed: three blocks and a checkmark, whatever the label says. Don't cast it when the beat's parts or their number matter, or when the work isn't finished.
- The label uses line-height 1 without the CJK leading lift other registers apply, so wrapped Chinese lines sit stroke on stroke.
- The block sizes and drop are fixed pixels; the clay colours are tinted and shaded from the DNA palette, so they still read as clay in the film's hues.

**Reference:** `remotion/src/shots/ClayStack.tsx`
