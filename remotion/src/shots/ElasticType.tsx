// SHOT · Elastic Type — jelly letters DROP in and jiggle with a damped elastic squash-stretch, then keep a
// soft gummy wobble, over a bright playful ground. The 2026 elastic/liquid-typography trend as a 2D gummy
// bounce (family P · dimensional type). Deterministic (elastic = damped sine of localT).
//
// EVERY CHARACTER OF THE WORD LANDS. Character i used to start falling at `0.06 + i * 0.08` — a fixed step
// per character — so the length of the word decided whether it was ever spelled: the eleventh and twelfth
// characters were still in the air on the last frame and the thirteenth onward started after the clip had
// ended. A film that wrote a thirteen-character phrase printed its first ten and nothing said so. The step is
// now laid out for the word — 0.08 stays the upper bound, so a short word keeps its exact rhythm and render —
// and shrinks until the last character has landed by LAND_BY, just before the frame `useT` calls settled.
// Past MAX_ELASTIC_CHARS the word is no longer a word this register can set big (the width fit would shrink
// it toward body size), so it refuses rather than printing a line of confetti.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, REDUCED_MOTION_T} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {fitTextPx} from '../runtime/layout';

export const DURATION = 145; // ~4.8s
const BG_D0 = '#141a2e';
const TONES0 = ['#ff5b7f', '#5b8cff', '#37d4a6', '#f6a531', '#c07bff'];
export const MAX_ELASTIC_CHARS = 16;
// Character i starts dropping at DROP_START + i * step and has landed DROP_DUR later. DROP_STEP is the
// original per-character gap and only an upper bound; the real step is derived from the word's length.
const DROP_START = 0.06, DROP_STEP = 0.08, DROP_DUR = 0.18;
const LAND_BY = REDUCED_MOTION_T - 0.02;

export const ElasticType: React.FC<{word?: string; tagline?: string}> = ({
  word: WORD = 'BOUNCE', tagline: TAG = 'springy, gummy, alive'} = {}) => {
  // One element per CHARACTER (code point, so an astral glyph is not split into two halves).
  const letters = [...String(WORD ?? '')];
  if (!String(WORD ?? '').trim() || letters.length > MAX_ELASTIC_CHARS) {
    throw new Error(
      `ElasticType needs a \`word\` of 1-${MAX_ELASTIC_CHARS} characters, spaces included (got ` +
      `${String(WORD ?? '').trim() ? letters.length : 'no visible character'}). ` +
      'Each character drops in on its own beat and must have landed before the settled frame, and the word ' +
      'is set on one line at display size; a longer phrase belongs in a headline or kinetic-type register.');
  }
  const n = letters.length;
  const step = n > 1 ? Math.min(DROP_STEP, (LAND_BY - DROP_START - DROP_DUR) / (n - 1)) : DROP_STEP;
  const dna = useDNA();
  const TONES = dnaPalette(dna, 5) ?? TONES0;   // derive the palette from the film's DNA (null DNA = the original)
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // THE WORD IS FITTED TO THE FRAME — see InflateType for the same defect in the same shape. 230px holds
  // 'BOUNCE' at 1920; an eight-glyph Chinese phrase was cut 412px each side at 1:1. The jelly squash pushes
  // each glyph out to 1.18 of its width at the moment of impact, which is the width that has to fit.
  const GLYPH_MARGIN = 8, SX_MAX = 1.18;
  const wordPx = Math.min(230, fitTextPx(WORD,
    Math.max(60, (W * 0.94) / SX_MAX - n * GLYPH_MARGIN), 230, {usable: 1}));
  const tagIn = easeOutCubic(seg(t, 0.66, 0.86));
  return (
    // THE LIFT IN THE GROUND IS THE FILM'S TOO. `radial-gradient(…, #1c2647, ${BG})` followed the DNA only at
    // its OUTER stop, so a film grounded warm white got a navy well in the middle of the frame — a murk, on a
    // register whose whole identity is a bright playful ground. The film's own treatment first, then its flat
    // ground, and only an un-themed film draws the original two-stop well.
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg
        ?? `radial-gradient(120% 100% at 50% 40%, #1c2647, ${BG_D0} 74%)`, overflow: 'hidden',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', alignItems: 'flex-end'}}>
        {letters.map((ch, i) => {
          if (ch === ' ') return <div key={i} style={{width: 56}} />;
          const st = DROP_START + i * step;
          const local = clamp01(seg(t, st, 1));
          const drop = easeOutCubic(clamp01(seg(t, st, st + DROP_DUR)));
          // damped elastic squash-stretch after impact
          const impact = clamp01((t - (st + 0.16)) * 6);
          const decay = Math.exp(-(t - st) * 4);
          const jelly = impact > 0 ? Math.sin((t - st) * 22) * 0.22 * decay : 0;
          const settleWob = 0.03 * Math.sin(t * 5 - i * 0.7) * clamp01(local * 2);
          const sy = 1 - jelly + settleWob;
          const sx = 1 + jelly * 0.8 - settleWob;
          const tone = TONES[i % TONES.length];
          return (
            <div key={i} style={{opacity: clamp01(drop * 1.5),
              transform: `translateY(${(1 - drop) * -220}px) scale(${sx}, ${sy})`, transformOrigin: 'center bottom',
              margin: '0 4px', fontFamily: 'var(--f-display, "Baloo 2", Inter, system-ui, sans-serif)', fontWeight: 900,
              fontSize: wordPx, lineHeight: 1, color: tone,
              textShadow: `0 10px 0 rgba(0,0,0,.16), 0 26px 40px rgba(0,0,0,.4)`}}>{ch}</div>
          );
        })}
      </div>
      <div style={{opacity: tagIn, transform: `translateY(${(1 - tagIn) * 12}px)`, marginTop: 48, color: dna?.dim ?? '#c7d0ee',
        font: '700 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.24em', textTransform: 'uppercase'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default ElasticType;
