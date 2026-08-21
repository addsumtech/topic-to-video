// SHOT · TermThink — a TERMINAL-NATIVE reasoning stream. Default OPEN (grammar, no window box): a command
// executes, a prompt appears, then a <think>…</think> block EXPANDS with streaming reasoning, then the answer —
// the same checkpoint toggling into reasoning mode. `framed` = explicit terminal window. Deterministic.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 175;

export const TermThink: React.FC<{cmd?: string; question?: string; think?: string[]; answer?: string; framed?: boolean}> = ({
  cmd = 'hermes --mode hybrid', question = 'solve it', think = ['reason…'], answer = 'answer', framed = false} = {}) => {
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const border = dna?.surfaceBorder ?? '#26324c';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4', acc2 = dna?.accent2 ?? '#4d8cff';
  const caretOn = Math.floor(frame / 16) % 2 === 0;
  const n = think.length;
  const answered = t > 0.86;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 40px/1.5 ${mono}`, width: '100%'}}>
          <div style={{color: fg}}><span style={{color: acc}}>❯</span> {question}</div>
          <div style={{margin: '24px 0', border: `1px dashed ${acc2}66`, borderRadius: dna?.radius ?? 6,
            background: `${acc2}0e`, padding: '20px 28px', opacity: clamp01(seg(t, 0.28, 0.38))}}>
            <div style={{color: acc2, font: `700 30px/1 ${mono}`, marginBottom: 14}}>&lt;think&gt;</div>
            {think.map((ln, i) => {
              const start = 0.36 + i * (0.46 / Math.max(1, n));
              const show = clamp01(seg(t, start, start + 0.06));
              if (show <= 0) return null;
              return <div key={i} style={{color: dim, opacity: show, transform: `translateX(${(1 - show) * -10}px)`, margin: '6px 0'}}>
                <span style={{color: acc2, opacity: 0.6}}>│</span> {ln}</div>;
            })}
            <div style={{color: acc2, font: `700 30px/1 ${mono}`, marginTop: 14, opacity: answered ? 1 : 0.3}}>&lt;/think&gt;</div>
          </div>
          <div style={{color: answered ? fg : dim, opacity: clamp01(seg(t, 0.84, 0.92)), fontWeight: 700}}>
            <span style={{color: acc}}>=</span> {answer}
            <span style={{display: 'inline-block', width: 14, height: 30, marginLeft: 12, verticalAlign: 'text-bottom',
              background: acc, opacity: caretOn ? 0.9 : 0.12}} /></div>
        </div>
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermThink;
