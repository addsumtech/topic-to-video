// SHOT · TermGitLog — a TERMINAL-NATIVE version history (`git log --graph`). Default OPEN (grammar, no window
// box): a command executes and the commit graph types out on the open canvas. `framed` = explicit terminal
// window. Deterministic (commit reveal = fn of t).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA, TermFrame, termInnerW} from '../runtime/dna';
import {clipCells, monoCells, monoFit} from '../runtime/layout';

export const DURATION = 165;

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  '← HEAD',
];
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
  // A REF COLUMN IS COUNTED IN CELLS, NOT CHARACTERS. `minWidth` is set in `ch`, and `ch` is one cell —
  // but a Han glyph occupies TWO of them, so a character count reserved half the column a Chinese ref
  // needs and the message beside it started inside the parenthesis. Same defect as TermTree's tree.
  const refW = Math.max(...commits.map((c) => monoCells(c.ref ?? '')), 4);
  // AND THE ROW IS SIZED TO THE WIDTH IT IS ACTUALLY GIVEN. 38px was chosen against a 1920-wide frame and
  // English commit messages; `white-space: pre` then guarantees the row cannot wrap out of trouble, so a
  // Chinese message ran 345px past the edge and '← HEAD' 510px. The widest row decides the size, measured
  // in the cells the face really advances. It can only ever shrink: short Latin rows still get their 38px.
  const M = monoFit();
  const GAPS = 18 * 3 + 10;   // the flex gaps and the HEAD margin are fixed px — they do not scale with the type
  const INNER = termInnerW(W, framed);
  // A LOG TRUNCATES; IT DOES NOT SHRINK. Sizing the whole log to its longest message is correct arithmetic
  // and the wrong form: a 26-glyph Chinese subject drove every row to 19px, which is not a terminal any
  // more. `git log --oneline` gives the subject the room the line has and the terminal clips the rest, so
  // the message is clipped to what survives at a size a terminal is still legible at, and the fit then
  // does the remaining work. Latin rows are far inside the budget and are never touched.
  const MIN_PX = 22;
  const fixedCells = (i: number, c: Commit) =>
    monoCells('*' + String(c.hash ?? '')) + refW + 2 + (i === 0 ? monoCells('← HEAD') : 0);
  const msgBudget = (i: number, c: Commit) =>
    Math.max(8, Math.floor((INNER - GAPS) / (MIN_PX * M.adv)) - fixedCells(i, c));
  const rows = commits.map((c, i) => ({...c, msg: clipCells(String(c.msg ?? ''), msgBudget(i, c))}));
  const widestCells = Math.max(...rows.map((c, i) => fixedCells(i, c) + monoCells(c.msg)));
  const rowPx = Math.max(MIN_PX, Math.min(38,
    Math.floor((INNER - GAPS) / Math.max(1, widestCells * M.adv))));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 ${rowPx}px/1 ${mono}`, whiteSpace: 'pre'}}>
          {rows.map((c, i) => {
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
