// SHOT · Cloth Wave — a silk flag ripples: horizontal fabric strips undulate on a travelling wave, shaded by
// the wave slope for a sheen, and the wordmark rides the ripple (each letter offset by the local wave). A
// tactile textile register (family Z · fabric). Deterministic (wave = summed sines of x + t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0c0f1a';
const STRIPS = 30;

export const ClothWave: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'Flow', tagline: TAG = 'soft power, in motion', accent: ACC = '#4d7cff', accent2: ACC2 = '#b44dff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const left = 160, right = W - 160, top = H / 2 - 300, cloth = 600, stripH = cloth / STRIPS;
  const settle = easeOutCubic(seg(t, 0.04, 0.5));                 // wave amplitude eases in
  const wave = (x: number, r: number) => {
    const amp = 70 * settle;
    return Math.sin(x * 0.006 + t * 4 + r * 0.12) * amp + Math.sin(x * 0.013 - t * 3) * amp * 0.4;
  };
  const slope = (x: number, r: number) => (wave(x + 20, r) - wave(x - 20, r)) / 40; // for sheen
  const titleIn = easeOutCubic(seg(t, 0.4, 0.66));
  const letters = TITLE.split('');
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 42%, #161a30, ${BG} 76%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><linearGradient id="silk" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor={ACC} /><stop offset="1" stopColor={ACC2} /></linearGradient></defs>
        {[...Array(STRIPS)].map((_, r) => {
          const yTop = top + r * stripH;
          const pts: string[] = [];
          for (let s = 0; s <= 40; s++) { const x = lerp(left, right, s / 40); pts.push(`${x.toFixed(1)} ${(yTop + wave(x, r)).toFixed(1)}`); }
          for (let s = 40; s >= 0; s--) { const x = lerp(left, right, s / 40); pts.push(`${x.toFixed(1)} ${(yTop + stripH + wave(x, r + 1)).toFixed(1)}`); }
          const sh = clamp01(0.5 + slope(cloth / 2 + left, r) * 1.2);  // sheen by slope
          return <path key={r} d={`M${pts.join(' L')} Z`} fill="url(#silk)" opacity={settle}
            style={{filter: `brightness(${lerp(0.55, 1.35, sh)})`}} />;
        })}
      </svg>
      {/* wordmark riding the ripple */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{display: 'flex', opacity: titleIn}}>
          {letters.map((ch, i) => {
            const lx = left + cloth * 0.5 + (i - letters.length / 2) * 96;
            const dy = wave(lx, STRIPS * 0.4);
            return <span key={i} style={{display: 'inline-block', transform: `translateY(${dy}px)`,
              color: '#fff', font: '900 150px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
              textShadow: '0 8px 30px #000a'}}>{ch}</span>;
          })}
        </div>
      </AbsoluteFill>
      <div style={{position: 'absolute', bottom: bottomInset(W, H, 120), left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.62, 0.84)), color: '#c7d0ee',
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default ClothWave;
