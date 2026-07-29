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
import type {Theme} from '../Video';
import type {CaptionSeg} from '../Captions';
import {Captions} from '../Captions';
import {Finish} from '../theme/Finish';

export type Plane3D = {
  kind?: 'plane' | 'bars'; // a 3D element: a plane (default) or an extruded bar chart
  color?: string;
  src?: string; // image/screenshot -> textured onto a REAL 3D mesh (true perspective, not a flat overlay)
  position: [number, number, number];
  rotation?: [number, number, number];
  size?: [number, number]; // world units of the plane (default [3, 1.8])
  data?: number[]; // bars: values (drive bar heights)
  labels?: string[]; // bars: optional per-bar labels
};

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
const TexturedPlane: React.FC<{tex?: THREE.Texture; size: [number, number]; position: [number, number, number]; rotation: [number, number, number]; theme: Theme}> = ({tex, size, position, rotation, theme}) => {
  if (!tex) {
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
      {/* UNLIT: a UI screen emits its own image — show the screenshot at its true pixel colours, not
          darkened by scene lighting. toneMapped:false keeps the colours accurate. */}
      <meshBasicMaterial map={tex} toneMapped={false} />
    </mesh>
  );
};

// A real extruded 3D BAR CHART — boxes with genuine depth the orbit camera reveals; data drives heights;
// each bar GROWS from the floor over the scene (frame-driven, eased staggered). Born-in-3D data-viz, not a
// flat chart on a plane. Lit (meshStandardMaterial) so the depth reads via shading.
const Bars3D: React.FC<{data: number[]; frame: number; durationInFrames: number; accent: string; accent2: string}> = ({data, frame, durationInFrames, accent, accent2}) => {
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
        return (
          <mesh key={i} position={[x, -1.3 + h / 2, 0]}>
            <boxGeometry args={[bw, h, bw]} />
            <meshStandardMaterial color={i === data.length - 1 ? accent : accent2} metalness={0.1} roughness={0.55} />
          </mesh>
        );
      })}
    </group>
  );
};
export type Camera3DKey = {atFrame: number; yaw: number; pitch: number; radius: number; height: number; easing?: string};

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
}> = ({planes, camera3d, theme, captions, audio, captionFontPx, reducedMotion, fadeInFrames, fadeOutFrames}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const dur = Math.max(1, durationInFrames);
  const keys = camera3d && camera3d.length ? camera3d : [{atFrame: 0, yaw: -0.6, pitch: 0, radius: 7, height: 4}];
  // Load plane textures HERE (DOM reconciler) so the render waits; pass the ready textures into the canvas.
  const srcs = planes.map((p) => p.src).filter((s): s is string => !!s);
  const textures = usePlaneTextures(srcs);

  // scene-edge fade (2D overlay — same semantics as the other tiers)
  const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const fi = Math.min(fadeInFrames || 0, dur), fo = Math.min(fadeOutFrames || 0, dur);
  const fadeOpacity = 1 - Math.min(fi > 0 ? interpolate(frame, [0, fi], [0, 1], clamp) : 1,
                                   fo > 0 ? interpolate(frame, [dur - fo, dur], [1, 0], clamp) : 1);

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg}}>
      <ThreeCanvas width={width} height={height} style={{backgroundColor: theme.bg}} camera={{fov: 45, position: [0, keys[0].height, keys[0].radius]}}>
        <ambientLight intensity={0.55} />
        <directionalLight position={[5, 9, 4]} intensity={1.3} />
        <pointLight position={[-5, 3, -3]} intensity={0.5} color={theme.accent2} />
        <CameraRig keys={keys} reduced={!!reducedMotion} />
        {/* ground plane — real perspective floor receding to a vanishing point */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.3, 0]}>
          <planeGeometry args={[40, 40]} />
          <meshStandardMaterial color={theme.surface || theme.bg} />
        </mesh>
        {planes.map((p, i) =>
          p.kind === 'bars' && p.data ? (
            <group key={i} position={p.position} rotation={p.rotation || [0, 0, 0]}>
              <Bars3D data={p.data} frame={frame} durationInFrames={dur} accent={theme.accent} accent2={theme.accent2} />
            </group>
          ) : p.src ? (
            <TexturedPlane key={i} tex={textures[p.src]} size={p.size || [3, 1.8]} position={p.position} rotation={p.rotation || [0, 0, 0]} theme={theme} />
          ) : (
            <mesh key={i} position={p.position} rotation={p.rotation || [0, 0, 0]}>
              <planeGeometry args={p.size || [3, 1.8]} />
              <meshStandardMaterial color={p.color || theme.accent} />
            </mesh>
          )
        )}
      </ThreeCanvas>

      {/* 2D overlays on top of the canvas — grade/grain/vignette, edge fade, captions, audio */}
      <Finish frame={frame} theme={theme} />
      <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: theme.bg, opacity: fadeOpacity}} />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
