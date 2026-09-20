# LowPolyForm

**Identity:** a jittered triangle mesh assembles from the centre outward — each facet popping up from its own centroid, graded across a two-colour duotone — and a wordmark with a spaced tagline settles over a dark vignette at centre.

**Use when:** a title or brand beat that should feel crystalline and generative — "many facets, one form" — carried by one name and one line. **Not when:** the facets need names or data (they are anonymous decoration); for a whole broken into its named parts use MadeOf.

**Motion core:** facets reveal by distance from centre — each starts at 0.04 + 0.45 × its distance and pops with a slight overshoot over 0.26 of the clip, brightening as it lands, so the centre fills first and the corners last; the title rises in over 0.52–0.76, the tagline over 0.64–0.86; after ~0.9 the mesh holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the white wordmark at centre | a fixed 138px with no fit-to-width: one word reads as a logotype, a phrase wraps into stacked huge lines |
| `tagline` | the mono line under the title | a short phrase sits as a spaced caption; the letter-spacing stretches a long one wide |
| `accent` | one end of the facet duotone (left / lower side of the mesh) | a colour close to `accent2` gives a near-flat crystal; a far one a vivid diagonal sweep |
| `accent2` | the other end of the duotone (right / upper side) | as above — the two mix per facet across the frame |

**Known traps:**
- Omitting `title` / `tagline` prints the demo copy `Faceted` / `many facets, one form`.
- The duotone does not read the DNA: without `accent` / `accent2` the mesh is always the default blue-to-pink, whatever the film's palette. Only the ground follows the DNA.

**Reference:** `remotion/src/shots/LowPolyForm.tsx`
