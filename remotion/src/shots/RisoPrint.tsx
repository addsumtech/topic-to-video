// SHOT · Riso Print — a risograph/screen-print wordmark on cream paper: two ink channels (pink + blue) start
// badly MISREGISTERED (an RGB-split look) and snap into registration on the beat, multiply-blended like real
// ink, over a grain + halftone texture. A warm, hand-printed craft register (family G) — and a rare LIGHT
// ground among the dark shots. Deterministic (offsets = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';

export const DURATION = 145; // ~4.8s
const PAPER = '#f2ecdd', PINK = '#ff5c8a', BLUE = '#2b52d6';

export const RisoPrint: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'PRINT IT', tagline: TAG = 'analog warmth, on purpose'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const reg = easeOutBack(clamp01(seg(t, 0.16, 0.62)));                  // misregistered → registered
  const wob = (1 - reg) + 0.06 * Math.sin(t * 22) * clamp01(seg(t, 0.62, 1)); // residual print wobble
  const dx = lerp(46, 5, reg) + wob * 6, dy = lerp(26, 3, reg);
  const tagIn = easeOutCubic(seg(t, 0.58, 0.82));
  const font = '900 210px/0.9 Inter, system-ui, sans-serif';
  const Layer: React.FC<{c: string; ox: number; oy: number}> = ({c, ox, oy}) => (
    <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
      transform: `translate(${ox}px, ${oy}px)`, mixBlendMode: 'multiply', color: c, font, letterSpacing: '-0.03em'}}>{TITLE}</div>
  );
  return (
    <AbsoluteFill style={{background: PAPER, overflow: 'hidden'}}>
      {/* halftone dots + grain (fixed-seed, deterministic) */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        <defs>
          <pattern id="ht" width={16} height={16} patternUnits="userSpaceOnUse">
            <circle cx={4} cy={4} r={1.5} fill="#00000022" /></pattern>
          <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" /></filter>
        </defs>
        <rect width={W} height={H} fill="url(#ht)" />
        <rect width={W} height={H} filter="url(#grain)" opacity={0.06} />
      </svg>

      <Layer c={BLUE} ox={-dx} oy={-dy} />
      <Layer c={PINK} ox={dx} oy={dy} />

      {/* registration marks in the corners */}
      {[[70, 70], [W - 70, 70], [70, H - 70], [W - 70, H - 70]].map((p, i) => (
        <svg key={i} width={44} height={44} style={{position: 'absolute', left: p[0] - 22, top: p[1] - 22, opacity: 0.5 * reg}}>
          <circle cx={22} cy={22} r={13} fill="none" stroke="#1a1a1a" strokeWidth={1.5} />
          <line x1={22} y1={2} x2={22} y2={42} stroke="#1a1a1a" strokeWidth={1.5} />
          <line x1={2} y1={22} x2={42} y2={22} stroke="#1a1a1a" strokeWidth={1.5} />
        </svg>
      ))}

      <div style={{position: 'absolute', left: 0, right: 0, bottom: 210, textAlign: 'center', opacity: tagIn,
        transform: `translateY(${(1 - tagIn) * 12}px)`, color: '#2a2a2a',
        font: '700 34px/1 "JetBrains Mono", monospace', letterSpacing: '0.22em', textTransform: 'uppercase'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default RisoPrint;
