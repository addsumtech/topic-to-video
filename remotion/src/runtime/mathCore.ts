// THE MATHS OF MOVING MATHS — pure functions of an equation's glyphs and a progress value. No hooks, NO IMPORTS
// (tests/test_math_morph.py runs this file under node directly, and the typesetter shares its sibling pathCore.ts).
//
// The ideas are Manim's (3b1b/manim, ManimCommunity), reimplemented here from their published behaviour, not their
// code: Write / DrawBorderThenFill (each glyph's outline is drawn, then filled, staggered through the expression — a
// LaggedStart), TransformMatchingTex (glyphs both forms share TRAVEL to their new place; the rest leave and arrive),
// Indicate (a term swells and takes the accent, then settles) and Circumscribe (a frame drawn round a term), and the
// ValueTracker (a number inside an equation that is a live function of time, set from the film's own two values).
//
// WHAT A GLYPH IS. The typesetter (scripts/tex_glyphs.mjs) hands every glyph over with the matrix MathJax placed it with,
// in the equation's own units (1/1000 em, y down). A PLACEMENT puts an equation on the frame: `x, y` its box's top-left
// in px and `s` px per unit. Everything below works in SCREEN matrices (placement · glyph), so lerping one glyph from
// its place in A to its place in B is lerping two matrices — translation and scale together, and a fraction bar of one
// length becomes a fraction bar of another exactly, because a rule is the unit square under a scale.

export type Mat6 = [number, number, number, number, number, number];
export type MGlyph = {
  /** the outline in the glyph's own coordinates */
  d: string;
  /** MathJax's placement of it, into equation units */
  m: Mat6;
  /** the character (hex code point), or `rule:<role>` / `frame:` / `stroke:` / `ring:` for drawn parts */
  c: string;
  /** the MathML node that holds it (mi, mo, mn, …) and that node's parent */
  n: string;
  p: string;
  /** every \class{…} the glyph sits inside, outermost first */
  k: string[];
  /** a \color the film wrote */
  col?: string;
  /** its exact ink box, equation units */
  b: [number, number, number, number];
};
export type Equation = {
  v: number; key: string; tex: string; display: boolean; mathjax: string;
  /** the box MathJax laid out (spacing included), its baseline and the union of the ink */
  w: number; h: number; base: number; ink: [number, number, number, number];
  glyphs: MGlyph[];
  atlas?: Record<string, {d: string; adv: number}>;
};
export type Placement = {x: number; y: number; s: number};

/** One glyph as drawn on one frame. `m` maps its outline to frame px. */
export type GDraw = {
  id: string;
  d: string;
  m: Mat6;
  /** fill opacity 0..1 */
  fill: number;
  /** how much of its outline is drawn 0..1, and that outline's opacity */
  stroke: number;
  strokeOp: number;
  /** 0..1 toward the accent colour */
  accent: number;
};

const clamp01 = (x: number) => (x > 0 ? (x < 1 ? x : 1) : 0);
export const segOf = (t: number, a: number, b: number) => clamp01((t - a) / Math.max(1e-9, b - a));
/** Manim's `smooth`: a sigmoid-like in-out with zero speed at both ends. Cubic in-out is the house equivalent. */
export const smooth = (t: number) => {
  const x = clamp01(t);
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
};
export const thereAndBack = (t: number) => Math.sin(Math.PI * clamp01(t));

export const mul = (m: Mat6, n: Mat6): Mat6 => [
  m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
  m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
  m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5],
];
export const lerpMat = (a: Mat6, b: Mat6, u: number): Mat6 =>
  a.map((v, i) => v + (b[i] - v) * u) as Mat6;
const placeMat = (pl: Placement): Mat6 => [pl.s, 0, 0, pl.s, pl.x, pl.y];
/** A glyph's matrix onto the frame. */
export const screenMat = (g: MGlyph, pl: Placement): Mat6 => mul(placeMat(pl), g.m);
/** A glyph's ink box on the frame, px. */
export const screenBox = (g: MGlyph, pl: Placement): [number, number, number, number] =>
  [pl.x + g.b[0] * pl.s, pl.y + g.b[1] * pl.s, pl.x + g.b[2] * pl.s, pl.y + g.b[3] * pl.s];
/** Scale a matrix by `f` about the frame point (cx, cy). */
export const scaleAbout = (m: Mat6, f: number, cx: number, cy: number): Mat6 =>
  mul([f, 0, 0, f, cx - f * cx, cy - f * cy], m);
const translate = (m: Mat6, dx: number, dy: number): Mat6 => [m[0], m[1], m[2], m[3], m[4] + dx, m[5] + dy];

/** The innermost \class of a glyph that is not a live-number slot (those are addressed separately). */
const groupOf = (g: MGlyph): string | null => {
  for (let i = g.k.length - 1; i >= 0; i--) if (!/^live/.test(g.k[i])) return g.k[i];
  return null;
};
/** Glyphs under \class{cls} (at any depth), in typeset order. */
export const glyphsOf = (eq: Equation, cls: string): number[] =>
  eq.glyphs.map((g, i) => (g.k.includes(cls) ? i : -1)).filter((i) => i >= 0);
export const classesOf = (eq: Equation): string[] => {
  const s = new Set<string>();
  eq.glyphs.forEach((g) => g.k.forEach((k) => s.add(k)));
  return Array.from(s);
};
/** The union ink box of some glyphs, frame px. */
export const unionBox = (eq: Equation, idx: number[], pl: Placement): [number, number, number, number] | null => {
  if (!idx.length) return null;
  return idx.map((i) => screenBox(eq.glyphs[i], pl)).reduce((a, b) =>
    [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])]);
};

// ── MATCHING (TransformMatchingTex) ───────────────────────────────────────────────────────────────────────────────
export type Pair = {a: number; b: number; kind: 'stay' | 'move'};
export type Match = {pairs: Pair[]; out: number[]; in: number[]};

/**
 * Pair the glyphs of A with the glyphs of B that are the SAME mark: same character (or the same kind of rule), and —
 * where the film wrote \class{name}{…} in both — inside the same named term first.
 *
 *  1. Terms the film named in both forms are matched with each other (an explicit "this is the same thing").
 *  2. What is left is aligned in reading order: the longest run of shared marks, ties broken by the smaller travel,
 *     so `x^2 + 2x` → `x(x + 2)` keeps the x that stays put rather than the one across the expression. These STAY:
 *     they slide straight to their new place.
 *  3. Shared marks left over after that changed ORDER (the b in `a + b = c` → `a = c - b`) are paired in order of
 *     appearance. Any pair — from any phase — whose left-to-right order flips against another pair MOVES on an arc,
 *     so it passes over or under the marks that stay instead of through them.
 *  4. Anything else leaves (A) or arrives (B).
 * Deterministic: the same two equations always match the same way.
 */
export const matchGlyphs = (A: Equation, B: Equation, pa?: Placement, pb?: Placement): Match => {
  const usedA = new Set<number>(), usedB = new Set<number>();
  const pairs: Pair[] = [];
  // Travel is measured WHERE THE GLYPHS WILL BE DRAWN when the placements are known: aligned on their relation sign,
  // two forms' "=" sit on one vertical and must read as the mark that stays, however far it is from either end of
  // its own expression. Without placements, as a share of each form's own width.
  const span = pa && pb ? Math.max(A.w * pa.s, B.w * pb.s, 1) : 0;
  const pos = (eq: Equation, i: number, pl?: Placement): [number, number] => {
    const g = eq.glyphs[i];
    const x = (g.b[0] + g.b[2]) / 2, y = (g.b[1] + g.b[3]) / 2;
    return pl && span ? [(pl.x + x * pl.s) / span, (pl.y + y * pl.s) / span] : [x / Math.max(1, eq.w), y / Math.max(1, eq.h)];
  };
  const cx = (eq: Equation, i: number) => pos(eq, i, eq === A ? pa : pb)[0];
  const cy = (eq: Equation, i: number) => pos(eq, i, eq === A ? pa : pb)[1];
  // Two DIFFERENT named terms never trade glyphs: the square's exponent 2 must not fly into the 2 of a "±2" the film
  // named as another term — a shared character is not a shared meaning. Unnamed glyphs match anything of their mark.
  const same = (ia: number, ib: number) => {
    const ga = A.glyphs[ia], gb = B.glyphs[ib];
    if (ga.c !== gb.c) return false;
    const ka = groupOf(ga), kb = groupOf(gb);
    return !(ka && kb && ka !== kb);
  };
  const align = (as: number[], bs: number[], kind: Pair['kind']) => {
    const n = as.length, m = bs.length;
    if (!n || !m) return;
    // score = matches × 1000 − travel (normalised), maximised: as many shared marks as possible, then the closest
    const S: number[][] = Array.from({length: n + 1}, () => new Array(m + 1).fill(0));
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        let best = Math.max(S[i + 1][j], S[i][j + 1]);
        if (same(as[i], bs[j])) {
          const dist = Math.hypot(cx(A, as[i]) - cx(B, bs[j]), 0.5 * (cy(A, as[i]) - cy(B, bs[j])));
          best = Math.max(best, 1000 - Math.min(999, dist * 100) + S[i + 1][j + 1]);
        }
        S[i][j] = best;
      }
    }
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (same(as[i], bs[j])) {
        const dist = Math.hypot(cx(A, as[i]) - cx(B, bs[j]), 0.5 * (cy(A, as[i]) - cy(B, bs[j])));
        const take = 1000 - Math.min(999, dist * 100) + S[i + 1][j + 1];
        if (Math.abs(take - S[i][j]) < 1e-9) {
          pairs.push({a: as[i], b: bs[j], kind});
          usedA.add(as[i]); usedB.add(bs[j]);
          i++; j++;
          continue;
        }
      }
      if (S[i + 1][j] >= S[i][j + 1]) i++; else j++;
    }
  };
  // 1. named terms, matched as terms
  const groupsA = new Map<string, number[]>(), groupsB = new Map<string, number[]>();
  A.glyphs.forEach((g, i) => { const k = groupOf(g); if (k) groupsA.set(k, [...(groupsA.get(k) ?? []), i]); });
  B.glyphs.forEach((g, i) => { const k = groupOf(g); if (k) groupsB.set(k, [...(groupsB.get(k) ?? []), i]); });
  Array.from(groupsA.keys()).sort().forEach((k) => {
    const gb = groupsB.get(k);
    if (gb) align(groupsA.get(k)!, gb, 'stay');
  });
  // 2. the rest, in reading order
  const restA = A.glyphs.map((_, i) => i).filter((i) => !usedA.has(i));
  const restB = B.glyphs.map((_, i) => i).filter((i) => !usedB.has(i));
  align(restA, restB, 'stay');
  // 3. same marks that changed order
  const leftA = A.glyphs.map((_, i) => i).filter((i) => !usedA.has(i));
  const leftB = B.glyphs.map((_, i) => i).filter((i) => !usedB.has(i));
  for (const ia of leftA) {
    const jb = leftB.find((j) => !usedB.has(j) && same(ia, j));
    if (jb === undefined) continue;
    pairs.push({a: ia, b: jb, kind: 'stay'});       // its kind is decided below, by whether it crosses another
    usedA.add(ia); usedB.add(jb);
  }
  // WHO TRAVELS ON AN ARC is decided by the GEOMETRY, not by which phase found the pair: a term the film named in
  // both forms (\class{b}{b} in `a + b = c` → `a = c − b`) is matched as a term and still changes sides. Two pairs
  // whose left-to-right order flips between the forms would pass THROUGH each other on straight lines; of the two,
  // the one that travels further takes the arc, so the mark that barely moves stays on the baseline.
  const dxs = pairs.map((pr) => cx(B, pr.b) - cx(A, pr.a));
  pairs.forEach((pr, i) => {
    for (let j = 0; j < pairs.length; j++) {
      if (j === i) continue;
      const qa = pairs[j];
      const flips = (cx(A, pr.a) - cx(A, qa.a)) * (cx(B, pr.b) - cx(B, qa.b)) < 0;
      if (flips && Math.abs(dxs[i]) >= Math.abs(dxs[j])) { pr.kind = 'move'; break; }
    }
  });
  return {
    pairs: pairs.sort((p, q) => p.b - q.b),
    out: A.glyphs.map((_, i) => i).filter((i) => !usedA.has(i)),
    in: B.glyphs.map((_, i) => i).filter((i) => !usedB.has(i)),
  };
};

// ── LAYOUT ───────────────────────────────────────────────────────────────────────────────────────────────────────
const EQUALS = '3D';
/** The x (equation units) of an equation's first top-level relation sign, the pivot a derivation is aligned on. */
export const pivotX = (eq: Equation): number | null => {
  const g = eq.glyphs.find((gg) => gg.c === EQUALS || gg.c === '2248' || gg.c === '2264' || gg.c === '2265');
  return g ? (g.b[0] + g.b[2]) / 2 : null;
};

/**
 * Place a set of equations (the forms of one derivation) in a box: ONE scale for all of them, so a glyph that travels
 * keeps its size unless the TeX changes it; ONE baseline, so the eye does not hop between forms; and, when every form
 * has a relation sign and the box allows it, the relation signs on one vertical — the way a derivation is set on paper.
 * The scale is the authored em size, reduced until the widest and tallest form fits: measured from the INK the
 * typesetter computed, never from a character count.
 */
export const placeAll = (eqs: Equation[], box: {x: number; y: number; w: number; h: number}, emPx: number,
  align: 'center' | 'equals' | 'left' = 'equals'): {pl: Placement[]; s: number; aligned: boolean} => {
  if (!eqs.length) return {pl: [], s: 0, aligned: false};
  const maxW = Math.max(...eqs.map((e) => e.ink[2] - e.ink[0]));
  const asc = Math.max(...eqs.map((e) => e.base - e.ink[1]));
  const desc = Math.max(...eqs.map((e) => e.ink[3] - e.base));
  let s = Math.min(emPx / 1000, box.w / Math.max(1, maxW), box.h / Math.max(1, asc + desc));
  if (!(s > 0)) throw new Error('mathCore.placeAll: the box has no room for the equation');
  const baseY = box.y + (box.h - (asc + desc) * s) / 2 + asc * s;
  const centred = (e: Equation) => box.x + (box.w - (e.ink[2] - e.ink[0]) * s) / 2 - e.ink[0] * s;
  const left = (e: Equation) => box.x - e.ink[0] * s;
  let xs = eqs.map(align === 'left' ? left : centred);
  let aligned = false;
  if (align === 'equals' && eqs.length > 1) {
    const piv = eqs.map(pivotX);
    if (piv.every((p) => p !== null)) {
      // the pivot's frame x must keep every form inside the box: an interval per form, intersected
      let lo = -Infinity, hi = Infinity;
      eqs.forEach((e, i) => {
        lo = Math.max(lo, box.x + (piv[i]! - e.ink[0]) * s);
        hi = Math.min(hi, box.x + box.w - (e.ink[2] - piv[i]!) * s);
      });
      if (lo <= hi + 1e-6) {
        const mid = box.x + box.w / 2;
        const X = Math.max(lo, Math.min(hi, mid));
        xs = eqs.map((_, i) => X - piv[i]! * s);
        aligned = true;
      }
    }
  }
  return {pl: eqs.map((e, i) => ({x: xs[i], y: baseY - e.base * s, s})), s, aligned};
};

// ── STATES ───────────────────────────────────────────────────────────────────────────────────────────────────────
const still = (eq: Equation, pl: Placement, tag: string): GDraw[] => eq.glyphs.map((g, i) => ({
  id: `${tag}${i}`, d: g.d, m: screenMat(g, pl), fill: 1, stroke: 0, strokeOp: 0, accent: g.col ? 1 : 0,
}));
export const stillState = still;

/**
 * Write (DrawBorderThenFill, staggered): each glyph's outline draws on, its fill rises under it, and the outline goes
 * once the fill holds — so the settled frame is the plain typeset equation, not an outlined one. `lag` is the share of
 * the window the stagger spreads over (Manim's lag_ratio, as a fraction of the whole).
 */
export const writeState = (eq: Equation, pl: Placement, p: number, lag = 0.55, tag = 'w'): GDraw[] => {
  const n = eq.glyphs.length;
  const dur = Math.max(0.05, 1 - lag);
  return eq.glyphs.map((g, i) => {
    const a = n > 1 ? (lag * i) / (n - 1) : 0;
    const u = segOf(p, a, a + dur);
    return {id: `${tag}${i}`, d: g.d, m: screenMat(g, pl), stroke: smooth(segOf(u, 0, 0.6)),
      fill: smooth(segOf(u, 0.35, 0.9)), strokeOp: u <= 0 ? 0 : 1 - segOf(u, 0.78, 1), accent: g.col ? 1 : 0};
  });
};

/**
 * TransformMatchingTex at progress p. Leaving glyphs shrink and fade over the first 65%, arriving glyphs grow over the
 * last 65% (opacity linear, scale smooth), shared glyphs travel through the middle with a small stagger in their new reading order (LaggedStart). The
 * windows overlap on purpose: measured on the first renders, disjoint halves — and then smooth-eased fades, whose long
 * tails are as good as disjoint (0.3% and 1% opacity at p = 0.5) — left a mid-transform frame holding only the
 * travellers — "x +  2  = 0" — which reads as an equation with holes in it, not as one turning into another. A shared glyph whose outline differs (a parenthesis at another size)
 * is stretched from one box into the other while the two outlines cross-fade.
 */
export const transformState = (A: Equation, pa: Placement, B: Equation, pb: Placement, match: Match, p: number,
  opts: {arc?: number} = {}): GDraw[] => {
  const out: GDraw[] = [];
  const arcK = opts.arc ?? 0.35;
  const nP = Math.max(1, match.pairs.length);
  match.out.forEach((ia) => {
    // opacity runs LINEARLY (Manim's FadeOut under a transform is visible for most of it); the shrink is smooth
    const g = A.glyphs[ia], v = segOf(p, 0, 0.65), u = smooth(v);
    const bx = screenBox(g, pa), cxp = (bx[0] + bx[2]) / 2, cyp = (bx[1] + bx[3]) / 2;
    out.push({id: `a${ia}`, d: g.d, m: scaleAbout(screenMat(g, pa), 1 - 0.45 * u, cxp, cyp), fill: 1 - v, stroke: 0,
      strokeOp: 0, accent: g.col ? 1 : 0});
  });
  match.pairs.forEach((pr, rank) => {
    const ga = A.glyphs[pr.a], gb = B.glyphs[pr.b];
    const lag = 0.14 * (rank / nP);
    const u = smooth(segOf(p, 0.12 + lag, 0.78 + lag));
    const ma = screenMat(ga, pa), mb = screenMat(gb, pb);
    const ba = screenBox(ga, pa), bb = screenBox(gb, pb);
    let dy = 0;
    if (pr.kind === 'move') {
      // over when travelling right, under when travelling left: two marks that swap places pass each other
      const dx = (bb[0] + bb[2]) / 2 - (ba[0] + ba[2]) / 2;
      const hgt = Math.max(ba[3] - ba[1], bb[3] - bb[1]);
      dy = -Math.sign(dx || 1) * Math.min(Math.abs(dx) * arcK, hgt * 0.9) * Math.sin(Math.PI * u);
    }
    const accent = (ga.col ? 1 : 0) * (1 - u) + (gb.col ? 1 : 0) * u;
    if (ga.d === gb.d) {
      out.push({id: `p${pr.a}_${pr.b}`, d: ga.d, m: translate(lerpMat(ma, mb, u), 0, dy), fill: 1, stroke: 0,
        strokeOp: 0, accent});
      return;
    }
    // different outlines under one mark: fit each into the other's box and cross-fade through the middle
    const fit = (from: number[], to: number[]): Mat6 => {
      const sx = (to[2] - to[0]) / Math.max(1e-6, from[2] - from[0]);
      const sy = (to[3] - to[1]) / Math.max(1e-6, from[3] - from[1]);
      return [sx, 0, 0, sy, to[0] - from[0] * sx, to[1] - from[1] * sy];
    };
    const v = smooth(segOf(u, 0.25, 0.75));
    out.push({id: `p${pr.a}_${pr.b}A`, d: ga.d, m: translate(lerpMat(ma, mul(fit(ba, bb), ma), u), 0, dy),
      fill: 1 - v, stroke: 0, strokeOp: 0, accent});
    out.push({id: `p${pr.a}_${pr.b}B`, d: gb.d, m: translate(lerpMat(mul(fit(bb, ba), mb), mb, u), 0, dy),
      fill: v, stroke: 0, strokeOp: 0, accent});
  });
  match.in.forEach((ib) => {
    const g = B.glyphs[ib], v = segOf(p, 0.35, 1), u = smooth(v);
    const bx = screenBox(g, pb), cxp = (bx[0] + bx[2]) / 2, cyp = (bx[1] + bx[3]) / 2;
    out.push({id: `b${ib}`, d: g.d, m: scaleAbout(screenMat(g, pb), 0.55 + 0.45 * u, cxp, cyp), fill: v, stroke: 0,
      strokeOp: 0, accent: g.col ? 1 : 0});
  });
  return out;
};

/**
 * Indicate: the glyphs of a term swell about the term's centre and take the accent, then settle back to size. With
 * `hold` the accent stays once the pulse is over — the term is now the one the narration is talking about.
 */
export const indicate = (draws: GDraw[], ids: Set<string>, box: [number, number, number, number], p: number,
  scaleMax = 1.16, hold = true): GDraw[] => {
  if (p <= 0) return draws;
  const f = 1 + (scaleMax - 1) * thereAndBack(p);
  const cx = (box[0] + box[2]) / 2, cy = (box[1] + box[3]) / 2;
  const tint = hold ? smooth(segOf(p, 0, 0.35)) : thereAndBack(p);
  return draws.map((d) => (ids.has(d.id) ? {...d, m: scaleAbout(d.m, f, cx, cy), accent: Math.max(d.accent, tint)} : d));
};

// ── LIVE NUMBER (ValueTracker) ──────────────────────────────────────────────────────────────────────────────────
/** One number, as the film wrote it. Exactly one number with optional sign and decimals — anything else is refused. */
export const parseLive = (s: string): {num: number; decimals: number; text: string} => {
  const text = String(s ?? '').trim().replace(/^-/, '−');
  const m = /^(−?)(\d+)(?:\.(\d+))?$/.exec(text);
  if (!m) throw new Error(`a live number is one plain number like "0.87" or "−12.5", got ${JSON.stringify(s)}`);
  const v = parseFloat(`${m[1] ? '-' : ''}${m[2]}.${m[3] ?? '0'}`);
  return {num: v, decimals: m[3] ? m[3].length : 0, text};
};

/** The text a live number shows at progress p: the film's `from` at 0, its `to` at 1, exactly; between, the
 *  value at that point printed with `to`'s decimals. */
export const liveText = (from: string, to: string, p: number): string => {
  const a = parseLive(from), b = parseLive(to);
  if (p <= 0) return a.text;
  if (p >= 1) return b.text;
  const v = a.num + (b.num - a.num) * p;
  const dec = b.decimals;
  const abs = Math.abs(v).toFixed(dec);
  return (v < 0 && Number(abs) !== 0 ? '−' : '') + abs;
};

/**
 * The glyphs that draw `text` in the slot \class{cls}{template} of `eq`, from the font atlas the typesetter shipped with
 * the equation: the template's size and baseline, decimal points on one vertical (or right edges, when either side has
 * no point) — so the digits never shuffle sideways as the value runs. Refuses a value that would not fit the room the
 * template reserved: the film writes the template as wide as its widest value.
 */
export const liveDraws = (eq: Equation, pl: Placement, cls: string, text: string, tag = 'L'): GDraw[] => {
  const idx = glyphsOf(eq, cls);
  if (!idx.length) throw new Error(`no \\class{${cls}}{…} slot in "${eq.tex}" for the live number`);
  if (!eq.atlas) throw new Error(`"${eq.tex}" was typeset without a digit atlas — its live slot must be named live…`);
  const at = eq.atlas;
  const tg = idx.map((i) => eq.glyphs[i]);
  const s = Math.abs(tg[0].m[0]);
  const baseY = tg[0].m[5];
  const chOf = (c: string) => String.fromCodePoint(parseInt(c, 16));
  const tChars = tg.map((g) => chOf(g.c));
  tChars.forEach((ch) => {
    if (!at[ch]) throw new Error(`the live slot \\class{${cls}} holds ${JSON.stringify(ch)}; write the template as digits`);
  });
  const pens = tg.map((g) => g.m[4]);
  const tEnd = pens[pens.length - 1] + at[tChars[tChars.length - 1]].adv * s;
  const chars = Array.from(text);
  chars.forEach((ch) => { if (!at[ch]) throw new Error(`the live number ${JSON.stringify(text)} holds ${JSON.stringify(ch)}`); });
  const advs = chars.map((ch) => at[ch].adv * s);
  const width = advs.reduce((a, b) => a + b, 0);
  const tDot = tChars.indexOf('.'), vDot = chars.indexOf('.');
  let x0: number;
  if (tDot >= 0 && vDot >= 0) x0 = pens[tDot] - advs.slice(0, vDot).reduce((a, b) => a + b, 0);
  else x0 = tEnd - width;
  const room = tEnd - pens[0];
  if (x0 < pens[0] - 0.5 * at['0'].adv * s - 1e-6 || x0 + width > tEnd + 0.5 * at['0'].adv * s + 1e-6) {
    throw new Error(`the live number ${JSON.stringify(text)} is wider than its slot \\class{${cls}}{${tChars.join('')}} ` +
      `(${(width / s).toFixed(0)} vs ${(room / s).toFixed(0)} units) — write the template as wide as the widest value`);
  }
  let x = x0;
  return chars.map((ch, i) => {
    const m: Mat6 = mul(placeMat(pl), [s, 0, 0, s, x, baseY]);
    x += advs[i];
    return {id: `${tag}${i}`, d: at[ch].d, m, fill: 1, stroke: 0, strokeOp: 0, accent: 1};
  });
};
