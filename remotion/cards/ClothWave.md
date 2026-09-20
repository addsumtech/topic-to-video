# ClothWave

**Identity:** a silk flag of thirty horizontal strips in a two-colour gradient ripples on a travelling wave, its sheen shaded by the wave's slope. A big white wordmark rides the ripple letter by letter, and a spaced tagline fades in below.

**Use when:** the beat is a soft, tactile brand or mood moment: one short word (a name, a value) carried by motion. **Not when:** the title is more than a word or two (see traps), or the beat carries information.

**Motion core:** the cloth fades in while the wave's amplitude eases up, 0.04–0.50; the wave then travels continuously. The title fades in 0.40–0.66, each letter bobbing with the local wave; the tagline fades in 0.62–0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the wordmark, one span per character | fixed 150px, not fitted, in a row that never wraps. A short word rides the wave cleanly, and a long one runs past both edges |
| `tagline` | the spaced mono line near the bottom | fixed 30px with 0.2em tracking, not fitted |
| `accent` | the silk gradient's left colour | defaults to blue. It is NOT the DNA's accent, so pass it to put the cloth in the film's palette |
| `accent2` | the silk gradient's right colour | defaults to violet; same caveat |

**Known traps:**
- The cloth ignores the DNA's accents: a themed film keeps the blue→violet silk unless it passes `accent` / `accent2`.
- The title is split into one flex item per character, so a space becomes an empty item and collapses. Multi-word titles lose their word gaps.
- Omitting props prints the demo `Flow` / `soft power, in motion`.
- The cloth is a fixed 600px band with 160px side margins, and the wave under each letter is sampled at a fixed 96px pitch, not at the glyph's real position. Only the ground follows the DNA.

**Reference:** `remotion/src/shots/ClothWave.tsx`
