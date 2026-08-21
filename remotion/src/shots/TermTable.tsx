// SHOT · TermTable — a TERMINAL-NATIVE table (a `cat *.tsv` / config readout). Default OPEN (grammar, no window
// box): a command executes and a bordered mono table types out on the open canvas, one row optionally HERO-lit.
// `framed` = explicit terminal window. Deterministic (row reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 160;

export const TermTable: React.FC<{cmd?: string; headers?: string[]; rows?: string[][]; hero?: number; framed?: boolean}> = ({
  cmd = 'cat table.tsv', headers = ['col', 'value'], rows = [['a', '1'], ['b', '2']], hero = -1, framed = false} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const border = dna?.surfaceBorder ?? '#26324c';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4';
  const cell: React.CSSProperties = {padding: '18px 30px', borderBottom: `1px solid ${border}`, textAlign: 'left', whiteSpace: 'nowrap'};

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <table style={{borderCollapse: 'collapse', font: `500 40px/1 ${mono}`, border: `1px solid ${border}`}}>
          <thead>
            <tr style={{opacity: clamp01(seg(t, 0.22, 0.32))}}>
              {headers.map((h, i) => <th key={i} style={{...cell, color: dim, fontWeight: 600, letterSpacing: '0.06em',
                textTransform: 'uppercase', fontSize: 26, borderBottom: `2px solid ${border}`}}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => {
              const start = 0.3 + ri * 0.15;
              const show = clamp01(seg(t, start, start + 0.12));
              const isHero = ri === hero;
              return (
                <tr key={ri} style={{opacity: show, background: isHero ? `${acc}16` : 'transparent'}}>
                  {r.map((c, ci) => (
                    <td key={ci} style={{...cell, color: ci === 0 ? (isHero ? acc : fg) : fg,
                      borderLeft: isHero && ci === 0 ? `3px solid ${acc}` : `1px solid ${border}`, fontWeight: ci === 0 ? 700 : 500}}>
                      {c}{isHero && ci === r.length - 1 ? <span style={{color: acc, marginLeft: 16, fontSize: 24}}>◂ note</span> : null}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermTable;
