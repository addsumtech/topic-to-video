// SpinningProton — what a hydrogen nucleus IS, encoded: a single proton (+ charge) SPINNING, which makes it a
// tiny magnet — a magnetic dipole with field lines and a moment vector μ. Water (H₂O) all around supplies them
// in bulk. A generic ball-and-stick molecule didn't show the spin or the magnetism; this does. Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01, hash01, radians} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY} from '../runtime/layout';

export const DURATION = 180; // 6s

export const SpinningProton: React.FC<{accent?: string; accent2?: string; label?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'A proton that spins like a tiny magnet',
} = {}) => {
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const cx = W * 0.5, cy = H * 0.5 - 10, R = Math.min(W, H) * 0.075;
  const spin = t * Math.PI * 8;                              // the proton's spin

  // dipole field lines (the "tiny magnet") — nested loops through the poles
  const loops: React.ReactNode[] = [];
  for (let i = 1; i <= 4; i++) {
    const w = R * (0.8 + i * 0.85), h = R * (1.6 + i * 1.5);
    loops.push(<ellipse key={i} cx={cx} cy={cy} rx={w} ry={h} fill="none" stroke={accent} strokeWidth={1.4}
      opacity={0.34 - i * 0.05} transform={`rotate(${Math.sin(radians(t, durationInFrames, fps, 4)) * 4} ${cx} ${cy})`} />);
  }
  // faint background water molecules (bulk H₂O)
  const waters: React.ReactNode[] = [];
  for (let i = 0; i < 14; i++) {
    const x = hash01(i * 2 + 1) * W, y = hash01(i * 2 + 5) * H;
    if (Math.hypot(x - cx, y - cy) < R * 7) continue;
    waters.push(<g key={i} opacity={0.16} transform={`translate(${x} ${y})`}>
      <circle cx={0} cy={0} r={9} fill={accent2} /><circle cx={-13} cy={9} r={5} fill="#7f8aa0" /><circle cx={13} cy={9} r={5} fill="#7f8aa0" />
    </g>);
  }

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {waters}
        {loops}
        {/* the proton */}
        <circle cx={cx} cy={cy} r={R} fill="url(#pgrad)" stroke="#eaf6ff" strokeWidth={2} />
        <defs><radialGradient id="pgrad" cx="42%" cy="38%" r="70%">
          <stop offset="0%" stopColor="#fff" /><stop offset="55%" stopColor={accent} /><stop offset="100%" stopColor="#1c6a86" /></radialGradient></defs>
        <text x={cx} y={cy + 9} textAnchor="middle" fill="#04222c" fontSize={R * 0.8} fontFamily="var(--f-display, Inter, sans-serif)" fontWeight={800}>+</text>
        {/* spin arrow (angular momentum) — a curved arc around the pole */}
        <path d={`M ${cx - R * 1.5} ${cy - R * 1.7} A ${R * 1.5} ${R * 0.6} 0 1 1 ${cx + R * 1.5} ${cy - R * 1.7}`}
          fill="none" stroke={accent2} strokeWidth={2.5} markerEnd="url(#ah)"
          transform={`rotate(${(spin * 20) % 360} ${cx} ${cy - R * 1.7})`} opacity={0.9} />
        <defs><marker id="ah" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill={accent2} /></marker></defs>
        {/* magnetic moment vector μ (up, along the dipole) */}
        <line x1={cx} y1={cy} x2={cx} y2={cy - R * 5.4} stroke="#eaf6ff" strokeWidth={3} markerEnd="url(#ah2)" />
        <defs><marker id="ah2" markerWidth="12" markerHeight="12" refX="4" refY="6" orient="auto">
          <path d="M0,0 L8,6 L0,12 Z" fill="#eaf6ff" /></marker></defs>
        <text x={cx + 14} y={cy - R * 5} fill="#eaf6ff" fontSize="28" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800}>μ</text>
        <text x={cx} y={Math.min(cy + R * 5.6, bottomTextY(W, H))} textAnchor="middle" fill="#8aa" fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">~70% water · ¹H</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default SpinningProton;
