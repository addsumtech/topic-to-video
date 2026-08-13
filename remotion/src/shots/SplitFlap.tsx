// SHOT · Split-Flap — a Solari departure-board register (mechanical, nostalgic-premium): a grid of flap tiles
// riffles through characters and SETTLES, staggered left→right, to spell the message. Amber-on-charcoal, a
// hairline split across each tile. The tactile "board updates" feel no digital shot has. Deterministic
// (each tile's flip stream + settle time = fn of cell + frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, clamp01, hash01, easeOutBack} from '../runtime/motion';

export const DURATION = 155; // ~5.2s
const CH = '▚ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789▸✓'.split('');
const DEFAULT_ROWS = ['WORKBUDDY', 'DELIVERED'];

export const SplitFlap: React.FC<{rows?: string[]}> = ({rows: ROWS = DEFAULT_ROWS} = {}) => {
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const COLS = Math.max(...ROWS.map((r) => r.length));
  const tw = 150, th = 178, gap = 14;
  const boardW = COLS * tw + (COLS - 1) * gap;
  const x0 = (W - boardW) / 2, y0 = (H - (ROWS.length * th + (ROWS.length - 1) * gap)) / 2;

  const tiles: React.ReactNode[] = [];
  ROWS.forEach((label, r) => {
    const pad = Math.floor((COLS - label.length) / 2);
    for (let c = 0; c < COLS; c++) {
      const ch = label[c - pad] ?? ' ';
      const settle = 0.14 + c * 0.05 + r * 0.14 + hash01(r * 40 + c) * 0.05;
      const settled = t >= settle;
      const shown = settled ? ch : CH[Math.floor(hash01(r * 97 + c * 13 + Math.floor(frame / 2)) * CH.length)];
      const justLanded = clamp01((t - settle) / 0.05);
      const flapScale = settled ? 1 : 0.96;
      const tx = x0 + c * (tw + gap), ty = y0 + r * (th + gap);
      tiles.push(
        <div key={`${r}-${c}`} style={{position: 'absolute', left: tx, top: ty, width: tw, height: th,
          transform: `scaleY(${flapScale})`}}>
          <div style={{position: 'absolute', inset: 0, borderRadius: 12, background: 'linear-gradient(#26262c 0%, #191920 49%, #0e0e12 51%, #1a1a20 100%)',
            border: '1px solid #000', boxShadow: 'inset 0 1px 0 #ffffff10, 0 8px 20px #0007'}} />
          {/* hairline split */}
          <div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: 2, background: '#000', opacity: 0.7}} />
          <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            font: '800 108px/1 "Anton", Impact, sans-serif', color: settled ? '#ffcf4a' : '#c9a24a',
            opacity: settled ? 1 : 0.86, transform: `translateY(${(1 - justLanded) * 0}px)`,
            textShadow: settled ? '0 0 18px #ffcf4a55' : 'none'}}>{shown === ' ' ? '' : shown}</div>
        </div>
      );
    }
  });

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 34%, #17171d 0%, #0a0a0e 72%)'}}>
      {/* board backing plate */}
      <div style={{position: 'absolute', left: x0 - 30, top: y0 - 30, width: boardW + 60,
        height: ROWS.length * th + (ROWS.length - 1) * gap + 60, borderRadius: 22, background: '#050506',
        border: '1px solid #23232a', boxShadow: '0 40px 120px #000b'}} />
      {tiles}
      {/* header label */}
      <div style={{position: 'absolute', left: 0, right: 0, top: y0 - 100, textAlign: 'center',
        color: '#6f7078', font: '700 26px/1 "JetBrains Mono", monospace', letterSpacing: '0.5em', paddingLeft: '0.5em'}}>STATUS · TODAY</div>
    </AbsoluteFill>
  );
};
export default SplitFlap;
