# KineticManifesto

**Identity:** on a flood of saturated colour, one phrase at a time rushes toward the viewer: it arrives small and blurred, snaps sharp at reading size, then blows past, growing and blurring, as the next one arrives.

**Use when:** a manifesto or a set of values: 1–5 short declarative lines, one idea each, said loudly. **Not when:** the lines must be compared or read together (they never share the screen), there are more than five, or the beat is quiet.

**Motion core:** the phrases share 0.06–0.66 of the clip, overlapping by 0.12, so words fly through continuously. The last one starts at 0.66 and has a longer span. Each phrase approaches (the first 0.22 of its span: from 62% size, blur clearing, fading in), holds sharp until 0.62 of its span, then departs, scaling up to at most 1.9× (less if the zone can't hold it) while it blurs and fades. At the settled point (t ≈ 0.86) the last phrase is sharp; by the final frame it is already rushing past. A lone phrase arrives and holds almost to the end. Behind it all, the field's hue drifts and a light band moves across.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `phrases` | 1–5 lines, shown one after another | each line is fitted (up to 200px) to an 82%-wide column in the content zone. A short Latin line stays huge; a long line or a CJK line wraps and shrinks to fit. More lines give each one less time on screen |
| `hero` | the index of the phrase the film crowns | on a themed DNA the hero lands at full size and the others at 0.86×, all in the one readable ink. With no DNA every phrase is full size and the hero turns yellow. Left out, every phrase lands alike |

**Known traps:**
- The hero used to be hard-coded to the third phrase, and its ink was `accent2`, the colour of its own ground (measured at 1.00:1). Now every word uses `onAccent` and the emphasis is size, not a second hue.
- Phrases used to start 0.30 apart whatever the count, so a fourth arrived as a blur in the last frames and a fifth never appeared. The stagger is now laid out for the count, and more than five throws.
- A 200px Chinese line once wrapped past both edges and 692px into the caption band. The size is now fitted, and the rush-past scale is clamped so a tall block doesn't swell into the band on its way out.
- Leaving out `phrases` prints the demo `ONE PROMPT. / A HUNDRED EXPERTS. / YOUR AI TEAM.`, with the demo's own hero.
- On a light film the frame still reads dark — light-probe sheet Y=0.118, frame Y=0.131 — and that is the design, not a register keeping a night of its own: the whole ground is `accent`→`accent2`, and Y=0.13 is the exposure `light.tsx` deepens a chromatic ground to (`CHROMA_TARGET_Y`; its clay and olive grounds sit at Y=0.14 and 0.09). A light film gets one deliberately saturated beat in its own two hues, inked in `onAccent`.

**Refuses:** 0 or more than 5 phrases; an empty phrase; a `hero` that is not an integer index into `phrases`.

**Reference:** `remotion/src/shots/KineticManifesto.tsx`
