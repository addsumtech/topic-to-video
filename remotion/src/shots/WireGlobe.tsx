// SHOT · Wire Globe — a premium "global / connected" register: a rotating wireframe sphere (projected lat/long
// lines, depth-faded) with glowing integration nodes on its surface and great-circle ARCS that draw between
// them. Distinct from the flat MapRoutes — this is a true 3D-projected globe. Deterministic (rotation = fn t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {useDNA} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';

// THE CLOSING MARK FITS THE SENTENCE: a CJK line takes 。, a Latin one ., and a line that already ends in its own
// punctuation takes none — a Latin "." after a Chinese headline read as a typo, and "Done!." as two marks.
const closingMark = (s: string): string => /[.!?。！？…:：;；]\s*$/.test(s) ? ''
  : /[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/.test(s) ? '。' : '.';

export const DURATION = 165; // 5.5s
const CY_D0 = '#3fe0ff';
const D2R = Math.PI / 180;

export const WireGlobe: React.FC<{tagline?: string}> = ({tagline = 'connected to everything'} = {}) => {
  const t = useT();
  const dna = useDNA();
  // THE GLOBE READ THE DNA FOR ITS GROUND AND FOR NOTHING ELSE. Every graticule, arc, node and the closing
  // line were cyan or near-white literals, so on a film grounded paper the SPHERE survived as a grey disc and
  // the connections across it — the whole claim — measured 1.18:1 and 1.05:1, with the tagline (#dff4ff,
  // 1.02:1) gone entirely. The sphere's body is a surface and takes the film's; the wire is the film's accent.
  const CY = dna?.accent ?? CY_D0;
  const BODY = dna?.surface ?? '#06101f';
  const NODE = dna?.fg ?? '#eafcff';
  const ARC = dna?.accent ?? '#8ff0ff';
  const TAG_INK = dna?.fg ?? '#dff4ff';
  const HALO = dna?.surface ?? '#0a1830';
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2, R = 340;
  const rotY = t * 55 * D2R + 0.6; // spin

  // project a (lat,lon) on the sphere → screen point + depth (z, front>0)
  const proj = (latDeg: number, lonDeg: number) => {
    const lat = latDeg * D2R, lon = lonDeg * D2R + rotY;
    const x = Math.cos(lat) * Math.sin(lon), y = Math.sin(lat), z = Math.cos(lat) * Math.cos(lon);
    return {x: cx + x * R, y: cy - y * R, z};
  };
  const polyline = (pts: {x: number; y: number; z: number}[], base: number) =>
    pts.map((p, i) => (i ? 'L' : 'M') + p.x.toFixed(1) + ',' + p.y.toFixed(1)).join(' ');

  const latLines: React.ReactNode[] = [];
  for (let lat = -60; lat <= 60; lat += 30) {
    const pts = []; for (let lon = 0; lon <= 360; lon += 12) pts.push(proj(lat, lon));
    latLines.push(<path key={`la${lat}`} d={polyline(pts, 0)} fill="none" stroke={CY} strokeWidth={1.4} strokeOpacity={0.32} />);
  }
  const lonLines: React.ReactNode[] = [];
  for (let lon = 0; lon < 360; lon += 30) {
    const pts = []; for (let lat = -90; lat <= 90; lat += 10) pts.push(proj(lat, lon));
    lonLines.push(<path key={`lo${lon}`} d={polyline(pts, 0)} fill="none" stroke={CY} strokeWidth={1.4} strokeOpacity={0.28} />);
  }

  // integration nodes on the surface
  const NODES = [[20, 40], [-15, 120], [42, 200], [-30, 260], [8, 320], [55, 90]];
  // @decor: unlabelled surface nodes and the arcs between them are the globe's texture; no film item is placed on them
  const arcs: [number, number][] = [[0, 2], [1, 4], [3, 5], [2, 4]];

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #081426 0%, #050a16 60%, #03060e 100%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><filter id="wg"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <radialGradient id="atmo"><stop offset="0.72" stopColor={HALO} stopOpacity="0" /><stop offset="1" stopColor={CY} stopOpacity="0.28" /></radialGradient></defs>
        {/* atmosphere halo */}
        <circle cx={cx} cy={cy} r={R + 18} fill="url(#atmo)" />
        {/* back hemisphere dimmer via a filled disc behind */}
        <circle cx={cx} cy={cy} r={R} fill={BODY} opacity={0.55} />
        <g opacity={easeOutCubic(seg(t, 0.04, 0.34))}>{latLines}{lonLines}</g>

        {/* arcs (great-circle-ish, lifted off surface) drawn on */}
        {arcs.map(([a, b], k) => {
          const pa = proj(NODES[a][0], NODES[a][1]), pb = proj(NODES[b][0], NODES[b][1]);
          const midLat = (NODES[a][0] + NODES[b][0]) / 2, midLon = (NODES[a][1] + NODES[b][1]) / 2;
          const pm = proj(midLat, midLon);
          const lift = 90; const mx = pm.x + (pm.x - cx) * (lift / R), my = pm.y + (pm.y - cy) * (lift / R);
          const draw = easeOutCubic(seg(t, 0.42 + k * 0.08, 0.6 + k * 0.08));
          if (pa.z < -0.2 && pb.z < -0.2) return null;
          return <path key={k} d={`M${pa.x},${pa.y} Q${mx},${my} ${pb.x},${pb.y}`} fill="none" stroke={ARC}
            strokeWidth={2.4} strokeOpacity={0.9} {...drawOn(draw)} filter="url(#wg)" />;
        })}

        {/* nodes */}
        {NODES.map(([la, lo], i) => {
          const p = proj(la, lo); const front = clamp01((p.z + 0.3) / 1.0);
          const pop = easeOutBack(seg(t, 0.3 + i * 0.05, 0.45 + i * 0.05));
          return <g key={i} opacity={front * pop}><circle cx={p.x} cy={p.y} r={9 * pop} fill={NODE} filter="url(#wg)" />
            <circle cx={p.x} cy={p.y} r={16 * pop} fill="none" stroke={CY} strokeWidth={2} opacity={0.7} /></g>;
        })}
      </svg>

      <div style={{position: 'absolute', left: 0, right: 0, bottom: bottomInset(W, H, H * 0.12), textAlign: 'center',
        opacity: clamp01(seg(t, 0.55, 0.8)), color: TAG_INK, font: '800 44px/1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em'}}>
        {tagline}<span style={{color: CY}}>{closingMark(String(tagline))}</span>
      </div>
    </AbsoluteFill>
  );
};
export default WireGlobe;
