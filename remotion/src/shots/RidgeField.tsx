// SHOT · Ridge Field — stacked ridgeline curves (the "Unknown Pleasures" plot): rows of peaked lines, each
// filled to occlude the ones behind, rippling as a wave passes through, revealing bottom-up. Iconic
// generative data-landscape (family K · generative). Deterministic (ridge height = summed sines of x/row/t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#07060d';
const ROWS = 28, SAMP = 72;

export const RidgeField: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Signals', tagline: TAG = 'patterns in the noise', accent: ACC = '#8de0ff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const left = 260, right = W - 260, top = 190, rowGap = (H - 360) / ROWS;
  const height = (x: number, r: number) => {
    const cxn = (x - (left + right) / 2) / ((right - left) / 2);   // -1..1 across width
    const env = Math.exp(-cxn * cxn * 3);                          // peak toward centre
    const wave = Math.sin(x * 0.02 + r * 0.5 - t * 5) + 0.6 * Math.sin(x * 0.05 - r * 0.9 + t * 3);
    const ripple = 0.6 + 0.4 * Math.sin(r * 0.6 - t * 6);
    return env * (60 + 120 * ((wave + 1.6) / 3.2)) * ripple;
  };
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, #0d1030, ${BG} 78%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(ROWS)].map((_, r) => {
          const yBase = top + r * rowGap;
          const appear = clamp01(seg(t, 0.02 + (1 - r / ROWS) * 0.4, 0.24 + (1 - r / ROWS) * 0.4));
          if (appear <= 0) return null;
          let d = `M${left} ${yBase + 4}`;
          for (let s = 0; s <= SAMP; s++) {
            const x = lerp(left, right, s / SAMP);
            const y = yBase - height(x, r) * appear;
            d += ` L${x.toFixed(1)} ${y.toFixed(1)}`;
          }
          d += ` L${right} ${yBase + 4} Z`;
          const depth = r / ROWS;
          return <path key={r} d={d} fill={BG} stroke={ACC} strokeWidth={2}
            opacity={lerp(0.35, 1, depth)} style={{filter: depth > 0.6 ? `drop-shadow(0 0 4px ${ACC})` : undefined}} />;
        })}
      </svg>
      <div style={{position: 'absolute', top: 74, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#fff', font: '800 92px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.02em',
        textShadow: '0 8px 40px #000'}}>{TITLE}</div>
      <div style={{position: 'absolute', bottom: 90, left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.62, 0.84)), color: '#9fb2d0',
        font: '600 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default RidgeField;
