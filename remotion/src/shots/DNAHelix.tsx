// SHOT · DNA Helix — a rotating double helix: two sine-phased strands of nodes with base-pair RUNGS between
// them, depth-shaded (front bright, back dim), assembling top-down then spinning. A scientific / biotech
// register (family S · scientific/molecular). Deterministic (strand x = sin(y·k + t·ω), depth = cos).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#060a10', A_T = '#37e0ff', G_C = '#ff5b9e', STRAND = '#7fe9c8';

export const DNAHelix: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Encoded', tagline: TAG = 'the blueprint of it all'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, top = 150, bottom = H - 150, M = 48;
  const amp = 190, freq = 0.020, spin = t * 2.4;
  const titleIn = easeOutCubic(seg(t, 0.5, 0.74));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  type Item = {z: number; el: React.ReactNode; key: string};
  const items: Item[] = [];
  for (let i = 0; i <= M; i++) {
    const y = lerp(top, bottom, i / M);
    const appear = clamp01(seg(t, 0.05 + (i / M) * 0.4, 0.2 + (i / M) * 0.4));
    if (appear <= 0) continue;
    const ph = y * freq * 40 + spin;
    const x1 = cx + Math.cos(ph) * amp, z1 = Math.sin(ph);
    const x2 = cx + Math.cos(ph + Math.PI) * amp, z2 = Math.sin(ph + Math.PI);
    const depth = (z: number) => clamp01((z + 1) / 2);
    // rung every 2 steps
    if (i % 2 === 0) {
      const zc = (z1 + z2) / 2;
      items.push({z: zc, key: `r${i}`, el: <line x1={x1} y1={y} x2={x2} y2={y}
        stroke={i % 4 === 0 ? A_T : G_C} strokeWidth={lerp(3, 8, depth(zc))} opacity={appear * (0.25 + 0.6 * depth(zc))} strokeLinecap="round" />});
    }
    const node = (x: number, z: number, k: string) => ({z, key: k, el:
      <circle cx={x} cy={y} r={lerp(6, 15, depth(z))} fill={STRAND} opacity={appear * (0.3 + 0.7 * depth(z))}
        style={{filter: depth(z) > 0.7 ? `drop-shadow(0 0 8px ${STRAND})` : undefined}} />});
    items.push(node(x1, z1, `a${i}`));
    items.push(node(x2, z2, `b${i}`));
  }
  items.sort((p, q) => p.z - q.z); // back-to-front
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 44%, #0b1526, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>{items.map((it) => <g key={it.key}>{it.el}</g>)}</svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 16}px)`, color: '#eafffb',
          font: '800 128px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: `0 0 50px ${A_T}44, 0 12px 40px #000`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 20, color: '#9fd6d0',
          font: '600 32px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em', textShadow: '0 4px 20px #000'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default DNAHelix;
