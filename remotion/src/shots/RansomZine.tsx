// SHOT · Ransom Zine — a punk cut-out ransom-note / zine collage: each letter is a torn paper scrap in a
// different colour + typeface, dropped in askew and settling under tape strips, over a photocopied grain,
// with a marker scrawl underlining the word. Loud, DIY, hand-made (family L · editorial — the anti-slick
// pole). Deterministic (scrap drops + jitter = fn of index, never RNG).
//
// EVERY LETTER OF THE NOTE LANDS. Scrap i used to drop over `0.06 + i * 0.07 … 0.34 + i * 0.07` — a fixed step
// per character, spaces included — so only about the first ten characters had landed by the settled frame,
// the eleventh to fourteenth were still falling on the LAST frame, and from the fifteenth on they started after
// the clip had ended. The demo's own `STAY WEIRD` was ten, which is why it looked finished; a film's
// 「不要乖，要怪一点」plus a word or two lost its tail in silence. The step is now laid out for the word —
// 0.07 stays the upper bound, so a word of up to eight characters keeps its exact rhythm — and closes until the
// last scrap has settled by LAND_BY, just before the frame `useT` calls settled (the demo's ten now tighten a
// little and settle instead of overshooting on that frame). Past MAX_RANSOM_CHARS the scraps would shrink below
// a legible cut-out, so the register refuses. The marker scrawl and the tape now follow the scrap's scale,
// which they never needed to while the scrap could only be full size.
//
// THE SCRAP PALETTE IS THE REGISTER'S MEANING AND DOES NOT FOLLOW THE DNA. A ransom note is made of scraps cut
// from DIFFERENT printed sources — that is the whole form — so the seven papers and their inks stay exactly as
// they are on every film, the way a syntax palette or a brand hue would. What a scrap does NOT own is its
// BOUNDARY: see the cut edge below.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutBack, easeOutCubic, hash01, REDUCED_MOTION_T} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';

export const DURATION = 145; // ~4.8s
// LEVEL-C: the multi-colour torn-paper SCRAPS are the ransom-note's identity (kept — they pop on any surface); on a
// dark DNA the ground becomes a dark table, the marker scrawl takes the accent, the tagline lifts to fg. Null=orig.
const SCRAPS = ['#f2ead6', '#ffffff', '#ffd23f', '#ff5c8a', '#151515', '#c9a24b', '#7ac0ff'];
const INKS = ['#151515', '#151515', '#151515', '#ffffff', '#ffd23f', '#151515', '#151515'];
const FONTS = ['"Playfair Display", Georgia, serif', 'Impact, system-ui, sans-serif',
  '"JetBrains Mono", monospace', 'Inter, system-ui, sans-serif', '"Source Serif 4", Georgia, serif'];
export const MAX_RANSOM_CHARS = 16;
// Scrap i drops over [DROP_START + i * step, … + DROP_DUR]; DROP_STEP is the original gap and only an upper
// bound — the real step is derived from the word's length so the last scrap has settled by LAND_BY.
const DROP_START = 0.06, DROP_STEP = 0.07, DROP_DUR = 0.28;
const LAND_BY = REDUCED_MOTION_T - 0.02;

export const RansomZine: React.FC<{word?: string; tagline?: string}> = ({
  word: WORD = 'STAY WEIRD', tagline: TAG = 'cut · paste · repeat'} = {}) => {
  const dna = useDNA();
  const bgc = dna?.bg ?? '#d9d4c7', MARK = dna?.accent ?? '#e8452e', TAGc = dna?.fg ?? '#151515';
  // THE CUT EDGE IS DRAWN INSTEAD OF LEFT TO THE SHADOW. A scrap's boundary was nothing but its drop shadow,
  // which works while the paper under it is dark — but two of the seven papers are cream and white, and on a
  // cream FILM a cream scrap's border is paper on paper. Measured on a light ground (2026-09-21,
  // scripts/ink_contrast_qa.py): 30.0% of this register's ink under 3:1, chained into one connected region
  // 1.22% of the frame, and every pixel of it a scrap rim — the letters themselves read (median 4.15:1).
  // A cut-out wants the line anyway, so each scrap and each tape strip now carries the film's own container
  // border as a 1px hairline. It is INSET, so no scrap's box grows by 2px and every drop lands where it did.
  const CUT = dna?.surfaceBorder ?? null;
  const cutEdge = CUT ? `inset 0 0 0 1px ${CUT}, ` : '';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const letters = [...String(WORD ?? '')];
  const n = letters.length;
  if (!String(WORD ?? '').trim() || n > MAX_RANSOM_CHARS) {
    throw new Error(
      `RansomZine needs a \`word\` of 1-${MAX_RANSOM_CHARS} characters, spaces included (got ` +
      `${String(WORD ?? '').trim() ? n : 'no visible character'}). Every character is its own scrap, dropped ` +
      'in one after another on one row; past that the scraps shrink below a legible cut-out. Keep the slogan ' +
      'to a few words.');
  }
  const step = n > 1 ? Math.min(DROP_STEP, (LAND_BY - DROP_START - DROP_DUR) / (n - 1)) : DROP_STEP;
  // The scrap yields to the frame: at a fixed 150 a ten-letter word is 1500px of paper — fine at 1920, and
  // 135px of letters off each edge at 1080-wide portrait. Everything on the scrap scales with it.
  const scrapW = Math.min(150, Math.floor((W * 0.94) / Math.max(1, letters.reduce(
    (c, ch) => c + (ch === ' ' ? 0.4 : 1), 0))));
  const spaceW = Math.round(scrapW * 0.4);
  const scrapK = scrapW / 150;
  const totalW = letters.reduce((s, ch) => s + (ch === ' ' ? spaceW : scrapW), 0);
  let cx = (W - totalW) / 2;
  const tagIn = easeOutCubic(seg(t, 0.66, 0.86));
  const marker = easeOutCubic(seg(t, 0.6, 0.86));
  const scraps = letters.map((ch, i) => {
    const w = ch === ' ' ? spaceW : scrapW;
    const x = cx; cx += w;
    return {ch, x, w, i};
  });
  return (
    <AbsoluteFill style={{background: bgc, overflow: 'hidden'}}>
      {/* photocopy grain */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.16}}>
        <filter id="rz"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4" />
          <feColorMatrix type="saturate" values="0" /></filter>
        <rect width={W} height={H} filter="url(#rz)" />
      </svg>
      {/* torn top/bottom edges */}
      <div style={{position: 'absolute', inset: 0, boxShadow: 'inset 0 0 160px #0000004d'}} />

      {scraps.map((s) => {
        if (s.ch === ' ') return null;
        const rot = (hash01(s.i * 7.3) - 0.5) * 18;
        const drop = easeOutBack(clamp01(seg(t, DROP_START + s.i * step, DROP_START + s.i * step + DROP_DUR)));
        const paper = SCRAPS[Math.floor(hash01(s.i * 3.1) * SCRAPS.length)];
        const ink = INKS[SCRAPS.indexOf(paper)] ?? '#151515';
        const font = FONTS[Math.floor(hash01(s.i * 5.9) * FONTS.length)];
        const sz = Math.round((108 + Math.floor(hash01(s.i * 2.2) * 26)) * scrapK);
        return (
          <div key={s.i} style={{position: 'absolute', left: s.x + Math.round(14 * scrapK), top: H / 2 - Math.round(90 * scrapK), width: s.w - Math.round(20 * scrapK), height: Math.round(180 * scrapK),
            opacity: clamp01(drop * 1.5), transform: `translateY(${(1 - drop) * -140}px) rotate(${rot * drop}deg)`,
            transformOrigin: 'center', background: paper, boxShadow: `${cutEdge}0 14px 26px #00000055`,
            display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <span style={{color: ink, fontFamily: font, fontWeight: 900, fontSize: sz, lineHeight: 1}}>{s.ch}</span>
            {/* a strip of tape across some scraps */}
            {hash01(s.i * 8.8) > 0.5 ? <div style={{position: 'absolute', top: Math.round(-14 * scrapK), left: '20%', width: '60%', height: Math.round(34 * scrapK),
              background: '#e9dfae99', transform: `rotate(${rot > 0 ? -8 : 8}deg)`, boxShadow: `${cutEdge}0 2px 6px #0003`}} /> : null}
          </div>
        );
      })}

      {/* marker underline scrawl */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
        <path d={`M${(W - totalW) / 2 - 10} ${H / 2 + Math.round(90 * scrapK) + 60} q ${totalW / 4} 40 ${totalW / 2} 6 t ${totalW / 2 + 10} 2`}
          fill="none" stroke={MARK} strokeWidth={12} strokeLinecap="round"
          strokeDasharray={totalW + 60} strokeDashoffset={(totalW + 60) * (1 - marker)} opacity={0.9} />
      </svg>

      <div style={{position: 'absolute', left: 0, right: 0, bottom: bottomInset(W, H, 130), textAlign: 'center', opacity: tagIn,
        color: TAGc, font: '800 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.24em',
        textTransform: 'uppercase'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default RansomZine;
