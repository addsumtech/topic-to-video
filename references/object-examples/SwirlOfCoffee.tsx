// BAD — DECORATION THAT CARRIES NOTHING. A pretty spiral of coffee-coloured dots, turning: on topic by colour and
// by nothing else. Hide the caption and ask what it says about extraction — nothing. It passes every gate.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';

export const META: ObjectMeta = {aspect: 1, provenance: 'motion-graphics'};

export const SwirlOfCoffee: React.FC<ObjectProps> = ({w, h, t}) => (
  <svg width={w} height={h} style={{display: 'block'}}>
    {Array.from({length: 90}).map((_, i) => {   // @decor: a spiral — texture, and all it is
      const a = i * 0.35 + t * 4, r = (i / 90) * w * 0.45;
      return <circle key={i} cx={w / 2 + Math.cos(a) * r} cy={h / 2 + Math.sin(a) * r} r={w * 0.012}
        fill={i % 2 ? '#6f4e37' : '#c69c6d'} />;
    })}
  </svg>
);
