import React from 'react';
import {AbsoluteFill, Audio, Img, staticFile, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Theme} from './Video';
import {Captions, CaptionSeg} from './Captions';
import {CinematicScene, CinematicScene3D, CameraKeyframe, LensKeyframe, Layer} from './Camera';
import {SceneStage, type StageData} from './stage/SceneStage';
import type {ShotSpec} from './stage/shots';
import {ThreeScene, type Plane3D, type Camera3DKey} from './three/ThreeScene';

export type CalloutData = {
  box: number[];           // [x0, y0, x1, y1] normalized 0..1
  style?: string;          // 'highlight' (yellow wash) | else a red target box
  label?: string | null;
  fromFrame?: number;      // appears at this frame and holds (0 = whole scene)
};

export type SceneData = {
  index: number;
  durationInFrames: number;
  image?: string | null;   // path relative to the public dir (the out_dir)
  audio?: string | null;   // path relative to the public dir
  captions?: CaptionSeg[]; // scene-local, in frames
  kenburns?: boolean;      // default true; false => static hold
  motion?: {from: number[]; to: number[]};  // Ken Burns from/to [x, y, zoom] (mirrors slide.motion)
  fit?: string;            // 'contain' (default, letterbox) | 'cover' (full-bleed)
  callouts?: CalloutData[];
  title?: string | null;
  kicker?: string | null;
  fadeInFrames?: number;   // gentle dip-in at the scene edge (from meta.transition)
  fadeOutFrames?: number;
  // CINEMATIC (opt-in): virtual-camera paths over 2.5D/3D scenes.
  // SHOT-BASED (P2): `stage` (the SET) + `shots` (ordered framings) → SceneStage (the paradigm)
  // LEGACY: `lens` → CinematicScene3D; `camera`+`layers` → CinematicScene (flat parallax)
  stage?: StageData | null;
  shots?: ShotSpec[] | null;
  camera?: CameraKeyframe[] | null;
  lens?: LensKeyframe[] | null;
  perspective?: number | null;
  layers?: Layer[] | null;
  reducedMotion?: boolean;
  // CROSS-SCENE transition INTO the next scene (P3): a marked seam that overlaps the two scenes.
  transitionToNext?: {style: string; durationInFrames: number} | null;
  transitionStyle?: string | null; // per-scene seam-look override (consumed by build_props)
  // TRUE-3D tier (P6): WebGL planes + an orbit/crane camera (renders via ThreeScene / @remotion/three).
  planes?: Plane3D[] | null;
  camera3d?: Camera3DKey[] | null;
  filmLook?: boolean; // the true-3D film-look post stack (default on)
  reveal3d?: boolean; // opt-in dark->lit reveal for a 3D hero opener
};

const CLAMP = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

export const Scene: React.FC<{scene: SceneData; theme: Theme; captionFontPx: number}> = ({
  scene,
  theme,
  captionFontPx,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const dur = Math.max(1, durationInFrames);

  // CINEMATIC DISPATCH. Shot-based (P2+): `stage` + `shot` → SceneStage; legacy: `lens` → 3D
  // perspective (real depth + camera angles); `layers` → flat parallax; else unchanged image/Ken-Burns.
  if (Array.isArray(scene.planes) && scene.planes.length) {
    return (
      <ThreeScene
        planes={scene.planes}
        camera3d={Array.isArray(scene.camera3d) ? scene.camera3d : []}
        theme={theme}
        captions={scene.captions}
        audio={scene.audio}
        captionFontPx={captionFontPx}
        reducedMotion={scene.reducedMotion}
        fadeInFrames={scene.fadeInFrames}
        fadeOutFrames={scene.fadeOutFrames}
        reveal3d={scene.reveal3d}
        filmLook={scene.filmLook}
      />
    );
  }
  if (scene.stage && Array.isArray(scene.shots) && scene.shots.length) {
    return (
      <SceneStage
        stage={scene.stage}
        shots={scene.shots}
        theme={theme}
        captions={scene.captions}
        audio={scene.audio}
        captionFontPx={captionFontPx}
        reducedMotion={scene.reducedMotion}
        fadeInFrames={scene.fadeInFrames}
        fadeOutFrames={scene.fadeOutFrames}
      />
    );
  }
  if (Array.isArray(scene.lens) && scene.lens.length && Array.isArray(scene.layers) && scene.layers.length) {
    return (
      <CinematicScene3D
        layers={scene.layers}
        lens={scene.lens}
        perspective={scene.perspective || 1300}
        theme={theme}
        captions={scene.captions}
        audio={scene.audio}
        captionFontPx={captionFontPx}
        reducedMotion={scene.reducedMotion}
        fadeInFrames={scene.fadeInFrames}
        fadeOutFrames={scene.fadeOutFrames}
      />
    );
  }
  if (Array.isArray(scene.layers) && scene.layers.length) {
    return (
      <CinematicScene
        layers={scene.layers}
        camera={Array.isArray(scene.camera) ? scene.camera : [{atFrame: 0, x: 0.5, y: 0.5, zoom: 1}]}
        theme={theme}
        captions={scene.captions}
        audio={scene.audio}
        captionFontPx={captionFontPx}
        reducedMotion={scene.reducedMotion}
        fadeInFrames={scene.fadeInFrames}
        fadeOutFrames={scene.fadeOutFrames}
      />
    );
  }

  // Ken Burns that HONOURS the authored camera (slide.motion): zoom z0->z1 (may zoom OUT) about a pan
  // anchor that moves from->to — mirrors the local zoompan instead of a hardcoded push.
  const kb = scene.kenburns !== false && !!scene.image;
  const m = scene.motion || {from: [0.5, 0.5, 1.0], to: [0.5, 0.5, 1.12]};
  const z = kb ? interpolate(frame, [0, dur], [m.from[2], m.to[2]], CLAMP) : 1;
  const ox = kb ? interpolate(frame, [0, dur], [m.from[0], m.to[0]], CLAMP) * 100 : 50;
  const oy = kb ? interpolate(frame, [0, dur], [m.from[1], m.to[1]], CLAMP) * 100 : 50;

  // scene-edge dip (matches the local renderer's dip-to-bg transitions). Separate, guarded ramps —
  // Remotion's interpolate() requires a STRICTLY increasing input range, so a 0-length edge can't be
  // folded into one 4-point range.
  const fi = Math.min(scene.fadeInFrames || 0, dur);
  const fo = Math.min(scene.fadeOutFrames || 0, dur);
  const fadeIn = fi > 0 ? interpolate(frame, [0, fi], [0, 1], CLAMP) : 1;
  const fadeOut = fo > 0 ? interpolate(frame, [dur - fo, dur], [1, 0], CLAMP) : 1;
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden', opacity}}>
      {scene.image ? (
        <Img
          src={staticFile(scene.image)}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            objectFit: scene.fit === 'cover' ? 'cover' : 'contain',
            transform: `scale(${z})`,
            transformOrigin: `${ox}% ${oy}%`,
          }}
        />
      ) : null}

      {/* graded scrim so a lower-third title + captions read on any image */}
      <AbsoluteFill
        style={{background: `linear-gradient(180deg, ${theme.bg}00 40%, ${theme.bg}b3 100%)`}}
      />

      {/* timed/static callout highlights (appear at fromFrame, hold to the end — parity with local) */}
      {(scene.callouts || []).map((co, i) => {
        if (frame < (co.fromFrame || 0) || co.box.length !== 4) return null;
        const [x0, y0, x1, y1] = co.box;
        const hl = co.style === 'highlight';
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x0 * 100}%`, top: `${y0 * 100}%`,
              width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%`,
              background: hl ? 'rgba(255,230,0,0.24)' : 'transparent',
              border: hl ? '4px solid rgba(255,200,0,0.9)' : '5px solid rgba(255,60,60,0.94)',
              borderRadius: 4,
            }}
          >
            {co.label ? (
              <div style={{
                position: 'absolute', left: 6, top: -34, color: '#fff', fontSize: 30, fontWeight: 700,
                whiteSpace: 'nowrap', textShadow: '0 2px 6px rgba(0,0,0,0.7)',
                fontFamily: 'Helvetica, Arial, "PingFang SC", sans-serif',
              }}>{co.label}</div>
            ) : null}
          </div>
        );
      })}

      {scene.kicker ? (
        <div
          style={{
            position: 'absolute', left: 96, top: 92, color: theme.accent2, fontSize: 34,
            fontWeight: 700, letterSpacing: 3, textTransform: 'uppercase',
            fontFamily: 'Helvetica, Arial, "PingFang SC", "Hiragino Sans", sans-serif',
          }}
        >
          {scene.kicker}
        </div>
      ) : null}

      {scene.title ? (
        <div
          style={{
            position: 'absolute', left: 96, right: 96, bottom: 210, color: theme.fg, fontSize: 76,
            fontWeight: 800, lineHeight: 1.12,
            fontFamily: 'Georgia, "Songti SC", "Hiragino Mincho ProN", serif',
            textShadow: '0 3px 18px rgba(0,0,0,0.5)',
          }}
        >
          {scene.title}
        </div>
      ) : null}

      {scene.captions && scene.captions.length ? (
        <Captions segments={scene.captions} fontPx={captionFontPx} />
      ) : null}

      {scene.audio ? <Audio src={staticFile(scene.audio)} /> : null}
    </AbsoluteFill>
  );
};
