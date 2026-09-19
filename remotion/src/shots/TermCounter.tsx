// SHOT · TermCounter — a TERMINAL-NATIVE key figure. Default OPEN (grammar, no window box): a command executes
// and ONE huge mono number counts up on the open canvas, unit + note below. `framed` = explicit terminal window.
// Deterministic (count = fn of t; lands ~35% then holds — the delivery keyframe is the mid-scene frame).
//
// THE NUMBER IS THE FILM'S STRING. The counter used to run `parseFloat(value.replace(/[^\d.]/g, ''))` and print
// the result through `toLocaleString`: "−12" landed as 12 (the claim's sign flipped), "3–5" as 35, "2019-2024"
// as 20,192,024, "N/A" as 0, and anything >= 1000 was rounded to an integer. The film said none of those.
// Now the settled frame is `figureText(value)` exactly, and the count-up is runtime/figure.ts `figureAt`, which
// animates only a string that is exactly one number — keeping its sign, decimals, grouping, prefix and suffix —
// and shows a range, a span or a word verbatim from the first frame, since there is nothing to count up to.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, TermFrame} from '../runtime/dna';
import {Figure} from '../runtime/atoms';
import {parseFigure, figureAt, figureText} from '../runtime/figure';
import {textWidthPx, monoFit} from '../runtime/layout';

export const DURATION = 150;

export const TermCounter: React.FC<{cmd?: string; value?: string; unit?: string; note?: string; framed?: boolean}> = ({
  cmd = 'stat --value', value = '100', unit = '', note = '', framed = false} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const mono = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const dim = dna?.dim ?? '#5f6b80', acc = dna?.accent ?? '#3dd6a4';
  const fig = parseFigure(value);
  if (!fig.text) {
    throw new Error('TermCounter needs a `value` — the one figure is the whole readout. Pass the sourced figure ' +
      'as a string, exactly as it should read ("19%", "−12", "2019–2024").');
  }
  // Landed at t=0.70; the delivery gate captures the MID-scene frame, so a sourced 19% was delivered
  // reading 18%. The count-up is the register's character — it just has to finish before anyone looks.
  const g = easeOutCubic(clamp01(seg(t, 0.12, 0.35)));
  const shown = figureAt(fig, g);                 // the film's own string from g = 1 on
  // SIZED TO THE FILM'S STRING. A fixed 220px was only ever tried on short integers; now that a value is
  // printed as written ("2019–2024", "¥1,234,567", "3–5 天"), a mono figure that long ran off a portrait
  // frame. Fit the SETTLED string plus its unit to TermFrame's open column (min(84vw, 1320px)) — never larger
  // than before, so a film that fitted is unchanged; the count-up strings are never longer than the settled one.
  const colW = Math.min(0.84 * W, 1320) * 0.96;
  const perPx = textWidthPx(figureText(value), 1, monoFit()) + (unit ? textWidthPx(unit, 56 / 220, monoFit()) : 0);
  const figPx = Math.max(56, Math.min(220, Math.floor((colW - (unit ? 20 : 0)) / Math.max(0.1, perPx))));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% -8%, #0f1723, #06080d 72%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <TermFrame dna={dna} cmd={cmd} t={t} framed={framed} align="center">
        <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'center'}}>
          <span style={{textShadow: `0 0 60px ${acc}44`, fontVariantNumeric: 'tabular-nums'}}>
            <Figure value={shown} unit={unit} ink={acc} tone={dim} size={figPx} unitScale={56 / 220}
              gap={20} fallbackForm="mono" fallbackFamily={mono} />
          </span>
        </div>
        {note ? <div style={{marginTop: 34, color: dim, font: `500 34px/1.4 ${mono}`, textAlign: 'center'}}># {note}</div> : null}
      </TermFrame>
    </AbsoluteFill>
  );
};
export default TermCounter;
