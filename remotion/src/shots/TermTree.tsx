// SHOT · TermTree — a TERMINAL-NATIVE listing (an `ls`/file-tree). Default OPEN (grammar, no window box): a
// command executes and a tree of the topic's parts types out on the open canvas. `framed` = explicit terminal
// window. Deterministic (row reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {fitMono, contentZoneBox} from '../runtime/layout';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 165;
type Item = {name?: string; note?: string; tag?: string};

export const TermTree: React.FC<{cmd?: string; root?: string; items?: Item[]; framed?: boolean}> = ({
  cmd = 'ls -la', root = '~/project', framed = false,
  items = [{name: 'src/', note: 'source', tag: 'ok'}, {name: 'docs/', note: 'docs', tag: 'ok'}]} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4';
  const nameW = Math.max(...items.map((i) => [...(i.name ?? '')].length), 10);
  // SIZED TO THE FRAME, not to a literal. At a fixed 40px this tree occupied 9.0% of a 1920-wide frame —
  // the "small" half of the density diagnosis (scripts/register_energy.py reports it beside the ink). The
  // widest line is the tree glyphs, the name column, the note column and the tag, all monospace, so the
  // size that fills the content zone is solvable rather than guessed.
  const lineChars = 4 + nameW + 1 + 14 + 6;
  const zone = contentZoneBox(W, H);
  const FS = fitMono(lineChars, items.length + 1, zone, {fill: 0.8});

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 ${FS}px/1.6 ${mono}`, whiteSpace: 'pre'}}>
          <div style={{color: acc}}>{root}</div>
          {items.map((it, i) => {
            const last = i === items.length - 1;
            const start = 0.26 + i * 0.14;
            const show = clamp01(seg(t, start, start + 0.12));
            return (
              <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: Math.round(FS*0.55), opacity: show,
                transform: `translateX(${(1 - show) * -14}px)`}}>
                <span style={{color: dim}}>{last ? '└──' : '├──'}</span>
                <span style={{color: fg, minWidth: `${nameW}ch`}}>{(it.name ?? '').padEnd(nameW, ' ')}</span>
                {it.note ? <span style={{color: dim, minWidth: '14ch'}}>{it.note}</span> : null}
                {it.tag ? <span style={{color: acc, border: `1px solid ${acc}`, borderRadius: 4, padding: `${Math.round(FS*0.075)}px ${Math.round(FS*0.28)}px`,
                  font: `700 ${Math.round(FS * 0.55)}px/1 ${mono}`}}>{it.tag}</span> : null}
              </div>
            );
          })}
        </div>
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermTree;
