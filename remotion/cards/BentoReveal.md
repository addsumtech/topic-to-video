# BentoReveal

**Identity:** a bento grid — one hero cell and one cell per item — pops in tile by tile and assembles into a product surface; once it lands, a slow focus walks the cells in reading order.

**Use when:** the beat names a product and a handful of its parts (1–6), and the claim is "these are all in one place". **Not when:** the parts must read as a sequence (use a list register), carry numbers (use a number register), or there are more than six.

**Motion core:** cells land one after another (each ~0.26 of the clip, staggered 0.1), with a slight overshoot; after the last lands, the focus walks one cell at a time (~1.1 s per cell) by tinting its edge and wash. Nothing moves as a whole frame.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the hero cell's big word | short (one product name) reads as a brand plate; a sentence fits but loses the plate feel |
| `hero` | the line under the title | a quiet tagline; long copy wraps and pushes the title up |
| `heroKicker` | the small spaced caps above the title | a category word; leaving the demo `DASHBOARD` prints a product-demo word on any film |
| `items` | one cell each: `label`, optional `icon`, optional `detail` | 1–2 items give big, calm cells; 5–6 make a dense dashboard. A cell with `icon` reads as a kind of thing; without one the label takes the room |

**Known traps:**
- The cells used to carry index-picked mini-charts (bars, gauge, sparkline) with invented heights — a film about anime characters shipped a sparkline under 路飞. Cells now draw only the icon the film names; never add a chart back without a prop that carries the data.
- The labels used to cycle to fill six cells, printing an item twice. The grid is laid out per count; do not pad `items` to six.
- Portrait has its own layouts (not a transpose) so the focus walk keeps reading order.

**Refuses:** 0 items or more than 6; an item with no label.

**Reference:** `remotion/src/shots/BentoReveal.tsx`
