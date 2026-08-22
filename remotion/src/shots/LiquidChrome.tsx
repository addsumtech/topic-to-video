// SHOT · Liquid Chrome — a HIGH-END Awwwards-register: a wordmark rendered as flowing liquid metal. A tall
// chrome gradient (reflected horizon bands) FLOWS vertically, a specular highlight sweeps across, chromatic-
// aberration fringe edges it, and a blurred mirror reflection sits below on a dark stage. Premium, editorial.
// Deterministic (flow + sweep = fn of t). Pure SVG — no WebGL, so it composites cleanly under Remotion.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA, mix, tint, shade} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
export const LiquidChrome: React.FC<{word?: string; tagline?: string}> = ({
  word: WORD = 'DELIVERED', tagline: SUB = 'your ai team · on your machine'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, baseY = H / 2 - 20;
  const flow = (t * 260) % 360;            // vertical band drift (loops via reflect)
  const sweep = lerp(-0.3, 1.3, (t * 0.9) % 1); // specular highlight x position 0..1
  const rise = easeOutExpo(seg(t, 0.05, 0.5));  // mercury rise-in
  const settle = easeOutCubic(seg(t, 0.05, 0.6));
  const fontPx = 260;
  const fontCss = `900 ${fontPx}px/1 "Playfair Display", "Times New Roman", Georgia, serif`;

  const Word: React.FC<{fill: string; opacity?: number; dx?: number; dy?: number}> = ({fill, opacity = 1, dx = 0, dy = 0}) => (
    <text x={cx + dx} y={baseY + dy} textAnchor="middle" dominantBaseline="middle"
      style={{font: fontCss, letterSpacing: '-0.02em'}} fill={fill} opacity={opacity}>{WORD}</text>
  );

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(120% 130% at 50% 34%, #1a1e26 0%, #0a0c11 62%, #06070a 100%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          {/* flowing chrome: reflected vertical bands, translated over time */}
          <linearGradient id="chrome" gradientUnits="userSpaceOnUse" x1="0" y1={-180 + flow} x2="0" y2={180 + flow} spreadMethod="reflect">
            {/* metallic ramp — the reflection bands are DERIVED from the DNA accent (chrome in the film's own hue,
                whatever the style), grey-metal when there is no DNA */}
            {(dna ? [['0', mix(dna.accent, dna.bg, 0.82)], ['0.28', dna.accent], ['0.42', tint(dna.accent, 0.86)], ['0.52', shade(dna.accent, 0.5)], ['0.66', dna.accent], ['0.82', mix(dna.accent, dna.bg, 0.62)], ['1', mix(dna.accent, dna.bg, 0.9)]]
                  : [['0', '#20242c'], ['0.28', '#c3ccd8'], ['0.42', '#ffffff'], ['0.52', '#8b95a3'], ['0.66', '#e9eef4'], ['0.82', '#454b56'], ['1', '#141821']]
             ).map(([o, c]) => <stop key={o} offset={o} stopColor={c} />)}
          </linearGradient>
          {/* specular sweep band */}
          <linearGradient id="spec" gradientUnits="objectBoundingBox" x1="0" y1="0" x2="1" y2="0">
            <stop offset={clamp01(sweep - 0.12).toString()} stopColor="#ffffff" stopOpacity="0" />
            <stop offset={clamp01(sweep).toString()} stopColor="#ffffff" stopOpacity="0.85" />
            <stop offset={clamp01(sweep + 0.12).toString()} stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>
          <filter id="refblur"><feGaussianBlur stdDeviation="7" /></filter>
          {/* rise-in mask: reveal from the baseline upward */}
          <clipPath id="riseclip"><rect x={0} y={baseY - fontPx * 0.62 * rise - 10} width={W} height={fontPx * 0.62 * rise + fontPx} /></clipPath>
        </defs>

        {/* mirror reflection (flipped, blurred, faded) */}
        <g transform={`translate(0 ${baseY * 2 + 150}) scale(1 -1)`} opacity={0.16 * settle} filter="url(#refblur)">
          <Word fill="url(#chrome)" />
        </g>

        <g clipPath="url(#riseclip)" transform={`translate(0 ${(1 - settle) * 30}) `}>
          {/* chromatic-aberration fringe */}
          <Word fill={dna?.accent2 ?? '#ff2d55'} opacity={0.5} dx={-4} />
          <Word fill={dna?.accent ?? '#22d3ee'} opacity={0.5} dx={4} />
          {/* chrome body */}
          <Word fill="url(#chrome)" />
          {/* specular sweep on top (screen) */}
          <g style={{mixBlendMode: 'screen'}}><Word fill="url(#spec)" /></g>
        </g>
      </svg>

      {/* refined sub-line, letter-spaced small caps */}
      <div style={{position: 'absolute', left: 0, right: 0, top: baseY + 190, textAlign: 'center',
        opacity: clamp01(seg(t, 0.55, 0.8)), font: '500 30px/1 var(--f-mono, "JetBrains Mono", ui-monospace, monospace)',
        color: '#9aa6b6', letterSpacing: '0.42em', textTransform: 'uppercase', paddingLeft: '0.42em'}}>{SUB}</div>

      {/* soft top vignette for depth */}
      <AbsoluteFill style={{background: 'linear-gradient(#06070a00 60%, #06070a 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default LiquidChrome;
