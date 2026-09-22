// SHOT · Focal Isolation — Vercel/Linear language: out of a whole field, ONE thing is isolated. The
// periphery blurs + a vignette darkens the edges + a spotlight lands on the focal item, which sharpens,
// rings, and rises. Mid-dark SLATE (distinct from the near-black Command palette + the light shots).
// Real DoF-style blur on the non-focal planes — the flat HTML tier cannot pull focus like this.
//
// THE ISOLATED ITEM IS THE ONE THE FILM NAMES. `const focal = 4` spotlit the FIFTH cell of every grid — the
// demo's 'YOUR MACHINE', and on any other film whatever happened to be fifth: a film listing nine suspects
// isolated the fifth as the culprit, and a film giving four items put the spotlight, the ring and its
// `focalLabel` on an EMPTY cell, a caption pointing at nothing. The whole register is one emphasis, so the
// emphasis cannot be left to position and cannot be left out either: a film that passes `items` must pass
// `focal` (the index of the item to isolate), and an index outside the list throws. The grid is also laid
// out for the count now — three rows were reserved for any count, so four items sat in the top two thirds of
// the zone and more than nine ran off the grid into the caption band.

//
// THE CAPTION IS THE FILM'S, AND THE VIGNETTE IS SCALED TO THE GROUND IT DARKENS. The caption under the
// focal cell was a literal near-white, and all eight DNA presets are near-black, so on a film whose DNA came
// from a warm-white deck the one sentence naming what was isolated drew white on paper
// (`scripts/ink_contrast_qa.py`: 43.7% of this register's marks under 3:1, largest connected hole 0.90% of
// the frame). The vignette was the other half of it: tuned for a void, it is barely a deepening on this
// register's own slate and a stain on paper — sampled off the light probe render, the frame's corners came
// out RGB 42,44,49 and 60,62,66 where the page is 246,243,238, so the page was simply black at the edges.
// (The 42,44,49 is what this gradient composites to over that paper exactly; the lighter pair is the two
// corners the spotlight reaches.)
//
// THE CARDS ARE NOT INK AND ARE UNTOUCHED. This register's field is a mid-dark slate world (see above) and
// each card carries its own surface, so its own label answers to that card and not to the page. The RECEDED
// labels do wash into their cards on paper — `measure_ground_reach.py`'s INK_REFUSED reads 1.07:1 there —
// but that is the recede, not the ground: computed through this runtime's own helpers at the lens's 0.18
// opacity floor, the same label measures 1.25:1 on this register's OWN slate, 1.22:1 on the ink probe's
// paper and 1.21:1 on gallery white. A periphery you can read is not a periphery. The one label that must
// read is the focal one, at 13.08:1 on its own card. The curve itself is the shared house lens in
// runtime/focus.ts, not a colour decision made here.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {focusAt, focusFilter} from '../runtime/focus';
import {useDNA} from '../runtime/dna';
import {onLight} from '../runtime/light';
import {CONTENT_TOP, contentBottom, textWidthPx} from '../runtime/layout';

export const DURATION = 135; // 4.5s
const ACCENT0 = '#2E7BFF', SPOT = '#ffe6ad';
const CAPTION0 = '#eaf1ff';          // the caption under the focal cell
const VIGNETTE0 = '#060910';         // what the edges darken TOWARD
// HOW FAR THE EDGES GO, PER GROUND. 0.85 is what this register has always used and is what its own slate
// wants: composited over #0d131d it is a deepening of about a third of a channel, which is a vignette.
// Composited over paper it is the blackout sampled above. On a light ground the same gradient is painted at
// a quarter, which computes (runtime/dna `mix`) to a deepest corner of #bab9b7 — 186,185,183 against the
// page's 246,243,238, instead of 42,44,49. The periphery still falls away and the page is still a page. The
// geometry, the colour and the timing do not move, and on a dark ground or with no DNA nothing here does.
const VIGNETTE_PEAK = 0.85, VIGNETTE_PEAK_LIGHT = 0.25;
// A CONTACT SHADOW TUNED FOR A VOID FILLS EVERY GAP ON PAPER. `rgba(0,0,0,.5)` blurred 70px is what lifts
// the focal card off near-black; on a light ground it is a grey smear under the one thing the beat is
// pointing at. Lightened there and left alone everywhere else (the same move as KSpaceAnatomy's plates).
const FOCAL_SHADOW = 'rgba(0,0,0,.5)', FOCAL_SHADOW_LIGHT = 'rgba(0,0,0,.18)';

const DEFAULT_ITEMS = ['Cloud drive', 'Shared server', 'Email', 'Someone’s laptop', 'YOUR MACHINE', 'A vendor', 'Chat export', 'Backup', 'The internet'];
// the demo's own focal item, used only while the demo's own items are showing — never for a film's list
const DEMO_FOCAL = 4;
// A 3x3 field is what the zone holds at every aspect; one item alone is not isolated FROM anything.
export const MIN_FOCAL_ITEMS = 2, MAX_FOCAL_ITEMS = 9;

export const FocalIsolation: React.FC<{focalLabel?: string; items?: string[]; focal?: number}> = ({
  focalLabel = 'Your files · on your machine',
  items = DEFAULT_ITEMS, focal: FOCAL,
} = {}) => {
  if (!Array.isArray(items) || items.length < MIN_FOCAL_ITEMS || items.length > MAX_FOCAL_ITEMS) {
    throw new Error(`FocalIsolation needs ${MIN_FOCAL_ITEMS}-${MAX_FOCAL_ITEMS} \`items\` (got ${Array.isArray(items) ? items.length : typeof items}). ` +
      'It isolates one item out of a field: one item is not a field, and past nine the field no longer fits a 3x3 grid — ' +
      'narrow the field to the items the viewer must see.');
  }
  items.forEach((it, i) => {
    if (!String(it ?? '').trim()) throw new Error(`FocalIsolation: item ${i + 1} is empty.`);
  });
  const focal = FOCAL ?? (items === DEFAULT_ITEMS ? DEMO_FOCAL : undefined);
  if (focal == null) {
    throw new Error('FocalIsolation: pass `focal` — the index of the item to isolate. The whole shot is ONE emphasis, ' +
      'and which item it falls on is the film\'s claim to make, not a position\'s.');
  }
  if (!(Number.isInteger(focal) && focal >= 0 && focal < items.length)) {
    throw new Error(`FocalIsolation: \`focal\` is ${JSON.stringify(focal)}, but it must be an index into \`items\` (0-${items.length - 1}).`);
  }
  const t = useT();
  const dna = useDNA(); const ACCENT = dna?.accent ?? ACCENT0;
  const light = onLight(dna);
  const captionInk = dna?.fg ?? CAPTION0;
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const iso = easeOutCubic(seg(t, 0.32, 0.66)); // isolation progress
  // The grid is fitted to the CONTENT ZONE. Three 220px rows and two 90px gutters are 840px tall and the
  // grid was centred in the frame, so the bottom row — 'The internet' among them — sat in the strip the
  // renderer burns the caption over. The row height yields; the gutters and the column rhythm do not.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  // the grid also yields to the WIDTH: three fixed 380px cells + gutters are 1320px, wider than a portrait
  // frame is; two item labels were riding 51px and 13px off its edges
  // and it is laid out for the COUNT: as many rows as the items fill, a short last row centred under the rest
  const n = items.length;
  const cols = Math.min(3, n), rows = Math.ceil(n / cols), gx = 90, gy = 90;
  const cw = Math.min(380, Math.floor((W * 0.94 - (cols - 1) * gx) / cols));
  // (+0.12 of a row: the focal cell rises to 1.12x, and on the top or bottom row that growth is outside the grid)
  const ch = Math.min(220, ((zBot - zTop) - (rows - 1) * gy) / (rows + 0.12));
  const gridW = cols * cw + (cols - 1) * gx, gridH = rows * ch + (rows - 1) * gy;
  const ox = (W - gridW) / 2, oy = zTop + ((zBot - zTop) - gridH) / 2;
  const cellX = (i: number) => {
    const row = Math.floor(i / cols), inRow = Math.min(cols, n - row * cols);
    return ox + ((cols - inRow) * (cw + gx)) / 2 + (i % cols) * (cw + gx);
  };
  const cellY = (i: number) => oy + Math.floor(i / cols) * (ch + gy);
  const fx = cellX(focal) + cw / 2, fy = cellY(focal) + ch / 2;
  // the focal label sits in the gutter under its cell — or over it when the cell is on the bottom row of a
  // multi-row grid, where "under" is the caption band
  const labelTop = rows > 1 && Math.floor(focal / cols) === rows - 1 ? fy - ch / 2 - 40 - 44 : fy + ch / 2 + 40;
  // and it is centred on ITS cell, not on the frame: centred on the frame it only ever sat under the demo's
  // middle-column item, and under a side column it pointed at the gutter between two others. Held inside the
  // frame's 3% margins when the cell is at an edge.
  const labelW = Math.min(W * 0.94, textWidthPx(focalLabel, 44));
  const labelLeft = Math.max(W * 0.03, Math.min(W * 0.97 - labelW, fx - labelW / 2));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 120% at 50% 45%, #1b2434, #0d131d)'}}>
      {/* spotlight that lands on the focal item */}
      <div style={{position: 'absolute', left: fx - 520, top: fy - 520, width: 1040, height: 1040,
        background: `radial-gradient(closest-side, ${SPOT}${Math.round(28 * iso).toString(16).padStart(2, '0')}, transparent)`,
        filter: 'blur(20px)', opacity: iso}} />
      {items.map((label, i) => {
        const isF = i === focal;
        const x = cellX(i), y = cellY(i);
        const appear = easeOutCubic(seg(t, i * 0.03, i * 0.03 + 0.2));
        // THE HOUSE LENS, NOT A THIRD COPY OF IT. `runtime/focus.ts` exists because SurfaceCarousel had
        // hand-rolled a recede curve and "the next register to want it would have written a third" — and
        // this was that third: a literal 9px blur, a literal 0.18 opacity floor and a literal 0.96 scale,
        // none of them related to each other or to any other shot's. The numbers below are the ones this
        // register already used, handed to the shared curve, so a film that puts this beat next to a
        // RackFocus beat has ONE lens in it rather than two that happen to both be blurry.
        const f = focusAt(isF ? 0 : iso, U, {blurFrac: 0.0022, minOpacity: 0.34, minScale: 0.96,
                                             minBrightness: 1, desat: 0.30});
        const op = f.opacity * clamp01(appear);
        const sc = isF ? lerp(1, 1.12, easeOutBack(clamp01(iso))) : f.scale;
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: cw, height: ch, opacity: op,
            transform: `scale(${sc})`, transformOrigin: 'center', filter: isF ? undefined : focusFilter(f),
            background: isF ? 'linear-gradient(160deg,#223049,#18212f)' : '#161d29',
            border: `${isF ? 2 : 1}px solid ${isF ? ACCENT : '#26303f'}`, borderRadius: 16,
            boxShadow: isF ? `0 0 0 6px ${ACCENT}22, 0 30px 70px ${light ? FOCAL_SHADOW_LIGHT : FOCAL_SHADOW}` : 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <div style={{textWrap: 'balance', font: `${isF ? 700 : 500} ${isF ? 40 : 32}px/1.15 var(--f-body, Inter,system-ui,sans-serif)`,
              color: isF ? '#eaf1ff' : '#7f8da3', textAlign: 'center', padding: '0 24px'}}>{label}</div>
          </div>
        );
      })}
      {/* vignette darkening the edges as isolation lands — at the depth this ground can carry (see above) */}
      <AbsoluteFill style={{background: `radial-gradient(70% 70% at 50% 46%, transparent 55%, ${VIGNETTE0} 100%)`,
        opacity: (light ? VIGNETTE_PEAK_LIGHT : VIGNETTE_PEAK) * iso, pointerEvents: 'none'}} />
      {/* focal label — it sits in the gutter ON the film's ground, so it is the film's ink */}
      {iso > 0.4 && (
        <div style={{position: 'absolute', left: labelLeft, width: labelW, top: labelTop, textAlign: 'center',
          opacity: easeOutCubic(seg(t, 0.5, 0.7)), font: '700 44px/1 var(--f-body, Inter,system-ui,sans-serif)', color: captionInk}}>{focalLabel}</div>
      )}
    </AbsoluteFill>
  );
};
export default FocalIsolation;
