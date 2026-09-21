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

//
// THE TYPE AND THE AXIS ARE THE FILM'S; THE TILE KEEPS ITS NIGHT. Every word and every tick here was a
// literal picked for a near-black ground, and all eight DNA presets are near-black, so on a film whose DNA
// came from a warm-white deck the title, the cap sentence, the "g-factor noise →" callout, the read-out and
// the whole 1×..5× axis drew light ink on light paper (`scripts/ink_contrast_qa.py`: 45.1% of this
// register's marks under 3:1, largest connected hole 1.26% of the frame). Those are ink and they read from
// the DNA. The TILE is not ink: it is a reconstructed scan viewport whose entire content is white and red
// speckle, and a scan viewport is black in every reader that has ever shown one — on paper it would be a
// white square with nothing on it. It keeps its own dark stop, and so does the grain drawn on it.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';
import {useDNA, mix, contrastOf, readableOn} from '../runtime/dna';
import {INK_CONTRAST_MIN} from '../runtime/light';
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

// The literals this register was authored in, hoisted so an un-themed render is byte-for-byte what it was.
const WARN_D0 = '#ff5d6c';        // the unusable zone, the cap line, the callout, the cap sentence
const TITLE_D0 = '#dfe8f5';       // the title
const READOUT_D0 = '#eaf6ff';     // the live R read-out riding the fill
const TICK_D0 = '#8aa';           // the 1×..5× axis ticks
const ACCENT_D0 = '#22d3ee';      // the tile border, the usable zone and the fill
const TILE_GRAD = 'linear-gradient(160deg,#0e1b30,#0a1424)';   // the tile's own night — see the header

// THE RED IS THE MEANING here (viz-semantics: red = bad), so the mark keeps its hue and only its EXPOSURE
// moves — shading is a linear scale of r:g:b, so a deepened #ff5d6c is the same red. It has to move because
// the red zone, the cap line, the callout and the cap sentence are all drawn ON the film's ground, and a red
// chosen for near-black does not read on paper.
//
// AGAINST THE TEXT FLOOR, NOT THE GRAPHICS ONE. The same red is a fill, a rule and two runs of 20-22px mono
// type, and the type is the demanding job: 3.0 is WCAG's floor for a rule and for LARGE text, which those
// runs are not. Measured through this runtime's own helpers on the ink probe's warm white, the graphics
// floor lands the red at 3.05:1 — over the gate's 3:1 line by five hundredths — and the ink floor lands it
// at #bf4651 / 4.51:1, still plainly red. The band and the rule only gain from the deeper one.
//
// A LADDER, NOT ONE FIXED STEP: a single shade is a constant tuned to the one ground it was checked on, and
// the ground a film derives from a client deck is not that ground. It walks toward whichever pure ink
// MEASURES more on this ground rather than toward the one its key is named after — the same correction
// runtime/light.tsx's `exposeTo` records, so a chromatic ground lifts the red instead of burying it. And it
// stops three-quarters of the way: there, a colour that cannot clear its floor becomes pure ink, which here
// would print "unusable" in black and lose the semantics silently. The hue survives and the mark is as deep
// as red gets.
const DEEPEN_STEPS = 12, DEEPEN_MAX = 0.75;
const readsOn = (c: string, ground: string): string => {
  if (contrastOf(c, ground) >= INK_CONTRAST_MIN) return c;
  const toward = readableOn(ground, '#ffffff', '#000000');
  for (let i = 1; i <= DEEPEN_STEPS; i++) {
    const out = mix(c, toward, (DEEPEN_MAX * i) / DEEPEN_STEPS);
    if (contrastOf(out, ground) >= INK_CONTRAST_MIN) return out;
  }
  return mix(c, toward, DEEPEN_MAX);
};

// `factor` is the amplification the FILM measured. No default: the read-out used to count 1.0x -> 3.0x off
// the clock and print the result as though it had been measured, on whatever topic reached for the register.
// It may be a number or the film's string ("2.5×"); either way it must be exactly one number >= 1, and the
// settled read-out prints it as the film wrote it (a bare number gets the axis unit ×), never rounded.
export const GFactorNoise: React.FC<{accent?: string; label?: string; factor?: number | string | null; cap?: number; limit?: string}> = ({
  accent: ACC, label = 'Unfolding amplifies noise', factor = null,
  cap = 3, limit = 'R = 2–3 max · never beyond the coil count',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // The film's accent when it has one: `groundFrom` has already exposed it for whatever ground the beat is
  // lit on, so the track and the tile's border read there without this register measuring anything.
  const accent = ACC ?? dna?.accent ?? ACCENT_D0;
  const ground = dna?.bg ?? '#05060a';
  const warn = dna ? readsOn(WARN_D0, ground) : WARN_D0;     // on the film's ground — see readsOn
  const ink = dna?.fg ?? TITLE_D0;                           // the title
  const readoutInk = dna?.fg ?? READOUT_D0;                  // the live R read-out
  // The ticks are the AXIS every other mark is drawn against, not metadata that may recede: on its own
  // ground the literal #8aa measured well clear of the ink floor, and `dim` alone would put the scale under
  // it. The house second tier (runtime conventions) is the film's ink pulled 40% toward its own `dim`.
  const tickInk = dna ? mix(dna.fg, dna.dim, 0.4) : TICK_D0;

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
  // The specks are drawn ON the tile's own night, never on the film's ground, so they keep the two literals
  // they were measured for: a warn deepened to read on paper would sink into the dark tile it sits on, and a
  // speck in the film's ink would be a black dot on a black square.
  for (let i = 0; i < n; i++) {
    grain.push(<circle key={i} cx={hash01(i * 2 + 1) * tw} cy={hash01(i * 2 + 7) * th}
      r={0.8 + hash01(i * 3) * 1.6} fill={hash01(i) > 0.7 ? WARN_D0 : '#ffffff'} opacity={0.15 + noise * 0.5} />);
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
        border: `2px solid ${past ? warn : accent}`, background: TILE_GRAD, overflow: 'hidden'}}>
        <svg width={tw} height={th}><g>{grain}</g></svg>
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* track */}
        <rect x={bx} y={by} width={bw * capFrac} height={12} rx={6} fill={accent} opacity={0.28} />
        <rect x={bx + bw * capFrac} y={by} width={bw * (1 - capFrac)} height={12} rx={6} fill={warn} opacity={0.3} />
        {/* the fill — only for a factor the film supplied */}
        {F == null ? null : <rect x={bx} y={by} width={bw * frac(R)} height={12} rx={6} fill={past ? warn : accent} />}
        <line x1={bx + bw * capFrac} y1={by - 20} x2={bx + bw * capFrac} y2={by + 32} stroke={warn} strokeWidth={2} strokeDasharray="4 4" />
        <text x={bx + bw * capFrac} y={by - 28} fill={warn} fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" textAnchor="middle">g-factor noise →</text>
        {ticks.map((v) => (
          <text key={v} x={bx + bw * frac(v)} y={by + 52} fill={tickInk} fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" textAnchor="middle">{v}×</text>
        ))}
        {/* the live R read-out — drawn only when the film supplied a measured factor. It sits ABOVE the zone
            label: at the old by-22 a factor near the cap printed its number straight through "g-factor noise". */}
        {F == null ? null : (
          <text x={bx + bw * frac(R)} y={by - 62} fill={readoutInk} fontSize="40" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} textAnchor="middle">
            {readout}</text>
        )}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}
        {String(limit ?? '').trim() ? (
          <div style={{marginTop: 8, font: "600 22px/1 var(--f-mono, 'JetBrains Mono', monospace)", color: warn, letterSpacing: '0.12em'}}>
            {limit}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default GFactorNoise;
