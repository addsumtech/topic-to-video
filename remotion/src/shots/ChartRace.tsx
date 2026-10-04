// SHOT · Chart Race — a bar-chart RACE: horizontal bars grow at different rates and RE-RANK as they overtake
// each other (bars slide to their live rank), value counters ticking, the leader glowing. The "who pulls
// ahead over time" data register (family D). Number-bearing → a real film passes SOURCED `data` (see NUM
// guard); the demo values are illustrative. Deterministic (value(t) = eased growth per item).
//
// THE SETTLED LABEL IS THE FILM'S FIGURE, AND EVERY ROW IS DRAWN. Three defects, all fixed here:
//  • the counter printed `Math.round(r.cur)` + unit, so a film's 4.6 settled as "5" and 0.45 as "0", and it
//    was still between values until t=0.92. Each row's figure now goes through runtime/figure.ts: it counts up
//    with the bar and lands on the film's own string (`display` if given, else `value` as written + `unit`),
//    and the race settles by t=0.62 so the true figures hold for the back third of the beat.
//  • the live rank was a sigmoid of the RAW value gap (× 0.22), which only separates bars whose values differ by
//    tens: rows of 0.45 / 0.30 / 0.25 all sat at the same slot, and even the demo's 84 vs 78 settled
//    half-overlapped. The gap is now measured relative to the largest value, equal values are ordered by the
//    film's final ranking, and the last stretch of the race eases every bar onto its exact final slot.
//  • `DATA.slice(0, 6)` dropped a seventh row in silence, and a row with no value raced to 0. Beyond six rows,
//    fewer than two, or a row without a label or a drawable value, the register now THROWS.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';
import {contentBottom, fitTextPx, textWidthPx} from '../runtime/layout';
import {parseFigure, figureAt, figureText} from '../runtime/figure';
import {useGlide} from '../runtime/glide';

export const DURATION = 155; // ~5.2s
const BG = '#0a0c14';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff', '#4dd0e1'];
export const MIN_RACE_ROWS = 2, MAX_RACE_ROWS = 6;
const RACE_A = 0.06, RACE_B = 0.62;   // the race runs here; from RACE_B on every bar and figure is the film's

type Row = {
  label?: string;
  /** the SOURCED quantity the bar is drawn from (a number, or a string that is exactly one number) */
  value?: number | string;
  /** when this row starts growing, as a fraction 0-0.9 of the race — the film's staging, 0 when omitted */
  delay?: number;
  /** how the settled figure is written ("4.6M 人"); defaults to `value` as written plus `unit` */
  display?: string;
};

const DEFAULT_DATA: Row[] = [{label: 'Alpha', value: 92, delay: 0.0}, {label: 'Bravo', value: 78, delay: 0.28},
  {label: 'Charlie', value: 100, delay: 0.42}, {label: 'Delta', value: 64, delay: 0.1}, {label: 'Echo', value: 84, delay: 0.5}];

const normalise = (data: unknown, unit: string) => {
  if (!Array.isArray(data) || data.length < MIN_RACE_ROWS || data.length > MAX_RACE_ROWS) {
    throw new Error(`ChartRace needs ${MIN_RACE_ROWS}-${MAX_RACE_ROWS} \`data\` rows (got ` +
      `${Array.isArray(data) ? data.length : typeof data}). One row is not a race; more than six do not fit as ` +
      'readable bars — split the beat or use a table register. Rows are never dropped to fit.');
  }
  const rows = data.map((r: any, i: number) => {
    const label = String(r?.label ?? '').trim();
    if (!label) throw new Error(`ChartRace: row ${i + 1} has no \`label\`.`);
    const fig = typeof r?.value === 'number' ? null : parseFigure(r?.value);
    const value = typeof r?.value === 'number' ? r.value : fig!.num;
    if (value == null || !Number.isFinite(value) || value < 0) {
      throw new Error(`ChartRace: row ${i + 1} ("${label}") needs a \`value\` that is one number >= 0, got ` +
        `${JSON.stringify(r?.value)}. A bar's length is drawn from it; pass the sourced number, and put how it ` +
        'should read in `display`.');
    }
    const delay = r?.delay == null ? 0 : Number(r.delay);
    if (!Number.isFinite(delay) || delay < 0 || delay > 0.9) {
      throw new Error(`ChartRace: row ${i + 1} ("${label}") has \`delay\` ${JSON.stringify(r?.delay)}; it must be 0-0.9 ` +
        '(the fraction of the race before this bar starts growing).');
    }
    const display = r?.display == null ? '' : figureText(r.display);
    // the string this row settles on: the film's own, never a re-formatted number
    const settled = display || (figureText(r?.value) + unit);
    return {label, value, delay, settled, affix: fig ? `${fig.prefix.trim()}|${fig.suffix.trim()}` : '|'};
  });
  // "4.6M" and "900k" parse to 4.6 and 900 — drawn as bars, the smaller figure would win. Refuse mixed units.
  const affixes = new Set(rows.map((r) => r.affix));
  if (affixes.size > 1) {
    throw new Error(`ChartRace: the rows' values are written in different units (${[...affixes].join(' / ')}), so ` +
      'their bars cannot be compared. Pass every `value` as a plain number in ONE unit and put the written form in `display`.');
  }
  if (!rows.some((r) => r.value > 0)) throw new Error('ChartRace: every value is 0, so there is no bar to draw.');
  return rows;
};

export const ChartRace: React.FC<{data?: Row[]; title?: string; unit?: string}> = ({
  data: DATA = DEFAULT_DATA,
  title: TITLE = 'Who pulls ahead', unit: UNIT = ''} = {}) => {
  const t = useT();
  const glide = useGlide();
  const dna = useDNA(); const TONES = dnaPalette(dna, 6) ?? TONES0;
  const {width: W, height: H} = useVideoConfig();
  const rows = normalise(DATA, UNIT ?? '');
  const n = rows.length;
  const maxVal = Math.max(...rows.map((r) => r.value));

  // ── geometry, from the frame and the film's strings (was 1920-only constants) ─────────────────────────
  const x0 = Math.round(W * 0.219);                                     // 420 at 1920
  const top = 240;
  const rowH = Math.min(118, (contentBottom(W, H) - 20 - top) / n);
  const labelPx = Math.max(14, Math.min(40, Math.round(rowH * 0.34),
    ...rows.map((r) => fitTextPx(r.label, x0 - 26 - 30, 40, {usable: 1}))));
  const valuePx = Math.max(14, Math.min(40, Math.round(rowH * 0.34)));
  const valueW = Math.max(...rows.map((r) => textWidthPx(r.settled, valuePx)));
  // the longest bar: 1200px on a 1920 frame as before, scaled to the frame, and never so long that the widest
  // settled figure beside it runs off the right edge
  const barMax = Math.max(80, Math.min(W * 0.625, W - x0 - 20 - valueW - 40));
  const titlePx = fitTextPx(TITLE, W - (x0 - 40) - 40, 34, {usable: 1, track: 0.24});

  // live value grows from each item's delay to the end of the race
  const live = rows.map((r, i) => {
    const g = easeOutCubic(clamp01(seg(t, RACE_A + r.delay * (RACE_B - RACE_A), RACE_B)));
    return {...r, i, g, cur: r.value * g};
  });
  // the film's FINAL order (ties keep the film's row order) — the slot each bar ends in
  const above = (o: {value: number; i: number}, r: {value: number; i: number}) =>
    o.value > r.value || (o.value === r.value && o.i < r.i);
  const finalRank = (r: {value: number; i: number}) => rows.reduce((s, o, j) => (j !== r.i && above({...o, i: j}, r) ? s + 1 : s), 0);
  // SOFT rank: a continuous position (Σ sigmoid of pairwise gaps, RELATIVE to the largest value) so bars SLIDE
  // smoothly as they overtake — CSS transitions don't animate across Remotion's per-frame capture, so the motion
  // must be in t. The ±3 bias orders equal values by their final ranking instead of stacking them on one slot.
  const sig = (z: number) => 1 / (1 + Math.exp(-z));
  const softRank = (r: {i: number; cur: number; value: number}) =>
    live.reduce((s, o) => (o.i === r.i ? s
      : s + sig(((o.cur - r.cur) / maxVal) * 40 + (above(o, r) ? 3 : -3))), 0);
  const snap = easeInOutCubic(seg(t, RACE_B - 0.12, RACE_B));
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? `radial-gradient(120% 100% at 30% 20%, #12162a, ${BG} 72%)`, overflow: 'hidden'}}>
      {TITLE ? <div style={{position: 'absolute', top: 90, left: x0 - 40, opacity: titleIn,
        color: '#aeb6ca', font: `700 ${titlePx}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.24em', textTransform: 'uppercase'}}>{TITLE}</div> : null}
      {live.map((r) => {
        const sr = lerp(softRank(r), finalRank(r), snap);
        const y = top + sr * rowH;
        const bw = (r.cur / maxVal) * barMax;
        // the leader is the bar whose CURRENT value is strictly the largest — a tie has no leader
        const lead = live.every((o) => o.i === r.i || r.cur > o.cur);
        const tone = TONES[r.i % TONES.length];
        const shown = figureAt(parseFigure(r.settled), r.g);
        return (
          // the row travels by its LAYOUT top (the soft rank sliding to its final slot) and the value counts up
          // by its own LEFT, both of which Skia rounds the same way it rounds a translate: the label and the
          // counting value carry the unlock while the race can still move them (runtime/glide.ts)
          <div key={r.i} style={{position: 'absolute', left: x0, top: y, width: barMax + valueW + 40, height: rowH - 22,
            transform: glide(undefined, t < RACE_B)}}>
            {/* label */}
            <div style={{position: 'absolute', right: '100%', top: 0, height: rowH - 22, paddingRight: 26,
              display: 'flex', alignItems: 'center', color: lead ? '#fff' : '#c7cee0',
              font: `${lead ? 800 : 600} ${labelPx}px/1 var(--f-body, Inter, system-ui, sans-serif)`, whiteSpace: 'nowrap'}}>{r.label}</div>
            {/* bar */}
            <div style={{position: 'absolute', left: 0, top: 0, width: bw, height: rowH - 22, borderRadius: 12,
              background: `linear-gradient(90deg, ${tone}, ${tone}cc)`,
              boxShadow: lead ? `0 0 30px ${tone}88` : 'none'}} />
            {/* value — counts up with its bar and settles on the film's own string */}
            <div style={{position: 'absolute', left: bw + 20, top: 0, height: rowH - 22, display: 'flex', alignItems: 'center',
              color: lead ? tone : '#8b93a8', font: `800 ${valuePx}px/1 var(--f-body, Inter, system-ui, sans-serif)`, whiteSpace: 'nowrap'}}>
              {shown}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default ChartRace;
