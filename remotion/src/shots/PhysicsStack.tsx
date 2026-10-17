// SHOT · Physics Stack — a tactile gravity register: weighty blocks DROP from above and settle into a bar chart
// with a real bounce (decaying) + a dust puff on impact. Physical, satisfying — distinct from the soft ClayStack
// (no physics) and flat IsometricAssembly. Deterministic (parabolic fall + damped bounce = t).
//
// THE HEIGHTS ARE THE FILM'S NUMBERS, OR THERE ARE NO BARS. This register used to take `items` — plain labels —
// and lay them over five hardcoded heights (220 / 320 / 250 / 430 / 560 px, a rising week), cycling the labels
// (`items[i % items.length]`) to fill five slots. A film that named three tools got a chart saying the third
// tool was twice the first, and printed two of the names twice. A bar's height is a claim about its label, so
// the height has to come from the same place the label does: `bars: [{label, value}]`, drawn from zero and in
// proportion, with the value written on the bar so nobody has to guess the scale. `items` without values now
// THROWS rather than inventing them. The standalone demo keeps illustrative weekday values, and validate.py
// warns when a film uses the register without passing `bars` (the same rule as every number register).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA, dnaPalette, mix} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx, inkBlockH, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

// THE CLOSING MARK FITS THE SENTENCE: a CJK line takes 。, a Latin one ., and a line that already ends in its own
// punctuation takes none — a Latin "." after a Chinese headline read as a typo, and "Done!." as two marks.
const closingMark = (s: string): string => /[.!?。！？…:：;；]\s*$/.test(s) ? ''
  : /[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/.test(s) ? '。' : '.';

export const DURATION = 165; // 5.5s

export type PhysicsBar = {
  label: string;
  /** the SOURCED quantity; heights are drawn from zero in proportion to it */
  value: number;
  /** how the value is written on the bar (defaults to the number plus `unit`, never rounded) */
  display?: string;
};

export const MAX_PHYSICS_BARS = 8;
const TONES0 = ['#4c8dff', '#22c9a0', '#b06cff', '#ff8f5a', '#ffd23f', '#5ad1ff', '#ff6f91', '#9be15d'];
const DEFAULT_BARS: PhysicsBar[] = [
  {label: 'Mon', value: 22}, {label: 'Tue', value: 32}, {label: 'Wed', value: 25},
  {label: 'Thu', value: 43}, {label: 'Fri', value: 56},
];

const normalise = (bars: unknown, items: unknown): PhysicsBar[] => {
  if (items != null && bars == null) {
    throw new Error(
      'PhysicsStack draws HEIGHTS, and `items` carries only labels — the heights would have to be invented. ' +
      'Pass `bars: [{label, value}]` with sourced values, or cast a list register for a list of names.');
  }
  if (!Array.isArray(bars) || bars.length < 1 || bars.length > MAX_PHYSICS_BARS) {
    throw new Error(`PhysicsStack needs 1-${MAX_PHYSICS_BARS} \`bars\` (got ${Array.isArray(bars) ? bars.length : typeof bars}).`);
  }
  const out = bars.map((b: any, i: number) => {
    const label = String(b?.label ?? '').trim();
    const value = Number(b?.value);
    if (!label) throw new Error(`PhysicsStack: bar ${i + 1} has no label.`);
    if (!Number.isFinite(value) || value < 0) {
      throw new Error(`PhysicsStack: bar ${i + 1} ("${label}") needs a finite value >= 0, got ${JSON.stringify(b?.value)}. ` +
        'A bar standing on the ground cannot show a negative quantity; use a signed chart register.');
    }
    const display = b?.display == null ? undefined : String(b.display).trim() || undefined;
    return {label, value, display};
  });
  if (!out.some((b) => b.value > 0)) throw new Error('PhysicsStack: every value is 0, so there is nothing to draw.');
  return out;
};

export const PhysicsStack: React.FC<{bars?: PhysicsBar[]; items?: string[]; label?: string; unit?: string}> = ({
  bars, items, label = 'a week of shipping', unit = ''} = {}) => {
  const BARS = normalise(bars ?? (items == null ? DEFAULT_BARS : undefined), items);
  const n = BARS.length;
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const TONES = dnaPalette(dna, n) ?? TONES0;
  const FG = dna?.fg ?? '#eaf1ff';
  const DIM = dna?.dim ?? '#8494a8';
  const ACC = dna?.accent ?? '#ffd23f';
  const GROUND = dna?.line ?? '#2a3446';
  const GRID = dna ? mix(dna.bg, dna.line ?? '#161d29', 0.5) : '#161d29';

  // LAYOUT, top to bottom: headline · value text · the tallest bar · ground · labels, all in the content zone.
  const mark = closingMark(String(label));
  const headPx = fitTextPx(label + mark, W * 0.84, Math.round(U * 0.052));
  const headTop = CONTENT_TOP - Math.round(U * 0.04);
  const valuePx = Math.round(U * 0.026);
  const zoneW = W * 0.84;
  const gap = Math.round(Math.min(U * 0.043, zoneW / n * 0.2));
  const bw = Math.round(Math.min(U * 0.167, (zoneW - gap * (n - 1)) / n));
  // One size for every label (a mixed size would rank them), the largest at which each fits two lines of its
  // column — so one long name wraps instead of shrinking every other name to fit it on one line.
  const labelW = bw + gap * 0.8;
  let labelPx = Math.round(U * 0.028);
  while (labelPx > 14 && BARS.some((b) => wrapLines(b.label, labelPx, labelW) > 2)) labelPx -= 1;
  const labelLines = Math.min(2, Math.max(...BARS.map((b) => wrapLines(b.label, labelPx, labelW))));
  const LABEL_ROOM = inkBlockH(labelPx, labelLines) + Math.round(U * 0.02);
  const groundY = contentBottom(W, H) - LABEL_ROOM;
  const maxTop = headTop + inkBlockH(headPx) + inkBlockH(valuePx) + Math.round(U * 0.03);
  const maxH = Math.max(U * 0.1, groundY - maxTop);
  const vmax = Math.max(...BARS.map((b) => b.value));
  const totalW = n * bw + (n - 1) * gap;
  const x0 = (W - totalW) / 2;
  const radius = Math.round(Math.min(bw * 0.08, U * 0.013));

  // damped-bounce settle: block falls, lands at `land`, bounces a couple times decaying to rest
  const settleY = (targetTop: number, land: number) => {
    if (t < land) {const k = clamp01(t / land); return lerp(-H * 0.37, targetTop, k * k);} // accelerating fall
    const s = clamp01((t - land) / 0.34);
    const bounce = Math.abs(Math.sin(s * Math.PI * 2.4)) * (1 - s) * U * 0.11; // decaying
    return targetTop - bounce;
  };
  const landAt = (i: number) => 0.16 + i * Math.min(0.12, 0.5 / Math.max(1, n));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 24%, #141a26 0%, #0a0d14 72%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* ground + quarter rules of the tallest bar, so the proportions can be read against something */}
        <line x1={W * 0.06} y1={groundY} x2={W * 0.94} y2={groundY} stroke={GROUND} strokeWidth={3} />
        {[0.25, 0.5, 0.75].map((g, i) => <line key={i} x1={W * 0.06} y1={groundY - maxH * g} x2={W * 0.94} y2={groundY - maxH * g} stroke={GRID} strokeWidth={1.5} />)}

        {BARS.map((b, i) => {
          const land = landAt(i);
          const h = (b.value / vmax) * maxH;
          const top = settleY(groundY - h, land);
          const landed = t >= land;
          const impact = clamp01((t - land) / 0.12);
          const bx = x0 + i * (bw + gap);
          const tone = TONES[i % TONES.length];
          return (
            <g key={i}>
              {/* dust puff on impact */}
              {landed && impact < 1 && h > 0 && [...Array(6)].map((_, k) => {
                const a = (k / 6) * Math.PI - Math.PI, d = impact * bw * 0.5;
                return <circle key={k} cx={bx + bw / 2 + Math.cos(a) * d} cy={groundY + Math.sin(a) * d * 0.3} r={lerp(U * 0.013, 3, impact)} fill={dna?.dim ?? '#5a6675'} opacity={(1 - impact) * 0.5} />;
              })}
              {h > 0 ? <rect x={bx} y={top} width={bw} height={Math.max(0, groundY - top)} rx={radius} fill={tone} /> : null}
              {h > 0 ? <rect x={bx} y={top} width={bw} height={Math.max(0, Math.min(U * 0.026, groundY - top))} rx={radius} fill="#ffffff" opacity={0.22} /> : null}
            </g>
          );
        })}
      </svg>

      {BARS.map((b, i) => {
        const land = landAt(i);
        const h = (b.value / vmax) * maxH;
        const bx = x0 + i * (bw + gap);
        const text = b.display ?? `${b.value}${unit}`;
        const vPx = Math.max(12, Math.min(valuePx, fitTextPx(text, bw + gap * 0.8, valuePx, {usable: 1})));
        const valIn = clamp01(seg(t, land + 0.1, land + 0.24));
        return (
          <React.Fragment key={i}>
            {/* the value, written on the settled bar: the scale is never left to be inferred */}
            <div style={{position: 'absolute', left: bx - gap * 0.4, width: bw + gap * 0.8, textAlign: 'center',
              top: groundY - h - inkBlockH(vPx) - Math.round(U * 0.008), opacity: valIn, color: FG,
              font: `700 ${vPx}px/1 var(--f-mono, "JetBrains Mono", ui-monospace, monospace)`, whiteSpace: 'nowrap'}}>{text}</div>
            <div style={{position: 'absolute', left: bx - gap * 0.4, width: bw + gap * 0.8, textAlign: 'center',
              top: groundY + Math.round(U * 0.014), color: DIM, textWrap: 'balance',
              font: `600 ${labelPx}px/${leading(b.label, 1.2)} var(--f-body, Inter, system-ui, sans-serif)`}}>{b.label}</div>
          </React.Fragment>
        );
      })}

      <div style={{position: 'absolute', left: W * 0.08, right: W * 0.08, top: headTop, textAlign: 'center',
        opacity: clamp01(seg(t, 0.7, 0.9)), color: FG, whiteSpace: 'nowrap',
        font: `800 ${headPx}px/${leading(label, 1)} var(--f-body, Inter, system-ui, sans-serif)`, letterSpacing: '-0.01em'}}>
        {label}<span style={{color: ACC}}>{mark}</span>
      </div>
    </AbsoluteFill>
  );
};
export default PhysicsStack;
