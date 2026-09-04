// SHOT · Knowledge Graph — a generative constellation: a central WorkBuddy node, then connections REACH OUT
// (edges draw) and concept nodes POP into a connected graph — "your whole workspace, wired into one brain."
// Distinct from MapRoutes (geographic hub-spoke): abstract force-graph layout + inter-node chords + labels.
// Deterministic (angles/jitter seeded by index; edge draw + node pop = staggered fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack, hash01, life} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 165; // 5.5s
const NODE_PALETTE0 = ['#4c8dff', '#22d3c5', '#b06cff', '#ff8fc7', '#ffd23f', '#2fcb6e', '#ff6b6b'];

export const KnowledgeGraph: React.FC<{items?: string[]; hub?: string}> = ({
  items = ['Docs', 'Code', 'Slack', 'Calendar', 'Email', 'Tasks', 'Notes'], hub: HUB = 'WorkBuddy'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const NODE_PALETTE = dnaPalette(dna, 7) ?? NODE_PALETTE0;
  const NODES = items.map((label, i) => ({label, c: NODE_PALETTE[i % NODE_PALETTE.length]}));
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  // Centred on the CONTENT ZONE, not the frame, and scaled to it. Centred on H/2 with a fixed radius the
  // lowest node landed inside the strip the renderer burns the caption over, so a node label and a subtitle
  // drew on top of each other. Deriving both from the zone also makes the layout right at aspects the fixed
  // radius was never checked against.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const cx = W / 2, cy = (zTop + zBot) / 2;
  // 430 is the largest radius the spread below can produce. NODE_ROOM is what hangs BELOW a node's centre,
  // summed from the pieces rather than estimated: the label's 34px offset, its 24px type with 5px padding
  // top and bottom and a 1px border, and the 8px vertical bob. Estimated at 46 it left 'Calendar' 14px
  // inside the band — close enough to look fixed and not be.
  const NODE_ROOM = 34 + (24 + 5 * 2 + 2) + 8;
  const rScale = Math.min(1, ((zBot - zTop) / 2 - NODE_ROOM) / 430);
  // A LIVING SYSTEM KEEPS TURNING. At 0.18 rad across the whole clip this was ten degrees in five seconds —
  // a rotation nobody can see, so the register measured 0.0005 frame difference and read as a still diagram.
  // Rotation is not translation, so it stays invisible to scripts/shake_qa.py; and one revolution takes
  // ~35s, far slower than anything that could read as a wobble.
  const drift = t * 0.9;    // whole-graph slow rotate
  const pos = (i: number) => {
    const a = (i / NODES.length) * Math.PI * 2 - Math.PI / 2 + drift + (hash01(i) - 0.5) * 0.12;
    const R = (360 + hash01(i * 2) * 70) * rScale;
    // Each node breathes on its OWN period, so the constellation lives rather than turning as one rigid
    // wheel — periods seconds apart, an order of magnitude below anything that reads as vibration. The
    // AMPLITUDE is the authored 8px, unchanged: the diagnosed defect was a rotation nobody could see, and
    // enlarging an amplitude nobody complained about is exactly the unjustified step by which "living"
    // becomes "wobbling". A first pass raised it to 13px for no reason and it was put back.
    const bob = (life(t, durationInFrames, fps, 5 + (i % 4) * 1.3, i * 0.19) - 0.5) * 16;
    return {x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R + bob};
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% 45%, #0e1424 0%, #070a12 66%, #04060b 100%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="ng"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <radialGradient id="halo"><stop offset="0" stopColor={dna?.accent2 ?? "#7aa2ff"} stopOpacity="0.5" /><stop offset="1" stopColor={dna?.accent2 ?? "#7aa2ff"} stopOpacity="0" /></radialGradient>
        </defs>

        {/* spokes: center → node, drawn staggered */}
        {NODES.map((n, i) => {
          const at = 0.1 + i * 0.06;
          const draw = easeOutCubic(seg(t, at, at + 0.14));
          const p = pos(i);
          const ex = lerp(cx, p.x, draw), ey = lerp(cy, p.y, draw);
          return <line key={i} x1={cx} y1={cy} x2={ex} y2={ey} stroke={n.c} strokeWidth={2.5} strokeOpacity={0.5} filter="url(#ng)" />;
        })}
        {/* chords between neighbours (drawn later → makes it a graph, not a star) */}
        {[[0, 1], [1, 5], [2, 3], [4, 6], [5, 6]].map(([a, b], k) => {
          const draw = easeOutCubic(seg(t, 0.62 + k * 0.05, 0.78 + k * 0.05));
          const pa = pos(a), pb = pos(b);
          const ex = lerp(pa.x, pb.x, draw), ey = lerp(pa.y, pb.y, draw);
          return <line key={`c${k}`} x1={pa.x} y1={pa.y} x2={ex} y2={ey} stroke="#3a4a6b" strokeWidth={1.6} strokeOpacity={0.35 * draw} />;
        })}

        {/* concept nodes pop at spoke completion */}
        {NODES.map((n, i) => {
          const at = 0.1 + i * 0.06 + 0.12;
          const pop = easeOutBack(seg(t, at, at + 0.16));
          const p = pos(i);
          if (pop <= 0) return null;
          return (
            <g key={i} transform={`translate(${p.x},${p.y}) scale(${pop})`}>
              <circle r={40} fill="url(#halo)" />
              <circle r={16} fill={n.c} filter="url(#ng)" />
              <circle r={16} fill="none" stroke="#eaf1ff" strokeWidth={2.5} />
            </g>
          );
        })}

        {/* central WorkBuddy node */}
        {(() => {
          const pop = easeOutBack(seg(t, 0.02, 0.18));
          const pulse = 1 + Math.sin(t * Math.PI * 4) * 0.03;
          return (
            <g transform={`translate(${cx},${cy}) scale(${pop * pulse})`}>
              <circle r={92} fill="url(#halo)" />
              <circle r={54} fill="#0b1220" stroke={dna?.accent2 ?? "#7aa2ff"} strokeWidth={3} filter="url(#ng)" />
              <circle r={30} fill={dna?.accent ?? "#4c8dff"} filter="url(#ng)" />
            </g>
          );
        })()}
      </svg>

      {/* node labels (HTML for crisp type) */}
      {NODES.map((n, i) => {
        const at = 0.1 + i * 0.06 + 0.16;
        const show = clamp01(seg(t, at, at + 0.14));
        const p = pos(i);
        return (
          <div key={i} style={{position: 'absolute', left: p.x, top: p.y + 34, transform: 'translateX(-50%)', opacity: show,
            padding: '5px 14px', borderRadius: 999, background: '#0c1424cc', border: `1px solid ${n.c}66`,
            color: '#dbe5f5', font: `600 24px/1 var(--f-body, Inter, system-ui, sans-serif)`, whiteSpace: 'nowrap'}}>{n.label}</div>
        );
      })}
      {/* center label */}
      <div style={{position: 'absolute', left: cx, top: cy + 96, transform: 'translateX(-50%)',
        opacity: clamp01(seg(t, 0.16, 0.3)), color: '#eaf1ff', font: `800 34px/1 var(--f-body, Inter, system-ui, sans-serif)`,
        letterSpacing: '-0.01em', whiteSpace: 'nowrap'}}>{HUB}</div>
    </AbsoluteFill>
  );
};
export default KnowledgeGraph;
