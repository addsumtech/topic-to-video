// SHOT · Analog Tape — the 2026 "authenticity / analog revival" register: a warm VHS/CRT treatment — tungsten
// gradient, scanlines, RGB chromatic split, a rolling tracking band, grain, barrel vignette, and a retro OSD
// (● REC, timestamp, ▶ PLAY). Nostalgic, textured, human — the anti-slick shot. Deterministic (jitter = fn t).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, clamp01, seg, lerp} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'REC',
  '▶ PLAY',
];

export const AnalogTape: React.FC<{title?: string; tagline?: string}> = ({title: TITLE = 'WorkBuddy', tagline: TAGLINE = 'ON YOUR MACHINE'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const jit = Math.sin(frame * 0.9) * 1.6 + Math.sin(frame * 2.3) * 0.8; // tape wobble (px)
  const split = 3 + Math.abs(Math.sin(frame * 0.14)) * 4;                // RGB split amount
  const trackY = ((t * 1.4) % 1.25 - 0.12) * H;                         // rolling tracking band
  const recOn = frame % 40 < 26;                                         // blinking REC dot
  const inT = clamp01(seg(t, 0.06, 0.4));

  const Title: React.FC<{dx: number; color: string; blend?: string}> = ({dx, color, blend}) => (
    <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', transform: `translate(${dx + jit}px, ${jit * 0.4}px)`, mixBlendMode: (blend as any) || 'normal'}}>
      <div style={{color, font: '800 168px/0.95 var(--f-display, "Antonio", "Oswald", Impact, sans-serif)', letterSpacing: '0.02em',
        textTransform: 'uppercase', opacity: inT}}>{TITLE}</div>
      <div style={{color, font: '600 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.34em', marginTop: 22,
        opacity: clamp01(seg(t, 0.4, 0.7))}}>{TAGLINE}</div>
    </div>
  );

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #4a2f18 0%, #241408 46%, #0b0704 100%)'), overflow: 'hidden'}}>
      {/* content with RGB chromatic split (three offset copies) */}
      <Title dx={-split} color="#ff3b3b" blend="screen" />
      <Title dx={split} color="#38f0ff" blend="screen" />
      <Title dx={0} color="#fff3df" />

      {/* scanlines */}
      <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.5,
        background: 'repeating-linear-gradient(#0000 0px, #0000 2px, #00000066 3px, #00000066 4px)'}} />

      {/* rolling tracking band */}
      <div style={{position: 'absolute', left: 0, right: 0, top: trackY, height: 60, pointerEvents: 'none',
        background: 'linear-gradient(#0000, #ffffff22 40%, #ffffff33 50%, #0000)', filter: 'blur(1px)'}} />

      {/* grain */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, mixBlendMode: 'overlay', opacity: 0.5}}>
        <filter id="tg"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" seed={frame % 8} /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width={W} height={H} filter="url(#tg)" />
      </svg>

      {/* OSD — retro on-screen display */}
      <div style={{position: 'absolute', left: 60, top: 48, display: 'flex', alignItems: 'center', gap: 16,
        font: '700 40px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)', color: '#eafff0', letterSpacing: '0.06em'}}>
        <span style={{width: 22, height: 22, borderRadius: 11, background: '#ff2b2b', opacity: recOn ? 1 : 0.15}} />REC
      </div>
      <div style={{position: 'absolute', right: 60, top: 48, font: '700 40px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)', color: '#eafff0'}}>SP · AUG&nbsp;12&nbsp;2026</div>
      <div style={{position: 'absolute', left: 60, bottom: 48, font: '700 44px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)', color: '#eafff0', letterSpacing: '0.1em'}}>▶ PLAY</div>
      <div style={{position: 'absolute', right: 60, bottom: 48, font: '700 40px/1 var(--f-mono, "VT323", "JetBrains Mono", monospace)', color: '#eafff0'}}>{String(Math.floor(t * 12)).padStart(2, '0')}:{String(Math.floor((t * 12 * 60) % 60)).padStart(2, '0')}</div>

      {/* CRT barrel vignette */}
      <AbsoluteFill style={{background: 'radial-gradient(110% 100% at 50% 50%, #0000 56%, #000000cc 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default AnalogTape;
