# TensionScale

**Identity:** a balance beam on a glowing fulcrum, with a labelled pan hanging from each arm, teeters gently for the whole clip and never settles. Neither side wins, and a readout under the pivot says `equilibrium: unresolved`.

**Use when:** the thesis is a sustained tension between two forces that is never resolved (mission vs money, speed vs safety, privacy vs convenience), so the frame has to hold the tension rather than break it. **Not when:** one side wins or the beat ends in a verdict (use `VersusSplit`, which crowns a winner), or there are more than two forces.

**Motion core:** the title fades up over the first quarter and the beam and pans fade in by 0.25. The teeter's amplitude grows over the first third, and the beam then rocks about 1.15 times across the clip (at most ~0.095 rad), swelling toward the middle. The pivot knot pulses in step with the rocking. The note fades in over 0.15–0.48. Nothing ever comes to rest.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the headline across the top | the library's shared title style: centred, 40px, light ink, and a long title wraps. Leaving the demo in place prints `The tension that never resolves` |
| `leftLabel` | the left pan's name, in bold mono | fitted to the pan (at most 22px), so a long label shrinks. The pan box grows to the label's measured ink, up to 540px (less in portrait). Leaving the demo in place prints `MISSION` |
| `leftSub` | the smaller line under the left label | fitted the same way (at most 16px). The demo is `benefit all of humanity` |
| `rightLabel` | the right pan's name | as `leftLabel`. The demo is `SCALE - MONEY - POWER` |
| `rightSub` | the line under the right label | as `leftSub`. The demo is `the cost of the race` |
| `note` | one mono line above the caption band | an SVG line that cannot wrap, so a long note shrinks to fit 90% of the width (at most 20px) and a very long one becomes small. The demo is `neither side wins - that IS the story` |
| `accent` | the left pan's colour and the pivot ring | what you pass wins; unset it is the film's DNA accent, and only an un-themed film gets the original green |
| `accent2` | the right pan's colour | likewise: passed, then the DNA's accent2, then the original blue |

**Known traps:**
- Every text prop defaults to one film's mission-vs-money copy. Omit any of them and that copy prints.
- The beam is the one object this register has, and it was a near-white literal: on a paper ground it was drawn white on white (measured 1.07:1) and the frame became two labelled cards, a triangle and no balance between them. The beam, the pivot knot and the title now take the film's `fg`, the pans its `surface`, and the sub-lines, readout and note its `dim`.
- An SVG `<text>` cannot wrap. The note used to be bounded only vertically, and a Chinese note grew out of both frame edges; pan labels once ran 68px off each side because a Han glyph was counted as one Latin cell. Both are measured now, which means long copy gets smaller rather than wrapping.
- `equilibrium: unresolved` is the form's own readout and always prints, in English.

**Reference:** `remotion/src/shots/TensionScale.tsx`
