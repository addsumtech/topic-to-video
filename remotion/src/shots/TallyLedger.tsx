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

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 155;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7';

type Row = {label?: string; count?: number};

export const TallyLedger: React.FC<{
  kicker?: string;
  rows?: Row[];
  perStroke?: number;      // how many the single stroke stands for
  strokeUnit?: string;     // what one stroke means, printed so it is never a mystery mark
  total?: string;          // the figure the ledger adds up to, ruled off at the foot
  totalLabel?: string;
  note?: string;
}> = ({
  kicker = 'THE COUNT',
  rows: ROWS = [{label: 'first', count: 4}, {label: 'second', count: 7}, {label: 'third', count: 5}],
  perStroke = 1,
  strokeUnit = '',
  total = '',
  totalLabel = 'total',
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0012));

  const left = W * 0.10, right = W * 0.10;
  const top = CONTENT_TOP + H * 0.02;
  const bottom = H - captionBand(W, H) - H * 0.05;

  const rows = ROWS.slice(0, 5);
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
        const n = Math.max(0, Math.min(40, Math.round((r.count ?? 0) / Math.max(1, perStroke))));
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
              fontVariantNumeric: 'tabular-nums'}}>{(r.count ?? 0).toLocaleString('en-US')}</div>
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

      {strokeUnit ? (
        <div style={{position: 'absolute', left, top: bottom - Math.round(W * 0.030), opacity: land,
          font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em'}}>one stroke = {strokeUnit}</div>
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
