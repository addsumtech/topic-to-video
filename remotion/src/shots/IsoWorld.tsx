// SHOT · Iso World — an isometric diorama builds itself: a tiled ground grid draws in, then labelled BLOCKS
// (buildings) rise from it in an outward ripple, each a proper iso cube (shaded top/left/right faces). A
// little world / workspace-as-a-city (family N · isometric). Deterministic (heights fixed by index, rise = fn
// of t). True iso projection, painter's-ordered back-to-front.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
const BG_D0 = '#0a0d1a';
const TONES = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff', '#4dd0e1'];
const G = 7, TW = 150, TH = 76;

export const IsoWorld: React.FC<{items?: string[]; title?: string}> = ({
  items: ITEMS = ['Docs', 'Chat', 'Data', 'Code', 'Team'], title: TITLE = 'Your world, built'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H * 0.4;
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const pt = (sx: number, sy: number) => `${sx.toFixed(1)},${sy.toFixed(1)}`;

  type Cell = {i: number; j: number; sx: number; sy: number; block: boolean; hFrac: number; tone: string; label?: string};
  const cells: Cell[] = [];
  let labelN = 0;
  for (let i = 0; i < G; i++) for (let j = 0; j < G; j++) {
    const sx = cx + (i - j) * (TW / 2), sy = cy + (i + j) * (TH / 2);
    const seed = hash01(i * 12.7 + j * 31.3);
    const block = seed > 0.52;
    const isLabel = block && labelN < ITEMS.length && hash01(i * 3.1 + j * 9.9) > 0.6;
    cells.push({i, j, sx, sy, block, hFrac: 0.5 + seed * 0.9, tone: TONES[(i * 3 + j) % TONES.length],
      label: isLabel ? ITEMS[labelN++] : undefined});
  }
  cells.sort((a, b) => a.i + a.j - (b.i + b.j)); // back-to-front

  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 34%, #131a33, ${BG} 74%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 76, left: 0, right: 0, textAlign: 'center', opacity: titleIn, zIndex: 5,
        color: '#aeb6ca', font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {cells.map((c, idx) => {
          const wave = (c.i + c.j) / (2 * G);
          const tileIn = easeOutCubic(clamp01(seg(t, 0.06 + wave * 0.3, 0.28 + wave * 0.3)));
          const {sx, sy} = c;
          // ground diamond
          const ground = `${pt(sx, sy - TH / 2)} ${pt(sx + TW / 2, sy)} ${pt(sx, sy + TH / 2)} ${pt(sx - TW / 2, sy)}`;
          if (!c.block) {
            return <polygon key={idx} points={ground} fill="#18203a" stroke="#26304f" strokeWidth={1}
              opacity={tileIn * 0.9} style={{transformBox: 'fill-box', transformOrigin: 'center', transform: `scale(${lerp(0.7, 1, tileIn)})`}} />;
          }
          const rise = easeOutBack(clamp01(seg(t, 0.2 + wave * 0.32, 0.5 + wave * 0.32)));
          const h = 150 * c.hFrac * rise;
          const T2 = sy - TH / 2 - h, Ry = sy - h, B2 = sy + TH / 2 - h, Ly = sy - h;
          const top = `${pt(sx, T2)} ${pt(sx + TW / 2, Ry)} ${pt(sx, B2)} ${pt(sx - TW / 2, Ly)}`;
          const leftF = `${pt(sx - TW / 2, sy)} ${pt(sx, sy + TH / 2)} ${pt(sx, B2)} ${pt(sx - TW / 2, Ly)}`;
          const rightF = `${pt(sx, sy + TH / 2)} ${pt(sx + TW / 2, sy)} ${pt(sx + TW / 2, Ry)} ${pt(sx, B2)}`;
          return (
            <g key={idx} opacity={clamp01(tileIn * 1.4)}>
              <polygon points={ground} fill="#141b32" stroke="#26304f" strokeWidth={1} />
              <polygon points={leftF} fill={c.tone} style={{filter: 'brightness(0.6)'}} />
              <polygon points={rightF} fill={c.tone} style={{filter: 'brightness(0.82)'}} />
              <polygon points={top} fill={c.tone} style={{filter: 'brightness(1.15)'}} stroke="#ffffff44" strokeWidth={1} />
            </g>
          );
        })}
      </svg>

      {/* floating labels above the tallest labelled blocks */}
      {cells.filter((c) => c.label).map((c, k) => {
        const wave = (c.i + c.j) / (2 * G);
        const rise = easeOutBack(clamp01(seg(t, 0.2 + wave * 0.32, 0.5 + wave * 0.32)));
        const h = 150 * c.hFrac * rise;
        const on = clamp01(seg(t, 0.5 + wave * 0.2, 0.7 + wave * 0.2));
        return (
          <div key={k} style={{position: 'absolute', left: c.sx, top: c.sy - TH / 2 - h - 54,
            transform: 'translate(-50%, 0)', opacity: on, zIndex: 4,
            padding: '8px 18px', borderRadius: 10, background: '#0e1426',
            border: `1px solid ${c.tone}`, color: '#eef2ff', font: '700 26px/1 Inter, system-ui, sans-serif',
            whiteSpace: 'nowrap', boxShadow: '0 8px 24px #0008'}}>{c.label}</div>
        );
      })}
    </AbsoluteFill>
  );
};
export default IsoWorld;
