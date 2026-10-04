// SHOT · Low-Poly Form — a crystalline low-poly plane: a jittered triangle mesh assembles centre-out (each
// facet scaling + fading in from its centroid), colour graded across a duotone, with a wordmark settling over
// it. Faceted generative geometry (family K · generative). Deterministic (vertices jittered by hash, reveal by
// distance-from-centre).
//
// THE MESH IS FULL-BLEED, SO ITS EXPOSURE IS THE FRAME'S. Only the ground read the DNA — and the ground is
// the one thing a viewer never sees here, because a mesh at 0.92 opacity covers it. The duotone was a fixed
// blue→pink, the pool behind the type a fixed near-black and both type blooms `#000`, so a light film got its
// paper repainted as a mid-dark slab with a grey smudge over the middle: measured under a light probe
// (bg #f6f3ee) at sheet Y=0.328 / frame Y=0.282 (scripts/ink_contrast_qa.py). It is not a dark world — a
// crystal is a SURFACE, and a surface is lit by the room it is in — so the facets now carry the film's two
// hues, the pool and the blooms are the film's own ground, and the type is the film's ink.
//
// AND THE HUES ARE LIT FROM THE FILM'S GROUND ONLY ON A LIGHT FILM. On a dark film the accents ARE the
// crystal, at full strength, the way the original blue→pink was — a field brighter than the frame it sits on
// (#5b8cff and #ff5b9e carry relative luminance 0.28 and 0.31 against a 0.003 ground). On a light film they
// are not: there `groundFrom` darkens an accent until it clears 3:1 on paper, so a full-bleed pair of them is
// precisely the mid-dark slab above — the light probe's own accents sit at 0.14 and 0.15 under a 0.90 ground.
// Half way from the ground to the hue is still the hue (0.40 and 0.40 for that pair) and still the film's
// light. The pool then gives the type its own ground in either exposure, as the near-black one always did.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {onLight} from '../runtime/light';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#080a14';
// the originals, kept as the no-DNA rendering (byte-for-byte) and as the fallback chain
const ACC_D0 = '#5b8cff', ACC2_D0 = '#ff5b9e';
const INK_D0 = '#fff', TAG_D0 = '#c7d2e8';
const BLOOM_D0 = '#000';       // the type's separation bloom
const POOL_ALPHA = 0.8;        // was baked into the pool's `#080a14cc`
const FACET_MIX = 0.5;         // the facet sits half way from the ground to the hue — see the header
const GX = 11, GY = 7;

export const LowPolyForm: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'Faceted', tagline: TAG = 'many facets, one form', accent: ACC, accent2: ACC2} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // the film's hue, carried back toward its ground only where a full-strength accent would repaint the frame
  const hueOf = (tok?: string) => (tok && onLight(dna) ? mix(BG, tok, FACET_MIX) : tok);
  // a NAMED duotone still wins outright: a film that states the crystal's colours gets exactly those.
  const A1 = ACC ?? hueOf(dna?.accent) ?? ACC_D0;
  const A2 = ACC2 ?? hueOf(dna?.accent2) ?? ACC2_D0;
  // the type sits on the POOL, and the pool is the film's ground — so the ink that reads on it is the film's
  // own `fg`, which the DNA contract already measures against `bg` (4.5:1). The blooms are the same
  // substance as the pool: a `#000` bloom under dark type on paper is mud, not depth.
  const INK = dna?.fg ?? INK_D0;
  const TAG_INK = dna ? mix(dna.fg, dna.dim, 0.4) : TAG_D0;
  const BLOOM = dna?.bg ?? BLOOM_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const cellW = W / GX, cellH = H / GY;
  // jittered vertex grid (deterministic)
  const vert = (gx: number, gy: number) => {
    const edge = gx === 0 || gy === 0 || gx === GX || gy === GY;
    const jx = edge ? 0 : (hash01(gx * 13.1 + gy * 7.7) - 0.5) * cellW * 0.7;
    const jy = edge ? 0 : (hash01(gx * 5.3 + gy * 19.1) - 0.5) * cellH * 0.7;
    return [gx * cellW + jx, gy * cellH + jy] as [number, number];
  };
  const cx = W / 2, cy = H / 2;
  const maxD = Math.hypot(cx, cy);
  const tris: {pts: string; col: string; r: number}[] = [];
  for (let gx = 0; gx < GX; gx++) for (let gy = 0; gy < GY; gy++) {
    const a = vert(gx, gy), b = vert(gx + 1, gy), c = vert(gx + 1, gy + 1), d = vert(gx, gy + 1);
    const flip = (gx + gy) % 2 === 0;
    const t1 = flip ? [a, b, c] : [a, b, d], t2 = flip ? [a, c, d] : [b, c, d];
    for (const tri of [t1, t2]) {
      const mx = (tri[0][0] + tri[1][0] + tri[2][0]) / 3, my = (tri[0][1] + tri[1][1] + tri[2][1]) / 3;
      const dist = Math.hypot(mx - cx, my - cy) / maxD;
      const gh = clamp01(mx / W + (0.5 - my / H) * 0.4);
      const col = `color-mix(in oklab, ${A1} ${Math.round((1 - gh) * 100)}%, ${A2})`;
      tris.push({pts: tri.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' '), col, r: dist});
    }
  }
  const titleIn = easeOutCubic(seg(t, 0.52, 0.76));
  const tagIn = easeOutCubic(seg(t, 0.64, 0.86));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {tris.map((tr, i) => {
          const st = 0.04 + tr.r * 0.45;
          const e = easeOutBack(clamp01(seg(t, st, st + 0.26)));
          const bright = lerp(0.55, 1, clamp01(seg(t, st, st + 0.4)));
          // the crease between two facets is a SHADOW, not an ink — black at 13% alpha, so it darkens
          // whatever it is drawn over and stays a crease on a pale crystal as well as on a deep one
          return <polygon key={i} points={tr.pts} fill={tr.col} opacity={clamp01(e) * 0.92}
            style={{transformBox: 'fill-box', transformOrigin: 'center', transform: `scale(${lerp(0.2, 1, e)})`,
              filter: `brightness(${bright})`, stroke: '#00000022', strokeWidth: 1}} />;
        })}
      </svg>
      {/* the pool that gives the type a ground to be read on, in the film's own ground colour. The alpha is
          on the LAYER rather than baked into an 8-digit hex — `${BG}cc` is only a colour when `bg` is a
          6-digit hex, and an invalid one drops the whole gradient silently. Same premultiplied ramp: 0.8 → 0. */}
      <div style={{position: 'absolute', inset: 0, opacity: POOL_ALPHA,
        background: `radial-gradient(38% 40% at 50% 50%, ${BG}, #0000 72%)`}} />
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 16}px)`, titleIn !== 1), color: INK,
          font: '800 138px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em', textShadow: `0 12px 50px ${BLOOM}`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 22, color: TAG_INK,
          font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em', textShadow: `0 4px 20px ${BLOOM}`}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default LowPolyForm;
