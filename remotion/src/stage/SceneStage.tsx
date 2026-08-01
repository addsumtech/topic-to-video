// SceneStage: the SHOT-BASED renderer. A scene is a SET (elements placed once in a 3D world) plus an
// ordered LIST of shots; the camera moves between framings of that set with continuity across cuts.
//
// Rendering reuses the proven CSS-3D perspective rig (perspective + preserve-3d, DoF, flatten
// discipline) from Camera.tsx's CinematicScene3D — the only new thing here is that the camera pose
// comes from the multi-shot timeline (stage/camera.ts), not a single lens keyframe list.

import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Theme} from '../Video';
import type {CaptionSeg} from '../Captions';
import {Captions} from '../Captions';
import {Finish} from '../theme/Finish';
import {Element, type ElementData} from './elements';
import type {ShotSpec, Position} from './shots';
import {computeTimeline, poseAtFrame} from './camera';

// Stage data schema (from storyboard.json stage) — elements placed ONCE.
export type StageData = {
  elements: ElementData[];
  perspective?: number; // CSS perspective px (default 1300)
};

export type SceneStageProps = {
  stage: StageData;
  shots: ShotSpec[];
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
  shots,
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

  // Element position registry for camera targeting.
  const registry = new Map<string, Position>();
  for (const el of stage.elements) registry.set(el.id, el.position);

  // Resolve the shot list into a pose timeline, then read the pose for THIS frame (reduced motion =>
  // freeze at the first shot's start pose).
  const timeline = computeTimeline(shots, registry, width / height);
  const pose = reduced && timeline.length
    ? timeline[0].startPose
    : poseAtFrame(timeline, frame);
  const focusZ = pose.focusZ;

  // Same 3D rig as CinematicScene3D. The `world` node is the preserve-3d ancestor — NO opacity/filter
  // here (would silently flatten all translateZ; guarded by tests/test_remotion_3d.py).
  const world: React.CSSProperties = {
    position: 'absolute',
    left: width / 2,
    top: height / 2,
    width: 0,
    height: 0,
    transformStyle: 'preserve-3d',
    transform: `scale(${pose.zoom}) translateZ(${pose.dolly}px) rotateX(${pose.pitch}deg) rotateY(${pose.yaw}deg) rotateZ(${pose.roll}deg)`,
  };

  const fade = 1 - edgeOpacity(frame, dur, fadeInFrames, fadeOutFrames);

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden'}}>
      <AbsoluteFill style={{perspective: `${stage.perspective || 1300}px`, perspectiveOrigin: '50% 46%'}}>
        <div style={world}>
          {stage.elements.map((el) => {
            // rack focus: soften planes off the focal z. The blur is passed INTO Element, which applies it
            // on an inner leaf — NOT on a wrapper here. A wrapper div (default transform-style: flat) placed
            // above the element's translate3d node would collapse all per-element depth to one plane.
            const blur = focusZ != null ? computeDofBlur(el.position[2], focusZ) : 0;
            return (
              <Element key={el.id} element={el} theme={theme} frame={frame} reducedMotion={reduced} blur={blur} />
            );
          })}
        </div>
      </AbsoluteFill>

      {/* OUTER 2D overlays (never on the preserve-3d chain). */}
      <Finish frame={frame} theme={theme} />
      <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: theme.bg, opacity: fade}} />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};

// Depth-of-field blur for a plane at distance from the focal z (matches Camera.tsx planeBlur).
function computeDofBlur(elementZ: number, focusZ: number): number {
  return Math.min(14, Math.abs(elementZ - focusZ) / 120);
}

// Scene-edge fade (matches Camera.tsx edgeOpacity — clamped interpolate, strictly increasing ranges).
function edgeOpacity(frame: number, dur: number, fadeInFrames?: number, fadeOutFrames?: number): number {
  const fi = Math.min(fadeInFrames || 0, dur);
  const fo = Math.min(fadeOutFrames || 0, dur);
  const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const fadeIn = fi > 0 ? interpolate(frame, [0, fi], [0, 1], clamp) : 1;
  const fadeOut = fo > 0 ? interpolate(frame, [dur - fo, dur], [1, 0], clamp) : 1;
  return Math.min(fadeIn, fadeOut);
}
