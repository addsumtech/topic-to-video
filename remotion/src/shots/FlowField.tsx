// SHOT · Flow Field — hundreds of streamlines trace a static curl/flow field and DRAW ON in staggered waves,
// colour shifting along a duotone, revealing an ambient generative field with a wordmark settling at its
// centre. Generative-art motion you can't fake with gradients (family K · generative). Deterministic: the
// field is a pure fn of position, each streamline a fixed traced path animated by strokeDashoffset.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#070a14';

// static field angle at a point — a smooth curl from summed sinusoids (deterministic, no state)
const angleAt = (x: number, y: number) =>
  Math.sin(x * 0.0016 + Math.cos(y * 0.0012)) * Math.PI + Math.cos(y * 0.0018) * 0.9;

export const FlowField: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string; lines?: number}> = ({
  title: TITLE = 'In flow', tagline: TAG = 'everything, moving as one', accent: ACC = '#38e0c8',
  accent2: ACC2 = '#7a5bff', lines: LINES = 150} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const N = Math.max(20, Math.min(220, LINES));
  const STEPS = 34, STEP = 26;
  // build each streamline path once (field is static)
  const paths = [] as {d: string; len: number; col: string; seed: number}[];
  for (let i = 0; i < N; i++) {
    let x = hash01(i * 2.3) * W, y = hash01(i * 5.7) * H;
    let d = `M${x.toFixed(1)} ${y.toFixed(1)}`;
    for (let s = 0; s < STEPS; s++) {
      const a = angleAt(x, y);
      x += Math.cos(a) * STEP; y += Math.sin(a) * STEP;
      d += ` L${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    const mix = hash01(i * 9.1);
    paths.push({d, len: STEPS * STEP, col: mix < 0.5 ? ACC : ACC2, seed: i});
  }
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 45%, #0c1024, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {paths.map((p, i) => {
          const st = 0.02 + hash01(p.seed * 3.7) * 0.5;                  // staggered draw-on
          const draw = easeOutCubic(clamp01(seg(t, st, st + 0.4)));
          return <path key={i} d={p.d} fill="none" stroke={p.col} strokeWidth={2.2} strokeLinecap="round"
            opacity={0.16 + 0.5 * draw} strokeDasharray={p.len}
            strokeDashoffset={p.len * (1 - draw)} style={{filter: 'drop-shadow(0 0 3px currentColor)'}} />;
        })}
      </svg>
      {/* centre vignette so the wordmark reads over the field */}
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(34% 34% at 50% 48%, #070a14dd, #0000 70%)'}} />

      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 16}px)`, color: '#eafcff',
          font: '800 132px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em',
          textShadow: `0 0 50px ${ACC}55, 0 12px 40px #000`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 22, color: '#9fb2c8',
          font: '600 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default FlowField;
