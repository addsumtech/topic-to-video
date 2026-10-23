// KINETIC TYPE — THE PURE HALF. Everything here is a function of numbers and strings: no DOM, no React, no font.
// runtime/kinetic.tsx draws with it; tests run it in node (tests/_tsprobe.py) without a browser.
//
// THE MODEL IS AFTER EFFECTS', not a tween library's. A text animator in AE is ONE selector that assigns every unit
// (character, word, line) a coverage in [0, 1], and that one number drives every property at once — position,
// scale, opacity, blur, tracking, colour. Skia's Skottie implements the same semantics
// (modules/skottie/src/text/RangeSelector.cpp: based-on chars/words/lines, start/end/offset, shapes square / ramp /
// triangle / round / smooth, ease high/low, amount, a seeded randomise). A per-property tween list cannot express
// "a ramp three letters wide sweeping left to right"; a coverage can, and so can a plain stagger, which is the
// special case most launch sites use (Linear: lines, 33 ms apart; Framer: characters, 50 ms apart; GSAP SplitText:
// 0.04 / 0.15 / 0.25 s for chars / words / lines — references/motion-research.md §1).
//
// `c = 1` means "fully at the animator's FROM state", `c = 0` means "at rest". A reveal runs c from 1 to 0.
import {hash01} from './motion';
import READING from './readingSpec.json';

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

// ── the clock ────────────────────────────────────────────────────────────────────────────────────────────
// useT's mapping, as a pure function of (frame, scene length), for code that must reason about the WHOLE clip at
// once — the hold report walks every frame the hook would see. useT itself is not rewritten to call this: every
// register's measured row hashes the source of the symbols it reaches, and touching useT's body would re-key all
// two hundred of them for a change that is not a change. `tests/test_kinetic.py` pins this copy to
// render_remotion.frame_at_t (the Python mirror of the same clock) instead.
export const SEAM_FRAMES_K = 12;   // runtime/motion SEAM_FRAMES (the test reads both)
export const ENTRY_T_K = 0.06;     // runtime/motion ENTRY_T
export const tAtFrame = (frame: number, dur: number): number => {
  const pad = Math.min(SEAM_FRAMES_K, Math.floor(Math.max(0, dur - 1) / 3));
  const span = Math.max(1, dur - 1 - 2 * pad);
  return ENTRY_T_K + (1 - ENTRY_T_K) * clamp01((frame - pad) / span);
};
/** Seconds of the shot's own motion span → its t, and back. `spanF` is useAnimSpan(). */
export const secToT = (s: number, spanF: number, fps: number) => ((1 - ENTRY_T_K) * s * fps) / Math.max(1, spanF);
export const tToSec = (t: number, spanF: number, fps: number) =>
  ((t - ENTRY_T_K) / (1 - ENTRY_T_K)) * (Math.max(1, spanF) / fps);

// ── easing ───────────────────────────────────────────────────────────────────────────────────────────────
/** A CSS cubic-bezier(x1, y1, x2, y2) as a function of progress, solved for x the way a browser does (Newton,
 *  then bisection) — so `ease` here is the curve linear.app's hero actually runs, not a look-alike. */
export const cubicBezier = (x1: number, y1: number, x2: number, y2: number) => {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = (u: number) => ((ax * u + bx) * u + cx) * u;
  const sy = (u: number) => ((ay * u + by) * u + cy) * u;
  const dx = (u: number) => (3 * ax * u + 2 * bx) * u + cx;
  return (x: number): number => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let u = x;
    for (let k = 0; k < 8; k++) {
      const e = sx(u) - x;
      if (Math.abs(e) < 1e-7) return sy(u);
      const d = dx(u);
      if (Math.abs(d) < 1e-6) break;
      u -= e / d;
    }
    let lo = 0, hi = 1;
    u = x;
    for (let k = 0; k < 40; k++) {
      const v = sx(u);
      if (Math.abs(v - x) < 1e-7) break;
      if (v < x) lo = u; else hi = u;
      u = (lo + hi) / 2;
    }
    return sy(u);
  };
};

// Each named curve is one somebody measured or published (references/motion-research.md §1), not a taste.
export const EASES = {
  linear: (x: number) => clamp01(x),
  ease: cubicBezier(0.25, 0.1, 0.25, 1),       // CSS `ease` — linear.app's line reveal
  stripe: cubicBezier(0.33, 1, 0.68, 1),       // stripe.com's digit roller
  expo: (x: number) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp01(x))),   // GSAP expo.out — the mask reveal
  power3: (x: number) => 1 - Math.pow(1 - clamp01(x), 4),                  // GSAP power3.out
  power4: (x: number) => 1 - Math.pow(1 - clamp01(x), 5),                  // GSAP power4.out
  back: (x: number) => { const c1 = 1.70158, c3 = c1 + 1, u = clamp01(x) - 1; return 1 + c3 * u * u * u + c1 * u * u; },
  inOut: (x: number) => { const u = clamp01(x); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; },
};
export type EaseName = keyof typeof EASES;
export const easeOf = (e: EaseName | ((x: number) => number) | undefined): ((x: number) => number) => {
  if (typeof e === 'function') return e;
  const f = EASES[(e ?? 'expo') as EaseName];
  if (!f) throw new Error(`kinetic: unknown ease "${String(e)}" — one of ${Object.keys(EASES).join(', ')}.`);
  return f;
};

// ── segmentation ─────────────────────────────────────────────────────────────────────────────────────────
// Intl.Segmenter, never `split('')`: a grapheme is what a reader sees as one character (an accented letter in NFD,
// an emoji family, a Devanagari cluster), and Chinese and Japanese have no spaces to split words on — the segmenter
// does word segmentation for them (measured: 我们|今天|讨论|运动|图形|设计).
type Seg = {segment: string; index: number; isWordLike?: boolean};
const segmenter = (lang: string, granularity: 'grapheme' | 'word'): {segment: (s: string) => Iterable<Seg>} => {
  const S = (Intl as unknown as {Segmenter?: new (l: string, o: {granularity: string}) => {segment: (s: string) => Iterable<Seg>}}).Segmenter;
  if (!S) throw new Error('kinetic: this engine has no Intl.Segmenter; graphemes and CJK words cannot be found.');
  return new S(lang, {granularity});
};
export const graphemes = (s: string): string[] => Array.from(segmenter('und', 'grapheme').segment(s), (g) => g.segment);

const HAN = /\p{Script=Han}/u, KANA = /[\p{Script=Hiragana}\p{Script=Katakana}]/u, HANGUL = /\p{Script=Hangul}/u;
/** The locale to segment and lay out `s` in, when the caller did not say: kana → ja, Hangul → ko, Han → zh. */
export const langOf = (s: string): string =>
  KANA.test(s) ? 'ja' : HANGUL.test(s) ? 'ko' : HAN.test(s) ? 'zh' : 'en';

/** For each grapheme of `s`, the index of the WORD it belongs to. Spaces and punctuation join the word before them
 *  (so "model." animates as one unit), or the word after when nothing comes before. Also returns the count. */
export const wordIds = (s: string, lang: string): {ids: number[]; count: number} => {
  const gs = Array.from(segmenter('und', 'grapheme').segment(s));
  const ws = Array.from(segmenter(lang, 'word').segment(s));
  const wordAt = new Array<number>(s.length).fill(-1);
  let n = 0;
  for (const w of ws) {
    if (!w.isWordLike) continue;
    for (let k = 0; k < w.segment.length; k++) wordAt[w.index + k] = n;
    n += 1;
  }
  const ids = gs.map((g) => wordAt[g.index]);
  let last = -1;
  for (let i = 0; i < ids.length; i++) { if (ids[i] >= 0) last = ids[i]; else if (last >= 0) ids[i] = last; }
  for (let i = ids.length - 1; i >= 0; i--) { if (ids[i] < 0) ids[i] = i + 1 < ids.length ? ids[i + 1] : 0; }
  return {ids: ids.map((v) => Math.max(0, v)), count: Math.max(1, n)};
};

/** How many words a reader reads in `s` (Intl.Segmenter word-like segments) — the unit of the must-read bar. */
export const wordCount = (s: string, lang?: string): number =>
  Array.from(segmenter(lang ?? langOf(s), 'word').segment(s)).filter((w) => w.isWordLike).length;

// ── emphasis runs ────────────────────────────────────────────────────────────────────────────────────────
/** `*…*` marks an emphasised run INSIDE the film's own string, so the emphasis is the film's claim, never chosen by
 *  index. `\*` is a literal asterisk. An unclosed `*` is refused: it would silently emphasise to the end of the line. */
export type Run = {text: string; emph: boolean};
export const parseRuns = (s: string): Run[] => {
  const out: Run[] = [];
  let cur = '', emph = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === '\\' && s[i + 1] === '*') { cur += '*'; i += 1; continue; }
    if (c === '*') {
      if (cur) out.push({text: cur, emph});
      cur = '';
      emph = !emph;
      continue;
    }
    cur += c;
  }
  if (emph) throw new Error(`kinetic: "${s}" opens an emphasis with * and never closes it.`);
  if (cur) out.push({text: cur, emph});
  return out;
};
export const plainText = (s: string): string => parseRuns(s).map((r) => r.text).join('');

// ── the range selector (After Effects / Skottie semantics) ──────────────────────────────────────────────
export type RangeShape = 'square' | 'rampUp' | 'rampDown' | 'triangle' | 'round' | 'smooth';
export type RangeSelector = {
  /** start / end of the selected range and an offset added to both, as FRACTIONS of the unit count (AE's % / 100) */
  start?: number; end?: number; offset?: number;
  shape?: RangeShape;
  /** AE's ease high / low, -100..100. Positive values flatten the ramp's approach to 1 / to 0. (Negative values
   *  are read as 0 here — AE overshoots with them, which this library does not want inside a reading line.) */
  easeHigh?: number; easeLow?: number;
  /** AE's amount, -1..1 (its % / 100): scales the coverage */
  amount?: number;
  /** shuffle the units first, with a seed — deterministic, like Skottie's seed */
  randomize?: boolean; seed?: number;
};

/** A seeded permutation: `rank[i]` is where unit i lands. */
export const permutation = (n: number, seed = 1): number[] => {
  const keys = Array.from({length: n}, (_, i) => ({i, k: hash01(seed * 7919 + i * 104.729)}));
  keys.sort((a, b) => a.k - b.k || a.i - b.i);
  const rank = new Array<number>(n);
  keys.forEach((o, r) => { rank[o.i] = r; });
  return rank;
};

/** Coverage in [-1, 1] of unit `pos` (0-based, AFTER any randomise) of `n`, by `sel`.
 *  Square uses the share of the unit's own span inside the range, so a range edge crossing a unit fades it rather
 *  than snapping it; the shaped kinds sample the unit's mid-point, as Skottie does. */
export const rangeCoverage = (sel: RangeSelector, pos: number, n: number): number => {
  const N = Math.max(1, n);
  const off = sel.offset ?? 0;
  const s = (sel.start ?? 0) + off, e = (sel.end ?? 1) + off;
  const lo = Math.min(s, e), hi = Math.max(s, e);
  const a = pos / N, b = (pos + 1) / N, mid = (a + b) / 2;
  const eL = clamp01((sel.easeLow ?? 0) / 100), eH = clamp01((sel.easeHigh ?? 0) / 100);
  const shapeEase = eL === 0 && eH === 0 ? (x: number) => x : cubicBezier(eL, 0, 1 - eH, 1);
  const shape = sel.shape ?? 'square';
  let v: number;
  if (shape === 'square') {
    v = Math.max(0, Math.min(b, hi) - Math.max(a, lo)) / (b - a);
  } else {
    const w = hi - lo;
    const p = w > 1e-9 ? (mid - lo) / w : (mid < lo ? -Infinity : Infinity);
    if (shape === 'rampUp') v = p <= 0 ? 0 : p >= 1 ? 1 : shapeEase(p);
    else if (shape === 'rampDown') v = p <= 0 ? 1 : p >= 1 ? 0 : 1 - shapeEase(p);
    else if (p < 0 || p > 1) v = 0;
    else if (shape === 'triangle') v = shapeEase(1 - Math.abs(2 * p - 1));
    else if (shape === 'round') v = shapeEase(Math.sqrt(Math.max(0, 1 - (2 * p - 1) * (2 * p - 1))));
    else v = shapeEase(0.5 - 0.5 * Math.cos(2 * Math.PI * p));
  }
  return v * Math.max(-1, Math.min(1, sel.amount ?? 1));
};

// ── stagger ──────────────────────────────────────────────────────────────────────────────────────────────
export type Order = 'forward' | 'reverse' | 'center' | 'edges' | 'random';
/** The unit's place in the sweep (0 = first to move). center/edges give two units the same place, which is the
 *  point: they move together. */
export const orderRank = (i: number, n: number, order: Order = 'forward', seed = 1): number => {
  const mid = (n - 1) / 2;
  switch (order) {
    case 'reverse': return n - 1 - i;
    case 'center': return Math.abs(i - mid);
    case 'edges': return mid - Math.abs(i - mid);
    case 'random': return permutation(n, seed)[i];
    default: return i;
  }
};

// ── swaps ────────────────────────────────────────────────────────────────────────────────────────────────
/** When each alternative takes the slot, in t: alternative 0 is there from the start; 1..n-1 arrive at evenly
 *  spaced times from `first` to `last`. A cue may only bring one EARLIER (runtime/cue's rule), never later, and the
 *  order is kept: an arrival is never before the one it replaces. */
export const swapTimes = (n: number, first: number, last: number, cued?: (number | null)[],
                          times?: number[]): number[] => {
  const out = [0];
  for (let k = 1; k < n; k++) {
    const even = times && Number.isFinite(times[k]) ? times[k]
      : n <= 2 ? first : first + ((k - 1) * (last - first)) / (n - 2);
    const c = cued?.[k];
    out.push(typeof c === 'number' && Number.isFinite(c) ? Math.min(even, c) : even);
  }
  for (let k = 2; k < n; k++) out[k] = Math.max(out[k], out[k - 1]);
  return out;
};

/** A deterministic stand-in glyph for a scramble: drawn from `pool`, changing every `step` (frames / 2, "on twos"). */
export const scrambleChar = (pool: string[], seed: number, i: number, step: number): string =>
  pool.length ? pool[Math.floor(hash01(seed * 1013 + i * 37.7 + step * 3.31) * pool.length) % pool.length] : '';

// ── reading ──────────────────────────────────────────────────────────────────────────────────────────────
/** How long `text` takes to read, from the one table the gate also reads (runtime/readingSpec.json): `once` at the
 *  published rate for its script (never under the 5/6 s floor), `must` at ~0.6 s a word for copy that must be taken
 *  in. Graphemes are counted without spaces; words by Intl.Segmenter. */
export const readingSeconds = (text: string, lang?: string): {once: number; must: number} => {
  const l = lang ?? langOf(text);
  const cps = l.startsWith('ja') ? READING.cps.ja : l.startsWith('zh') ? READING.cps.zh
    : l.startsWith('ko') ? READING.cps.ko : READING.cps.latin;
  const chars = graphemes(text.replace(/\s+/g, '')).length;
  const once = Math.max(READING.minSeconds, chars / cps);
  return {once, must: Math.max(once, wordCount(text, l) * READING.mustReadSecondsPerWord)};
};

/** The longest run of `true` in `xs` — a line's hold is the longest stretch of frames it is readable for. */
export const longestRun = (xs: boolean[]): number => {
  let best = 0, cur = 0;
  for (const x of xs) { cur = x ? cur + 1 : 0; if (cur > best) best = cur; }
  return best;
};
