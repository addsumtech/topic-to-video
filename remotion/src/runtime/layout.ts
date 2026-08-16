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
export const CAPTION_BAND = 150;        // bottom px reserved for the Film's burned narration caption
export const CONTENT_TOP = TITLE_BAND;  // top of the usable content zone
export const contentBottom = (H: number) => H - CAPTION_BAND;   // bottom of the usable content zone

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
  const bottom0 = H - CAPTION_BAND - bottomReserve;
  const zoneH = Math.max(1, bottom0 - top0);
  const S = Math.min(zoneH * hFrac, W * wFrac);
  const top = top0 + (zoneH - S) / 2;          // centered in the content zone → a balanced gap above + below
  const left = (W - S) / 2;
  return {S, left, top};
}
