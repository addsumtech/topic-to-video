// SpeedLimit — why you can't just go faster, with text that STAYS IN ITS LAYOUT (the old circuit shot spilled
// its node labels). A quantity bar rises and is blocked by one or two CEILINGS — in the demo, the gradient
// speed stopped by the hardware slew-rate limit, with peripheral nerve stimulation above it — so it can't go
// higher; a conclusion line names the lever that is left. Labels sit OUTSIDE the bar with room, never inside
// cramped nodes. Deterministic (pure fn of useT).
//
// EVERY WORD AND EVERY CEILING IS THE FILM'S. This register was built for one MRI beat and wrote that beat's
// argument straight into the JSX: "gradient speed", "hardware: slew-rate limit", "patient: nerve
// stimulation", "blocked" and "→ skip k-space lines instead" — declared as INTRINSIC_TEXT, as though they
// were axis furniture, while LIBRARY.md offered the register for any "hard physical limit on going faster".
// A film about a battery charging curve or a road speed limit that took it got an MRI slew-rate ceiling and
// was told to skip k-space lines, and only `label` could be changed. The two ceilings' heights were fixed
// too (`hwY` at 0.28, `pnsY` at 0.14 of the track), so the frame also asserted WHICH limit binds first — a
// ranking nobody had supplied. All five are props now, each defaulting to the words it replaced, so the
// original film renders identically and the demo-copy gate lists every one a film leaves unset. The ceilings
// are `limits`: the ORDER given is the claim (the first is the one the bar jams against, the second sits
// above it), or, when the film knows where they sit, a `level` on every ceiling places them and the lowest
// binds. A supplied ceiling with no label, a third ceiling, or levels on only some of them THROW.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA, readableOn} from '../runtime/dna';
import {bottomTextY, cjkAdvance, CJK_FIT_ADVANCE, fitTextPx, latinAdvance, textWidthPx} from '../runtime/layout';

export const DURATION = 165; // 5.5s

export type SpeedCeiling = {
  /** what imposes this limit */
  label: string;
  /** where the ceiling sits on the track: 0 = the foot, 1 = the top. Give it on EVERY ceiling or on none —
   *  without levels the ceilings stack in the order given, the first one lowest (the one that binds). */
  level?: number;
};

export const MAX_SPEED_CEILINGS = 2;
// the slots an order-only list lands in — exactly where the two ceilings of the original film always sat
const SLOT_LEVELS = [0.72, 0.86];
const DEFAULT_LIMITS: (string | SpeedCeiling)[] = ['hardware: slew-rate limit', 'patient: nerve stimulation'];

const WARN = '#ff5d6c';

const normalise = (limits: unknown): {label: string; level: number}[] => {
  if (!Array.isArray(limits) || limits.length < 1 || limits.length > MAX_SPEED_CEILINGS) {
    throw new Error(
      `SpeedLimit draws 1-${MAX_SPEED_CEILINGS} ceilings in \`limits\` (got ${Array.isArray(limits) ? limits.length : typeof limits}). ` +
      'The bar jams against the lowest one and a second sits above it; more limits than that are a list — ' +
      'cast a list or comparison register instead.');
  }
  const items = limits.map((l: any, i: number) => {
    const label = String(typeof l === 'string' ? l : l?.label ?? '').trim();
    if (!label) throw new Error(`SpeedLimit: ceiling ${i + 1} has no label — pass \`limits: [{label}]\` naming what imposes it.`);
    const raw = typeof l === 'string' ? undefined : l?.level;
    return {label, raw};
  });
  const withLevel = items.filter((x) => x.raw != null).length;
  if (withLevel && withLevel !== items.length) {
    throw new Error(
      'SpeedLimit: give `level` on EVERY ceiling or on none. With none, the order you list them in decides ' +
      'which binds (the first, drawn lowest); a level on only some would leave the rest placed by a guess.');
  }
  const out = items.map((x, i) => {
    if (x.raw == null) return {label: x.label, level: SLOT_LEVELS[i]};
    const level = Number(x.raw);
    if (!Number.isFinite(level) || level <= 0.05 || level >= 0.95) {
      throw new Error(`SpeedLimit: ceiling ${i + 1} ("${x.label}") needs a level strictly between 0.05 and 0.95 ` +
        `of the track (0 = the foot, 1 = the top), got ${JSON.stringify(x.raw)}.`);
    }
    return {label: x.label, level};
  });
  if (out.length === 2 && Math.abs(out[0].level - out[1].level) < 0.08) {
    throw new Error('SpeedLimit: the two ceilings\' levels are less than 0.08 apart, so their lines and labels ' +
      'would draw on top of each other. Separate them, or pass one ceiling.');
  }
  // lowest first: the bar reaches that one and stops, which is what "binding" means on this frame
  return out.sort((a, b) => a.level - b.level);
};

export const SpeedLimit: React.FC<{accent?: string; label?: string; quantity?: string;
  limits?: (string | SpeedCeiling)[]; verdict?: string; instead?: string}> = ({
  accent: accentIn, label = "You can't just go faster", quantity = 'gradient speed',
  limits: LIMITS = DEFAULT_LIMITS, verdict = 'blocked', instead = '→ skip k-space lines instead',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const ceilings = normalise(LIMITS);
  // WHAT THE BAR AND THE CEILINGS ARE MADE OF.
  //
  // Three of this frame's four pieces of copy were near-white literals — the claim at the top (#dfe8f5), the
  // verdict (#eaf6ff) and the axis label (#c9d6ea) — so on a film grounded paper the register drew a red bar
  // under two dashed lines and said none of the words. Those take the film's ink.
  //
  // THE RED STAYS RED. A ceiling is a WARNING and the hue is the meaning, so it is not swapped for the film's
  // accent; only its EXPOSURE is re-picked, from the register's own pair, against the ground it will be read
  // on — #ff5d6c measures 2.70:1 on warm white and its deeper twin 5.0:1, and the frame keeps saying "stop"
  // either way. `readableOn` is the library's measured picker for exactly this.
  const GROUND = dna?.bg ?? '#05060a';
  const accent = accentIn ?? dna?.accent ?? '#22d3ee';
  const WARN_INK = dna ? readableOn(GROUND, WARN, '#b21f2d') : WARN;
  const WARN2_INK = dna ? readableOn(GROUND, '#ff8ad0', '#a01a6e') : '#ff8ad0';
  const WARN2_LINE = dna ? readableOn(GROUND, '#f06ecb', '#a01a6e') : '#f06ecb';
  const WELL = dna?.surface ?? '#0a1424';
  const QTY_INK = dna?.dim ?? '#c9d6ea';
  const VERDICT_INK = dna?.fg ?? '#eaf6ff';
  const LABEL_INK = dna?.fg ?? '#dfe8f5';
  // the axis label is a BASELINE 40px under the track's foot, and the foot was a flat 0.74 of the height —
  // 22px of the quantity label inside the caption band at 1:1. The track shortens; the label stays put.
  // THE LABELS' ROOM IS MEASURED, NOT RESERVED AS 344px. Each ceiling label was placed with a literal
  // width held back from the frame edge — `Math.min(bx + 230, W - 344)` — and 344 is how wide these words
  // are in INTER, the fallback in the font shorthand below. The face that actually renders is the DNA's
  // body stack: under `terminal` and `blueprint` it is JetBrains Mono, whose advance is 0.62 against
  // Inter's 0.52, and the same words run 16px and 30px off the right edge while the conclusion runs 73px
  // off the left. `latinAdvance` is the shared rule for exactly this question, and it takes the stack.
  // AND NOW THAT THE WORDS ARE THE FILM'S, THEIR SIZE IS FITTED TO THAT ROOM TOO. The demo copy at 16:9 has
  // more room than it needs and keeps its 24/30px exactly; a longer label, or a portrait frame, steps the
  // size down instead of sliding the words back across the dashed line and the track.
  const adv = latinAdvance(dna?.fontBody);
  const cjk = Math.max(CJK_FIT_ADVANCE, cjkAdvance(dna?.fontBody));
  const edge = Math.round(W * 0.02);
  const fit = (x: string, room: number, base: number) => Math.min(base, fitTextPx(x, room, base, {usable: 1, adv, cjk}));
  const wOf = (x: string, px: number) => textWidthPx(x, px, {adv, cjk});
  const bx = W * 0.5, trackTop = H * 0.26;
  const trackBot = Math.min(H * 0.74, bottomTextY(W, H) - 40);
  const trackH = trackBot - trackTop;
  const yOf = (level: number) => trackBot - trackH * level;
  const bindY = yOf(ceilings[0].level);                     // the lowest ceiling — the one the bar jams against
  const rise = clamp01(seg(t, 0.12, 0.62));                 // the bar rises, then jams at the binding ceiling
  const topY = lerp(trackBot, bindY, rise);
  const blocked = rise > 0.96;
  const shake = blocked ? Math.sin(t * 60) * 2 : 0;
  const font = 'var(--f-body, Inter, sans-serif)';

  // ceiling k: the binding one keeps the warning red and the wider line, the one above it the softer pink
  const STYLE = [{half: 210, gap: 230, stroke: WARN_INK, ink: WARN_INK, sw: 2.5, fade: [0.05, 0.3]},
                 {half: 180, gap: 200, stroke: WARN2_LINE, ink: WARN2_INK, sw: 2, fade: [0.1, 0.35]}];
  const qPx = fit(quantity, W - edge * 2, 24);
  const vPx = fit(verdict, bx - 60 - edge, 30);
  const iPx = fit(instead, bx - 60 - edge, 24);
  const concY = trackTop + trackH * 0.55;
  // the conclusion is right-aligned 250px left of the track, pulled right only as far as it must be to stay
  // on the frame — never across the track itself
  const concX = (text: string, px: number) => Math.min(bx - 60, Math.max(bx - 250, edge + wOf(text, px)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <rect x={bx - 46} y={trackTop} width={92} height={trackH} rx={12} fill={WELL} stroke={`${accent}44`} strokeWidth={1.4} />
        <rect x={bx - 40 + shake} y={topY} width={80} height={trackBot - topY} rx={9} fill={blocked ? WARN_INK : accent} opacity={0.9} />
        {quantity ? <text x={bx} y={trackBot + 40} textAnchor="middle" fill={QTY_INK} fontSize={qPx} fontFamily={font} fontWeight={700}>{quantity}</text> : null}

        {/* the ceilings — labels OUTSIDE the track with room */}
        {ceilings.map((c, k) => {
          const s = STYLE[k], y = yOf(c.level), op = clamp01(seg(t, s.fade[0], s.fade[1]));
          const px = fit(c.label, W - edge - (bx + s.gap), 24);
          return (
            <g key={k}>
              <line x1={bx - s.half} y1={y} x2={bx + s.half} y2={y} stroke={s.stroke} strokeWidth={s.sw} strokeDasharray="6 5" opacity={op} />
              <text x={Math.min(bx + s.gap, W - edge - wOf(c.label, px))} y={y + 6} fill={s.ink} fontSize={px} fontFamily={font} fontWeight={700} opacity={op}>{c.label}</text>
            </g>
          );
        })}

        {/* conclusion — left of the track, with room. An empty verdict or `instead` draws nothing. */}
        {verdict ? <text x={concX(verdict, vPx)} y={concY} textAnchor="end" fill={VERDICT_INK} fontSize={vPx} fontFamily={font} fontWeight={800} opacity={clamp01(seg(t, 0.66, 0.86))}>{verdict}</text> : null}
        {instead ? <text x={concX(instead, iPx)} y={concY + 34} textAnchor="end" fill={accent} fontSize={iPx} fontFamily={font} opacity={clamp01(seg(t, 0.72, 0.9))}>{instead}</text> : null}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: LABEL_INK, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default SpeedLimit;
