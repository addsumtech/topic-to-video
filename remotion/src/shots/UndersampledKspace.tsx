// UndersampledKspace — what "4–8× too sparsely" actually means: a full Cartesian k-space (every phase-encode
// line) has most of its lines REMOVED, keeping only every 6th — the measurements you skip to go faster. A deep
// network (trained on the fastMRI scale, 167k slices) reconstructs the image from what's left. The vanishing
// lines + the surviving sparse subset ARE the idea. Deterministic (pure fn of useT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';

export const DURATION = 180; // 6s

export const UndersampledKspace: React.FC<{accent?: string; accent2?: string; label?: string; keep?: number}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Reconstruct from far fewer lines', keep = 6,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const gx = W * 0.16, gw = W * 0.68, gy = H * 0.2, gh = H * 0.52;   // k-space grid box
  const nLines = 42;
  const drop = clamp01(seg(t, 0.15, 0.75));                 // how far the removal has progressed

  const lines: React.ReactNode[] = [];
  for (let i = 0; i < nLines; i++) {
    const y = gy + (i + 0.5) * (gh / nLines);
    const kept = i % keep === 0;
    // kept lines stay bright; the rest FADE OUT as `drop` advances
    const op = kept ? 0.95 : lerp(0.6, 0.06, drop);
    const col = kept ? accent : accent2;
    lines.push(<line key={i} x1={gx} y1={y} x2={gx + gw} y2={y} stroke={col} strokeWidth={kept ? 2.6 : 1.2} opacity={op} />);
  }

  // counters
  const total = nLines, acquired = Math.round(nLines / keep);
  const shownAcq = Math.round(lerp(total, acquired, drop));
  const scans = Math.round(lerp(0, 167, clamp01(seg(t, 0.2, 0.85))));

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 40%, #0b1120, #05060a)'}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <rect x={gx - 14} y={gy - 14} width={gw + 28} height={gh + 28} rx={10} fill="none" stroke={accent} strokeWidth={1.4} opacity={0.35} />
        {lines}
        <text x={gx - 14} y={gy - 26} fill="#9fb4cc" fontSize="22" fontFamily="'JetBrains Mono', monospace" letterSpacing="1">k-space · phase-encode lines</text>
        {/* live count of acquired lines */}
        <text x={gx + gw + 40} y={gy + gh * 0.42} fill="#eaf6ff" fontSize="72" fontFamily="Inter, sans-serif" fontWeight={800}>
          {shownAcq}<tspan fill={accent} fontSize="40">/{total}</tspan></text>
        <text x={gx + gw + 44} y={gy + gh * 0.42 + 40} fill="#8aa" fontSize="22" fontFamily="'JetBrains Mono', monospace">lines acquired</text>
        <text x={gx + gw + 44} y={gy + gh * 0.42 + 96} fill={accent2} fontSize="26" fontFamily="Inter, sans-serif" fontWeight={700}>~4–8× undersampled</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}
        <div style={{marginTop: 8, font: "600 22px/1 'JetBrains Mono', monospace", color: '#8aa', letterSpacing: '0.1em'}}>
          deep network · trained on {scans}k scans</div>
      </div>
    </AbsoluteFill>
  );
};
export default UndersampledKspace;
