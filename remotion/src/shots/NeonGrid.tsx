// SHOT · Neon Grid — a synthwave / retro-futuristic register: a neon perspective floor scrolls toward a
// gridded sun on the horizon under a starfield, with a glowing chrome-neon wordmark. High-energy, unmistakable
// atmosphere. Deterministic (grid scroll + twinkle = fn of t/frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s
const MAG_D0 = '#ff2d95', CYAN_D0 = '#22e3ff';

export const NeonGrid: React.FC<{title?: string; tagline?: string}> = ({title: TITLE = 'WORKBUDDY', tagline: TAGLINE = 'ON YOUR MACHINE'} = {}) => {
  const dna = useDNA();
  const MAG = dna?.accent ?? MAG_D0, CYAN = dna?.accent2 ?? CYAN_D0;
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const hy = H * 0.46, cx = W / 2;
  const scroll = (t * 0.6) % (1 / 16);
  const titleUp = easeOutExpo(seg(t, 0.12, 0.5));

  return (
    <AbsoluteFill style={{background: 'linear-gradient(#160726 0%, #2a0b3f 38%, #5b1063 47%, #12061f 55%, #0a0413 100%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="neon"><feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffe25a" /><stop offset="0.5" stopColor="#ff8a3c" /><stop offset="1" stopColor="#ff2d95" /></linearGradient>
          <clipPath id="floor"><rect x="0" y={hy} width={W} height={H - hy} /></clipPath>
        </defs>

        {/* stars */}
        {[...Array(70)].map((_, i) => {
          const x = hash01(i) * W, y = hash01(i * 2) * hy * 0.92;
          const tw = 0.4 + 0.6 * Math.abs(Math.sin(frame * 0.08 + i));
          return <circle key={i} cx={x} cy={y} r={hash01(i * 3) * 1.8 + 0.5} fill="#fff" opacity={tw * 0.8} />;
        })}

        {/* retro sun with scanline gaps */}
        <g>
          <circle cx={cx} cy={hy} r={180} fill="url(#sun)" filter="url(#neon)" />
          {[...Array(7)].map((_, i) => <rect key={i} x={cx - 190} y={hy + 30 + i * 22} width={380} height={11 + i * 1.6} fill="#2a0b3f" />)}
        </g>

        {/* perspective floor */}
        <g clipPath="url(#floor)">
          {/* vertical converging lines */}
          {[...Array(27)].map((_, i) => {
            const off = i - 13;
            return <line key={i} x1={cx} y1={hy} x2={cx + off * 200} y2={H} stroke={CYAN} strokeWidth={1.6} strokeOpacity={0.5} filter="url(#neon)" />;
          })}
          {/* horizontal scrolling lines (perspective-compressed) */}
          {[...Array(16)].map((_, i) => {
            const d = ((i / 16) + scroll) % 1;
            const y = hy + (H - hy) * d * d;
            return <line key={i} x1={0} y1={y} x2={W} y2={y} stroke={MAG} strokeWidth={1.2 + d * 2.4} strokeOpacity={0.35 + d * 0.5} filter="url(#neon)" />;
          })}
        </g>
        {/* horizon glow line */}
        <line x1={0} y1={hy} x2={W} y2={hy} stroke="#ffd0f0" strokeWidth={2.5} filter="url(#neon)" />
      </svg>

      {/* neon chrome wordmark */}
      <div style={{position: 'absolute', left: 0, right: 0, top: hy - 250, textAlign: 'center',
        transform: `translateY(${(1 - titleUp) * 30}px)`, opacity: titleUp}}>
        <div style={{font: '900 168px/0.9 "Antonio", Impact, sans-serif', letterSpacing: '0.02em',
          background: 'linear-gradient(#fff, #a7e9ff 40%, #ff9ee0 60%, #ff2d95)', WebkitBackgroundClip: 'text',
          backgroundClip: 'text', color: 'transparent', WebkitTextStroke: `2px ${CYAN}`, filter: 'drop-shadow(0 0 24px #ff2d9599)'}}>{TITLE}</div>
        <div style={{marginTop: 14, font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.5em',
          paddingLeft: '0.5em', color: CYAN, opacity: clamp01(seg(t, 0.45, 0.72)), textShadow: `0 0 18px ${CYAN}`}}>{TAGLINE}</div>
      </div>
    </AbsoluteFill>
  );
};
export default NeonGrid;
