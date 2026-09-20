# CodeRain

**Identity:** full-frame Matrix-style rain. Columns of katakana, Latin and digit glyphs fall at different speeds, each with a bright glowing head and a fading trail. The centre darkens and a big title resolves, then a glowing mono tagline.

**Use when:** the beat is "inside the machine / meaning pulled from a data stream", resolved to a short title. **Not when:** a message should decode in place (`AsciiField`), or the frame needs calm: the rain runs through the caption band on purpose.

**Motion core:** the rain falls throughout; each column's head moves at its own hashed speed, and the glyphs re-roll about nine times over the clip. The title rises 14px and fades in 0.42–0.66; the tagline fades in 0.60–0.82.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big line at the centre | fixed 130px display, not fitted; a single word sits inside the darkened core, and longer copy wraps across the frame |
| `tagline` | the glowing mono line under it | fixed 30px with 0.2em tracking, in the accent |

**Known traps:**
- Omitting props prints the demo `Decoded` / `meaning from the stream`.
- The rain is marked `data-bleed`: glyphs falling through the frame edge and the caption band are the effect, so the subtitle is always read over moving glyphs.
- The darkened core is a fixed ellipse at the centre. A long title reaches past it onto the brightest rain, and the title isn't fitted.
- **Dark world** (`@dark-world` in the shot). The rain is phosphor: each column is a bright head with a trail that decays by falling OPACITY, which on paper is a glyph fading into the page. It takes the film's ground only while that ground is DARK and keeps its own night when the film's is light — and on that night it keeps its own green too, because a light film's accent was chosen to read on paper and can be as dark as its ink.
- The charset (including katakana) is fixed and reads as the Matrix; the head glyphs are fixed pale mint and the title is fixed near-white, while ground and trail follow the DNA of a dark-ground film.

**Reference:** `remotion/src/shots/CodeRain.tsx`
