import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Theme} from './Video';
import {Captions, CaptionSeg} from './Captions';

// ── Cinematic props (additive to SceneData; see scripts/render_remotion.py build_props) ────────────
export type CameraKeyframe = {
  atFrame: number;             // integer frame index (0..durationInFrames)
  x: number;                   // camera target centre, normalised 0..1
  y: number;
  zoom: number;                // camera scale (1 = neutral)
  easing?: string;             // segment easing INTO this keyframe: linear|in|out|inout
};

export type Layer = {
  kind: string;                // 'fill' | 'grid' | 'hero' | 'panel' | 'image'
  parallax?: number;           // depth factor: <1 far, >1 near (docx: bg≈0.8, fg≈1.2–1.4)
  src?: string;                // image (kind:'image'), path relative to the public dir
  kicker?: string;             // panel
  title?: string;              // panel
  sub?: string;                // panel
  text?: string;               // hero big word
  align?: string;              // 'left' (default) | 'center'
  revealAtFrame?: number;      // ONE eased reveal on this layer's secondary content (sub / body)
};

// Easing families — the whole point of "cinematic" vs the free path's linear Ken Burns.
const EASE: Record<string, (n: number) => number> = {
  linear: Easing.linear,
  in: Easing.in(Easing.cubic),
  out: Easing.out(Easing.cubic),
  inout: Easing.inOut(Easing.cubic),
};

// Resolve the eased camera state at a frame from a keyframe list (deterministic; frame-driven only).
function cameraAt(kfs: CameraKeyframe[], frame: number): {x: number; y: number; zoom: number} {
  const first = kfs[0];
  if (kfs.length === 1 || frame <= first.atFrame) return {x: first.x, y: first.y, zoom: first.zoom};
  const last = kfs[kfs.length - 1];
  if (frame >= last.atFrame) return {x: last.x, y: last.y, zoom: last.zoom};
  for (let i = 0; i < kfs.length - 1; i++) {
    const a = kfs[i];
    const b = kfs[i + 1];
    if (frame >= a.atFrame && frame <= b.atFrame) {
      const span = Math.max(1, b.atFrame - a.atFrame);
      const ease = EASE[b.easing || 'inout'] || EASE.inout;
      const t = ease((frame - a.atFrame) / span);
      return {
        x: a.x + (b.x - a.x) * t,
        y: a.y + (b.y - a.y) * t,
        zoom: a.zoom + (b.zoom - a.zoom) * t,
      };
    }
  }
  return {x: last.x, y: last.y, zoom: last.zoom};
}

// One depth plane, transformed by the shared camera scaled by its own parallax factor.
const PlaneView: React.FC<{
  layer: Layer;
  cam: {x: number; y: number; zoom: number};
  theme: Theme;
  frame: number;
  reduced: boolean;
}> = ({layer, cam, theme, frame, reduced}) => {
  const {width, height} = useVideoConfig();
  const p = layer.parallax ?? 1;
  // world moves opposite the camera, scaled by depth; near planes (higher p) also zoom more.
  const panX = cam.x - 0.5;
  const panY = cam.y - 0.5;
  const tx = -panX * p * width;
  const ty = -panY * p * height;
  const scale = 1 + (cam.zoom - 1) * p;
  const transform = `translate(${tx}px, ${ty}px) scale(${scale})`;

  // OVERSCAN so a plane's parallax translate never reveals a hard edge of full-bleed content.
  const bleed: React.CSSProperties = {
    position: 'absolute',
    left: '-15%',
    top: '-15%',
    width: '130%',
    height: '130%',
  };

  const rf = layer.revealAtFrame ?? 0;
  const rev = reduced
    ? 1
    : interpolate(frame, [rf, rf + 12], [0, 1], {
        easing: Easing.out(Easing.cubic),
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  let content: React.ReactNode = null;
  if (layer.kind === 'fill') {
    content = (
      <div
        style={{
          ...bleed,
          background: `radial-gradient(120% 120% at 50% 38%, ${theme.bg} 0%, ${theme.bg} 55%, #00000055 100%)`,
        }}
      />
    );
  } else if (layer.kind === 'grid') {
    content = (
      <div
        style={{
          ...bleed,
          opacity: 0.16,
          backgroundImage: `linear-gradient(${theme.muted} 1px, transparent 1px), linear-gradient(90deg, ${theme.muted} 1px, transparent 1px)`,
          backgroundSize: '120px 120px',
        }}
      />
    );
  } else if (layer.kind === 'hero') {
    content = (
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div
          style={{
            color: theme.fg,
            opacity: 0.08,
            fontSize: 460,
            fontWeight: 800,
            letterSpacing: -8,
            fontFamily: '"JetBrains Mono", "SF Mono", Menlo, monospace',
          }}
        >
          {layer.text || ''}
        </div>
      </AbsoluteFill>
    );
  } else if (layer.kind === 'panel') {
    const centre = layer.align === 'center';
    content = (
      <AbsoluteFill
        style={{
          alignItems: centre ? 'center' : 'flex-start',
          justifyContent: 'center',
          padding: centre ? 0 : '0 0 0 160px',
        }}
      >
        <div style={{maxWidth: 1180, textAlign: centre ? 'center' : 'left'}}>
          {layer.kicker ? (
            <div
              style={{
                color: theme.accent2,
                fontSize: 34,
                fontWeight: 700,
                letterSpacing: 5,
                textTransform: 'uppercase',
                marginBottom: 22,
                fontFamily: '"JetBrains Mono", "SF Mono", Menlo, monospace',
              }}
            >
              {layer.kicker}
            </div>
          ) : null}
          {layer.title ? (
            <div
              style={{
                color: theme.fg,
                fontSize: 104,
                fontWeight: 800,
                lineHeight: 1.06,
                letterSpacing: -1,
                textShadow: '0 6px 30px rgba(0,0,0,0.45)',
                fontFamily: '"JetBrains Mono", "SF Mono", Menlo, monospace',
              }}
            >
              {layer.title}
            </div>
          ) : null}
          {layer.sub ? (
            <div
              style={{
                color: theme.muted,
                fontSize: 42,
                lineHeight: 1.34,
                marginTop: 30,
                opacity: rev,
                transform: `translateY(${(1 - rev) * 16}px)`,
                fontFamily: '"JetBrains Mono", "SF Mono", Menlo, monospace',
              }}
            >
              {layer.sub}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    );
  } else if (layer.kind === 'image' && layer.src) {
    content = (
      <Img
        src={staticFile(layer.src)}
        style={{...bleed, objectFit: 'cover'}}
      />
    );
  }

  return (
    <AbsoluteFill style={{transform, transformOrigin: 'center center', overflow: 'visible'}}>
      {content}
    </AbsoluteFill>
  );
};

// A full cinematic scene: the 2.5D layer stack under one eased camera, a premium vignette, then
// captions + audio. Honours reducedMotion (camera frozen at kf0, reveals instant) and scene-edge dips.
export const CinematicScene: React.FC<{
  layers: Layer[];
  camera: CameraKeyframe[];
  theme: Theme;
  captions?: CaptionSeg[];
  audio?: string | null;
  captionFontPx: number;
  reducedMotion?: boolean;
  fadeInFrames?: number;
  fadeOutFrames?: number;
}> = ({layers, camera, theme, captions, audio, captionFontPx, reducedMotion, fadeInFrames, fadeOutFrames}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const dur = Math.max(1, durationInFrames);
  const reduced = !!reducedMotion;

  const kfs = camera && camera.length ? camera : [{atFrame: 0, x: 0.5, y: 0.5, zoom: 1}];
  const cam = reduced ? {x: kfs[0].x, y: kfs[0].y, zoom: kfs[0].zoom} : cameraAt(kfs, frame);

  const fi = Math.min(fadeInFrames || 0, dur);
  const fo = Math.min(fadeOutFrames || 0, dur);
  const fadeIn = fi > 0 ? interpolate(frame, [0, fi], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  const fadeOut = fo > 0 ? interpolate(frame, [dur - fo, dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden', opacity}}>
      {layers.map((layer, i) => (
        <PlaneView key={i} layer={layer} cam={cam} theme={theme} frame={frame} reduced={reduced} />
      ))}

      {/* cinematic vignette — soft edge darkening so the eye lands centre (docx: lighting guides focus) */}
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background: 'radial-gradient(130% 130% at 50% 45%, rgba(0,0,0,0) 52%, rgba(0,0,0,0.42) 100%)',
        }}
      />

      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
