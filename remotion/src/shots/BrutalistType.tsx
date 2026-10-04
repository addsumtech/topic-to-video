// SHOT · Brutalist Type — a raw brutalist-editorial register: stark off-white/black + one hot accent, oversized
// grotesque type in hard-edged boxes, mono metadata, harsh rules, and a brief RGB-glitch jolt. Aggressive,
// anti-slick — the opposite pole from the refined SwissEditorial. Deterministic (glitch pulse = fn of frame).
//
// THE FOLIO IN THE ACCENT BLOCK IS THE FILM'S, OR THERE IS NONE. The block carried a literal `01/03` — a
// page counter saying "this is the first of three". On a film that is a claim about the beat's place in a
// sequence, and no film had made it: a single statement shipped as part one of a series that did not exist,
// and every beat that used the register was "01" of the same "03". It is `counter` now, with NO default:
// a film that numbers its parts passes the folio ('02/05'), and one that doesn't gets the bare hot block,
// which is the brutalist form on its own. It is not defaulted to the old text because that default could
// not be seen — the demo-copy gate reads a default by its Latin words and '01/03' has none, so a film that
// omitted it would have printed the fake folio without a word from any check.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {leading} from '../runtime/cjkType';
import {useT, seg, lerp, clamp01, easeOutExpo} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {captionBand, fitTextPx, wrapLines} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#ececec', INK_D0 = '#0a0a0a', ACC_D0 = '#ff3b00';

export const BrutalistType: React.FC<{titleTop?: string; titleBottom?: string; meta?: string; statement1?: string; statement2?: string;
  counter?: string}> = ({
  titleTop = 'WORK', titleBottom = 'BUDDY.', meta = 'WORKBUDDY / LOCAL-FIRST', statement1 = 'NO CLOUD.', statement2 = 'NO NONSENSE.',
  counter} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0, INK = dna?.fg ?? INK_D0, ACC = dna?.accent ?? ACC_D0;
  const t = useT();
  const glide = useGlide();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  // glitch jolts at two moments
  const g1 = clamp01(1 - Math.abs(t - 0.42) / 0.05), g2 = clamp01(1 - Math.abs(t - 0.72) / 0.04);
  const glitch = Math.max(g1, g2);
  const shift = glitch * (8 + (frame % 3) * 6);
  const slice = glitch > 0.3;
  const rise = easeOutExpo(seg(t, 0.06, 0.4));

  const BAND = captionBand(W, H);
  // the folio sits inside the 260px accent block (10px in from its right edge), so it is fitted to that width
  // at the original 46px; '01/03' is 5 mono cells and keeps 46px exactly
  const folio = String(counter ?? '').trim();
  const folioPx = Math.min(46, fitTextPx(folio, 230, 46, {usable: 1, adv: 0.62, cjk: 1.24}));
  // THE HEADLINE IS SIZED FROM THE ROOM IT HAS, not fixed at 300px. Two lines at 300px/0.82 stand 492px
  // tall; the space between the top rule and the statement is whatever the caption band leaves, and once
  // the band grew that space fell below what the type needed — so "1674" descended straight through
  // "A TORNADO CAME THROUGH THE CITY" and beat 23 of a delivered film shipped as an unreadable blot.
  // Constraining the BOX did not help: a box does not shrink its text. The size does.
  // The divisor is 2 lines x 0.82 leading PLUS the ink that overflows the line box. A display face set at
  // 0.82 line-height has a natural line box nearer 1.2, so roughly 0.2em of each glyph hangs outside the
  // box the layout reserves — sizing on 2*0.82 alone left the block ending 13px above the statement and
  // the ink still crossing it. 1.88 is 2*0.82 + 0.24, measured against the rendered frame.
  // THE STATEMENT'S HEIGHT IS MEASURED, NOT ASSUMED. The derivation above reserves the headline's room from
  // where the statement STARTS — which is only correct while the statement is one line. Its demo copy is
  // ("NO CLOUD." / "NO NONSENSE."), and a Chinese sentence of ordinary length wraps to three lines that grow
  // UPWARD from a bottom-anchored box, straight back through the headline this derivation just protected.
  // So the statement is fitted to the width it has, and the lines it then needs are what the headline
  // subtracts. Latin copy is unchanged: a short phrase still fits on one line at 54px.
  // ...AND THE LINES ARE COUNTED, NOT GUESSED FROM WHETHER THE FIT MOVED. This asked whether `fitTextPx`
  // had returned its base size and answered 1 line if so and 2 otherwise — a binary guess capped at two,
  // in the same derivation whose own comment above says a Chinese sentence "wraps to THREE lines". At three
  // the reserve was short by a line, `headRoom` came out too generous, and the headline it protects ran
  // 210px into the caption band at 1:1. `wrapLines` breaks the string the way the browser does.
  const stateMeasure = W - 192;
  const stateSize = fitTextPx(`${statement1} ${statement2}`, stateMeasure, 54, {usable: 1.0});
  const stateLines = wrapLines(`${statement1} ${statement2}`, stateSize, stateMeasure);
  const stateH = Math.ceil(stateSize * leading([statement1, statement2], 1) * stateLines);
  const headTop = 300, headGap = 24;
  const headRoom = Math.max(80, (H - (BAND + 52 + stateH)) - headTop - headGap);
  // THE HEADLINE IS SIZED BY ITS WIDTH AS WELL AS ITS ROOM. Everything above derives the size from the
  // vertical space and nothing asked how WIDE the words are — correct for the demo copy ("WORK" / "BUDDY.")
  // and wrong for anything longer: a six-glyph Chinese title at 230px wants 1380px and the box is 880, so
  // each of the two lines wrapped to two and the stack came out at four. That is why it ran 476px into the
  // caption band, and why counting the statement's lines correctly made it WORSE rather than better —
  // the derivation it feeds was never the binding constraint.
  const headBoxW = W - 200;
  const headFitW = Math.min(fitTextPx(titleTop, headBoxW, 300, {usable: 1}),
                            fitTextPx(titleBottom, headBoxW, 300, {usable: 1}));
  // ...and the divisor carries the REAL leading. 1.88 is 2 lines x 0.82 + 0.24 of ink overflow, and 0.82 is
  // the Latin stack — `leading()` raises the floor to 1.06 the moment the copy is CJK, so the block stood
  // 13% taller than the number that reserved it. Latin still divides by exactly 1.88.
  const headLead = leading([titleTop, titleBottom], 0.82);
  const headSize = Math.min(300, Math.floor(headRoom / (2 * headLead + 0.24)), headFitW);

  const Head: React.FC<{color: string; dx: number; blend?: string}> = ({color, dx, blend}) => (
    <div style={{position: 'absolute', inset: 0, transform: `translateX(${dx}px)`, color, mixBlendMode: (blend as any) || 'normal',
      // 0.82 is the point of a brutalist stack IN LATIN — capitals have no descenders, so the lines close
      // up and nothing touches. CJK glyphs fill their em box, so the same 0.82 laid these two title blocks
      // straight into each other on a real Chinese film. `leading` raises the floor only when the copy is
      // actually CJK, so the Latin stack renders byte-for-byte as before.
      font: `900 ${headSize}px/${leading([titleTop, titleBottom], 0.82)} var(--f-display, "Archivo", "Helvetica Neue", Arial Narrow, sans-serif)`, letterSpacing: '-0.03em'}}>
      {titleTop}<br />{titleBottom}
    </div>
  );

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* hard rules + accent block */}
      <div style={{position: 'absolute', left: 90, right: 90, top: 150, height: 8, background: INK}} />
      {/* The lower rule and the statement below used to be pinned at bottom:150 / bottom:176 — literal pixels
          that happened to clear the burned caption while the reserved band was 150px, and sat straight inside
          it the moment the band grew. They are measured from the BAND now, so the statement stays out of the
          subtitle at any caption size and any aspect. */}
      <div style={{position: 'absolute', left: 90, right: 90, bottom: BAND + 26, height: 8, background: INK}} />
      <div style={{position: 'absolute', right: 90, top: 158, width: 260, height: 120, background: ACC}} />

      {/* metadata */}
      <div style={{position: 'absolute', left: 96, top: 100, color: INK, font: '800 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.02em'}}>{meta}</div>
      {folio ? <div style={{position: 'absolute', right: 100, top: 186, color: BG, whiteSpace: 'pre',
        font: `800 ${folioPx}px/1 var(--f-mono, "JetBrains Mono", monospace)`}}>{folio}</div> : null}

      {/* headline (RGB-glitch stack) */}
      {/* The headline box ENDS where the statement begins. It was a fixed 720px tall from y=300 — which
          reached y=1020, straight through the statement line. That was tolerable while the statement sat at
          bottom:176; raising it to clear the grown caption band moved it to y≈801, into the middle of the
          headline's own glyphs, and beat 23 of a delivered film became an unreadable blot of "1674" over
          "A TORNADO CAME". Derived from the statement's position, so the two cannot collide again. */}
      <div style={{position: 'absolute', left: 96, top: headTop, width: W - 200, height: headRoom,
        transform: glide(`translateY(${(1 - rise) * 60}px)`, rise !== 1), opacity: rise}}>
        {glitch > 0.1 && <Head color="#ff004c" dx={-shift} blend="multiply" />}
        {glitch > 0.1 && <Head color="#00e5ff" dx={shift} blend="multiply" />}
        <Head color={INK} dx={0} />
        {/* glitch slice bars */}
        {slice && [0.2, 0.55, 0.8].map((yy, i) => (
          <div key={i} style={{position: 'absolute', left: -shift * 2, top: `${yy * 100}%`, width: '70%', height: 26, background: BG,
            transform: `translateX(${(i % 2 ? 1 : -1) * shift * 3}px)`}} />
        ))}
      </div>

      {/* statement */}
      <div style={{position: 'absolute', left: 96, right: 96, bottom: BAND + 52, color: INK, font: `800 ${stateSize}px/${leading([statement1, statement2], 1)} var(--f-body, "Archivo", Arial, sans-serif)`, letterSpacing: '-0.01em'}}>
        {statement1} <span style={{background: INK, color: BG, padding: '0 12px'}}>{statement2}</span>
      </div>
    </AbsoluteFill>
  );
};
export default BrutalistType;
