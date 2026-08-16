// InducedFID — the ACTUAL measured MR signal, not a voice-call waveform. The precessing transverse magnetization
// sweeps past a receive COIL and induces an oscillating voltage (Faraday's law); because the spins dephase (T2*),
// that voltage is a DECAYING oscillation — the Free Induction Decay. The damped sinusoid + the coil ARE the
// signal; a symmetric audio waveform (no decay) was decoration. Deterministic (pure fn of useT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';

export const DURATION = 180; // 6s

export const InducedFID: React.FC<{accent?: string; accent2?: string; label?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'The induced signal decays',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const midY = H * 0.52;
  const x0 = W * 0.16, x1 = W * 0.86, span = x1 - x0;

  // draw the FID as a damped sinusoid, revealed left→right as it is "acquired"
  const reveal = clamp01(seg(t, 0.08, 0.92));
  const cyc = 15;                                           // oscillations at the Larmor rate
  const pts: string[] = [];
  const xr = x0 + span * reveal;
  for (let x = x0; x <= xr; x += 2) {
    const u = (x - x0) / span;                              // 0..1 along the FID
    const decay = Math.exp(-u * 3.4);                       // T2* envelope: strong → dying away
    const y = midY - Math.sin(u * cyc * Math.PI * 2) * (H * 0.24) * decay;
    pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  // the decay envelope (a faint guide showing the signal dying)
  const envTop: string[] = [], envBot: string[] = [];
  for (let x = x0; x <= x1; x += 6) {
    const u = (x - x0) / span, d = Math.exp(-u * 3.4) * (H * 0.24);
    envTop.push(`${x.toFixed(1)},${(midY - d).toFixed(1)}`); envBot.push(`${x.toFixed(1)},${(midY + d).toFixed(1)}`);
  }
  // the read-out point (where the coil is currently sensing) + a small precessing spin above the coil
  const spin = t * Math.PI * 6;

  const A = (o: number) => `${accent}${Math.round(clamp01(o) * 255).toString(16).padStart(2, '0')}`;

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 48%, #0b1120, #05060a)'}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* decay envelope */}
        <polyline points={envTop.join(' ')} fill="none" stroke={accent2} strokeWidth={1.3} strokeDasharray="2 7" opacity={0.4} />
        <polyline points={envBot.join(' ')} fill="none" stroke={accent2} strokeWidth={1.3} strokeDasharray="2 7" opacity={0.4} />
        {/* baseline */}
        <line x1={x0} y1={midY} x2={x1} y2={midY} stroke={A(0.25)} strokeWidth={1} />
        {/* the FID trace */}
        <polyline points={pts.join(' ')} fill="none" stroke="#eaf6ff" strokeWidth={3} />
        {/* the receive COIL at the origin (a loop) + a precessing spin inducing the signal */}
        <ellipse cx={x0} cy={midY} rx={20} ry={40} fill="none" stroke={accent} strokeWidth={3} />
        <ellipse cx={x0} cy={midY} rx={11} ry={26} fill="none" stroke={accent} strokeWidth={2} opacity={0.6} />
        <circle cx={x0 + Math.cos(spin) * 22} cy={midY - 78 + Math.sin(spin) * 8} r={7} fill={accent} />
        <text x={x0 - 6} y={midY + 74} fill="#9fb4cc" fontSize="20" fontFamily="Inter, sans-serif" fontWeight={600}>coil</text>
        {/* labels */}
        <text x={x0 + span * 0.16} y={midY - H * 0.24 - 16} fill={accent} fontSize="19" fontFamily="'JetBrains Mono', monospace" letterSpacing="1">T2* decay</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}
        <div style={{marginTop: 8, font: "500 22px/1 'JetBrains Mono', monospace", color: '#8aa', letterSpacing: '0.12em'}}>
          free induction decay</div>
      </div>
    </AbsoluteFill>
  );
};
export default InducedFID;
