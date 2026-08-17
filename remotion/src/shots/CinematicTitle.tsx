// SHOT · Cinematic Title — the premium "film-title" register (2026 cinematic-storytelling trend): letterboxed
// 2.39:1, a serif display title fading up from deep shadow with a slow push-in, an anamorphic lens-flare sweep,
// warm tungsten glow + drifting dust motes. Deep, unhurried, mood-first. Deterministic (push/flare/dust = fn t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic, hash01} from '../runtime/motion';

export const DURATION = 170; // ~5.7s
export const CinematicTitle: React.FC<{kicker?: string; title?: string; tagline?: string}> = ({
  kicker: KICKER = 'A NEW KIND OF TEAMMATE', title: TITLE = 'WorkBuddy', tagline: TAG = 'your ai team · on your machine'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const bar = 132; // letterbox height
  const push = lerp(1.06, 1.14, easeOutCubic(t)); // slow Ken-Burns push
  const titleUp = easeOutExpo(seg(t, 0.16, 0.62));
  const flareX = lerp(-0.15, 1.15, easeOutCubic(seg(t, 0.2, 0.85))) * W;
  const flareGlow = Math.sin(clamp01(seg(t, 0.2, 0.85)) * Math.PI); // rise then fall

  return (
    <AbsoluteFill style={{background: '#05060a', overflow: 'hidden'}}>
      {/* warm tungsten room-glow, pushed */}
      <div style={{position: 'absolute', inset: 0, transform: `scale(${push})`,
        background: 'radial-gradient(80% 70% at 62% 42%, #3a2a1c 0%, #14100c 42%, #05060a 78%)'}} />

      {/* dust motes drifting */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><filter id="dust"><feGaussianBlur stdDeviation="2.2" /></filter></defs>
        {[...Array(34)].map((_, i) => {
          const bx = hash01(i) * W;
          const by = (hash01(i * 2) * H + t * (14 + hash01(i * 3) * 26)) % H;
          const r = 1.4 + hash01(i * 5) * 3;
          const op = 0.12 + 0.32 * hash01(i * 7);
          return <circle key={i} cx={bx} cy={by} r={r} fill="#ffe6c0" opacity={op * (0.5 + 0.5 * flareGlow)} filter="url(#dust)" />;
        })}
      </svg>

      {/* title block */}
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: clamp01(seg(t, 0.24, 0.5)), color: '#c69a63', font: '600 26px/1 "JetBrains Mono", monospace',
          letterSpacing: '0.5em', textTransform: 'uppercase', paddingLeft: '0.5em', marginBottom: 34,
          transform: `translateY(${(1 - titleUp) * 18}px)`}}>{KICKER}</div>
        <div style={{opacity: titleUp, transform: `translateY(${(1 - titleUp) * 46}px)`, maxWidth: W * 0.9,
          color: '#f4efe6',
          // width-AND-length-aware so a long title / narrow (portrait|square) frame can't clip the wordmark
          font: `800 ${Math.min(176, W * 0.13, (W * 0.86) / Math.max(1, String(TITLE).length * 0.52))}px/0.98 "Playfair Display", Georgia, serif`,
          letterSpacing: '-0.01em', textShadow: '0 30px 90px #000, 0 2px 0 #ffffff22'}}>{TITLE}</div>
        <div style={{opacity: clamp01(seg(t, 0.55, 0.82)), color: '#8b93a3', font: '500 30px/1 "JetBrains Mono", monospace',
          letterSpacing: '0.36em', textTransform: 'uppercase', paddingLeft: '0.36em', marginTop: 30}}>{TAG}</div>
      </AbsoluteFill>

      {/* anamorphic lens flare sweep */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, mixBlendMode: 'screen'}}>
        <defs>
          <radialGradient id="core"><stop offset="0" stopColor="#fff7e8" stopOpacity="0.95" /><stop offset="1" stopColor="#fff7e8" stopOpacity="0" /></radialGradient>
          <linearGradient id="streak" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#9fd0ff" stopOpacity="0" /><stop offset="0.5" stopColor="#dff0ff" stopOpacity="0.9" /><stop offset="1" stopColor="#9fd0ff" stopOpacity="0" /></linearGradient>
          <filter id="fb"><feGaussianBlur stdDeviation="6" /></filter>
        </defs>
        <g opacity={flareGlow}>
          <rect x={flareX - 620} y={H / 2 - 3} width={1240} height={6} fill="url(#streak)" filter="url(#fb)" />
          <ellipse cx={flareX} cy={H / 2} rx={70} ry={70} fill="url(#core)" />
          <ellipse cx={flareX} cy={H / 2} rx={16} ry={220} fill="url(#streak)" filter="url(#fb)" opacity={0.5} />
        </g>
      </svg>

      {/* letterbox bars */}
      <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: bar, background: '#000'}} />
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: bar, background: '#000'}} />
      {/* vignette */}
      <AbsoluteFill style={{background: 'radial-gradient(120% 100% at 50% 50%, #0000 52%, #000000cc 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default CinematicTitle;
