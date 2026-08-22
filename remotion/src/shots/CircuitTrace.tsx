// SHOT · Circuit Trace — a PCB comes alive: copper traces route (Manhattan bends) between chips and pads and
// DRAW ON, signal pulses race along them, and a central chip lights up. A hardware / systems register
// (family T · circuit/hardware). Deterministic (trace draw + pulse position = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BOARD = '#08130f', COPPER = '#2fd6a0', LIVE = '#7dffcf';

export const CircuitTrace: React.FC<{title?: string; chip?: string; nodes?: string[]}> = ({
  title: TITLE = 'Wired together', chip: CHIP = 'CORE', nodes: NODES = ['IN', 'MEM', 'I/O', 'NET', 'PWR']} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 + 10;
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const chipIn = easeOutBack(clamp01(seg(t, 0.1, 0.32)));
  // satellite pads around the core, each with an L-shaped trace to the core
  const pads = NODES.slice(0, 6).map((label, i) => {
    const ang = (i / Math.max(1, NODES.length)) * Math.PI * 2 - Math.PI / 2;
    const px = cx + Math.cos(ang) * 560, py = cy + Math.sin(ang) * 320;
    return {label, px, py, i, ang};
  });
  const lpath = (x1: number, y1: number, x2: number, y2: number) => `M${x1} ${y1} L${x1} ${y2} L${x2} ${y2}`;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? (`radial-gradient(130% 100% at 50% 42%, #0d2018, ${BOARD} 74%)`), overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 70, left: 0, right: 0, textAlign: 'center', opacity: titleIn, zIndex: 5,
        color: '#8fd8bf', font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>
      {/* faint pad grid */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g opacity={0.16}>{[...Array(28)].map((_, i) => [...Array(16)].map((__, j) =>
          <circle key={`${i}-${j}`} cx={60 + i * 66} cy={40 + j * 66} r={2} fill={COPPER} />))}</g>
        {/* traces */}
        {pads.map((p, i) => {
          const draw = easeOutCubic(clamp01(seg(t, 0.18 + i * 0.07, 0.5 + i * 0.07)));
          const len = Math.abs(p.px - cx) + Math.abs(p.py - cy);
          return <path key={i} d={lpath(p.px, p.py, cx, cy)} fill="none" stroke={COPPER} strokeWidth={5}
            strokeLinejoin="round" opacity={0.5} strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />;
        })}
      </svg>
      {/* signal pulses (rendered as absolutely-positioned dots for clean movement) */}
      {pads.map((p, i) => {
        const draw = clamp01(seg(t, 0.18 + i * 0.07, 0.5 + i * 0.07));
        const pulse = clamp01(seg(t, 0.52 + i * 0.05, 0.92));
        if (draw < 0.98) return null;
        // travel along the L path: first vertical (px,py)->(px,cy) then horizontal ->(cx,cy)
        const seg1 = clamp01(pulse * 2), seg2 = clamp01(pulse * 2 - 1);
        const x = p.px + (cx - p.px) * seg2;
        const y = p.py + (cy - p.py) * seg1;
        return <div key={i} style={{position: 'absolute', left: x, top: y, width: 14, height: 14, borderRadius: '50%',
          transform: 'translate(-50%,-50%)', background: LIVE, boxShadow: `0 0 16px ${LIVE}`, opacity: pulse < 1 ? 1 : 0}} />;
      })}
      {/* satellite pads */}
      {pads.map((p, i) => {
        const on = easeOutBack(clamp01(seg(t, 0.12 + i * 0.06, 0.34 + i * 0.06)));
        return <div key={i} style={{position: 'absolute', left: p.px, top: p.py, transform: `translate(-50%,-50%) scale(${on})`,
          opacity: clamp01(on), width: 116, height: 74, borderRadius: 10, background: '#0c241a',
          border: `2px solid ${COPPER}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: LIVE, font: '800 26px/1 "JetBrains Mono", monospace', boxShadow: `0 0 24px ${COPPER}44`}}>{p.label}</div>;
      })}
      {/* central chip */}
      <div style={{position: 'absolute', left: cx, top: cy, transform: `translate(-50%,-50%) scale(${chipIn})`,
        width: 260, height: 200, borderRadius: 14, background: 'linear-gradient(160deg, #103326, #0a1f17)',
        border: `3px solid ${LIVE}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#eafff6', font: '900 56px/1 Inter, system-ui, sans-serif',
        boxShadow: t > 0.5 ? `0 0 60px ${LIVE}66, inset 0 0 30px ${COPPER}44` : `0 0 20px ${COPPER}44`}}>
        {/* chip pins */}
        {[...Array(8)].map((_, k) => <div key={k} style={{position: 'absolute', top: -12, left: 24 + k * 28, width: 12, height: 12, background: COPPER}} />)}
        {CHIP}
      </div>
    </AbsoluteFill>
  );
};
export default CircuitTrace;
