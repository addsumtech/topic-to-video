// EARTH — the one globe the geography registers draw: an orthographic sphere lit from the upper left, Natural Earth
// land and borders, a hairline graticule, an atmosphere rim, and the film's regions lit in its accent. Pure function of
// the view it is handed; the registers own the camera (runtime/geo.ts lerpView) and everything that names a place.
//
// LOOK. Restraint, per the fx research: one material (a matte sphere), one light (upper left — a soft terminator
// shading the far limb), one optic (the rim glow). The land is a step off the ground, not a colour of its own, so the
// ONLY saturated thing on the planet is the region the film named.
import React from 'react';
import {AtlasRes, GlobeView, atlas, orthoProjection, geoPath, geoGraticule10, flatProjection} from './geo';
import {mix} from './dna';
import type {GeoProjection} from 'd3-geo';

export type EarthInk = {bg: string; fg: string; accent: string; lit?: string};

export const earthPalette = (ink: EarthInk) => ({
  oceanHi: mix(ink.bg, ink.accent, 0.16),
  oceanLo: mix(ink.bg, '#000000', 0.25),
  land: mix(ink.bg, ink.fg, 0.19),
  landHi: mix(ink.bg, ink.fg, 0.27),
  coast: mix(ink.bg, ink.fg, 0.4),
  border: mix(ink.bg, ink.fg, 0.3),
  grat: mix(ink.bg, ink.fg, 0.1),
  rim: ink.accent,
  lit: ink.lit ?? ink.accent,
});

const sid = (s: string) => s.replace(/[^A-Za-z0-9_-]/g, '');

export const Earth: React.FC<{
  uid: string; W: number; H: number; res: AtlasRes; ink: EarthInk;
  /** an orthographic view, or a ready flat projection (FlightArcs' flat mode) */
  view?: GlobeView; flat?: GeoProjection;
  /** regions lit in the accent; `lit` 0..1 fades them in */
  regions?: any[]; lit?: number;
  /** 0..1 — the planet's own entrance */
  show?: number;
  children?: (path: ReturnType<typeof geoPath>, proj: GeoProjection) => React.ReactNode;
}> = ({uid, W, H, res, ink, view, flat, regions = [], lit = 1, show = 1, children}) => {
  const id = sid(uid);
  const P = earthPalette(ink);
  const A = atlas(res);
  const proj = flat ?? orthoProjection(view!, W, H);
  const path = geoPath(proj);
  const sphere = path({type: 'Sphere'} as any) ?? '';
  const R = view?.R ?? 0, cx = view?.cx ?? W / 2, cy = view?.cy ?? H / 2;
  // the light: a highlight up-left of centre and a terminator darkening the far limb, both in the globe's own space
  const lx = cx - R * 0.42, ly = cy - R * 0.48;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: show}}>
      <defs>
        <radialGradient id={`${id}-ocean`} gradientUnits="userSpaceOnUse" cx={lx} cy={ly} r={Math.max(1, R * 1.75)}>
          <stop offset="0" stopColor={P.oceanHi} />
          <stop offset="1" stopColor={P.oceanLo} />
        </radialGradient>
        <radialGradient id={`${id}-shade`} gradientUnits="userSpaceOnUse" cx={lx} cy={ly} r={Math.max(1, R * 1.9)}>
          <stop offset="0.35" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.42" />
        </radialGradient>
        <radialGradient id={`${id}-atmo`} gradientUnits="userSpaceOnUse" cx={cx} cy={cy} r={Math.max(1, R * 1.12)}>
          <stop offset={0.86} stopColor={P.rim} stopOpacity="0" />
          <stop offset={0.9} stopColor={P.rim} stopOpacity="0.22" />
          <stop offset={1} stopColor={P.rim} stopOpacity="0" />
        </radialGradient>
        <filter id={`${id}-glow`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation={Math.max(2, Math.min(W, H) * 0.006)} result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <clipPath id={`${id}-clip`}>{flat ? <path d={sphere} /> : <path d={sphere} />}</clipPath>
      </defs>
      {view ? <circle cx={cx} cy={cy} r={R * 1.12} fill={`url(#${id}-atmo)`} /> : null}
      <path d={sphere} fill={view ? `url(#${id}-ocean)` : P.oceanLo} />
      <g clipPath={`url(#${id}-clip)`}>
        <path d={path(geoGraticule10() as any) ?? ''} fill="none" stroke={P.grat} strokeWidth={1} />
        <path d={path(A.land) ?? ''} fill={P.land} stroke={P.coast} strokeWidth={0.9} strokeLinejoin="round" />
        <path d={path(A.borders) ?? ''} fill="none" stroke={P.border} strokeWidth={0.7} strokeLinejoin="round" />
        {regions.map((f, i) => {
          const d = path(f) ?? '';
          return d ? (
            <g key={i} opacity={lit}>
              <path d={d} fill={P.lit} fillOpacity={0.88} filter={`url(#${id}-glow)`} />
              <path d={d} fill="none" stroke={mix(P.lit, '#ffffff', 0.55)} strokeWidth={1.4} strokeLinejoin="round" />
            </g>
          ) : null;
        })}
        {view ? <path d={sphere} fill={`url(#${id}-shade)`} /> : null}
        {children ? children(path, proj) : null}
      </g>
      {view ? <path d={sphere} fill="none" stroke={P.rim} strokeOpacity={0.45} strokeWidth={1.4} /> : null}
    </svg>
  );
};

export {flatProjection};
