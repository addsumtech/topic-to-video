// SHOT · Anti-Design Chaos — a deliberately "wrong" maximalist collage: a huge clashing headline, scattered
// mismatched words in different fonts/sizes/rotations, sticker shapes, hand-drawn arrows + scribbles, on a
// loud ground — every element popping in askew with a bounce. The 2026 anti-design / maximalist trend
// (family Q · anti-design). Deterministic (placement + rotation from hash01, not RNG).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {useDNA, dnaPalette} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';
import {CONTENT_TOP, contentBottom, fitBlockPx, fitTextPx, inkBlockH, textWidthPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 150; // 5s
// LEVEL-C: maximalism needs a CLASH, not one accent — dnaPalette() grows six distinct hues out of the DNA's two
// accents, so the collage stays loud and mismatched while still belonging to the film; the ground/headline invert
// on a dark DNA. Null DNA = the original yellow anti-design page.
const GROUND0 = '#f4e63a';
const POP0 = ['#ff2e6e', '#1b1b1b', '#2b6bff', '#00c37a', '#8b2fff', '#ff7a1a'];
const FONTS = ['Impact, system-ui, sans-serif', '"Playfair Display", Georgia, serif',
  '"JetBrains Mono", monospace', '"Baloo 2", Inter, sans-serif', '"Source Serif 4", Georgia, serif'];

export const AntiDesignChaos: React.FC<{title?: string; items?: string[]; tagline?: string}> = ({
  title: TITLE = 'RULES?', items: ITEMS = ['no grid', 'more!', 'why not', 'LOUD', 'oops', 'yes.'],
  tagline: TAG = 'break it on purpose'} = {}) => {
  const dna = useDNA();
  const GROUND = dna?.bg ?? GROUND0;
  const POP = dnaPalette(dna, 6) ?? POP0;
  const HEAD = dna?.fg ?? '#111';
  const CHIP_BG = dna?.fg ?? '#111', CHIP_FG = dna?.bg ?? GROUND0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const bg = seg(t, 0, 0.12) > 0.5 || t > 0.12;
  const TITLE_W = Math.round(W * 0.9);
  const TILT = Math.sin(6 * Math.PI / 180);
  const titlePx = fitBlockPx(TITLE, TITLE_W,
    Math.max(80, (contentBottom(W, H) - CONTENT_TOP) - Math.round(TILT * TITLE_W)), 300,
    {usable: 1, leading: leading(TITLE, 0.9)});
  return (
    <AbsoluteFill style={{background: GROUND, overflow: 'hidden'}}>
      {/* sticker shapes scattered */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(9)].map((_, i) => {
          const x = 120 + hash01(i * 3.1) * (W - 240), y = 120 + hash01(i * 7.7) * (H - 240);
          const s = clamp01(seg(t, 0.1 + i * 0.05, 0.34 + i * 0.05));
          const col = POP[i % POP.length];
          // @cycles: nine unlabelled sticker shapes; which of three outlines a sticker takes says nothing about any item
          const kind = i % 3;
          const rot = (hash01(i * 5) - 0.5) * 40;
          return (
            <g key={i} transform={`translate(${x} ${y}) rotate(${rot * s}) scale(${easeOutBack(s)})`} opacity={s}>
              {kind === 0 && <path d="M0,-46 L13,-14 46,-14 19,7 29,40 0,20 -29,40 -19,7 -46,-14 -13,-14 Z" fill={col} />}
              {kind === 1 && <circle r={40} fill="none" stroke={col} strokeWidth={12} />}
              {kind === 2 && <rect x={-42} y={-42} width={84} height={84} fill={col} transform="rotate(12)" />}
            </g>
          );
        })}
        {/* hand-drawn arrows / scribbles */}
        {[...Array(4)].map((_, i) => {
          const x = 200 + hash01(i * 9.3) * (W - 500), y = 200 + hash01(i * 4.1) * (H - 400);
          const on = clamp01(seg(t, 0.3 + i * 0.08, 0.6 + i * 0.08));
          const col = POP[(i + 2) % POP.length];
          return <path key={'a' + i} d={`M${x} ${y} q 80 -60 150 -10 t 120 20`} fill="none" stroke={col}
            strokeWidth={9} strokeLinecap="round" {...drawOn(on)}
            transform={`rotate(${(hash01(i) - 0.5) * 50} ${x} ${y})`} />;
        })}
      </svg>

      {/* scattered mismatched words */}
      {ITEMS.map((w, i) => {
        const sz0 = 60 + hash01(i * 3.7) * 90;
        // THE SCATTER IS RANDOM, ITS WIDTH IS NOT. The size came out of a hash and the words are `nowrap`,
        // so a long Chinese word at 149px simply ran off the right edge — 801px past it at 1:1. Chaos is
        // the point of this register; a word half outside the frame is not chaos, it is a clipped word.
        // The size is fitted to the frame first, then the random x is clamped so the whole word lands.
        const MARGIN = 60;
        const sz = Math.min(sz0, fitTextPx(w, W - MARGIN * 2, sz0, {usable: 1}));
        // THE SCATTER IS RANDOM, ITS BOX IS NOT. `H - 420` was the whole frame minus a 16:9 margin, so a
        // word could land anywhere down to H-240 — 77px of 'no grid' inside the caption band at 1:1. Chaos
        // is the point of this register; drawing under the subtitle is not.
        const x0 = 160 + hash01(i * 2.3 + 1) * (W - 520);
        const x = Math.max(MARGIN, Math.min(x0, W - MARGIN - textWidthPx(w, sz)));
        const yBot = Math.max(180, contentBottom(W, H) - inkBlockH(sz));
        const y = 180 + hash01(i * 8.1 + 2) * Math.max(0, Math.min(H - 420, yBot - 180));
        const pop = easeOutBack(clamp01(seg(t, 0.16 + i * 0.07, 0.4 + i * 0.07)));
        const rot = (hash01(i * 6.6) - 0.5) * 44;
        const col = POP[(i + 1) % POP.length];
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, opacity: clamp01(pop * 1.4),
            transform: `rotate(${rot * pop}deg) scale(${pop})`, color: col,
            fontFamily: FONTS[i % FONTS.length], fontWeight: 900, fontSize: sz, lineHeight: leading(w, 1),
            textShadow: '3px 3px 0 #00000022', whiteSpace: 'nowrap'}}>{w}</div>
        );
      })}

      {/* THE LOUD HEADLINE, TILTED — dead centre of the ZONE, not of the frame, and fitted to it. At a flat
          300px a Chinese title is wider than any frame here and taller than the room above the caption
          band: 280px of it drew inside the band at 1:1. The tilt is part of the fit, not an afterthought —
          a -6° rotation adds sin(6°) of the block's WIDTH to its height, which is 113px on a 1080 frame. */}
      <AbsoluteFill style={{top: CONTENT_TOP, height: Math.max(120, contentBottom(W, H) - CONTENT_TOP),
        display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{transform: `rotate(-6deg) scale(${easeOutBack(clamp01(seg(t, 0.3, 0.56)))})`, maxWidth: TITLE_W,
          // `balance` even here. The register breaks rules on PURPOSE, and a single glyph stranded on its
          // own line is not one of the rules it breaks — at this size it reads as the title having been
          // cut off, which is the one thing a display line may not look like. Chinese breaks between any
          // two glyphs, so an 8-glyph title a unit too wide for the box does exactly that.
          textWrap: 'balance',
          fontFamily: 'var(--f-display, Impact, system-ui, sans-serif)', fontSize: titlePx, lineHeight: leading(TITLE, 0.9), color: HEAD,
          WebkitTextStroke: `6px ${POP[0]}`, letterSpacing: '-0.02em',
          textShadow: `12px 12px 0 ${POP[2]}`}}>{TITLE}</div>
      </AbsoluteFill>

      <div style={{position: 'absolute', left: 60, bottom: bottomInset(W, H, 54), opacity: easeOutCubic(seg(t, 0.7, 0.9)),
        transform: 'rotate(-3deg)', background: CHIP_BG, color: CHIP_FG, padding: '10px 22px',
        font: '800 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.1em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default AntiDesignChaos;
