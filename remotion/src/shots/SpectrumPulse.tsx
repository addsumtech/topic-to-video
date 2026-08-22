// SHOT · Spectrum Pulse — a circular audio spectrum: a ring of frequency bars radiate from the centre and
// dance to a synth beat (kick every half-second scales + brightens the whole rig), a wordmark pulsing at the
// core. A music / audio-reactive register (family U · audio). The spectrum is a DETERMINISTIC fn of t (a
// visual style, not tied to the real VO), so it renders identically every time.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#080611';
const BARS = 72;

export const SpectrumPulse: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'On beat', tagline: TAG = 'it moves with you', accent: ACC = '#ff3b8b', accent2: ACC2 = '#41b8ff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const beat = Math.exp(-((t * 2) % 1) * 6);                      // kick every 0.5s, sharp decay
  const R0 = 180 + beat * 14;
  const rev = easeOutCubic(seg(t, 0.04, 0.4));                    // ring reveals
  const titleIn = easeOutCubic(seg(t, 0.3, 0.55));
  const tagIn = easeOutCubic(seg(t, 0.6, 0.82));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 48%, #16091f, ${BG} 76%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${cx} ${cy})`}>
          {[...Array(BARS)].map((_, i) => {
            const ang = (i / BARS) * Math.PI * 2 - Math.PI / 2;
            // simulated frequency response: low bins (bass) louder, layered sines + beat envelope
            const freq = i / BARS;
            const bass = (1 - freq) ** 1.5;
            const amp = (0.4 + 0.6 * bass) * (0.5 + 0.5 * Math.abs(Math.sin(i * 0.5 + t * 7))) *
              (0.35 + 0.65 * Math.abs(Math.sin(i * 0.17 - t * 4.3)));
            const len = (30 + amp * 240 * (0.7 + 0.6 * beat)) * rev;
            const x1 = Math.cos(ang) * R0, y1 = Math.sin(ang) * R0;
            const x2 = Math.cos(ang) * (R0 + len), y2 = Math.sin(ang) * (R0 + len);
            const col = i % 2 ? ACC : ACC2;
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={col} strokeWidth={7} strokeLinecap="round"
              opacity={0.5 + 0.5 * amp} style={{filter: `drop-shadow(0 0 6px ${col})`}} />;
          })}
          <circle r={R0 - 14} fill="none" stroke="#ffffff22" strokeWidth={2} />
          <circle r={R0 - 14} fill={`url(#core)`} opacity={0.14 + 0.2 * beat} />
        </g>
        <defs><radialGradient id="core"><stop offset="0" stopColor="#fff" stopOpacity="0.4" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></radialGradient></defs>
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `scale(${1 + beat * 0.03})`, color: '#fff',
          font: '800 112px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em', textShadow: `0 0 40px ${ACC}66`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 18, color: '#c9b6e6',
          font: '600 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default SpectrumPulse;
