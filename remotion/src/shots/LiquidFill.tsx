// SHOT · Liquid Fill — a fluid-progress register: a round vessel FILLS with gooey liquid (wobbling wave surface
// + rising metaball bubbles that merge via an SVG gooey filter) to the film's level, the figure counts up with it,
// and a vessel that reaches 100% settles with a checkmark. The "watch it complete" beat as real fluid, not a bar.
// Deterministic (level + waves = fn of t).
//
// THE LEVEL IS THE FILM'S `pct`, AND ONLY A FULL VESSEL GETS A CHECK. An earlier fix stopped the numeral being
// the animation's own progress, but left the LIQUID on the clock: whatever `pct` said, the vessel filled to the
// brim and a checkmark replaced the numeral, so `pct: 40` ended as a full vessel with a check — "done" drawn
// over a figure that says it is not — and a film that gave no figure at all still got a full vessel and a check.
// Now the liquid rises to `pct`% and holds there, the numeral counts up through runtime/figure.ts and lands on
// the film's own figure, and the checkmark appears only when `pct` is exactly 100. A film that passes no `pct`
// gets no liquid, no numeral and no check — just the empty vessel and its label: the level is the claim, and it
// is the film's to make. The illustrative full vessel appears only in the standalone preview (no props at all).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, fitTextPx} from '../runtime/layout';
import {parseFigure, figureAt, figureText, figureValue} from '../runtime/figure';

export const DURATION = 160; // ~5.3s

const readPct = (pct: unknown): number | null => {
  if (pct == null || pct === '') return null;
  const v = typeof pct === 'number' ? pct : figureValue(pct);
  if (v == null || !Number.isFinite(v) || v < 0 || v > 100) {
    throw new Error(`LiquidFill: \`pct\` must be one number from 0 to 100 (got ${JSON.stringify(pct)}). The liquid is ` +
      'drawn to that level, so a range, a word, or more than a full vessel cannot be drawn — pass the sourced ' +
      'percentage, or omit `pct` to draw no level.');
  }
  return v;
};

// `pct` has NO default for a film (see header). The numeral appears only when the film has a figure to put there.
export const LiquidFill: React.FC<{label?: string; pct?: number | string | null}> = ({
  // `label` is bound twice: `labelGiven` is what the film passed (undefined if nothing), `label` carries the
  // preview copy. Only "nothing passed at all" unlocks the preview's illustrative full vessel.
  label: labelGiven, label = 'on your machine', pct} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const standalone = labelGiven === undefined && pct === undefined;
  const level = standalone ? 100 : readPct(pct);
  // the film's figure as it will be printed: a string keeps its own form ("40%", "约 40%"); a bare number is a
  // percentage by this prop's definition, so it is printed with its "%"
  const figText = level == null ? '' : standalone ? '100' : figureText(pct);
  const pctSuffix = level != null && (standalone || typeof pct === 'number');

  // LAYOUT, fitted to the content zone: the label used to sit at min(cy + R + 70, contentBottom - 52), which at
  // 16:9 put it ACROSS the bottom of a 300px vessel centred on H/2. The vessel now sits above its label.
  const labelTop = contentBottom(W, H) - 52;
  const zoneTop = 60, zoneBottom = labelTop - 24;
  const R = Math.max(60, Math.min(300, (zoneBottom - zoneTop) / 2, W * 0.4));
  const cx = W / 2, cy = (zoneTop + zoneBottom) / 2;
  const k = R / 300;                                   // type scales with the vessel it sits in
  const p = easeInOutCubic(seg(t, 0.1, 0.62));         // fill progress, settled by t = 0.62
  const frac = level == null ? 0 : (level / 100) * p;  // the liquid's fraction of the vessel's height
  const surface = cy + R - 2 * R * frac;               // liquid surface y
  const full = level === 100;
  const done = full ? seg(t, 0.64, 0.8) : 0;           // the check exists only for a full vessel

  // wave surface path across the vessel bbox, clipped to the circle
  const wave = (amp: number, kk: number, phase: number, extra: number) => {
    const x0 = cx - R - 20, x1 = cx + R + 20, steps = 28;
    let d = `M${x0},${surface + extra}`;
    for (let i = 0; i <= steps; i++) {
      const x = lerp(x0, x1, i / steps);
      const y = surface + extra + Math.sin((x / (2 * R)) * kk * Math.PI * 2 + phase) * amp * k;
      d += ` L${x.toFixed(1)},${y.toFixed(1)}`;
    }
    d += ` L${x1},${cy + R + 40} L${x0},${cy + R + 40} Z`;
    return d;
  };

  const shown = figText ? figureAt(parseFigure(figText), p) : '';
  const labelPx = fitTextPx(label, W * 0.9, 34, {usable: 1, track: 0.06});
  const numPx = Math.min(150 * k, fitTextPx(figText + (pctSuffix ? '%' : ''), R * 1.6, 150 * k, {usable: 1}));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 30%, #0d1830 0%, #060b18 70%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <clipPath id="vessel"><circle cx={cx} cy={cy} r={R} /></clipPath>
          <filter id="goo"><feGaussianBlur in="SourceGraphic" stdDeviation="11" result="b" />
            <feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -10" result="g" />
            <feBlend in="SourceGraphic" in2="g" /></filter>
          <linearGradient id="liq" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#38e0d0" /><stop offset="1" stopColor="#2a7bff" /></linearGradient>
          <filter id="lglow"><feGaussianBlur stdDeviation="8" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>

        {/* liquid + bubbles, merged by the gooey filter, clipped to the vessel — only when the film gave a level */}
        {level == null || level === 0 ? null : (
          <g clipPath="url(#vessel)">
            <g filter="url(#goo)" fill="url(#liq)">
              <path d={wave(20, 2, t * 7, 0)} opacity={0.95} />
              <path d={wave(14, 3, t * 9 + 1.6, 8)} opacity={0.6} />
              {/* rising metaball bubbles inside the liquid */}
              {[0, 1, 2, 3].map((i) => {
                const rise = ((t * (0.5 + i * 0.12) + i * 0.25) % 1);
                const by = (cy + R) - rise * (2 * R * frac + 40);
                const bx = cx + Math.sin(i * 2 + t * 3) * (R * 0.5);
                if (by > surface - 6) return <circle key={i} cx={bx} cy={by} r={(16 + (i % 2) * 10) * k} />;
                return null;
              })}
            </g>
          </g>
        )}

        {/* THE VESSEL IS DRAWN ON THE FILM'S PAGE, so its two rules are the film's colours. The ring was a
            fixed slate and its inner highlight a fixed pale cyan — a highlight is a lift off a dark ground and
            on paper it is simply lighter than the paper, which is how the rim of the vessel disappeared at the
            top on a warm-white film (scripts/ink_contrast_qa.py). `dim` because the ring is structure a reader
            must see and `line`/`surfaceBorder` sit far too faint for a 6px rule that carries the shape. */}
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={dna?.dim ?? '#4b6a9c'} strokeWidth={6} />
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={dna?.accent ?? '#7fd8ff'} strokeWidth={2} opacity={0.5} filter="url(#lglow)" />
      </svg>

      {/* centre readout: the film's figure, counted up WITH the fill — and, for a full vessel only, a checkmark */}
      <div style={{position: 'absolute', left: cx - R, top: cy - R, width: 2 * R, height: 2 * R,
        display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        {!figText ? null : done < 0.15 ? (
          // THE FIGURE READS ON BOTH OF ITS GROUNDS. It is drawn inside the vessel, which is the film's own
          // page where the liquid has not reached and the liquid's mid-tone teal-to-blue where it has — so the
          // film's ink works for both: near-white over a dark page (as before), near-black over paper, and
          // either one clears 4:1 on the liquid itself. A literal near-white cleared only the first of those.
          <div style={{color: dna?.fg ?? '#eaf6ff', font: `800 ${numPx}px/1 var(--f-display, Inter, system-ui, sans-serif)`, fontVariantNumeric: 'tabular-nums',
            textShadow: '0 4px 30px #000a', whiteSpace: 'nowrap'}}>{shown}{pctSuffix ? <span style={{fontSize: numPx * 70 / 150, opacity: 0.7}}>%</span> : null}</div>
        ) : (
          <svg width={360 * k} height={360 * k} viewBox="-180 -180 360 360" style={{transform: `scale(${easeOutBack(done)})`}}>
            <path d="M-88,6 L-26,74 L96,-78" fill="none" stroke="#eafff8" strokeWidth={34} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>
      {/* the caption under the vessel is metadata on the film's own page — `dim`, not a fixed pale blue that
          only exists against a dark one */}
      <div style={{position: 'absolute', left: 0, right: 0, top: Math.min(cy + R + 44, labelTop), textAlign: 'center',
        color: dna?.dim ?? '#8fb0d8', font: `600 ${labelPx}px/1 var(--f-mono, "JetBrains Mono", monospace)`, letterSpacing: '0.06em'}}>{label}</div>
    </AbsoluteFill>
  );
};
export default LiquidFill;
