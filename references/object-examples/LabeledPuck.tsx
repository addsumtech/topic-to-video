// BAD — WORDS WRITTEN INTO THE OBJECT. The bed and the water are named in Chinese in the code itself, so a film in
// any other language prints Chinese, and no prop can change them. scripts/workshop.py check refuses it.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';

export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};

export const LabeledPuck: React.FC<ObjectProps> = ({w, h, dna}) => (
  <svg width={w} height={h} style={{display: 'block'}}>
    <rect x={w * 0.2} y={h * 0.55} width={w * 0.6} height={h * 0.2} fill={dna?.fg ?? '#1c2230'} opacity={0.5} />
    <text x={w * 0.5} y={h * 0.68} textAnchor="middle" fontSize={w * 0.06} fill={dna?.bg ?? '#ffffff'}>粉饼</text>
    <text x={w * 0.5} y={h * 0.3} textAnchor="middle" fontSize={w * 0.06} fill={dna?.accent ?? '#3563e9'}>水</text>
  </svg>
);
