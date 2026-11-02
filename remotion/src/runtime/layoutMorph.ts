// LAYOUT MORPH — one set of items, moved from one ARRANGEMENT to another inside a beat. Pure
// (tests/test_layout_morph.py); a register draws each item into the box this hands it.
//
// The arrangements are claims: `grid` (these are peers), `hero` (this one matters), `rank` (this is the order, by
// value), `groups` (these belong together). Moving the SAME items between them is how a beat changes its mind on
// screen, and the viewer keeps track of each item because it travels instead of being redrawn. The peer library
// does this in several shots (a mosaic re-framing between grid, hero slot and cascade; a headline demoting into a
// section label; rows turning into cards mid-flight); this library could carry one element across a cut and had
// nothing that moved a set of things between arrangements.
//
// Every layout is a deterministic set of boxes inside `box` (the register's content zone) with no two overlapping,
// and refuses — rather than shrinks past legibility — a count its box cannot hold at `minCell`.

export type Box = {x: number; y: number; w: number; h: number};
export type Rect = Box;

const GAP = 24;

const tooSmall = (what: string, n: number, cw: number, ch: number, min: number) =>
  new Error(`layoutMorph.${what}: ${n} item(s) in this box would be ${Math.round(cw)}x${Math.round(ch)} px — too small ` +
    `(under ${min} px); give the items more room or show fewer`);

/** n equal cells, the column count chosen so a cell is closest to `aspect` (w/h); a short last row is centred. */
export const grid = (n: number, box: Box, o: {gap?: number; aspect?: number; minCell?: number} = {}): Rect[] => {
  const gap = o.gap ?? GAP, aspect = o.aspect ?? 1.6, min = o.minCell ?? 96;
  if (n <= 0) return [];
  let best = 1, bestErr = Infinity;
  for (let c = 1; c <= n; c++) {
    const r = Math.ceil(n / c);
    const cw = (box.w - gap * (c - 1)) / c, ch = (box.h - gap * (r - 1)) / r;
    const err = Math.abs(Math.log((cw / ch) / aspect));
    if (cw > 0 && ch > 0 && err < bestErr) { best = c; bestErr = err; }
  }
  const cols = best, rows = Math.ceil(n / cols);
  const cw = (box.w - gap * (cols - 1)) / cols, ch = (box.h - gap * (rows - 1)) / rows;
  if (cw < min || ch < min) throw tooSmall('grid', n, cw, ch, min);
  const out: Rect[] = [];
  for (let i = 0; i < n; i++) {
    const r = Math.floor(i / cols), inRow = r === rows - 1 ? n - cols * (rows - 1) : cols;
    const c = i - r * cols;
    const x0 = box.x + (box.w - (inRow * cw + (inRow - 1) * gap)) / 2;
    out.push({x: x0 + c * (cw + gap), y: box.y + r * (ch + gap), w: cw, h: ch});
  }
  return out;
};

/** Item `hero` takes `share` of the box along its long side (the left of a landscape box, the top of a portrait
 *  one); the others grid in the rest. */
export const hero = (n: number, box: Box, heroIndex: number, o: {gap?: number; share?: number; minCell?: number} = {}):
  Rect[] => {
  const gap = o.gap ?? GAP, share = o.share ?? 0.58;
  if (n <= 0) return [];
  if (heroIndex < 0 || heroIndex >= n) throw new Error(`layoutMorph.hero: hero ${heroIndex} is not one of the ${n} items`);
  if (n === 1) return [{...box}];
  // the hero takes the box's LONG side: the left part of a landscape box, the top of a portrait one
  const tall = box.h > box.w;
  const hRect = tall ? {x: box.x, y: box.y, w: box.w, h: box.h * share} : {x: box.x, y: box.y, w: box.w * share, h: box.h};
  const restBox = tall ? {x: box.x, y: box.y + hRect.h + gap, w: box.w, h: box.h - hRect.h - gap}
    : {x: box.x + hRect.w + gap, y: box.y, w: box.w - hRect.w - gap, h: box.h};
  const rest = grid(n - 1, restBox, {gap, aspect: 1.4, minCell: o.minCell ?? 80});
  const out: Rect[] = [];
  let k = 0;
  for (let i = 0; i < n; i++) out.push(i === heroIndex ? hRect : rest[k++]);
  return out;
};

/** Each value's share of the largest — the length a register gives its bar inside a `rank` row. */
export const shares = (values: number[]): number[] => {
  const max = Math.max(...values) || 1;
  return values.map((v) => v / max);
};

/** Full-width rows sorted by value, largest first. The ROW is the item; the register draws its bar inside the row at
 *  `shares()` of the bar's room, with the label in a column of its own — a short bar then still has a readable label
 *  (a row whose own width carried the value left a 6% item no room for its name). */
export const rank = (values: number[], box: Box, o: {gap?: number; rowMax?: number} = {}): Rect[] => {
  const n = values.length, gap = o.gap ?? 16, rowMax = o.rowMax ?? 120;
  if (n === 0) return [];
  if (values.some((v) => !(typeof v === 'number' && isFinite(v) && v >= 0))) {
    throw new Error('layoutMorph.rank: every value must be a finite number >= 0 — a ranking of missing values is not one');
  }
  const rh = Math.min(rowMax, (box.h - gap * (n - 1)) / n);
  if (rh < 40) throw tooSmall('rank', n, box.w, rh, 40);
  const order = values.map((v, i) => i).sort((a, b) => values[b] - values[a] || a - b);
  const y0 = box.y + (box.h - (n * rh + (n - 1) * gap)) / 2;
  const out: Rect[] = new Array(n);
  order.forEach((i, pos) => {
    out[i] = {x: box.x, y: y0 + pos * (rh + gap), w: box.w, h: rh};
  });
  return out;
};

/** The group keys in the order they first appear — the columns `groups` lays out, left to right. */
export const groupOrder = (keys: string[]): string[] => keys.filter((k, i) => keys.indexOf(k) === i);

/** One column per group (first-appearance order), its items stacked under a header band of `head` px. */
export const groups = (keys: string[], box: Box, o: {gap?: number; head?: number; rowMax?: number; minCell?: number} = {}):
  Rect[] => {
  const gap = o.gap ?? GAP, head = o.head ?? 64, rowMax = o.rowMax ?? 180, min = o.minCell ?? 64;
  const g = groupOrder(keys);
  if (!g.length) return [];
  const cw = (box.w - gap * (g.length - 1)) / g.length;
  const most = Math.max(...g.map((k) => keys.filter((x) => x === k).length));
  const ch = Math.min(rowMax, (box.h - head - gap * (most - 1)) / most);
  if (cw < min || ch < min) throw tooSmall('groups', keys.length, cw, ch, min);
  const seen: Record<string, number> = {};
  return keys.map((k) => {
    const c = g.indexOf(k), r = (seen[k] = (seen[k] ?? -1) + 1);
    return {x: box.x + c * (cw + gap), y: box.y + head + r * (ch + gap), w: cw, h: ch};
  });
};

/** The header band of each group's column (for its name), in `groupOrder` order. */
export const groupHeads = (keys: string[], box: Box, o: {gap?: number; head?: number} = {}): Rect[] => {
  const gap = o.gap ?? GAP, head = o.head ?? 64, g = groupOrder(keys);
  const cw = (box.w - gap * (g.length - 1)) / g.length;
  return g.map((_, c) => ({x: box.x + c * (cw + gap), y: box.y, w: cw, h: head - 12}));
};

const ease = (q: number) => (q < 0.5 ? 4 * q * q * q : 1 - Math.pow(-2 * q + 2, 3) / 2);
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

export type MorphOpts = {
  /** 0..<1: the share of the move over which items set off one after another (0 = all together) */
  stagger?: number;
  /** which item sets off first: as listed, or the one with the furthest to go */
  order?: 'index' | 'distance';
  /** bow of each item's path, as a share of its travel (0 = straight) */
  arc?: number;
};

/** Every item's box at progress p (0 = `a`, 1 = `b`, exactly), each on its own eased, slightly bowed path. */
export const morph = (a: Rect[], b: Rect[], p: number, o: MorphOpts = {}): Rect[] => {
  if (a.length !== b.length) throw new Error(`layoutMorph.morph: ${a.length} items become ${b.length} — the same items move`);
  const n = a.length, stagger = Math.min(0.9, Math.max(0, o.stagger ?? 0)), arc = o.arc ?? 0.08;
  const dist = a.map((r, i) => Math.hypot(b[i].x - r.x, b[i].y - r.y));
  const rankOf = a.map((_, i) => i);
  if (o.order === 'distance') {
    const byDist = a.map((_, i) => i).sort((i, j) => dist[j] - dist[i] || i - j);
    byDist.forEach((i, k) => { rankOf[i] = k; });
  }
  return a.map((r, i) => {
    const d = n > 1 ? (stagger * rankOf[i]) / (n - 1) : 0;
    const e = ease(clamp01((p - d) / (1 - stagger)));
    const dx = b[i].x - r.x, dy = b[i].y - r.y, len = dist[i] || 1;
    const bow = arc * dist[i] * Math.sin(Math.PI * e);
    return {x: r.x + dx * e + (-dy / len) * bow, y: r.y + dy * e + (dx / len) * bow,
      w: r.w + (b[i].w - r.w) * e, h: r.h + (b[i].h - r.h) * e};
  });
};
