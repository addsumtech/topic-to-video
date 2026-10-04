// TensionScale — the mission-vs-money thesis, encoded as a balance that NEVER settles. A beam teeters on a
// central fulcrum: MISSION (benefit all) on one arm, SCALE / MONEY / POWER on the other. It oscillates gently
// and forever — neither arm wins, neither goes flat. A "VS" split or a payoff-burst would imply a victor or a
// resolution; this thesis is a SUSTAINED equilibrium, so the visual has to hold the tension, not break it.
// Deterministic (pure fn of useT); labels are props so it generalises to any two-force tension.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {titleStyle, bottomTextY, fitTextPx, monoFit, textWidthPx} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 175; // ~5.8s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'equilibrium: unresolved',
];

export const TensionScale: React.FC<{
  title?: string; leftLabel?: string; leftSub?: string; rightLabel?: string; rightSub?: string;
  note?: string; accent?: string; accent2?: string;
  /** The equilibrium read-out under the beam. It was the literal `equilibrium: unresolved` with no way
   *  to reach it, so every film printed English on its frame whatever language it was in — on a
   *  Chinese film it is the only Latin string in the shot. A word the form owns still has to be a
   *  prop (§B1): the default keeps every existing film pixel-identical. */
  readout?: string;
}> = ({
  title = 'The tension that never resolves', leftLabel = 'MISSION', leftSub = 'benefit all of humanity',
  rightLabel = 'SCALE - MONEY - POWER', rightSub = 'the cost of the race', note = 'neither side wins - that IS the story', readout = 'equilibrium: unresolved',
  accent: accentIn, accent2: accent2In,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  // THE BEAM WAS THE ONE THING THIS REGISTER HAS, AND IT WAS A LITERAL. `#e6edf5` is the teetering beam, the
  // single object that carries the thesis, and on a film grounded paper it was drawn white on white: measured
  // 1.07:1, a frame with two labelled cards, a triangle and NO BALANCE BETWEEN THEM. The title, the note, the
  // pans' sub-lines and the pivot knot went the same way. Each keeps its own fallback.
  const accent = accentIn ?? dna?.accent ?? '#10a37f';
  const accent2 = accent2In ?? dna?.accent2 ?? '#7aa2ff';
  const BEAM = dna?.fg ?? '#e6edf5';
  const KNOT = dna?.fg ?? '#fff';
  const CARD = dna?.surface ?? '#0d1117';
  const SUB_INK = dna?.dim ?? '#9fb0c3';
  const FULCRUM = dna?.surface ?? '#141b26';
  const FULCRUM_EDGE = dna?.line ?? '#2b3646';
  const BASE_LINE = dna?.line ?? '#1a2230';
  const READOUT_INK = dna?.dim ?? '#67788c';
  const NOTE_INK = dna?.dim ?? '#c9d6ea';
  const TITLE_INK = dna?.fg ?? '#dfe8f5';
  const t = useT();
  const glide = useGlide();
  const portrait = W < H;
  const cx = W * 0.5, fy = portrait ? H * 0.46 : H * 0.52, L = portrait ? W * 0.30 : W * 0.30;
  const capBw = portrait ? Math.min(W * 0.4, 432) : 540;   // keep the end-pans on-frame in a narrow portrait frame
  // a gentle, damped-but-continuing teeter — small amplitude so it reads as HELD tension, never tipping over
  const settle = clamp01(t * 3);                                  // beam appears, then teeters
  const th = 0.095 * settle * Math.sin(t * Math.PI * 2 * 1.15) * (0.62 + 0.38 * Math.sin(t * Math.PI * 2 * 0.5));
  const lx = cx - L * Math.cos(th), ly = fy + L * Math.sin(th);   // MISSION arm end
  const rx = cx + L * Math.cos(th), ry = fy - L * Math.sin(th);   // SCALE/MONEY arm end
  const appear = clamp01(t * 4);

  const MONO = monoFit();
  const pan = (x: number, y: number, label: string, sub: string, col: string, key: string) => {
    // BOX AND FONT ADAPT TO THE REAL LABEL — MEASURED, not counted. `label.length * 13` is a character
    // count with a Latin width attached to it, and in this monospace face a Han glyph advances TWO CELLS
    // (1.2em, not 0.62em). So a Chinese label got a box a third too narrow and an SVG <text>, which cannot
    // wrap and is centred on its anchor, ran out of BOTH sides of the frame — 68px each way, measured.
    // The size is fitted to the widest box this frame allows, and the box is then drawn to the ink.
    const inner = Math.max(60, capBw - 44);
    const lfs = fitTextPx(label, inner, 22, {usable: 1, ...MONO});
    const sfs = fitTextPx(sub, inner, 16, {usable: 1});
    const bw = Math.max(portrait ? 260 : 300, Math.min(capBw,
      Math.max(textWidthPx(label, lfs, MONO), textWidthPx(sub, sfs)) + 44));
    return (
    // the arm's x/y are SVG numeric attributes, not a CSS transform, but Skia judges the screen CTM the same
    // way either way: a beam that never settles (see the header) needs the unlock for as long as it teeters,
    // so it rides the whole `<g>` — harmless on the line/rect, and it reaches the two <text> runs beneath it.
    <g key={key} opacity={appear} transform={glide(undefined, true)}>
      <line x1={x} y1={y} x2={x} y2={y + 28} stroke={`${col}aa`} strokeWidth={2} />
      <rect x={x - bw / 2} y={y + 28} width={bw} height={78} rx={8} fill={CARD} stroke={col} strokeWidth={1.6} />
      <text x={x} y={y + 60} textAnchor="middle" fill={col} fontSize={lfs} fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" fontWeight={700}>{label}</text>
      <text x={x} y={y + 88} textAnchor="middle" fill={SUB_INK} fontSize={sfs} fontFamily="var(--f-body, Inter, sans-serif)">{sub}</text>
    </g>
    );
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0c1016, #06070a)')}}>
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        {/* faint technical grid baseline */}
        <line x1={W * 0.12} y1={fy} x2={W * 0.88} y2={fy} stroke={BASE_LINE} strokeWidth={1} strokeDasharray="2 10" opacity={0.6} />
        {/* the beam */}
        <line x1={lx} y1={ly} x2={rx} y2={ry} stroke={BEAM} strokeWidth={5} strokeLinecap="round" opacity={appear} />
        {/* the two force pans */}
        {pan(lx, ly, leftLabel, leftSub, accent, 'L')}
        {pan(rx, ry, rightLabel, rightSub, accent2, 'R')}
        {/* fulcrum triangle + glowing knot at the pivot */}
        <path d={`M${cx - 30},${fy + 66} L${cx},${fy + 6} L${cx + 30},${fy + 66} Z`} fill={FULCRUM} stroke={FULCRUM_EDGE} strokeWidth={1.4} />
        <circle cx={cx} cy={fy} r={9 + 3 * Math.sin(t * Math.PI * 2 * 1.15)} fill={KNOT} opacity={0.9} />
        <circle cx={cx} cy={fy} r={20} fill="none" stroke={`${accent}`} strokeWidth={1.5} opacity={0.4 + 0.3 * Math.abs(Math.sin(t * Math.PI * 2 * 1.15))} />
        {/* equilibrium readout */}
        <text x={cx} y={fy + 96} textAnchor="middle" fill={READOUT_INK} fontSize="15" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={appear}>{readout}</text>
        {/* bottom note (kept above the caption band) */}
        {/* The note was made band-aware VERTICALLY and never bounded horizontally. An SVG <text> does not
            wrap, and this one is centred on the frame, so a Chinese note simply grew out of both edges. */}
        <text x={cx} y={Math.min(H * 0.82, bottomTextY(W, H))} textAnchor="middle" fill={NOTE_INK} fontSize={fitTextPx(note, W * 0.9, 20, {usable: 1, ...MONO})} fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01((t - 0.15) * 3)}>{note}</text>
      </svg>
      <div style={{...titleStyle, color: TITLE_INK, opacity: lerp(0.4, 1, clamp01(t * 4))}}>{title}</div>
    </AbsoluteFill>
  );
};
export default TensionScale;
