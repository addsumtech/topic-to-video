// HOW A STAGE'S SURFACES TAKE LIGHT (references/craft-research.md §4) — the difference between a lit object and a
// filled rectangle. Stage-only (imported by remotion/src/stage/), never by a register, so no measured manifest re-keys.
//
//   elevation   a raised surface's shadow from ONE key light above: five layers whose offset and blur double
//               (1, 2, 4, 8, 16), each faint, tinted toward the ground's own hue on a light ground — one big black blur
//               read as a sticker on a light stage and as a hole on a dark one;
//   topLight    the top edge of a dark surface catching that light (a 1 px inset highlight);
//   sheen       a glossy face reflecting the key light as it TURNS: invisible at rest (where the face is read), a band
//               that crosses the face as the card turns past ~4 degrees — it is what makes a turn read as 3D;
//   blurOf      motion blur from the frame's own velocity: a 180-degree shutter smears a point moving v px a frame
//               over v/2 px, a box of standard deviation v/2/sqrt(12) = 0.144 v. Analytic, one Gaussian along the
//               axes the thing moves on — CameraMotionBlur's multi-sample approach combed and ran ~0.75 frame early.
import React from 'react';
import {relLum, shade} from '../runtime/dna';
import {hex6} from '../runtime/hexColor';
import {clamp01} from '../runtime/motion';

const rgbOf = (hex: string): [number, number, number] => {
  const h = hex.replace('#', '');
  const v = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6);
  const n = parseInt(v, 16);
  return Number.isFinite(n) ? [(n >> 16) & 255, (n >> 8) & 255, n & 255] : [0, 0, 0];
};

/** The shadow of a surface raised `level` (1 = a card held off the stage) on a frame whose short side is U. */
export const elevation = (level: number, U: number, ground: string, dark: boolean): string => {
  const u = (U / 1080) * 1.35 * Math.max(0, level);
  const [r, g, b] = dark ? [0, 0, 0] : rgbOf(shade(ground, 0.72));
  const a = dark ? 0.2 : 0.085;
  return [1, 2, 4, 8, 16].map((k) => `0 ${(k * u).toFixed(2)}px ${(2 * k * u).toFixed(2)}px rgba(${r}, ${g}, ${b}, ${a})`)
    .join(', ');
};

/** The top edge of a DARK surface catching the key light; nothing on a light one (white on white is no edge). */
export const topLight = (U: number, surfaceDark: boolean): string =>
  surfaceDark ? `inset 0 ${Math.max(1, U / 1080).toFixed(2)}px 0 rgba(255, 255, 255, 0.16)` : '';

/** The face's reflection of the key light at this turn: a band across the face, null at rest. `ry`, `rx` in degrees. */
export const sheen = (ry: number, rx: number): React.CSSProperties | null => {
  const turn = Math.abs(ry) + 0.5 * Math.abs(rx);
  const on = clamp01((turn - 4) / 10);
  if (on <= 0) return null;
  const at = clamp01(0.5 - ry / 40);                     // turned left, the band slides right, as a reflection does
  return {position: 'absolute', inset: 0, pointerEvents: 'none', mixBlendMode: 'screen', opacity: 0.11 * on,
    backgroundImage: 'linear-gradient(112deg, rgba(255,255,255,0) 38%, rgba(255,255,255,1) 50%, rgba(255,255,255,0) 62%)',
    backgroundSize: '300% 100%', backgroundPosition: `${(at * 100).toFixed(1)}% 0`};
};

/** Motion blur for a thing that moved (dx, dy) screen px since the last frame, drawn at `scale` (its local px per
 *  screen px is 1/scale): the standard deviations along its own x and y, or null when it barely moved. */
export const blurOf = (dx: number, dy: number, scale = 1): {sx: number; sy: number} | null => {
  const k = 0.144 / Math.max(0.05, scale);
  const sx = Math.abs(dx) * k, sy = Math.abs(dy) * k;
  return sx < 0.6 && sy < 0.6 ? null : {sx: Math.min(sx, 40), sy: Math.min(sy, 40)};
};

/** The SVG filter that draws `blurOf`'s smear (an invisible element; reference it as `url(#id)`). */
export const BlurFilter: React.FC<{id: string; blur: {sx: number; sy: number}; edge?: 'none' | 'duplicate'}> =
  ({id, blur, edge = 'none'}) => (
  <svg width={0} height={0} style={{position: 'absolute'}} aria-hidden>
    <filter id={id} x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
      <feGaussianBlur stdDeviation={`${blur.sx.toFixed(2)} ${blur.sy.toFixed(2)}`} edgeMode={edge} />
    </filter>
  </svg>
);

/** A rim of light on a surface's edge, brightest toward a light at (u, v) of the surface (0..1): a 1 px border masked
 *  by a radial falloff from that point. On a dark stage only — on a light one a white rim is no edge. */
export const rimLight = (u: number, v: number, U: number, radius: number): React.CSSProperties => {
  const mask = `radial-gradient(circle at ${(u * 100).toFixed(1)}% ${(v * 100).toFixed(1)}%, #000 0%, transparent 62%)`;
  return {position: 'absolute', inset: 0, pointerEvents: 'none', borderRadius: radius, boxSizing: 'border-box',
    border: `${Math.max(1, U / 1080 * 1.5).toFixed(2)}px solid rgba(255, 255, 255, 0.5)`,
    WebkitMaskImage: mask, maskImage: mask};
};

/** A dark surface (its own colour), for topLight — the threshold the stage reads its ground as dark by. */
export const surfaceIsDark = (surface: string): boolean => relLum(hex6(surface)) < 0.18;
