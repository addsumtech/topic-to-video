// SHOT · Ransom Zine — a punk cut-out ransom-note / zine collage: each letter is a torn paper scrap in a
// different colour + typeface, dropped in askew and settling under tape strips, over a photocopied grain,
// with a marker scrawl underlining the word. Loud, DIY, hand-made (family L · editorial — the anti-slick
// pole). Deterministic (scrap drops + jitter = fn of index, never RNG).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';

export const DURATION = 145; // ~4.8s
const SCRAPS = ['#f2ead6', '#ffffff', '#ffd23f', '#ff5c8a', '#151515', '#c9a24b', '#7ac0ff'];
const INKS = ['#151515', '#151515', '#151515', '#ffffff', '#ffd23f', '#151515', '#151515'];
const FONTS = ['"Playfair Display", Georgia, serif', 'Impact, system-ui, sans-serif',
  '"JetBrains Mono", monospace', 'Inter, system-ui, sans-serif', 'Georgia, serif'];

export const RansomZine: React.FC<{word?: string; tagline?: string}> = ({
  word: WORD = 'STAY WEIRD', tagline: TAG = 'cut · paste · repeat'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const letters = WORD.split('');
  const n = letters.length;
  const totalW = letters.reduce((s, ch) => s + (ch === ' ' ? 60 : 150), 0);
  let cx = (W - totalW) / 2;
  const tagIn = easeOutCubic(seg(t, 0.66, 0.86));
  const marker = easeOutCubic(seg(t, 0.6, 0.86));
  const scraps = letters.map((ch, i) => {
    const w = ch === ' ' ? 60 : 150;
    const x = cx; cx += w;
    return {ch, x, w, i};
  });
  return (
    <AbsoluteFill style={{background: '#d9d4c7', overflow: 'hidden'}}>
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
        const drop = easeOutBack(clamp01(seg(t, 0.06 + s.i * 0.07, 0.34 + s.i * 0.07)));
        const paper = SCRAPS[Math.floor(hash01(s.i * 3.1) * SCRAPS.length)];
        const ink = INKS[SCRAPS.indexOf(paper)] ?? '#151515';
        const font = FONTS[Math.floor(hash01(s.i * 5.9) * FONTS.length)];
        const sz = 108 + Math.floor(hash01(s.i * 2.2) * 26);
        return (
          <div key={s.i} style={{position: 'absolute', left: s.x + 14, top: H / 2 - 90, width: s.w - 20, height: 180,
            opacity: clamp01(drop * 1.5), transform: `translateY(${(1 - drop) * -140}px) rotate(${rot * drop}deg)`,
            transformOrigin: 'center', background: paper, boxShadow: '0 14px 26px #00000055',
            display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <span style={{color: ink, fontFamily: font, fontWeight: 900, fontSize: sz, lineHeight: 1}}>{s.ch}</span>
            {/* a strip of tape across some scraps */}
            {hash01(s.i * 8.8) > 0.5 ? <div style={{position: 'absolute', top: -14, left: '20%', width: '60%', height: 34,
              background: '#e9dfae99', transform: `rotate(${rot > 0 ? -8 : 8}deg)`, boxShadow: '0 2px 6px #0003'}} /> : null}
          </div>
        );
      })}

      {/* marker underline scrawl */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
        <path d={`M${(W - totalW) / 2 - 10} ${H / 2 + 150} q ${totalW / 4} 40 ${totalW / 2} 6 t ${totalW / 2 + 10} 2`}
          fill="none" stroke="#e8452e" strokeWidth={12} strokeLinecap="round"
          strokeDasharray={totalW + 60} strokeDashoffset={(totalW + 60) * (1 - marker)} opacity={0.9} />
      </svg>

      <div style={{position: 'absolute', left: 0, right: 0, bottom: 130, textAlign: 'center', opacity: tagIn,
        color: '#151515', font: '800 34px/1 "JetBrains Mono", monospace', letterSpacing: '0.24em',
        textTransform: 'uppercase'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default RansomZine;
