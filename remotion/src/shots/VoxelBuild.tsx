// SHOT · Voxel Build — an ISOMETRIC object assembles voxel by voxel: cubes drop in from above (staggered by
// depth) and stack into a checkmark, each a shaded iso cube (top/left/right). Isometric is a 2D drawing
// convention with no camera and no vanishing point — a legitimate one, and not the same thing as 3D, which
// is what this header used to call it. Playful voxel craft, true iso
// (family N · isometric). Deterministic (cube drop = fn of t + fixed shape).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#0a0d1c', ACC_D0 = '#37d68a';
const TW = 96, TH = 54, VH = 66; // tile width/height + voxel rise height

export const VoxelBuild: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Built to last', tagline: TAG = 'block by block', accent: accentProp} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0, ACC = dna?.accent ?? ACC_D0;
  const TONE = accentProp ?? ACC;   // prop wins; else the DNA accent (was a param default referencing the module const)
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2 - 40, cy = H / 2 - 40;
  const pt = (x: number, y: number) => `${x.toFixed(1)},${y.toFixed(1)}`;
  // checkmark footprint in (i,j) grid, each stacked 2 voxels tall
  const foot: [number, number][] = [[0, 3], [1, 4], [2, 5], [3, 4], [4, 3], [5, 2], [6, 1], [7, 0]];
  const voxels: {i: number; j: number; k: number; sx: number; sy: number; order: number}[] = [];
  for (const [i, j] of foot) for (let k = 0; k < 2; k++) {
    const sx = cx + (i - j) * (TW / 2), sy = cy + (i + j) * (TH / 2) - k * VH;
    voxels.push({i, j, k, sx, sy, order: i + j + k * 0.5});
  }
  voxels.sort((a, b) => a.order - b.order);
  const titleIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 34%, #131836, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {voxels.map((v, idx) => {
          const st = 0.06 + v.order * 0.05;
          const drop = easeOutBack(clamp01(seg(t, st, st + 0.3)));
          if (drop <= 0) return null;
          const dy = (1 - drop) * -260;
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
      <div style={{position: 'absolute', bottom: bottomInset(W, H, 92) + 58, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#eafff4', font: '800 88px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.02em',
        textShadow: '0 8px 40px #000'}}>{TITLE}</div>
      <div style={{position: 'absolute', bottom: bottomInset(W, H, 92), left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.72, 0.9)), color: '#9fd6bd',
        font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default VoxelBuild;
