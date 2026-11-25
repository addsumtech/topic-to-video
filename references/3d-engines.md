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

- **Light is the HDRI plus soft boxes** (`studio.world`, `studio.product_light`): three soft boxes alone left metal
  clean but empty (WorkBuddy 2026-11-07); a single-colour world drew a horizon line, the cyclorama (`studio.sweep`)
  removes it.
- **Every part a named manufactured finish** (`materials.finish`: gloss_plastic, anodized_alu, glass, fabric…) and a
  chamfer on hard edges (`materials.chamfer`) so edges catch a highlight; a part with one flat grey reads as clay.
- **Cycles on the GPU only** (`render.configure`: CPU+GPU was 4x slower). Settle framing and the move on `--still`
  frames and a small EEVEE draft, render Cycles once.
- **Model for three.js with `--glb`**: modifiers applied, sheen fixed, AO atlas optional; build the object at real
  scale in metres (glTF is metres, Y-up; the exporter converts Blender's Z-up).

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
caustics limits); Poly Haven licence (CC0 HDRIs); Khronos glTF-Sample-Assets (per-model licences).
