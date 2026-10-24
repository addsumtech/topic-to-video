// SHOT · Flow Counter — ONE QUANTITY, AND HOW IT MOVED: the film's figure set huge in lining tabular digits, rolling
// from each stated value to the next the way an odometer does — the units wheel spins hardest, the high places turn
// only when they must, a column appears when the number grows into it — and holding on every value long enough to read.
//
// WHAT IT ARGUES. That a number changed, and by how much, felt as distance travelled: 1,280 to 4,096 is a long roll in
// the hundreds and a short one in the thousands. Not for several figures side by side (a stat or table register), nor
// a ranking (RankRace). A single figure that does not move is EdStat / TermCounter.
//
// FIGURES ARE THE FILM'S STRINGS. Each step's settled frame prints its `value` exactly as written (runtime/figure.ts):
// the digit cells at rest hold exactly the characters of that string. Between two steps that are each ONE number with
// the same prefix and suffix, the roll passes through the values in between — interpolation between the film's own
// points, nothing outside them; any other pair (a range, a changed unit) crossfades, because there is nothing honest to
// count through.
//
// DIGITS SIT ON ONE LINE AT ONE WIDTH. Every digit has its own cell, as wide as the face's widest digit (measured,
// runtime/labelWidths), so the figure cannot jitter while it rolls whatever the face's own figures do; lining figures
// are on for every element (runtime/fonts.ts). A rolling cell holds at most TWO glyphs — the digit leaving and the one
// arriving — so at rest the DOM carries the figure's own characters and nothing else.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, dimOn, mix, contrastOf} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {parseFigure, figureText, Figure} from '../runtime/figure';
import {useLabelWidths} from '../runtime/labelWidths';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {useGlide} from '../runtime/glide';

export const DURATION = 210; // 7s
export const MAX_STEPS = 5;

type StepIn = {value?: string | number; label?: string};
const BG_D0 = '#07090f', FG_D0 = '#f4f6fa', DIM_D0 = '#8e97a9', ACC_D0 = '#7aa2ff';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';
const REF = 120;   // the size the glyphs are measured at; the figure is scaled from it

// Placeholder copy: two values that show the roll, named by their role; they measure nothing.
const DEMO: StepIn[] = [{value: '1,280', label: 'the first value'}, {value: '4,096', label: 'the value it reaches'}];

// a figure's number at value v, in the target's own written form (prefix, decimals, grouping, suffix)
const formatAs = (fig: Figure, v: number): string => {
  const neg = v < 0;
  let body = Math.abs(v).toFixed(fig.decimals);
  if (fig.grouped) {
    const [i, d] = body.split('.');
    body = i.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (d != null ? '.' + d : '');
  }
  return `${fig.prefix}${neg ? (fig.text.includes('−') ? '−' : '-') : ''}${body}${fig.suffix}`;
};

export const FlowCounter: React.FC<{
  kicker?: string;
  /** 1-5 steps: the `value` as the film writes it ("$1.2B", "4,096", "38%") and an optional `label` under it */
  steps?: StepIn[];
  note?: string;
  accent?: string;
}> = ({kicker = '', steps: stepsIn = DEMO, note = '', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const S = 'FlowCounter';
  const STEPS = rows<StepIn>(stepsIn, 'steps', S);
  if (STEPS.length < 1 || STEPS.length > MAX_STEPS) throw new Error(`${S}: needs 1-${MAX_STEPS} steps (got ${STEPS.length}).`);
  const steps = STEPS.map((s, i) => {
    const text = figureText(s?.value);
    if (!text) throw new Error(`${S}: step ${i + 1} has no \`value\` — the figure is the film's, pass it as written.`);
    return {text, fig: parseFigure(text), label: String(s?.label ?? '').trim()};
  });
  const n = steps.length;

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : FG;

  // ── measure the face: each digit's advance, and every non-digit glyph the steps use ─────────────────────
  const others = Array.from(new Set(steps.flatMap((s) => [...s.text].filter((c) => !/\d/.test(c)))));
  // @decor: the ten digits are MEASURED here to size the tabular cells; none is drawn unless the film's figure has it
  const glyphs = [...'0123456789', ...others];
  const gw = useLabelWidths(glyphs, DISPLAY, 700, REF);
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const kickPx = Math.round(U * 0.026), lblPx = Math.round(U * 0.034);
  // @decor: the widest of the ten measured digit advances (the first ten widths) — a cell size, not content
  const cellRef = gw.widths ? Math.max(...gw.widths.filter((_, i) => i < 10)) : REF * 0.62;
  const advRef = (c: string) => (/\d/.test(c) ? cellRef : (gw.widths?.[glyphs.indexOf(c)] ?? REF * 0.5));
  // the figure's size: the widest step fits 84% of the frame, never above a display cap
  const widestRef = Math.max(...steps.map((s) => [...s.text].reduce((a, c) => a + advRef(c), 0)));
  const size = Math.max(Math.round(U * 0.06), Math.min(Math.round(U * 0.24), Math.floor((W * 0.84 * REF) / Math.max(1, widestRef * 1.03))));
  const k = size / REF;
  const cellW = cellRef * k, cellH = Math.round(size * 1.08);

  // ── the timeline: hold, roll, hold, roll, … hold ────────────────────────────────────────────────────
  const A = 0.08, B = 0.86;
  const HOLD = 0.9, MOVE = 1;
  const total = n * HOLD + (n - 1) * MOVE;
  const u = seg(t, A, B) * total;
  let k0 = n - 1, q = 0, qr = 0;
  {
    let acc = 0;
    for (let i = 0; i < n; i++) {
      if (u < acc + HOLD || i === n - 1) { k0 = i; q = 0; break; }
      acc += HOLD;
      if (u < acc + MOVE) { k0 = i; qr = (u - acc) / MOVE; q = easeInOutCubic(qr); break; }
      acc += MOVE;
    }
  }
  const from = steps[k0], to = steps[Math.min(n - 1, k0 + 1)];
  const rolling = q > 0 && q < 1 && from !== to;
  const countable = from.fig.num != null && to.fig.num != null && from.fig.prefix === to.fig.prefix &&
    from.fig.suffix === to.fig.suffix;
  const v = rolling && countable ? from.fig.num! + (to.fig.num! - from.fig.num!) * q : null;
  // the string on screen: the film's own at rest, the target's form while counting between two of its numbers
  const shown = !rolling ? (q >= 1 ? to.text : from.text) : (v != null ? formatAs(to.fig.decimals >= from.fig.decimals ? to.fig : from.fig, v) : '');
  // digit speed, for motion blur: how far the roll moves per unit of q at this instant
  const dq = 0.02;
  const vNext = rolling && countable ? from.fig.num! + (to.fig.num! - from.fig.num!) * easeInOutCubic(Math.min(1, qr + dq)) : null;

  // each digit column's continuous position (odometer: place value 10^j turns at v / 10^j)
  const cells = (str: string, val: number | null) => {
    const chars = [...str];
    let intDigits = 0, seenDot = false;
    chars.forEach((c) => { if (c === '.') seenDot = true; else if (/\d/.test(c) && !seenDot) intDigits += 1; });
    let place = intDigits - 1;
    return chars.map((c) => {
      if (!/\d/.test(c)) return {c, digit: false, pos: 0, place: 0};
      const pl = place--;
      const pos = val == null ? Number(c) : ((Math.abs(val) / Math.pow(10, pl)) % 10 + 10) % 10;
      return {c, digit: true, pos, place: pl};
    });
  };
  const row = rolling && v == null ? null : cells(shown, v);
  const blurFor = (place: number) => {
    if (v == null || vNext == null) return 0;
    const speed = Math.abs(vNext - v) / Math.pow(10, place);   // digits per small step of the roll
    return Math.min(cellH * 0.05, speed * cellH * 0.01);
  };

  const fadeIn = easeOutCubic(seg(t, 0.02, 0.12));
  const kickK = useKinetic({text: kicker || ' ', w: Math.round(W * 0.84), nowrap: true, fit: 'box', align: 'center',
    font: {family: MONO, weight: 600, size: kickPx, minSize: Math.round(U * 0.02), lineHeight: 1.2, tracking: 0.12}});
  const noteK = useKinetic({text: note || ' ', w: Math.round(W * 0.8), fit: 'box', maxLines: 3, h: Math.round(U * 0.12), align: 'center',
    font: {family: BODY, weight: 420, size: Math.round(U * 0.03), minSize: Math.round(U * 0.024), lineHeight: 1.35}});

  const rowW = row ? row.reduce((a, c) => a + (c.digit ? cellW : advRef(c.c) * k), 0) : 0;
  const blockTop = Math.round((zTop + zBot) / 2 - cellH * 0.72);
  const xStart = (W - rowW) / 2;
  const label = (!rolling ? (q >= 1 ? to : from) : (q < 0.5 ? from : to)).label;
  const labelA = rolling ? Math.abs(1 - 2 * q) : 1;
  const trackY = blockTop + cellH + Math.round(U * 0.12);

  let x = xStart;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(90% 80% at 50% 45%, ${mix(BG, ACC, 0.1)}, ${BG} 72%)`}}>
      {gw.anchor}
      {kicker ? <KineticText k={kickK} x={Math.round(W * 0.08)} y={blockTop - Math.round(U * 0.09)} color={ACC} id="kicker"
        motion={{from: {opacity: 0, y: 0.4}, enter: {by: 'grapheme', at: 0.02, stagger: 0.02, dur: 0.4, ease: 'power3', cueKeys: ['kicker'], until: 0.3}}} />
        : kickK.anchor}
      {gw.widths ? (
        <div style={{position: 'absolute', left: 0, top: blockTop, width: W, height: cellH, opacity: fadeIn}}>
          {row ? row.map((c, i) => {
            const w = c.digit ? cellW : advRef(c.c) * k;
            const left = x; x += w;
            if (!c.digit) {
              return <div key={i} style={{position: 'absolute', left, top: 0, width: w, height: cellH, color: FG,
                font: `700 ${size}px/${cellH}px ${DISPLAY}`, textAlign: 'center', whiteSpace: 'pre'}}>{c.c}</div>;
            }
            const lo = Math.floor(c.pos + 1e-9), frac = c.pos - lo;
            const blur = blurFor(c.place);
            return (
              <div key={i} style={{position: 'absolute', left, top: 0, width: w, height: cellH, overflow: 'hidden'}}>
                <div style={{position: 'absolute', left: 0, top: 0, width: w, transform: glide(frac > 1e-6 ? `translateY(${-frac * cellH}px)` : undefined, frac > 1e-6),
                  filter: blur > 0.3 ? `blur(${blur.toFixed(2)}px)` : undefined}}>
                  <div style={{height: cellH, color: FG, font: `700 ${size}px/${cellH}px ${DISPLAY}`, textAlign: 'center'}}>{String(lo % 10)}</div>
                  {frac > 1e-6 ? <div style={{height: cellH, color: FG, font: `700 ${size}px/${cellH}px ${DISPLAY}`, textAlign: 'center'}}>{String((lo + 1) % 10)}</div> : null}
                </div>
              </div>
            );
          }) : (
            // not countable: the leaving figure rises out of the line and the arriving one rises into it — two written
            // figures laid over each other in place read as one illegible glyph soup
            <div style={{position: 'absolute', left: 0, top: -Math.round(cellH * 0.2), width: W, height: Math.round(cellH * 1.4), overflow: 'hidden'}}>
              {[from.text, to.text].map((s, j) => {
                const off = j === 0 ? -easeInOutCubic(clamp01(q * 1.6)) : 1 - easeInOutCubic(clamp01(q * 1.6 - 0.6));
                return (
                  <div key={j} style={{position: 'absolute', left: 0, width: W, top: Math.round(cellH * 0.2), height: cellH, textAlign: 'center',
                    color: FG, opacity: clamp01(1 - Math.abs(off) * 1.4), transform: glide(`translateY(${off * cellH * 0.9}px)`, true),
                    font: `700 ${size}px/${cellH}px ${DISPLAY}`, whiteSpace: 'nowrap'}}>{s}</div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}
      {label ? (
        <div style={{position: 'absolute', left: W * 0.08, width: W * 0.84, top: blockTop + cellH + Math.round(U * 0.03), textAlign: 'center',
          color: DIM, opacity: labelA * fadeIn, font: `500 ${lblPx}px/1.3 ${BODY}`}}>{label}</div>
      ) : null}
      {n > 1 ? (
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          {steps.map((s, i) => {
            const span = Math.min(W * 0.5, U * 0.16 * (n - 1));
            const cx = W / 2 - span / 2 + (n > 1 ? (span * i) / (n - 1) : 0);
            const on = i < k0 || (i === k0) || (i === k0 + 1 && q >= 1);
            return <circle key={i} cx={cx} cy={trackY} r={U * 0.007} fill={on ? ACC : 'none'} stroke={ACC} strokeWidth={2} opacity={fadeIn} />;
          })}
          {(() => {
            const span = Math.min(W * 0.5, U * 0.16 * (n - 1));
            const xa = W / 2 - span / 2, p = clamp01((k0 + q) / (n - 1));
            return <line x1={xa} y1={trackY} x2={xa + span * p} y2={trackY} stroke={ACC} strokeWidth={2} opacity={0.7 * fadeIn} />;
          })()}
        </svg>
      ) : null}
      {note ? <KineticText k={noteK} x={Math.round(W * 0.1)} y={Math.min(zBot - Math.round(U * 0.12), trackY + Math.round(U * 0.05))} color={DIM} id="note"
        motion={{from: {opacity: 0, y: 0.4}, enter: {by: 'word', at: 0.2, stagger: 0.03, dur: 0.5, ease: 'power3', cueKeys: ['note'], until: 0.5}}} />
        : noteK.anchor}
    </AbsoluteFill>
  );

};
export default FlowCounter;
