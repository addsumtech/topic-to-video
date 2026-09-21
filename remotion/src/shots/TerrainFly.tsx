// SHOT · Terrain Fly — a wireframe heightmap scrolls toward the viewer under a HAND-ROLLED perspective
// projection (`proj()` below, not WebGL): hills drift in from the horizon, grid lines are coloured by
// elevation, fog closes into a glowing horizon, a wordmark sits above. The heights and the perspective are
// real arithmetic; only the renderer is 2D, and naming that is what stops "3D" being a claim the library
// cannot keep. A
// camera/landscape register (family B · camera/space). Deterministic (heights = summed sines of x, z+t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {onLight} from '../runtime/light';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#070312', ACC_D0 = '#00e0c8', ACC2_D0 = '#ff4fa3';
const SKY0_D0 = '#16043a', SKY1_D0 = '#3a0a4e', MID_D0 = '#4a6cff', INK_D0 = '#eafcff', TAG_D0 = '#c7b6ff';
const GX = 40, GZ = 24;

export const TerrainFly: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Cross it', tagline: TAG = 'new ground, ahead'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0, ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  // THE SKY WAS A LITERAL NIGHT AND THE WORDMARK A LITERAL NEAR-WHITE, WHILE THE LAND TOOK THE FILM'S
  // GROUND. On a light film the frame ran from that fixed violet at the top to paper at the bottom, so the
  // near half of the mesh — the rows a viewer actually reads the terrain from — was mid-blue on white at
  // 1.05:1, and the title only survived because the top happened to stay dark. The sky is now the film's
  // own ground carried up and deepened toward the accents, which keeps the dusk on a dark film and gives a
  // light one a pale sky over legible land.
  const SKY0 = dna ? mix(dna.bg, dna.accent2, 0.18) : SKY0_D0;
  const SKY1 = dna ? mix(dna.bg, dna.accent, 0.12) : SKY1_D0;
  const MID = dna ? mix(dna.fg, dna.accent, 0.5) : MID_D0;    // the elevations between the two accents
  const INK = dna?.fg ?? INK_D0, TAG_INK = dna ? mix(dna.fg, dna.dim, 0.4) : TAG_D0;
  // AND DISTANCE IS NOT THE SAME THING ON PAPER. The far rows recede by alpha, down to 0.15 — which on a
  // dark ground is still a lit line and on paper is nothing at all, so the half of the mesh that carries
  // the horizon washed out. A drawn line has a floor; a glowing one does not.
  const FADE_FLOOR = onLight(dna) ? 0.42 : 0.15;
  // ...and a black bloom under dark type is mud, not depth: the glow belongs to the emissive world only.
  const TITLE_GLOW = onLight(dna) ? `0 2px 10px ${ACC}55` : `0 0 44px ${ACC}88, 0 10px 40px #000`;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, horizon = H * 0.42, focal = 460, camH = 2.2;
  const scroll = t * 4;
  const heightAt = (gi: number, gjWorld: number) =>
    (Math.sin(gi * 0.5 + gjWorld * 0.4) + Math.sin(gi * 0.23 - gjWorld * 0.31) * 1.4 + Math.sin(gjWorld * 0.7) * 0.6);
  // project a grid point (gi 0..GX across, gj 0..GZ depth) to screen
  const proj = (gi: number, gj: number) => {
    const depth = gj + 1 - (scroll % 1);                          // near rows recycle toward the viewer
    const gjWorld = gj + Math.floor(scroll);
    const hx = (gi - GX / 2) * 0.5;
    const hy = heightAt(gi, gjWorld) * 0.55;
    return {x: cx + (hx / depth) * focal, y: horizon + ((camH - hy) / depth) * focal, depth, h: hy};
  };
  const titleIn = easeOutCubic(seg(t, 0.16, 0.44));
  const lines: React.ReactNode[] = [];
  for (let gj = 0; gj < GZ; gj++) {
    const fog = clamp01(1 - gj / GZ);                              // fade far rows
    for (let gi = 0; gi < GX; gi++) {
      const p = proj(gi, gj);
      const col = p.h > 0.4 ? ACC : p.h < -0.4 ? ACC2 : MID;
      if (gi < GX - 1) { const q = proj(gi + 1, gj); lines.push(<line key={`h${gi}-${gj}`} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={col} strokeWidth={1.5} opacity={FADE_FLOOR + 0.6 * fog} />); }
      if (gj < GZ - 1) { const q = proj(gi, gj + 1); lines.push(<line key={`v${gi}-${gj}`} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={col} strokeWidth={1.5} opacity={FADE_FLOOR + 0.6 * fog} />); }
    }
  }
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ??
      `linear-gradient(180deg, ${SKY0} 0%, ${SKY1} ${horizon / H * 100}%, ${BG} 78%)`, overflow: 'hidden'}}>
      {/* horizon sun glow */}
      <div style={{position: 'absolute', left: cx, top: horizon, width: 700, height: 360, transform: 'translate(-50%,-70%)',
        background: `radial-gradient(circle, ${ACC}66, ${ACC2}33 40%, #0000 70%)`, filter: 'blur(6px)'}} />
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>{lines}</svg>
      <div style={{position: 'absolute', top: 96, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        transform: `translateY(${(1 - titleIn) * 14}px)`, color: INK,
        font: '800 120px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
        textShadow: TITLE_GLOW}}>{TITLE}</div>
      <div style={{position: 'absolute', top: 244, left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.3, 0.56)), color: TAG_INK,
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default TerrainFly;
