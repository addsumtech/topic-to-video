// SHOT · Liquid Metal — a chrome/mercury blob flows and MERGES (SVG goo filter) filled with a banded
// reflection gradient so it reads as molten metal, over a soft 2026 palette (lavender / icy-blue / warm
// beige), a chrome wordmark on top. The "liquid chrome, alive" trend (family F · fluid). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01, radians} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s

export const LiquidMetal: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Molten', tagline: TAG = 'chrome, but alive'} = {}) => {
  // LEVEL-C: chrome IS chrome on any ground (the silver reflection gradient is the metal's identity, kept), so only
  // the GROUND flips to the DNA (chrome reads even better on dark) + the tagline lifts to dim. Null DNA = original.
  const dna = useDNA();
  const bgc = dna?.bgGrad ?? dna?.bg ?? 'linear-gradient(160deg, #e9e3f5, #cfe0f2 55%, #f3ebdd)', TAGc = dna?.dim ?? '#4a5273';
  const t = useT();
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const gather = easeOutCubic(seg(t, 0.16, 0.55));
  const blobs = [...Array(8)].map((_, i) => {
    const ang = i / 8 * Math.PI * 2 + t * (0.5 + hash01(i) * 0.4);
    const spread = lerp(380 + hash01(i * 3) * 150, 150, gather) * (0.8 + 0.22 * Math.sin(radians(t, durationInFrames, fps, 6, i)));
    const r = lerp(120, 185, hash01(i * 7)) * (0.85 + 0.2 * Math.sin(radians(t, durationInFrames, fps, 4.5, i * 2)));
    return {x: cx + Math.cos(ang) * spread, y: cy + Math.sin(ang) * spread * 0.66, r};
  });
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: bgc, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="lmgoo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="20" result="b" />
            <feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 24 -11" />
          </filter>
          <linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#f6f8ff" /><stop offset="0.28" stopColor="#8a93b8" />
            <stop offset="0.42" stopColor="#3a4160" /><stop offset="0.5" stopColor="#c9d2ee" />
            <stop offset="0.62" stopColor="#2b3050" /><stop offset="0.8" stopColor="#9aa6cc" />
            <stop offset="1" stopColor="#e7ecfb" />
          </linearGradient>
        </defs>
        <g filter="url(#lmgoo)">
          {blobs.map((b, i) => <circle key={i} cx={b.x} cy={b.y} r={b.r} fill="url(#chrome)" />)}
        </g>
        {/* specular hot-spots */}
        {blobs.slice(0, 4).map((b, i) => (
          <ellipse key={i} cx={b.x - b.r * 0.28} cy={b.y - b.r * 0.4} rx={b.r * 0.26} ry={b.r * 0.16} fill="#ffffff" opacity={0.6} />
        ))}
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`,
          font: '900 150px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.04em',
          background: 'linear-gradient(180deg, #ffffff, #6b76a0 44%, #171b33 51%, #9aa6cc 58%, #eef2ff)',
          WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent',
          WebkitTextStroke: '2px #2b3050',
          filter: 'drop-shadow(0 3px 0 #ffffffcc) drop-shadow(0 10px 22px #1a1f3aaa)'} as React.CSSProperties}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 18, color: TAGc,
          font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em', textTransform: 'uppercase'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default LiquidMetal;
