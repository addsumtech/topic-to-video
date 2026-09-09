// SHOT · Comic Panels — a comic page tells a beat: panels snap in one by one (tilted gutters, halftone,
// speed-lines + burst captions), building to a final full-width SPLASH panel with the payoff. Sequential
// manga/comic storytelling (family G · illustrated/craft). Deterministic (panel reveals = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {contentBottom} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
// LEVEL-C: comic storytelling is the STRUCTURE (tilted panels, gutters, halftone wash, speed lines, a splash
// payoff) — on a themed DNA the page INVERTS to dark stock with light ink and DNA-derived POP flats (an inked
// night comic), keeping every panel legible. Null DNA = the original newsprint page.
const PAPER0 = '#f7f2e7', INK0 = '#141414';
const POP0 = ['#ff3b6b', '#ffd23f', '#2b7bff', '#00b070'];

// `title` USED TO BE DECLARED HERE AND WAS NEVER DRAWN. A strip is panels and a splash; the frame is full
// from margin to margin and there is nowhere a title could go without taking a panel's room. A prop that is
// accepted and discarded is worse than a missing one — the film's copy disappears with no error anywhere —
// so the signature says what the register actually renders.
export const ComicPanels: React.FC<{panels?: string[]; splash?: string}> = ({
  panels: PANELS = ['ZIP!', 'WHIRR', 'CLICK'], splash: SPLASH = 'DONE!'} = {}) => {
  const dna = useDNA();
  const PAPER = dna?.bg ?? PAPER0, INK = dna?.fg ?? INK0;
  const POP = dnaPalette(dna, 4) ?? POP0;
  const HT = dna ? `${dna.fg}1a` : '#0000001a';          // halftone wash follows the ink
  const SPLASHINK = dna?.onAccent ?? '#fff';             // type on the accent-filled splash panel
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const M = 70, gut = 22;
  // THE PAGE IS TWO ROWS AND THE SECOND IS 0.82 OF THE FIRST, so the page is 1.82 rows deep from `topY` —
  // and `rowH` was a flat 0.52 of the FRAME's height, which reaches past the caption band (81px of 'DONE!'
  // inside it at 1:1, and the bottom plate crossing it even at 16:9, where only the lettering's centring
  // kept the gate quiet). A comic page is laid out to its plate, not to the paper it is printed on.
  const topY = M;
  const rowH = Math.min((H - 2 * M - gut) * 0.52, (contentBottom(W, H) - topY - gut) / 1.82);
  const cols = Math.max(1, PANELS.length);
  const colW = (W - 2 * M - (cols - 1) * gut) / cols;
  const splashIn = easeOutBack(clamp01(seg(t, 0.6, 0.84)));
  return (
    <AbsoluteFill style={{background: PAPER, overflow: 'hidden'}}>
      {/* halftone wash */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        <pattern id="cht" width={14} height={14} patternUnits="userSpaceOnUse"><circle cx={3} cy={3} r={1.4} fill={HT} /></pattern>
        <rect width={W} height={H} fill="url(#cht)" />
      </svg>

      {/* top row of action panels */}
      {PANELS.map((cap, i) => {
        const x = M + i * (colW + gut);
        const pop = easeOutBack(clamp01(seg(t, 0.08 + i * 0.13, 0.34 + i * 0.13)));
        const col = POP[i % POP.length];
        const rot = (i - (cols - 1) / 2) * 1.4;
        return (
          <div key={i} style={{position: 'absolute', left: x, top: topY, width: colW, height: rowH,
            opacity: clamp01(pop * 1.4), transform: `translateY(${(1 - pop) * 40}px) rotate(${rot}deg) scale(${lerp(0.92, 1, pop)})`,
            background: `radial-gradient(120% 120% at 30% 20%, ${col}22, ${PAPER})`, border: `6px solid ${INK}`,
            boxShadow: '10px 12px 0 #0000001f', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            {/* speed lines converging */}
            <svg width={colW} height={rowH} style={{position: 'absolute', inset: 0}}>
              {[...Array(20)].map((_, k) => {
                const a = (k / 20) * Math.PI * 2;
                const ox = colW / 2 + Math.cos(a) * colW, oy = rowH / 2 + Math.sin(a) * rowH;
                return <line key={k} x1={ox} y1={oy} x2={colW / 2 + Math.cos(a) * 120} y2={rowH / 2 + Math.sin(a) * 90}
                  stroke={INK} strokeWidth={2} opacity={0.14} />;
              })}
            </svg>
            <div style={{position: 'relative', color: INK, fontFamily: 'var(--f-display, Impact, system-ui, sans-serif)', fontSize: 92,
              WebkitTextStroke: `3px ${col}`, transform: 'rotate(-6deg)', letterSpacing: '-0.02em'}}>{cap}</div>
            <div style={{position: 'absolute', top: 14, left: 18, color: INK, font: '800 26px/1 var(--f-mono, "JetBrains Mono", monospace)'}}>{i + 1}</div>
          </div>
        );
      })}

      {/* splash payoff panel */}
      <div style={{position: 'absolute', left: M, top: topY + rowH + gut, width: W - 2 * M, height: rowH * 0.82,
        opacity: clamp01(splashIn), transform: `scale(${lerp(0.94, 1, splashIn)})`, transformOrigin: 'center',
        background: `linear-gradient(120deg, ${POP[0]}, ${POP[2]})`, border: `8px solid ${INK}`,
        boxShadow: '14px 16px 0 #00000022', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden'}}>
        {/* burst */}
        <svg width={W - 2 * M} height={rowH * 0.82} style={{position: 'absolute', inset: 0}}>
          {[...Array(28)].map((_, k) => {
            const a = (k / 28) * Math.PI * 2, r0 = 40, r1 = k % 2 ? 460 : 300, cx2 = (W - 2 * M) / 2, cy2 = rowH * 0.41;
            return <line key={k} x1={cx2 + Math.cos(a) * r0} y1={cy2 + Math.sin(a) * r0}
              x2={cx2 + Math.cos(a) * r1} y2={cy2 + Math.sin(a) * r1} stroke={SPLASHINK} strokeWidth={3} opacity={0.16} />;
          })}
        </svg>
        <div style={{position: 'relative', color: SPLASHINK, fontFamily: 'var(--f-display, Impact, system-ui, sans-serif)', fontSize: 190,
          WebkitTextStroke: `6px ${INK}`, letterSpacing: '-0.02em', transform: 'rotate(-4deg)',
          textShadow: '8px 8px 0 #00000044'}}>{SPLASH}</div>
      </div>
    </AbsoluteFill>
  );
};
export default ComicPanels;
