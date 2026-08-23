// SHOT · Blueprint Grid — the premium Vercel/Geist "technical" register: a faint measured grid, corner crop-
// marks, a schematic module DRAWN with thin strokes, dimension lines with arrowheads + mono spec labels, a
// centre crosshair with a coordinate readout. Near-monochrome + ONE accent = precision, not decoration.
// Deterministic (stroke-draw + counters = fn of t). Light, systematic, engineering-grade.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
// LEVEL-C: the whole blueprint flips with the DNA (paper→bg, ink→fg, grid→line, accent) so on a dark DNA it reads
// as a dark engineering drawing instead of pale strokes on white (inversion). Draw + the main component each read
// useDNA (Draw's stroke default can't reference the renamed const from the param scope — it derives inside).
const INK0 = '#1a2230', FAINT0 = '#c9d2de', ACC0 = '#2e6bff', MONO = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';

// stroke that draws itself over [a,b]
const Draw: React.FC<{d: string; t: number; a: number; b: number; len: number; stroke?: string; sw?: number; dash?: string}> =
  ({d, t, a, b, len, stroke, sw = 2, dash}) => {
    const dna = useDNA();
    const s = stroke ?? dna?.fg ?? INK0;
    return (
      <path d={d} fill="none" stroke={s} strokeWidth={sw} strokeLinecap="round"
        strokeDasharray={dash ?? len} strokeDashoffset={dash ? 0 : len * (1 - easeOutCubic(seg(t, a, b)))} opacity={dash ? easeOutCubic(seg(t, a, b)) : 1} />
    );
  };

export const BlueprintGrid: React.FC<{unit?: string; tag?: string; spec1?: string; spec2?: string; metricLabel?: string}> = ({
  unit = 'workbuddy.unit', tag = 'local-only', spec1 = 'runs on your machine', spec2 = '0 cloud calls', metricLabel = 'on-device'} = {}) => {
  const dna = useDNA();
  const INK = dna?.fg ?? INK0, FAINT = dna?.line ?? FAINT0, ACC = dna?.accent ?? ACC0, BG = dna?.bg ?? '#f6f8fb';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  // module box
  const mw = 720, mh = 380, mx = cx - mw / 2, my = cy - mh / 2;
  const sub = clamp01(seg(t, 0.4, 0.7)); // sub-blocks appear
  const specN = Math.round(lerp(0, 100, easeOutCubic(seg(t, 0.55, 0.9)))); // a counting readout

  return (
    <AbsoluteFill style={{background: BG}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M24 0H0V24" fill="none" stroke={FAINT} strokeWidth="1" opacity="0.5" />
          </pattern>
          <pattern id="grid5" width="120" height="120" patternUnits="userSpaceOnUse">
            <path d="M120 0H0V120" fill="none" stroke={FAINT} strokeWidth="1.4" opacity="0.8" />
          </pattern>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto">
            <path d="M0,0 L7,3 L0,6" fill="none" stroke={INK} strokeWidth="1.4" />
          </marker>
        </defs>
        {/* measured grid */}
        <rect width={W} height={H} fill="url(#grid)" />
        <rect width={W} height={H} fill="url(#grid5)" />

        {/* corner crop-marks */}
        {[[70, 70, 1, 1], [W - 70, 70, -1, 1], [70, H - 70, 1, -1], [W - 70, H - 70, -1, -1]].map(([x, y, sx, sy], i) => (
          <g key={i} stroke={INK} strokeWidth={2}>
            <line x1={x} y1={y} x2={(x as number) + 34 * (sx as number)} y2={y} />
            <line x1={x} y1={y} x2={x} y2={(y as number) + 34 * (sy as number)} />
          </g>
        ))}

        {/* schematic module (drawn) */}
        <Draw d={`M${mx},${my} h${mw} v${mh} h${-mw} Z`} t={t} a={0.1} b={0.42} len={2 * (mw + mh)} sw={2.4} />
        {/* accent header band of the module */}
        <Draw d={`M${mx},${my + 70} h${mw}`} t={t} a={0.34} b={0.5} len={mw} stroke={ACC} sw={2.4} />
        {/* sub-blocks */}
        {[0, 1, 2].map((i) => {
          const bx = mx + 40 + i * ((mw - 80) / 3), bw = (mw - 80) / 3 - 26;
          return <rect key={i} x={bx} y={my + 110} width={bw} height={mh - 160} rx={8} fill="none" stroke={INK} strokeWidth={1.6} opacity={sub} />;
        })}

        {/* horizontal dimension line under module */}
        <g opacity={easeOutCubic(seg(t, 0.5, 0.72))}>
          <line x1={mx} y1={my + mh + 60} x2={mx + mw} y2={my + mh + 60} stroke={INK} strokeWidth={1.6} markerStart="url(#arrow)" markerEnd="url(#arrow)" />
          <line x1={mx} y1={my + mh + 44} x2={mx} y2={my + mh + 76} stroke={INK} strokeWidth={1.4} />
          <line x1={mx + mw} y1={my + mh + 44} x2={mx + mw} y2={my + mh + 76} stroke={INK} strokeWidth={1.4} />
        </g>
        {/* vertical dimension line right of module */}
        <g opacity={easeOutCubic(seg(t, 0.58, 0.8))}>
          <line x1={mx + mw + 60} y1={my} x2={mx + mw + 60} y2={my + mh} stroke={INK} strokeWidth={1.6} markerStart="url(#arrow)" markerEnd="url(#arrow)" />
        </g>

        {/* centre crosshair */}
        <g opacity={easeOutCubic(seg(t, 0.66, 0.84))} stroke={ACC} strokeWidth={1.4}>
          <line x1={cx - 26} y1={cy} x2={cx + 26} y2={cy} /><line x1={cx} y1={cy - 26} x2={cx} y2={cy + 26} />
          <circle cx={cx} cy={cy} r={5} fill="none" />
        </g>
      </svg>

      {/* mono labels (HTML for crisp type) */}
      <div style={{position: 'absolute', left: mx, top: my - 44, color: INK, font: `600 24px/1 ${MONO}`, letterSpacing: '0.04em', opacity: clamp01(seg(t, 0.12, 0.3))}}>
        <span style={{color: ACC}}>◇</span> {unit} · <span style={{color: '#5b6675'}}>{tag}</span>
      </div>
      {[
        {x: cx, y: my + mh + 70, txt: spec1, anchor: 'center'},
        {x: mx + mw + 76, y: cy, txt: spec2, anchor: 'left'},
        {x: cx + 34, y: cy + 6, txt: `x:960  y:540`, anchor: 'left'},
      ].map((l, i) => (
        <div key={i} style={{position: 'absolute', left: l.x, top: l.y, transform: l.anchor === 'center' ? 'translateX(-50%)' : 'none',
          color: '#48566a', font: `600 22px/1 ${MONO}`, opacity: easeOutCubic(seg(t, 0.6, 0.86)), whiteSpace: 'nowrap'}}>{l.txt}</div>
      ))}
      {/* a counting spec readout, top-right */}
      <div style={{position: 'absolute', right: 120, top: 120, textAlign: 'right', opacity: clamp01(seg(t, 0.55, 0.78))}}>
        <div style={{color: INK, font: `800 80px/1 ${MONO}`, fontVariantNumeric: 'tabular-nums'}}>{specN}<span style={{color: ACC}}>%</span></div>
        <div style={{color: '#5b6675', font: `600 22px/1 ${MONO}`, marginTop: 6}}>{metricLabel}</div>
      </div>
    </AbsoluteFill>
  );
};
export default BlueprintGrid;
