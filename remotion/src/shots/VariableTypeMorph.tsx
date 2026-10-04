// SHOT · Variable Type Morph — one enormous word ALIVE on its type axes: a wave of WEIGHT (thin→black) travels
// across the letters while the whole word breathes on the WIDTH axis (condensed→expanded), each glyph
// overshooting into place over a drifting duotone field. The "type as a living material" register — bold,
// expressive typography beyond a static title (family J · experimental type). Deterministic (axes = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, shade} from '../runtime/dna';
import {onLight} from '../runtime/light';
import {fitTextPx} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#08080f';

export const VariableTypeMorph: React.FC<{word?: string; kicker?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  word: WORD = 'EXPRESSIVE', kicker: KICKER = 'type, alive', tagline: TAG = 'weight · width · in motion',
  accent: accIn, accent2: acc2In} = {}) => {
  const dna = useDNA();
  // THE ENORMOUS WORD IS THE FRAME'S ONLY INK, and its colour was a pair of literals that no film could
  // reach: a themed film got this register's pink→blue whatever palette it had declared, and a film grounded
  // warm white got that pair drawn ON warm white (#5b8cff measures 2.86:1 there, under the 3:1 a display
  // mark needs). What the film passes still wins; then the film's own accents; then the original pair.
  const ACC = accIn ?? dna?.accent ?? '#ff5b7f';
  const ACC2 = acc2In ?? dna?.accent2 ?? '#5b8cff';
  const BG = dna?.bg ?? BG_D0;
  // ...AND THE DROP IS SEPARATION FROM THE GROUND, NOT A CONSTANT BLACK. `#000a` blurred 60px hugs every
  // glyph; on this library's near-black grounds it is invisible, and on paper it is a dark smear pressed
  // against the one word on the frame. Measured, the word's own interior reads at 4.06:1 on warm white while
  // the gate still reported 90% of the marks under 3:1 — because the marks it can see are the glyph EDGES,
  // and what sat behind them was this halo rather than the page. A shade of the ground on a light key.
  const DROP = dna && onLight(dna) ? `0 14px 40px ${shade(dna.bg, 0.12)}` : '0 20px 60px #000a';
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  // THE ENORMOUS WORD IS FITTED TO THE FRAME. 210px is one enormous word on a 1920-wide frame in a narrow
  // grotesque; under the EDITORIAL DNA's serif on a 1080-wide frame 'EXPRESSIVE' was sliced at BOTH edges —
  // the first E and the last E each cut in half. The type gate never saw it because it sweeps one DNA, and
  // the DNA is what chooses the face and therefore the width.
  // The word is a flex ROW that cannot wrap, and each glyph breathes on the WIDTH axis out to 1.12, so the
  // fit is given the width the widest moment of that breath needs — not the resting width.
  const WIDTH_AXIS_MAX = 1.12;
  const wordPx = Math.min(210, fitTextPx(WORD, (W * 0.94) / WIDTH_AXIS_MAX, 210, {usable: 1, track: -0.02}));
  const letters = WORD.split('');
  const n = letters.length;
  const fieldX = lerp(-0.2, 0.2, easeInOutCubic(t)) * W;
  const kickIn = easeOutCubic(seg(t, 0.04, 0.2));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center'}}>
      {/* drifting duotone field */}
      <div style={{position: 'absolute', inset: '-20%', filter: 'blur(80px)', opacity: 0.5,
        transform: `translateX(${fieldX}px)`,
        background: `radial-gradient(50% 60% at 30% 40%, ${ACC}, #0000 60%), radial-gradient(50% 60% at 72% 60%, ${ACC2}, #0000 60%)`}} />

      <div style={{opacity: kickIn, transform: glide(`translateY(${(1 - kickIn) * 12}px)`, kickIn !== 1), color: dna?.dim ?? '#c7cee0',
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.5em', textTransform: 'uppercase',
        paddingLeft: '0.5em', marginBottom: 40, zIndex: 2}}>{KICKER}</div>

      <div style={{display: 'flex', alignItems: 'baseline', zIndex: 2}}>
        {letters.map((ch, i) => {
          const st = 0.12 + i * (0.4 / Math.max(1, n));
          const entr = easeOutBack(clamp01(seg(t, st, st + 0.3)));       // rise + thicken in
          // a weight wave that keeps travelling after entrance
          const wave = 0.5 + 0.5 * Math.sin(t * 4 - i * 0.6);
          const weight = Math.round(lerp(140, 900, clamp01(entr * 0.6 + wave * 0.5)));
          const widthAxis = lerp(0.66, 1.06 + 0.06 * Math.sin(t * 3 - i * 0.5), entr); // condensed→expanded breath
          const rise = (1 - entr) * 80;
          const hue = i / Math.max(1, n - 1);
          return (
            // THE WAVE NEVER STOPS — the word is "alive" by design (see the header): once `entr` settles,
            // `widthAxis` keeps breathing on `sin(t*3 - i*0.5)` for the rest of the shot, so every glyph's
            // scaleX is in motion for the WHOLE beat, not just its own entrance.
            <span key={i} style={{display: 'inline-block', opacity: clamp01(entr * 1.4),
              transform: glide(`translateY(${rise}px) scaleX(${widthAxis}) scaleY(${lerp(0.8, 1, entr)})`, true),
              transformOrigin: 'center bottom',
              fontFamily: 'var(--f-display, Inter, system-ui, sans-serif)', fontWeight: weight,
              fontSize: wordPx, lineHeight: 0.9, letterSpacing: '-0.02em',
              color: `color-mix(in oklab, ${ACC} ${Math.round((1 - hue) * 100)}%, ${ACC2})`,
              // enhancement if a variable font is present (harmless otherwise)
              fontVariationSettings: `"wght" ${weight}, "wdth" ${Math.round(widthAxis * 100)}`,
              textShadow: DROP} as React.CSSProperties}>{ch}</span>
          );
        })}
      </div>

      <div style={{opacity: tagIn, transform: glide(`translateY(${(1 - tagIn) * 10}px)`, tagIn !== 1), marginTop: 44, color: dna?.dim ?? '#8b93a8',
        font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.24em', textTransform: 'uppercase', zIndex: 2}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default VariableTypeMorph;
