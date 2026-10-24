// MAGIC MOVE — THE PURE HALF. Which glyph of one setting becomes which glyph of the next, where each one is on any
// frame of the move, and where a scattered glyph starts. No DOM, no React, no font: runtime/kineticMove.tsx draws
// with it, and tests run it in node.
//
// WHAT THE MOVE IS. Keynote's Magic Move for type, the core move of a title sequence: two settings of type, and the
// glyphs the two share TRAVEL from where they sit in the first to where they sit in the second, while the glyphs only
// the first has leave and the glyphs only the second has arrive. bench-rams had to hand-roll it (PasteUp read
// `useKinetic().layout.alts[0].glyphs` and drew its own spans) because the primitive animates every unit from ONE
// shared `from` state — it can say "everything rises", never "this letter goes THERE".
//
// WHICH GLYPH GOES WHERE. The longest common subsequence of the two grapheme sequences first: a run both settings
// share, in the same order, is the same WORD, and it should read as kept — it travels as a body. What the
// subsequence leaves is then paired by identity, nearest first (an anagram's letters cross over). Whitespace never
// pairs and never travels: it is not something the eye follows.
import {hash01} from './motion';
import {clamp01} from './kineticCore';

export type Match = {pairs: [number, number][]; leave: number[]; arrive: number[]};

const isSpace = (g: string) => /^\s+$/.test(g);

/** Pair the graphemes of `a` with those of `b` (indices). `posA` / `posB` are each glyph's x (for nearest-first). */
export const matchGlyphs = (a: string[], b: string[], posA?: number[], posB?: number[]): Match => {
  const n = a.length, m = b.length;
  // LCS table over non-space graphemes
  const L: number[][] = Array.from({length: n + 1}, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      L[i][j] = a[i] === b[j] && !isSpace(a[i]) ? 1 + L[i + 1][j + 1] : Math.max(L[i + 1][j], L[i][j + 1]);
    }
  }
  const usedA = new Array<boolean>(n).fill(false), usedB = new Array<boolean>(m).fill(false);
  const pairs: [number, number][] = [];
  for (let i = 0, j = 0; i < n && j < m;) {
    if (a[i] === b[j] && !isSpace(a[i]) && L[i][j] === 1 + L[i + 1][j + 1]) {
      pairs.push([i, j]); usedA[i] = true; usedB[j] = true; i += 1; j += 1;
    } else if (L[i + 1][j] >= L[i][j + 1]) i += 1;
    else j += 1;
  }
  // the rest, by identity, nearest first (a deterministic order: by distance, then by index)
  const cand: {i: number; j: number; d: number}[] = [];
  for (let i = 0; i < n; i++) {
    if (usedA[i] || isSpace(a[i])) continue;
    for (let j = 0; j < m; j++) {
      if (usedB[j] || a[i] !== b[j]) continue;
      const d = posA && posB ? Math.abs((posA[i] ?? 0) - (posB[j] ?? 0)) : Math.abs(i / Math.max(1, n) - j / Math.max(1, m));
      cand.push({i, j, d});
    }
  }
  cand.sort((p, q) => p.d - q.d || p.i - q.i || p.j - q.j);
  for (const c of cand) {
    if (usedA[c.i] || usedB[c.j]) continue;
    usedA[c.i] = true; usedB[c.j] = true;
    pairs.push([c.i, c.j]);
  }
  pairs.sort((p, q) => p[1] - q[1]);
  const leave = a.map((g, i) => (usedA[i] || isSpace(g) ? -1 : i)).filter((i) => i >= 0);
  const arrive = b.map((g, j) => (usedB[j] || isSpace(g) ? -1 : j)).filter((j) => j >= 0);
  return {pairs, leave, arrive};
};

// ── the path a travelling glyph takes ──────────────────────────────────────────────────────────────────────
/** A point `p` (0..1, already eased) along a gentle arc from (x0, y0) to (x1, y1). The arc bows by `bow` of the
 *  distance, to one side by the direction of travel — a glyph moving right rises over the line, one moving left
 *  passes under it, so two letters that swap places never pass through each other. */
export const arcAt = (p: number, x0: number, y0: number, x1: number, y1: number, bow = 0.16, maxLift = Infinity) => {
  const dx = x1 - x0, dy = y1 - y0, dist = Math.hypot(dx, dy);
  if (dist < 1e-6) return {x: x0, y: y0};
  // the normal (-dy, dx)/dist points DOWN the screen for a rightward move and UP for a leftward one, so stepping
  // against it lifts a rightward glyph and drops a leftward one: one formula, opposite sides. The bow is capped
  // (`maxLift`, px): a glyph crossing a whole line rose 120 px into the kicker above it on the first render.
  const lift = Math.min(maxLift, dist * bow) * Math.sin(Math.PI * clamp01(p));
  return {x: x0 + dx * p + (dy / dist) * lift, y: y0 + dy * p - (dx / dist) * lift};
};

// ── where a scattered glyph starts ─────────────────────────────────────────────────────────────────────────
export type Scatter = {x: number; y: number; rot: number; scale: number};
/** Glyph `i`'s scattered start inside the box (px), deterministic from `seed`: anywhere in the box, turned up to
 *  `turn` degrees, scaled between 0.7 and 1.5 of its rest size. */
export const scatterOf = (i: number, seed: number, box: {x: number; y: number; w: number; h: number}, turn = 28):
  Scatter => {
  const u = hash01(seed * 131 + i * 17.13), v = hash01(seed * 733 + i * 5.71);
  const r = hash01(seed * 37 + i * 91.3), s = hash01(seed * 59 + i * 3.17);
  return {x: box.x + u * box.w, y: box.y + v * box.h, rot: (r * 2 - 1) * turn, scale: 0.7 + 0.8 * s};
};

// ── the schedule of one move ───────────────────────────────────────────────────────────────────────────────
// In SECONDS, from the move's start. Leaving glyphs go first, the travellers cross in a stagger ordered by where they
// LAND (left to right, so the new line assembles in reading order), and arriving glyphs come in last, on their own
// stagger — so at every moment there is one thing to watch.
export type MoveTiming = {dur: number; leave: number; travel: number; arrive: number; stagger: number};
// the stagger is per WORD (runtime/kineticMove ranks by word, so a word travels as one body)
export const MOVE_DEFAULT: MoveTiming = {dur: 1.15, leave: 0.38, travel: 0.72, arrive: 0.42, stagger: 0.15};

/** A move's timing for a move given `dur` seconds: the parts keep their proportions, the stagger shrinks so the
 *  last traveller of `n` still lands inside the move. */
export const moveTiming = (dur: number, n: number): MoveTiming => {
  const k = Math.max(0.2, dur) / MOVE_DEFAULT.dur;
  const leave = MOVE_DEFAULT.leave * k, travel = MOVE_DEFAULT.travel * k, arrive = MOVE_DEFAULT.arrive * k;
  const room = Math.max(0, dur - 0.1 * dur - travel);
  const stagger = n > 1 ? Math.min(MOVE_DEFAULT.stagger, room / (n - 1)) : 0;
  return {dur: Math.max(0.2, dur), leave, travel, arrive, stagger};
};

/** Each traveller's [start, end] in seconds from the move's start, by its landing rank (0 = first to land). */
export const travelWindow = (rank: number, n: number, mt: MoveTiming): [number, number] => {
  const a = Math.min(mt.dur - mt.travel, 0.1 * mt.dur + rank * mt.stagger);
  return [a, a + mt.travel];
};
/** Each leaving glyph's window (rank by its own x). */
export const leaveWindow = (rank: number, n: number, mt: MoveTiming): [number, number] => {
  const st = n > 1 ? Math.min(mt.stagger, (mt.leave * 0.5) / (n - 1)) : 0;
  return [rank * st, rank * st + mt.leave * 0.6];
};
/** Each arriving glyph's window (rank by its landing x). */
export const arriveWindow = (rank: number, n: number, mt: MoveTiming): [number, number] => {
  const st = n > 1 ? Math.min(mt.stagger, (mt.arrive * 0.5) / (n - 1)) : 0;
  const a = mt.dur - mt.arrive + rank * st - (n > 1 ? (n - 1) * st : 0);
  return [Math.max(0, a), Math.max(0, a) + mt.arrive * 0.7];
};
