// P6 — the TRUE-3D hero tier (React Three Fiber under Remotion). For what the CSS-3D card-plane rig
// structurally cannot do: a 90° top-down / full-orbit / crane camera over content planes at real depth,
// with real lighting and occlusion. Opt-in per scene (`type:"cinematic3d"`); renders inside the same
// Video timeline as the 2D scenes. REQUIRES the render to pass `--gl=angle` (render_remotion adds it when
// any 3D scene is present) — without a GL renderer headless Chrome has no WebGL and the scene is black.
//
// Everything is a pure function of useCurrentFrame() (deterministic). The 2D finish (grade/grain/vignette)
// + captions + audio ride ON TOP as normal Remotion layers, outside the canvas.

import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import type {Theme} from '../Video';
import type {CaptionSeg} from '../Captions';
import {Captions} from '../Captions';
import {Finish} from '../theme/Finish';

export type Plane3D = {
  color?: string;
  position: [number, number, number];
  rotation?: [number, number, number];
  size?: [number, number];
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
        {planes.map((p, i) => (
          <mesh key={i} position={p.position} rotation={p.rotation || [0, 0, 0]}>
            <planeGeometry args={p.size || [3, 1.8]} />
            <meshStandardMaterial color={p.color || theme.accent} />
          </mesh>
        ))}
      </ThreeCanvas>

      {/* 2D overlays on top of the canvas — grade/grain/vignette, edge fade, captions, audio */}
      <Finish frame={frame} theme={theme} />
      <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: theme.bg, opacity: fadeOpacity}} />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
