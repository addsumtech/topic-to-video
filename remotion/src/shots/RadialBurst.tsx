// SHOT · Radial Burst — a kaleidoscopic radial-symmetry register: concentric rings of shapes BLOOM outward in
// N-fold symmetry and slowly rotate, resolving into a central hub. Mesmerizing, vivid, mandala-like — a
// composition axis none of the linear shots use. Deterministic (bloom per ring + spin = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
const N = 14;

export const RadialBurst: React.FC<{hub?: string; tagline?: string}> = ({hub: HUB = 'WorkBuddy', tagline = 'EVERYTHING, IN ORBIT'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const spin = t * 26;
  const hub = easeOutBack(seg(t, 0.02, 0.2));

  // ring descriptor: radius, bloom window, shape
  const rings = [
    {r: 190, a: 0.1, kind: 'ray', hueA: 190},
    {r: 300, a: 0.24, kind: 'petal', hueA: 260},
    {r: 410, a: 0.4, kind: 'dot', hueA: 320},
    {r: 520, a: 0.56, kind: 'petal', hueA: 30},
  ];

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 50%, #141032 0%, #0a0722 60%, #050318 100%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><filter id="rg"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        <g transform={`translate(${cx} ${cy}) rotate(${spin})`}>
          {rings.map((ring, ri) => {
            const bloom = easeOutBack(seg(t, ring.a, ring.a + 0.24));
            if (bloom <= 0) return null;
            return [...Array(N)].map((_, i) => {
              const ang = (i / N) * 360 + (ri % 2 ? 360 / N / 2 : 0);
              const hue = (ring.hueA + i * (360 / N) * 0.5) % 360;
              const col = `hsl(${hue} 85% 62%)`;
              const rr = ring.r * bloom;
              const common = {transform: `rotate(${ang}) translate(0 ${-rr})`, filter: 'url(#rg)'};
              if (ring.kind === 'ray')
                return <rect key={`${ri}-${i}`} x={-5} y={-70} width={10} height={140} rx={5} fill={col} {...common} opacity={0.9} />;
              if (ring.kind === 'dot')
                return <circle key={`${ri}-${i}`} r={16 * bloom} fill={col} {...common} />;
              // petal
              return <path key={`${ri}-${i}`} d="M0,-46 C26,-30 26,20 0,52 C-26,20 -26,-30 0,-46 Z" fill={col} {...common} opacity={0.92} transform={`rotate(${ang}) translate(0 ${-rr}) scale(${bloom})`} />;
            });
          })}
        </g>

        {/* central hub */}
        <g transform={`translate(${cx} ${cy}) scale(${hub})`}>
          <circle r={110} fill="#1a1440" stroke="#8f7bff" strokeWidth={3} filter="url(#rg)" />
          <circle r={64} fill="#c9b8ff" filter="url(#rg)" opacity={0.9} />
          <circle r={34} fill="#fff" />
        </g>
      </svg>

      <div style={{position: 'absolute', left: 0, right: 0, top: cy + 130, textAlign: 'center',
        opacity: clamp01(seg(t, 0.16, 0.32)), color: '#eae4ff', font: '800 40px/1 Inter, system-ui, sans-serif',
        letterSpacing: '-0.01em', textShadow: '0 2px 20px #000'}}>{HUB}</div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: H * 0.1, textAlign: 'center',
        opacity: clamp01(seg(t, 0.6, 0.82)), color: '#cbbfff', font: '600 34px/1 "JetBrains Mono", monospace',
        letterSpacing: '0.4em', paddingLeft: '0.4em'}}>{tagline}</div>
    </AbsoluteFill>
  );
};
export default RadialBurst;
