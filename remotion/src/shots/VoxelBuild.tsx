// SHOT · Voxel Build — an ISOMETRIC object assembles voxel by voxel: cubes drop in from above (staggered in
// stroke order) and stack into a checkmark, each a shaded iso cube (top/left/right). Isometric is a 2D drawing
// convention with no camera and no vanishing point — a legitimate one, and not the same thing as 3D, which
// is what this header used to call it. Playful voxel craft, true iso
// (family N · isometric). Deterministic (cube drop = fn of t + fixed shape).
//
// THE CHECKMARK IS DRAWN ON THE SCREEN, NOT ON THE GROUND. The shape used to be a footprint in the iso (i,j)
// grid — (0,3) (1,4) (2,5) (3,4) … (7,0) — which looks like a ✓ written on graph paper and is not one on the
// frame: the iso mapping puts a cell at x ∝ i−j, y ∝ i+j, so the first three cells (i−j = −3 each) stack
// straight DOWN and the other five (i+j = 7 each) run flat to the RIGHT. What rendered was an L — a column and
// a floor — under a header promising a check, and the title (anchored from the bottom) ran through its base.
// A shape is a picture, and this one's meaning is "done"; an L means nothing.
// So the cubes now stand in a WALL facing the viewer: along the iso diagonal (i+1, j−1), the one direction
// that is exactly horizontal on screen (Δx = TW, Δy = 0), with the stack height k as the vertical (Δy = −VH).
// On that wall a cell (u, v) lands at (u·TW, −v·VH) — an undistorted pixel grid of corner-on cubes — and a
// pixel-art check drawn in it (a short arm down to the vertex, a long arm up, each stroke two cubes thick)
// reads as ✓ in the frame. The cubes still drop from above and land in stroke order, left arm first, each
// column bottom cube then top, so the check is drawn the way a hand draws one. It is sized to sit between the
// content top and the title, scaling down only where that room is short (1:1).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomInset, CONTENT_TOP, textWidthPx} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0a0d1c', ACC_D0 = '#37d68a';
const TW0 = 96, TH0 = 54, VH0 = 66; // tile width/height + voxel rise height, at full size
// @decor: the check-mark form itself, as (column, level) cells on the viewer-facing wall: geometry, not data
const CHECK: [number, number][] = [
  [0, 2], [0, 3], [1, 1], [1, 2], [2, 0], [2, 1],                  // short arm, down to the vertex
  [3, 1], [3, 2], [4, 2], [4, 3], [5, 3], [5, 4], [6, 4], [6, 5],  // long arm, up to the right
];
const COLS = 7, LEVELS = 6;
const TITLE_PX = 88, TITLE_RISE = 58, GAP = 40, DROP = 260;

export const VoxelBuild: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Built to last', tagline: TAG = 'block by block', accent: accentProp} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0, ACC = dna?.accent ?? ACC_D0;
  const TONE = accentProp ?? ACC;   // prop wins; else the DNA accent (was a param default referencing the module const)
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const pt = (x: number, y: number) => `${x.toFixed(1)},${y.toFixed(1)}`;
  // the room: from the content top down to the title's top edge (the title is anchored from the bottom and
  // wraps UPWARD, so a long one takes more), less a gap that also clears the landing overshoot (~10% of DROP)
  const titleLines = Math.max(1, Math.ceil(textWidthPx(TITLE, TITLE_PX) / W));
  const roomTop = CONTENT_TOP, roomBot = H - bottomInset(W, H, 92) - TITLE_RISE - TITLE_PX * titleLines - GAP;
  const glyphW = COLS * TW0, glyphH = (LEVELS - 1) * VH0 + TH0 + VH0;   // a cube spans its top diamond + its rise
  const sc = Math.min(1, Math.max(0.3, (roomBot - roomTop) / glyphH), (W * 0.9) / glyphW);
  const TW = TW0 * sc, TH = TH0 * sc, VH = VH0 * sc;
  const x0 = W / 2 - (glyphW * sc) / 2 + TW / 2;                        // centre of column 0
  const y0 = (roomTop + roomBot) / 2 + (glyphH * sc) / 2 - TH / 2 - VH;  // centre of a level-0 top face
  // stroke order: columns left to right, each column's lower cube a half-step before its upper one
  const voxels = CHECK.map(([u, v]) => {
    const lower = CHECK.some(([u2, v2]) => u2 === u && v2 < v);
    return {sx: x0 + u * TW, sy: y0 - v * VH, v, order: u + (lower ? 0.5 : 0)};
  });
  // painter's order: the wall has no depth, so the only overlap is a cube over the top face of the one below
  const paint = [...voxels].sort((a, b) => a.v - b.v);
  const titleIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 34%, #131836, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {paint.map((v, idx) => {
          // the same window as before: first cube starts at 0.21, last at 0.44, each lands over 0.3
          const st = 0.21 + v.order * (0.23 / 6.5);
          const drop = easeOutBack(clamp01(seg(t, st, st + 0.3)));
          if (drop <= 0) return null;
          const dy = (1 - drop) * -DROP * sc;
          const sx = v.sx, sy = v.sy + dy;
          const top = `${pt(sx, sy - TH / 2)} ${pt(sx + TW / 2, sy)} ${pt(sx, sy + TH / 2)} ${pt(sx - TW / 2, sy)}`;
          const B2 = sy + TH / 2 + VH;
          const leftF = `${pt(sx - TW / 2, sy)} ${pt(sx, sy + TH / 2)} ${pt(sx, sy + TH / 2 + VH)} ${pt(sx - TW / 2, sy + VH)}`;
          const rightF = `${pt(sx, sy + TH / 2)} ${pt(sx + TW / 2, sy)} ${pt(sx + TW / 2, sy + VH)} ${pt(sx, B2)}`;
          return (
            <g key={idx} opacity={clamp01(drop * 1.4)}>
              <polygon points={leftF} fill={TONE} style={{filter: 'brightness(0.6)'}} />
              <polygon points={rightF} fill={TONE} style={{filter: 'brightness(0.82)'}} />
              <polygon points={top} fill={TONE} style={{filter: 'brightness(1.2)'}} stroke="#ffffff55" strokeWidth={1} />
            </g>
          );
        })}
      </svg>
      <div style={{position: 'absolute', bottom: bottomInset(W, H, 92) + TITLE_RISE, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#eafff4', font: `800 ${TITLE_PX}px/1 var(--f-display, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em',
        textShadow: '0 8px 40px #000'}}>{TITLE}</div>
      <div style={{position: 'absolute', bottom: bottomInset(W, H, 92), left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.72, 0.9)), color: '#9fd6bd',
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default VoxelBuild;
