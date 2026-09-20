// SHOT · Radial Burst — a kaleidoscopic radial-symmetry register: concentric rings of shapes BLOOM outward in
// N-fold symmetry and slowly rotate, resolving into a central hub. Mesmerizing, vivid, mandala-like — a
// composition axis none of the linear shots use. Deterministic (bloom per ring + spin = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA, rotate} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {bottomInset} from '../runtime/layout';

export const DURATION = 165; // 5.5s
const N = 14;
const HUB_RING_D0 = '#8f7bff';
// `hsl(0 85% 62%)` WRITTEN AS A HEX — the seed `rotate` (which keeps saturation and lightness and moves only
// the hue) carries around the wheel. The mandala's colours are GENERATED from an angle, so there is no literal
// anywhere to read the film's exposure into; a hex of the same S/L gives the exposure ladder something to walk.
// It is used only when the film grounds on paper: the dark and un-themed renders keep the `hsl()` string
// verbatim, so not one of their pixels moves.
const WHEEL_SEED = '#f04c4c';

export const RadialBurst: React.FC<{hub?: string; tagline?: string}> = ({hub: HUB = 'WorkBuddy', tagline = 'EVERYTHING, IN ORBIT'} = {}) => {
  const t = useT();
  const dna = useDNA();
  // A MANDALA IS A FORM. It prints on paper — that is where mandalas come from — so it takes the film's ground
  // and its ink rather than needing a night. Its wheel was nonetheless picked against near-black: at 62%
  // lightness every petal, ray and dot sits around 2:1 on warm white, which is why 88% of the register's marks
  // fell under the floor there and the hub's violet ring came in at 2.92:1. On a light ground each colour is
  // walked along its own black-to-white axis until it clears the legibility floor, by the same tested ladder the
  // film tier uses for a re-grounded beat (`groundFrom`) — exposure only, every hue kept exactly where it was.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  // Exposed to the INK floor, not the graphics one: the petals, rays and dots ARE the content of this frame,
  // and 3.0 is also the exact ratio the ink gate fails at, so a colour solved to 3.00 lands on the wrong side
  // of it as soon as the ground behind a mark is sampled locally rather than as the flat page.
  const litHue = (c: string) => (dna && lit ? groundFrom(dna, {bg: dna.bg, fg: c}).fg : c);
  const wheel = (hue: number) => (lit ? litHue(rotate(WHEEL_SEED, hue)) : `hsl(${hue} 85% 62%)`);
  // THE BLOOM GLOW IS A DARK-GROUND DEVICE. `#rg` blurs each shape and merges it under itself, which against
  // night is a bloom and on paper is a soft halo of the shape's own colour — so every petal was read against
  // its own light instead of against the page, and its edge dissolved into it. A printed mandala is crisp.
  const GLOW = lit ? 'none' : 'url(#rg)';
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const spin = t * 26;
  const hub = easeOutBack(seg(t, 0.02, 0.2));

  // ring descriptor: radius, bloom window, shape
  const rings = [
    {r: 190, a: 0.1, kind: 'ray', hueA: 190},
    {r: 300, a: 0.24, kind: 'petal', hueA: 260},
    {r: 410, a: 0.4, kind: 'dot', hueA: 320},
    {r: 520, a: 0.56, kind: 'petal', hueA: 30},
  ];

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 50%, #141032 0%, #0a0722 60%, #050318 100%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><filter id="rg"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        <g transform={`translate(${cx} ${cy}) rotate(${spin})`}>
          {rings.map((ring, ri) => {
            const bloom = easeOutBack(seg(t, ring.a, ring.a + 0.24));
            if (bloom <= 0) return null;
            return [...Array(N)].map((_, i) => {
              const ang = (i / N) * 360 + (ri % 2 ? 360 / N / 2 : 0);
              const hue = (ring.hueA + i * (360 / N) * 0.5) % 360;
              const col = wheel(hue);
              const rr = ring.r * bloom;
              const common = {transform: `rotate(${ang}) translate(0 ${-rr})`, filter: GLOW};
              if (ring.kind === 'ray')
                return <rect key={`${ri}-${i}`} x={-5} y={-70} width={10} height={140} rx={5} fill={col} {...common} opacity={0.9} />;
              if (ring.kind === 'dot')
                return <circle key={`${ri}-${i}`} r={16 * bloom} fill={col} {...common} />;
              // petal
              return <path key={`${ri}-${i}`} d="M0,-46 C26,-30 26,20 0,52 C-26,20 -26,-30 0,-46 Z" fill={col} {...common} opacity={0.92} transform={`rotate(${ang}) translate(0 ${-rr}) scale(${bloom})`} />;
            });
          })}
        </g>

        {/* CENTRAL HUB — left as it is, and on purpose: it carries its OWN ground (a deep violet disc with a
            lilac inner and a white core), so its three tones read against each other on any paper. Only the
            outer ring meets the film's ground, and at 2.92:1 on warm white it was the one mark here that fell
            under the floor, so that ring is exposed for the ground and nothing else in the hub moves. */}
        <g transform={`translate(${cx} ${cy}) scale(${hub})`}>
          <circle r={110} fill="#1a1440" stroke={litHue(HUB_RING_D0)} strokeWidth={3} filter={GLOW} />
          <circle r={64} fill="#c9b8ff" filter={GLOW} opacity={0.9} />
          <circle r={34} fill="#fff" />
        </g>
      </svg>

      {/* the hub's name and the kicker are set ON the ground, so they are the film's ink and its metadata; the
          separation shadow is the ground's own colour on paper, not a fixed black under near-black type */}
      <div style={{position: 'absolute', left: 0, right: 0, top: cy + 130, textAlign: 'center',
        opacity: clamp01(seg(t, 0.16, 0.32)), color: dna?.fg ?? '#eae4ff', font: '800 40px/1 var(--f-body, Inter, system-ui, sans-serif)',
        letterSpacing: '-0.01em', textShadow: `0 2px 20px ${lit ? (dna?.bg ?? '#000') : '#000'}`}}>{HUB}</div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: bottomInset(W, H, H * 0.1), textAlign: 'center',
        opacity: clamp01(seg(t, 0.6, 0.82)), color: dna?.dim ?? '#cbbfff', font: '600 34px/1 var(--f-mono, "JetBrains Mono", monospace)',
        letterSpacing: '0.4em', paddingLeft: '0.4em'}}>{tagline}</div>
    </AbsoluteFill>
  );
};
export default RadialBurst;
