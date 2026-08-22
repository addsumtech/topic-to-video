// SHOT · Neon Ticker Wall — a night-city wall of signage: stacked LED ticker strips scroll headlines at
// different speeds/directions, neon billboards flicker, and a big central marquee holds the message. Urban,
// electric, Times-Square energy (family O · urban / signage). Deterministic (scroll = fn of t, flicker stepped).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#05060d';
const NEON = ['#ff2e88', '#00e5ff', '#ffe14d', '#8b5bff', '#39ff88'];

export const NeonTickerWall: React.FC<{headline?: string; tickers?: string[]; accent?: string}> = ({
  headline: HEADLINE = 'NOW SHIPPING', tickers: TICKERS =
    ['BREAKING · IT WORKS · ', 'LIVE NOW · ', 'ALL SYSTEMS GO · ', 'SOLD OUT · ENCORE · '],
  accent: ACC = '#ff2e88'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const flick = (seed: number) => 0.6 + 0.4 * (hash01(seed + Math.floor(t * 12)) > 0.15 ? 1 : 0.3);
  const marquee = easeOutBack(clamp01(seg(t, 0.24, 0.5)));
  const strips = [
    {y: 90, sp: 1, dir: 1}, {y: 210, sp: 1.7, dir: -1}, {y: 300, sp: 1.2, dir: 1},
    {y: H - 320, sp: 1.5, dir: -1}, {y: H - 210, sp: 1, dir: 1}, {y: H - 96, sp: 2.1, dir: -1},
  ];
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 90% at 50% 46%, #0c0f22, ${BG} 76%)`, overflow: 'hidden'}}>
      {/* rain of vertical light streaks (buildings) */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        {[...Array(24)].map((_, k) => {
          const x = (k / 24) * W + 20, col = NEON[k % NEON.length];
          return <rect key={k} x={x} y={0} width={3} height={H} fill={col} opacity={0.05 + 0.05 * hash01(k)} />;
        })}
      </svg>

      {/* scrolling LED ticker strips */}
      {strips.map((s, i) => {
        const col = NEON[i % NEON.length];
        const txt = (TICKERS[i % TICKERS.length] + '').repeat(8);
        const shift = ((t * s.sp * 420) % 800) * s.dir;
        return (
          <div key={i} style={{position: 'absolute', left: 0, right: 0, top: s.y, height: 64, overflow: 'hidden',
            background: '#0a0c18', borderTop: `1px solid ${col}55`, borderBottom: `1px solid ${col}55`,
            opacity: flick(i * 3.3)}}>
            <div style={{position: 'absolute', whiteSpace: 'nowrap', top: 10, left: 0, transform: `translateX(${-shift}px)`,
              color: col, font: '800 42px/1 "JetBrains Mono", monospace', letterSpacing: '0.06em',
              textShadow: `0 0 14px ${col}`}}>{txt}</div>
          </div>
        );
      })}

      {/* central neon billboard marquee */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{transform: `scale(${lerp(0.8, 1, marquee)})`, opacity: clamp01(marquee * 1.3),
          padding: '38px 66px', borderRadius: 18, background: '#07091a',
          border: `4px solid ${ACC}`, boxShadow: `0 0 60px ${ACC}88, inset 0 0 40px ${ACC}44`}}>
          <div style={{color: '#fff', font: '900 128px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.02em',
            textShadow: `0 0 30px ${ACC}, 0 0 60px ${ACC}`, opacity: flick(99)}}>{HEADLINE}</div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default NeonTickerWall;
