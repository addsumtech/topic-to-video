# CraneUp

**Identity:** the items lie flat on the ground and the camera rises while tilting down. At the low angle they are a band of slivers with no readable shape; at the top of the move they are a grid, labelled and legible. One continuous lift, no cuts.

**Use when:** the claim is "you could not see this from where you were standing" — a shape, a scale or a pattern that eye level withholds. **Not when:** the claim is "look closer" (`CrashZoom`), "look at more of it" (`InfiniteCanvas`, a pull-back), "the same thing inside a bigger system" (`DollyZoom`) or "not this, that" (`RackFocus`). Every one of those keeps the camera's EYE where it was; zooming out from a plane seen edge-on shows you more edge, and only elevation resolves it.

**Why the arrangement is on the FLOOR:** upright cards read perfectly well from eye level, and then the lift reveals nothing — a camera move with nothing to reveal, which is the difference between a camera register and a motion preset. Flat on the ground, the foreshortening does the argument's work: what the frame withholds at the start is exactly what it hands over at the end.

**Motion core:** the camera is on an ARC, not a ladder. Raising `y` alone walks the subject out of frame, because the eye keeps pointing where it pointed; the position is derived from the aim (`cam = target + D · forward(rx)`), so the target stays centred and the only thing that changes is where it is seen FROM. `TermSpace` derives its fly-to the same way and its header records what the naive version cost. Tilt runs `RX_LOW` (7°) → `RX_HIGH` (52°) on an `easeInOutCubic` between 0.12 and 0.84. The low angle is not zero: dead level puts the floor exactly edge-on, which renders as a mathematically invisible plane and opens the shot on nothing.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `tiles` | what is lying there — 3 to `MAX_TILES` (12) | three is the fewest that can form a SHAPE; two things in a row look the same from any height |
| `near` | what it looked like from down here | shown early and cleared before the reveal lands, so the frame never carries both readings at once |
| `reveal` | what the shape turns out to be | named once the camera is high enough to see it |
| `kicker` | the spaced label over the low angle | fades out as the move tops, because it was a statement about where the camera WAS |
| `note` | one line under the frame, in the film's voice | where to say what the arrangement MEANT |

**Known traps:**
- Columns follow the FRAME as well as the count. A square-ish grid of six is 2×3, which is a narrow column down the middle of a 16:9 frame and the opposite at 9:16; weighting the count by the aspect gives 3×2 on a landscape frame and 2×3 on a portrait one from one expression.
- The camera's distance is DERIVED from the arrangement's radius, not set as a number. A CSS perspective `P` scales an object at depth `D` by `P/(P+D)`, so asking for a target on-screen radius inverts to a distance — and three tiles and twelve then both fill the frame. The first render used a flat `U × 1.35` and the whole arrangement occupied about a fifth of the frame width.
- Tiles step away from the ground with `plane`, never `dna.surface`: on a dark preset `surface` is within a few points of `bg`, and the first render put six tiles on a ground they were nearly the same value as — an arrangement being revealed that a viewer cannot see. `plane` steps in whichever direction the ground allows, so it holds on a light film too.
- The labels are FLAT type positioned at each tile's projected centre and scaled by that tile's own perspective factor — never rotated into the floor plane, where type tilted 83° away is unreadable and invisible to every type gate, and never at a fixed size, which makes the far row's labels as large as the near row's and reads as a caption layer floating over the shot.
- A tile behind the lens is skipped on `projectPose`'s own `behind` flag rather than on a finiteness check, because a projection behind the camera can still be a finite number and drawing it puts a label where nothing is.

**Refuses:** fewer than 3 `tiles`; more than `MAX_TILES`; an unlabelled tile.

**Reference:** `remotion/src/shots/CraneUp.tsx`
