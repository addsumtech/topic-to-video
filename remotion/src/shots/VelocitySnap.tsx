// SHOT · Velocity Snap — Linear/Stripe language: a UI ASSEMBLES in a blink, each element flying in and
// SNAPPING into place with a micro-bounce + a motion-blur streak on arrival. Signals raw speed / "instant".
// Dark premium + Linear-purple (adds a snappy dark language). Deterministic (blur ∝ per-element velocity).
//
// THE FIGURE IS THE FILM'S, WITH THE FILM'S UNIT, OR THERE IS NONE. `metric` defaulted to '0' and `unit` to 'ms'
// independently, so a film that passed only `label` shipped a big "0ms" beside its own words, and one that
// passed `metric: '1.2 秒'` with no unit printed "1.2 秒ms" — a unit nobody supplied, welded onto a sourced
// figure. The illustrative "0ms" is now one piece that appears only in the standalone preview (no `label`,
// `metric` or `unit` passed at all). A film's metric carries exactly the unit the film wrote, or none, and a
// film with no metric gets no figure. The metric is printed through runtime/figure.ts `figureText` — as
// written, never re-formatted — and sized to the room above the panels.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA, mix, shade} from '../runtime/dna';
import {Figure} from '../runtime/atoms';
import {figureText} from '../runtime/figure';
import {textWidthPx} from '../runtime/layout';
import {useGlide} from '../runtime/glide';

export const DURATION = 120; // 4s — snappy
const PUR0 = '#7C89FF', BG = '#0c0d14';

type Piece = {x: number; y: number; w: number; h: number; dx: number; dy: number; at: number; c?: string};

export const VelocitySnap: React.FC<{label?: string; metric?: string; unit?: string}> = ({
  // `label` and `metric` are each bound twice on purpose: `labelIn` / `metricIn` are what the film actually
  // passed (undefined when it passed nothing); the defaulted names hold the preview's illustrative copy. Only
  // "nothing passed at all" may unlock the demo figure.
  label: labelIn, label = 'Done.', metric: metricIn, metric = '0', unit} = {}) => {
  const t = useT();
  const glide = useGlide();
  const dna = useDNA(); const PUR = dna?.accent ?? PUR0;
  // A PANEL IS A SURFACE, NOT A DARK WORLD — it takes the film's ground and its ink like everything else.
  // The fills and borders were dark literals, which is what this register's own card means by "a light,
  // paper-toned film breaks it (the panels stay dark)": on a warm-white DNA five navy blocks sat on the page
  // and the film reached only the accent panel and the backdrop. With no DNA the originals still render.
  const PANEL = dna?.surface ?? '#161826';
  const PANEL_BORDER = dna?.surfaceBorder ?? '#242741';
  // The accent panel's second gradient stop was a hardcoded indigo, so on a themed film it OVERRODE the
  // film's hue across half of the one panel that carries the word — the defect CrashZoom's hero card already
  // records. Derived from the film's own two hues; with no DNA the original indigo is exactly what renders.
  const PUR_DEEP = dna ? shade(mix(PUR, dna.accent2 ?? PUR, 0.45), 0.3) : '#5a63d8';
  const {width: W} = useVideoConfig();
  const standalone = labelIn === undefined && metricIn === undefined && unit === undefined;
  const figure = figureText(standalone ? metric : metricIn);
  const UNIT = standalone ? 'ms' : (unit ?? '');
  // the figure's right-aligned block has everything from the left margin to its own right inset; a long film
  // string ("不到 1 秒") shrinks to fit rather than running off the left edge. Never larger than the 120px it was.
  const metricPx = Math.max(40, Math.min(120, Math.floor((W - 150 - 130) /
    Math.max(0.1, textWidthPx(figure, 1) + textWidthPx(UNIT, 1)))));
  // UI sits in the LEFT band; the big "0ms" gets a clear RIGHT band (no overlap).
  const cx = 130, cy = 300;
  const pieces: Piece[] = [
    {x: cx, y: cy, w: 1240, h: 90, dx: 0, dy: -120, at: 0.06},
    {x: cx, y: cy + 120, w: 360, h: 480, dx: -220, dy: 0, at: 0.12},
    {x: cx + 390, y: cy + 120, w: 500, h: 300, dx: 0, dy: 160, at: 0.18, c: PUR},
    {x: cx + 390, y: cy + 450, w: 500, h: 150, dx: 0, dy: 200, at: 0.26},
    {x: cx + 920, y: cy + 120, w: 320, h: 220, dx: 220, dy: 0, at: 0.22},
    {x: cx + 920, y: cy + 360, w: 320, h: 240, dx: 220, dy: 120, at: 0.30},
  ];
  const doneAll = t > 0.44;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? `radial-gradient(120% 100% at 50% 30%, #14162a, ${BG} 62%)`}}>
      {pieces.map((p, i) => {
        const r = clamp01(seg(t, p.at, p.at + 0.14));
        const e = easeOutBack(r);
        const vel = 1 - easeOutCubic(r);
        const blur = r < 0.75 ? 22 * vel : 0;
        const tx = lerp(p.dx, 0, e), ty = lerp(p.dy, 0, e);
        const pulse = doneAll ? 1 + 0.012 * Math.max(0, Math.sin((t - 0.44) * 30)) * Math.exp(-(t - 0.44) * 6) : 1;
        const flying = e !== 1 || pulse !== 1;
        return <div key={i} style={{position: 'absolute', left: p.x, top: p.y, width: p.w, height: p.h,
          opacity: clamp01(r * 2), transform: glide(`translate(${tx}px, ${ty}px) scale(${pulse})`, flying)}}>
          {/* the motion-blur streak is its own layer: a blur() on the SAME element as the flying transform
              keeps only the scale of the matrix above it, so the unlock above would never reach the word
              drawn inside it (runtime/glide.ts) — the word below carries a second, local one instead. */}
          <div style={{position: 'absolute', inset: 0,
            filter: blur > 0.5 ? `blur(${blur}px)` : undefined,
            background: p.c ? `linear-gradient(150deg, ${p.c}, ${PUR_DEEP})` : PANEL,
            border: `1px solid ${p.c ? 'transparent' : PANEL_BORDER}`, borderRadius: 16,
            boxShadow: '0 20px 50px rgba(0,0,0,.4)'}}>
            {/* the word sits ON the accent fill, so its ink is the film's `onAccent`, not a literal white:
                across the eight presets white measures 1.77–3.51:1 on their own accents and `onAccent`
                5.35–10.70:1, and at the gradient's deep end 1.77–3.51 against 3.20–5.01. */}
            {p.c && <div style={{position: 'absolute', left: 30, bottom: 26, transform: glide(undefined, flying),
              font: '800 66px/1 var(--f-display, Inter,system-ui,sans-serif)', color: dna?.onAccent ?? '#fff'}}>{label}</div>}
          </div>
        </div>;
      })}
      {figure ? <div style={{position: 'absolute', right: 150, top: 150, textAlign: 'right', opacity: easeOutCubic(seg(t, 0.4, 0.55))}}>
        {/* fallbackForm/fallbackFamily make explicit what previously worked only because NEUTRAL_DNA.fontDisplay
            happens to match this shot's hardcoded Inter stack — a coincidence, not a contract, until now. */}
        {/* THE FIGURE STANDS ON THE GROUND, so it is the film's ink. `ink="#fff"` is where this register's
            measured failure was: on a warm-white DNA the whole value read 1.06:1 — the only thing left of it
            was the unit, in the accent, beside nothing (scripts/ink_contrast_qa.py, 2026-09-20: 60% of the
            register's marks under 3:1, and they were all this number). */}
        <div><Figure value={figure} unit={UNIT} ink={dna?.fg ?? '#fff'} tone={PUR} size={metricPx} unitScale={1}
          fallbackForm="display" fallbackFamily="Inter, system-ui, sans-serif" /></div>
      </div> : null}
    </AbsoluteFill>
  );
};
export default VelocitySnap;
