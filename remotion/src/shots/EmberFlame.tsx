// SHOT · Ember Flame — a wordmark forged in fire: flame licks flicker at the base, embers rise + drift + fade,
// heat-glow blooms, the title glowing in white-hot → red. An energy / passion register (family Y · fire).
// Deterministic (ember y = wrap of t·speed; flame licks = summed sines of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0b0402';

export const EmberFlame: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Ignite', tagline: TAG = 'built with fire'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, baseY = H * 0.66;
  const titleIn = easeOutCubic(seg(t, 0.28, 0.56));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  const flick = 0.85 + 0.15 * Math.sin(t * 30) * Math.sin(t * 11);
  // flame licks as layered wavy paths rising from the base
  const lick = (spanW: number, hgt: number, phase: number, col: string, op: number) => {
    const pts: string[] = [`${cx - spanW} ${baseY}`];
    for (let s = 0; s <= 20; s++) {
      const fx = cx - spanW + (s / 20) * spanW * 2;
      const rise = Math.sin((s / 20) * Math.PI) * hgt;
      const wob = Math.sin(s * 0.8 + t * 6 + phase) * 26 + Math.sin(s * 1.9 - t * 9) * 12;
      pts.push(`${fx} ${baseY - rise * flick + wob}`);
    }
    pts.push(`${cx + spanW} ${baseY}`);
    return <path d={`M${pts.join(' L')} Z`} fill={col} opacity={op} />;
  };
  return (
    <AbsoluteFill style={{background: `radial-gradient(90% 70% at 50% 78%, #3a1004, ${BG} 70%)`, overflow: 'hidden'}}>
      {/* heat glow */}
      <div style={{position: 'absolute', left: cx, top: baseY - 120, width: 900, height: 700, transform: 'translate(-50%,-50%)',
        background: 'radial-gradient(circle, #ff7a1866, #ff2e0022 40%, #0000 68%)', opacity: 0.6 + 0.2 * flick}} />
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, filter: 'blur(2px)'}}>
        {lick(360, 520, 0, '#7a1500', 0.7)}
        {lick(300, 470, 1.4, '#ff4d00', 0.7)}
        {lick(220, 400, 2.7, '#ff9a1e', 0.8)}
        {lick(130, 300, 4.1, '#ffe08a', 0.9)}
      </svg>
      {/* rising embers */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(70)].map((_, i) => {
          const x0 = cx + (hash01(i * 3.1) - 0.5) * 760;
          const life = ((t * (0.4 + hash01(i * 7) * 0.7) + hash01(i * 5)) % 1);
          const y = baseY - life * (H * 0.7);
          const x = x0 + Math.sin(life * 8 + i) * 40;
          const r = (1 + hash01(i * 9) * 3.5) * (1 - life * 0.5);
          return <circle key={i} cx={x} cy={y} r={r} fill={hash01(i) > 0.5 ? '#ffcf6a' : '#ff6a1e'}
            opacity={clamp01((1 - life) * 1.3)} style={{filter: 'drop-shadow(0 0 4px #ff8a2e)'}} />;
        })}
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingBottom: 40}}>
        {/* the shadows sit on a wrapper: a drop-shadow keeps only the scale of the matrix above it, so the flickering
            title's unlock has to be BELOW the filter to reach its glyphs (runtime/glide.ts) */}
        <div style={{filter: 'drop-shadow(0 4px 10px #000d) drop-shadow(0 0 44px #ff6a1eaa)'}}>
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 16}px) scale(${1 + (flick - 0.85) * 0.15})`, true),
          font: '900 168px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          background: 'linear-gradient(180deg, #fff7e0, #ffd24d 40%, #ff6a1e 72%, #ffb04d)',
          WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent',
          WebkitTextStroke: '2px #4a0f00'} as React.CSSProperties}>{TITLE}</div>
        </div>
        <div style={{opacity: tagIn, marginTop: 10, color: '#ffcf9a',
          font: '700 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.24em', textTransform: 'uppercase'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default EmberFlame;
