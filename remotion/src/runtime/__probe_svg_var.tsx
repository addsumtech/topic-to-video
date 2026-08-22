// PROBE — does `var(--x, <fallback>)` resolve inside an SVG `fontFamily="..."` JSX presentation
// attribute, in a REAL `npx remotion render` (not just `npx remotion still`)? Task 8's spec assumed
// no (an XML presentation attribute cannot take CSS var()); a later reviewer's `still` probe showed
// yes. Task 9's brief requires re-confirming that on an actual video render before trusting it for
// 62 real declarations across 17 shots.
//
// Row 1: `--probe-face` IS set (scoped via a wrapping <div style>) to JetBrains Mono, fallback
// Playfair Display. Row 2: the SAME attribute, same fallback, but the variable is UNSET (no
// ancestor sets --probe-face) — must resolve to the fallback, Playfair Display.
// If var() does not apply in this attribute position at all, both rows render identically (whatever
// Chromium's default SVG text font is) instead of one monospace + one serif. That is the mechanical,
// screenshot-checkable signal — not an assertion.
import React from 'react';
import {AbsoluteFill} from 'remotion';

export const DURATION = 60; // 2s — long enough to be a real `render`, not a single-frame `still`

const SAMPLE = 'Handgloves 0123';

export const SvgVarProbe: React.FC = () => {
  return (
    <AbsoluteFill style={{background: '#fff'}}>
      <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: '50%',
        // @ts-ignore -- custom property
        '--probe-face': "'JetBrains Mono', monospace"}}>
        <svg width="100%" height="100%">
          <text x="5%" y="50%" fontSize={72} fontWeight={700} fill="#000"
            fontFamily="var(--probe-face, 'Playfair Display', serif)">
            {SAMPLE}
          </text>
        </svg>
      </div>
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: '50%'}}>
        <svg width="100%" height="100%">
          <text x="5%" y="50%" fontSize={72} fontWeight={700} fill="#000"
            fontFamily="var(--probe-face, 'Playfair Display', serif)">
            {SAMPLE}
          </text>
        </svg>
      </div>
    </AbsoluteFill>
  );
};
export default SvgVarProbe;
