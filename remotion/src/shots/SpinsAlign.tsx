// SpinsAlign — spins ALIGNING, not a generic flow field. A cloud of proton spins starts pointing every which way
// (no net magnetism); slide into B0 and a small minority tips to point along the field, so a net
// magnetization M0 emerges from that excess. Random → aligned minority → net vector. Deterministic.
//
// THE LINE AND THE PICTURE NOW SAY THE SAME THING, AND THE LINE IS THE FILM'S. The caption under the cloud
// was the literal `~3 in a million tip the balance → net signal` — a physics figure no prop could reach,
// declared as INTRINSIC_TEXT as if it were an axis label, printed on every film that used a register
// LIBRARY.md offers for "disorder resolving into order / many parts agreeing". And the cloud contradicted
// it: `hash01(i * 11) < 0.5` turned about HALF the arrows accent-coloured and pointing up, directly above a
// sentence saying three in a million do. The sentence is `note` now, defaulting to the words it replaced, so
// the demo-copy gate lists it when a film omits it and a film can state its own (or pass '' for none).
// The drawn share is `alignedFraction`, and its default is 0.1 — a VISIBLE small minority (6 of the 60
// arrows). Three in a million cannot be drawn with sixty arrows; what can be drawn honestly is the claim's
// direction, a few against a crowd, instead of its opposite. A film whose point is many parts agreeing
// passes its own share. Which arrows align is a hash of their index — the arrows are anonymous, so that
// choice carries no meaning; how many align is the film's.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY, fitTextPx, MONO_ADVANCE} from '../runtime/layout';

export const DURATION = 170; // ~5.7s
const N = 60;

export const SpinsAlign: React.FC<{accent?: string; accent2?: string; label?: string; note?: string;
  alignedFraction?: number}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Spins align in the field',
  note = '~3 in a million tip the balance → net signal', alignedFraction = 0.1, } = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const frac = Number(alignedFraction);
  if (!Number.isFinite(frac) || frac <= 0 || frac > 1) {
    throw new Error(`SpinsAlign: \`alignedFraction\` is the share of the ${N} drawn spins that end up along B₀, ` +
      `so it must be a number in (0, 1] — got ${JSON.stringify(alignedFraction)}. A tiny physical excess is ` +
      'drawn as a small visible minority (the default 0.1), not as zero.');
  }
  // the k spins that align: the k lowest hashes, so the count is exact rather than a coin flip per arrow
  const k = Math.max(1, Math.round(N * frac));
  const aligned = new Set([...Array(N).keys()].sort((a, b) => hash01(a * 11) - hash01(b * 11)).slice(0, k));
  const align = clamp01(seg(t, 0.15, 0.75));                 // 0 random → 1 field on
  const arrows: React.ReactNode[] = [];
  for (let i = 0; i < N; i++) {
    const x = W * 0.14 + hash01(i * 2 + 1) * W * 0.56, y = H * 0.24 + hash01(i * 2 + 7) * H * 0.52;
    const rnd = hash01(i * 5) * Math.PI * 2;
    const flips = aligned.has(i);
    const ang = lerp(rnd, flips ? -Math.PI / 2 : rnd, align);   // aligned ones point up (−90°)
    const len = 22;
    arrows.push(<line key={i} x1={x} y1={y} x2={x + Math.cos(ang) * len} y2={y + Math.sin(ang) * len}
      stroke={flips ? accent : '#6b7688'} strokeWidth={flips ? 2.4 : 1.6} opacity={flips ? 0.95 : 0.6}
      markerEnd={flips ? 'url(#sa)' : undefined} />);
  }
  const mBase = H * 0.78, mY = lerp(0, H * 0.15, align);
  // the film's sentence is fitted to the frame at the original 20px, which the demo line is well inside
  const notePx = Math.min(20, fitTextPx(note, W * 0.92, 20, {usable: 1, adv: MONO_ADVANCE + 0.02, cjk: 2 * (MONO_ADVANCE + 0.02)}));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <defs><marker id="sa" markerWidth="9" markerHeight="9" refX="3" refY="4.5" orient="auto"><path d="M0,0 L6,4.5 L0,9 Z" fill={accent} /></marker></defs>
        {/* B0 field direction (up) appears as it turns on */}
        <line x1={W * 0.8} y1={H * 0.75} x2={W * 0.8} y2={H * 0.25} stroke={`${accent2}${Math.round(align * 160).toString(16).padStart(2, '0')}`} strokeWidth={2} strokeDasharray="4 6" />
        <text x={W * 0.8 + 12} y={H * 0.27} fill="#9fb4cc" fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700} opacity={align}>B₀</text>
        {arrows}
        {/* the net magnetization that emerges from the excess */}
        <line x1={W * 0.5} y1={mBase} x2={W * 0.5} y2={mBase - mY} stroke="#eaf6ff" strokeWidth={5} markerEnd="url(#sa2)" opacity={align} />
        <defs><marker id="sa2" markerWidth="12" markerHeight="12" refX="4" refY="6" orient="auto"><path d="M0,0 L8,6 L0,12 Z" fill="#eaf6ff" /></marker></defs>
        <text x={W * 0.5 + 16} y={mBase - mY} fill="#eaf6ff" fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} opacity={align}>M₀</text>
        {note ? <text x={W * 0.5} y={Math.min(H * 0.84, bottomTextY(W, H))} textAnchor="middle" fill={accent} fontSize={notePx} fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={align}>{note}</text> : null}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default SpinsAlign;
