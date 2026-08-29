// layout.ts — the FRAME-CRAFT FLOOR, shared so every bespoke shot gets the safe zones for free instead of
// hand-guessing pixel positions (the source of a whole class of defects this tier kept hitting: an image sized
// to the FULL frame rode up UNDER the title; two edge-anchored labels COLLIDED when a panel shrank; a global
// downscale added BLACK BORDERS by shrinking each shot's own background). The rules:
//
//   • FULL-BLEED. A shot's root AbsoluteFill background MUST reach all four frame edges (opaque, no inset,
//     no wrapping scale). The Film composites shots edge-to-edge; never scale the whole shot to gain a margin
//     — that exposes the atmosphere behind as a border. Edge-safety is a per-ELEMENT contract, not a global squish.
//   • TITLE band at the top: the shot title sits at TITLE_Y; keep real content out of [0, CONTENT_TOP).
//   • CAPTION band at the bottom: the Film burns the narration caption in the bottom CAPTION_BAND px. Keep the
//     shot's OWN text/labels out of [H - CAPTION_BAND, H] (a small credit line at the very bottom is the only
//     allowed exception). Otherwise the shot text and the caption overlap.
//   • So the usable CONTENT ZONE is [CONTENT_TOP, H - CAPTION_BAND]. Center a hero image/panel THERE, not in the
//     whole frame, or it collides with the title. Use fitContentSquare() and it's automatic.
//
// These are the numbers the Film (src/Film.tsx) reserves; keep them in sync with its CAPTION_BAND + title.

import type React from 'react';

export const TITLE_Y = 92;              // title top (px) — the shared header position for a shot's title <div>
export const TITLE_BAND = 176;          // content must start BELOW this (title + a comfortable gap ~40px)
// The caption BAND is derived from the caption's own type size, not guessed. It has to hold two wrapped lines
// of `CAPTION_SIZE_FRAC` type plus the block's bottom margin plus a real GAP, or the caption reads as part of
// the content above it — which is exactly what a viewer reported: "subtitle is too close to the content".
// Shrinking the type closed that gap by starting the block lower, but it also dropped the caption to 3.4% of
// frame height, under the 5.2% floor that keeps a 1080p film readable in a phone-sized window. Both are fixed
// by paying for the gap out of the BAND instead of out of the type.
export const CAPTION_SIZE_FRAC = 0.052;   // caption type as a fraction of min(W,H) — 56px at 1080
export const CAPTION_LINES = 2;           // the band must hold a two-line caption without touching content
export const CAPTION_LEAD = 1.26;
export const CAPTION_LEAD_CJK = 1.7;      // CJK needs more leading; the band is sized on the LATIN
                                          // lead and the caption fits itself to the band (Film.tsx)
export const CAPTION_MARGIN_FRAC = 0.037; // the block's own bottom margin
export const CAPTION_GAP_FRAC = 0.042;    // clear air between the content zone and the caption block
// (The old flat `CAPTION_BAND = 150` export is gone. It had no importers left and sat in the one file every
// register author reads before deciding where their content ends — the literal that produced the whole
// class of "cleared a 150px band, sat inside the grown one" defects, still on offer.)
export const CONTENT_TOP = TITLE_BAND;  // top of the usable content zone
// ASPECT-AWARE caption band: a NARROW frame (portrait/square/4:5) wraps the caption to more lines, so it needs a
// TALLER reserved band. Shots + the Film should reserve `captionBand(W,H)`, not the fixed CAPTION_BAND, so content
// clears the caption at every aspect. `contentBottom(W,H)` is the bottom of the usable content zone.
// The line count the band reserves for. A NARROW frame wraps the same sentence to more lines, so it
// reserves one extra. Exported because `maxCameraPush` below has to subtract the SAME block: it used
// CAPTION_LINES flat while the band reserved one more, so at 9:16 it believed there was 2.6x the headroom
// there is (12.1% against a true 4.7%) and would have let an authored camera push content onto the
// subtitle. Two places deriving the same quantity from the same fractions and disagreeing on the count is
// the shape this file exists to prevent.
export const CAPTION_NARROW_W = 1400;   // below this the caption wraps to one more line
export const captionLines = (W: number) => CAPTION_LINES + (W < CAPTION_NARROW_W ? 1 : 0);
export const captionBlockH = (W: number, H: number) =>
  Math.min(W, H) * (CAPTION_SIZE_FRAC * CAPTION_LEAD * captionLines(W) + CAPTION_MARGIN_FRAC);

export const captionBand = (W: number, H: number) =>
  Math.round(captionBlockH(W, H) + Math.min(W, H) * CAPTION_GAP_FRAC);
export const contentBottom = (W: number, H: number) => H - captionBand(W, H);

// The largest camera push that CANNOT drive a shot's lowest content into the caption band.
//
// A scene camera scales the shot about the centre of the content zone, so the zone's bottom edge travels
// down by half the zone's height times the push. The band holds the caption block plus a gap of clear air;
// as long as that travel stays inside the gap, the burned subtitle never has shot content sitting on it.
// Derived rather than chosen, so a change to the caption's type size moves this with it instead of leaving
// a stale constant that used to be safe.
// `driftExtra` is the largest EXTRA scale the film-wide ambient drift adds on top of this. The two camera
// layers multiply, and the per-beat cap could not see the other one: with the drift at full amplitude a
// per-beat push of 8% already drives the lowest content 51px down into a 46px gap. Measured, not guessed.
// The drift scales about the FRAME centre, so its travel is H/2 x driftExtra; the beat scales about the
// content zone, so its travel is zoneH/2 x amount. The beat gets whatever the drift has not already spent.
// `driftTranslate` is the film-wide drift's downward y-amplitude in px (Film.DRIFT_MAX_TRANSLATE_Y scaled
// by the drift amount). It spends the same headroom the scale does and was simply not counted.
export const maxCameraPush = (W: number, H: number, driftExtra = 0, driftTranslate = 0) => {
  const band = captionBand(W, H);
  const gap = Math.max(0, band - captionBlockH(W, H))
            - (H / 2) * Math.max(0, driftExtra) - Math.max(0, driftTranslate);
  const zoneH = Math.max(1, H - CONTENT_TOP - band);
  return Math.max(0, (gap / (zoneH / 2)) * 0.75);   // 3/4 of the headroom — the last quarter is not worth spending
};

// The shared title style — use for a shot's top title so every shot's header reads identically (position,
// size, weight, tracking). Spread it onto the title <div>; override `color`/`opacity` as needed.
export const titleStyle: React.CSSProperties = {
  position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center',
  color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
};

// fitContentSquare — the correct box for a hero IMAGE/panel: a square CENTERED in the content zone (below the
// title, above the caption band), never the whole frame. Pass `bottomReserve` when the shot draws its OWN labels
// UNDER the image (ticks, a caption line) so the square shrinks to leave room and those labels stay out of the
// caption band. hFrac/wFrac cap the size (leave hFrac<1 for breathing room around a big image).
export function fitContentSquare(
  W: number, H: number,
  {hFrac = 0.86, wFrac = 0.5, bottomReserve = 0}: {hFrac?: number; wFrac?: number; bottomReserve?: number} = {},
): {S: number; left: number; top: number} {
  const top0 = CONTENT_TOP;
  const bottom0 = H - captionBand(W, H) - bottomReserve;
  const zoneH = Math.max(1, bottom0 - top0);
  // On a PORTRAIT frame the caller's landscape wFrac (often ~0.44) would leave a tiny square in a wide-open
  // column — boost it so a hero image fills the portrait width, while landscape keeps the caller's value.
  const wf = W < H ? Math.max(wFrac, 0.9) : wFrac;
  const S = Math.min(zoneH * hFrac, W * wf);
  const top = top0 + (zoneH - S) / 2;          // centered in the content zone → a balanced gap above + below
  const left = (W - S) / 2;
  return {S, left, top};
}

/** Where a label goes beside a point, WITHOUT leaving the box it belongs to.
 *
 * The recurring bug this exists for: a label is placed by `mark.x > 0.5 ? right : left` and given a fixed
 * width. That reads the point's HALF, not the room actually left, so any point near an edge gets a label
 * pushed straight out of its container — two city names crossed a map plate's border in a delivered film,
 * and a flap board's rows ran off the frame the same way. No raster check can catch it: text crossing a
 * DRAWN border and a full-bleed field reaching the frame edge are the same pixels.
 *
 * So the fix is at the source. Pass the point, the box it must stay inside, and the label's width; get back
 * a left edge that is clamped into the box and the side the text should align to.
 *
 * @param x     the point the label annotates, in px
 * @param x0,x1 the box the label must stay inside, in px
 * @param labelW the label's width in px
 * @param gap   clearance between the point and the label
 */
export function placeLabel(x: number, x0: number, x1: number, labelW: number, gap: number):
  {left: number; align: 'left' | 'right'} {
  const roomRight = (x1 - x) - gap;
  // side by ROOM, not by which half of the box the point sits in
  const align: 'left' | 'right' = (roomRight >= labelW || (x - x0) < labelW) ? 'left' : 'right';
  const raw = align === 'left' ? x + gap : x - gap - labelW;
  return {left: Math.max(x0, Math.min(raw, x1 - labelW)), align};
}
