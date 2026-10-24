// SHOT · Magic Move Type — one phrase BECOMES the next: the letters the two share travel from where the first set
// them to where the second does, the letters only the first has leave, the ones only the second has arrive. The
// first phrase can rise in as a line, stand as a stack of its words (a layout that becomes a line), or assemble out of
// its own scattered letters.
//
// WHAT IT ARGUES. That two statements are made of the same material. "What stays, moves" → "what moves, stays";
// 少，但更好 → 更好; a word kept across a rewrite; an anagram; a slogan that is its predecessor re-ordered. The kept
// letters travelling is the claim: a viewer SEES which words survived and where they went, with the caption hidden.
// Not for two unrelated statements (nothing is shared, so everything leaves and arrives — a cross-fade with extra
// steps: use HeadlineReveal), not for a slot in a fixed sentence (WordRoll).
//
// HOW IT MOVES (runtime/kineticMove). The longest common subsequence pairs the glyphs first, so a word both phrases
// share travels as one body; the rest pair by identity, nearest first. Leaving letters lift and fade first, the
// travellers cross on gentle arcs ordered by where they LAND (the new line assembles in reading order; a letter moving
// right passes over the line, one moving left under it, so two that swap never collide), and the arrivals rise in
// last. Every setting is measured by runtime/kinetic, so each glyph lands exactly where one text node would set it.
//
// HOW LONG EACH HOLDS — in SECONDS, scaled to the beat. Each phrase is held in proportion to its must-read time
// (runtime/readingSpec.json, the table the hold gate reads), the moves and the entrance shrink on a short beat down
// to a floor, and `scripts/shot_proof.py` measures each phrase's readable stretch through the component's own state
// function at the beat's real length — a beat too short to read them is named there, not hidden here.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useAnimSpan} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, dimOn, contrastOf} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {useCues} from '../runtime/cue';
import {hasCJK} from '../runtime/cjkType';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {readingSeconds, wordIds, langOf, graphemes, plainText, tToSec} from '../runtime/kineticCore';
import {KineticMove, moveSchedule, MOVE_ROOM_EM} from '../runtime/kineticMove';

// 7s — two phrases, each held to its must-read time, one move between (at 6 s the demo's three-word phrases could be
// read once and were 0.1 s short of being taken in: a hold-gate warning at the register's own length)
export const DURATION = 210;
// THE PACE IS IN SECONDS (validate.py reads this): every duration in this register is a duration, scaled to the beat
// with floors, so a short beat plays the same moves faster only down to those floors and holds less — it does not run
// a 6 s design 2x fast. Whether each phrase can still be READ is the hold gate's measurement.
export const PACE = 'seconds';
export const MIN_PHRASES = 2, MAX_PHRASES = 4;

const BG_D0 = '#0d0e12', FG_D0 = '#f2f3f6', DIM_D0 = '#8d95a6', ACC_D0 = '#7fd3b0';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// Placeholder copy in the library's placeholder voice: two settings of the same words, so the demo shows the move
// itself and states nothing about any subject.
const DEMO = ['what stays, *moves*', 'what moves, *stays*'];

/** A phrase as its words, one per entry (Intl.Segmenter — Chinese has no spaces to split on). Punctuation stays with
 *  the word before it. */
const wordsOf = (s: string): string[] => {
  const plain = plainText(s);
  const gs = graphemes(plain);
  const {ids} = wordIds(plain, langOf(plain));
  const out: string[] = [];
  gs.forEach((g, i) => {
    if (/^\s+$/.test(g)) return;
    out[ids[i]] = (out[ids[i]] ?? '') + g;
  });
  return out.filter(Boolean);
};

export const MagicMoveType: React.FC<{
  /** a small label over the type, mono */
  kicker?: string;
  /** 2–4 phrases, in order; each BECOMES the next. `*…*` marks a run that takes the accent */
  phrases?: string[];
  /** how the first phrase is set: a line rising in, a stack of its words that becomes the line, or its letters
   *  scattered across the frame assembling into it */
  first?: 'line' | 'stack' | 'scatter';
  /** one supporting sentence under the type */
  note?: string;
  align?: 'center' | 'left';
  accent?: string;
}> = ({kicker = 'SAME LETTERS', phrases: phrasesIn = DEMO, first = 'line', note = '', align = 'center',
       accent: accIn} = {}) => {
  const dna = useDNA();
  const {width: W, height: H, fps} = useVideoConfig();
  const spanF = useAnimSpan();
  const cue = useCues();
  const PH = rows<string>(phrasesIn, 'phrases', 'MagicMoveType').map((s) => String(s ?? '').trim());
  if (PH.length < MIN_PHRASES) {
    throw new Error(`MagicMoveType needs at least ${MIN_PHRASES} phrases, got ${PH.length}: one phrase has nothing to ` +
      'become. Use HeadlineReveal.');
  }
  if (PH.length > MAX_PHRASES) {
    throw new Error(`MagicMoveType moves through at most ${MAX_PHRASES} phrases, got ${PH.length}: past that every ` +
      'move is gone before the phrase it made can be read. Keep the ones the beat argues with.');
  }
  const empty = PH.findIndex((p) => !plainText(p).trim());
  if (empty >= 0) throw new Error(`MagicMoveType was given an empty phrase (index ${empty}).`);
  // a pair that shares nothing is not a magic move — it is a cross-fade, and it should be named one
  for (let j = 0; j + 1 < PH.length; j++) {
    const a = new Set(graphemes(plainText(PH[j])).filter((g) => !/^\s+$/.test(g)));
    if (!graphemes(plainText(PH[j + 1])).some((g) => a.has(g))) {
      throw new Error(`MagicMoveType: "${PH[j]}" and "${PH[j + 1]}" share no letter, so nothing would travel — every ` +
        'glyph would only leave and arrive. Two unrelated statements are HeadlineReveal\'s, not this register\'s.');
    }
  }

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);

  // ── geometry ────────────────────────────────────────────────────────────────────────────────────────────
  const U = Math.min(W, H);
  const portrait = W < H;
  const colW = Math.round(W * (portrait ? 0.86 : 0.78));
  const x0 = align === 'center' ? Math.round((W - colW) / 2) : Math.round(W * 0.08);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H), zoneH = zoneBot - zoneTop;
  const KICK = Math.ceil(U * 0.028), NOTE = Math.round(U * 0.034), gap = Math.round(U * 0.036);
  const kickH = kicker ? Math.round(KICK * 1.25) + gap : 0;
  const noteMaxH = note ? Math.round(NOTE * 1.36 * 2) : 0;
  const headH = Math.max(U * 0.25, zoneH - kickH - (note ? noteMaxH + gap : 0));
  const cjk = hasCJK(PH.join(''));
  // ONE SIZE for every phrase: fitted once on all of them (the widest decides), so a kept word does not change size
  // as it travels. In a tall frame the floor is high — a short phrase fills the width at display size instead of
  // sitting small in the middle of an empty frame (bench-launch measured 2.5–3% ink on a 9:16 kinetic beat).
  const font = {family: DISPLAY, weight: 640, emphWeight: 720, size: Math.round(U * (portrait ? 0.21 : 0.15)),
    minSize: Math.round(U * 0.06), lineHeight: 1.04, tracking: cjk ? 0 : -0.025};
  // in a tall frame two big lines beat one small one (the vertical-video idiom): first every phrase on at most two
  // lines at a display floor of U·0.19, then one line down to U·0.11, then two at whatever fits
  const fit = useKinetic({alts: PH, w: colW, h: headH, fit: 'box', maxLines: 3, align, wrap: 'balance',
    fitTiers: portrait ? [{maxLines: 2, minSize: Math.round(U * 0.19)}, {maxLines: 1, minSize: Math.round(U * 0.11)},
      {maxLines: 2}] : [{maxLines: 1, minSize: Math.round(U * 0.085)}, {maxLines: 2}], font});
  const size = fit.layout?.size ?? font.size;
  // the room a travelling glyph needs above and below its line (runtime/kineticMove MOVE_ROOM_EM): the kicker and the
  // note are set clear of it, so a letter crossing the line never runs through them
  const room = Math.round(size * MOVE_ROOM_EM);
  const fixed = {...font, size, minSize: size};
  // the settings: phrase j as a line (or, first === 'stack', the first phrase as one word per line)
  const settingSpecs = PH.map((p, j) => (j === 0 && first === 'stack'
    ? {text: wordsOf(p), w: colW, h: headH, fit: 'box' as const, align, font: {...font, size,
        minSize: Math.round(U * 0.06)}}
    : {text: p, w: colW, fit: 'none' as const, align, wrap: 'balance' as const, font: fixed}));
  // a fixed number of hooks: MAX_PHRASES handles, the unused ones measuring a space
  const hs = Array.from({length: MAX_PHRASES}, (_, j) =>
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useKinetic(settingSpecs[j] ?? {text: ' ', w: 10, fit: 'none', font: fixed}));
  const handles = hs.slice(0, PH.length);
  const sub = useKinetic({text: note || ' ', w: Math.min(colW, Math.round(U * 1.1)), h: noteMaxH || NOTE * 2,
    fit: 'box', maxLines: 2, align, wrap: 'balance',
    font: {family: BODY, weight: 420, size: NOTE, minSize: Math.ceil(U * 0.028), lineHeight: 1.36}});
  const kick = useKinetic({text: kicker || ' ', w: colW, nowrap: true, fit: 'box', align,
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});

  // every setting centred in the head area on its MEASURED height; the block centred in the zone
  const heights = handles.map((h) => h.layout?.height ?? size * 1.2);
  const headArea = Math.max(...heights);
  const subHt = note ? (sub.layout?.height ?? noteMaxH) : 0;
  const kickRoom = kicker ? Math.max(kickH, Math.round(KICK * 1.25) + room) : 0;
  const noteGap = Math.max(gap, room);
  const blockH = kickRoom + headArea + (note ? noteGap + subHt : 0);
  const top = Math.round(zoneTop + Math.max(0, (zoneH - blockH) / 2));
  const settings = handles.map((k, j) => ({k, x: x0, y: Math.round(top + kickRoom + (headArea - heights[j]) / 2)}));

  // ── THE SCHEDULE, in seconds of the beat's own span ───────────────────────────────────────────────────────
  const spanS = Math.max(0.5, spanF / fps);
  const moveDur = Math.max(0.6, Math.min(1.15, spanS * 0.2));
  const enterDur = first === 'scatter' ? Math.max(0.7, Math.min(1.4, spanS * 0.26)) : Math.max(0.45, Math.min(0.9, spanS * 0.16));
  const lead = 0.06;
  const need = PH.map((p) => readingSeconds(plainText(p)).must);
  let starts = moveSchedule(need, spanS, moveDur, lead + enterDur);
  // a cue may bring a phrase EARLIER onto the word that says it (runtime/cue's rule), never later, and never before
  // the phrase it replaces has been held for its read-once time
  starts = starts.map((s0, j) => {
    const c = cue.readT(`phrases.${j + 1}`);
    if (c === null) return s0;
    return Math.min(s0, tToSec(c, spanF, fps) - moveDur * 0.7);
  });
  for (let j = 0; j < starts.length; j++) {
    const prevEnd = j === 0 ? lead + enterDur : starts[j - 1] + moveDur;
    starts[j] = Math.max(starts[j], prevEnd + readingSeconds(plainText(PH[j])).once);
  }

  const noteAt = Math.min(0.6, (lead + enterDur) / Math.max(0.5, spanS));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <KineticText k={kick} x={x0} y={top} color={ACC} read={false} id="kicker"
          motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.07, stagger: 0.03, dur: 0.45,
            ease: 'power3', cueKeys: ['kicker'], until: 0.4}}} />
      ) : kick.anchor}
      {fit.anchor}
      {hs.slice(PH.length).map((h, j) => <React.Fragment key={`u${j}`}>{h.anchor}</React.Fragment>)}
      <KineticMove settings={settings} starts={starts} dur={moveDur} color={FG} emphColor={ACC} id="phrases"
        enter={first === 'scatter' ? false : {at: lead, dur: enterDur}}
        scatter={first === 'scatter' ? {box: {x: W * 0.08, y: zoneTop + zoneH * 0.05, w: W * 0.84, h: zoneH * 0.9},
          at: lead, dur: enterDur, seed: 5} : undefined} />
      {note ? (
        <KineticText k={sub} x={align === 'center' ? Math.round((W - Math.min(colW, U * 1.1)) / 2) : x0}
          y={top + kickRoom + headArea + noteGap} color={DIM} id="note"
          motion={{from: {opacity: 0, y: 0.4}, enter: {by: 'word', at: noteAt, stagger: 0.045, dur: 0.55,
            ease: 'power3', cueKeys: ['note'], until: 0.75}}} />
      ) : sub.anchor}
    </AbsoluteFill>
  );
};
export default MagicMoveType;
