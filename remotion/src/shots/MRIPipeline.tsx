// MRIPipeline — the recap as the ACTUAL pipeline, not four generic cards. Four stages flow left→right, each a
// tiny true representation — a decaying signal, gradient encoding, a k-space lattice — culminating in the REAL
// reconstructed MRI. It literally re-shows "signal → encoding → k-space → image: always computed." Deterministic.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01, seg} from '../runtime/motion';

export const DURATION = 180; // 6s

export const MRIPipeline: React.FC<{src?: string; accent?: string; accent2?: string; label?: string} > = ({
  src, accent = '#22d3ee', accent2 = '#a78bfa', label = 'Always computed',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const names = ['signal', 'encoding', 'k-space', 'image'];
  const n = names.length, box = Math.min(W * 0.17, H * 0.34), gap = (W - n * box) / (n + 1);
  const cy = H * 0.5 - 8;
  const on = (i: number) => clamp01(seg(t, 0.1 + i * 0.14, 0.35 + i * 0.14));

  const stageArt = (i: number, x: number, p: number) => {
    const s = box, cx = x + s / 2, mid = cy;
    if (i === 0) { // decaying signal
      const pts: string[] = [];
      for (let k = 0; k <= s - 20; k += 3) pts.push(`${x + 10 + k},${mid + Math.sin(k / 5) * (s * 0.3) * Math.exp(-k / (s * 0.9)) * p}`);
      return <polyline points={pts.join(' ')} fill="none" stroke="#eaf6ff" strokeWidth={2.4} />;
    }
    if (i === 1) { // gradient ramp grid
      const g: React.ReactNode[] = [];
      for (let c = 0; c < 6; c++) g.push(<line key={c} x1={x + 12 + c * (s - 24) / 5} y1={mid - s * 0.32} x2={x + 12 + c * (s - 24) / 5} y2={mid + s * 0.32} stroke={accent} strokeWidth={1.3} opacity={(0.3 + c * 0.13) * p} />);
      return <g>{g}</g>;
    }
    if (i === 2) { // k-space dots
      const d: React.ReactNode[] = [];
      for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) {
        const dx = (c - 2.5) / 2.5, dy = (r - 2.5) / 2.5, dd = Math.hypot(dx, dy);
        d.push(<circle key={`${r}-${c}`} cx={cx + dx * s * 0.34} cy={mid + dy * s * 0.34} r={1 + (1 - dd) * 2.4} fill={(r + c) % 4 === 0 ? accent2 : accent} opacity={(0.15 + (1 - dd) * 0.7) * p} />);
      }
      return <g>{d}</g>;
    }
    return null; // image handled as <Img> below
  };

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)'}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {names.map((nm, i) => {
          const x = gap + i * (box + gap), p = on(i);
          return <g key={nm}>
            <rect x={x} y={cy - box / 2} width={box} height={box} rx={10} fill="#0a1424" stroke={i === n - 1 ? accent : `${accent}66`} strokeWidth={1.6} opacity={0.35 + p * 0.65} />
            {i < n - 1 ? stageArt(i, x, p) : null}
            <text x={x + box / 2} y={cy + box / 2 + 34} textAnchor="middle" fill="#c9d6ea" fontSize="24" fontFamily="Inter, sans-serif" fontWeight={700} opacity={p}>{nm}</text>
            {i < n - 1 ? <text x={x + box + gap / 2} y={cy + 8} textAnchor="middle" fill={accent} fontSize="34" opacity={on(i + 1)}>→</text> : null}
          </g>;
        })}
      </svg>
      {/* the final stage = the REAL reconstructed MRI */}
      {src ? <div style={{position: 'absolute', left: gap + (n - 1) * (box + gap) + 5, top: cy - box / 2 + 5,
        width: box - 10, height: box - 10, borderRadius: 8, overflow: 'hidden', opacity: on(n - 1)}}>
        <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /></div> : null}
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default MRIPipeline;
