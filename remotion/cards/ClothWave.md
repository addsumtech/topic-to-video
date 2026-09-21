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
- The cloth is a fixed 600px band with 160px side margins, and the wave under each letter is sampled at a fixed 96px pitch, not at the glyph's real position.
- The middle of the ground used to be a grey blob on a light film: the radial's inner stop was a literal near-black laid over the film's own `bg`, so the paper had a dark bloom across it. It is derived from the film's accent now. The sheen's ceiling goes with it — `brightness()` past 1 walks the silk toward white, which is a highlight on night and a hole in paper, and the flag's lit top edge against the ground was the register's whole reported hole (0.36% of the frame, `ink_contrast_qa`). On a light film the sheen modulates DOWN from the silk's own colour instead of up past it.
- The tagline is pinned to the caption band while the cloth's hem swings through that same row, so part of the line is always on silk and part on the ground — opposite polarities, which no flat ink serves. It takes the ground's ink and carries the GROUND'S OWN COLOUR as a 3px stroke: invisible where the line is on the ground, and what carves it out of the silk where it is not. Before that, the half of the line that had slipped off the hem was a pale blue-white lying on the ground, flagged end to end.
- The wordmark keeps its white while white clears the large-text floor against both ends of the silk (3.72:1 and 3.86:1 on the register's own two), and is re-picked from the film's two inks only when a film hands it a pale silk of its own.

**Reference:** `remotion/src/shots/ClothWave.tsx`
