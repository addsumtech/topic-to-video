# CinematicTitle

**Identity:** a film-title card. In a dark room glow with drifting dust motes, a widely spaced mono kicker, a big display title and a spaced tagline rise up out of shadow under a slow push-in. With no DNA, an anamorphic flare streak also sweeps across and 2.39:1 letterbox bars frame the shot.

**Use when:** the beat opens or names something with gravity: a film's title card, a chapter title, a product's name, delivered slowly and mood-first. **Not when:** the beat carries data or a list, or needs speed.

**Motion core:** the background push runs 1.06→1.14 over the whole clip; the title rises 0.16–0.62 (expo); the kicker fades 0.24–0.50; the tagline 0.55–0.82; with no DNA, the flare sweeps left to right 0.20–0.85, rising and then falling, and the motes brighten with it.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | the small spaced line above the title | fixed 26px mono, uppercased, 0.5em tracking, not fitted; a DNA with `prompt` prefixes `▸ ` |
| `title` | the title | measured in the real display face and fitted to 86% of the width on one line, capped at 176px and 13% of the width, so a short name is large and a long title steps down. A DNA with `cursor` adds a caret after it |
| `tagline` | the spaced line under the title | fixed 30px mono, uppercased, 0.36em tracking, not fitted |

**Known traps:**
- Omitting props prints the demo `A NEW KIND OF TEAMMATE` / `WorkBuddy` / `your ai team · on your machine`.
- The title's width used to be guessed as `len × 0.52`, which underestimates high-contrast faces (Bodoni Moda). Long titles wrapped and crowded the tagline at 9:16, so the string is now measured.
- The flare and letterbox are skipped under ANY DNA (`!dna`), not only a terminal one, so a themed film gets neither.
- The kicker and tagline are uppercased and widely tracked with no fit, so long copy wraps into wide, spaced blocks.

**Reference:** `remotion/src/shots/CinematicTitle.tsx`
