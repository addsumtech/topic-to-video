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
- The backdrop's own centre stop was a hardcoded navy too, so only the OUTER stop followed the film: on a warm-white DNA the beat painted a dark pool over the middle of the page, the paper survived in the corners, and the hero card — the whole point of the beat — measured 1.97:1 against it (99% of the register's ink under 3:1). The pool is a lift of the film's own ground toward its own accent now, so it is a pool of that film's light at either exposure.
- The neighbour tiles, their borders and their labels were dark literals; they take the film's `surface`, `surfaceBorder` and `fg` now, so a paper film gets pale cards with dark labels instead of nine navy tiles on the page. The kicker over the grid is the film's `dim`.
- The landed card's label is the film's `onAccent`, not white: white measures 1.77–3.51:1 on the eight presets' own accents (mint, amber, sky) where `onAccent` measures 5.35–10.70:1, so on a mint or amber film the one line the beat exists to show used to be the least readable thing on it.
- The speed lines are the film's ink, composited `screen` on a dark ground and `multiply` on a light one. They were a literal white under `screen`, which on paper draws nothing at all — a light film got a punch with no speed lines.

**Refuses:** no items; a missing, non-integer or out-of-range `target` when the items are the film's own.

**Reference:** `remotion/src/shots/CrashZoom.tsx`
