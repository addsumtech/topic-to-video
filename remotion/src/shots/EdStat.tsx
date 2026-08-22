// SHOT · EdStat — an EDITORIAL pull-stat (the editorial analogue of TermCounter): a kicker + a HUGE serif figure
// + a caption, ruled like a magazine feature. The 'metric/hero-stat' idea rebuilt in the editorial DNA, not a
// terminal counter reskinned. Deterministic (count = fn of t; lands ~68% then holds).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, lerp} from '../runtime/motion';
import {useDNA, EdFrame} from '../runtime/dna';
import {Figure} from '../runtime/atoms';

export const DURATION = 155;

export const EdStat: React.FC<{kicker?: string; value?: string; unit?: string; caption?: string; framed?: boolean}> = ({
  kicker = 'BY THE NUMBERS', value = '100', unit = '', caption = '', framed = false} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const fg = dna?.fg ?? '#efe9df', dim = dna?.dim ?? '#9a9084', acc = dna?.accent ?? '#e2603f';
  const num = parseFloat(String(value).replace(/[^\d.]/g, '')) || 0;
  const decimals = (String(value).split('.')[1]?.replace(/[^\d]/g, '') || '').length;
  const g = easeOutCubic(clamp01(seg(t, 0.22, 0.7)));
  const cur = lerp(0, num, g);
  const fmt = (v: number) => num >= 1000 ? Math.round(v).toLocaleString('en-US') : v.toFixed(decimals);
  const shown = fmt(cur);
  // WIDTH-AWARE: size the figure by its FINAL string length so a big number ("5,000,000") stays inside the frame
  // (a fixed 260px overflowed the surface + ran the unit off-screen). Sizing off the landed value keeps it stable
  // (no reflow jitter as it counts up — intermediate strings are shorter, so they always fit). Unit may wrap below.
  const finalLen = fmt(num).length;
  const numSize = Math.max(108, Math.min(260, Math.floor(1120 / (finalLen * 0.6))));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(120% 120% at 50% -6%, #1c1815, #0d0b09 74%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <EdFrame dna={dna} kicker={kicker} t={t} framed={framed} align="left">
        <div style={{display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: 22, maxWidth: '100%'}}>
          <Figure value={shown} unit={unit} ink={fg} tone={acc} size={numSize} />
        </div>
        {caption ? <div style={{marginTop: 30, color: dim, font: `400 36px/1.4 ${body}`, maxWidth: 900}}>{caption}</div> : null}
      </EdFrame>
    </AbsoluteFill>
  );
};
export default EdStat;
