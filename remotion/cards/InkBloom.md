# InkBloom

**Identity:** a drop of ink spreads through water from the centre, soft clouds and feathery tendrils pushed about by turbulence. A big glowing title rises over the bloom, with a mono tagline after it.

**Use when:** something spreads, reaches or grows organically outward from one point. **Not when:** separate things merge (MetaballMerge), or the reach follows specific routes (MapRoutes).

**Motion core:** the spread runs over 0.04–0.7 (ease-out): the clouds grow, the tendrils lengthen and thin from thick strokes to fine ones, and the turbulence warps them more. The title rises over 0.5–0.74 and the tagline fades in over 0.62–0.84. Then the frame holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big word over the bloom, 132px | one short word is the form. Not fitted: several words wrap at the frame edges, and one long word runs past them |
| `tagline` | the spaced mono line under the title | a short phrase. Not fitted: long copy wraps |
| `ink` | the ink colour | used only with no DNA. On any themed film the DNA accent replaces it |

**Known traps:**
- `ink` is ignored whenever a DNA is present, and nothing warns about it.
- The title is a fixed 132px with no width fit, so a long single word is cut off by the frame.
- Leaving the props unset prints the demo `Diffuse` / `it spreads everywhere`.

**Reference:** `remotion/src/shots/InkBloom.tsx`
