// SHOT · Data Orrery — an orbiting "solar-system of your work" register: a glowing core with perspective-tilted
// orbital rings, each carrying a labeled data node that ORBITS continuously (nodes pass behind the core for real
// depth). Distinct from RadialBurst (static bloom) + KnowledgeGraph (static graph) — this MOVES in orbit.
// Deterministic (each node's angle = base + t·speed).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 170; // ~5.7s
const DEFAULT_RINGS = [
  {rx: 300, ry: 96, speed: 1.0, base: 0.2, label: 'Docs', c: '#4c8dff'},
  {rx: 470, ry: 150, speed: -0.7, base: 2.4, label: 'Code', c: '#22d3c5'},
  {rx: 640, ry: 205, speed: 0.5, base: 4.1, label: 'Tasks', c: '#b06cff'},
  {rx: 800, ry: 262, speed: -0.38, base: 1.0, label: 'Comms', c: '#ff8fc7'},
];

export const DataOrrery: React.FC<{items?: string[]; hub?: string}> = ({items, hub: HUB = 'WorkBuddy'} = {}) => {
  const RINGS = items ? DEFAULT_RINGS.map((r, i) => ({...r, label: items[i % items.length]})) : DEFAULT_RINGS;
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const core = easeOutBack(seg(t, 0.02, 0.2));

  const nodeAt = (r: typeof RINGS[number]) => {
    const a = r.base + t * r.speed * Math.PI * 2;
    return {x: cx + Math.cos(a) * r.rx, y: cy + Math.sin(a) * r.ry, front: Math.sin(a) >= 0};
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% 46%, #0e1330 0%, #070a1c 60%, #04050f 100%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="og"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <radialGradient id="ocore"><stop offset="0" stopColor="#eaf0ff" /><stop offset="0.5" stopColor="#7aa2ff" /><stop offset="1" stopColor="#3a5cff" stopOpacity="0" /></radialGradient>
        </defs>

        {/* orbit rings (tilted ellipses) appear staggered */}
        {RINGS.map((r, i) => {
          const on = easeOutCubic(seg(t, 0.1 + i * 0.08, 0.34 + i * 0.08));
          return <ellipse key={`e${i}`} cx={cx} cy={cy} rx={r.rx} ry={r.ry} fill="none" stroke={r.c} strokeWidth={1.6} strokeOpacity={0.28 * on} />;
        })}

        {/* nodes BEHIND the core */}
        {RINGS.map((r, i) => {
          const n = nodeAt(r); if (n.front) return null;
          const on = easeOutBack(seg(t, 0.2 + i * 0.08, 0.4 + i * 0.08));
          return <circle key={`nb${i}`} cx={n.x} cy={n.y} r={12 * on} fill={r.c} opacity={0.45} filter="url(#og)" />;
        })}

        {/* core */}
        <g transform={`translate(${cx} ${cy}) scale(${core})`}>
          <circle r={140} fill="url(#ocore)" opacity={0.7} />
          <circle r={60} fill="#0c1330" stroke="#8fb0ff" strokeWidth={3} filter="url(#og)" />
          <circle r={34} fill="#cfe0ff" filter="url(#og)" />
        </g>

        {/* nodes IN FRONT of the core */}
        {RINGS.map((r, i) => {
          const n = nodeAt(r); if (!n.front) return null;
          const on = easeOutBack(seg(t, 0.2 + i * 0.08, 0.4 + i * 0.08));
          return <g key={`nf${i}`}><circle cx={n.x} cy={n.y} r={30 * on} fill={r.c} opacity={0.18} />
            <circle cx={n.x} cy={n.y} r={13 * on} fill="#f2f7ff" filter="url(#og)" />
            <circle cx={n.x} cy={n.y} r={13 * on} fill="none" stroke={r.c} strokeWidth={3} /></g>;
        })}
      </svg>

      {/* node labels (front only, HTML) */}
      {RINGS.map((r, i) => {
        const n = nodeAt(r); const on = clamp01(seg(t, 0.3 + i * 0.08, 0.46 + i * 0.08));
        if (!n.front) return null;
        return <div key={i} style={{position: 'absolute', left: n.x, top: n.y + 26, transform: 'translateX(-50%)', opacity: on,
          padding: '4px 14px', borderRadius: 999, background: '#0b122acc', border: `1px solid ${r.c}66`,
          color: '#dbe5f5', font: `600 24px/1 var(--f-body, Inter, system-ui, sans-serif)`, whiteSpace: 'nowrap'}}>{r.label}</div>;
      })}
      <div style={{position: 'absolute', left: 0, right: 0, top: cy + 150, textAlign: 'center',
        opacity: clamp01(seg(t, 0.18, 0.34)), color: '#eaf0ff', font: `800 40px/1 var(--f-body, Inter, system-ui, sans-serif)`,
        letterSpacing: '-0.01em', textShadow: '0 2px 20px #000'}}>{HUB}</div>
    </AbsoluteFill>
  );
};
export default DataOrrery;
