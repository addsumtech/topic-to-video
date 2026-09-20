# MadeOf

**Identity:** the whole content zone splits edge to edge into rectangles, one per part, each region's AREA its share, largest first — the parts grow out of the whole one by one, each printing its figure and label, while the name of the whole sits above.

**Use when:** the claim is structural — "this whole is made of these parts, in these proportions, and that one is the big one" — with 2–7 parts and a real, sourced share for each. **Not when:** there is only one figure (use a single-figure register), the parts have no meaningful sizes (area that means nothing cannot be drawn), or there are more than seven.

**Motion core:** kicker and whole fade in over 0.04–0.24; the regions then arrive largest first, each fading and scaling up from 0.94 over 0.22 of the clip, staggered 0.09 apart from 0.22; the top-right note fades in over 0.72–0.9; the frame then holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | small spaced mono line, top left | a topic tag in the dim colour; empty draws nothing |
| `whole` | the bold name of the thing being taken apart, under the kicker | a short noun reads as the frame's title; it has no width limit, so a long one runs along the top band |
| `parts` | one region each: `label`, `share` (a number), optional `note` | 2 parts give two big blocks; 7 a dense mosaic. Area is share ÷ total, laid out slice-and-dice along the long side. Type is sized to each region, and a region too small (shorter side under 0.14 of the frame's short side) drops its figure and note and keeps only the label |
| `note` | one line at the top right, opposite the title | a short source or caveat line in the dim colour, capped at about a third of the width and balanced across lines |
| `unit` | the suffix printed after every figure | `%`, `GB`, `人` … appended as written; omitted in a film, the figures print bare |

**Known traps:**
- The figure printed is the share AS WRITTEN plus `unit`, never a computed percentage — it used to print `share / total × 100` with the film's unit, so shares [4, 3] in GB came out "57GB" and "43GB". If you want percentages, write percentages.
- `unit` does not default to `%` in a film; only the standalone preview's demo parts ("the biggest piece", "the second" …) print with `%`, and omitting `parts` prints those demo parts.
- A share of exactly 0 is left out silently (a zero-area region is not a part); every other bad share throws.
- The note used to sit under the partition inside the caption band; it now rides the title band top right — a long `whole` beside a `note` shares that band with it.

**Refuses:** `parts` not an array or more than 7; a part with no label; a share that is not one number ≥ 0; fewer than 2 parts with a share above 0.

**Reference:** `remotion/src/shots/MadeOf.tsx`
