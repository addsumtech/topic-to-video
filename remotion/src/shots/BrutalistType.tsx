// SHOT · Brutalist Type — a raw brutalist-editorial register: stark off-white/black + one hot accent, oversized
// grotesque type in hard-edged boxes, mono metadata, harsh rules, and a brief RGB-glitch jolt. Aggressive,
// anti-slick — the opposite pole from the refined SwissEditorial. Deterministic (glitch pulse = fn of frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo} from '../runtime/motion';

export const DURATION = 155; // ~5.2s
const BG = '#ececec', INK = '#0a0a0a', ACC = '#ff3b00';

export const BrutalistType: React.FC<{titleTop?: string; titleBottom?: string; meta?: string; statement1?: string; statement2?: string}> = ({
  titleTop = 'WORK', titleBottom = 'BUDDY.', meta = 'WORKBUDDY / LOCAL-FIRST', statement1 = 'NO CLOUD.', statement2 = 'NO NONSENSE.'} = {}) => {
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  // glitch jolts at two moments
  const g1 = clamp01(1 - Math.abs(t - 0.42) / 0.05), g2 = clamp01(1 - Math.abs(t - 0.72) / 0.04);
  const glitch = Math.max(g1, g2);
  const shift = glitch * (8 + (frame % 3) * 6);
  const slice = glitch > 0.3;
  const rise = easeOutExpo(seg(t, 0.06, 0.4));

  const Head: React.FC<{color: string; dx: number; blend?: string}> = ({color, dx, blend}) => (
    <div style={{position: 'absolute', inset: 0, transform: `translateX(${dx}px)`, color, mixBlendMode: (blend as any) || 'normal',
      font: '900 300px/0.82 "Archivo", "Helvetica Neue", Arial Narrow, sans-serif', letterSpacing: '-0.03em'}}>
      {titleTop}<br />{titleBottom}
    </div>
  );

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* hard rules + accent block */}
      <div style={{position: 'absolute', left: 90, right: 90, top: 150, height: 8, background: INK}} />
      <div style={{position: 'absolute', left: 90, right: 90, bottom: 150, height: 8, background: INK}} />
      <div style={{position: 'absolute', right: 90, top: 158, width: 260, height: 120, background: ACC}} />

      {/* metadata */}
      <div style={{position: 'absolute', left: 96, top: 100, color: INK, font: '800 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.02em'}}>{meta}</div>
      <div style={{position: 'absolute', right: 100, top: 186, color: BG, font: '800 46px/1 "JetBrains Mono", monospace'}}>01/03</div>

      {/* headline (RGB-glitch stack) */}
      <div style={{position: 'absolute', left: 96, top: 300, width: W - 200, height: 720, transform: `translateY(${(1 - rise) * 60}px)`, opacity: rise}}>
        {glitch > 0.1 && <Head color="#ff004c" dx={-shift} blend="multiply" />}
        {glitch > 0.1 && <Head color="#00e5ff" dx={shift} blend="multiply" />}
        <Head color={INK} dx={0} />
        {/* glitch slice bars */}
        {slice && [0.2, 0.55, 0.8].map((yy, i) => (
          <div key={i} style={{position: 'absolute', left: -shift * 2, top: `${yy * 100}%`, width: '70%', height: 26, background: BG,
            transform: `translateX(${(i % 2 ? 1 : -1) * shift * 3}px)`}} />
        ))}
      </div>

      {/* statement */}
      <div style={{position: 'absolute', left: 96, bottom: 176, color: INK, font: '800 54px/1 "Archivo", Arial, sans-serif', letterSpacing: '-0.01em'}}>
        {statement1} <span style={{background: INK, color: BG, padding: '0 12px'}}>{statement2}</span>
      </div>
    </AbsoluteFill>
  );
};
export default BrutalistType;
