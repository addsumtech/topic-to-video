# HoloFoil

**Identity:** a wordmark filled with shifting rainbow holographic foil rises into place; a white sheen slides across it, sparkle glints twinkle around it, and a widely spaced mono tagline fades in underneath.

**Use when:** a playful-luxe brand or product-name moment: collectible, special edition, "shiny new". **Not when:** a sober premium metal feel is wanted (LiquidChrome), or the text is longer than a name.

**Motion core:** the word rises and fades in over 0.06–0.5 (quick ease-out). The tagline fades in over 0.5–0.76. Throughout, the foil's hues rotate (about 220° across the clip), one sheen sweeps left to right, and 16 glints twinkle.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `word` | the foil wordmark | fitted to one line at up to 210px. A short name stays big; a long one gets smaller rather than wrapping |
| `tagline` | the spaced mono line under the word | fitted to one line at up to 32px with wide 0.42em tracking, so long copy shrinks quickly |

**Known traps:**
- Leaving the props unset prints the demo `WORKBUDDY` / `YOUR AI TEAM`.
- The word used to be a fixed 210px, which fit at 1920 wide but lost 107px off each edge at 1080. It is now fitted to the width.
- The foil HUES (pink, yellow, mint, blue, violet) are fixed, but their exposure is not. Foil is a surface, not a light, so this register draws on the film's ground — and all five hues sit near 68% lightness because they were picked against near-black, which put the word around 1.7-2.6:1 on paper. On a film that grounds on paper each one is walked along its own black-to-white axis until it clears the floor, hue untouched. Real foil is deep because its substrate is dark metal, and the sheen comes back with it: a white `screen` band over near-white foil is arithmetically nothing, over a deepened one it is the specular sweep.
- The tagline takes the film's `dim`. On a light ground the 2px white rim under the wordmark is dropped entirely — it is a lit edge, and on paper it erases the glyph's own boundary into the page. (A keyline in the film's ink was tried in its place and measured worse: a 2px band the same tone as the deepened foil, so the letter was then read against its own outline.) The offset drop shadow still grounds the word, and the glints are struck in the film's ink, since nothing can spark brighter than paper.
- The sheen turns over with the ground: against night it is a white `screen` band, on paper it multiplies a mid-tone instead, which is the same sweep at the foil's dark phase.

**Reference:** `remotion/src/shots/HoloFoil.tsx`
