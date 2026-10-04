// SHOT · Flow Field — hundreds of streamlines trace a static curl/flow field and DRAW ON in staggered waves,
// colour shifting along a duotone, revealing an ambient generative field with a wordmark settling at its
// centre. Generative-art motion you can't fake with gradients (family K · generative). Deterministic: the
// field is a pure fn of position, each streamline a fixed traced path animated by strokeDashoffset.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, shade} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {useGlide} from '../runtime/glide';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#070a14';
const POOL_D0 = '#0c1024';      // the lit core of the ground — a LIFT off this register's own night
const CORE_D0 = '#070a14dd';    // the centre wash the wordmark is read against

// static field angle at a point — a smooth curl from summed sinusoids (deterministic, no state)
const angleAt = (x: number, y: number) =>
  Math.sin(x * 0.0016 + Math.cos(y * 0.0012)) * Math.PI + Math.cos(y * 0.0018) * 0.9;

export const FlowField: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string; lines?: number}> = ({
  title: TITLE = 'In flow', tagline: TAG = 'everything, moving as one', accent: ACC = '#38e0c8',
  accent2: ACC2 = '#7a5bff', lines: LINES = 150} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // A FILM CAN GROUND ON PAPER. This register's duotone was picked against near-black — the teal measured
  // 1.56:1 on a warm-white ground, which is a streamline nobody can see — so on a light ground each of the two
  // hues is walked along its OWN black-to-white axis until it clears the graphics floor, by the same tested
  // ladder the film tier uses for a re-grounded beat (`groundFrom`: exposure only, never hue). A film that
  // passes its own `accent`/`accent2` keeps that hue; only its exposure moves. Null DNA and the eight (dark)
  // presets never reach this at all.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  // Exposed to the INK floor, not the graphics one: a streamline is the CONTENT of this frame, not a rule
  // beside it, and 3.0 is also the exact ratio the ink gate fails at — a colour solved to 3.00 lands on the
  // wrong side of it the moment the ground behind a mark is sampled locally rather than as the flat page.
  const litHue = (c: string) => (dna && lit ? groundFrom(dna, {bg: dna.bg, fg: c}).fg : c);
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const N = Math.max(20, Math.min(220, LINES));
  const ACC_L = litHue(ACC), ACC2_L = litHue(ACC2);
  const STEPS = 34, STEP = 26;
  // build each streamline path once (field is static)
  const paths = [] as {d: string; len: number; col: string; seed: number}[];
  for (let i = 0; i < N; i++) {
    let x = hash01(i * 2.3) * W, y = hash01(i * 5.7) * H;
    let d = `M${x.toFixed(1)} ${y.toFixed(1)}`;
    for (let s = 0; s < STEPS; s++) {
      const a = angleAt(x, y);
      x += Math.cos(a) * STEP; y += Math.sin(a) * STEP;
      d += ` L${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    const mix = hash01(i * 9.1);
    paths.push({d, len: STEPS * STEP, col: mix < 0.5 ? ACC_L : ACC2_L, seed: i});
  }
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    // The ground's core is a LIFT off this register's night; on paper a lift is invisible and the literal is a
    // near-black hole in the middle of the film's page. On a light ground it is the same gesture at the other
    // exposure — a slightly deeper wash of the film's own paper, hue untouched.
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 45%, ${lit ? shade(BG, 0.06) : POOL_D0}, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* A GLOW IS A DARK-GROUND DEVICE. Around a line on paper it is a soft halo of the line's own colour,
            so the line is read against itself and its edge dissolves — the white-halo failure the caption rule
            forbids, in colour. Measured: it put 83% of this register's marks under the floor on warm white
            while the lines themselves were perfectly legible. */}
        {paths.map((p, i) => {
          const st = 0.02 + hash01(p.seed * 3.7) * 0.5;                  // staggered draw-on
          const draw = easeOutCubic(clamp01(seg(t, st, st + 0.4)));
          // ALPHA IS NOT THE SAME GESTURE ON THE TWO GROUNDS. A stroke painted at 66% is composited back into
          // whatever it sits on: against night that DEEPENS it, against paper it dilutes it toward white. So a
          // hue solved to the ink floor still landed at 2.55:1 once the alpha was applied, which is exactly the
          // "present but not readable" this gate exists for — 75% of the marks, measured. On a light ground the
          // settled stroke is therefore opaque and the fade-in alone carries the draw-on; the ramp starts
          // higher so the entrance is the same length of time rather than the same lightness.
          return <path key={i} d={p.d} fill="none" stroke={p.col} strokeWidth={2.2} strokeLinecap="round"
            opacity={lit ? 0.35 + 0.65 * draw : 0.16 + 0.5 * draw} strokeDasharray={p.len}
            strokeDashoffset={p.len * (1 - draw)}
            style={{filter: lit ? 'none' : 'drop-shadow(0 0 3px currentColor)'}} />;
        })}
      </svg>
      {/* centre vignette so the wordmark reads over the field — the FILM'S ground at the same 87% opacity, not
          a fixed near-black, which on paper was a dark disc under near-black type */}
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(34% 34% at 50% 48%, ${lit ? `${BG}dd` : CORE_D0}, #0000 70%)`}} />

      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        {/* the wordmark and its kicker are on the ground, so they are the film's ink and its metadata; the
            separation shadow is the ground's OWN colour on paper, never a fixed black under dark type */}
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 16}px)`, titleIn !== 1), color: dna?.fg ?? '#eafcff',
          font: '800 132px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: `0 0 50px ${ACC_L}55, 0 12px 40px ${lit ? BG : '#000'}`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 22, color: dna?.dim ?? '#9fb2c8',
          font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default FlowField;
