# HalftonePop

**Identity:** a pop-art comic page: a Ben-Day dot field, radial speed lines, and a jagged burst that pops with two lines of thick-outlined comic type; then a tilted caption box slams in at the bottom-left, all inside a heavy ink panel border.

**Use when:** a loud, fun highlight: a launch shout, a "ta-da", a playful reveal in a light-hearted film. **Not when:** the beat needs sober credibility or carries data, or wants a mascot instead of print texture (CartoonPop).

**Motion core:** the speed lines shoot out over 0.08–0.5. The burst pops with overshoot over 0.14–0.4 and keeps a slow spin. The caption box slams in with overshoot over 0.5–0.72, then everything holds. With no DNA it is the yellow and red pop page; on a themed DNA the paper goes dark and the ink turns light.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `burstTop` | the burst's first line | red type with a thick ink stroke, tilted. Latin copy stays at 150px whatever its length; only CJK copy is stepped down to fit |
| `burstBottom` | the burst's second line | the same as `burstTop`: one short shout per line ("SHIP" / "IT!") is the form |
| `lead` | the start of the caption sentence | the caption reads `lead` + `brand` + `tail` at 52px. Long copy wraps and the box grows upward |
| `brand` | the middle word of the caption, in the second colour | the name the box is about |
| `tail` | the end of the caption sentence | closes the sentence after the brand |

**Known traps:**
- `lead` used to be declared but never read, because the caption words were hard-coded. Every part is now a prop, but the defaults still print the demo `MEANWHILE… WorkBuddy delivers.` and `SHIP IT!`. A film that sets only some of the props gets demo words (including the demo brand) inside its own sentence.
- A long Latin burst is not fitted and runs out of the burst. The fit applies only to CJK, where a Chinese line at 150px once ran off every edge.

**Reference:** `remotion/src/shots/HalftonePop.tsx`
