# TerrainFly

**Identity:** a synthwave wireframe landscape scrolls toward the viewer under a glowing horizon, with hills drifting in from the fog and grid lines coloured by elevation, while a big glowing title and a spaced mono tagline rise in above it.

**Use when:** an atmospheric opener or transition about new ground, a journey ahead or exploration, where the mood is the message and two short lines carry the words. **Not when:** the beat carries data or a real place. The terrain is summed sine waves; its hills mean nothing and must not stand in for a real landscape or a data surface.

**Motion core:** the terrain advances at a constant speed for the whole clip (four grid rows' worth), with near rows recycling so the ground never ends. Far rows fade into the horizon glow. The title rises and fades in over 0.16–0.44 and the tagline fades in over 0.30–0.56. Nothing settles, because the ground keeps flying.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big glowing word above the horizon | a fixed 120px heavy display face, not fitted to the frame. One or two short words read as a title card; a longer title wraps down onto the tagline. The demo `Cross it` prints if omitted |
| `tagline` | the spaced mono line under the title | a fixed 30px with wide tracking. Short phrases only. The demo `new ground, ahead` prints if omitted |

**Known traps:**
- The sky is DERIVED from the film's ground (lifted toward `accent2` at the top and `accent` at the horizon), not a fixed dusk. It used to run from a literal violet to the film's ground, so on a light film the near half of the mesh — the rows the terrain is actually read from — was mid-blue on white at 1.05:1, and the wordmark read only because the top of the frame happened to stay dark.
- The perspective is hand-rolled arithmetic drawn in 2D SVG, not WebGL. The header was corrected so "3D" is not a claim the library cannot keep, so do not describe it as a 3D scene.
- The palette is mostly fixed: the purple sky gradient, the mid-elevation line colour (`#4a6cff`) and the title and tagline inks are literals. Only the lower ground and the two accents follow the DNA, so it stays a night-synthwave look on any film.
- Everything is in fixed pixels tuned to a 1920×1080 frame (title at 96px from the top, tagline at 244px, a 700px horizon glow). Nothing is fitted, so long copy is the failure mode.
- Omitting either prop prints the demo copy.

**Reference:** `remotion/src/shots/TerrainFly.tsx`
