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
- The foil colours (pink, yellow, mint, blue, violet) are fixed. The DNA reaches only the background.

**Reference:** `remotion/src/shots/HoloFoil.tsx`
