// SHOT · Morph Forms — a rotating 3D point-cloud MORPHS between primitives: sphere → cube → torus → sphere,
// points easing between each shape's positions while the whole cloud spins, depth-shaded. Kinetic 3D geometry
// as a living object (family E · 3D / spatial). Deterministic (positions are pure fns of index; morph +
// rotation are fns of t). Pure math + SVG — no WebGL.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA, shade} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {bottomInset} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s
const BG_D0 = '#070912', ACC_D0 = '#5b8cff', ACC2_D0 = '#c07bff';
const POOL_D0 = '#10142c';   // the lit core of the ground, a LIFT off this register's own night
const N = 260;
const GOLDEN = Math.PI * (3 - Math.sqrt(5));

export const MorphForms: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'One idea, many shapes', tagline: TAG = ''} = {}) => {
  const dna = useDNA();
  // A FILM CAN GROUND ON PAPER, AND THIS REGISTER'S PALETTE WAS PICKED AGAINST NEAR-BLACK. `groundFrom` relights
  // the film's OWN tokens for the ground they will actually be drawn on — exposure only, hue kept — so a light
  // film gets its own accents at a legible exposure instead of the pastels it chose for dark type on paper.
  // Null DNA and all eight (dark) presets never reach it: they take the `??` fallbacks exactly as before.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  const BG = dna?.bg ?? BG_D0;
  const ACC = lit?.accent ?? dna?.accent ?? ACC_D0, ACC2 = lit?.accent2 ?? dna?.accent2 ?? ACC2_D0;
  // The ground's core is a LIFT off this register's night — on paper a lift is invisible and the literal is a
  // near-black hole in the middle of the film's page (measured: a dark ellipse over half the frame). On a light
  // ground it becomes the same gesture at the other exposure: a slightly deeper wash of the film's own paper.
  const POOL = lit ? shade(BG, 0.06) : POOL_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  // three target shapes per point index
  const pts = [] as {sph: number[]; cub: number[]; tor: number[]}[];
  for (let i = 0; i < N; i++) {
    const y = 1 - 2 * (i + 0.5) / N;                    // fibonacci sphere
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const phi = i * GOLDEN;
    const sph = [Math.cos(phi) * r, y, Math.sin(phi) * r];
    const m = Math.max(Math.abs(sph[0]), Math.abs(sph[1]), Math.abs(sph[2])) || 1;
    const cub = [sph[0] / m, sph[1] / m, sph[2] / m];   // sphere→cube via chebyshev normalise
    const a = phi, b = i * 0.7;                          // torus
    const R = 0.72, rr = 0.34;
    const tor = [(R + rr * Math.cos(b)) * Math.cos(a), rr * Math.sin(b), (R + rr * Math.cos(b)) * Math.sin(a)];
    pts.push({sph, cub, tor});
  }
  // morph phase: sphere→cube (0–.33), cube→torus (.33–.66), torus→sphere (.66–1)
  const seg1 = easeInOutCubic(clamp01(seg(t, 0.08, 0.36)));
  const seg2 = easeInOutCubic(clamp01(seg(t, 0.38, 0.64)));
  const seg3 = easeInOutCubic(clamp01(seg(t, 0.66, 0.92)));
  const mix = (a: number[], b: number[], k: number) => a.map((v, i) => lerp(v, b[i], k));
  const ang = t * Math.PI * 1.4, ca = Math.cos(ang), sa = Math.sin(ang), tilt = -0.32;
  const cx = W / 2, cy = H / 2 + 10, S = 360;
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const dots = pts.map((p, i) => {
    let pos = mix(p.sph, p.cub, seg1);
    pos = mix(pos, p.tor, seg2);
    pos = mix(pos, p.sph, seg3);
    // rotateY then tilt on X
    let x = pos[0] * ca + pos[2] * sa;
    let z = -pos[0] * sa + pos[2] * ca;
    let yv = pos[1] * Math.cos(tilt) - z * Math.sin(tilt);
    z = pos[1] * Math.sin(tilt) + z * Math.cos(tilt);
    const persp = 1.9 / (1.9 - z);
    return {x: cx + x * S * persp, y: cy + yv * S * persp, z, persp, i};
  }).sort((a, b) => a.z - b.z);
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 44%, ${POOL}, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {dots.map((d) => {
          const depth = clamp01((d.z + 1) / 2);
          const rad = lerp(2, 9, depth) * d.persp;
          const col = depth > 0.5 ? ACC : ACC2;
          return <circle key={d.i} cx={d.x} cy={d.y} r={rad} fill={col} opacity={lerp(0.28, 1, depth)}
            style={{filter: depth > 0.7 ? `drop-shadow(0 0 6px ${col})` : undefined}} />;
        })}
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', paddingBottom: bottomInset(W, H, 120)}}>
        {/* the title and its kicker sit ON the ground, so they are the film's ink and its metadata. The
            separation shadow is the GROUND'S OWN colour, never a fixed black: black behind near-black type on
            paper is a smudge, and a white one would be the halo the caption rule forbids. */}
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 14}px)`, titleIn !== 1), color: dna?.fg ?? '#eaf0ff',
          font: '800 76px/1.05 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.02em', textAlign: 'center',
          textShadow: lit ? `0 8px 40px ${BG}` : '0 8px 40px #000'}}>{TITLE}</div>
        {TAG ? <div style={{opacity: titleIn, marginTop: 16, color: dna?.dim ?? '#9fb0d0', font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.16em'}}>{TAG}</div> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default MorphForms;
