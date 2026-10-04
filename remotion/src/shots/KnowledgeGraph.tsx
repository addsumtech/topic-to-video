// SHOT · Knowledge Graph — a generative constellation: a central WorkBuddy node, then connections REACH OUT
// (edges draw) and concept nodes POP into a connected graph — "your whole workspace, wired into one brain."
// Distinct from MapRoutes (geographic hub-spoke): abstract force-graph layout + labels, and inter-node chords
// exactly where the film passes `links`.
// Deterministic (angles/jitter seeded by index; edge draw + node pop = staggered fn of t).
//
// A CHORD IS A CLAIM THAT TWO THINGS ARE CONNECTED, SO ONLY THE FILM DRAWS ONE. The chords between nodes came
// from a fixed index table — `[[0,1],[1,5],[2,3],[4,6],[5,6]]` — so every film's first and second items were
// wired together, its second and sixth, its fifth and seventh. A film naming seven organs got a line from the
// heart to the skin; a film naming four had indices 5 and 6 wrap to `undefined` positions and lines drawn to
// nowhere. Chords now come from `links` — pairs of node indices or labels — and a film that passes none gets
// the hub's spokes only: every item connected to the hub, which is what naming them around it already says,
// and nothing connected to anything else. A link naming a node that is not there throws. The demo keeps its
// own five chords in its own data.

//
// THE TWO MARKS DRAWN ON THE GROUND ARE THE FILM'S. The hub's label and the rim around every node were
// literal near-whites, and all eight DNA presets are near-black, so on a film whose DNA came from a
// warm-white deck the hub had no name and every node lost its edge (`scripts/ink_contrast_qa.py`: 41.6% of
// this register's marks under 3:1, largest connected hole 0.29% of the frame — small because they are the
// only two things here that touch the ground). Everything else was checked against the light probe render
// and left alone on purpose: the node LABELS ride dark pills that carry their own ground, the chords are a
// mid slate that reads on either, and the halos are GLOW — a glow that stops showing on paper costs a
// reader nothing, because what it separates the node from is a darkness that is no longer there.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack, hash01, life} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s
const NODE_PALETTE0 = ['#4c8dff', '#22d3c5', '#b06cff', '#ff8fc7', '#ffd23f', '#2fcb6e', '#ff6b6b'];
// The literals this register was authored in, hoisted so an un-themed render is byte-for-byte what it was.
const RIM_D0 = '#eaf1ff';        // the ring on every node's edge
const HUB_D0 = '#eaf1ff';        // the hub's name, under the hub

const DEFAULT_ITEMS = ['Docs', 'Code', 'Slack', 'Calendar', 'Email', 'Tasks', 'Notes'];
// the demo's own chords, drawn only while the demo's own nodes are showing — never between a film's nodes
// @decor: the standalone demo's chords only — used when `items` is the untouched demo list and `links` is absent; a film's nodes get only the links it passes
const DEMO_LINKS: [number, number][] = [[0, 1], [1, 5], [2, 3], [4, 6], [5, 6]];
// Eight nodes is what the ring carries at 1:1 before neighbouring labels of a word or two start to touch.
export const MAX_GRAPH_NODES = 8;
export type GraphLink = [number | string, number | string];

export const KnowledgeGraph: React.FC<{items?: string[]; hub?: string; links?: GraphLink[]}> = ({
  items = DEFAULT_ITEMS, hub: HUB = 'WorkBuddy', links: LINKS} = {}) => {
  if (!Array.isArray(items) || items.length < 1 || items.length > MAX_GRAPH_NODES) {
    throw new Error(`KnowledgeGraph needs 1-${MAX_GRAPH_NODES} \`items\` (got ${Array.isArray(items) ? items.length : typeof items}). ` +
      'Each is one node on the ring around the hub; past eight the labels collide — group the nodes or cast a list register.');
  }
  items.forEach((it, i) => {
    if (!String(it ?? '').trim()) throw new Error(`KnowledgeGraph: item ${i + 1} is empty.`);
  });
  // RESOLVE THE CHORDS: an index or a label, both must name a node that exists; a self-link and a repeat are
  // refused/merged rather than drawn as a dot or a double line.
  const resolve = (end: unknown, k: number): number => {
    const idx = typeof end === 'number' ? end : items.findIndex((it) => it === end);
    if (!(Number.isInteger(idx) && idx >= 0 && idx < items.length)) {
      throw new Error(`KnowledgeGraph: link ${k + 1} names ${JSON.stringify(end)}, which is not a node — pass an index ` +
        `(0-${items.length - 1}) or one of the item labels exactly.`);
    }
    return idx;
  };
  const rawLinks = LINKS !== undefined ? LINKS : (items === DEFAULT_ITEMS ? DEMO_LINKS : []);
  if (!Array.isArray(rawLinks)) throw new Error('KnowledgeGraph: `links` must be an array of [a, b] pairs.');
  const seen = new Set<string>();
  const chords: [number, number][] = [];
  rawLinks.forEach((l, k) => {
    if (!Array.isArray(l) || l.length !== 2) throw new Error(`KnowledgeGraph: link ${k + 1} must be a pair [a, b], got ${JSON.stringify(l)}.`);
    const a = resolve(l[0], k), b = resolve(l[1], k);
    if (a === b) throw new Error(`KnowledgeGraph: link ${k + 1} connects "${items[a]}" to itself.`);
    const key = a < b ? `${a}-${b}` : `${b}-${a}`;
    if (!seen.has(key)) { seen.add(key); chords.push([a, b]); }
  });
  const t = useT();
  const glide = useGlide();
  const dna = useDNA();
  // A node's rim and the hub's name are the only marks here drawn straight onto the film's ground, so they
  // are the film's ink. The rim is what separates a node from that ground; on paper that has to be dark.
  const rim = dna?.fg ?? RIM_D0;
  const hubInk = dna?.fg ?? HUB_D0;
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
        {/* chords the FILM asserted (drawn later → a graph, not a star); none given → spokes only. The stagger
            closes up with the count so the last chord has finished drawing by the end (five keep 0.05). */}
        {chords.map(([a, b], k) => {
          const step = chords.length > 1 ? Math.min(0.05, 0.2 / (chords.length - 1)) : 0;
          const draw = easeOutCubic(seg(t, 0.62 + k * step, 0.78 + k * step));
          const pa = pos(a), pb = pos(b);
          // A CHORD THROUGH THE HUB IS INVISIBLE: between two nodes on opposite sides of the ring the straight
          // line runs under the hub and along two spokes, so a link the film asserted drew nothing anyone could
          // see (found on an 8-node render: node 4 to node 0). Such a chord bows out just far enough to clear the
          // hub's halo; every other chord stays the straight line it always was.
          const dx = pb.x - pa.x, dy = pb.y - pa.y, len = Math.max(1, Math.hypot(dx, dy));
          const mx = (pa.x + pb.x) / 2, my = (pa.y + pb.y) / 2;
          const dist = Math.abs(dx * (pa.y - cy) - dy * (pa.x - cx)) / len;   // hub centre to the chord's line
          const CLEAR = 80;                                                   // the hub disc (r 54) plus its glow
          let nx = -dy / len, ny = dx / len;                                  // unit normal, pointed away from the hub
          if ((mx - cx) * nx + (my - cy) * ny < 0) { nx = -nx; ny = -ny; }
          const bow = Math.max(0, CLEAR - dist) * 2;                          // a quadratic's apex sits at half its control offset
          const d = `M${pa.x},${pa.y} Q${mx + nx * bow},${my + ny * bow} ${pb.x},${pb.y}`;
          return <path key={`c${k}`} d={d} fill="none" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - draw}
            stroke="#3a4a6b" strokeWidth={1.6} strokeOpacity={0.35 * draw} />;
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
              <circle r={16} fill="none" stroke={rim} strokeWidth={2.5} />
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
          // the constellation keeps turning for the whole clip (`drift`, by design — "a living system keeps
          // turning"), so the label's position is never a settled `top`/`left`; it carries the unlock for the
          // whole beat rather than a span that would have to end on motion that does not
          <div key={i} style={{position: 'absolute', left: p.x, top: p.y + 34, transform: glide('translateX(-50%)', true), opacity: show,
            padding: '5px 14px', borderRadius: 999, background: '#0c1424cc', border: `1px solid ${n.c}66`,
            color: '#dbe5f5', font: `600 24px/1 var(--f-body, Inter, system-ui, sans-serif)`, whiteSpace: 'nowrap'}}>{n.label}</div>
        );
      })}
      {/* center label — the one word here with no pill under it, so it reads straight off the ground */}
      <div style={{position: 'absolute', left: cx, top: cy + 96, transform: 'translateX(-50%)',
        opacity: clamp01(seg(t, 0.16, 0.3)), color: hubInk, font: `800 34px/1 var(--f-body, Inter, system-ui, sans-serif)`,
        letterSpacing: '-0.01em', whiteSpace: 'nowrap'}}>{HUB}</div>
    </AbsoluteFill>
  );
};
export default KnowledgeGraph;
