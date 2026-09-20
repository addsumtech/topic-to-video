# MoleculeBallStick

**Identity:** a ball-and-stick molecule builds outward from its centre with an overshoot and turns in genuine 3D (hand-projected, depth-sorted spheres and sticks) above a title and a mono tagline.

**Use when:** a chemistry beat about a real compound whose structure the film passes as atoms and bonds — drawn in conventional CPK colours; or, with no `molecule`, a generic "a molecule" moment in one neutral tone. **Not when:** the frame names a specific compound but the film has no coordinates for it (the generic ring is not that compound), or the beat is not about molecular structure.

**Motion core:** the structure scales up from its centre with a slight overshoot over 0.06–0.44 while it rocks about the vertical axis — (t − 0.5) × 1.0 rad, so it swings from 0.5 rad left of the viewer to 0.5 rad right and faces the viewer at the middle of the clip; the title rises 14px into place over 0.52–0.76 and the tagline fades in over 0.62–0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big title under the molecule | fixed size (up to 104px, smaller on narrow frames) with no fit-to-width; a short name reads as a label, a long one wraps |
| `tagline` | the mono line under the title | a quiet caption; long text runs wide |
| `molecule` | `{atoms: [{x, y, z?, el}], bonds: [[a, b]]}` — 2–40 atoms, element symbols, bonds by atom index; `null` for the generic form | the coordinates are centred and scaled so the farthest atom sits at a fixed radius, then the whole thing is fitted to the room above the title over the whole swing — a sprawling molecule draws smaller. Atoms take CPK colours; H is drawn smaller than heavier atoms. Every bond is the same single stick |

**Known traps:**
- It used to draw one made-up molecule under any title, colouring outer atoms as O/N/H by their POSITION. Without `molecule` it now draws a neutral ring naming no element — do not caption that as a specific compound.
- The rock is symmetric about facing the viewer, so a flat structure (atoms given without `z`, and the near-flat generic ring) stays legible for the whole clip; `z` values add depth but are not needed for the shape to read. The register previously turned 1.6 rad one way and ended a flat molecule edge-on, as a column of overlapping balls.
- Bond order cannot be shown — a double or triple bond draws as the same single stick.
- The molecule used to swing down through the title as it turned; the scale is now fitted to the room above the title, so a long title that wraps is the one thing that can still crowd it.
- Omitting `title` / `tagline` prints the demo copy `Composed` / `the chemistry of it`.

**Refuses:** `molecule.atoms` with fewer than 2 or more than 40 atoms; an atom with a non-finite `x`, `y` or `z`; an element with no CPK colour here (known: H, C, N, O, F, Cl, Br, I, S, P, B, Si, Na, K, Mg, Ca, Fe, Zn, Cu); a bond that does not join two different valid atom indices.

**Reference:** `remotion/src/shots/MoleculeBallStick.tsx`
