// SceneStage: shot-based 3D scene renderer.
// Interprets stage + shot specification, places elements in scene-space, and executes camera motion.

import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Theme} from '../Video';
import type {CaptionSeg} from '../Captions';
import {Captions} from '../Captions';
import {Finish} from '../theme/Finish';
import type {LensKeyframe} from '../Camera';
import {Element, type ElementData} from './elements';
import {calculateShotFrame, resolveTarget, type ShotSpec, type CameraTarget, type Position} from './shots';
import {generateMotion, parseMotionPattern} from './motions';

// Stage data schema (from storyboard.json props.stage)
export type StageData = {
  elements: ElementData[];
  perspective?: number; // CSS perspective px (default 1300)
};

// SceneStage props (replaces CinematicScene3D for shot-based scenes)
export type SceneStageProps = {
  stage: StageData;
  shot: ShotSpec;
  theme: Theme;
  captions?: CaptionSeg[];
  audio?: string | null;
  captionFontPx: number;
  reducedMotion?: boolean;
  fadeInFrames?: number;
  fadeOutFrames?: number;
};

export const SceneStage: React.FC<SceneStageProps> = ({
  stage,
  shot,
  theme,
  captions,
  audio,
  captionFontPx,
  reducedMotion,
  fadeInFrames,
  fadeOutFrames,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width, height} = useVideoConfig();
  const dur = Math.max(1, durationInFrames);
  const reduced = !!reducedMotion;

  // Build element position registry for camera targeting
  const elementRegistry = new Map<string, Position>();
  for (const el of stage.elements) {
    elementRegistry.set(el.id, el.position);
  }

  // Resolve camera target
  let target: CameraTarget;
  if (shot.lens) {
    target = {kind: 'manual', lens: shot.lens};
  } else if (shot.target) {
    target = {kind: 'element', id: shot.target};
  } else if (shot.targetPos) {
    target = {kind: 'position', pos: shot.targetPos};
  } else {
    // Default: aim at stage center
    target = {kind: 'position', pos: [0, 0, -500]};
  }

  // Generate lens keyframes
  let lens: LensKeyframe[];
  if (target.kind === 'manual') {
    lens = target.lens;
  } else {
    const targetPos = resolveTarget(target, elementRegistry);
    const startFrame = calculateShotFrame(shot.type, targetPos, width / height);
    const motion = parseMotionPattern(shot.motion);
    lens = generateMotion(motion, startFrame, shot.duration, shot.easing || 'out');
  }

  // Interpolate current camera state from lens keyframes
  const kfs = lens.length ? lens : [{atFrame: 0}];
  const read = (get: (k: LensKeyframe) => number) =>
    reduced ? get(kfs[0]) : lerpField(kfs, frame, get);
  const dolly = read((k) => k.dolly || 0);
  const pitch = read((k) => k.pitch || 0);
  const yaw = read((k) => k.yaw || 0);
  const roll = read((k) => k.roll || 0);
  const zoom = read((k) => (k.zoom == null ? 1 : k.zoom));
  const hasFocus = kfs.some((k) => k.focusZ != null);
  const focusZ = hasFocus ? read((k) => (k.focusZ == null ? 0 : k.focusZ)) : null;

  // World transform (same CSS-3D rig as Camera.tsx CinematicScene3D)
  const world: React.CSSProperties = {
    position: 'absolute',
    left: width / 2,
    top: height / 2,
    width: 0,
    height: 0,
    transformStyle: 'preserve-3d',
    transform: `scale(${zoom}) translateZ(${dolly}px) rotateX(${pitch}deg) rotateY(${yaw}deg) rotateZ(${roll}deg)`,
  };

  const fade = 1 - edgeOpacity(frame, dur, fadeInFrames, fadeOutFrames);

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden'}}>
      <AbsoluteFill style={{perspective: `${stage.perspective || 1300}px`, perspectiveOrigin: '50% 46%'}}>
        <div style={world}>
          {stage.elements.map((el) => {
            // Compute depth-of-field blur if rack focus is active
            const blur = focusZ != null ? computeDofBlur(el.position[2], focusZ) : 0;
            return (
              <div
                key={el.id}
                style={{
                  filter: blur > 0 ? `blur(${blur}px)` : undefined,
                }}
              >
                <Element element={el} theme={theme} frame={frame} reducedMotion={reduced} />
              </div>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* Outer 2D overlays */}
      <Vignette />
      <Finish frame={frame} theme={theme} />
      <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: theme.bg, opacity: fade}} />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};

// Keyframe interpolation (copied from Camera.tsx lerpField)
function lerpField<T extends {atFrame: number; easing?: string}>(
  kfs: T[],
  frame: number,
  get: (k: T) => number,
): number {
  const first = kfs[0];
  if (kfs.length === 1 || frame <= first.atFrame) return get(first);
  const last = kfs[kfs.length - 1];
  if (frame >= last.atFrame) return get(last);
  for (let i = 0; i < kfs.length - 1; i++) {
    const a = kfs[i];
    const b = kfs[i + 1];
    if (frame >= a.atFrame && frame <= b.atFrame) {
      const ease = EASE[b.easing || 'inout'] || EASE.inout;
      const t = ease((frame - a.atFrame) / Math.max(1, b.atFrame - a.atFrame));
      return get(a) + (get(b) - get(a)) * t;
    }
  }
  return get(last);
}

// Easing functions (copied from Camera.tsx)
import {Easing} from 'remotion';
const EASE: Record<string, (n: number) => number> = {
  linear: Easing.linear,
  in: Easing.in(Easing.cubic),
  out: Easing.out(Easing.cubic),
  inout: Easing.inOut(Easing.cubic),
};

// Depth-of-field blur calculation
function computeDofBlur(elementZ: number, focusZ: number): number {
  return Math.min(14, Math.abs(elementZ - focusZ) / 120);
}

// Edge fade (copied from Camera.tsx)
function edgeOpacity(frame: number, dur: number, fadeInFrames?: number, fadeOutFrames?: number): number {
  const fi = Math.min(fadeInFrames || 0, dur);
  const fo = Math.min(fadeOutFrames || 0, dur);
  const fadeIn =
    fi > 0
      ? Easing.bezier(0.25, 0.1, 0.25, 1.0)((frame - 0) / fi)
      : 1;
  const fadeOut =
    fo > 0
      ? Easing.bezier(0.25, 0.1, 0.25, 1.0)((dur - frame) / fo)
      : 1;
  return Math.min(Math.max(0, fadeIn), Math.max(0, fadeOut));
}

// Vignette (copied from Camera.tsx)
const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: 'radial-gradient(130% 130% at 50% 45%, rgba(0,0,0,0) 52%, rgba(0,0,0,0.42) 100%)',
    }}
  />
);
