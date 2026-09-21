// MRIPipeline — the recap as the ACTUAL pipeline, not four generic cards. Four stages flow left→right, each a
// tiny true representation — a decaying signal, gradient encoding, a k-space lattice — culminating in the REAL
// reconstructed MRI. It literally re-shows "signal → encoding → k-space → image: always computed." Deterministic.
//
// THE CHAIN IS THE FILM'S; THE FOUR BOXES KEEP THEIR NIGHT. The headline, all four stage names and the three
// arrows between them were literals picked for a near-black ground, and all eight DNA presets are near-black,
// so on a film whose DNA came from a warm-white deck the whole chain went light-on-light: the four boxes sat
// on paper with no names under them and nothing joining them (`scripts/ink_contrast_qa.py`: 33.0% of this
// register's marks under 3:1, largest connected hole 0.52% of the frame — the median stayed at 16.67:1
// because the boxes themselves are most of the ink and they never moved). An arrow is a claim as much as a
// word is: it is the "→" in "signal → encoding → k-space → image". All of it reads from the DNA now. The
// BOXES are not ink: they hold a signal trace, a gradient encode, a k-space lattice and — in the last one —
// a real reconstructed MR slice, and a scan viewport is black in every reader that has ever shown one. They
// keep their own night, and the art drawn inside them is lifted to read against it rather than against paper.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01, seg} from '../runtime/motion';
import {useDNA, tint} from '../runtime/dna';
import {ACCENT_CONTRAST_MIN, readsOn} from '../runtime/light';

export const DURATION = 180; // 6s

// The literals this register was authored in, hoisted so an un-themed render is byte-for-byte what it was.
const ACCENT_D0 = '#22d3ee', ACCENT2_D0 = '#a78bfa';
const TITLE_D0 = '#dfe8f5';      // the headline
const STAGE_D0 = '#c9d6ea';      // the four stage names
const TRACE_D0 = '#eaf6ff';      // the decaying signal INSIDE box one
const BOX = '#0a1424';           // a stage's viewport — see the header

export const MRIPipeline: React.FC<{src?: string; accent?: string; accent2?: string; label?: string} > = ({
  src, accent: ACC, accent2: ACC2, label = 'Always computed',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // The film's accents when it has them: `groundFrom` has already exposed both for whatever ground the beat
  // is lit on, so the arrows and the last box's outline read there without this register measuring anything.
  const accent = ACC ?? dna?.accent ?? ACCENT_D0;
  const accent2 = ACC2 ?? dna?.accent2 ?? ACCENT2_D0;
  const ink = dna?.fg ?? TITLE_D0;         // the headline
  const stageInk = dna?.fg ?? STAGE_D0;    // the four stage names — the chain the frame asserts
  // ART INSIDE A BOX ANSWERS TO THE BOX, NOT TO THE PAGE. A light film's accent is chosen to read on paper,
  // and on the box's night that is the same disappearance one layer in — so the gradient lines and the
  // k-space dots are lifted until they clear the non-text floor against the box. With no DNA both literals
  // are far clear of it and pass through unchanged. (Same lift as KSpaceAnatomy's rings in its k-space panel.)
  // A LADDER, NOT ONE FIXED STEP. `tint(c, 0.6)` cleared 3:1 by landing at 8.45:1 and washing a dark
  // accent's saturation out on the way; the shared ladder stops at the first rung that reads.
  const inBox = (c: string) => readsOn(c, BOX, ACCENT_CONTRAST_MIN);
  const names = ['signal', 'encoding', 'k-space', 'image'];
  const n = names.length, box = Math.min(W * 0.17, H * 0.34), gap = (W - n * box) / (n + 1);
  const cy = H * 0.5 - 8;
  const on = (i: number) => clamp01(seg(t, 0.1 + i * 0.14, 0.35 + i * 0.14));

  const stageArt = (i: number, x: number, p: number) => {
    const s = box, cx = x + s / 2, mid = cy;
    if (i === 0) { // decaying signal
      const pts: string[] = [];
      for (let k = 0; k <= s - 20; k += 3) pts.push(`${x + 10 + k},${mid + Math.sin(k / 5) * (s * 0.3) * Math.exp(-k / (s * 0.9)) * p}`);
      // the trace is drawn ON the box's night, so it keeps the literal it was measured for: the film's ink
      // on a light film is near-black, which inside this box would be a black line on a black square.
      return <polyline points={pts.join(' ')} fill="none" stroke={TRACE_D0} strokeWidth={2.4} />;
    }
    // @positional: the four stages ARE the register's fixed mechanism (signal, encoding, k-space, image); stage 2 is always the gradient
    if (i === 1) { // gradient ramp grid
      const g: React.ReactNode[] = [];
      for (let c = 0; c < 6; c++) g.push(<line key={c} x1={x + 12 + c * (s - 24) / 5} y1={mid - s * 0.32} x2={x + 12 + c * (s - 24) / 5} y2={mid + s * 0.32} stroke={inBox(accent)} strokeWidth={1.3} opacity={(0.3 + c * 0.13) * p} />);
      return <g>{g}</g>;
    }
    // @positional: the four stages ARE the register's fixed mechanism (signal, encoding, k-space, image); stage 3 is always k-space
    if (i === 2) { // k-space dots
      const d: React.ReactNode[] = [];
      for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) {
        const dx = (c - 2.5) / 2.5, dy = (r - 2.5) / 2.5, dd = Math.hypot(dx, dy);
        d.push(<circle key={`${r}-${c}`} cx={cx + dx * s * 0.34} cy={mid + dy * s * 0.34} r={1 + (1 - dd) * 2.4} fill={inBox((r + c) % 4 === 0 ? accent2 : accent)} opacity={(0.15 + (1 - dd) * 0.7) * p} />);
      }
      return <g>{d}</g>;
    }
    return null; // image handled as <Img> below
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {names.map((nm, i) => {
          const x = gap + i * (box + gap), p = on(i);
          return <g key={nm}>
            <rect x={x} y={cy - box / 2} width={box} height={box} rx={10} fill={BOX} stroke={i === n - 1 ? accent : `${accent}66`} strokeWidth={1.6} opacity={0.35 + p * 0.65} />
            {i < n - 1 ? stageArt(i, x, p) : null}
            <text x={x + box / 2} y={cy + box / 2 + 34} textAnchor="middle" fill={stageInk} fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700} opacity={p}>{nm}</text>
            {i < n - 1 ? <text x={x + box + gap / 2} y={cy + 8} textAnchor="middle" fill={accent} fontSize="34" opacity={on(i + 1)}>→</text> : null}
          </g>;
        })}
      </svg>
      {/* the final stage = the REAL reconstructed MRI */}
      {src ? <div style={{position: 'absolute', left: gap + (n - 1) * (box + gap) + 5, top: cy - box / 2 + 5,
        width: box - 10, height: box - 10, borderRadius: 8, overflow: 'hidden', opacity: on(n - 1)}}>
        <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /></div> : null}
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default MRIPipeline;
