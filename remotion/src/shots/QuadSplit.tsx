// SHOT · Quad Split — the frame divides into a 2×2 grid of micro-panels that populate in sequence (each a
// distinct accent + a legible motif), a dividing cross snaps in, then ONE hero panel expands to take the
// whole frame. The "four angles, then the one that matters" register (comparison / overview). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeInOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const BG0 = '#0b0d14';
const TONES0 = ['#5b8cff', '#ff5b7f', '#22c197', '#f6a531'];

// a small decodable motif per cell (bars / ring / dots / wave) — never mystery furniture
const Motif: React.FC<{kind: number; c: string; g: number}> = ({kind, c, g}) => {
  if (kind === 0) return (
    <svg width={220} height={120}>{[0, 1, 2, 3, 4].map((b) => {
      const h = (28 + ((b * 37) % 70)) * clamp01(g * 1.4 - b * 0.08);
      return <rect key={b} x={b * 44} y={120 - h} width={30} height={h} rx={5} fill={c} />;
    })}</svg>);
  if (kind === 1) return (
    <svg width={140} height={140}><circle cx={70} cy={70} r={54} fill="none" stroke="#ffffff18" strokeWidth={12} />
      <circle cx={70} cy={70} r={54} fill="none" stroke={c} strokeWidth={12} strokeLinecap="round"
        strokeDasharray={2 * Math.PI * 54} strokeDashoffset={2 * Math.PI * 54 * (1 - 0.72 * g)}
        transform="rotate(-90 70 70)" /></svg>);
  if (kind === 2) return (
    <svg width={200} height={120}>{[...Array(12)].map((_, k) => {
      const on = k / 12 < g;
      return <circle key={k} cx={16 + (k % 6) * 34} cy={30 + Math.floor(k / 6) * 60} r={12}
        fill={on ? c : '#ffffff14'} />;
    })}</svg>);
  const pts = [...Array(24)].map((_, k) => {
    const x = (k / 23) * 220;
    const y = 60 - Math.sin(k * 0.6) * 34 * clamp01(g * 1.3 - k / 40);
    return `${x},${y}`;
  }).join(' ');
  return <svg width={220} height={120}><polyline points={pts} fill="none" stroke={c} strokeWidth={5} strokeLinecap="round" /></svg>;
};

export const QuadSplit: React.FC<{panels?: {label?: string}[]; heading?: string; hero?: number}> = ({
  panels: PANELS = [{label: 'Faster'}, {label: 'Simpler'}, {label: 'Cheaper'}, {label: 'Safer'}],
  heading: HEADING = 'Four ways it wins', hero: HERO = 0} = {}) => {
  const t = useT();
  const dna = useDNA(); const BG = dna?.bg ?? BG0; const TONES = dna ? [dna.accent, dna.accent2, dna.dim, dna.accent2] : TONES0;
  const {width: W, height: H} = useVideoConfig();
  const cells = PANELS.slice(0, 4);
  const heroIdx = Math.min(HERO, cells.length - 1);
  const HEAD = 112;                                 // clean header band so the title never sits on the panels
  const gap = 20, halfW = W / 2, halfH = (H - HEAD) / 2;
  const expand = easeInOutCubic(seg(t, 0.72, 0.97)); // hero takes the frame
  const headIn = clamp01(seg(t, 0.04, 0.16)) * (1 - clamp01(seg(t, 0.66, 0.74)));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {cells.map((p, i) => {
        const col = i % 2, row = Math.floor(i / 2);
        const enter = easeOutBack(clamp01(seg(t, 0.12 + i * 0.09, 0.34 + i * 0.09)));
        const grow = i === heroIdx ? expand : 0;
        const others = i === heroIdx ? 0 : expand;
        // base quadrant rect, then lerp the hero toward full-frame / others toward gone
        const x0 = col * halfW + gap / 2, y0 = HEAD + row * halfH + gap / 2;
        const w0 = halfW - gap, h0 = halfH - gap;
        const x = lerp(x0, 0, grow), y = lerp(y0, 0, grow);
        const w = lerp(w0, W, grow), h = lerp(h0, H, grow);
        const tone = TONES[i % TONES.length];
        const g = clamp01(seg(t, 0.16 + i * 0.09, 0.6)); // motif fill progress
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: w, height: h,
            opacity: (0.15 + 0.85 * enter) * (1 - others), transform: `scale(${lerp(0.9, 1, enter)})`,
            transformOrigin: `${col ? 'left' : 'right'} ${row ? 'top' : 'bottom'}`,
            background: `linear-gradient(150deg, #14172480, #0d0f18)`, border: '1px solid #20243a',
            borderRadius: lerp(22, 0, grow), overflow: 'hidden',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 54,
            boxShadow: i === heroIdx && grow > 0.1 ? `inset 0 0 200px ${tone}22` : '0 24px 60px #0006'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 18}}>
              <div style={{width: 16, height: 16, borderRadius: 5, background: tone,
                boxShadow: `0 0 20px ${tone}`}} />
              <div style={{color: '#7f879c', font: '600 24px/1 "JetBrains Mono", monospace',
                letterSpacing: '0.14em'}}>{String(i + 1).padStart(2, '0')}</div>
            </div>
            <Motif kind={i % 4} c={tone} g={g} />
            <div style={{color: '#f3f5ff', font: `800 ${lerp(56, 132, grow)}px/1 Inter, system-ui, sans-serif`,
              letterSpacing: '-0.02em'}}>{p.label}</div>
          </div>
        );
      })}
      <div style={{position: 'absolute', top: 42, left: 0, right: 0, textAlign: 'center', opacity: headIn,
        color: '#aeb6ca', font: '700 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.28em',
        textTransform: 'uppercase'}}>{HEADING}</div>
    </AbsoluteFill>
  );
};
export default QuadSplit;
