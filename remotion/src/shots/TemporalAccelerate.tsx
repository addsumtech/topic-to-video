// SHOT · Temporal Accelerate — Arc/Raycast language: a long task COMPRESSED. Steps blur past at speed, a
// timer races, then it SNAPS to done. "100% of top product films accelerate complex tasks." LIGHT + a hot
// accent, deliberately unlike the dark Command palette. Deterministic (blur ∝ analytic scroll velocity).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

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
export const TemporalAccelerate: React.FC<{items?: string[]; seconds?: number | null}> = ({
  items: STEPS = DEFAULT_STEPS, seconds = null} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? '#f3f4f7', ACC = dna?.accent ?? HOT, GOOD = dna?.accent2 ?? '#12b76a', FG = dna?.fg ?? '#1b2333';
  const DIM = dna?.dim ?? '#98a2b3', LINE = dna?.line ?? '#dfe3ea', ON = dna?.onAccent ?? '#fff';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const rowH = 96, listX = 150, listTop = 250, visN = STEPS.length;
  // scroll fraction (eased: slow→FAST→settle); analytic velocity drives the motion blur.
  const sf = easeInOutCubic(clamp01((t - 0.08) / 0.72));
  const vel = Math.sin(Math.PI * clamp01((t - 0.08) / 0.72)); // 0 at ends, 1 at mid
  const blur = t > 0.06 && t < 0.82 ? 26 * vel : 0;
  const travel = sf * (visN - 4) * rowH; // leave the last few settled in view at the end
  const done = t > 0.84;
  const elapsed = seconds == null ? null : (lerp(0, seconds, sf)).toFixed(1);
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
            const passed = i * rowH < travel + 40;
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
            fontVariantNumeric: 'tabular-nums'}}>{done ? (seconds as number).toFixed(1) : elapsed}<span style={{fontSize: 120, color: ACC}}>s</span></div>
        )}
        <div style={{font: '700 54px/1 var(--f-body, Inter,system-ui,sans-serif)', color: done ? GOOD : DIM, marginTop: 20,
          transform: `scale(${done ? 0.94 + 0.06 * snap : 1})`, transformOrigin: 'right'}}>
          {/* counts the list it is actually showing. It counted a hardcoded 12 either way, so a film with
              five steps watched a counter run to twelve. */}
          {done ? `${visN} / ${visN} · done` : `${Math.min(visN, Math.floor(sf * visN + 0.5))} / ${visN}`}</div>
      </div>
    </AbsoluteFill>
  );
};
export default TemporalAccelerate;
