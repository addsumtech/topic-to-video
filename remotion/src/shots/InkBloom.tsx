// SHOT · Ink Bloom — a drop of ink DIFFUSES in water: feathery tendrils radiate and soft clouds spread from
// the centre through a turbulence-displaced blur, blooming into an organic mass behind a wordmark. Fluid,
// organic — distinct from discrete metaballs (family F · fluid). Deterministic (spread + tendrils = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';

export const DURATION = 155; // ~5.2s
const BG = '#f3eee4'; // a pale water ground so dark ink reads

export const InkBloom: React.FC<{title?: string; tagline?: string; ink?: string}> = ({
  title: TITLE = 'Diffuse', tagline: TAG = 'it spreads everywhere', ink: INK = '#1b2a5e'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const spread = easeOutCubic(clamp01(seg(t, 0.04, 0.7)));
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  const tendrils = 22;
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 46%, #ffffff, ${BG} 78%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="ink" x="-40%" y="-40%" width="180%" height="180%">
            <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="11" result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale={90 * spread} />
            <feGaussianBlur stdDeviation="5" />
          </filter>
        </defs>
        <g filter="url(#ink)" fill={INK}>
          {/* central bloom */}
          <circle cx={cx} cy={cy} r={280 * spread} opacity={0.5} />
          <circle cx={cx} cy={cy} r={180 * spread} opacity={0.6} />
          {/* radiating tendrils */}
          {[...Array(tendrils)].map((_, i) => {
            const a = (i / tendrils) * Math.PI * 2 + hash01(i) * 0.4;
            const reach = (260 + hash01(i * 3) * 360) * spread;
            const ex = cx + Math.cos(a) * reach, ey = cy + Math.sin(a) * reach;
            const midR = reach * 0.5, mx = cx + Math.cos(a + 0.3) * midR, my = cy + Math.sin(a + 0.3) * midR;
            const wgt = lerp(70, 8, clamp01(spread));
            return <path key={i} d={`M${cx} ${cy} Q ${mx} ${my} ${ex} ${ey}`} fill="none" stroke={INK}
              strokeWidth={wgt} strokeLinecap="round" opacity={0.4} />;
          })}
        </g>
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#fff',
          font: '800 132px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em',
          textShadow: `0 4px 30px ${INK}, 0 0 60px ${INK}aa`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 20, color: '#26314f',
          font: '600 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default InkBloom;
