// PhaseEncodeStep — phase encoding, encoded literally: a phase-encode GRADIENT BLIP steps through its amplitudes
// (−Gmax → +Gmax), and each step writes ONE line into k-space. The grid fills one line per repetition (TR) — the
// serial bottleneck that makes MRI slow. Gears (a generic "repeat") didn't show k-space filling; this does.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s

export const PhaseEncodeStep: React.FC<{accent?: string; accent2?: string; label?: string; steps?: number}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Phase encoding · one line per TR', steps = 16,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const cur = Math.min(steps - 1, Math.floor(clamp01(t) * steps));   // current phase-encode step

  // k-space grid (right): fill one line per step, from centre outward (typical order) — here top→bottom for clarity
  const gx = W * 0.44, gw = W * 0.4, gy = H * 0.24, gh = H * 0.5;
  const lines: React.ReactNode[] = [];
  for (let i = 0; i < steps; i++) {
    const y = gy + (i + 0.5) * (gh / steps);
    const on = i <= cur;
    const isCur = i === cur;
    lines.push(<line key={i} x1={gx} y1={y} x2={gx + gw} y2={y}
      stroke={isCur ? '#eaf6ff' : accent} strokeWidth={isCur ? 3.4 : 2.2} opacity={on ? (isCur ? 1 : 0.85) : 0.12} />);
  }

  // phase-encode gradient blip (left): a bar whose signed height = this step's amplitude (−Gmax..+Gmax)
  const amp = (cur / (steps - 1)) * 2 - 1;                   // −1..+1
  const bx = W * 0.24, baseY = H * 0.5, barMax = H * 0.18;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* k-space grid box */}
        <rect x={gx - 12} y={gy - 12} width={gw + 24} height={gh + 24} rx={8} fill="none" stroke={accent} strokeWidth={1.3} opacity={0.35} />
        {lines}
        <text x={gx - 12} y={gy - 24} fill="#9fb4cc" fontSize="20" fontFamily="'JetBrains Mono', monospace">k-space</text>
        <text x={gx + gw + 24} y={gy + gh * 0.5} fill="#eaf6ff" fontSize="52" fontFamily="Inter, sans-serif" fontWeight={800}>{cur + 1}<tspan fill={accent} fontSize="30">/{steps}</tspan></text>
        <text x={gx + gw + 26} y={gy + gh * 0.5 + 32} fill="#8aa" fontSize="18" fontFamily="'JetBrains Mono', monospace">lines written</text>

        {/* gradient blip */}
        <line x1={bx - 70} y1={baseY} x2={bx + 70} y2={baseY} stroke="#3a4658" strokeWidth={1.5} />
        <rect x={bx - 30} y={amp < 0 ? baseY : baseY - Math.abs(amp) * barMax} width={60} height={Math.abs(amp) * barMax || 2}
          rx={4} fill={accent2} opacity={0.9} />
        <text x={bx} y={baseY + barMax + 60} textAnchor="middle" fill="#c9d6ea" fontSize="22" fontFamily="Inter, sans-serif" fontWeight={700}>gradient blip</text>
        <text x={bx} y={baseY - barMax - 22} textAnchor="middle" fill="#8aa" fontSize="17" fontFamily="'JetBrains Mono', monospace">±Gmax · steps each TR</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default PhaseEncodeStep;
