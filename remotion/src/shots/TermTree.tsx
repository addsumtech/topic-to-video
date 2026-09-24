// SHOT · TermTree — a TERMINAL-NATIVE listing (an `ls`/file-tree). Default OPEN (grammar, no window box): a
// command executes and a tree of the topic's parts types out on the open canvas. `framed` = explicit terminal
// window. Deterministic (row reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {rows} from '../runtime/rows';
import {clipCells, fitMono, contentZoneBox, monoCells} from '../runtime/layout';
import {useDNA, TermFrame} from '../runtime/dna';

export const DURATION = 165;
type Item = {name?: string; note?: string; tag?: string};

// The reveal window: the first row starts here, each row takes TREE_SPAN, and the LAST one lands at
// TREE_START + 0.42 + TREE_SPAN = 0.80 — comfortably before the t=0.88 every gate in this repo samples.
const TREE_START = 0.26, TREE_SPAN = 0.12;

export const TermTree: React.FC<{cmd?: string; root?: string; items?: Item[]; framed?: boolean}> = ({
  cmd = 'ls -la', root = '~/project', framed = false,
  items: items_IN = [{name: 'src/', note: 'source', tag: 'ok'}, {name: 'docs/', note: 'docs', tag: 'ok'}]} = {}) => {
  const items = rows<Item>(items_IN, 'items', 'TermTree');
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4';
  // COUNTED IN CELLS, NOT IN CHARACTERS. A Han glyph is FULL-WIDTH in a monospace face — two cells — so a
  // character count reports a Chinese name at half its width, `fitMono` then solves for a size that fits a
  // line twice as narrow as the one it draws, and the tree runs off the right edge (measured: 2086px past
  // it at 16:9). The note and tag columns are measured the same way instead of being assumed at 14 and 6;
  // those stay as FLOORS, so the Latin demo resolves to the same numbers it always did.
  const nameW = Math.max(...items.map((i) => monoCells(i.name ?? '')), 10);
  // AND THE COLUMN IS BOUNDED. A line here cannot wrap — `white-space: pre` is what makes a tree a tree —
  // so a note long enough drives the fit down until the type is unreadable AND still overflows. A terminal
  // truncates; the column is 24 cells and anything past it ends in an ellipsis, which makes the size
  // solvable for any input rather than only for short ones.
  const NOTE_CELLS = 24;
  const note = (x?: string) => clipCells(String(x ?? ''), NOTE_CELLS);
  const noteW = Math.max(14, ...items.map((i) => monoCells(note(i.note))));
  const tagW = Math.max(6, ...items.map((i) => (i.tag ? monoCells(i.tag) + 3 : 0)));
  // SIZED TO THE FRAME, not to a literal. At a fixed 40px this tree occupied 9.0% of a 1920-wide frame —
  // the "small" half of the density diagnosis (scripts/register_energy.py reports it beside the ink). The
  // widest line is the tree glyphs, the name column, the note column and the tag, all monospace, so the
  // size that fills the content zone is solvable rather than guessed.
  const lineChars = 4 + nameW + 1 + noteW + tagW;
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
            // THE STAGGER SCALES WITH THE LIST, and for a long time it did not. At a fixed 0.14 per row the
            // fifth row finished at t=1.08 and the seventh at 1.36 — past the end of the shot, so a register
            // that accepts an unbounded `items` could never draw more than five of them, and the sixth
            // onward were permanently half-arrived. Worse at the frame everything samples: every gate here
            // reads t=0.88, where the fourth row was 50% in, so the "settled" frame of this register was
            // never settled. Spread over a fixed window instead and the whole list lands by TREE_SETTLE
            // whatever its length. At four items the step is 0.42/3 = 0.14, so every film that shipped
            // before this renders byte-identically.
            const step = 0.42 / Math.max(1, items.length - 1);
            const start = TREE_START + i * step;
            const show = clamp01(seg(t, start, start + TREE_SPAN));
            return (
              <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: Math.round(FS*0.55), opacity: show,
                transform: `translateX(${(1 - show) * -14}px)`}}>
                <span style={{color: dim}}>{last ? '└──' : '├──'}</span>
                <span style={{color: fg, minWidth: `${nameW}ch`}}>{(it.name ?? '').padEnd(nameW, ' ')}</span>
                {it.note ? <span style={{color: dim, minWidth: '14ch'}}>{note(it.note)}</span> : null}
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
