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
// Standalone it shows its own preview form (objects/DemoForm, no words). A film must name its object —
// REQUIRED_IN_FILM, which validate.py reads.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {onAccentInk} from '../runtime/onAccent';
import {rows} from '../runtime/rows';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

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
  });
  const entry = useObjectEntry(OBJECT);
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0;
  const ON_ACC = onAccentInk(ACC, dna?.accent2, dna?.onAccent, FG);
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);

  // THE WORDS FIRST, SIZED TO THEIR COPY; THE OBJECT TAKES THE ROOM THEY LEAVE.
  const capW = Math.min(W * 0.84, 1240);
  const tLead = leading(title, 1.12), nLead = leading(note, 1.4);
  const titlePx = title ? fitBlockPx(title, capW, U * 0.13, Math.round(U * 0.05), {usable: 1, leading: tLead}) : 0;
  const titleH = title ? wrapLines(title, titlePx, capW) * titlePx * tLead : 0;
  const notePx = Math.round(U * 0.022);
  const noteH = note ? wrapLines(note, notePx, capW) * notePx * nLead : 0;
  const noteGap = title && note ? Math.round(U * 0.012) : 0;
  const wordsH = titleH + noteGap + noteH;
  const gap = wordsH ? Math.round(U * 0.03) : 0;

  // SIDE CALLOUTS where the frame has room beside the object; a NUMBERED KEY under the words where it does not.
  const nL = LABELS.length;
  const side = nL > 0 && W >= H * 1.2;
  const keyPx = Math.round(U * 0.02);
  const keyLines = LABELS.map((l, i) => `${i + 1}  ${l.text}`);
  const keyH = !side && nL
    ? keyLines.reduce((acc, s, i) => acc + (i ? keyPx * 0.45 : 0) + wrapLines(s, keyPx, capW) * keyPx * leading(s, 1.35), 0)
    : 0;
  const keyGap = keyH ? Math.round(U * 0.022) : 0;
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
  const onAt = (i: number) => easeOutCubic(clamp01(seg(t, LBL_A + i * step, LBL_A + i * step + 0.12)));
  const titleIn = easeOutCubic(clamp01(seg(t, 0.62, 0.78)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.66, 0.82)));

  // side callouts: each column ordered by height and pushed apart so no label overprints its neighbour; a column
  // that then runs past the content zone is lifted back as a whole
  const lblPx = Math.round(U * 0.02), lblLead = 1.3;
  const placed = LABELS.map((l, i) => ({l, i, p: {x: box.x + l.x * box.w, y: box.y + l.y * box.h},
    right: (l.side ?? (l.x >= 0.5 ? 'right' : 'left')) === 'right'}));
  const rowY: number[] = placed.map((q) => q.p.y);
  if (side) {
    for (const right of [true, false]) {
      const col = placed.filter((q) => q.right === right).sort((a, b) => a.p.y - b.p.y);
      let prev = -Infinity;
      for (const q of col) {
        rowY[q.i] = Math.max(q.p.y, prev + lblPx * 0.8);
        prev = rowY[q.i] + wrapLines(q.l.text, lblPx, colW) * lblPx * lblLead;
      }
      const over = prev - zBot;
      if (col.length && over > 0) col.forEach((q) => { rowY[q.i] -= over; });
    }
  }
  const dot = Math.max(4, Math.round(U * 0.006));
  const hair = Math.max(1, Math.round(W * 0.0012));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', opacity: floorIn,
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      {/* the floor it stands on: a soft shadow in the film's own ink, at a whisper */}
      <div style={{position: 'absolute', left: box.x + box.w * 0.08, top: floorY - U * 0.012, width: box.w * 0.84,
        height: U * 0.03, borderRadius: '50%', background: FG, opacity: 0.1 * floorIn,
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
        return (
          <React.Fragment key={i}>
            <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: on}}>
              <polyline points={`${p.x},${p.y} ${elbowX},${y} ${edgeX},${y}`} fill="none" stroke={ACC}
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
