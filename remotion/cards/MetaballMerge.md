# MetaballMerge

**Identity:** ten gradient-filled liquid blobs orbit in from a wide spread and fuse through an SVG goo filter into one soft, churning mass at centre, with a white wordmark and a spaced tagline settling on top.

**Use when:** a title or brand beat whose feel is merging — "many drops, one flow" — carried by one name and one line. **Not when:** the pieces need names or sizes (the blobs are anonymous; use MaterialHero or MadeOf), or the look should be metallic (use LiquidMetal).

**Motion core:** the blobs orbit and pulse for the whole clip (never still); they gather from the wide spread into one mass over 0.2–0.55 and stay merged after that; the title fades up and rises 16px over 0.5–0.74, the tagline fades in over 0.62–0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the white wordmark over the mass | a fixed 150px with no fit-to-width: one word reads as a logotype, a phrase wraps into stacked huge lines |
| `tagline` | the mono line under the title | white, widely tracked; a short phrase sits as a caption, a long one becomes a wide strip |
| `accent` | the blobs' gradient start (upper-left of each blob) | with `accent2` sets the liquid's colour; close hues give a single-colour fluid, far ones a two-tone sheen |
| `accent2` | the blobs' gradient end (lower-right) | as above |

**Known traps:**
- Omitting `title` / `tagline` prints the demo copy `Fluid` / `many drops, one flow`.
- The liquid does not read the DNA: without `accent` / `accent2` it is pink-to-violet on every film, and the ground keeps a fixed dark-violet glow at its centre — only the outer ground takes the DNA's `bg`.
- The title is never shrunk to fit; keep it to a word or two.

**Reference:** `remotion/src/shots/MetaballMerge.tsx`
