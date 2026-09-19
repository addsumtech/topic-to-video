// SHOT · OverlapSeparation — TWO MEASURES, ONE PAIR OF POPULATIONS. The beat this register exists for is an
// argument the library could not previously DRAW: a metric that cannot tell two populations apart, next to one
// that can. Stating it ("the two distributions overlap") is words; this draws it — the same two populations,
// scored twice, on two panels with IDENTICAL chrome, an IDENTICAL x-axis and (wherever the peaks are at all
// comparable) an IDENTICAL y-scale, so the only thing that differs is the DATA.
//
// On the failing panel the two densities sit on top of each other and the region where they are indistinguishable
// is flooded with the two hues BLENDED — the colour of "cannot attribute" — while a threshold line searches
// across and never finds a clean cut: at every position a large hatched slice of BOTH populations (each tinted in
// its own hue) is on the wrong side of it. On the separating panel there is no blended region at all, the same
// search locks onto an empty gap, and both wrong-side slices vanish.
//
// Hide the caption and the frame still says exactly one thing: "the left measure cannot tell these apart, the
// right one can." Nothing is hardcoded to the beat that commissioned it — the two measures, the two population
// labels and their mean/spread all arrive as props, so any film comparing two measures of one population pair can
// use it. Curves are exact Gaussian densities evaluated from mean/spread (no sampled points, no RNG); every
// colour comes from the DNA (dnaPalette's two categorical hues + the film's ink/ground); every position is a
// fraction of W/H, so the shot reflows and STACKS at portrait aspects.
//
// EVERY CURVE IS THE FILM'S, OR THE SHOT REFUSES. Each population used to be read as `p?.mean ?? 0.52`,
// `p?.spread ?? 0.17`, `p?.label ?? 'A'` — so a film that named its two measures and its populations but left
// out a mean or a spread got the demo's curves drawn as its own data, and a film that passed `fail` alone got
// the demo's "Execution" panel (0.82 vs 0.16, cleanly split) standing next to it as though it had measured
// that too. A density curve is a quantitative claim about a population: its position IS the mean and its
// width IS the spread. So `fail` and `pass` now come together or not at all, every population in them needs
// a `label`, a finite `mean` and a finite `spread >= 0`, and anything missing throws naming the exact path.
// The standalone demo (no props) is unchanged.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {useT, seg, clamp01, lerp, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, titleStyle} from '../runtime/layout';
import {useDNA, dnaPalette, mix} from '../runtime/dna';

export const DURATION = 150; // 5s

// The shot's OWN identity when no film provides a DNA (every token below reads `dna?.x ?? *_D0`).
const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', DIM_D0 = '#7d8a9b', LINE_D0 = '#1a2431',
  SURF_D0 = '#111823', BORD_D0 = '#22303f', A_D0 = '#37d4a6', B_D0 = '#f2b544';

export type OverlapPop = {label?: string; mean?: number; spread?: number};
export type OverlapMeasure = {label?: string; note?: string; a?: OverlapPop; b?: OverlapPop};

type Pop = {label: string; mean: number; spread: number};
type Box = {x: number; y: number; w: number; h: number};

// ── maths ────────────────────────────────────────────────────────────────────────────────────────────────────
// A density, not a histogram: equal AREA per population, so a tighter spread is genuinely taller. Both panels
// then share one y-scale (below) and the comparison stays honest.
const dens = (x: number, m: number, s: number) => Math.exp(-0.5 * ((x - m) / s) ** 2) / s;

// Fail LOUDLY on a prop that cannot be drawn, rather than silently painting a flat/NaN curve.
const finite = (v: unknown, what: string): number => {
  const n = typeof v === 'number' ? v : Number(v);
  if (!Number.isFinite(n)) throw new Error(`OverlapSeparation: ${what} must be a finite number, got ${String(v)}`);
  return n;
};

const niceStep = (raw: number) => {
  const safe = raw > 0 ? raw : 1;
  const e = Math.pow(10, Math.floor(Math.log10(safe)));
  const f = safe / e;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * e;
};

/** The threshold a real classifier would pick: where the two densities cross, searched only BETWEEN the two
 *  means (an unequal-spread pair also crosses far out in a tail, which is never the operating point). */
const crossing = (a: Pop, b: Pop): number => {
  const l = Math.min(a.mean, b.mean), r = Math.max(a.mean, b.mean);
  if (r - l < 1e-9) return l;
  let best = (l + r) / 2, bd = Infinity;
  for (let i = 0; i <= 400; i++) {
    const x = l + ((r - l) * i) / 400;
    const d = Math.abs(dens(x, a.mean, a.spread) - dens(x, b.mean, b.spread));
    if (d < bd) { bd = d; best = x; }
  }
  return best;
};

const samples = (m: number, s: number, x0: number, x1: number, n: number): [number, number][] => {
  const out: [number, number][] = [];
  for (let i = 0; i <= n; i++) { const x = x0 + ((x1 - x0) * i) / n; out.push([x, dens(x, m, s)]); }
  return out;
};

const toLine = (pts: [number, number][], sx: (v: number) => number, sy: (d: number) => number) =>
  pts.map(([x, d], i) => `${i ? 'L' : 'M'}${sx(x).toFixed(2)},${sy(d).toFixed(2)}`).join(' ');
const toArea = (pts: [number, number][], sx: (v: number) => number, sy: (d: number) => number, base: number) =>
  pts.length
    ? `${toLine(pts, sx, sy)} L${sx(pts[pts.length - 1][0]).toFixed(2)},${base.toFixed(2)} ` +
      `L${sx(pts[0][0]).toFixed(2)},${base.toFixed(2)} Z`
    : '';

// ── one measure's panel ──────────────────────────────────────────────────────────────────────────────────────
type PanelProps = {
  box: Box; uid: string; label: string; note: string; a: Pop; b: Pop;
  lo: number; hi: number; yFrac: number; ticks: number[]; fmt: (v: number) => string;
  ca: string; cb: string; muddy: string; fg: string; dim: string; line: string;
  card: string; border: string; radius: number; face: string; monoFace: string;
  labelSize: number; noteSize: number; legendSize: number; ownLegend: boolean;
  t: number; cardAt: number; growAt: [number, number]; overlapAt: number;
  sweep: {from: number; to: number; amp: number}; cutLocks: boolean; noteAt: number;
};

const Panel: React.FC<PanelProps> = ({
  box, uid, label, note, a, b, lo, hi, yFrac, ticks, fmt, ca, cb, muddy, fg, dim, line, card, border, radius,
  face, monoFace, labelSize, noteSize, legendSize, ownLegend, t, cardAt, growAt, overlapAt, sweep, cutLocks, noteAt,
}) => {
  const {w, h} = box;
  const cardIn = clamp01(seg(t, cardAt, cardAt + 0.10));
  const grow = easeOutCubic(seg(t, growAt[0], growAt[1]));
  const ovIn = clamp01(seg(t, overlapAt, overlapAt + 0.12));
  const cutIn = clamp01(seg(t, sweep.from, sweep.from + 0.07));
  const noteIn = clamp01(seg(t, noteAt, noteAt + 0.10));

  // local geometry — all fractions of the card, so it reflows at any aspect / panel size
  const plotY = h * (ownLegend ? 0.285 : 0.205);
  const plotH = h * (ownLegend ? 0.515 : 0.595);
  const plotBot = plotY + plotH;
  const x0 = w * 0.065, x1 = w * 0.935;
  const yScale = plotH * 0.92 * yFrac;          // derived HERE so the curve can never outgrow its own plot box
  const sx = (v: number) => lerp(x0, x1, (v - lo) / (hi - lo));
  const sy = (d: number) => plotBot - d * yScale * grow;

  // the threshold: it SEARCHES (a decaying swing around the true crossing) and then parks. On the separating
  // measure the same search is given a short leash and locks — motion carries "found it" vs "never finds it".
  const base = crossing(a, b);
  const u = clamp01(seg(t, sweep.from, sweep.to));
  const decay = Math.pow(1 - u, 1.6);
  const cut = Math.max(lo, Math.min(hi, base + decay * sweep.amp * Math.cos(u * Math.PI * 2.2)));

  const N = 200;
  const ptsA = samples(a.mean, a.spread, lo, hi, N);
  const ptsB = samples(b.mean, b.spread, lo, hi, N);
  const ptsI = ptsA.map(([x, d], i) => [x, Math.min(d, ptsB[i][1])] as [number, number]);
  // How much of this panel actually IS overlap. A cleanly separated pair still has a mathematically non-empty
  // intersection curve hugging zero; drawing it would lay a stray coloured line along the axis, so the blended
  // region fades in with the overlap it represents instead of being a permanent fixture.
  const pk = Math.max(1 / a.spread, 1 / b.spread);
  const ovVis = clamp01((Math.max(...ptsI.map((p) => p[1])) / pk - 0.012) / 0.04);
  // whichever population sits HIGHER on the axis is the one a threshold puts on the right — derived from the
  // data, never assumed, so a film may hand the populations in either order.
  const aRight = a.mean >= b.mean;
  const wrongA = aRight ? samples(a.mean, a.spread, lo, cut, 90) : samples(a.mean, a.spread, cut, hi, 90);
  const wrongB = aRight ? samples(b.mean, b.spread, cut, hi, 90) : samples(b.mean, b.spread, lo, cut, 90);

  const hidA = `ovsHa${uid}`, hidB = `ovsHb${uid}`;
  const cx = sx(cut);

  return (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: w, height: h, background: card,
      border: `1px solid ${border}`, borderRadius: radius, overflow: 'hidden', opacity: cardIn,
      transform: `translateY(${(1 - cardIn) * 12}px)`}}>

      {/* measure name — the panel's only claim about itself */}
      <div style={{position: 'absolute', left: w * 0.065, right: w * 0.05, top: h * 0.05, color: fg,
        font: `600 ${labelSize}px/1.15 ${face}`, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
        {label}
      </div>

      {/* per-panel legend — only when the two panels do NOT score the same named populations */}
      {ownLegend ? (
        <div style={{position: 'absolute', left: w * 0.065, right: w * 0.05, top: h * 0.05 + labelSize * 1.35,
          display: 'flex', gap: w * 0.05, color: dim, font: `500 ${legendSize}px/1 ${face}`, whiteSpace: 'nowrap'}}>
          {[[ca, a.label], [cb, b.label]].map(([c, l], i) => (
            <span key={i} style={{display: 'flex', alignItems: 'center', gap: 8}}>
              <span style={{width: legendSize * 0.8, height: legendSize * 0.8, borderRadius: 3, background: c}} />{l}
            </span>
          ))}
        </div>
      ) : null}

      <svg width={w} height={h} style={{position: 'absolute', inset: 0}}>
        <defs>
          {/* LINE-ONLY hatches: they tint the wrong-side slice with its population's hue without painting a solid
              block. A solid block read as "green on the left, amber on the right" — i.e. as SEPARATION, the exact
              opposite of what the failing panel means. */}
          {[[hidA, ca], [hidB, cb]].map(([id, c]) => (
            <pattern key={id} id={id} width={11} height={11} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1={0} y1={0} x2={0} y2={11} stroke={c} strokeWidth={2.6} />
            </pattern>
          ))}
        </defs>

        {/* the score axis, ruled at the ticks — IDENTICAL in both panels, which is what makes them comparable */}
        {ticks.map((v, i) => (
          <line key={i} x1={sx(v)} y1={plotY} x2={sx(v)} y2={plotBot} stroke={line} strokeWidth={1} opacity={0.9} />
        ))}

        {/* the two populations */}
        <path d={toArea(ptsA, sx, sy, plotBot)} fill={ca} opacity={0.26 * grow} />
        <path d={toArea(ptsB, sx, sy, plotBot)} fill={cb} opacity={0.26 * grow} />

        {/* WHERE THE TWO ARE INDISTINGUISHABLE — the two hues blended into one colour you cannot attribute */}
        <path d={toArea(ptsI, sx, sy, plotBot)} fill={muddy} opacity={0.62 * ovIn * ovVis} />
        <path d={toLine(ptsI, sx, sy)} fill="none" stroke={muddy} strokeWidth={2} opacity={0.9 * ovIn * ovVis} />

        {/* what THIS threshold gets wrong: the slice of each population that lands on the other side of the cut */}
        <path d={toArea(wrongA, sx, sy, plotBot)} fill={`url(#${hidA})`} opacity={0.85 * cutIn} />
        <path d={toArea(wrongB, sx, sy, plotBot)} fill={`url(#${hidB})`} opacity={0.85 * cutIn} />

        <path d={toLine(ptsA, sx, sy)} fill="none" stroke={ca} strokeWidth={3} opacity={grow} strokeLinejoin="round" />
        <path d={toLine(ptsB, sx, sy)} fill="none" stroke={cb} strokeWidth={3} opacity={grow} strokeLinejoin="round" />

        {/* the threshold */}
        <g opacity={cutIn}>
          {cutLocks ? <line x1={cx} y1={plotY} x2={cx} y2={plotBot} stroke={fg} strokeWidth={9} opacity={0.13} /> : null}
          <line x1={cx} y1={plotY} x2={cx} y2={plotBot} stroke={fg} strokeWidth={2.2}
            strokeDasharray={cutLocks ? undefined : '9 8'} opacity={cutLocks ? 0.95 : 0.55} />
          <path d={`M${cx - 9},${plotBot} L${cx + 9},${plotBot} L${cx},${plotBot - 14} Z`} fill={fg}
            opacity={cutLocks ? 0.95 : 0.55} />
        </g>

        <line x1={x0} y1={plotBot} x2={x1} y2={plotBot} stroke={dim} strokeWidth={1.5} opacity={0.65} />
        {ticks.map((v, i) => (
          <text key={i} x={sx(v)} y={plotBot + h * 0.052} textAnchor="middle" fill={dim}
            fontSize={Math.round(Math.min(20, h * 0.030))} fontFamily={monoFace} opacity={0.8 * cardIn}>{fmt(v)}</text>
        ))}
      </svg>

      {/* the panel's finding, in the film's own words */}
      <div style={{position: 'absolute', left: w * 0.065, right: w * 0.065, top: plotBot + h * 0.09, color: fg,
        font: `500 ${noteSize}px/1.3 ${face}`, opacity: 0.9 * noteIn, transform: `translateY(${(1 - noteIn) * 8}px)`}}>
        {note}
      </div>
    </div>
  );
};

// ── the shot ─────────────────────────────────────────────────────────────────────────────────────────────────
// The standalone demo's two measures. Module constants so the shot can tell "the film passed nothing" (the
// demo, by identity) from "the film passed one of the two" (refused below) — a partial film must never be
// completed with the demo's curves.
const DEMO_FAIL: OverlapMeasure = {label: 'Surface similarity', note: 'the two populations sit on top of each other',
  a: {label: 'passes', mean: 0.52, spread: 0.17}, b: {label: 'fails', mean: 0.48, spread: 0.17}};
const DEMO_PASS: OverlapMeasure = {label: 'Execution', note: 'same cases, cleanly split',
  a: {label: 'passes', mean: 0.82, spread: 0.09}, b: {label: 'fails', mean: 0.16, spread: 0.09}};

export const OverlapSeparation: React.FC<{
  kicker?: string; title?: string; fail?: OverlapMeasure; pass?: OverlapMeasure; domain?: [number, number];
}> = ({
  kicker: KICKER = '',
  title: TITLE = 'Two measures, one set of cases',
  fail: FAIL = DEMO_FAIL,
  pass: PASS = DEMO_PASS,
  domain: DOMAIN,
} = {}) => {
  if ((FAIL === DEMO_FAIL) !== (PASS === DEMO_PASS)) {
    throw new Error(
      `OverlapSeparation needs BOTH measures: \`${FAIL === DEMO_FAIL ? 'fail' : 'pass'}\` is missing. The shot ` +
      'is the comparison — the same two populations scored by a measure that cannot separate them (`fail`) and ' +
      'by one that can (`pass`) — and drawing the demo\'s curves in the missing panel would present numbers ' +
      'nobody measured. Pass `fail: {label, note, a: {label, mean, spread}, b: {…}}` and `pass: {…}`.');
  }
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const portrait = W < H;

  // COLOUR — categorical hues from the DNA (dnaPalette stays inside the film's two accents), chrome from its
  // ink/ground. The overlap hue is literally the two population hues blended: the colour of "cannot attribute".
  // Nothing else in the frame may wear either categorical hue, or it reads as one of the populations.
  const pal = dnaPalette(dna, 2);
  const CA = pal?.[0] ?? A_D0, CB = pal?.[1] ?? B_D0;
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, LINE = dna?.line ?? LINE_D0;
  const BG = dna?.bg ?? BG_D0, SURF = dna?.surface ?? SURF_D0, BORD = dna?.surfaceBorder ?? BORD_D0;
  const MUDDY = mix(CA, CB, 0.5);
  const CARD = mix(BG, SURF, 0.85);
  const RADIUS = dna?.radius ?? 8;
  const face = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const dispFace = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';
  const monoFace = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';

  // DATA — resolved once, asserted finite, with a spread floor so a zero-variance population still draws.
  // Nothing is filled in: the old `p?.mean ?? 0.52` / `p?.label ?? 'A'` drew the demo's curve under the film's
  // name whenever a piece was left out (see the header). A missing piece names its own path and throws.
  const D = React.useMemo(() => {
    const rd = (p: OverlapPop | undefined | null, what: string): Pop => {
      if (p == null || typeof p !== 'object') {
        throw new Error(`OverlapSeparation: \`${what}\` is missing. Each measure scores the SAME two populations — ` +
          `pass \`${what}: {label, mean, spread}\` with the population's real mean and spread on the shared axis.`);
      }
      const label = String(p.label ?? '').trim();
      if (!label) {
        throw new Error(`OverlapSeparation: \`${what}.label\` is missing — the legend names which curve is which ` +
          'population, and an invented "A"/"B" tells the viewer nothing.');
      }
      if (p.mean == null || p.spread == null) {
        throw new Error(`OverlapSeparation: \`${what}\` ("${label}") needs both \`mean\` and \`spread\` — the curve's ` +
          `position IS its mean and its width IS its spread, so neither can be assumed (got mean=${String(p.mean)}, ` +
          `spread=${String(p.spread)}).`);
      }
      const spread = finite(p.spread, `${what}.spread`);
      if (spread < 0) throw new Error(`OverlapSeparation: ${what}.spread must be >= 0, got ${spread}`);
      return {label, mean: finite(p.mean, `${what}.mean`), spread};
    };
    const fa = rd(FAIL?.a, 'fail.a'), fb = rd(FAIL?.b, 'fail.b');
    const pa = rd(PASS?.a, 'pass.a'), pb = rd(PASS?.b, 'pass.b');
    const all = [fa, fb, pa, pb];
    const ms = all.map((p) => p.mean), ss = all.map((p) => p.spread);
    const sMax = Math.max(...ss), mSpan = Math.max(...ms) - Math.min(...ms);
    const unit = sMax > 0 ? sMax : mSpan > 0 ? mSpan / 6 : 1;
    all.forEach((p) => { p.spread = Math.max(p.spread, unit * 0.02); });

    // x-DOMAIN — one axis for both panels (this is the honesty of the comparison). A normalised 0..1 score keeps
    // its natural bounds; anything else gets a padded, round-numbered range.
    let lo: number, hi: number;
    if (DOMAIN && Number.isFinite(DOMAIN[0]) && Number.isFinite(DOMAIN[1]) && DOMAIN[1] > DOMAIN[0]) {
      [lo, hi] = DOMAIN;
    } else if (ms.every((m) => m >= 0 && m <= 1) && all.every((p) => p.spread <= 0.5)) {
      lo = 0; hi = 1;
    } else {
      const lo0 = Math.min(...all.map((p) => p.mean - 3 * p.spread));
      const hi0 = Math.max(...all.map((p) => p.mean + 3 * p.spread));
      const st = niceStep((hi0 - lo0 || Math.abs(hi0) || 1) / 4);
      lo = Math.floor(lo0 / st) * st; hi = Math.ceil(hi0 / st) * st;
      if (hi - lo < st) hi = lo + st;
    }
    const step = (hi - lo) / 4;
    const dec = step >= 10 ? 0 : step >= 1 ? 1 : step >= 0.1 ? 2 : 3;
    const ticks = [0, 1, 2, 3, 4].map((i) => lo + step * i);

    // ONE y-scale for both panels wherever the peaks are comparable (they are, for any realistic pair), so the
    // curves are directly readable against each other. Only an extreme ratio trips the 45% legibility floor.
    const peak = (p: Pop, q: Pop) => Math.max(1 / p.spread, 1 / q.spread);
    const pkF = peak(fa, fb), pkP = peak(pa, pb), pkAll = Math.max(pkF, pkP);
    const yFrac = (pk: number) => Math.max(pk / pkAll, 0.45) / pk;

    return {fa, fb, pa, pb, lo, hi, ticks, fmt: (v: number) => v.toFixed(dec), yF: yFrac(pkF), yP: yFrac(pkP)};
  }, [FAIL, PASS, DOMAIN]);

  // TYPE — every string is width-fitted, and peer strings share ONE size so neither panel reads as the senior of
  // the two (real copy is Chinese and far longer than the English defaults).
  const titleSize = React.useMemo(() => (String(TITLE || '').trim()
    ? fitTextOnNLines({text: String(TITLE), maxLines: 1, maxBoxWidth: W * 0.84, fontFamily: dispFace,
      fontWeight: 700, maxFontSize: 40}).fontSize : 40), [TITLE, W, dispFace]);
  const kickerSize = React.useMemo(() => (String(KICKER || '').trim()
    ? fitTextOnNLines({text: String(KICKER), maxLines: 1, maxBoxWidth: W * 0.82, fontFamily: monoFace,
      fontWeight: 600, maxFontSize: Math.round(Math.min(26, W * 0.014))}).fontSize : 22), [KICKER, W, monoFace]);
  const legendSize = React.useMemo(() => Math.min(...[D.fa.label, D.fb.label].map((s) => (String(s).trim()
    ? fitTextOnNLines({text: String(s), maxLines: 1, maxBoxWidth: W * 0.3, fontFamily: face,
      fontWeight: 600, maxFontSize: Math.round(Math.min(28, W * 0.0155))}).fontSize : 28))), [D, W, face]);

  const shared = D.fa.label === D.pa.label && D.fb.label === D.pb.label;

  // BOXES — side by side in landscape, STACKED in portrait (a two-column chart is unreadable at 1080 wide).
  const top = CONTENT_TOP, bot = contentBottom(W, H) - 16;   // 16px of air above the burned-caption band
  const legendH = shared ? legendSize * 1.5 + 16 : 0;
  const boxTop = top + legendH;
  const mx = portrait ? W * 0.07 : W * 0.055;
  const zoneW = W - 2 * mx, zoneH = bot - boxTop;
  const gap = portrait ? Math.max(24, zoneH * 0.035) : W * 0.032;
  const bw = portrait ? zoneW : (zoneW - gap) / 2;
  const bh = portrait ? (zoneH - gap) / 2 : zoneH;
  const boxF: Box = {x: mx, y: boxTop, w: bw, h: bh};
  const boxP: Box = portrait ? {x: mx, y: boxTop + bh + gap, w: bw, h: bh} : {x: mx + bw + gap, y: boxTop, w: bw, h: bh};

  const labelSize = React.useMemo(() => Math.min(...[FAIL?.label, PASS?.label].map((s) => (String(s ?? '').trim()
    ? fitTextOnNLines({text: String(s), maxLines: 1, maxBoxWidth: bw * 0.87, fontFamily: face,
      fontWeight: 600, maxFontSize: Math.round(Math.min(36, bh * 0.052))}).fontSize
    : Math.round(Math.min(36, bh * 0.052))))), [FAIL, PASS, bw, bh, face]);
  const noteSize = React.useMemo(() => Math.min(...[FAIL?.note, PASS?.note].map((s) => (String(s ?? '').trim()
    ? fitTextOnNLines({text: String(s), maxLines: 2, maxBoxWidth: bw * 0.87, fontFamily: face,
      fontWeight: 500, maxFontSize: Math.round(Math.min(24, bh * 0.036))}).fontSize
    : Math.round(Math.min(24, bh * 0.036))))), [FAIL, PASS, bw, bh, face]);

  const headIn = easeOutCubic(seg(t, 0.0, 0.14));
  const legIn = clamp01(seg(t, 0.08, 0.22));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 110% at 50% 0%, #13202c, #080d13 74%)',
      color: FG, overflow: 'hidden'}}>

      {KICKER ? (
        <div style={{position: 'absolute', top: 48, left: 0, right: 0, textAlign: 'center', color: DIM,
          opacity: headIn, font: `600 ${kickerSize}px/1.2 ${monoFace}`,
          letterSpacing: dna?.labelSpacing ?? '0.08em', whiteSpace: 'nowrap'}}>{KICKER}</div>
      ) : null}

      <div style={{...titleStyle, color: FG, opacity: headIn, font: `700 ${titleSize}px/1.1 ${dispFace}`,
        transform: `translateY(${(1 - headIn) * -8}px)`, whiteSpace: 'nowrap'}}>{TITLE}</div>

      {/* ONE legend for BOTH panels — the statement that the same two populations are being scored twice */}
      {shared ? (
        <div style={{position: 'absolute', top: top + 4, left: 0, right: 0, display: 'flex', justifyContent: 'center',
          alignItems: 'center', gap: W * 0.04, opacity: legIn}}>
          {[[CA, D.fa.label], [CB, D.fb.label]].map(([c, l], i) => (
            <span key={i} style={{display: 'flex', alignItems: 'center', gap: 10, color: FG,
              font: `600 ${legendSize}px/1 ${face}`, whiteSpace: 'nowrap'}}>
              <span style={{width: legendSize * 0.82, height: legendSize * 0.82, borderRadius: 3, background: c}} />{l}
            </span>
          ))}
        </div>
      ) : null}

      <Panel box={boxF} uid="f" label={String(FAIL?.label ?? '')} note={String(FAIL?.note ?? '')}
        a={D.fa} b={D.fb} lo={D.lo} hi={D.hi} yFrac={D.yF} ticks={D.ticks} fmt={D.fmt}
        ca={CA} cb={CB} muddy={MUDDY} fg={FG} dim={DIM} line={LINE} card={CARD} border={BORD} radius={RADIUS}
        face={face} monoFace={monoFace} labelSize={labelSize} noteSize={noteSize} legendSize={legendSize}
        ownLegend={!shared} t={t} cardAt={0.0} growAt={[0.06, 0.28]} overlapAt={0.26}
        sweep={{from: 0.32, to: 0.62, amp: (D.hi - D.lo) * 0.3}} cutLocks={false} noteAt={0.40} />

      <Panel box={boxP} uid="p" label={String(PASS?.label ?? '')} note={String(PASS?.note ?? '')}
        a={D.pa} b={D.pb} lo={D.lo} hi={D.hi} yFrac={D.yP} ticks={D.ticks} fmt={D.fmt}
        ca={CA} cb={CB} muddy={MUDDY} fg={FG} dim={DIM} line={LINE} card={CARD} border={BORD} radius={RADIUS}
        face={face} monoFace={monoFace} labelSize={labelSize} noteSize={noteSize} legendSize={legendSize}
        ownLegend={!shared} t={t} cardAt={0.04} growAt={[0.36, 0.56]} overlapAt={0.56}
        sweep={{from: 0.56, to: 0.72, amp: (D.hi - D.lo) * 0.12}} cutLocks noteAt={0.70} />
    </AbsoluteFill>
  );
};
export default OverlapSeparation;
