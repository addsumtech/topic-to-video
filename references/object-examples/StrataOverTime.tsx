// GOOD — LAYERED STRATA. It ENCODES "each era was laid on the last": caption hidden, a viewer sees a column grow
// layer by layer from the bottom, each as thick as the film says it was (`layers`, oldest first), the newest on
// top in the accent. The stage's labels name the eras; the object draws only what the numbers say.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
import {clamp01, seg, easeOutCubic} from '@runtime/motion';
import {mix} from '@runtime/dna';

export const META: ObjectMeta = {aspect: 0.8, provenance: 'survey-archive'};

export const StrataOverTime: React.FC<ObjectProps & {layers?: number[]}> = ({w, h, t, dna, layers = []}) => {
  if (!Array.isArray(layers) || layers.length < 1 || layers.some((v) => !(typeof v === 'number' && v > 0))) {
    throw new Error('StrataOverTime: `layers` is a list of positive thicknesses, oldest first — got ' +
      JSON.stringify(layers));
  }
  const ink = dna?.fg ?? '#1c2230', acc = dna?.accent ?? '#3563e9', paper = dna?.surface ?? '#e9edf3';
  const total = layers.reduce((a, b) => a + b, 0);
  const n = layers.length;
  let y = h;
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      {layers.map((v, i) => {
        const th = (v / total) * h * 0.96;
        y -= th;
        const on = easeOutCubic(clamp01(seg(t, (i / n) * 0.8, (i / n) * 0.8 + 0.2)));
        // @positional: the last layer is the newest — the order of the list is time
        const newest = i === n - 1;
        return <rect key={i} x={w * 0.1} y={y - (1 - on) * h * 0.05} width={w * 0.8} height={th}
          fill={newest ? acc : mix(paper, ink, 0.12 + (0.5 * i) / Math.max(1, n - 1))} opacity={on}
          stroke={ink} strokeWidth={Math.max(1, w * 0.003)} />;
      })}
    </svg>
  );
};
