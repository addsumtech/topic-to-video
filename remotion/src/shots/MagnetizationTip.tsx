// MagnetizationTip — what an RF pulse ACTUALLY does, made meaningful (not "energy radiating outward"). It shows
// the real mechanism: the net magnetization M starts along B0 (vertical); a resonant RF field B1 — a single-
// frequency wave at the Larmor frequency — drives it; and M NUTATES 90° down into the transverse plane, spiralling
// as it precesses. The tipping vector + the resonant wave ARE the RF pulse; a radial burst was decoration. The
// transverse magnetization it leaves is what induces the signal (next beat). Deterministic (pure fn of useT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 180; // 6s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'RF pulse · B₁',
  'at the Larmor frequency',
  'transverse plane',
];

export const MagnetizationTip: React.FC<{accent?: string; accent2?: string; label?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Resonance tips the magnetization',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const ox = W * 0.40, oy = H * 0.56;                       // origin of the vector frame (left-of-centre)
  const L = Math.min(W, H) * 0.34;                          // vector length
  const ell = 0.34;                                         // vertical squash of the transverse plane (perspective)

  // tip 0 → 90° (nutation), while precessing (azimuth) — driven only once the resonant RF "arrives"
  const drive = seg(t, 0.18, 0.9);
  const tip = easeInOutCubic(drive) * (Math.PI / 2);
  const az = drive * Math.PI * 4 + t * 0.6;                 // precession about B0
  // M endpoint (project 3D → 2D with a squashed transverse plane)
  const mx = ox + L * Math.sin(tip) * Math.cos(az);
  const my = oy - L * Math.cos(tip) + L * Math.sin(tip) * Math.sin(az) * ell;

  // spiral trace of the tip so far
  const trace: string[] = [];
  for (let s = 0; s <= drive; s += 0.02) {
    const tp = easeInOutCubic(s) * (Math.PI / 2), a = s * Math.PI * 4 + t * 0.6;
    trace.push(`${(ox + L * Math.sin(tp) * Math.cos(a)).toFixed(1)},${(oy - L * Math.cos(tp) + L * Math.sin(tp) * Math.sin(a) * ell).toFixed(1)}`);
  }

  // the resonant RF wave (right side): a single-frequency sine at the Larmor rate, its envelope = the pulse
  const rfx = W * 0.72, rfw = W * 0.22, rfy = H * 0.5;
  const env = Math.sin(Math.PI * clamp01(drive));           // pulse envelope (on during the tip)
  const wave: string[] = [];
  for (let x = 0; x <= rfw; x += 3) {
    const y = rfy + Math.sin(x / 7 - t * 14) * 44 * env;
    wave.push(`${(rfx + x).toFixed(1)},${y.toFixed(1)}`);
  }

  const A = (o: number) => `${accent}${Math.round(clamp01(o) * 255).toString(16).padStart(2, '0')}`;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 42% 50%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* B0 axis (vertical) + the transverse plane it tips into */}
        <line x1={ox} y1={oy - L * 1.15} x2={ox} y2={oy + L * 0.35} stroke={A(0.5)} strokeWidth={1.6} strokeDasharray="3 6" />
        <text x={ox + 12} y={oy - L * 1.05} fill="#9fb4cc" fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700}>B₀</text>
        <ellipse cx={ox} cy={oy} rx={L * 0.92} ry={L * 0.92 * ell} fill="none" stroke={accent2} strokeWidth={1.3} opacity={0.4} />
        <text x={ox + L * 0.9} y={oy + L * ell + 26} fill="#8aa" fontSize="20" fontFamily="var(--f-body, Inter, sans-serif)">transverse plane</text>

        {/* the spiral trace of M as it nutates */}
        {trace.length > 1 && <polyline points={trace.join(' ')} fill="none" stroke={accent} strokeWidth={2} opacity={0.5} />}

        {/* the magnetization vector M */}
        <line x1={ox} y1={oy} x2={mx} y2={my} stroke="#eaf6ff" strokeWidth={4} />
        <circle cx={mx} cy={my} r={9} fill="#eaf6ff" />
        <circle cx={mx} cy={my} r={20} fill="none" stroke={accent} strokeWidth={2} opacity={0.6} />
        <text x={mx + 16} y={my - 10} fill="#eaf6ff" fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800}>M</text>

        {/* the resonant RF field B1 — a single-frequency wave (the actual pulse) */}
        <polyline points={wave.join(' ')} fill="none" stroke={accent2} strokeWidth={2.5} opacity={0.9} />
        <text x={rfx} y={rfy - 78} fill="#c9d6ea" fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700}>RF pulse · B₁</text>
        <text x={rfx} y={rfy + 92} fill={accent} fontSize="19" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" letterSpacing="1">at the Larmor frequency</text>
      </svg>

      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default MagnetizationTip;
