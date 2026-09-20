// SHOT · Ridge Field — stacked ridgeline curves (the "Unknown Pleasures" plot): rows of peaked lines, each
// filled to occlude the ones behind, rippling as a wave passes through, revealing bottom-up. Iconic
// generative data-landscape (family K · generative). Deterministic (ridge height = summed sines of x/row/t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, shade} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {bottomInset} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#07060d';
const POOL_D0 = '#0d1030';     // the lit core of the ground — a LIFT off this register's own night
const ROWS = 28, SAMP = 72;

export const RidgeField: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Signals', tagline: TAG = 'patterns in the noise', accent: ACC0 = '#8de0ff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // A FILM CAN GROUND ON PAPER. A ridgeline plot is a FORM — it is published black-on-white in every journal
  // that prints one — so it takes the film's ground and its ink like any other drawing. Its stroke was a pale
  // cyan picked against near-black and measured 1.77:1 on warm white with 82% of the register's marks under
  // the floor: 28 rows of curves that are all there and none of which can be seen. On a light ground the
  // stroke is walked along its own black-to-white axis until it clears the floor (`groundFrom`: exposure only,
  // hue kept), so a film that passes its own `accent` keeps that hue. Null DNA and the eight presets are dark
  // and never reach this.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  // Exposed to the INK floor, not the graphics one: the ridgelines ARE the content, and 3.0 is also the exact
  // ratio the ink gate fails at, so a colour solved to 3.00 lands on the wrong side of it as soon as the
  // ground behind a mark is sampled locally rather than as the flat page.
  const ACC = lit && dna ? groundFrom(dna, {bg: dna.bg, fg: ACC0}).fg : ACC0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const left = 260, right = W - 260, top = 190, rowGap = (H - 360) / ROWS;
  const height = (x: number, r: number) => {
    const cxn = (x - (left + right) / 2) / ((right - left) / 2);   // -1..1 across width
    const env = Math.exp(-cxn * cxn * 3);                          // peak toward centre
    const wave = Math.sin(x * 0.02 + r * 0.5 - t * 5) + 0.6 * Math.sin(x * 0.05 - r * 0.9 + t * 3);
    const ripple = 0.6 + 0.4 * Math.sin(r * 0.6 - t * 6);
    return env * (60 + 120 * ((wave + 1.6) / 3.2)) * ripple;
  };
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  return (
    // the ground's lit core follows the film's own paper when the film grounds on paper; the literal is a
    // near-black pool, which on a light film is a hole behind the ridgelines
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, ${lit ? shade(BG, 0.06) : POOL_D0}, ${BG} 78%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(ROWS)].map((_, r) => {
          const yBase = top + r * rowGap;
          const appear = clamp01(seg(t, 0.02 + (1 - r / ROWS) * 0.4, 0.24 + (1 - r / ROWS) * 0.4));
          if (appear <= 0) return null;
          let d = `M${left} ${yBase + 4}`;
          for (let s = 0; s <= SAMP; s++) {
            const x = lerp(left, right, s / SAMP);
            const y = yBase - height(x, r) * appear;
            d += ` L${x.toFixed(1)} ${y.toFixed(1)}`;
          }
          d += ` L${right} ${yBase + 4} Z`;
          const depth = r / ROWS;
          // The near rows' glow is a DARK-GROUND DEVICE. On paper it is a halo of the stroke's own colour, so
          // the stroke is read against itself and its edge dissolves into it.
          // ...AND ALPHA IS NOT THE SAME GESTURE ON THE TWO GROUNDS. The far rows are painted at 35% so they
          // recede: against night that composites them toward black and they stay lines, against paper it
          // dilutes them toward white and they stop being lines at all, however well the stroke's colour was
          // solved (measured 39% of this register's marks under the floor — the widest margin of the seventeen).
          // So on a light ground the ramp keeps its direction and lifts its floor: the back of the field still
          // recedes from the front, it just recedes in TONE rather than into the page.
          return <path key={r} d={d} fill={BG} stroke={ACC} strokeWidth={2}
            opacity={lit ? lerp(0.62, 1, depth) : lerp(0.35, 1, depth)}
            style={{filter: depth > 0.6 && !lit ? `drop-shadow(0 0 4px ${ACC})` : undefined}} />;
        })}
      </svg>
      {/* the title and its kicker sit on the ground, so they are the film's ink and its metadata; the
          separation shadow is the ground's own colour on paper, never a fixed black under near-black type */}
      <div style={{position: 'absolute', top: 74, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: dna?.fg ?? '#fff', font: '800 92px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.02em',
        textShadow: `0 8px 40px ${lit ? BG : '#000'}`}}>{TITLE}</div>
      <div style={{position: 'absolute', bottom: bottomInset(W, H, 90), left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.62, 0.84)), color: dna?.dim ?? '#9fb2d0',
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default RidgeField;
