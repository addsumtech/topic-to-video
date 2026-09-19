// SHOT · Before / After Slider — comparison language: a slider WIPES across, transforming a rough draft into
// the finished deliverable in place. A clean split-reveal (before dull, after vivid). Deterministic wipe.
//
// THE MOCK SLIDE'S CHART IS THE FILM'S DATA, OR IT IS NOT DRAWN. The slide carried a five-bar column chart
// from a module literal — `[0.5, 0.82, 0.4, 0.95, 0.66]` — with the fourth bar painted the "good" green,
// directly under the film's own heading and metric. On a film about anything, that reads as the data behind
// the number: "here is the quarter, and here is the week it peaked". Nobody supplied it. The bars now come
// from `series` (numbers, or the film's figure strings in one unit, drawn from zero in proportion), laid
// out for however many the film gives; no `series`, no chart. The green bar is `highlight` — an index into
// `series` the film chooses — and by default no bar is singled out.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {parseFigure} from '../runtime/figure';

export const DURATION = 150; // 5s
// LEVEL-C: the previewed "slide" surfaces + accents follow the DNA → a DARK slide being refined on a dark DNA (the
// before/after contrast is carried by the CONTENT colours — dull greys vs vivid accent — so it survives the flip).
const ACCENT = '#2E7BFF';
export const MIN_SLIDER_BARS = 2;
export const MAX_SLIDER_BARS = 8;

const normaliseSeries = (series: unknown, highlight: unknown): {bars: number[] | null; hi: number | null} => {
  if (series == null) {
    if (highlight != null) {
      throw new Error('BeforeAfterSlider: `highlight` picks a bar of `series`, and no `series` was given.');
    }
    return {bars: null, hi: null};
  }
  if (!Array.isArray(series) || series.length < MIN_SLIDER_BARS || series.length > MAX_SLIDER_BARS) {
    throw new Error(`BeforeAfterSlider needs ${MIN_SLIDER_BARS}-${MAX_SLIDER_BARS} \`series\` values when it draws a chart ` +
      `(got ${Array.isArray(series) ? series.length : typeof series}). One bar is not a chart — the metric already ` +
      'says it; omit `series` for a slide with no chart.');
  }
  let unit: string | null = null;
  const bars = series.map((v, i) => {
    const fig = parseFigure(v);
    if (fig.num == null || fig.num < 0) {
      throw new Error(`BeforeAfterSlider: series[${i}] must be one number >= 0 (bars stand on a baseline), got ` +
        `${JSON.stringify(v)}.`);
    }
    // heights compare the numbers as written, so "1.2M" next to "800k" would draw 1.2 against 800
    const u = `${fig.prefix.trim()}|${fig.suffix.trim()}`;
    if (unit != null && u !== unit) {
      throw new Error(`BeforeAfterSlider: \`series\` mixes units (${JSON.stringify(v)} vs series[0]) — convert them to one unit.`);
    }
    unit = u;
    return fig.num;
  });
  if (!bars.some((b) => b > 0)) throw new Error('BeforeAfterSlider: every `series` value is 0 — there is no chart to draw.');
  if (highlight != null && !(Number.isInteger(highlight) && (highlight as number) >= 0 && (highlight as number) < bars.length)) {
    throw new Error(`BeforeAfterSlider: \`highlight\` must be an index into \`series\` (0-${bars.length - 1}), ` +
      `got ${JSON.stringify(highlight)}.`);
  }
  return {bars, hi: highlight == null ? null : (highlight as number)};
};

const Slide: React.FC<{finished: boolean; heading: string; metric: string; sub: string; bars: number[] | null;
  hi: number | null; w: number; h: number}> = ({finished, heading, metric, sub, bars, hi, w, h}) => {
  const dna = useDNA();                       // module-scope subcomponent reads the DNA itself
  const ACC = dna?.accent ?? ACCENT, GOOD = dna?.accent2 ?? '#12b76a', DIM = dna?.dim ?? '#c3c8d2';
  const SURF = dna?.surface ?? '#ffffff', BEFOREBG = dna?.surface ?? '#f1f2f5', DULLBAR = dna?.dim ?? '#d4d8e0', SUB = dna?.dim ?? '#9aa3b2';
  const title = finished ? ACC : DIM;
  const barC = (i: number) => finished ? (i === hi ? GOOD : ACC) : DULLBAR;
  // THE CHART TAKES THE ROOM THAT IS LEFT, not a fixed 420px. The panel is clamped to the content zone (704px
  // tall at 1920x1080) and the slide's copy is fixed-size, so a fixed chart pushed the film's own METRIC out of
  // the panel's bottom edge — measured on the first render with a series: the bars ran under the before/after
  // chips and the headline number was not on the frame at all. Stack, top to bottom: pad · heading 96 · rule 38
  // · chart gap 40 · CHART · 30 · metric+sub 130 · the chips' strip at the bottom (40 + 54 + 20).
  const pad = Math.round(Math.min(120, h * 0.12)), chipStrip = 114;
  const chartW = Math.max(200, Math.min(1000, w - pad * 2));
  const chartH = Math.max(80, h - pad - chipStrip - 96 - 38 - 40 - 30 - 130);
  const n = bars?.length ?? 0;
  const barW = n ? Math.min((chartW / n) * 0.72, Math.max(24, chartH * 0.55)) : 0;
  const pitch = n ? Math.min(chartW / n, barW / 0.55) : 0;     // few bars sit together under the heading, not spread thin
  const vmax = bars ? Math.max(...bars) : 1;
  const base = chartH - 4, tall = chartH - 12;
  return (
    <div style={{position: 'absolute', inset: 0, background: finished ? SURF : BEFOREBG, padding: pad}}>
      <div style={{font: `800 ${finished ? 96 : 92}px/1 var(--f-display, Inter,system-ui,sans-serif)`, color: title}}>{heading}</div>
      <div style={{height: 8, width: finished ? 260 : 200, background: finished ? ACC : DULLBAR, borderRadius: 4, marginTop: 30}} />
      {bars ? (
        <svg width={chartW} height={chartH} style={{marginTop: 40, display: 'block'}}>
          {bars.map((v, i) => {
            const bh = tall * (v / vmax);
            return <rect key={i} x={i * pitch + (pitch - barW) / 2} y={base - bh} width={barW} height={bh} rx={Math.min(10, barW / 4)} fill={barC(i)} />;
          })}
        </svg>
      ) : null}
      <div style={{display: 'flex', gap: 40, marginTop: bars ? 30 : 70}}>
        <div><div style={{font: '800 84px/1 var(--f-body, Inter)', color: finished ? GOOD : DIM}}>{metric}</div>
          <div style={{font: '600 34px/1 var(--f-body, Inter)', color: SUB, marginTop: 12}}>{sub}</div></div>
      </div>
    </div>
  );
};

export const BeforeAfterSlider: React.FC<{heading?: string; metric?: string; sub?: string; beforeLabel?: string; afterLabel?: string;
  series?: (number | string)[]; highlight?: number | null}> = ({
  heading = 'Q3 Performance', metric = '+18%', sub = 'vs Q2', beforeLabel = 'Rough draft', afterLabel = 'Board-ready',
  series, highlight = null} = {}) => {
  const {bars, hi} = normaliseSeries(series, highlight);
  const dna = useDNA();
  const ACC = dna?.accent ?? ACCENT, BG = dna?.bg ?? '#e7e9ef', HANDLE = dna?.fg ?? '#fff', ON = dna?.onAccent ?? '#fff', CHIP = dna?.surface ?? 'rgba(30,35,55,.5)';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // The panel is sized to the zone the shot OWNS. At 1500x900 fixed it hung 157px into the caption band and
  // carried its 'Rough draft' / 'Board-ready' chips and its headline figure down there with it — four of this
  // library's 73 band collisions came from this one panel. Fixed pixels also make it wrong at every aspect
  // but the one it was drawn on.
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const CW = Math.min(1500, W * 0.86), CH = Math.min(900, zoneBot - zoneTop);
  const X = (W - CW) / 2, Y = zoneTop + (zoneBot - zoneTop - CH) / 2;
  const s = lerp(0.14, 0.86, easeInOutCubic(seg(t, 0.12, 0.9))); // slider fraction
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: X, top: Y, width: CW, height: CH, borderRadius: 20, overflow: 'hidden', boxShadow: '0 40px 100px rgba(40,45,80,.2)'}}>
        {/* BEFORE (behind) */}
        <Slide finished={false} heading={heading} metric={metric} sub={sub} bars={bars} hi={hi} w={CW} h={CH} />
        {/* AFTER (front), revealed from the left up to the slider */}
        <div style={{position: 'absolute', inset: 0, clipPath: `inset(0 ${(1 - s) * 100}% 0 0)`}}>
          <Slide finished={true} heading={heading} metric={metric} sub={sub} bars={bars} hi={hi} w={CW} h={CH} />
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
