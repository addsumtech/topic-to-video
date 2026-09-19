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

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {focusAt, focusFilter} from '../runtime/focus';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, textWidthPx} from '../runtime/layout';

export const DURATION = 135; // 4.5s
const ACCENT0 = '#2E7BFF', SPOT = '#ffe6ad';

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
        const f = focusAt(isF ? 0 : iso, U, {blurFrac: 9 / 1080, minOpacity: 0.18, minScale: 0.96,
                                             minBrightness: 1, desat: 0.30});
        const op = f.opacity * clamp01(appear);
        const sc = isF ? lerp(1, 1.12, easeOutBack(clamp01(iso))) : f.scale;
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: cw, height: ch, opacity: op,
            transform: `scale(${sc})`, transformOrigin: 'center', filter: isF ? undefined : focusFilter(f),
            background: isF ? 'linear-gradient(160deg,#223049,#18212f)' : '#161d29',
            border: `${isF ? 2 : 1}px solid ${isF ? ACCENT : '#26303f'}`, borderRadius: 16,
            boxShadow: isF ? `0 0 0 6px ${ACCENT}22, 0 30px 70px rgba(0,0,0,.5)` : 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <div style={{textWrap: 'balance', font: `${isF ? 700 : 500} ${isF ? 40 : 32}px/1.15 var(--f-body, Inter,system-ui,sans-serif)`,
              color: isF ? '#eaf1ff' : '#7f8da3', textAlign: 'center', padding: '0 24px'}}>{label}</div>
          </div>
        );
      })}
      {/* vignette darkening the edges as isolation lands */}
      <AbsoluteFill style={{background: 'radial-gradient(70% 70% at 50% 46%, transparent 55%, #060910 100%)', opacity: 0.85 * iso, pointerEvents: 'none'}} />
      {/* focal label */}
      {iso > 0.4 && (
        <div style={{position: 'absolute', left: labelLeft, width: labelW, top: labelTop, textAlign: 'center',
          opacity: easeOutCubic(seg(t, 0.5, 0.7)), font: '700 44px/1 var(--f-body, Inter,system-ui,sans-serif)', color: '#eaf1ff'}}>{focalLabel}</div>
      )}
    </AbsoluteFill>
  );
};
export default FocalIsolation;
