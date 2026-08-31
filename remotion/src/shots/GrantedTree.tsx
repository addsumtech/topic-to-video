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
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', ACC_D0 = '#4f8cff', DIM_D0 = '#7c8798', LINE_D0 = '#1e2733';

type Node = {label?: string; depth?: number; granted?: boolean};

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

  const rows = NODES.slice(0, 8);
  const rowH = Math.round(base * 0.072);
  const font = Math.round(base * 0.034);
  const pad = Math.round(base * 0.018);
  const hair = Math.max(1, Math.round(base * 0.0018));
  const indent = Math.round(base * 0.055);

  // The tree is placed as a block inside the content zone, never against the frame edge and never into the
  // band the burned caption owns.
  const treeH = rows.length * rowH + (root ? rowH : 0);
  const top = Math.max(CONTENT_TOP + pad, (CONTENT_TOP + zoneBottom - treeH) / 2);
  const left = Math.round(W * 0.14);
  const width = Math.round(W * 0.46);

  const inn = (i: number) => easeOutCubic(clamp01(seg(t, 0.06 + i * 0.035, 0.28 + i * 0.035)));
  const bracket = easeOutCubic(clamp01(seg(t, 0.40, 0.62)));   // the boundary draws itself
  const chip = easeOutCubic(clamp01(seg(t, 0.60, 0.76)));
  const quiet = clamp01(seg(t, 0.66, 0.86));                   // the rest goes quiet AFTER the edge exists

  const gi = rows.map((n, i) => (n.granted ? i : -1)).filter((i) => i >= 0);
  const gTop = gi.length ? top + (root ? rowH : 0) + gi[0] * rowH : 0;
  const gBot = gi.length ? top + (root ? rowH : 0) + (gi[gi.length - 1] + 1) * rowH : 0;

  return (
    <AbsoluteFill style={{background: BG, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left, top: CONTENT_TOP, opacity: inn(0),
          letterSpacing: '0.14em', color: ACC,
          font: `700 ${Math.round(base * 0.024)}px/1.2 var(--f-mono, ui-monospace, monospace)`}}>
          {kicker}
        </div>
      ) : null}

      {/* the granted branch's BRACKET — drawn, not implied */}
      {gi.length ? (
        <div style={{position: 'absolute', left: left - pad, top: gTop,
          width: width + pad * 2, height: (gBot - gTop) * bracket,
          border: `${hair * 2}px solid ${ACC}`, borderRadius: pad * 0.6,
          opacity: bracket, boxSizing: 'border-box'}} />
      ) : null}

      {root ? (
        <div style={{position: 'absolute', left, top, width, opacity: inn(0), color: DIM,
          font: `500 ${font}px/1.15 var(--f-mono, ui-monospace, monospace)`}}>{root}</div>
      ) : null}

      {rows.map((n, i) => {
        const y = top + (root ? rowH : 0) + i * rowH;
        const on = inn(i + 1);
        const dimmed = n.granted ? 0 : quiet;
        return (
          <div key={i} style={{position: 'absolute', left: left + (n.depth ?? 0) * indent,
            top: y, width: width - (n.depth ?? 0) * indent, opacity: on,
            color: n.granted ? FG : DIM,
            filter: dimmed ? `opacity(${(1 - dimmed * 0.55).toFixed(2)})` : undefined,
            font: `${n.granted ? 700 : 400} ${font}px/1.15 var(--f-mono, ui-monospace, monospace)`,
            display: 'flex', alignItems: 'center', gap: pad * 0.6}}>
            <span style={{width: hair * 8, height: hair * 8, borderRadius: hair * 8,
              background: n.granted ? ACC : LINE, flex: '0 0 auto'}} />
            {n.label ?? ''}
          </div>
        );
      })}

      {grantLabel && gi.length ? (
        <div style={{position: 'absolute', left: left + width + pad * 2, top: gTop,
          opacity: chip, transform: `translateY(${(1 - chip) * pad}px)`,
          background: ACC, color: ON, padding: `${pad * 0.45}px ${pad}px`, borderRadius: pad * 0.5,
          font: `700 ${Math.round(base * 0.026)}px/1.2 var(--f-mono, ui-monospace, monospace)`}}>
          {grantLabel}
        </div>
      ) : null}

      {denyLabel ? (
        <div style={{position: 'absolute', left: left + width + pad * 2, top: gBot + pad,
          opacity: quiet * 0.9, color: DIM,
          font: `400 ${Math.round(base * 0.024)}px/1.2 var(--f-mono, ui-monospace, monospace)`}}>
          {denyLabel}
        </div>
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left, top: Math.min(top + treeH + pad * 2, zoneBottom - font * 2),
          width: W - left * 2, opacity: chip, color: DIM,
          font: `400 ${Math.round(base * 0.026)}px/1.4 var(--f-body, system-ui, sans-serif)`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default GrantedTree;
