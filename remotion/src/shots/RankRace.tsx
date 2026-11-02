// SHOT · Rank Race — A RANKING OVER TIME: the film's series as horizontal bars, stepping period by period through the
// values the film gives — each period HELD long enough to read with every figure exactly as written, each move
// between two periods a continuous slide in which bars grow, shrink and overtake — with the period itself on a
// timeline the playhead walks.
//
// WHAT IT ARGUES. Who led WHEN, and when the order changed: the overtakes are the data, because every position on
// screen comes from the film's values at a given period or from a straight line between two of them. Unlike ChartRace
// (one final ranking whose mid-race overtakes are staging from `delay`), nothing here is staged. Not for a single
// period (ChartRace / PhysicsStack), nor one quantity moving (FlowCounter).
//
// FIGURES. At a hold every figure is the film's string (`display`, else the value as written plus `unit`). During a
// move a figure counts between the two given values in the target's own written form; a series whose two strings are
// not each one number in the same form shows the arriving string. Values are never rounded, and a value that is not a
// number ≥ 0 throws. The bar scale follows the CURRENT leader, eased, so a race whose total grows tenfold stays legible.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic, lerp} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, TITLE_Y} from '../runtime/layout';
import {useDNA, readableOn, dimOn, mix, dnaPalette, contrastOf} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {hasCJK} from '../runtime/cjkType';
import {parseFigure, figureText, Figure} from '../runtime/figure';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {useLabelWidths} from '../runtime/labelWidths';
import {useGlide} from '../runtime/glide';

export const DURATION = 270; // 9s
export const MAX_SERIES = 12, MAX_PERIODS = 8, MAX_SHOWN = 8;

type SeriesIn = {label?: string; values?: number[]; display?: string[]};
const BG_D0 = '#080a11', FG_D0 = '#eef1f7', DIM_D0 = '#8f98ab';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff', '#4dd0e1', '#a3e635', '#fb7185', '#facc15', '#60a5fa', '#f472b6', '#34d399'];
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// Placeholder copy: series and periods named by role; the values only exercise an overtake and describe nothing.
const DEMO_PERIODS = ['first', 'second', 'third'];
const DEMO_SERIES: SeriesIn[] = [{label: 'series one', values: [40, 52, 58]}, {label: 'series two', values: [55, 50, 47]},
  {label: 'series three', values: [20, 41, 66]}, {label: 'series four', values: [30, 33, 35]}];

const formatAs = (fig: Figure, v: number): string => {
  let body = Math.abs(v).toFixed(fig.decimals);
  if (fig.grouped) {
    const [i, d] = body.split('.');
    body = i.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (d != null ? '.' + d : '');
  }
  return `${fig.prefix}${v < 0 ? '-' : ''}${body}${fig.suffix}`;
};

export const RankRace: React.FC<{
  title?: string;
  /** 2-8 period labels, in time order ("2000", "Q3", "第一年") — printed as written, never counted through */
  periods?: string[];
  /** 2-12 series: `label`, one `value` per period (numbers ≥ 0, one unit), optional `display` per period */
  series?: SeriesIn[];
  unit?: string;
  /** how many bars are on screen (2-8); the rest wait below the last and enter when they rise into it */
  show?: number;
  note?: string;
}> = ({title = '', periods: periodsIn = DEMO_PERIODS, series: seriesIn = DEMO_SERIES, unit = '', show: showIn, note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const S = 'RankRace';
  if ((periodsIn === DEMO_PERIODS) !== (seriesIn === DEMO_SERIES)) {
    throw new Error(`RankRace: pass \`periods\` and \`series\` together — one without the other would be drawn against the demo's.`);
  }
  const PER = rows<string>(periodsIn, 'periods', S).map((p) => String(p ?? '').trim());
  const SER = rows<SeriesIn>(seriesIn, 'series', S);
  const P = PER.length, N = SER.length;
  if (P < 2 || P > MAX_PERIODS) throw new Error(`${S}: needs 2-${MAX_PERIODS} \`periods\` (got ${P}); one period is not a race — use ChartRace.`);
  if (N < 2 || N > MAX_SERIES) throw new Error(`${S}: needs 2-${MAX_SERIES} \`series\` (got ${N}).`);
  if (PER.some((p) => !p)) throw new Error(`${S}: every period needs a label.`);
  const series = SER.map((s, i) => {
    const label = String(s?.label ?? '').trim();
    if (!label) throw new Error(`${S}: series ${i + 1} has no \`label\`.`);
    const vals = rows<number>(s?.values, `series[${i}].values`, S);
    if (vals.length !== P) throw new Error(`${S}: ${JSON.stringify(label)} has ${vals.length} values for ${P} periods — one per period, no gaps filled in.`);
    vals.forEach((v, j) => {
      if (typeof v !== 'number' || !Number.isFinite(v) || v < 0) {
        throw new Error(`${S}: ${JSON.stringify(label)} at ${PER[j]} needs a number ≥ 0, got ${JSON.stringify(v)}. A bar is drawn from it.`);
      }
    });
    const disp = s?.display == null ? null : rows<string>(s.display, `series[${i}].display`, S).map(figureText);
    if (disp && disp.length !== P) throw new Error(`${S}: ${JSON.stringify(label)}'s \`display\` needs one string per period.`);
    const text = vals.map((v, j) => (disp ? disp[j] : figureText(v) + unit));
    return {i, label, vals, text, figs: text.map(parseFigure)};
  });
  const show = Math.max(2, Math.min(MAX_SHOWN, N, showIn ?? MAX_SHOWN));

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);
  // @positional: a series' hue only tells it from the others; it encodes no quantity, rank or status
  const TONES = dnaPalette(dna, Math.max(3, N)) ?? TONES0;

  // ── the timeline: hold, move, hold … ──────────────────────────────────────────────────────────────────
  const A = 0.08, B = 0.9, HOLD = 0.85, MOVE = 1;
  const total = P * HOLD + (P - 1) * MOVE;
  const u = seg(t, A, B) * total;
  let k0 = P - 1, q = 0;
  {
    let acc = 0;
    for (let k = 0; k < P; k++) {
      if (u < acc + HOLD || k === P - 1) { k0 = k; q = 0; break; }
      acc += HOLD;
      if (u < acc + MOVE) { k0 = k; q = easeInOutCubic((u - acc) / MOVE); break; }
      acc += MOVE;
    }
  }
  const k1 = Math.min(P - 1, k0 + 1);
  const moving = q > 0 && q < 1;
  const cur = series.map((s) => lerp(s.vals[k0], s.vals[k1], q));
  const rankAt = (vals: number[]) => vals.map((v, i) => vals.reduce((a, o, j) => a + (o > v || (o === v && j < i) ? 1 : 0), 0));
  const r0 = rankAt(series.map((s) => s.vals[k0])), r1 = rankAt(series.map((s) => s.vals[k1]));
  // a bar's slot: the exact rank at a hold; during a move, a soft rank that follows the overtakes as they happen
  const maxCur = Math.max(1e-9, ...cur);
  const sig = (z: number) => 1 / (1 + Math.exp(-z));
  const slot = series.map((s, i) => {
    if (!moving) return q >= 1 ? r1[i] : r0[i];
    const soft = cur.reduce((a, o, j) => (j === i ? a : a + sig(((o - cur[i]) / maxCur) * 40 + (r1[j] < r1[i] ? 2 : -2))), 0);
    const exact = lerp(r0[i], r1[i], q);
    return lerp(soft, exact, Math.pow(q, 3));   // lands exactly on the arriving ranking
  });
  // the scale follows the leader, eased between the two periods' leaders
  const scaleMax = lerp(Math.max(...series.map((s) => s.vals[k0])), Math.max(...series.map((s) => s.vals[k1])), q) || 1;

  // ── geometry ─────────────────────────────────────────────────────────────────────────────────────────
  const U = Math.min(W, H);
  const portrait = W < H;
  const zTop = CONTENT_TOP + Math.round(U * 0.01);
  const noteH = note ? Math.round(U * 0.05) : 0;
  const lineH = Math.round(U * 0.12);
  const zBot = contentBottom(W, H) - noteH - lineH;
  const rowH = (zBot - zTop) / show;
  const barH = Math.round(rowH * 0.64);
  const lblPx = Math.round(Math.min(rowH * 0.36, U * (portrait ? 0.034 : 0.03)));
  const valPx = Math.round(lblPx * 0.95);
  const lw = useLabelWidths(series.map((s) => s.label), BODY, 600, lblPx);
  const vw = useLabelWidths(series.flatMap((s) => s.text), MONO, 600, valPx);
  const measured = Boolean(lw.widths && vw.widths);
  const gap = Math.round(U * 0.016);
  const labW = Math.min(W * (portrait ? 0.34 : 0.26), Math.max(0, ...(lw.widths ?? [0])));
  const x0 = Math.round(W * 0.05 + labW + gap);
  const valW = Math.max(0, ...(vw.widths ?? [0])) * 1.04;
  const barMax = Math.max(W * 0.2, W * 0.95 - x0 - gap - valW);
  if (measured && (lw.widths ?? []).some((w) => w > labW + 0.5)) {
    throw new Error(`${S}: a series label is wider than the label column (${Math.round(labW)}px at ${lblPx}px type) — shorten it.`);
  }

  const titleK = useKinetic({text: title || ' ', w: Math.round(W * 0.84), nowrap: true, fit: 'box',
    font: {family: DISPLAY, weight: 640, size: Math.round(U * 0.046), minSize: Math.round(U * 0.03), lineHeight: 1.1,
      tracking: hasCJK(title) ? 0 : -0.015}});
  const noteK = useKinetic({text: note || ' ', w: Math.round(W * 0.84), fit: 'box', maxLines: 2, h: noteH,
    font: {family: MONO, weight: 500, size: Math.round(U * 0.021), minSize: Math.round(U * 0.017), lineHeight: 1.3}});
  const perPx = Math.round(U * 0.024);
  const pw = useLabelWidths(PER, MONO, 600, perPx);

  const intro = easeOutCubic(seg(t, 0.02, 0.1));
  // the period timeline: ticks for every period, the playhead between them
  const tlY = zBot + Math.round(lineH * 0.55), tlX0 = W * 0.05, tlX1 = W * 0.95;
  const tickX = (k: number) => tlX0 + ((tlX1 - tlX0) * k) / (P - 1);
  const head = tickX(k0 + q);
  // every period label is printed when all of them fit side by side; otherwise the CURRENT one always, and the first and
  // last only where they clear it (long period names laid side by side overlapped — cjk_type_qa found the pair)
  const perBox = (k: number) => {
    const w = pw.widths![k];
    const left = Math.max(tlX0, Math.min(tlX1 - w, tickX(k) - w / 2));
    return [left, left + w];
  };
  const perFits = pw.widths ? pw.widths.every((_, k) => k === 0 || perBox(k)[0] > perBox(k - 1)[1] + gap) : false;
  const curK = !moving ? (q >= 1 ? k1 : k0) : -1;
  const perShown = (() => {
    if (!pw.widths) return [] as number[];
    if (perFits) return PER.map((_, k) => k);
    const out: number[] = curK >= 0 ? [curK] : [];
    for (const k of [0, P - 1]) {
      if (out.includes(k)) continue;
      const [a, b] = perBox(k);
      if (out.every((o) => b + gap < perBox(o)[0] || a > perBox(o)[1] + gap)) out.push(k);
    }
    return out;
  })();

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(120% 100% at 30% 20%, ${mix(BG, '#2b3a66', 0.14)}, ${BG} 72%)`, overflow: 'hidden'}}>
      {lw.anchor}{vw.anchor}{pw.anchor}
      {measured && series.map((s, i) => {
        const sl = slot[i];
        const y = zTop + sl * rowH + (rowH - barH) / 2;
        const vis = clamp01(show - sl) * intro;   // below the last shown slot it fades out of the list
        if (vis <= 0.001) return null;
        const bw = Math.max(2, (cur[i] / scaleMax) * barMax);
        const tone = TONES[i % TONES.length];
        const fA = s.figs[k0], fB = s.figs[k1];
        const text = !moving ? (q >= 1 ? s.text[k1] : s.text[k0])
          : (fA.num != null && fB.num != null && fA.prefix === fB.prefix && fA.suffix === fB.suffix)
            ? formatAs(fB.decimals >= fA.decimals ? fB : fA, cur[i]) : s.text[k1];
        const lead = !moving && (q >= 1 ? r1[i] : r0[i]) === 0;
        return (
          <div key={i} style={{position: 'absolute', left: 0, top: 0, width: W, height: barH, opacity: vis,
            transform: glide(`translateY(${y}px)`, true)}}>
            <div style={{position: 'absolute', right: W - x0 + gap, top: 0, height: barH, display: 'flex', alignItems: 'center',
              color: FG, font: `600 ${lblPx}px/1.1 ${BODY}`, whiteSpace: 'nowrap'}}>{s.label}</div>
            <div style={{position: 'absolute', left: x0, top: 0, width: bw, height: barH, borderRadius: Math.round(barH * 0.18),
              background: `linear-gradient(90deg, ${mix(tone, BG, 0.25)}, ${tone})`,
              boxShadow: lead ? `0 0 ${Math.round(U * 0.02)}px ${tone}66` : 'none'}} />
            <div style={{position: 'absolute', left: 0, top: 0, height: barH, display: 'flex', alignItems: 'center',
              transform: glide(`translateX(${x0 + bw + gap}px)`, true), whiteSpace: 'nowrap',
              color: contrastOf(tone, BG) >= 4.5 ? tone : FG, font: `600 ${valPx}px/1 ${MONO}`, fontVariantNumeric: 'tabular-nums'}}>{text}</div>
          </div>
        );
      })}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: intro}}>
        <line x1={tlX0} y1={tlY} x2={tlX1} y2={tlY} stroke={mix(BG, FG, 0.25)} strokeWidth={2} />
        <line x1={tlX0} y1={tlY} x2={head} y2={tlY} stroke={FG} strokeWidth={3} />
        {PER.map((_, k) => <circle key={k} cx={tickX(k)} cy={tlY} r={U * 0.006} fill={k <= k0 + (q >= 1 ? 1 : 0) ? FG : BG} stroke={FG} strokeWidth={2} />)}
        <circle cx={head} cy={tlY} r={U * 0.009} fill={FG} />
      </svg>
      {pw.widths && PER.map((p, k) => {
        const current = curK === k;
        if (!perShown.includes(k)) return null;
        const w = pw.widths![k];
        const left = perBox(k)[0];
        return <div key={k} style={{position: 'absolute', left, top: tlY + Math.round(U * 0.018), width: w + 2, opacity: intro,
          color: current ? FG : DIM, font: `${current ? 700 : 500} ${perPx}px/1.2 ${MONO}`, whiteSpace: 'nowrap'}}>{p}</div>;
      })}
      {title ? (
        <KineticText k={titleK} x={Math.round(W * 0.05)} y={TITLE_Y} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.04}, enter: {by: 'line', at: 0.02, stagger: 0.1, dur: 0.8, ease: 'expo', cueKeys: ['title'], until: 0.4}}} />
      ) : titleK.anchor}
      {note ? (
        <KineticText k={noteK} x={Math.round(W * 0.05)} y={contentBottom(W, H) - noteH} color={DIM} id="note"
          motion={{from: {opacity: 0, y: 0.4}, enter: {by: 'word', at: 0.1, stagger: 0.03, dur: 0.5, ease: 'power3', cueKeys: ['note'], until: 0.4}}} />
      ) : noteK.anchor}
    </AbsoluteFill>
  );
};
export default RankRace;
