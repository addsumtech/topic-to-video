// SHOT · Physics Stack — a tactile gravity register: weighty blocks DROP from above and settle into an ascending
// result-bar chart with a real bounce (decaying) + a dust puff on impact. Physical, satisfying — distinct from
// the soft ClayStack (no physics) and flat IsometricAssembly. Deterministic (parabolic fall + damped bounce = t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
const DEFAULT_BARS = [
  {h: 220, c: '#4c8dff', label: 'Mon'}, {h: 320, c: '#22c9a0', label: 'Tue'}, {h: 250, c: '#b06cff', label: 'Wed'},
  {h: 430, c: '#ff8f5a', label: 'Thu'}, {h: 560, c: '#ffd23f', label: 'Fri'},
];

export const PhysicsStack: React.FC<{items?: string[]; label?: string}> = ({items, label = 'a week of shipping'} = {}) => {
  const BARS = items ? DEFAULT_BARS.map((b, i) => ({...b, label: items[i % items.length]})) : DEFAULT_BARS;
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const groundY = H - 200, bw = 180, gap = 46;
  const totalW = BARS.length * bw + (BARS.length - 1) * gap;
  const x0 = (W - totalW) / 2;

  // damped-bounce settle: block falls, lands at `land`, bounces a couple times decaying to rest
  const settleY = (targetTop: number, land: number) => {
    if (t < land) {const k = clamp01(t / land); return lerp(-400, targetTop, k * k);} // accelerating fall
    const s = clamp01((t - land) / 0.34);
    const bounce = Math.abs(Math.sin(s * Math.PI * 2.4)) * (1 - s) * 120; // decaying
    return targetTop - bounce;
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 24%, #141a26 0%, #0a0d14 72%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* ground */}
        <line x1={80} y1={groundY} x2={W - 80} y2={groundY} stroke="#2a3446" strokeWidth={3} />
        {[0.25, 0.5, 0.75].map((g, i) => <line key={i} x1={80} y1={groundY - 600 * g} x2={W - 80} y2={groundY - 600 * g} stroke="#161d29" strokeWidth={1.5} />)}

        {BARS.map((b, i) => {
          const land = 0.16 + i * 0.12;
          const top = settleY(groundY - b.h, land);
          const landed = t >= land;
          const impact = clamp01((t - land) / 0.12);
          return (
            <g key={i}>
              {/* dust puff on impact */}
              {landed && impact < 1 && [...Array(6)].map((_, k) => {
                const a = (k / 6) * Math.PI - Math.PI, d = impact * 90;
                return <circle key={k} cx={x0 + i * (bw + gap) + bw / 2 + Math.cos(a) * d} cy={groundY + Math.sin(a) * d * 0.3} r={lerp(14, 3, impact)} fill="#5a6675" opacity={(1 - impact) * 0.5} />;
              })}
              {/* bar */}
              <rect x={x0 + i * (bw + gap)} y={top} width={bw} height={groundY - top} rx={14} fill={b.c} />
              <rect x={x0 + i * (bw + gap)} y={top} width={bw} height={Math.min(28, groundY - top)} rx={14} fill="#ffffff" opacity={0.22} />
              {/* label */}
              <text x={x0 + i * (bw + gap) + bw / 2} y={groundY + 44} textAnchor="middle" fill="#8494a8" style={{font: '600 30px/1 Inter, system-ui, sans-serif'}}>{b.label}</text>
            </g>
          );
        })}
      </svg>

      <div style={{position: 'absolute', left: 0, right: 0, top: 130, textAlign: 'center',
        opacity: clamp01(seg(t, 0.7, 0.9)), color: '#eaf1ff', font: '800 56px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em'}}>
        {label}<span style={{color: '#ffd23f'}}>.</span>
      </div>
    </AbsoluteFill>
  );
};
export default PhysicsStack;
