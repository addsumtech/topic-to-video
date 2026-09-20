# NeonGrid

**Identity:** synthwave — a neon perspective floor scrolls toward a striped retro sun on the horizon under a twinkling starfield, while a chrome-neon wordmark and a widely tracked tagline rise above the horizon.

**Use when:** a high-energy, retro-futuristic title beat carried by one name and one line. **Not when:** the beat carries content (parts, steps, figures), or the film is calm or serious — the sky and sun are unmistakably 1980s.

**Motion core:** the floor's horizontal lines scroll toward the viewer and the stars twinkle for the whole clip; the wordmark fades in and rises 30px over 0.12–0.5 with a quick-out settle; the tagline fades in over 0.45–0.72.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the chrome-neon wordmark above the sun | measured in the real face and fitted to the frame width minus 120px, capped at 168px: a short word keeps the full neon size, a long one shrinks to stay on the frame |
| `tagline` | the cyan line under the wordmark | same fit, capped at 30px, with 0.5em tracking — short copy spreads wide as a sign; long copy shrinks rather than wrapping onto the sun |

**Known traps:**
- Omitting `title` / `tagline` prints a product demo: `WORKBUDDY` / `ON YOUR MACHINE`.
- The sky gradient and the sun are fixed purple/orange and do not read the DNA's ground; the DNA's `accent` recolours only the floor's scrolling lines and `accent2` the converging lines, the wordmark stroke and the tagline.
- Before the fit, a long title ran off the frame and a long tagline wrapped onto the sun at 1:1; the fit fixed that, so very long copy now just gets small — keep both short.

**Reference:** `remotion/src/shots/NeonGrid.tsx`
