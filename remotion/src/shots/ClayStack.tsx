// SHOT · Clay Stack — a soft-3D claymation register (tactile "style" axis): matte pastel rounded blocks with
// soft cast shadows + top-light highlights DROP and settle into a little stack, then a clay checkmark pops on
// top. Warm, friendly, hand-made-toy feel — faux-3D via layered gradients (no WebGL). Deterministic (drop = t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack} from '../runtime/motion';
import {useDNA, dnaPalette, tint, shade} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';

export const DURATION = 160; // ~5.3s

const ClayBlock: React.FC<{x: number; y: number; w: number; h: number; base: string; hi: string; sh: string; id: string; drop: number}> =
  ({x, y, w, h, base, hi, sh, id, drop}) => {
    const dy = (1 - drop) * -520;            // falls from above
    const squash = 1 + Math.sin(clamp01(drop) * Math.PI) * 0.0; // (settle handled by easeOutBack)
    return (
      <g transform={`translate(0 ${dy})`} opacity={drop > 0 ? 1 : 0}>
        <defs>
          <radialGradient id={`hi${id}`} cx="32%" cy="26%" r="80%"><stop offset="0" stopColor={hi} /><stop offset="0.55" stopColor={base} /><stop offset="1" stopColor={sh} /></radialGradient>
        </defs>
        {/* soft cast shadow */}
        <ellipse cx={x + w / 2} cy={y + h + 26} rx={w * 0.5} ry={22} fill="#00000022" />
        {/* body */}
        <rect x={x} y={y} width={w} height={h * squash} rx={h * 0.42} fill={`url(#hi${id})`} />
        {/* bottom contact shade */}
        <rect x={x + 10} y={y + h - 26} width={w - 20} height={22} rx={11} fill={sh} opacity={0.5} />
        {/* specular dab */}
        <ellipse cx={x + w * 0.3} cy={y + h * 0.28} rx={w * 0.16} ry={h * 0.14} fill="#ffffff" opacity={0.5} />
      </g>
    );
  };

export const ClayStack: React.FC<{label?: string}> = ({label = 'built, piece by piece'} = {}) => {
  // LEVEL-C: claymation is a MATERIAL (matte body + top-light highlight + contact shade + soft cast shadow), not a
  // fixed pastel set — each block's base comes from the DNA and its highlight/shade are TINT/SHADE of that base, so
  // the clay still reads as clay in the film's hues. Null DNA = the original warm pastel stack.
  const dna = useDNA();
  const P = dnaPalette(dna, 3);
  const clay = (i: number, base0: string, hi0: string, sh0: string) =>
    P ? {base: P[i], hi: tint(P[i], 0.45), sh: shade(P[i], 0.3)} : {base: base0, hi: hi0, sh: sh0};
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, groundY = H * 0.72;
  const blocks = [
    {w: 460, h: 168, ...clay(0, '#f7b7a3', '#ffd8c9', '#d98a72'), at: 0.08},
    {w: 380, h: 156, ...clay(1, '#b9a9f0', '#ddd3fb', '#8f7fd0'), at: 0.24},
    {w: 300, h: 146, ...clay(2, '#9fe6c8', '#cbf5e3', '#6dbf9d'), at: 0.4},
  ];
  let cursorY = groundY;
  const laid = blocks.map((b) => {const y = cursorY - b.h; cursorY = y; return {...b, x: cx - b.w / 2, y};});
  const checkDrop = easeOutBack(seg(t, 0.6, 0.82));
  const topY = laid[laid.length - 1].y;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% 30%, #fff5ee 0%, #ffe9dd 55%, #f6d8c8 100%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* ground plane soft shadow */}
        <ellipse cx={cx} cy={groundY + 34} rx={360} ry={40} fill="#00000018" />
        {laid.map((b, i) => (
          <ClayBlock key={i} id={`b${i}`} x={b.x} y={b.y} w={b.w} h={b.h} base={b.base} hi={b.hi} sh={b.sh}
            drop={easeOutBack(seg(t, b.at, b.at + 0.2))} />
        ))}
        {/* clay checkmark pops on top */}
        <g transform={`translate(${cx} ${topY - 90}) scale(${checkDrop})`} opacity={checkDrop > 0 ? 1 : 0}>
          <ellipse cx={0} cy={70} rx={70} ry={16} fill="#00000018" />
          <path d="M-46,4 L-14,40 L52,-40" fill="none" stroke={dna?.accent2 ?? '#3fbf77'} strokeWidth={34} strokeLinecap="round" strokeLinejoin="round" />
          <path d="M-46,4 L-14,40 L52,-40" fill="none" stroke={dna ? tint(dna.accent2, 0.5) : '#8ef0b6'} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" opacity={0.6} />
        </g>
      </svg>

      {/* soft label */}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: bottomInset(W, H, H * 0.12), textAlign: 'center',
        opacity: clamp01(seg(t, 0.78, 0.95)), color: dna?.dim ?? '#8a5b48', font: '800 46px/1 var(--f-body, "Baloo 2", Inter, sans-serif)'}}>{label}</div>
    </AbsoluteFill>
  );
};
export default ClayStack;
