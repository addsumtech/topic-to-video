// SHOT · Before / After Slider — comparison language: a slider WIPES across, transforming a rough draft into
// the finished deliverable in place. A clean split-reveal (before dull, after vivid). Deterministic wipe.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
// LEVEL-C: the previewed "slide" surfaces + accents follow the DNA → a DARK slide being refined on a dark DNA (the
// before/after contrast is carried by the CONTENT colours — dull greys vs vivid accent — so it survives the flip).
const ACCENT = '#2E7BFF';

const Slide: React.FC<{finished: boolean; heading?: string; metric?: string; sub?: string}> = ({
  finished, heading = 'Q3 Performance', metric = '+18%', sub = 'vs Q2'}) => {
  const dna = useDNA();                       // module-scope subcomponent reads the DNA itself
  const ACC = dna?.accent ?? ACCENT, GOOD = dna?.accent2 ?? '#12b76a', DIM = dna?.dim ?? '#c3c8d2';
  const SURF = dna?.surface ?? '#ffffff', BEFOREBG = dna?.surface ?? '#f1f2f5', DULLBAR = dna?.dim ?? '#d4d8e0', SUB = dna?.dim ?? '#9aa3b2';
  const bars = [0.5, 0.82, 0.4, 0.95, 0.66];
  const title = finished ? ACC : DIM;
  const barC = (i: number) => finished ? (i === 3 ? GOOD : ACC) : DULLBAR;
  return (
    <div style={{position: 'absolute', inset: 0, background: finished ? SURF : BEFOREBG, padding: 120}}>
      <div style={{font: `800 ${finished ? 96 : 92}px/1 var(--f-display, Inter,system-ui,sans-serif)`, color: title}}>{heading}</div>
      <div style={{height: 8, width: finished ? 260 : 200, background: finished ? ACC : DULLBAR, borderRadius: 4, marginTop: 30}} />
      <svg width="1000" height="420" style={{marginTop: 70}}>
        {bars.map((h, i) => <rect key={i} x={20 + i * 180} y={380 - 340 * h} width={130} height={340 * h} rx={10} fill={barC(i)} />)}
      </svg>
      <div style={{display: 'flex', gap: 40, marginTop: 30}}>
        <div><div style={{font: '800 84px/1 var(--f-body, Inter)', color: finished ? GOOD : DIM}}>{metric}</div>
          <div style={{font: '600 34px/1 var(--f-body, Inter)', color: SUB, marginTop: 12}}>{sub}</div></div>
      </div>
    </div>
  );
};

export const BeforeAfterSlider: React.FC<{heading?: string; metric?: string; sub?: string; beforeLabel?: string; afterLabel?: string}> = ({
  heading = 'Q3 Performance', metric = '+18%', sub = 'vs Q2', beforeLabel = 'Rough draft', afterLabel = 'Board-ready'} = {}) => {
  const dna = useDNA();
  const ACC = dna?.accent ?? ACCENT, BG = dna?.bg ?? '#e7e9ef', HANDLE = dna?.fg ?? '#fff', ON = dna?.onAccent ?? '#fff', CHIP = dna?.surface ?? 'rgba(30,35,55,.5)';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const CW = 1500, CH = 900, X = (W - CW) / 2, Y = (H - CH) / 2 + 20;
  const s = lerp(0.14, 0.86, easeInOutCubic(seg(t, 0.12, 0.9))); // slider fraction
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: X, top: Y, width: CW, height: CH, borderRadius: 20, overflow: 'hidden', boxShadow: '0 40px 100px rgba(40,45,80,.2)'}}>
        {/* BEFORE (behind) */}
        <Slide finished={false} heading={heading} metric={metric} sub={sub} />
        {/* AFTER (front), revealed from the left up to the slider */}
        <div style={{position: 'absolute', inset: 0, clipPath: `inset(0 ${(1 - s) * 100}% 0 0)`}}>
          <Slide finished={true} heading={heading} metric={metric} sub={sub} />
        </div>
        {/* slider handle */}
        <div style={{position: 'absolute', left: `${s * 100}%`, top: 0, bottom: 0, width: 4, background: HANDLE, boxShadow: '0 0 20px rgba(0,0,0,.25)'}}>
          <div style={{position: 'absolute', left: -32, top: '50%', width: 64, height: 64, marginTop: -32, borderRadius: 32, background: HANDLE, boxShadow: '0 6px 20px rgba(0,0,0,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: ACC, font: '700 30px/1 var(--f-body, Inter)'}}>⟺</div>
        </div>
        <div style={{position: 'absolute', left: 40, bottom: 40, padding: '12px 26px', borderRadius: 10, background: CHIP, color: HANDLE, font: '700 30px/1 var(--f-body, Inter)'}}>{beforeLabel}</div>
        <div style={{position: 'absolute', right: 40, bottom: 40, padding: '12px 26px', borderRadius: 10, background: ACC, color: ON, font: '700 30px/1 var(--f-body, Inter)'}}>{afterLabel}</div>
      </div>
    </AbsoluteFill>
  );
};
export default BeforeAfterSlider;
