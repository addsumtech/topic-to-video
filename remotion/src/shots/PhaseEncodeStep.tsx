// PhaseEncodeStep — phase encoding, encoded literally: a phase-encode GRADIENT BLIP steps through its amplitudes
// (−Gmax → +Gmax), and each step writes ONE line into k-space. The grid fills one line per repetition (TR) — the
// serial bottleneck that makes MRI slow. Gears (a generic "repeat") didn't show k-space filling; this does.
//
// 'gradient blip' names the mechanism under the bar the way 'k-space' names the grid, and it is now declared
// with the rest of this register's form vocabulary. It had been left out, and nothing noticed only because
// onscreen_text_qa discards any string containing "gradient" as CSS — so the one undeclared English label
// on the frame was invisible to the gate that exists to find it, rather than judged and kept.
// `steps` must be an integer 2-128: the blip's amplitude is `cur / (steps - 1)`, so one step divided by zero
// and drew a NaN bar, and past 128 the k-space lines sit under 4px apart and merge.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'k-space',
  'lines written',
  '±Gmax · steps each TR',
  'gradient blip',
];

export const MAX_PE_STEPS = 128;

export const PhaseEncodeStep: React.FC<{accent?: string; accent2?: string; label?: string; steps?: number}> = ({
  accent: ACC, accent2: ACC2, label = 'Phase encoding · one line per TR', steps = 16,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // THE INK IS THE FILM'S, AND THIS IS A DIAGRAM, NOT A GLOW. The k-space lines, the counter, the blip and
  // every label were literals picked for a near-black ground; all eight DNA presets are near-black, so a
  // film whose DNA came from a warm-white deck drew the grid and its count white on white — measured median
  // 1.54:1 over 99.99% of the marks (`scripts/ink_contrast_qa.py`). A ruled grid with a counter beside it is
  // a diagram: it reads in the film's own ink on any ground. Each token keeps its OWN original literal as
  // its fallback, so an un-themed render is unchanged.
  const accent = ACC ?? dna?.accent ?? '#22d3ee';
  const accent2 = ACC2 ?? dna?.accent2 ?? '#a78bfa';
  const live = dna?.fg ?? '#eaf6ff';         // the line being written now, and the acquired count
  const ink = dna?.fg ?? '#dfe8f5';          // the title
  const meta = dna?.dim ?? '#9fb4cc';        // 'k-space'
  const meta2 = dna?.dim ?? '#8aa';          // 'lines written', '±Gmax · steps each TR'
  const meta3 = dna?.fg ?? '#c9d6ea';        // 'gradient blip' — the name of the thing drawn beneath it
  const rule = dna?.line ?? '#3a4658';       // the blip's zero line
  if (!Number.isInteger(steps) || steps < 2 || steps > MAX_PE_STEPS) {
    throw new Error(`PhaseEncodeStep: \`steps\` is the number of phase-encode lines and must be an integer 2-${MAX_PE_STEPS} ` +
      `(got ${JSON.stringify(steps)}). The blip steps from -Gmax to +Gmax, which needs two ends; past ${MAX_PE_STEPS} ` +
      'the lines merge — draw a representative count and name the real matrix in the label.');
  }
  const cur = Math.min(steps - 1, Math.floor(clamp01(t) * steps));   // current phase-encode step

  // k-space grid (right): fill one line per step, from centre outward (typical order) — here top→bottom for clarity
  const gx = W * 0.44, gw = W * 0.4, gy = H * 0.24, gh = H * 0.5;
  const lines: React.ReactNode[] = [];
  for (let i = 0; i < steps; i++) {
    const y = gy + (i + 0.5) * (gh / steps);
    const on = i <= cur;
    const isCur = i === cur;
    lines.push(<line key={i} x1={gx} y1={y} x2={gx + gw} y2={y}
      stroke={isCur ? live : accent} strokeWidth={isCur ? 3.4 : 2.2} opacity={on ? (isCur ? 1 : 0.85) : 0.12} />);
  }

  // phase-encode gradient blip (left): a bar whose signed height = this step's amplitude (−Gmax..+Gmax)
  const amp = (cur / (steps - 1)) * 2 - 1;                   // −1..+1
  const bx = W * 0.24, baseY = H * 0.5, barMax = H * 0.18;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* k-space grid box */}
        <rect x={gx - 12} y={gy - 12} width={gw + 24} height={gh + 24} rx={8} fill="none" stroke={accent} strokeWidth={1.3} opacity={0.35} />
        {lines}
        <text x={gx - 12} y={gy - 24} fill={meta} fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">k-space</text>
        <text x={gx + gw + 24} y={gy + gh * 0.5} fill={live} fontSize="52" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800}>{cur + 1}<tspan fill={accent} fontSize="30">/{steps}</tspan></text>
        <text x={gx + gw + 26} y={gy + gh * 0.5 + 32} fill={meta2} fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">lines written</text>

        {/* gradient blip */}
        <line x1={bx - 70} y1={baseY} x2={bx + 70} y2={baseY} stroke={rule} strokeWidth={1.5} />
        <rect x={bx - 30} y={amp < 0 ? baseY : baseY - Math.abs(amp) * barMax} width={60} height={Math.abs(amp) * barMax || 2}
          rx={4} fill={accent2} opacity={0.9} />
        <text x={bx} y={baseY + barMax + 60} textAnchor="middle" fill={meta3} fontSize="22" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700}>gradient blip</text>
        <text x={bx} y={baseY - barMax - 22} textAnchor="middle" fill={meta2} fontSize="17" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">±Gmax · steps each TR</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default PhaseEncodeStep;
