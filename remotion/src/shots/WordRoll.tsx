// SHOT · Word Roll — one sentence with a slot in it, and the slot cycles: the alternatives roll through it like a
// split counter (or scramble into place, or flip), each one held long enough to read, until it lands on the last.
//
// WHAT IT ARGUES. "It is not X, not Y — it is Z", or "the same sentence is true of A, of B and of C". The sentence
// stays put and only the slot changes, so the viewer reads the frame once and then watches ONE place: what is
// constant and what varies is the composition itself, not a caption explaining it. The order is the film's: the last
// alternative is the one it lands on and keeps. Not for a list of peers read together (a list register), not for a
// single statement (HeadlineReveal).
//
// HOW IT MOVES. Roll — stripe.com's digit roller, measured on the live site: each glyph a strip that travels a full
// line through its clip, 325-420 ms on (.33,1,.68,1), staggered glyph by glyph. Scramble — GSAP ScrambleText's idea:
// random glyphs of the copy's OWN script resolving left to right, changing on twos. Flip — a split-flap's collapse
// and open, in 2D so the type stays sharp. An underline under the slot changes width WITH the word (the container
// stays, its size animates — Material's container transform), so the slot reads as one place that holds different
// things. Each arrival may be cued: `options.N` moves EARLIER onto the word that says it.
//
// HOW LONG EACH HOLDS is the gate's question, not a hope: scripts/shot_proof.py asks this register's own clock, at
// the beat's real length, how long every alternative is readable, and reports one held under its reading time.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, contrastOf} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {useCues} from '../runtime/cue';
import {useKinetic, KineticText, KMotion} from '../runtime/kinetic';
import {KineticWord} from '../runtime/kineticWord';
import {swapTimes, EASES, secToT, readingSeconds, graphemes} from '../runtime/kineticCore';

// 7s, not the house 5.5: every alternative needs its own reading time AND a change between each, and at 6s the
// demo's three (one word, one word, three) came back from the hold gate a third of a second short of being read.
// (In a film this number is not used — the beat's own length is, and the gate measures against that.)
export const DURATION = 210;
// THE PACE IS IN SECONDS (validate.py reads this). Authored in shares of the beat, a 3–4 s beat played this
// register's 7 s design 2.1–2.4x fast and the second option was readable 0.73 s against 0.83 s (bench-launch). Every
// time below is a duration in seconds, shrunk on a short beat only down to a floor, and the reading floors are paid
// FIRST: each option gets its read-once time before any of the rest is shared out by must-read time. A beat too short
// for even that is the hold gate's finding (scripts/shot_proof.py), measured, not this file's guess.
export const PACE = 'seconds';
export const MIN_OPTIONS = 2, MAX_OPTIONS = 6;
// the fallback spacing (t) when the beat cannot pay the floors — the gate then names what cannot be read
const FIRST = 0.3, LAST = 0.74;
// a change: the glyph's roll and the stagger across the arriving word, at their natural length on a long beat and
// never shorter than the floor (0.24 s still reads as a roll; under it the word blinks)
const TURN_S = 0.38, TURN_MIN_S = 0.24, STAGGER_S = 0.028;

const BG_D0 = '#0d0f14', FG_D0 = '#f1f2f5', ACC_D0 = '#ffb547';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// Placeholder copy that describes the register itself, so it is no film's fact.
const DEMO_OPTIONS = ['here', 'there', 'on its word'];

export const WordRoll: React.FC<{
  kicker?: string;
  /** the sentence before the slot */
  before?: string;
  /** what the slot cycles through, in order; it lands on the LAST and keeps it */
  options?: string[];
  /** the sentence after the slot, if it goes on */
  after?: string;
  /** how the slot changes */
  mode?: 'roll' | 'scramble' | 'flip';
  /** what the landed option does while it holds: `alive` — a breath of tracking and a light passing along it;
   *  `still` — nothing */
  hold?: 'alive' | 'still';
  accent?: string;
}> = ({kicker = 'ONE SLOT', before = 'The same line can end', options: optionsIn = DEMO_OPTIONS, after = '',
       mode = 'roll', hold = 'alive', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H, fps} = useVideoConfig();
  const spanF = useAnimSpan();
  const cue = useCues();
  const OPTS = rows<string>(optionsIn, 'options', 'WordRoll').map((s) => String(s ?? '').trim());
  if (OPTS.length < MIN_OPTIONS) {
    throw new Error(`WordRoll needs at least ${MIN_OPTIONS} options for its slot, got ${OPTS.length}: one option is ` +
      'a sentence, not a slot. Use HeadlineReveal.');
  }
  if (OPTS.length > MAX_OPTIONS) {
    throw new Error(`WordRoll cycles at most ${MAX_OPTIONS} options, got ${OPTS.length}. Past that each one is gone ` +
      'before it can be read; keep the ones the beat argues with.');
  }
  const empty = OPTS.findIndex((o) => !o);
  if (empty >= 0) throw new Error(`WordRoll was given an empty option (index ${empty}); a slot with nothing in it reads as a fault.`);

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);

  const U = Math.min(W, H);
  const portrait = W < H;
  const colW = Math.round(W * (portrait ? 0.84 : 0.78));
  const x0 = Math.round((W - colW) / 2);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H), zoneH = zoneBot - zoneTop;
  const KICK = Math.ceil(U * 0.028);
  const gap = Math.round(U * 0.03);

  // the slot is fitted on its WIDEST alternative, so every one is set at one size and the slot never jumps.
  // IN A TALL FRAME THE SLOT MAY TAKE TWO LINES. Held to one line, a long option set the whole slot at ~80 px in a
  // 1920-tall frame (bench-launch: 2.5–3% ink) — the width bounds the type and the height is empty. So in portrait the
  // first tier keeps every option on one line only down to a display floor; past it an option wraps (at a word) at a
  // size that fills the frame.
  const slot = useKinetic({alts: OPTS, w: colW, nowrap: !portrait, fit: 'box', align: 'left', wrap: 'balance',
    ...(portrait ? {h: Math.round(zoneH * 0.42), maxLines: 2,
      fitTiers: [{maxLines: 1, minSize: Math.round(U * 0.13)}, {maxLines: 2}]} : {}),
    font: {family: DISPLAY, weight: 680, size: Math.round(U * (portrait ? 0.22 : 0.16)), minSize: Math.round(U * 0.06),
      lineHeight: 1.08, tracking: -0.02}});
  const slotSize = slot.layout?.size ?? U * 0.12;
  const leadSize = Math.round(U * (portrait ? 0.088 : 0.072));
  const lead = useKinetic({text: before || ' ', w: colW, h: Math.round(zoneH * (portrait ? 0.26 : 0.32)), fit: 'box',
    maxLines: 3, align: 'left', wrap: 'balance', font: {family: DISPLAY, weight: 500, size: leadSize,
      minSize: Math.ceil(U * 0.04), lineHeight: 1.1, tracking: -0.015}});
  const tail = useKinetic({text: after || ' ', w: colW, h: Math.round(zoneH * 0.22), fit: 'box', maxLines: 2,
    align: 'left', wrap: 'balance', font: {family: DISPLAY, weight: 500, size: leadSize,
      minSize: Math.ceil(U * 0.04), lineHeight: 1.1, tracking: -0.015}});
  const kick = useKinetic({text: kicker || ' ', w: colW, nowrap: true, fit: 'box', align: 'left',
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});

  // THE BLOCK IS CENTRED ON WHAT IT MEASURES, the text inside it stays flush left. Set flush left at the column's
  // edge, a short sentence filled 43% of the frame's width from one side and the proof sheet called the other side
  // dead; centred on the widest thing it holds (the sentence, any alternative, the tail), it sits in the frame.
  const blockW = Math.max(before ? (lead.layout?.width ?? colW) : 0, slot.layout?.width ?? colW,
    after ? (tail.layout?.width ?? 0) : 0);
  const bx = Math.round(x0 + Math.max(0, (colW - blockW) / 2));
  const kickH = kicker ? Math.round(KICK * 1.25) + gap : 0;
  const leadH = before ? (lead.layout?.height ?? zoneH * 0.2) : 0;
  const slotH = slot.layout?.height ?? slotSize * 1.08;
  const ulGap = Math.round(slotSize * 0.06), ulH = Math.max(3, Math.round(slotSize * 0.045));
  // the frame is held until the measured height replaces this (runtime/kinetic useKinetic)
  // @fallback: the room reserved for the tail before its measurement lands — layout, never drawn as a value
  const tailH = after ? (tail.layout?.height ?? 0) : 0;
  // the slot's clip is its own line box: the room above it is where an outgoing word disappears, so it is kept
  // clear of the sentence (a tighter gap read as the word sliding INTO the line above)
  const slotGap = Math.round(gap * 1.1);
  const blockH = kickH + leadH + (before ? slotGap : 0) + slotH + ulGap + ulH + (after ? gap + tailH : 0);
  const top = Math.round(zoneTop + Math.max(0, (zoneH - blockH) / 2));
  const yLead = top + kickH, ySlot = yLead + leadH + (before ? slotGap : 0);
  const yUl = ySlot + slotH + ulGap, yTail = yUl + ulH + gap;

  // ── THE SCHEDULE, in seconds: each alternative's read-once time first, then the rest by must-read time ─────
  // Even spacing gave "here" and "on its word" the same time, so the one-word options were over-held and the
  // three-word ending — the one the sentence lands on — fell under its reading time; a share-only split (the first
  // fix) still let a short beat hand one option less than it takes to read once while others got more. Now the beat
  // pays every option its read-once time (runtime/readingSpec.json, the table the hold gate reads), then shares what is
  // left in proportion to the must-read time. Each change takes its own turn — the roll, shrunk on a short beat to
  // TURN_MIN_S — plus the stagger across the arriving word. Only when the floors themselves do not fit does it fall
  // back to even spacing, and scripts/shot_proof.py names the option that cannot be read.
  const n = OPTS.length;
  const spanS = Math.max(0.5, spanF / fps);
  const turnS = Math.max(TURN_MIN_S, Math.min(TURN_S, spanS * 0.07));
  const stagS = Math.min(STAGGER_S, turnS * 0.08);
  const glyphsOf = (j: number) => Math.max(1, graphemes(OPTS[j]).length);
  // a change's whole length (the underline follows it)
  const tr = OPTS.map((_, j) => (j === 0 ? 0 : secToT(turnS + stagS * (glyphsOf(j) - 1), spanF, fps)));
  // WHAT A CHANGE COSTS IN READING TIME is not its whole length: the leaving option stops being readable a fraction
  // into the turn and the arriving one starts being readable a fraction in (the hold gate's own criterion — half of
  // a glyph inside its clip, not scrambled, half its flip height). Reserving the whole turn per change, the first
  // version of this schedule refused three Chinese options at a 4 s beat that the gate can read; the fraction is the
  // turn's share before the arriving option reads, per mode, with a margin.
  const readFrac = mode === 'scramble' ? 0.8 : mode === 'flip' ? 0.55 : 0.3;
  const gapS = (j: number) => stagS * (glyphsOf(j) - 1) + readFrac * turnS;
  // option 0 reads once its entrance has risen half-way through its clip — not at the end of the sentence's entrance
  const slotEnterS = Math.max(0.35, Math.min(0.6, spanS * 0.1));
  const slotAtS = 0.03;
  const LANDED = 0.06 + secToT(slotAtS + stagS * (glyphsOf(0) - 1) + slotEnterS * 0.6, spanF, fps);
  const ENTERED = 0.06 + secToT(slotAtS + stagS * (glyphsOf(0) - 1) + slotEnterS + 0.02, spanF, fps);
  const once = OPTS.map((o) => readingSeconds(o).once), must = OPTS.map((o) => readingSeconds(o).must);
  const budgetS = ((1 - LANDED) * (spanF / fps)) / 0.94 - OPTS.reduce((a, _o, j) => a + (j ? gapS(j) : 0), 0);
  const onceSum = once.reduce((a, b) => a + b, 0), mustSum = must.reduce((a, b) => a + b, 0);
  // a beat that cannot pay the floors still gets them in PROPORTION (each option the same share of what it needs), so
  // the shortfall is spread instead of landing on whichever option even spacing happened to shortchange — and the hold
  // gate names every option that falls under its read-once time
  const holdS = budgetS >= onceSum ? once.map((o, j) => o + ((budgetS - onceSum) * must[j]) / mustSum)
    : budgetS > 0 ? once.map((o) => (budgetS * o) / onceSum) : null;
  const times: number[] | undefined = holdS ? [0] : undefined;
  if (times && holdS) {
    let at = LANDED;
    for (let j = 0; j < n - 1; j++) {
      at += secToT(holdS[j] + gapS(j + 1), spanF, fps);
      times.push(at);
    }
  }
  const TURN = turnS, STAGGER = stagS;
  // the same schedule the slot runs on (runtime/kineticCore swapTimes) — the underline's width follows it
  const cueKeys = OPTS.map((_, i) => `options.${i}`);
  const T = swapTimes(n, FIRST, LAST, cueKeys.map((c) => cue.readT(c)), times);
  // the landed option stays alive while it holds (runtime/kinetic `idle`): a breath of tracking, a light along it
  const idle: KMotion['idle'] = hold === 'alive'
    ? {breathe: 0.006, period: 3.4, light: {color: FG, every: 3.2, dur: 1.0, strength: 0.4}, delay: 0.2} : undefined;
  let k = 0;
  for (let i = 1; i < T.length; i++) if (t >= T[i]) k = i;
  const widths = slot.layout?.alts.map((a) => a.width) ?? OPTS.map(() => colW * 0.5);
  const trans = k === 0 ? 1e-6 : tr[k];
  const p = k === 0 ? 1 : EASES.stripe(clamp01((t - T[k]) / Math.max(1e-6, trans)));
  const ulW = k === 0 ? widths[0] : widths[k - 1] + (widths[k] - widths[k - 1]) * p;
  const ulIn = easeOutCubic(clamp01(seg(t, 0.14, 0.26)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <KineticText k={kick} x={bx} y={top} color={ACC} read={false} id="kicker"
          motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.06, stagger: 0.03, dur: 0.45,
            ease: 'power3', cueKeys: ['kicker'], until: 0.36}}} />
      ) : kick.anchor}
      {before ? (
        <KineticText k={lead} x={bx} y={yLead} color={FG} id="before"
          motion={{mask: 'word', from: {ymask: 1.02}, enter: {by: 'word', at: 0.08, stagger: 0.06, dur: 0.7,
            ease: 'expo', cueKeys: ['before'], until: 0.3}}} />
      ) : lead.anchor}
      {/* the slot is the `word` carry anchor (runtime/kineticWord): a seam can take hold of the option it lands on */}
      <KineticWord k={slot} x={bx} y={ySlot} color={ACC} id="slot"
        motion={{from: {ymask: 1.02}, enter: {by: 'grapheme', at: 0.06 + secToT(slotAtS, spanF, fps), stagger: STAGGER, dur: slotEnterS,
          ease: 'expo', until: ENTERED}, swap: {mode, first: FIRST, last: LAST, times, turn: TURN, stagger: STAGGER,
          cueKeys, seed: 11}, idle}} />
      {/* the slot's underline: one place, holding different things — its width follows the word in it */}
      <div style={{position: 'absolute', left: bx, top: yUl, height: ulH, width: Math.max(0, ulW),
        background: ACC, opacity: 0.9, transformOrigin: '0 50%', transform: `scaleX(${ulIn})`}} />
      {after ? (
        <KineticText k={tail} x={bx} y={yTail} color={FG} id="after"
          motion={{from: {opacity: 0, y: 0.35}, enter: {by: 'word', at: 0.2, stagger: 0.05, dur: 0.6, ease: 'power3',
            cueKeys: ['after'], until: 0.4}}} />
      ) : tail.anchor}
    </AbsoluteFill>
  );
};
export default WordRoll;
