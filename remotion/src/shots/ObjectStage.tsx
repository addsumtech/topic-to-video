// SHOT · ObjectStage — one thing, shown whole and named: an object the FILM drew, standing on a quiet floor, its
// parts called out and its name set under it. Family E (a hero object).
//
// THE ARGUMENT SHAPE: "this is the thing — look at it." The library's hero registers each draw a thing of their
// own (MaterialHero's ring of parts, TechnicalPlate's stroked elevation); none could show an object a film drew
// for itself. This one holds any object (runtime/objectSlot) and frames it: a floor it stands on, callouts that
// point at named points on it, its name and one line under it.
//
// THE OBJECT OWNS ITS PICTURE AND THE STAGE OWNS THE WORDS. The object's clock runs 0 → 1 over 0.06–0.6 of the
// beat and then holds, so what is labelled is the object SETTLED, and the settled frame every gate reads shows
// the whole object with its names. Callout points are fractions of the object's own drawn box, so they stay on
// the part they name at every aspect. Where the frame is wide enough the callouts run to the side margins;
// where it is not (portrait, square) the object carries numbered dots and a numbered key sits under its name.
// The object and its words are centred together in the content zone.
//
// WORDS ARRIVE WHEN THE VOICE SAYS THEM (runtime/cue.ts). A label, the title or the note the narration names
// before its slot starts early enough to read on its word — never later than its slot. The callouts were dealt in
// one late run, so a narration that names its first part in its first sentence left that label 3.7 s late on a
// delivered film, past anything the beat's warp could reach. A label cued that early arrives while the object is
// still building — the voice and the picture introducing the thing together; the object's own clock is left alone,
// since compressing it would move the object's events off the sentences that describe them. The settled frame is
// unchanged: every word is in by then.
//
// Standalone it shows its own preview form (objects/DemoForm, no words). A film must name its object —
// REQUIRED_IN_FILM, which validate.py reads.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, relLum} from '../runtime/dna';
import {onAccentInk} from '../runtime/onAccent';
import {rows} from '../runtime/rows';
import {hex6} from '../runtime/hexColor';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';
import {useCues, REACH_CUBIC} from '../runtime/cue';

export const DURATION = 165;
export const MAX_STAGE_LABELS = 6;
export const REQUIRED_IN_FILM = ['object'] as const;
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8';
const DEMO_OBJECT: ObjectRef = {id: DEMO_ID};
const OBJ_A = 0.06, OBJ_B = 0.6;          // the object's own t runs 0 → 1 here, then holds
const LBL_A = 0.6, LAND_BY = 0.84;        // callouts, every one in before the settled frame

type Label = {text: string; x: number; y: number; side?: 'left' | 'right'};
const isUnit = (v: unknown) => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;

export const ObjectStage: React.FC<{
  object?: ObjectRef;   // the thing the film drew (runtime/objectSlot) — absent: the stage's own preview form
  labels?: Label[];     // 0-6 callouts at points on the object, in its box's unit space
  title?: string;       // what it is, set under it
  note?: string;        // one line under the title
  kicker?: string;      // a spaced label above
}> = ({object: OBJECT = DEMO_OBJECT, labels, title = '', note = '', kicker = ''} = {}) => {
  const LABELS = rows<Label>(labels, 'labels', 'ObjectStage');
  if (LABELS.length > MAX_STAGE_LABELS) {
    throw new Error(`ObjectStage takes 0-${MAX_STAGE_LABELS} \`labels\` (got ${LABELS.length}) — past six the ` +
      'callouts crowd the thing they name; keep the parts the beat argues about.');
  }
  LABELS.forEach((l, i) => {
    if (!l || typeof l.text !== 'string' || !l.text.trim()) {
      throw new Error(`ObjectStage: label ${i + 1} has no \`text\` (got ${JSON.stringify(l)}).`);
    }
    if (!isUnit(l.x) || !isUnit(l.y)) {
      throw new Error(`ObjectStage: label ${i + 1} ("${l.text}") needs \`x\` and \`y\` in 0..1 of the object's box ` +
        `(got x=${String(l.x)}, y=${String(l.y)}) — the dot says "this part is HERE".`);
    }
    if (l.side !== undefined && l.side !== 'left' && l.side !== 'right') {
      throw new Error(`ObjectStage: label ${i + 1} ("${l.text}") has \`side\` ${JSON.stringify(l.side)} — ` +
        "it is 'left' or 'right', or leave it out and the point's own half decides.");
    }
  });
  const entry = useObjectEntry(OBJECT);
  const dna = useDNA();
  const t = useT();
  const cue = useCues();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0;
  const ON_ACC = onAccentInk(ACC, dna?.accent2, dna?.onAccent, FG);
  // A CONTACT SHADOW IS ALWAYS DARKER THAN ITS FLOOR, on any ground: `FG` is only reliably dark on a light
  // one — on all eight shipped presets (every one dark) it is the film's near-white ink, and mixing toward
  // it painted a pale GLOW under the object instead of a shadow. Read from the ground actually being
  // painted below (`bg`, this register's own fallback otherwise), not guessed from the DNA's identity.
  const groundLight = relLum(hex6(dna?.bg ?? BG_D0)) > 0.5;
  const shadowInk = groundLight ? FG : '#000000';
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);

  // THE WORDS FIRST, SIZED TO THEIR COPY; THE OBJECT TAKES THE ROOM THEY LEAVE — and if the words
  // themselves (a long title, a note, a six-entry CJK key) would still overrun the content zone even with
  // the object down at its floor (U*0.2), they SCALE DOWN to the room actually left rather than spill into
  // the caption band. Legal props are the only bound (title/note are free text; MAX_STAGE_LABELS caps the
  // key at six), so "heavy but legal" is a real case, not a hypothetical one.
  const capW = Math.min(W * 0.84, 1240);
  const tLead = leading(title, 1.12), nLead = leading(note, 1.4);
  const nL = LABELS.length;
  const side = nL > 0 && W >= H * 1.2;
  const keyLines = LABELS.map((l, i) => `${i + 1}  ${l.text}`);
  const titlePx0 = title ? fitBlockPx(title, capW, U * 0.13, Math.round(U * 0.05), {usable: 1, leading: tLead}) : 0;
  const MIN_WORD_SCALE = 0.5;

  // The block's total height at a given font-size SCALE (1 = the ideal, unshrunk sizes above).
  const wordsAt = (scale: number) => {
    const titlePx = title ? Math.max(1, Math.round(titlePx0 * scale)) : 0;
    const titleH = title ? wrapLines(title, titlePx, capW) * titlePx * tLead : 0;
    const notePx = Math.max(1, Math.round(U * 0.022 * scale));
    const noteH = note ? wrapLines(note, notePx, capW) * notePx * nLead : 0;
    const noteGap = title && note ? Math.round(U * 0.012 * scale) : 0;
    const wordsH = titleH + noteGap + noteH;
    const gap = wordsH ? Math.round(U * 0.03) : 0;
    const keyPx = Math.max(1, Math.round(U * 0.02 * scale));
    const keyH = !side && nL
      ? keyLines.reduce((acc, s, i) => acc + (i ? keyPx * 0.45 : 0) + wrapLines(s, keyPx, capW) * keyPx * leading(s, 1.35), 0)
      : 0;
    const keyGap = keyH ? Math.round(U * 0.022) : 0;
    return {titlePx, titleH, notePx, noteH, noteGap, wordsH, gap, keyPx, keyH, keyGap, total: gap + wordsH + keyGap + keyH};
  };
  // The room left for words once the object has claimed its floor — the same U*0.2 `roomH` already floors
  // to below. `wordsAt(scale).total` FALLS as scale falls (checked over 30k random boards) but not linearly
  // — height is set by a wrapped LINE COUNT more than by the px size directly, so it falls closer to the
  // SQUARE of the scale, and a step sized for a linear fall overshoots: for an 855-glyph note at 16:9, such
  // a step stalls at scale 0.657 where 0.820 already fits, rendering visibly smaller than it needs to be.
  // Monotone total means the LARGEST fitting scale is found by bisection instead — about a dozen steps,
  // against a [MIN_WORD_SCALE, 1] range 0.5 wide, is far past the precision a rounded px size can even show.
  // Title/note/labels are free text with no length cap, so "the words still don't fit at the floor" is a
  // real case, not a hypothetical one, and the register refuses by name rather than let the key print into
  // the caption band.
  const budget = Math.max(0, zBot - zTop - U * 0.02 - U * 0.2);
  let scale = 1;
  if (wordsAt(1).total > budget) {
    if (wordsAt(MIN_WORD_SCALE).total > budget) {
      scale = MIN_WORD_SCALE;                    // the floor itself does not fit; the throw below says so
    } else {
      let lo = MIN_WORD_SCALE, hi = 1;
      for (let i = 0; i < 12; i++) {
        const mid = (lo + hi) / 2;
        if (wordsAt(mid).total <= budget) lo = mid; else hi = mid;
      }
      scale = lo;
    }
  }
  const total = wordsAt(scale).total;
  if (total > budget) {
    // SIDE MODE DRAWS NO KEY, AND ITS LABELS SIT IN THEIR OWN COLUMNS — this total is title+note alone there.
    const what = side ? 'the title and note' : 'the title, note and key';
    const fix = side ? 'shorten the title or the note' : 'shorten the note or the labels';
    throw new Error(`ObjectStage: ${what} need ${Math.ceil(total)}px even at half size; the frame leaves ` +
      `${Math.floor(budget)}px under the object — ${fix}.`);
  }
  const {titlePx, titleH, notePx, noteH, noteGap, wordsH, gap, keyPx, keyH, keyGap} = wordsAt(scale);

  const colW = side ? Math.round(W * 0.19) : 0;
  const margin = Math.round(W * 0.045);
  const roomW = side ? W - 2 * (margin + colW + W * 0.03) : W * 0.84;
  const roomH = Math.max(U * 0.2, zBot - zTop - U * 0.02 - gap - wordsH - keyGap - keyH);
  const drawn = fitAspect({x: (W - roomW) / 2, y: 0, w: roomW, h: roomH}, entry.meta?.aspect);
  // the object and its words are one group, centred in the content zone
  const groupH = drawn.h + gap + wordsH + keyGap + keyH;
  const top0 = zTop + Math.max(U * 0.01, (zBot - zTop - groupH) / 2);
  const box = {x: drawn.x, y: top0, w: drawn.w, h: drawn.h};
  const floorY = box.y + box.h;
  const wordsTop = floorY + gap;

  const objT = clamp01(seg(t, OBJ_A, OBJ_B));
  const floorIn = easeOutCubic(clamp01(seg(t, 0.03, 0.2)));
  const step = nL > 1 ? Math.min(0.05, (LAND_BY - LBL_A - 0.12) / (nL - 1)) : 0;
  const onAt = (i: number) => easeOutCubic(clamp01(seg(t,
    ...cue.win('labels.' + i, LBL_A + i * step, LBL_A + i * step + 0.12, REACH_CUBIC))));
  const titleIn = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.62, 0.78, REACH_CUBIC))));
  const noteIn = easeOutCubic(clamp01(seg(t, ...cue.win('note', 0.66, 0.82, REACH_CUBIC))));

  // SIDE CALLOUT COLUMNS: each column is ordered top-to-bottom from its labels' own points and pushed apart
  // so no label overprints its neighbour, the SAME bound the words already keep — inside the content zone,
  // and (when there is a title or note under the object) never reaching into it, since a wide frame's words
  // block sits close enough in X for a tall column to print straight over it. LEFT AND RIGHT ARE TWO
  // INDEPENDENT STACKS IN TWO SEPARATE MARGINS, and are measured and fitted that way: what a column NEEDS
  // is its OWN span, so a one-line label alone in a short column must never be judged (or shrunk, or
  // refused) by how tall the OTHER column happens to be — a union of the two spans is neither column's own
  // requirement, and reading a few labels stacked opposite a genuinely long one as if they shared a budget
  // both refused boards a per-column fit existed for and shrank type nobody's own column needed shrunk.
  // Each column is measured as ONE span FIRST and only placed once that span is known to fit — shifting a
  // column that already overflows can push its far end back inside while pushing its NEAR end out the
  // other side: keeping the bottom off the caption band by shifting the whole column up is exactly what can
  // send its top past the frame's own edge. A column whose own labels need more room than the bound has,
  // even at their smallest legible size, refuses by name rather than print outside the frame or over the
  // words.
  const lblLead = 1.3;
  let lblPx = Math.round(U * 0.02);
  const placed = LABELS.map((l, i) => ({l, i, p: {x: box.x + l.x * box.w, y: box.y + l.y * box.h},
    right: (l.side ?? (l.x >= 0.5 ? 'right' : 'left')) === 'right'}));
  const rowY: number[] = placed.map((q) => q.p.y);
  if (side) {
    const colBoundBottom = (title || note) ? Math.min(zBot, wordsTop) : zBot;
    const available = Math.max(1, colBoundBottom - zTop);
    const cascade = (px: number) => {
      const cols: {laid: {i: number; top: number}[]; top: number; bottom: number}[] = [];
      let span = 0;
      for (const right of [true, false]) {
        const col = placed.filter((q) => q.right === right).sort((a, b) => a.p.y - b.p.y);
        let prev = -Infinity, top = Infinity, bottom = -Infinity;
        const laid: {i: number; top: number}[] = [];
        for (const q of col) {
          const y = Math.max(q.p.y, prev + px * 0.8);
          const rowH = wrapLines(q.l.text, px, colW) * px * lblLead;
          laid.push({i: q.i, top: y - px * 0.68});
          top = Math.min(top, y - px * 0.68);
          bottom = Math.max(bottom, y - px * 0.68 + rowH);
          prev = y + rowH;
        }
        if (laid.length) { cols.push({laid, top, bottom}); span = Math.max(span, bottom - top); }
      }
      return {cols, span};
    };
    let cur = cascade(lblPx);
    let colScale = 1;
    while (cur.span > available && colScale > MIN_WORD_SCALE) {
      colScale = Math.max(MIN_WORD_SCALE, Math.min(colScale - 0.01, colScale * available / Math.max(1, cur.span)));
      lblPx = Math.max(1, Math.round(U * 0.02 * colScale));
      cur = cascade(lblPx);
    }
    if (cur.span > available) {
      throw new Error(`ObjectStage: a side column needs ${Math.ceil(cur.span)}px even at the smallest legible ` +
        `size; this frame leaves ${Math.floor(available)}px for it — shorten that side's labels or drop one.`);
    }
    for (const c of cur.cols) {
      const shift = Math.min(Math.max(0, zTop - c.top), colBoundBottom - c.bottom);
      for (const row of c.laid) rowY[row.i] = row.top + shift + lblPx * 0.68;
    }
  }
  const dot = Math.max(4, Math.round(U * 0.006));
  const hair = Math.max(1, Math.round(W * 0.0012));
  const leaderGap = Math.max(4, Math.round(U * 0.006));   // clear air between a leader's end and its label

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', opacity: floorIn,
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      {/* the floor it stands on: a soft shadow, always darker than the floor, at a whisper */}
      <div style={{position: 'absolute', left: box.x + box.w * 0.08, top: floorY - U * 0.012, width: box.w * 0.84,
        height: U * 0.03, borderRadius: '50%', background: shadowInk, opacity: 0.1 * floorIn,
        filter: `blur(${Math.round(U * 0.01)}px)`}} />
      <ObjectSlot object={OBJECT} box={box} t={objT} />
      {placed.map(({l, i, p, right}) => {
        const on = onAt(i);
        if (on <= 0) return null;
        if (!side) {
          return (
            <div key={i} style={{position: 'absolute', left: p.x - dot * 2.2, top: p.y - dot * 2.2, width: dot * 4.4,
              height: dot * 4.4, borderRadius: '50%', background: ACC, color: ON_ACC, opacity: on, textAlign: 'center',
              font: `700 ${Math.round(dot * 2.6)}px/${dot * 4.4}px ${mono}`}}>{i + 1}</div>
          );
        }
        const y = rowY[i];
        const colX = right ? box.x + box.w + W * 0.03 : box.x - W * 0.03 - colW;
        const edgeX = right ? colX : colX + colW;
        const elbowX = right ? Math.max(p.x + W * 0.012, edgeX - W * 0.02) : Math.min(p.x - W * 0.012, edgeX + W * 0.02);
        const lineEndX = right ? edgeX - leaderGap : edgeX + leaderGap;   // stop short — the label reads as
        return (                                                          // NEXT to the line, not welded to it
          <React.Fragment key={i}>
            <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: on}}>
              <polyline points={`${p.x},${p.y} ${elbowX},${y} ${lineEndX},${y}`} fill="none" stroke={ACC}
                strokeWidth={hair * 1.5} opacity={0.85} />
              <circle cx={p.x} cy={p.y} r={dot} fill={ACC} />
            </svg>
            <div style={{position: 'absolute', left: colX, top: y - lblPx * 0.68, width: colW, opacity: on,
              textAlign: right ? 'left' : 'right', font: `500 ${lblPx}px/${lblLead} ${bodyF}`, color: DIM,
              textWrap: 'balance'}}>{l.text}</div>
          </React.Fragment>
        );
      })}
      {title ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop, width: capW, textAlign: 'center',
          opacity: titleIn, font: `700 ${titlePx}px/${tLead} ${disp}`, color: FG, textWrap: 'balance'}}>{title}</div>
      ) : null}
      {note ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop + titleH + noteGap, width: capW,
          textAlign: 'center', opacity: noteIn, font: `400 ${notePx}px/${nLead} ${bodyF}`, color: DIM}}>{note}</div>
      ) : null}
      {!side && nL ? (
        <div style={{position: 'absolute', left: (W - capW) / 2, top: wordsTop + wordsH + keyGap, width: capW,
          display: 'flex', flexDirection: 'column', gap: keyPx * 0.45}}>
          {LABELS.map((l, i) => (
            <div key={i} style={{opacity: onAt(i), font: `500 ${keyPx}px/${leading(keyLines[i], 1.35)} ${bodyF}`, color: DIM}}>
              <span style={{color: ACC, fontWeight: 700}}>{i + 1}</span>&nbsp;&nbsp;{l.text}</div>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default ObjectStage;
