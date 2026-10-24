// SHOT · Function Plot — a function the narration is about, drawn the way a lecturer draws it: its typeset formula
// written on, the axes ruled, the curve traced from its first value to its last, and a point that rides the curve
// with a readout of where it is — every number on the frame one the film supplied.
//
// WHAT IT ARGUES. The SHAPE of a dependence: where it rises, where it turns, where it dies away — and, through the
// rider, that each point of that shape is a pair of numbers. Hide the caption and the curve still says "decays while
// it oscillates" or "grows faster and faster". Not for comparing categories (a bar register), not for a quantity's
// history with events on it (a timeline/chart register), not for a single number (a figure register).
//
// THE NUMBERS ARE THE FILM'S. The curve is the film's own samples (`points`), drawn as the polyline through them —
// nothing is fitted or smoothed in between. The axes span exactly the film's data, or the film's `xRange`/`yRange`,
// and their end labels print those numbers as written. The readout is the LAST SAMPLE THE RIDER HAS PASSED, printed
// as the film wrote it, so it ticks through the data rather than inventing values between them. The formula is the
// film's TeX (runtime/mathMorph), typeset ahead of the render.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, dimOn, contrastOf, mix} from '../runtime/dna';
import {drawOn} from '../runtime/draw';
import {rows} from '../runtime/rows';
import {figureText} from '../runtime/figure';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {useEquations, MathLayer, writeState} from '../runtime/mathMorph';

export const DURATION = 240; // 8s

const BG_D0 = '#0b0f17', FG_D0 = '#eef2f8', DIM_D0 = '#8b95a7', ACC_D0 = '#7cc4ff';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// THE DEMO'S DATA: y = e^(−x/2)·cos 2x sampled at x = 0, 0.05, …, 6, each value rounded to three decimals here —
// computed from the formula it is drawn under, never typed in.
const DEMO_TEX = 'y = e^{-x/2}\\cos 2x';
const DEMO_TITLE = 'It swings, and every swing is smaller';
const DEMO_XLABEL = 'time (s)', DEMO_YLABEL = 'displacement';
const DEMO_POINTS: [number, number][] = Array.from({length: 121}, (_, i) => {
  const x = Math.round(i * 5) / 100;
  return [x, Math.round(Math.exp(-x / 2) * Math.cos(2 * x) * 1000) / 1000];
});

export const FunctionPlot: React.FC<{
  kicker?: string;
  title?: string;
  /** the function, in TeX — drawn in the plot's corner */
  tex?: string;
  /** the film's samples [x, y], x increasing — the curve is the polyline through them */
  points?: [number, number][];
  /** the axes' spans; default: exactly the data's */
  xRange?: [number, number];
  yRange?: [number, number];
  /** what each axis measures */
  xLabel?: string;
  yLabel?: string;
  /** the readout's variable names (default x, y) */
  xName?: string;
  yName?: string;
  accent?: string;
}> = ({kicker = 'DAMPED OSCILLATION', title: TITLE_IN, tex: TEX_IN, points: PTS_IN, xRange, yRange,
       xLabel: XL_IN, yLabel: YL_IN, xName = 'x', yName = 'y', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // the demo's formula, title and axis names belong to the demo's DATA: a film that passes its own points and leaves
  // one of them out gets none. Written as `?? (demo ? …)`, never as prop defaults — a string default cannot be told
  // apart from the same string passed (a film plotting this very function would lose its formula), and none of them
  // can reach a film's frame: they print only over the demo's own data.
  const demo = PTS_IN === undefined;
  const tex = TEX_IN ?? (demo ? DEMO_TEX : undefined);
  const title = TITLE_IN ?? (demo ? DEMO_TITLE : undefined);
  const xLabel = XL_IN ?? (demo ? DEMO_XLABEL : undefined);
  const yLabel = YL_IN ?? (demo ? DEMO_YLABEL : undefined);
  const pts = rows<[number, number]>(PTS_IN ?? DEMO_POINTS, 'points', 'FunctionPlot');
  if (pts.length < 2) throw new Error(`FunctionPlot draws a curve through the film's samples: at least 2, got ${pts.length}.`);
  pts.forEach((p, i) => {
    if (!Array.isArray(p) || p.length !== 2 || !p.every((v) => typeof v === 'number' && Number.isFinite(v))) {
      throw new Error(`FunctionPlot: points[${i}] must be [x, y], two finite numbers — got ${JSON.stringify(p)}.`);
    }
    if (i && !(p[0] > pts[i - 1][0])) throw new Error(`FunctionPlot: x must increase — points[${i}] is at ${p[0]}.`);
  });
  const range = (r: [number, number] | undefined, k: 0 | 1, name: string): [number, number] => {
    if (r !== undefined) {
      if (!Array.isArray(r) || r.length !== 2 || !(r[1] > r[0])) throw new Error(`FunctionPlot: \`${name}\` is [lo, hi] with hi > lo.`);
      return r;
    }
    const vs = pts.map((p) => p[k]);
    const lo = Math.min(...vs), hi = Math.max(...vs);
    if (!(hi > lo)) throw new Error(`FunctionPlot: every sample has the same ${k ? 'y' : 'x'} — pass \`${name}\`.`);
    return [lo, hi];
  };
  const [x0, x1] = range(xRange, 0, 'xRange'), [y0, y1] = range(yRange, 1, 'yRange');

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);

  const U = Math.min(W, H);
  const mx = Math.round(W * 0.07);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const KICK = Math.ceil(U * 0.028);
  const kickH = kicker ? Math.round(KICK * 1.25 + U * 0.022) : 0;
  const TITLE = Math.round(U * 0.054);
  const titleRes = title ? Math.round(TITLE * 1.1 * 2 + U * 0.015) : 0;
  const kick = useKinetic({text: kicker || ' ', w: W - 2 * mx, nowrap: true, fit: 'box',
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});
  const head = useKinetic({text: title || ' ', w: W - 2 * mx, h: titleRes, fit: 'box', maxLines: 2, wrap: 'balance',
    font: {family: DISPLAY, weight: 640, size: TITLE, minSize: Math.ceil(U * 0.034), lineHeight: 1.06, tracking: -0.015}});
  // the heading's MEASURED height once it is known: a one-line title reserved two lines left the plot a strip
  const titleH = title ? (head.layout ? Math.round(head.layout.height + U * 0.02) : titleRes) : 0;
  const TICK = Math.ceil(U * 0.028);
  const AX = Math.ceil(U * 0.03);
  const READ = Math.ceil(U * 0.04);
  const eqs = useEquations(tex ? [tex] : []);
  const eq = eqs && tex ? eqs[0] : null;
  // LANDSCAPE: the plot on the left, a column on the right for the formula and the readout, so neither is ever drawn
  // over the curve (the first render set the readout beside the rider and it sat on the curve's next swing, and the
  // y axis's name sat on the curve's first value). PORTRAIT / 4:5: the formula above the plot, the readout under it —
  // a SQUARE frame takes the column too: stacked, the heading, formula, axis names and readout left a 1:1 plot 98 px.
  const side = W >= H * 0.95;
  const head0 = zoneTop + kickH + titleH + U * 0.03;
  const colW = side ? Math.round((W - 2 * mx) * 0.3) : 0;
  const yLabH = yLabel ? AX * 1.7 : 0;
  // the formula's em: as large as its room allows (the column, or the full width), under a ceiling
  const eqRoomW = side ? colW : (W - 2 * mx) * 0.9;
  const eqEm = eq ? Math.min(U * 0.075, (eqRoomW * 1000) / Math.max(1, eq.ink[2] - eq.ink[0])) : 0;
  if (eq && eqEm < U * 0.03) {
    throw new Error(`FunctionPlot: the formula only fits at ${Math.round(eqEm)} px an em (floor ${Math.round(U * 0.03)}) ` +
      '— write a shorter `tex` (the function, not its derivation).');
  }
  const eqH = eq ? ((eq.ink[3] - eq.ink[1]) * eqEm) / 1000 : 0;
  const padL = Math.round(TICK * 0.62 * Math.max(...[y0, y1].map((v) => figureText(v).length)) + U * 0.03);
  const plotTop = head0 + (side ? 0 : (eq ? eqH + U * 0.04 : 0)) + yLabH;
  const plotBot = zoneBot - TICK * 1.4 - (xLabel ? AX * 1.6 : 0) - (side ? 0 : READ * 1.35 * 2 + U * 0.02) - U * 0.02;
  const plot = {l: mx + padL, r: W - mx - (side ? colW + U * 0.06 : 0), t: plotTop, b: plotBot};
  if (plot.b - plot.t < U * 0.2) throw new Error('FunctionPlot: no room for the plot under the heading at this aspect.');
  const X = (v: number) => plot.l + ((v - x0) / (x1 - x0)) * (plot.r - plot.l);
  const Y = (v: number) => plot.b - ((v - y0) / (y1 - y0)) * (plot.b - plot.t);

  // unique per mount: a seam mounts two beats at once, and two clipPaths with one id clip each other's curve
  const clipId = `fp${React.useId().replace(/[^A-Za-z0-9]/g, '')}`;

  // ── the timeline ─────────────────────────────────────────────────────────────────────────────────────────
  const axes = easeOutCubic(clamp01(seg(t, 0.06, 0.24)));
  const trace = easeInOutCubic(clamp01(seg(t, 0.2, 0.5)));
  const ride = easeInOutCubic(clamp01(seg(t, 0.5, 0.9)));
  // the curve, clipped to the plot (a film's yRange may be narrower than its data)
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(2)} ${Y(p[1]).toFixed(2)}`).join('');
  // the rider: by arc length along the drawn polyline, so it moves at an even pace whatever the sample spacing
  const seglen: number[] = [0];
  for (let i = 1; i < pts.length; i++) {
    seglen.push(seglen[i - 1] + Math.hypot(X(pts[i][0]) - X(pts[i - 1][0]), Y(pts[i][1]) - Y(pts[i - 1][1])));
  }
  const L = seglen[seglen.length - 1];
  const s = ride * L;
  let k = 0;
  while (k < pts.length - 2 && seglen[k + 1] < s) k++;
  const f = seglen[k + 1] > seglen[k] ? (s - seglen[k]) / (seglen[k + 1] - seglen[k]) : 0;
  const rx = X(pts[k][0]) + (X(pts[k + 1][0]) - X(pts[k][0])) * f;
  const ry = Y(pts[k][1]) + (Y(pts[k + 1][1]) - Y(pts[k][1])) * f;
  const shown = f >= 1 - 1e-9 ? k + 1 : k;                // the last sample the rider has reached
  const rideOn = clamp01(seg(t, 0.48, 0.54));
  const xText = `${xName} = ${figureText(pts[shown][0])}`, yText = `${yName} = ${figureText(pts[shown][1])}`;
  // the formula: top of the column, or centred over the plot
  let eqDraw = null as React.ReactNode;
  if (eq) {
    const sc = eqEm / 1000, ew = (eq.ink[2] - eq.ink[0]) * sc;
    const pl = side ? {x: plot.r + U * 0.06 - eq.ink[0] * sc, y: plot.t - eq.ink[1] * sc, s: sc}
      : {x: (W - ew) / 2 - eq.ink[0] * sc, y: head0 - eq.ink[1] * sc, s: sc};
    eqDraw = <MathLayer draws={writeState(eq, pl, clamp01(seg(t, 0.1, 0.32)))} tex={eq.tex} emPx={eqEm} W={W} H={H}
      ink={FG} accent={ACC} id="formula" />;
  }
  const readTop = side ? plot.t + eqH + U * 0.06 : zoneBot - READ * 1.35 * 2 - U * 0.005;
  // the readout's size: its LONGEST line fitted to its room, counted in the faces that draw it — the mono's Latin
  // cell (0.62 em) and, for a Chinese variable name, the CJK fallback's full em (E2). Measured on the fixture, a film
  // that names its axis 「交付可验收的成果」 ran a one-line readout past a 1080 frame.
  const est = (txt: string) => Array.from(txt).reduce((a, ch) => a + (/[\u2E80-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]/.test(ch) ? 1 : 0.62), 0);
  const readRoom = side ? colW : W - 2 * mx;
  // over EVERY sample's readout, not this frame's: sized per frame it would twitch as the values change length. A name
  // too long for one line at the floor size goes over its value (the column has the height); one that does not fit
  // even then is refused — measured on the CJK fixture at 1:1, 「交付可验收的成果 = 5.95」 ran 24 px past the frame.
  const floorPx = Math.ceil(U * 0.028);
  const widest = Math.max(1, ...pts.map((p) => Math.max(est(`${xName} = ${figureText(p[0])}`), est(`${yName} = ${figureText(p[1])}`))));
  const split = readRoom / widest < floorPx;
  const widestSplit = Math.max(1, est(xName), est(yName),
    ...pts.map((p) => Math.max(est(`= ${figureText(p[0])}`), est(`= ${figureText(p[1])}`))));
  const READ_PX = Math.min(READ, readRoom / (split ? widestSplit : widest));
  if (READ_PX < floorPx || (split && !side)) {
    throw new Error(`FunctionPlot: the readout ("${xName}", "${yName}") does not fit its room at a readable size — ` +
      'name the variables shortly (x, t, 温度).');
  }
  const sw = Math.max(2, Math.round(U * 0.004));
  const zeroY = y0 < 0 && y1 > 0 ? Y(0) : null;
  const tickStyle = (o: number): React.CSSProperties => ({position: 'absolute', color: DIM, opacity: o,
    font: `500 ${TICK}px/1 ${MONO}`, whiteSpace: 'nowrap'});
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <KineticText k={kick} x={mx} y={zoneTop} color={ACC} read={false} id="kicker"
          motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.02, stagger: 0.03, dur: 0.45,
            ease: 'power3', cueKeys: ['kicker'], until: 0.2}}} />
      ) : kick.anchor}
      {title ? (
        <KineticText k={head} x={mx} y={zoneTop + kickH} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.03}, enter: {by: 'line', at: 0.04, stagger: 0.12,
            dur: 0.8, ease: 'expo', cueKeys: ['title'], until: 0.24}}} />
      ) : head.anchor}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <defs>
          <clipPath id={clipId}><rect x={plot.l} y={plot.t - sw * 2} width={plot.r - plot.l} height={plot.b - plot.t + sw * 4} /></clipPath>
        </defs>
        <path d={`M${plot.l} ${plot.t}L${plot.l} ${plot.b}L${plot.r} ${plot.b}`} fill="none" stroke={mix(DIM, BG, 0.25)}
          strokeWidth={Math.max(1.5, sw * 0.5)} {...drawOn(axes)} />
        {zeroY !== null ? (
          <path d={`M${plot.l} ${zeroY}L${plot.r} ${zeroY}`} stroke={mix(DIM, BG, 0.55)} strokeWidth={Math.max(1, sw * 0.35)}
            strokeDasharray={`${sw * 2} ${sw * 3}`} opacity={axes} />
        ) : null}
        <g clipPath={`url(#${clipId})`}>
          <path d={d} fill="none" stroke={ACC} strokeWidth={sw} strokeLinejoin="round" strokeLinecap="round"
            {...drawOn(trace)} />
        </g>
        {rideOn > 0 ? (
          <g opacity={rideOn}>
            <path d={`M${rx} ${plot.b}L${rx} ${ry}`} stroke={mix(ACC, BG, 0.5)} strokeWidth={Math.max(1, sw * 0.35)} />
            <circle cx={rx} cy={ry} r={sw * 3.2} fill={BG} stroke={ACC} strokeWidth={sw} />
            <circle cx={rx} cy={ry} r={sw * 1.2} fill={ACC} />
          </g>
        ) : null}
      </svg>
      {eqDraw}
      {/* the axes' ends: the film's numbers, as written */}
      <div style={{...tickStyle(axes), left: plot.l - padL, width: padL - U * 0.012, top: plot.t - TICK * 0.5, textAlign: 'right'}}>{figureText(y1)}</div>
      <div style={{...tickStyle(axes), left: plot.l - padL, width: padL - U * 0.012, top: plot.b - TICK * 0.5, textAlign: 'right'}}>{figureText(y0)}</div>
      <div style={{...tickStyle(axes), left: plot.l, top: plot.b + TICK * 0.4}}>{figureText(x0)}</div>
      <div style={{...tickStyle(axes), left: plot.r - U * 0.3, width: U * 0.3, top: plot.b + TICK * 0.4, textAlign: 'right'}}>{figureText(x1)}</div>
      {xLabel ? (
        <div style={{position: 'absolute', left: plot.l, right: W - plot.r, top: plot.b + TICK * 1.5, textAlign: 'center',
          color: DIM, opacity: axes, font: `500 ${AX}px/1.3 ${BODY}`}}>{xLabel}</div>
      ) : null}
      {yLabel ? (
        <div style={{position: 'absolute', left: plot.l - padL, top: plot.t - yLabH, maxWidth: plot.r - plot.l + padL,
          whiteSpace: 'nowrap', color: DIM, opacity: axes, font: `500 ${AX}px/1.3 ${BODY}`}}>{yLabel}</div>
      ) : null}
      {/* the readout: the last sample the rider reached, as the film wrote it — in the column, or under the plot */}
      {rideOn > 0 ? (
        side ? (
          <div style={{position: 'absolute', left: plot.r + U * 0.06, width: colW, top: readTop, color: FG, opacity: rideOn,
            font: `600 ${READ_PX}px/1.35 ${MONO}`, whiteSpace: 'nowrap'}}>
            {split ? (
              <>
                <div style={{color: DIM}}>{xName}</div><div>{`= ${figureText(pts[shown][0])}`}</div>
                <div style={{color: DIM}}>{yName}</div><div style={{color: ACC}}>{`= ${figureText(pts[shown][1])}`}</div>
              </>
            ) : (
              <><div>{xText}</div><div style={{color: ACC}}>{yText}</div></>
            )}
          </div>
        ) : (
          <div style={{position: 'absolute', left: mx, right: mx, top: readTop, textAlign: 'center', color: FG,
            opacity: rideOn, font: `600 ${READ_PX}px/1.35 ${MONO}`, whiteSpace: 'nowrap'}}>
            <div>{xText}</div><div style={{color: ACC}}>{yText}</div>
          </div>
        )
      ) : null}
    </AbsoluteFill>
  );
};
export default FunctionPlot;
