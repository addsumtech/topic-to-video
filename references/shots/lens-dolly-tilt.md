---
name: lens-dolly-tilt
one_liner: A camera dollies THROUGH layered space while tilting from a high angle down to eye level.
purpose: The establishing / hero move for a cinematic beat — it reveals a real space (not a flat card) by moving a virtual camera through depth. Use to open a section, introduce a product, or land a payoff with weight. This is the move flat parallax fundamentally cannot make.
energy: bold
duration: 5–7s; the tilt+dolly runs the whole scene; one reveal at ~0.45×
tier: [remotion]
delivers_via: remotion/src/Camera.tsx (CinematicScene3D); props `lens` + `layers[].z` + `perspective` (scripts/render_remotion.py build_props)
---

## Rule

Author the scene's content as HTML/CSS `layers` at real `z` depths inside a `perspective` rig, and move ONE `lens` (dolly/pitch/yaw keyframes) through them. Keep the focal content SHARP at the front; make far planes soft (`blur`) and dim.

## Rationale

Flat parallax only *scales* planes — no vanishing point, no camera angle — so it reads as a zoom. A CSS-3D rig gives true perspective: planes at different `z` **occlude** and foreshorten, the camera can look DOWN (bird's-eye, +pitch) or UP (worm's-eye, −pitch), **yaw** for orbit-lite, and **dolly** to move THROUGH the space. Depth-of-field (per-plane blur) with one sharp focal plane is what makes it read as a *lens*, not a diagram.

Mechanics (`CinematicScene3D`): a `perspective` container wraps a `preserve-3d` world transformed each frame by `scale · translateZ(dolly) · rotateX(pitch) · rotateY(yaw) · rotateZ(roll)`; each layer sits at `translateZ(z)`; the `floor` plane lies flat (`rotateX 90`). The lens settles on an eased curve.

## Good

| param | typical | tuning feel |
|---|---|---|
| lens `pitch` | 22–34 → 4 | start high (bird's-eye), settle near eye level; past ~40° card planes keystone |
| lens `yaw` | ±8–14 → ±2 | a little orbit makes depth legible; past ±35° planes lose their face |
| lens `dolly` | −500 → +200 px | the push-through; more negative starts further back |
| layer `z` | focal +120 … far −1500 | spread ≥ ~800px between focal and far so occlusion/parallax read |
| layer `blur` / `dim` | focal 0 / 0; far 6–10 / 0.3–0.5 | rack focus: only the focal plane is sharp; background softens + darkens |
| `perspective` | 1200–1400 | smaller warps, larger flattens toward orthographic |

Tuned truth lives in `remotion/src/Camera.tsx` `CinematicScene3D`.

## Bad

- **opacity / filter / overflow≠visible on the 3D ancestor** → silently FLATTENS all depth to a flat image, and no per-frame test catches it. The runtime keeps the rig inner (fades/vignette on OUTER nodes, blur on an INNER wrapper) and a source test (`tests/test_remotion_3d.py`) guards `Camera.tsx` against regressions — do not defeat it.
- **pitch past ~40° / yaw past ~35°** → flat card planes reveal as thin sheets and text keystones. Route a true 90° top-down / full orbit to the reserved R3F tier, not this rig. `validate` warns past the band.
- **Text on the background planes** → competing words muddle into noise even when blurred. Reserve TEXT for the focal plane; make far planes texture/shape/grid/floor.
- **No focal plane** (everything equally sharp) → no rack focus, reads flat. Give exactly one plane `blur: 0`, `dim: 0`.
- **"Parallax of nothing"** → an all-vector-furniture scene with no lit/topical subject stays cold. If the beat is about a real thing, make a deep plane a real `image` (documentary/atmosphere tier), never generic filler.

## Impl

- **Determinism:** pure `useCurrentFrame()` — no `Date.now()`/`Math.random()`; lens `atFrame` are integer frame indices authored relative to the beat.
- **Gate:** `validate._cinematic_fields` checks keyframe ordering, the pitch/yaw bands, `z`/`blur`/`dim`/`perspective` ranges, and image-plane existence. The move itself is judged only from the rendered filmstrip `<out_dir>/_keyframes/scene_NN.png`.
- **reduced_motion:** the lens freezes at keyframe 0 (a clean static frame); reveals show instantly.

## Checklist

- [ ] **Real depth** — on the filmstrip, planes OCCLUDE and the floor grid CONVERGES to a vanishing point; it is not a uniform zoom. [design-critic D2e depth-ordering]
- [ ] **A lens angle is visible** — the frame looks DOWN then levels (or up): a camera, not a slider. [D2e camera-motivation]
- [ ] **One focus** — exactly one sharp focal plane; background soft + dim. [D5 focal dominance]
- [ ] **In band** — pitch ≤ ~40°, yaw ≤ ~35°; text lives only on the focal plane. [D9 renegotiated]
