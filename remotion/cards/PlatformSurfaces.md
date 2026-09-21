# PlatformSurfaces

**Identity:** a coloured hero panel naming one platform pops in, then a bento of product tiles pops in beside it (below it in portrait), each tile drawing a small pictogram that means its own surface — chat bubbles, API braces, a film frame, code lines, a cursor on a window.

**Use when:** the claim is "one platform, many surfaces" — a product family or one system exposed through 1–6 distinct front ends, each of which can be named and, ideally, pictured. **Not when:** the parts are features inside one screen (use `PointerTour`), they plug into a shared standard (use `PortRail`), or they are ordered steps (use a list or flow register).

**Motion core:** the hero panel scales up with a slight overshoot 0.04–0.30; tiles follow one at a time, tile *i* popping over 0.28 of the clip from 0.16 + 0.12·*i*; each tile's glyph draws itself in (dashes, bars, play mark, cursor) just behind its tile. Once the last tile lands the frame holds still.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `markLabel` | the small spaced mono caps at the top of the hero panel | a category word; omitted, the demo `THE PLATFORM` prints |
| `title` | the hero panel's headline — drawn once | fixed large type, balanced wrap: a short name reads as a brand plate, a sentence wraps to several lines and fills the panel; omitted, the demo `One platform, not one app` prints |
| `subtitle` | the line under the headline | a quiet one-liner; long copy wraps and pushes the block up; omitted, a demo line prints |
| `tiles` | one tile each: `label`, optional `note`, optional `glyph` | laid out two to a row (a single tile takes the whole row; an odd last tile sits in the left half of its row): 1–2 tiles give big, calm cells, 5–6 give short, dense rows. `glyph` is one of `chat`, `api`, `video`, `code`, `cursor`, `node`; without one the tile draws no picture and its label sits at the bottom. Omitted, four demo tiles naming real products (API / Sora / Codex / Operator) print |
| `accent` | the hero panel's gradient and the first tile's tone (overridden by the DNA accent) | plumbing |
| `accent2` | the second tile's tone (overridden by the DNA's second accent) | plumbing |

**Known traps:**
- `title` used to be drawn twice (frame header and hero headline). It is now the hero headline only — don't add a header back.
- A tile without a glyph used to get a generic `node` pictogram; now it gets no picture, and an unknown glyph name throws. `node` is only for a surface that really is "a node".
- Omitting `tiles`, `title` or `markLabel` prints the demo copy about someone else's product line.
- Type is fixed-size, not fitted: a long label or note wraps, and in the shorter rows of 5–6 tiles there is little room under the glyph for it.
- The tile's fill had a TRANSLUCENT top stop, so on a light film it composited to a mid grey over the paper — and the glyph, the one thing this register exists to draw, sits in exactly that half of the tile. Measured on a light film: 32.6% of the ink under 3:1, and the mark render is four glyphs and nothing else. On a light ground the tile is now the film's `surface`, its label the film's ink and its note the film's metadata ink.
- Tiles 3–5 no longer use three fixed tones picked for a near-black tile: every tone is the film's palette, exposed for the ground it will be drawn on. The hero panel's own gradient (the accent into a fixed deep green) and its white type are unchanged — the panel is opaque and dark at either exposure, and the gate flagged only two slivers of its edge, read against its own drop shadow.
- The hero and tile drop shadows are scaled to the ground: at their dark-film weight they are a grey field in every gutter on paper.

**Refuses:** fewer than 1 or more than 6 tiles; a tile with no label; a glyph name outside the list above.

**Reference:** `remotion/src/shots/PlatformSurfaces.tsx`
