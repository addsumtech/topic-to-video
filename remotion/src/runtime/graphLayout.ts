// ONE STRUCTURE FOR A WHOLE FILM — the layout of a graph that a film builds up beat by beat (LivingMap). Pure
// (tests/test_living_map.py).
//
// The layout is computed ONCE over every node the film will ever show, so adding a node never moves the others: a
// viewer who has learnt where "k-space" sits keeps it there for the rest of the film. Layered left to right (the
// longest path from a source decides a node's column — the reading direction of a pipeline or a derivation), and
// within a column ordered by two barycentre sweeps so edges cross as little as such a simple pass can manage. A cycle
// is broken at the edge that closes it (the one pointing back to a node still being visited), never by guessing.
// `frame` is the camera: the scale and offset that put a set of nodes in the content zone, capped so a single node
// is framed, not blown up to fill it.

export type GNode = {id: string; label?: string};
export type GEdge = [string, string] | [string, string, string];
export type Placed = {x: number; y: number; layer: number; order: number};

/** A node's box in WORLD units (the register draws it at this size before the camera's scale). */
export const NODE_W = 300, NODE_H = 116;
export const DX = 400, DY = 190;

export const layout = (nodes: GNode[], edges: GEdge[]): Record<string, Placed> => {
  const ids = nodes.map((n) => n.id);
  const known = new Set(ids);
  for (const e of edges) {
    if (!known.has(e[0]) || !known.has(e[1])) throw new Error(`graphLayout: edge ${e[0]} -> ${e[1]} names a node that is not in the map`);
  }
  const out: Record<string, string[]> = Object.fromEntries(ids.map((i) => [i, []]));
  for (const [a, b] of edges) if (a !== b) out[a].push(b);
  // break cycles at the edge that closes them (DFS in the order the nodes were given)
  const state: Record<string, 0 | 1 | 2> = Object.fromEntries(ids.map((i) => [i, 0]));
  const keep: [string, string][] = [];
  const visit = (u: string) => {
    state[u] = 1;
    for (const v of out[u]) {
      if (state[v] === 1) continue;            // back edge: dropped for layering
      keep.push([u, v]);
      if (state[v] === 0) visit(v);
    }
    state[u] = 2;
  };
  for (const i of ids) if (state[i] === 0) visit(i);
  const preds: Record<string, string[]> = Object.fromEntries(ids.map((i) => [i, []]));
  for (const [a, b] of keep) preds[b].push(a);
  // longest path from a source
  const layer: Record<string, number> = {};
  const lay = (u: string): number => {
    if (layer[u] !== undefined) return layer[u];
    layer[u] = 0;                               // provisional (acyclic now, so never read mid-recursion wrongly)
    layer[u] = preds[u].length ? Math.max(...preds[u].map(lay)) + 1 : 0;
    return layer[u];
  };
  ids.forEach(lay);
  // a SOURCE that feeds a later column sits just before what it feeds, not in column 0: a side input (gradients into
  // the signal) drawn at the far left ran its edge across the whole map
  const succOf: Record<string, string[]> = Object.fromEntries(ids.map((i) => [i, []]));
  for (const [a, b] of keep) succOf[a].push(b);
  for (const i of ids) {
    if (!preds[i].length && succOf[i].length) layer[i] = Math.max(0, Math.min(...succOf[i].map((j) => layer[j])) - 1);
  }
  const nL = Math.max(0, ...Object.values(layer)) + 1;
  const cols: string[][] = Array.from({length: nL}, () => []);
  for (const i of ids) cols[layer[i]].push(i);
  const pos: Record<string, number> = {};
  const index = (c: string[]) => c.forEach((id, k) => { pos[id] = k; });
  cols.forEach(index);
  const succ: Record<string, string[]> = Object.fromEntries(ids.map((i) => [i, []]));
  for (const [a, b] of keep) succ[a].push(b);
  const sweep = (c: string[], nb: Record<string, string[]>) => {
    const bc = (id: string) => (nb[id].length ? nb[id].reduce((s, j) => s + pos[j], 0) / nb[id].length : pos[id]);
    const key = Object.fromEntries(c.map((id) => [id, bc(id)]));
    c.sort((p, q) => key[p] - key[q] || ids.indexOf(p) - ids.indexOf(q));
    index(c);
  };
  for (let r = 0; r < 2; r++) {
    for (let l = 1; l < nL; l++) sweep(cols[l], preds);
    for (let l = nL - 2; l >= 0; l--) sweep(cols[l], succ);
  }
  const res: Record<string, Placed> = {};
  cols.forEach((c, l) => c.forEach((id, k) => {
    res[id] = {x: l * DX, y: (k - (c.length - 1) / 2) * DY, layer: l, order: k};
  }));
  return res;
};

export type Zone = {x: number; y: number; w: number; h: number};
export type Cam = {s: number; tx: number; ty: number};

/** The camera that puts `ids` (their boxes plus `margin` world units) inside `zone`, scale capped at `maxScale`. */
export const frame = (p: Record<string, Placed>, ids: string[], zone: Zone, o: {maxScale?: number; margin?: number} = {}): Cam => {
  const pts = ids.map((i) => p[i]).filter(Boolean);
  if (!pts.length) throw new Error('graphLayout.frame: nothing to frame');
  const m = o.margin ?? 40;
  const x0 = Math.min(...pts.map((q) => q.x)) - NODE_W / 2 - m, x1 = Math.max(...pts.map((q) => q.x)) + NODE_W / 2 + m;
  const y0 = Math.min(...pts.map((q) => q.y)) - NODE_H / 2 - m, y1 = Math.max(...pts.map((q) => q.y)) + NODE_H / 2 + m;
  const s = Math.min(o.maxScale ?? 1.5, zone.w / (x1 - x0), zone.h / (y1 - y0));
  return {s, tx: zone.x + zone.w / 2 - s * (x0 + x1) / 2, ty: zone.y + zone.h / 2 - s * (y0 + y1) / 2};
};

/** Two cameras blended at e (eased by the caller): the scale in log space so a zoom reads even, and the WORLD point at
 *  the zone's centre on a straight line — blending the offsets instead swings the picture sideways during a zoom. */
export const blendCam = (a: Cam, b: Cam, e: number, zone: Zone): Cam => {
  const cx = zone.x + zone.w / 2, cy = zone.y + zone.h / 2;
  const s = Math.exp(Math.log(a.s) + (Math.log(b.s) - Math.log(a.s)) * e);
  const wa = {x: (cx - a.tx) / a.s, y: (cy - a.ty) / a.s}, wb = {x: (cx - b.tx) / b.s, y: (cy - b.ty) / b.s};
  const w = {x: wa.x + (wb.x - wa.x) * e, y: wa.y + (wb.y - wa.y) * e};
  return {s, tx: cx - s * w.x, ty: cy - s * w.y};
};
