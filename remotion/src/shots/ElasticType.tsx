// SHOT · Elastic Type — jelly letters DROP in and jiggle with a damped elastic squash-stretch, then keep a
// soft gummy wobble, over a bright playful ground. The 2026 elastic/liquid-typography trend as a 2D gummy
// bounce (family P · dimensional type). Deterministic (elastic = damped sine of localT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';

export const DURATION = 145; // ~4.8s
const BG_D0 = '#141a2e';
const TONES0 = ['#ff5b7f', '#5b8cff', '#37d4a6', '#f6a531', '#c07bff'];

export const ElasticType: React.FC<{word?: string; tagline?: string}> = ({
  word: WORD = 'BOUNCE', tagline: TAG = 'springy, gummy, alive'} = {}) => {
  const dna = useDNA();
  const TONES = dnaPalette(dna, 5) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const letters = WORD.split('');
  const tagIn = easeOutCubic(seg(t, 0.66, 0.86));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, #1c2647, ${BG} 74%)`, overflow: 'hidden',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'flex-end'}}>
        {letters.map((ch, i) => {
          if (ch === ' ') return <div key={i} style={{width: 56}} />;
          const st = 0.06 + i * 0.08;
          const local = clamp01(seg(t, st, 1));
          const drop = easeOutCubic(clamp01(seg(t, st, st + 0.18)));
          // damped elastic squash-stretch after impact
          const impact = clamp01((t - (st + 0.16)) * 6);
          const decay = Math.exp(-(t - st) * 4);
          const jelly = impact > 0 ? Math.sin((t - st) * 22) * 0.22 * decay : 0;
          const settleWob = 0.03 * Math.sin(t * 5 - i * 0.7) * clamp01(local * 2);
          const sy = 1 - jelly + settleWob;
          const sx = 1 + jelly * 0.8 - settleWob;
          const tone = TONES[i % TONES.length];
          return (
            <div key={i} style={{opacity: clamp01(drop * 1.5),
              transform: `translateY(${(1 - drop) * -220}px) scale(${sx}, ${sy})`, transformOrigin: 'center bottom',
              margin: '0 4px', fontFamily: 'var(--f-display, "Baloo 2", Inter, system-ui, sans-serif)', fontWeight: 900,
              fontSize: 230, lineHeight: 1, color: tone,
              textShadow: `0 10px 0 rgba(0,0,0,.16), 0 26px 40px rgba(0,0,0,.4)`}}>{ch}</div>
          );
        })}
      </div>
      <div style={{opacity: tagIn, transform: `translateY(${(1 - tagIn) * 12}px)`, marginTop: 48, color: '#c7d0ee',
        font: '700 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.24em', textTransform: 'uppercase'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default ElasticType;
