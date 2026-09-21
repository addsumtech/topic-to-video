# LowPolyForm

**Identity:** a jittered triangle mesh assembles from the centre outward — each facet popping up from its own centroid, graded across a two-colour duotone — and a wordmark with a spaced tagline settles over a dark vignette at centre.

**Use when:** a title or brand beat that should feel crystalline and generative — "many facets, one form" — carried by one name and one line. **Not when:** the facets need names or data (they are anonymous decoration); for a whole broken into its named parts use MadeOf.

**Motion core:** facets reveal by distance from centre — each starts at 0.04 + 0.45 × its distance and pops with a slight overshoot over 0.26 of the clip, brightening as it lands, so the centre fills first and the corners last; the title rises in over 0.52–0.76, the tagline over 0.64–0.86; after ~0.9 the mesh holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the white wordmark at centre | a fixed 138px with no fit-to-width: one word reads as a logotype, a phrase wraps into stacked huge lines |
| `tagline` | the mono line under the title | a short phrase sits as a spaced caption; the letter-spacing stretches a long one wide |
| `accent` | one end of the facet duotone (left / lower side of the mesh) | a colour close to `accent2` gives a near-flat crystal; a far one a vivid diagonal sweep. Named here it is used exactly as given; left out, it is the film's own `accent` |
| `accent2` | the other end of the duotone (right / upper side) | as above — the two mix per facet across the frame |

**Known traps:**
- Omitting `title` / `tagline` prints the demo copy `Faceted` / `many facets, one form`.
- The duotone used to ignore the DNA — the mesh was always the default blue-to-pink whatever the film's palette — and the mesh covers the ground, which was the only thing that did follow it. On a light film that repainted the paper as a mid-dark slab with a grey smudge over the middle: measured under the light probe at sheet Y=0.328 / frame Y=0.282. Without `accent` / `accent2` the facets are now the film's two hues; on a light film they are carried half way back to the film's ground, so the crystal stays coloured and the frame stays light.
- The pool behind the type and both type blooms were a fixed near-black and `#000`. They are the film's `bg` now, and the type is `fg` over it (with the tagline a step toward `dim`) — a `#000` bloom under dark type on paper is mud, not depth.

**Reference:** `remotion/src/shots/LowPolyForm.tsx`
