// SHOT · TermThink — a TERMINAL-NATIVE reasoning stream. Default OPEN (grammar, no window box): a command
// executes, a prompt appears, then a <think>…</think> block EXPANDS with streaming reasoning, then the answer —
// the same checkpoint toggling into reasoning mode. `framed` = explicit terminal window. Deterministic.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {rows} from '../runtime/rows';
import {useDNA, TermFrame, termInnerW} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, monoFit, wrapLines} from '../runtime/layout';

export const DURATION = 175;

export const TermThink: React.FC<{cmd?: string; question?: string; think?: string[]; answer?: string; framed?: boolean}> = ({
  cmd = 'hermes --mode hybrid', question = 'solve it', think: think_IN = ['reason…'], answer = 'answer', framed = false} = {}) => {
  const think = rows<string>(think_IN, 'think', 'TermThink');
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

  // THE STACK IS SIZED TO THE ZONE IT IS DRAWN IN. 40px was chosen against a 1920-wide frame and English
  // reasoning lines. TermFrame centres its child in the WHOLE frame, so when Chinese copy wrapped the
  // stack past the zone's height it grew out of both ends and the answer — plus the '=' that introduces
  // it — landed 89px inside the caption band at 1:1.
  //
  // Every length below is declared ONCE and used by both the height model and the style that draws it. A
  // model that restates the JSX's numbers is a second copy of the layout, and the two drift apart on the
  // first edit; this way a change to the padding changes the prediction with it.
  const INNER = termInnerW(W, framed);
  const M = monoFit();
  const LH = 1.5, BASE = 40, TAG = 30;
  const BOX_PADY = 20, BOX_PADX = 28, BOX_MY = 24, TAG_GAP = 14, LINE_MY = 6;
  const TERM_CHROME = 30 + 40;          // TermFrame's own command line and the margin under it
  const measure = Math.max(80, INNER - BOX_PADX * 2);
  const linesAt = (txt: string, px: number, w: number) => wrapLines(String(txt ?? ''), px, w, M);
  const needAt = (k: number) => {
    const f = BASE * k, tg = TAG * k;
    const q = linesAt(question, f, INNER) * f * LH;
    const reasoning = think.reduce((acc, ln) => acc + linesAt(ln, f, measure) * f * LH + LINE_MY * 2 * k, 0);
    const box = BOX_PADY * 2 * k + tg + TAG_GAP * k + reasoning + TAG_GAP * k + tg + 2;
    const a = linesAt(answer, f, INNER) * f * LH;
    return TERM_CHROME * k + q + BOX_MY * 2 * k + box + a;
  };
  // THE ROOM IS MEASURED FROM WHERE THE BLOCK IS ACTUALLY CENTRED. TermFrame centres its child on the
  // FRAME, and the content zone is not centred on the frame — the caption band hangs off the bottom, so the
  // zone's middle sits above H/2. Comparing the stack to the zone's HEIGHT therefore allowed a block that
  // fits the zone and still overhangs it: at 1:1 the zone is 176..823 (centre 499) against a frame centre
  // of 540, and 20px of the answer drew inside the band. What a centred block may use is twice its distance
  // to the NEARER zone edge.
  const ZONE_H = Math.max(120, 2 * Math.min(H / 2 - CONTENT_TOP, contentBottom(W, H) - H / 2));
  // Walk down rather than divide: shrinking the type also re-wraps it, so `need` is not linear in `k` and
  // a single division over-shrinks. Ten steps is finer than the eye, and it stops at the first that fits.
  let k = 1;
  for (let i = 0; i <= 20; i++) { k = 1 - i * 0.04; if (needAt(k) <= ZONE_H) break; }
  k = Math.max(0.36, k);
  const px = (v: number) => Math.round(v * k);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="left">
        <div style={{font: `500 ${px(BASE)}px/${LH} ${mono}`, width: '100%'}}>
          <div style={{color: fg}}><span style={{color: acc}}>❯</span> {question}</div>
          <div style={{margin: `${px(BOX_MY)}px 0`, border: `1px dashed ${acc2}66`, borderRadius: dna?.radius ?? 6,
            background: `${acc2}0e`, padding: `${px(BOX_PADY)}px ${px(BOX_PADX)}px`, opacity: clamp01(seg(t, 0.28, 0.38))}}>
            <div style={{color: acc2, font: `700 ${px(TAG)}px/1 ${mono}`, marginBottom: px(TAG_GAP)}}>&lt;think&gt;</div>
            {think.map((ln, i) => {
              const start = 0.36 + i * (0.46 / Math.max(1, n));
              const show = clamp01(seg(t, start, start + 0.06));
              if (show <= 0) return null;
              return <div key={i} style={{color: dim, opacity: show, transform: `translateX(${(1 - show) * -10}px)`, margin: `${px(LINE_MY)}px 0`}}>
                <span style={{color: acc2, opacity: 0.6}}>│</span> {ln}</div>;
            })}
            <div style={{color: acc2, font: `700 ${px(TAG)}px/1 ${mono}`, marginTop: px(TAG_GAP), opacity: answered ? 1 : 0.3}}>&lt;/think&gt;</div>
          </div>
          <div style={{color: answered ? fg : dim, opacity: clamp01(seg(t, 0.84, 0.92)), fontWeight: 700}}>
            <span style={{color: acc}}>=</span> {answer}
            <span style={{display: 'inline-block', width: px(14), height: px(30), marginLeft: px(12), verticalAlign: 'text-bottom',
              background: acc, opacity: caretOn ? 0.9 : 0.12}} /></div>
        </div>
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermThink;
