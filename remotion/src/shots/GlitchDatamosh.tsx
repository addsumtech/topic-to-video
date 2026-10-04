// SHOT · Glitch Datamosh — a word TEARS out of digital noise: RGB channels split and drift, horizontal
// displacement bands stutter-shift, scanlines + block noise flicker, then the signal RESOLVES (channels
// converge, tears settle) to a clean lockup. Aggressive digital-decay aesthetic (family M · glitch).
// Deterministic: all offsets from hash01 + a stepped fn of t (no RNG), so it stutters identically every render.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {bottomInset} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 140; // ~4.7s
// @dark-world: a BROKEN TRANSMISSION, which only exists as light coming off a screen. The tear is two offset
// copies of the word composited with `mixBlendMode: 'screen'` — additive light, and on a white ground screen
// is arithmetically a no-op, so the red and the cyan channel simply cease to exist. What is left is the third
// copy, pure white, plus scanlines and a vignette that are shaping a lit display rather than colouring a
// surface. Measured on a warm-white DNA (scripts/ink_contrast_qa.py, 2026-09-20) the register came back at a
// median 1.11:1 with 100% of its marks under 3:1, and the marked render is a blank sheet of paper with a
// ghost outline of SIGNAL on it — no split, no flecks, no tear. The picture has no meaning on paper because
// its subject is a signal failing, and a signal is not a pigment: inverting it would give dark ink torn on
// white, which reads as a misprint — a fault of the PAGE — and not as a channel losing sync.
const BG_D0 = '#07070b';

export const GlitchDatamosh: React.FC<{word?: string; tagline?: string; accent?: string}> = ({
  word: WORD = 'SIGNAL', tagline: TAG = 'noise, then clarity', accent: ACC = '#00e5ff'} = {}) => {
  const dna = useDNA();
  // the film's ground while the film's ground is dark (all eight presets, and no DNA at all); this
  // register's own night when it is not (see @dark-world above)
  const BG = darkGround(dna?.bg, BG_D0);
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  // glitch intensity: strong start, periodic bursts, resolves to ~0 by the end
  const base = clamp01(1 - seg(t, 0.55, 0.9));
  const burst = Math.max(0, Math.sin(t * 26)) * Math.max(0, Math.sin(t * 7));
  const g = clamp01(base * (0.5 + 0.5 * burst));
  const step = Math.floor(t * 14);                       // stutter clock (deterministic)
  const wordStyle: React.CSSProperties = {position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
    justifyContent: 'center', font: '900 240px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em'};
  const tagIn = easeOutCubic(seg(t, 0.7, 0.9));
  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* RGB-split channels */}
      <div style={{...wordStyle, color: '#ff004c', mixBlendMode: 'screen', transform: glide(`translate(${-14 * g - 4}px, ${6 * g}px)`, true)}}>{WORD}</div>
      <div style={{...wordStyle, color: ACC, mixBlendMode: 'screen', transform: glide(`translate(${14 * g + 4}px, ${-6 * g}px)`, true)}}>{WORD}</div>
      <div style={{...wordStyle, color: '#ffffff', opacity: 1 - 0.3 * g}}>{WORD}</div>

      {/* horizontal displacement / tear bands (copies of the word clipped to a strip, shoved sideways) */}
      {[...Array(7)].map((_, k) => {
        const on = hash01(k * 3.1 + step) > 0.55 ? 1 : 0;
        const top = (k / 7) * 100, bot = 100 - ((k + 1) / 7) * 100;
        const dx = (hash01(k * 9.7 + step) - 0.5) * 180 * g * on;
        return on && g > 0.02 ? (
          <div key={k} style={{...wordStyle, color: '#fff', clipPath: `inset(${top}% 0 ${bot}% 0)`,
            transform: `translateX(${dx}px)`, opacity: 0.9}}>{WORD}</div>
        ) : null;
      })}

      {/* block-noise flecks */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: g}}>
        {[...Array(22)].map((_, k) => {
          const on = hash01(k * 5.3 + step * 2) > 0.6;
          if (!on) return null;
          const x = hash01(k * 2.1 + step) * W, y = hash01(k * 7.9 + step) * H;
          // @decor: glitch slices are texture; their sizes are not a reading about the word
          const w = 30 + hash01(k * 4.4) * 160, h = 6 + hash01(k * 8.2) * 20;
          return <rect key={k} x={x} y={y} width={w} height={h} fill={k % 2 ? ACC : '#ff004c'} opacity={0.5} />;
        })}
      </svg>

      {/* scanlines + vignette */}
      <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.4 + 0.4 * g,
        background: 'repeating-linear-gradient(#0000 0 3px, #00000066 3px 4px)'}} />
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(120% 100% at 50% 50%, #0000 55%, #000a 100%)'}} />

      <div style={{position: 'absolute', left: 0, right: 0, bottom: bottomInset(W, H, 150), textAlign: 'center', opacity: tagIn,
        color: ACC, font: '700 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em', textTransform: 'uppercase',
        textShadow: `0 0 20px ${ACC}`}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default GlitchDatamosh;
