# 3D engines: three.js (the page's stage) and Blender — which, when, and how to get each to its ceiling

Read when a shot has a 3D object, product, device, character or simulation in it. SKILL.md step 6 points here.

## The evidence this rests on

One object, one camera, one HDRI, rendered every way (an MRI scanner modeled once in Blender, exported as GLB;
`~/code_project/film_work/three_vs_blender`, 2026-11-25). Luminance measured against Cycles in the same regions
(gantry / floor / pad):

| Render | Time a 1080p frame | Gantry · floor · pad | What it looked like |
|---|---|---|---|
| Blender Cycles, 128 spp, denoised | ~45 s | 205 · 214 · 192 | the reference: soft area shadows, contact darkening, real reflections |
| Stage3D as it was (RoomEnvironment, ACES, one hard key) | <1 s | 199 · 223 · 193 | clean but CG: flat white ground, stepped shadow edges, no grounding |
| three.js raster + rect area lights + GTAO + whole-frame bloom | <1 s | 198 · 220 · 190 | bright haze: bloom smeared the white shell over every dark part |
| **Stage3D now: `hdri` + `areaLight` + `passes: 64` + `glb({ao})`, AgX** | **~0.3 s** (64 passes, 4K internal) | **189 · 210 · 188** | close to Cycles: soft penumbras, falloff on the wall, dark trim stays dark |
| three-gpu-pathtracer (WebGL), 64 spp, no denoiser | ~50 s | — | grainy; **clearcoat rendered black**; slower and noisier than Cycles |

So: three.js, used properly, gets within ~10 % of Cycles on an opaque product at ~1/100 of the time, and keeps what
only the page has (text, captions, screens and marks in the same frame, a camera on the voice's clock, the checks
looking inside it). Cycles still wins on inter-reflection and on materials whose look IS light transport.

## Which engine

| The shot | Engine | Why |
|---|---|---|
| An opaque product or device (plastic, paint, anodised or brushed metal) that the camera moves around, with words or marks on it | **three.js stage**, model made in Blender (`blender_clip.py --glb --ao`) | the measured case above: HDRI + area lights + passes + baked AO |
| Characters that act, panels and real screens in 3D, data or a simulation drawn from the content (a field, particles, a growing structure, a map) | **three.js stage** | it is code on the film's clock; the picture computes from the subject itself |
| A hero whose look IS the material or the light: glass seen through glass, liquid in a bottle, gems and dispersion, caustics, subsurface (skin, wax, food, marble), smoke and volumetric light, true displacement | **Blender Cycles clip** (`blender_clip.py --engine cycles`) | built-in transmission cannot see other transmissive objects; three.js SSS and caustics are approximations |
| Physics and simulation as the subject's own behaviour (cloth, fluid, rigid bodies, hair) | **Blender** (simulate and render; or bake to GLB animation for the stage) | only Blender has the solvers and grooming |
| A detailed real-world device built to look manufactured (a scanner, a camera, earbuds) | **Blender models it, always**; render in **three.js** when the shot also carries words or moves on the voice, in **Cycles** when the material close-up is the hero | modelling is Blender's either way; the render follows the shot |
| "It must look like a photograph" on a still or slow shot with no overlay | **Cycles** | the shortest path to photoreal: tuning three.js to match Cycles is time better spent in Blender |

Both in one film is normal: Cycles clips for the material heroes, the three.js stage for everything that moves with
the voice. Match them by lighting both with the SAME HDRI (`blender/kit/hdri/studio_small_09_1k.hdr`), both under
AgX (`Stage3D.create({toneMapping: 'agx'})`; Blender's `render.configure` sets AgX).

## three.js at its ceiling (the Stage3D kit; commands in the toolbox)

In order of what moved the picture most on the bench:

1. **A real HDRI, not a procedural room.** `await st.hdri('studio_small_09_1k.hdr', {intensity: 0.5})`. It is the light
   AND what every glossy surface reflects; a white plastic shell is mostly the studio it mirrors. `rotation` turns the
   reflections (judge on the frame: Blender and three.js do not orient an equirect the same way).
2. **Area lights averaged over passes.** `Stage3D.create({passes: 64})` + `st.areaLight({pos, aim, size, power})`
   (`power` ~ Blender area-light watts). Each pass moves every area light over its square and the camera by a
   sub-pixel (Halton sequences, so any K covers them evenly and the frame stays a pure function of the state).
   Real penumbras, no stepped shadow-map edges, supersampled edges. 64 passes took 0.3 s at 1080p with pixelRatio 2 (measured on the bench page).
   An offline film can afford this; a live page cannot, which is why web demos never look like this.
3. **AgX tone mapping**, once, at the end (the kit's OutputPass). ACES shifts hues and clips whites on white
   products; `neutral` keeps brand colours exact on flat graphics.
4. **Cycles-baked ambient occlusion on the model** (`blender_clip.py --glb --ao 2048` → `st.glb(url, {ao})`).
   Contact darkening (a bore, a seam, where a part meets another) that screen-space AO did not deliver: the GTAO pass
   changed the bench frame by under 1 %. The atlas darkens the environment light, so pair it with `hdri()`.
5. **Depth of field by the lens**, under passes: `st.render({..., lens: 0.02, focus})` (aperture radius in metres)
   — every pass sees from another point of the lens, aimed at the focus plane. True blur with no halo around edges;
   the old `dof` (BokehPass) ghosts words and marks and cannot be mixed with passes.
6. **Materials from the model** (glTF PBR → MeshPhysicalMaterial): clearcoat for gloss plastic and paint, anisotropy
   for brushed metal, sheen for fabric, transmission + thickness + ior for one glass part over opaque ones, emissive
   strength for LEDs and screens. Use the kit finishes in Blender (`blender/kit/materials.py`) and export.

Not in the kit, and why: whole-frame bloom (see pitfalls; glow belongs to emissive parts only, drawn as a mark or a
selective pass); the WebGL path tracer (deprecated upstream, slower than Cycles here); WebGPU SSGI/SSR/TRAA
(three.js r17x+ WebGPU-only, the kit is pinned at r169 with Remotion — revisit when the kit moves to WebGPURenderer
and headless Chrome WebGPU capture is proven on this machine).

## Blender at its ceiling (blender/kit; references/blender-plates.md for the scene API)

Measured on the same scanner through the kit's own product path (`studio.product_light` + `sweep` +
`tune_cycles`, 1080p, M-series GPU, 2026-11-25):

| Setting | Frame time | Picture |
|---|---|---|
| 24 spp, OIDN on the CPU (the kit before) | 25.6 s | the reference look |
| 24 spp, **OIDN on the GPU** (the kit now: `render.configure`, `tune_cycles`) | 19.8 s | same (mean diff 0.33/255 vs 128 spp, as before) |
| 16 spp, OIDN on the GPU | 10-13 s | same on a still (0.39/255); between two noise seeds 0.9 % of pixels move > 3 levels, so it does not boil on clean studio surfaces |
| light tree off | 46.7 s | — keep it on (the kit asserts it) |
| first frame of a process | +30 s | Metal kernels compile once: render a clip's frames in ONE process (the runner does) |

What lifts the picture, in order (each judged on the bench or in the craft study):

- **Light is the HDRI plus shaped soft boxes** (`studio.product_light`: a broad key, two tall rim strips, a top strip,
  a weak fill, sized from the object; `turn_light` swings the studio so a highlight travels). Light linking
  (`stage.product_rig`) gives a rim to one part only. Three soft boxes alone left metal clean but empty (WorkBuddy
  2026-11-07); a single-colour world drew a horizon line, the cyclorama (`studio.sweep`) removes it.
- **The view transform follows the product's colour** (`product_light(view=)`): AgX for white, light and glossy
  products (it keeps the highlight that draws an edge; Neutral turned the white shell creamy and flat); **Khronos PBR
  Neutral for a brand colour** (a #e4572e shell: saturation 0.72 under Neutral, 0.61 under AgX and Standard, target
  0.80). The page's stage has the same pair: `toneMapping: 'agx' | 'neutral'`.
- **Every part a named manufactured finish** (`materials.finish`) and a chamfer on hard edges (`materials.chamfer`):
  one flat grey per part reads as clay. `materials.micro(m)` varies a gloss or satin finish's roughness so a large face
  mirrors the studio unevenly, like a moulded part (subtle at 1080p; leave a hero polished metal or glass clean).
- **Cycles where the look is light transport, EEVEE where it is not.** EEVEE has no anisotropy, a crude sheen, one
  refraction event, no Bevel node, no area-light spread, screen-space reflections only: brushed metal, fabric and glass
  go to Cycles; matte and satin plastics and fast motion-design moves can stay EEVEE.
- **Camera like a product photographer**: 36 mm sensor; 70-120 mm for a hero close-up (no distortion), wider for a
  dynamic move; depth of field (`cam.data.dof`, a focus EMPTY that can travel for a rack focus, f/2.8-f/8 at product
  scale) shows only on a long lens close in — at 40 mm and 6 m it changed nothing visible; true motion blur
  (`render.use_motion_blur`, shutter 0.5) for parts that move fast.
- **Over the page, not baked on a backdrop**: a clip placed over the film's own ground renders `rgba` with a shadow
  catcher floor (`obj.is_shadow_catcher = True`, the laptop scene does) so its contact shadow lands on any ground.
- **The compositor sparingly.** Blender 5's Glare node takes its type as an INPUT (`gl.inputs["Type"].default_value =
  "Fog Glow"`; the old `glare_type` property is gone, and the default is Streaks). Fog glow above the white shell's
  level left every dark part unchanged and added little; grain and vignette belong to the film's own finish, once,
  not to each render.
- **Simulation is Blender's alone** (cloth, rigid body, fluid, Geometry Nodes simulation zones): bake it to disk before
  frames are rendered in chunks; a Geometry Nodes modifier's inputs live at `modifier.properties.inputs` in 5.2.
- **Model for three.js with `--glb`**: modifiers applied, sheen fixed, AO atlas optional; build at real scale in
  metres (glTF is metres, Y-up; the exporter converts Blender's Z-up).

Blender 5 API traps met or documented: the compositor is `scene.compositing_node_group` (a `CompositorNodeTree` with a
Group Output, `scene.node_tree` is gone); EEVEE's id is `BLENDER_EEVEE`; a UV-layer reference dangles after
`uv_layers.new()`; with `--factory-startup` no GPU is enabled unless set (the kit's `render.configure` enables it and
refuses to fall back to the CPU).

## Pitfalls found on the bench (each cost a wrong picture first)

- **glTF drops Sheen Weight.** Blender's exporter writes Sheen Tint (white) as sheenColorFactor: a 0.25 sheen became a
  full white one and the dark plinth and slate pad rendered light grey. `blender/kit/glb.py` folds the weight into the
  tint for the export.
- **Whole-frame bloom lifts every dark part near a white one.** A white shell is above 1.0 in linear light, so even a
  1.2 threshold bloomed it over the control panels (measured 172 vs 91 without; Cycles 120).
- **Additive blending in three.js multiplies by alpha**: averaging passes with `AdditiveBlending` came out at 1/K² (a
  black frame). The kit sums with one + one blending.
- **The WebGL path tracer renders clearcoat black** (three-gpu-pathtracer 0.0.28, three r187) and its loop must yield
  to the event loop while shaders compile (a tight loop never advances).
- **A Blender UV-layer reference dangles after `uv_layers.new()`** (the collection reallocates): set the active layer
  by index.
- **Rect area lights cast no shadows in the rasteriser**: they light, but nothing grounds the object. The kit's
  `areaLight` is a shadowing spot moved across the light's square under passes.
- **Tone mappers differ between engines** even by the same name: judge against a reference frame, not by settings.

## Sources (research 2026-11-25)

three.js manual: color management, WebGPU post-processing; Scene.js (environmentIntensity/Rotation, background
blurriness); three.js forum: "photorealistic render comparison — why does three.js look so bad", "tone mapping
overview" (Don McCurdy), lightmaps from Blender in glTF; pmndrs postprocessing README, drei AccumulativeShadows /
MeshTransmissionMaterial / Caustics docs; three-gpu-pathtracer README, API.md, releases and `example/renderVideo.js`;
Codrops case studies (Windland, Forged.build: baked lighting from Blender); Blender manual (Cycles light paths, MNEE
caustics limits, GPU rendering, EEVEE limitations, light linking, shadow catcher, Bevel node); Blender release notes
4.0-5.3 (light linking, Khronos PBR Neutral, OIDN on Apple GPUs, the 5.0 compositor and Python API changes); Poly Haven licence (CC0 HDRIs); Khronos glTF-Sample-Assets (per-model licences).
