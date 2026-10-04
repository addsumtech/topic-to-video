// SHOT · Temporal Accelerate — Arc/Raycast language: a long task COMPRESSED. Steps blur past at speed, a
// timer races, then it SNAPS to done. "100% of top product films accelerate complex tasks." LIGHT + a hot
// accent, deliberately unlike the dark Command palette. Deterministic (blur ∝ analytic scroll velocity).
//
// THE WORD AND THE TICKS AGREE WITH EACH OTHER, AND THE WORD IS THE FILM'S. The finished counter read
// `N / N · done` with "done" written into the JSX, so a Chinese film's list snapped to an English word no
// prop could reach. It is `doneLabel` now (default 'done', listed by the demo-copy gate when omitted; ''
// leaves the bare `N / N`). And the counter said every step was done while the list said otherwise: a row
// ticked only once the scroll had carried it past a line, and the last rows settle in view without ever
// crossing it — the demo ended on "12 / 12 · done" above three unticked steps; a list of four never scrolled,
// ticked one step and claimed four; a shorter one ticked none. When the timer snaps to done, every row is
// done. A list shorter than four also no longer scrolls DOWN (the travel went negative), and an empty list
// throws instead of counting "0 / 0 · done".

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, easeInOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {figureAt, figureText, parseFigure} from '../runtime/figure';
import {useGlide} from '../runtime/glide';

export const DURATION = 135; // 4.5s — short + punchy (it's about speed)
// LEVEL-C: the whole light Arc/Raycast UI flips with the DNA (bg/ink/accent/success), coherent-dark on a dark DNA,
// original light on null DNA.
const HOT = '#F5820B';
const DEFAULT_STEPS = ['Read the brief', 'Pull the numbers', 'Clean the data', 'Draft the outline', 'Build the charts',
  'Design the slides', 'Write the narrative', 'Add the appendix', 'Proof the copy', 'Format the export',
  'Package the files', 'Deliver to folder'];

// `seconds` is the elapsed time the FILM measured. No default: the timer used to race 0.0 -> 2.8 off the
// clock and land on a hardcoded '2.8s', so every film that reached for this register reported the same
// invented duration. The race still runs — the NUMERAL only appears when there is a real figure for it.
// CJK-EXEMPT (tight leading, no floor): the tight-leading element renders a NUMERAL (elapsed / seconds), never author copy.
export const TemporalAccelerate: React.FC<{items?: string[]; seconds?: number | null; doneLabel?: string}> = ({
  items: STEPS = DEFAULT_STEPS, seconds = null, doneLabel = 'done'} = {}) => {
  if (!Array.isArray(STEPS) || STEPS.length < 1) {
    throw new Error('TemporalAccelerate needs at least one step in `items` — it counts the list it shows, and an ' +
      'empty list would snap to "0 / 0" done.');
  }
  const dna = useDNA();
  const BG = dna?.bg ?? '#f3f4f7', ACC = dna?.accent ?? HOT, GOOD = dna?.accent2 ?? '#12b76a', FG = dna?.fg ?? '#1b2333';
  const DIM = dna?.dim ?? '#98a2b3', LINE = dna?.line ?? '#dfe3ea', ON = dna?.onAccent ?? '#fff';
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const rowH = 96, listX = 150, listTop = 250, visN = STEPS.length;
  // scroll fraction (eased: slow→FAST→settle); analytic velocity drives the motion blur.
  const sf = easeInOutCubic(clamp01((t - 0.08) / 0.72));
  const vel = Math.sin(Math.PI * clamp01((t - 0.08) / 0.72)); // 0 at ends, 1 at mid
  const blur = t > 0.06 && t < 0.82 ? 26 * vel : 0;
  const travel = sf * Math.max(0, visN - 4) * rowH; // leave the last few settled in view at the end
  const done = t > 0.84;
  // THE FILM'S FIGURE, AS WRITTEN. The settled timer printed `seconds.toFixed(1)`, which rounds a film's 3.25
  // to "3.3" and dresses a measured 12 as "12.0" — a precision nobody supplied. runtime/figure prints the film's
  // number exactly on the settled frame and races up to it with the decimals the film used.
  if (seconds != null && !(typeof seconds === 'number' && Number.isFinite(seconds) && seconds >= 0)) {
    throw new Error(`TemporalAccelerate: \`seconds\` is the elapsed time the film measured and must be a finite number >= 0, ` +
      `got ${JSON.stringify(seconds)}. Omit it to show no timer.`);
  }
  const secFig = seconds == null ? null : parseFigure(String(seconds));
  const elapsed = secFig == null ? null : figureAt(secFig, sf);
  const snap = done ? easeOutBack(seg(t, 0.84, 0.98)) : 0;
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* speed streaks */}
      {vel > 0.05 && [...Array(9)].map((_, i) => (
        <div key={i} style={{position: 'absolute', left: `${8 + i * 11}%`, top: 0, bottom: 0, width: 2,
          background: `linear-gradient(${ACC}, transparent)`, opacity: 0.12 * vel}} />
      ))}
      {/* the task list, scrolling up fast with velocity blur */}
      <div style={{position: 'absolute', left: listX, top: listTop, width: 980, height: 760, overflow: 'hidden'}}>
        <div style={{transform: `translateY(${-travel}px)`, filter: blur > 0.5 ? `blur(${blur}px)` : undefined}}>
          {STEPS.map((s, i) => {
            // ticked once scrolled past — and ALL of them once the timer snaps, which is what the counter says
            const passed = done || i * rowH < travel + 40;
            return (
              <div key={i} style={{height: rowH, display: 'flex', alignItems: 'center', gap: 26}}>
                <div style={{width: 46, height: 46, borderRadius: 12, background: passed ? GOOD : LINE,
                  color: ON, font: '700 26px/46px var(--f-body, Inter)', textAlign: 'center'}}>{passed ? '✓' : ''}</div>
                <div style={{font: '600 44px/1 var(--f-body, Inter,system-ui,sans-serif)', color: passed ? DIM : FG}}>{s}</div>
              </div>
            );
          })}
        </div>
      </div>
      {/* the racing timer + counter (right) */}
      <div style={{position: 'absolute', right: 150, top: 300, textAlign: 'right'}}>
        {elapsed == null ? null : (
          <div style={{font: '800 260px/0.9 var(--f-body, Inter,system-ui,sans-serif)', color: FG, letterSpacing: '-0.03em',
            fontVariantNumeric: 'tabular-nums'}}>{done ? figureText(seconds) : elapsed}<span style={{fontSize: 120, color: ACC}}>s</span></div>
        )}
        <div style={{font: '700 54px/1 var(--f-body, Inter,system-ui,sans-serif)', color: done ? GOOD : DIM, marginTop: 20,
          transform: glide(`scale(${done ? 0.94 + 0.06 * snap : 1})`, done && snap !== 1), transformOrigin: 'right'}}>
          {/* counts the list it is actually showing. It counted a hardcoded 12 either way, so a film with
              five steps watched a counter run to twelve. */}
          {done ? `${visN} / ${visN}${doneLabel ? ` · ${doneLabel}` : ''}` : `${Math.min(visN, Math.floor(sf * visN + 0.5))} / ${visN}`}</div>
      </div>
    </AbsoluteFill>
  );
};
export default TemporalAccelerate;
