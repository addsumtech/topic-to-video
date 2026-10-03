// SHOT · TechnicalPlate — an ordinary object drawn as a NUMBERED TECHNICAL ELEVATION: outline, callout
// leaders, a parts key, a plate number. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: "this everyday thing IS the mechanism." When a beat's point is that some unremarkable
// object does the load-bearing work — a bicycle that is really a station's last mile, a valve that is really
// the safety case, a paper form that is really the policy — the frame should treat it the way a patent plate
// or a parts catalogue treats an object: drawn flat, numbered, and annotated. That reading is what a factory
// conveyor belt or a product card cannot give it: a belt says "assembly line", a card says "feature", and a
// plate says "look at the thing itself, here are its parts".
//
// The object is described by props as a list of STROKES in unit space (0..1 across, 0..1 down), so any film
// can draw its own object without a new register: `parts` positions the callouts, `strokes` draws the thing —
// or, for a drawing the film already built in its workshop, `art` takes the strokes' place in that same square.
//
// THE DRAWING AND ITS CALLOUTS ARE ONE CLAIM, SO THEY COME FROM ONE PLACE. Both props used to default
// independently: a film that passed its own `parts` but no `strokes` got the demo BICYCLE, numbered with the
// film's part names — "1 知识库" pointing at a bicycle wheel — and a film that drew its own object but passed
// no `parts` got "the part that does the work" and "the part that steers" pinned to the bicycle's wheel and
// head-tube coordinates on top of it. A part without `x`/`y` was also placed at the drawing's centre
// (`p.x ?? 0.5`), and parts past the fourth started their fade at t >= 1 and were never seen at all. Now: pass
// `strokes` and `parts` together, or `art` (a drawing the film built) and `parts` together, or neither (neither
// is the standalone demo); every part needs `x` and `y`; a stroke missing a coordinate it needs throws; and
// the callout timing is spread over however many parts there are, up to six.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {CONTENT_TOP, captionBand, contentBottom, inkBlockH, wrapLines} from '../runtime/layout';
import {useDNA} from '../runtime/dna';
import {ObjectSlot, type ObjectRef} from '../runtime/objectSlot';

export const DURATION = 160;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7';

// `ghost` marks a part that is NOT THERE — demolished, never built, proposed. A plate that can only draw
// what exists cannot make the commonest argument a plate is used for: what is missing from this object.
type Stroke =
  | {kind: 'circle'; x: number; y: number; r: number; w?: number; ghost?: boolean}
  | {kind: 'line'; x: number; y: number; x2: number; y2: number; w?: number; ghost?: boolean}
  | {kind: 'bar'; x: number; y: number; w: number; h: number; fill?: boolean; ghost?: boolean};

type Part = {n?: number; label?: string; x?: number; y?: number; side?: 'left' | 'right'};

// A bicycle, as the default — the object this register was built for, and a legible example of the
// stroke vocabulary for anyone authoring a different one.
const BIKE: Stroke[] = [
  {kind: 'circle', x: 0.20, y: 0.66, r: 0.15},
  {kind: 'circle', x: 0.78, y: 0.66, r: 0.15},
  {kind: 'line', x: 0.20, y: 0.66, x2: 0.44, y2: 0.66},
  {kind: 'line', x: 0.44, y: 0.66, x2: 0.36, y2: 0.36},
  {kind: 'line', x: 0.36, y: 0.36, x2: 0.20, y2: 0.66},
  {kind: 'line', x: 0.44, y: 0.66, x2: 0.62, y2: 0.34},
  {kind: 'line', x: 0.36, y: 0.36, x2: 0.62, y2: 0.34},
  {kind: 'line', x: 0.62, y: 0.34, x2: 0.78, y2: 0.66},
  {kind: 'line', x: 0.62, y: 0.34, x2: 0.70, y2: 0.22},
  {kind: 'line', x: 0.62, y: 0.22, x2: 0.78, y2: 0.22},
  {kind: 'line', x: 0.36, y: 0.36, x2: 0.34, y2: 0.24},
  {kind: 'bar', x: 0.28, y: 0.22, w: 0.12, h: 0.026, fill: true},
];
// Placeholder callouts, deliberately generic. These read 'the last mile' / 'no timetable' — the exact copy
// of the beat this register was written during — so the register shipped one film's argument as its default
// and any later film that forgot to set `parts` silently inherited it.
const BIKE_PARTS: Part[] = [
  {n: 1, label: 'the part that does the work', x: 0.20, y: 0.66, side: 'left'},
  {n: 2, label: 'the part that steers', x: 0.62, y: 0.34, side: 'right'},
];

export const MAX_PLATE_PARTS = 6;
// A SLOT THAT TAKES ANOTHER PROP'S PLACE. `art` is drawn instead of `strokes` and the two are refused together, so a
// beat that sets `art` has not left `strokes` to the demo bicycle; scripts/shot_proof.py reads this before it calls
// an unset `strokes` the register's own demo content.
export const SLOT_REPLACES = {art: ['strokes']} as const;

const isNum = (v: unknown) => typeof v === 'number' && Number.isFinite(v);

// A stroke is geometry the film authored; one missing a coordinate would draw at NaN (nothing, silently) or be
// patched with a guess. Each kind names what it needs.
const checkStroke = (st: any, i: number): Stroke => {
  const need: Record<string, string[]> = {circle: ['x', 'y', 'r'], line: ['x', 'y', 'x2', 'y2'], bar: ['x', 'y', 'w', 'h']};
  const keys = need[st?.kind];
  if (!keys) {
    throw new Error(`TechnicalPlate: stroke ${i + 1} has kind ${JSON.stringify(st?.kind)} — use 'circle' {x, y, r}, ` +
      "'line' {x, y, x2, y2} or 'bar' {x, y, w, h}, all in unit space.");
  }
  const missing = keys.filter((k) => !isNum(st[k]));
  if (missing.length) {
    throw new Error(`TechnicalPlate: stroke ${i + 1} ('${st.kind}') is missing ${missing.map((k) => `\`${k}\``).join(', ')} ` +
      '(numbers in unit space, 0..1 of the drawing).');
  }
  return st as Stroke;
};

export const TechnicalPlate: React.FC<{
  kicker?: string;
  object?: string;          // what it is, set under the plate
  plateNo?: string;         // the plate's own number, like a real sheet
  strokes?: Stroke[];       // the object, in unit space
  art?: ObjectRef;          // a drawing the FILM made (runtime/objectSlot), in place of `strokes`
  parts?: Part[];           // numbered callouts with leader lines
  note?: string;
}> = ({
  kicker = 'PLATE',
  object = 'the object',
  plateNo = '',
  strokes: STROKES = BIKE,
  art,
  parts: PARTS = BIKE_PARTS,
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0012));

  // ONE SOURCE FOR THE OBJECT AND ITS PARTS (see the header). Identity with the module constants is how the shot
  // knows a prop was left out: a film's props arrive as fresh arrays, never as BIKE itself.
  const demoStrokes = STROKES === BIKE, demoParts = PARTS === BIKE_PARTS;
  if (art) {
    // A DRAWING THE FILM MADE takes the strokes' place — and is still ONE claim with its callouts.
    if (!demoStrokes) {
      throw new Error("TechnicalPlate got both `art` and `strokes` — one drawing per plate: the film's own " +
        '(`art`, from its workshop) or strokes, not both.');
    }
    if (demoParts) {
      throw new Error("TechnicalPlate got `art` but no `parts`, so it would pin the demo callouts to the film's " +
        'drawing. Pass `parts: [{n, label, x, y, side}]` at points on the art (0..1 of its square), or `parts: []`.');
    }
  } else if (demoStrokes !== demoParts) {
    throw new Error(demoStrokes
      ? 'TechnicalPlate got `parts` but no `strokes`, so it would number the film\'s parts on its demo BICYCLE. ' +
        'Pass `strokes` that draw the object those parts belong to (circle / line / bar in unit space), or cast ' +
        'a register that does not need a drawing.'
      : 'TechnicalPlate got `strokes` but no `parts`, so it would pin the demo callouts ("the part that does the ' +
        'work") to the demo bicycle\'s coordinates on top of the film\'s object. Pass `parts: [{n, label, x, y, ' +
        'side}]` naming the film\'s own parts, or `parts: []` for an unannotated drawing.');
  }
  if (!Array.isArray(STROKES) || STROKES.length < 1) {
    throw new Error(`TechnicalPlate needs at least one stroke in \`strokes\` (got ${Array.isArray(STROKES) ? 0 : typeof STROKES}) — the plate IS the drawing.`);
  }
  STROKES.forEach(checkStroke);
  if (!Array.isArray(PARTS) || PARTS.length > MAX_PLATE_PARTS) {
    throw new Error(
      `TechnicalPlate takes 0-${MAX_PLATE_PARTS} \`parts\` (got ${Array.isArray(PARTS) ? PARTS.length : typeof PARTS}). ` +
      'Past six the callouts on each side of the sheet overprint one another — keep the parts the argument ' +
      'names, or split the object across two plates.');
  }
  PARTS.forEach((p, i) => {
    if (!isNum(p?.x) || !isNum(p?.y)) {
      throw new Error(
        `TechnicalPlate: part ${i + 1}${p?.label ? ` ("${p.label}")` : ''} needs \`x\` and \`y\` in the drawing's ` +
        `unit space (got x=${String(p?.x)}, y=${String(p?.y)}). The callout's dot says "this part is HERE"; ` +
        'without a point it would sit on the middle of the object.');
    }
  });

  const top = CONTENT_TOP + H * 0.02;
  const bottom = H - captionBand(W, H) - H * 0.09;
  // the drawing occupies a square-ish field, so the object keeps its proportions at any aspect
  const fieldH = bottom - top;
  const fieldW = Math.min(W * 0.52, fieldH * 1.45);
  const fx0 = (W - fieldW) / 2, fy0 = top;
  // The object is drawn in SQUARE unit space. Mapping u by fieldW and v by fieldH independently destroys
  // its proportions the moment the sheet is not ~1.45:1 — at 9:16 the default bicycle came out with its two
  // wheels overlapping. The drawing keeps its shape and is centred in the sheet; only the SHEET reflows.
  const unit = Math.min(fieldW, fieldH);
  const ox = fx0 + (fieldW - unit) / 2, oy = fy0 + (fieldH - unit) / 2;

  // THE PLATE CAPTION IS TWO BLOCKS AT FIXED OFFSETS, and both assume one line — the same shape as
  // ProfileGrowth's, and it fails the same way: a Chinese object name wraps, the note starts inside it, and
  // the pair reaches 66px into the caption band. Derived from the lines the copy takes in `fieldW`, clamped
  // to the zone, and identical to the old offsets for one-line Latin. Computed here, ahead of the drawing
  // square below, because a drawing the film made is capped against it.
  const OBJ_PX = Math.round(W * 0.028), PNOTE_PX = Math.round(W * 0.0145);
  const objH = wrapLines(String(object ?? ''), OBJ_PX, fieldW) * OBJ_PX * 1.2;
  const pnoteH = note ? wrapLines(String(note), PNOTE_PX, fieldW) * PNOTE_PX * 1.4 : 0;
  const pGap = Math.max(0, Math.round(W * 0.032) - Math.round(OBJ_PX * 1.2));
  const plateBlockH = objH + (note ? pGap + pnoteH : 0);
  const plateCapTop = Math.min(bottom + H * 0.030,
    contentBottom(W, H) - plateBlockH - (inkBlockH(PNOTE_PX) - PNOTE_PX));
  const plateNoteTop = plateCapTop + objH + pGap;

  // A DRAWING THE FILM MADE USUALLY PAINTS ITS WHOLE BOX, where a hand-drawn stroke leaves room around itself —
  // so at a full-height square (16:9, 4:3) a two-line name and note can rise into it: the identity film's own
  // copy started 16px into the square for a one-line pair, ~55px for a two-line note, ~81px for both two lines.
  // `art`'s own square is capped so its bottom never passes `plateCapTop`; the strokes path never asked for
  // more than `unit` and keeps it, unchanged. The callouts map through the SAME square the art is actually
  // drawn in (`ux`/`uy`, just below), so a part at y=0.9 still lands on the drawing rather than in the space
  // this capping frees up.
  //
  // THE SHEET ENDS ABOVE ITS CAPTION, on the art path. When the caption is lifted out of the caption band (a
  // name with a note at 16:9 is enough), `plateCapTop` rises above the field's own bottom and the sheet's rule
  // ran straight through the object's name. A drawing the film made is fitted to the sheet that is left, at
  // the same gap an unlifted caption keeps from it; with no lift the sheet, the square and the callouts are
  // exactly what they were. The strokes path keeps the sheet it has always drawn.
  const sheetH = art ? Math.max(1, Math.min(fieldH, plateCapTop - H * 0.030 - fy0)) : fieldH;
  const artUnit = art ? Math.max(1, Math.min(unit, sheetH, plateCapTop - H * 0.02 - oy)) : unit;
  const artX = art ? fx0 + (fieldW - artUnit) / 2 : ox;
  const artY = art ? Math.max(fy0, Math.min(oy, fy0 + sheetH - artUnit)) : oy;
  const ux = (u: number) => artX + u * artUnit;
  const uy = (v: number) => artY + v * artUnit;

  const sheet = easeOutCubic(clamp01(seg(t, 0.02, 0.18)));
  const draw = clamp01(seg(t, 0.14, 0.62));
  const land = easeOutExpo(clamp01(seg(t, 0.66, 0.88)));
  const lw = Math.max(2, Math.round(W * 0.0026));

  const nS = Math.max(1, STROKES.length);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      <div style={{position: 'absolute', left: fx0, top: CONTENT_TOP - H * 0.055, opacity: sheet,
        font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: ACC,
        letterSpacing: dna?.labelSpacing ?? '0.14em',
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      {plateNo ? (
        <div style={{position: 'absolute', right: fx0, top: CONTENT_TOP - H * 0.055, opacity: sheet,
          font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, color: DIM,
          letterSpacing: '0.10em'}}>{plateNo}</div>
      ) : null}

      {/* the sheet: a ruled field with corner ticks, the way a drawing sheet is bounded */}
      <div style={{position: 'absolute', left: fx0, top: fy0, width: fieldW * sheet, height: sheetH,
        border: `${hair}px solid ${LINE}`, boxSizing: 'border-box'}} />

      {/* the object, drawn stroke by stroke */}
      {art ? <ObjectSlot object={art} box={{x: artX, y: artY, w: artUnit, h: artUnit}} t={draw} /> : STROKES.map((st, i) => {
        const on = easeOutCubic(clamp01(draw * nS - i));
        if (on <= 0) return null;
        if (st.kind === 'circle') {
          const r = st.r * unit;
          return (
            <div key={i} style={{position: 'absolute', left: ux(st.x) - r, top: uy(st.y) - r,
              width: r * 2, height: r * 2, borderRadius: '50%',
              // @fallback: on a circle or a line `w` is the STROKE WEIGHT multiplier (1 = the plate's hairline), a drawing parameter, not a reading about the part
              border: `${Math.max(2, Math.round((st.w ?? 1) * lw))}px ${st.ghost ? 'dashed' : 'solid'} ${st.ghost ? DIM : FG}`,
              opacity: on * (st.ghost ? 0.6 : 1), transform: `scale(${0.85 + 0.15 * on})`}} />
          );
        }
        if (st.kind === 'bar') {
          return (
            <div key={i} style={{position: 'absolute', left: ux(st.x), top: uy(st.y),
              width: st.w * unit * on, height: Math.max(2, st.h * unit),
              background: st.fill ? (st.ghost ? DIM : FG) : 'transparent',
              border: st.fill ? 'none' : `${lw}px ${st.ghost ? 'dashed' : 'solid'} ${st.ghost ? DIM : FG}`,
              opacity: on * (st.ghost ? 0.55 : 1)}} />
          );
        }
        const x1 = ux(st.x), y1 = uy(st.y), x2 = ux(st.x2), y2 = uy(st.y2);
        const len = Math.hypot(x2 - x1, y2 - y1) * on;
        const ang = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        return (
          <div key={i} style={{position: 'absolute', left: x1, top: y1 - lw / 2, width: len,
            // @fallback: on a circle or a line `w` is the STROKE WEIGHT multiplier (1 = the plate's hairline), a drawing parameter, not a reading about the part
            height: Math.max(2, Math.round((st.w ?? 1) * lw)),
            background: st.ghost ? 'transparent' : FG,
            // @fallback: on a circle or a line `w` is the STROKE WEIGHT multiplier (1 = the plate's hairline), a drawing parameter, not a reading about the part
            borderTop: st.ghost ? `${Math.max(2, Math.round((st.w ?? 1) * lw))}px dashed ${DIM}` : undefined,
            opacity: st.ghost ? 0.6 : 1,
            transformOrigin: '0 50%', transform: `rotate(${ang}deg)`}} />
        );
      })}

      {/* numbered callouts with leader lines out to the margin */}
      {PARTS.map((p, i) => {
        // Spread over however many parts there are. A fixed 0.10 step put part 5's fade-in at t = 1.0, so every
        // part past the fourth was drawn at opacity 0 — present in props, absent from the film.
        const step = Math.min(0.10, 0.22 / Math.max(1, PARTS.length));
        const on = easeOutCubic(clamp01(seg(t, 0.60 + i * step, 0.76 + i * step)));
        if (on <= 0) return null;
        const right = (p.side ?? 'right') === 'right';
        const px = ux(p.x as number), py = uy(p.y as number);
        const lx = right ? fx0 + fieldW + W * 0.020 : fx0 - W * 0.020;
        const len = Math.abs(lx - px) * on;
        const dot = Math.max(4, Math.round(W * 0.0035));
        return (
          <React.Fragment key={'p' + i}>
            <div style={{position: 'absolute', left: px - dot, top: py - dot, width: dot * 2,
              height: dot * 2, borderRadius: dot, background: ACC, opacity: on}} />
            <div style={{position: 'absolute', left: right ? px : px - len, top: py - hair / 2,
              width: len, height: hair, background: ACC, opacity: 0.8}} />
            <div style={{position: 'absolute', top: py - Math.round(W * 0.014), opacity: on,
              left: right ? lx + W * 0.006 : undefined, right: right ? undefined : W - lx + W * 0.006,
              width: W * 0.17, textAlign: right ? 'left' : 'right',
              font: `500 ${Math.round(W * 0.0145)}px/1.3 ${mono}`, color: DIM}}>
              <span style={{color: ACC, fontWeight: 700}}>{p.n ?? i + 1}</span>&nbsp;&nbsp;{p.label}
            </div>
          </React.Fragment>
        );
      })}

      {/* the object's name, set under the sheet like a plate caption */}
      <div style={{position: 'absolute', left: fx0, top: plateCapTop, width: fieldW,
        textAlign: 'center', opacity: land,
        font: `700 ${Math.round(W * 0.028)}px/1.2 ${disp}`, color: FG}}>{object}</div>
      {note ? (
        <div style={{position: 'absolute', left: fx0, top: plateNoteTop,
          width: fieldW, textAlign: 'center', opacity: land * 0.9,
          font: `400 ${Math.round(W * 0.0135)}px/1.4 var(--f-body, system-ui, sans-serif)`,
          color: DIM}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default TechnicalPlate;
