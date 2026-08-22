// SHOT · Exploded Schematic — blueprint/engineering language (Framer/hardware films): a system starts
// clustered, then EXPLODES apart along its axis into labelled parts with leader lines + a dimension readout,
// like a spec sheet building itself. Blueprint navy + cyan line-work (a cool, technical, distinct look).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const NAVY = '#081726', CYAN_D0 = '#43C4E8', LINE_D0 = '#1f5f7d';
export const ExplodedSchematic: React.FC<{items?: string[]}> = ({
  items: STAGES = ['Instruction', 'Planner', 'Experts ×100', 'Your tools', 'Deliverable']} = {}) => {
  const dna = useDNA();
  const CYAN = dna?.accent ?? CYAN_D0, LINE = dna?.line ?? LINE_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const ex = easeInOutCubic(seg(t, 0.14, 0.62)); // explode progress
  const cy = H / 2 - 40, bw = 260, bh = 200;
  const spread = 340; // final gap between part centres
  const n = STAGES.length, mid = (n - 1) / 2;
  return (
    <AbsoluteFill style={{background: `radial-gradient(130% 130% at 50% 40%, #0d2236, ${NAVY} 70%)`}}>
      {/* faint blueprint grid */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        {[...Array(40)].map((_, i) => <line key={`v${i}`} x1={i * 60} y1={0} x2={i * 60} y2={H} stroke="#0e2b42" strokeWidth={1} />)}
        {[...Array(22)].map((_, i) => <line key={`h${i}`} x1={0} y1={i * 60} x2={W} y2={i * 60} stroke="#0e2b42" strokeWidth={1} />)}
      </svg>
      {/* connectors (draw on as it assembles/explodes) */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {STAGES.slice(0, -1).map((_, i) => {
          const x1 = W / 2 + (i - mid) * spread * ex + bw / 2;
          const x2 = W / 2 + (i + 1 - mid) * spread * ex - bw / 2;
          const grow = clamp01((ex - 0.2) / 0.6);
          return <line key={i} x1={x1} y1={cy} x2={lerp(x1, x2, grow)} y2={cy} stroke={CYAN} strokeWidth={2.5} markerEnd="url(#a)" />;
        })}
        <defs><marker id="a" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke={CYAN} strokeWidth="1.4" /></marker></defs>
      </svg>
      {STAGES.map((s, i) => {
        const x = W / 2 + (i - mid) * spread * ex;
        const app = easeOutCubic(seg(t, 0.06 + i * 0.03, 0.3));
        const labelIn = easeOutCubic(seg(t, 0.4 + i * 0.05, 0.7));
        const hot = i === 2; // the "experts" part is the hot/active one
        return (
          <div key={i}>
            {/* wireframe part box */}
            <div style={{position: 'absolute', left: x - bw / 2, top: cy - bh / 2, width: bw, height: bh, opacity: clamp01(app),
              border: `2px solid ${hot ? CYAN : LINE}`, borderRadius: 6, background: hot ? `${CYAN}12` : 'rgba(67,196,232,0.04)',
              boxShadow: hot ? `0 0 40px ${CYAN}44` : 'none'}}>
              {/* corner ticks */}
              {[[0, 0], [1, 0], [0, 1], [1, 1]].map(([hx, hy], k) => <div key={k} style={{position: 'absolute',
                left: hx ? bw - 14 : 2, top: hy ? bh - 14 : 2, width: 12, height: 12,
                borderTop: hy ? 'none' : `2px solid ${CYAN}`, borderBottom: hy ? `2px solid ${CYAN}` : 'none',
                borderLeft: hx ? 'none' : `2px solid ${CYAN}`, borderRight: hx ? `2px solid ${CYAN}` : 'none'}} />)}
              <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                font: '800 34px/1.1 Inter,system-ui,sans-serif', color: hot ? '#eaffff' : '#9fc6d8', textAlign: 'center', padding: 16}}>{s}</div>
            </div>
            {/* leader line + numbered label below */}
            <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: labelIn}}>
              <line x1={x} y1={cy + bh / 2} x2={x} y2={cy + bh / 2 + 70} stroke={LINE} strokeWidth={1.5} strokeDasharray="5 5" />
            </svg>
            <div style={{position: 'absolute', left: x - 90, top: cy + bh / 2 + 82, width: 180, textAlign: 'center', opacity: labelIn}}>
              <div style={{font: '800 26px/1 Inter', color: CYAN}}>{String(i + 1).padStart(2, '0')}</div>
            </div>
          </div>
        );
      })}
      {/* corner spec HUD (top-right — keeps clear of the film's bottom caption zone) */}
      <div style={{position: 'absolute', right: 90, top: 90, font: '600 28px/1.6 "JetBrains Mono",monospace', color: CYAN, opacity: 0.8, textAlign: 'right'}}>
        SYSTEM · {STAGES.length} STAGES<br />ONE PROMPT → DELIVERED
      </div>
    </AbsoluteFill>
  );
};
export default ExplodedSchematic;
