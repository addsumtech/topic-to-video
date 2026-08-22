// SHOT · Aurora Flow — Stripe/Vercel "gradient craft" language: a living, flowing multi-hue aurora field
// (soft colour bodies drifting + blending) under crisp kinetic type. Premium, gradient-forward, deliberately
// unlike the flat/dark shots. Deterministic (blob positions = sin/cos of frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const BLOBS = [
  {c: '#4F7BFF', r: 780, sx: 0.00040, sy: 0.00055, px: 0.28, py: 0.32},
  {c: '#B14BFF', r: 720, sx: 0.00052, sy: 0.00038, px: 0.72, py: 0.30},
  {c: '#FF4F8B', r: 680, sx: 0.00035, sy: 0.00060, px: 0.62, py: 0.74},
  {c: '#22D3C5', r: 700, sx: 0.00060, sy: 0.00042, px: 0.30, py: 0.70},
  {c: '#FFB020', r: 560, sx: 0.00047, sy: 0.00050, px: 0.50, py: 0.52},
];

export const AuroraFlow: React.FC<{lines?: string[]}> = ({lines = ['Your AI team.', 'On your machine.']}) => {
  const dna = useDNA();
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: dna?.bg ?? '#0a0b12', overflow: 'hidden'}}>
      {/* the flowing aurora — drifting soft colour bodies that blend */}
      <AbsoluteFill style={{filter: 'blur(70px) saturate(1.3)'}}>
        {BLOBS.map((b, i) => {
          const x = (b.px + Math.sin(frame * b.sx * 60 + i) * 0.13) * W;
          const y = (b.py + Math.cos(frame * b.sy * 60 + i * 1.7) * 0.15) * H;
          return <div key={i} style={{position: 'absolute', left: x - b.r, top: y - b.r, width: b.r * 2, height: b.r * 2,
            borderRadius: '50%', background: `radial-gradient(closest-side, ${b.c}, transparent)`, opacity: 0.85}} />;
        })}
      </AbsoluteFill>
      {/* subtle darkening at the edges so type stays crisp */}
      <AbsoluteFill style={{background: 'radial-gradient(80% 80% at 50% 50%, transparent 40%, rgba(6,7,14,.6) 100%)'}} />
      {/* crisp kinetic type */}
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10}}>
        {lines.map((ln, i) => {
          const r = easeOutCubic(seg(t, 0.16 + i * 0.16, 0.16 + i * 0.16 + 0.34));
          return <div key={i} style={{font: '900 150px/1.02 Inter,system-ui,sans-serif', color: '#fff', letterSpacing: '-0.03em',
            opacity: clamp01(r), transform: `translateY(${lerp(40, 0, clamp01(r))}px)`, textShadow: '0 20px 80px rgba(0,0,0,.35)'}}>{ln}</div>;
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default AuroraFlow;
