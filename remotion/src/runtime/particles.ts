// PARTICLES taken FROM a mark — a word, a drawn shape — that dissolve and re-form as another. Pure
// (tests/test_particles.py); runtime/particlesDom.tsx samples a word's pixels and draws the particles.
//
// The peer library boils a line of type into grain and condenses the cloud into a larger word, bursts a formation
// into a smoke ring and scatters gold dust over a finale. This library's one particle register flew ~140 dots into
// a fixed checkmark. What a viewer reads from a dissolve is CONSERVATION — the same matter, re-formed — so every
// particle starts exactly on the first mark and lands exactly on the second, and the pairing keeps the left of one
// word flowing to the left of the next (a random pairing reads as noise, not as one thing becoming another).
//
// Deterministic: every random choice is a hash of the particle's index and a seed.

export type Pt = {x: number; y: number};
export type Pair = {a: Pt; b: Pt};

/** A frame-stable hash in [0, 1). */
const h01 = (i: number, seed = 0) => {
  let x = Math.imul((i + 1) ^ Math.imul(seed + 0x9e37, 0x85ebca6b), 0xc2b2ae35);
  x ^= x >>> 15; x = Math.imul(x, 0x27d4eb2d); x ^= x >>> 13;
  return ((x >>> 0) % 100000) / 100000;
};

/** Points every `step` px where the mask's alpha is at least `threshold` (row-major, w x h). */
export const sampleMask = (alpha: ArrayLike<number>, w: number, h: number, step: number, threshold = 128): Pt[] => {
  const out: Pt[] = [];
  for (let y = Math.floor(step / 2); y < h; y += step) {
    for (let x = Math.floor(step / 2); x < w; x += step) if (alpha[y * w + x] >= threshold) out.push({x, y});
  }
  return out;
};

/** Exactly `n` points: an evenly strided subset of real points, or every point and then repeats of them. */
export const fitCount = (pts: Pt[], n: number, seed = 1): Pt[] => {
  if (!pts.length || n <= 0) return [];
  if (n <= pts.length) return Array.from({length: n}, (_, i) => pts[Math.floor((i * pts.length) / n)]);
  return Array.from({length: n}, (_, i) => (i < pts.length ? pts[i] : pts[Math.floor(h01(i, seed) * pts.length)]));
};

const order = (p: Pt) => p.x + 0.35 * p.y;

/** The two sets made one size and paired in reading order, so the flow from one mark to the next keeps its sides. */
export const pair = (a: Pt[], b: Pt[], seed = 1): Pair[] => {
  const n = Math.max(a.length, b.length);
  const A = fitCount(a, n, seed).slice().sort((p, q) => order(p) - order(q));
  const B = fitCount(b, n, seed + 1).slice().sort((p, q) => order(p) - order(q));
  return A.map((p, i) => ({a: p, b: B[i]}));
};

const ease = (q: number) => (q < 0.5 ? 4 * q * q * q : 1 - Math.pow(-2 * q + 2, 3) / 2);
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

export type FlowOpts = {
  /** how far (px) a particle drifts off its straight path at the middle of the move */
  scatter?: number;
  /** share of the move over which particles set off in reading order (0 = all at once) */
  stagger?: number;
  seed?: number;
};

/** Particle `i` of `q` at progress p (0 = on the first mark, 1 = on the second, exactly). */
export const particleAt = (q: Pair, i: number, p: number, o: FlowOpts = {}): Pt & {alpha: number} => {
  const scatter = o.scatter ?? 120, stagger = o.stagger ?? 0, seed = o.seed ?? 7;
  const d = stagger * h01(i, seed + 3);
  const e = ease(clamp01((p - d) / Math.max(1e-6, 1 - stagger)));
  if (e <= 0) return {...q.a, alpha: 1};   // exactly on the marks at both ends (sin(pi) is not exactly 0)
  if (e >= 1) return {...q.b, alpha: 1};
  const ang = h01(i, seed) * Math.PI * 2;
  const amp = scatter * (0.35 + 0.65 * h01(i, seed + 1)) * Math.sin(Math.PI * e);
  return {x: q.a.x + (q.b.x - q.a.x) * e + Math.cos(ang) * amp, y: q.a.y + (q.b.y - q.a.y) * e + Math.sin(ang) * amp,
    alpha: 1};
};

export type BurstOpts = {cx: number; cy: number; reach?: number; seed?: number};

/** A mark bursting: each particle flies outward from (cx, cy) — further for the ones further out — and fades. */
export const burstAt = (a: Pt, i: number, p: number, o: BurstOpts): Pt & {alpha: number} => {
  const reach = o.reach ?? 400, seed = o.seed ?? 11;
  const dx = a.x - o.cx, dy = a.y - o.cy, len = Math.hypot(dx, dy) || 1;
  const jitter = (h01(i, seed) - 0.5) * 0.9;
  const ang = Math.atan2(dy, dx) + jitter;
  const out = (1 - Math.pow(1 - clamp01(p), 3)) * reach * (0.45 + 0.55 * h01(i, seed + 1));
  return {x: a.x + Math.cos(ang) * out, y: a.y + Math.sin(ang) * out, alpha: p >= 1 ? 0 : 1 - clamp01(p) ** 1.6};
};
