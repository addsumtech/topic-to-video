// BAD — WORDS WRITTEN INTO THE OBJECT. The bed and the water are named in Chinese in the code itself, so a film in
// any other language prints Chinese, and no prop can change them. scripts/workshop.py check refuses it.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';

export const META: ObjectMeta & {fidelity: object} = {aspect: 1, provenance: 'industrial', fidelity: {
  subject: 'a tamped espresso coffee bed in a 58 mm portafilter basket, in section', depicts: 'real',
  references: [
    {kind: 'photo', source: 'refs/portafilter.jpg', note: 'portafilters and filter baskets (Wikimedia Commons, CC BY-SA 2.0)'},
    {kind: 'spec', source: 'https://beanbros.co/en-dk/products/e-b-lab-precision-filter-basket-58mm',
      note: 'E&B Lab 58 mm basket: rim 70 mm, height 24 mm, 715 holes across 49 mm, flat bottom'},
  ],
  proportions: {depth_to_diameter: {value: 0.41, drawn: 0.75, source: 'https://beanbros.co/en-dk/products/e-b-lab-precision-filter-basket-58mm'}},
  parts: ['coffee-bed'],
  materials: ['stainless-steel basket', 'compacted ground coffee'],
}};

export const LabeledPuck: React.FC<ObjectProps> = ({w, h, dna}) => (
  <svg width={w} height={h} style={{display: 'block'}}>
    <rect data-part="coffee-bed" x={w * 0.2} y={h * 0.55} width={w * 0.6} height={h * 0.2} fill={dna?.fg ?? '#1c2230'} opacity={0.5} />
    <text x={w * 0.5} y={h * 0.68} textAnchor="middle" fontSize={w * 0.06} fill={dna?.bg ?? '#ffffff'}>粉饼</text>
    <text x={w * 0.5} y={h * 0.3} textAnchor="middle" fontSize={w * 0.06} fill={dna?.accent ?? '#3563e9'}>水</text>
  </svg>
);
