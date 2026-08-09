# Bespoke hero-beat components (the `component` escape hatch)

The cinematic tier ships a fixed vocabulary of native-3D forms (`planes` kinds:
`particles/surface/bars/stack/glyphrain/device/connector3d/text`, plus the shot-based `stage`
elements). Those are a **floor**, not the ceiling. A genuine hero beat often needs something no
enum anticipates — a precessing spin-field of quaternion-oriented arrows, a k-space grid that
IFFTs into a brain slice, an audio-reactive waveform, a path-morph between two logos. Growing the
enum for every one-off is the wrong move.

A **bespoke component** is the escape hatch: you write an ordinary React/R3F component, the
pipeline stages it into the Remotion bundle and dispatches it by name, and it renders through the
**normal `render_remotion` path** — captions, audio, edge-fades, cross-scene transitions, the
`.srt`, and every gate stay intact. You get unbounded expressive power **without forking the
composition** (the thing that lost pipeline parity before this existed).

## When to reach for it — and when NOT to

- **Reach for it** when the beat's core visual is HTML-impossible *and* not expressible as a
  parametric `planes` kind: real WebGL 3D with custom geometry/materials, audio-reactive motion
  (`@remotion/media-utils`), path/shape morphing (`@remotion/paths`), a physics-flavoured
  simulation. This is the "REMOTION'S REAL EDGE" beat.
- **Don't** reach for it for a beat a fixed `planes` kind or a `stage` archetype already covers —
  that's more code for no gain, and the data path is fully lint-checked. Don't use it to smuggle a
  flat HTML slide into the 3D tier either (that's Path A, deprecated). If the whole film is bespoke
  components, you've probably skipped the archetype system that gives beats variety — reserve
  bespoke for the 1–3 HERO beats and let the stock forms carry the calm beats.

## The contract (author this exactly)

**File:** `out_dir/bespoke/<Name>.tsx`. `<Name>` must be a bare identifier
(`[A-Za-z][A-Za-z0-9_]*`) — it becomes a filename *and* a TypeScript import.

**Export:** a **named export matching `<Name>`** (preferred) or a default export. The registry
resolves `<Name>` first, then `default`. Anything else → `validate` errors (the beat would render
blank).

**Storyboard:** the scene (type `cinematic` or `cinematic3d`) carries:
```jsonc
{ "index": 7, "type": "cinematic3d", "archetype": "data-materializes",
  "duration": 6.0, "narration": "...", "audio": "audio/07.mp3",
  "component": "SpinField",                       // → out_dir/bespoke/SpinField.tsx
  "componentProps": { "count": 64, "mode": "precess", "tiltDeg": 30 } }
```
The component renders the **whole** beat and **owns its own camera** — it does NOT receive the
pipeline's `camera3d`/`planes`/`lens`/`stage`. Put any camera move *inside* your component (a
`ThreeCanvas` camera, or CSS). `validate` **warns** if a component scene also carries those fields,
because they'd silently do nothing. Any orbit/animation you want goes in `componentProps` (e.g.
`{"orbitDeg": 40}`) and is read by your code.

**Props your component receives** (nothing else — pull the rest from Remotion hooks):

| prop | type | notes |
|------|------|-------|
| `theme` | `{bg, fg, accent, accent2, …}` | the deck's resolved colour world (from `theme.css`). Use it — don't hardcode colours, or the beat won't match the film. |
| `componentProps` | `object` | your author params, verbatim from the storyboard. Give every field a default (`props.count ?? 40`). |
| `reducedMotion` | `boolean` | when true, hold a legible static composition (no spin/drift) — accessibility parity. |
| `atmosphere` | `{materialClass, post, …} \| null` | the world substrate, if a `meta.atmosphere` is set. Optional to honour. |
| `durationInFrames` | `number` | the scene length, for normalising your own timing. |

For the current frame / fps / canvas, call Remotion hooks **inside** the component:
`useCurrentFrame()`, `useVideoConfig()` (`{width, height, fps, durationInFrames}`),
`spring()`, `interpolate()`.

**Return ONLY the visual body.** The Scene wrapper renders `<Captions>`, `<Audio>`, the
edge-fade, and the atmosphere `<Finish>` pass *around* your component. **Do not render captions or
audio yourself** — you'd double them (`validate` warns if it sees `<Captions>`/`<Audio>`/an audio
`staticFile` in the file). Fill the frame with an `<AbsoluteFill>` at `theme.bg` (or transparent,
to sit over the wrapper's bg).

## Worked example — a real R3F 3D beat

`out_dir/bespoke/SpinField.tsx` — a field of arrows precessing about a shared axis (the thing no
`planes` kind draws). Uses `@remotion/three` (`ThreeCanvas`) + `@react-three/fiber`, both already
in the skill's `remotion/package.json`:

```tsx
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';

const UP = new THREE.Vector3(0, 1, 0);

const Arrow: React.FC<{i: number; n: number; t: number; tilt: number; color: string}> = ({i, n, t, tilt, color}) => {
  // precession: each arrow tips `tilt` off vertical and sweeps its azimuth over time (offset per index).
  const az = t * Math.PI * 2 + (i / n) * Math.PI * 2;
  const dir = new THREE.Vector3(Math.sin(tilt) * Math.cos(az), Math.cos(tilt), Math.sin(tilt) * Math.sin(az));
  const q = new THREE.Quaternion().setFromUnitVectors(UP, dir);           // orient the arrow to `dir`
  const x = (i / (n - 1) - 0.5) * 8;
  return (
    <group position={[x, 0, 0]} quaternion={q}>
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.04, 0.04, 1, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
      </mesh>
      <mesh position={[0, 1.05, 0]}>
        <coneGeometry args={[0.13, 0.28, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
      </mesh>
    </group>
  );
};

export const SpinField: React.FC<{
  theme: {bg: string; fg: string; accent: string};
  componentProps: {count?: number; tiltDeg?: number};
  reducedMotion?: boolean;
  durationInFrames: number;
}> = ({theme, componentProps, reducedMotion}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width, height} = useVideoConfig();
  const n = componentProps.count ?? 16;
  const tilt = ((componentProps.tiltDeg ?? 28) * Math.PI) / 180;
  const t = reducedMotion ? 0 : interpolate(frame, [0, durationInFrames], [0, 1]);
  return (
    <AbsoluteFill style={{background: theme.bg}}>
      <ThreeCanvas width={width} height={height} camera={{position: [0, 2.5, 11], fov: 45}}>
        <ambientLight intensity={0.6} />
        <pointLight position={[6, 8, 6]} intensity={80} />
        {Array.from({length: n}).map((_, i) => (
          <Arrow key={i} i={i} n={n} t={t} tilt={tilt} color={theme.accent} />
        ))}
      </ThreeCanvas>
    </AbsoluteFill>
  );
};
```

A **2D bespoke beat** is just as valid — return DOM/SVG/CSS (springy glossy spheres, an animated
SVG `path`), no `ThreeCanvas` needed. Reach for R3F only when the beat is genuinely 3D.

## What the pipeline does for you (and what it checks)

- **`_stage_bespoke`** (render pre-pass) copies each *used* `out_dir/bespoke/*.tsx` into
  `remotion/src/bespoke/` and regenerates `registry.ts` (name → module). Stale staged files from a
  prior render are removed; the registry is rewritten every render (empty map when no beat uses a
  component). A missing file or unsafe name **fails the render loud**.
- **GL** is auto-enabled (`--gl=angle`/`swangle`) for a deck with any `component` scene, so a WebGL
  beat isn't black-framed.
- **`validate.py`** gates the WIRING deterministically: bare-identifier name, file exists under
  `out_dir/bespoke/`, exports `<Name>` or default, `componentProps` is an object, and no
  self-rendered captions/audio. It **cannot** judge the component's visual interior — that's
  rendered-frame review (the `design-critic`'s D12, from `_keyframes/scene_NN.png`), exactly like
  any hero beat's look.
- **The registry** (`remotion/src/bespoke/`) is a per-project staging area: staged `*.tsx` are
  gitignored, only the empty default `registry.ts` is tracked. Your component lives with your
  project (`out_dir`), not in the skill.

## Failure modes (all fail loud)

- Component set but `out_dir/bespoke/<Name>.tsx` missing → `validate` + render error.
- File exports neither `<Name>` nor default → `validate` error ("renders BLANK").
- Unsafe name (`../x`, `foo-bar`, `1x`) → `validate` + render error (it's a filename + import).
- Component renders its own `<Captions>`/`<Audio>` → `validate` warns (double captions/audio).
- Unregistered name at render (shouldn't happen via the pipeline) → Scene.tsx throws with the fix.
