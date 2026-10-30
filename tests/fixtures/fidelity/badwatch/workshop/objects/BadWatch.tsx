// OBJECT · BadWatch — a DELIBERATELY UNFAITHFUL wristwatch, the fidelity sheet's negative fixture
// (tests/test_fidelity.py). It declares a case, a band and a crown, and draws the band floating apart from the case
// and no crown at all: scripts/fidelity.py must report the crown MISSING and the band DETACHED. Never promote it.
import React from 'react';
import type {ObjectProps} from '@runtime/objectSlot';
import type {FidelityMeta} from '@runtime/fidelity';

export const META: FidelityMeta = {aspect: 0.6, provenance: 'product-ui', fidelity: {
  subject: 'an analogue wristwatch',
  depicts: 'real',
  references: [{kind: 'photo', source: 'refs/watch.jpg', note: 'an analogue wristwatch on a desk (Wikimedia Commons)'}],
  proportions: {band_width_to_case_width: {value: 0.6, source: 'refs/watch.jpg'}},
  parts: ['case', 'band', 'crown'],
  materials: ['steel case', 'rubber band'],
}};

export const BadWatch: React.FC<ObjectProps> = ({w, h, dna}) => {
  const ink = dna?.fg ?? '#e8eef6', acc = dna?.accent ?? '#f2c46b';
  const cw = w * 0.8, ch = cw, cx = (w - cw) / 2, cy = (h - ch) / 2;
  const bw = cw * 0.6, bx = (w - bw) / 2;
  return (
    <svg width={w} height={h} style={{display: 'block'}}>
      <g data-part="band">
        <rect x={bx} y={0} width={bw} height={cy - h * 0.08} rx={bw * 0.1} fill="#30343c" />
        <rect x={bx} y={cy + ch + h * 0.08} width={bw} height={h - (cy + ch + h * 0.08)} rx={bw * 0.1} fill="#30343c" />
      </g>
      <g data-part="case">
        <rect x={cx} y={cy} width={cw} height={ch} rx={cw * 0.22} fill="#1b1e24" stroke={ink} strokeWidth={w * 0.01} />
        <line x1={w / 2} y1={h / 2} x2={w / 2} y2={cy + ch * 0.25} stroke={acc} strokeWidth={w * 0.012} />
        <line x1={w / 2} y1={h / 2} x2={cx + cw * 0.72} y2={h / 2} stroke={ink} strokeWidth={w * 0.008} />
      </g>
    </svg>
  );
};
