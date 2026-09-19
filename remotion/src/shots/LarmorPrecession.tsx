// LarmorPrecession — precession, not electron orbits. The magnetic moment μ sits tilted from B0 and PRECESSES
// around it like a spinning top, tracing a cone; the precession rate is the Larmor frequency f0 = γ·B0. A shot of
// electrons orbiting a nucleus showed atomic structure, not this. Deterministic (pure fn of useT).
//
// THE CONSTANT IS THE FILM'S. The formula line ended in a literal `≈ 42.58 MHz/T` — the gyromagnetic ratio of
// ¹H, and ONLY of ¹H — printed on every film that reached for a register LIBRARY.md offers for "a steady
// rotation set by a field / the fundamental frequency of a system". A sodium or phosphorus film was told the
// hydrogen number, and no prop could reach it. The relation `f₀ = γ·B₀` names the mechanism and stays; the
// value is `gamma` now, defaulting to the text it replaced (so the original film is unchanged and the
// demo-copy gate lists it when a film omits it), printed exactly as the film writes it through
// runtime/figure. '' prints the bare relation.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY, fitTextPx} from '../runtime/layout';
import {figureText} from '../runtime/figure';

export const DURATION = 165; // 5.5s

export const LarmorPrecession: React.FC<{accent?: string; accent2?: string; label?: string; gamma?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Larmor precession', gamma = '42.58 MHz/T', } = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const cx = W * 0.5, oy = H * 0.62, L = Math.min(W, H) * 0.32, tilt = 0.5;   // fixed tilt from B0
  const ell = 0.34;                                                            // perspective squash of the cone base
  const az = t * Math.PI * 8;                                                  // precession about B0 (Larmor rate)
  const mx = cx + L * Math.sin(tilt) * Math.cos(az);
  const my = oy - L * Math.cos(tilt) + L * Math.sin(tilt) * Math.sin(az) * ell;

  // the cone the tip sweeps (precession path) + a fading trail
  const trail: string[] = [];
  for (let a = az - Math.PI * 1.6; a <= az; a += 0.12)
    trail.push(`${(cx + L * Math.sin(tilt) * Math.cos(a)).toFixed(1)},${(oy - L * Math.cos(tilt) + L * Math.sin(tilt) * Math.sin(a) * ell).toFixed(1)}`);
  const A = (o: number) => `${accent}${Math.round(clamp01(o) * 255).toString(16).padStart(2, '0')}`;
  const g = figureText(gamma);
  const eq = g ? `f₀ = γ·B₀ ≈ ${g}` : 'f₀ = γ·B₀';
  // fitted to the frame at the original 24px (mono cells); the demo line is far inside that
  const eqPx = Math.min(24, fitTextPx(eq, W * 0.92, 24, {usable: 1, adv: 0.62, cjk: 1.24}));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 50%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* B0 axis */}
        <line x1={cx} y1={oy - L * 1.2} x2={cx} y2={oy + L * 0.3} stroke={A(0.55)} strokeWidth={1.8} strokeDasharray="3 6" />
        <text x={cx + 12} y={oy - L * 1.1} fill="#9fb4cc" fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700}>B₀</text>
        {/* the precession cone base + the tip's circular path */}
        <ellipse cx={cx} cy={oy - L * Math.cos(tilt)} rx={L * Math.sin(tilt)} ry={L * Math.sin(tilt) * ell} fill="none" stroke={accent2} strokeWidth={1.3} opacity={0.4} />
        <line x1={cx} y1={oy} x2={cx + L * Math.sin(tilt)} y2={oy - L * Math.cos(tilt)} stroke={A(0.2)} strokeWidth={1} />
        <line x1={cx} y1={oy} x2={cx - L * Math.sin(tilt)} y2={oy - L * Math.cos(tilt)} stroke={A(0.2)} strokeWidth={1} />
        {/* fading precession trail */}
        <polyline points={trail.join(' ')} fill="none" stroke={accent} strokeWidth={2.4} opacity={0.55} />
        {/* the moment vector μ, precessing */}
        <line x1={cx} y1={oy} x2={mx} y2={my} stroke="#eaf6ff" strokeWidth={4} markerEnd="url(#lp)" />
        <defs><marker id="lp" markerWidth="12" markerHeight="12" refX="4" refY="6" orient="auto"><path d="M0,0 L8,6 L0,12 Z" fill="#eaf6ff" /></marker></defs>
        <circle cx={mx} cy={my} r={7} fill="#eaf6ff" />
        <text x={mx + 14} y={my - 8} fill="#eaf6ff" fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800}>μ</text>
        <text x={cx} y={Math.min(oy + L * 0.5 + 40, bottomTextY(W, H))} textAnchor="middle" fill={accent} fontSize={eqPx} fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">{eq}</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default LarmorPrecession;
