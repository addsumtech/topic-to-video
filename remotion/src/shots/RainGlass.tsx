// SHOT · Rain Glass — a message sits behind a rain-blurred glass pane: droplets slide and streak down the
// glass, the soft-focus scene behind slowly SHARPENS as the title resolves. Atmospheric, moody, material
// (family X · weather/atmosphere). Muted palette. Deterministic (droplet y = fn of t + seed).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {darkGround} from '../runtime/light';

export const DURATION = 155; // ~5.2s
// @dark-world: a lit pane at night. Every droplet, wake and streak on the glass is drawn as WHITE at 6-30%
// opacity — a specular highlight catching the light behind it — and the scene behind the pane is three soft
// glows. Nothing here has a colour of its own to invert; on a warm-white film the register measured a median
// 1.62:1 with 100% of its marks under 3:1 (scripts/ink_contrast_qa.py) and the frame was blank cream with a
// title on it. Rain drawn as dark specks on paper is a dirty window, not a lit one, so it keeps its own night.
const BG1 = '#26313f', BG2 = '#3a4a5e';
const OWN_NIGHT = `linear-gradient(160deg, ${BG1}, ${BG2})`;

export const RainGlass: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Weather it', tagline: TAG = 'calm behind the storm', accent: ACC = '#9fd0ff'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const sharpen = easeOutCubic(seg(t, 0.3, 0.8));
  const blur = lerp(22, 2, sharpen);
  const titleIn = easeOutCubic(seg(t, 0.28, 0.6));
  const streaks = 46, drops = 60;
  // the film's ground while the film's ground is dark (all eight presets), this register's own night when it
  // is not. The branch is on what `darkGround` RETURNED, so a dark film grounded on exactly BG1 still gets
  // its own `bgGrad` treatment rather than ours.
  const night = darkGround(dna?.bg, BG1);
  const ground = night === dna?.bg ? (dna?.bgGrad ?? night) : OWN_NIGHT;
  return (
    <AbsoluteFill style={{background: ground, overflow: 'hidden'}}>
      {/* soft-focus scene behind the glass (blurred bokeh + the message) */}
      <div style={{position: 'absolute', inset: 0, filter: `blur(${blur}px)`}}>
        <div style={{position: 'absolute', inset: 0,
          background: `radial-gradient(30% 40% at 26% 34%, ${ACC}44, #0000 60%), radial-gradient(26% 34% at 74% 62%, #ffd79955, #0000 60%), radial-gradient(20% 26% at 60% 20%, #ffffff33, #0000 60%)`}} />
        <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
          <div style={{opacity: titleIn, color: '#f2f7ff', font: '800 138px/1 var(--f-display, Inter, system-ui, sans-serif)',
            letterSpacing: '-0.03em', textShadow: '0 10px 50px #0009'}}>{TITLE}</div>
          <div style={{opacity: clamp01(seg(t, 0.5, 0.74)), marginTop: 22, color: '#cfe0f5',
            font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em'}}>{TAG}</div>
        </AbsoluteFill>
      </div>

      {/* glass sheen + rain on the pane (crisp, in front) */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* thin static streaks */}
        {[...Array(streaks)].map((_, i) => {
          const x = hash01(i * 3.1) * W, len = 40 + hash01(i * 7.7) * 200, y = hash01(i * 5.5) * H;
          return <line key={'s' + i} x1={x} y1={y} x2={x + 6} y2={y + len} stroke="#ffffff" strokeWidth={2} opacity={0.06} />;
        })}
        {/* sliding droplets with a trailing wake */}
        {[...Array(drops)].map((_, i) => {
          const x = hash01(i * 2.3) * W, spd = 0.3 + hash01(i * 9.1) * 0.9;
          const y = ((t * spd + hash01(i * 4.4)) % 1.2) * H;
          const r = 3 + hash01(i * 6.6) * 6;
          return <g key={'d' + i}>
            <line x1={x} y1={y - r * 8} x2={x} y2={y} stroke="#ffffff" strokeWidth={r * 0.5} opacity={0.08} />
            <circle cx={x} cy={y} r={r} fill="#ffffff" opacity={0.16} />
            <circle cx={x - r * 0.3} cy={y - r * 0.3} r={r * 0.35} fill="#ffffff" opacity={0.3} />
          </g>;
        })}
      </svg>
      {/* vignette */}
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(120% 100% at 50% 50%, #0000 52%, #0007 100%)'}} />
    </AbsoluteFill>
  );
};
export default RainGlass;
