// FrequencyEncode — the actual mechanism, not a generic spectrum. A readout gradient makes each COLUMN of the
// slice precess at its OWN frequency (a LINEAR ramp along the axis: left slow → right fast) = position→frequency.
// The coil reads ONE summed signal; a single Fourier transform then SEPARATES that signal back into the columns
// by frequency. Three stages: columns get their pitches → they sum into one readout → an FFT prism splits it back
// to the columns. A radial spectrum burst showed none of this. Deterministic (pure fn of useT).
//
// THE RECOVERED PEAKS ARE AS TALL AS EACH OTHER, BECAUSE THE COLUMNS ARE. Each column's wave is drawn at the
// same amplitude, and the summed readout adds them with equal weight — but the FFT stage drew its peaks at
// `0.6 + 0.4 * Math.sin(i)`, so the transform "recovered" a column at twice the strength of another (the 6th
// peak barely a quarter of the 3rd). A spectrum's peak height is the claim of how much signal sits at that
// frequency, and that claim contradicted the encoding one stage above it. The peaks are equal now; a film
// whose columns carry different signal needs a register that draws per-column amplitudes from its data.
// `cols` is an integer 2-8: one column has nothing to separate, and past eight the fastest column's wave
// drops under 8px a cycle on a 1080-wide frame and stops reading as a wave.
// The two stage labels are centred over the readout, where the summed wave is flattest: left-aligned, they
// sat where the columns' phases line up, and the wave's swing ran through "one Fourier transform"; and the
// first label's baseline sat 11px under the column boxes, so its capitals touched their bottom edge.
//
// THE DATA LAYER IS THE FILM'S; THE SCOPE PANELS KEEP THEIR NIGHT. Every mark that is not inside a column
// box was a literal picked for a near-black ground, and all eight DNA presets are near-black, so on a film
// whose DNA came from a warm-white deck the title, both axis ends, "one measured signal", the summed
// readout curve itself and every bar of the FFT spectrum drew light ink on light paper
// (`scripts/ink_contrast_qa.py`: 42.3% of this register's marks under 3:1, largest connected hole 1.15% of
// the frame). The curve and the bars are claims exactly as much as the words are — the readout IS "one
// measured signal" and a bar IS "this column came back" — so all of it reads from the DNA. The seven COLUMN
// BOXES are not ink: each is a scope showing one column's own oscillation, and a scope viewport is dark in
// every instrument that has ever shown one. They keep their own night, and the traces on them are lifted to
// read against it rather than against the paper.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, radians} from '../runtime/motion';
import {useDNA, mix, tint, contrastOf} from '../runtime/dna';
import {ACCENT_CONTRAST_MIN} from '../runtime/light';

export const DURATION = 180; // 6s
export const MAX_FREQ_COLS = 8;

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'low freq',
  'high freq · readout gradient',
  'one measured signal',
  'one Fourier transform → columns',
];

// The literals this register was authored in, hoisted so an un-themed render is byte-for-byte what it was.
const ACCENT_D0 = '#22d3ee', ACCENT2_D0 = '#a78bfa';
const TITLE_D0 = '#dfe8f5';       // the title
const AXIS_D0 = '#8aa';           // 'low freq' / 'high freq · readout gradient'
const STAGE_D0 = '#c9d6ea';       // 'one measured signal'
const SUM_D0 = '#eaf6ff';         // the summed readout curve
const PANEL = '#0a1424';          // a column's scope viewport — see the header

export const FrequencyEncode: React.FC<{accent?: string; accent2?: string; label?: string; cols?: number}> = ({
  accent: ACC, accent2: ACC2, label = 'Position becomes frequency', cols = 7,
} = {}) => {
  const {width: W, height: H, durationInFrames, fps} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // The film's accents when it has them: `groundFrom` has already exposed both for whatever ground the beat
  // is lit on, so the spectrum bars and the transform label read there without this register measuring.
  const accent = ACC ?? dna?.accent ?? ACCENT_D0;
  const accent2 = ACC2 ?? dna?.accent2 ?? ACCENT2_D0;
  const ink = dna?.fg ?? TITLE_D0;                        // the title
  const sumInk = dna?.fg ?? SUM_D0;                       // the summed readout — the beat's own measurement
  const stageInk = dna ? mix(dna.fg, dna.dim, 0.4) : STAGE_D0;   // the annotation naming that measurement
  const axisInk = dna?.dim ?? AXIS_D0;                    // the two ends of the gradient: metadata
  // A TRACE INSIDE A SCOPE ANSWERS TO THE SCOPE, NOT TO THE PAGE. A light film's accent is chosen to read on
  // paper, and on the panel's night that is the same disappearance one layer in — so a trace that does not
  // clear the non-text floor against the panel is lifted until it does. With no DNA both literals are far
  // clear of it and pass through unchanged. (Same lift as KSpaceAnatomy's rings inside its k-space panel.)
  const onPanel = (c: string) => (contrastOf(c, PANEL) >= ACCENT_CONTRAST_MIN ? c : tint(c, 0.6));
  if (!Number.isInteger(cols) || cols < 2 || cols > MAX_FREQ_COLS) {
    throw new Error(`FrequencyEncode: \`cols\` must be an integer 2-${MAX_FREQ_COLS} (got ${JSON.stringify(cols)}). One column ` +
      `has nothing for the transform to separate, and past ${MAX_FREQ_COLS} the fastest column's wave is under 8px a ` +
      'cycle on a 1080-wide frame. The columns stand for positions, so a representative few say the same thing.');
  }
  const gx = W * 0.14, gw = W * 0.72, colW = gw / cols;
  const rowY = H * 0.3, rowH = H * 0.2;
  const sumY = H * 0.62, specY = H * 0.82;

  const p1 = clamp01(seg(t, 0.06, 0.34));   // columns get their pitches
  const p2 = clamp01(seg(t, 0.36, 0.56));   // they sum into one readout signal
  const p3 = clamp01(seg(t, 0.58, 0.9));    // FFT separates them back into columns

  const freqOf = (i: number) => 1.2 + i * 1.1;              // linear frequency ramp across the columns

  // per-column mini-waves (position → its own frequency)
  const colWaves: React.ReactNode[] = [];
  for (let i = 0; i < cols; i++) {
    const cx0 = gx + i * colW, f = freqOf(i);
    const pts: string[] = [];
    // sampled every pixel: at 2px the fastest columns aliased into peaks of visibly different heights, which
    // reads as different amplitudes — the very claim the equal peaks below exist not to make
    for (let x = 6; x <= colW - 6; x += 1) {
      const u = (x - 6) / (colW - 12);
      // THE TEMPORAL PHASE, in seconds. Authored as `t * 6` — which reads like radians per second and is
      // not: `t` runs 0→1 across the whole clip, so the readout waveform advanced 0.95 of one cycle in five
      // seconds and a frequency encode that never completes an oscillation is not encoding a frequency.
      // Measured before and after on the settled half: 0.00097 -> 0.00119 frame difference, +23%.
      pts.push(`${(cx0 + x).toFixed(1)},${(rowY + rowH / 2 - Math.sin(u * f * Math.PI * 2 + radians(t, durationInFrames, fps, 4)) * rowH * 0.34 * p1).toFixed(1)}`);
    }
    colWaves.push(<g key={i}>
      <rect x={cx0 + 2} y={rowY} width={colW - 4} height={rowH} rx={5} fill={PANEL} stroke={`${accent}55`} strokeWidth={1} opacity={0.5 + p1 * 0.5} />
      <polyline points={pts.join(' ')} fill="none" stroke={onPanel(i % 2 ? accent2 : accent)} strokeWidth={2} />
    </g>);
  }

  // the summed readout signal (one complex waveform = sum of the column frequencies)
  const sum: string[] = [];
  for (let x = 0; x <= gw; x += 2) {
    let y = 0;
    for (let i = 0; i < cols; i++) y += Math.sin((x / gw) * freqOf(i) * Math.PI * 2 + radians(t, durationInFrames, fps, 4));
    sum.push(`${(gx + x).toFixed(1)},${(sumY - (y / cols) * H * 0.10 * p2).toFixed(1)}`);
  }

  // FFT spectrum: a peak per column, positioned by its frequency (→ recovers its column/position)
  const peaks: React.ReactNode[] = [];
  for (let i = 0; i < cols; i++) {
    const px = gx + (i + 0.5) * colW;
    const hgt = lerp(0, H * 0.11, p3);                     // equal: every column was encoded at the same amplitude
    peaks.push(<g key={i}>
      <line x1={px} y1={specY} x2={px} y2={specY - H * 0.11} stroke={`${accent}33`} strokeWidth={1} />
      <line x1={px} y1={specY} x2={px} y2={specY - hgt} stroke={i % 2 ? accent2 : accent} strokeWidth={5} />
      {p3 > 0.5 && <line x1={px} y1={rowY + rowH} x2={px} y2={specY - hgt} stroke={`${accent}22`} strokeWidth={1} strokeDasharray="2 5" />}
    </g>);
  }

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* gradient ramp arrow above the row: position → frequency */}
        <line x1={gx} y1={rowY - 26} x2={gx + gw} y2={rowY - 26} stroke={accent} strokeWidth={2} opacity={0.5 * p1} markerEnd="url(#fah)" />
        <defs><marker id="fah" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill={accent} /></marker></defs>
        <text x={gx} y={rowY - 34} fill={axisInk} fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={p1}>low freq</text>
        <text x={gx + gw} y={rowY - 34} textAnchor="end" fill={axisInk} fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={p1}>high freq · readout gradient</text>
        {colWaves}
        {/* summed readout — drawn on the film's GROUND, not in a scope, so it is the film's ink */}
        <polyline points={sum.join(' ')} fill="none" stroke={sumInk} strokeWidth={2.4} opacity={p2} />
        <text x={gx + gw / 2} y={rowY + rowH + 32} textAnchor="middle" fill={stageInk} fontSize="18" fontFamily="var(--f-body, Inter, sans-serif)" opacity={p2}>one measured signal</text>
        {/* FFT separates it back into columns */}
        <text x={gx + gw / 2} y={specY - H * 0.13} textAnchor="middle" fill={accent} fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t,0.56,0.66))}>one Fourier transform → columns</text>
        {peaks}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default FrequencyEncode;
