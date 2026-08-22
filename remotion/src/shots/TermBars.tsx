// SHOT · TermBars — a TERMINAL-NATIVE metric readout. Default OPEN (no window box): a `$ eval` command executes
// and the figures grow out as block-character progress bars on the open canvas (command→result motion). Set
// `framed` to render it inside an explicit terminal window (an anchor beat). Deterministic (fill = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, TermFrame} from '../runtime/dna';
import {Bar} from '../runtime/atoms';

export const DURATION = 165;
type Row = {label?: string; fill?: number; value?: string; tag?: string};

export const TermBars: React.FC<{cmd?: string; rows?: Row[]; note?: string; cells?: number; framed?: boolean}> = ({
  cmd = 'eval --suite bench', cells = 28, note = '', framed = false,
  rows = [{label: 'metric_a', fill: 0.9, tag: 'PASS'}, {label: 'metric_b', fill: 0.84, tag: 'PASS'}]} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4';
  const pad = Math.max(...rows.map((r) => [...(r.label ?? '')].length), 8);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        {rows.map((r, i) => {
          const start = 0.24 + i * 0.2;
          const g = easeOutCubic(clamp01(seg(t, start, start + 0.4)));
          const target = clamp01(r.fill ?? 0);
          const pct = Math.round(100 * target * g);
          const done = g > 0.98;
          return (
            <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 24, margin: i ? '30px 0 0' : 0,
              font: `500 40px/1.2 ${mono}`, whiteSpace: 'pre', opacity: clamp01(seg(t, start - 0.04, start + 0.06))}}>
              <Bar value={target * g} label={r.label} tag={r.value ?? `${pct}%`} cells={cells}
                size={40} tone={acc} ink={fg} dimInk={dim} labelWidth={`${pad}ch`} fallbackForm="block" />
              <span style={{color: done ? acc : dim, opacity: done ? 1 : 0.4, border: `1px solid ${done ? acc : dim}`,
                borderRadius: 4, padding: '3px 11px', font: `700 22px/1 ${mono}`, marginLeft: 6}}>{r.tag ?? 'OK'}</span>
            </div>
          );
        })}
        {note ? <div style={{marginTop: 34, color: dim, font: `500 30px/1 ${mono}`}}># {note}</div> : null}
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermBars;
