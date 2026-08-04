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
import {Finish} from './theme/Finish';
import {panelMaterial} from './stage/elements';   // shared style->surface recipe (same as the shot tier)
import {textStyle} from './theme/typography';

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
  focusZ?: number;  // rack focus: the z-plane in focus this frame; planes further from it soften.
                    // Set it in keyframes to PULL focus (bg→fg) as the camera moves. Overrides layer.blur.
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
  // Content is positioned CENTER-ORIGIN (offsets around 0,0). Both render paths put PlaneContent inside a
  // zero-size div anchored at the frame/world centre, so these coordinates centre identically in flat and 3D.
  const monoStyle = textStyle(theme, 'body', 'number');

  if (layer.kind === 'fill') {
    return (
      <div style={{position: 'absolute', left: '50%', top: '50%', width: 3200, height: 2200,
                   transform: 'translate(-50%, -50%)',
                   background: `radial-gradient(120% 120% at 50% 40%, ${theme.bg} 0%, ${theme.bg} 55%, #00000055 100%)`}} />
    );
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
    const heroStyle = textStyle(theme, 'display', 'body');
    return (
      <div style={{...heroStyle, position: 'absolute', left: -760, top: -280, width: 1520, textAlign: 'center', color: theme.fg, opacity: 0.09, fontSize: 420, fontWeight: 800, letterSpacing: -6}}>
        {layer.text || ''}
      </div>
    );
  }
  if (layer.kind === 'image' && layer.src) {
    // FIXED px, centred on the plane origin — works in BOTH paths: the 3D rig's layer div is zero-size
    // (percentage bleed would collapse to nothing), and in the flat AbsoluteFill this still centres.
    return (
      <Img
        src={staticFile(layer.src)}
        style={{position: 'absolute', left: '50%', top: '50%', width: 1920, height: 1080,
                transform: 'translate(-50%, -50%)', objectFit: 'cover',
                boxShadow: '0 60px 160px rgba(0,0,0,0.6)'}}
      />
    );
  }
  // panel — a floating glass card in space (gradient + rim highlight + inner accent glow = premium material)
  const centre = layer.align === 'center';
  const kickerStyle = textStyle(theme, 'caption', 'body');
  const titleStyle = textStyle(theme, 'display', 'display');
  const subStyle = textStyle(theme, 'body', 'body');
  const radius = parseInt(theme.radius || '14px', 10);
  const mat = panelMaterial(theme);   // card SURFACE follows the deck's style (shared with the shot tier)

  return (
    <div
      style={{
        position: 'absolute',
        left: -520,
        top: -200,
        width: 1040,
        padding: '44px 52px',
        boxSizing: 'border-box',
        textAlign: centre ? 'center' : 'left',
        background: mat.background,
        border: mat.border,
        borderRadius: mat.radius ?? radius,
        boxShadow: mat.boxShadow,
      }}
    >
      {layer.kicker ? (
        <div style={{...kickerStyle, color: theme.accent2, fontSize: 28, fontWeight: 700, letterSpacing: 4, textTransform: 'uppercase', marginBottom: 20}}>{layer.kicker}</div>
      ) : null}
      {layer.title ? (
        <div style={{...titleStyle, color: theme.fg, fontSize: 80, fontWeight: 800, lineHeight: 1.08, letterSpacing: -1, textShadow: '0 6px 30px rgba(0,0,0,0.45)'}}>{layer.title}</div>
      ) : null}
      {layer.sub ? (
        <div style={{...subStyle, color: theme.muted, fontSize: 34, lineHeight: 1.34, marginTop: 22, opacity: rev, transform: `translateY(${(1 - rev) * 16}px)`}}>{layer.sub}</div>
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
      {/* zero-size node at the frame CENTRE so PlaneContent's center-origin coordinates match the 3D path */}
      <div style={{position: 'absolute', left: '50%', top: '50%', width: 0, height: 0}}>
        <PlaneContent layer={layer} theme={theme} frame={frame} reduced={reduced} />
      </div>
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
      <Finish frame={frame} theme={theme} />
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
  // dynamic RACK FOCUS: if any keyframe sets focusZ, the focal distance can PULL across the move, and
  // each plane's blur is derived from |z − focusZ| (overrides the plane's static blur). No focusZ set
  // → planes keep their authored static blur.
  const hasFocus = kfs.some((k) => k.focusZ != null);
  const focusZ = hasFocus ? read((k) => (k.focusZ == null ? 0 : k.focusZ)) : null;

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
      <AbsoluteFill style={{perspective: `${perspective || 2000}px`, perspectiveOrigin: '50% 50%'}}>
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
              <div style={{filter: planeBlur(p, focusZ) ? `blur(${planeBlur(p, focusZ)}px)` : undefined, opacity: p.dim != null ? 1 - p.dim : 1}}>
                <PlaneContent layer={p} theme={theme} frame={frame} reduced={reduced} />
              </div>
            </div>
          ))}
        </div>
      </AbsoluteFill>

      {/* OUTER overlays (2D, on top) — vignette, grade+grain finish, then the scene-edge fade. */}
      <Finish frame={frame} theme={theme} />
      <AbsoluteFill style={{pointerEvents: 'none', backgroundColor: theme.bg, opacity: fade}} />
      {captions && captions.length ? <Captions segments={captions} fontPx={captionFontPx} /> : null}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};

// Rack-focus blur for a plane: static (author's layer.blur) unless the lens sets focusZ, in which case
// the blur is derived from the plane's distance from the focal z (a real, pullable depth-of-field).
function planeBlur(p: Layer, focusZ: number | null): number {
  if (focusZ == null) return p.blur || 0;
  return Math.min(14, Math.abs((p.z || 0) - focusZ) / 120);
}

// ── shared bits ──────────────────────────────────────────────────────────────────────────────────
function edgeOpacity(frame: number, dur: number, fadeInFrames?: number, fadeOutFrames?: number): number {
  const fi = Math.min(fadeInFrames || 0, dur);
  const fo = Math.min(fadeOutFrames || 0, dur);
  const fadeIn = fi > 0 ? interpolate(frame, [0, fi], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  const fadeOut = fo > 0 ? interpolate(frame, [dur - fo, dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  return Math.min(fadeIn, fadeOut);
}
