// SHOT · Conveyor Belt — raw items ride a scrolling belt left→right, pass under a STAMP press that slams down
// (flash + the item flips to a finished ✓ state), and exit as "done". The "assembly line / it just processes
// everything" register (family I — mechanical). Deterministic (belt scroll + item x = fn of t). No fabricated
// numbers.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaHas, ScanGrid} from '../runtime/dna';

const BG = '#0b0c11', DONE = '#37d4a6';
export const DURATION = 155; // ~5.2s

export const ConveyorBelt: React.FC<{items?: string[]; title?: string; doneLabel?: string}> = ({
  items: ITEMS = ['ticket', 'email', 'doc', 'lead', 'bug'], title: TITLE = 'Everything, handled',
  doneLabel: DONELABEL = '✓ done'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // DESIGN DNA — inherit the film's visual system (or the shot's original look when no DNA is provided).
  const dna = useDNA();
  const done = dna?.accent ?? DONE;
  const bgStyle = dna?.bgGrad ?? `radial-gradient(120% 100% at 50% 34%, #14172a, ${BG} 72%)`;
  const cardBg = dna?.surface ?? 'linear-gradient(150deg, #232838, #171b28)';
  const cardBorder = dna?.surfaceBorder ?? '#333a52';
  const cardRadius = dna?.radius ?? 16;
  const labelFont = dna?.fontMono ?? 'Inter, system-ui, sans-serif';
  const fg = dna?.fg ?? '#c7cee0', onAcc = dna?.onAccent ?? '#04120d', dim = dna?.dim ?? '#6b7488';
  const titleFont = dna?.fontMono ?? '"JetBrains Mono", monospace', titleCol = dna?.dim ?? '#aeb6ca';
  const beltBorder = dna?.surfaceBorder ?? '#262c40', treadCol = dna?.line ?? '#2a3048';
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
    <AbsoluteFill style={{background: bgStyle, overflow: 'hidden'}}>
      <ScanGrid dna={dna} w={W} h={H} />
      <div style={{position: 'absolute', top: 92, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: titleCol, font: `700 30px/1 ${titleFont}`, letterSpacing: dna ? '0.14em' : '0.3em',
        textTransform: dna ? 'none' : 'uppercase'}}>
        {dnaHas(dna, 'prompt') ? <span style={{color: done}}>▸ </span> : null}{TITLE}</div>

      {/* belt */}
      <div style={{position: 'absolute', left: -20, top: beltY, width: W + 40, height: beltH, borderRadius: 14,
        background: 'linear-gradient(#1b1f2e, #10131d)', border: `1px solid ${beltBorder}`, overflow: 'hidden'}}>
        <svg width={W + 40} height={beltH}>
          {[...Array(Math.ceil((W + 40) / 64) + 1)].map((_, i) => (
            <line key={i} x1={i * 64 - treadOff} y1={0} x2={i * 64 - treadOff} y2={beltH} stroke={treadCol} strokeWidth={6} />
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
        boxShadow: prox > 0.5 ? `0 0 40px ${done}55` : '0 10px 30px #0007',
        display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: 12}}>
        <div style={{width: 120, height: 20, borderRadius: 6, background: prox > 0.5 ? done : '#5a6478'}} />
      </div>
      <div style={{position: 'absolute', left: cx - 4, top: beltY - 260, width: 8, height: 60, background: '#454d68'}} />

      {/* cards riding the belt — SIZE-AWARE: real (non-demo) copy is longer than 'ticket'/'email', so the label
          font shrinks by length and wraps, and the card grows in height (minHeight, not a fixed 116) so a long
          label or a full-sentence doneLabel never bleeds past the box (frame-craft §A.8). Short demo labels keep
          the original 30px look. */}
      {cards.map((c, k) => {
        const sub = c.stamped ? DONELABEL : 'queued';
        const lLen = [...(c.label ?? '')].length, sLen = [...sub].length;
        const lfs = lLen <= 6 ? 30 : lLen <= 10 ? 23 : lLen <= 16 ? 18 : 15;
        const sfs = sLen <= 8 ? 18 : sLen <= 16 ? 15 : 13;
        return (
          <div key={k} style={{position: 'absolute', left: c.x, top: beltY + beltH / 2, transform: 'translate(-50%,-50%)',
            width: 208, minHeight: 116, padding: '12px 14px', boxSizing: 'border-box', borderRadius: cardRadius,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 7,
            background: c.stamped ? `linear-gradient(150deg, ${done}, ${done}cc)` : cardBg,
            border: `1px solid ${c.stamped ? 'transparent' : cardBorder}`,
            boxShadow: c.stamped ? `0 16px 40px ${done}44` : '0 12px 30px #0006'}}>
            <div style={{color: c.stamped ? onAcc : fg, textAlign: 'center', maxWidth: 180,
              wordBreak: 'break-word', font: `800 ${lfs}px/1.12 ${labelFont}`}}>{c.label}</div>
            <div style={{color: c.stamped ? onAcc : dim, textAlign: 'center', maxWidth: 180,
              wordBreak: 'break-word', font: `700 ${sfs}px/1.15 ${dna?.fontMono ?? '"JetBrains Mono", monospace'}`}}>{sub}</div>
          </div>
        );
      })}
      {/* flash at stamp on contact */}
      {prox > 0.2 ? <div style={{position: 'absolute', left: cx - 130, top: beltY - 30, width: 260, height: beltH + 60,
        background: `radial-gradient(closest-side, ${done}55, #0000)`, opacity: prox * 0.9, pointerEvents: 'none'}} /> : null}
    </AbsoluteFill>
  );
};
export default ConveyorBelt;
