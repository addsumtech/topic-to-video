// SHOT · Headline Reveal — the beat's headline arrives the way a launch site's hero does: each line rises through its
// own mask (or each word does, or each letter blurs in), on the word the narration says it, and the run the film
// marked `*…*` takes the accent after it lands, with a rule drawn under it.
//
// WHAT IT ARGUES. The headline IS the beat — a claim said in one breath, where the sentence's own rhythm is the
// design. A title register sets a sentence and fades it up; this one sets it at the pace it is spoken, so the line a
// viewer is reading is the line they are hearing, and the one phrase that carries the claim is the one that changes
// colour. Not for a list of peers (a list register), not for one enormous word (CroppedType, VariableTypeMorph).
//
// HOW IT MOVES (references/motion-research.md §1, measured on the launch sites themselves). Lines: a mask reveal —
// each line rises a whole clip-height through an overflow clip (GSAP SplitText's mask, `yPercent: 100`, expo.out),
// with the slight blur-to-sharp linear.app's hero runs, staggered by line. Words: the same at word scale, the
// SplitText 0.04 : 0.15 : 0.25 stagger ratio's middle term. Letters: Framer's per-character blur-in. Every
// entrance is cued: `lines.N` moves EARLIER onto the word that names it (runtime/cue) and never later.
//
// THE TYPE IS runtime/kinetic's: laid out once by the browser, every glyph placed where that layout put it — so the
// kerning, a Chinese line's punctuation compression and its line breaks are the ones a plain text node would have
// (measured: 0 px apart), and every type gate reads the headline as its lines.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, dimOn, contrastOf} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {hasCJK} from '../runtime/cjkType';
import {useKinetic, KineticText, KMotion} from '../runtime/kinetic';

export const DURATION = 165; // 5.5s
export const MAX_LINES = 5;

const BG_D0 = '#0c0e13', FG_D0 = '#f3f4f7', DIM_D0 = '#8f97a8', ACC_D0 = '#86a8ff';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// Placeholder copy in the library's placeholder voice: it describes the register, so no film's words become the
// next film's default and nothing here is a fact about anything.
const DEMO = ['Each line rises', 'on *its own word*'];

export const HeadlineReveal: React.FC<{
  /** a small label over the headline, in the mono face */
  kicker?: string;
  /** the headline, one entry per line the film wants (a long entry wraps); `*…*` marks the emphasised run */
  lines?: string[];
  /** one supporting sentence under it */
  note?: string;
  /** what rises: whole lines through their masks, words through theirs, or letters blurring in */
  reveal?: 'line' | 'word' | 'char';
  align?: 'left' | 'center';
  accent?: string;
}> = ({kicker = 'IN ONE BREATH', lines: linesIn = DEMO, note = 'and the emphasis lands last',
       reveal = 'line', align = 'left', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const LINES = rows<string>(linesIn, 'lines', 'HeadlineReveal').map((s) => String(s ?? ''));
  if (!LINES.length || LINES.every((s) => !s.trim())) {
    throw new Error('HeadlineReveal needs at least one line of headline; an empty headline is an empty frame.');
  }
  if (LINES.length > MAX_LINES) {
    throw new Error(`HeadlineReveal sets at most ${MAX_LINES} lines and was given ${LINES.length}. Past that it is a ` +
      'paragraph, and a paragraph revealed line by line reads as a teleprompter: split the beat.');
  }
  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  // THE ACCENT IS KEPT WHEREVER IT CAN BE READ. `readableOn(BG, accent, FG)` returns the MOST legible candidate,
  // which on a dark ground is always the near-white foreground — the first render drew the emphasised run white on
  // white text, an emphasis nobody could see. Display type needs 3:1 (WCAG large text); below it, the foreground.
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);

  // ── geometry, in fractions of the frame; the type sizes come from MEASURING the copy into the room ──────────
  const U = Math.min(W, H);
  const portrait = W < H;
  const colW = Math.round(W * (portrait ? 0.84 : 0.74));
  const x0 = align === 'center' ? Math.round((W - colW) / 2) : Math.round(W * (portrait ? 0.08 : 0.085));
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H), zoneH = zoneBot - zoneTop;
  const KICK = Math.ceil(U * 0.028), NOTE = Math.round(U * 0.033);
  const gap = Math.round(U * 0.034);
  const kickH = kicker ? Math.round(KICK * 1.25) + gap : 0;
  const noteMaxH = note ? Math.round(NOTE * 1.36 * 3) : 0;
  const headH = Math.max(U * 0.2, zoneH - kickH - (note ? noteMaxH + gap : 0));
  const cjk = hasCJK(LINES.join(''));

  // the emphasised run THICKENS as it lands (620 → 760), and a weight change reflows the line — so the range is
  // declared here, measured at five anchors, and the line breaks are fixed at the heaviest
  // THE FILM'S LINES ARE LINES. Fitted only to the box, the largest size that fits wins, and it got there by
  // wrapping: 「一行一行升起」 came out as 「一行一 / 行升起」, a phrase cut in half for a few more pixels of type. So
  // the first tier keeps every entry whole down to a display floor; only past that floor may an entry wrap.
  const head = useKinetic({text: LINES, w: colW, h: headH, fit: 'box', maxLines: MAX_LINES + 2, align,
    fitTiers: [{maxLines: LINES.length, minSize: Math.round(U * 0.072)}],
    axes: {wght: [620, 760]}, wrap: 'balance', font: {family: DISPLAY, weight: 620, size: Math.round(U * (portrait ? 0.165 : 0.15)),
      minSize: Math.round(U * 0.05), lineHeight: 1.02, tracking: cjk ? 0 : -0.024}});
  const sub = useKinetic({text: note || ' ', w: Math.min(colW, Math.round(U * 1.1)), h: noteMaxH || NOTE * 2,
    fit: 'box', maxLines: 3, align, wrap: 'balance',
    font: {family: BODY, weight: 420, size: NOTE, minSize: Math.ceil(U * 0.028), lineHeight: 1.36}});
  // the kicker's rule sits INSIDE the column, ahead of the kicker (a rule hung outside it was 13px from the edge
  // of a portrait frame); centred, there is no rule
  const ruleW = Math.round(U * 0.05), ruleGap = Math.round(U * 0.018);
  const kickX = align === 'center' ? x0 : x0 + ruleW + ruleGap;
  const kick = useKinetic({text: kicker || ' ', w: colW - (kickX - x0), nowrap: true, fit: 'box', align,
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});

  // the block is centred in the content zone on its MEASURED height (the frame waits for the measurement)
  const headHt = head.layout?.height ?? headH;
  const subHt = note ? (sub.layout?.height ?? noteMaxH) : 0;
  const blockH = kickH + headHt + (note ? gap + subHt : 0);
  const top = Math.round(zoneTop + Math.max(0, (zoneH - blockH) / 2));

  const cueKeys = LINES.map((_, i) => `lines.${i}`);
  const headMotion: KMotion = reveal === 'char'
    ? {from: {opacity: 0, blur: 0.12, y: 0.12},
       enter: {by: 'grapheme', at: 0.1, stagger: cjk ? 0.08 : 0.035, dur: 0.5, ease: 'power3', cueKeys, until: 0.72}}
    : reveal === 'word'
      ? {mask: 'word', from: {ymask: 1.02, blur: 0.03},
         enter: {by: 'word', at: 0.1, stagger: 0.07, dur: 0.75, ease: 'expo', cueKeys, until: 0.72}}
      : {mask: 'line', from: {ymask: 1.02, blur: 0.04},
         enter: {by: 'line', at: 0.1, stagger: 0.16, dur: 0.95, ease: 'expo', cueKeys, until: 0.72}};
  // EMPHASIS IS COLOUR AND WEIGHT, NOT A RULE. A rule under the run was the first build; at display size it ran
  // straight through the descenders ("by", "pay") and read as a strike in the wrong place. The run takes the accent
  // and thickens, each letter a beat after the last, once its own line has landed.
  headMotion.emph = {after: 0.18, stagger: cjk ? 0.06 : 0.028, dur: 0.45, wght: 760};

  // the kicker's rule draws first; it is the shot's one piece of furniture and it points at the type
  const ruleIn = easeOutCubic(clamp01(seg(t, 0.06, 0.2)));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <>
          {align === 'center' ? null : (
            <div style={{position: 'absolute', top: top + Math.round(KICK * 0.6), left: x0, width: ruleW,
              height: Math.max(2, Math.round(U * 0.003)), background: ACC, transformOrigin: '0 50%',
              transform: `scaleX(${ruleIn})`}} />
          )}
          <KineticText k={kick} x={kickX} y={top} color={ACC} read={false} id="kicker"
            motion={{from: {opacity: 0, blur: 0.3, x: -0.15},
              enter: {by: 'grapheme', at: 0.07, stagger: 0.03, dur: 0.45, ease: 'power3', cueKeys: ['kicker'],
                until: 0.42}}} />
        </>
      ) : kick.anchor}
      <KineticText k={head} x={x0} y={top + kickH} color={FG} emphColor={ACC} motion={headMotion} id="headline" />
      {note ? (
        <KineticText k={sub} x={align === 'center' ? Math.round((W - Math.min(colW, U * 1.1)) / 2) : x0}
          y={top + kickH + headHt + gap} color={DIM} id="note"
          motion={{from: {opacity: 0, y: 0.45},
            enter: {by: 'word', at: 0.3, stagger: 0.045, dur: 0.6, ease: 'power3', cueKeys: ['note'], until: 0.7}}} />
      ) : sub.anchor}
    </AbsoluteFill>
  );
};
export default HeadlineReveal;
