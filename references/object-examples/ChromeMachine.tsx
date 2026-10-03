// BAD — AN IMITATION OF A PHOTOGRAPH. Gradients and a highlight dressing up an espresso machine: it looks like
// clip-art, it shows no mechanism, and it competes with the real thing a documentary image would show. When a
// beat needs the machine as it LOOKS, composite a real, credited image (references/remotion-shot-authoring.md,
// the documentary tier); when it needs how it WORKS, draw the mechanism (PuckInSection). It passes every gate.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';

export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};

export const ChromeMachine: React.FC<ObjectProps> = ({w, h}) => (
  <svg width={w} height={h} style={{display: 'block'}}>
    <defs>
      <linearGradient id="chrome" x1="0" x2="1">
        <stop offset="0" stopColor="#6b6f76" /><stop offset="0.45" stopColor="#f4f6f9" /><stop offset="1" stopColor="#50545b" />
      </linearGradient>
    </defs>
    <rect x={w * 0.15} y={h * 0.15} width={w * 0.7} height={h * 0.6} rx={w * 0.04} fill="url(#chrome)" />
    <circle cx={w * 0.5} cy={h * 0.5} r={w * 0.09} fill="#2b2e33" />
    <ellipse cx={w * 0.38} cy={h * 0.25} rx={w * 0.12} ry={h * 0.03} fill="#ffffff" opacity={0.6} />
    <rect x={w * 0.2} y={h * 0.78} width={w * 0.6} height={h * 0.05} fill="#3a3d42" />
  </svg>
);
