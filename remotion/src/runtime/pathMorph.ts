// ONE FIGURE BECOMING THE NEXT — shape morphs for "a diagram that grows": a cell into two, a point into a line into a
// triangle, a circle into the ellipse of an orbit. Pure functions of two outlines and a progress value.
//
// WHY NOT `interpolatePath` STRAIGHT. @remotion/paths' interpolatePath (4.0.486, installed) interpolates SEGMENT BY
// SEGMENT after padding the shorter command list: it is exact when both paths were written with the same commands,
// and that is the case it is for. Between two different shapes it pairs whatever segments happen to share an index,
// so a circle (four arcs from 3 o'clock) into a triangle (three lines from the top) twists through itself, and a path
// with one subpath into one with two is refused ("mismatch"). Measured (tests/test_math_morph.py), the signed area of
// the HALF-WAY shape in a 400px box — endpoints in brackets: circle→triangle 4,932 against [125,686 · 57,288];
// circle→square 32,384 against [125,686 · 118,336]; triangle→hexagon 15,365 against [57,288 · 103,923] — a shape
// folding through itself. Resampled and aligned here: 90,848 · 122,925 · 81,637. So both outlines
// are flattened, RESAMPLED to the same number of points by arc length, and ALIGNED (same winding, the start index
// that moves the points least) before anything is lerped; subpaths are paired by where they sit, and a subpath with no
// partner is shared — one cell drawn twice over itself becomes two cells, which is what a split looks like.
import {alignTo, centroidOf, flatten, parsePath, polyLength, ptsToD, resample, type Poly, type Pt} from './pathCore';

export type MorphPlan = {
  /** one entry per drawn piece: its start and end points, index-aligned */
  pieces: {a: Pt[]; b: Pt[]; closed: boolean}[];
};

const polysOf = (d: string): Poly[] => {
  const ps = flatten(parsePath(d), 32).filter((p) => p.pts.length > 1 && polyLength(p) > 1e-6);
  if (!ps.length) throw new Error(`pathMorph: the outline ${JSON.stringify(String(d).slice(0, 40))} draws nothing`);
  return ps;
};

/** Points per piece: dense enough that a chord's sag is far under a pixel at any size this library draws. */
const countFor = (la: number, lb: number) => Math.max(64, Math.min(720, Math.ceil(Math.max(la, lb) / 5)));

/**
 * Plan the morph from outline `dA` to outline `dB` (frame px, absolute or relative commands, any mix of lines, curves
 * and arcs). Deterministic: the same two outlines always plan the same way.
 */
export const planMorph = (dA: string, dB: string): MorphPlan => {
  const A = polysOf(dA), B = polysOf(dB);
  const ca = A.map((p) => centroidOf(p.pts)), cb = B.map((p) => centroidOf(p.pts));
  // pair each piece of the side with MORE pieces to the nearest piece of the other: a split shares the one cell
  // between its daughters, a merge sends each part to the whole it joins
  const pairs: [number, number][] = [];
  const near = (c: Pt, cs: Pt[]) => cs.reduce((best, q, i) =>
    (Math.hypot(q[0] - c[0], q[1] - c[1]) < Math.hypot(cs[best][0] - c[0], cs[best][1] - c[1]) ? i : best), 0);
  if (A.length === B.length) {
    // same count: in reading order (top-to-bottom bands, then left-to-right) — stable and what the eye expects
    const ord = (cs: Pt[]) => cs.map((c, i) => [c, i] as [Pt, number])
      .sort((p, q) => (Math.abs(p[0][1] - q[0][1]) > 1 ? p[0][1] - q[0][1] : p[0][0] - q[0][0])).map((x) => x[1]);
    const oa = ord(ca), ob = ord(cb);
    oa.forEach((ia, k) => pairs.push([ia, ob[k]]));
  } else if (A.length < B.length) {
    cb.forEach((c, ib) => pairs.push([near(c, ca), ib]));
    // a piece of A nobody chose still has to go somewhere: into the nearest piece of B
    A.forEach((_, ia) => { if (!pairs.some((p) => p[0] === ia)) pairs.push([ia, near(ca[ia], cb)]); });
  } else {
    ca.forEach((c, ia) => pairs.push([ia, near(c, cb)]));
    B.forEach((_, ib) => { if (!pairs.some((p) => p[1] === ib)) pairs.push([near(cb[ib], ca), ib]); });
  }
  const pieces = pairs.map(([ia, ib]) => {
    const pa = A[ia], pb = B[ib];
    const closed = pa.closed && pb.closed;
    const n = countFor(polyLength(pa), polyLength(pb));
    // an open side is morphed as an open line; a closed outline it meets is opened at its own start
    const open = (p: Poly): Poly => (p.closed && !closed ? {pts: [...p.pts, p.pts[0]], closed: false} : p);
    const a = resample(open(pa), n);
    const b = alignTo(a, resample(open(pb), n), closed);
    return {a, b, closed};
  });
  return {pieces};
};

/** Each piece's outline at progress p (0 = A, 1 = B) — for drawing a split's pieces apart (see GrowingFigure). */
export const morphPieces = (plan: MorphPlan, p: number): string[] => {
  const u = p > 0 ? (p < 1 ? p : 1) : 0;
  return plan.pieces.map((pc) => ptsToD(pc.a.map((q, i) =>
    [q[0] + (pc.b[i][0] - q[0]) * u, q[1] + (pc.b[i][1] - q[1]) * u] as Pt), pc.closed));
};
/** The outline at progress p (0 = A, 1 = B), as one `d`. */
export const morphAt = (plan: MorphPlan, p: number): string => morphPieces(plan, p).join('');

// ── NAMED SHAPES ─────────────────────────────────────────────────────────────────────────────────────────────────
// The vocabulary a film can name a state by, each drawn into a box. Geometry only — what a shape MEANS is the film's
// label beside it. `count` repeats a shape side by side (a split: one cell, then two), so a division is two states.
export type ShapeName = 'dot' | 'circle' | 'ellipse' | 'square' | 'triangle' | 'diamond' | 'pentagon' | 'hexagon' |
  'star' | 'line' | 'ring';
export const SHAPE_NAMES: ShapeName[] = ['dot', 'circle', 'ellipse', 'square', 'triangle', 'diamond', 'pentagon',
  'hexagon', 'star', 'line', 'ring'];

const circleD = (cx: number, cy: number, rx: number, ry: number, ccw = false) =>
  `M${cx + rx} ${cy}A${rx} ${ry} 0 0 ${ccw ? 0 : 1} ${cx} ${cy + (ccw ? -ry : ry)}A${rx} ${ry} 0 0 ${ccw ? 0 : 1} ${cx - rx} ${cy}` +
  `A${rx} ${ry} 0 0 ${ccw ? 0 : 1} ${cx} ${cy + (ccw ? ry : -ry)}A${rx} ${ry} 0 0 ${ccw ? 0 : 1} ${cx + rx} ${cy}Z`;
const polyD = (cx: number, cy: number, r: number, n: number, rot = -Math.PI / 2, inner = 0) => {
  const pts: Pt[] = [];
  const k = inner > 0 ? n * 2 : n;
  for (let i = 0; i < k; i++) {
    const th = rot + (2 * Math.PI * i) / k;
    const rr = inner > 0 && i % 2 ? r * inner : r;
    pts.push([cx + rr * Math.cos(th), cy + rr * Math.sin(th)]);
  }
  return ptsToD(pts, true);
};

/** A named shape, `count` times side by side, filling the box (x, y, w, h) frame px. */
export const shapeD = (name: ShapeName, box: {x: number; y: number; w: number; h: number}, count = 1): string => {
  if (!SHAPE_NAMES.includes(name)) throw new Error(`pathMorph: shape is one of ${SHAPE_NAMES.join(', ')}, got "${name}"`);
  if (!(Number.isInteger(count) && count >= 1 && count <= 6)) throw new Error(`pathMorph: count is 1..6, got ${count}`);
  const gap = count > 1 ? Math.min(box.w, box.h) * 0.08 : 0;
  const cellW = (box.w - gap * (count - 1)) / count;
  const out: string[] = [];
  for (let i = 0; i < count; i++) {
    const x = box.x + i * (cellW + gap);
    const cx = x + cellW / 2, cy = box.y + box.h / 2;
    const r = Math.min(cellW, box.h) / 2;
    if (name === 'dot') out.push(circleD(cx, cy, r * 0.07, r * 0.07));
    else if (name === 'circle') out.push(circleD(cx, cy, r, r));
    else if (name === 'ellipse') out.push(circleD(cx, cy, Math.min(cellW / 2, r * 1.7), r * 0.58));
    else if (name === 'square') out.push(polyD(cx, cy, r * Math.SQRT2 * 0.86, 4, -Math.PI / 4));
    else if (name === 'triangle') out.push(polyD(cx, cy + r * 0.12, r * 1.05, 3));
    else if (name === 'diamond') out.push(polyD(cx, cy, r, 4));
    else if (name === 'pentagon') out.push(polyD(cx, cy, r, 5));
    else if (name === 'hexagon') out.push(polyD(cx, cy, r, 6, 0));
    else if (name === 'star') out.push(polyD(cx, cy, r, 5, -Math.PI / 2, 0.45));
    else if (name === 'line') out.push(`M${x} ${cy}L${x + cellW} ${cy}`);
    else out.push(circleD(cx, cy, r, r) + circleD(cx, cy, r * 0.62, r * 0.62, true));
  }
  return out.join('');
};

/**
 * The film's own outline, written in a 0..1000 square, scaled to fill the box (aspect kept, centred). Absolute or
 * relative commands, arcs included: the outline is parsed, not re-written number by number.
 */
export const fitD = (d: string, box: {x: number; y: number; w: number; h: number}): string => {
  const segs = parsePath(d);
  if (!segs.length) throw new Error('pathMorph.fitD: empty outline');
  const s = Math.min(box.w, box.h) / 1000;
  const ox = box.x + (box.w - 1000 * s) / 2, oy = box.y + (box.h - 1000 * s) / 2;
  return flatten(segs, 32).map((p) => ptsToD(p.pts.map((q) => [ox + q[0] * s, oy + q[1] * s] as Pt), p.closed)).join('');
};
