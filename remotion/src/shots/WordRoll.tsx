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
import {useKinetic, KineticText} from '../runtime/kinetic';
import {swapTimes, EASES, secToT, readingSeconds, graphemes} from '../runtime/kineticCore';

// 7s, not the house 5.5: every alternative needs its own reading time AND a change between each, and at 6s the
// demo's three (one word, one word, three) came back from the hold gate a third of a second short of being read.
// (In a film this number is not used — the beat's own length is, and the gate measures against that.)
export const DURATION = 210;
export const MIN_OPTIONS = 2, MAX_OPTIONS = 6;
// by when the sentence and the first alternative have landed; the fallback spacing when the beat is too short
const LANDED = 0.2, FIRST = 0.3, LAST = 0.74;
const TURN_S = 0.38, STAGGER_S = 0.028;

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
  accent?: string;
}> = ({kicker = 'ONE SLOT', before = 'The same line can end', options: optionsIn = DEMO_OPTIONS, after = '',
       mode = 'roll', accent: accIn} = {}) => {
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

  // the slot is fitted on its WIDEST alternative, so every one is set at one size and the slot never jumps
  const slot = useKinetic({alts: OPTS, w: colW, nowrap: true, fit: 'box', align: 'left',
    font: {family: DISPLAY, weight: 680, size: Math.round(U * (portrait ? 0.15 : 0.16)), minSize: Math.round(U * 0.06),
      lineHeight: 1.08, tracking: -0.02}});
  const slotSize = slot.layout?.size ?? U * 0.12;
  const lead = useKinetic({text: before || ' ', w: colW, h: Math.round(zoneH * 0.32), fit: 'box', maxLines: 3,
    align: 'left', wrap: 'balance', font: {family: DISPLAY, weight: 500, size: Math.round(U * (portrait ? 0.07 : 0.072)),
      minSize: Math.ceil(U * 0.04), lineHeight: 1.1, tracking: -0.015}});
  const tail = useKinetic({text: after || ' ', w: colW, h: Math.round(zoneH * 0.22), fit: 'box', maxLines: 2,
    align: 'left', wrap: 'balance', font: {family: DISPLAY, weight: 500, size: Math.round(U * (portrait ? 0.07 : 0.072)),
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

  // ── THE SCHEDULE: each alternative holds the slot in proportion to what it takes to READ it ──────────────
  // Even spacing gave "here" and "on its word" the same time, so the one-word options were over-held and the
  // three-word ending — the one the sentence lands on — fell under its reading time. The shot's time after the
  // first alternative lands is split: each change takes its own turn (a glyph's roll plus the stagger across the
  // arriving word), and what is left is shared in proportion to each alternative's must-read time
  // (runtime/readingSpec.json, the table the hold gate reads). A beat too short for that falls back to even
  // spacing, and scripts/shot_proof.py then names the alternative that cannot be read.
  const n = OPTS.length;
  const trS = (j: number) => TURN_S + STAGGER_S * Math.max(0, graphemes(OPTS[j]).length - 1);
  const tr = OPTS.map((_, j) => (j === 0 ? 0 : secToT(trS(j), spanF, fps)));
  const needs = OPTS.map((o) => readingSeconds(o).must);
  const budget = 1 - LANDED - tr.reduce((a, b) => a + b, 0);
  const times: number[] | undefined = budget > 0 ? [0] : undefined;
  if (times) {
    const total = needs.reduce((a, b) => a + b, 0);
    let at = LANDED;
    for (let j = 0; j < n - 1; j++) {
      at += (budget * needs[j]) / total;
      times.push(at);
      at += tr[j + 1];
    }
  }
  // the same schedule the slot runs on (runtime/kineticCore swapTimes) — the underline's width follows it
  const cueKeys = OPTS.map((_, i) => `options.${i}`);
  const T = swapTimes(n, FIRST, LAST, cueKeys.map((c) => cue.readT(c)), times);
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
      <KineticText k={slot} x={bx} y={ySlot} color={ACC} id="slot"
        motion={{from: {ymask: 1.02}, enter: {by: 'grapheme', at: 0.12, stagger: STAGGER_S, dur: 0.6, ease: 'expo',
          until: LANDED}, swap: {mode, first: FIRST, last: LAST, times, turn: TURN_S, stagger: STAGGER_S, cueKeys,
          seed: 11}}} />
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
