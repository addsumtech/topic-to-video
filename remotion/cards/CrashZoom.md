# CrashZoom

**Identity:** a wide grid of tiles holds, then the camera punches in on one tile — radial speed lines, a small overshoot — until it fills the content zone as a detail card whose text becomes the beat's label.

**Use when:** overview → "and here is the one that matters": the film names which of several things is the point. **Not when:** no single item is the point (use a grid or list register), or the emphasis should be a soft focus pull rather than a hit (FocalIsolation, RackFocus).

**Motion core:** the title rises (0.04–0.18); tiles pop in one after another (from 0.06, staggered 0.03); the punch runs 0.34–0.74 — neighbours fade out early in it, speed lines rise and fall around where the card will land; an overshoot swells from 0.68 and settles by 0.95; shortly after 0.72 the card's text swaps to `label`. The title fades out as the punch runs.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one tile each, up to three per row | 1–3 items make one row of tall tiles (height is capped); more add rows and shrink every tile. All tiles share one type size — the smallest that fits the longest item on two lines |
| `target` | the index of the tile the camera punches into | that tile is the accent one and becomes the card |
| `label` | the text on the landed card, replacing the item's name | fitted to two lines of the unscaled tile, so it still fits at full punch |
| `title` | small spaced caps over the grid | fixed 30px, not fitted; gone once the punch is under way |

**Known traps:**
- `target` used to default to 4 and be clamped, so any film's fifth (or last) item was punched into as "the one that matters" — a verdict the film never gave. With the film's own items it is required.
- The landed card shows `label`, not the item: if `label` does not name the thing, the item's own name is gone at the moment of emphasis.
- The punch is sized to land inside the content zone, clear of the action-safe border and the caption band; running it to the frame edge once parked the card under the subtitle.
- The hero card's second gradient stop was a hardcoded royal blue that overrode themed films; it is derived from the DNA now.

**Refuses:** no items; a missing, non-integer or out-of-range `target` when the items are the film's own.

**Reference:** `remotion/src/shots/CrashZoom.tsx`
