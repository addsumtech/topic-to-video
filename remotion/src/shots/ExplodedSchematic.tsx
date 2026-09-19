// SHOT · Exploded Schematic — blueprint/engineering language (Framer/hardware films): a system starts
// clustered, then EXPLODES apart along its axis into labelled parts with leader lines + a dimension readout,
// like a spec sheet building itself. Blueprint navy + cyan line-work (a cool, technical, distinct look).
//
// THE GLOWING PART IS THE ONE THE FILM NAMES. `const hot = i === 2` lit the THIRD part of every pipeline as
// the key stage — right for the demo, where it is 'Experts ×100', and a claim on every other film: a film's
// five-step checkout had its payment step glowing as the heart of the system for no reason but its position,
// and a two-stage pipeline had no hot part at all while a three-stage one crowned its last. `hot` is now an
// index the film passes; without it every part is drawn alike. The demo passes its own.
//
// AND THE PARTS NEVER OVERLAP. The boxes were a fixed 260px on a fixed axis, so at 9:16 five parts were
// spaced 178px apart: every box sat on top of its neighbour, the labels ran into each other, and the
// connectors — drawn from one box's right edge to the next box's left edge — pointed BACKWARDS, an arrow
// from 'Planner' to 'Instruction' that no film drew. The parts now explode along the frame's long axis
// (whichever axis lets the labels be read — downward on a portrait or square frame), each box is sized to the
// slot its count leaves, and the type is fitted to the box, so a connector always runs forward.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitBlockPx, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 150; // 5s
const NAVY = '#081726', CYAN_D0 = '#43C4E8', LINE_D0 = '#1f5f7d';
const DEFAULT_STAGES = ['Instruction', 'Planner', 'Experts ×100', 'Your tools', 'Deliverable'];
// the demo's own key stage, applied only while the demo's own stages are showing — never to a film's
const DEMO_HOT = 2;
// Six parts is where a square frame runs out on both axes: stacked, a part is ~54px tall; side by side, ~125px
// wide. Past it neither leaves a box a label can be read in.
export const MAX_SCHEMATIC_PARTS = 6;

export const ExplodedSchematic: React.FC<{caption?: string; label?: string; unit?: string; items?: string[]; hot?: number | null}> = ({
  // `caption` was DECLARED and never read — the corner block wrote its own English out in full. Each
  // piece is a prop now, defaulting to the literal it replaced.
  caption = 'ONE PROMPT → DELIVERED', label = 'SYSTEM', unit = 'STAGES',
  items: STAGES = DEFAULT_STAGES, hot: HOT} = {}) => {
  if (!Array.isArray(STAGES) || STAGES.length < 1 || STAGES.length > MAX_SCHEMATIC_PARTS) {
    throw new Error(`ExplodedSchematic needs 1-${MAX_SCHEMATIC_PARTS} \`items\` (got ${Array.isArray(STAGES) ? STAGES.length : typeof STAGES}). ` +
      'Each is one part of the exploded system; past six the parts are too small to label — group stages, or ' +
      'cast a pipeline/list register.');
  }
  STAGES.forEach((st, i) => {
    if (!String(st ?? '').trim()) throw new Error(`ExplodedSchematic: item ${i + 1} is empty.`);
  });
  // `hot` selects, so it defaults to NONE; only the untouched demo stages get the demo's own hot part.
  const hotIdx = HOT !== undefined ? HOT : (STAGES === DEFAULT_STAGES ? DEMO_HOT : null);
  if (hotIdx != null && !(Number.isInteger(hotIdx) && hotIdx >= 0 && hotIdx < STAGES.length)) {
    throw new Error(`ExplodedSchematic: \`hot\` is ${JSON.stringify(hotIdx)}, but it must be the index (0-${STAGES.length - 1}) ` +
      'of the part the film calls the key stage — or leave it out and every part is drawn alike.');
  }
  const dna = useDNA();
  const CYAN = dna?.accent ?? CYAN_D0, LINE = dna?.line ?? LINE_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const ex = easeInOutCubic(seg(t, 0.14, 0.62)); // explode progress
  const n = STAGES.length, mid = (n - 1) / 2;
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const GAP = 44;                                        // the least room a forward connector needs
  // THE AXIS IS THE FRAME'S LONG ONE — UNLESS THE LABELS CANNOT BE READ ALONG IT. Each axis sizes its boxes
  // from the slot its count leaves and fits the type to them. The long axis is kept while it carries at least
  // READABLE_PX; below that the other axis is taken if it does better. At 16:9 that is sideways, the default
  // five at their original 340px pitch and 260px boxes; at 9:16 it is downward; at 1:1 three parts stay
  // sideways, while five sideways boxes would carry 16px type and are stacked instead. (Choosing the larger
  // type outright was tried: it stacked the 16:9 demo, because a stacked box is 520px wide.)
  const layoutFor = (vert: boolean) => {
    const spread = vert
      ? Math.min(340, (zBot - zTop - 60) / n)            // final gap between part centres, along the axis
      : Math.min(340, (W * 0.94) / n);
    const bw = vert ? Math.min(520, W * 0.62) : Math.min(260, spread - GAP);
    const bh = vert ? Math.min(200, spread - GAP) : 200;
    const pad = Math.round(Math.min(16, bh * 0.15, bw * 0.08));
    const innerW = bw - 2 * pad, innerH = bh - 2 * pad;
    // ONE SIZE FOR EVERY LABEL (a mixed size would rank the parts): the largest at which each label fits its
    // box's height, and its longest unbreakable word fits the width.
    const px = STAGES.reduce((acc, st) => {
      const longest = String(st).split(/\s+/).reduce((a, b) => (b.length > a.length ? b : a), '');
      return Math.min(acc, fitBlockPx(String(st), innerW, innerH, 34, {usable: 1, leading: 1.1}),
                      fitTextPx(longest, innerW, 34, {usable: 1}));
    }, 34);
    return {vert, spread, bw, bh, pad, px};
  };
  const across = layoutFor(false), down = layoutFor(true);
  const READABLE_PX = 24;
  const [long, other] = H > W * 1.15 ? [down, across] : [across, down];
  const {vert, spread, bw, bh, pad, px: labelPx} = long.px >= READABLE_PX || long.px >= other.px ? long : other;
  const cx = W / 2;
  const cy = vert ? (zTop + zBot) / 2 : H / 2 - 40;
  const at = (i: number) => (i - mid) * spread * ex;     // offset of part i from the centre, along the axis
  return (
    <AbsoluteFill style={{background: `radial-gradient(130% 130% at 50% 40%, #0d2236, ${NAVY} 70%)`}}>
      {/* faint blueprint grid */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        {[...Array(Math.ceil(W / 60) + 1)].map((_, i) => <line key={`v${i}`} x1={i * 60} y1={0} x2={i * 60} y2={H} stroke="#0e2b42" strokeWidth={1} />)}
        {[...Array(Math.ceil(H / 60) + 1)].map((_, i) => <line key={`h${i}`} x1={0} y1={i * 60} x2={W} y2={i * 60} stroke="#0e2b42" strokeWidth={1} />)}
      </svg>
      {/* connectors (draw on as it assembles/explodes) — always from part i's far edge to part i+1's near one */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {STAGES.slice(0, -1).map((_, i) => {
          const grow = clamp01((ex - 0.2) / 0.6);
          const half = vert ? bh / 2 : bw / 2;
          const a1 = at(i) + half, a2 = at(i + 1) - half;
          if (a2 - a1 < 12) return null;                 // still clustered: no room for an arrow to point forward
          return vert
            ? <line key={i} x1={cx} y1={cy + a1} x2={cx} y2={cy + lerp(a1, a2, grow)} stroke={CYAN} strokeWidth={2.5} markerEnd="url(#a)" />
            : <line key={i} x1={cx + a1} y1={cy} x2={cx + lerp(a1, a2, grow)} y2={cy} stroke={CYAN} strokeWidth={2.5} markerEnd="url(#a)" />;
        })}
        <defs><marker id="a" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke={CYAN} strokeWidth="1.4" /></marker></defs>
      </svg>
      {STAGES.map((s, i) => {
        const x = vert ? cx : cx + at(i);
        const y = vert ? cy + at(i) : cy;
        const app = easeOutCubic(seg(t, 0.06 + i * 0.03, 0.3));
        const labelIn = easeOutCubic(seg(t, 0.4 + i * 0.05, 0.7));
        const hot = i === hotIdx;                        // the part the FILM called the key stage, if any
        return (
          <div key={i}>
            {/* wireframe part box */}
            <div style={{position: 'absolute', left: x - bw / 2, top: y - bh / 2, width: bw, height: bh, opacity: clamp01(app),
              border: `2px solid ${hot ? CYAN : LINE}`, borderRadius: 6, background: hot ? `${CYAN}12` : 'rgba(67,196,232,0.04)',
              boxShadow: hot ? `0 0 40px ${CYAN}44` : 'none'}}>
              {/* corner ticks */}
              {[[0, 0], [1, 0], [0, 1], [1, 1]].map(([hx, hy], k) => <div key={k} style={{position: 'absolute',
                left: hx ? bw - 14 : 2, top: hy ? bh - 14 : 2, width: 12, height: 12,
                borderTop: hy ? 'none' : `2px solid ${CYAN}`, borderBottom: hy ? `2px solid ${CYAN}` : 'none',
                borderLeft: hx ? 'none' : `2px solid ${CYAN}`, borderRight: hx ? `2px solid ${CYAN}` : 'none'}} />)}
              <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                font: `800 ${labelPx}px/${leading(String(s), 1.1)} var(--f-body, Inter,system-ui,sans-serif)`, color: hot ? '#eaffff' : '#9fc6d8',
                textAlign: 'center', padding: pad, textWrap: 'balance'}}>{s}</div>
            </div>
            {/* leader line + numbered label: below the part when the axis runs across, beside it when it runs down */}
            <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: labelIn}}>
              {vert
                ? <line x1={x - bw / 2} y1={y} x2={x - bw / 2 - 50} y2={y} stroke={LINE} strokeWidth={1.5} strokeDasharray="5 5" />
                : <line x1={x} y1={y + bh / 2} x2={x} y2={y + bh / 2 + 70} stroke={LINE} strokeWidth={1.5} strokeDasharray="5 5" />}
            </svg>
            <div style={vert
              ? {position: 'absolute', left: x - bw / 2 - 50 - 12 - 60, top: y - 13, width: 60, textAlign: 'right', opacity: labelIn}
              : {position: 'absolute', left: x - 90, top: y + bh / 2 + 82, width: 180, textAlign: 'center', opacity: labelIn}}>
              <div style={{font: '800 26px/1 var(--f-body, Inter)', color: CYAN}}>{String(i + 1).padStart(2, '0')}</div>
            </div>
          </div>
        );
      })}
      {/* corner spec HUD (top-right — keeps clear of the film's bottom caption zone) */}
      <div style={{position: 'absolute', right: 90, top: 90, font: '600 28px/1.6 var(--f-mono, "JetBrains Mono",monospace)', color: CYAN, opacity: 0.8, textAlign: 'right'}}>
        {label} · {STAGES.length} {unit}<br />{caption}
      </div>
    </AbsoluteFill>
  );
};
export default ExplodedSchematic;
