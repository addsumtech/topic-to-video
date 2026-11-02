// SHOT · DNA Helix — a rotating double helix: two backbones wound right-handed round one axis, base-pair RUNGS
// between them, depth-shaded (front bright, back dim), assembling top-down then spinning. A scientific / biotech
// register (family S · scientific/molecular). Deterministic (phase = 2π·y/pitch + t·ω, depth = sin).
//
// IT IS B-DNA, IN ITS OWN PROPORTIONS (FIDELITY below). The strands were two sines half a turn apart, sampled
// every 16 px at a phase step of 13 rad — so the helix the eye saw was an ALIAS: about seven rungs a turn, a pitch
// a third of the diameter's 1.7, no groove, and a handedness that held only because 13 rad happened to land where it
// did. It is drawn now from the molecule's own numbers: 10.5 base pairs a turn, a pitch 1.7 times the diameter, the
// second backbone a minor-groove's 12/34 of a turn behind the first (so the major and minor grooves alternate as
// they do in every crystal structure), right-handed, each backbone a continuous depth-shaded line with a phosphate
// at every base pair.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 160; // ~5.3s
export const FIDELITY = {
  subject: 'B-DNA double helix (the Watson-Crick form)',
  depicts: 'real',
  references: [
    {kind: 'drawing', source: 'references/object-refs/DNAHelix/dna-structure.png',
      note: 'Wikimedia Commons structure diagram of the double helix (its sidecar names licence and author)'},
    {kind: 'spec', source: 'https://en.wikipedia.org/wiki/Nucleic_acid_double_helix',
      note: 'B-DNA: right-handed; 10.5 bp per turn; rise 3.32 Å; pitch 33.2 Å; diameter 20 Å; major groove 22 Å wide, minor 12 Å — "as the strands are not directly opposite each other, the grooves are unequally sized"'},
  ],
  proportions: {
    pitch_to_diameter: {value: '1.66-1.74 (pitch 33.2 Å, or 10.5 × 3.32 = 34.9 Å, over 20 Å)', drawn: 1.7,
      source: 'https://en.wikipedia.org/wiki/Nucleic_acid_double_helix'},
    base_pairs_per_turn: {value: 10.5, drawn: 10.5, source: 'https://en.wikipedia.org/wiki/Nucleic_acid_double_helix'},
    minor_groove_share_of_pitch: {value: '12 / (22 + 12) = 0.35', drawn: 0.353,
      source: 'https://en.wikipedia.org/wiki/Nucleic_acid_double_helix'},
    handedness: {value: 'right-handed', drawn: 'right-handed',
      source: 'https://en.wikipedia.org/wiki/Nucleic_acid_double_helix'},
  },
  parts: ['backbone', 'base-pair'],
  mounted_on: {'backbone': null, 'base-pair': 'backbone'},   // each rung is bonded to both strands
  materials: ['sugar-phosphate backbones', 'paired bases (A-T, G-C) as rungs'],
};
const BG_D0 = '#060a10', A_T = '#37e0ff', G_C = '#ff5b9e', STRAND = '#7fe9c8';
const PITCH_PER_DIAMETER = 1.7, BP_PER_TURN = 10.5, MINOR_GROOVE = 12 / 34;   // FIDELITY.proportions
const SEGS_PER_BP = 4;                                                       // backbone smoothness

export const DNAHelix: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Encoded', tagline: TAG = 'the blueprint of it all'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const cx = W / 2, top = Math.round(H * 0.14), bottom = H - Math.round(H * 0.14);
  const amp = Math.round(U * 0.17);                          // the helix's radius: 184 px at 1080, as before
  const pitch = PITCH_PER_DIAMETER * 2 * amp;
  const rise = pitch / BP_PER_TURN;
  const spin = t * 2.4;
  // RIGHT-HANDED: going UP the axis (screen y falling) the phase falls, so a backbone in FRONT runs from lower left
  // to upper right — the turn a right hand's fingers make with its thumb along the axis.
  const phaseAt = (y: number) => (2 * Math.PI * (y - (top + bottom) / 2)) / pitch + spin;
  const offB = 2 * Math.PI * MINOR_GROOVE;                   // the second backbone, a minor groove behind
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  const depth = (z: number) => clamp01((z + 1) / 2);
  const appearAt = (y: number) => clamp01(seg(t, 0.05 + ((y - top) / (bottom - top)) * 0.4, 0.2 + ((y - top) / (bottom - top)) * 0.4));
  type Item = {z: number; el: React.ReactNode; key: string};
  const items: Item[] = [];
  const pt = (y: number, off: number) => {
    const ph = phaseAt(y) + off;
    return {x: cx + Math.cos(ph) * amp, z: Math.sin(ph)};
  };
  // the backbones: continuous, each short segment as bright and as wide as its own depth
  const nSeg = Math.ceil(((bottom - top) / rise) * SEGS_PER_BP);
  for (const [s, off] of [['a', 0], ['b', offB]] as const) {
    for (let k = 0; k < nSeg; k++) {
      const y0 = lerp(top, bottom, k / nSeg), y1 = lerp(top, bottom, (k + 1) / nSeg);
      const appear = appearAt(y1);
      if (appear <= 0) continue;
      const p0 = pt(y0, off), p1 = pt(y1, off), zc = (p0.z + p1.z) / 2;
      items.push({z: zc, key: `${s}s${k}`, el: <line data-part="backbone" x1={p0.x} y1={y0} x2={p1.x} y2={y1}
        stroke={STRAND} strokeWidth={lerp(4, 12, depth(zc))} strokeLinecap="round"
        opacity={appear * (0.25 + 0.75 * depth(zc))} />});
    }
  }
  // a base pair every `rise`: the rung between the two backbones, and a phosphate on each
  const nBp = Math.floor((bottom - top) / rise);
  for (let i = 0; i <= nBp; i++) {
    const y = top + i * rise;
    const appear = appearAt(y);
    if (appear <= 0) continue;
    const a = pt(y, 0), b = pt(y, offB), zc = (a.z + b.z) / 2;
    items.push({z: zc - 0.02, key: `r${i}`, el: <line data-part="base-pair" x1={a.x} y1={y} x2={b.x} y2={y}
      // @positional: the rungs alternate base-pair colours along the strand, which is what a helix diagram draws; no film item sits on a rung
      stroke={i % 2 === 0 ? A_T : G_C} strokeWidth={lerp(3, 8, depth(zc))} opacity={appear * (0.25 + 0.6 * depth(zc))} strokeLinecap="round" />});
    for (const [s, p] of [['a', a], ['b', b]] as const) {
      items.push({z: p.z + 0.01, key: `${s}n${i}`, el:
        <circle cx={p.x} cy={y} r={lerp(5, 13, depth(p.z))} fill={STRAND} opacity={appear * (0.3 + 0.7 * depth(p.z))}
          style={{filter: depth(p.z) > 0.7 ? `drop-shadow(0 0 8px ${STRAND})` : undefined}} />});
    }
  }
  items.sort((p, q) => p.z - q.z); // back-to-front
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 44%, #0b1526, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>{items.map((it) => <g key={it.key}>{it.el}</g>)}</svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none'}}>
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 16}px)`, true), color: '#eafffb',
          font: '800 128px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: `0 0 50px ${A_T}44, 0 12px 40px #000`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 20, color: '#9fd6d0',
          font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em', textShadow: '0 4px 20px #000'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default DNAHelix;
