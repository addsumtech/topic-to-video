// GOOD — A MECHANISM IN CUTAWAY. It ENCODES "water is forced through a packed bed": caption hidden, a viewer sees
// drops enter at the top and fight down through a dense layer — and the denser the layer (`packed`, 0..1) the thinner
// the bed, the fewer drops get through and the slower they go. It draws no words: the stage names the parts.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg, easeOutCubic, hash01} from '@runtime/motion';
import {pointAt} from '@runtime/alongPath';
import {mix} from '@runtime/dna';

export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};

export const PuckInSection: React.FC<ObjectProps & {packed?: number}> = ({w, h, t, dna, packed = 0.8}) => {
  if (!(typeof packed === 'number' && packed >= 0 && packed <= 1)) {
    throw new Error(`PuckInSection: \`packed\` is 0..1 — got ${JSON.stringify(packed)}`);
  }
  const ink = dna?.fg ?? '#1c2230', acc = dna?.accent ?? '#3563e9', paper = dna?.surface ?? '#e9edf3';
  const wall = Math.max(3, w * 0.012);
  const x0 = w * 0.18, x1 = w * 0.82, top = h * 0.3, bot = h * 0.78;
  const bedTop = bot - (bot - top) * (0.55 - 0.25 * packed);     // packed harder, the bed is thinner and denser
  const bedIn = easeOutCubic(clamp01(seg(t, 0, 0.3)));
  const grains = Math.round(160 + 340 * packed);
  const lanes = 7, passing = Math.round(lanes * (1 - 0.6 * packed));
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      <path d={`M ${x0} ${top} L ${x0} ${bot} L ${x1} ${bot} L ${x1} ${top}`} fill="none" stroke={ink}
        strokeWidth={wall} strokeLinejoin="round" />
      <rect x={x0} y={bedTop} width={x1 - x0} height={bot - bedTop} fill={mix(paper, ink, 0.25 + 0.35 * packed)}
        opacity={bedIn} />
      {Array.from({length: grains}).map((_, i) => (   // @decor: stipple texture; its density follows `packed`
        <circle key={i} cx={x0 + (x1 - x0) * hash01(i * 2 + 1)} cy={bedTop + (bot - bedTop) * hash01(i * 2 + 2)}
          r={w * 0.004} fill={ink} opacity={0.35 * bedIn} />
      ))}
      {Array.from({length: lanes}).map((_, k) => {
        const x = x0 + ((x1 - x0) * (k + 0.5)) / lanes;
        const d = `M ${x} ${h * 0.08} L ${x} ${bot + h * 0.12}`;
        // @positional: how MANY lanes pass follows `packed`; which ones is the order they are drawn in
        const through = k < passing;
        const u = clamp01(seg(t, 0.25 + k * 0.03, 0.25 + k * 0.03 + 0.35 + 0.35 * packed));
        const stop = through ? 1 : (bedTop - h * 0.08) / (bot + h * 0.04);
        const p = pointAt(d, Math.min(u, stop));
        return <circle key={k} cx={p.x} cy={p.y} r={w * 0.02} fill={acc} opacity={u > 0 ? 1 : 0} />;
      })}
    </svg>
  );
};
