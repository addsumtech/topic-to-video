// SHOT · Bokeh Pull — a cinematic focus-pull register: a drifting field of out-of-focus bokeh orbs, then the
// lens "pulls focus" — the orbs shrink and sharpen while a blurred wordmark resolves crisp. Real depth-of-field
// storytelling, distinct from FocalIsolation's UI blur. Deterministic (drift + focus = fn of t/frame).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, hash01, radians} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA, dnaPalette} from '../runtime/dna';
import {darkGround} from '../runtime/light';

export const DURATION = 160; // ~5.3s
// @dark-world: bokeh IS out-of-focus points of LIGHT. Each orb is an additive radial glow run at a fifth of
// full strength, and the beat closes on a lens vignette — a photograph of highlights, which is a thing that
// only exists when the rest of the frame is darker than they are. On a warm-white film it measured a median
// 2.81:1 with 60% of its marks under 3:1 (scripts/ink_contrast_qa.py) and the field read as dust. A dark
// disc on paper is a polka dot, not a highlight thrown out of focus, so this keeps its own night.
const COLORS0 = ['#ffd48a', '#8ab6ff', '#ff9ec9', '#8affce', '#c9a2ff', '#fff2c0'];
const OWN_NIGHT = 'radial-gradient(120% 120% at 50% 42%, #101828 0%, #070b14 66%, #04060c 100%)';
const OWN_NIGHT_FLAT = '#070b14';                 // the same night as one colour, for darkGround to judge

export const BokehPull: React.FC<{title?: string; tagline?: string}> = ({title = 'WorkBuddy', tagline = 'IN FOCUS'} = {}) => {
  const t = useT();
  const dna = useDNA();
  // the film's ground while the film's ground is dark (all eight presets), this register's own night when it
  // is not. The branch is on what `darkGround` RETURNED, so a dark film grounded on exactly this colour still
  // gets its own `bgGrad` treatment rather than ours.
  const night = darkGround(dna?.bg, OWN_NIGHT_FLAT);
  const onFilmGround = night === dna?.bg;
  const ground = onFilmGround ? (dna?.bgGrad ?? night) : OWN_NIGHT;
  // AND ITS OWN HIGHLIGHTS WITH IT. `dnaPalette` grows the orbs out of the film's two accents — which, on a
  // film that grounds on paper, were chosen to read ON paper and can be as dark as its ink. Dropped onto this
  // register's night those are orbs nobody can see, so the palette follows the ground it is drawn on: the
  // film's while the film's ground is dark (unchanged for every preset and for null DNA), ours when it is not.
  const COLORS = (onFilmGround ? dnaPalette(dna, 6) : null) ?? COLORS0;
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const focus = easeInOutCubic(seg(t, 0.32, 0.72)); // 0 = all blurred, 1 = sharp
  const wordBlur = lerp(34, 0, focus);
  const wordOp = clamp01(seg(t, 0.36, 0.66));

  return (
    <AbsoluteFill style={{background: ground}}>
      {/* bokeh field */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          {COLORS.map((c, i) => (
            <radialGradient key={i} id={`bk${i}`}><stop offset="0" stopColor={c} stopOpacity="0.9" />
              <stop offset="0.6" stopColor={c} stopOpacity="0.35" /><stop offset="1" stopColor={c} stopOpacity="0" /></radialGradient>
          ))}
          <filter id="soft"><feGaussianBlur stdDeviation={lerp(10, 1.5, focus)} /></filter>
        </defs>
        <g filter="url(#soft)">
          {[...Array(30)].map((_, i) => {
            const bx = (hash01(i) * 1.2 - 0.1) * W + Math.sin(radians(t, durationInFrames, fps, 7, i)) * 30;
            const by = ((hash01(i * 2) * H + t * (10 + hash01(i * 3) * 24)) % (H * 1.2)) - H * 0.1;
            const big = lerp(130, 26, focus) * (0.5 + hash01(i * 5));
            const op = lerp(0.55, 0.2, focus) * (0.5 + 0.5 * hash01(i * 7));
            return <circle key={i} cx={bx} cy={by} r={big} fill={`url(#bk${i % COLORS.length})`} opacity={op} />;
          })}
        </g>
      </svg>

      {/* the resolving wordmark */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
        <div style={{filter: `blur(${wordBlur}px)`, opacity: wordOp, color: '#f4f8ff',
          font: `800 190px/${leading(title, 0.92)} var(--f-display, "Playfair Display", Georgia, serif)`, letterSpacing: '-0.01em',
          textShadow: '0 20px 80px #000'}}>{title}</div>
        <div style={{marginTop: 24, filter: `blur(${wordBlur * 0.5}px)`, opacity: clamp01(seg(t, 0.62, 0.84)),
          color: '#9fb2cc', font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.4em', paddingLeft: '0.4em'}}>{tagline}</div>
      </AbsoluteFill>

      {/* lens vignette */}
      <AbsoluteFill style={{background: 'radial-gradient(120% 100% at 50% 50%, #0000 46%, #000000cc 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default BokehPull;
