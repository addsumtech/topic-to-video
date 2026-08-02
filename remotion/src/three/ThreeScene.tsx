// P6 — the TRUE-3D hero tier (React Three Fiber under Remotion). For what the CSS-3D card-plane rig
// structurally cannot do: a 90° top-down / full-orbit / crane camera over content planes at real depth,
// with real lighting and occlusion. Opt-in per scene (`type:"cinematic3d"`); renders inside the same
// Video timeline as the 2D scenes. REQUIRES the render to pass `--gl=angle` (render_remotion adds it when
// any 3D scene is present) — without a GL renderer headless Chrome has no WebGL and the scene is black.
//
// Everything is a pure function of useCurrentFrame() (deterministic). The 2D finish (grade/grain/vignette)
// + captions + audio ride ON TOP as normal Remotion layers, outside the canvas.

import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate, Easing, delayRender, continueRender} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
// Film-look POST stack (pinned v2 line — @react-three/postprocessing@2.19.1 for R3F v8 / React 18). Runs
// deterministically under @remotion/three (ThreeCanvas forces frameloop='never' + advance() per frame).
import {EffectComposer, DepthOfField, Bloom, ToneMapping, SMAA} from '@react-three/postprocessing';
import {ToneMappingMode} from 'postprocessing';
import type {Theme} from '../Video';
import type {CaptionSeg} from '../Captions';
import {Captions} from '../Captions';
import {Finish} from '../theme/Finish';

export type Plane3D = {
  kind?: 'plane' | 'bars' | 'stack'; // a plane (default) / a bar chart / an accreting cube stack (`text` -> a plane)
  color?: string;
  src?: string; // image/screenshot/rasterized-text -> textured onto a REAL 3D mesh (true perspective)
  alpha?: boolean; // the texture has transparency (a rasterized-text PNG) -> transparent material
  billboard?: boolean; // face the camera (text labels) — else a fixed-facing plane goes edge-on when orbited
  position: [number, number, number];
  rotation?: [number, number, number];
  size?: [number, number]; // world units of the plane (default [3, 1.8])
  data?: number[]; // bars/stack: values (drive bar heights / cube counts)
  labels?: string[]; // per-column category labels — consumed by render_remotion._rasterize_text3d (which
  //                    emits billboarded label PLANES), NOT read here; kept on the type for the props shape.
};

// NOTE ON 3D TEXT: troika/drei <Text> renders BLANK under Remotion — it generates its glyph SDF
// ASYNCHRONOUSLY inside the R3F canvas (a layer below font loading; a DOM-level preloadFont doesn't fix
// it), and the capture happens before it syncs. So a `kind:"text"` element is RASTERIZED to a transparent
// PNG at build (PIL + the bundled font, in render_remotion) and textured onto a plane here — reusing the
// proven DOM-level texture path, no troika. `alpha:true` selects a transparent material.

// Load all plane image textures at the DOM level (Remotion's reconciler) so delayRender/continueRender
// actually make the render WAIT — the SAME pattern fails inside the R3F canvas children (a separate
// reconciler whose effects/delayRender aren't synced to the frame capture; verified: it renders blank).
// The ready THREE.Texture objects are passed DOWN into the canvas meshes, which then just consume them.
function usePlaneTextures(srcs: string[]): Record<string, THREE.Texture> {
  const [textures, setTextures] = React.useState<Record<string, THREE.Texture>>({});
  const [handle] = React.useState(() => (srcs.length ? delayRender('3d plane textures') : null));
  React.useEffect(() => {
    if (!srcs.length) return;
    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin('anonymous'); // WebGL needs a CORS-clean image to avoid a tainted texture
    const out: Record<string, THREE.Texture> = {};
    let done = 0;
    const finish = () => {
      done += 1;
      if (done === srcs.length) {
        setTextures(out);
        if (handle != null) continueRender(handle);
      }
    };
    srcs.forEach((s) =>
      loader.load(staticFile(s), (t) => {
        t.colorSpace = THREE.SRGBColorSpace;
        out[s] = t;
        finish();
      }, undefined, finish), // a failed load still resolves the gate (never hang the render)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return textures;
}

// A plane textured with a real screenshot/image, living in true 3D (the camera orbits it with real
// perspective + lighting) — NOT a flat 2D overlay. Consumes an ALREADY-LOADED texture (loaded at the DOM
// level by usePlaneTextures). If the texture isn't ready/failed, renders a dark placeholder plane.
const TexturedPlane: React.FC<{tex?: THREE.Texture; size: [number, number]; position: [number, number, number]; rotation: [number, number, number] | THREE.Euler; theme: Theme; alpha?: boolean}> = ({tex, size, position, rotation, theme, alpha}) => {
  if (!tex) {
    // a rasterized-text plane has nothing to show without its texture -> render nothing (not a dark rect)
    if (alpha) return null;
    return (
      <mesh position={position} rotation={rotation}>
        <planeGeometry args={size} />
        <meshStandardMaterial color={theme.surface || theme.bg} />
      </mesh>
    );
  }
  return (
    <mesh position={position} rotation={rotation}>
      <planeGeometry args={size} />
      {/* UNLIT: a UI screen / text label emits its own image — true pixel colours, not scene-lit.
          alpha (a rasterized-text PNG) -> transparent so only the glyphs show, no black card. */}
      <meshBasicMaterial map={tex} toneMapped={false} transparent={!!alpha} depthWrite={!alpha} />
    </mesh>
  );
};

// A real extruded 3D BAR CHART — boxes with genuine depth the orbit camera reveals; data drives heights;
// each bar GROWS from the floor over the scene (frame-driven, eased staggered). Born-in-3D data-viz, not a
// flat chart on a plane. Lit (meshStandardMaterial) so the depth reads via shading.
const Bars3D: React.FC<{data: number[]; frame: number; durationInFrames: number; accent: string; accent2: string; glow?: boolean}> = ({data, frame, durationInFrames, accent, accent2, glow}) => {
  const max = Math.max(1e-6, ...data.map((v) => Math.abs(v)));
  const bw = 0.62, gap = 0.42, maxH = 2.6; // bar width / gap / tallest bar (world units)
  const total = data.length * bw + (data.length - 1) * gap;
  const growStart = Math.round(durationInFrames * 0.1);
  const growSpan = Math.max(1, Math.round(durationInFrames * 0.45));
  return (
    <group>
      {data.map((v, i) => {
        const full = (Math.abs(v) / max) * maxH;
        const stagger = growStart + i * 4;
        const t = Math.max(0, Math.min(1, (frame - stagger) / growSpan));
        const e = EASE.out(t); // ease-out grow
        const h = Math.max(0.001, full * e);
        const x = -total / 2 + bw / 2 + i * (bw + gap);
        const isLast = i === data.length - 1;
        return (
          <mesh key={i} position={[x, -1.3 + h / 2, 0]} castShadow receiveShadow>
            <boxGeometry args={[bw, h, bw]} />
            {/* the RESULT bar glows via HDR emissive (>1) so selective Bloom picks only it; toneMapped=false
                keeps the colour out of [0,1] so it survives to the composer. Only when filmLook is on. */}
            <meshStandardMaterial color={isLast ? accent : accent2}
              emissive={glow && isLast ? accent : '#000000'} emissiveIntensity={glow && isLast ? 2.4 : 0}
              toneMapped={!(glow && isLast)} metalness={0.1} roughness={0.55} />
          </mesh>
        );
      })}
    </group>
  );
};
// Tilt is driven by height + radius (a high/short crane looks down); there is deliberately NO `pitch`
// field — the camera always lookAt(0,0,0), so a pitch value would silently no-op.
// ACCRETING CUBE STACK — data[c] unit cubes per column, stacking bottom-up cube-by-cube (each slides down
// + scales in on its own frame slice). "accumulation has MASS" — the orbit camera reveals real depth. The
// layout constants MUST match render_remotion._STACK_* so rasterized per-column totals sit on their stacks.
const STACK_U = 0.5, STACK_GAP = 0.5, STACK_BASE_Y = -1.3;
const STACK_MAX_CUBES = 50; // per-column safety cap (see Stack3D) — validate warns above ~40
const Stack3D: React.FC<{data: number[]; frame: number; durationInFrames: number; accent: string; accent2: string; glow?: boolean}> = ({data, frame, durationInFrames, accent, accent2, glow}) => {
  const total = data.length * STACK_U + (data.length - 1) * STACK_GAP;
  const growStart = Math.round(durationInFrames * 0.1);
  let order = 0;
  return (
    <group>
      {data.map((cnt, c) => {
        const x = -total / 2 + STACK_U / 2 + c * (STACK_U + STACK_GAP);
        // SAFETY CAP: one shadow-casting mesh PER UNIT, so a large count (a realistic "420 customers")
        // would spawn hundreds of meshes AND stagger past the scene's end (never finishing). `stack` is for
        // SMALL countable accumulation; validate warns the author toward `bars` for magnitudes — this bounds
        // the render so a mistake degrades gracefully instead of melting it.
        const n = Math.min(STACK_MAX_CUBES, Math.max(0, Math.round(cnt)));
        return Array.from({length: n}).map((_, k) => {
          const my = order++;
          const t = Math.max(0, Math.min(1, (frame - (growStart + my * 3)) / 6));
          const e = EASE.out(t);
          if (e <= 0) return null;
          const isTop = k === n - 1;
          return (
            <mesh key={`${c}-${k}`} position={[x, STACK_BASE_Y + STACK_U / 2 + k * STACK_U + (1 - e) * 1.2, 0]} scale={[e, e, e]} castShadow receiveShadow>
              <boxGeometry args={[STACK_U, STACK_U, STACK_U]} />
              <meshStandardMaterial color={isTop ? accent : accent2}
                emissive={glow && isTop ? accent : '#000000'} emissiveIntensity={glow && isTop ? 2.2 : 0}
                toneMapped={!(glow && isTop)} metalness={0.1} roughness={0.55} />
            </mesh>
          );
        });
      })}
    </group>
  );
};
export type Camera3DKey = {atFrame: number; yaw: number; radius: number; height: number; easing?: string};

const EASE: Record<string, (n: number) => number> = {
  linear: Easing.linear, in: Easing.in(Easing.cubic), out: Easing.out(Easing.cubic), inout: Easing.inOut(Easing.cubic),
};
function lerpKey(keys: Camera3DKey[], frame: number, get: (k: Camera3DKey) => number): number {
  const first = keys[0];
  if (keys.length === 1 || frame <= first.atFrame) return get(first);
  const last = keys[keys.length - 1];
  if (frame >= last.atFrame) return get(last);
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1];
    if (frame >= a.atFrame && frame <= b.atFrame) {
      const t = (EASE[b.easing || 'inout'] || EASE.inout)((frame - a.atFrame) / Math.max(1, b.atFrame - a.atFrame));
      return get(a) + (get(b) - get(a)) * t;
    }
  }
  return get(last);
}

// A TRUE billboard rotation: face the camera in BOTH yaw AND pitch, so a label never foreshortens or leans
// back under a crane / top-down angle (yaw-only billboarding does). The camera orbits the origin at
// (yaw, radius, height); a plane at p turns to look straight down the ray from p to the camera. Returns a
// THREE.Euler with order 'YXZ' (yaw THEN pitch, the FPS-camera order) so combining the two adds NO roll —
// default 'XYZ' order visibly tilts the word at mid-orbit when both angles are non-zero.
function billboardEuler(
  p: [number, number, number], camYaw: number, camHeight: number, camRadius: number,
): THREE.Euler {
  const camX = Math.sin(camYaw) * camRadius, camZ = Math.cos(camYaw) * camRadius;
  const dx = camX - p[0], dz = camZ - p[2], dy = camHeight - p[1];
  const yaw = Math.atan2(dx, dz);
  const pitch = Math.atan2(dy, Math.hypot(dx, dz));
  return new THREE.Euler(-pitch, yaw, 0, 'YXZ'); // rotate.x = -pitch tilts the +Z face UP toward the camera
}

// Frame-driven orbit/crane camera: yaw around the target, at a keyframed radius + height. Reduced motion
// freezes at the first keyframe. This is the move CSS-3D cannot make (no keystone limit in real 3D).
const CameraRig: React.FC<{keys: Camera3DKey[]; reduced: boolean}> = ({keys, reduced}) => {
  const frame = useCurrentFrame();
  const camera = useThree((s) => s.camera);
  const f = reduced ? keys[0].atFrame : frame;
  const yaw = lerpKey(keys, f, (k) => k.yaw);
  const radius = lerpKey(keys, f, (k) => k.radius);
  const height = lerpKey(keys, f, (k) => k.height);
  camera.position.set(Math.sin(yaw) * radius, height, Math.cos(yaw) * radius);
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();
  return null;
};

// ── LIGHT AS A MOVING CHARACTER ──────────────────────────────────────────────────────────────────────
// A frame-driven light rig (pure fn of useCurrentFrame): the KEY + its contact shadow SWEEP across the
// shot, a travelling SPECULAR glint crosses the front, a RIM/backlight pops the silhouette, and the whole
// rig RAMPS out of a per-register mood floor (a noir/void beat opens near-black and lifts in — the
// lighting-driven reveal a static rig can't do). Bound to a lighting MOOD per style.
type Mood = 'studio' | 'noir' | 'void' | 'product';
const STYLE_TO_MOOD: Record<string, Mood> = {
  swiss: 'studio', bauhaus: 'studio', memphis: 'studio', risograph: 'studio', cartographic: 'studio', watercolor: 'studio', manga: 'studio',
  noir: 'noir', editorial: 'noir', cinematic: 'noir', artdeco: 'noir',
  cyberpunk: 'void', vaporwave: 'void', terminal: 'void', blueprint: 'void', brutalism: 'void',
  glassmorphism: 'product', claymorphism: 'product',
};
const W = (_: Theme) => '#ffffff';
type Rig = {amb: number; key: number; rim: number; spec: number; fill: number; floor: number; keyY: number; rimY: number;
  keyColor: (t: Theme) => string; rimColor: (t: Theme) => string; specColor: (t: Theme) => string; fillColor: (t: Theme) => string};
// amb/key/rim/fill are 0–2 scale; spec is candela-scale (three 0.169 decay=2 eats ~1/16 at a ~4-unit subject)
const RIG: Record<Mood, Rig> = {
  // `floor` = the light level a scene OPENS at (before the reveal ramp lifts it to full). Kept non-zero so
  // every mid-film beat opens DIM-but-visible + lifts (moody), never full-black — the full dark->lit hero
  // reveal is the opt-in `reveal3d` overlay. (A 0 floor rendered frame 0 black and made shot_qa abstain.)
  studio: {amb: 0.38, key: 1.50, rim: 0.55, spec: 26, fill: 0.35, floor: 0.30, keyY: 9, rimY: 6, keyColor: W, rimColor: (t) => t.accent2, specColor: W, fillColor: (t) => t.accent2},
  noir: {amb: 0.06, key: 1.85, rim: 1.05, spec: 24, fill: 0.12, floor: 0.16, keyY: 6, rimY: 5, keyColor: () => '#fff1df', rimColor: (t) => t.accent, specColor: W, fillColor: (t) => t.accent2},
  void: {amb: 0.05, key: 1.15, rim: 1.35, spec: 20, fill: 0.10, floor: 0.14, keyY: 7, rimY: 6, keyColor: (t) => t.accent, rimColor: (t) => t.accent2, specColor: W, fillColor: (t) => t.accent},
  product: {amb: 0.46, key: 1.30, rim: 0.70, spec: 32, fill: 0.42, floor: 0.42, keyY: 8, rimY: 6, keyColor: W, rimColor: (t) => t.accent, specColor: W, fillColor: (t) => t.accent},
};
const _hexLum = (hex: string) => {
  const h = (hex || '').replace('#', '');
  if (h.length < 6) return 0.5;
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
};
// dark->lit reveal envelope (0..1 over the first ~22% of the scene); exported so the rig + the reveal
// overlay share one curve and can't drift.
export const revealEnvelope = (frame: number, dur: number) => interpolate(frame, [0, Math.round(dur * 0.22)], [0, 1],
  {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});

const LightRig: React.FC<{theme: Theme; dur: number; reduced: boolean}> = ({theme, dur, reduced}) => {
  const cf = useCurrentFrame();
  const f = reduced ? Math.round(dur * 0.5) : cf;          // freeze REVEALED + mid-sweep, never at black
  const mood: Mood = STYLE_TO_MOOD[theme.style] ?? (_hexLum(theme.bg) < 0.4 ? 'noir' : 'studio');
  const r = RIG[mood];
  const rev = revealEnvelope(f, dur);
  const revRim = interpolate(f, [0, Math.round(dur * 0.14)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const lift = r.floor + (1 - r.floor) * rev;              // intensities climb out of the mood floor
  const liftRim = r.floor * 0.5 + (1 - r.floor * 0.5) * revRim; // edge lights FIRST
  const p = Math.max(0, Math.min(1, f / Math.max(1, dur)));
  const swing = -1 + 2 * p;                                // key sweeps L->R
  return (
    <>
      <ambientLight intensity={r.amb * lift} />
      <hemisphereLight intensity={r.fill * lift} color={r.fillColor(theme)} groundColor={theme.bg} />
      {/* travelling KEY — the only shadow caster; shadows rake with the sweep */}
      <directionalLight position={[swing * 7, r.keyY, 5]} intensity={r.key * lift} color={r.keyColor(theme)}
        castShadow shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-14} shadow-camera-right={14} shadow-camera-top={14} shadow-camera-bottom={-14}
        shadow-camera-near={0.5} shadow-camera-far={44} shadow-bias={-0.0006} />
      {/* travelling SPECULAR glint — crosses the front opposite the key; decay gives a localized hotspot */}
      <pointLight position={[-swing * 5.5, 1.5, 4.5]} intensity={r.spec * lift} color={r.specColor(theme)} distance={16} decay={2} />
      {/* RIM / backlight — behind + counter-swing, pops the silhouette; leads the reveal */}
      <directionalLight position={[-swing * 4, r.rimY, -7]} intensity={r.rim * liftRim} color={r.rimColor(theme)} />
    </>
  );
};

export const ThreeScene: React.FC<{
  planes: Plane3D[];
  camera3d: Camera3DKey[];
  theme: Theme;
  captions?: CaptionSeg[];
  audio?: string | null;
  captionFontPx: number;
  reducedMotion?: boolean;
  fadeInFrames?: number;
  fadeOutFrames?: number;
  reveal3d?: boolean; // opt-in dark->lit reveal for an unlit-plane hero opener
  filmLook?: boolean; // the EffectComposer post stack (DoF + selective Bloom + ACES); default on
}> = ({planes, camera3d, theme, captions, audio, captionFontPx, reducedMotion, fadeInFrames, fadeOutFrames, reveal3d, filmLook}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const dur = Math.max(1, durationInFrames);
  // The real pipeline always supplies a crane (render_remotion._clean_camera3d synthesizes a 2-key default
  // when absent); this fallback is only for driving ThreeScene in isolation — make it the SAME moving crane
  // (height 6 -> 2.6) so an isolated render also moves, instead of a single static keyframe.
  const keys = camera3d && camera3d.length ? camera3d
    : [{atFrame: 0, yaw: -0.6, radius: 7, height: 6}, {atFrame: dur, yaw: 0.4, radius: 7, height: 2.6}];
  // Camera pose at this frame (for billboarding labels to face the camera in yaw + pitch).
  const camYaw = reducedMotion ? keys[0].yaw : lerpKey(keys, frame, (k) => k.yaw);
  const camHeight = reducedMotion ? keys[0].height : lerpKey(keys, frame, (k) => k.height);
  const camRadius = reducedMotion ? keys[0].radius : lerpKey(keys, frame, (k) => k.radius);
  // Load plane textures HERE (DOM reconciler) so the render waits; pass the ready textures into the canvas.
  // (Rasterized-text planes are just image planes with alpha — same path.)
  const srcs = planes.map((p) => p.src).filter((s): s is string => !!s);
  const textures = usePlaneTextures(srcs);

  // scene-edge fade (2D overlay — same semantics as the other tiers)
  const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const fi = Math.min(fadeInFrames || 0, dur), fo = Math.min(fadeOutFrames || 0, dur);
  const fadeOpacity = 1 - Math.min(fi > 0 ? interpolate(frame, [0, fi], [0, 1], clamp) : 1,
                                   fo > 0 ? interpolate(frame, [dur - fo, dur], [1, 0], clamp) : 1);

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg}}>
      <ThreeCanvas shadows width={width} height={height} style={{backgroundColor: theme.bg}} camera={{fov: 45, position: [0, keys[0].height, keys[0].radius]}}>
        {/* opaque scene background — the composer's input buffer replaces the transparent (CSS-bg) region
            above the horizon with BLACK; an explicit background keeps the whole graded frame consistent. */}
        <color attach="background" args={[theme.bg]} />
        {/* depth fog: the floor's far edge + distant geometry DISSOLVE into the bg instead of ending at a
            hard 40-unit horizon — the atmospheric falloff that makes a 3D space read as large, not a toy. */}
        <fog attach="fog" args={[theme.bg, 11, 33]} />
        {/* LIGHT AS A MOVING CHARACTER — the travelling key/rim/specular rig (replaces the 3 static lights);
            ramps out of a per-register mood floor so a noir/void beat opens near-black and lifts in. */}
        <LightRig theme={theme} dur={dur} reduced={!!reducedMotion} />
        <CameraRig keys={keys} reduced={!!reducedMotion} />
        {/* ground plane — real perspective floor that RECEIVES the contact shadows (dropped a hair below the
            bar feet so the shadow reads and the coplanar faces don't z-fight). */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.32, 0]} receiveShadow>
          <planeGeometry args={[40, 40]} />
          <meshStandardMaterial color={theme.surface || theme.bg} />
        </mesh>
        {planes.map((p, i) =>
          p.kind === 'bars' && p.data ? (
            <group key={i} position={p.position} rotation={p.rotation || [0, 0, 0]}>
              <Bars3D data={p.data} frame={frame} durationInFrames={dur} accent={theme.accent} accent2={theme.accent2} glow={filmLook !== false} />
            </group>
          ) : p.kind === 'stack' && p.data ? (
            <group key={i} position={p.position} rotation={p.rotation || [0, 0, 0]}>
              <Stack3D data={p.data} frame={frame} durationInFrames={dur} accent={theme.accent} accent2={theme.accent2} glow={filmLook !== false} />
            </group>
          ) : p.src ? (
            <TexturedPlane key={i} tex={textures[p.src]} size={p.size || [3, 1.8]} position={p.position}
              rotation={p.billboard ? billboardEuler(p.position, camYaw, camHeight, camRadius) : p.rotation || [0, 0, 0]}
              theme={theme} alpha={p.alpha} />
          ) : (
            <mesh key={i} position={p.position} rotation={p.rotation || [0, 0, 0]} castShadow>
              <planeGeometry args={p.size || [3, 1.8]} />
              <meshStandardMaterial color={p.color || theme.accent} />
            </mesh>
          )
        )}
        {/* FILM-LOOK POST — real optical DoF (bokeh) + selective Bloom (only HDR-emissive elements glow) +
            ACES tone map (matches R3F's default the composer bypasses) + SMAA. Vignette + grain stay in the
            2D Finish (one owner — no double vignette). Deterministic: DoF focus is geometric from the pose,
            Bloom/tone are stateless. Opt-in (default on); resolutionScale 0.5 + multisampling 0 keep it cheap. */}
        {filmLook !== false ? (
          <EffectComposer multisampling={0} frameBufferType={THREE.HalfFloatType} enableNormalPass={false} stencilBuffer={false}>
            <DepthOfField target={[0, 0, 0]} worldFocusRange={4} bokehScale={3} resolutionScale={0.5} />
            <Bloom mipmapBlur luminanceThreshold={1.0} luminanceSmoothing={0.2} intensity={0.9} radius={0.7} />
            <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
            <SMAA />
          </EffectComposer>
        ) : null}
      </ThreeCanvas>

      {/* opt-in dark->lit reveal for an unlit-plane hero: a black scrim that lifts in lockstep with the rig
          (shares revealEnvelope so they can't drift). Default OFF — an ordinary 3D scene opens normally. */}
      {reveal3d ? (
        <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: '#000',
          opacity: 1 - revealEnvelope(reducedMotion ? Math.round(dur * 0.5) : frame, dur)}} />
      ) : null}

      {/* 2D overlays on top of the canvas — grade/grain/vignette, edge fade, captions, audio */}
      <Finish frame={frame} theme={theme} />
      <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: theme.bg, opacity: fadeOpacity}} />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
