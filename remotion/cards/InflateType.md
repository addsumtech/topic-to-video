# InflateType

**Identity:** a word's letters inflate one by one into glossy, puffy balloon letters, each in its own colour. Each one overshoots, settles, and then breathes with a soft squash, and a spaced tagline fades in underneath.

**Use when:** a playful, bold hero word: a friendly product name or a soft, dimensional title. **Not when:** a phrase longer than 16 characters (it refuses), a serious or technical beat, or springy drop-in letters (ElasticType).

**Motion core:** letter `i` starts at 0.08 + step·i and inflates with overshoot over 0.34 of the clip. The step is 0.09 for words up to five characters and closes for longer ones, so the last letter has always inflated by 0.84 (just before the settled frame at 0.86). Once settled it breathes (a squash-stretch of ±3%). The tagline fades up over 0.66–0.86. The volume is 2D shading (gradients, stacked shadows, a specular blob); there is no 3D camera.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the balloon letters, one row that never wraps, 1–16 characters | fitted to the width at up to 240px, so a longer word gets smaller letters (the specular highlight scales with them). Each letter takes the next palette tone (the DNA's palette when themed). A space becomes a 60px gap |
| `tagline` | the spaced mono caps line under the word | a short phrase sits under the word. Not fitted: long copy wraps |

**Known traps:**
- A balloon's lit top cannot be brighter than the paper under it: the gloss ramps from a LIFT of the letter's own tone on a light film and from white on a dark one. At a fixed white it ate the top two fifths of every letter of the hero word on paper.
- The timing was once a fixed 0.09 per letter, so an 11th letter was still a faint blob on the last frame and a 12th never appeared. It is laid out for the length now; long words set small (13 Han glyphs are about 60px on a 1080-wide portrait frame).
- At eight CJK glyphs the word was once cut off 450px on the left and 461px on the right at 1:1. The fit now allows for each letter's margin and the widest moment of the breath.
- The header used to call this "3D". It is 2D shading, so don't cast it where a 3D form is promised.
- Leaving the props unset prints the demo `PUFFY` / `soft, bold, dimensional`.

**Refuses:** a `word` with no visible character, or longer than 16 characters (spaces included).

**Reference:** `remotion/src/shots/InflateType.tsx`
