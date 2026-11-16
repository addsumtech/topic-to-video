// A PATH WALKED BY ARC LENGTH — the one walker runtime/kinetic (type on a path) and runtime/alongPath (a thing sent
// down a curve) both read, so a head and the glyphs it leads agree about where the curve is.
//
// THE WALK IS THE BROWSER'S OWN, NOT @remotion/paths'. Measured on a 1710px cubic (TypeOnPath's `rise`): its
// getPointAtLength went BACKWARDS 45 times in 2048 steps, by up to 2.3px, with steps up to 4.0px where 0.83 was due —
// the points lie on the curve but jitter along it. Its getTangentAtLength is also REVERSED on arc commands. kinetic
// had fixed this privately; alongPath still asked the library, and GenerationLoop's return stroke went back 50 of 66
// times in 2048 steps (audit 2026-11-15, step 6). The SVG engine's own arc length is exact, so it is used wherever
// there is a DOM; the library is the fallback for node, and every tangent is taken from the points, never asked.
//
// A TABLE (2048 steps, under a pixel apart on any path that fits a frame) is built for a path the second time it is
// asked about: a path whose `d` changes every frame would otherwise rebuild 2049 samples per frame, so a string seen
// once is answered directly. Tables are ~80 KB each and capped at 64; the lengths memo at 512 strings.
import {getLength, getPointAtLength} from '@remotion/paths';

export type PathTable = {L: number; xs: Float64Array; ys: Float64Array; tx: Float64Array; ty: Float64Array};
export const PATH_STEPS = 2048;
const TABLES = new Map<string, PathTable>();
const MAX_TABLES = 64;
const SEEN = new Map<string, number>();          // d -> its arc length
const MAX_SEEN = 512;
const ASKED = new Set<string>();                 // strings whose POINTS were asked once (a second ask builds the table)

let EL: SVGPathElement | null | undefined;
const svgPath = (d: string): SVGPathElement | null => {
  if (EL === undefined) {
    EL = typeof document !== 'undefined'
      ? (document.createElementNS('http://www.w3.org/2000/svg', 'path') as SVGPathElement) : null;
  }
  if (EL) EL.setAttribute('d', d);
  return EL;
};
const lengthNow = (d: string): number => {
  const el = svgPath(d);
  return el ? el.getTotalLength() : getLength(d);
};
const pointNow = (d: string, s: number): {x: number; y: number} => {
  const el = svgPath(d);
  if (el) {
    const p = el.getPointAtLength(s);
    return {x: p.x, y: p.y};
  }
  return getPointAtLength(d, s);
};

/** The table for `d`, built now if it is not held (kinetic asks every frame of a path's life, so it always builds). */
export const pathTable = (d: string): PathTable => {
  const hit = TABLES.get(d);
  if (hit) return hit;
  const xs = new Float64Array(PATH_STEPS + 1), ys = new Float64Array(PATH_STEPS + 1);
  const tx = new Float64Array(PATH_STEPS + 1), ty = new Float64Array(PATH_STEPS + 1);
  const L = lengthNow(d);
  for (let k = 0; k <= PATH_STEPS; k++) {
    const p = pointNow(d, (L * k) / PATH_STEPS);
    xs[k] = p.x; ys[k] = p.y;
  }
  for (let k = 0; k <= PATH_STEPS; k++) {
    const a = Math.max(0, k - 3), b = Math.min(PATH_STEPS, k + 3);
    const vx = xs[b] - xs[a], vy = ys[b] - ys[a], n = Math.hypot(vx, vy) || 1;
    tx[k] = vx / n; ty[k] = vy / n;
  }
  if (TABLES.size >= MAX_TABLES) TABLES.clear();
  const v = {L, xs, ys, tx, ty};
  TABLES.set(d, v);
  return v;
};

/** Point and direction (degrees) `s` px along a table. */
export const alongTable = (P: PathTable, s: number): {x: number; y: number; deg: number} => {
  const u = Math.max(0, Math.min(1, s / Math.max(1e-9, P.L))) * PATH_STEPS;
  const k = Math.min(PATH_STEPS - 1, Math.floor(u)), f = u - k;
  const x = P.xs[k] + (P.xs[k + 1] - P.xs[k]) * f, y = P.ys[k] + (P.ys[k + 1] - P.ys[k]) * f;
  const vx = P.tx[k] + (P.tx[k + 1] - P.tx[k]) * f, vy = P.ty[k] + (P.ty[k + 1] - P.ty[k]) * f;
  return {x, y, deg: (Math.atan2(vy, vx) * 180) / Math.PI};
};

/** A path's arc length, memoised by its string. */
export const walkLength = (d: string): number => {
  const t = TABLES.get(d);
  if (t) return t.L;
  const hit = SEEN.get(d);
  if (hit !== undefined) return hit;
  const L = lengthNow(d);
  if (SEEN.size >= MAX_SEEN) SEEN.clear();
  SEEN.set(d, L);
  return L;
};

/** Point and direction `s` px along `d`: from its table once the string recurs, answered directly the first time. */
export const walkAt = (d: string, s: number): {x: number; y: number; deg: number} => {
  const t = TABLES.get(d);
  if (t) return alongTable(t, s);
  if (ASKED.has(d)) return alongTable(pathTable(d), s);
  if (ASKED.size >= MAX_SEEN) ASKED.clear();
  ASKED.add(d);
  const L = walkLength(d);
  const c = Math.max(0, Math.min(L, s));
  const h = Math.min(0.5, L / 2);
  const p = pointNow(d, c), a = pointNow(d, Math.max(0, c - h)), b = pointNow(d, Math.min(L, c + h));
  return {x: p.x, y: p.y, deg: (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI};
};

export const _walkInternals = {TABLES, MAX_TABLES, SEEN, MAX_SEEN, ASKED};
