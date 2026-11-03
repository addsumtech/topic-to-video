// SHOT · Living Map — ONE structure for the whole film: a pipeline, a system, a family of ideas, laid out once over
// every node the film will show, and built up beat by beat while the camera moves through it. Each beat adds nodes
// (they pop in where they will always be), draws the edges that now connect, and frames what it is about; its last
// frame is the next map beat's first, so the cut between them is invisible (render_remotion makes it a hard cut).
// At the end of a stretch a beat with no focus pulls back to everything built so far.
//
// This is the skill's own move, not a peer's: films of separate registers redraw their structure from nothing on
// every beat and the viewer loses where they are. Here the place of every idea is learnt once and kept.
//
// The board names the map once (`meta.maps[id] = {nodes, edges}`) and each beat `{map, add, focus}`;
// render_remotion.expand_living_maps hands this register the whole map plus `before`/`after` (what is shown when the
// beat starts and ends) and `focusFrom`/`focusTo` (where the camera starts and ends). Layout: runtime/graphLayout.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutBack, easeInOutCubic, lerp} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useGlide} from '../runtime/glide';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {rows} from '../runtime/rows';
import {layoutGraph, frameNodes as frameOn, blendCam, NODE_W, NODE_H, type GNode, type GEdge} from '../runtime/graphLayout';

export const DURATION = 180; // 6 s

export type MapNode = GNode & {label: string; note?: string};

const DEMO_NODES: MapNode[] = [{id: 'a', label: 'Demo one'}, {id: 'b', label: 'Demo two'}, {id: 'c', label: 'Demo three'},
  {id: 'd', label: 'Demo four'}];
const DEMO_EDGES: GEdge[] = [['a', 'b'], ['a', 'c'], ['b', 'd'], ['c', 'd']];

/** The smallest camera scale at which a node's label still meets the type floor. */
const MIN_SCALE = 0.7;
const LABEL_WORLD = 44;        // a label's size in world units — 30.8 px at MIN_SCALE, the floor

export const LivingMap: React.FC<{nodes?: MapNode[]; edges?: GEdge[]; before?: string[]; after?: string[];
  focusFrom?: string[]; focusTo?: string[]; title?: string}> = ({nodes: nodesIn, edges: edgesIn, before: beforeIn,
  after: afterIn, focusFrom, focusTo, title = ''} = {}) => {
  // The defaults follow the NODES they are given: the demo's edges and ids are the demo's alone, and a map of other
  // nodes handed them named edges to nodes it does not have (a library sweep's fixture refused to render)
  const nodes = nodesIn ?? DEMO_NODES;
  if (!Array.isArray(nodes) || nodes.length < 2 || nodes.length > 16) {
    throw new Error(`LivingMap needs 2-16 nodes in its map (got ${Array.isArray(nodes) ? nodes.length : typeof nodes})`);
  }
  const edges = edgesIn ?? (nodesIn ? [] : DEMO_EDGES);
  const after = afterIn ?? nodes.map((n) => n.id);
  // @truncates: with no `before` (a standalone still) the map opens on its first node — nothing a film gave is dropped; a film always names it
  const before = beforeIn ?? after.slice(0, 1);
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const BG = dna?.bg ?? '#0a0d12', FG = dna?.fg ?? '#eef1f6', DIM = dna?.dim ?? '#8b93a3', ACC = dna?.accent ?? '#7cc4ff';
  const SURF = dna?.surface ?? '#151a22', EDGE = dna?.line ?? '#2b3240';
  const DISPLAY = 'var(--f-display, Inter, system-ui, sans-serif)';
  const k = U / 1080;           // the map's world is sized for a 1080 short side

  const placed = layoutGraph(nodes, edges);
  const shownBefore = new Set(before), shownAfter = new Set(after);
  const fromList = rows<string>(focusFrom, 'focusFrom', 'LivingMap'), toList = rows<string>(focusTo, 'focusTo', 'LivingMap');
  const fFrom = fromList.length ? fromList : after;
  const fTo = toList.length ? toList : after;
  const top = Math.max(CONTENT_TOP, Math.round(U * 0.07)) + (title ? Math.round(U * 0.06) : 0);
  const zone = {x: Math.round(W * 0.06), y: top, w: Math.round(W * 0.88), h: contentBottom(W, H) - top - Math.round(U * 0.02)};
  // the camera works in a world sized for 1080: scale the zone into it, frame, and scale back
  const wz = {x: zone.x / k, y: zone.y / k, w: zone.w / k, h: zone.h / k};
  const c0 = frameOn(placed, fFrom, wz, {maxScale: 1.45}), c1 = frameOn(placed, fTo, wz, {maxScale: 1.45});
  for (const [c, which] of [[c0, fFrom], [c1, fTo]] as const) {
    if (c.s < MIN_SCALE) {
      throw new Error(`LivingMap: framing ${which.length} nodes needs a scale of ${c.s.toFixed(2)}, under ${MIN_SCALE} — their ` +
        'labels would fall under the type floor; focus a part of the map, or split it');
    }
  }
  const added = after.filter((id) => !shownBefore.has(id));
  // EACH ADDED NODE ARRIVES ON THE WORD THAT NAMES IT (runtime/cue: `nodes.<i>` by its label), its own window spread
  // across the beat so a node the voice never names still comes in turn. Measured on a delivered test film, a fixed
  // 0.30-0.48 window put every node in before the voice reached it and then held the frame still for ~3 s, and a
  // hit-stop on the last node's word landed on that still frame and did nothing.
  const cue = useCues();
  // The defaults sit LATE (the last node by ~0.86): a cue only ever moves an entrance EARLIER, so a default before the
  // word left the node landing early — on the test film 0.8 s before "distance", and a hit-stop on that word froze a
  // frame that had already stopped moving. Late defaults are pulled onto their words; an unnamed node still comes in.
  const first0 = before.length ? 0.2 : 0.08, span = before.length ? 0.56 : 0.6;
  const win: Record<string, [number, number]> = {};
  added.forEach((id, k) => {
    const a0 = first0 + (added.length > 1 ? (k / (added.length - 1)) * span : 0);
    win[id] = cue.win('nodes.' + nodes.findIndex((n) => n.id === id), a0, a0 + 0.1, REACH_CUBIC) as [number, number];
  });
  const addAt = (id: string) => (win[id] ? win[id][0] : 0);
  // the camera travels from the beat's first arrival to its last, so the frame is moving while the map grows
  const mv0 = added.length ? Math.min(...added.map((id) => win[id][0])) - 0.04 : 0.08;
  const mv1 = added.length ? Math.max(...added.map((id) => win[id][1])) : 0.42;
  const move = easeInOutCubic(clamp01(seg(t, Math.max(0.06, mv0), Math.max(mv0 + 0.2, mv1))));
  const cam = blendCam(c0, c1, move, wz);
  const S = (x: number, y: number) => ({x: (x * cam.s + cam.tx) * k, y: (y * cam.s + cam.ty) * k});
  const nodeOn = (id: string) => (shownBefore.has(id) ? 1 : shownAfter.has(id) ? easeOutBack(clamp01(seg(t, win[id][0], win[id][1]))) : 0);
  const lit = (id: string) => lerp(fFrom.includes(id) ? 1 : 0, fTo.includes(id) ? 1 : 0, move);
  const scale = cam.s * k;
  const labelPx = LABEL_WORLD * scale;
  // ONE label size for the whole map: the size at which every label fits its box (per-node fitting made a short word
  // larger than its neighbours)
  // a NOTE is secondary: it shows only while the camera is close enough for it to fit its box at the type floor, fading
  // across the threshold (in the whole-map view a node is too small to hold one, and it overflowed)
  const floorPx = Math.round(U * 0.028);
  const noteFits = (note: string, w: number) => clamp01((fitTextPx(note, w * 0.9, floorPx * 2) / floorPx - 0.97) / 0.06);
  const nodePx = Math.max(Math.round(U * 0.028), Math.min(labelPx, ...nodes.map((n) => fitTextPx(n.label, NODE_W * scale * 0.86, labelPx))));

  return (
    <AbsoluteFill style={{background: dna ? `radial-gradient(100% 90% at 50% 40%, ${mix(BG, ACC, 0.06)}, ${BG} 72%)` : BG}}>
      {title ? <div style={{position: 'absolute', left: zone.x, top: Math.max(CONTENT_TOP, Math.round(U * 0.07)), color: mix(FG, DIM, 0.35),
        font: `700 ${fitTextPx(title, zone.w, Math.round(U * 0.036))}px/1.1 ${DISPLAY}`}}>{title}</div> : null}
      <svg style={{position: 'absolute', left: 0, top: 0}} width={W} height={H}>
        {edges.map((e, i) => {
          const [a, b] = e;
          if (!shownAfter.has(a) || !shownAfter.has(b)) return null;
          const was = shownBefore.has(a) && shownBefore.has(b);
          const d0 = Math.max(addAt(a), addAt(b)) + 0.08;
          const draw = was ? 1 : easeInOutCubic(clamp01(seg(t, d0, d0 + 0.14)));
          const pa = placed[a], pb = placed[b];
          const forward = pb.x > pa.x;
          const A = S(pa.x + (forward ? NODE_W / 2 : 0), pa.y + (forward ? 0 : NODE_H / 2));
          const B = S(pb.x - (forward ? NODE_W / 2 : 0), pb.y - (forward ? 0 : NODE_H / 2));
          const mx = (A.x + B.x) / 2;
          const path = forward ? `M${A.x} ${A.y} C${mx} ${A.y} ${mx} ${B.y} ${B.x} ${B.y}`
            : `M${A.x} ${A.y} C${A.x} ${(A.y + B.y) / 2} ${B.x} ${(A.y + B.y) / 2} ${B.x} ${B.y}`;
          const hl = Math.min(lit(a), lit(b));
          const ah = 14 * scale;
          const ang = forward ? 0 : Math.atan2(B.y - A.y, 0.0001) ;
          const hx = (s: number) => B.x - Math.cos(ang + s) * ah, hy = (s: number) => B.y - Math.sin(ang + s) * ah;
          return (
            <g key={i}>
              <path d={path} pathLength={1} fill="none" stroke={mix(EDGE, ACC, 0.25 + 0.6 * hl)} strokeWidth={Math.max(2, 3 * scale)}
                strokeDasharray={1} strokeDashoffset={1 - draw} strokeLinecap="round" />
              {draw >= 0.98 ? <path d={`M${hx(0.5)} ${hy(0.5)} L${B.x} ${B.y} L${hx(-0.5)} ${hy(-0.5)}`} fill="none"
                stroke={mix(EDGE, ACC, 0.25 + 0.6 * hl)} strokeWidth={Math.max(2, 3 * scale)} strokeLinecap="round" strokeLinejoin="round" /> : null}
            </g>
          );
        })}
      </svg>
      {nodes.map((n) => {
        const on = nodeOn(n.id);
        if (on <= 0) return null;
        const p = placed[n.id], c = S(p.x, p.y), L = lit(n.id);
        const w = NODE_W * scale, h = NODE_H * scale;
        // A NODE THE CAMERA HAS LEFT BEHIND fades out before it reaches the frame's edge and is not drawn across it: a
        // label half off the frame read as broken ("our receiver" on the test film, text_safe_qa CUT OFF)
        const room = Math.min(c.x - w / 2, W - (c.x + w / 2));
        const edgeFade = clamp01(room / (w * 0.35));
        if (edgeFade <= 0.01) return null;
        const px = nodePx;
        return (
          <div key={n.id} style={{position: 'absolute', left: c.x - w / 2, top: c.y - h / 2, width: w, height: h, boxSizing: 'border-box',
            opacity: clamp01(on * 1.3) * edgeFade * (1 - 0.35 * (1 - L) * (fTo.length < after.length ? 1 : 0)),
            transform: glide(`scale(${lerp(0.85, 1, on)})`, true), transformOrigin: 'center',
            borderRadius: 18 * scale, border: `${Math.max(1.5, (2 + 2 * L) * scale)}px solid ${mix(EDGE, ACC, 0.2 + 0.8 * L)}`,
            background: `linear-gradient(160deg, ${mix(SURF, ACC, 0.06 + 0.14 * L)}, ${mix(SURF, BG, 0.35)})`,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
            boxShadow: `0 ${12 * scale}px ${30 * scale}px #0006`}}>
            <div style={{color: FG, font: `700 ${px}px/${leading(n.label, 1.1)} ${DISPLAY}`, whiteSpace: 'nowrap'}}>{n.label}</div>
            {n.note && noteFits(n.note, w) > 0 ? <div style={{color: mix(DIM, FG, 0.3), marginTop: 4 * scale, whiteSpace: 'nowrap',
              opacity: noteFits(n.note, w), font: `500 ${floorPx}px/1.1 var(--f-body, Inter, system-ui, sans-serif)`}}>{n.note}</div> : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default LivingMap;
