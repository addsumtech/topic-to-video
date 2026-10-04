// SHOT · Metaball Merge — gooey liquid blobs orbit, MERGE into one mass and split again through the classic
// SVG "goo" filter (blur → alpha-threshold), a wordmark settling on the fluid. The 2026 liquid-glass / fluid
// register done as true metaballs, not gradients (family F · fluid). Deterministic (blob orbits = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01, radians} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#0a0713';

export const MetaballMerge: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'Fluid', tagline: TAG = 'many drops, one flow', accent: ACC = '#ff4fa3', accent2: ACC2 = '#7a5bff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const gather = easeOutCubic(seg(t, 0.2, 0.55));                 // spread → merged (stays a big soft mass)
  const balls = [...Array(10)].map((_, i) => {
    const ang = i / 10 * Math.PI * 2 + t * (0.6 + hash01(i) * 0.5);
    const spread = lerp(430 + hash01(i * 3) * 170, 175, gather) * (0.8 + 0.25 * Math.sin(radians(t, durationInFrames, fps, 6, i)));
    const r = lerp(120, 190, hash01(i * 7)) * (0.85 + 0.22 * Math.sin(radians(t, durationInFrames, fps, 4.5, i * 2)));
    return {x: cx + Math.cos(ang) * spread, y: cy + Math.sin(ang) * spread * 0.68, r};
  });
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 45%, #160c2a, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="22" result="b" />
            <feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 24 -11" result="g" />
            <feBlend in="SourceGraphic" in2="g" />
          </filter>
          <linearGradient id="mg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={ACC} /><stop offset="1" stopColor={ACC2} />
          </linearGradient>
        </defs>
        <g filter="url(#goo)">
          {balls.map((b, i) => (
            <circle key={i} cx={b.x} cy={b.y} r={b.r} fill="url(#mg)"
              style={{filter: `drop-shadow(0 0 0 ${ACC})`}} />
          ))}
        </g>
        {/* specular highlights (outside goo) — on the first four of the register's OWN ten blobs, which are
            generated here, not film items (this register takes only a title, a tagline and two colours) */}
        {/* // @truncates: the balls are the register's own generated decoration, not film content */}
        {balls.slice(0, 4).map((b, i) => (
          <ellipse key={i} cx={b.x - b.r * 0.3} cy={b.y - b.r * 0.35} rx={b.r * 0.28} ry={b.r * 0.2}
            fill="#ffffff" opacity={0.28} />
        ))}
      </svg>

      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 16}px)`, titleIn !== 1), color: '#fff',
          font: '800 150px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: '0 6px 30px #000, 0 0 60px #000c, 0 2px 0 #ffffff40'}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 20, color: '#fff',
          font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em',
          textShadow: '0 2px 14px #000, 0 0 24px #000c'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default MetaballMerge;
