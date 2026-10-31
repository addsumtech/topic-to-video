// THE STYLE ENGINE'S PER-PIXEL FILTERS — what the DOM pass (runtime/style.tsx) cannot do by rewriting properties.
//
//   wobble   the line is redrawn by a hand: feTurbulence displaces the drawing a few px. With `boil_hz` the noise is
//            redrawn on the animator's clock — a few drawings cycled (`boilPhase`, runtime/draw.ts), never fresh noise
//            per frame, which reads as television snow.
//   outer    one ring around a drawing's silhouette (line.outline: 'outer'): its alpha dilated, flooded with ink, laid
//            UNDER the drawing — the drawing's parts are not each ringed.
//   surface  the medium the drawing is made on (paper, canvas, brush, grain): a texture multiplied into the drawing.
//   posterize a soft glow cut into hard levels (shade: 'cel').
//
// Built by the pass into the layer's own <defs> (which React renders empty and never reconciles), one filter per
// distinct recipe, and applied ONLY to elements that hold no type: a filter on a group displaces everything in it.
import {boilPhase} from './draw';

const NS = 'http://www.w3.org/2000/svg';

/** Which drawing of the line is on screen: 1 when the line does not boil (no rate, or reduced motion). A pure
 *  function of the beat's clock, so a seam's copy of the beat — the same beat at the same frame — boils in phase. */
export const wobbleSeed = (frame: number, durF: number, fps: number, hz: number, reduced: boolean): number => {
  if (reduced || !(hz > 0)) return 1;
  return 1 + boilPhase(frame / Math.max(1, durF), durF, fps, hz, 3);
};

/** One filter: what it does, and where — `region` [x, y, w, h] in the target's own user space (a filter defined in
 *  another <svg> resolves percentages against THAT svg's viewport, and the layer's defs are 0×0: every filtered shape
 *  vanished, measured on StyleProbe), and `k` the target's user units per screen px, so a wobble, a ring and a tooth
 *  are sized on screen whatever the drawing's own scale. */
export type Recipe = {wobble: number; seed: number; outer: number; ink: string; surface: string | null;
  strength: number; posterize: boolean; region?: [number, number, number, number]; k?: number; dark?: boolean};

/** The tooth as an opaque grey layer from noise (R, ~0.5 ± 0.15): GRAIN, never a veil. Light ground: 1 where the
 *  noise is above its middle and darker only where it dips below, MULTIPLIED in. Dark ground: 0 where the noise is
 *  below its middle and a light speck only where it rises above, SCREENED in. The first build mapped the whole noise
 *  range onto the layer, so a dark film's tooth was a constant grey lift: every dark ground went mid-grey and a
 *  subtitle lost its contrast (looked at; style_qa's TONE_MAX now fails it). */
export const toothMatrix = (amt: number, dark: boolean): string => {
  // screened onto near-black a speck ADDS its value, where multiplied onto paper it scales a light ground: the same k
  // gave the dark ground 8x the grain and a 10-level lift (StyleProbe, paper 0.8) — the dark side takes 0.3 of it
  const k = +(5 * amt).toFixed(4), kd = +(1.5 * amt).toFixed(4);
  return dark
    ? `${kd} 0 0 0 ${+(-0.6 * kd).toFixed(4)}  ${kd} 0 0 0 ${+(-0.6 * kd).toFixed(4)}  ${kd} 0 0 0 ${+(-0.6 * kd).toFixed(4)}  0 0 0 0 1`
    : `${k} 0 0 0 ${+(1 - 0.4 * k).toFixed(4)}  ${k} 0 0 0 ${+(1 - 0.4 * k).toFixed(4)}  ${k} 0 0 0 ${+(1 - 0.4 * k).toFixed(4)}  0 0 0 0 1`;
};

export const recipeKey = (r: Recipe): string =>
  [r.wobble.toFixed(2), r.seed, r.outer.toFixed(2), r.ink, r.surface ?? '-', r.strength.toFixed(2), r.posterize ? 'p' : '-',
    (r.region ?? []).map((v) => v.toFixed(1)).join(','), (r.k ?? 1).toFixed(3), r.dark ? 'd' : 'l'].join('|');

/** The noise each medium is made of: [baseFrequency x, y, octaves, contrast]. Frequencies are per px at a 1080 short
 *  side; the caller divides by the frame's scale. */
export const SURFACE_NOISE: Record<string, [number, number, number, number]> = {
  paper: [0.9, 0.9, 3, 0.16],
  canvas: [0.35, 0.06, 2, 0.2],
  brush: [0.02, 0.6, 2, 0.24],
  grain: [1.6, 1.6, 1, 0.14],
};

const el = (doc: Document, tag: string, attrs: Record<string, string | number>) => {
  const e = doc.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  return e;
};

/** Build one filter for `r` into `defs` with id `id`. Region: the drawing's own user space, generous enough that a
 *  displaced or dilated edge is not clipped — and in user space, so a horizontal line (zero-height bbox) is kept. */
export const buildFilter = (doc: Document, defs: Element, id: string, r: Recipe, scale: number): void => {
  const reg = r.region ?? [-1e4, -1e4, 2e4, 2e4];
  const k = r.k ?? 1;                       // user units per screen px
  const f = el(doc, 'filter', {id, filterUnits: 'userSpaceOnUse', x: reg[0], y: reg[1], width: reg[2], height: reg[3],
    'color-interpolation-filters': 'sRGB'});
  let src = 'SourceGraphic';
  if (r.posterize) {
    const ct = el(doc, 'feComponentTransfer', {in: src, result: 'post'});
    ct.appendChild(el(doc, 'feFuncA', {type: 'discrete', tableValues: '0 1 1'}));
    f.appendChild(ct);
    src = 'post';
  }
  if (r.wobble > 0) {
    f.appendChild(el(doc, 'feTurbulence', {type: 'fractalNoise', baseFrequency: +(0.02 / scale / k).toFixed(5),
      numOctaves: 2, seed: r.seed, result: 'wob'}));
    f.appendChild(el(doc, 'feDisplacementMap', {in: src, in2: 'wob', scale: +(r.wobble * 2 * scale * k).toFixed(3),
      xChannelSelector: 'R', yChannelSelector: 'G', result: 'moved'}));
    src = 'moved';
  }
  if (r.outer > 0) {
    f.appendChild(el(doc, 'feMorphology', {in: src, operator: 'dilate', radius: +(r.outer * scale * k).toFixed(3), result: 'grown'}));
    f.appendChild(el(doc, 'feFlood', {'flood-color': r.ink, result: 'inkc'}));
    f.appendChild(el(doc, 'feComposite', {in: 'inkc', in2: 'grown', operator: 'in', result: 'ring'}));
    const m = el(doc, 'feMerge', {result: 'ringed'});
    m.appendChild(el(doc, 'feMergeNode', {in: 'ring'}));
    m.appendChild(el(doc, 'feMergeNode', {in: src}));
    f.appendChild(m);
    src = 'ringed';
  }
  if (r.surface && SURFACE_NOISE[r.surface]) {
    const [fx, fy, oct, k] = SURFACE_NOISE[r.surface];
    f.appendChild(el(doc, 'feTurbulence', {type: 'fractalNoise', baseFrequency: `${+(fx / scale / k).toFixed(5)} ${+(fy / scale / k).toFixed(5)}`,
      numOctaves: oct, seed: 7, stitchTiles: 'stitch', result: 'tex'}));
    // an OPAQUE grey layer, 1 where the noise is high and 1 - 2·amt where it is low: multiplied in, the medium's tooth
    // darkens the drawing by up to ~amt around its mean. (The first build carried the noise in ALPHA over a constant
    // grey: ~1.4% of light, which no viewer sees — measured on StyleProbe at strength 1.)
    const amt = +(k * r.strength).toFixed(3);
    f.appendChild(el(doc, 'feColorMatrix', {in: 'tex', type: 'matrix', result: 'tooth', values: toothMatrix(amt, Boolean(r.dark))}));
    f.appendChild(el(doc, 'feBlend', {in: src, in2: 'tooth', mode: r.dark ? 'screen' : 'multiply', result: 'toothed'}));
    f.appendChild(el(doc, 'feComposite', {in: 'toothed', in2: src, operator: 'in', result: 'textured'}));
    src = 'textured';
  }
  defs.appendChild(f);
};
