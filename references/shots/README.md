# Shot cards — the cinematic move library

Load-on-demand recipe cards for the **cinematic tier** (Remotion). Each card is one camera/motion
move: a compact, gate-bound recipe the design-director cites by `name` in the plan and the design-critic
checks the rendered result against. Cards are **semantics + a pointer to the tuned source** — never a
copy of the code (the component is the single source of parameter truth).

This is the load-on-demand alternative to a prose "bible": a director reads only the 1–2 cards a beat
needs, so the library can grow to full coverage without a context penalty.

## Card schema

```
---
name: <kebab-key>              # cited in the design plan; unique
one_liner: <what it is, one line>
purpose: <the narrative job it serves — WHEN to reach for it>
energy: subtle | balanced | bold      # ties to the beat's energy + meta.audacity
duration: <frames + seconds, e.g. "push 90–180f (3–6s), reveal +12f, settle ≤0.5s">
tier: [remotion]               # which renderer delivers it: remotion | html-parallax | kenburns-free | doc-only
delivers_via: <impl pointer, e.g. remotion/src/Camera.tsx CinematicScene>
---

## Rule          — the imperative one-liner (what the author must DO)
## Rationale     — why it means something for the beat + the animation-core mechanics
## Good          — a Parameters table (param | typical | tuning feel) + a POINTER to the tuned source
## Bad           — the failure modes (cap lurch, second living backdrop, un-eased push, callout riding the camera, cross-seam move on the free path)
## Impl          — determinism (no Date.now()/Math.random(); relative frame refs); which gate validates it; reduced_motion behaviour
## Checklist     — 2–4 yes/no bound to critic IDs + acceptance thresholds
```

## Manifest

| card | tier | energy | move |
|------|------|--------|------|
| [push-in-parallax](push-in-parallax.md) | remotion | balanced | eased push-in over a 2.5D depth stack (flat parallax) |
| [lens-dolly-tilt](lens-dolly-tilt.md) | remotion | bold | dolly THROUGH real `z` depth while tilting bird's-eye → eye level, with rack focus (CSS-3D lens) |

## Two depth paths

- **Flat parallax** (`push-in-parallax`) — `layers[].parallax` + a `camera` (x/y/zoom). Cheap, no true
  depth; the cinematic-lite look. Reads as a zoom unless it has a real lit subject to push into.
- **CSS-3D lens** (`lens-dolly-tilt`) — `layers[].z` + a `lens` (dolly/pitch/yaw) inside a `perspective`
  rig. Real occlusion, vanishing point, camera angles (bird's-eye / worm's-eye), rack focus. The
  headline cinematic path; the layers are still authored in the HTML/CSS design system.
- **TRUE-3D / @remotion/three (R3F)** — the hero tier for what the CSS-3D card-plane rig structurally
  cannot do: real 90° top-down / full orbit / crane over content planes at true depth, with real lighting
  and occlusion (no keystone limit). Author a scene `type:"cinematic3d"` with `planes` (content planes at
  `position:[x,y,z]`, optional `rotation`/`size`/`color`) + a `camera3d` orbit/crane path (`{at, yaw,
  radius, height}`, `at` = 0..1 fraction). Renders via `remotion/src/three/ThreeScene.tsx`; the render
  auto-adds `--gl=angle` (WebGL). **Current state:** the camera/depth/lighting spine is built + verified
  end-to-end; content planes are solid-COLOR (or textured — image/text texturing on planes is the next
  increment). Reach for it only when a beat genuinely needs a true-3D move a card plane can't hold.

## Attribution

Cards are authored for this skill. Where a card **adapts** material or a component from
[`video-shotcraft`](https://github.com/Vincentwei1021/video-shotcraft) (Apache-2.0, © 2026 Wei Yihao),
that card names the source in `delivers_via` and the repo carries the upstream `LICENSE` + a `NOTICE`
with attribution and a note of modifications, per Apache-2.0 §4. The current cards are original and do
not yet adapt upstream code.
