---
name: push-in-parallax
one_liner: A slow eased push-in while foreground and background planes drift at different rates.
purpose: The opener / establishing move for a cinematic beat — it introduces depth and pulls the eye toward the hero content without any object animating. Use it when the beat's job is "arrive somewhere and settle," not "reveal a list."
energy: balanced
duration: push 90–180f (3–6s); optional single reveal at +60–80f; settle ≤0.5s at the end
tier: [remotion]
delivers_via: remotion/src/Camera.tsx (CinematicScene + PlaneView); props on scripts/render_remotion.py build_props (camera, layers)
---

## Rule

Put the scene's content on **2–4 depth planes** (`layers`, each with a `parallax` factor: background < 1, foreground > 1) and move ONE virtual **`camera`** across them with an **eased** multi-keyframe push-in. Nothing inside a plane animates except at most one reveal.

## Rationale

A push-in over flat art is a Ken Burns zoom — the free tier already does that. It becomes *cinematic* only when the planes separate: a near plane grows and travels faster than a far plane, so the frame reads as **space**, not a picture. That differential is the whole move. The eased curve (not linear) is what makes it read as a camera settling rather than a slider dragging.

Mechanics (all frame-driven, in `PlaneView`): for camera state `{x, y, zoom}` at a frame, each plane gets `translate(-(x-0.5)·parallax·W, -(y-0.5)·parallax·H)` and `scale(1 + (zoom-1)·parallax)`. So a higher-parallax (nearer) plane both pans and zooms more. One `revealAtFrame` fades a single secondary line in on an ease-out. A soft radial **vignette** sits above the planes so the eye lands centre.

## Good

| param | typical | tuning feel |
|---|---|---|
| `layers[].parallax` (bg → fg) | `0.6 / 0.82 / 0.9 / 1.28` | spread ≥ 0.4 between the nearest and farthest plane, or the depth is invisible |
| `camera` push `zoom` | `1.0 → 1.10–1.14` | past ~1.18 the near plane crops its own content and lurches |
| `camera` drift `x,y` | `±0.04–0.07` from `0.5` | a small off-centre drift makes the parallax legible; 0 drift shows depth only through differential zoom |
| `easing` (into the end keyframe) | `inout` | `out` for "arrive fast, settle"; never `linear` |
| `revealAtFrame` | `~0.4 × duration` | one reveal only; a second competing motion trips the depth-stack budget |

Tuned truth lives in `remotion/src/Camera.tsx` — the parallax formula, the reveal ease, and the vignette are there; this card gives the semantics, the component gives the numbers.

## Bad

- **Zoom past the read-safe band** (> ~1.18 on the near plane) → the foreground crops and the move lurches. The `validate.py` cinematic gate warns past `zoom 1.6` and on any single-segment `Δzoom > 0.35`.
- **All planes at the same parallax** → no depth; it is just a zoom. Give the nearest and farthest planes a spread ≥ 0.4.
- **A second thing animating inside a plane** (two reveals, a spinning icon) → competes with the camera and reads as noise. This is the declared depth stack's one-motivated-system budget (see the D9 renegotiation).
- **A callout/caption placed to "ride" the camera** → it must sit in screen space (captions layer), never inside a parallax plane, or it drifts off its target.
- **Reaching for this on the free tier** → the cross-plane parallax can't ship there; the honest fallback is a single-plane eased Ken Burns (`kenburns-free` tier), not this card.

## Impl

- **Determinism:** the move is a pure function of `useCurrentFrame()` — no `Date.now()`, no `Math.random()`, no wall-clock. Keyframe `atFrame` values are integer frame indices; author them relative to the beat, not as magic absolutes.
- **Gate:** `scripts/validate.py` `_cinematic_fields` checks keyframe ordering, on-canvas targets, the zoom band, layer kinds/parallax, and image-plane existence. The **move itself is judged only from the rendered filmstrip** `<out_dir>/_keyframes/scene_NN.png` (pre-tts the blind envelope is meaningless → mark UNJUDGED, never pass). `check_av.py` guards A/V parity.
- **reduced_motion:** the camera freezes at keyframe 0 and the reveal shows instantly (`CinematicScene` honours `reducedMotion`), so the accessibility variant is a clean static frame.

## Checklist

- [ ] **Depth is visible** — on the filmstrip, the near plane has clearly travelled/grown more than the far plane (not a uniform zoom). [D12a depth-ordering]
- [ ] **The move is motivated** — the push lands on the beat's hero content and settles as the narration makes its point, not a decorative drift. [D12b camera-motivation]
- [ ] **Eased, not linear** — the push accelerates in and settles out (≤0.5s settle), never a constant-rate slide. [D12c easing-not-linear]
- [ ] **One motion system** — exactly one declared depth stack + at most one reveal; no stray second animation. [D12e one motion system]
