# LiquidChrome

**Identity:** a wordmark in flowing liquid metal (reflected horizon bands drifting through the letters, red and cyan fringes at the edges (the DNA's two accents when themed), a highlight sweeping across) rises onto a dark stage above a blurred mirror reflection, with a widely spaced caps tagline below.

**Use when:** a premium hero title: a product or brand name that should feel expensive and editorial. **Not when:** the tone is playful (HoloFoil, InflateType), or the text is longer than a name.

**Motion core:** the word is uncovered upward from just above its midline (the lower half shows first) over 0.05–0.5, and it eases up 30px into place over 0.05–0.6, with its reflection fading in alongside. The chrome bands flow for the whole clip, and one highlight sweeps left to right. The tagline fades in over 0.55–0.8.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the chrome wordmark | fitted to one line at up to 260px. A short name stays monumental; a long one gets small rather than wrapping. On a themed DNA the metal bands are drawn in the accent's hue; with no DNA they are grey metal |
| `tagline` | the spaced mono caps line, a fixed 190px below the word's centre | 30px with 0.42em tracking. Not fitted: long copy wraps |

**Known traps:**
- The word used to be a fixed 260px and lost about 95px off each edge at 9:16. It is now fitted to the width.
- The darkening gradient at the bottom of the frame is a fixed near-black whatever the DNA, so on a light DNA the bottom of the frame goes dark. The tagline colour is fixed too.
- Leaving the props unset prints the demo `DELIVERED` / `your ai team · on your machine`.

**Reference:** `remotion/src/shots/LiquidChrome.tsx`
