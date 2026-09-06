// SHOT · Paper Slot — the same claim made of PAPER. A folded card is scored with slots, and each tool is a
// cut tag that drops into one. Tactility here is not depth, it is MATERIAL: matte stock, a real cut edge, the
// soft double shadow a card casts on a card, and the small imperfection of a tag that did not land perfectly
// straight.
//
// WHY THIS IS A DIFFERENT REPRESENTATION AND NOT A RESKIN OF THE 3D ONE. `PortWall` argues with SPACE — a
// machined part enters a machined socket, and you believe the fit because you watch the gap close under real
// light. This argues with the HAND: something was cut, and it goes in the slot, the way a luggage tag goes on
// a case. It reads warm and made rather than manufactured, and it says the connection is simple rather than
// engineered. Those are different claims about the same product, which is exactly what a representation
// choice is, and neither is a decoration of the other.
//
// Everything is drawn — no image, no texture file. The paper is a flat stock colour with a fibre wash and a
// darker cut edge; the shadow is two offset blurs, a tight contact one and a wide soft one, which is what
// makes a flat rectangle read as a thing lying on another thing.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useT, seg, clamp01, easeOutCubic, easeOutBack, lerp, hash01} from '../runtime/motion';

export const DURATION = 165; // 5.5s

const PAPER_D0 = '#efe9dd', INK_D0 = '#211d18', DIM_D0 = '#7d7466';

/** Relative luminance of a #rgb/#rrggbb — used only to ask whether a DNA's ground can pass for paper. */
function _lum(hex: string): number {
  const h = String(hex || '').replace('#', '');
  if (!/^[0-9a-fA-F]{3,8}$/.test(h)) return 0;
  const f = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6);
  const n = parseInt(f, 16);
  if (!isFinite(n)) return 0;
  return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
}
const TONES0 = ['#c2603f', '#3f7a63', '#c99a2e', '#6b5aa6', '#a8486a', '#3c7fa0'];

export const PaperSlot: React.FC<{hub?: string; items?: string[]; note?: string}> = ({
  hub: HUB = 'One slot', items: ITEMS = ['Docs', 'Chat', 'Mail', 'Calendar', 'Wiki', 'DB'], note: NOTE = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // A PAPER WORLD IS A LIGHT WORLD, and that is a constraint on the DNA rather than a preference.
  // `MagazineSpread` takes `dna.bg` outright, which is right for it because an editorial cover is whatever
  // stock the film is printed on. Here the whole argument is that something was CUT and DROPPED IN, and a
  // black sheet of paper says nothing of the kind — on a dark DNA the register would keep its form and lose
  // its meaning. So the film's ground is adopted when it is light enough to read as stock, and otherwise
  // this stays paper and only the INK follows the film. A register that quietly becomes unreadable under
  // half the presets is worse than one that declares which half it belongs to.
  const bg = dna?.bg ?? '';
  const PAPER = _lum(bg) > 0.55 ? bg : PAPER_D0;
  const onPaper = _lum(PAPER) > 0.5;
  const INK = onPaper && dna ? dna.fg : INK_D0;
  const DIM = onPaper && dna ? dna.dim : DIM_D0;
  const TONES = dnaPalette(dna, 6) ?? TONES0;
  const list = ITEMS.filter((x) => String(x ?? '').trim()).slice(0, 6);
  // A CARD WITH NO TAGS still composes — a clean sheet with a title under it — and says nothing at all.
  // That is the silent-wrong-output this library's evidence guard exists to end, so it throws instead.
  if (!list.length) {
    throw new Error(
      'PaperSlot needs at least one non-empty `items` entry. The whole form is things dropping into slots; ' +
      'with nothing to drop it draws an empty card, which composes and argues nothing.');
  }
  const n = list.length;

  const U = Math.min(W, H);
  const bottom = H - captionBand(W, H);
  const zoneH = bottom - CONTENT_TOP;
  const cardW = Math.round(W * 0.74), cardH = Math.round(zoneH * 0.52);
  const cardX = Math.round((W - cardW) / 2), cardY = Math.round(CONTENT_TOP + zoneH * 0.10);
  const tagW = Math.round(cardW / n * 0.80);
  // A TAG STAYS TAG-SHAPED. Sized off the card's height alone it became a tall column at 9:16 — the
  // same object, but reading as a strip of paper rather than a thing you hang on something.
  const tagH = Math.round(Math.min(cardH * 0.62, tagW * 2.05));
  // ONE SIZE FOR THE WHOLE SET. Fitted per label, six sibling tags printed at five different sizes,
  // which no set of tags ever is: the smallest that fits the longest label is the size they share.
  const labelPx = list.reduce(
    (px, txt) => Math.min(px, fitTextPx(txt, tagW - Math.round(U * 0.02), Math.round(U * 0.030),
      {usable: 1.05})), Math.round(U * 0.030));

  const titlePx = fitTextPx(HUB, W * 0.6, Math.round(U * 0.048), {usable: 1.0});
  const notePx = Math.round(U * 0.029);
  const copyBlockH = Math.round(titlePx * 1.6) + (NOTE ? Math.round(notePx * 1.5) : 0);
  const copyTop = Math.min(cardY + cardH + Math.round(U * 0.055),
                           bottom - copyBlockH - Math.round(U * 0.02));

  return (
    <AbsoluteFill style={{background: PAPER, overflow: 'hidden'}}>
      {/* the fibre of the stock: a faint, fixed-seed speckle, so the ground is a MATERIAL and not a fill */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        <filter id="ps-fibre"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width={W} height={H} filter="url(#ps-fibre)" opacity={0.05} />
      </svg>

      {/* THE CARD — scored, with a fold line down its length and a cut edge that catches the light */}
      <div style={{position: 'absolute', left: cardX, top: cardY, width: cardW, height: cardH,
        background: `linear-gradient(178deg, #f6f1e7, #e6dfd1)`, borderRadius: 3,
        boxShadow: `0 2px 3px #2a231a22, 0 26px 46px -18px #2a231a55`,
        transform: `rotate(-0.35deg)`, opacity: clamp01(seg(t, 0.0, 0.14))}}>
        {/* the score line: the fold the slots are cut along */}
        <div style={{position: 'absolute', left: 0, right: 0, top: '58%', height: 1,
          background: '#2a231a1f', boxShadow: '0 1px 0 #ffffffcc'}} />
        {list.map((_, i) => {
          const sx = Math.round((cardW / n) * (i + 0.5));
          return (
            <div key={i} style={{position: 'absolute', left: sx - tagW / 2, top: '58%', width: tagW, height: 5,
              marginTop: -2, background: '#2a231a', opacity: 0.5, borderRadius: 3,
              boxShadow: 'inset 0 2px 3px #00000055'}} />
          );
        })}
      </div>

      {/* THE TAGS — each cut, each dropped into its slot, each landing a hair off straight */}
      {list.map((text, i) => {
        const a = 0.10 + (i / n) * 0.42;
        const drop = easeOutBack(clamp01(seg(t, a, a + 0.26)));
        const sx = cardX + Math.round((cardW / n) * (i + 0.5));
        const restY = cardY + Math.round(cardH * 0.58) - tagH + Math.round(tagH * 0.30);
        // THE TAG MUST START INSIDE THE FRAME. At a 0.42-zone drop the entering tag was cut by the top
        // edge for the first third of the shot — invisible in the final still, obvious in motion.
        const startY = Math.max(CONTENT_TOP + Math.round(U * 0.01), restY - Math.round(zoneH * 0.30));
        const y = lerp(startY, restY, drop);
        const tilt = (hash01(i * 13 + 3) - 0.5) * 2.4;         // no two tags land at the same angle
        return (
          <div key={i} style={{position: 'absolute', left: sx - tagW / 2, top: y, width: tagW, height: tagH,
            opacity: clamp01(drop * 2),
            transform: `rotate(${tilt}deg)`, transformOrigin: '50% 90%'}}>
            {/* the tag: stock, a cut edge on the left, and the tone as a printed band at its head */}
            <div style={{position: 'absolute', inset: 0, borderRadius: 4,
              background: `linear-gradient(176deg, #fffdf8, #efe7d8)`,
              boxShadow: `0 1px 2px #2a231a33, 0 ${Math.round(10 * drop)}px ${Math.round(22 * drop)}px -8px #2a231a4d`}} />
            <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: 3,
              background: '#2a231a', opacity: 0.10}} />
            <div style={{position: 'absolute', left: '14%', right: '14%', top: '10%', height: Math.round(tagH * 0.055),
              background: TONES[i % TONES.length], borderRadius: 2, opacity: 0.9}} />
            {/* the punch hole, which is why a tag is a tag */}
            <div style={{position: 'absolute', left: '50%', top: `${18}%`, width: Math.round(tagW * 0.10),
              height: Math.round(tagW * 0.10), marginLeft: -Math.round(tagW * 0.05), borderRadius: '50%',
              background: PAPER, boxShadow: 'inset 0 1px 2px #2a231a55'}} />
            <div style={{position: 'absolute', left: '8%', right: '8%', top: '38%', color: INK,
              textAlign: 'center', textWrap: 'balance',
              font: `700 ${labelPx}px/${leading(text, 1.2)} var(--f-body, system-ui, sans-serif)`}}>{text}</div>
          </div>
        );
      })}

      {/* THE COPY BLOCK IS CLAMPED ABOVE THE CAPTION BAND. It hangs off the card's bottom edge, so any change
          to the card's height slides it down the frame — and the renderer burns the subtitle over the bottom
          band whatever is there. Pushed up until the last line clears it, the card can be re-proportioned
          freely and the copy still cannot land under the caption. */}
      <div style={{position: 'absolute', left: 0, right: 0, top: copyTop,
        textAlign: 'center', color: INK, opacity: clamp01(seg(t, 0.04, 0.20)), textWrap: 'balance',
        padding: `0 ${Math.round(W * 0.14)}px`,
        font: `800 ${titlePx}px/${leading(HUB, 1.1)} var(--f-display, system-ui, sans-serif)`}}>{HUB}</div>
      {NOTE ? (
        <div style={{position: 'absolute', left: 0, right: 0,
          top: copyTop + Math.round(titlePx * 1.6), textAlign: 'center',
          color: DIM, opacity: clamp01(seg(t, 0.66, 0.84)), textWrap: 'balance',
          padding: `0 ${Math.round(W * 0.16)}px`,
          font: `500 ${notePx}px/${leading(NOTE, 1.4)} var(--f-body, system-ui, sans-serif)`}}>
          {NOTE}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default PaperSlot;
