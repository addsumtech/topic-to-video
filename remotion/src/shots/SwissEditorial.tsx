// SHOT · Swiss Editorial — the high-end typographic register (Obys / fashion-film): a strict grid, hairline
// rules, an index counter, a MASSIVE flush-left word that SNAPS through a sequence (WORK. → SHIP. → DONE.) via
// a clip-reveal, and a marquee TICKER scrolling the opposite way. Red/black/cream. Type IS the design.
// Deterministic (snap index + ticker offset = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutExpo} from '../runtime/motion';
import {captionBand} from '../runtime/layout';
import {useDNA} from '../runtime/dna';
import {fitText} from '@remotion/layout-utils';

export const DURATION = 165; // 5.5s

// The index marker of a Swiss editorial grid — the mark that says "this is a numbered index", the way a
// folio rule says "this is a page". It names no topic.
export const INTRINSIC_TEXT = ['INDEX /'];
const CREAM = '#f0ece1', INK = '#141414', RED = '#e8321f';
const DEFAULT_WORDS = ['WORK.', 'SHIP.', 'DONE.'];
const DEFAULT_TICKER = 'WORKBUDDY —— ON YOUR MACHINE —— YOUR AI TEAM —— NO CLOUD —— ';

// CJK-EXEMPT (tight leading, no floor): the word is whiteSpace:'nowrap' — it cannot wrap, so its lines cannot collide.
export const SwissEditorial: React.FC<{items?: string[]; ticker?: string; wordmark?: string;
  colophon?: string}> = ({
  items: WORDS = DEFAULT_WORDS, ticker: TICKER = DEFAULT_TICKER, wordmark: MARK = 'WORKBUDDY™',
  // was the literal '©2026 · LOCAL', printed onto every film that used this register whatever it was
  // about. A corner mark nobody can decode is furniture; pass one that means something, or nothing.
  colophon: COLOPHON = ''} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // LEVEL-C DNA migration: the WHOLE palette flips together (ground + ink + accent + on-accent), so on a dark DNA
  // this reads as a dark editorial poster instead of inverting to invisible ink-on-ink (the level-A failure). Null
  // DNA = the original cream/ink/red poster, byte-for-byte. Fonts follow the DNA too (mono labels, display word).
  const dna = useDNA();
  const BG = dna?.bg ?? CREAM, FG = dna?.fg ?? INK, ACC = dna?.accent ?? RED, ON = dna?.onAccent ?? CREAM;
  const FAINT = dna ? `${FG}22` : '#00000022';
  const disp = dna?.fontDisplay ?? '"Archivo", "Helvetica Neue", Arial, sans-serif';
  const mono = dna?.fontMono ?? '"JetBrains Mono", monospace';
  // NO WORDS IS A REFUSAL, NOT A CRASH. `items: []` used to reach `word.slice(0, -1)` on an undefined word and
  // die with a TypeError that named nothing a film author could act on; an empty string printed an empty
  // snap and an INDEX counter pointing at it. Both now say what to pass.
  if (!Array.isArray(WORDS) || WORDS.length < 1) {
    throw new Error('SwissEditorial needs `items`: at least one word to snap through (e.g. ["WORK.", "SHIP.", ' +
      '"DONE."]). With none there is nothing for the index to count or the grid to set.');
  }
  WORDS.forEach((w, i) => {
    if (!String(w ?? '').trim()) throw new Error(`SwissEditorial: word ${i + 1} of \`items\` is empty.`);
  });
  // which word + its local reveal
  const seq = clamp01(seg(t, 0.08, 0.92)) * WORDS.length;
  const idx = Math.min(WORDS.length - 1, Math.floor(seq));
  const local = seq - idx;                       // 0..1 within this word
  const reveal = easeOutExpo(clamp01(local / 0.4)); // clip-rise reveal at each snap
  const word = WORDS[idx];
  // WIDTH-AWARE, MEASURED. This block used a fixed 340px with `nowrap` inside an `overflow:hidden` box, so any
  // word past ~9 characters was SILENTLY TRUNCATED — "ONBOARDING." rendered as "ONBOARD", with no ellipsis and
  // no error, and portrait roughly halved the safe length. The library's older fix for this shape is a magic
  // ratio (EdStat uses len*0.6), but that cannot be right here: `disp` is the DNA's display face, and those
  // range from Bodoni Moda to JetBrains Mono, whose advance widths differ enormously. So measure the real
  // string in the real face instead. Sized off the LONGEST word so all beats share one size (the register's
  // character — the words swap in place) and every one of them fits.
  const longest = WORDS.reduce((a, b) => (String(b).length > String(a).length ? b : a), WORDS[0] ?? '');
  const wordSize = Math.min(340, fitText({
    text: String(longest), withinWidth: W - 240, fontFamily: disp, fontWeight: 900,
    letterSpacing: '-0.04em',
  }).fontSize);
  const tick = (t * 420) % 1000;                 // ticker scroll (px)

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* grid hairlines */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[0.5].map((v, i) => <line key={i} x1={W * v} y1={0} x2={W * v} y2={H} stroke={FG} strokeOpacity={0.12} strokeWidth={1.5} />)}
        <line x1={120} y1={150} x2={W - 120} y2={150} stroke={FG} strokeWidth={2} />
        <line x1={120} y1={H - 260} x2={W - 120} y2={H - 260} stroke={FG} strokeWidth={2} />
      </svg>

      {/* top labels */}
      <div style={{position: 'absolute', left: 120, top: 104, color: FG, font: `700 26px/1 ${mono}`, letterSpacing: '0.02em'}}>{MARK}</div>
      <div style={{position: 'absolute', right: 120, top: 104, color: FG, font: `700 26px/1 ${mono}`}}>INDEX / {String(idx + 1).padStart(2, '0')}</div>
      {COLOPHON ? (
        <div style={{position: 'absolute', right: 120, top: 180, color: ACC,
          font: `700 26px/1 ${mono}`}}>{COLOPHON}</div>
      ) : null}

      {/* massive flush-left snapping word (clip-rise reveal) */}
      <div style={{position: 'absolute', left: 120, top: H * 0.5, transform: 'translateY(-50%)', width: W - 240, height: 360, overflow: 'hidden'}}>
        <div style={{transform: `translateY(${(1 - reveal) * 360}px)`, color: FG,
          font: `900 ${wordSize}px/0.86 ${disp}`, letterSpacing: '-0.04em', whiteSpace: 'nowrap'}}>
          {word.slice(0, -1)}<span style={{color: ACC}}>{word.slice(-1)}</span>
        </div>
      </div>

      {/* progress ticks (which word we're on) */}
      <div style={{position: 'absolute', left: 120, bottom: 300, display: 'flex', gap: 14}}>
        {WORDS.map((_, i) => <div key={i} style={{width: i === idx ? 64 : 26, height: 8, background: i === idx ? ACC : FAINT, transition: 'none'}} />)}
      </div>

      {/* marquee ticker band (accent) */}
      {/* The ticker band used to sit at bottom:90 — INSIDE the 150px the renderer reserves for the burned
          caption, so the subtitle was printed onto a moving accent bar on every film that used this
          register. Lifting it clear then put it through the snapped words instead, so it is now drawn
          ONLY when there is a ticker to run: an empty ticker is a band with nothing in it, and a band with
          nothing in it is furniture. */}
      {TICKER ? (
      <div style={{position: 'absolute', left: 0, right: 0, bottom: captionBand(W, H) + 24, height: 96, background: ACC, display: 'flex', alignItems: 'center', overflow: 'hidden'}}>
        <div style={{transform: `translateX(${-tick}px)`, whiteSpace: 'nowrap', color: ON,
          font: `800 48px/1 ${disp}`, letterSpacing: '0.02em'}}>
          {TICKER.repeat(6)}
        </div>
      </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default SwissEditorial;
