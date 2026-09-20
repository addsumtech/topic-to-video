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
| `accent` | the left pan's colour and the pivot ring | a prop, not the DNA's accent: the default is a fixed green whatever the film's palette |
| `accent2` | the right pan's colour | likewise a fixed blue unless passed |

**Known traps:**
- Every text prop defaults to one film's mission-vs-money copy. Omit any of them and that copy prints.
- Only the background follows the DNA. The beam, pan fills (`#0d1117`), sub-text, note and title ink are hard-coded for a dark ground, and the two accents are fixed unless passed, so on a light DNA the light ink loses its contrast.
- An SVG `<text>` cannot wrap. The note used to be bounded only vertically, and a Chinese note grew out of both frame edges; pan labels once ran 68px off each side because a Han glyph was counted as one Latin cell. Both are measured now, which means long copy gets smaller rather than wrapping.
- `equilibrium: unresolved` is the form's own readout and always prints, in English.

**Reference:** `remotion/src/shots/TensionScale.tsx`
