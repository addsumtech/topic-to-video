// SHOT · Fractal Tree — a recursive tree GROWS from the ground: the trunk splits into branches depth by depth
// (each drawing on in order), then blossoms bloom at the tips. Techno-natural / organic growth (family W ·
// organic/botanical). Deterministic (branch geometry is a pure recursion; draw-on staggered by depth).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, shade} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#0b120e';
const POOL_D0 = '#14231b';      // the lit floor the tree grows out of — a LIFT off this register's own night
const LEAF_D0 = '#7fae95', BLOSSOM2_D0 = '#ffd36e';
const MAXD = 9;

type Seg = {x1: number; y1: number; x2: number; y2: number; depth: number; w: number; leaf: boolean; seed: number};

export const FractalTree: React.FC<{title?: string; tagline?: string; branch?: string; blossom?: string}> = ({
  title: TITLE = 'Grow', tagline: TAG = 'from one root, everything', branch: BR = '#9fb8a8', blossom: BL = '#ff8fc4'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // A TREE IS A FORM, NOT A LIGHT — it has been drawn as dark branches on pale paper for as long as anyone has
  // drawn one — so it takes the film's ground and ink like any other drawing. Its palette was nonetheless
  // picked against near-black: the sage branches measured 1.89:1 and the amber blossoms 1.28:1 on warm white,
  // with 90% of the register's marks under the floor. On a light ground each hue is walked along its own
  // black-to-white axis until it clears the floor (`groundFrom`: exposure only, hue kept), so a film that
  // passes its own `branch`/`blossom` keeps that colour and only its exposure moves. Null DNA and the eight
  // (dark) presets never reach this.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  // Exposed to the INK floor, not the graphics one: the branches and blossoms ARE the content, and 3.0 is also
  // the exact ratio the ink gate fails at, so a colour solved to 3.00 lands on the wrong side of it as soon as
  // the ground behind a mark is sampled locally rather than as the flat page.
  const litHue = (c: string) => (dna && lit ? groundFrom(dna, {bg: dna.bg, fg: c}).fg : c);
  const BRANCH = litHue(BR), LEAF = litHue(LEAF_D0);
  const BLOSSOM = litHue(BL), BLOSSOM2 = litHue(BLOSSOM2_D0);
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const segs: Seg[] = [];
  const grow = (x: number, y: number, ang: number, len: number, depth: number, seed: number) => {
    if (depth > MAXD || len < 6) return;
    const x2 = x + Math.cos(ang) * len, y2 = y + Math.sin(ang) * len;
    segs.push({x1: x, y1: y, x2, y2, depth, w: Math.max(1.5, (MAXD - depth) * 2.4), leaf: depth >= MAXD - 1, seed});
    const spread = 0.38 + hash01(seed) * 0.16;
    grow(x2, y2, ang - spread, len * 0.76, depth + 1, seed * 2 + 1);
    grow(x2, y2, ang + spread, len * 0.74, depth + 1, seed * 2 + 2);
    if (depth < 3 && hash01(seed * 3) > 0.4) grow(x2, y2, ang + (hash01(seed) - 0.5) * 0.3, len * 0.5, depth + 2, seed * 2 + 7);
  };
  grow(W / 2, H - 120, -Math.PI / 2, 210, 0, 1);
  const titleIn = easeOutCubic(seg(t, 0.6, 0.82));
  return (
    // the lit floor follows the film's own paper when the film grounds on paper; the literal is a near-black
    // pool, which on a light film is a dark hole where the trunk meets the page
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 90%, ${lit ? shade(BG, 0.06) : POOL_D0}, ${BG} 72%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {segs.map((s, i) => {
          const st = 0.04 + (s.depth / MAXD) * 0.5;
          const g = easeOutCubic(clamp01(seg(t, st, st + 0.16)));
          if (g <= 0) return null;
          const ex = lerp(s.x1, s.x2, g), ey = lerp(s.y1, s.y2, g);
          return <line key={i} x1={s.x1} y1={s.y1} x2={ex} y2={ey}
            stroke={s.leaf ? LEAF : BRANCH} strokeWidth={s.w} strokeLinecap="round"
            opacity={lerp(0.5, 1, s.depth / MAXD)} />;
        })}
        {/* blossoms at the tips */}
        {segs.filter((s) => s.leaf).map((s, i) => {
          const bloom = clamp01(seg(t, 0.62 + hash01(s.seed) * 0.18, 0.9));
          if (bloom <= 0) return null;
          const col = hash01(s.seed * 5) > 0.5 ? BLOSSOM : BLOSSOM2;
          // a blossom's glow is a dark-ground device: on paper the 6px halo is the blossom's own colour, so
          // every blossom (and every twig behind one) was read against its own light instead of the page
          return <circle key={i} cx={s.x2} cy={s.y2} r={lerp(0, 9, bloom)} fill={col} opacity={0.85}
            style={{filter: lit ? 'none' : `drop-shadow(0 0 6px ${col})`}} />;
        })}
      </svg>
      {/* the title and its kicker are on the ground, so they are the film's ink and its metadata; the
          separation shadow is the ground's own colour on paper, never a fixed black under near-black type */}
      <div style={{position: 'absolute', top: 120, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        transform: `translateY(${(1 - titleIn) * 14}px)`, color: dna?.fg ?? '#eafff2',
        font: '800 120px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em', textShadow: `0 8px 40px ${lit ? BG : '#000'}`}}>{TITLE}</div>
      <div style={{position: 'absolute', top: 268, left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.7, 0.9)), color: dna?.dim ?? '#9fc4b0',
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.16em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default FractalTree;
