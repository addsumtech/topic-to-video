// SHOT · Liquid Glass — Apple's 2026 design-language register: a real frosted-glass lens (backdrop blur +
// specular rim + refraction highlight) glides across a soft UI and settles over the row the film names as
// `target`, which resolves with a ✓ (with no target it comes to rest off the list). Two smaller droplets trail. Premium, on-trend, tactile-optical. Deterministic (lens path = t).
//
// THE ROW THE LENS RESOLVES IS THE FILM'S. It used to be two different rows by position, both wrong: the
// strike-through and green chip went to `i === 3`, the FOURTH item, whatever the list, while the lens and its
// ✓ settled on the LAST row. A film handing it four steps it had not started shipped the fourth crossed out;
// a film handing it seven had row 4 crossed out and the ✓ on row 7 — two different "done" claims on one frame,
// neither of them made. Now `target` (an index) names the row the lens settles on, and that row alone ticks,
// greens and strikes through. With no target nothing is resolved: the lens glides across the list and comes
// to rest OFF it — in the empty gutter beside the list, or below it on a tall frame, or peeking in from the
// right edge where the frame has neither — with no ✓ and no row struck. (Resting it on the heading was tried
// and rejected by looking: the glass is frosted, so it blurred the heading it was meant to leave neutral and
// half of row 1 with it.) The standalone demo keeps its landing on 'Ship it' by passing its own target.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, inkBlockH} from '../runtime/layout';

export const DURATION = 165; // 5.5s
// LEVEL-C: frosted glass IS translucent-white on any ground (kept — that's what glass looks like), so the GROUND
// flips to the DNA (a dark-mode Apple glass UI), the UI cards become dark-frosted, ink→fg, orbs/✓→accents. Null=orig.
const DEFAULT_ROWS = ['Draft the brief', 'Pull the numbers', 'Build the deck', 'Ship it'];
// the demo's own choice, applied only while the demo's own rows are showing — never to a film's list
const DEMO_TARGET = 3;
// Past six the pitch closes below what a row's own chip and 44px label need on a square frame (rowH - 26 < 56).
export const MAX_GLASS_ROWS = 6;
const CHIPS = ['#7aa8ff', '#b58cff', '#ff9ec9', '#ffcf5a'];

const Glass: React.FC<{x: number; y: number; d: number; settled?: number; check?: number}> = ({x, y, d, settled = 0, check: CHECK = 90}) => {
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
      font: `800 ${CHECK}px/1 var(--f-display, Inter, sans-serif)`, color: check, textShadow: '0 2px 10px #0006'}}>✓</div>}
  </div>
  );
};

export const LiquidGlass: React.FC<{items?: string[]; title?: string; target?: number | null}> = ({items: ROWS = DEFAULT_ROWS, title = 'Today’s plan', target: TARGET} = {}) => {
  if (!Array.isArray(ROWS) || ROWS.length < 1 || ROWS.length > MAX_GLASS_ROWS) {
    throw new Error(`LiquidGlass needs 1-${MAX_GLASS_ROWS} \`items\` (got ${Array.isArray(ROWS) ? ROWS.length : typeof ROWS}). ` +
      'Past six the rows close up below the height their chip and label need — split the list or cast a list register.');
  }
  ROWS.forEach((r, i) => {
    if (!String(r ?? '').trim()) throw new Error(`LiquidGlass: item ${i + 1} is empty.`);
  });
  // `target` selects, so it defaults to NONE; only the untouched demo list gets the demo's own target.
  const target = TARGET !== undefined ? TARGET : (ROWS === DEFAULT_ROWS ? DEMO_TARGET : null);
  if (target != null && !(Number.isInteger(target) && target >= 0 && target < ROWS.length)) {
    throw new Error(`LiquidGlass: \`target\` is ${JSON.stringify(target)}, but it must be the index (0-${ROWS.length - 1}) ` +
      'of the row the lens resolves with a ✓ — or leave it out and no row is resolved.');
  }
  const dna = useDNA();
  const bgc = dna?.bgGrad ?? dna?.bg ?? 'linear-gradient(140deg, #dfe8f7 0%, #eef1f6 45%, #f6ecf3 100%)';
  const FG = dna?.fg ?? '#1b2740', ORB1 = dna?.accent ?? '#7aa8ff', ORB2 = dna?.accent2 ?? '#ff9ec9';
  const CARD = dna ? '#ffffff14' : '#ffffffcc', CARDB = dna ? '#ffffff2e' : '#ffffff', GOOD = dna?.accent2 ?? '#2ee06a';
  const ROW_INK = dna?.fg ?? '#26324c';        // the row label had its own ink — restore it exactly with no DNA
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // THE ROW PITCH YIELDS, AND IT YIELDS TO THE LIST THE FILM SUPPLIED. Four rows of 150 is 600px and the
  // last one ('Ship it' — the row the whole shot lands on) ran into the caption band at 1:1. The first
  // repair divided by 4 — the DEMO's row count — so a film passing seven items put three of them under the
  // subtitle and one off the frame, at 16:9. `rowH - 26` is a row's own height, so the last row's foot is
  // `listY + n*rowH - 26`. The default four on a 16:9 frame keep 150 exactly.
  const listX = W / 2 - 420, listY = 300;
  const n = Math.max(1, ROWS.length);
  const rowH = Math.min(150, Math.floor((contentBottom(W, H) - listY + 26) / n));
  const path = easeInOutCubic(seg(t, 0.1, 0.78));
  // THE LENS IS SIZED FOR A 150px ROW, so when the pitch closes up the orb and its ✓ close up with it —
  // otherwise a seven-item list shrinks its rows and then parks a 300px orb carrying a 90px tick across the
  // caption band. `k` is exactly 1 at the pitch this was drawn at, so the default four rows are untouched.
  const k = rowH / 150;
  const ORB = Math.round(300 * k), CHECK = Math.round(90 * k);
  // WHERE IT SETTLES: on the target row, or — with no target — somewhere no text is. Frosted glass blurs what
  // is under it, so a lens at rest over a row both emphasises that row and makes it unreadable.
  const titleY = listY - 96;
  const listBottom = listY + n * rowH - 26;
  const gutterR = W - (listX + 900), roomBelow = contentBottom(W, H) - listBottom;
  const [restX, restY] = target != null
    // and the settle point yields to the band: the tick is centred on it, so half its ink hangs below.
    ? [listX + 470, Math.min(listY + target * rowH + 46 * k, contentBottom(W, H) - Math.round(inkBlockH(CHECK) / 2))]
    : gutterR >= ORB + 40 ? [listX + 900 + gutterR / 2, (listY + listBottom) / 2]
    : roomBelow >= ORB + 40 ? [W / 2, listBottom + roomBelow / 2]
    // peeking in over the rows' empty right ends, centred on the GAP between two rows (for an odd count the
    // list's middle is a row's middle, and a lens there would single that row out)
    : [W - ORB * 0.25, listY + Math.max(1, Math.floor(n / 2)) * rowH - 13];
  const lx = lerp(W * 0.28, restX, path);
  const ly = lerp(H * 0.34, restY, path);
  const settled = easeOutBack(seg(t, 0.78, 0.94));

  return (
    <AbsoluteFill style={{background: bgc}}>
      {/* soft colour orbs for the glass to refract */}
      <div style={{position: 'absolute', left: '12%', top: '18%', width: 520, height: 520, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${ORB1}66, ${ORB1}00)`, filter: 'blur(20px)'}} />
      <div style={{position: 'absolute', right: '10%', bottom: '14%', width: 560, height: 560, borderRadius: '50%',
        background: `radial-gradient(closest-side, ${ORB2}66, ${ORB2}00)`, filter: 'blur(20px)'}} />

      {/* the UI beneath */}
      <div style={{position: 'absolute', left: listX, top: titleY, color: FG, font: '800 60px/1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.02em'}}>{title}</div>
      {ROWS.map((r, i) => {
        const done = settled > 0.5 && i === target;
        return (
          <div key={i} style={{position: 'absolute', left: listX, top: listY + i * rowH, width: 900, height: rowH - 26,
            borderRadius: 22, background: CARD, border: `1px solid ${CARDB}`, boxShadow: '0 10px 30px #8aa0c022',
            display: 'flex', alignItems: 'center', gap: 26, padding: '0 34px'}}>
            <div style={{width: 46, height: 46, borderRadius: 12, background: done ? GOOD : CHIPS[i % CHIPS.length]}} />
            <div style={{color: ROW_INK, font: '600 44px/1 var(--f-body, Inter, system-ui, sans-serif)', textDecoration: done ? 'line-through' : 'none', opacity: done ? 0.6 : 1}}>{r}</div>
          </div>
        );
      })}

      {/* trailing droplets + the main lens (siblings AFTER content → backdrop-filter refracts the UI) */}
      <Glass x={lerp(W * 0.22, lx - 150 * k, path)} y={ly - 120 * k} d={Math.round(70 * k)} />
      <Glass x={lerp(W * 0.25, lx - 90 * k, path)} y={ly + 100 * k} d={Math.round(46 * k)} />
      <Glass x={lx} y={ly} d={ORB} settled={target != null ? settled : 0} check={CHECK} />
    </AbsoluteFill>
  );
};
export default LiquidGlass;
