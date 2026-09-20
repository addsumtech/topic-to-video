// SHOT · TermDiff — a TERMINAL-NATIVE contrast (a `diff`). Default OPEN (grammar, no window box): a command
// executes and ---/+++ headers + red `-` / green `+` lines type out on the open canvas. `framed` = explicit
// terminal window. Deterministic (line reveal = fn of t).
//
// EVERY LINE OF THE DIFF IS DRAWN. Line i used to arrive at `0.34 + i * 0.13` — a fixed step — so the fifth
// line landed just before the end, the sixth started at 0.99 and reached a tenth of its opacity on the last
// frame, and any line after that was never drawn at all, with no error: a film whose change had six lines
// showed five. The step is now laid out for the count — 0.13 stays the upper bound, so four lines keep their
// exact rhythm — and closes until the last line has landed by LAND_BY, just before the frame `useT` calls
// settled. Past MAX_DIFF_LINES the lines would arrive faster than a before/after can be read, and the
// register refuses. The lines that now arrive are fitted: the type steps down from 40px (never below 22) until
// the whole diff sits in the content zone, which the block is now centred on rather than on the frame.
//
// THE REMOVED-LINE COLOUR COMES FROM THE FILM. It was a literal `#ff6b6b` whatever the DNA said, so a themed
// film got one foreign red on every diff. Under a DNA the `-` side takes the DNA's second accent (the `+` side
// already took its accent); with no DNA it is the original red.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, REDUCED_MOTION_T} from '../runtime/motion';
import {useDNA, TermFrame, termInnerW} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, monoFit, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 160;

export const MAX_DIFF_LINES = 8;
// Line i slides in over [LINE_START + i * step, … + LINE_DUR]; LINE_STEP is the original gap and only an upper
// bound — the real step is derived from the count so the last line has landed by LAND_BY.
const LINE_START = 0.34, LINE_STEP = 0.13, LINE_DUR = 0.1;
const LAND_BY = REDUCED_MOTION_T - 0.02;
const PX0 = 40, PX_MIN = 22;

export const TermDiff: React.FC<{cmd?: string; leftLabel?: string; rightLabel?: string; minus?: string[]; plus?: string[]; framed?: boolean}> = ({
  cmd = 'diff a b', leftLabel = 'before', rightLabel = 'after', minus = ['old line'], plus = ['new line'], framed = false} = {}) => {
  if (!Array.isArray(minus) || !Array.isArray(plus)) {
    throw new Error('TermDiff: `minus` and `plus` must be arrays of lines (pass [] for a side with no lines).');
  }
  const n = minus.length + plus.length;
  if (n < 1 || n > MAX_DIFF_LINES) {
    throw new Error(
      `TermDiff needs 1-${MAX_DIFF_LINES} lines across \`minus\` and \`plus\` (got ${n}). ` +
      (n < 1 ? 'With no line there is no change to show.'
        : `Each line slides in one after another and must have landed before the settled frame; past ${MAX_DIFF_LINES} ` +
          'they arrive faster than a before/after can be read. Show the lines that carry the change, or use a ' +
          'side-by-side register (VersusSplit) for two whole sides.'));
  }
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const fg = dna?.fg ?? '#cdd7e4', dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4';
  const red = dna ? dna.accent2 : '#ff6b6b';
  const all = [...minus.map((x) => ({s: '-', c: red, text: String(x ?? '')})),
               ...plus.map((x) => ({s: '+', c: acc, text: String(x ?? '')}))];
  const step = n > 1 ? Math.min(LINE_STEP, (LAND_BY - LINE_START - LINE_DUR) / (n - 1)) : LINE_STEP;

  // THE FIT, in the measures the block really gets: TermFrame's inner width, less each row's padding, rule,
  // gutter and sign; the command line (or the framed title bar) above; two headers; every row's wrapped lines.
  const M = monoFit();
  const lead = leading([leftLabel, rightLabel, ...all.map((r) => r.text)], 1.4);
  const headH = framed ? 118 : 70;
  const needH = (f: number) => {
    const k = f / PX0;
    const textW = termInnerW(W, framed) - 48 * k - 4 - 22 * k - f * M.adv;
    const rows = all.reduce((h, r) => h + wrapLines(r.text || ' ', f, textW, M) * f * lead + 40 * k, 0);
    return headH + 2 * f * lead + 22 * k + rows;
  };
  const room = contentBottom(W, H) - CONTENT_TOP;
  let fs = PX0;
  while (fs > PX_MIN && needH(fs) > room) fs -= 1;
  if (needH(fs) > room) {
    throw new Error(
      `TermDiff: these ${n} lines need ${Math.round(needH(PX_MIN))}px at the ${PX_MIN}px floor and the content ` +
      `zone leaves ${Math.round(room)}px at ${W}x${H}. Shorten the lines or pass fewer of them.`);
  }
  const k = fs / PX0;
  const px = (v: number) => Math.round(v * k);

  return (
    // CENTRED ON THE CONTENT ZONE, NOT THE FRAME: the fit above is against the zone, so the block must sit in it.
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      paddingTop: CONTENT_TOP, paddingBottom: H - contentBottom(W, H)}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 ${fs}px/${lead} ${mono}`, width: '100%'}}>
          <div style={{color: red, opacity: clamp01(seg(t, 0.22, 0.3))}}>--- {leftLabel}</div>
          <div style={{color: acc, opacity: clamp01(seg(t, 0.26, 0.34)), marginBottom: px(22)}}>+++ {rightLabel}</div>
          {all.map((r, i) => {
            const start = LINE_START + i * step;
            const show = clamp01(seg(t, start, start + LINE_DUR));
            if (show <= 0) return null;
            return (
              <div key={i} style={{display: 'flex', gap: px(22), padding: `${px(14)}px ${px(24)}px`, background: `${r.c}12`, opacity: show,
                transform: `translateX(${(1 - show) * -12}px)`, borderLeft: `4px solid ${r.c}`, marginBottom: px(12)}}>
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
