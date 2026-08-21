// SHOT · TermGitLog — a TERMINAL-NATIVE version history (`git log --graph`). Default OPEN (grammar, no window
// box): a command executes and the commit graph types out on the open canvas. `framed` = explicit terminal
// window. Deterministic (commit reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 165;
type Commit = {hash?: string; ref?: string; msg?: string};

export const TermGitLog: React.FC<{cmd?: string; commits?: Commit[]; framed?: boolean}> = ({
  cmd = 'git log --oneline --graph', framed = false,
  commits = [{hash: 'a1b2c3d', ref: 'v2', msg: 'second'}, {hash: 'e4f5a6b', ref: 'v1', msg: 'first'}]} = {}) => {
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4', acc2 = dna?.accent2 ?? '#4d8cff';
  const refW = Math.max(...commits.map((c) => [...(c.ref ?? '')].length), 4);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 38px/1 ${mono}`, whiteSpace: 'pre'}}>
          {commits.map((c, i) => {
            const start = 0.24 + i * 0.16;
            const show = clamp01(seg(t, start, start + 0.13));
            const head = i === 0;
            return (
              <React.Fragment key={i}>
                <div style={{display: 'flex', alignItems: 'baseline', gap: 18, opacity: show, margin: '12px 0',
                  transform: `translateX(${(1 - show) * -10}px)`}}>
                  <span style={{color: acc, textShadow: head ? `0 0 10px ${acc}` : 'none'}}>*</span>
                  <span style={{color: dim}}>{c.hash}</span>
                  <span style={{color: head ? acc : acc2, minWidth: `${refW + 2}ch`}}>({c.ref})</span>
                  <span style={{color: fg}}>{c.msg}</span>
                  {head ? <span style={{color: dim, marginLeft: 10}}>← HEAD</span> : null}
                </div>
                {i < commits.length - 1 ? <div style={{color: dim, opacity: show, height: 16, lineHeight: '16px'}}>│</div> : null}
              </React.Fragment>
            );
          })}
        </div>
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermGitLog;
