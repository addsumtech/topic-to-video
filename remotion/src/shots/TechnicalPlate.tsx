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
//
// A CALLOUT READS WHEN THE VOICE NAMES ITS PART (runtime/cue.ts). The callouts are dealt in the last fifth of the
// beat, and a narration that walks the parts from its first sentence left them seconds late — the first one 3.2 s
// after the voice said it on a delivered film, with the beat's clock already warped as far as the warp may go. A
// cued callout starts early enough to read on its word, never later than its own slot. The drawing keeps its own
// pace: the callout may arrive while its part is still being drawn (measured on that film, the pan was drawn
// within a second of its callout), which is the voice and the pen naming the same thing together; compressing
// the drawing instead would have moved the art's own events (the pour) off the sentence that describes them.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {CONTENT_TOP, captionBand, contentBottom, inkBlockH, wrapLines} from '../runtime/layout';
import {useDNA} from '../runtime/dna';
import {ObjectSlot, type ObjectRef} from '../runtime/objectSlot';
import {useCues, REACH_CUBIC, REACH_EXPO} from '../runtime/cue';

export const DURATION = 160;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7';
const DRAW_B = 0.62;        // the art's own t lands here; an art object's idle clock runs from it (runtime/objectSlot)

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

// THE OBJECT, STROKE BY STROKE — one renderer for both layouts below. `on` per stroke is the pen's progress.
const plateStrokes = (STROKES: Stroke[], draw: number, unit: number, ux: (u: number) => number,
  uy: (v: number) => number, lw: number, FG: string, DIM: string) => {
  const nS = Math.max(1, STROKES.length);
  return STROKES.map((st, i) => {
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
  });
};

// THE SIDE-CALLOUT SHEET NEEDS A WIDE FRAME. Its labels hang in two columns of 0.17 W beside a sheet of 0.52 W, and
// every size is a fraction of W. On a 9:16 frame that left the drawing a 561 px square floating in a 1270 px-tall
// sheet — the object at ~50% of the width, measured on a GPS satellite, and down to ~35% for art that paints less of
// its square — with callouts set at 15.7 px, the kicker at 13.5 px and the note at 14.6 px (the type floor is 23.8 px).
// 1:1, 4:5 and 4:3 shared it in proportion. A frame narrower than this is drawn as a patent plate is drawn instead:
// the object as large as the frame allows, a NUMBER at the end of each leader, and the names in a parts KEY.
export const PLATE_SIDE_MIN_ASPECT = 1.6;

type PlateKeyArgs = {
  W: number; H: number; t: number; cue: ReturnType<typeof useCues>; dna: ReturnType<typeof useDNA>;
  kicker: string; object: string; plateNo: string; strokes: Stroke[]; art?: ObjectRef; parts: Part[]; note: string;
};

/**
 * The plate on a frame narrower than PLATE_SIDE_MIN_ASPECT (9:16, 4:5, 1:1, 4:3): a numbered drawing and its key.
 *
 * Type is a fraction of the frame's SHORT side scaled to the 16:9 sizes (TU = min(W, H) * 16/9 is W at 16:9), so a
 * label is the size it is on the wide sheet, not a third smaller. The key goes BELOW the drawing or BESIDE it —
 * whichever leaves the larger square: on a tall frame below (the width is the drawing's), on a square frame beside
 * (the height is). Exported so the slot-identity reference (tests/test_slot_identity.py) draws the same layout.
 */
export const renderPlateKey = ({W, H, t, cue, dna, kicker, object, plateNo, strokes: STROKES, art, parts: PARTS,
  note}: PlateKeyArgs) => {
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const short = Math.min(W, H);
  const TU = short * 16 / 9;
  const hair = Math.max(1, Math.round(short * 0.0012 * 16 / 9));
  const lw = Math.max(2, Math.round(TU * 0.0026));
  const KICK = Math.round(TU * 0.0156), NUM = Math.round(TU * 0.016), KEY = Math.round(TU * 0.016);
  const OBJ = Math.round(TU * 0.028), NOTE = Math.round(TU * 0.016);
  const mx = Math.round(W * 0.06);
  const gap = Math.round(short * 0.035);
  const top = CONTENT_TOP + short * 0.02;
  const zoneH = contentBottom(W, H) - top;

  // each leader ends in a number just outside the square, on its part's side: room is reserved only on a side used
  const sideOf = (p: Part) => p.side ?? 'right';
  const badgeW = Math.round(NUM * 2.0);
  const padL = PARTS.some((p) => sideOf(p) === 'left') ? badgeW : 0;
  const padR = PARTS.some((p) => sideOf(p) === 'right') ? badgeW : 0;
  const numW = Math.round(KEY * 1.9);
  // a label's width is a property of its face and script (E2): a Han glyph is a full em in the mono stack's CJK
  // fallback, a Latin one ~0.62 em — wrapLines is told the Latin advance and keeps its own CJK one
  const rowsIn = (colW: number) => PARTS.map((p) => wrapLines(String(p.label ?? ''), KEY, Math.max(1, colW - numW),
    {adv: 0.62}));
  const rowGap = Math.round(KEY * 0.45);
  const keyHeight = (colW: number) => PARTS.length
    ? rowsIn(colW).reduce((a, n) => a + n * KEY * 1.3, 0) + (PARTS.length - 1) * rowGap : 0;
  // the plate caption — the object's name and its note — measured in the width it is given
  const capGap = Math.round(OBJ * 0.35);
  const capHeight = (w: number) => wrapLines(String(object ?? ''), OBJ, w) * OBJ * 1.2 +
    (note ? capGap + wrapLines(String(note), NOTE, w) * NOTE * 1.4 : 0) +
    (inkBlockH(note ? NOTE : OBJ) - (note ? NOTE : OBJ));

  // THREE ARRANGEMENTS, and the one that leaves the LARGEST drawing wins. Every block is measured at the width it is
  // then drawn in (E1) — a key measured full-width and drawn under a small square wrapped into the name below it.
  //   A · below:  square / key / caption, the key and caption full width       (tall frames: 9:16, 4:5)
  //   B · beside: square | key, then caption, in one column                   (square and 4:3 frames)
  //   C · beside, caption below: [square | key] / caption full width          (a long name that will not fit a column)
  type Arr = {side: number; sx: number; sy: number; keyX: number; keyY: number; keyW: number; capX: number;
    capTop: number; capW: number; align: 'left' | 'center'; need: number};
  const nP = PARTS.length;
  const capW = W - 2 * mx;
  const capLead = Math.round(gap * 1.4);
  const estW = (s: string, px: number) =>
    [...s].reduce((a, ch) => a + px * (/[⺀-鿿豈-﫿＀-￯]/.test(ch) ? 1 : 0.62), 0);
  const longest = Math.max(0, ...PARTS.map((p) => estW(String(p.label ?? ''), KEY)));
  // a column wide enough for the longest label, and for the name on one line when that costs little (a short name
  // broken in two leaves one glyph on its own line; a long one wraps rather than starving the drawing of width)
  const nameW = estW(String(object ?? ''), OBJ);
  const colW = Math.min(W * 0.42, Math.max(W * 0.24, numW + longest, nameW <= W * 0.34 ? nameW : 0));
  const besideGap = Math.max(gap, Math.round(NUM * 2.5));   // the right-hand numbers are not read as key rows
  const roomBeside = W - 2 * mx - padL - padR - besideGap - colW;
  const arrs: Arr[] = [];
  {
    const keyH = keyHeight(capW), rest = (nP ? gap + keyH : 0) + capLead + capHeight(capW);
    const side = Math.min(W - 2 * mx - padL - padR, zoneH - rest);
    const y0 = top + Math.max(0, (zoneH - side - rest) / 2);
    const sx = (W - (padL + side + padR)) / 2 + padL;
    arrs.push({side, sx, sy: y0, keyX: mx, keyY: y0 + side + gap, keyW: capW, capX: mx,
      capTop: y0 + side + (nP ? gap + keyH : 0) + capLead, capW, align: 'center', need: side + rest});
  }
  if (nP) {
    const keyH = keyHeight(colW);
    const colH = keyH + capLead + capHeight(colW);
    const side = Math.min(zoneH, roomBeside);
    const h = Math.max(side, colH);
    const y0 = top + Math.max(0, (zoneH - h) / 2);
    const sx = (W - (padL + side + padR + besideGap + colW)) / 2 + padL;
    const keyX = sx + side + padR + besideGap, keyY = y0 + (h - colH) / 2;
    arrs.push({side, sx, sy: y0 + (h - side) / 2, keyX, keyY, keyW: colW, capX: keyX, capTop: keyY + keyH + capLead,
      capW: colW, align: 'left', need: h});
    const capH = capHeight(capW);
    const sideC = Math.min(zoneH - capLead - capH, roomBeside);
    const hC = Math.max(sideC, keyH);
    const y0C = top + Math.max(0, (zoneH - hC - capLead - capH) / 2);
    const sxC = (W - (padL + sideC + padR + besideGap + colW)) / 2 + padL;
    arrs.push({side: sideC, sx: sxC, sy: y0C + (hC - sideC) / 2, keyX: sxC + sideC + padR + besideGap,
      keyY: y0C + (hC - keyH) / 2, keyW: colW, capX: mx, capTop: y0C + hC + capLead, capW, align: 'center',
      need: hC + capLead + capH});
  }
  const MIN_SIDE = short * 0.2;
  const fits = arrs.filter((a) => a.side >= MIN_SIDE && a.need <= zoneH + 0.5);
  if (!fits.length) {
    const best = arrs.reduce((a, b) => (b.side > a.side ? b : a));
    throw new Error(`TechnicalPlate at ${W}x${H}: the key (${nP} part${nP === 1 ? '' : 's'}) and the name/note leave ` +
      `the drawing ${Math.max(0, Math.round(best.side))} px (it needs ${Math.round(MIN_SIDE)}) — shorten the labels, ` +
      'the name or the note, or name fewer parts on this plate.');
  }
  const L = fits.reduce((a, b) => (b.side > a.side ? b : a));
  const {side, sx, sy} = L;
  const keyX = L.keyX, keyY = L.keyY, keyColWidth = L.keyW, capX = L.capX, capColW = L.capW, capTop = L.capTop;
  const beside = L.align === 'left';
  const objH = wrapLines(String(object ?? ''), OBJ, capColW) * OBJ * 1.2;
  const noteTop = capTop + objH + capGap;
  const ux = (u: number) => sx + u * side;
  const uy = (v: number) => sy + v * side;

  const sheet = easeOutCubic(clamp01(seg(t, 0.02, 0.18)));
  const draw = clamp01(seg(t, 0.14, DRAW_B));
  const land = easeOutExpo(clamp01(seg(t, ...cue.win('object', 0.66, 0.88, REACH_EXPO))));
  const noteLand = easeOutExpo(clamp01(seg(t, ...cue.win('note', 0.66, 0.88, REACH_EXPO))));

  // badges on one side are kept a line apart, in the order of their parts down the drawing
  const badgeY: number[] = PARTS.map((p) => uy(p.y as number));
  (['left', 'right'] as const).forEach((sd) => {
    const idx = PARTS.map((p, i) => i).filter((i) => sideOf(PARTS[i]) === sd).sort((a, b) => badgeY[a] - badgeY[b]);
    for (let k = 1; k < idx.length; k++) {
      badgeY[idx[k]] = Math.max(badgeY[idx[k]], badgeY[idx[k - 1]] + NUM * 1.35);
    }
  });
  const step = Math.min(0.10, 0.22 / Math.max(1, PARTS.length));
  const partOn = PARTS.map((_p, i) => easeOutCubic(clamp01(seg(t, ...cue.win('parts.' + i, 0.60 + i * step,
    0.76 + i * step, REACH_CUBIC)))));
  const rows = rowsIn(keyColWidth);
  let ry = keyY;
  const rowTop = rows.map((n) => { const y = ry; ry += n * KEY * 1.3 + rowGap; return y; });
  const dot = Math.max(4, Math.round(TU * 0.0035));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      <div style={{position: 'absolute', left: mx, top: CONTENT_TOP - Math.round(KICK * 2.2), opacity: sheet,
        font: `600 ${KICK}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      {plateNo ? (
        <div style={{position: 'absolute', right: mx, top: CONTENT_TOP - Math.round(KICK * 2.2), opacity: sheet,
          font: `600 ${KICK}px/1.2 ${mono}`, color: DIM, letterSpacing: '0.10em'}}>{plateNo}</div>
      ) : null}

      {/* the sheet: the drawing's own square, ruled */}
      <div style={{position: 'absolute', left: sx, top: sy, width: side * sheet, height: side,
        border: `${hair}px solid ${LINE}`, boxSizing: 'border-box'}} />
      {art ? <ObjectSlot object={art} box={{x: sx, y: sy, w: side, h: side}} t={draw} idleFrom={DRAW_B} />
        : plateStrokes(STROKES, draw, side, ux, uy, lw, FG, DIM)}

      {/* each part: a dot, a leader to the square's edge, a number past it */}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {PARTS.map((p, i) => {
          const on = partOn[i];
          if (on <= 0) return null;
          const right = sideOf(p) === 'right';
          const px = ux(p.x as number), py = uy(p.y as number);
          const edge = right ? sx + side + badgeW * 0.25 : sx - badgeW * 0.25;
          const by = badgeY[i];
          return (
            <g key={'l' + i} opacity={on}>
              <polyline points={`${px},${py} ${edge},${py} ${right ? edge + badgeW * 0.2 : edge - badgeW * 0.2},${by}`}
                fill="none" stroke={ACC} strokeWidth={hair} opacity={0.8} />
              <circle cx={px} cy={py} r={dot} fill={ACC} />
            </g>
          );
        })}
      </svg>
      {PARTS.map((p, i) => {
        const on = partOn[i];
        if (on <= 0) return null;
        const right = sideOf(p) === 'right';
        return (
          <div key={'b' + i} style={{position: 'absolute', top: badgeY[i] - NUM * 0.62, opacity: on,
            left: right ? sx + side + badgeW * 0.5 : undefined, right: right ? undefined : W - (sx - badgeW * 0.5),
            font: `700 ${NUM}px/1.2 ${mono}`, color: ACC}}>{p.n ?? i + 1}</div>
        );
      })}

      {/* the parts key */}
      {PARTS.map((p, i) => (
        <div key={'k' + i} style={{position: 'absolute', left: keyX, top: rowTop[i], width: keyColWidth,
          opacity: partOn[i], display: 'flex', font: `500 ${KEY}px/1.3 ${mono}`, color: DIM}}>
          <span style={{flex: `0 0 ${numW}px`, color: ACC, fontWeight: 700}}>{p.n ?? i + 1}</span>
          <span style={{flex: '1 1 auto', textWrap: 'balance'}}>{p.label}</span>
        </div>
      ))}

      {/* balanced: Chinese breaks between any two glyphs, and a last line of one glyph reads as a stray (cjk_type_qa);
          balancing keeps the line count wrapLines measured */}
      <div style={{position: 'absolute', left: capX, top: capTop, width: capColW, textAlign: beside ? 'left' : 'center',
        textWrap: 'balance', opacity: land, font: `700 ${OBJ}px/1.2 ${disp}`, color: FG}}>{object}</div>
      {note ? (
        <div style={{position: 'absolute', left: capX, top: noteTop, width: capColW, textAlign: beside ? 'left' : 'center',
          textWrap: 'balance', opacity: noteLand * 0.9, font: `400 ${NOTE}px/1.4 var(--f-body, system-ui, sans-serif)`,
          color: DIM}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
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
  const cue = useCues();
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

  if (W < H * PLATE_SIDE_MIN_ASPECT) {
    return renderPlateKey({W, H, t, cue, dna, kicker, object, plateNo, strokes: STROKES, art, parts: PARTS, note});
  }
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
  const draw = clamp01(seg(t, 0.14, DRAW_B));
  const land = easeOutExpo(clamp01(seg(t, ...cue.win('object', 0.66, 0.88, REACH_EXPO))));
  const noteLand = easeOutExpo(clamp01(seg(t, ...cue.win('note', 0.66, 0.88, REACH_EXPO))));
  const lw = Math.max(2, Math.round(W * 0.0026));

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
      {art ? <ObjectSlot object={art} box={{x: artX, y: artY, w: artUnit, h: artUnit}} t={draw}
        idleFrom={DRAW_B} /> : plateStrokes(STROKES, draw, unit, ux, uy, lw, FG, DIM)}

      {/* numbered callouts with leader lines out to the margin */}
      {PARTS.map((p, i) => {
        // Spread over however many parts there are. A fixed 0.10 step put part 5's fade-in at t = 1.0, so every
        // part past the fourth was drawn at opacity 0 — present in props, absent from the film.
        const step = Math.min(0.10, 0.22 / Math.max(1, PARTS.length));
        const on = easeOutCubic(clamp01(seg(t, ...cue.win('parts.' + i, 0.60 + i * step, 0.76 + i * step, REACH_CUBIC))));
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
          width: fieldW, textAlign: 'center', opacity: noteLand * 0.9,
          font: `400 ${Math.round(W * 0.0135)}px/1.4 var(--f-body, system-ui, sans-serif)`,
          color: DIM}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default TechnicalPlate;
