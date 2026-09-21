// SHOT · Chart Live — analytics language done as a LIVE DRAWING (not static bars/cards): a glowing line draws
// itself across, an area fills under it, a leading dot glows, and a headline metric counts up in step. Dark +
// a bright accent. Deterministic (draw progress + counter = fn of t).
//
// THE LINE IS THE FILM'S SERIES, OR THERE IS NO LINE. This register used to draw one hardcoded rising curve
// (`DATA = [0.28, 0.34, … 0.96]`) under whatever `endVal` and `label` a film passed. No prop could reach it,
// so every film that used it — the WorkBuddy film's "68× Hy3 call volume" included — shipped a steady
// twelve-step climb as though it were that figure's history. A trend line under a label is a claim about the
// label. Now the curve is `series` (the film's numbers, in order, drawn on a zero-based scale), and a film that
// gives a figure but no series gets the figure alone, centred, with no chart furniture under it.
//
// THE FIGURE IS THE FILM'S STRING. The counter was `Math.round(lerp(0, endVal, prog))`: 2.5 printed as 3, and
// it only reached the value at t≈0.86. It now goes through runtime/figure.ts — `figureAt` counts up a string
// that is exactly one number with its own decimals/sign/grouping/suffix and prints anything else as written —
// and the draw and the count settle together by t=0.6, so the true figure holds for the last 40% of the beat.
// `unit` no longer defaults to 'k' for a film: "68" with no unit printed "68k", a unit nobody supplied.
//
// THE DEMO IS ALL-OR-NOTHING. The illustrative 128k / rising series / 'k' appear only when the register gets
// NONE of its content props (`npx remotion still src/index.ts ChartLive`). A film that passes any of them is
// never completed with a demo datum — a numeric series is invisible to the demo-copy gate, so the register
// itself must refuse to invent one.
//
// AND THE SHEET IS THE FILM'S, NOT A DARK ROOM OF ITS OWN. The ground was a fixed near-black radial
// (#0f1a1a→#060b0b), the gridlines a dark green and the figure's ink a pale mint, so only the accent ever
// moved with the film: rendered under a light probe (bg #f6f3ee) the register painted its own black sheet
// over the paper at Y=0.005 with 19% of its marks under 3:1 (scripts/ink_contrast_qa.py). This is NOT a dark
// world — a chart's meaning is the SHAPE of its line, which is the same shape drawn in ink on paper as in
// light on glass, and a chart on paper is the oldest form of chart there is. So ground, gridlines, figure ink
// and label all come from the DNA, and the accent keeps drawing the line: `groundFrom` exposes an accent
// until it clears 3:1 on whatever ground it is handed, so the line reads on the film's paper by contract
// rather than by luck. The line's `#lg` bloom is kept on both exposures — it is a blurred copy of the accent
// merged under the accent, so it thickens the stroke in the stroke's own colour and never lays black on
// paper (the mud case runtime/light.tsx warns about).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {Figure} from '../runtime/atoms';
import {parseFigure, figureAt, figureText, figureValue} from '../runtime/figure';
import {contentBottom, fitTextPx, textWidthPx} from '../runtime/layout';

export const DURATION = 150; // 5s
const ACC_D0 = '#37E0A0';
// the original dark-room literals, kept as the no-DNA rendering (byte-for-byte) and as the fallback chain
const GROUND_D0 = 'radial-gradient(120% 120% at 50% 30%, #0f1a1a, #060b0b 72%)';
const INK_D0 = '#eafff4';    // the figure, and the dot riding the line's tip
const LABEL_D0 = '#6f8f83';  // the metadata line under the figure
const GRID_D0 = '#16302a';   // the unlabelled reading gridlines
// the standalone preview's illustrative data — used ONLY when no content prop at all was passed (see header)
const DEMO_SERIES = [28, 34, 30, 44, 52, 48, 62, 70, 66, 82, 90, 96];
const DEMO_END = 128, DEMO_UNIT = 'k';
export const MAX_SERIES_POINTS = 240;   // ~6px a step on a 1920 frame; past that it is a texture, not a line

const readSeries = (series: unknown): number[] | null => {
  if (series == null) return null;
  if (!Array.isArray(series)) {
    throw new Error(`ChartLive: \`series\` must be an array of numbers in order (got ${typeof series}).`);
  }
  if (series.length === 0) return null;   // an explicit [] = "no line", the same as omitting it
  if (series.length < 2 || series.length > MAX_SERIES_POINTS) {
    throw new Error(`ChartLive: \`series\` needs 2-${MAX_SERIES_POINTS} points to draw a line (got ${series.length}). ` +
      'One value is a figure, not a trend — pass it as `endVal` alone; a longer run should be resampled by the ' +
      'film (and say so), never silently cut here.');
  }
  return series.map((v, i) => {
    const n = typeof v === 'number' ? v : figureValue(v);
    if (n == null || !Number.isFinite(n)) {
      throw new Error(`ChartLive: series point ${i + 1} is ${JSON.stringify(v)}, which is not one number. ` +
        'Every point is drawn at its height, so each must be a sourced number.');
    }
    return n;
  });
};

// Copy is overridable so a film can show a FAITHFUL, sourced figure (never a fabricated demo number).
export const ChartLive: React.FC<{endVal?: number | string; unit?: string; label?: string; series?: number[]}> = ({
  // `label` is bound twice: `labelIn` is what the film passed (undefined if nothing), `label` adds the preview
  // copy the demo-copy gate lists. Only "nothing passed at all" may unlock the demo data.
  endVal, unit, label: labelIn, label = 'tasks handled this month', series} = {}) => {
  const dna = useDNA();
  const ACC = dna?.accent ?? ACC_D0;
  // the figure is the film's ink, its label the film's metadata token, the gridlines the film's rule — the
  // three places this register used to state a colour of its own (see the header)
  const INK = dna?.fg ?? INK_D0;
  const LABEL_INK = dna?.dim ?? LABEL_D0;
  const GRID = dna?.line ?? GRID_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const standalone = endVal === undefined && unit === undefined && labelIn === undefined && series === undefined;
  const DATA = standalone ? DEMO_SERIES : readSeries(series);
  const figText = standalone ? String(DEMO_END) : figureText(endVal);
  const UNIT = standalone ? DEMO_UNIT : (unit ?? '');
  const LABEL = String(label ?? '');

  // ── the draw and the count share one clock, settled by t = 0.6 ─────────────────────────────────────────
  const prog = easeOutCubic(seg(t, 0.12, 0.6));
  const shown = figText ? figureAt(parseFigure(figText), prog) : '';

  // ── LAYOUT: the headline block on top, the plot BELOW it, both inside the content zone ───────────────────
  // The plot used to span y 300..H-300 with the metric drawn OVER its top-left corner; that only looked clean
  // because the one hardcoded curve rose to the right. A falling series starts top-left and ran through the
  // figure and its label, so the plot now starts under the headline block, whatever the data does.
  const mX = Math.round(W * 0.115);                                     // 220 at 1920
  const bottom = contentBottom(W, H) - Math.round(Math.min(W, H) * 0.02);
  const unitScale = 100 / 210;
  const figPer = figText ? textWidthPx(figText, 1) + (UNIT ? textWidthPx(UNIT, unitScale) : 0) : 0;
  const figPx = figText ? Math.max(48, Math.min(210, Math.floor((W - 2 * mX) / Math.max(0.1, figPer)))) : 0;
  const labelPx = LABEL ? fitTextPx(LABEL, W - 2 * mX, 42, {usable: 1}) : 0;
  // A film's figure can carry a grouping comma ("1,204"), and the display form's 0.9 line box is tighter than
  // the comma's descender: at the old 6px gap it landed on the label's first glyph. Reserve it always.
  const labelGap = figText ? Math.max(6, Math.round(figPx * 0.2)) : 0;
  const headH = (figText ? Math.round(figPx * 0.9) : 0) + (LABEL ? labelGap + Math.round(labelPx * 1.1) : 0);
  // with no series the headline IS the frame: centre it in the content zone instead of pinning it top-left
  const headTop = DATA ? 150 : Math.round((150 + bottom) / 2 - headH / 2);
  const X0 = mX, X1 = W - mX, Y1 = headTop + headH + Math.round(H * 0.06), Y0 = bottom;

  let plot: React.ReactNode = null;
  if (DATA) {
    const lo = Math.min(0, ...DATA), hiRaw = Math.max(...DATA);
    const hi = hiRaw > lo ? hiRaw : lo + 1;                               // a flat all-zero series sits on the floor
    const yOf = (v: number) => lerp(Y0, Y1, (v - lo) / (hi - lo));
    const pt = (i: number): [number, number] => [lerp(X0, X1, i / (DATA.length - 1)), yOf(DATA[i])];
    const path = DATA.map((_, i) => (i ? 'L' : 'M') + pt(i).join(',')).join(' ');
    const base = yOf(0);                                                   // the area fills to ZERO, not to the frame
    const area = path + ` L${X1},${base} L${X0},${base} Z`;
    // leading dot position along the drawn portion
    const fi = prog * (DATA.length - 1); const li = Math.min(DATA.length - 2, Math.floor(fi));
    const lead: [number, number] = [lerp(pt(li)[0], pt(li + 1)[0], fi - li), lerp(pt(li)[1], pt(li + 1)[1], fi - li)];
    plot = (
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="af" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={ACC} stopOpacity="0.35" /><stop offset="1" stopColor={ACC} stopOpacity="0" /></linearGradient>
          <filter id="lg"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <clipPath id="rev"><rect x={X0} y={0} width={(X1 - X0) * prog} height={H} /></clipPath>
        </defs>
        {/* gridlines — unlabelled, evenly spaced: a reading aid, never a value */}
        {[0, 0.25, 0.5, 0.75, 1].map((g, i) => <line key={i} x1={X0} y1={lerp(Y0, Y1, g)} x2={X1} y2={lerp(Y0, Y1, g)} stroke={GRID} strokeWidth={1.5} />)}
        {/* area + line, revealed left→right */}
        <g clipPath="url(#rev)">
          <path d={area} fill="url(#af)" />
          <path d={path} fill="none" stroke={ACC} strokeWidth={5} filter="url(#lg)" />
        </g>
        {/* leading dot */}
        {prog > 0.02 && prog < 0.99 && <circle cx={lead[0]} cy={lead[1]} r={12} fill={INK} filter="url(#lg)" />}
      </svg>
    );
  }

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? GROUND_D0}}>
      {plot}
      {/* headline metric counting up */}
      <div style={DATA ? {position: 'absolute', left: mX, top: headTop}
        : {position: 'absolute', left: mX, right: mX, top: headTop, textAlign: 'center'}}>
        {/* fontVariantNumeric is THIS shot's own choice (Figure's shared base does not impose it) — kept
            here, on the wrapper, exactly where it lived before the migration. unitScale is the EXACT ratio
            (100/210) the original hardcoded unit size (100px) was, not the 0.476 float that rounded to
            99.96px. fallbackForm/fallbackFamily make explicit what previously worked only because
            NEUTRAL_DNA.fontDisplay happens to match this shot's hardcoded stack. */}
        {figText ? (
          <div style={{fontVariantNumeric: 'tabular-nums'}}>
            <Figure value={shown} unit={UNIT} ink={INK} tone={ACC} size={figPx} unitScale={unitScale}
              fallbackForm="display" fallbackFamily="Inter, system-ui, sans-serif" />
          </div>
        ) : null}
        {LABEL ? (
          <div style={{font: `600 ${labelPx}px/1.1 var(--f-body, Inter,system-ui,sans-serif)`, color: LABEL_INK,
            marginTop: labelGap, maxWidth: W - 2 * mX}}>{LABEL}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default ChartLive;
