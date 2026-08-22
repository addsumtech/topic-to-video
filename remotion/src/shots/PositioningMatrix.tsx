// SHOT · Positioning Matrix — a 2×2 map: X and Y axes draw through the centre, labelled at their ends, then
// item dots drift to their positions and the HERO dot lands top-right with a ring + label. The "where things
// sit / who leads" register (family H — comparison). Positions are QUALITATIVE (illustrative unless a real
// film overrides items); no numeric axis, so nothing is asserted as a stat. Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

type Item = {label?: string; x?: number; y?: number; hero?: boolean};

export const DURATION = 150; // 5s

export const PositioningMatrix: React.FC<{
  title?: string; xAxis?: [string, string]; yAxis?: [string, string]; items?: Item[]}> = ({
  title: TITLE = 'The landscape', xAxis: XA = ['Simple', 'Powerful'], yAxis: YA = ['Manual', 'Automated'],
  items: ITEMS = [{label: 'A', x: 0.28, y: 0.34}, {label: 'B', x: 0.4, y: 0.6}, {label: 'C', x: 0.56, y: 0.3},
    {label: 'Us', x: 0.8, y: 0.82, hero: true}]} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const PLOT = 760, cx = W / 2, cy = H / 2 + 26;
  const x0 = cx - PLOT / 2, y0 = cy - PLOT / 2;
  const px = (x: number) => x0 + clamp01(x) * PLOT;
  const py = (y: number) => y0 + (1 - clamp01(y)) * PLOT; // y up
  const axis = easeOutCubic(seg(t, 0.08, 0.4));
  const titleIn = easeOutCubic(seg(t, 0.02, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(120% 100% at 50% 42%, #12162a, #090b12 72%)'}}>
      <div style={{position: 'absolute', top: 62, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#aeb6ca', font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* quadrant fill for hero corner */}
        <rect x={cx} y={y0} width={PLOT / 2} height={PLOT / 2} fill="#5b8cff10" opacity={clamp01(seg(t, 0.5, 0.7))} />
        {/* axes */}
        <line x1={x0} y1={cy} x2={x0 + PLOT * axis} y2={cy} stroke="#39405c" strokeWidth={2} />
        <line x1={cx} y1={y0 + PLOT} x2={cx} y2={y0 + PLOT - PLOT * axis} stroke="#39405c" strokeWidth={2} />
        {/* arrowheads */}
        <path d={`M${x0 + PLOT} ${cy} l-16 -8 l0 16 z`} fill="#39405c" opacity={axis} />
        <path d={`M${cx} ${y0} l-8 16 l16 0 z`} fill="#39405c" opacity={axis} />
      </svg>

      {/* axis end labels */}
      {([[XA[1], px(1) + 6, cy - 12, 'left'], [XA[0], x0 - 6, cy - 12, 'right'],
         [YA[1], cx + 16, y0 - 4, 'left'], [YA[0], cx + 16, y0 + PLOT + 6, 'left']] as const).map((L, i) => (
        <div key={i} style={{position: 'absolute', left: L[1], top: L[2], transform: L[3] === 'right' ? 'translateX(-100%)' : undefined,
          opacity: clamp01(seg(t, 0.3, 0.5)), color: '#8b93a8', font: '600 24px/1 var(--f-mono, "JetBrains Mono", monospace)',
          letterSpacing: '0.1em'}}>{L[0]}</div>
      ))}

      {/* item dots */}
      {ITEMS.map((it, i) => {
        const st = 0.42 + i * 0.1;
        const r = easeOutBack(clamp01(seg(t, st, st + 0.24)));
        const X = px(it.x ?? 0.5), Y = py(it.y ?? 0.5);
        const hero = !!it.hero;
        const size = hero ? 34 : 20;
        const col = hero ? '#5b8cff' : '#5a6478';
        const pulse = hero && t > st + 0.24 ? 1 + 0.12 * Math.max(0, Math.sin((t - st - 0.24) * 10)) * Math.exp(-(t - st - 0.24) * 3) : 1;
        return (
          <div key={i} style={{position: 'absolute', left: X, top: Y, transform: `translate(-50%,-50%) scale(${r * pulse})`}}>
            <div style={{width: size, height: size, borderRadius: '50%', background: col,
              boxShadow: hero ? `0 0 30px ${col}` : 'none', border: hero ? '3px solid #cdd8ff' : 'none'}} />
            {hero || (it.label && it.label.length > 1) ? (
              <div style={{position: 'absolute', left: size / 2 + 14, top: -4, whiteSpace: 'nowrap',
                color: hero ? '#eef2ff' : '#8b93a8', font: `${hero ? '800' : '600'} ${hero ? 32 : 22}px/1 Inter, system-ui, sans-serif`}}>{it.label}</div>
            ) : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default PositioningMatrix;
