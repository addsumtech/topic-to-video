// SHOT · Conveyor Belt — raw items ride a scrolling belt left→right, pass under a STAMP press that slams down
// (flash + the item flips to a finished ✓ state), and exit as "done". The "assembly line / it just processes
// everything" register (family I — mechanical). Deterministic (belt scroll + item x = fn of t). No fabricated
// numbers.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';

const BG = '#0b0c11', DONE = '#37d4a6';
export const DURATION = 155; // ~5.2s

export const ConveyorBelt: React.FC<{items?: string[]; title?: string; doneLabel?: string}> = ({
  items: ITEMS = ['ticket', 'email', 'doc', 'lead', 'bug'], title: TITLE = 'Everything, handled',
  doneLabel: DONELABEL = '✓ done'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const beltY = H / 2 + 60, beltH = 176, cx = W / 2;
  const treadOff = (t * 1400) % 64;
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const n = ITEMS.length;
  // items flow continuously; each card's centre x sweeps across the full width
  const cards = ITEMS.map((label, k) => {
    const phase = (t * 0.85 + k / n) % 1;         // 0..1 position along the run
    const x = lerp(-220, W + 220, phase);
    const stamped = x > cx;
    return {label, x, stamped, dist: Math.abs(x - cx)};
  });
  const minDist = Math.min(...cards.map((c) => c.dist));
  const prox = clamp01(1 - minDist / 80);         // press engagement near the stamp
  const pressDrop = easeOutCubic(prox) * 92;
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 34%, #14172a, ${BG} 72%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 92, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#aeb6ca', font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div>

      {/* belt */}
      <div style={{position: 'absolute', left: -20, top: beltY, width: W + 40, height: beltH, borderRadius: 14,
        background: 'linear-gradient(#1b1f2e, #10131d)', border: '1px solid #262c40', overflow: 'hidden'}}>
        <svg width={W + 40} height={beltH}>
          {[...Array(Math.ceil((W + 40) / 64) + 1)].map((_, i) => (
            <line key={i} x1={i * 64 - treadOff} y1={0} x2={i * 64 - treadOff} y2={beltH} stroke="#2a3048" strokeWidth={6} />
          ))}
        </svg>
      </div>
      {/* belt rollers */}
      {[40, W - 40].map((rx, i) => (
        <div key={i} style={{position: 'absolute', left: rx - 34, top: beltY + beltH / 2 - 34, width: 68, height: 68,
          borderRadius: '50%', background: 'radial-gradient(circle at 40% 35%, #3a4358, #1a1f2e)', border: '1px solid #2a3048'}} />
      ))}

      {/* stamp press */}
      <div style={{position: 'absolute', left: cx - 90, top: beltY - 210 + pressDrop, width: 180, height: 150,
        borderRadius: 14, background: `linear-gradient(#3a4358, #232838)`, border: '1px solid #454d68',
        boxShadow: prox > 0.5 ? `0 0 40px ${DONE}55` : '0 10px 30px #0007',
        display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: 12}}>
        <div style={{width: 120, height: 20, borderRadius: 6, background: prox > 0.5 ? DONE : '#5a6478'}} />
      </div>
      <div style={{position: 'absolute', left: cx - 4, top: beltY - 260, width: 8, height: 60, background: '#454d68'}} />

      {/* cards riding the belt */}
      {cards.map((c, k) => (
        <div key={k} style={{position: 'absolute', left: c.x, top: beltY + beltH / 2, transform: 'translate(-50%,-50%)',
          width: 168, height: 116, borderRadius: 16, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 8,
          background: c.stamped ? `linear-gradient(150deg, ${DONE}, #17977a)` : 'linear-gradient(150deg, #232838, #171b28)',
          border: `1px solid ${c.stamped ? 'transparent' : '#333a52'}`,
          boxShadow: c.stamped ? `0 16px 40px ${DONE}44` : '0 12px 30px #0006'}}>
          <div style={{color: c.stamped ? '#04120d' : '#c7cee0', font: '800 30px/1 Inter, system-ui, sans-serif'}}>{c.label}</div>
          <div style={{color: c.stamped ? '#04241a' : '#6b7488', font: '700 18px/1 "JetBrains Mono", monospace'}}>
            {c.stamped ? DONELABEL : 'queued'}</div>
        </div>
      ))}
      {/* flash at stamp on contact */}
      {prox > 0.2 ? <div style={{position: 'absolute', left: cx - 130, top: beltY - 30, width: 260, height: beltH + 60,
        background: `radial-gradient(closest-side, ${DONE}55, #0000)`, opacity: prox * 0.9, pointerEvents: 'none'}} /> : null}
    </AbsoluteFill>
  );
};
export default ConveyorBelt;
