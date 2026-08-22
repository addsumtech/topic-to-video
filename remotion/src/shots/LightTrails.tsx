// SHOT · Light Trails — a long-exposure light-painting register: glowing neon ribbons sweep in and TRACE OUT a
// giant checkmark (plus ambient swooshes), each with a bright travelling head + a fading motion-blur tail, then
// the finished mark blooms. Premium, kinetic, photographic. Deterministic (draw progress + head = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s

// sample a quadratic/cubic-ish check path at u∈[0,1] → point (for the head dot)
function checkPoint(u: number, W: number, H: number): [number, number] {
  const A: [number, number] = [W / 2 - 300, H / 2 - 20], B: [number, number] = [W / 2 - 70, H / 2 + 200], C: [number, number] = [W / 2 + 360, H / 2 - 260];
  if (u < 0.4) {const k = u / 0.4; return [lerp(A[0], B[0], k), lerp(A[1], B[1], k)];}
  const k = (u - 0.4) / 0.6; return [lerp(B[0], C[0], k), lerp(B[1], C[1], k)];
}

export const LightTrails: React.FC<{label?: string}> = ({label = 'done in one motion'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const checkD = `M${W / 2 - 300},${H / 2 - 20} L${W / 2 - 70},${H / 2 + 200} L${W / 2 + 360},${H / 2 - 260}`;
  const LEN = 1500;
  const draw = easeInOutCubic(seg(t, 0.16, 0.72));
  const [hx, hy] = checkPoint(clamp01(draw), W, H);
  const bloom = easeOutCubic(seg(t, 0.72, 0.92));

  // ambient swoosh ribbons (parallax)
  const swoosh = (phase: number, amp: number) => {
    const p = (t * 0.6 + phase) % 1;
    const x = lerp(-300, W + 300, p);
    const y = H / 2 + Math.sin(p * Math.PI * 2 + phase * 6) * amp;
    return {x, y};
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0a1020 0%, #05070f 66%, #03040a 100%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="ltglow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="8" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <linearGradient id="ltc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#22e3ff" /><stop offset="0.5" stopColor="#6a8bff" /><stop offset="1" stopColor="#c86bff" /></linearGradient>
        </defs>

        {/* ambient swoosh ribbons */}
        {[[0, 220, '#1b6bff'], [0.4, 320, '#c23bff'], [0.75, 160, '#1fd4c2']].map(([ph, amp, col], i) => {
          const a = swoosh(ph as number, amp as number), b = swoosh((ph as number) + 0.08, amp as number);
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={col as string} strokeWidth={10} strokeLinecap="round" opacity={0.5} filter="url(#ltglow)" />;
        })}

        {/* the check being traced */}
        <path d={checkD} fill="none" stroke="url(#ltc)" strokeWidth={16} strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray={LEN} strokeDashoffset={LEN * (1 - draw)} filter="url(#ltglow)" />
        {/* full-bloom glow at the end */}
        {bloom > 0 && <path d={checkD} fill="none" stroke="#eaffff" strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" opacity={bloom} filter="url(#ltglow)" />}
        {/* travelling head */}
        {draw > 0.01 && draw < 0.99 && <circle cx={hx} cy={hy} r={16} fill="#ffffff" filter="url(#ltglow)" />}
      </svg>

      <div style={{position: 'absolute', left: 0, right: 0, bottom: H * 0.12, textAlign: 'center',
        opacity: clamp01(seg(t, 0.74, 0.94)), color: '#eaf4ff', font: '800 46px/1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em'}}>{label}</div>
    </AbsoluteFill>
  );
};
export default LightTrails;
