// A test shot for runtime/blenderPlate: the plate over a known ground, a magenta dot on the plate's "top" anchor,
// and (optionally) a label at a given place, for plate_qa.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BlenderPlate, usePlate} from '@runtime/blenderPlate';
import {PLATES} from '../assets/plates';

export const DURATION = 4;
export const GROUND = '#204060';
export const PROVENANCE = 'scientific';

export const PlateProbe: React.FC<{label?: string; at?: number[]}> = ({label = '', at = [0, 0]}) => {
  const p = PLATES['sat'];
  const u = usePlate(p);
  const a = u.anchor('top');
  return (
    <AbsoluteFill style={{background: '#204060'}}>
      <BlenderPlate plate={p} />
      <div style={{position: 'absolute', left: a.x - 6, top: a.y - 6, width: 12, height: 12, background: '#ff00ff'}} />
      {label ? (
        <div style={{position: 'absolute', left: at[0], top: at[1], font: '700 40px sans-serif', color: '#ffffff'}}>{label}</div>
      ) : null}
    </AbsoluteFill>
  );
};
