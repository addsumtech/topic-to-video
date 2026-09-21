# InfiniteCanvas

**Identity:** a whiteboard canvas (dot grid, a central hub card, pastel sticky notes on a ring around it). We see it wide, then the camera pushes in to the hub while connectors grow out to each sticky and the stickies pop onto the board.

**Use when:** going from the big picture to the detail: one centre with the pieces mapped around it, and the camera moving in on the centre. **Not when:** the connections between items are the claim (KnowledgeGraph draws links the film gives; here every sticky connects only to the hub), or the items have an order (InOrder).

**Motion core:** the zoom goes from 0.5× to 1.35× over 0.12–0.90, easing in and out, and ends centred on the hub. Stickies pop in with overshoot and connectors grow from the hub, both staggered by index and tied to the zoom's progress. The hub is on the board from the first frame. By the end only the hub and the nearest stickies are in frame.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `hub` | the text on the central card (56px bold, 420×240 card) | a short project name fills the card. Long copy wraps inside it |
| `items` | one sticky per label, evenly spaced on a ring around the hub | colours cycle through six pastels. Labels are 40px in 300×180 stickies and are not fitted. Nothing caps the count: all stickies sit on one ring, so a long list packs them edge to edge |

**Known traps:**
- Leaving the props unset prints the demo board: `Q3 Board Deck` with eight board-deck stickies (`Market scan`, `Financials`, …).
- The board is a fixed 3600×2200 world and the final framing is on the hub, so the sticky labels are read mainly mid-zoom. Content off the frame is intended (the shot is a viewport over a larger canvas).
- The pastel stickies and their dark text stay the same on every DNA. Only the canvas, grid, connectors and hub follow it.
- The stickies had no border at all, only a shadow, and the six pastels sit within a hair of a warm-white ground. Measured 29.8% of the register's ink under 3:1 on a light ground, chained into one region 0.80% of the frame, all of it note rims — the labels on them read at a median 9.00:1, and the hub, which has carried a border since it was written, is not in the finding. Each note now takes a 1px hairline in the DNA's `surfaceBorder`, inset so a 300×180 note stays 300×180.

**Reference:** `remotion/src/shots/InfiniteCanvas.tsx`
