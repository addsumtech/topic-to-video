# Blender plates

A Blender plate is a 3D render that a film's own workshop shot draws its overlay on. Blender draws what 3D physicality
*is* the content of. Remotion keeps words, captions, timing, data and layout. A plate is never a whole film, and never
carries body text. Design: `docs/superpowers/specs/2026-11-04-blender-plates-design.md`.

## When a beat may route to Blender

Write the beat's ideal picture (`shot_fit.ideal`) first. A plate is allowed only when that picture needs one of the
following. `slide.blender.why` names which, from a closed vocabulary:

| `why` | for | why Remotion cannot |
|---|---|---|
| `real-world` | a real place or object with real data or scans: the Earth and planets (NASA imagery), terrain (elevation data), museum scans (Smithsonian CC0), molecules (PDB) | 2.5D only draws a diagram of it |
| `material` | the material is the point: metal, glass, liquid, translucency, subsurface; a product hero with a known shape | CSS/SVG has no real reflection or refraction |
| `physics` | the physical process is the content: rigid bodies, cloth, fluid, smoke, particles (baked) | Remotion can only approximate the motion by hand |
| `optics` | caustics, refraction, volumetric light, macro depth of field | needs path tracing |
| `space` | moving through a 3D structure, inside a machine, an exploded view with real parts | 2.5D parallax breaks under a large camera move |

Never route a beat to Blender when the picture is any of these: words or layout, charts and data (the library has data
registers), UI, diagrams, abstract ideas.

Rules for choosing:
- **Compare before choosing.** When a library register can say the beat, render a still of each, side by side. The
  plate must be clearly better. The first plate (a GPS satellite) only matched the 2.5D register; its real Earth is
  what won.
- **A designed object needs references** (its fidelity record, as for any object). With none, it does not go to
  Blender.
- **Budget.** At most about 30% of a film's beats, and about 40 s of plate in total.
  - `meta.blender_budget_min` (default 60) bounds the estimated render time. Over it, `blender_plate.py` exits 3 and
    prints the estimate.
  - Ask the user before re-running with `--yes`.
- **Downloads.** At the start of a film, list every asset to download once: file name, source, size and licence. Ask
  the user once, then ask again for any later addition. Every asset needs a `<file>.json` sidecar with `license` and
  `source`, or the spec is refused.

## The board contract: `slide.blender`

```json
"blender": {"id": "sat-broadcast", "scene": "blender/sat_broadcast.py", "why": "real-world",
            "mode": "rgba", "engine": "eevee", "cues": ["广播"], "anchors": ["antenna", "limb"],
            "objects": ["sat", "earth"], "assets": ["assets/earth/earth_24k.jpg"]}
```

- `id`: lower-case, digits and `-`, unique on the board. The plate is written to `media/blender/<id>/`.
- `scene`: a `.py` file under `<out_dir>/blender/`.
- `mode`:
  - `rgba` (default): a transparent plate composited over the film's own ground, so the stars and ground stay the
    film's;
  - `env`: an opaque plate, for when the world itself is the content.
- `engine`: `eevee` (default) or `cycles`. Cycles is for glass, caustics and heavy volumes only, and is GPU-only.
- `cues`: spoken phrases whose times the scene receives as `k.cue[phrase]` (seconds into the beat). A phrase the
  voice does not say is an error, never a guess.
- `anchors` / `objects`: names the scene must build. Anchors become pixels per frame. Objects get an ID colour, and
  so a box per frame.
- `assets`: files the scene reads. They are hashed into the plate's key.
- The beat's `shot` must be a workshop shot. It imports `BlenderPlate` and `usePlate` from `@runtime/blenderPlate`
  and `PLATES` from `../assets/plates` (generated).

## The scene-script API

`build(k)` returns `{"objects": {name: obj}, "anchors": {name: (obj, (x, y, z) local) | fn(k)}}`. A computed
anchor `fn(k)` returns `[x, y, depth, visible]` in frame pixels, for a point found on the picture each frame, such as
the near crossing of a sphere's limb. `pose(k, t)` sets the scene
at `t` seconds into the beat (plate time 0 is the beat's first frame, which is when its voice starts).

`k` carries:
- `scene`, `camera` (made by the runner: at the origin, looking +Y; right = +X, up = +Z), `cue`, `fps`, `frames`, `w`,
  `h`, `duration`, `mode`, `engine`;
- `k.hexc('#rrggbb')`, a linear colour for nodes;
- `k.stage`:
  - `place(cam, obj, sx, sy, depth)` (screen fraction from the top-left);
  - `face_toward(obj, '-Z', target, toward_lens)`;
  - `screen_point`, `frame_at`;
- `k.anchors`: `project`, and `sphere_limb_crossing` (the near crossing of a ray toward a sphere's limb).

**Compose in camera space.** On the first plate, guessing in world space put the Earth off the frame and the satellite
edge-on. Placing things by where they should fall in the picture fixed both.

**Metal reflects its surroundings, and space is black.** On the first plate the gold foil came out black. Two fixes
worked:
- a reflection dome that the lens never sees (a Light Path *Is Camera Ray* mix in the world shader);
- a soft key light from the lens' left.

**A real asset can carry a defect that no gate sees.** NASA's 24k Blue Marble on Commons has a white last column. Wrapped
round a sphere, that column drew a bright meridian.
- validate WARNs on any 2:1 map whose edge column is a flat band unlike its neighbour (`asset_warnings`).
- To fix it, make a copy, record `derived_from` and `change` in the copy's sidecar, and point the scene at the copy.

**An opaque (`env`) plate must end in the shot's GROUND.** On a 9:16 film the shot is drawn in a scaled frame whose
edge dissolves into the shot's own GROUND, and the margin never copies a picture. The glass plate's stripes and lit
table ran to the plate's edge, so it read as a panel: frame_safe_qa measured steps of 171–194 levels at the left and
right edges. Keep the plate's outer tenth in the room's own colour: stop props and backdrops short of it, and light
the floor only where the subject is. The room colour also shifts under AgX: the world `#0b1220` at strength 1
rendered (1, 6, 16), so measure a still's edge against the GROUND.

**A 9:16 frame fits the sensor to its long side**, so a lens and distance chosen by eye fill a portrait frame with the
subject; the first glass plate was all glass. Size the subject from `k.stage.frame_at(cam, 1.0)` (the frame's width
and height one unit from the lens).

**A plate keeps the voice's clock.** Film's sync warp re-times a register's entrances, so the register sees fractional
frames. `usePlate` reads `PlateClock`, the beat's own frame with the time grammar applied but no warp and no stepping,
and rounds it. Its cues come from the word times, so it is on the voice already.

## Commands

- `python3 scripts/blender_plate.py <out_dir> [--only ID] [--still F] [--layout] [--skip-layout] [--preview] [--yes]`
  builds every stale plate, LAYOUT FIRST: the ID pass and anchors of every plate whose layout has not passed, the
  film judged by plate_qa, and pictures only once that is clean. A passed layout is recorded (`layout.json`) against
  the plate's key, so the same inputs are never judged twice.
  - Exit codes: `0` built or fresh · `1` failed (the Blender log tail is printed) · `2` Blender missing or older
    than 5.0 · `3` over budget · `4` the layout failed plate_qa (move the type or `stage.place` the object; no
    picture was rendered).
  - `--layout` builds only the layout pass (a plate of the objects' silhouettes; validate refuses it for delivery).
    `--skip-layout` builds pictures without it.
  - `--still F` renders one frame of each plate to look at, and writes no plate.
- `--preview` builds every stale plate at half the frame each way and 16 samples, to check motion and layout
  cheaply. validate refuses a preview plate for delivery. A full build replaces it.
- `python3 scripts/plate_qa.py <out_dir>`, a blocking delivery gate on films with a plate: the shot's own type must not
  sit on a plate object (an ERROR at 15% of a line's box on 2 sampled frames).
- `validate.py` refuses a beat whose plate is missing or stale. The key covers its scene, the kit, its assets, its
  cue times, its frame count and size, its engine and mode, and the Blender version.

## Never pay twice

The first two acceptance films (17 s and 6.6 s) cost about 135 GPU minutes: the GPS plates were built whole three
times and the glass plate twice, the last GPS rebuild only to move the Earth out from under a title. Building a plate
whole is the one expensive step, so it happens ONCE, after everything cheap has said yes:

1. **Look at one still** (`--still F`, the beat's settled frame): composition, materials, light.
2. **Pass the layout** (automatic in a plain build): the ID pass alone, a fraction of a picture frame, is what
   plate_qa judges type against.
3. **Build the pictures**, once.

Inside a build, nothing that did not change is rendered (blender/kit/reuse.py):
- `copy`: nothing the picture depends on changed since the last frame;
- `patch`: only some objects moved under a still camera, lights and world, so only their rectangle (then and now, with a
  margin) is rendered;
- `full`: anything else.

The signature reads every object's matrix, visibility and modifiers, every node value, every light and camera setting.
The first reused frame of each run, and every 24th after it, is rendered whole as well and compared. A mismatch
turns reuse off for the plate and re-renders the frames since the last good check, so a frame is never quietly
wrong. A scene whose pose changes something else (a mesh's vertices) sets `k.reuse = False`. Keyframes, drivers, a
Scene Time node or an image sequence turn reuse off on their own. run.json and plate.json record what each frame was.

## Costs (measured on an Apple M4 with a 10-core GPU, 2026-11-04)

| pass | per frame |
|---|---|
| EEVEE, simple scene, 1080p | 3.4 s |
| EEVEE, first plate (satellite + 24k Earth), 1080p | 4.6 s (169 frames in 783 s) |
| Cycles, GPU only, 64 spp + denoise, simple scene | 13–19 s |
| ID pass (Workbench, half size) | 0.72 s |
| acceptance plates, EEVEE: sat-broadcast 169 frames / orbit-gain 351 frames | 895 s / 1359 s (estimated 909 / 1877) |
| `--preview` Cycles (glass, 540×960, 16 spp), 199 frames | 1027 s and 702 s: 0.31 and 0.21 of the full-build estimate |

Four plates of 6 s each are about 55 min on EEVEE. Never enable the CPU device for Cycles: CPU+GPU at 128 spp
measured 67 s a frame.
