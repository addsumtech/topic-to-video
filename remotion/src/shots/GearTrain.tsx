// SHOT · Gear Train — interlocking gears mesh and turn in a CHAIN: the drive gear spins, each neighbour
// engages a beat later and turns the opposite way, hubs carry the step labels (kept upright), and the last
// gear LOCKS and lights the payoff. The "mechanism / one turn drives the next" register (family I). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0b0c11';
const TONES0 = ['#5b8cff', '#f6a531', '#ff5b7f', '#22c197'];
const R = 156, TEETH = 12, SPACING = 278;

const Gear: React.FC<{cx: number; cy: number; angle: number; tone: string; live: boolean}> = ({cx, cy, angle, tone, live}) => (
  <g transform={`rotate(${angle} ${cx} ${cy})`}>
    {[...Array(TEETH)].map((_, j) => {
      const a = (j / TEETH) * Math.PI * 2;
      const tx = cx + Math.cos(a) * R, ty = cy + Math.sin(a) * R;
      return <rect key={j} x={tx - 20} y={ty - 20} width={40} height={40} rx={7}
        fill={live ? tone : '#2a2f45'} transform={`rotate(${(a * 180) / Math.PI} ${tx} ${ty})`} />;
    })}
    <circle cx={cx} cy={cy} r={R - 6} fill="#12141f" stroke={live ? tone : '#2a2f45'} strokeWidth={4} />
    <circle cx={cx} cy={cy} r={R - 58} fill="none" stroke="#ffffff10" strokeWidth={10} />
    {[...Array(6)].map((_, s) => {
      const a = (s / 6) * Math.PI * 2;
      return <line key={s} x1={cx + Math.cos(a) * 40} y1={cy + Math.sin(a) * 40}
        x2={cx + Math.cos(a) * (R - 60)} y2={cy + Math.sin(a) * (R - 60)}
        stroke="#ffffff12" strokeWidth={12} strokeLinecap="round" />;
    })}
  </g>
);

export const GearTrain: React.FC<{items?: string[]; label?: string; title?: string}> = ({
  items: ITEMS = ['Trigger', 'Process', 'Deliver'], label: LABEL = 'Automatic', title: TITLE = 'How it runs'} = {}) => {
  const dna = useDNA();
  const TONES = dnaPalette(dna, 4) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const gears = ITEMS.slice(0, 4);
  const n = gears.length;
  const totalW = (n - 1) * SPACING;
  const x0 = W / 2 - totalW / 2;
  const cy = H / 2 + 20;
  const revs = 2.2;
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const locked = t > 0.82;
  const payoff = easeOutBack(clamp01(seg(t, 0.82, 0.98)));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, #14172a, ${BG} 70%)`}}>
      <div style={{position: 'absolute', top: 88, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#aeb6ca', font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {gears.map((_, i) => {
          const cx = x0 + i * SPACING;
          const dir = i % 2 === 0 ? 1 : -1;
          const engaged = easeInOutCubic(clamp01(seg(t, 0.12 + i * 0.12, 0.86)));
          const base = (i % 2) * (180 / TEETH); // half-tooth offset so neighbours interleave
          const angle = base + dir * revs * 360 * engaged;
          const live = t > 0.12 + i * 0.12 - 0.02;
          return <Gear key={i} cx={cx} cy={cy} angle={angle} tone={TONES[i % TONES.length]} live={live} />;
        })}
      </svg>

      {/* upright hub labels (outside the rotating groups) + step index */}
      {gears.map((g, i) => {
        const cx = x0 + i * SPACING;
        const on = clamp01(seg(t, 0.16 + i * 0.12, 0.36 + i * 0.12));
        const isLast = i === n - 1;
        return (
          <div key={i} style={{position: 'absolute', left: cx, top: cy, transform: 'translate(-50%,-50%)',
            textAlign: 'center', opacity: on, width: R * 1.7}}>
            <div style={{color: '#7f879c', font: '600 20px/1 var(--f-mono, "JetBrains Mono", monospace)',
              letterSpacing: '0.14em', marginBottom: 8}}>{String(i + 1).padStart(2, '0')}</div>
            <div style={{color: isLast && locked ? '#fff' : '#e7ebf7',
              font: '800 40px/1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em'}}>{g}</div>
          </div>
        );
      })}

      {/* payoff badge off the last gear */}
      <div style={{position: 'absolute', left: x0 + (n - 1) * SPACING, top: cy - R - 96,
        transform: `translate(-50%,0) scale(${payoff})`, opacity: clamp01(payoff * 1.4),
        padding: '16px 34px', borderRadius: 999, background: 'linear-gradient(150deg, #22c197, #12916e)',
        color: '#04120d', font: '800 40px/1 var(--f-body, Inter, system-ui, sans-serif)',
        boxShadow: '0 18px 50px #22c19755'}}>{LABEL}</div>
    </AbsoluteFill>
  );
};
export default GearTrain;
