// OpenQuestions — unresolved questions surfaced one by one under a descending scan-light, then left standing
// together (no arrows, no sequence — they are PARALLEL open questions, not steps). The dramatic-interrogation
// vibe of a spotlight, but a layout that fits long questions and encodes "these are all still open." A blinking
// caret at the end says: unanswered. Prop-driven (kicker + questions) → generalises. Deterministic (fn of t).
//
// EVERY OPEN QUESTION IS ASKED, OR THE REGISTER SAYS IT CANNOT ASK THEM ALL. It used to take
// `questions.slice(0, 4)`: a film with five open questions showed four and the footer then said "still
// unresolved" over a list that was quietly one short. Four is the clock's limit: question i lights over
// 0.12 + 0.2i -> 0.30 + 0.2i as the scan passes it, so the fourth is lit by 0.90, just as the footer lands; a
// fifth would start lighting at 0.92 and never finish. Past four it THROWS naming the limit; no questions, or
// an empty one, throws too — a scan light passing over nothing is not a question left open.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {captionBand, contentBottom, inkBlockH, wrapLines} from '../runtime/layout';

export const DURATION = 170; // ~5.7s

export const MAX_OPEN_QUESTIONS = 4;

export const OpenQuestions: React.FC<{kicker?: string; questions?: string[]; accent?: string; footer?: string}> = ({
  kicker = 'The open questions', questions = ['How fast is too fast?', 'Is it safe?', 'Who gets a say?'],
  accent = '#10a37f', footer = 'still unresolved',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // The film's own inks, each with the ORIGINAL literal it replaced as its null-DNA fallback — the kicker and
  // the unlit question were two different greys, and collapsing them to one changed the un-themed look (the
  // null-DNA colour test caught exactly that: `#8f9bb0` had become unreachable).
  const FG = dna?.fg ?? '#eef4fc';
  const DIM = dna?.dim ?? '#464e5c';          // the unlit end of a question
  const KICKER = dna?.dim ?? '#8f9bb0';       // the spaced label above them
  // Every question once — the header says why four is the ceiling.
  if (!Array.isArray(questions) || questions.length < 1 || questions.length > MAX_OPEN_QUESTIONS) {
    throw new Error(
      `OpenQuestions asks 1-${MAX_OPEN_QUESTIONS} questions (got ${Array.isArray(questions) ? questions.length : typeof questions}). ` +
      `Each lights as the scan passes it and the fourth is lit just as the footer lands; a fifth would never ` +
      `finish lighting. Keep the ${MAX_OPEN_QUESTIONS} that matter, or split them across two beats.`);
  }
  const qs = questions.map((q, i) => {
    const text = String(q ?? '').trim();
    if (!text) throw new Error(`OpenQuestions: question ${i + 1} is empty.`);
    return text;
  });
  const n = qs.length;
  // THE QUESTIONS ARE CENTRED ON THEIR OWN LINE, so a question that wraps grows BOTH ways and the last one
  // reaches into the caption band — 67px of it at 1:1, where a Chinese question runs to two lines in a
  // measure that held one in English. The stack is placed from the deepest question it actually has: the
  // rows keep their rhythm and the whole block rises, rather than the last row being nudged off its own
  // spacing. `lines` is 1 for Latin demo copy, so nothing that ships today moves.
  const QPX = 62, QMEASURE = W * 0.86;
  const qLines = Math.max(1, ...qs.map((q) => wrapLines(q, QPX, QMEASURE)));
  const qHalf = (qLines * QPX * 1.1) / 2 + (inkBlockH(QPX) - QPX);   // half the block, plus the ink that hangs below
  // ...AND THE FOOTER IS PART OF THE STACK. The footer is clamped above the caption band, and the stack used
  // to be placed as if the footer were not there: at four questions on a 16:9 frame the last question sat
  // centred at y=799 and the footer was clamped to 818, so 「仍待回答」 printed across the middle of the last
  // question. The last row now stops a gap above where the footer will be, and if the rows cannot keep their
  // rhythm between the kicker and that line, the rhythm tightens (never below the rows' own height) rather
  // than the stack climbing into the kicker. Three one-line questions — the demo — are placed exactly as before.
  const FOOT_TOP = H - captionBand(W, H) - 34;                 // where the footer is clamped (see below)
  const yLastMax = Math.min(contentBottom(W, H) - qHalf, FOOT_TOP - Math.round(H * 0.015) - qHalf);
  const yFirstMin = 92 + 26 + Math.round(H * 0.03) + qHalf;    // under the kicker (top 92, 26px)
  const minStep = qLines * QPX * 1.2;
  let stepY = Math.max(H * 0.15, minStep);
  if (n > 1 && yFirstMin + stepY * (n - 1) > yLastMax) {
    stepY = Math.max(minStep, (yLastMax - yFirstMin) / (n - 1));
  }
  const topY = Math.min(H * 0.34, yLastMax - stepY * Math.max(0, n - 1));
  const scanProg = clamp01(seg(t, 0.1, 0.14 + n * 0.2));           // the light descends past each question
  const scanY = lerp(topY - stepY * 0.5, topY + stepY * (n - 0.5), scanProg);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 30%, #0d1119, #05060a 70%)')}}>
      {/* kicker */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center', opacity: clamp01(t * 5),
        color: KICKER, font: '600 26px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.34em', textTransform: 'uppercase'}}>{kicker}</div>

      {/* the descending scan light */}
      <div style={{position: 'absolute', left: 0, right: 0, top: scanY - 60, height: 120, pointerEvents: 'none',
        background: `radial-gradient(60% 100% at 50% 50%, ${accent}22, transparent 70%)`, opacity: scanProg < 1 ? 1 : 0.0}} />
      <div style={{position: 'absolute', left: '18%', right: '18%', top: scanY, height: 2, pointerEvents: 'none',
        background: `linear-gradient(90deg, transparent, ${accent}, transparent)`, opacity: scanProg < 1 ? 0.9 : 0}} />

      {/* the questions — each lights as the scan passes, then stays lit */}
      {qs.map((q, i) => {
        const yc = topY + stepY * i;
        const lit = clamp01(seg(t, 0.12 + i * 0.2, 0.3 + i * 0.2));
        const glow = clamp01(1 - Math.abs(scanY - yc) / 90) * (scanProg < 1 ? 1 : 0);
        const b = Math.max(lit * 0.86, glow);
        return (
          // THE QUESTION WRAPS IN THE MEASURE THE STACK WAS PLANNED FOR. `qLines` is counted in QMEASURE (86% of
          // the width), but the row itself was the full frame: a long question ran to within 10px of both
          // edges and broke wherever the frame ended, leaving 「眠？」 alone on a line — and the stack's
          // spacing was then planned for a different line count than the one drawn. Padded to the measure and
          // balanced, the drawn wrap is the planned one. Short questions are unchanged.
          <div key={i} style={{position: 'absolute', left: 0, right: 0, top: yc, transform: 'translateY(-50%)', textAlign: 'center',
            padding: `0 ${Math.round((W - QMEASURE) / 2)}px`, boxSizing: 'border-box', textWrap: 'balance'}}>
            {/* THE QUESTION LIGHTS FROM THE FILM'S OWN DIM TO THE FILM'S OWN INK. It used to interpolate
                between two literals — slate rgb(70,78,92) and near-white rgb(238,244,252) — both of which
                assume a dark ground. Measured on a warm-white DNA (scripts/ink_contrast_qa.py), every
                question in this register set at a median 1.24:1: the whole content of the beat, present in
                the DOM, invisible on the frame, with every type gate satisfied because nothing was missing
                or overlapping. */}
            <span style={{color: mix(DIM, FG, b),
              font: '700 62px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em', opacity: clamp01(lit * 1.3),
              textShadow: glow > 0.3 ? `0 0 46px ${accent}${Math.round(glow * 140).toString(16).padStart(2, '0')}` : 'none'}}>
              {q}</span>
          </div>
        );
      })}

      {/* footer: unresolved + a blinking caret (once all questions are up) — clamped ABOVE the caption band */}
      <div style={{position: 'absolute', left: 0, right: 0,
        top: Math.min(topY + stepY * (n - 1) + H * 0.12, FOOT_TOP), textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.78, 0.92)), color: accent, font: '600 24px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.2em'}}>
        {footer}<span style={{opacity: Math.sin(t * Math.PI * 2 * 6) > 0 ? 1 : 0}}> _</span>
      </div>
    </AbsoluteFill>
  );
};
export default OpenQuestions;
