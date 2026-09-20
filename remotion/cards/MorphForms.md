# MorphForms

**Identity:** a spinning cloud of 260 depth-shaded points morphs sphere → cube → torus → sphere, the near points bright in the accent and the far ones dim in the second accent, with a title (and optional tagline) at the bottom.

**Use when:** an abstract "one idea, many shapes" or transformation beat carried by a title alone. **Not when:** the shapes should be the film's own named forms (the three primitives are fixed — use LiquidMorph, which takes `forms`), or the beat has content beyond a title line.

**Motion core:** sphere to cube over 0.08–0.36, cube to torus over 0.38–0.64, torus back to sphere over 0.66–0.92, each eased in and out; the whole cloud rotates continuously (about 0.7 of a turn over the clip) on a fixed tilt, so it never holds still; the title and tagline fade up and rise 14px over 0.5–0.74.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the centred title at the bottom | a fixed 76px, centred; a short claim is one line, a long one wraps upward into the cloud's space |
| `tagline` | an optional mono line under the title | empty (the default) draws nothing; a short phrase adds a spaced caption |

**Known traps:**
- Omitting `title` prints the demo copy "One idea, many shapes".
- The cloud is drawn at a fixed scale around the frame's centre and is not fitted to the room above the title (the fix MoleculeBallStick records for the same layout), so its lower points can pass behind the title, more so on short frames.
- The colours are the DNA's `accent` (near side) and `accent2` (far side); there is no prop to set them per beat. On a film that grounds on PAPER both are walked along their own black-to-white axis until they clear the graphics floor (exposure only, hue kept) — a light film's accents were chosen for dark type on paper and would otherwise be a cloud of pastels on it.
- The title takes the film's ink and the kicker its `dim`; the lit core of the ground and the title's separation shadow follow the film's own paper when the film grounds on paper, instead of painting a near-black pool in the middle of a light page.

**Reference:** `remotion/src/shots/MorphForms.tsx`
