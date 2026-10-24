// KINETIC TYPE — one primitive every register that animates type by the letter, word or line draws with.
//
// WHY ONE. Eight registers hand-rolled a per-character split before this existed (references/motion-research.md
// §0), each as `display: inline-block` spans — and per-character inline-blocks are not the text they split:
// measured on this renderer (Chrome 149, Inter 500 at 100px, "AVATAR Wave To") they set the line 8.1% wider and
// differ from the same string in one text node by 27,650 pixels, because each box loses the kerning against its
// neighbour. Chinese loses more: 18 characters with punctuation measured 1600px in one node and 1800px as
// per-character boxes, because the box defeats Chrome's punctuation compression (text-spacing-trim) — 11% wider,
// and a line that fitted in the reference no longer fits. Ligatures pop in and out the moment tracking moves (a
// non-zero letter-spacing switches them off: Playfair "fi fl ffi ffl" 401.5px at 0, 419.4px at 0.01em).
//
// WHAT THIS DOES INSTEAD (measured: 0 px difference against the single text node). The text is laid out ONCE, by
// the browser, in a reference node with the same face, size, axes and tracking and with ligatures off; every
// grapheme's box is read with `Range.getClientRects()`; and each glyph is then drawn on its own, absolutely placed
// where the reference put it. Kerning, CJK punctuation compression and kinsoku line breaking are therefore the
// browser's own, not re-implemented. A layout is measured once per (text, face, size, axes, box) and memoised; a
// weight or width MORPH reflows the line (Inter wght 100→900 is +21%, Plex wdth 75→100 +11%), so it is measured at
// five anchors across the range and interpolated (5 anchors ≈ 1px, research §1), with the line breaks fixed at the
// widest anchor so a morph can never push a word off its line.
//
// WHERE IT IS MEASURED. In a detached node at the document root, not inside the shot: a register is drawn under a
// camera scale, a platform-safe frame (0.8) and a time warp, and client rects come back in SCALED pixels — a
// measurement taken under them would differ by float noise from frame to frame, and a glyph rasterised at a
// different sub-pixel is different bytes. The face the shot actually resolves is read off an in-tree anchor first
// (a DNA's `--f-display`, or a terminal DNA's `!important` monospace), then written literally onto the reference.
//
// THE ANIMATION IS A PURE FUNCTION OF `useT()` — the After Effects model (kineticCore.ts): one coverage per unit
// drives every property. No CSS transition, no clock, no Math.random (randomness is `hash01` of a seed). A moving
// glyph carries the baseline unlock (runtime/glide) INSIDE any blur, so it glides instead of stepping whole pixels.
//
// THE GATES STILL SEE IT. Each glyph's text holder is marked with its line (runtime/kineticDom.ts), and the census
// (runtime/textSafe.tsx, titleProbe.tsx) reads a KineticText as the LINES a viewer reads — one cut-off, one title,
// one sync entry per line — instead of forty one-letter elements.
import React from 'react';
import {cancelRender, continueRender, delayRender, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, ReducedMotionContext, SceneDurationContext, REDUCED_MOTION_T} from './motion';
import {useGlide, BaselineUnlockContext} from './glide';
import {useCues, REACH_CUBIC} from './cue';
import {CJK_MIN_LEADING, hasCJK} from './cjkType';
import {getLength, getPointAtLength} from '@remotion/paths';
import {KIN_ALIGN, KIN_ALT, KIN_GLYPH, KIN_LINE, KIN_READ, KIN_ROOT, KINETIC_HOLDS_TAG, kineticBusy, kineticIdle,
  facesReady} from './kineticDom';
import {
  clamp01, easeOf, EaseName, graphemes, langOf, orderRank, Order, parseRuns, permutation, rangeCoverage,
  RangeSelector, scrambleGlyph, ScrambleGlyph, secToT, swapTimes, tAtFrame, tToSec, wordCount, wordIds, longestRun,
} from './kineticCore';

export type {RangeSelector, Order, EaseName} from './kineticCore';

// ── what is measured ─────────────────────────────────────────────────────────────────────────────────────
export type KFont = {
  /** a CSS family list — write `var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)` like any register */
  family: string;
  /** the rest weight */
  weight?: number;
  /** the largest size, px. With `fit: 'box'` the measured fit may set it smaller, never larger. */
  size: number;
  /** the smallest size a fit may reach, px. Below it the text does not fit, and that is an error, not a shrink. */
  minSize?: number;
  /** line-height as a ratio. Raised to CJK_MIN_LEADING when the copy carries CJK (runtime/cjkType). */
  lineHeight?: number;
  /** letter-spacing at rest, em (Linear's hero: -0.022) */
  tracking?: number;
  italic?: boolean;
  /** font-stretch at rest, % — only a face with a `wdth` axis answers (IBM Plex Sans, 75-100) */
  stretch?: number;
  /** the weight of `*emphasised*` runs; defaults to `weight` */
  emphWeight?: number;
};

export type KSpec = {
  /** the copy. `*…*` marks an emphasised run (kineticCore.parseRuns). An array is paragraphs: each starts a line. */
  text?: string | string[];
  /** a SWAP: the alternatives the text cycles through, laid out each on its own, in the same box and size */
  alts?: string[];
  font: KFont;
  /** the box, px. `h` bounds the fit; without it only the width does. */
  w: number;
  h?: number;
  fit?: 'box' | 'none';
  maxLines?: number;
  /** fits to try FIRST, in order, before the spec's own `maxLines`/`minSize`: e.g. "every entry on one line, down to
   *  a display floor" before "wrap if you must". A tier that cannot fit at its floor hands over to the next. */
  fitTiers?: {maxLines?: number; minSize?: number}[];
  /** one line, never wrapped (a slot, type on a path, cropped big type) */
  nowrap?: boolean;
  wrap?: 'balance' | 'pretty' | 'normal';
  /** break Chinese and Japanese at punctuation and spaces, not between any two characters (default true): a run
   *  that cannot fit its line still breaks anywhere rather than overflow */
  keepPhrases?: boolean;
  align?: 'left' | 'center' | 'right';
  valign?: 'top' | 'middle' | 'bottom';
  /** segmenter / layout locale. Default: from the script of the copy (kana → ja, Hangul → ko, Han → zh). */
  lang?: string;
  /** the range a morph will move each axis through. Required for any axis the motion animates. */
  axes?: {wght?: [number, number]; wdth?: [number, number]};
};

export type KGlyph = {
  g: string; sp: boolean;            // the grapheme, and whether it is whitespace
  x: number; y: number;              // where its holder's top-left goes, in box px
  left: number; adv: number;         // the reference's pen x and advance (for reflow)
  w: number; h: number;              // its content box (the Range rect)
  dy: number; base: number;          // content top and baseline inside the holder
  line: number; word: number; para: number; emph: boolean;
  trim: boolean;                     // CJK punctuation the reference compressed
};
export type KLine = {top: number; bottom: number; left: number; right: number; para: number; text: string;
  first: number; last: number};
export type KAlt = {text: string; glyphs: KGlyph[]; lines: KLine[]; width: number; height: number; words: number};
export type KAxisAnchors = {v: number[]; adv: number[][][]};   // adv[alt][anchor][glyph]
export type KLayout = {
  key: string; size: number; lh: number; family: string; lang: string; align: 'left' | 'center' | 'right';
  boxW: number; boxH: number; alts: KAlt[];
  /** the widest alternative's extent */
  width: number; height: number;
  axes: {wght?: KAxisAnchors; wdth?: KAxisAnchors};
  weight: number; emphWeight: number; stretch: number; tracking: number; italic: boolean;
};

const LAYOUTS = new Map<string, KLayout>();
const MAX_LAYOUTS = 256;           // a bound on a leak, not a working-set size

const RTL = /[\p{Script=Arabic}\p{Script=Hebrew}\p{Script=Syriac}\p{Script=Thaana}\p{Script=Nko}]/u;
// The OPENING ones: Chrome compresses them by moving the ink (the `halt` placement), so a holder must ask for the same
// trim; a closing mark keeps its ink where it was and only loses advance, which a placed glyph does not have.
const CJK_OPEN = /[\u3008\u300A\u300C\u300E\u3010\u3014\u3016\u3018\u301A\u301D\uFF08\uFF3B\uFF5B\uFF5F\uFF62\u2018\u201C]/;

type Resolved = {family: string; kerning: string; synthesis: string; rendering: string; optical: string};
const resolveFont = (el: Element): Resolved => {
  const cs = getComputedStyle(el);
  return {family: cs.fontFamily, kerning: cs.fontKerning, synthesis: cs.fontSynthesis,
    rendering: cs.textRendering, optical: (cs as unknown as {fontOpticalSizing?: string}).fontOpticalSizing ?? 'auto'};
};

const paragraphs = (spec: KSpec): string[][] => {
  if (spec.alts) {
    if (!Array.isArray(spec.alts) || !spec.alts.length) throw new Error('kinetic: `alts` must be a non-empty list.');
    return spec.alts.map((a) => [String(a ?? '')]);
  }
  const t = spec.text;
  const paras = Array.isArray(t) ? t.map((x) => String(x ?? '')) : [String(t ?? '')];
  return [paras];
};

const leadingFor = (spec: KSpec, texts: string[]): number => {
  const lh = spec.font.lineHeight ?? 1.05;
  return texts.some((s) => hasCJK(s)) ? Math.max(lh, CJK_MIN_LEADING) : lh;
};

// The style every node that DRAWS a glyph shares with the reference. One function, so the measurement and the
// drawing cannot set two different fonts.
const baseStyle = (r: Resolved, size: number, lh: number, f: KFont): Partial<CSSStyleDeclaration> => ({
  fontFamily: r.family, fontSize: `${size}px`, lineHeight: `${lh}px`, fontStyle: f.italic ? 'italic' : 'normal',
  fontKerning: r.kerning, fontSynthesis: r.synthesis, textRendering: r.rendering,
  fontVariantLigatures: 'none', whiteSpace: 'pre',
});
const assign = (el: HTMLElement, st: Record<string, string | undefined>) => {
  for (const [k, v] of Object.entries(st)) if (v !== undefined) (el.style as unknown as Record<string, string>)[k] = v;
};

type GSrc = {g: string; para: number; emph: boolean};
/** The ONE grapheme sequence every pass maps its rects back onto, so index i is the same glyph in all of them. */
const sequence = (paras: string[]): GSrc[] => {
  const out: GSrc[] = [];
  paras.forEach((p, pi) => parseRuns(p).forEach((run) => graphemes(run.text).forEach((g) =>
    out.push({g, para: pi, emph: run.emph}))));
  return out;
};
const isSpace = (g: string) => /^\s+$/.test(g);
const CJK_CHAR = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/u;
/** Each grapheme's word index, paragraph by paragraph, numbered across the whole text (Intl.Segmenter). */
const wordsOfSeq = (seq: GSrc[], lang: string): {word: number[]; count: number} => {
  const word: number[] = new Array(seq.length).fill(0);
  const nParas = seq.length ? seq[seq.length - 1].para + 1 : 0;
  let base = 0;
  for (let p = 0; p < nParas; p++) {
    const ix = seq.map((g, i) => (g.para === p ? i : -1)).filter((i) => i >= 0);
    const {ids, count} = wordIds(ix.map((i) => seq[i].g).join(''), lang);
    ix.forEach((i, k) => { word[i] = base + (ids[k] ?? 0); });
    base += count;
  }
  return {word, count: base};
};

/** Measure. DOM only; throws, with the measured numbers, when the copy cannot fit the box. */
const measure = (spec: KSpec, r: Resolved, key: string): KLayout => {
  const alts = paragraphs(spec);
  const flat = alts.flat();
  if (flat.some((s) => RTL.test(s))) {
    throw new Error('kinetic: right-to-left and joining scripts are not supported — each letter\'s shape depends on ' +
      'its neighbours, so a glyph drawn on its own is a different glyph. Set this copy as one text node instead.');
  }
  const lang = spec.lang ?? langOf(flat.join(''));
  const f = spec.font;
  const weight = f.weight ?? 600, emphWeight = f.emphWeight ?? weight, stretch = f.stretch ?? 100;
  const tracking = f.tracking ?? 0;
  const align = spec.align ?? 'left';
  const ratio = leadingFor(spec, flat.map((s) => s.replace(/\*/g, '')));
  const host = document.createElement('div');
  host.setAttribute('lang', lang);
  assign(host, {position: 'absolute', left: '0px', top: '0px', visibility: 'hidden', pointerEvents: 'none',
    contain: 'layout style'});
  document.body.appendChild(host);
  try {
    const wMax = spec.axes?.wght ? Math.max(...spec.axes.wght, weight, emphWeight) : null;
    const sMax = spec.axes?.wdth ? Math.max(...spec.axes.wdth, stretch) : null;
    type Built = {ref: HTMLDivElement; nodes: {node: Text; idx: number[]}[]; lh: number};
    // the reference: one block per `blocks` entry (a paragraph, or a forced line), one span per emphasis run
    // A CHINESE OR JAPANESE RUN MAY BREAK ONLY AT A WORD. `keep-all` alone left a run with no punctuation exactly one
    // break opportunity — the emergency one, wherever it overflowed — so `balance` had nothing to choose from and a
    // title came out 「沿着波形前进的文 / 字」. Each word boundary inside a CJK run (Intl.Segmenter, the same words the
    // animation counts) gets a <wbr>, which is a break opportunity and nothing else: no glyph, no width.
    const phraseWords = new Map<GSrc[], number[]>();
    const build = (seq: GSrc[], blocks: number[][], size: number, o: {wAx?: number; sAx?: number; forced?: boolean}):
      Built => {
      const lh = size * ratio;
      const ref = document.createElement('div');
      const pre = spec.nowrap || o.forced;
      assign(ref, {...baseStyle(r, size, lh, f) as Record<string, string>, position: 'absolute', left: '0px',
        top: '0px', width: `${spec.w}px`, textAlign: align, letterSpacing: `${tracking}em`,
        whiteSpace: pre ? 'pre' : 'pre-line', fontWeight: String(o.wAx ?? weight),
        fontStretch: `${o.sAx ?? stretch}%`});
      (ref.style as unknown as Record<string, string>).textWrap =
        pre ? 'nowrap' : spec.wrap === 'normal' ? 'wrap' : (spec.wrap ?? 'balance');
      if (!pre && spec.keepPhrases !== false) {
        // A CHINESE SENTENCE MAY BREAK BETWEEN ANY TWO CHARACTERS, and the browser takes the first place that fits:
        // a note came out as 「…强调的部分最后换 / 色、加粗」, a word cut in two. keep-all makes a run of CJK one
        // word, so lines break at its punctuation and spaces; `anywhere` is the fallback for a run too long to fit.
        assign(ref, {wordBreak: 'keep-all', overflowWrap: 'anywhere'});
      }
      const nodes: {node: Text; idx: number[]}[] = [];
      for (const blk of blocks) {
        const div = document.createElement('div');
        let i = 0;
        while (i < blk.length) {
          const emph = seq[blk[i]].emph;
          const idx: number[] = [];
          while (i < blk.length && seq[blk[i]].emph === emph) idx.push(blk[i++]);
          const sp = document.createElement('span');
          if (emph) sp.style.fontWeight = String(o.wAx ?? emphWeight);
          const wd = !pre && spec.keepPhrases !== false ? phraseWords.get(seq) : undefined;
          let part: number[] = [];
          const flush = () => {
            if (!part.length) return;
            const tn = document.createTextNode(part.map((k) => seq[k].g).join(''));
            sp.appendChild(tn);
            nodes.push({node: tn, idx: part});
            part = [];
          };
          idx.forEach((k, n) => {
            const prev = idx[n - 1];
            if (wd && n > 0 && wd[k] !== wd[prev] && (CJK_CHAR.test(seq[k].g) || CJK_CHAR.test(seq[prev].g))) {
              flush();
              sp.appendChild(document.createElement('wbr'));
            }
            part.push(k);
          });
          flush();
          div.appendChild(sp);
        }
        if (!blk.length) div.appendChild(document.createElement('br'));
        ref.appendChild(div);
      }
      host.appendChild(ref);
      return {ref, nodes, lh};
    };
    const rectsOf = (b: Built, seq: GSrc[]): (DOMRect | null)[] => {
      const origin = b.ref.getBoundingClientRect();
      const out: (DOMRect | null)[] = new Array(seq.length).fill(null);
      for (const nd of b.nodes) {
        let at = 0;
        for (const k of nd.idx) {
          const len = (nd.node.textContent ?? '').length;
          const g = seq[k].g;
          const rg = document.createRange();
          rg.setStart(nd.node, at);
          rg.setEnd(nd.node, Math.min(len, at + g.length));
          const rs = Array.from(rg.getClientRects()).filter((x) => x.width > 0 || x.height > 0);
          const q = rs.length ? rs[rs.length > 1 && isSpace(g) ? rs.length - 1 : 0] : null;
          out[k] = q ? new DOMRect(q.left - origin.left, q.top - origin.top, q.width, q.height) : null;
          at += g.length;
        }
      }
      return out;
    };
    const linesFrom = (rects: (DOMRect | null)[], lh: number, seq: GSrc[]): number[] => {
      const out: number[] = [];
      let line = -1, top = -Infinity;
      rects.forEach((q, i) => {
        if (q && q.width > 0 && !isSpace(seq[i].g) && q.top > top + lh * 0.5) { line += 1; top = q.top; }
        else if (q && q.width > 0 && line < 0) { line = 0; top = q.top; }
        out.push(Math.max(0, line));
      });
      return out;
    };
    const paraBlocks = (seq: GSrc[]) => {
      const n = seq.length ? seq[seq.length - 1].para + 1 : 0;
      const blocks: number[][] = Array.from({length: Math.max(n, 1)}, () => []);
      seq.forEach((g, i) => blocks[g.para].push(i));
      return blocks;
    };

    // 1. THE FIT — at the widest point of any morph, every alternative, by the browser's own wrapping.
    const fitOne = (seq: GSrc[], size: number) => {
      const b = build(seq, paraBlocks(seq), size, {wAx: wMax ?? undefined, sAx: sMax ?? undefined});
      const rects = rectsOf(b, seq);
      const ln = linesFrom(rects, b.lh, seq);
      const res = {width: b.ref.scrollWidth, height: b.ref.offsetHeight,
        lines: seq.length ? Math.max(...ln) + 1 : 0, lh: b.lh};
      b.ref.remove();
      return res;
    };
    let maxLines = spec.maxLines;
    const fits = (m: {width: number; height: number; lines: number}) =>
      m.width <= spec.w + 0.5 && (spec.h === undefined || m.height <= spec.h + 0.5) &&
      (maxLines === undefined || m.lines <= maxLines);
    const seqs = alts.map(sequence);
    seqs.forEach((seq) => phraseWords.set(seq, wordsOfSeq(seq, lang).word));
    let size = f.size;
    if ((spec.fit ?? 'box') === 'box') {
      let floor = Math.min(f.size, f.minSize ?? f.size);
      // the preferred tiers: the first whose floor every alternative fits at sets the rules for the real fit
      for (const tier of spec.fitTiers ?? []) {
        const ml = tier.maxLines ?? spec.maxLines, fl = Math.min(f.size, tier.minSize ?? floor);
        maxLines = ml;
        if (seqs.every((seq) => fits(fitOne(seq, fl)))) { floor = fl; break; }
        maxLines = spec.maxLines;
      }
      seqs.forEach((seq, ai) => {
        let lo = floor, hi = size;
        if (fits(fitOne(seq, hi))) return;
        const atFloor = fitOne(seq, lo);
        if (!fits(atFloor)) {
          throw new Error(`kinetic: "${alts[ai].join(' / ').slice(0, 60)}" does not fit ${Math.round(spec.w)}` +
            `${spec.h !== undefined ? `x${Math.round(spec.h)}` : ''}px even at ${lo}px — it measured ` +
            `${Math.round(atFloor.width)}x${Math.round(atFloor.height)}px on ${atFloor.lines} line(s)` +
            `${maxLines !== undefined ? ` (max ${maxLines})` : ''}. Shorten the copy or give it more room; ` +
            'a smaller size than the floor is not a fix, it is unreadable type.');
        }
        for (let k = 0; k < 12 && hi - lo > 0.5; k++) {
          const mid = (lo + hi) / 2;
          if (fits(fitOne(seq, mid))) lo = mid; else hi = mid;
        }
        size = Math.floor(lo * 2) / 2;
      });
    }
    const lh = size * ratio;

    // 2. THE REST LAYOUT. With a morph, the lines are broken at its widest value and then FORCED, one block each,
    //    so no anchor can re-wrap them; the spaces a break swallowed are dropped from those blocks (a forced line's
    //    trailing space would otherwise count in its centring) and placed as the collapsed spaces they are.
    const out: KAlt[] = [];
    const anchorsW: number[][][] = [], anchorsS: number[][][] = [];
    const wAnch = spec.axes?.wght ? anchorValues([...spec.axes.wght, weight, emphWeight]) : null;
    const sAnch = spec.axes?.wdth ? anchorValues([...spec.axes.wdth, stretch]) : null;
    const probeCache = new Map<string, {dx: number; dy: number; base: number}>();
    seqs.forEach((seq, ai) => {
      let blocks = paraBlocks(seq);
      let forced = false;
      if (wAnch || sAnch) {
        const b0 = build(seq, blocks, size, {wAx: wMax ?? undefined, sAx: sMax ?? undefined});
        const r0 = rectsOf(b0, seq);
        const l0 = linesFrom(r0, b0.lh, seq);
        b0.ref.remove();
        const byLine: number[][] = [];
        seq.forEach((_g, i) => { (byLine[l0[i]] = byLine[l0[i]] ?? []).push(i); });
        blocks = byLine.filter(Boolean).map((ix) => {
          let a = 0, z = ix.length;
          while (a < z && isSpace(seq[ix[a]].g)) a++;
          while (z > a && isSpace(seq[ix[z - 1]].g)) z--;
          return ix.slice(a, z);
        });
        forced = true;
      }
      const b = build(seq, blocks, size, {forced});
      const rects = rectsOf(b, seq);
      const height = b.ref.offsetHeight;
      b.ref.remove();
      const lineOf = linesFrom(rects, lh, seq);
      // words, per paragraph, numbered across the whole text
      const {word, count: wBase} = wordsOfSeq(seq, lang);
      const nParas = seq.length ? seq[seq.length - 1].para + 1 : 0;
      const glyphs: KGlyph[] = [];
      seq.forEach((src, i) => {
        const q = rects[i];
        const prev = glyphs[i - 1];
        const wt = src.emph ? emphWeight : weight;
        if (!q) {
          glyphs.push({g: src.g, sp: isSpace(src.g), x: prev ? prev.left + prev.adv : 0, y: prev ? prev.y : 0,
            left: prev ? prev.left + prev.adv : 0, adv: 0, w: 0, h: prev ? prev.h : lh, dy: prev ? prev.dy : 0,
            base: prev ? prev.base : lh * 0.8, line: lineOf[i], word: word[i], para: src.para, emph: src.emph,
            trim: false});
          return;
        }
        let trim = false;
        if (CJK_OPEN.test(src.g) && q.width > 0) {
          // THE REFERENCE COMPRESSED AN OPENING BRACKET (text-spacing-trim: `”（` collapses to half an em). Chrome
          // does that by moving the INK half an em left, so a glyph drawn on its own at the reference's pen lands
          // half an em to the right — measured: two brackets of a Chinese probe line drawn on top of the next
          // character, 2,428 px off the reference. A holder is a line of one, and `trim-start` trims an opening
          // mark at a line's start the same way. (`trim-both` would read more naturally and Chrome 149 drops it
          // as invalid, falling back to `normal`, which keeps a line-start bracket full width.)
          trim = q.width < probeWidth(host, r, f, size, lh, src.g, wt, stretch) * 0.75;
        }
        const pk = `${src.g}|${wt}|${trim ? 't' : ''}`;
        let pr = probeCache.get(pk);
        if (!pr) {
          pr = probeGlyph(host, r, f, size, lh, src.g, wt, stretch, trim ? 'trim-start' : 'space-all');
          probeCache.set(pk, pr);
        }
        glyphs.push({g: src.g, sp: isSpace(src.g), x: q.left - pr.dx, y: q.top - pr.dy, left: q.left, adv: q.width,
          w: q.width, h: q.height, dy: pr.dy, base: pr.base, line: lineOf[i], word: word[i], para: src.para,
          emph: src.emph, trim});
      });
      // advances from consecutive pens on a line — kerning lives in the gap between boxes, not in a box
      const advOf = (rs: (DOMRect | null)[]) => seq.map((_g, i) => {
        const a = rs[i];
        if (!a) return 0;
        for (let j = i + 1; j < seq.length; j++) {
          const bq = rs[j];
          if (!bq) continue;
          if (lineOf[j] === lineOf[i] && bq.left >= a.left) return bq.left - a.left;
          break;
        }
        return a.width;
      });
      advOf(rects).forEach((a, i) => { glyphs[i].adv = a; });
      const lines = linesOf(glyphs);
      const width = lines.reduce((m, l) => Math.max(m, l.right - l.left), 0);
      const plain = Array.from({length: nParas}, (_, p) => seq.filter((g) => g.para === p).map((g) => g.g).join(''));
      out.push({text: plain.join('\n'), glyphs, lines, width, height, words: Math.max(1, wBase)});
      // 3. each glyph's advance at each anchor of each axis a morph may move
      const anchorAdv = (axis: 'wght' | 'wdth', vals: number[]) => vals.map((v) => {
        const ba = build(seq, blocks, size, {forced, ...(axis === 'wght' ? {wAx: v} : {sAx: v})});
        const ra = rectsOf(ba, seq);
        ba.ref.remove();
        return advOf(ra);
      });
      if (wAnch) anchorsW[ai] = anchorAdv('wght', wAnch);
      if (sAnch) anchorsS[ai] = anchorAdv('wdth', sAnch);
    });
    // vertical alignment inside the box
    const H = spec.h;
    if (H !== undefined) {
      for (const a of out) {
        const dy = spec.valign === 'bottom' ? H - a.height : spec.valign === 'middle' ? (H - a.height) / 2 : 0;
        if (dy) {
          a.glyphs.forEach((g) => { g.y += dy; });
          a.lines.forEach((l) => { l.top += dy; l.bottom += dy; });
        }
      }
    }
    return {
      key, size, lh, family: r.family, lang, align, boxW: spec.w, boxH: H ?? Math.max(...out.map((a) => a.height)),
      alts: out, width: Math.max(...out.map((a) => a.width)), height: Math.max(...out.map((a) => a.height)),
      axes: {...(wAnch ? {wght: {v: wAnch, adv: anchorsW}} : {}), ...(sAnch ? {wdth: {v: sAnch, adv: anchorsS}} : {})},
      weight, emphWeight, stretch, tracking, italic: Boolean(f.italic),
    };
  } finally {
    host.remove();
  }
};

/** Five anchors across a range — research §1: piecewise-linear between 5 anchors is within ~1px at 100px type. */
const anchorValues = (vals: number[]): number[] => {
  const lo = Math.min(...vals), hi = Math.max(...vals);
  return hi - lo < 1e-6 ? [lo] : [0, 0.25, 0.5, 0.75, 1].map((k) => lo + (hi - lo) * k);
};

/** One holder, built as the shot builds it, at (0,0): where its content box and baseline land inside it. */
const probeGlyph = (host: HTMLElement, r: Resolved, f: KFont, size: number, lh: number, g: string, weight: number,
                    stretch: number, trim: string) => {
  const outer = document.createElement('span');
  assign(outer, {...baseStyle(r, size, lh, f) as Record<string, string>, position: 'absolute', left: '0px',
    top: '0px', letterSpacing: '0px', fontWeight: String(weight), fontStretch: `${stretch}%`});
  const inner = document.createElement('span');
  assign(inner, {display: 'block'});
  (inner.style as unknown as Record<string, string>).textSpacingTrim = trim;
  const tn = document.createTextNode(g);
  inner.appendChild(tn);
  const mark = document.createElement('span');
  assign(mark, {display: 'inline-block', width: '0px', height: '0px', verticalAlign: 'baseline'});
  inner.appendChild(mark);
  outer.appendChild(inner);
  host.appendChild(outer);
  const o = outer.getBoundingClientRect();
  const rg = document.createRange();
  rg.selectNodeContents(tn);
  const rr = rg.getClientRects()[0] ?? rg.getBoundingClientRect();
  const base = mark.getBoundingClientRect().top - o.top;
  outer.remove();
  return {dx: rr.left - o.left, dy: rr.top - o.top, base};
};
const probeWidth = (host: HTMLElement, r: Resolved, f: KFont, size: number, lh: number, g: string, weight: number,
                    stretch: number) => {
  const s = document.createElement('span');
  assign(s, {...baseStyle(r, size, lh, f) as Record<string, string>, position: 'absolute', left: '0px', top: '0px',
    fontWeight: String(weight), fontStretch: `${stretch}%`});
  (s.style as unknown as Record<string, string>).textSpacingTrim = 'space-all';
  s.textContent = g;
  host.appendChild(s);
  const w = s.getBoundingClientRect().width;
  s.remove();
  return w;
};

const linesOf = (glyphs: KGlyph[]): KLine[] => {
  const out: KLine[] = [];
  glyphs.forEach((g, i) => {
    let L = out[g.line];
    if (!L) {
      L = out[g.line] = {top: Infinity, bottom: -Infinity, left: Infinity, right: -Infinity, para: g.para, text: '',
        first: i, last: i};
    }
    L.text += g.g;
    L.last = i;
    if (g.sp || g.w <= 0) return;
    L.top = Math.min(L.top, g.y + g.dy);
    L.bottom = Math.max(L.bottom, g.y + g.dy + g.h);
    L.left = Math.min(L.left, g.left);
    L.right = Math.max(L.right, g.left + g.w);
  });
  return out.map((L) => (L ? {...L, text: L.text.trim(),
    top: isFinite(L.top) ? L.top : 0, bottom: isFinite(L.bottom) ? L.bottom : 0,
    left: isFinite(L.left) ? L.left : 0, right: isFinite(L.right) ? L.right : 0}
    : {top: 0, bottom: 0, left: 0, right: 0, para: 0, text: '', first: 0, last: -1}));
};

// ── the handle a register holds ──────────────────────────────────────────────────────────────────────────
export type KineticHandle = {layout: KLayout | null; anchor: React.ReactElement; spec: KSpec; key: string};

/**
 * Measure `spec` and hand back its layout (null until measured — the frame is held with delayRender until it is).
 * The register MUST draw the KineticText the handle belongs to (or `handle.anchor`), because the face is resolved
 * off that anchor in the shot's own CSS context.
 */
export function useKinetic(spec: KSpec): KineticHandle {
  const specKey = JSON.stringify(spec);
  const ref = React.useRef<HTMLSpanElement>(null);
  const [state, setState] = React.useState<{key: string; lay: KLayout} | null>(null);
  // THE FRAME IS HELD FOR EVERY MEASUREMENT, NOT ONLY THE FIRST. A spec can change after the first one lands — a
  // register that sizes one text from another's measured height re-specs it on the next render — and a handle
  // released after the first measurement let the frame be captured while the second was still pending, with no
  // glyphs on it. So a hold is taken whenever this hook is waiting for a layout it does not have.
  const [first] = React.useState(() => delayRender('kinetic: measuring type', {timeoutInMilliseconds: 120000}));
  const hold = React.useRef<number | null>(first);
  const busy = React.useRef(false);
  const want = React.useRef('');
  const ready = Boolean(state && state.key.startsWith(specKey + '|'));
  React.useLayoutEffect(() => {
    const el = ref.current;
    if (!el) {
      // Loud, now — not a 30-second delayRender timeout naming nobody. The face is resolved off the anchor in the
      // shot's own CSS context (a DNA's variables, a terminal DNA's !important monospace), so without it there is
      // nothing honest to measure with.
      cancelRender(new Error('useKinetic: the handle\'s anchor was never mounted. Render <KineticText k={handle} …/> ' +
        '(or {handle.anchor}) in the same commit as the hook.'));
      return;
    }
    if (want.current === specKey) return;
    want.current = specKey;
    const resolved = resolveFont(el);
    const key = specKey + '|' + JSON.stringify(resolved);
    if (hold.current === null) {
      hold.current = delayRender('kinetic: re-measuring type', {timeoutInMilliseconds: 120000});
    }
    if (!busy.current) { busy.current = true; kineticBusy(1); }
    const hit = LAYOUTS.get(key);
    if (hit) { setState({key, lay: hit}); return; }
    facesReady().then(() => {
      if (want.current !== specKey) return;
      try {
        const lay = LAYOUTS.get(key) ?? measure(JSON.parse(specKey) as KSpec, resolved, key);
        if (LAYOUTS.size >= MAX_LAYOUTS) LAYOUTS.clear();
        LAYOUTS.set(key, lay);
        setState({key, lay});
      } catch (e) {
        cancelRender(e as Error);
      }
    }).catch((e) => cancelRender(e));
  });
  // released only once the glyphs for the CURRENT spec are committed — this runs after the render that drew them
  React.useEffect(() => {
    if (!ready) return;
    if (busy.current) { busy.current = false; kineticBusy(-1); }
    if (hold.current !== null) { continueRender(hold.current); hold.current = null; }
  }, [ready, state]);
  React.useEffect(() => () => {
    if (busy.current) { busy.current = false; kineticBusy(-1); }
    if (hold.current !== null) { continueRender(hold.current); hold.current = null; }
  }, []);
  const anchor = React.useMemo(() => (
    <span ref={ref} aria-hidden style={{position: 'absolute', width: 0, height: 0, overflow: 'hidden',
      fontFamily: spec.font.family}} />
  ), [spec.font.family]);
  return {layout: ready ? state!.lay : null, anchor, spec, key: specKey};
}

// ── what moves ───────────────────────────────────────────────────────────────────────────────────────────
/** A unit's state AT coverage 1 (the entrance's start / the exit's end). x, y, blur, tracking in em. */
export type KState = {x?: number; y?: number; scale?: number; rotate?: number; opacity?: number; blur?: number;
  tracking?: number; wght?: number; wdth?: number; color?: string;
  /** an offset in the unit's own MASK heights (GSAP's yPercent on a clip): 1 = one whole clip below, hidden in any
   *  script — a Latin line's box is ~1.2 em tall and a Chinese one ~1.45, so an offset in em that hides one shows
   *  the top of the other */
  ymask?: number};

export type KTiming = {
  /** the unit the sweep counts */
  by?: 'grapheme' | 'word' | 'line' | 'para';
  /** t (useT) at which the sweep starts */
  at?: number;
  /** seconds between consecutive units, and each unit's own duration */
  stagger?: number;
  dur?: number;
  /** seconds for the whole sweep — sets the stagger */
  total?: number;
  /** the t by which the last unit must have landed; a sweep that would overrun is compressed to it */
  until?: number;
  order?: Order;
  seed?: number;
  ease?: EaseName;
  /** the prop path the narration names, per paragraph (runtime/cue): a paragraph moves EARLIER to land on it */
  cueKeys?: (string | null)[];
  /** AE mode instead of a stagger: the range's offset sweeps `from`→`to` across [at, at + dur] */
  selector?: RangeSelector & {from: number; to: number};
};

export type KSwap = {
  mode: 'roll' | 'scramble' | 'flip' | 'cut';
  /** t at which the second alternative arrives, and the last (evenly between) — or `times`, each arrival's t */
  first: number; last: number;
  times?: number[];
  /** seconds a change takes, and between glyphs within it */
  turn?: number; stagger?: number;
  /** the prop path the narration names, per alternative — it may arrive EARLIER, onto its word */
  cueKeys?: (string | null)[];
  seed?: number;
};

export type KPath = {
  /** an SVG path in the box's own px */
  d: string;
  /** px along the path where the text's left edge rests */
  at: number;
  /** px the text travels to get there (it starts `travel` px earlier along the path) */
  travel?: number;
  enter?: KTiming;
  /** px per second it keeps moving after (a ring that turns) */
  speed?: number;
  /** a closed path filled with copies of the text, `gap` px apart; the copies wrap around */
  repeatGap?: number;
  /** px off the path, along its normal (negative = above) */
  lift?: number;
};

export type KMotion = {
  from?: KState;
  enter?: KTiming;
  exit?: KTiming & {to: KState};
  mask?: 'line' | 'word' | 'grapheme';
  /** em per second, the whole shot long — the big type that never stops */
  drift?: {x?: number; y?: number};
  swap?: KSwap;
  path?: KPath;
  /** colour sweep onto the `*emphasised*` run: at a t, or `after` seconds once the run itself has landed */
  emph?: {at?: number; after?: number; stagger?: number; dur?: number; ease?: EaseName;
    /** the weight the run thickens to as it lands — a reflow, so declare it in the spec's `axes.wght` */
    wght?: number;
    /** a rule under the run, drawn left to right as the colour lands (em) */
    underline?: {color: string; thickness?: number; offset?: number}};
  /** HELD TYPE STAYS ALIVE: what a line does once it has landed, eased in over 0.8 s from its landing (+ `delay` s).
   *  Every part is continuous in time and marks the glyph moving, so the baseline unlock (runtime/glide) is on and
   *  nothing steps a whole pixel. Restraint is the point — the defaults are a breath, not an animation. */
  idle?: KIdle;
};
export type KIdle = {
  /** tracking that swells and settles, em at the peak (0.004–0.012 reads as breath; more reads as a wobble) */
  breathe?: number;
  /** seconds per breath */
  period?: number;
  /** a light passing along the landed line: the ink lifts toward `color` under a band `width` (a share of the line)
   *  wide, crossing in `dur` s, once every `every` s, at most `strength` (0..1) */
  light?: {color: string; every?: number; dur?: number; width?: number; strength?: number};
  /** a slow travel once landed, em per second, its velocity eased in (no jolt) */
  drift?: {x?: number; y?: number};
  /** seconds after the line lands before any of it starts */
  delay?: number;
};

type GState = {x: number; y: number; scale: number; sy: number; rotate: number; opacity: number; blur: number;
  track: number; wght: number; wdth: number; mix: number; xmix: number; emix: number; vis: number; scr: ScrambleGlyph | null; lmix: number;
  moving: boolean;
  px: number; py: number; pr: number; onPath: boolean};

type Ctx = {t: number; fps: number; spanF: number; reduced: boolean; paraShift: number[]; swapT: number[] | null;
  frameNo: number; pathShift?: number};

const unitsOf = (alt: KAlt, by: KTiming['by']): {ids: number[]; n: number} => {
  const g = alt.glyphs;
  if (by === 'line') return {ids: g.map((x) => x.line), n: Math.max(1, alt.lines.length)};
  if (by === 'para') return {ids: g.map((x) => x.para), n: Math.max(1, Math.max(...g.map((x) => x.para)) + 1)};
  if (by === 'word') return {ids: g.map((x) => x.word), n: alt.words};
  // graphemes, spaces excluded — a space is not something the eye waits for (Framer counts the same way)
  const ids: number[] = [];
  let k = -1;
  g.forEach((x) => { if (!x.sp) k += 1; ids.push(Math.max(0, k)); });
  return {ids, n: Math.max(1, k + 1)};
};

/** Each unit's [a, b] window in t for a stagger timing — compressed to `until` when it would run over. */
const windows = (tm: KTiming, n: number, ctx: Ctx, paraOfUnit: number[]): [number, number][] => {
  const toT = (s: number) => secToT(s, ctx.spanF, ctx.fps);
  const ranks = Array.from({length: n}, (_, u) => orderRank(u, n, tm.order ?? 'forward', tm.seed ?? 1));
  const maxRank = Math.max(0, ...ranks);
  const dur = toT(tm.dur ?? 0.6);
  let st = tm.total !== undefined && maxRank > 0 ? toT(Math.max(0, tm.total - (tm.dur ?? 0.6))) / maxRank
    : toT(tm.stagger ?? 0.05);
  const at = tm.at ?? 0.1, until = tm.until ?? 0.95;
  let d = dur;
  if (at + maxRank * st + d > until) {
    const room = Math.max(0.02, until - at);
    if (d > room * 0.6) d = room * 0.6;
    st = maxRank > 0 ? Math.max(0, (room - d) / maxRank) : 0;
  }
  return ranks.map((r, u) => {
    const sh = ctx.paraShift[paraOfUnit[u] ?? 0] ?? 0;
    return [at + r * st + sh, at + r * st + d + sh];
  });
};

/** Every glyph's state at `ctx.t`. ONE function for the picture and for the hold report, so the report is the
 *  picture's own clock, not a model of it. */
const frameState = (lay: KLayout, m: KMotion, ctx: Ctx): GState[][] => {
  const {t, reduced} = ctx;
  const sz = lay.size;
  const pathL = m.path ? pathLUT(m.path.d).L : 0;
  return lay.alts.map((alt, ai) => {
    const N = alt.glyphs.length;
    const out: GState[] = alt.glyphs.map(() => ({x: 0, y: 0, scale: 1, sy: 1, rotate: 0, opacity: 1, blur: 0, track: 0,
      wght: 0, wdth: 0, mix: 0, xmix: 0, emix: 0, vis: 1, scr: null, lmix: 0, moving: false, px: 0, py: 0, pr: 0, onPath: true}));
    const from = m.from ?? {};
    const boxes = m.mask || m.swap ? maskBoxes(lay, ai, m) : null;
    const land: number[] = new Array(N).fill(-Infinity);
    const apply = (s: GState, st: KState, c: number, i: number, exit = false) => {
      if (st.x) s.x += st.x * c;
      if (st.y) s.y += st.y * c;
      if (st.ymask) {
        const b = boxes ? boxes[i] : {top: 0, bottom: lay.lh};
        s.y += (st.ymask * (b.bottom - b.top) / sz) * c;
      }
      if (st.scale !== undefined) s.scale *= 1 + (st.scale - 1) * c;
      if (st.rotate) s.rotate += st.rotate * c;
      if (st.opacity !== undefined) s.opacity *= clamp01(1 + (st.opacity - 1) * c);
      if (st.blur) s.blur += Math.max(0, st.blur * c);
      if (st.tracking) s.track += st.tracking * c;
      if (st.wght !== undefined) s.wght += (st.wght - lay.weight) * c;
      if (st.wdth !== undefined) s.wdth += (st.wdth - lay.stretch) * c;
      if (st.color && exit) s.xmix = Math.max(s.xmix, clamp01(c));
      else if (st.color) s.mix = Math.max(s.mix, clamp01(c));
      if (c > 0 && c < 1) s.moving = true;
    };
    // 1. entrance (and exit) coverage
    const swapOnly = Boolean(m.swap) && ai > 0;
    const doUnits = (tm: KTiming | undefined, st: KState, invert: boolean) => {
      if (!tm || reduced) return;
      const {ids, n} = unitsOf(alt, tm.by ?? 'grapheme');
      const paraOfUnit: number[] = [];
      alt.glyphs.forEach((g, i) => { if (paraOfUnit[ids[i]] === undefined) paraOfUnit[ids[i]] = g.para; });
      const ease = easeOf(tm.ease ?? 'expo');
      let cov: (u: number) => number;
      let landOf: (u: number) => number;
      if (tm.selector) {
        const sel = tm.selector;
        const end = (tm.at ?? 0.1) + secToT(tm.dur ?? 1, ctx.spanF, ctx.fps);
        const p = ease(clamp01((t - (tm.at ?? 0.1)) / Math.max(1e-6, end - (tm.at ?? 0.1))));
        const perm = sel.randomize ? permutation(n, sel.seed ?? 1) : null;
        const offset = sel.from + (sel.to - sel.from) * p;
        cov = (u) => rangeCoverage({...sel, offset}, perm ? perm[u] : u, n);
        landOf = () => end;
      } else {
        const win = windows(tm, n, ctx, paraOfUnit);
        cov = (u) => { const [a, b] = win[u]; return 1 - ease(clamp01((t - a) / Math.max(1e-6, b - a))); };
        landOf = (u) => win[u][1];
      }
      alt.glyphs.forEach((_, i) => {
        const c = cov(ids[i]);
        apply(out[i], st, invert ? 1 - c : c, i, invert);
        if (!invert) land[i] = landOf(ids[i]);
      });
    };
    if (!swapOnly) doUnits(m.enter, from, false);
    if (m.exit) doUnits(m.exit, m.exit.to, true);
    // 2. the emphasised run's colour lands
    if (m.emph && !reduced) {
      const e = m.emph, ease = easeOf(e.ease ?? 'inOut');
      let k = 0, start = 0;
      alt.glyphs.forEach((g, i) => {
        if (!g.emph) { k = 0; return; }
        if (k === 0) {
          // each run starts on its own landing (its first glyph's), or at the given t
          start = e.at ?? (Number.isFinite(land[i]) ? land[i] : 0) + secToT(e.after ?? 0.25, ctx.spanF, ctx.fps);
        }
        const a = start + secToT((e.stagger ?? 0.03) * k, ctx.spanF, ctx.fps);
        out[i].emix = ease(clamp01((t - a) / Math.max(1e-6, secToT(e.dur ?? 0.35, ctx.spanF, ctx.fps))));
        if (e.wght !== undefined) {
          out[i].wght += (e.wght - lay.emphWeight) * out[i].emix;
          if (out[i].emix > 0 && out[i].emix < 1) out[i].moving = true;
        }
        k += g.sp ? 0 : 1;
      });
    } else {
      alt.glyphs.forEach((g, i) => { out[i].emix = g.emph ? 1 : 0; });
    }
    // 3. swaps: which alternative holds the slot, and how it changes
    if (m.swap && ctx.swapT) {
      const T = ctx.swapT, n = lay.alts.length, sw = m.swap;
      const turn = secToT(sw.turn ?? 0.42, ctx.spanF, ctx.fps), stg = secToT(sw.stagger ?? 0.03, ctx.spanF, ctx.fps);
      const tIn = ai === 0 ? -Infinity : T[ai], tOut = ai + 1 < n ? T[ai + 1] : Infinity;
      const final = reduced ? n - 1 : -1;
      const roll = lay.lh / sz * 1.04;
      let k = 0;
      alt.glyphs.forEach((g, i) => {
        const s = out[i];
        const r = g.sp ? k : k++;
        if (reduced) { if (ai !== final) s.opacity = 0; return; }
        const pin = tIn === -Infinity ? 1 : easeOf('stripe')(clamp01((t - tIn - r * stg) / Math.max(1e-6, turn)));
        const pout = tOut === Infinity ? 0 : easeOf('stripe')(clamp01((t - tOut - r * stg) / Math.max(1e-6, turn)));
        const live = (pin > 0 && pin < 1) || (pout > 0 && pout < 1);
        if (live) s.moving = true;
        if (sw.mode === 'cut') {
          if (t < tIn || t >= tOut) s.opacity = 0;
        } else if (sw.mode === 'roll') {
          s.y += (1 - pin) * roll - pout * roll;
          if (pin <= 0 || pout >= 1) s.opacity = 0;
          // a little motion blur at the roll's fastest point, none at either end (measured by eye: 0.035 em smeared a
          // 170px word into a band; 0.018 reads as speed)
          s.blur += 0.018 * Math.sin(Math.PI * pin) + 0.018 * Math.sin(Math.PI * pout);
        } else if (sw.mode === 'flip') {
          const a = clamp01((pin - 0.5) * 2), b = clamp01(pout * 2);
          s.sy *= tIn === -Infinity ? 1 - b : a * (1 - b);
          if (s.sy <= 0.001) s.opacity = 0;
          s.opacity *= 0.55 + 0.45 * s.sy;
        } else {
          // scramble: stand-ins that can never spell a word (kineticCore scrambleGlyph — blocks or the right glyph at
          // another weight for CJK, symbols for everything else), resolving left to right
          const step = Math.floor(ctx.frameNo / 2);
          const resolved = tIn === -Infinity || t >= tIn + r * stg + turn * 0.7;
          const arrived = tIn === -Infinity || t >= tIn + r * stg * 0.4;
          if (!arrived) s.opacity = 0;
          if (!resolved && !g.sp) s.scr = scrambleGlyph(g.g, (sw.seed ?? 7) + ai, i, step);
          if (pout > 0) {
            if (!g.sp && pout < 1) s.scr = scrambleGlyph(g.g, (sw.seed ?? 7) + ai + 50, i, step);
            s.opacity *= clamp01(1 - pout * 1.6);
          }
        }
      });
    }
    // 4. a mask makes a unit visible only inside its own box
    if (boxes) {
      alt.glyphs.forEach((g, i) => {
        const s = out[i];
        const top = g.y + g.dy + s.y * sz, h = Math.max(1, g.h * s.scale * s.sy);
        const L = boxes[i];
        const ov = Math.max(0, Math.min(top + h, L.bottom) - Math.max(top, L.top));
        s.vis = clamp01(ov / h);
      });
    }
    // 5. drift and the path
    if (m.drift && !reduced) {
      const sec = tToSec(t, ctx.spanF, ctx.fps);
      out.forEach((s) => { s.x += (m.drift!.x ?? 0) * sec; s.y += (m.drift!.y ?? 0) * sec; s.moving = true; });
    }
    // 6. HELD TYPE STAYS ALIVE (m.idle): once its LINE has landed (the latest of its glyphs), a micro tracking
    //    breathe, a light passing along it and a drift, each eased in — one line moves as one, never glyph by glyph
    if (m.idle && !reduced) {
      const I = m.idle, sec = tToSec(t, ctx.spanF, ctx.fps);
      const lineLand: number[] = [];
      alt.glyphs.forEach((g, i) => { lineLand[g.line] = Math.max(lineLand[g.line] ?? -Infinity, land[i]); });
      const per = Math.max(0.5, I.period ?? 3.2), RAMP = 0.8;
      const lw = Math.max(0.05, I.light?.width ?? 0.22), ldur = Math.max(0.2, I.light?.dur ?? 1.1);
      const every = Math.max(ldur, I.light?.every ?? 3.0);
      // the unlock's SPAN is the whole shot for a line that breathes or drifts (runtime/glide: switched on with the
      // motion itself, the type would jump from whole-pixel to quarter-pixel on the frame the idle starts)
      const span = Boolean(I.breathe || I.drift);
      alt.glyphs.forEach((g, i) => {
        const s = out[i];
        if (span) s.moving = true;
        const L0 = lineLand[g.line];
        const since = sec - (Number.isFinite(L0) ? tToSec(L0, ctx.spanF, ctx.fps) : 0) - (I.delay ?? 0.15);
        if (since <= 0) return;
        const r = since >= RAMP ? 1 : (since / RAMP) * (since / RAMP) * (3 - 2 * (since / RAMP));
        if (I.breathe) {
          s.track += I.breathe * r * (0.5 - 0.5 * Math.cos((2 * Math.PI * since) / per));
        }
        if (I.drift) {
          const d = since < RAMP ? (since * since) / (2 * RAMP) : since - RAMP / 2;   // the velocity ramps in
          s.x += (I.drift.x ?? 0) * d; s.y += (I.drift.y ?? 0) * d;
        }
        if (I.light && !g.sp) {
          const L = alt.lines[g.line];
          const u = (g.left + g.adv / 2 - L.left) / Math.max(1, L.right - L.left);
          const cyc = since % every;
          if (cyc < ldur) {
            const pos = -lw + (cyc / ldur) * (1 + 2 * lw);
            const k = clamp01(1 - Math.abs(u - pos) / lw);
            s.lmix = clamp01(I.light.strength ?? 0.5) * k * k * (3 - 2 * k) * r;
          }
        }
      });
    }
    if (m.path) {
      const P = m.path;
      let c = 0;
      if (P.enter && !reduced) {
        const e = easeOf(P.enter.ease ?? 'power3');
        const a = P.enter.at ?? 0.1, d = secToT(P.enter.dur ?? 1.6, ctx.spanF, ctx.fps);
        c = 1 - e(clamp01((t - a) / Math.max(1e-6, d)));
      }
      const spin = reduced ? 0 : (P.speed ?? 0) * Math.max(0, tToSec(t, ctx.spanF, ctx.fps));
      const x0 = alt.lines[0]?.left ?? 0;
      alt.glyphs.forEach((g, i) => {
        const s = out[i];
        let along = P.at - (P.travel ?? 0) * c + spin + (g.left - x0) + g.adv / 2 + s.x * sz + (ctx.pathShift ?? 0);
        if (P.repeatGap !== undefined && pathL > 0) {
          along = ((along % pathL) + pathL) % pathL;
        }
        s.onPath = along >= 0 && along <= pathL;
        if (!s.onPath) { s.opacity = 0; return; }
        const p = alongAt(P.d, along), th = p.deg;
        const nx = -Math.sin((th * Math.PI) / 180), ny = Math.cos((th * Math.PI) / 180);
        s.px = p.x + nx * ((P.lift ?? 0) + s.y * sz);
        s.py = p.y + ny * ((P.lift ?? 0) + s.y * sz);
        s.pr = th;
        if (c > 0 && c < 1) s.moving = true;
        if (spin) s.moving = true;
      });
    }
    return out;
  });
};

// A PATH, SAMPLED ONCE BY ARC LENGTH. Every glyph on a path asks for a point and a tangent every frame, and the hold
// report asks for every frame of the clip; so each path is walked once into a table (2048 steps — under a pixel
// apart on any path that fits a frame) and read by linear interpolation: the same numbers on every frame, cold or
// warm.
//
// THE WALK IS THE BROWSER'S OWN, NOT @remotion/paths'. Measured on a 1710px cubic (TypeOnPath's `rise`): its
// getPointAtLength went BACKWARDS 45 times in 2048 steps, by up to 2.3px, with steps up to 4.0px where 0.83 was due —
// the points lie on the curve but jitter along it, so letters were spaced unevenly and one glyph whose neighbours'
// order flipped was drawn upside down under the line. Its getTangentAtLength is also REVERSED on arc commands. The
// SVG engine's own arc length is exact, so it is used wherever there is a DOM; the library is the fallback for node.
const PATHS = new Map<string, {L: number; xs: Float64Array; ys: Float64Array; tx: Float64Array; ty: Float64Array}>();
const PATH_STEPS = 2048;
const pathLUT = (d: string) => {
  const hit = PATHS.get(d);
  if (hit) return hit;
  const xs = new Float64Array(PATH_STEPS + 1), ys = new Float64Array(PATH_STEPS + 1);
  const tx = new Float64Array(PATH_STEPS + 1), ty = new Float64Array(PATH_STEPS + 1);
  let L: number;
  const el = typeof document !== 'undefined'
    ? (document.createElementNS('http://www.w3.org/2000/svg', 'path') as SVGPathElement) : null;
  if (el) {
    el.setAttribute('d', d);
    L = el.getTotalLength();
    for (let k = 0; k <= PATH_STEPS; k++) {
      const p = el.getPointAtLength((L * k) / PATH_STEPS);
      xs[k] = p.x; ys[k] = p.y;
    }
  } else {
    L = getLength(d);
    for (let k = 0; k <= PATH_STEPS; k++) {
      const p = getPointAtLength(d, (L * k) / PATH_STEPS);
      xs[k] = p.x; ys[k] = p.y;
    }
  }
  // the tangent from the points (a few steps either side), never asked of the library: see above
  for (let k = 0; k <= PATH_STEPS; k++) {
    const a = Math.max(0, k - 3), b = Math.min(PATH_STEPS, k + 3);
    const vx = xs[b] - xs[a], vy = ys[b] - ys[a], n = Math.hypot(vx, vy) || 1;
    tx[k] = vx / n; ty[k] = vy / n;
  }
  if (PATHS.size >= 64) PATHS.clear();
  const v = {L, xs, ys, tx, ty};
  PATHS.set(d, v);
  return v;
};
/** A path's arc length as the glyphs on it are placed by — a register sizing type to a path asks this, not another
 *  library, so the two cannot disagree. */
export const kineticPathLength = (d: string): number => pathLUT(d).L;
/** Point and direction (degrees) `s` px along `d`. */
const alongAt = (d: string, s: number): {x: number; y: number; deg: number} => {
  const P = pathLUT(d);
  const u = Math.max(0, Math.min(1, s / Math.max(1e-9, P.L))) * PATH_STEPS;
  const k = Math.min(PATH_STEPS - 1, Math.floor(u)), f = u - k;
  const x = P.xs[k] + (P.xs[k + 1] - P.xs[k]) * f, y = P.ys[k] + (P.ys[k + 1] - P.ys[k]) * f;
  const vx = P.tx[k] + (P.tx[k + 1] - P.tx[k]) * f, vy = P.ty[k] + (P.ty[k + 1] - P.ty[k]) * f;
  return {x, y, deg: (Math.atan2(vy, vx) * 180) / Math.PI};
};

// Mask boxes depend only on the layout, the mask kind and the glyph — never on the frame — so they are computed once
// per layout: the word mask walks the line for each glyph, which per frame per glyph is quadratic.
const MASKS = new Map<string, {top: number; bottom: number; left: number; right: number}[]>();
const maskBoxes = (lay: KLayout, ai: number, m: KMotion) => {
  const key = `${lay.key}|${ai}|${m.swap ? 'swap' : m.mask ?? ''}`;
  const hit = MASKS.get(key);
  if (hit) return hit;
  const v = lay.alts[ai].glyphs.map((g) => maskBox(lay, ai, g, m));
  if (MASKS.size >= 256) MASKS.clear();
  MASKS.set(key, v);
  return v;
};

/** A scramble block inside a CJK glyph's ideographic em box (baseline - 0.88 em to baseline + 0.12 em, inset 7%), in
 *  holder px: full, lower half, upper half, outline (drawn as a border), left half. */
const scrambleBlock = (shape: number, w: number, base: number, sz: number) => {
  const left = w * 0.07, top = base - 0.88 * sz + sz * 0.07, bw = w * 0.86, bh = sz * 0.86;
  if (shape === 1) return {left, top: top + bh / 2, width: bw, height: bh / 2};
  if (shape === 2) return {left, top, width: bw, height: bh / 2};
  if (shape === 4) return {left, top, width: bw / 2, height: bh};
  return {left, top, width: bw, height: bh};
};

/** The box a glyph is visible inside under its mask: its line's, word's or own, padded so nothing at REST is cut. */
const maskBox = (lay: KLayout, ai: number, g: KGlyph, m: KMotion): {top: number; bottom: number; left: number;
  right: number} => {
  const sz = lay.size, padY = sz * 0.08, padX = sz * 0.16;
  if (m.swap) {
    // a swap's slot is the union of every alternative's line box at that line index
    let top = Infinity, bottom = -Infinity;
    for (const a of lay.alts) {
      const L = a.lines[g.line];
      if (L) { top = Math.min(top, L.top); bottom = Math.max(bottom, L.bottom); }
    }
    return {top: top - padY, bottom: bottom + padY, left: -padX, right: lay.boxW + padX};
  }
  const alt = lay.alts[ai];
  if (m.mask === 'grapheme') return {top: g.y + g.dy - padY, bottom: g.y + g.dy + g.h + padY, left: g.left - padX,
    right: g.left + g.w + padX};
  if (m.mask === 'word') {
    let top = Infinity, bottom = -Infinity, left = Infinity, right = -Infinity;
    alt.glyphs.forEach((o) => {
      if (o.word !== g.word || o.line !== g.line || o.sp) return;
      top = Math.min(top, o.y + o.dy); bottom = Math.max(bottom, o.y + o.dy + o.h);
      left = Math.min(left, o.left); right = Math.max(right, o.left + o.w);
    });
    return {top: top - padY, bottom: bottom + padY, left: left - padX, right: right + padX};
  }
  const L = alt.lines[g.line];
  return {top: L.top - padY, bottom: L.bottom + padY, left: -padX, right: lay.boxW + padX};
};

/** Axis value → advance, piecewise-linear between the measured anchors. */
const advAt = (an: KAxisAnchors | undefined, ai: number, i: number, v: number, rest: number): number => {
  if (!an) return rest;
  const vs = an.v, row = an.adv[ai];
  if (vs.length === 1) return row[0][i];
  const k = Math.max(0, Math.min(vs.length - 2, vs.findIndex((x, j) => j + 1 < vs.length && v <= vs[j + 1])));
  const f = (v - vs[k]) / Math.max(1e-9, vs[k + 1] - vs[k]);
  return row[k][i] + (row[k + 1][i] - row[k][i]) * f;
};

// ── the component ────────────────────────────────────────────────────────────────────────────────────────
export type KineticTextProps = {
  k: KineticHandle;
  /** where the box's top-left sits in the register, px */
  x: number; y: number;
  color: string;
  emphColor?: string;
  /** the colour a unit has at coverage 1, when `from.color` is set */
  motion?: KMotion;
  /** the copy must be READ: a gate holds its hold to its reading time (scripts/shot_proof.py) */
  read?: boolean;
  /** id for the census (defaults to the copy) */
  id?: string;
  style?: React.CSSProperties;
};

export const KineticText: React.FC<KineticTextProps> = ({k, x, y, color, emphColor, motion = {}, read = true, id,
  style}) => {
  const t = useT();
  const {fps, durationInFrames} = useVideoConfig();
  const spanF = useAnimSpan();
  const sceneDur = React.useContext(SceneDurationContext);
  const reduced = React.useContext(ReducedMotionContext);
  const allowed = React.useContext(BaselineUnlockContext);
  const glide = useGlide();
  const cue = useCues();
  const report = React.useContext(KineticHoldContext);
  const lay = k.layout;
  const m = motion;

  // cue shifts — computed with the hook here, then handed to the pure state function as numbers
  const paraShift = React.useMemo(() => {
    const keys = m.enter?.cueKeys;
    if (!lay || !keys || !m.enter) return [];
    const alt = lay.alts[0];
    const by = m.enter.by ?? 'grapheme';
    const {ids, n} = unitsOf(alt, by);
    const paraOfUnit: number[] = [];
    alt.glyphs.forEach((g, i) => { if (paraOfUnit[ids[i]] === undefined) paraOfUnit[ids[i]] = g.para; });
    const base = windows(m.enter, n, {t: 0, fps, spanF, reduced, paraShift: [], swapT: null, frameNo: 0}, paraOfUnit);
    return keys.map((key, p) => {
      const u = paraOfUnit.indexOf(p);
      if (!key || u < 0) return 0;
      const [a, b] = base[u];
      const [a2] = cue.win(key, a, b, REACH_CUBIC);
      return a2 - a;
    });
  }, [lay, m.enter, fps, spanF, reduced, cue]);
  const swapT = React.useMemo(() => {
    if (!lay || !m.swap) return null;
    const keys = m.swap.cueKeys;
    return swapTimes(lay.alts.length, m.swap.first, m.swap.last, keys?.map((kk) => (kk ? cue.readT(kk) : null)),
      m.swap.times);
  }, [lay, m.swap, cue]);
  const frameNo = Math.round(((t - 0.06) / 0.94) * spanF);

  // the hold report (only when a gate asked for it): every frame of the clip, through the same state function
  React.useLayoutEffect(() => {
    if (!report || !lay || !read) return;
    const dur = sceneDur ?? durationInFrames;
    const pad = Math.min(12, Math.floor(Math.max(0, dur - 1) / 3));
    const lines: Map<string, boolean[]> = new Map();
    const alts: boolean[][] = lay.alts.map(() => []);
    for (let f = 0; f <= dur - 1 - pad; f++) {
      const tf = reduced ? REDUCED_MOTION_T : tAtFrame(f, dur);
      const st = frameState(lay, m, {t: tf, fps, spanF, reduced, paraShift, swapT,
        frameNo: Math.round(((tf - 0.06) / 0.94) * spanF)});
      lay.alts.forEach((alt, ai) => {
        const ok = (g: KGlyph, s: GState) => g.sp || (s.opacity >= 0.5 && s.vis >= 0.5 && !s.scr && s.sy >= 0.5);
        alts[ai].push(alt.glyphs.every((g, i) => ok(g, st[ai][i])));
        if (lay.alts.length === 1) {
          alt.lines.forEach((L, li) => {
            const key = String(li);
            const arr = lines.get(key) ?? [];
            let all = true;
            for (let i = L.first; i <= L.last; i++) if (!ok(alt.glyphs[i], st[ai][i])) { all = false; break; }
            arr.push(all);
            lines.set(key, arr);
          });
        }
      });
    }
    const recs: HoldRecord[] = [];
    const rec = (text: string, frames: boolean[], kind: HoldRecord['kind']) => {
      const lang = lay.lang;
      recs.push({text, kind, hold: longestRun(frames) / fps, chars: graphemes(text.replace(/\s+/g, '')).length,
        words: wordCount(text, lang), lang});
    };
    if (lay.alts.length > 1) lay.alts.forEach((a, ai) => rec(a.text, alts[ai], 'alt'));
    else {
      lay.alts[0].lines.forEach((L, li) => rec(L.text, lines.get(String(li)) ?? [], 'line'));
      const any = (lines.get('0') ?? []).map((_, f) => lay.alts[0].lines.some((_L, li) => (lines.get(String(li)) ?? [])[f]));
      const first = any.indexOf(true), last = any.lastIndexOf(true);
      // the BLOCK only when there is more than one line: one line's block is that line, reported twice
      if (lay.alts[0].lines.length > 1) recs.push({text: lay.alts[0].text.replace(/\n/g, ' '), kind: 'block',
        hold: first < 0 ? 0 : (last - first + 1) / fps,
        chars: graphemes(lay.alts[0].text.replace(/\s+/g, '')).length, words: wordCount(lay.alts[0].text, lay.lang),
        lang: lay.lang});
    }
    report({id: id ?? lay.alts.map((a) => a.text).join(' | ').slice(0, 60), frames: dur, fps, texts: recs});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report, lay, read]);

  const sz = lay?.size ?? k.spec.font.size;
  const box: React.CSSProperties = {position: 'absolute', left: x, top: y, width: k.spec.w,
    height: lay ? lay.boxH : k.spec.h, pointerEvents: 'none', ...style};
  const rootAttrs = {[KIN_ROOT]: id ?? 'k', [KIN_READ]: read ? '1' : '0', [KIN_ALIGN]: k.spec.align ?? 'left'};
  if (!lay) return <div {...rootAttrs} style={box}>{k.anchor}</div>;

  if ((m.emph?.wght !== undefined || m.from?.wght !== undefined || m.exit?.to.wght !== undefined) && !lay.axes.wght) {
    throw new Error('KineticText: the motion morphs the weight, which reflows the line, but the spec declares no ' +
      '`axes.wght` range to measure it at. Add `axes: {wght: [lo, hi]}` to useKinetic.');
  }
  if ((m.from?.wdth !== undefined || m.exit?.to.wdth !== undefined) && !lay.axes.wdth) {
    throw new Error('KineticText: the motion morphs the width (wdth), which reflows the line, but the spec declares ' +
      'no `axes.wdth` range. Add `axes: {wdth: [lo, hi]}` to useKinetic.');
  }
  // A RING OF WORDS: copies of the phrase, one PERIOD apart along a closed path, the period spread evenly so the
  // last copy meets the first with the same gap as every other pair
  const ringPeriod = (() => {
    if (!m.path || m.path.repeatGap === undefined) return 0;
    const L = pathLUT(m.path.d).L, one = lay.alts[0].width + m.path.repeatGap;
    return one > 0 ? L / Math.max(1, Math.floor(L / one)) : 0;
  })();
  const copies = ringPeriod > 0 ? Math.max(1, Math.round(pathLUT(m.path!.d).L / ringPeriod)) : 1;
  const sts = Array.from({length: copies}, (_, c) =>
    frameState(lay, m, {t, fps, spanF, reduced, paraShift, swapT, frameNo, pathShift: c * ringPeriod}));
  const st = sts[0];
  const fromColor = m.from?.color;
  const lightColor = m.idle?.light?.color;
  const exitColor = m.exit?.to.color;
  const ec = emphColor ?? color;
  const nodes: React.ReactNode[] = [];
  sts.forEach((stc, copy) => lay.alts.forEach((alt, ai) => {
    const st = stc;
    // the reflowed pens: an axis morph or a tracking move changes advances, so each line is re-laid from its start
    const reflow = alt.glyphs.some((_, i) => st[ai][i].wght || st[ai][i].wdth || st[ai][i].track);
    const pen = alt.glyphs.map((g) => g.left);
    if (reflow) {
      alt.lines.forEach((L) => {
        let w = 0;
        const advs: number[] = [];
        for (let i = L.first; i <= L.last; i++) {
          const g = alt.glyphs[i], s = st[ai][i];
          const restW = g.emph ? lay.emphWeight : lay.weight;
          let a = g.adv;
          if (s.wght) a += advAt(lay.axes.wght, ai, i, restW + s.wght, g.adv) - advAt(lay.axes.wght, ai, i, restW, g.adv);
          if (s.wdth) a += advAt(lay.axes.wdth, ai, i, lay.stretch + s.wdth, g.adv) -
            advAt(lay.axes.wdth, ai, i, lay.stretch, g.adv);
          a += s.track * sz;
          advs.push(a);
          w += a;
        }
        // re-laid from the line's own REST pens: the change in width is shared out by the alignment, so with nothing
        // changed every glyph is exactly where it rests. (Measured from the ink extent instead, a centred line with a
        // trailing space jumped half that space the moment any glyph's advance moved off its rest value.)
        let wRest = 0;
        for (let i = L.first; i <= L.last; i++) wRest += alt.glyphs[i].adv;
        const p0 = alt.glyphs[L.first]?.left ?? L.left;
        const start = lay.align === 'center' ? p0 + (wRest - w) / 2 : lay.align === 'right' ? p0 + (wRest - w) : p0;
        let p = start;
        for (let i = L.first; i <= L.last; i++) { pen[i] = p; p += advs[i - L.first]; }
      });
    }
    const glyph = (g: KGlyph, i: number, ox: number, oy: number) => {
      const s = st[ai][i];
      const hx = g.x - ox, hy = g.y - oy;
      const ty = s.y * sz, tx = s.x * sz + (pen[i] - g.left);
      let tf: string;
      const ox0 = g.adv / 2, oy0 = g.dy + g.h / 2;
      if (m.path) {
        const dx = s.px - (g.x + g.adv / 2), dy = s.py - (g.y + g.base);
        tf = `translate(${dx}px, ${dy}px) rotate(${s.pr + s.rotate}deg) scale(${s.scale}, ${s.scale * s.sy})`;
      } else {
        const parts: string[] = [];
        if (tx || ty) parts.push(`translate(${tx}px, ${ty}px)`);
        if (s.rotate) parts.push(`rotate(${s.rotate}deg)`);
        if (s.scale !== 1 || s.sy !== 1) parts.push(`scale(${s.scale}, ${s.scale * s.sy})`);
        tf = parts.join(' ');
      }
      const restW = g.emph ? lay.emphWeight : lay.weight;
      const ink0 = g.emph ? (s.emix >= 1 ? ec : s.emix <= 0 ? color : `color-mix(in oklab, ${ec} ${(s.emix * 100).toFixed(1)}%, ${color})`) : color;
      let ink = ink0;
      if (fromColor && s.mix > 0) ink = `color-mix(in oklab, ${fromColor} ${(s.mix * 100).toFixed(1)}%, ${ink0})`;
      if (exitColor && s.xmix > 0) ink = `color-mix(in oklab, ${exitColor} ${(s.xmix * 100).toFixed(1)}%, ${ink})`;
      if (lightColor && s.lmix > 0.001) ink = `color-mix(in oklab, ${lightColor} ${(s.lmix * 100).toFixed(1)}%, ${ink})`;
      const blurPx = s.blur * sz;
      // a scramble's stand-in: a block drawn as a box inside the glyph's own em (never a character), the right glyph
      // at another weight, or a symbol centred on the glyph's advance (kineticCore scrambleGlyph)
      const sc = s.scr;
      const face: React.ReactNode = !sc ? g.g : sc.kind === 'weight' ? g.g : sc.kind === 'symbol' ? (
        <span style={{display: 'inline-block', width: Math.max(1, g.adv), textAlign: 'center'}}>{sc.ch}</span>
      ) : (
        <span style={{display: 'inline-block', position: 'relative', width: Math.max(1, g.w), height: 0,
          verticalAlign: 'top'}}>
          <span style={{position: 'absolute', ...scrambleBlock(sc.shape, g.w, g.base, sz), background:
            sc.shape === 3 ? undefined : 'currentColor', border: sc.shape === 3 ? `${Math.max(1.5, sz * 0.06)
            .toFixed(2)}px solid currentColor` : undefined, boxSizing: 'border-box'}} />
        </span>
      );
      const under = Math.max(0.05, Math.abs(s.scale * s.sy));
      const attrs: Record<string, string> = {[KIN_LINE]: String(g.line),
        [KIN_GLYPH]: String(i + copy * alt.glyphs.length)};
      if (lay.alts.length > 1) attrs[KIN_ALT] = String(ai);
      return (
        <span key={`${copy}-${ai}-${i}`} style={{position: 'absolute', left: hx, top: hy,
          transformOrigin: m.path ? `${ox0}px ${g.base}px` : `${ox0}px ${oy0}px`,
          transform: tf || undefined, opacity: s.opacity >= 0.999 ? undefined : s.opacity,
          filter: blurPx > 0.05 ? `blur(${blurPx.toFixed(2)}px)` : undefined}}>
          <span {...attrs} style={{display: 'block', color: ink,
            fontWeight: sc?.kind === 'weight' ? sc.weight : s.wght ? restW + s.wght : g.emph ? lay.emphWeight : undefined,
            fontStretch: s.wdth ? `${lay.stretch + s.wdth}%` : undefined,
            transform: glide(undefined, allowed && s.moving, under),
            ...({textSpacingTrim: g.trim ? 'trim-start' : 'space-all'} as React.CSSProperties)}}>
            {face}
          </span>
        </span>
      );
    };
    if (m.mask || m.swap) {
      // one clip per line / word / glyph; its children are placed relative to it
      const groups = new Map<string, {box: {top: number; bottom: number; left: number; right: number}; idx: number[]}>();
      alt.glyphs.forEach((g, i) => {
        const key = m.swap ? `l${g.line}` : m.mask === 'grapheme' ? `g${i}` : m.mask === 'word' ? `w${g.word}-${g.line}`
          : `l${g.line}`;
        const grp = groups.get(key) ?? {box: maskBoxes(lay, ai, m)[i], idx: []};
        grp.idx.push(i);
        groups.set(key, grp);
      });
      groups.forEach((grp, key) => {
        const b = grp.box;
        nodes.push(
          <div key={`${copy}-${ai}-${key}`} style={{position: 'absolute', left: b.left, top: b.top, width: b.right - b.left,
            height: b.bottom - b.top, overflow: 'hidden'}}>
            {grp.idx.map((i) => glyph(alt.glyphs[i], i, b.left, b.top))}
          </div>,
        );
      });
    } else {
      alt.glyphs.forEach((g, i) => nodes.push(glyph(g, i, 0, 0)));
    }
  }));
  // the rule under the emphasised run: drawn left to right as its colour lands, riding with the run's own offset
  const ul = m.emph?.underline;
  if (ul && lay.alts.length === 1) {
    emphBoxes(lay, 0).forEach((b) => {
      const gs = lay.alts[0].glyphs.map((g, i) => ({g, s: st[0][i]})).filter(({g}) => g.emph && !g.sp && g.line === b.line);
      if (!gs.length) return;
      const p = gs.reduce((acc, q) => acc + q.s.emix, 0) / gs.length;
      const dy = (gs.reduce((acc, q) => acc + q.s.y, 0) / gs.length) * sz;
      nodes.push(
        <div key={`ul-${b.line}`} style={{position: 'absolute', left: b.left, width: b.right - b.left,
          top: b.baseline + (ul.offset ?? 0.12) * sz + dy, height: Math.max(2, (ul.thickness ?? 0.055) * sz),
          background: ul.color, transformOrigin: '0 50%', transform: `scaleX(${clamp01(p)})`,
          opacity: p > 0.001 ? 1 : 0}} />,
      );
    });
  }
  return (
    <div {...rootAttrs} lang={lay.lang} style={{...box, fontFamily: lay.family, fontSize: `${lay.size}px`,
      lineHeight: `${lay.lh}px`, fontWeight: lay.weight, fontStyle: lay.italic ? 'italic' : 'normal',
      fontStretch: `${lay.stretch}%`, fontVariantLigatures: 'none', letterSpacing: 0, whiteSpace: 'pre', color}}>
      {k.anchor}
      {nodes}
    </div>
  );
};

/** The emphasised run's boxes on each line it spans (box px) — for a register drawing a rule or a mark under it. */
export const emphBoxes = (lay: KLayout | null, ai = 0): {line: number; left: number; right: number; top: number;
  bottom: number; baseline: number}[] => {
  if (!lay) return [];
  const out = new Map<number, {line: number; left: number; right: number; top: number; bottom: number; baseline: number}>();
  lay.alts[ai].glyphs.forEach((g) => {
    if (!g.emph || g.sp || g.w <= 0) return;
    const b = out.get(g.line) ?? {line: g.line, left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity,
      baseline: g.y + g.base};
    b.left = Math.min(b.left, g.left); b.right = Math.max(b.right, g.left + g.w);
    b.top = Math.min(b.top, g.y + g.dy); b.bottom = Math.max(b.bottom, g.y + g.dy + g.h);
    out.set(g.line, b);
  });
  return Array.from(out.values());
};

// ── the hold report (scripts/shot_proof.py asks for it) ─────────────────────────────────────────────────
export type HoldRecord = {text: string; kind: 'line' | 'alt' | 'block'; hold: number; chars: number; words: number;
  lang: string};
export type HoldReport = {id: string; frames: number; fps: number; texts: HoldRecord[]};
export const KineticHoldContext = React.createContext<((r: HoldReport) => void) | null>(null);

/**
 * Armed by `kineticHolds: true` (Root.tsx). Waits for every KineticText to be measured, then cancels the render with
 * each one's holds — how long each must-read line, alternative and block is READABLE (opacity and visible share at
 * least a half: the sync audit's own "appeared"), walked frame by frame through the picture's own state function at
 * the composition's length. The verdict (reading time per script) is the gate's, in Python, beside the caption rule.
 */
export const KineticHoldAudit: React.FC<{reports: HoldReport[]}> = ({reports}) => {
  const [handle] = React.useState(() => delayRender('kinetic hold audit', {timeoutInMilliseconds: 60000}));
  React.useEffect(() => {
    let dead = false;
    (async () => {
      try { await facesReady(); } catch { /* the font gate reports that */ }
      await kineticIdle();
      if (dead) return;
      cancelRender(new Error(KINETIC_HOLDS_TAG + JSON.stringify({reports})));
      void handle;
    })();
    return () => { dead = true; };
  }, [handle, reports]);
  return null;
};
