// SHOT · TermCounter — a TERMINAL-NATIVE key figure. Default OPEN (grammar, no window box): a command executes
// and ONE huge mono number counts up on the open canvas, unit + note below. `framed` = explicit terminal window.
// Deterministic (count = fn of t; lands ~68% then holds so the figure registers).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, lerp} from '../runtime/motion';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 150;

export const TermCounter: React.FC<{cmd?: string; value?: string; unit?: string; note?: string; framed?: boolean}> = ({
  cmd = 'stat --value', value = '100', unit = '', note = '', framed = false} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4';
  const num = parseFloat(String(value).replace(/[^\d.]/g, '')) || 0;
  const decimals = (String(value).split('.')[1]?.replace(/[^\d]/g, '') || '').length;
  const g = easeOutCubic(clamp01(seg(t, 0.24, 0.7)));
  const cur = lerp(0, num, g);
  const shown = num >= 1000 ? Math.round(cur).toLocaleString('en-US') : cur.toFixed(decimals);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="center">
        <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 20}}>
          <span style={{color: acc, font: `800 220px/0.9 ${mono}`, letterSpacing: '-4px', textShadow: `0 0 60px ${acc}44`,
            fontVariantNumeric: 'tabular-nums'}}>{shown}</span>
          {unit ? <span style={{color: dim, font: `600 56px/1 ${mono}`}}>{unit}</span> : null}
        </div>
        {note ? <div style={{marginTop: 34, color: dim, font: `500 34px/1.4 ${mono}`, textAlign: 'center'}}># {note}</div> : null}
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermCounter;
