// SHOT · ObjectCompare — two things the film drew, side by side, and the ONE difference between them named and
// marked at the same place on both. Family H (comparison).
//
// THE ARGUMENT SHAPE: "these two differ HERE." The library's comparison registers set numbers, sentences or
// photographs against each other; this one sets two objects a film drew — one object in two states (a loose bed
// of coffee and a tamped one, the same street in 1900 and now) or two things with one decisive difference. A ring
// marks the same point on both (`at`, a fraction of each object's box), a dashed tie joins the rings, and the
// difference is set under the pair, in words.
//
// FAIRNESS IS PART OF THE CLAIM. Two objects of one aspect are drawn at ONE size on one floor line; the right one
// arrives a beat after the left, so the eye reads them in order, and nothing is emphasised by size. Wide frames
// set them side by side; tall frames stack them, first above second, both centred.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {drawOn} from '../runtime/draw';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef, type Rect} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

export const DURATION = 165;
export const REQUIRED_IN_FILM = ['first', 'second', 'difference'] as const;
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8';

const DEMO_FIRST: ObjectRef = {id: DEMO_ID, props: {layers: 3}};
const DEMO_SECOND: ObjectRef = {id: DEMO_ID, props: {layers: 2}};
const isUnit = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;

export const ObjectCompare: React.FC<{
  first?: ObjectRef;              // the first thing the film drew (runtime/objectSlot)
  second?: ObjectRef;             // the second — the same object with other props, or another thing
  firstLabel?: string;            // what the first is, under it
  secondLabel?: string;           // what the second is, under it
  difference?: string;            // the one difference, in words, set under both
  at?: {x: number; y: number};    // where it is on both (0..1 of each object's box) — a ring on each, tied together
  kicker?: string;                // a spaced label in the title band
}> = ({first: FIRST = DEMO_FIRST, second: SECOND = DEMO_SECOND, firstLabel = '', secondLabel = '', difference = '',
  at, kicker = ''} = {}) => {
  if (at != null && !(typeof at === 'object' && !Array.isArray(at) && isUnit(at.x) && isUnit(at.y))) {
    throw new Error(`ObjectCompare: \`at\` is {"x": …, "y": …} in 0..1 of each object's box — got ${JSON.stringify(at)}`);
  }
  const eL = useObjectEntry(FIRST), eR = useObjectEntry(SECOND);
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const wide = W >= H * 1.2;
  const sw = Math.max(2, Math.round(U * 0.004));

  // THE WORDS FIRST: each label under its object, the difference under the pair.
  const capW = Math.min(W * 0.84, 1400);
  const gapX = Math.round(W * 0.06);
  const colW = wide ? (capW - gapX) / 2 : capW;
  const lblPx0 = Math.round(U * 0.026);
  let lblPx = Math.min(lblPx0, ...[firstLabel, secondLabel].filter((s) => !!s)
    .map((s) => fitBlockPx(s, colW, lblPx0 * 2.7, lblPx0, {usable: 1, leading: leading(s, 1.3)})));
  const lblH = (s?: string) => (s ? wrapLines(s, lblPx, colW) * lblPx * leading(s, 1.3) : 0);
  const dLead = leading(difference, 1.2);
  let diffPx = difference ? fitBlockPx(difference, capW, U * 0.1, Math.round(U * 0.038), {usable: 1, leading: dLead}) : 0;
  const ruleH = difference ? sw + Math.round(U * 0.016) : 0;
  const diffH = () => (difference ? ruleH + wrapLines(difference, diffPx, capW) * diffPx * dLead : 0);
  const lblGap = Math.round(U * 0.018), diffGap = difference ? Math.round(U * 0.04) : 0;
  const x0 = (W - capW) / 2;

  let bL: Rect, bR: Rect, lblL: Rect, lblR: Rect, diffTop: number;
  if (wide) {
    const labelH = Math.max(lblH(firstLabel), lblH(secondLabel));
    const roomH = Math.max(U * 0.18, zBot - zTop - U * 0.02 - lblGap - labelH - diffGap - diffH());
    const dL = fitAspect({x: 0, y: 0, w: colW, h: roomH}, eL.meta?.aspect);
    const dR = fitAspect({x: 0, y: 0, w: colW, h: roomH}, eR.meta?.aspect);
    const h = Math.max(dL.h, dR.h);
    const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - (h + lblGap + labelH + diffGap + diffH())) / 2);
    bL = {x: x0 + (colW - dL.w) / 2, y: top0 + h - dL.h, w: dL.w, h: dL.h};
    bR = {x: x0 + colW + gapX + (colW - dR.w) / 2, y: top0 + h - dR.h, w: dR.w, h: dR.h};
    lblL = {x: x0, y: top0 + h + lblGap, w: colW, h: lblH(firstLabel)};
    lblR = {x: x0 + colW + gapX, y: top0 + h + lblGap, w: colW, h: lblH(secondLabel)};
    diffTop = top0 + h + lblGap + labelH + diffGap;
  } else {
    // STACKED: BOTH LABELS' HEIGHT ADDS UP — one sits above the other, unlike the wide branch's single
    // taller-of-two side columns — so a tall, narrow frame is the shape where the words can genuinely
    // outgrow the room two stacked objects leave. Each object is pinned to its own floor (OBJ_FLOOR) first:
    // it is already the smallest either may be drawn at, so when the words would still overflow the content
    // zone at that floor, the WORDS are what gives — stepped down together, in proportion, to the largest
    // size that fits, or refused by name if even half size does not. Two full two-line labels under a
    // same-size pair plus an ordinary two-line difference is a real case at 1:1, not a contrived one — the
    // card's own labels promise up to two lines each.
    const between = Math.round(U * 0.03);
    const OBJ_FLOOR = U * 0.14;
    const wordsBudget = Math.max(0, zBot - zTop - U * 0.02 - 2 * OBJ_FLOOR - 2 * lblGap - between - diffGap);
    const wordsAt = (lp: number, dp: number) => {
      const h1 = firstLabel ? wrapLines(firstLabel, lp, colW) * lp * leading(firstLabel, 1.3) : 0;
      const h2 = secondLabel ? wrapLines(secondLabel, lp, colW) * lp * leading(secondLabel, 1.3) : 0;
      const dh = difference ? ruleH + wrapLines(difference, dp, capW) * dp * dLead : 0;
      return {h1, h2, dh, total: h1 + h2 + dh};
    };
    let words = wordsAt(lblPx, diffPx);
    if (words.total > wordsBudget) {
      // STEP DOWN AND CHECK EVERY STEP — NEVER BISECT. `wrapLines` is non-monotone in px on mixed
      // Chinese/English copy (a slightly smaller size can wrap to MORE lines, not fewer), so a search that
      // trusts one sample and discards half the remaining range on it can converge on a size that does not
      // actually fit. A full scan from the ideal size down to half, taking the first (largest) step that
      // measures as fitting, cannot be fooled that way regardless of which way the text's own wrapping
      // moves in between.
      const MIN_WORD_SCALE = 0.5;
      let found: {lp: number; dp: number; words: ReturnType<typeof wordsAt>} | null = null;
      for (let pct = 95; pct >= Math.round(MIN_WORD_SCALE * 100); pct -= 5) {
        const lp = Math.max(1, Math.round(lblPx * pct / 100)), dp = Math.max(1, Math.round(diffPx * pct / 100));
        const w = wordsAt(lp, dp);
        if (w.total <= wordsBudget) { found = {lp, dp, words: w}; break; }
      }
      if (!found) {
        const floorLp = Math.max(1, Math.round(lblPx * MIN_WORD_SCALE));
        const floorDp = Math.max(1, Math.round(diffPx * MIN_WORD_SCALE));
        const floorWords = wordsAt(floorLp, floorDp);
        throw new Error(`ObjectCompare: the labels and the difference need ${Math.ceil(floorWords.total)}px even ` +
          `at half size; the frame leaves ${Math.floor(wordsBudget)}px for them — shorten the labels or the ` +
          'difference.');
      }
      lblPx = found.lp; diffPx = found.dp; words = found.words;
    }
    const roomH = Math.max(OBJ_FLOOR, (zBot - zTop - U * 0.02 - 2 * lblGap - words.h1 - words.h2 - between
      - diffGap - words.dh) / 2);
    const dL = fitAspect({x: 0, y: 0, w: capW, h: roomH}, eL.meta?.aspect);
    const dR = fitAspect({x: 0, y: 0, w: capW, h: roomH}, eR.meta?.aspect);
    const groupH = dL.h + lblGap + words.h1 + between + dR.h + lblGap + words.h2 + diffGap + words.dh;
    const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - groupH) / 2);
    bL = {x: (W - dL.w) / 2, y: top0, w: dL.w, h: dL.h};
    lblL = {x: x0, y: top0 + dL.h + lblGap, w: capW, h: words.h1};
    const topR = lblL.y + lblL.h + between;
    bR = {x: (W - dR.w) / 2, y: topR, w: dR.w, h: dR.h};
    lblR = {x: x0, y: topR + dR.h + lblGap, w: capW, h: words.h2};
    diffTop = lblR.y + lblR.h + diffGap;
  }

  const tL = clamp01(seg(t, 0.06, 0.44)), tR = clamp01(seg(t, 0.16, 0.54));
  const inL = easeOutCubic(clamp01(seg(t, 0.4, 0.58))), inR = easeOutCubic(clamp01(seg(t, 0.46, 0.62)));
  const ringOn = clamp01(seg(t, 0.58, 0.7)), tieOn = clamp01(seg(t, 0.64, 0.76));
  const diffIn = easeOutCubic(clamp01(seg(t, 0.66, 0.82)));
  const r = U * 0.045;
  const pL = at ? {x: bL.x + at.x * bL.w, y: bL.y + at.y * bL.h} : null;
  const pR = at ? {x: bR.x + at.x * bR.w, y: bR.y + at.y * bR.h} : null;
  let tie: {x1: number; y1: number; x2: number; y2: number} | null = null;
  if (pL && pR) {            // the tie runs between the rings' edges, not through their centres
    const dx = pR.x - pL.x, dy = pR.y - pL.y, len = Math.hypot(dx, dy) || 1;
    tie = {x1: pL.x + (dx / len) * r, y1: pL.y + (dy / len) * r, x2: pR.x - (dx / len) * r, y2: pR.y - (dy / len) * r};
  }
  const label = (text: string | undefined, box: Rect, on: number) => (text ? (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, textAlign: 'center', opacity: on,
      font: `500 ${lblPx}px/${leading(text, 1.3)} ${bodyF}`, color: DIM, textWrap: 'balance'}}>{text}</div>
  ) : null);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center',
          opacity: easeOutCubic(clamp01(seg(t, 0.03, 0.18))),
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      <ObjectSlot object={FIRST} box={bL} t={tL} />
      <ObjectSlot object={SECOND} box={bR} t={tR} />
      {label(firstLabel, lblL, inL)}
      {label(secondLabel, lblR, inR)}
      {pL && pR && tie ? (
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          <line x1={tie.x1} y1={tie.y1} x2={tie.x2} y2={tie.y2} stroke={ACC} strokeWidth={sw * 0.75}
            strokeDasharray={`${sw * 3} ${sw * 3}`} opacity={0.8 * tieOn} />
          <circle cx={pL.x} cy={pL.y} r={r} fill="none" stroke={ACC} strokeWidth={sw} {...drawOn(ringOn)} />
          <circle cx={pR.x} cy={pR.y} r={r} fill="none" stroke={ACC} strokeWidth={sw} {...drawOn(ringOn)} />
        </svg>
      ) : null}
      {difference ? (
        <div style={{position: 'absolute', left: x0, top: diffTop, width: capW, textAlign: 'center', opacity: diffIn}}>
          <div style={{width: U * 0.06, height: sw, background: ACC, margin: `0 auto ${Math.round(U * 0.016)}px`}} />
          <div style={{font: `700 ${diffPx}px/${dLead} ${disp}`, color: FG, textWrap: 'balance'}}>{difference}</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ObjectCompare;
