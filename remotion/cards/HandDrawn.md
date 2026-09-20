# HandDrawn

**Identity:** on warm grainy paper, rough ink boxes draw themselves one after another with sketched arrows between them; a red risograph copy is printed slightly off-register underneath, and each box's label fades in a little askew.

**Use when:** a short, human flow told warmly: two to five steps, "you → it → done". **Not when:** there are more than five steps (it refuses; use InOrder), or the beat is about a polished product surface.

**Motion core:** box `i` starts drawing at 0.08 + step·i and takes 0.2 of the clip. Its arrow starts 0.16 after the box, and its label fades in 0.14 after the box over 0.2. The step is 0.27 for two items and closes for more (0.21 for three, 0.105 for five), so the last label is always fully in by 0.84, just before the settled frame at 0.86. The boxes run as a full-size row when the frame is wide enough for the count; otherwise the chart takes whichever of a width-scaled row or a height-scaled column lets it be drawn larger.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one sketched box per label, in order, 1–5 | 2–3 labels form a full-size row on a 16:9 frame; four or five run across at 0.85 / 0.66 scale. A narrow frame switches to a column (full size at 9:16, about 0.41 scale for five at 1:1). Labels are 56px times that scale and are not fitted to their box, so long copy wraps inside it |

**Known traps:**
- The timing was once a fixed 0.27 per box, so even the demo's third label was only half in on the settled frame, a fourth box was half drawn when the clip ended and a fifth never started. It is laid out for the count now.
- A four- or five-step flow on a 16:9 frame used to fall to a column at about half size; it now runs across, scaled to the width.
- Fixed x positions once put the third box off a 1080-wide frame, and the first repair made the boxes overlap. The layout now switches to a column. That column once hung into the caption band on short frames, so it now scales down.
- Leaving out `items` prints the demo `You / WorkBuddy / Done ✓`.

**Refuses:** no `items`, more than five, or an item with an empty label.

**Reference:** `remotion/src/shots/HandDrawn.tsx`
