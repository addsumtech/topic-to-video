// SHOT · Kaleido Mandala — an N-fold mirror-symmetric kaleidoscope: a base wedge of shapes is replicated and
// mirrored around the centre, blooming outward + rotating with a colour cycle, then settling behind a
// wordmark. Generative radial symmetry (family K · generative). Deterministic (wedge shapes from index/sin).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack, hash01, radians} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0a0714';
const SEG = 12; // symmetry order

export const KaleidoMandala: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'Symmetry', tagline: TAG = 'order out of many', accent: ACC = '#ff4fa3', accent2: ACC2 = '#37e0ff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const bloom = easeOutBack(clamp01(seg(t, 0.06, 0.5)));
  const spin = t * 26;
  // base wedge: a few shapes at increasing radius (deterministic)
  const wedge = [...Array(5)].map((_, k) => {
    const r = lerp(90, 460, k / 4) * bloom;
    const col = k % 2 ? ACC : ACC2;
    const wob = 1 + 0.1 * Math.sin(radians(t, durationInFrames, fps, 5, k));
    return {r, col, k, wob};
  });
  const titleIn = easeOutCubic(seg(t, 0.52, 0.76));
  const tagIn = easeOutCubic(seg(t, 0.64, 0.86));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 50%, #160a2a, ${BG} 76%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${cx} ${cy}) rotate(${spin})`} opacity={clamp01(bloom * 1.2)}>
          {[...Array(SEG)].map((_, s) => {
            const rot = (360 / SEG) * s;
            const mir = s % 2 === 0 ? 1 : -1; // alternate mirror for a true kaleidoscope
            return (
              <g key={s} transform={`rotate(${rot}) scale(${mir}, 1)`}>
                {wedge.map((w) => {
                  const hueShift = (Math.sin(radians(t, durationInFrames, fps, 8, w.k)) + 1) / 2;
                  // @positional: every third wedge takes the second accent to make the mandala's pattern; no wedge carries a label
                  const col = w.k % 3 === 0 ? `color-mix(in oklab, ${ACC} ${Math.round(hueShift * 100)}%, ${ACC2})` : w.col;
                  const petalW = 46 * w.wob;
                  return <g key={w.k}>
                    <path d={`M0 ${-w.r} Q ${petalW} ${-w.r + 60} 0 ${-w.r + 130} Q ${-petalW} ${-w.r + 60} 0 ${-w.r} Z`}
                      fill={col} opacity={0.5} />
                    <circle cx={0} cy={-w.r} r={9 * w.wob} fill="#fff" opacity={0.5} />
                  </g>;
                })}
                <line x1={0} y1={0} x2={0} y2={-480 * bloom} stroke="#ffffff" strokeWidth={1.5} opacity={0.12} />
              </g>
            );
          })}
        </g>
      </svg>
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(30% 30% at 50% 50%, #0a0714dd, #0000 72%)'}} />
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#fff',
          font: '800 128px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em', textShadow: '0 10px 50px #000'}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 20, color: '#e7d8ff',
          font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em', textShadow: '0 4px 20px #000'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default KaleidoMandala;
