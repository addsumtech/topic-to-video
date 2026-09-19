// SHOT · GrantedTree — a permission BOUNDARY made visible: a structure tree where the granted branch is
// bracketed and operable and everything else goes quiet.
//
// WHY THIS EXISTS AS A REGISTER. A film that says "it only touches what you authorised" can assert that in
// words, and a viewer has no way to see the shape of the claim. The argument has a shape: a whole tree, ONE
// bracketed subtree, and a visible edge between them. That shape is reusable — a data-residency beat, a
// scoped API token, an org unit a policy applies to, a repo path a CI job may write — so it is a register
// and not a one-off. The topic arrives entirely through props; nothing here knows what a file is.
//
// The bracket is the whole point. Dimming the rest would say "these matter more"; a drawn edge says "the
// boundary is here, and it was drawn by you" — which is the difference between an emphasis and a promise.
//
// SO THE BRACKET MAY ENCLOSE ONLY WHAT WAS GRANTED. It used to be one box from the FIRST granted row to the
// LAST — so a film granting `Work` and `Photos` but not `Personal` between them drew `Personal` inside the
// boundary, the frame promising access the film had just said was withheld. Each contiguous run of granted
// rows now gets its own bracket. Nodes past the eighth were also cut by `.slice(0, 8)` without a word; more
// than eight now throws. A node needs its `label` (a row with a dot and no name says nothing) and its
// `depth` (the indent IS the tree's structure, and an assumed 0 would re-parent the node to the root). A tree
// with no granted node has no boundary: it used to go "quiet" all over, i.e. every row drawn as withheld, which
// the film never said. It now draws the tree with equal treatment — no bracket, no dimming, no grant or deny
// label — because a status nobody supplied is a status nobody gets.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP, wrapLines} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', ACC_D0 = '#4f8cff', DIM_D0 = '#7c8798', LINE_D0 = '#1e2733';

type Node = {label?: string; depth?: number; granted?: boolean};   // label + depth REQUIRED

export const MAX_TREE_NODES = 8;

const DEFAULT_NODES: Node[] = [
  {label: 'Documents', depth: 0},
  {label: 'Work', depth: 1, granted: true},
  {label: 'reports', depth: 2, granted: true},
  {label: 'data', depth: 2, granted: true},
  {label: 'Personal', depth: 1},
  {label: 'Photos', depth: 0},
];

export const GrantedTree: React.FC<{
  kicker?: string;          // what this frame is about
  root?: string;            // the tree's root label
  nodes?: Node[];           // the tree — `granted` marks the bracketed branch
  grantLabel?: string;      // the chip on the granted branch
  denyLabel?: string;       // the quiet label on everything else
  note?: string;            // one line under the tree
}> = ({kicker = '', root = '', nodes: NODES = DEFAULT_NODES,
       grantLabel = '', denyLabel = '', note = ''} = {}) => {
  const dna = useDNA();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const LINE = dna?.line ?? LINE_D0;
  const ON = dna?.onAccent ?? '#fff';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const base = Math.min(W, H);
  const zoneBottom = H - captionBand(W, H);

  // Every node once, as the film gave it (see the header).
  if (!Array.isArray(NODES) || NODES.length < 1 || NODES.length > MAX_TREE_NODES) {
    throw new Error(
      `GrantedTree needs 1-${MAX_TREE_NODES} \`nodes\` (got ${Array.isArray(NODES) ? NODES.length : typeof NODES}). ` +
      'A dropped node could be the very one outside the boundary — show the branch the grant is about and ' +
      'collapse the rest into one sibling (e.g. "everything else").');
  }
  const rows = NODES.map((n, i) => {
    const label = String(n?.label ?? '').trim();
    const depth = n?.depth;
    if (!label) throw new Error(`GrantedTree: node ${i + 1} has no \`label\`.`);
    if (!(Number.isInteger(depth) && (depth as number) >= 0)) {
      throw new Error(`GrantedTree: node ${i + 1} ("${label}") needs \`depth\` as an integer >= 0 (0 = top level), ` +
        `got ${JSON.stringify(depth)}. The indent is the tree's structure; it is never assumed.`);
    }
    return {label, depth: depth as number, granted: n?.granted === true};
  });
  const pad = Math.round(base * 0.018);
  const hair = Math.max(1, Math.round(base * 0.0018));
  const indent = Math.round(base * 0.055);
  const left = Math.round(W * 0.14);
  const width = Math.round(W * 0.46);

  // THE MAXIMUM HAS TO FIT. Eight nodes used to be the silent cut-off, and eight nodes plus a root, a kicker
  // and a note did not fit the zone at fixed row height: the root printed over the kicker and the note over the
  // last row. Now that eight is a stated maximum (and nine throws), eight must render cleanly — so the rows
  // share the room left between the kicker and the note, at their usual size whenever that fits.
  const rowH0 = Math.round(base * 0.072);
  const kickerH = kicker ? Math.round(base * 0.024 * 1.2) + pad : 0;
  const notePx = Math.round(base * 0.026);
  const noteH = note ? Math.round(wrapLines(String(note), notePx, W - left * 2) * notePx * 1.4) + pad * 2 : 0;
  const avail = zoneBottom - (CONTENT_TOP + kickerH + pad) - noteH;
  const rowH = Math.max(1, Math.min(rowH0, Math.floor(avail / (rows.length + (root ? 1 : 0)))));
  const font = Math.round(base * 0.034 * (rowH / rowH0));

  // The tree is placed as a block inside the content zone, never against the frame edge and never into the
  // band the burned caption owns.
  const treeH = rows.length * rowH + (root ? rowH : 0);
  const top = Math.max(CONTENT_TOP + kickerH + pad, (CONTENT_TOP + zoneBottom - treeH) / 2);

  const inn = (i: number) => easeOutCubic(clamp01(seg(t, 0.06 + i * 0.035, 0.28 + i * 0.035)));
  const bracket = easeOutCubic(clamp01(seg(t, 0.40, 0.62)));   // the boundary draws itself
  const chip = easeOutCubic(clamp01(seg(t, 0.60, 0.76)));
  const quiet = clamp01(seg(t, 0.66, 0.86));                   // the rest goes quiet AFTER the edge exists

  // ONE BRACKET PER CONTIGUOUS GRANTED RUN — a single first-to-last box enclosed the denied rows between two
  // granted ones (see the header). The chip labels the first run; the deny label sits under the last.
  const rowY = (i: number) => top + (root ? rowH : 0) + i * rowH;
  const runs: [number, number][] = [];
  rows.forEach((n, i) => {
    if (!n.granted) return;
    const last = runs[runs.length - 1];
    if (last && last[1] === i - 1) last[1] = i; else runs.push([i, i]);
  });
  const anyGranted = runs.length > 0;
  const gTop = anyGranted ? rowY(runs[0][0]) : 0;
  // The deny label names a WITHHELD row, so it sits beside one: the first denied row after the first granted
  // run (the row the boundary excludes), else the first denied row at all. It used to sit under the last
  // granted row, which with several runs is below the whole tree, and it was drawn even when every row was
  // granted — "withheld" beside nothing withheld. No denied row, no deny label.
  const denyRow = anyGranted
    ? (() => { const k = rows.findIndex((n, i) => !n.granted && i > runs[0][1]); return k >= 0 ? k : rows.findIndex((n) => !n.granted); })()
    : -1;

  return (
    <AbsoluteFill style={{background: BG, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left, top: CONTENT_TOP, opacity: inn(0),
          letterSpacing: '0.14em', color: ACC,
          font: `700 ${Math.round(base * 0.024)}px/1.2 var(--f-mono, ui-monospace, monospace)`}}>
          {kicker}
        </div>
      ) : null}

      {/* the granted branch's BRACKET — drawn, not implied; one per run, so no denied row is ever inside one */}
      {runs.map(([a, b]) => (
        <div key={'br' + a} style={{position: 'absolute', left: left - pad, top: rowY(a),
          width: width + pad * 2, height: (rowY(b + 1) - rowY(a)) * bracket,
          border: `${hair * 2}px solid ${ACC}`, borderRadius: pad * 0.6,
          opacity: bracket, boxSizing: 'border-box'}} />
      ))}

      {root ? (
        <div style={{position: 'absolute', left, top, width, height: rowH, opacity: inn(0), color: DIM,
          display: 'flex', alignItems: 'center',
          font: `500 ${font}px/1.15 var(--f-mono, ui-monospace, monospace)`}}>{root}</div>
      ) : null}

      {rows.map((n, i) => {
        const y = top + (root ? rowH : 0) + i * rowH;
        const on = inn(i + 1);
        const dimmed = n.granted || !anyGranted ? 0 : quiet;   // nothing granted → nothing withheld either
        return (
          // CENTRED IN ITS ROW (`height: rowH`). Top-aligned, the label sat on the row's top edge, which is exactly
          // where a bracket's border runs — with one bracket per granted run, single-row runs are common and
          // their border struck through the name it was enclosing.
          <div key={i} style={{position: 'absolute', left: left + n.depth * indent,
            top: y, height: rowH, width: width - n.depth * indent, opacity: on,
            color: n.granted || !anyGranted ? FG : DIM,
            filter: dimmed ? `opacity(${(1 - dimmed * 0.55).toFixed(2)})` : undefined,
            font: `${n.granted ? 700 : 400} ${font}px/1.15 var(--f-mono, ui-monospace, monospace)`,
            display: 'flex', alignItems: 'center', gap: pad * 0.6}}>
            <span style={{width: hair * 8, height: hair * 8, borderRadius: hair * 8,
              background: n.granted ? ACC : LINE, flex: '0 0 auto'}} />
            {n.label}
          </div>
        );
      })}

      {grantLabel && anyGranted ? (
        <div style={{position: 'absolute', left: left + width + pad * 2, top: gTop,
          opacity: chip, transform: `translateY(${(1 - chip) * pad}px)`,
          background: ACC, color: ON, padding: `${pad * 0.45}px ${pad}px`, borderRadius: pad * 0.5,
          font: `700 ${Math.round(base * 0.026)}px/1.2 var(--f-mono, ui-monospace, monospace)`}}>
          {grantLabel}
        </div>
      ) : null}

      {denyLabel && denyRow >= 0 ? (
        <div style={{position: 'absolute', left: left + width + pad * 2, top: rowY(denyRow), height: rowH,
          display: 'flex', alignItems: 'center', opacity: quiet * 0.9, color: DIM,
          font: `400 ${Math.round(base * 0.024)}px/1.2 var(--f-mono, ui-monospace, monospace)`}}>
          {denyLabel}
        </div>
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left, top: Math.min(top + treeH + pad * 2, zoneBottom - noteH + pad),
          width: W - left * 2, opacity: chip, color: DIM,
          font: `400 ${notePx}px/1.4 var(--f-body, system-ui, sans-serif)`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default GrantedTree;
