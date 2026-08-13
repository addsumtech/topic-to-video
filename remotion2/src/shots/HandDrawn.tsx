// SHOT · Hand-drawn / Riso — the "authenticity & imperfection" 2026 trend: a warm-paper sketch where ink
// strokes DRAW ON (rough boxes + arrows), with a two-colour risograph misregistration + grain. Analog, warm,
// hand-made — deliberately unlike every polished-digital shot. Deterministic (wobble seeded by index).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';

export const DURATION = 165; // 5.5s
const INK = '#243a6b', RISO = '#e0533f';

// a rough hand-drawn rectangle path (jittered corners, slightly overshooting)
function roughRect(x: number, y: number, w: number, h: number, s: number): string {
  const j = (k: number) => (hash01(s * 7 + k) - 0.5) * 10;
  return `M${x + j(1)},${y + j(2)} L${x + w + j(3)},${y + j(4)} L${x + w + j(5)},${y + h + j(6)} L${x + j(7)},${y + h + j(8)} Z`;
}

const Sketch: React.FC<{d: string; t: number; at: number; color: string; len?: number; sw?: number}> = ({d, t, at, color, len = 900, sw = 5}) => {
  const draw = clamp01((t - at) / 0.2);
  return <path d={d} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"
    strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />;
};

export const HandDrawn: React.FC<{items?: string[]}> = ({items = ['You', 'WorkBuddy', 'Done ✓']} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const y = H / 2 - 120, bw = 380, bh = 240;
  const boxes = items.map((label, i) => ({x: 200 + i * 570, label, at: 0.08 + i * 0.27}));
  return (
    <AbsoluteFill style={{background: '#f3ecda'}}>
      {/* grain */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5, mixBlendMode: 'multiply'}}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width={W} height={H} filter="url(#grain)" opacity="0.12" />
      </svg>
      {/* riso misregistered under-layer (warm red, offset) */}
      <svg width={W} height={H} style={{position: 'absolute', left: 6, top: 7, opacity: 0.55}}>
        {boxes.map((b, i) => <Sketch key={i} d={roughRect(b.x, y, bw, bh, i + 1)} t={t} at={b.at} color={RISO} />)}
      </svg>
      {/* ink layer */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {boxes.map((b, i) => <Sketch key={i} d={roughRect(b.x, y, bw, bh, i + 1)} t={t} at={b.at} color={INK} />)}
        {/* hand-drawn arrows between boxes */}
        {[0, 1].map((i) => {
          const x1 = boxes[i].x + bw + 8, x2 = boxes[i + 1].x - 8, my = y + bh / 2;
          const d = `M${x1},${my} C${x1 + 60},${my - 40} ${x2 - 60},${my + 30} ${x2},${my} M${x2 - 26},${my - 16} L${x2},${my} L${x2 - 26},${my + 16}`;
          return <Sketch key={i} d={d} t={t} at={boxes[i].at + 0.16} color={INK} len={500} sw={4} />;
        })}
      </svg>
      {/* labels (slightly rotated for a hand feel) */}
      {boxes.map((b, i) => {
        const show = clamp01((t - b.at - 0.14) / 0.2);
        return <div key={i} style={{position: 'absolute', left: b.x, top: y, width: bw, height: bh, display: 'flex',
          alignItems: 'center', justifyContent: 'center', opacity: show, transform: `rotate(${(hash01(i + 9) - 0.5) * 3}deg)`,
          font: '800 56px/1.1 Inter,system-ui,sans-serif', color: INK, textAlign: 'center'}}>{b.label}</div>;
      })}
    </AbsoluteFill>
  );
};
export default HandDrawn;
