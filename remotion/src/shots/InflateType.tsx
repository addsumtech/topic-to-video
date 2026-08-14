// SHOT · Inflate Type — big puffy 3D BALLOON letters inflate into place with an over-bounce, glossy shaded
// fills + specular highlights + soft contact shadows, then a gentle breathing wobble. The 2026 inflated-3D
// typography trend (family P · dimensional type). Deterministic (inflate + wobble = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';

export const DURATION = 150; // 5s
const BG = '#0e1030';
const TONES = ['#ff6f9d', '#5b8cff', '#ffd24d', '#37e0c8', '#c07bff', '#ff8a4d'];

export const InflateType: React.FC<{word?: string; tagline?: string}> = ({
  word: WORD = 'PUFFY', tagline: TAG = 'soft, bold, dimensional'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const letters = WORD.split('');
  const n = letters.length;
  const tagIn = easeOutCubic(seg(t, 0.66, 0.86));
  // 3D extrusion via stacked shadows, glossy top-light gradient, specular blob
  const extrude = (c: string) => {
    let s = '';
    for (let k = 1; k <= 10; k++) s += `${k * 2}px ${k * 3}px 0 rgba(0,0,0,${0.06}), `;
    return s + `0 30px 50px rgba(0,0,0,.4)`;
  };
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 34%, #1a1c50, ${BG} 74%)`, overflow: 'hidden',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'center'}}>
        {letters.map((ch, i) => {
          const st = 0.08 + i * 0.09;
          const inf = easeOutBack(clamp01(seg(t, st, st + 0.34)));       // inflate with overshoot
          const settle = t > st + 0.34;
          const wob = settle ? 1 + 0.03 * Math.sin(t * 4 - i * 0.6) : 1; // breathing
          const sx = lerp(0.2, 1, inf) * (settle ? wob : 1);
          const sy = lerp(0.2, 1, inf) * (settle ? 2 - wob : 1);         // squash-counter for a soft-body feel
          const tone = TONES[i % TONES.length];
          if (ch === ' ') return <div key={i} style={{width: 60}} />;
          return (
            <div key={i} style={{position: 'relative', opacity: clamp01(inf * 1.6),
              transform: `translateY(${(1 - inf) * 40}px) scale(${sx}, ${sy})`, transformOrigin: 'center bottom',
              margin: '0 6px'}}>
              <span style={{display: 'block',
                fontFamily: '"Baloo 2", Inter, system-ui, sans-serif', fontWeight: 900, fontSize: 240, lineHeight: 1,
                letterSpacing: '-0.01em', color: tone,
                background: `linear-gradient(180deg, #ffffff, ${tone} 42%, ${tone})`,
                WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent',
                filter: `drop-shadow(6px 10px 0 rgba(0,0,0,.18)) drop-shadow(0 26px 34px rgba(0,0,0,.45))`,
                textShadow: extrude(tone)} as React.CSSProperties}>{ch}</span>
              {/* specular highlight */}
              <div style={{position: 'absolute', left: '24%', top: '14%', width: 46, height: 30, borderRadius: '50%',
                background: '#ffffff', opacity: 0.55 * inf, filter: 'blur(4px)'}} />
            </div>
          );
        })}
      </div>
      <div style={{opacity: tagIn, transform: `translateY(${(1 - tagIn) * 12}px)`, marginTop: 54, color: '#c7d0ff',
        font: '700 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.24em', textTransform: 'uppercase'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default InflateType;
