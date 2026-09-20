# KaleidoMandala

**Identity:** a 12-fold mirrored kaleidoscope of petals blooms out from the centre with overshoot, turning slowly as its colours cycle; a big title and a tagline settle over a darkened centre.

**Use when:** order out of many, or an ornate ambient backdrop for a title. **Not when:** the beat has content to show (the mandala carries no data), and never as k-space (KSpaceReal exists because a decorative mandala was standing in for the real thing).

**Motion core:** the bloom runs over 0.06–0.5 (overshoot ease). The whole figure turns 26° across the clip, and the petals wobble and shift colour throughout. The title rises over 0.52–0.76 and the tagline over 0.64–0.86.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the 128px title at the centre | one short word is the form. Not fitted: several words wrap at the frame edges, and one long word runs past them |
| `tagline` | the spaced mono line under the title | a short phrase. Not fitted: long copy wraps |
| `accent` | one petal colour, and one end of the cycling blend | together with `accent2`, sets the whole mandala's colour |
| `accent2` | the other petal colour | the other end of the cycling blend |

**Known traps:**
- The petal colours come only from `accent` / `accent2` (pink and cyan by default). The DNA reaches only the background, so a themed film gets pink and cyan unless it passes both.
- The centre wash is a fixed dark purple and the title is fixed white, whatever the DNA.
- Leaving the props unset prints the demo `Symmetry` / `order out of many`.

**Reference:** `remotion/src/shots/KaleidoMandala.tsx`
