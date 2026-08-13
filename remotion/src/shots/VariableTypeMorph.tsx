// SHOT · Variable Type Morph — one enormous word ALIVE on its type axes: a wave of WEIGHT (thin→black) travels
// across the letters while the whole word breathes on the WIDTH axis (condensed→expanded), each glyph
// overshooting into place over a drifting duotone field. The "type as a living material" register — bold,
// expressive typography beyond a static title (family J · experimental type). Deterministic (axes = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, easeInOutCubic} from '../runtime/motion';

export const DURATION = 155; // ~5.2s
const BG = '#08080f';

export const VariableTypeMorph: React.FC<{word?: string; kicker?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  word: WORD = 'EXPRESSIVE', kicker: KICKER = 'type, alive', tagline: TAG = 'weight · width · in motion',
  accent: ACC = '#ff5b7f', accent2: ACC2 = '#5b8cff'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const letters = WORD.split('');
  const n = letters.length;
  const fieldX = lerp(-0.2, 0.2, easeInOutCubic(t)) * W;
  const kickIn = easeOutCubic(seg(t, 0.04, 0.2));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center'}}>
      {/* drifting duotone field */}
      <div style={{position: 'absolute', inset: '-20%', filter: 'blur(80px)', opacity: 0.5,
        transform: `translateX(${fieldX}px)`,
        background: `radial-gradient(50% 60% at 30% 40%, ${ACC}, #0000 60%), radial-gradient(50% 60% at 72% 60%, ${ACC2}, #0000 60%)`}} />

      <div style={{opacity: kickIn, transform: `translateY(${(1 - kickIn) * 12}px)`, color: '#c7cee0',
        font: '600 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.5em', textTransform: 'uppercase',
        paddingLeft: '0.5em', marginBottom: 40, zIndex: 2}}>{KICKER}</div>

      <div style={{display: 'flex', alignItems: 'baseline', zIndex: 2}}>
        {letters.map((ch, i) => {
          const st = 0.12 + i * (0.4 / Math.max(1, n));
          const entr = easeOutBack(clamp01(seg(t, st, st + 0.3)));       // rise + thicken in
          // a weight wave that keeps travelling after entrance
          const wave = 0.5 + 0.5 * Math.sin(t * 4 - i * 0.6);
          const weight = Math.round(lerp(140, 900, clamp01(entr * 0.6 + wave * 0.5)));
          const widthAxis = lerp(0.66, 1.06 + 0.06 * Math.sin(t * 3 - i * 0.5), entr); // condensed→expanded breath
          const rise = (1 - entr) * 80;
          const hue = i / Math.max(1, n - 1);
          return (
            <span key={i} style={{display: 'inline-block', opacity: clamp01(entr * 1.4),
              transform: `translateY(${rise}px) scaleX(${widthAxis}) scaleY(${lerp(0.8, 1, entr)})`,
              transformOrigin: 'center bottom',
              fontFamily: 'Inter, system-ui, sans-serif', fontWeight: weight,
              fontSize: 210, lineHeight: 0.9, letterSpacing: '-0.02em',
              color: `color-mix(in oklab, ${ACC} ${Math.round((1 - hue) * 100)}%, ${ACC2})`,
              // enhancement if a variable font is present (harmless otherwise)
              fontVariationSettings: `"wght" ${weight}, "wdth" ${Math.round(widthAxis * 100)}`,
              textShadow: '0 20px 60px #000a'} as React.CSSProperties}>{ch}</span>
          );
        })}
      </div>

      <div style={{opacity: tagIn, transform: `translateY(${(1 - tagIn) * 10}px)`, marginTop: 44, color: '#8b93a8',
        font: '600 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.24em', textTransform: 'uppercase', zIndex: 2}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default VariableTypeMorph;
