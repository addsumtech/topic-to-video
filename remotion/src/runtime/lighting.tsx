// LIGHTING — the product light of the craft bar, for built (SVG/DOM) shots (spec 2026-11-06 D3).
//
// WHY. Apple-style product films light the subject with a soft KEY, a FILL, and a RIM light behind it that traces
// its silhouette and lifts it off a dark ground (references/craft-bar.md). Our built subjects were flat fills with a
// stroke; measured on the ANC film, even its Blender plates carried almost no highlight (0.04-0.13). These return
// the DATA of the three lights — gradient stops and geometry — so a shot draws them in its own SVG (a
// <linearGradient> for the rim, a <radialGradient> for the key, an <ellipse> for the contact shadow) and every value
// is a pure function of the box, never of the frame: light does not tremble.
export type Box = {x: number; y: number; w: number; h: number};
export type Stop = {offset: number; opacity: number};
export type Side = 'left' | 'right' | 'top' | 'bottom';

const assertBox = (b: Box) => {
  if (!b || ![b.x, b.y, b.w, b.h].every(Number.isFinite) || b.w <= 0 || b.h <= 0) {
    throw new Error(`lighting: box must be {x, y, w, h} with a positive size, got ${JSON.stringify(b)}`);
  }
};

// The gradient's direction points INTO the subject from the lit edge (SVG gradientTransform rotate, degrees).
const SIDE_ANGLE: Record<Side, number> = {left: 0, top: 90, right: 180, bottom: 270};

// A rim: bright in a thin band at the edge, gone a fifth of the way in. strength 0..1.
export const rimGradient = (box: Box, side: Side, strength = 1): {angle: number; stops: Stop[]} => {
  assertBox(box);
  const s = Math.max(0, Math.min(1, strength));
  return {angle: SIDE_ANGLE[side], stops: [
    {offset: 0, opacity: 0.9 * s}, {offset: 0.04, opacity: 0.55 * s}, {offset: 0.12, opacity: 0.18 * s},
    {offset: 0.22, opacity: 0}, {offset: 1, opacity: 0},
  ]};
};

// A soft key: a radial pool centred where the key falls on the subject (fractions of the box), fading to nothing.
export const keyFalloff = (box: Box, key: [number, number]): {cx: number; cy: number; r: number; stops: Stop[]} => {
  assertBox(box);
  return {cx: key[0], cy: key[1], r: 0.9, stops: [{offset: 0, opacity: 0.5}, {offset: 0.45, opacity: 0.16},
    {offset: 1, opacity: 0}]};
};

// The contact shadow: a flat soft ellipse where the subject meets the ground (`groundY` in the same units as box).
export const contactShadow = (box: Box, groundY: number): {cx: number; cy: number; rx: number; ry: number; opacity: number} => {
  assertBox(box);
  return {cx: box.x + box.w / 2, cy: groundY, rx: box.w * 0.45, ry: Math.max(2, box.w * 0.06), opacity: 0.32};
};
