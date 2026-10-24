// PATH GEOMETRY, PURE — parse an SVG `d`, transform it, bound it, flatten it, resample it.
//
// NO IMPORTS, AND THAT IS LOAD-BEARING. Two programs read this file: the Remotion bundle (runtime/mathMorph.tsx,
// runtime/pathMorph.ts) and the node typesetter (scripts/tex_glyphs.mjs, which imports it by type stripping). A glyph's
// bounding box is computed by the typesetter and a morph's outline by the bundle, and they must be the same geometry:
// one implementation, not two that agree today.
//
// WHY NOT @remotion/paths FOR THIS. It is used where it is right (runtime/alongPath for a point at a length). But the
// research for runtime/kinetic measured its `getPointAtLength` going BACKWARDS 45 times in 2048 steps on a cubic, and a
// morph built on uneven samples crawls: the points bunch where the walk stalls and the outline shimmers between frames.
// Here the samples are taken off a flattened polyline, by cumulative chord length, which is monotone by construction.
// And `interpolatePath` (installed 4.0.486) pairs SEGMENTS, not shapes: two outlines with different subpath counts or a
// different start point twist through each other — measured in runtime/pathMorph.ts — which is why the morph
// resamples both sides to the same points and aligns them before it lerps.

export type Pt = [number, number];
/** One absolute segment. `M` opens a subpath, `Z` closes it. Every other command is reduced to these. */
export type Seg =
  | {c: 'M'; p: Pt}
  | {c: 'L'; p: Pt}
  | {c: 'Q'; p1: Pt; p: Pt}
  | {c: 'C'; p1: Pt; p2: Pt; p: Pt}
  | {c: 'Z'};
/** 2D affine [a, b, c, d, e, f]: x' = a·x + c·y + e, y' = b·x + d·y + f (SVG's own order). */
export type Mat = [number, number, number, number, number, number];
export type Poly = {pts: Pt[]; closed: boolean};

export const IDENTITY: Mat = [1, 0, 0, 1, 0, 0];
export const matMul = (m: Mat, n: Mat): Mat => [
  m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
  m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
  m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5],
];
export const apply = (m: Mat, p: Pt): Pt => [m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5]];

const NUM = /[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/y;
const CMD = /[MmLlHhVvQqTtCcSsAaZz]/;
const ARGS: Record<string, number> = {M: 2, L: 2, H: 1, V: 1, Q: 4, T: 2, C: 6, S: 4, A: 7, Z: 0};

/** Tokenise `d` into commands and numbers. Throws on anything else — a path that silently loses a command draws a
 *  different shape, and nothing downstream could tell. */
const tokens = (d: string): (string | number)[] => {
  const out: (string | number)[] = [];
  let i = 0;
  while (i < d.length) {
    const ch = d[i];
    if (ch === ' ' || ch === ',' || ch === '\n' || ch === '\t' || ch === '\r') { i++; continue; }
    if (CMD.test(ch)) { out.push(ch); i++; continue; }
    // the arc flags are single digits that may be written with no separator ("0 01" or "011"), read below
    NUM.lastIndex = i;
    const m = NUM.exec(d);
    if (!m || m.index !== i) throw new Error(`pathCore: cannot read "${d.slice(i, i + 12)}" in an SVG path`);
    out.push(parseFloat(m[0]));
    i += m[0].length;
  }
  return out;
};

/** SVG arc → cubic Béziers (the standard endpoint→centre conversion, ≤90° a piece). */
const arcToCubics = (p0: Pt, rx: number, ry: number, phiDeg: number, large: number, sweep: number, p: Pt): Seg[] => {
  if (rx === 0 || ry === 0 || (p0[0] === p[0] && p0[1] === p[1])) return [{c: 'L', p}];
  rx = Math.abs(rx); ry = Math.abs(ry);
  const phi = (phiDeg * Math.PI) / 180, cos = Math.cos(phi), sin = Math.sin(phi);
  const dx = (p0[0] - p[0]) / 2, dy = (p0[1] - p[1]) / 2;
  const x1 = cos * dx + sin * dy, y1 = -sin * dx + cos * dy;
  const lam = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry);
  if (lam > 1) { const s = Math.sqrt(lam); rx *= s; ry *= s; }
  const num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1;
  const den = rx * rx * y1 * y1 + ry * ry * x1 * x1;
  const k = (large === sweep ? -1 : 1) * Math.sqrt(Math.max(0, num / den));
  const cx1 = (k * rx * y1) / ry, cy1 = (-k * ry * x1) / rx;
  const cx = cos * cx1 - sin * cy1 + (p0[0] + p[0]) / 2, cy = sin * cx1 + cos * cy1 + (p0[1] + p[1]) / 2;
  const ang = (ux: number, uy: number, vx: number, vy: number) => {
    const a = Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
    return a;
  };
  const th1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry);
  let dth = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry);
  if (!sweep && dth > 0) dth -= 2 * Math.PI;
  if (sweep && dth < 0) dth += 2 * Math.PI;
  const n = Math.max(1, Math.ceil(Math.abs(dth) / (Math.PI / 2) - 1e-9));
  const step = dth / n, kk = (4 / 3) * Math.tan(step / 4);
  const out: Seg[] = [];
  const pt = (t: number): Pt => [cx + rx * Math.cos(t) * cos - ry * Math.sin(t) * sin,
    cy + rx * Math.cos(t) * sin + ry * Math.sin(t) * cos];
  const dpt = (t: number): Pt => [-rx * Math.sin(t) * cos - ry * Math.cos(t) * sin,
    -rx * Math.sin(t) * sin + ry * Math.cos(t) * cos];
  for (let i = 0; i < n; i++) {
    const a = th1 + i * step, b = a + step;
    const pa = pt(a), pb = i === n - 1 ? p : pt(b), da = dpt(a), db = dpt(b);
    out.push({c: 'C', p1: [pa[0] + kk * da[0], pa[1] + kk * da[1]], p2: [pb[0] - kk * db[0], pb[1] - kk * db[1]], p: pb});
  }
  return out;
};

/** Parse `d` into ABSOLUTE M/L/Q/C/Z segments. H/V/T/S/A and every relative command are reduced to those. */
export const parsePath = (d: string): Seg[] => {
  const tk = tokens(String(d ?? ''));
  const out: Seg[] = [];
  let i = 0, cmd = '', cur: Pt = [0, 0], start: Pt = [0, 0];
  let lastQ: Pt | null = null, lastC: Pt | null = null;
  const num = (): number => {
    const v = tk[i++];
    if (typeof v !== 'number') throw new Error(`pathCore: command ${cmd} is missing a number in "${String(d).slice(0, 40)}"`);
    return v;
  };
  while (i < tk.length) {
    if (typeof tk[i] === 'string') cmd = tk[i++] as string;
    else if (!cmd) throw new Error(`pathCore: a path must open with a command, got "${String(d).slice(0, 20)}"`);
    const C = cmd.toUpperCase(), rel = cmd !== C;
    const ox = rel ? cur[0] : 0, oy = rel ? cur[1] : 0;
    if (C === 'Z') {
      out.push({c: 'Z'});
      cur = start; lastQ = lastC = null;
      // a number straight after Z is malformed; without this the loop would re-read Z on it forever
      if (typeof tk[i] === 'number') throw new Error(`pathCore: a number follows Z in "${String(d).slice(0, 40)}"`);
      continue;
    }
    if (!(C in ARGS)) throw new Error(`pathCore: unknown command ${cmd}`);
    if (C === 'M') {
      cur = [ox + num(), oy + num()]; start = cur;
      out.push({c: 'M', p: cur});
      cmd = rel ? 'l' : 'L';                         // further pairs after M are line-tos
      lastQ = lastC = null;
      continue;
    }
    if (C === 'L') { cur = [ox + num(), oy + num()]; out.push({c: 'L', p: cur}); lastQ = lastC = null; continue; }
    if (C === 'H') { cur = [ox + num(), cur[1]]; out.push({c: 'L', p: cur}); lastQ = lastC = null; continue; }
    if (C === 'V') { cur = [cur[0], oy + num()]; out.push({c: 'L', p: cur}); lastQ = lastC = null; continue; }
    if (C === 'Q') {
      const p1: Pt = [ox + num(), oy + num()], p: Pt = [ox + num(), oy + num()];
      out.push({c: 'Q', p1, p}); lastQ = p1; lastC = null; cur = p; continue;
    }
    if (C === 'T') {
      const p1: Pt = lastQ ? [2 * cur[0] - lastQ[0], 2 * cur[1] - lastQ[1]] : cur;
      const p: Pt = [ox + num(), oy + num()];
      out.push({c: 'Q', p1, p}); lastQ = p1; lastC = null; cur = p; continue;
    }
    if (C === 'C') {
      const p1: Pt = [ox + num(), oy + num()], p2: Pt = [ox + num(), oy + num()], p: Pt = [ox + num(), oy + num()];
      out.push({c: 'C', p1, p2, p}); lastC = p2; lastQ = null; cur = p; continue;
    }
    if (C === 'S') {
      const p1: Pt = lastC ? [2 * cur[0] - lastC[0], 2 * cur[1] - lastC[1]] : cur;
      const p2: Pt = [ox + num(), oy + num()], p: Pt = [ox + num(), oy + num()];
      out.push({c: 'C', p1, p2, p}); lastC = p2; lastQ = null; cur = p; continue;
    }
    // A
    const rx = num(), ry = num(), phi = num(), large = num(), sweep = num();
    const p: Pt = [ox + num(), oy + num()];
    out.push(...arcToCubics(cur, rx, ry, phi, large ? 1 : 0, sweep ? 1 : 0, p));
    lastQ = lastC = null; cur = p;
  }
  return out;
};

export const transformSegs = (segs: Seg[], m: Mat): Seg[] => segs.map((s) => {
  if (s.c === 'Z') return s;
  if (s.c === 'M' || s.c === 'L') return {c: s.c, p: apply(m, s.p)};
  if (s.c === 'Q') return {c: 'Q', p1: apply(m, s.p1), p: apply(m, s.p)};
  return {c: 'C', p1: apply(m, s.p1), p2: apply(m, s.p2), p: apply(m, s.p)};
});

const r4 = (v: number) => {
  const x = Math.round(v * 1e4) / 1e4;
  return Object.is(x, -0) ? '0' : String(x);
};
export const segsToD = (segs: Seg[]): string => segs.map((s) => {
  if (s.c === 'Z') return 'Z';
  if (s.c === 'M' || s.c === 'L') return `${s.c}${r4(s.p[0])} ${r4(s.p[1])}`;
  if (s.c === 'Q') return `Q${r4(s.p1[0])} ${r4(s.p1[1])} ${r4(s.p[0])} ${r4(s.p[1])}`;
  return `C${r4(s.p1[0])} ${r4(s.p1[1])} ${r4(s.p2[0])} ${r4(s.p2[1])} ${r4(s.p[0])} ${r4(s.p[1])}`;
}).join('');

/** The EXACT bounding box (curve extrema, not the control hull), or null for an empty path. */
export const segsBBox = (segs: Seg[]): [number, number, number, number] | null => {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const add = (p: Pt) => { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); };
  let cur: Pt = [0, 0], start: Pt = [0, 0];
  for (const s of segs) {
    if (s.c === 'Z') { cur = start; continue; }
    if (s.c === 'M') { cur = s.p; start = s.p; add(s.p); continue; }
    if (s.c === 'L') { add(s.p); cur = s.p; continue; }
    if (s.c === 'Q') {
      add(s.p);
      for (let k = 0; k < 2; k++) {
        const den = cur[k] - 2 * s.p1[k] + s.p[k];
        if (Math.abs(den) > 1e-12) {
          const t = (cur[k] - s.p1[k]) / den;
          if (t > 0 && t < 1) add(qAt(cur, s.p1, s.p, t));
        }
      }
      cur = s.p; continue;
    }
    add(s.p);
    for (let k = 0; k < 2; k++) {
      // derivative of a cubic: a·t² + b·t + c
      const a = -cur[k] + 3 * s.p1[k] - 3 * s.p2[k] + s.p[k];
      const b = 2 * (cur[k] - 2 * s.p1[k] + s.p2[k]);
      const c = s.p1[k] - cur[k];
      const roots: number[] = [];
      if (Math.abs(a) < 1e-12) { if (Math.abs(b) > 1e-12) roots.push(-c / b); }
      else {
        const disc = b * b - 4 * a * c;
        if (disc >= 0) { const q = Math.sqrt(disc); roots.push((-b + q) / (2 * a), (-b - q) / (2 * a)); }
      }
      roots.forEach((t) => { if (t > 0 && t < 1) add(cAt(cur, s.p1, s.p2, s.p, t)); });
    }
    cur = s.p;
  }
  return isFinite(x0) ? [x0, y0, x1, y1] : null;
};

const qAt = (a: Pt, b: Pt, c: Pt, t: number): Pt => {
  const u = 1 - t;
  return [u * u * a[0] + 2 * u * t * b[0] + t * t * c[0], u * u * a[1] + 2 * u * t * b[1] + t * t * c[1]];
};
const cAt = (a: Pt, b: Pt, c: Pt, d: Pt, t: number): Pt => {
  const u = 1 - t;
  return [u * u * u * a[0] + 3 * u * u * t * b[0] + 3 * u * t * t * c[0] + t * t * t * d[0],
    u * u * u * a[1] + 3 * u * u * t * b[1] + 3 * u * t * t * c[1] + t * t * t * d[1]];
};

/** Flatten to polylines, one per subpath. `steps` points per curve (curves are short in every use here). */
export const flatten = (segs: Seg[], steps = 24): Poly[] => {
  const out: Poly[] = [];
  let cur: Pt = [0, 0], pts: Pt[] | null = null;
  const close = (closed: boolean) => {
    if (pts && pts.length > 1) out.push({pts, closed});
    pts = null;
  };
  for (const s of segs) {
    if (s.c === 'M') { close(false); pts = [s.p]; cur = s.p; continue; }
    if (s.c === 'Z') {
      if (pts) {
        const f = pts[0], l = pts[pts.length - 1];
        if (Math.hypot(f[0] - l[0], f[1] - l[1]) < 1e-9) pts.pop();
      }
      close(true);
      continue;
    }
    if (!pts) pts = [cur];
    if (s.c === 'L') { pts.push(s.p); cur = s.p; continue; }
    for (let k = 1; k <= steps; k++) {
      const t = k / steps;
      pts.push(s.c === 'Q' ? qAt(cur, s.p1, s.p, t) : cAt(cur, s.p1, s.p2, s.p, t));
    }
    cur = s.p;
  }
  close(false);
  return out;
};

/** A polyline's length (closing edge included when closed). */
export const polyLength = (p: Poly): number => {
  let L = 0;
  const n = p.pts.length;
  for (let i = 1; i < n; i++) L += Math.hypot(p.pts[i][0] - p.pts[i - 1][0], p.pts[i][1] - p.pts[i - 1][1]);
  if (p.closed && n > 1) L += Math.hypot(p.pts[0][0] - p.pts[n - 1][0], p.pts[0][1] - p.pts[n - 1][1]);
  return L;
};

/** `n` points evenly spaced by ARC LENGTH. Closed: n points round the loop (the first is not repeated). Open: n points
 *  from the start to the end inclusive. Monotone by construction (cumulative chord length), so samples never bunch. */
export const resample = (p: Poly, n: number): Pt[] => {
  if (n < 2) throw new Error('pathCore.resample needs at least 2 points');
  const src = p.closed ? [...p.pts, p.pts[0]] : p.pts;
  if (src.length < 2) return Array.from({length: n}, () => [src[0][0], src[0][1]] as Pt);
  const cum: number[] = [0];
  for (let i = 1; i < src.length; i++) cum.push(cum[i - 1] + Math.hypot(src[i][0] - src[i - 1][0], src[i][1] - src[i - 1][1]));
  const L = cum[cum.length - 1];
  const out: Pt[] = [];
  const count = p.closed ? n : n - 1;
  let j = 1;
  for (let k = 0; k < n; k++) {
    const s = L <= 0 ? 0 : (L * k) / count;
    while (j < cum.length - 1 && cum[j] < s) j++;
    const seg = cum[j] - cum[j - 1];
    const f = seg > 0 ? Math.max(0, Math.min(1, (s - cum[j - 1]) / seg)) : 0;
    out.push([src[j - 1][0] + (src[j][0] - src[j - 1][0]) * f, src[j - 1][1] + (src[j][1] - src[j - 1][1]) * f]);
  }
  return out;
};

/** Signed area (positive = clockwise in a y-down frame). */
export const signedArea = (pts: Pt[]): number => {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], q = pts[(i + 1) % pts.length];
    a += p[0] * q[1] - q[0] * p[1];
  }
  return a / 2;
};
export const centroidOf = (pts: Pt[]): Pt => {
  let x = 0, y = 0;
  pts.forEach((p) => { x += p[0]; y += p[1]; });
  return [x / Math.max(1, pts.length), y / Math.max(1, pts.length)];
};

/**
 * Re-order `b` so that lerping `a[i] → b[i]` moves each point the least: for a closed loop, the same winding as `a`
 * and the start index that minimises the summed squared distance; for an open line, forwards or reversed. Without it a
 * circle morphing into a square spins a quarter turn on the way, or turns itself inside out through its own centre.
 */
export const alignTo = (a: Pt[], b: Pt[], closed: boolean): Pt[] => {
  const n = a.length;
  if (b.length !== n) throw new Error('pathCore.alignTo needs equal point counts — resample both first');
  const cost = (bb: Pt[], off: number) => {
    let s = 0;
    for (let i = 0; i < n; i++) {
      const q = bb[(i + off) % n];
      s += (a[i][0] - q[0]) ** 2 + (a[i][1] - q[1]) ** 2;
    }
    return s;
  };
  if (!closed) {
    const rev = b.slice().reverse();
    return cost(rev, 0) < cost(b, 0) ? rev : b;
  }
  const bw = Math.sign(signedArea(a)) !== Math.sign(signedArea(b)) && signedArea(b) !== 0 ? b.slice().reverse() : b;
  let best = 0, bestC = Infinity;
  for (let off = 0; off < n; off++) {
    const c = cost(bw, off);
    if (c < bestC - 1e-9) { bestC = c; best = off; }
  }
  return Array.from({length: n}, (_, i) => bw[(i + best) % n]);
};

export const ptsToD = (pts: Pt[], closed: boolean): string =>
  pts.map((p, i) => `${i ? 'L' : 'M'}${r4(p[0])} ${r4(p[1])}`).join('') + (closed ? 'Z' : '');
