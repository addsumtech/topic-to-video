// GradientTilt — gradient encoding, encoded: the field starts UNIFORM across space (every position the same
// Larmor frequency), then a gradient coil TILTS it into a linear ramp B = B0 + G·x, so frequency now depends on
// POSITION (slow on the left, fast on the right). A targeting reticle showed none of this. Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 170; // ~5.7s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'coils  Gx · Gy · Gz    →    B = B₀ + G·x',
  'high freq',
  'low freq',
  'position →',
  'uniform field',
];

export const GradientTilt: React.FC<{accent?: string; accent2?: string; label?: string; cols?: number}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Position becomes frequency', cols = 11,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const on = clamp01(seg(t, 0.18, 0.72));                    // 0 uniform field → 1 tilted ramp
  const gx = W * 0.16, gw = W * 0.68, colW = gw / cols, baseY = H * 0.66, maxH = H * 0.26;

  const bars: React.ReactNode[] = [];
  for (let i = 0; i < cols; i++) {
    const u = i / (cols - 1);                                // 0..1 across space
    const field = lerp(0.5, 0.15 + u * 0.8, on);            // uniform 0.5 → linear ramp
    const hgt = field * maxH;
    const col = `hsl(${lerp(200, 200, 1)}, ${lerp(20, 80, on)}%, ${lerp(55, 40 + u * 35, on)}%)`;
    bars.push(<rect key={i} x={gx + i * colW + 3} y={baseY - hgt} width={colW - 6} height={hgt} rx={4}
      fill={i % 2 ? accent2 : accent} opacity={lerp(0.45, 0.55 + u * 0.4, on)} />);
  }

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <line x1={gx} y1={baseY} x2={gx + gw} y2={baseY} stroke="#3a4658" strokeWidth={1.5} />
        {bars}
        {/* the tilt line B0 → ramp */}
        <line x1={gx} y1={baseY - 0.5 * maxH} x2={gx + gw} y2={baseY - lerp(0.5, 0.95, on) * maxH} stroke="#eaf6ff" strokeWidth={2.5} opacity={0.85} />
        <text x={gx} y={baseY + 36} fill="#8aa" fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">position →</text>
        <text x={gx} y={baseY - 0.5 * maxH - 14} fill="#9fb4cc" fontSize="18" fontFamily="var(--f-body, Inter, sans-serif)" opacity={1 - on}>uniform field</text>
        <text x={gx} y={baseY + 12} fill={accent} fontSize="18" fontFamily="var(--f-body, Inter, sans-serif)" opacity={on}>low freq</text>
        <text x={gx + gw} y={baseY - 0.95 * maxH - 12} textAnchor="end" fill={accent2} fontSize="18" fontFamily="var(--f-body, Inter, sans-serif)" opacity={on}>high freq</text>
        {/* the three gradient coils */}
        <text x={W * 0.5} y={H * 0.8} textAnchor="middle" fill="#c9d6ea" fontSize="22" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t,0.05,0.3))}>coils  Gx · Gy · Gz    →    B = B₀ + G·x</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default GradientTilt;
