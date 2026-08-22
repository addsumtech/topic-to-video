// SHOT · Game of Life — Conway's cellular automaton evolves from a fixed seed (recomputed to the current
// generation each frame, so it's fully deterministic + seekable), living cells glowing, a wordmark resolving
// over the emergent order. Generative / "simple rules, complex life" (family K · generative).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#060a09', LIVE = '#37ff9a';
const GX = 64, GY = 36;

export const GameOfLife: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Emergent', tagline: TAG = 'simple rules, complex life', accent: ACC = LIVE} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cw = W / GX, ch = H / GY;
  const gens = Math.floor(t * 24);                                // generation at time t
  // init + step (toroidal). Deterministic seed.
  let grid = new Uint8Array(GX * GY);
  for (let i = 0; i < GX; i++) for (let j = 0; j < GY; j++) grid[j * GX + i] = hash01(i * 12.9 + j * 78.2) > 0.72 ? 1 : 0;
  for (let g = 0; g < gens; g++) {
    const nx = new Uint8Array(GX * GY);
    for (let i = 0; i < GX; i++) for (let j = 0; j < GY; j++) {
      let n = 0;
      for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
        if (!di && !dj) continue;
        n += grid[((j + dj + GY) % GY) * GX + ((i + di + GX) % GX)];
      }
      const a = grid[j * GX + i];
      nx[j * GX + i] = a ? (n === 2 || n === 3 ? 1 : 0) : (n === 3 ? 1 : 0);
    }
    grid = nx;
  }
  const titleIn = easeOutCubic(seg(t, 0.42, 0.66));
  const tagIn = easeOutCubic(seg(t, 0.6, 0.82));
  const cells: React.ReactNode[] = [];
  for (let i = 0; i < GX; i++) for (let j = 0; j < GY; j++) {
    if (!grid[j * GX + i]) continue;
    cells.push(<rect key={`${i}-${j}`} x={i * cw + 2} y={j * ch + 2} width={cw - 4} height={ch - 4} rx={4}
      fill={ACC} opacity={0.85} />);
  }
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 46%, #0a1512, ${BG} 76%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, filter: `drop-shadow(0 0 4px ${ACC})`}}>{cells}</svg>
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(40% 40% at 50% 50%, #060a09dd, #0000 72%)'}} />
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#eafff4',
          font: '800 128px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: `0 0 40px ${ACC}, 0 12px 40px #000`}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 20, color: ACC,
          font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em', textShadow: `0 0 14px ${ACC}`}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default GameOfLife;
