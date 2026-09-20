// UndersampledKspace — what undersampling actually means: a full Cartesian k-space (every phase-encode line) has
// most of its lines REMOVED, keeping only every `keep`-th — the measurements you skip to go faster. A method
// line under the title says what reconstructs the image from what's left. The vanishing lines + the
// surviving sparse subset ARE the idea. Deterministic (pure fn of useT).
//
// EVERY NUMBER ON THIS FRAME IS NOW EITHER THE FILM'S OR COUNTED FROM WHAT IS DRAWN. Three were not:
//   * the method line counted `Math.round(lerp(0, 167, …))` up to "167", so "trained on 167k scans" printed
//     on every film whatever its method was trained on — `method` and `unit` were props, the count was not.
//     The figure is `scans` now, the film's string ('167k scans' by default, which the demo-copy gate lists
//     when a film omits it), counted up through runtime/figure and landing on the film's exact text; a
//     string that is not one number is shown verbatim, and '' draws no figure.
//   * "~4–8× undersampled" was a literal that ignored `keep`, so `keep: 2` drew 21/42 lines acquired beside
//     a claim of four to eight times. The factor printed now IS `keep` — the nominal acceleration R of
//     keeping every R-th line — so the words cannot disagree with the lines.
//   * the 42-line total was the register's own. It is `lines` (default 42).
// And the acquired count was `Math.round(lines / keep)`, which is not how many lines `i % keep === 0` keeps
// (42 lines at keep 5 keeps 9, and it printed 8); it is the ceiling now, the count of lines actually drawn.
// A `keep` below 2 (nothing is undersampled), above `lines`, or a non-integer, THROWS; so does a `lines`
// count the grid cannot draw as separate strokes.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY} from '../runtime/layout';
import {figureAt, parseFigure} from '../runtime/figure';

export const DURATION = 180; // 6s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
// '× undersampled' follows the factor `keep` supplies — the mechanism's own name for what is drawn.
export const INTRINSIC_TEXT = [
  'k-space · phase-encode lines',
  'lines acquired',
  '× undersampled',
];

export const MAX_KSPACE_LINES = 128;   // past this the strokes sit under 4px apart and merge into a block

export const UndersampledKspace: React.FC<{accent?: string; accent2?: string; label?: string; keep?: number;
  lines?: number; method?: string; scans?: string}> = ({
  accent: ACC, accent2: ACC2, label = 'Reconstruct from far fewer lines', keep = 6,
  lines = 42,
  // A CLAIM ABOUT A METHOD, written straight into the JSX: `deep network · trained on {scans}k scans`
  // printed on every film that ever reached for this register, whatever the film's method actually was,
  // and the count beside it is the register's own. Both halves are props now, each defaulting to the words
  // it replaced, so existing films render identically and a film that trains on something else can say so.
  method = 'deep network · trained on', scans = '167k scans',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // THE INK IS THE FILM'S, AND THIS IS A DIAGRAM, NOT A GLOW. The lines, the counter and every label were
  // literals picked for a near-black ground; all eight DNA presets are near-black, so a film whose DNA came
  // from a warm-white deck drew the k-space grid and its count white on white — measured median 1.60:1 over
  // 100% of the marks (`scripts/ink_contrast_qa.py`). Ruled lines and a count are a diagram, and they read
  // in the film's own ink on any ground. Each token keeps its OWN original literal as its fallback, so an
  // un-themed render is unchanged.
  const accent = ACC ?? dna?.accent ?? '#22d3ee';
  const accent2 = ACC2 ?? dna?.accent2 ?? '#a78bfa';
  const live = dna?.fg ?? '#eaf6ff';         // the acquired count
  const ink = dna?.fg ?? '#dfe8f5';          // the title
  const meta = dna?.dim ?? '#9fb4cc';        // 'k-space · phase-encode lines'
  const meta2 = dna?.dim ?? '#8aa';          // 'lines acquired' and the film's method line
  if (!Number.isInteger(lines) || lines < 2 || lines > MAX_KSPACE_LINES) {
    throw new Error(`UndersampledKspace: \`lines\` is the fully-sampled line count and must be an integer 2-${MAX_KSPACE_LINES} ` +
      `(got ${JSON.stringify(lines)}); past ${MAX_KSPACE_LINES} the strokes merge. Draw a representative count and put ` +
      'the real matrix size in the label.');
  }
  if (!Number.isInteger(keep) || keep < 2 || keep > lines) {
    throw new Error(`UndersampledKspace: \`keep\` is the acceleration R — every R-th of the ${lines} lines is kept — and ` +
      `must be an integer from 2 to ${lines} (got ${JSON.stringify(keep)}). R = 1 keeps every line, which is not ` +
      'undersampled.');
  }
  const gx = W * 0.16, gw = W * 0.68, gy = H * 0.2;
  // the acquired-lines counter sits to the grid's right when the room exists; on a narrow frame it steps
  // UNDER the grid (the sweep caught '~4-8x undersampled' 135px off a portrait edge)
  const cRoom = W - (gx + gw) - 40;
  const cUnder = cRoom < 240;   // 16:9 leaves 267px and has always fit; 9:16 leaves 133 and never can
  // AND THE ROOM IT STEPS INTO HAS TO EXIST. Stepping under was checked at 9:16, where the frame is 1920
  // tall and the block lands 108px clear. It was never checked at the three aspects nobody had swept: the
  // block is 160px deep below the grid, `gh` is a flat 0.52 of the height, and at 1:1 that put its last
  // line 128px INSIDE the caption band (52px at 4:5, 71px at 4:3) — the burned subtitle drawn straight
  // through the number the shot exists to show. The grid yields the room instead, because it is the
  // element that can: 42 lines read the same at 434px as at 562px, and a reading missing its label does
  // not. 16:9 (never under) and 9:16 (already clear) are untouched by construction.
  const CBLOCK = 64 + 96;       // first baseline below the grid, plus the block's own last baseline
  const gh = cUnder ? Math.min(H * 0.52, bottomTextY(W, H) - gy - CBLOCK) : H * 0.52;
  const cX = cUnder ? gx : gx + gw + 40;
  const cY = (line: number) => (cUnder ? gy + gh + 64 + line * 46 : gy + gh * 0.42 + line * 46);
  const drop = clamp01(seg(t, 0.15, 0.75));                 // how far the removal has progressed

  const strokes: React.ReactNode[] = [];
  for (let i = 0; i < lines; i++) {
    const y = gy + (i + 0.5) * (gh / lines);
    const kept = i % keep === 0;
    // kept lines stay bright; the rest FADE OUT as `drop` advances
    const op = kept ? 0.95 : lerp(0.6, 0.06, drop);
    const col = kept ? accent : accent2;
    strokes.push(<line key={i} x1={gx} y1={y} x2={gx + gw} y2={y} stroke={col} strokeWidth={kept ? 2.6 : 1.2} opacity={op} />);
  }

  // counters — both counted from the lines drawn above
  const total = lines, acquired = Math.ceil(lines / keep);
  const shownAcq = Math.round(lerp(total, acquired, drop));
  const scansFig = parseFigure(scans);
  const scansShown = figureAt(scansFig, clamp01(seg(t, 0.2, 0.85)));
  const methodLine = [String(method ?? '').trim(), scansShown].filter(Boolean).join(' ');

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 40%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <rect x={gx - 14} y={gy - 14} width={gw + 28} height={gh + 28} rx={10} fill="none" stroke={accent} strokeWidth={1.4} opacity={0.35} />
        {strokes}
        <text x={gx - 14} y={gy - 26} fill={meta} fontSize="22" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" letterSpacing="1">k-space · phase-encode lines</text>
        {/* live count of acquired lines */}
        <text x={cX} y={cY(0)} fill={live} fontSize="72" fontFamily="var(--f-display, Inter, sans-serif)" fontWeight={800}>
          {shownAcq}<tspan fill={accent} fontSize="40">/{total}</tspan></text>
        <text x={cX + 4} y={cY(0) + 40} fill={meta2} fontSize="22" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">lines acquired</text>
        <text x={cX + 4} y={cY(0) + 96} fill={accent2} fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700}>{keep}× undersampled</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}
        {methodLine ? (
          <div style={{marginTop: 8, font: "600 22px/1 var(--f-mono, 'JetBrains Mono', monospace)", color: meta2, letterSpacing: '0.1em'}}>
            {methodLine}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default UndersampledKspace;
