// SHOT · Swiss Editorial — the high-end typographic register (Obys / fashion-film): a strict grid, hairline
// rules, an index counter, a MASSIVE flush-left word that SNAPS through a sequence (WORK. → SHIP. → DONE.) via
// a clip-reveal, and a marquee TICKER scrolling the opposite way. Red/black/cream. Type IS the design.
// Deterministic (snap index + ticker offset = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutExpo} from '../runtime/motion';

export const DURATION = 165; // 5.5s
const CREAM = '#f0ece1', INK = '#141414', RED = '#e8321f';
const DEFAULT_WORDS = ['WORK.', 'SHIP.', 'DONE.'];
const DEFAULT_TICKER = 'WORKBUDDY —— ON YOUR MACHINE —— YOUR AI TEAM —— NO CLOUD —— ';

export const SwissEditorial: React.FC<{items?: string[]; ticker?: string; wordmark?: string}> = ({
  items: WORDS = DEFAULT_WORDS, ticker: TICKER = DEFAULT_TICKER, wordmark: MARK = 'WORKBUDDY™'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // which word + its local reveal
  const seq = clamp01(seg(t, 0.08, 0.92)) * WORDS.length;
  const idx = Math.min(WORDS.length - 1, Math.floor(seq));
  const local = seq - idx;                       // 0..1 within this word
  const reveal = easeOutExpo(clamp01(local / 0.4)); // clip-rise reveal at each snap
  const word = WORDS[idx];
  const tick = (t * 420) % 1000;                 // ticker scroll (px)

  return (
    <AbsoluteFill style={{background: CREAM, overflow: 'hidden'}}>
      {/* grid hairlines */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[0.5].map((v, i) => <line key={i} x1={W * v} y1={0} x2={W * v} y2={H} stroke={INK} strokeOpacity={0.12} strokeWidth={1.5} />)}
        <line x1={120} y1={150} x2={W - 120} y2={150} stroke={INK} strokeWidth={2} />
        <line x1={120} y1={H - 260} x2={W - 120} y2={H - 260} stroke={INK} strokeWidth={2} />
      </svg>

      {/* top labels */}
      <div style={{position: 'absolute', left: 120, top: 104, color: INK, font: '700 26px/1 "JetBrains Mono", monospace', letterSpacing: '0.02em'}}>{MARK}</div>
      <div style={{position: 'absolute', right: 120, top: 104, color: INK, font: '700 26px/1 "JetBrains Mono", monospace'}}>INDEX / {String(idx + 1).padStart(2, '0')}</div>
      <div style={{position: 'absolute', right: 120, top: 180, color: RED, font: '700 26px/1 "JetBrains Mono", monospace'}}>©2026 · LOCAL</div>

      {/* massive flush-left snapping word (clip-rise reveal) */}
      <div style={{position: 'absolute', left: 120, top: H * 0.5, transform: 'translateY(-50%)', width: W - 240, height: 360, overflow: 'hidden'}}>
        <div style={{transform: `translateY(${(1 - reveal) * 360}px)`, color: INK,
          font: '900 340px/0.86 "Archivo", "Helvetica Neue", Arial, sans-serif', letterSpacing: '-0.04em', whiteSpace: 'nowrap'}}>
          {word.slice(0, -1)}<span style={{color: RED}}>{word.slice(-1)}</span>
        </div>
      </div>

      {/* progress ticks (which word we're on) */}
      <div style={{position: 'absolute', left: 120, bottom: 300, display: 'flex', gap: 14}}>
        {WORDS.map((_, i) => <div key={i} style={{width: i === idx ? 64 : 26, height: 8, background: i === idx ? RED : '#00000022', transition: 'none'}} />)}
      </div>

      {/* marquee ticker band (red) */}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 90, height: 96, background: RED, display: 'flex', alignItems: 'center', overflow: 'hidden'}}>
        <div style={{transform: `translateX(${-tick}px)`, whiteSpace: 'nowrap', color: CREAM,
          font: '800 48px/1 "Archivo", "Helvetica Neue", Arial, sans-serif', letterSpacing: '0.02em'}}>
          {TICKER.repeat(6)}
        </div>
      </div>
    </AbsoluteFill>
  );
};
export default SwissEditorial;
