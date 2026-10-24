// SHOT · Flow Sankey — QUANTITY THAT IS CONSERVED: the film's stages as columns of nodes and the flows between them as
// ribbons whose widths ARE their values, drawn on stage by stage so the viewer watches the total split and rejoin.
//
// WHAT IT ARGUES. Where a whole goes: an energy budget, a funnel, a supply chain, a budget by programme. The width of
// every ribbon is its quantity on ONE scale, and the layout REFUSES a node whose inflow and outflow differ
// (runtime/sankey.ts) — so the picture can only ever assert a balance the figures have. Not for parts of a whole with no
// stages (MadeOf), a ranking (RankRace / ChartRace), or connections with no quantity (a network register).
//
// WHAT COMES FROM WHERE. Every node, every link and every value is the film's. A node prints its figure only when the
// film gives its `display` — a node's height is a SUM of link values, and a sum printed is a figure nobody stated.
// Nothing is emphasised unless the film names a `focus`.
//
// LABELS NEVER COLLIDE. The first column is labelled on its left, the last on its right, the middle ones beside their
// node on a chip; within a column the labels are de-overlapped in one dimension (runtime/sankey stackLabels), and a
// column whose labels cannot all fit at the floor size THROWS instead of laying one over another. A middle chip wider
// than the room before the next column also throws.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {CONTENT_TOP, contentBottom, TITLE_Y} from '../runtime/layout';
import {useDNA, readableOn, dimOn, mix, dnaPalette, contrastOf} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {hasCJK} from '../runtime/cjkType';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {layoutSankey, ribbonPath, stackLabels} from '../runtime/sankey';

type SNodeIn = {id?: string; label?: string; display?: string};
type SLinkIn = {from?: string; to?: string; value?: number};
import {useLabelWidths} from '../runtime/labelWidths';

export const DURATION = 210; // 7s
export const MAX_NODES = 14, MAX_LINKS = 24;

const BG_D0 = '#070a12', FG_D0 = '#eef1f7', DIM_D0 = '#8f98ab';
const TONES0 = ['#5b8cff', '#37d4a6', '#f6a531', '#ff6f91', '#c07bff', '#4dd0e1', '#a3e635', '#fb7185'];
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// Placeholder copy: stages named by their role. The demo values balance (60 + 40 in, 70 + 30 out) and describe nothing.
const DEMO_NODES: SNodeIn[] = [{id: 'a', label: 'input one'}, {id: 'b', label: 'input two'}, {id: 'm', label: 'the stage'},
  {id: 'x', label: 'output one'}, {id: 'y', label: 'output two'}];
const DEMO_LINKS: SLinkIn[] = [{from: 'a', to: 'm', value: 60}, {from: 'b', to: 'm', value: 40},
  {from: 'm', to: 'x', value: 70}, {from: 'm', to: 'y', value: 30}];

export const FlowSankey: React.FC<{
  title?: string;
  /** 3-14 nodes: `id`, `label`, optional `display` (the figure the node prints, as the film writes it) */
  nodes?: SNodeIn[];
  /** 2-24 links `{from, to, value}`; every interior node's inflow must equal its outflow */
  links?: SLinkIn[];
  /** a node id the film emphasises; its flows stay lit and the rest recede */
  focus?: string;
  note?: string;
}> = ({title = '', nodes: nodesIn = DEMO_NODES, links: linksIn = DEMO_LINKS, focus, note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H, durationInFrames: DUR, fps} = useVideoConfig();
  const S = 'FlowSankey';
  if ((nodesIn === DEMO_NODES) !== (linksIn === DEMO_LINKS)) {
    throw new Error(`FlowSankey: pass \`nodes\` and \`links\` together — one without the other would be drawn against the demo's.`);
  }
  const NODES = rows<SNodeIn>(nodesIn, 'nodes', S);
  const LINKS = rows<SLinkIn>(linksIn, 'links', S);
  if (NODES.length < 3 || NODES.length > MAX_NODES) throw new Error(`${S}: needs 3-${MAX_NODES} nodes (got ${NODES.length}).`);
  if (LINKS.length < 2 || LINKS.length > MAX_LINKS) throw new Error(`${S}: needs 2-${MAX_LINKS} links (got ${LINKS.length}).`);

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);
  // @positional: a node's hue only tells one node from another; it encodes no quantity, rank or status
  const TONES = dnaPalette(dna, Math.max(3, NODES.length)) ?? TONES0;
  const CHIP = mix(BG, '#000000', 0.3);

  // ── type, measured ───────────────────────────────────────────────────────────────────────────────────
  const U = Math.min(W, H);
  const portrait = W < H;
  const lblPx = Math.round(U * (portrait ? 0.03 : 0.026)), dispPx = Math.round(U * (portrait ? 0.026 : 0.022));
  const labels = NODES.map((n) => String(n?.label ?? n?.id ?? '').trim() || ' ');
  const displays = NODES.map((n) => String(n?.display ?? '').trim() || ' ');
  const lw = useLabelWidths(labels, BODY, 600, lblPx);
  const dw = useLabelWidths(displays, MONO, 500, dispPx);
  const titleK = useKinetic({text: title || ' ', w: Math.round(W * 0.84), nowrap: true, fit: 'box',
    font: {family: DISPLAY, weight: 640, size: Math.round(U * 0.046), minSize: Math.round(U * 0.03), lineHeight: 1.1,
      tracking: hasCJK(title) ? 0 : -0.015}});
  const noteH = note ? Math.round(U * 0.05) : 0;
  const noteK = useKinetic({text: note || ' ', w: Math.round(W * 0.84), fit: 'box', maxLines: 2, h: noteH,
    font: {family: MONO, weight: 500, size: Math.round(U * 0.021), minSize: Math.round(U * 0.017), lineHeight: 1.3}});
  const anchors = <>{lw.anchor}{dw.anchor}</>;
  const measured = Boolean(lw.widths && dw.widths);

  const zTop = CONTENT_TOP + Math.round(U * 0.02), zBot = contentBottom(W, H) - noteH - Math.round(U * 0.02);
  const nodeW = Math.max(10, Math.round(U * 0.013));
  const gap = Math.round(U * 0.014);
  const blockW = (i: number) => Math.max(lw.widths?.[i] ?? 0, NODES[i]?.display ? (dw.widths?.[i] ?? 0) : 0);
  const blockH = (i: number) => Math.round(lblPx * 1.22) + (NODES[i]?.display ? Math.round(dispPx * 1.3) : 0);

  // a first, provisional layout tells which nodes sit in the outer columns; the gutters are then sized to THEIR labels
  const probe = layoutSankey(NODES, LINKS, {x0: 0, x1: 1000, y0: 0, y1: 1000}, 10, 10, S);
  const lastCol = probe.cols - 1;
  const leftW = Math.max(0, ...probe.nodes.filter((n) => n.col === 0).map((n) => blockW(n.i))) + gap * 1.5;
  const rightW = Math.max(0, ...probe.nodes.filter((n) => n.col === lastCol).map((n) => blockW(n.i))) + gap * 1.5;
  const x0 = Math.round(W * 0.05 + leftW), x1 = Math.round(W * 0.95 - rightW);
  if (measured && x1 - x0 < W * 0.3) {
    throw new Error(`${S}: the first and last columns' labels take ${Math.round(leftW + rightW)}px of a ${W}px frame, leaving ` +
      'no room for the flow. Shorten the outer labels.');
  }
  const pad = Math.max(gap * 1.2, ...NODES.map((_, i) => blockH(i) * 0.2));
  const L = layoutSankey(NODES, LINKS, {x0, x1, y0: zTop, y1: zBot}, nodeW, pad, S);
  const colPitch = (x1 - x0 - nodeW) / Math.max(1, lastCol);

  // ── labels: de-overlapped per column, refused when they cannot all fit ───────────────────────────────
  // A MIDDLE LABEL IS SET SMALLER BEFORE IT IS REFUSED. At 9:16 the room between two stages is ~220px, and a
  // six-glyph Chinese name at the full label size does not fit it; it may shrink to 70% (still above the caption's
  // own size floor), and only a label that cannot fit even then is refused.
  const room = colPitch - nodeW - gap * 2;
  const scaleOf = (n: typeof L.nodes[number]) => (n.col > 0 && n.col < lastCol && measured
    ? Math.min(1, room / Math.max(1, blockW(n.i) + gap * 1.4)) : 1);
  const lab: {left: number; top: number; w: number; h: number; side: 'l' | 'r' | 'm'; k: number}[] = new Array(L.nodes.length);
  if (measured) {
    for (let c = 0; c <= lastCol; c++) {
      const ns = L.nodes.filter((n) => n.col === c);
      const tops = stackLabels(ns.map((n) => ({cy: (n.y0 + n.y1) / 2, h: blockH(n.i) * Math.max(0.7, scaleOf(n))})), zTop, zBot, Math.round(gap * 0.6));
      if (!tops) {
        throw new Error(`${S}: the ${ns.length} labels of stage ${c + 1} (${ns.map((n) => n.label).join(', ')}) cannot all be set ` +
          'without overlapping at this size. Merge small flows into one node, or split the beat.');
      }
      ns.forEach((n, j) => {
        const side = c === 0 ? 'l' : c === lastCol ? 'r' : 'm';
        const k = scaleOf(n);
        if (side === 'm' && k < 0.7) {
          throw new Error(`${S}: the label ${JSON.stringify(n.label)} is wider than the room between its stage and the next ` +
            `(${Math.round(room)}px) even at 70% of the label size. Shorten it.`);
        }
        const w = (blockW(n.i) + (side === 'm' ? gap * 1.4 : 0)) * k;
        const left = side === 'l' ? n.x0 - gap - w : n.x1 + gap;
        lab[n.i] = {left, top: tops[j], w, h: blockH(n.i) * k, side, k};
      });
    }
  }

  // ── timing, stage by stage ───────────────────────────────────────────────────────────────────────────
  const colStep = 0.5 / Math.max(1, lastCol);
  const nodeIn = (c: number) => easeOutCubic(seg(t, 0.06 + c * colStep, 0.16 + c * colStep));
  const linkDraw = (c: number) => easeInOutCubic(seg(t, 0.1 + c * colStep, 0.1 + (c + 1) * colStep + 0.04));
  const flowT = (t * DUR) / fps;   // seconds — the shimmer moves at one speed whatever the beat's length
  const focusId = focus == null ? null : String(focus);
  if (focusId != null && !L.nodes.some((n) => n.id === focusId)) {
    throw new Error(`${S}: \`focus\` names ${JSON.stringify(focusId)}, which is not a node id.`);
  }
  const lit = (l: typeof L.links[number]) => focusId == null || l.source.id === focusId || l.target.id === focusId;
  const uid = 'fsk';
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(120% 100% at 50% 30%, ${mix(BG, '#3a4a7a', 0.12)}, ${BG} 70%)`}}>
      {anchors}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          {L.links.map((l) => {
            // the flow itself: a soft band of light travels each drawn ribbon source → target, one crossing every few
            // seconds (a period in seconds, never a vibration); dashes at ribbon width read as a barcode of slabs
            const c = ((flowT * 0.3 + l.i * 0.23) % 1.5) - 0.25;
            return (
              <React.Fragment key={l.i}>
                <linearGradient id={`${uid}-g${l.i}`} gradientUnits="userSpaceOnUse" x1={l.source.x1} x2={l.target.x0} y1={0} y2={0}>
                  <stop offset="0" stopColor={TONES[l.source.i % TONES.length]} />
                  <stop offset="1" stopColor={TONES[l.target.i % TONES.length]} />
                </linearGradient>
                <linearGradient id={`${uid}-s${l.i}`} gradientUnits="userSpaceOnUse" x1={l.source.x1} x2={l.target.x0} y1={0} y2={0}>
                  <stop offset={clamp01(c - 0.14)} stopColor="#ffffff" stopOpacity={0} />
                  <stop offset={clamp01(c)} stopColor="#ffffff" stopOpacity={0.2} />
                  <stop offset={clamp01(c + 0.14)} stopColor="#ffffff" stopOpacity={0} />
                </linearGradient>
              </React.Fragment>
            );
          })}
        </defs>
        {L.links.map((l) => {
          const p = linkDraw(l.source.col);
          if (p <= 0) return null;
          const d = ribbonPath(l);
          const op = lit(l) ? 0.44 : 0.12;
          return (
            <g key={l.i}>
              <path d={d} fill="none" stroke={`url(#${uid}-g${l.i})`} strokeOpacity={op} strokeWidth={Math.max(1, l.width)}
                strokeLinecap="butt" {...drawOn(p)} />
              {p >= 1 && lit(l) ? (
                <path d={d} fill="none" stroke={`url(#${uid}-s${l.i})`} strokeWidth={Math.max(1, l.width)} strokeLinecap="butt" />
              ) : null}
            </g>
          );
        })}
        {L.nodes.map((n) => {
          const a = nodeIn(n.col);
          const h = (n.y1 - n.y0) * a, cy = (n.y0 + n.y1) / 2;
          return <rect key={n.i} x={n.x0} y={cy - h / 2} width={nodeW} height={Math.max(0, h)} rx={Math.min(nodeW / 2, 4)}
            fill={TONES[n.i % TONES.length]} opacity={focusId == null || focusId === n.id ? 1 : 0.55} />;
        })}
      </svg>
      {measured && L.nodes.map((n) => {
        const q = lab[n.i];
        const a = easeOutCubic(seg(t, 0.12 + n.col * colStep, 0.24 + n.col * colStep));
        const align = q.side === 'l' ? 'flex-end' : 'flex-start';
        return (
          <div key={n.i} style={{position: 'absolute', left: q.left, top: q.top, width: q.w, height: q.h, opacity: a,
            display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: align, boxSizing: 'border-box',
            ...(q.side === 'm' ? {padding: `0 ${Math.round(gap * 0.7 * q.k)}px`, background: `${CHIP}cc`, borderRadius: Math.round(lblPx * 0.3)} : {})}}>
            <div style={{color: FG, font: `600 ${Math.round(lblPx * q.k)}px/1.22 ${BODY}`, whiteSpace: 'nowrap'}}>{n.label}</div>
            {n.display ? (
              <div style={{color: contrastOf(TONES[n.i % TONES.length], q.side === 'm' ? CHIP : BG) >= 4.5 ? TONES[n.i % TONES.length] : FG,
                font: `500 ${Math.round(dispPx * q.k)}px/1.3 ${MONO}`, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap'}}>{n.display}</div>
            ) : null}
          </div>
        );
      })}
      {title ? (
        <KineticText k={titleK} x={Math.round(W * 0.05)} y={TITLE_Y} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.04}, enter: {by: 'line', at: 0.02, stagger: 0.1, dur: 0.8, ease: 'expo', cueKeys: ['title'], until: 0.4}}} />
      ) : titleK.anchor}
      {note ? (
        <KineticText k={noteK} x={Math.round(W * 0.05)} y={contentBottom(W, H) - noteH} color={DIM} id="note"
          motion={{from: {opacity: 0, y: 0.4}, enter: {by: 'word', at: 0.7, stagger: 0.03, dur: 0.5, ease: 'power3', cueKeys: ['note'], until: 0.86}}} />
      ) : noteK.anchor}
    </AbsoluteFill>
  );
};
export default FlowSankey;
