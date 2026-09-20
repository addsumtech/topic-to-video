# VoxelBuild

**Identity:** isometric cubes, each shaded on three faces, drop in from above in stroke order and stack into a pixel-art check mark (✓) that faces the viewer: a short arm down to the vertex, then a long arm up to the right, each stroke two cubes thick. Then a big title and a spaced mono tagline rise in underneath.

**Use when:** the beat is about something being built or completed piece by piece ("built to last", "shipped"), a playful, crafted closing note where the check-mark reads as done. **Not when:** the beat has a count or a structure to show (the shape is fixed, 14 voxels whatever the film says), or the outcome is failure or unresolved.

**Motion core:** cubes drop 260px (scaled with the glyph) with an overshoot, each over 0.3, starting in stroke order (column by column from the left arm's tip, each column's lower cube half a step before its upper one) between 0.21 and 0.44, so the last lands around 0.74. The title rises in over 0.62–0.84 and the tagline over 0.72–0.90. It holds after that.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big line near the bottom | a fixed 88px heavy face, not fitted. It is anchored from the bottom and wraps upward; the check is placed above the title's estimated line count and shrinks to keep clear of it. The demo `Built to last` prints if omitted |
| `tagline` | the spaced mono line under the title | a fixed 30px with wide tracking. The demo `block by block` prints if omitted |
| `accent` | the cube colour | when passed it beats the DNA accent; otherwise the DNA accent is used. Faces are that one colour at three brightnesses (top, right, left) |

**Known traps:**
- The check is fixed geometry (14 cells on a 7-column × 6-level wall), marked in the code as the form itself, not data. It cannot draw the film's object or a count.
- It used to be an iso FOOTPRINT, (0,3) (1,4) (2,5) (3,4) … (7,0), which is a ✓ on graph paper and an L on screen (x ∝ i−j, y ∝ i+j: three cells straight down, then five flat to the right), with the title running through its base. It now stands on the iso diagonal that is horizontal on screen, so the cells form an undistorted pixel grid and the ✓ reads as one.
- Isometric is a 2D drawing convention with no camera and no vanishing point. The header used to call it 3D; don't.
- Tiles are 96×54 with a 66px rise at full size (a 672×450 glyph). They are scaled down only when the room between the content top and the title is shorter than that (1:1, or a title that wraps to several lines). The upper background glow and the title and tagline inks are literals, so a light DNA loses the text.
- Omitting `title` or `tagline` prints the demo copy.

**Reference:** `remotion/src/shots/VoxelBuild.tsx`
