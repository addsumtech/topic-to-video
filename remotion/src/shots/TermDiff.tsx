// SHOT · TermDiff — a TERMINAL-NATIVE contrast (a `diff`). Default OPEN (grammar, no window box): a command
// executes and ---/+++ headers + red `-` / green `+` lines type out on the open canvas. `framed` = explicit
// terminal window. Deterministic (line reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 160;

export const TermDiff: React.FC<{cmd?: string; leftLabel?: string; rightLabel?: string; minus?: string[]; plus?: string[]; framed?: boolean}> = ({
  cmd = 'diff a b', leftLabel = 'before', rightLabel = 'after', minus = ['old line'], plus = ['new line'], framed = false} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4', red = '#ff6b6b';
  const all = [...minus.map((x) => ({s: '-', c: red, text: x})), ...plus.map((x) => ({s: '+', c: acc, text: x}))];

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 40px/1.4 ${mono}`, width: '100%'}}>
          <div style={{color: red, opacity: clamp01(seg(t, 0.22, 0.3))}}>--- {leftLabel}</div>
          <div style={{color: acc, opacity: clamp01(seg(t, 0.26, 0.34)), marginBottom: 22}}>+++ {rightLabel}</div>
          {all.map((r, i) => {
            const start = 0.34 + i * 0.13;
            const show = clamp01(seg(t, start, start + 0.1));
            if (show <= 0) return null;
            return (
              <div key={i} style={{display: 'flex', gap: 22, padding: '14px 24px', background: `${r.c}12`, opacity: show,
                transform: `translateX(${(1 - show) * -12}px)`, borderLeft: `4px solid ${r.c}`, marginBottom: 12}}>
                <span style={{color: r.c, fontWeight: 800, width: '1ch'}}>{r.s}</span>
                <span style={{color: r.s === '-' ? dim : fg}}>{r.text}</span>
              </div>
            );
          })}
        </div>
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermDiff;
