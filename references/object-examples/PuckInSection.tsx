// GOOD — A MECHANISM IN CUTAWAY. It ENCODES "water is forced through a packed bed": caption hidden, a viewer sees
// drops enter at the top and fight down through a dense layer — and the denser the layer (`packed`, 0..1) the thinner
// the bed, the fewer drops get through and the slower they go. It draws no words: the stage names the parts.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg, easeOutCubic, hash01} from '@runtime/motion';
import {pointAt} from '@runtime/alongPath';
import {mix} from '@runtime/dna';

export const META: ObjectMeta & {fidelity: object} = {aspect: 1, provenance: 'industrial', fidelity: {
  subject: 'a tamped espresso coffee bed in a 58 mm portafilter basket, in section', depicts: 'real',
  references: [
    {kind: 'photo', source: 'refs/portafilter.jpg', note: 'portafilters and filter baskets (Wikimedia Commons, CC BY-SA 2.0)'},
    {kind: 'spec', source: 'https://beanbros.co/en-dk/products/e-b-lab-precision-filter-basket-58mm',
      note: 'E&B Lab 58 mm basket: rim 70 mm, height 24 mm, 715 holes across 49 mm, flat bottom'},
    {kind: 'spec', source: 'https://www.maxicoffee.com/en-gb/h24-ridgeless-filter-basket-1618g-nanotechnological-coating-p-40540.html',
      note: 'E&B Lab H24: 58 mm ridgeless, height 24 mm, micro-perforated'},
  ],
  proportions: {
    depth_to_diameter: {value: 0.41, drawn: 0.41, source: 'https://beanbros.co/en-dk/products/e-b-lab-precision-filter-basket-58mm'},
    rim_to_diameter: {value: '70 / 58 = 1.21', drawn: 1.21, source: 'https://beanbros.co/en-dk/products/e-b-lab-precision-filter-basket-58mm'},
    perforated_share_of_floor: {value: '49 / 58 = 0.84', drawn: 0.84, source: 'https://beanbros.co/en-dk/products/e-b-lab-precision-filter-basket-58mm'},
    hole_pitch: {value: '715 holes over a 49 mm disc: about 1.75 mm apart', drawn: '1.75 mm',
      source: 'https://beanbros.co/en-dk/products/e-b-lab-precision-filter-basket-58mm'},
  },
  parts: ['basket-wall', 'basket-floor', 'coffee-bed'],
  materials: ['stainless-steel basket, its floor perforated', 'compacted ground coffee'],
}};

export const PuckInSection: React.FC<ObjectProps & {packed?: number}> = ({w, h, t, dna, packed = 0.8}) => {
  if (!(typeof packed === 'number' && packed >= 0 && packed <= 1)) {
    throw new Error(`PuckInSection: \`packed\` is 0..1 — got ${JSON.stringify(packed)}`);
  }
  const ink = dna?.fg ?? '#1c2230', acc = dna?.accent ?? '#3563e9', paper = dna?.surface ?? '#e9edf3';
  const wall = Math.max(3, w * 0.012);
  // THE BASKET IN ITS OWN PROPORTIONS (META.fidelity): 58 mm across inside, 24 mm deep, a 70 mm rim, a flat floor
  // perforated across its middle 49 mm. It was drawn 0.75 deep and solid-floored, a cup the water could not leave.
  const x0 = w * 0.2, x1 = w * 0.8, mm = (x1 - x0) / 58;
  const bot = h * 0.72, top = bot - 24 * mm;
  const lip = 6 * mm;                                        // (70 − 58) / 2: the rim's flange each side
  const bedTop = bot - (bot - top) * (0.8 - 0.35 * packed);   // packed harder, the bed is thinner and denser
  const bedIn = easeOutCubic(clamp01(seg(t, 0, 0.3)));
  const grains = Math.round(160 + 340 * packed);
  const lanes = 7, passing = Math.round(lanes * (1 - 0.6 * packed));
  // the floor: solid for 4.5 mm at each wall, then a hole every 1.75 mm across the middle 49 mm
  const pitch = 1.75 * mm, hole = Math.max(1.5, 0.3 * mm), px0 = x0 + 4.5 * mm, px1 = x1 - 4.5 * mm;
  const nHoles = Math.floor((px1 - px0) / pitch);
  const floor: string[] = [`M ${x0} ${bot} L ${px0} ${bot}`];
  for (let k = 0; k < nHoles; k++) {
    const a = px0 + k * pitch + hole / 2, b = Math.min(px1, px0 + (k + 1) * pitch - hole / 2);
    floor.push(`M ${a.toFixed(1)} ${bot} L ${b.toFixed(1)} ${bot}`);
  }
  floor.push(`M ${px1} ${bot} L ${x1} ${bot}`);
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      <rect data-part="coffee-bed" x={x0} y={bedTop} width={x1 - x0} height={bot - bedTop} fill={mix(paper, ink, 0.25 + 0.35 * packed)}
        opacity={bedIn} />
      {Array.from({length: grains}).map((_, i) => (   // @decor: stipple texture; its density follows `packed`
        <circle key={i} cx={x0 + (x1 - x0) * hash01(i * 2 + 1)} cy={bedTop + (bot - bedTop) * hash01(i * 2 + 2)}
          r={w * 0.004} fill={ink} opacity={0.35 * bedIn} />
      ))}
      {/* the steel over the bed's edges, so the section reads crisp */}
      <path data-part="basket-wall" d={`M ${x0 - lip} ${top} L ${x0} ${top} L ${x0} ${bot} M ${x1} ${bot} L ${x1} ${top} L ${x1 + lip} ${top}`}
        fill="none" stroke={ink} strokeWidth={wall} strokeLinejoin="round" strokeLinecap="round" />
      <path data-part="basket-floor" d={floor.join(' ')} fill="none" stroke={ink} strokeWidth={wall} />
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
