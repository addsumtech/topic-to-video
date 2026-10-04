// SHOT · Game of Life — Conway's cellular automaton evolves from a fixed seed (recomputed to the current
// generation each frame, so it's fully deterministic + seekable), living cells glowing, a wordmark resolving
// over the emergent order. Generative / "simple rules, complex life" (family K · generative).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, shade} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#060a09', LIVE = '#37ff9a';
const POOL_D0 = '#0a1512';      // the lit core of the ground — a LIFT off this register's own night
const CORE_D0 = '#060a09dd';    // the centre wash the wordmark is read against
const GX = 64, GY = 36;

export const GameOfLife: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Emergent', tagline: TAG = 'simple rules, complex life', accent: ACC0 = LIVE} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  // A FILM CAN GROUND ON PAPER, and a living cell here is a lit square: `#37ff9a` is a phosphor green that
  // measured well under the graphics floor on warm white, so the grid read as a pale mint stain. Conway's grid
  // is a FORM, not a light — it has been printed black-on-white since 1970 — so the fix is exposure, not a
  // night: the live colour is walked along its own black-to-white axis until it clears the floor, by the same
  // tested ladder the film tier uses for a re-grounded beat. Hue is kept; only the exposure moves. Null DNA and
  // the eight (dark) presets never reach this.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  // Exposed to the INK floor, not the graphics one: the cells ARE the content here, and 3.0 is also the exact
  // ratio the ink gate fails at, so a colour solved to 3.00 lands on the wrong side of it as soon as the
  // ground behind a mark is sampled locally rather than as the flat page.
  const ACC = lit && dna ? groundFrom(dna, {bg: dna.bg, fg: ACC0}).fg : ACC0;
  const t = useT();
  const glide = useGlide();
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
    // the ground's lit core and the centre wash both follow the film's own paper when the film grounds on
    // paper — the literals are a near-black pool and a near-black disc, which on a light film are two holes
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 46%, ${lit ? shade(BG, 0.06) : POOL_D0}, ${BG} 76%)`, overflow: 'hidden'}}>
      {/* A GLOW IS A DARK-GROUND DEVICE: on paper the 4px halo around each cell is the cell's own colour, so
          every cell was read against its own light rather than against the page and 92% of the register's
          marks fell under the floor while the cells themselves were perfectly legible. */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, filter: lit ? 'none' : `drop-shadow(0 0 4px ${ACC})`}}>{cells}</svg>
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(40% 40% at 50% 50%, ${lit ? `${BG}dd` : CORE_D0}, #0000 72%)`}} />
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        {/* the wordmark is on the ground, so it is the film's ink; its separation shadow is the ground's own
            colour on paper rather than a fixed black under near-black type */}
        <div style={{opacity: titleIn, transform: glide(`translateY(${(1 - titleIn) * 14}px)`, titleIn !== 1), color: dna?.fg ?? '#eafff4',
          font: '800 128px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: lit ? `0 0 40px ${BG}, 0 12px 40px ${BG}` : `0 0 40px ${ACC}, 0 12px 40px #000`}}>{TITLE}</div>
        {/* the kicker's halo is the same lit device: on paper it is a green haze around green type, so it goes
            and the exposed accent carries the line on its own */}
        <div style={{opacity: tagIn, marginTop: 20, color: ACC,
          font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em', textShadow: lit ? 'none' : `0 0 14px ${ACC}`}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default GameOfLife;
