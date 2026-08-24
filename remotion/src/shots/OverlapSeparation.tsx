// SHOT · OverlapSeparation — STUB, to be authored. Registered so it can be still-rendered while it is written.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, clamp01, seg} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150;
const BG0 = '#0a0f16';

export const OverlapSeparation: React.FC<{title?: string}> = ({title: TITLE = 'OverlapSeparation'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const inn = clamp01(seg(t, 0.05, 0.3));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? (dna?.bg ?? BG0), color: dna?.fg ?? '#e8eef6'}}>
      <div style={{position: 'absolute', top: H * 0.45, left: 0, right: 0, textAlign: 'center', opacity: inn,
        font: `700 ${Math.round(W * 0.03)}px/1.2 var(--f-display, system-ui, sans-serif)`}}>{TITLE}</div>
    </AbsoluteFill>
  );
};
export default OverlapSeparation;
