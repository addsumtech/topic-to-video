// SHOT · Holo Foil — an iridescent holographic-foil register: a wordmark filled with a shifting rainbow foil
// (conic gradient rotating), a bright specular sheen sweeping across, and sparkle glints twinkling. Distinct
// from LiquidChrome's grey metal — this is trading-card holo. Premium, playful-luxe. Deterministic (hue + sheen = t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {fitTextPx} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
// CJK-EXEMPT (tight leading, no floor): the word is sized by fitTextPx to one line, so there is never a second line to collide with.
export const HoloFoil: React.FC<{word?: string; tagline?: string}> = ({word: WORD = 'WORKBUDDY', tagline: TAGLINE = 'YOUR AI TEAM'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const angle = (t * 220) % 360;                 // rotating foil hue
  const sheen = lerp(-0.3, 1.3, (t * 0.8) % 1);  // specular band x
  const rise = easeOutExpo(seg(t, 0.06, 0.5));
  const foil = `conic-gradient(from ${angle}deg at 50% 50%, #ff5db2, #ffd45b, #5bffcf, #5bb4ff, #b45bff, #ff5db2)`;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 40%, #14121c 0%, #0a0910 70%)')}}>
      {/* faint foil wash on the backdrop */}
      <div style={{position: 'absolute', inset: 0, background: foil, opacity: 0.1, filter: 'blur(60px)'}} />

      {/* the holo wordmark */}
      {/* sized to the WIDTH it ships at: 210px fits this word at 1920 and loses 107px off each edge at 1080 */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
        <div style={{position: 'relative', transform: `translateY(${(1 - rise) * 40}px)`, opacity: rise}}>
          <div style={{font: `900 ${fitTextPx(WORD, W, 210, {track: 0.01})}px/0.9 var(--f-display, "Antonio", Impact, sans-serif)`, letterSpacing: '0.01em',
            background: foil, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
            filter: 'drop-shadow(0 8px 30px #ff5db255) drop-shadow(0 0 2px #fff8)'}}>{WORD}</div>
          {/* specular sheen overlay (screen) */}
          <div style={{position: 'absolute', inset: 0, font: `900 ${fitTextPx(WORD, W, 210, {track: 0.01})}px/0.9 var(--f-display, "Antonio", Impact, sans-serif)`,
            letterSpacing: '0.01em', mixBlendMode: 'screen',
            background: `linear-gradient(105deg, #fff0 ${(sheen - 0.12) * 100}%, #ffffffdd ${sheen * 100}%, #fff0 ${(sheen + 0.12) * 100}%)`,
            WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent'}}>{WORD}</div>
        </div>
        <div style={{marginTop: 30, opacity: clamp01(seg(t, 0.5, 0.76)), color: '#c9c2e0',
          font: `600 ${fitTextPx(TAGLINE, W, 32, {track: 0.42})}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.42em', paddingLeft: '0.42em'}}>{TAGLINE}</div>
      </AbsoluteFill>

      {/* sparkle glints */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(16)].map((_, i) => {
          const x = W * (0.24 + hash01(i) * 0.52), y = H * (0.34 + hash01(i * 2) * 0.34);
          const ph = (t * 2 + hash01(i * 3)) % 1;
          const s = Math.sin(ph * Math.PI) * (6 + hash01(i * 5) * 10);
          if (s <= 0.5) return null;
          return <g key={i} stroke="#fff" strokeWidth={2} opacity={Math.sin(ph * Math.PI)}>
            <line x1={x - s} y1={y} x2={x + s} y2={y} /><line x1={x} y1={y - s} x2={x} y2={y + s} /></g>;
        })}
      </svg>
    </AbsoluteFill>
  );
};
export default HoloFoil;
