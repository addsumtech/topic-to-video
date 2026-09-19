// SHOT · Neon Ticker Wall — a night-city wall of signage: stacked LED ticker strips scroll headlines at
// different speeds/directions, neon billboards flicker, and a big central marquee holds the message. Urban,
// electric, Times-Square energy (family O · urban / signage). Deterministic (scroll = fn of t, flicker stepped).
//
// ONE STRIP PER TICKER THE FILM WROTE. The wall had six fixed strips and filled them with
// `TICKERS[i % TICKERS.length]`, so a film's four headlines printed its first two twice, and a film with one
// headline had it on all six strips — a wall of repetition standing in for a wall of news, and a reader
// counting "six things are happening". The strips are now laid out for the count: as many as there are
// tickers (1-6), the first half above the marquee and the rest below it, spaced into the bands the marquee
// leaves — a sixth fixed strip used to run behind the marquee itself. A ticker still repeats ALONG its own
// strip, which is what a ticker is, and it now repeats far enough to fill the strip at any scroll position
// (a short headline used to leave most of its strip dark, and the reverse-scrolling strips opened a blank gap
// at the left edge).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {contentBottom, textWidthPx} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#05060d';
const NEON0 = ['#ff2e88', '#00e5ff', '#ffe14d', '#8b5bff', '#39ff88'];
export const MAX_TICKERS = 6;
// the original six strips' speeds and directions, in top-down order for each band
const TOP_MOTION = [{sp: 1, dir: 1}, {sp: 1.7, dir: -1}, {sp: 1.2, dir: 1}];
const BOTTOM_MOTION = [{sp: 1.5, dir: -1}, {sp: 1, dir: 1}, {sp: 2.1, dir: -1}];

export const NeonTickerWall: React.FC<{headline?: string; tickers?: string[]; accent?: string}> = ({
  headline: HEADLINE = 'NOW SHIPPING', tickers: TICKERS =
    ['BREAKING · IT WORKS · ', 'LIVE NOW · ', 'ALL SYSTEMS GO · ', 'SOLD OUT · ENCORE · '],
  accent: ACC = '#ff2e88'} = {}) => {
  if (!Array.isArray(TICKERS) || TICKERS.length < 1 || TICKERS.length > MAX_TICKERS) {
    throw new Error(`NeonTickerWall needs 1-${MAX_TICKERS} \`tickers\` (got ${Array.isArray(TICKERS) ? TICKERS.length : typeof TICKERS}). ` +
      'Each gets its own strip, three above the marquee and three below; past six, keep the headlines that matter.');
  }
  TICKERS.forEach((tk, i) => {
    if (!String(tk ?? '').trim()) throw new Error(`NeonTickerWall: ticker ${i + 1} is empty.`);
  });
  const dna = useDNA();
  const NEON = dnaPalette(dna, 5) ?? NEON0;   // derive the palette from the film's DNA (null DNA = the original)
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const flick = (seed: number) => 0.6 + 0.4 * (hash01(seed + Math.floor(t * 12)) > 0.15 ? 1 : 0.3);
  const marquee = easeOutBack(clamp01(seg(t, 0.24, 0.5)));
  // The lower rows were pinned to the FRAME's bottom, so the last one ran straight through the strip the
  // renderer burns the caption over — a scrolling marquee under a subtitle. Pinned to the content zone's
  // floor instead, keeping the spacing they were authored with (32/142/224px up from the floor).
  const floor = contentBottom(W, H);
  // THE STRIPS ARE LAID OUT FOR THE COUNT, in the two bands the marquee leaves: the top band starts where the
  // first strip always did (y=90) and keeps its 120px pitch while there is room; the bottom band is pinned to
  // the content floor. The marquee box is 128px type + 38px padding each side + a 4px border, centred on the
  // frame, plus 16px of air.
  const STRIP_H = 64, mTop = H / 2 - 106 - 16, mBot = H / 2 + 106 + 16;
  const n = TICKERS.length, nTop = Math.ceil(n / 2), nBot = n - nTop;
  const band = (a: number, b: number, k: number, cap: number) =>
    // @positional: `k` is how MANY strips share a band, not any ticker's index — a band holding one strip has no pitch to fit
    k <= 1 ? cap : Math.max(STRIP_H + 6, Math.min(cap, (b - a - STRIP_H) / (k - 1)));
  const topPitch = band(90, mTop, nTop, 120), botPitch = band(mBot, floor, nBot, 114);
  const strips = TICKERS.map((text, i) => (i < nTop
    ? {text, y: 90 + i * topPitch, ...TOP_MOTION[i]}
    : {text, y: floor - STRIP_H - (nBot - 1 - (i - nTop)) * botPitch, ...BOTTOM_MOTION[3 - nBot + (i - nTop)]}));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 90% at 50% 46%, #0c0f22, ${BG} 76%)`, overflow: 'hidden'}}>
      {/* rain of vertical light streaks (buildings) */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        {[...Array(24)].map((_, k) => {
          const x = (k / 24) * W + 20, col = NEON[k % NEON.length];
          // @decor: 24 faint background streaks of city glow; their opacity varies so they read as distant signage, and none stands for a ticker
          return <rect key={k} x={x} y={0} width={3} height={H} fill={col} opacity={0.05 + 0.05 * hash01(k)} />;
        })}
      </svg>

      {/* scrolling LED ticker strips */}
      {strips.map((s, i) => {
        const col = NEON[i % NEON.length];
        // repeated along its OWN strip far enough to cover the frame plus the 800px of scroll either way; the
        // run starts 800px left of the frame so a strip scrolling right never opens a gap at the left edge
        const unit = String(TICKERS[i]);   // strips are TICKERS.map(...), so strip i IS ticker i
        const unitW = Math.max(1, textWidthPx(unit, 42, {adv: 0.6, cjk: 1.0}));   // low estimate → enough copies
        const txt = unit.repeat(Math.ceil((W + 1600) / unitW) + 1);
        const shift = ((t * s.sp * 420) % 800) * s.dir;
        return (
          <div key={i} style={{position: 'absolute', left: 0, right: 0, top: s.y, height: 64, overflow: 'hidden',
            background: '#0a0c18', borderTop: `1px solid ${col}55`, borderBottom: `1px solid ${col}55`,
            opacity: flick(i * 3.3)}}>
            <div style={{position: 'absolute', whiteSpace: 'nowrap', top: 10, left: -800, transform: `translateX(${-shift}px)`,
              color: col, font: '800 42px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.06em',
              textShadow: `0 0 14px ${col}`}}>{txt}</div>
          </div>
        );
      })}

      {/* central neon billboard marquee */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{transform: `scale(${lerp(0.8, 1, marquee)})`, opacity: clamp01(marquee * 1.3),
          padding: '38px 66px', borderRadius: 18, background: '#07091a',
          border: `4px solid ${ACC}`, boxShadow: `0 0 60px ${ACC}88, inset 0 0 40px ${ACC}44`}}>
          <div style={{color: '#fff', font: '900 128px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.02em',
            textShadow: `0 0 30px ${ACC}, 0 0 60px ${ACC}`, opacity: flick(99)}}>{HEADLINE}</div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default NeonTickerWall;
