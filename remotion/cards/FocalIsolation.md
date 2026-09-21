# FocalIsolation

**Identity:** a grid of items; the periphery blurs, dims and shrinks, a vignette closes in, and a warm spotlight lands on the one item the film names, which grows and rings in the accent with a label beside it.

**Use when:** one emphasis out of a field — "of all of these, this one". **Not when:** the beat is a punch-in to detail (CrashZoom), two readings of one subject (RackFocus), or there is no single item to isolate.

**Motion core:** cells appear staggered (0.03 apart, each over 0.2); the isolation runs 0.32–0.66 — the others recede through the shared focus lens while the focal cell scales up with a slight overshoot and the vignette deepens; the focal label fades in 0.50–0.70; then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | the field, up to three per row | 2–9; laid out for the count, a short last row centred under the rest; row height yields to the content zone. Item type is fixed (32px, 40px on the focal), balanced, not fitted |
| `focal` | the index of the isolated item | where the spotlight, ring and label land |
| `focalLabel` | the line in the gutter under the focal cell (over it on a bottom row) | fixed 44px; measured for width, centred on its own cell and kept inside the frame's margins |

**Known traps:**
- The spotlight used to fall on the FIFTH cell of every grid; a film with four items put the spotlight and its label on an empty cell. `focal` is required with the film's own items.
- Three rows were once reserved for any count, so four items sat high in the zone and more than nine ran into the caption band; the grid is laid out per count now.
- The label is placed as one line; a label long enough to wrap is not given the room.
- `focalLabel` defaults to the demo's 'Your files · on your machine'.
- The label was a literal near-white, so on a warm-white film the one sentence naming what was isolated drew white on paper — 43.7% of this register's marks under 3:1, connected hole 0.90% of the frame. It reads from `fg` now; the cards' own labels do not, because they sit on the field's own slate.
- The vignette and the focal card's contact shadow were tuned for a void. Sampled off the light probe render, the frame's corners came out RGB 42,44,49 and 60,62,66 where the page is 246,243,238 — the vignette that is a third-of-a-channel deepening on this register's own slate simply blacked out the edges of the paper. On a light ground the same gradient is painted at a quarter of its opacity (deepest corner 186,185,183) and the shadow is lightened; on a dark film and with no DNA neither is touched.
- The spotlight and the periphery's recede are untouched: the spotlight is a warm glow that a page cannot show and a reader loses nothing to, and the recede is the shared lens in `runtime/focus.ts` (blur, a 0.18 opacity floor, desaturation), so on a light ground the non-focal cells wash out to pale ghosts rather than dark ones — the lens's decision, not this register's.
- `INK_REFUSED` records the receded cards' labels at 1.07:1 on paper. That is the recede and not the ground: at the lens's 0.18 opacity floor the same label computes to 1.25:1 on this register's OWN slate, 1.22:1 on the ink probe's paper and 1.21:1 on gallery white. The label that must read is the focal one, at 13.08:1 on its own card.
- This register is deliberately NOT in `GROUND_FOLLOWS_MEASURED`, so a beat still cannot declare a `ground` for it; the repair above is for a film whose whole DNA is light (`dna_from_deck`), which reaches it without that table.

**Refuses:** fewer than 2 or more than 9 items; an empty item; no `focal` with the film's own items; a `focal` that is not an index into the items.

**Reference:** `remotion/src/shots/FocalIsolation.tsx`
