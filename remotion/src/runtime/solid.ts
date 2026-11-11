// SOLID — a drawn object as a manufactured, lit SOLID instead of a flat vector fill (SVG, pure functions).
//
// WHY. The craft study's surface measure (2026-11-11, references/craft-study.md P8) found the one difference the eye
// sees first between a product film and ours: in B&O, Dyson, Nothing and Apple films 54-92 % of frames hold a large
// region whose luminance the light has MODELLED (a continuous ramp of >= 25 luma inside it); in our films 10-29 %.
// Our objects were vector fills with a hairline: a shell one grey, a pipe one red, a panel one white. A product's
// surface reads as a material because of three things, all of which are geometry plus one light direction:
//   1. the FORM SHADE — light falls off across the body away from the key (a ramp, not a fill);
//   2. the CHAMFER — the edges facing the key catch a thin highlight, the edges away from it a thin shade
//      (OP-XY's keys, the MacBook lid's edge light: Rams' "thorough down to the last detail");
//   3. the REFLECTION — a glossy or metal surface mirrors the studio's strip lights as soft bands
//      (petapixel's gradient-light practice: a reflection that fades bright->dark reads as a rounded surface).
// These helpers return SVG nodes and defs for exactly those, from a FINISH (the same names as the Blender kit,
// blender/kit/materials.py) and ONE key direction shared by the whole film, so every object is lit by the same lamp.
// Every value is a pure function of its arguments — light never trembles.
import React from 'react';
import {mix} from './dna';

const h = React.createElement;

/** The manufactured finishes (blender/kit/materials.py has the same list for 3D plates). */
export const FINISHES = ['gloss_plastic', 'satin_plastic', 'soft_touch', 'silicone', 'anodized_alu', 'brushed_steel',
  'polished_metal', 'copper', 'enamel', 'pcb', 'ceramic', 'glass', 'fabric', 'wood', 'skin'] as const;
export type Finish = (typeof FINISHES)[number];

type FinishSpec = {
  /** how far the lit side lifts toward white and the far side sinks toward black (0..1) */
  lift: number; sink: number;
  /** reflection bands: strength 0..1 (0 = a diffuse finish shows none) and sharpness 0..1 */
  bands: number; sharp: number;
  /** chamfer: the edge highlight and edge shade strength (0..1) */
  edge: number;
  /** a metal's reflection alternates light and dark (it mirrors the room); a dielectric only adds light */
  metal: boolean;
};

export const FINISH_SPEC: Record<Finish, FinishSpec> = {
  gloss_plastic: {lift: 0.35, sink: 0.16, bands: 0.75, sharp: 0.8, edge: 0.7, metal: false},
  satin_plastic: {lift: 0.22, sink: 0.22, bands: 0.25, sharp: 0.3, edge: 0.5, metal: false},
  soft_touch: {lift: 0.12, sink: 0.28, bands: 0.0, sharp: 0.0, edge: 0.35, metal: false},
  silicone: {lift: 0.2, sink: 0.22, bands: 0.18, sharp: 0.25, edge: 0.3, metal: false},
  anodized_alu: {lift: 0.3, sink: 0.3, bands: 0.45, sharp: 0.35, edge: 0.85, metal: true},
  brushed_steel: {lift: 0.35, sink: 0.35, bands: 0.6, sharp: 0.45, edge: 0.8, metal: true},
  polished_metal: {lift: 0.5, sink: 0.5, bands: 0.95, sharp: 0.9, edge: 0.9, metal: true},
  copper: {lift: 0.38, sink: 0.4, bands: 0.6, sharp: 0.55, edge: 0.7, metal: true},
  enamel: {lift: 0.25, sink: 0.18, bands: 0.5, sharp: 0.65, edge: 0.65, metal: false},
  pcb: {lift: 0.18, sink: 0.25, bands: 0.35, sharp: 0.6, edge: 0.5, metal: false},
  ceramic: {lift: 0.16, sink: 0.25, bands: 0.25, sharp: 0.5, edge: 0.55, metal: false},
  glass: {lift: 0.45, sink: 0.1, bands: 0.85, sharp: 0.95, edge: 0.8, metal: false},
  fabric: {lift: 0.14, sink: 0.3, bands: 0.0, sharp: 0.0, edge: 0.15, metal: false},
  wood: {lift: 0.18, sink: 0.26, bands: 0.08, sharp: 0.2, edge: 0.4, metal: false},
  skin: {lift: 0.16, sink: 0.24, bands: 0.08, sharp: 0.2, edge: 0.25, metal: false},
};

/** The film's ONE key light: the direction the light COMES FROM in screen space, degrees (0 = from the right,
 *  -90 = from above, -135 = from the upper left — the studio default), and how high it stands (elevation, degrees). */
export type Key = {from: number; elev: number};
export const STUDIO_KEY: Key = {from: -125, elev: 48};

export type Box = {x: number; y: number; w: number; h: number};

const assertFinish = (f: string): Finish => {
  if (!(FINISHES as readonly string[]).includes(f)) {
    throw new Error(`solid: unknown finish "${f}" — one of ${FINISHES.join(', ')}`);
  }
  return f as Finish;
};
const assertBox = (b: Box) => {
  if (!b || ![b.x, b.y, b.w, b.h].every(Number.isFinite) || b.w <= 0 || b.h <= 0) {
    throw new Error(`solid: box must be {x, y, w, h} with a positive size, got ${JSON.stringify(b)}`);
  }
};

/** The unit vector the light travels ALONG (from the lamp into the scene), screen space. */
export const lightDir = (key: Key = STUDIO_KEY) => {
  const a = (key.from * Math.PI) / 180;
  return {x: -Math.cos(a), y: -Math.sin(a)};
};

/** The form shade's gradient across `box`: lit end toward the key, the body colour through the middle, the far end
 *  sunk. Returns the gradient's end points (userSpace) and stops — a pure function of the box, finish and key. */
export const formShade = (box: Box, colour: string, finish: Finish | string, key: Key = STUDIO_KEY) => {
  assertBox(box);
  const f = FINISH_SPEC[assertFinish(finish)];
  const d = lightDir(key);
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
  // half the box's extent along the light direction
  const half = (Math.abs(d.x) * box.w + Math.abs(d.y) * box.h) / 2;
  const x1 = cx - d.x * half, y1 = cy - d.y * half, x2 = cx + d.x * half, y2 = cy + d.y * half;
  const stops: {offset: number; color: string}[] = [
    {offset: 0, color: mix(colour, '#ffffff', f.lift)},
    {offset: 0.42, color: colour},
    {offset: 1, color: mix(colour, '#000000', f.sink)},
  ];
  if (f.metal) {
    // a metal mirrors the room: a dark band (the unlit studio) between two bright ones
    stops.splice(1, 0, {offset: 0.2, color: mix(colour, '#ffffff', f.lift * 0.6)});
    stops.splice(3, 0, {offset: 0.62, color: mix(colour, '#000000', f.sink * 0.85)},
      {offset: 0.8, color: mix(colour, '#ffffff', f.lift * 0.35)});
  }
  return {x1, y1, x2, y2, stops};
};

/** The strip-light reflection bands over `box`: soft white bands running ACROSS the light direction, placed by the
 *  finish (none for a diffuse finish). Pure geometry: rects in the box's own rotated frame. */
export const reflectionBands = (box: Box, finish: Finish | string, key: Key = STUDIO_KEY) => {
  assertBox(box);
  const f = FINISH_SPEC[assertFinish(finish)];
  if (f.bands <= 0) return [] as {x: number; y: number; w: number; h: number; opacity: number; blur: number; angle: number}[];
  const d = lightDir(key);
  const angle = (Math.atan2(d.y, d.x) * 180) / Math.PI;           // the bands run perpendicular to this
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
  const along = (Math.abs(d.x) * box.w + Math.abs(d.y) * box.h);
  const across = (Math.abs(d.y) * box.w + Math.abs(d.x) * box.h) * 1.4;
  const soft = 1 - f.sharp;
  // two strips: the key's own (near the lit edge, broad) and a thin kicker on the far side (the back strip)
  return [
    {at: -0.24, width: 0.13, op: 0.55 * f.bands},
    {at: 0.36, width: 0.05, op: 0.32 * f.bands},
  ].map(({at, width, op}) => ({
    x: cx + at * along - (width * along) / 2, y: cy - across / 2, w: width * along, h: across,
    opacity: op, blur: Math.max(0.5, (0.02 + 0.06 * soft) * along), angle,
  }));
};

/** A filter that chamfers a shape: its alpha is the height field, a distant light at the film's key lifts the edges
 *  facing it and shades the edges away, and the flat interior keeps its colour exactly (the diffuse map is divided
 *  by its own flat value). `width` is the chamfer's width in px. */
export const chamferFilter = (id: string, width: number, finish: Finish | string, key: Key = STUDIO_KEY) => {
  const f = FINISH_SPEC[assertFinish(finish)];
  if (!(width > 0)) throw new Error(`solid.chamferFilter: width must be > 0, got ${width}`);
  const flat = Math.sin((key.elev * Math.PI) / 180);
  // feDistantLight azimuth is measured in the SVG plane from +x toward +y: the direction TO the light
  const az = key.from;
  // out = colour * (edge * shade / flat + (1 - edge)): the flat interior (shade == flat) keeps its colour exactly
  return h('filter', {id, x: '-10%', y: '-10%', width: '120%', height: '120%', colorInterpolationFilters: 'sRGB'},
    h('feGaussianBlur', {in: 'SourceAlpha', stdDeviation: width * 0.6, result: 'bump'}),
    h('feDiffuseLighting', {in: 'bump', surfaceScale: Math.max(1, width * 0.9), diffuseConstant: 1, lightingColor: '#ffffff',
      result: 'shade'}, h('feDistantLight', {azimuth: az, elevation: key.elev})),
    h('feComposite', {in: 'SourceGraphic', in2: 'shade', operator: 'arithmetic', k1: f.edge / flat, k2: 1 - f.edge, k3: 0, k4: 0,
      result: 'lit'}),
    h('feComposite', {in: 'lit', in2: 'SourceAlpha', operator: 'in'}));
};

/** A drawn SOLID: `shape` is the outline (any SVG shape element's props + its tag), filled with the finish's form
 *  shade, chamfered, with the reflection bands clipped inside it. `box` is the shape's bounding box (userSpace).
 *  `edgeWidth` is the chamfer width in px (≈ 0.6-1 % of the frame's short side reads as a machined edge). */
export const solid = (id: string, tag: 'path' | 'rect' | 'ellipse' | 'circle', shape: Record<string, unknown>, box: Box,
  colour: string, finish: Finish | string, edgeWidth: number, key: Key = STUDIO_KEY, extra: Record<string, unknown> = {}) => {
  const fs = formShade(box, colour, finish, key);
  const bands = reflectionBands(box, finish, key);
  const gid = `${id}-form`, fid = `${id}-ch`, cid = `${id}-clip`, bid = `${id}-bl`;
  return h('g', {key: id, ...extra},
    h('defs', null,
      h('linearGradient', {id: gid, gradientUnits: 'userSpaceOnUse', x1: fs.x1, y1: fs.y1, x2: fs.x2, y2: fs.y2},
        ...fs.stops.map((s, i) => h('stop', {key: i, offset: s.offset, stopColor: s.color}))),
      chamferFilter(fid, edgeWidth, finish, key),
      h('clipPath', {id: cid}, h(tag, {...shape})),
      bands.length ? h('filter', {id: bid, x: '-50%', y: '-50%', width: '200%', height: '200%'},
        h('feGaussianBlur', {stdDeviation: bands[0].blur})) : null),
    h(tag, {...shape, fill: `url(#${gid})`, filter: `url(#${fid})`}),
    bands.length ? h('g', {clipPath: `url(#${cid})`},
      ...bands.map((b, i) => h('rect', {key: i, x: b.x, y: b.y, width: b.w, height: b.h, fill: '#ffffff', opacity: b.opacity,
        filter: `url(#${bid})`, transform: `rotate(${b.angle} ${box.x + box.w / 2} ${box.y + box.h / 2})`}))) : null);
};

/** A TUBE along path `d` (a pipe, a wire, a cable) of width `w`: the cylinder's shade from the key — a dark outline,
 *  the body, the shade side, the lit side and, on a reflective finish, a thin specular line — as stacked strokes
 *  offset toward / away from the key. Returns the stroke nodes, back to front. */
export const tube = (key0: string, d: string, w: number, colour: string, finish: Finish | string, key: Key = STUDIO_KEY,
  extra: Record<string, unknown> = {}) => {
  const f = FINISH_SPEC[assertFinish(finish)];
  if (!(w > 0)) throw new Error(`solid.tube: width must be > 0, got ${w}`);
  const L = lightDir(key);
  const off = (k: number) => `translate(${(-L.x * w * k).toFixed(2)} ${(-L.y * w * k).toFixed(2)})`;
  const common = {d, fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round'};
  const nodes = [
    h('path', {key: `${key0}-o`, ...common, stroke: mix(colour, '#000000', 0.55), strokeWidth: w * 1.18}),
    h('path', {key: `${key0}-b`, ...common, stroke: mix(colour, '#000000', f.sink * 0.9), strokeWidth: w}),
    h('path', {key: `${key0}-m`, ...common, stroke: colour, strokeWidth: w * 0.72, transform: off(0.1)}),
    h('path', {key: `${key0}-l`, ...common, stroke: mix(colour, '#ffffff', f.lift), strokeWidth: w * 0.34, transform: off(0.2),
      opacity: 0.9}),
  ];
  if (f.bands > 0.2) {
    nodes.push(h('path', {key: `${key0}-s`, ...common, stroke: '#ffffff', strokeWidth: Math.max(0.6, w * 0.1), transform: off(0.26),
      opacity: 0.35 + 0.5 * f.bands * f.sharp}));
  }
  return h('g', {key: key0, ...extra}, ...nodes);
};

/** A soft contact shadow under an object resting on (or hovering just over) a ground at `groundY`. */
export const groundShadow = (key0: string, cx: number, groundY: number, width: number, opacity = 0.28) =>
  h('g', {key: key0},
    h('defs', null, h('radialGradient', {id: `${key0}-g`},
      h('stop', {offset: 0, stopColor: '#000000', stopOpacity: opacity}),
      h('stop', {offset: 1, stopColor: '#000000', stopOpacity: 0}))),
    h('ellipse', {cx, cy: groundY, rx: width * 0.55, ry: Math.max(2, width * 0.07), fill: `url(#${key0}-g)`}));
