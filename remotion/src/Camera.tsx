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
// Two paths share this file:
//   • FLAT parallax  — a `camera` (x/y/zoom keyframes) over `layers` with a `parallax` factor. Cheap,
//     no true depth; the "cinematic-lite" fallback.
//   • 3D LENS        — a `lens` (dolly/pitch/yaw keyframes) over `layers` placed on real `z` planes
//     inside a CSS perspective rig. Delivers bird's-eye / worm's-eye / dolly-through / rack-focus that
//     flat parallax cannot. Chosen when the scene declares `lens`.
// EVERYTHING is a pure function of useCurrentFrame() — deterministic, no Date.now()/Math.random().

export type CameraKeyframe = {
  atFrame: number;
  x: number;
  y: number;
  zoom: number;
  easing?: string;
};

export type LensKeyframe = {
  atFrame: number;
  dolly?: number;   // world translateZ px (+ pushes the world toward the lens)
  pitch?: number;   // rotateX deg (+ look down / bird's-eye · − look up / worm's-eye)
  yaw?: number;     // rotateY deg (orbit-lite)
  roll?: number;    // rotateZ deg (dutch tilt)
  zoom?: number;    // overall scale (a subtle vertigo/zoom on top of the dolly)
  easing?: string;
};

export type Layer = {
  kind: string;                // 'fill' | 'grid' | 'floor' | 'hero' | 'panel' | 'image'
  parallax?: number;           // FLAT path depth factor (bg < 1, fg > 1)
  z?: number;                  // 3D path translateZ depth (negative = further away)
  x?: number;                  // 3D path in-world px offset
  y?: number;
  blur?: number;               // depth-of-field: px blur on this plane's content (rack focus)
  dim?: number;                // 0..1 extra darkening so the focal plane dominates (one focus/frame)
  src?: string;                // image
  kicker?: string;             // panel
  title?: string;
  sub?: string;
  text?: string;               // hero
  align?: string;              // 'left' (default) | 'center'
  revealAtFrame?: number;      // ONE eased reveal on this layer's secondary content
};

const EASE: Record<string, (n: number) => number> = {
  linear: Easing.linear,
  in: Easing.in(Easing.cubic),
  out: Easing.out(Easing.cubic),
  inout: Easing.inOut(Easing.cubic),
};

// Generic eased keyframe read for a numeric field over a keyframe list (deterministic, frame-driven).
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

// ── Shared content renderer: a layer's `kind` → JSX. Positioning/transform/DoF live in the wrappers. ─
const PlaneContent: React.FC<{layer: Layer; theme: Theme; frame: number; reduced: boolean}> = ({
  layer,
  theme,
  frame,
  reduced,
}) => {
  const rf = layer.revealAtFrame ?? 0;
  const rev = reduced
    ? 1
    : interpolate(frame, [rf, rf + 12], [0, 1], {
        easing: Easing.out(Easing.cubic),
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
  const bleed: React.CSSProperties = {position: 'absolute', left: '-18%', top: '-18%', width: '136%', height: '136%'};
  const mono = '"JetBrains Mono", "SF Mono", Menlo, monospace';

  if (layer.kind === 'fill') {
    return <div style={{...bleed, background: `radial-gradient(120% 120% at 50% 40%, ${theme.bg} 0%, ${theme.bg} 55%, #00000055 100%)`}} />;
  }
  if (layer.kind === 'grid' || layer.kind === 'floor') {
    const strong = layer.kind === 'floor';
    return (
      <div
        style={{
          position: 'absolute',
          left: strong ? -1400 : -900,
          top: strong ? -1400 : -600,
          width: strong ? 4600 : 3720,
          height: strong ? 4600 : 2280,
          opacity: strong ? 0.5 : 0.14,
          backgroundImage: `linear-gradient(${strong ? theme.accent + '55' : theme.muted} ${strong ? 2 : 1}px, transparent ${strong ? 2 : 1}px), linear-gradient(90deg, ${strong ? theme.accent + '55' : theme.muted} ${strong ? 2 : 1}px, transparent ${strong ? 2 : 1}px)`,
          backgroundSize: strong ? '170px 170px' : '120px 120px',
        }}
      />
    );
  }
  if (layer.kind === 'hero') {
    return (
      <div style={{position: 'absolute', left: -760, top: -280, width: 1520, textAlign: 'center', color: theme.fg, opacity: 0.09, fontSize: 420, fontWeight: 800, letterSpacing: -6, fontFamily: mono}}>
        {layer.text || ''}
      </div>
    );
  }
  if (layer.kind === 'image' && layer.src) {
    return <Img src={staticFile(layer.src)} style={{...bleed, objectFit: 'cover'}} />;
  }
  // panel — a floating card in space
  const centre = layer.align === 'center';
  return (
    <div
      style={{
        position: 'absolute',
        left: -580,
        top: -230,
        width: 1160,
        padding: '52px 60px',
        boxSizing: 'border-box',
        textAlign: centre ? 'center' : 'left',
        background: `${theme.bg}dd`,
        border: `2px solid ${theme.accent}55`,
        borderRadius: 14,
        boxShadow: '0 44px 130px rgba(0,0,0,0.55)',
      }}
    >
      {layer.kicker ? (
        <div style={{color: theme.accent2, fontSize: 32, fontWeight: 700, letterSpacing: 4, textTransform: 'uppercase', marginBottom: 20, fontFamily: mono}}>{layer.kicker}</div>
      ) : null}
      {layer.title ? (
        <div style={{color: theme.fg, fontSize: 96, fontWeight: 800, lineHeight: 1.05, letterSpacing: -1, fontFamily: mono, textShadow: '0 6px 30px rgba(0,0,0,0.45)'}}>{layer.title}</div>
      ) : null}
      {layer.sub ? (
        <div style={{color: theme.muted, fontSize: 40, lineHeight: 1.34, marginTop: 28, opacity: rev, transform: `translateY(${(1 - rev) * 16}px)`, fontFamily: mono}}>{layer.sub}</div>
      ) : null}
    </div>
  );
};

// ── FLAT parallax plane (cinematic-lite) ───────────────────────────────────────────────────────────
const PlaneViewFlat: React.FC<{layer: Layer; cam: {x: number; y: number; zoom: number}; theme: Theme; frame: number; reduced: boolean}> = ({layer, cam, theme, frame, reduced}) => {
  const {width, height} = useVideoConfig();
  const p = layer.parallax ?? 1;
  const tx = -(cam.x - 0.5) * p * width;
  const ty = -(cam.y - 0.5) * p * height;
  const scale = 1 + (cam.zoom - 1) * p;
  return (
    <AbsoluteFill style={{transform: `translate(${tx}px, ${ty}px) scale(${scale})`, transformOrigin: 'center center', overflow: 'visible'}}>
      <PlaneContent layer={layer} theme={theme} frame={frame} reduced={reduced} />
    </AbsoluteFill>
  );
};

// ── FLAT cinematic scene (unchanged behaviour) ─────────────────────────────────────────────────────
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
  const cam = reduced
    ? {x: kfs[0].x, y: kfs[0].y, zoom: kfs[0].zoom}
    : {
        x: lerpField(kfs, frame, (k) => k.x),
        y: lerpField(kfs, frame, (k) => k.y),
        zoom: lerpField(kfs, frame, (k) => k.zoom),
      };
  const opacity = edgeOpacity(frame, dur, fadeInFrames, fadeOutFrames);
  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden', opacity}}>
      {layers.map((layer, i) => (
        <PlaneViewFlat key={i} layer={layer} cam={cam} theme={theme} frame={frame} reduced={reduced} />
      ))}
      <Vignette />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};

// ── 3D LENS scene ──────────────────────────────────────────────────────────────────────────────────
// A real perspective rig: HTML/CSS layers on translateZ planes under one camera doing pitch/yaw/dolly.
// FLATTENING FOOTGUN (silent, catches no test): opacity<1 / filter / overflow≠visible / blend / mask on
// a preserve-3d ANCESTOR forces transform-style flat and collapses all translateZ. So the rig is an
// INNER node; the scene fade, the overflow clip, and the vignette live on OUTER siblings/ancestors, and
// per-plane DoF blur/dim sit on an inner wrapper INSIDE each plane — never on the plane div itself.
export const CinematicScene3D: React.FC<{
  layers: Layer[];
  lens: LensKeyframe[];
  perspective?: number;
  theme: Theme;
  captions?: CaptionSeg[];
  audio?: string | null;
  captionFontPx: number;
  reducedMotion?: boolean;
  fadeInFrames?: number;
  fadeOutFrames?: number;
}> = ({layers, lens, perspective, theme, captions, audio, captionFontPx, reducedMotion, fadeInFrames, fadeOutFrames}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, width, height} = useVideoConfig();
  const dur = Math.max(1, durationInFrames);
  const reduced = !!reducedMotion;

  const kfs = lens && lens.length ? lens : [{atFrame: 0}];
  const read = (get: (k: LensKeyframe) => number) => (reduced ? get(kfs[0]) : lerpField(kfs, frame, get));
  const dolly = read((k) => k.dolly || 0);
  const pitch = read((k) => k.pitch || 0);
  const yaw = read((k) => k.yaw || 0);
  const roll = read((k) => k.roll || 0);
  const zoom = read((k) => (k.zoom == null ? 1 : k.zoom));

  const world: React.CSSProperties = {
    position: 'absolute',
    left: width / 2,
    top: height / 2,
    width: 0,
    height: 0,
    transformStyle: 'preserve-3d',
    transform: `scale(${zoom}) translateZ(${dolly}px) rotateX(${pitch}deg) rotateY(${yaw}deg) rotateZ(${roll}deg)`,
  };

  const fade = 1 - edgeOpacity(frame, dur, fadeInFrames, fadeOutFrames); // overlay opacity (0 = visible)

  return (
    // OUTER: bg + overflow clip. NO opacity/filter here (would flatten the inner 3D).
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden'}}>
      {/* INNER RIG: perspective + preserve-3d, no opacity/filter on this chain. */}
      <AbsoluteFill style={{perspective: `${perspective || 1300}px`, perspectiveOrigin: '50% 46%'}}>
        <div style={world}>
          {layers.map((p, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                transformStyle: 'preserve-3d',
                transform: `translate3d(${p.x || 0}px, ${p.y || 0}px, ${p.z || 0}px)${p.kind === 'floor' ? ' rotateX(90deg)' : ''}`,
              }}
            >
              {/* DoF + dim on an INNER wrapper (leaf) — safe: it has no 3D descendants to flatten. */}
              <div style={{filter: p.blur ? `blur(${p.blur}px)` : undefined, opacity: p.dim != null ? 1 - p.dim : 1}}>
                <PlaneContent layer={p} theme={theme} frame={frame} reduced={reduced} />
              </div>
            </div>
          ))}
        </div>
      </AbsoluteFill>

      {/* OUTER overlays (2D, on top) — vignette then the scene-edge fade. */}
      <Vignette />
      <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: theme.bg, opacity: fade}} />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};

// ── shared bits ──────────────────────────────────────────────────────────────────────────────────
function edgeOpacity(frame: number, dur: number, fadeInFrames?: number, fadeOutFrames?: number): number {
  const fi = Math.min(fadeInFrames || 0, dur);
  const fo = Math.min(fadeOutFrames || 0, dur);
  const fadeIn = fi > 0 ? interpolate(frame, [0, fi], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  const fadeOut = fo > 0 ? interpolate(frame, [dur - fo, dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  return Math.min(fadeIn, fadeOut);
}

const Vignette: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none', background: 'radial-gradient(130% 130% at 50% 45%, rgba(0,0,0,0) 52%, rgba(0,0,0,0.42) 100%)'}} />
);
