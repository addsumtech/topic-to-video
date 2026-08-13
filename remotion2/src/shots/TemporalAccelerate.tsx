// SHOT · Temporal Accelerate — Arc/Raycast language: a long task COMPRESSED. Steps blur past at speed, a
// timer races, then it SNAPS to done. "100% of top product films accelerate complex tasks." LIGHT + a hot
// accent, deliberately unlike the dark Command palette. Deterministic (blur ∝ analytic scroll velocity).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutBack, clamp01} from '../runtime/motion';

export const DURATION = 135; // 4.5s — short + punchy (it's about speed)
const HOT = '#F5820B';
const DEFAULT_STEPS = ['Read the brief', 'Pull the numbers', 'Clean the data', 'Draft the outline', 'Build the charts',
  'Design the slides', 'Write the narrative', 'Add the appendix', 'Proof the copy', 'Format the export',
  'Package the files', 'Deliver to folder'];

export const TemporalAccelerate: React.FC<{items?: string[]}> = ({items: STEPS = DEFAULT_STEPS} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const rowH = 96, listX = 150, listTop = 250, visN = STEPS.length;
  // scroll fraction (eased: slow→FAST→settle); analytic velocity drives the motion blur.
  const sf = easeInOutCubic(clamp01((t - 0.08) / 0.72));
  const vel = Math.sin(Math.PI * clamp01((t - 0.08) / 0.72)); // 0 at ends, 1 at mid
  const blur = t > 0.06 && t < 0.82 ? 26 * vel : 0;
  const travel = sf * (visN - 4) * rowH; // leave the last few settled in view at the end
  const done = t > 0.84;
  const elapsed = (lerp(0, 2.8, sf)).toFixed(1);
  const snap = done ? easeOutBack(seg(t, 0.84, 0.98)) : 0;
  return (
    <AbsoluteFill style={{background: '#f3f4f7'}}>
      {/* speed streaks */}
      {vel > 0.05 && [...Array(9)].map((_, i) => (
        <div key={i} style={{position: 'absolute', left: `${8 + i * 11}%`, top: 0, bottom: 0, width: 2,
          background: `linear-gradient(${HOT}, transparent)`, opacity: 0.12 * vel}} />
      ))}
      {/* the task list, scrolling up fast with velocity blur */}
      <div style={{position: 'absolute', left: listX, top: listTop, width: 980, height: 760, overflow: 'hidden'}}>
        <div style={{transform: `translateY(${-travel}px)`, filter: blur > 0.5 ? `blur(${blur}px)` : undefined}}>
          {STEPS.map((s, i) => {
            const passed = i * rowH < travel + 40;
            return (
              <div key={i} style={{height: rowH, display: 'flex', alignItems: 'center', gap: 26}}>
                <div style={{width: 46, height: 46, borderRadius: 12, background: passed ? '#12b76a' : '#dfe3ea',
                  color: '#fff', font: '700 26px/46px Inter', textAlign: 'center'}}>{passed ? '✓' : ''}</div>
                <div style={{font: '600 44px/1 Inter,system-ui,sans-serif', color: passed ? '#98a2b3' : '#1b2333'}}>{s}</div>
              </div>
            );
          })}
        </div>
      </div>
      {/* the racing timer + counter (right) */}
      <div style={{position: 'absolute', right: 150, top: 300, textAlign: 'right'}}>
        <div style={{font: '800 260px/0.9 Inter,system-ui,sans-serif', color: '#1b2333', letterSpacing: '-0.03em',
          fontVariantNumeric: 'tabular-nums'}}>{done ? '2.8' : elapsed}<span style={{fontSize: 120, color: HOT}}>s</span></div>
        <div style={{font: '700 54px/1 Inter,system-ui,sans-serif', color: done ? '#12b76a' : '#98a2b3', marginTop: 20,
          transform: `scale(${done ? 0.94 + 0.06 * snap : 1})`, transformOrigin: 'right'}}>
          {done ? '12 / 12 · done' : `${Math.min(12, Math.floor(sf * 12 + 0.5))} / 12`}</div>
      </div>
    </AbsoluteFill>
  );
};
export default TemporalAccelerate;
