// SHOT · MadeOf — the WHOLE is the frame, and it divides into what it is made of.
//
// WHY THIS EXISTS. Measured across the library, the three shapes an explainer film is actually built from
// have no dense register at all: process (12 registers, 0 over the density floor), mechanism (5, 0) and
// STRUCTURE — "what is this made of" — which has 3 registers in total and 0 over the floor. A skill for
// explaining things could not say the most ordinary explanatory sentence there is without an empty frame.
//
// The library's dense registers are dense the wrong way: of the 32 that clear the floor, nine are described
// by MOOD ("calm premium ambient", "warm storybook", "playful / friendly") and get their pixels from a field
// or a texture — they fill the frame precisely because they are not saying anything. Only five are both
// dense and argumentative. This is the sixth, and it takes the one route that is not decoration: the
// partition IS the claim, so every pixel it adds is the content.
//
// THE HIDE-THE-CAPTION TEST, which this is built to pass: cover the subtitle and the frame still says "this
// whole is made of these parts, in these proportions, and that one is the big one". Nothing here is filler —
// a region's AREA is its share, so an area that means nothing cannot be drawn.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, dnaPalette, separated, surfaceOn, readableOn, dimOn, pilL, TONE_MIN_STEP} from '../runtime/dna';

export const DURATION = 165; // 5.5s

const BG_D0 = '#07090f', FG_D0 = '#eef2f8', DIM_D0 = '#6c7788';
const TONES_D0 = ['#4f8cff', '#8b6cf0', '#3dd6a4', '#f0b23d', '#ef6a6a', '#57c4e5'];

type Part = {label?: string; share?: number; note?: string};

const DEFAULT_PARTS: Part[] = [
  {label: 'the biggest piece', share: 44},
  {label: 'the second', share: 26},
  {label: 'the third', share: 18},
  {label: 'the rest', share: 12},
];

/** Slice-and-dice: split the box for the remaining shares, alternating direction, largest first.
 *  Deterministic and total — every part gets a rectangle and the rectangles tile the box exactly, which is
 *  what makes the density a property of the CLAIM rather than something added on top. */
const partition = (parts: {share: number; i: number}[], box: {x: number; y: number; w: number; h: number},
                   horiz: boolean): {i: number; x: number; y: number; w: number; h: number}[] => {
  if (parts.length === 0) return [];
  if (parts.length === 1) return [{i: parts[0].i, ...box}];
  const total = parts.reduce((s, p) => s + p.share, 0);
  // take the head off along the LONG side, so no cell degenerates into a sliver
  const along = box.w >= box.h;
  const head = parts[0], rest = parts.slice(1);
  const f = total > 0 ? head.share / total : 1 / parts.length;
  if (along) {
    const w = box.w * f;
    return [{i: head.i, x: box.x, y: box.y, w, h: box.h},
            ...partition(rest, {x: box.x + w, y: box.y, w: box.w - w, h: box.h}, !horiz)];
  }
  const h = box.h * f;
  return [{i: head.i, x: box.x, y: box.y, w: box.w, h},
          ...partition(rest, {x: box.x, y: box.y + h, w: box.w, h: box.h - h}, !horiz)];
};

export const MadeOf: React.FC<{
  kicker?: string;     // what this frame is about
  whole?: string;      // the thing being taken apart
  parts?: Part[];      // its constituents — `share` is the AREA, so it must mean something
  note?: string;       // one line under the partition
  unit?: string;       // what a share is counted in ('%' by default); shown beside each figure
}> = ({kicker = '', whole = '', parts: PARTS = DEFAULT_PARTS, note = '', unit = '%'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const mono = dna?.fontMono ?? 'ui-monospace, monospace';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const disp = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';

  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const base = Math.min(W, H);
  const zoneTop = CONTENT_TOP;
  const zoneBottom = H - captionBand(W, H);

  const items = PARTS.slice(0, 7).filter((p) => (p.share ?? 0) > 0);
  const sorted = items.map((p, i) => ({...p, share: p.share ?? 0, i})).sort((a, b) => b.share - a.share);
  const total = sorted.reduce((s, p) => s + p.share, 0) || 1;

  // The partition fills the whole content zone, edge to edge. A composition that insets itself is the
  // "small" half of this library's emptiness — measured, four of its sparsest registers occupy between 9%
  // and 19% of the frame.
  const box = {x: 0, y: zoneTop, w: W, h: Math.max(1, zoneBottom - zoneTop)};
  const cells = partition(sorted.map((p) => ({share: p.share, i: p.i})), box, true);

  // Every region must be a SURFACE against the ground and distinguishable from its neighbours — otherwise
  // the partition is a claim nobody can see. The palette carries the film's own hues; `separated` and
  // `surfaceOn` guarantee the step the density instrument (and an eye) needs.
  const pal = (dna ? dnaPalette(dna, Math.max(3, sorted.length)) : null) ?? TONES_D0;
  const fills = sorted.map((p, k) => {
    const hue = pal[k % pal.length];
    if (!dna) return TONES_D0[k % TONES_D0.length];
    const c = surfaceOn(BG, hue, TONE_MIN_STEP * 1.5);
    // stagger the depth so neighbours never land on the same tone even when the palette repeats
    return k % 2 === 0 ? c : separated(c, readableOn(c, '#ffffff', '#05070c'), TONE_MIN_STEP * 0.9);
  });

  const wholeIn = easeOutCubic(clamp01(seg(t, 0.04, 0.24)));
  const cellAt = (k: number) => easeOutCubic(clamp01(seg(t, 0.22 + k * 0.09, 0.44 + k * 0.09)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.72, 0.9)));
  const hair = Math.max(2, Math.round(base * 0.004));

  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {cells.map((c, k) => {
        const p = sorted[k];
        const on = cellAt(k);
        const fill = fills[k];
        const ink = readableOn(fill, '#ffffff', '#05070c');
        const sub = dimOn(fill, ink);
        const pct = Math.round((p.share / total) * 100);
        // Type sized to the CELL: a label larger than the region it names is the frame-craft defect this
        // project keeps finding, and a cell's area is exactly what tells you how big its label may be.
        const room = Math.min(c.w, c.h);
        const labelPx = Math.max(14, Math.min(Math.round(base * 0.042), Math.round(c.w / Math.max(4, [...(p.label ?? '')].length) * 1.7), Math.round(c.h * 0.30)));
        const figPx = Math.max(16, Math.min(Math.round(base * 0.075), Math.round(room * 0.38)));
        const tight = room < base * 0.14;
        return (
          <div key={k} style={{position: 'absolute', left: c.x, top: c.y, width: c.w, height: c.h,
            background: fill, opacity: on,
            // the parts arrive by GROWING out of the whole, not by fading in from nowhere
            transform: `scale(${(0.94 + 0.06 * on).toFixed(4)})`, transformOrigin: '50% 50%',
            boxShadow: `inset 0 0 0 ${hair}px ${BG}`,
            display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
            padding: Math.round(base * 0.022), boxSizing: 'border-box', overflow: 'hidden'}}>
            {!tight ? (
              <div style={{color: ink, font: `800 ${figPx}px/1 ${disp}`, letterSpacing: '-0.02em',
                fontVariantNumeric: 'lining-nums tabular-nums'}}>{pct}{unit}</div>
            ) : null}
            <div style={{color: ink, font: `700 ${labelPx}px/1.15 ${body}`, marginTop: tight ? 0 : Math.round(base * 0.006)}}>
              {p.label ?? ''}
            </div>
            {p.note && !tight ? (
              <div style={{color: sub, font: `400 ${Math.round(labelPx * 0.62)}px/1.3 ${body}`,
                marginTop: Math.round(base * 0.004)}}>{p.note}</div>
            ) : null}
          </div>
        );
      })}

      {kicker ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.045), top: Math.round(zoneTop * 0.42),
          opacity: wholeIn, letterSpacing: '0.16em', color: DIM,
          font: `700 ${Math.round(base * 0.024)}px/1.2 ${mono}`}}>{kicker}</div>
      ) : null}
      {whole ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.045), top: Math.round(zoneTop * 0.42) + Math.round(base * 0.036),
          opacity: wholeIn, color: FG, font: `800 ${Math.round(base * 0.046)}px/1.05 ${disp}`,
          letterSpacing: '-0.02em'}}>{whole}</div>
      ) : null}
      {/* The whole-level note rides the TITLE band, opposite the claim — it was first placed under the
          partition at `zoneBottom + …`, which is INSIDE the band the burned caption owns. That is the exact
          collision this project keeps finding (and which, on another register, turned two legible whites
          into mush the moment the ground changed). Nothing this component draws may enter that band. */}
      {note ? (
        <div style={{position: 'absolute', right: Math.round(W * 0.045), top: Math.round(zoneTop * 0.42),
          maxWidth: W * 0.34, textAlign: 'right', opacity: noteIn, color: DIM,
          // `balance`: Chinese breaks between any two glyphs, so a note a unit too wide for the column
          // under the partition drops one character onto a line of its own. First seen on the first Chinese
          // render this register ever received — its five props were read as one until 2026-09-15.
          textWrap: 'balance',
          font: `400 ${Math.round(base * 0.022)}px/1.35 ${body}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default MadeOf;
