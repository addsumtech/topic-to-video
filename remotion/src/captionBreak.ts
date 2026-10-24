// WHERE A BURNED CJK CAPTION MAY BREAK — and the lines it breaks into.
//
// A browser breaks Chinese between ANY two characters, so the caption HUD — which let the browser wrap it — cut words
// in half: 「交回成 / 片」, 「GPS 怎么 / 定位」, 「抓下 / 来的原文」 (a 9:16 launch film) and 「…加速电 / 子。」, a word split and
// its last glyph orphaned (a 16:9 science film), both 2026-10-24 benchmarks. A delivery review found the first three;
// no gate could, because nothing looked at a caption's line breaks.
//
// So a CJK caption's lines are decided HERE, deterministically, and drawn as decided:
//   · a break may fall only between two WORDS (Intl.Segmenter, `granularity: 'word'` — its zh dictionary segmentation
//     works in the renderer's Chrome; measured);
//   · never before closing punctuation or after opening punctuation (kinsoku: 。，、！？）」 never start a line,
//     （「 never end one) — punctuation rides with the word it belongs to;
//   · the lines are BALANCED: as few as the greedy fill needs, then the breaks that make the longest line shortest, so
//     the last line is not a scrap.
// Film.tsx draws each line as its own block (a line our width estimate got wrong may still wrap, but only at these
// same word boundaries); scripts/caption_breaks_qa.py runs this same file in node to check a board's captions before
// a render and render_remotion.py breaks out.srt's CJK cues with it. One definition, three callers.
//
// Imported by Film.tsx only — never by a register, so no register's measured manifest depends on it.

import {cjkAdvance, latinAdvance, CAPTION_SIZE_FRAC, CAPTION_LINES} from './runtime/layout';
import {SAFE_CAPTION_SCALE} from './runtime/safeZone';

export const CAP_PAD_X = 60; // the caption block's own side padding, inside its measure (border-box)

/** The caption's type size and the measure its lines wrap in, at this frame — Film.tsx CaptionTrack draws in exactly
 *  this box (moved from there). On a platform-safe film a size larger, and the lines end short of the button column
 *  (runtime/safeZone `right`), centred: a full line of a 1080-wide caption ran to x 960, under the buttons from 929. */
export const captionBox = (width: number, height: number, safe?: {right: number} | null) => {
  const capSize = Math.round(Math.min(width, height) * CAPTION_SIZE_FRAC * (safe ? SAFE_CAPTION_SCALE : 1));
  const capMeasure = Math.min(1600, width - 120,
    safe ? Math.floor(width * (1 - 2 * safe.right)) - 8 + 2 * CAP_PAD_X : Infinity);
  return {capSize, capMeasure, capTextW: capMeasure - 2 * CAP_PAD_X};
};

/** Every chunk a caption is burned as at this frame, and — for a CJK chunk — the lines it is drawn in: what the film
 *  shows, for the gate (scripts/caption_breaks_qa.py) to check. Mirrors CaptionTrack's own calls exactly. */
export const captionPlan = (caption: string, width: number, height: number, safe: {right: number} | null,
                            fontStack?: string, uniform?: boolean, lines: number = CAPTION_LINES) => {
  const {capSize, capTextW} = captionBox(width, height, safe);
  return fitCaption(splitCaption(caption), capSize, capTextW, lines, fontStack, uniform).map((chunk) => {
    const cjkChars = (chunk.match(/[\u3040-\u9fff\uac00-\ud7af]/g) ?? []).length;
    const cjk = cjkChars * 2 >= chunk.length && cjkChars > 0;
    return {chunk, cjk, lines: cjk ? cjkCaptionLines(chunk, capSize, capTextW, fontStack, uniform) : null};
  });
};

const CLOSE = new Set(Array.from('、。，．,.：:；;？?！!）)]｝}」』】〕〉》〗〙〛’”…‥〜～ー々〻ゝゞヽヾぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ・%％'));
const OPEN = new Set(Array.from('（([｛{「『【〔〈《〖〘〚‘“'));

export const isCJKChar = (c: string): boolean => /[㐀-鿿豈-﫿぀-ヿ가-힯]/.test(c);
const isSpace = (c: string) => /\s/.test(c);

type Seg = {segment: string; index: number};
const segmenter = (): {segment: (t: string) => Iterable<Seg>} | null => {
  const S = (Intl as unknown as {Segmenter?: new (l: string, o: {granularity: string}) => {segment: (t: string) => Iterable<Seg>}}).Segmenter;
  return S ? new S('zh', {granularity: 'word'}) : null;
};

/** Is Intl.Segmenter here? Without it every CJK character is its own word (the browser's old behaviour) and the
 *  kinsoku rules still hold — the gate says which it ran on. */
export const hasSegmenter = (): boolean => segmenter() !== null;

/**
 * The places `text` may break, as offsets: a break at k puts text[k] first on the next line. Word starts only (or
 * every CJK character without a segmenter), never in front of closing punctuation, never just after opening
 * punctuation, never inside a run with no space (a Latin word, a number).
 */
export const breakPoints = (text: string): number[] => {
  const starts = new Set<number>();
  const seg = segmenter();
  if (seg) {
    for (const s of seg.segment(text)) if (s.index > 0) starts.add(s.index);
  } else {
    for (let i = 1; i < text.length; i++) if (isCJKChar(text[i]) || isCJKChar(text[i - 1])) starts.add(i);
  }
  for (let i = 1; i < text.length; i++) if (isSpace(text[i - 1]) && !isSpace(text[i])) starts.add(i);
  const out: number[] = [];
  for (const k of Array.from(starts).sort((a, b) => a - b)) {
    const c = text[k], p = text[k - 1];
    if (isSpace(c)) continue;                       // a break lands on the word after a space, not on the space
    if (CLOSE.has(c) || OPEN.has(p)) continue;      // kinsoku
    if (!isCJKChar(c) && !isCJKChar(p) && !isSpace(p)) continue;   // inside a Latin word or a number
    out.push(k);
  }
  return out;
};

const lexLess = (a: number[], b: number[]) => {
  for (let q = 0; q < Math.min(a.length, b.length); q++) if (a[q] !== b[q]) return a[q] < b[q];
  return a.length < b.length;
};
const SCRAP = 0.4;   // a line shorter than this share of the longest reads as a scrap, not a line

/** The balanced breaks for a long caption (more than four lines): minimise the longest line, by dynamic programming. */
const balancedCuts = (t: string, pts: number[], n: number, width: (a: number, b: number) => number): number[] => {
  const P = pts.length;
  const INF = Number.POSITIVE_INFINITY;
  const best: number[][] = Array.from({length: n + 1}, () => new Array(P).fill(INF));
  const from: number[][] = Array.from({length: n + 1}, () => new Array(P).fill(-1));
  best[0][0] = 0;
  for (let k = 1; k <= n; k++) {
    for (let j = 1; j < P; j++) {
      for (let i = 0; i < j; i++) {
        if (best[k - 1][i] === INF) continue;
        const v = Math.max(best[k - 1][i], width(pts[i], pts[j]));
        if (v < best[k][j] - 1e-9 || (Math.abs(v - best[k][j]) <= 1e-9 && i > from[k][j])) {
          best[k][j] = v; from[k][j] = i;
        }
      }
    }
  }
  const cuts: number[] = [];
  for (let k = n, j = P - 1; k > 0 && j > 0; k--) { cuts.unshift(pts[j]); j = from[k][j]; }
  return cuts.filter((c) => c > 0 && c < t.length);           // the inner breaks only
};

/**
 * `text` broken into lines no wider than `measure`, where `adv(ch)` is a character's advance in the same units. The
 * fewest lines a greedy fill at the allowed breaks needs, then — among breaks that keep that count — the ones that
 * make the longest line shortest (ties: the later break, so the first line is the fuller). A single word wider than
 * the measure stays whole on its own line; the block it is drawn in may still wrap it (Film.tsx), which is the one
 * case the estimate cannot promise.
 */
export const breakLines = (text: string, measure: number, adv: (ch: string) => number): string[] => {
  const t = text.trim();
  if (!t) return [];
  const pts = [0, ...breakPoints(t), t.length];
  const cum = [0];
  for (let i = 0; i < t.length; i++) cum.push(cum[i] + adv(t[i]));
  // the width of t[a..b) as it is drawn — trailing spaces hang, leading ones are dropped at a break
  const width = (a: number, b: number) => {
    let x = a, y = b;
    while (x < y && isSpace(t[x])) x++;
    while (y > x && isSpace(t[y - 1])) y--;
    return cum[y] - cum[x];
  };
  // greedy: how many lines this needs at the allowed breaks
  let n = 0;
  for (let a = 0, i = 0; a < t.length; n++) {
    let j = i + 1;
    while (j + 1 < pts.length && width(a, pts[j + 1]) <= measure) j++;
    a = pts[j]; i = j;
  }
  if (n <= 1) return [t];
  // WHICH n-1 BREAKS. A reader's break is after a clause — 「查资料、写稿、/ 配音，交回成片。」 — so a set that breaks
  // after punctuation (or a space) wins, as long as no line is a scrap (every line at least SCRAP of the longest); then
  // the most balanced; then the later breaks, so the first line is the fuller. Every line fits the measure, or is one
  // word too wide to fit anywhere. A caption is 1-3 lines, so the sets are few enough to try them all.
  const inner = pts.slice(1, -1);
  const soft = (k: number) => CLOSE.has(t[k - 1]) || isSpace(t[k - 1]);
  const fits = (a: number, b: number) => width(a, b) <= measure + 1e-9 || !inner.some((k) => k > a && k < b);
  let bestCuts: number[] | null = null;
  let bestKey: number[] | null = null;
  const pick = (chosen: number[]) => {
    const edges = [0, ...chosen, t.length];
    const ws: number[] = [];
    for (let q = 0; q + 1 < edges.length; q++) {
      if (!fits(edges[q], edges[q + 1])) return;
      ws.push(width(edges[q], edges[q + 1]));
    }
    const mx = Math.max(...ws), mn = Math.min(...ws);
    const key = [mn >= SCRAP * mx ? 0 : 1, chosen.filter((k) => !soft(k)).length, mx, ...chosen.map((k) => -k)];
    if (!bestKey || lexLess(key, bestKey)) { bestKey = key; bestCuts = chosen; }
  };
  const walk = (from: number, left: number, chosen: number[]) => {
    if (left === 0) { pick(chosen); return; }
    for (let q = from; q < inner.length; q++) walk(q + 1, left - 1, [...chosen, inner[q]]);
  };
  if (n <= 4 && inner.length <= 80) walk(0, n - 1, []);
  const cuts: number[] = [...(bestCuts ?? balancedCuts(t, pts, n, width)), t.length];
  const lines: string[] = [];
  let a = 0;
  for (const b of cuts) { lines.push(t.slice(a, b).trim()); a = b; }
  return lines.filter(Boolean);
};

export type LineFault = {line: number; kind: 'kinsoku' | 'orphan' | 'split'; text: string};

/**
 * What is wrong with a set of lines a caption was broken into: a line that STARTS with closing punctuation
 * (kinsoku), a last line that is ONE CJK glyph (with or without its punctuation — 「子。」), or a break that falls
 * INSIDE a word (`split`: the line's end and the next line's start are one segmenter word). Empty when the lines are
 * clean. This is the gate's question, asked of the lines the film draws.
 */
export const lineFaults = (lines: string[]): LineFault[] => {
  const out: LineFault[] = [];
  lines.forEach((l, i) => {
    const s = l.trim();
    if (i > 0 && s && CLOSE.has(s[0])) out.push({line: i, kind: 'kinsoku', text: s});
    const core = Array.from(s).filter((c) => !CLOSE.has(c) && !OPEN.has(c) && !isSpace(c));
    if (i === lines.length - 1 && lines.length > 1 && core.length === 1 && isCJKChar(core[0])) {
      out.push({line: i, kind: 'orphan', text: s});
    }
  });
  const seg = segmenter();
  if (seg && lines.length > 1) {
    // re-join as the caption was written: a space between two Latin line ends, nothing between CJK ones
    let joined = '';
    const at: number[] = [];
    lines.forEach((l, i) => {
      const s = l.trim();
      if (i > 0) {
        if (!isCJKChar(joined[joined.length - 1] ?? '') && !isCJKChar(s[0] ?? '')) joined += ' ';
        at.push(joined.length);
      }
      joined += s;
    });
    const starts = new Set<number>();
    for (const x of seg.segment(joined)) starts.add(x.index);
    at.forEach((k, i) => {
      if (!starts.has(k)) out.push({line: i + 1, kind: 'split', text: lines[i + 1].trim()});
    });
  }
  return out;
};

// ── the caption's chunks — moved here from Film.tsx unchanged, so the gate runs the film's own code ─────────────
// Split a caption into progressively-shown chunks. Splits on sentence enders — ASCII (.!?) AND CJK (。！？) —
// so a 中文 caption chunks per sentence too (not one block). Short LATIN fragments merge into their neighbour
// (the 22-char floor is a Latin measure); CJK sentences each stand alone (a full sentence is few chars but a
// complete thought, and merging them by a Latin char-count would collapse them). Never empty. Deterministic.
export const isCJKText = (s: string): boolean => /[㐀-鿿぀-ヿ가-힯]/.test(s);
export const splitCaption = (text: string): string[] => {
  // A DECIMAL POINT is not a sentence end. The splitter treats `.` as a terminator, so "19.3 到 28.9%"
  // broke into "19." / "3 到 28." / "9%。" and the caption on screen read 「pass@k 最多掉 19.」 — a
  // number cut in half, on the beat carrying the film's headline figure. Shield digit-dot-digit behind a
  // sentinel for the split, then restore it. Applies to any figure: 0.833, 2.39, 19.3.
  const DEC = '\u0000';
  const guarded = text.replace(/(\d)\.(\d)/g, `$1${DEC}$2`);
  const chunks = guarded.match(/[^.!?。！？—]+[.!?。！？]?(\s*—)?/g)
    ?.map((c) => c.trim().split(DEC).join('.')).filter(Boolean) ?? [text];
  const merged: string[] = [];
  for (const c of chunks) {
    const prev = merged[merged.length - 1];
    if (prev && !isCJKText(c) && !isCJKText(prev) && (prev.length < 22 || c.length < 22)) merged[merged.length - 1] += ' ' + c;
    else merged.push(c);
  }
  return merged;
};

// FIT THE CAPTION TO THE BAND IT WAS GIVEN — not the other way round.
//
// The band reserves CAPTION_LINES lines. A single long SENTENCE is one chunk however long it is, so a
// 100-character line wrapped to THREE lines, overflowed the two-line reserve, and climbed into the picture:
// a delivered frame had the caption printed straight through the shot's own subtitle. Widening the measure
// alone does not fix it, because there is always a longer sentence.
//
// So an over-long chunk is split at its best CLAUSE boundary (comma / semicolon / dash — a place a reader
// already pauses), nearest the middle so neither half is a scrap. Capacity is estimated from the type size
// and the measure: Latin advance averages ~0.52em, CJK is monospaced at 1em. The estimate is calibrated
// against real renders — a 100-char Latin caption at 56px in a 1400px measure is predicted 3 lines and
// rendered 3 lines. Deterministic, and it degrades to the original chunk when there is no boundary to cut on.
// THE ADVANCE BELONGS TO THE FONT, not to one font. Both estimates below were calibrated on Inter and
// then applied to whatever face the film's DNA supplies. Measured on this renderer at 56px: this film's
// IBM Plex Sans averages 0.452-0.478 em on real prose — so 0.52 is conservative and safe — but the
// `terminal` DNA sets ALL type to JetBrains Mono, where the same sentence measures 0.588. There the
// estimate UNDER-counts, the caption wraps to more lines than the fit assumed, and it overflows the band
// it was supposed to be guaranteed to fit. CJK measures 0.995 in a PROPORTIONAL face, so 1.0 was right for
// the faces this was written against — and wrong for a terminal DNA, whose caption is set in the mono
// stack, where a Han glyph is two cells. `cjkAdvance` asks the face, exactly as `latinAdvance` does.
export const advanceFor = (text: string, fontStack?: string, uniform?: boolean): number =>
  isCJKText(text) ? cjkAdvance(fontStack, uniform) : latinAdvance(fontStack, uniform);

// A CJK caption's lines are decided by captionBreak.ts (word boundaries, kinsoku, balanced) against the same advance
// estimate the band fit uses — per CHARACTER here, because a Latin word inside a Chinese line is narrower than a Han
// glyph and the old whole-text estimate charged it a full em.
const CJK_ADV_RE = /[\u3000-\u303f\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af\uff00-\uffef]/;
const charAdvance = (fontStack?: string, uniform?: boolean) => {
  const c = cjkAdvance(fontStack, uniform), l = latinAdvance(fontStack, uniform);
  return (ch: string) => (CJK_ADV_RE.test(ch) ? c : l);
};
/** The lines a CJK chunk is drawn in at `size` px in a `measure`-px line (captionBreak.breakLines). */
export const cjkCaptionLines = (t: string, size: number, measure: number, fontStack?: string, uniform?: boolean): string[] => {
  const adv = charAdvance(fontStack, uniform);
  return breakLines(t, measure, (ch) => size * adv(ch));
};

const CLAUSE = /[,;，；、]|\s—\s/g;
export const fitCaption = (chunks: string[], size: number, measure: number, lines: number,
                    fontStack?: string, uniform?: boolean): string[] => {
  const out: string[] = [];
  const cap = (t: string) => Math.max(8, Math.floor(measure / (size * advanceFor(t, fontStack, uniform))));
  const split = (t: string, depth: number): void => {
    const budget = cap(t) * lines;
    // a CJK chunk is counted in the lines it will really be broken into (word boundaries cost a little per line)
    const fits = isCJKText(t) ? cjkCaptionLines(t, size, measure, fontStack, uniform).length <= lines : t.length <= budget;
    if (fits || depth > 2) { out.push(t); return; }
    const mid = t.length / 2;
    let best = -1;
    CLAUSE.lastIndex = 0;
    for (let m = CLAUSE.exec(t); m; m = CLAUSE.exec(t)) {
      // A SEPARATOR INSIDE A NUMBER IS NOT A CLAUSE BOUNDARY. `378,140` and `19.3` carry a thousands
      // separator and a decimal point, and cutting there guillotines the figure across two lines —
      // "the register today counts 378," / "140 residents". This is the same defect as the one already
      // guarded in splitCaption above, reproduced here because the two functions scan for different
      // things and only one of them knew. A digit on both sides means it belongs to the number.
      if (/\d/.test(t[m.index - 1] ?? '') && /\d/.test(t[m.index + m[0].length] ?? '')) continue;
      const at = m.index + m[0].length;
      if (at > 4 && at < t.length - 4 && (best < 0 || Math.abs(at - mid) < Math.abs(best - mid))) best = at;
    }
    if (best < 0) { out.push(t); return; }          // nothing to cut on — better one long chunk than a word sliced
    split(t.slice(0, best).trim(), depth + 1);
    split(t.slice(best).trim(), depth + 1);
  };
  chunks.forEach((c) => split(c, 0));
  return out;
};

