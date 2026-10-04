// SHOT · Cloth Wave — a silk flag ripples: horizontal fabric strips undulate on a travelling wave, shaded by
// the wave slope for a sheen, and the wordmark rides the ripple (each letter offset by the local wave). A
// tactile textile register (family Z · fabric). Deterministic (wave = summed sines of x + t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, contrastOf, mix, readableOnAll} from '../runtime/dna';
import {ACCENT_CONTRAST_MIN, onLight} from '../runtime/light';
import {bottomInset} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0c0f1a';
// The lift at the middle of the ground. A literal dark stop over the film's own `bg`, which on a light film
// is not a lift at all — it paints a grey blob across the middle of the paper, and it is what the cloth's
// top edge was being measured against.
const LIFT_D0 = '#161a30';
const SILK_D0 = '#4d7cff', SILK2_D0 = '#b44dff';
const TITLE_D0 = '#fff', TAG_D0 = '#c7d0ee';
// THE SHEEN'S CEILING. `brightness()` past 1 walks the silk toward white: on a night ground that is the
// highlight rolling over the fabric, and on paper it is the cloth dissolving into the page — measured by
// `ink_contrast_qa`, the register's largest failing region (0.36% of the frame, its whole reported hole)
// was the lit top edge of the flag against the ground, not any word on it. On a light film the sheen
// modulates DOWN from the silk's own colour instead of up past it.
const SHEEN_LO = 0.55, SHEEN_HI_D0 = 1.35;
const STRIPS = 30;

export const ClothWave: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'Flow', tagline: TAG = 'soft power, in motion', accent: ACC = SILK_D0, accent2: ACC2 = SILK2_D0} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // THE SILK IS NOT RE-THEMED. It is this register's own blue-violet unless the film names the two hues
  // itself, and neither end of it is near the ground on any film — the measured hole was the LIT edge, which
  // is the sheen's doing and is handled below, not the silk's colour.
  const lit = dna ? onLight(dna) : false;
  const SHEEN_HI = lit ? 1.0 : SHEEN_HI_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const left = 160, right = W - 160, top = H / 2 - 300, cloth = 600, stripH = cloth / STRIPS;
  const settle = easeOutCubic(seg(t, 0.04, 0.5));                 // wave amplitude eases in
  const wave = (x: number, r: number) => {
    const amp = 70 * settle;
    return Math.sin(x * 0.006 + t * 4 + r * 0.12) * amp + Math.sin(x * 0.013 - t * 3) * amp * 0.4;
  };
  const slope = (x: number, r: number) => (wave(x + 20, r) - wave(x - 20, r)) / 40; // for sheen
  const titleIn = easeOutCubic(seg(t, 0.4, 0.66));
  const letters = TITLE.split('');
  // The wordmark rides the SILK, never the ground, and white is right on this register's own silk on either
  // ground. It is KEPT while it clears the ink floor against both ends of the fabric and re-picked from the
  // film's own two inks only when a film hands the register a pale silk of its own — `readableOnAll`
  // maximises the WORST of the two ends, which is the only one a viewer sees.
  // The floor is the LARGE-TEXT one: this is 150px at weight 900, and white measures 3.72:1 and 3.86:1 on
  // the register's own two silks — kept, as it should be. At the body floor it would be re-picked to near
  // black on every film, which is a different register, not a repair.
  const titleInk = !dna || [ACC, ACC2].every((c) => contrastOf(TITLE_D0, c) >= ACCENT_CONTRAST_MIN)
    ? TITLE_D0 : readableOnAll([ACC, ACC2], dna.onAccent, dna.fg);
  // THE TAGLINE STRADDLES THE HEM. It is pinned to the caption band while the cloth's lower edge swings
  // through that row on the wave, so at any frame part of the line is on the silk and part is on the ground,
  // and no single ink serves both (they are opposite polarities by construction). It takes the ground's ink
  // and carries the GROUND'S OWN COLOUR as a stroke, which is invisible where the line is on the ground and
  // is what carves it out of the silk where it is not. On the light probe's own frame the half of this line
  // that had slipped off the hem was a pale blue-white lying on the ground, and it was flagged end to end.
  const tagInk = dna ? mix(dna.fg, dna.dim, 0.4) : TAG_D0;
  const tagCarve: React.CSSProperties = dna
    ? {WebkitTextStroke: `3px ${BG}`, paintOrder: 'stroke'} : {};
  return (
    // the lift in the middle of the ground is DERIVED from the film's own hue; the literal dark stop over
    // `bg` was a grey blob across the middle of the paper on a light film (see LIFT_D0)
    <AbsoluteFill style={{background:
      `radial-gradient(120% 100% at 50% 42%, ${dna ? mix(BG, dna.accent, 0.12) : LIFT_D0}, ${BG} 76%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><linearGradient id="silk" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor={ACC} /><stop offset="1" stopColor={ACC2} /></linearGradient></defs>
        {[...Array(STRIPS)].map((_, r) => {
          const yTop = top + r * stripH;
          const pts: string[] = [];
          for (let s = 0; s <= 40; s++) { const x = lerp(left, right, s / 40); pts.push(`${x.toFixed(1)} ${(yTop + wave(x, r)).toFixed(1)}`); }
          for (let s = 40; s >= 0; s--) { const x = lerp(left, right, s / 40); pts.push(`${x.toFixed(1)} ${(yTop + stripH + wave(x, r + 1)).toFixed(1)}`); }
          const sh = clamp01(0.5 + slope(cloth / 2 + left, r) * 1.2);  // sheen by slope
          return <path key={r} d={`M${pts.join(' L')} Z`} fill="url(#silk)" opacity={settle}
            style={{filter: `brightness(${lerp(SHEEN_LO, SHEEN_HI, sh)})`}} />;
        })}
      </svg>
      {/* wordmark riding the ripple */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{display: 'flex', opacity: titleIn}}>
          {letters.map((ch, i) => {
            const lx = left + cloth * 0.5 + (i - letters.length / 2) * 96;
            const dy = wave(lx, STRIPS * 0.4);
            // the ripple never stops (it is the register's whole point), so each letter carries the unlock for
            // the whole beat rather than a span that would have to end on motion that does not
            return <span key={i} style={{display: 'inline-block', transform: glide(`translateY(${dy}px)`, true),
              color: titleInk, font: '900 150px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
              // the drop stays literal: the wordmark is always ON the silk, so this shadow always falls on
              // fabric and never on the page, whichever way the film's ground goes
              textShadow: '0 8px 30px #000a'}}>{ch}</span>;
          })}
        </div>
      </AbsoluteFill>
      <div style={{position: 'absolute', bottom: bottomInset(W, H, 120), left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.62, 0.84)), color: tagInk, ...tagCarve,
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default ClothWave;
