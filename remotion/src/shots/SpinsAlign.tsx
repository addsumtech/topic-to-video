// SpinsAlign — spins ALIGNING, not a generic flow field. A cloud of proton spins starts pointing every which way
// (no net magnetism); slide into B0 and a TINY majority (~3 in a million) tips to point along the field, so a net
// magnetization M0 emerges from that faint excess. Random → slight-parallel-majority → net vector. Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 170; // ~5.7s

export const SpinsAlign: React.FC<{accent?: string; accent2?: string; label?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Spins align in the field', } = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const align = clamp01(seg(t, 0.15, 0.75));                 // 0 random → 1 field on
  const N = 60, arrows: React.ReactNode[] = [];
  for (let i = 0; i < N; i++) {
    const x = W * 0.14 + hash01(i * 2 + 1) * W * 0.56, y = H * 0.24 + hash01(i * 2 + 7) * H * 0.52;
    const rnd = hash01(i * 5) * Math.PI * 2;
    const flips = hash01(i * 11) < 0.5;                       // ~half nudge toward up; net excess is what counts
    const ang = lerp(rnd, flips ? -Math.PI / 2 : rnd, align);   // aligned ones point up (−90°)
    const len = 22;
    arrows.push(<line key={i} x1={x} y1={y} x2={x + Math.cos(ang) * len} y2={y + Math.sin(ang) * len}
      stroke={flips ? accent : '#6b7688'} strokeWidth={flips ? 2.4 : 1.6} opacity={flips ? 0.95 : 0.6}
      markerEnd={flips ? 'url(#sa)' : undefined} />);
  }
  const mBase = H * 0.78, mY = lerp(0, H * 0.15, align);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <defs><marker id="sa" markerWidth="9" markerHeight="9" refX="3" refY="4.5" orient="auto"><path d="M0,0 L6,4.5 L0,9 Z" fill={accent} /></marker></defs>
        {/* B0 field direction (up) appears as it turns on */}
        <line x1={W * 0.8} y1={H * 0.75} x2={W * 0.8} y2={H * 0.25} stroke={`${accent2}${Math.round(align * 160).toString(16).padStart(2, '0')}`} strokeWidth={2} strokeDasharray="4 6" />
        <text x={W * 0.8 + 12} y={H * 0.27} fill="#9fb4cc" fontSize="24" fontFamily="Inter, sans-serif" fontWeight={700} opacity={align}>B₀</text>
        {arrows}
        {/* the net magnetization that emerges from the tiny excess */}
        <line x1={W * 0.5} y1={mBase} x2={W * 0.5} y2={mBase - mY} stroke="#eaf6ff" strokeWidth={5} markerEnd="url(#sa2)" opacity={align} />
        <defs><marker id="sa2" markerWidth="12" markerHeight="12" refX="4" refY="6" orient="auto"><path d="M0,0 L8,6 L0,12 Z" fill="#eaf6ff" /></marker></defs>
        <text x={W * 0.5 + 16} y={mBase - mY} fill="#eaf6ff" fontSize="24" fontFamily="Inter, sans-serif" fontWeight={800} opacity={align}>M₀</text>
        <text x={W * 0.5} y={H * 0.84} textAnchor="middle" fill={accent} fontSize="20" fontFamily="'JetBrains Mono', monospace" opacity={align}>~3 in a million tip the balance → net signal</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default SpinsAlign;
