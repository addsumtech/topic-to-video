// TensionScale — the mission-vs-money thesis, encoded as a balance that NEVER settles. A beam teeters on a
// central fulcrum: MISSION (benefit all) on one arm, SCALE / MONEY / POWER on the other. It oscillates gently
// and forever — neither arm wins, neither goes flat. A "VS" split or a payoff-burst would imply a victor or a
// resolution; this thesis is a SUSTAINED equilibrium, so the visual has to hold the tension, not break it.
// Deterministic (pure fn of useT); labels are props so it generalises to any two-force tension.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {titleStyle} from '../runtime/layout';

export const DURATION = 175; // ~5.8s

export const TensionScale: React.FC<{
  title?: string; leftLabel?: string; leftSub?: string; rightLabel?: string; rightSub?: string;
  note?: string; accent?: string; accent2?: string;
}> = ({
  title = 'The tension that never resolves', leftLabel = 'MISSION', leftSub = 'benefit all of humanity',
  rightLabel = 'SCALE - MONEY - POWER', rightSub = 'the cost of the race', note = 'neither side wins - that IS the story',
  accent = '#10a37f', accent2 = '#7aa2ff',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const portrait = W < H;
  const cx = W * 0.5, fy = portrait ? H * 0.46 : H * 0.52, L = portrait ? W * 0.30 : W * 0.30;
  const capBw = portrait ? Math.min(W * 0.4, 432) : 540;   // keep the end-pans on-frame in a narrow portrait frame
  // a gentle, damped-but-continuing teeter — small amplitude so it reads as HELD tension, never tipping over
  const settle = clamp01(t * 3);                                  // beam appears, then teeters
  const th = 0.095 * settle * Math.sin(t * Math.PI * 2 * 1.15) * (0.62 + 0.38 * Math.sin(t * Math.PI * 2 * 0.5));
  const lx = cx - L * Math.cos(th), ly = fy + L * Math.sin(th);   // MISSION arm end
  const rx = cx + L * Math.cos(th), ry = fy - L * Math.sin(th);   // SCALE/MONEY arm end
  const appear = clamp01(t * 4);

  const pan = (x: number, y: number, label: string, sub: string, col: string, key: string) => {
    // box + font ADAPT to the real label length so long labels don't overflow (size-for-real-content)
    const bw = Math.max(portrait ? 260 : 300, Math.min(capBw, Math.max(label.length * 13, sub.length * 8.5) + 44));
    const lfs = Math.min(22, (bw - 30) / Math.max(1, label.length * 0.62));
    return (
    <g key={key} opacity={appear}>
      <line x1={x} y1={y} x2={x} y2={y + 28} stroke={`${col}aa`} strokeWidth={2} />
      <rect x={x - bw / 2} y={y + 28} width={bw} height={78} rx={8} fill="#0d1117" stroke={col} strokeWidth={1.6} />
      <text x={x} y={y + 60} textAnchor="middle" fill={col} fontSize={lfs} fontFamily="'JetBrains Mono', monospace" fontWeight={700}>{label}</text>
      <text x={x} y={y + 88} textAnchor="middle" fill="#9fb0c3" fontSize="16" fontFamily="Inter, sans-serif">{sub}</text>
    </g>
    );
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0c1016, #06070a)')}}>
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        {/* faint technical grid baseline */}
        <line x1={W * 0.12} y1={fy} x2={W * 0.88} y2={fy} stroke="#1a2230" strokeWidth={1} strokeDasharray="2 10" opacity={0.6} />
        {/* the beam */}
        <line x1={lx} y1={ly} x2={rx} y2={ry} stroke="#e6edf5" strokeWidth={5} strokeLinecap="round" opacity={appear} />
        {/* the two force pans */}
        {pan(lx, ly, leftLabel, leftSub, accent, 'L')}
        {pan(rx, ry, rightLabel, rightSub, accent2, 'R')}
        {/* fulcrum triangle + glowing knot at the pivot */}
        <path d={`M${cx - 30},${fy + 66} L${cx},${fy + 6} L${cx + 30},${fy + 66} Z`} fill="#141b26" stroke="#2b3646" strokeWidth={1.4} />
        <circle cx={cx} cy={fy} r={9 + 3 * Math.sin(t * Math.PI * 2 * 1.15)} fill="#fff" opacity={0.9} />
        <circle cx={cx} cy={fy} r={20} fill="none" stroke={`${accent}`} strokeWidth={1.5} opacity={0.4 + 0.3 * Math.abs(Math.sin(t * Math.PI * 2 * 1.15))} />
        {/* equilibrium readout */}
        <text x={cx} y={fy + 96} textAnchor="middle" fill="#67788c" fontSize="15" fontFamily="'JetBrains Mono', monospace" opacity={appear}>equilibrium: unresolved</text>
        {/* bottom note (kept above the caption band) */}
        <text x={cx} y={H * 0.82} textAnchor="middle" fill="#c9d6ea" fontSize="20" fontFamily="'JetBrains Mono', monospace" opacity={clamp01((t - 0.15) * 3)}>{note}</text>
      </svg>
      <div style={{...titleStyle, opacity: lerp(0.4, 1, clamp01(t * 4))}}>{title}</div>
    </AbsoluteFill>
  );
};
export default TensionScale;
