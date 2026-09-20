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

**Refuses:** fewer than 2 or more than 9 items; an empty item; no `focal` with the film's own items; a `focal` that is not an index into the items.

**Reference:** `remotion/src/shots/FocalIsolation.tsx`
