# LightShafts

**Identity:** light arriving — a source behind an occluder (clouds, a canopy, the slats of a blind) and the shafts its gaps send through the air toward the lens, drawn by runtime/volume's scattering march (the sky round the source seen through each gap, averaged along each line toward it), so each shaft IS a gap; the type sits in the shade, on the side away from the light.

**Use when:** "a gap is enough", light breaking through, morning arriving, hope after a cover, a reveal that is literally light. `breakAt` opens the occluder at a point of the beat — the clouds part, the blind tilts — and the shafts strengthen with it. **Not when:** the light is a lamp or a screen in a scene (an optic, `bloom`), or the beat is about something else and the shafts would be a backdrop.

**Motion core:** the shafts fade up over the first 0.3; title 0.12–0.34, note 0.3–0.52; the clouds drift slowly; with `breakAt` the occluder opens from nearly shut to half open over 0.16 of the beat, centred a little before that point.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the statement, lower left | — |
| `kicker` | a mono line above it | — |
| `note` | a quieter line under it | — |
| `occluder` | `clouds` · `canopy` · `slats` | clouds: broad shafts; canopy: many small ones; slats: parallel bars of light |
| `source` | where the light is `[u, v]` (fractions; may be above the frame) | default top right at 16:9, top centre-right at 9:16 |
| `color` | the light's colour | default warm daylight, nudged toward the DNA accent |
| `breakAt` | a point of the beat (0..1) where the light breaks through | owns a `swell` sound; absent: a steady half-open sky, no sound |
| `seed` | which gaps | — |

**Known traps:**
- Shafts need the occluder: the break never opens it past half (a clear sky has no shafts — a wash).
- The type's box clears the light to 18% inside it with a wide feather; keep the source on the far side of the words.
- Under a light DNA the register paints its own dark ground.

**Refuses:** an occluder that is not one of the three; a colour that is not #rrggbb; no WebGL context.

**Reference:** `remotion/src/shots/LightShafts.tsx`, `remotion/src/runtime/volume.tsx`
