// SHOT · Chart Live — analytics language done as a LIVE DRAWING (not static bars/cards): a glowing line draws
// itself across, an area fills under it, a leading dot glows, and a headline metric counts up in step. Dark +
// a bright accent. Deterministic (draw progress + counter = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, clamp01} from '../runtime/motion';

export const DURATION = 150; // 5s
const ACC = '#37E0A0';
const DATA = [0.28, 0.34, 0.30, 0.44, 0.52, 0.48, 0.62, 0.7, 0.66, 0.82, 0.9, 0.96];

// Copy is overridable so a film can show a FAITHFUL, sourced figure (never a fabricated demo number).
export const ChartLive: React.FC<{endVal?: number; unit?: string; label?: string}> = ({endVal = 128, unit = 'k', label = 'tasks handled this month'}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const X0 = 220, X1 = W - 220, Y0 = H - 300, Y1 = 300;
  const pt = (i: number): [number, number] => [lerp(X0, X1, i / (DATA.length - 1)), lerp(Y0, Y1, DATA[i])];
  const path = DATA.map((_, i) => (i ? 'L' : 'M') + pt(i).join(',')).join(' ');
  const area = path + ` L${X1},${Y0} L${X0},${Y0} Z`;
  const prog = easeOutCubic(seg(t, 0.12, 0.86));
  const len = 4200;
  // leading dot position along the drawn portion
  const fi = prog * (DATA.length - 1); const li = Math.min(DATA.length - 2, Math.floor(fi));
  const lead: [number, number] = [lerp(pt(li)[0], pt(li + 1)[0], fi - li), lerp(pt(li)[1], pt(li + 1)[1], fi - li)];
  const val = Math.round(lerp(0, endVal, prog));
  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 30%, #0f1a1a, #060b0b 72%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="af" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={ACC} stopOpacity="0.35" /><stop offset="1" stopColor={ACC} stopOpacity="0" /></linearGradient>
          <filter id="lg"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <clipPath id="rev"><rect x={X0} y={0} width={(X1 - X0) * prog} height={H} /></clipPath>
        </defs>
        {/* gridlines */}
        {[0, 0.25, 0.5, 0.75, 1].map((g, i) => <line key={i} x1={X0} y1={lerp(Y0, Y1, g)} x2={X1} y2={lerp(Y0, Y1, g)} stroke="#16302a" strokeWidth={1.5} />)}
        {/* area + line, revealed left→right */}
        <g clipPath="url(#rev)">
          <path d={area} fill="url(#af)" />
          <path d={path} fill="none" stroke={ACC} strokeWidth={5} filter="url(#lg)" />
        </g>
        {/* leading dot */}
        {prog > 0.02 && prog < 0.99 && <circle cx={lead[0]} cy={lead[1]} r={12} fill="#eafff4" filter="url(#lg)" />}
      </svg>
      {/* headline metric counting up */}
      <div style={{position: 'absolute', left: 220, top: 150}}>
        <div style={{font: '800 210px/0.9 Inter,system-ui,sans-serif', color: '#eafff4', letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums'}}>{val}<span style={{fontSize: 100, color: ACC}}>{unit}</span></div>
        <div style={{font: '600 42px/1 Inter,system-ui,sans-serif', color: '#6f8f83', marginTop: 6}}>{label}</div>
      </div>
    </AbsoluteFill>
  );
};
export default ChartLive;
