// THE FILM'S DITHER — what keeps a dark gradient a gradient after it has been encoded.
//
// BANDING WAS MEASURED, NOT SUSPECTED. CAMBI (libvmaf's banding index; past ~5 a viewer sees it) over this tier's own
// films: median 12-15 and peaks of 22 on the dark radial grounds most DNAs paint — concentric rings on the opening
// frame — where the html tier, encoded from the same kind of frames, measured 0. Chrome paints an 8-bit gradient one
// code value a ring, the frame reached x264 as a JPEG (quality 80 then — remotion.config.ts), and x264 kept the steps.
//
// A DITHER BREAKS THE STEPS before they are encoded: every pixel moved by a small, zero-mean amount, so a ring's edge
// becomes a fine mixture the encoder cannot keep as an edge. Measured on 60 frames of that dark opening: a ±1 static
// luma dither before x264 took CAMBI from 8.7 to 0.01. Remotion's own ffmpeg has no noise filter, so the dither is
// painted here, last, over the whole frame: two fixed tiles of 0..AMP code values, one ADDED (plus-lighter) and one
// SUBTRACTED (difference: |b − n| is b − n wherever the ground is brighter than AMP, which is every ground that bands)
// — their difference is the textbook triangular dither, mean zero, so no ground is lifted or darkened.
//
// STATIC on purpose: the same tile on every frame (references/craft-research.md §4 — per-frame grain was WORSE after
// x264), fixed seeds, so a render stays byte-identical to the last and every segment of a film matches the next. It is
// a delivery step, not a look: Film draws it only when render_remotion asks (`dither`), never in a register's own still.
import React from 'react';
import {continueRender, delayRender} from 'remotion';

export const DITHER_TILE = 256;
/** The tiles' largest code value: their difference spans ±AMP. */
export const DITHER_AMP = 2;
const SEEDS = [20260802, 19970114];

const mulberry32 = (seed: number) => () => {
  let t = (seed = (seed + 0x6d2b79f5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

/** One tile as a PNG data URL: grey pixels of 0..AMP, from a fixed seed. */
export const ditherTile = (seed: number): string | null => {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas');
  c.width = c.height = DITHER_TILE;
  const ctx = c.getContext('2d');
  if (!ctx) return null;
  const img = ctx.createImageData(DITHER_TILE, DITHER_TILE);
  const rnd = mulberry32(seed);
  for (let i = 0; i < DITHER_TILE * DITHER_TILE; i++) {
    const v = Math.min(DITHER_AMP, Math.floor(rnd() * (DITHER_AMP + 1)));
    img.data[4 * i] = img.data[4 * i + 1] = img.data[4 * i + 2] = v;
    img.data[4 * i + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return c.toDataURL('image/png');
};

let TILES: (string | null)[] | null = null;

/** The whole-frame dither. The tiles are decoded before the first frame is taken (a frame shot before an image has
 *  decoded would go out undithered — and differ from the next render of it). */
export const FilmDither: React.FC = () => {
  const [tiles] = React.useState(() => (TILES ??= SEEDS.map(ditherTile)));
  const [handle] = React.useState(() => delayRender('film dither tiles'));
  React.useEffect(() => {
    Promise.all(tiles.map((src) => {
      if (!src) return Promise.resolve();
      const im = new Image();
      im.src = src;
      return im.decode().catch(() => undefined);
    })).then(() => continueRender(handle));
  }, [tiles, handle]);
  if (!tiles[0] || !tiles[1]) return null;
  const layer = (src: string, mode: 'plus-lighter' | 'difference') => (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', backgroundImage: `url("${src}")`,
      backgroundSize: `${DITHER_TILE}px ${DITHER_TILE}px`, imageRendering: 'pixelated', mixBlendMode: mode}} />
  );
  return (
    <>
      {layer(tiles[0], 'plus-lighter')}
      {layer(tiles[1], 'difference')}
    </>
  );
};
