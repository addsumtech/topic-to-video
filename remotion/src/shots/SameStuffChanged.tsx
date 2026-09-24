// SHOT · SameStuffChanged — one body of material, re-formed at each stage, never leaving the frame.
//
// THE ARGUMENT SHAPE, and why four stages side by side cannot carry it. PROCESS is the second-emptiest
// shape in this library: the process registers measure a median of 4.0% ink and NONE clears the 12% floor.
// The reason is the same one `RestsOn` recorded for mechanism — the conventional drawing is boxes with
// arrows between them, and the space BETWEEN the boxes is most of the frame. `MRIPipeline` draws four
// stages left to right and measures 4.1%; `InOrder` draws equal bands in time and measures 5.0%.
//
// The claim a process actually makes is not "these four things happen". It is "the SAME thing is what
// changes". So there are no stages here: there is one body of material occupying the whole content zone,
// and at each stage it is RE-FORMED — the same area, redistributed. The frame is never partly empty,
// because the material never goes anywhere, which is also the argument. `MadeOf` proved the density half
// of this (area is the quantity, 52.6% ink); what this adds is that the area is CONSERVED while its shape
// is not.
//
// CONSERVATION IS THE RULE, AND IT IS ENFORCED. Every stage's cells are normalised to the same total area,
// so a film cannot draw a process that quietly creates or destroys material — which is the visual form of
// the claim this register exists to refuse. If a stage genuinely loses some, the film says so with a
// `lost` share and it is drawn as the part that leaves; nothing vanishes silently.
//
// WHAT IT IS NOT. `MRIPipeline` shows four different pictures of four different things. `InOrder` is about
// ORDER, its bands equal citizens. `WorksThrough` cuts ONE body open and threads a path through its parts
// — it answers "how does it work", static body, moving path; this one answers "what happens to it", the
// body itself moving. `MadeOf` partitions once and does not change.
//
// EVERY WORD COMES FROM A PROP, and `share` is unitless — it sets an area and is never printed, so the
// register cannot put a figure on screen that no source supports.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeInOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP, fitsBox, inkBlockH, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix, readableOn, dimOn} from '../runtime/dna';
import {rows} from '../runtime/rows';

export const DURATION = 195; // 6.5s — each re-forming has to be seen HAPPENING, not cut to

const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', ACC_D0 = '#e0563f', DIM_D0 = '#7b8a9c', LINE_D0 = '#22303f';

export const MAX_STAGES = 4;
export const MAX_CELLS = 8;

type Stage = {
  /** what this stage is, in the film's words */
  label?: string;
  /** the material as it stands HERE — one entry per part, each `{name, share}`. Areas, never printed. */
  cells?: {name?: string; share?: number}[];
  /** the share that LEAVES at this stage, if any — drawn as the part that goes, never dropped silently */
  lost?: number;
  /** what the loss is called */
  lostLabel?: string;
};

const DEMO: Stage[] = [
  {label: 'as it arrives', cells: [{name: 'all of it', share: 1}]},
  {label: 'sorted', cells: [{name: 'one kind', share: 0.6}, {name: 'the other', share: 0.4}]},
  {label: 'most of it set aside', cells: [{name: 'what is kept', share: 0.45}], lost: 0.55,
   lostLabel: 'set aside'},
];

export const SameStuffChanged: React.FC<{
  kicker?: string;
  /** the stages, in order — 2 to MAX_STAGES */
  stages?: Stage[];
  /** one line under the body, in the film's voice */
  note?: string;
}> = ({kicker: KICK = 'THE SAME MATERIAL, RE-FORMED', stages: STAGES_IN = DEMO,
       note: NOTE = 'nothing here is a new thing; it is the same thing, differently arranged'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  // A WRONG SHAPE REFUSES IN WORDS. Fed a `cells` that was not an array this called `.some` on it and threw
  // `(s.cells || []).some is not a function` — an error naming a line of this file and not the thing the
  // caller got wrong. Dropping the bad stage silently was the first repair and it was no better: the
  // register then refused with a message about the stage COUNT, sending the reader to look for data that
  // was in fact present in the wrong wrapper. `rows` names the shape it was actually given.
  const cellsOf = (s: Stage) => rows<{name?: string; share?: number}>(s?.cells, 'cells', 'SameStuffChanged');
  const stages = rows<Stage>(STAGES_IN, 'stages', 'SameStuffChanged').filter(
    (s) => s && String(s.label ?? '').trim() && cellsOf(s).some((c) => Number(c?.share) > 0));
  if (stages.length < 2) {
    throw new Error(
      'SameStuffChanged needs at least two stages, each with a `label` and at least one cell with a ' +
      'positive `share`. One stage is a partition, and `MadeOf` already draws that; the claim here is that ' +
      'the same material CHANGES.');
  }
  if (stages.length > MAX_STAGES) {
    throw new Error(
      `SameStuffChanged was given ${stages.length} stages and re-forms at most ${MAX_STAGES}; past that ` +
      'each re-forming is too brief to be seen happening, and being seen to happen is the whole picture.');
  }
  for (const s of stages) {
    if (cellsOf(s).length > MAX_CELLS) {
      throw new Error(
        `SameStuffChanged draws at most ${MAX_CELLS} cells in a stage; "${s.label}" has ` +
        `${cellsOf(s).length}. Past that the areas stop being comparable, which is what they are for.`);
    }
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FLAT = dna?.bg ?? BG_D0;
  const FG = readableOn(FLAT, dna?.fg ?? FG_D0, '#ffffff', '#0a0d14');
  const ACC = dna?.accent ?? ACC_D0;
  const DIM = dimOn(FLAT, FG, 4.5);
  const LINE = dna?.line ?? LINE_D0;
  const body = 'var(--f-body, system-ui, sans-serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';

  const zTop = CONTENT_TOP;
  const zBot = H - captionBand(W, H);
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019);
  const CELL_PX = Math.round(U * 0.021), STAGE_PX = Math.round(U * 0.023);
  const noteH = NOTE ? inkBlockH(NOTE_PX, wrapLines(String(NOTE), NOTE_PX, W * 0.84)) + U * 0.028 : 0;

  const kickIn = clamp01(seg(t, 0.02, 0.10));
  // the whole run: which stage we are in, and how far through its re-forming
  const runs = stages.length - 1;
  const prog = clamp01(seg(t, 0.14, 0.88)) * runs;
  const at = Math.min(runs - 1, Math.floor(prog));
  const k = easeInOutCubic(clamp01(prog - at));
  const A = stages[at], B = stages[Math.min(stages.length - 1, at + 1)];

  const bx0 = W * 0.07, bx1 = W * 0.93;
  const by0 = zTop + U * 0.075, by1 = zBot - noteH - U * 0.055;
  const BW = bx1 - bx0, BH = by1 - by0;

  // AREA IS CONSERVED. Each stage's cells are normalised to the same total, so the body is always the same
  // amount of material — the claim the register exists to make, enforced rather than trusted to the props.
  const laidOut = (s: Stage) => {
    const cells = cellsOf(s).filter((c) => Number(c?.share) > 0);
    const lost = Math.max(0, Math.min(0.95, Number(s.lost) || 0));
    const tot = cells.reduce((a, c) => a + Number(c.share), 0) || 1;
    let x = bx0;
    const out = cells.map((c) => {
      const w = BW * (1 - lost) * (Number(c.share) / tot);
      const r = {name: String(c.name ?? ''), x, w};
      x += w;
      return r;
    });
    return {cells: out, lostX: x, lostW: BW * lost, lostLabel: String(s.lostLabel ?? '')};
  };
  const LA = laidOut(A), LB = laidOut(B);
  const lerp = (a: number, b: number) => a + (b - a) * k;

  // A NAME IS DRAWN ONLY WHERE IT CAN BE READ — every box here changes width for the whole shot, so a
  // fixed floor is a floor for one string and nothing else. See `fitsBox`, which this register is the
  // reason for.
  const PAD_X = U * 0.028, PAD_Y = U * 0.036;
  const roomFor = (text: string, boxW: number) => fitsBox(text, CELL_PX, boxW, BH, PAD_X, PAD_Y);

  // the cells are matched by POSITION, so a cell that splits is seen splitting rather than cross-fading
  const n = Math.max(LA.cells.length, LB.cells.length);
  // THE WIDTHS ARE LERPED; THE POSITIONS ARE THEN LAID OUT FROM THEM. Lerping each cell's `x` and its `w`
  // independently is the obvious thing and it breaks the register's own claim: two lerped edges only meet
  // at the endpoints, so mid-transition the cells OVERLAP and the visible body is narrower than the body.
  // Seen on an 8-way split — the material appeared to shrink while it divided, which argues the opposite of
  // "nothing is added and nothing is lost". Packed end to end the drawn total is the SUM of the lerped
  // widths, and a sum of lerps is the lerp of the sums, so the body is exactly conserved at every frame
  // rather than at the two frames anyone would have checked.
  const widths = Array.from({length: n}).map((_, i) =>
    lerp(i < LA.cells.length ? LA.cells[i].w : 0, i < LB.cells.length ? LB.cells[i].w : 0));
  let run = bx0;
  const cells = widths.map((w, i) => {
    const a = LA.cells[Math.min(i, LA.cells.length - 1)];
    const b = LB.cells[Math.min(i, LB.cells.length - 1)];
    const wantA = i < LA.cells.length, wantB = i < LB.cells.length;
    const x = run;
    run += w;
    return {
      x,
      w,
      name: k < 0.5 ? a.name : b.name,
      fade: k < 0.5 ? (wantA ? 1 : k * 2) : (wantB ? 1 : (1 - k) * 2),
    };
  });

  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {KICK ? (
        <div style={{position: 'absolute', left: bx0, top: zTop, opacity: kickIn, color: DIM,
          letterSpacing: dna?.labelSpacing ?? '0.16em', font: `700 ${KICK_PX}px/1.2 ${mono}`}}>
          {dna?.uppercaseLabels === false ? KICK : String(KICK).toUpperCase()}
        </div>
      ) : null}

      {/* THE STAGE'S NAME, on the body itself — a process whose stage you must read off a legend is a
          legend with a picture beside it. */}
      <div style={{position: 'absolute', left: bx0, top: by0 - U * 0.042, opacity: kickIn,
        color: ACC, font: `800 ${STAGE_PX}px/1.2 ${body}`}}>{k < 0.5 ? A.label : B.label}</div>

      {/* THE MATERIAL. One body, full width, re-apportioned. Nothing is drawn between stages because
          nothing travels between them: it is the same stuff. */}
      {cells.map((c, i) => (
        <React.Fragment key={i}>
          <div style={{position: 'absolute', left: c.x, top: by0, width: Math.max(0, c.w), height: BH,
            background: mix(FG, FLAT, i % 2 ? 0.74 : 0.62), opacity: c.fade,
            borderRight: `1px solid ${LINE}`}} />
          {roomFor(c.name, c.w) ? (
            <div style={{position: 'absolute', left: c.x + U * 0.014, top: by0 + U * 0.018,
              width: Math.max(0, c.w - U * 0.028), opacity: c.fade, color: FLAT, textWrap: 'balance',
              font: `700 ${CELL_PX}px/${leading(c.name, 1.3)} ${body}`}}>{c.name}</div>
          ) : null}
        </React.Fragment>
      ))}

      {/* WHAT LEAVES, drawn as the part that goes — hatched, still on the frame, never silently gone */}
      {(() => {
        // IT STARTS WHERE THE MATERIAL ENDS. Lerping the loss block's x independently of the cells' widths
        // left a gap between them mid-transition, which draws the loss as a separate object arriving from
        // off-frame — the opposite of the claim, which is that this part was IN the body and is leaving it.
        const lw = lerp(LA.lostW, LB.lostW);
        if (lw <= 1) return null;
        const lx = cells.reduce((m, c) => Math.max(m, c.x + c.w), bx0);
        // ...and it is labelled by whichever stage HAS the loss: reading `k` picked the stage that does not,
        // so the block drew with no name on it for the whole first half of the move.
        const lab = LB.lostLabel || LA.lostLabel;
        return (
          <>
            {/* WHAT LEAVES MUST NOT SHOUT LOUDER THAN WHAT STAYS. At 78% accent the hatching was the most
                energetic thing in the frame — 70% of the body rendered as bright diagonal stripes, so the
                eye read the write-off as the subject and the material that survived as its margin. The
                stripes now sit BELOW the material's own weight, over a ghost of that material's fill, so
                the region reads as what it is: this same stuff, struck through. */}
            <div style={{position: 'absolute', left: lx, top: by0, width: lw, height: BH,
              border: `1px dashed ${mix(ACC, FLAT, 0.45)}`, background: mix(FG, FLAT, 0.90)}}>
              <div style={{position: 'absolute', inset: 0,
                background: `repeating-linear-gradient(45deg, ${mix(ACC, FLAT, 0.62)} 0 ${Math.round(U * 0.005)}px, transparent ${Math.round(U * 0.005)}px ${Math.round(U * 0.020)}px)`}} />
            </div>
            {roomFor(lab, lw) ? (
              // the hatching runs UNDER the name, so the name needs its own ground or the strokes read
              // through the glyphs — the same reason a caption never draws straight onto a texture here
              <div style={{position: 'absolute', left: lx + U * 0.014, top: by0 + U * 0.018,
                maxWidth: Math.max(0, lw - U * 0.028), color: ACC, textWrap: 'balance',
                background: FLAT, padding: `${Math.round(U * 0.004)}px ${Math.round(U * 0.008)}px`,
                font: `700 ${CELL_PX}px/${leading(lab, 1.3)} ${body}`}}>{lab}</div>
            ) : null}
          </>
        );
      })()}

      {NOTE ? (
        <div style={{position: 'absolute', left: bx0, width: W * 0.84, top: zBot - noteH,
          opacity: clamp01(seg(t, 0.76, 0.88)), color: DIM,
          font: `400 ${NOTE_PX}px/${leading(String(NOTE), 1.4)} ${body}`,
          borderTop: `1px solid ${LINE}`, paddingTop: Math.round(U * 0.012)}}>{NOTE}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default SameStuffChanged;
