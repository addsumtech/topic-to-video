# Cinematic-tier component library — what to adopt, what to build

The Remotion cinematic tier's content vocabulary is thin (`panel`/`hero`/`textblock`/`callout`/`image` +
backgrounds; 3D = colour planes). A **product** film needs more: device frames, data/metrics/charts,
diagrams, icons, logos, shapes/connectors. This is the catalog of components to pull in — from the
Remotion ecosystem, third-party libs, and our own HTML tier — with the one rule that governs every choice.

## THE HARD RULE — everything must be FRAME-DRIVEN

Remotion renders by advancing `useCurrentFrame()` and snapshotting each render. **Any component that
animates on real time** (`useEffect`+`setInterval`/`requestAnimationFrame`, CSS `transition`/`animation`,
Framer-Motion `animate()`, a chart lib's built-in enter animation) **renders as a frozen/undeterministic
frame in Remotion.** So:

- **Adopt only what is frame-safe**, or take a component's STATIC render and drive the motion ourselves
  with `spring({fps, frame})` / `interpolate(frame, …)`.
- Charts/counters: **turn OFF the library's animation** (`isAnimationActive={false}` in recharts) and
  animate the DATA/reveal from the frame instead.
- Official `@remotion/*` packages are frame-safe by construction — prefer them.
- Determinism ban (already enforced elsewhere): no `Date.now()` / `Math.random()`; seed by frame/index.

## 1. Official `@remotion/*` packages — the safe foundation (prefer these)

| Package | Provides | Use here | Installed? |
|---|---|---|---|
| `@remotion/shapes` | Rect/Circle/Triangle/Star/Pie/Ellipse + path gens | shapes, masks, dividers, pie bases | add |
| `@remotion/paths` | `evolvePath` (draw-on), `getPointAtLength`, `interpolatePath`, `warpPath` | connectors/arrows/underlines drawing on, path-follow, morph | add |
| `@remotion/lottie` | plays After-Effects Lottie JSON (render waits for load) | designer-made logo/icon/celebration motion — high value, low effort | add |
| `@remotion/skia` | GPU Skia canvas (shaders, blur, glow) | **bloom/glow** — a separate canvas, so it does NOT flatten the CSS-3D rig (unlike motion-blur) | add (later) |
| `@remotion/three` | `ThreeCanvas`, `useOffthreadVideoTexture` | textures (screenshots/video) on true-3D planes — fills the P6 "colour-only" gap | ✅ installed |
| `@remotion/layout-utils` | `measureText`/`fitText`/`fillTextBox` | fit headlines to a box (wire the fitText that's currently unused) | ✅ installed |
| `@remotion/animation-utils` | `interpolateStyles`, `makeTransform` | clean style/transform keyframing | ✅ installed |
| `@remotion/media-utils` | `visualizeAudio`, `getAudioData` | audio waveform / beat-sync (optional flair) | add (optional) |
| `@remotion/motion-blur` | `CameraMotionBlur`, `Trail` | RESERVED — its opacity composite FLATTENS the CSS-3D rig; use only on flat 2D | ✅ installed (unused) |

## 2. Third-party libraries — product-video essentials (vet frame-safety + version)

- **Charts — `recharts`** (React-first, pure **SVG** → deterministic). Use with `isAnimationActive={false}`
  and drive the bar/line reveal from the frame. Alternatives: `nivo` (SVG mode only), `visx` (D3, max
  control, heaviest). **recharts is the pragmatic pick.**
- **Device frames — `react-device-frameset`** (iPhone/iPad/Macbook/browser chrome, CSS-based) or
  `react-device-mockup` (pure `div`, Android/iOS). Put a product screenshot in a real device shell — the
  most-used product-video component. Static markup → frame-safe.
- **Icons — `lucide-react`** (the SAME Lucide family the HTML tier uses; themeable via `currentColor`).
  Standalone React components, static → frame-safe. One icon world across both tiers.
- **3D text — do NOT use drei/troika `<Text>` under Remotion.** It renders BLANK: troika generates its
  glyph SDF ASYNCHRONOUSLY inside the R3F canvas (a layer below font loading — a DOM-level `preloadFont`
  does not fix it), so the frame captures before it syncs. Verified + drei removed. **The working path:
  RASTERIZE text to a transparent PNG at build (PIL + the bundled font, `render_remotion._rasterize_text3d`)
  and texture it onto a plane** (`kind:"text"` → an alpha textured plane, billboarded to face the camera).
  Reuses the proven DOM-level texture load. Real 3D text, deterministic, any camera angle.

## 3. Community kits — mine for ideas, adopt selectively

Copy-paste kits; each component must be checked for frame-safety before use.
- **Onda** (onda.video) — richest: 80+ components, 21 transitions, 17 effects (kinetic type, film burn,
  luma wipe, whip pan, zoom blur, mesh gradients, particles, path morph, bloom, DoF, colour grade, 3D
  extrude, beat sync). **Study the effects; reimplement the good ones natively — don't take a heavy dep.**
- **RemotionUI** (remotionui.com) — ready SCENE recipes (Data Story, Product Intro, Lower-third, Showcase,
  Hero Loop). Mine the scene-template shapes.
- **Remocn** (remocn.dev, 64+ shadcn-style), **Remotion Bits** (`AnimatedText` kinetic type),
  **remotion-kit** (seblavoie, helper presets).
- **Official `remotion-dev/skills`** — authoritative rule-packs (text-animations / transitions / 3d /
  fonts). Follow these for correct frame-safe patterns.

## 4. Two integration PATHS (use both)

- **Path A — reuse the HTML tier's ~30 forms as rendered planes.** The HTML tier already solves
  chart/timeline/table/diagram design (base.css/motifs.css). Render a designed HTML page to an image, then
  fly the cinematic camera over/through it as a plane (the reserved "captured layer"). **Highest leverage
  for complex data/diagrams/layout** — don't rebuild what's already designed.
- **Path B — a few NATIVE cinematic primitives** for hero moments that must animate crisply in 3D:
  device frame, big KPI counter, kinetic statement, icon, shape/connector. Built on the official packages
  above.

## 5. Need → source decision matrix (for a PRODUCT film)

| Content need | Best source | Path | Frame-safe note |
|---|---|---|---|
| Product screenshot in device chrome | `react-device-frameset` + image `size` | B (native element) | static → safe |
| KPI / big number | native counter via `spring(frame)` | B | drive from frame |
| Bar/line/donut chart | `recharts` (anim off) OR HTML `chart` form as plane | A or B | anim off; reveal by frame |
| Timeline / flow / architecture / table | HTML form → plane | A | reuse HTML design |
| Icons | `lucide-react` | B | static → safe |
| Logo / brand animation | `@remotion/lottie` (or static PNG) | B | Lottie is frame-safe |
| Connector / arrow / underline draw-on | `@remotion/paths` `evolvePath` | B | frame-safe |
| Shapes / masks / dividers | `@remotion/shapes` | B | frame-safe |
| Real 3D text / product mockup | `@react-three/drei` Text3D + `useOffthreadVideoTexture` | B (P6) | frame-safe |
| Bloom / glow | `@remotion/skia` | B | separate canvas — won't flatten 3D |

## 6. Adoption checklist (run BEFORE `npm install` anything)

1. **Version compat** with the stack: React 18.3.1 · Remotion 4.0.486 · @react-three/fiber 8.17.10 ·
   three 0.169.0. (drei → v9, NOT v10.) Install a compatible SET in one `npm install` to avoid ERESOLVE.
2. **Frame-safety**: does it animate on `useCurrentFrame`, or on real time? If real-time, disable its
   animation and drive from the frame.
3. **Determinism**: no `Date.now()`/`Math.random()`; no network fetch at render (bundle assets locally,
   like the fonts in `.fonts/`).
4. **Flatten check** (if it wraps 3D content): no `opacity`/`filter`/`overflow` on a `preserve-3d`
   ancestor (see `tests/test_remotion_3d.py`).
5. **Gate it**: every new element kind → add to `_ELEM_KINDS` (validate) + `elements.tsx`; verify from a
   real render + `shot_qa`; keep the HTML tier byte-untouched.

## 7. Priority batches (product-video first)

1. **Device frame element + image `size`** — makes "show the product UI" look right immediately.
2. **HTML-form-as-plane** — one step to reuse all ~30 data/diagram forms (highest leverage).
3. **Native KPI counter + `lucide-react` icons + `@remotion/shapes`/`paths` connectors** — hero moments.
4. **`@remotion/lottie` (brand/icon motion) + drei Text3D/textures (P6 content) + `@remotion/skia` bloom**.
