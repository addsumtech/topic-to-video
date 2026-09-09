// SHOT · Liquid Glass — Apple's 2026 design-language register: a real frosted-glass lens (backdrop blur +
// specular rim + refraction highlight) glides across a soft UI and settles over the key row, which resolves
// with a ✓. Two smaller glass droplets trail. Premium, on-trend, tactile-optical. Deterministic (lens path = t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom} from '../runtime/layout';

export const DURATION = 165; // 5.5s
// LEVEL-C: frosted glass IS translucent-white on any ground (kept — that's what glass looks like), so the GROUND
// flips to the DNA (a dark-mode Apple glass UI), the UI cards become dark-frosted, ink→fg, orbs/✓→accents. Null=orig.
const DEFAULT_ROWS = ['Draft the brief', 'Pull the numbers', 'Build the deck', 'Ship it'];

const Glass: React.FC<{x: number; y: number; d: number; settled?: number}> = ({x, y, d, settled = 0}) => {
  const dna = useDNA();
  const check = dna?.accent2 ?? dna?.accent ?? '#2ee06a';
  return (
  <div style={{position: 'absolute', left: x - d / 2, top: y - d / 2, width: d, height: d,
    borderRadius: '46% 54% 52% 48% / 50% 46% 54% 50%',
    backdropFilter: 'blur(6px) brightness(1.14) saturate(1.5)', WebkitBackdropFilter: 'blur(6px) brightness(1.14) saturate(1.5)',
    background: 'linear-gradient(135deg, #ffffff30, #ffffff08 40%, #ffffff22)',
    boxShadow: `inset 0 2px 10px #ffffff88, inset 0 -8px 20px #6a86b033, 0 20px 50px #0a1a3a55, 0 0 0 1px #ffffff40`,
    overflow: 'hidden'}}>
    {/* specular sweep */}
    <div style={{position: 'absolute', left: '10%', top: '8%', width: '52%', height: '30%', borderRadius: '50%',
      background: 'radial-gradient(closest-side, #ffffffcc, #ffffff00)', filter: 'blur(3px)'}} />
    {settled > 0.5 && <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
      font: '800 90px/1 var(--f-display, Inter, sans-serif)', color: check, textShadow: '0 2px 10px #0006'}}>✓</div>}
  </div>
  );
};

export const LiquidGlass: React.FC<{items?: string[]; title?: string}> = ({items: ROWS = DEFAULT_ROWS, title = 'Today’s plan'} = {}) => {
  const dna = useDNA();
  const bgc = dna?.bgGrad ?? dna?.bg ?? 'linear-gradient(140deg, #dfe8f7 0%, #eef1f6 45%, #f6ecf3 100%)';
  const FG = dna?.fg ?? '#1b2740', ORB1 = dna?.accent ?? '#7aa8ff', ORB2 = dna?.accent2 ?? '#ff9ec9';
  const CARD = dna ? '#ffffff14' : '#ffffffcc', CARDB = dna ? '#ffffff2e' : '#ffffff', GOOD = dna?.accent2 ?? '#2ee06a';
  const ROW_INK = dna?.fg ?? '#26324c';        // the row label had its own ink — restore it exactly with no DNA
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // FOUR ROWS OF 150 IS 600px OF LIST, and the last one ('Ship it' — the row the whole shot lands on) ran
  // into the caption band at 1:1. The row PITCH yields: the same four rows, closer together, rather than a
  // fourth row the subtitle is drawn over. `rowH - 26` is the row's own height, so the last row's foot is
  // `listY + 4*rowH - 26`. 16:9 and every taller frame keep 150 exactly.
  const listX = W / 2 - 420, listY = 300;
  const rowH = Math.min(150, Math.floor((contentBottom(W, H) - listY + 26) / 4));
  const path = easeInOutCubic(seg(t, 0.1, 0.78));
  const lx = lerp(W * 0.28, listX + 470, path);
  const ly = lerp(H * 0.34, listY + 3 * rowH + 46, path); // settles on last row "Ship it"
  const settled = easeOutBack(seg(t, 0.78, 0.94));

  return (
    <AbsoluteFill style={{background: bgc}}>
      {/* soft colour orbs for the glass to refract */}
      <div style={{position: 'absolute', left: '12%', top: '18%', width: 520, height: 520, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${ORB1}66, ${ORB1}00)`, filter: 'blur(20px)'}} />
      <div style={{position: 'absolute', right: '10%', bottom: '14%', width: 560, height: 560, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${ORB2}66, ${ORB2}00)`, filter: 'blur(20px)'}} />

      {/* the UI beneath */}
      <div style={{position: 'absolute', left: listX, top: listY - 96, color: FG, font: '800 60px/1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.02em'}}>{title}</div>
      {ROWS.map((r, i) => {
        const done = settled > 0.5 && i === 3;
        return (
          <div key={i} style={{position: 'absolute', left: listX, top: listY + i * rowH, width: 900, height: rowH - 26,
            borderRadius: 22, background: CARD, border: `1px solid ${CARDB}`, boxShadow: '0 10px 30px #8aa0c022',
            display: 'flex', alignItems: 'center', gap: 26, padding: '0 34px'}}>
            <div style={{width: 46, height: 46, borderRadius: 12, background: done ? GOOD : ['#7aa8ff', '#b58cff', '#ff9ec9', '#ffcf5a'][i]}} />
            <div style={{color: ROW_INK, font: '600 44px/1 var(--f-body, Inter, system-ui, sans-serif)', textDecoration: done ? 'line-through' : 'none', opacity: done ? 0.6 : 1}}>{r}</div>
          </div>
        );
      })}

      {/* trailing droplets + the main lens (siblings AFTER content → backdrop-filter refracts the UI) */}
      <Glass x={lerp(W * 0.22, lx - 150, path)} y={ly - 120} d={70} />
      <Glass x={lerp(W * 0.25, lx - 90, path)} y={ly + 100} d={46} />
      <Glass x={lx} y={ly} d={300} settled={settled} />
    </AbsoluteFill>
  );
};
export default LiquidGlass;
