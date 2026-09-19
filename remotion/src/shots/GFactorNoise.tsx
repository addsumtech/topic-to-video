// GFactorNoise — why parallel imaging can't go much faster. As the acceleration factor R rises, unfolding the
// aliased signal AMPLIFIES noise (the g-factor): the reconstructed tile gets grainier, and past the usable cap it
// is too noisy to use. The covarying "R up => noise up => cap" IS the idea; red marks the unusable zone
// (viz-semantics: red = bad). Deterministic (pure fn of useT).
//
// ONE AXIS, OR THE PICTURE CONTRADICTS ITSELF. The track used to be drawn from three different numbers. The
// ticks put 3x at the middle of a 1..5 track, the red zone started at `capFrac = 3/5` — which on those same
// ticks is 3.4x — and the fill turned red at `R > 3.02`. So a film passing `factor: 3.2` got a RED bar that
// had not reached the red zone, and the sentence under the title said "2-3 max" over a line drawn at 3.4.
// And with no `factor` at all the fill still ran to the 3x tick, which reads as a measured R of 3 that no
// film supplied. Now every mark goes through one `frac(r)`: the ticks, the dashed cap line, the red zone,
// the fill and the read-out. The fill is red exactly when R is past the cap it is drawn against. With no
// `factor` there is no fill and no read-out; the grain still grows, because noise growing with R is the
// mechanism this register exists to show, and it claims no value.
//
// THE CAP IS A CLAIM, SO IT IS A PROP. "R = 2-3 max · never beyond the coil count" was printed on every film,
// declared as this register's own vocabulary so the demo-copy gate could not see it. It is a clinical rule of
// thumb about the world, not the name of the mechanism: a 32-channel head coil film says something else. It
// is now `limit` (default the old sentence, so the gate lists it when a film omits it; "" draws no line), and
// the red zone starts at `cap` (default 3), so a film that changes the sentence can move the line with it.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom} from '../runtime/layout';
import {parseFigure, figureAt} from '../runtime/figure';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
// The cap sentence ('R = 2–3 max · never beyond the coil count') used to be listed here. It is a claim
// about the world, not the form's own word, so it is the `limit` prop now and a film that omits it is told.
export const INTRINSIC_TEXT = [
  'g-factor noise →',
];
const WARN = '#ff5d6c';

// `factor` is the amplification the FILM measured. No default: the read-out used to count 1.0x -> 3.0x off
// the clock and print the result as though it had been measured, on whatever topic reached for the register.
// It may be a number or the film's string ("2.5×"); either way it must be exactly one number >= 1, and the
// settled read-out prints it as the film wrote it (a bare number gets the axis unit ×), never rounded.
export const GFactorNoise: React.FC<{accent?: string; label?: string; factor?: number | string | null; cap?: number; limit?: string}> = ({
  accent = '#22d3ee', label = 'Unfolding amplifies noise', factor = null,
  cap = 3, limit = 'R = 2–3 max · never beyond the coil count',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();

  if (typeof cap !== 'number' || !Number.isFinite(cap) || cap <= 1) {
    throw new Error(`GFactorNoise: \`cap\` is the acceleration factor where the red zone starts and must be a number > 1, ` +
      `got ${JSON.stringify(cap)}.`);
  }
  const fig = factor == null ? null : parseFigure(factor);
  if (fig && (fig.num == null || fig.num < 1)) {
    throw new Error(`GFactorNoise: \`factor\` must be exactly one number >= 1 (e.g. 2.5 or "2.5×"), got ` +
      `${JSON.stringify(factor)}. The bar is drawn to it, so a range or a word has no length; omit \`factor\` ` +
      'to show the mechanism without a measured value.');
  }
  const F = fig ? (fig.num as number) : null;

  // ONE AXIS: 1x .. axisMax, wide enough for the cap and the film's factor, ticks every `step`.
  const reach = Math.max(4, Math.ceil(Math.max(cap, F ?? 0)));          // at least 1..5, as before
  const step = reach <= 8 ? 1 : Math.ceil(reach / 8);
  const axisMax = 1 + step * Math.ceil(reach / step);
  const frac = (r: number) => clamp01((r - 1) / (axisMax - 1));
  const ticks = Array.from({length: Math.round((axisMax - 1) / step) + 1}, (_, k) => 1 + k * step);

  const rise = clamp01(seg(t, 0.12, 0.8));
  // R rises to the supplied factor; with none, an illustrative R rises to the cap and drives the grain ONLY
  const R = lerp(1, F ?? cap, rise);
  const past = F != null && R > cap;                          // red exactly when the fill is past the cap line
  const noise = clamp01(((R - 1) / (cap - 1)) * 0.75);        // the grain reaches its "unusable" density AT the cap

  // a small reconstructed tile that gets grainier as R rises. The grain is drawn in the TILE's own coordinates:
  // it used to add the tile's frame offset (tx, ty) inside an svg only tw x th big, so every speck landed
  // outside it and the tile stayed empty — the one thing this register exists to show was never on a frame.
  const tx = W * 0.5 - 200, ty = H * 0.26, tw = 400, th = 300;
  const grain: React.ReactNode[] = [];
  const n = Math.round(40 + noise * 520);
  for (let i = 0; i < n; i++) {
    grain.push(<circle key={i} cx={hash01(i * 2 + 1) * tw} cy={hash01(i * 2 + 7) * th}
      r={0.8 + hash01(i * 3) * 1.6} fill={hash01(i) > 0.7 ? WARN : '#ffffff'} opacity={0.15 + noise * 0.5} />);
  }

  // the R track: usable zone up to the cap, then the red g-factor zone
  // the track's tick labels hang below it; both come off the content zone's floor rather than 78% of a frame
  const by = Math.min(H * 0.78, contentBottom(W, H) - 78);
  const bx = W * 0.24, bw = W * 0.52, capFrac = frac(cap);
  const readout = fig ? figureAt(fig, R / (F as number)) + (fig.suffix.trim() ? '' : '×') : '';

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #0b1120, #05060a)')}}>
      {/* the noisy reconstructed tile */}
      <div style={{position: 'absolute', left: tx, top: ty, width: tw, height: th, borderRadius: 12,
        border: `2px solid ${past ? WARN : accent}`, background: 'linear-gradient(160deg,#0e1b30,#0a1424)', overflow: 'hidden'}}>
        <svg width={tw} height={th}><g>{grain}</g></svg>
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* track */}
        <rect x={bx} y={by} width={bw * capFrac} height={12} rx={6} fill={accent} opacity={0.28} />
        <rect x={bx + bw * capFrac} y={by} width={bw * (1 - capFrac)} height={12} rx={6} fill={WARN} opacity={0.3} />
        {/* the fill — only for a factor the film supplied */}
        {F == null ? null : <rect x={bx} y={by} width={bw * frac(R)} height={12} rx={6} fill={past ? WARN : accent} />}
        <line x1={bx + bw * capFrac} y1={by - 20} x2={bx + bw * capFrac} y2={by + 32} stroke={WARN} strokeWidth={2} strokeDasharray="4 4" />
        <text x={bx + bw * capFrac} y={by - 28} fill={WARN} fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" textAnchor="middle">g-factor noise →</text>
        {ticks.map((v) => (
          <text key={v} x={bx + bw * frac(v)} y={by + 52} fill="#8aa" fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" textAnchor="middle">{v}×</text>
        ))}
        {/* the live R read-out — drawn only when the film supplied a measured factor. It sits ABOVE the zone
            label: at the old by-22 a factor near the cap printed its number straight through "g-factor noise". */}
        {F == null ? null : (
          <text x={bx + bw * frac(R)} y={by - 62} fill="#eaf6ff" fontSize="40" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} textAnchor="middle">
            {readout}</text>
        )}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}
        {String(limit ?? '').trim() ? (
          <div style={{marginTop: 8, font: "600 22px/1 var(--f-mono, 'JetBrains Mono', monospace)", color: WARN, letterSpacing: '0.12em'}}>
            {limit}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default GFactorNoise;
