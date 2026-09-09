// SHOT · Pixel Build — an 8-bit retro-game register (style axis): a chunky pixel checkmark assembles cell by
// cell on a CRT screen with a HUD (SCORE / 1UP), a brick ground, and a "COMPLETE" banner. Deliberately lo-fi,
// nostalgic-game. Deterministic (each pixel reveals on a diagonal sweep = fn of cell + t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, inkBlockH} from '../runtime/layout';

export const DURATION = 155; // ~5.2s

// An arcade HUD's own furniture. `1UP` and its three credit pips are what an arcade screen READS like —
// the form depicting itself, not copy about any topic. Declared so onscreen_text_qa can tell the two apart.
export const INTRINSIC_TEXT = ['1UP ▪▪▪'];
// pixel checkmark grid ('#' = lit)
const GRID = [
  '................',
  '...............#',
  '..............##',
  '.............##.',
  '#...........##..',
  '##.........##...',
  '.##.......##....',
  '..##.....##.....',
  '...##...##......',
  '....##.##.......',
  '.....###........',
];
const PX = 46;

export const PixelBuild: React.FC<{hud?: string; label?: string}> = ({
  hud = 'SCORE 9999',label = 'WORKBUDDY · COMPLETE'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const cols = GRID[0].length, rows = GRID.length;
  const gw = cols * PX, gh = rows * PX;
  // THE COMPLETE BANNER HANGS 30px UNDER THE GRID and the grid was centred on the frame, so the banner
  // landed 40px inside the caption band at 1:1. The grid and its banner are one object — the banner is what
  // the build is FOR — so the pair slides up by exactly what did not fit. Zero at 16:9 and 9:16.
  const BANNER = 68;                                                  // `700 68px/1`
  const gyRaw = (H - gh) / 2 - 40;
  const over = Math.max(0, gyRaw + gh + 30 + inkBlockH(BANNER) - contentBottom(W, H));
  const gx = (W - gw) / 2, gy = gyRaw - over;
  const maxSum = cols + rows;
  const banner = easeOutBack(seg(t, 0.7, 0.9));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('#0b0f2a'), overflow: 'hidden'}}>
      {/* HUD */}
      <div style={{position: 'absolute', left: 60, top: 44, color: '#ffe14d', font: '700 42px/1 var(--f-mono, "Press Start 2P", "VT323", monospace)', letterSpacing: '0.04em'}}>{hud}</div>
      <div style={{position: 'absolute', right: 60, top: 44, color: '#ff5b7f', font: '700 42px/1 var(--f-mono, "VT323", monospace)', letterSpacing: '0.04em'}}>1UP ▪▪▪</div>

      {/* the sprite */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}} shapeRendering="crispEdges">
        {GRID.map((row, r) => row.split('').map((c, x) => {
          if (c !== '#') return null;
          const reveal = clamp01((t * maxSum * 1.6 - (x + r)) / 1.2);
          if (reveal <= 0) return null;
          const s = easeOutBack(clamp01(reveal)) * PX;
          const px = gx + x * PX + (PX - s) / 2, py = gy + r * PX + (PX - s) / 2;
          return <g key={`${r}-${x}`}>
            <rect x={px} y={py} width={s} height={s} fill="#3ce06a" />
            <rect x={px} y={py} width={s} height={s * 0.32} fill="#8bffb0" />
            <rect x={px} y={py + s * 0.68} width={s} height={s * 0.32} fill="#22a04e" />
          </g>;
        }))}
      </svg>

      {/* brick ground */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}} shapeRendering="crispEdges">
        {[...Array(Math.ceil(W / 92))].map((_, i) => (
          <g key={i}>
            <rect x={i * 92} y={H - 96} width={90} height={44} fill="#8a4a1e" /><rect x={i * 92} y={H - 96} width={90} height={8} fill="#b06a34" />
            <rect x={i * 92 + 46} y={H - 52} width={90} height={44} fill="#8a4a1e" /><rect x={i * 92 + 46} y={H - 52} width={90} height={8} fill="#b06a34" />
          </g>
        ))}
      </svg>

      {/* COMPLETE banner */}
      <div style={{position: 'absolute', left: 0, right: 0, top: gy + gh + 30, textAlign: 'center', transform: `scale(${banner})`,
        opacity: banner > 0 ? 1 : 0, color: '#ffe14d', font: `700 ${BANNER}px/1 var(--f-mono, "Press Start 2P", "VT323", monospace)`,
        letterSpacing: '0.06em', textShadow: '5px 5px 0 #b23b00'}}>{label}</div>

      {/* CRT scanlines + vignette */}
      <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.4,
        background: 'repeating-linear-gradient(#0000 0 3px, #00000066 3px 4px)'}} />
      <AbsoluteFill style={{background: 'radial-gradient(120% 100% at 50% 50%, #0000 60%, #00000099 100%)', pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default PixelBuild;
