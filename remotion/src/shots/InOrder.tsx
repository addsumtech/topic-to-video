// SHOT · InOrder — N labelled steps, in order, with the frame ON one of them.
//
// WHY THIS EXISTS. Asked structurally rather than by reading prose — which register PROPS actually accept an
// ordered list of steps — the library had TWO, and neither does this: VoiceSignal's `phases` are audio
// segments and PhaseEncodeStep's `steps` is a count. So a film that wants to say "this happens in five
// steps, and here they are" had no register to say it in. That is not a density gap, it is an absence.
//
// HOW IT GETS ITS PIXELS. From the claim, like MadeOf and unlike the nine mood registers that clear the
// density floor with a field. The steps TILE the content zone edge to edge — the sequence IS the frame — and
// the band the film is currently on EXPANDS while the others compress. So the same accordion carries three
// things at once: the density (bands, not marks), the motion (the expansion travels across the frame as the
// narration advances), and the argument (you can see how many steps there are, which one we are on, and that
// they are ordered).
//
// THE HIDE-THE-CAPTION TEST: cover the subtitle and the frame still says "five steps, in this order, we are
// on the third, two are done". Nothing here is filler — a band that named no step could not be drawn.
//
// ...WHICH MEANS NO STEP MAY BE LEFT OUT EITHER. The steps used to be cut with `.slice(0, 6)`, so a seven-step
// process was drawn as a six-step one — "you can see how many steps there are" became a wrong count, with
// the last step, where the walk ends, silently gone. More than six now throws; so does a step with no `label`
// (the band would draw a number over nothing, which is the filler this register says it does not have).
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, dnaPalette, separated, surfaceOn, readableOn, dimOn, TONE_MIN_STEP} from '../runtime/dna';
import {useGlide} from '../runtime/glide';

export const DURATION = 180; // 6s

const BG_D0 = '#07090f', FG_D0 = '#eef2f8', DIM_D0 = '#6c7788';
const TONE_D0 = '#4f8cff', DONE_D0 = '#2b3550';

type Step = {label?: string; note?: string};

export const MAX_INORDER_STEPS = 6;

const DEFAULT_STEPS: Step[] = [
  {label: 'first', note: 'what starts it'},
  {label: 'second', note: 'what follows'},
  {label: 'third', note: 'the turn'},
  {label: 'last', note: 'what it leaves'},
];

export const InOrder: React.FC<{
  kicker?: string;      // what this frame is about
  whole?: string;       // the process being taken in order
  steps?: Step[];       // the steps — ORDER is the claim, so it is never sorted
  at?: number;          // which step the frame rests on (0-based); omitted = it walks the whole sequence
  doneLabel?: string;   // the mark on a completed step
}> = ({kicker = '', whole = '', steps: STEPS = DEFAULT_STEPS, at, doneLabel = ''} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const mono = dna?.fontMono ?? 'ui-monospace, monospace';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const disp = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';

  const t = useT();
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const base = Math.min(W, H);
  const zoneTop = CONTENT_TOP;
  const zoneBottom = H - captionBand(W, H);
  const zoneH = Math.max(1, zoneBottom - zoneTop);
  const portrait = H > W;

  if (!Array.isArray(STEPS) || STEPS.length < 1 || STEPS.length > MAX_INORDER_STEPS) {
    throw new Error(
      `InOrder needs 1-${MAX_INORDER_STEPS} \`steps\` (got ${Array.isArray(STEPS) ? STEPS.length : typeof STEPS}). The ` +
      'bands ARE the count, so a dropped step would state the wrong number of steps; past six a compressed band ' +
      'is too narrow to name. Group the steps into at most six stages, or split the process across two beats.');
  }
  STEPS.forEach((st, i) => {
    if (!String(st?.label ?? '').trim()) {
      throw new Error(`InOrder: step ${i + 1} has no \`label\` — a band must name the step it stands for.`);
    }
  });
  const steps = STEPS;
  const n = steps.length;

  // WHERE THE FRAME IS. With no `at` the focus WALKS the sequence — which is what makes this a shot rather
  // than a diagram, and where the frame-wide motion comes from. An explicit `at` pins it for a beat that
  // narrates one step.
  const walk = easeInOutCubic(clamp01(seg(t, 0.10, 0.92))) * (n - 1);
  const focus = at === undefined ? walk : Math.max(0, Math.min(n - 1, at));

  // The focused band takes FOCUS_SHARE of the axis and the rest split what is left, so the bands always
  // tile the zone exactly — the density is the partition, never an addition to it.
  const FOCUS_SHARE = n <= 2 ? 0.62 : n <= 4 ? 0.46 : 0.38;
  const weight = (i: number) => {
    const d = Math.abs(i - focus);
    return d >= 1 ? 1 : 1 + (FOCUS_SHARE * n - 1) * (1 - d);   // a smooth peak at the focus
  };
  const ws = steps.map((_, i) => weight(i));
  const tot = ws.reduce((a, b) => a + b, 0) || 1;

  const pal = (dna ? dnaPalette(dna, Math.max(3, n)) : null) ?? [TONE_D0];
  const liveFill = dna ? surfaceOn(BG, pal[0], TONE_MIN_STEP * 1.5) : TONE_D0;
  const doneFill = dna ? separated(BG, readableOn(BG, '#ffffff', '#05070c'), TONE_MIN_STEP * 1.15) : DONE_D0;
  const hair = Math.max(2, Math.round(base * 0.004));
  const enter = easeOutCubic(clamp01(seg(t, 0.04, 0.30)));
  // a band's left/top/width/height move while it first tiles in (`enter`) AND, with no `at` pinned, for as
  // long as the focus keeps walking the sequence (0.10-0.92 of the clip) — both of which Skia rounds the same
  // way it rounds a translate, so the band carries the unlock for whichever of the two can still be running
  const bandMoving = enter !== 1 || (at === undefined && t < 0.92);

  let acc = 0;
  const bands = steps.map((s, i) => {
    const f = ws[i] / tot;
    const start = acc; acc += f;
    return {s, i, start, f};
  });

  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {bands.map(({s, i, start, f}) => {
        const live = Math.abs(i - focus) < 0.5;
        const done = i < focus - 0.5;
        const fill = live ? liveFill : done ? doneFill : BG;
        const ink = readableOn(fill === BG ? BG : fill, '#ffffff', '#05070c');
        const sub = dimOn(fill === BG ? BG : fill, ink);
        const along = portrait ? zoneH : W;
        const px = start * along * enter;
        const sz = f * along * enter;
        const cross = portrait ? W : zoneH;
        const room = Math.min(sz, cross);
        const numPx = Math.max(14, Math.min(Math.round(base * 0.05), Math.round(room * 0.34)));
        const labelPx = Math.max(13, Math.min(Math.round(base * 0.036), Math.round(sz * 0.16), Math.round(cross * 0.10)));
        const tight = sz < base * 0.12;
        const bx = portrait ? 0 : px, by = portrait ? zoneTop + px : zoneTop;
        const bw = portrait ? W : sz, bh = portrait ? sz : zoneH;
        const inset = Math.round(base * 0.022);
        return (
          <React.Fragment key={i}>
          <div style={{position: 'absolute', left: bx, top: by, width: bw, height: bh,
            background: fill,
            // a PENDING step is an outline, not a fill: it has not happened yet, and the frame should say so
            boxShadow: `inset 0 0 0 ${hair}px ${BG}` + (fill === BG ? `, inset 0 0 0 ${hair * 2}px ${DIM}44` : ''),
            boxSizing: 'border-box'}} />
          {/* THE TYPE IS NOT LAID OUT IN THE BAND. The band's rectangle stays in layout — snapped, axis-aligned,
              so its fill cannot bleed past zoneBottom into the caption band (a skew on it measured spread 0.110
              there; a uniform band must read < 0.02 — tests/test_inorder.py). Its type stands in a clip of the
              same rectangle placed by TRANSLATE, set at the band's foot by a translate of its own: laid out
              inside the band it rode the band's left/top/height, which the browser rounds to whole pixels
              before anything is drawn, and it stepped whatever unlocked it (9:16, where the bands move down
              the frame: 7 steps). Only the glyphs carry the skew (runtime/glide.ts). */}
          <div style={{position: 'absolute', left: 0, top: 0, width: bw, height: bh, overflow: 'hidden',
            transform: `translate(${bx}px, ${by}px)`}}>
            <div style={{position: 'absolute', left: 0, top: 0, width: bw - 2 * inset,
              transform: glide(`translate(${inset}px, ${bh - inset}px) translateY(-100%)`, bandMoving)}}>
              <div style={{color: live ? ink : sub, font: `800 ${numPx}px/1 ${mono}`,
                fontVariantNumeric: 'lining-nums tabular-nums', opacity: 0.9}}>
                {done && doneLabel ? doneLabel : String(i + 1).padStart(2, '0')}
              </div>
              {!tight ? (
                <div style={{color: ink, font: `700 ${labelPx}px/1.15 ${body}`,
                  marginTop: Math.round(base * 0.006)}}>{s.label}</div>
              ) : null}
              {s.note && live && !tight ? (
                <div style={{color: sub, font: `400 ${Math.round(labelPx * 0.66)}px/1.35 ${body}`,
                  marginTop: Math.round(base * 0.005)}}>{s.note}</div>
              ) : null}
            </div>
          </div>
          </React.Fragment>
        );
      })}

      {kicker ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.045), top: Math.round(zoneTop * 0.42),
          opacity: enter, letterSpacing: '0.16em', color: DIM,
          font: `700 ${Math.round(base * 0.024)}px/1.2 ${mono}`}}>{kicker}</div>
      ) : null}
      {whole ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.045),
          top: Math.round(zoneTop * 0.42) + Math.round(base * 0.036), opacity: enter, color: FG,
          font: `800 ${Math.round(base * 0.046)}px/1.05 ${disp}`, letterSpacing: '-0.02em'}}>{whole}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default InOrder;
