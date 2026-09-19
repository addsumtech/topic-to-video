// SHOT · TallyLedger — a hand-ruled ledger counting something into a total, in STROKES rather than
// digits. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: a number somebody actually counted. A digit that ticks up on a dark panel says
// "telemetry"; a ruled sheet with gate-five tallies says "a person stood there and marked this off", and
// for a civic or historical figure that is the truer register. It also does something a counter cannot:
// the strokes show the count's SHAPE — which row carries most of it, how the parts compose the whole.
//
// Each row's strokes are count/perStroke, so a large figure stays legible (one stroke = 500 bicycles).
// The unit of the stroke is printed, because an unexplained stroke is decoration.
//
// A STROKE IS A CLAIM ABOUT THE COUNT, SO THE TALLY NEVER LIES TO FIT. It used to draw
// `Math.min(40, Math.round(count / perStroke))` strokes: every row past 40 strokes was cut to 40 in silence, so
// counts of 45 and 200 drew identical tallies — the one thing a tally exists to show, which row carries more, was
// false. A row with no `count` printed "0" beside no strokes, and a sixth row was dropped without a word. Now:
//  • too many strokes for the sheet (more than MAX_TALLY_STROKES in a row): when the film named no `strokeUnit`,
//    the register coarsens the stroke on a 1-2-5 ladder (1 → 2 → 5 → 10 …, times `perStroke`) until the largest
//    row fits, and the legend PRINTS the stroke it used ("one stroke = 5") — the scale is said on the frame. When
//    the film DID write a `strokeUnit` ("500 bicycles"), those words would become false at another scale, so it
//    throws instead and names the `perStroke` that would fit.
//  • a stroke is round(count / stroke). A non-zero count that would round to NO strokes throws — an empty row
//    beside a real figure reads as "none".
//  • a row without a label or a count, a negative count, or more than five rows, throws. The row's figure is
//    printed as the film wrote it (runtime/figure.ts `figureText`), not re-formatted.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA} from '../runtime/dna';
import {figureText, figureValue} from '../runtime/figure';

export const DURATION = 155;

// The LEGEND of a tally chart: what one stroke stands for. A tally without its unit is a pile of marks, so the
// legend belongs to the form exactly as an axis label belongs to a graph — but its WORDS are the film's. It was
// the literal 'one stroke =', printed in English under a Chinese film's rows; `legendLabel` carries it now, with
// that text as the default so the demo-copy gate lists it when a film omits it.

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7';

type Row = {label?: string; count?: number | string};

export const MAX_TALLY_ROWS = 5;
export const MAX_TALLY_STROKES = 40;   // 8 gates of five: what one ruled row holds legibly at any aspect

export const TallyLedger: React.FC<{
  kicker?: string;
  rows?: Row[];
  perStroke?: number;      // how many the single stroke stands for
  strokeUnit?: string;     // what one stroke means, printed so it is never a mystery mark
  total?: string;          // the figure the ledger adds up to, ruled off at the foot
  totalLabel?: string;
  note?: string;
  legendLabel?: string;    // the words before the stroke's meaning — 'one stroke =' / 「每一笔 =」
}> = ({
  kicker = 'THE COUNT',
  rows: ROWS = [{label: 'first', count: 4}, {label: 'second', count: 7}, {label: 'third', count: 5}],
  perStroke = 1,
  strokeUnit = '',
  total = '',
  legendLabel = 'one stroke =',
  totalLabel = 'total',
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0012));

  const left = W * 0.10, right = W * 0.10;
  const top = CONTENT_TOP + H * 0.02;
  const bottom = H - captionBand(W, H) - H * 0.05;

  if (!Array.isArray(ROWS) || ROWS.length < 1 || ROWS.length > MAX_TALLY_ROWS) {
    throw new Error(`TallyLedger needs 1-${MAX_TALLY_ROWS} \`rows\` (got ${Array.isArray(ROWS) ? ROWS.length : typeof ROWS}). ` +
      'More rows do not fit the sheet as legible tallies; merge the smallest into one row the film names, or use a ' +
      'table register. Rows are never dropped to fit.');
  }
  const rows = ROWS.map((r, i) => {
    const label = String(r?.label ?? '').trim();
    if (!label) throw new Error(`TallyLedger: row ${i + 1} has no \`label\`.`);
    const raw = r?.count as unknown;
    const value = typeof raw === 'number' ? raw : figureValue(raw);
    if (value == null || !Number.isFinite(value) || value < 0) {
      throw new Error(`TallyLedger: row ${i + 1} ("${label}") needs a \`count\` that is one number >= 0, got ` +
        `${JSON.stringify(raw)}. The strokes are drawn from it; nothing may stand in for a count nobody made.`);
    }
    return {label, value, text: figureText(raw)};
  });
  const base = Number(perStroke);
  if (!Number.isFinite(base) || base <= 0) {
    throw new Error(`TallyLedger: \`perStroke\` must be a number above 0 (got ${JSON.stringify(perStroke)}).`);
  }
  const maxCount = Math.max(...rows.map((r) => r.value));
  // the stroke actually drawn: the film's, or — only when the film wrote no strokeUnit — coarsened to fit
  let stroke = base;
  if (Math.round(maxCount / base) > MAX_TALLY_STROKES) {
    // the smallest multiplier on the 1-2-5 ladder at which the largest row fits
    let m = 1;
    ladder: for (let dec = 1; dec < 1e15; dec *= 10) {
      for (const x of [1, 2, 5]) {
        m = x * dec;
        if (Math.round(maxCount / (base * m)) <= MAX_TALLY_STROKES) break ladder;
      }
    }
    const scaled = parseFloat((base * m).toPrecision(12));   // 0.1 × 3 must print "0.3", not 0.30000000000000004
    if (strokeUnit) {
      throw new Error(`TallyLedger: the largest row (${maxCount}) needs ${Math.round(maxCount / base)} strokes at one ` +
        `stroke = "${strokeUnit}" (perStroke ${base}); a row holds ${MAX_TALLY_STROKES}. Pass perStroke ${scaled} ` +
        'and a strokeUnit that says what that stroke stands for.');
    }
    stroke = scaled;
  }
  const strokesOf = rows.map((r) => {
    const n = Math.round(r.value / stroke);
    if (r.value > 0 && n === 0) {
      throw new Error(`TallyLedger: "${r.label}" (${r.text}) is too small to draw at one stroke = ${stroke} — it ` +
        'would be an empty row beside a real count. The counts span too wide a range for a tally; use a bar or ' +
        'table register, or a finer perStroke if the largest row allows it.');
    }
    return n;
  });
  const legend = strokeUnit || (stroke !== 1 ? String(stroke) : '');
  const labW = W * 0.20;
  const tallyX = left + labW + W * 0.02;
  const rowH = Math.min(H * 0.14, (bottom - top - H * 0.13) / Math.max(1, rows.length));

  const kick = easeOutCubic(clamp01(seg(t, 0.02, 0.16)));
  const rule = easeOutCubic(clamp01(seg(t, 0.08, 0.30)));
  const land = easeOutExpo(clamp01(seg(t, 0.78, 0.94)));

  const sw = Math.max(2, Math.round(W * 0.0022));       // stroke weight
  const sh = Math.round(rowH * 0.42);                    // stroke height
  const sgap = Math.round(W * 0.0075);                   // gap between strokes
  const ggap = Math.round(W * 0.017);                    // gap between gates of five

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      <div style={{position: 'absolute', left, top: CONTENT_TOP - H * 0.055, opacity: kick,
        font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: ACC,
        letterSpacing: dna?.labelSpacing ?? '0.14em',
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>

      {rows.map((r, i) => {
        const y = top + i * rowH;
        const st = 0.20 + i * (0.48 / Math.max(1, rows.length));
        const on = easeOutCubic(clamp01(seg(t, st, st + 0.48 / Math.max(1, rows.length) + 0.08)));
        const n = strokesOf[i];
        const shown = Math.round(n * on);
        return (
          <React.Fragment key={i}>
            {/* the ruled line this row is written on */}
            <div style={{position: 'absolute', left, top: y + rowH - hair, width: (W - left - right) * rule,
              height: hair, background: LINE}} />
            <div style={{position: 'absolute', left, top: y + rowH * 0.30, width: labW, opacity: on,
              font: `500 ${Math.round(W * 0.0195)}px/1.25 ${disp}`, color: FG}}>{r.label}</div>
            {/* the strokes, in gates of five — the fifth laid across the previous four */}
            <div style={{position: 'absolute', left: tallyX, top: y + rowH * 0.22, height: sh,
              display: 'flex', alignItems: 'flex-start', gap: ggap}}>
              {Array.from({length: Math.ceil(shown / 5)}).map((_, g) => {
                const inGate = Math.min(5, shown - g * 5);
                return (
                  <div key={g} style={{position: 'relative', height: sh,
                    width: 4 * sw + 3 * sgap + sw}}>
                    {Array.from({length: Math.min(4, inGate)}).map((__, k) => (
                      <div key={k} style={{position: 'absolute', left: k * (sw + sgap), top: 0,
                        width: sw, height: sh, background: ACC}} />
                    ))}
                    {inGate >= 5 ? (
                      <div style={{position: 'absolute', left: -sgap, top: sh * 0.5 - sw / 2,
                        width: 4 * sw + 4 * sgap, height: sw, background: ACC,
                        transform: 'rotate(-18deg)', transformOrigin: '0 50%'}} />
                    ) : null}
                  </div>
                );
              })}
            </div>
            {/* the row's own figure, right-aligned like a ledger column */}
            <div style={{position: 'absolute', right, top: y + rowH * 0.30, opacity: on,
              font: `600 ${Math.round(W * 0.0185)}px/1.25 ${mono}`, color: DIM,
              fontVariantNumeric: 'tabular-nums'}}>{r.text}</div>
          </React.Fragment>
        );
      })}

      {/* the total, double-ruled off at the foot the way a ledger closes a column */}
      {total ? (
        <>
          <div style={{position: 'absolute', left, top: top + rows.length * rowH + H * 0.030,
            width: (W - left - right) * land, height: hair * 2, background: FG}} />
          <div style={{position: 'absolute', left, top: top + rows.length * rowH + H * 0.045,
            opacity: land, font: `500 ${Math.round(W * 0.0145)}px/1.3 ${mono}`, color: DIM,
            letterSpacing: '0.08em', textTransform: 'uppercase'}}>{totalLabel}</div>
          <div style={{position: 'absolute', right, top: top + rows.length * rowH + H * 0.036,
            opacity: land, font: `700 ${Math.round(W * 0.046)}px/1.1 ${disp}`, color: ACC,
            fontVariantNumeric: 'tabular-nums'}}>{total}</div>
        </>
      ) : null}

      {legend ? (
        <div style={{position: 'absolute', left, top: bottom - Math.round(W * 0.030), opacity: land,
          font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em'}}>{legendLabel ? `${legendLabel} ` : ''}{legend}</div>
      ) : null}
      {note ? (
        <div style={{position: 'absolute', left, right, top: bottom - Math.round(W * 0.012), opacity: land,
          font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em'}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default TallyLedger;
