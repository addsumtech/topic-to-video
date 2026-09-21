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
- It is a declared `@dark-world`: neon is emitted light, so on a light film it keeps its own night rather than printing a sign in dark ink on white. On a dark film it now takes the film's ground (and its `bgGrad` treatment) instead of its own purple sky — the sun's scanline gaps are the sky, so they follow it too, or a deep-green film would have striped the sun in plum.
- Under the light probe it measured sheet Y=0.005 with 7% of its marks under 3:1: the film's accents, chosen to read on paper, were being drawn on this sky as dark tubes. On its own night the neon is now the register's own magenta/cyan; on the film's ground it is `accent` (floor lines, sun's lower stop, wordmark backlight, horizon glow) and `accent2` (converging lines, wordmark stroke, tagline).
- The stars stay white and the sun stays yellow→orange: those are what a star and a setting sun ARE, not this film's ink.
- Before the fit, a long title ran off the frame and a long tagline wrapped onto the sun at 1:1; the fit fixed that, so very long copy now just gets small — keep both short.

**Reference:** `remotion/src/shots/NeonGrid.tsx`
