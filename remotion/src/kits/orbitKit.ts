// HELPER · orbitKit — the pieces every orbit-world shot of this film is drawn from, so the shots read as ONE
// place: the sky's texture, the Earth's sunlit limb with its thin blue atmosphere, and the phone that only
// listens. Pure functions returning SVG nodes (React.createElement — a .ts helper has no JSX); no words, no
// clock, no film figures. Every id is prefixed by the caller's own React.useId(), because two shots overlap in
// the DOM during a cross-dissolve and a shared gradient id would resolve to the OTHER shot's defs.
import React from 'react';
import {hash01} from '../runtime/motion';
import {mix} from '../runtime/dna';

const h = React.createElement;

export type Pt = {x: number; y: number};

/** The sky's stars — texture, never a reading. `skip` keeps them off the Earth's disc. */
export const starField = (W: number, H: number, n: number, ink: string, opacity: number, U: number,
  skip?: (x: number, y: number) => boolean, seed = 0): React.ReactNode[] => {
  const out: React.ReactNode[] = [];
  for (let k = 0; k < n; k++) {
    // @decor: where a star sits is texture; no star stands for anything the film names
    const x = W * hash01(seed + k * 5 + 1);
    // @decor: as above — a star's height is texture
    const y = H * hash01(seed + k * 5 + 2);
    // @decor: as above — a star's brightness is texture
    const b = hash01(seed + k * 5 + 3);
    if (skip && skip(x, y)) continue;
    out.push(h('circle', {key: `st${k}`, cx: x, cy: y, r: U * (b > 0.96 ? 0.0024 : 0.0011), fill: ink,
      opacity: (0.16 + 0.5 * b) * opacity}));
  }
  return out;
};

/** The defs an Earth needs: its sunlit-to-night body and the atmosphere's blue rim. Ids: `${id}-earth`,
 *  `${id}-atmo`. `sunDir` is where the light comes from, as a unit vector in screen space. */
export const earthDefs = (id: string, E: Pt, R: number, limb: string, bg: string, sunDir: Pt = {x: -0.6, y: -0.8}) => [
  h('radialGradient', {key: 'atmo', id: `${id}-atmo`, cx: E.x, cy: E.y, r: R * 1.07, gradientUnits: 'userSpaceOnUse'},
    h('stop', {offset: 0.9, stopColor: limb, stopOpacity: 0}),
    h('stop', {offset: 0.935, stopColor: limb, stopOpacity: 0.55}),
    h('stop', {offset: 0.945, stopColor: limb, stopOpacity: 0.3}),
    h('stop', {offset: 1, stopColor: limb, stopOpacity: 0})),
  h('radialGradient', {key: 'earth', id: `${id}-earth`, cx: E.x - sunDir.x * R * 0.55, cy: E.y - sunDir.y * R * 0.55,
    r: R * 1.72, gradientUnits: 'userSpaceOnUse'},
    h('stop', {offset: 0, stopColor: mix(bg, '#000000', 0.2)}),
    h('stop', {offset: 0.6, stopColor: mix(limb, bg, 0.9)}),
    h('stop', {offset: 0.84, stopColor: mix(limb, bg, 0.66)}),
    h('stop', {offset: 0.95, stopColor: mix(limb, bg, 0.3)}),
    h('stop', {offset: 1, stopColor: mix(limb, '#ffffff', 0.35)})),
];

/** The Earth's disc with its atmosphere rim and a bright limb line — draw after `earthDefs`. */
export const earthDisc = (id: string, E: Pt, R: number, limb: string, lw: number, opacity: number) =>
  h('g', {key: 'earth', opacity},
    h('circle', {cx: E.x, cy: E.y, r: R * 1.07, fill: `url(#${id}-atmo)`}),
    h('circle', {cx: E.x, cy: E.y, r: R, fill: `url(#${id}-earth)`}),
    h('circle', {cx: E.x, cy: E.y, r: R, fill: 'none', stroke: mix(limb, '#ffffff', 0.4), strokeWidth: lw * 1.2,
      opacity: 0.7}));

/** The phone: a dark handset standing on the ground, its screen lit by `glow` (0..1) — it only ever receives.
 *  `s` is its height; `deg` turns it so it stands along the local up. */
export const phoneGlyph = (key: string, at: Pt, s: number, deg: number, ink: {body: string; edge: string;
  screen: string; lit: string}, glow: number, lw: number) => {
  const w = s * 0.5, r = s * 0.1;
  return h('g', {key, transform: `translate(${at.x} ${at.y}) rotate(${deg})`},
    h('rect', {x: -w / 2, y: -s, width: w, height: s, rx: r, fill: ink.body, stroke: mix(ink.edge, ink.lit, glow * 0.6),
      strokeWidth: lw * 1.4}),
    h('rect', {x: -w / 2 + s * 0.045, y: -s + s * 0.07, width: w - s * 0.09, height: s * 0.82, rx: r * 0.55,
      fill: mix(ink.screen, ink.lit, glow * 0.75)}),
    h('rect', {x: -w * 0.16, y: -s + s * 0.03, width: w * 0.32, height: s * 0.018, rx: s * 0.01, fill: ink.edge,
      opacity: 0.6}));
};

/** Where a ray from `a` at angle `ang` meets the circle (E, R) first, or null. */
export const rayHitsCircle = (a: Pt, ang: number, E: Pt, R: number): number | null => {
  const dx = Math.cos(ang), dy = Math.sin(ang);
  const fx = a.x - E.x, fy = a.y - E.y;
  const b = fx * dx + fy * dy, c = fx * fx + fy * fy - R * R;
  const disc = b * b - c;
  if (disc < 0) return null;
  const s = -b - Math.sqrt(disc);
  return s > 0 ? s : null;
};

/** THE FILM'S TYPE SCALE, as fractions of min(W, H): one scale for every shot, set so that at 1080p no label is
 *  under ~38 px, no secondary note under ~33 px, no title under ~65 px — read in a second on a phone. A shot that
 *  cannot fit its copy at these sizes cuts words; it never sets type smaller. */
export const TYPE = {label: 0.036, note: 0.031, title: 0.06, figure: 0.052, display: 0.1} as const;
/** The smallest size a fitted line may fall to (fitTextPx can shrink a long line): a title never below this. */
export const TITLE_MIN = 0.052;
