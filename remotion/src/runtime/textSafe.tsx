// TEXT-SAFE AUDIT — does any TYPE fall off the canvas? Asked of the DOM, not of pixels.
//
// WHY THIS IS NOT A PIXEL GATE. `frame_safe_qa.py` asks "how much ink is in the outer border?" and treats a
// high answer as an overflow. Measured against real cases, that gate is INVERTED: three registers whose type
// is genuinely cut by the canvas read 1.00%, 1.45% and 4.40% — all UNDER its 4.5% error threshold, so all
// three ship — while four deliberately full-bleed registers read 9.6%, 12.7%, 14.1% and 35.2% and are all
// blocked. It also refuses 100% of the sampled frames of OpenAI's launch film, 57% of Figma's and 57% of
// Anthropic's. The reason is structural and cannot be fixed by moving the number: a cut word makes a THIN
// band (low coverage) and a full-bleed flood makes a SOLID field (high coverage), so coverage runs opposite
// to the defect. Two structural statistics were tried on the same samples — run structure along the border,
// and row-occupancy of border ink — and neither separated the classes either.
//
// A browser does not have to infer any of this. A cut word is exactly "a text node's visible box crosses the
// canvas edge", which the layout engine knows to the pixel. So this audits the DOM.
//
// WHAT COUNTS AS DELIBERATE. Not a flag someone can write to silence a finding: text clipped by an ancestor
// with `overflow: hidden` is INTENDED — the author built a marquee, a masked reveal, a cropping window, and
// the clip is the design. Text clipped by the CANVAS with no clipping ancestor is an ACCIDENT: nothing in the
// source says the frame should cut it, so the frame cutting it is a layout that did not fit. That distinction
// is structural, it is already present in every register that means it, and it costs an author nothing.
// `data-bleed` remains for the rare element that must escape a clip on purpose.
//
// FULL-BLEED GRAPHICS ARE NOT A CONCERN HERE, deliberately. A gradient, a flow field or a colour flood that
// runs to the edge loses nothing a viewer needed. Only TYPE carries meaning that a frame edge can destroy.
import React from 'react';
import {cancelRender, continueRender, delayRender} from 'remotion';
import {captionBand} from './layout';
import {CJK_MIN_LEADING, hasCJK} from './cjkType';

/** Prefix on the render-cancelling error, so a caller can find the JSON payload in the CLI's stderr. */
export const TEXT_SAFE_TAG = 'TEXT-SAFE-VIOLATIONS ';

export type Violation = {
  /** how far past each canvas edge the visible box reaches, in px (only sides > 0 are reported) */
  out: {left?: number; top?: number; right?: number; bottom?: number};
  /**
   * px this text reaches DOWN into the strip the renderer reserves for the burned caption.
   *
   * A second question, same walk, because pixels cannot answer it. `band_debt.py` measures the band as a
   * FRACTION OF ITS AREA THAT IS INK, and a line of type is a tiny fraction of a 227px strip: CardStack3D
   * sets its title 'All of it, in hand' wholly inside the band and measures 2.1%, while AuroraFlow — a
   * generative field whose ground legitimately covers the frame — measures 53%. The instrument ranked the
   * harmless case 25x above the fatal one and neither crossed the threshold, so the collision was invisible
   * and the caption burns straight through the title. Type has a box; ask the box.
   */
  band?: number;
  text: string;
  tag: string;
  cls: string;
  font: string;
};

const TOL = 1.0;          // sub-pixel layout noise; a real clip is tens of pixels
// A cut smaller than a third of a glyph cannot destroy a character — it shaves an edge. Without this floor
// the audit reported 27 findings on one full-bleed ASCII character FIELD (8px off a 30px mono glyph) and
// four on a glitch register whose whole technique is 5px misregistered copies of a 240px word. Both are
// texture, neither loses anything a viewer needed, and drowning the real findings is how a gate stops being
// read. Scaled to the FONT rather than fixed, so it means the same thing at 18px and at 240px.
const CUT_FRAC_OF_GLYPH = 0.35;
// A field of characters can report hundreds of boxes. The payload travels through a CLI error message, so an
// unbounded list is truncated mid-JSON and arrives as nothing at all — a register with the MOST violations
// reporting as unparseable. Cap it and carry the true count.
const MAX_REPORTED = 12;
const MIN_OPACITY = 0.05; // an element mid-fade is not yet the frame's content

/**
 * The box the GLYPHS actually occupy, not the box the element declares.
 *
 * These differ constantly and the difference is all false positives: a centred word inside a full-width
 * container reports a box wider than the frame while every letter sits comfortably inside it. Measured with
 * element boxes, this audit called two registers broken whose type is visibly intact — PixelBuild's centred
 * 'WORKBUDDY · COMPLETE' and SectionRoute's 'end' — which is exactly the kind of finding that teaches a
 * reader to stop believing the gate. A Range over the element's own text nodes returns the line boxes the
 * type is set in, so what is measured is the ink.
 */
const inkRect = (el: Element): DOMRect | null => {
  const doc = el.ownerDocument;
  if (!doc?.createRange) return el.getBoundingClientRect();
  const rects: DOMRect[] = [];
  el.childNodes.forEach((n) => {
    if (n.nodeType !== 3 || !(n.textContent ?? '').trim()) return;
    const range = doc.createRange();
    range.selectNodeContents(n);
    Array.from(range.getClientRects()).forEach((r) => {
      if (r.width > 0 && r.height > 0) rects.push(r as DOMRect);
    });
    range.detach?.();
  });
  if (!rects.length) return null;                 // SVG <text> yields none in some engines — see caller
  const l = Math.min(...rects.map((r) => r.left)), t = Math.min(...rects.map((r) => r.top));
  const ri = Math.max(...rects.map((r) => r.right)), b = Math.max(...rects.map((r) => r.bottom));
  return new DOMRect(l, t, ri - l, b - t);
};

/** Does this element hold text of its OWN (not merely descendants')? Covers SVG <text> too. */
const hasOwnText = (el: Element): string => {
  let s = '';
  el.childNodes.forEach((n) => {
    if (n.nodeType === 3) s += n.textContent ?? '';
  });
  return s.trim();
};

/**
 * The box a viewer can actually SEE: the element's own box, intersected with every ancestor that clips.
 *
 * Without this the audit would report every marquee — a ticker's text box is metres wide by construction and
 * its container is what makes it a ticker. Intersecting with the clip is what turns "the text is wider than
 * the frame" (true and irrelevant) into "the text is cut by the frame" (the defect).
 *
 * `frame` is the canvas box. Clipping ancestors at least that large are SKIPPED, because a container the
 * size of the frame is the frame, not a crop the author drew.
 */
const visibleRect = (el: Element, frame: DOMRect): DOMRect | null => {
  const win = el.ownerDocument?.defaultView;
  if (!win) return null;
  // The INK box starts the measurement; ancestors then clip it. An engine that returns no range rects
  // (some SVG text implementations) falls back to the element box rather than silently reporting nothing.
  const r = inkRect(el) ?? el.getBoundingClientRect();
  if (r.width <= 0 || r.height <= 0) return null;
  let l = r.left, t = r.top, ri = r.right, b = r.bottom;
  let node: Element | null = el;
  while (node) {
    const cs = win.getComputedStyle(node);
    if (cs.display === 'none' || cs.visibility === 'hidden') return null;
    if (parseFloat(cs.opacity || '1') < MIN_OPACITY) return null;
    // The element's OWN overflow clips too, and skipping it was a real false positive: a nav label with
    // `overflow: hidden; text-overflow: ellipsis` paints «在授权目...» inside its rail, while `inkRect`
    // measures the whole uncut string — a rect reaching into the panel beside it, reported as two pieces of
    // type colliding when nothing of the sort is on the frame. A gate that names phantom collisions is a
    // gate people learn to scroll past.
    if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') {
      const c = node.getBoundingClientRect();
      // Remotion's own AbsoluteFill sets `overflow: hidden`, so every shot's root is a clipping ancestor.
      // Counting it would read the FRAME as an author's deliberate crop and exempt the entire film — which
      // is exactly what the first version of this file did: it passed all four known overflow cases.
      const coversFrame = c.left <= frame.left + TOL && c.top <= frame.top + TOL &&
                          c.right >= frame.right - TOL && c.bottom >= frame.bottom - TOL;
      if (coversFrame) {
        node = node.parentElement;
        continue;
      }
      l = Math.max(l, c.left); t = Math.max(t, c.top);
      ri = Math.min(ri, c.right); b = Math.min(b, c.bottom);
      if (ri <= l || b <= t) return null;             // fully clipped away — not on screen at all
    }
    node = node.parentElement;
  }
  return new DOMRect(l, t, ri - l, b - t);
};

/** Prefix on the collision payload, so a caller can find it in the CLI's stderr. */
export const TYPE_COLLISION_TAG = 'TYPE-COLLISIONS ';
/** Prefix on the reached-the-screen payload. */
export const FED_TEXT_TAG = 'FED-TEXT ';

export type Collision = {
  /**
   * `leading` — one element's own wrapped LINES overlap each other. `overlap` — two elements' type collides.
   * `tight` — WRAPPED Chinese set below the library's own CJK leading floor: nothing overlaps, and there is
   * no air between the lines either. `orphan` — a wrapped Chinese label whose LAST LINE holds a single
   * character, which reads as a typo rather than as a line break. `unmeasured` — the element is drawn under a rotation AND the
   * rotation-free instrument could not read it, so NOTHING is known about it either way (see
   * `metricLeading`). Never silently dropped.
   */
  kind: 'leading' | 'overlap' | 'tight' | 'orphan' | 'unmeasured';
  /** how deep the collision runs, in px */
  depth: number;
  text: string;
  other?: string;
  font: string;
  cls: string;
  /** set when the element is drawn under a rotation, so a reader knows which instrument produced `depth` */
  rot?: boolean;
  /** on `unmeasured`, why */
  why?: string;
};

// How much two consecutive line boxes may overlap before it is a collision, as a fraction of the LINE BOX's
// own height.
//
// Measured against the line box, not against `fontSize`, and that is not a detail. A register drawn inside a
// scaled or 3D-transformed container reports rects in SCALED pixels while `getComputedStyle().fontSize`
// stays unscaled, so a fontSize-relative threshold reads the zoom as a collision: `InfiniteCanvas` (a
// camera-zoomed canvas) was reported at 14px on "40px Inter" and its type is visibly clean, and three more
// small findings had the same shape. Both numbers here come from the same rects, so the scale cancels.
//
// A CJK glyph box runs to roughly 1.35em even at line-height 1.0, so consecutive boxes touch at ordinary
// leading and the ink is still nowhere near. 0.45 of the box sits above that and below the real cases
// (CartoonPop 0.65, the synthetic probe 0.72).
const LEADING_OVERLAP_FRAC = 0.45;
// The least missing air worth naming, in px. Below this the shortfall is the browser rounding a used
// `line-height` to whole pixels, not a register that set its type tight.
const TIGHT_MIN_PX = 1.0;
// Two elements' type overlapping is sometimes a technique (a brutalist stack, a glitch's offset copies), so
// a graze is not a finding — the intersection has to eat a real share of the smaller box before it counts.
const OVERLAP_AREA_FRAC = 0.22;
const MIN_OVERLAP_PX = 6;
// Two rects on ONE line (a CJK run and a Latin run sharing a baseline) overlap vertically almost entirely;
// two stacked lines overlap by a fraction at most. 0.6 sits well clear of both.
const SAME_LINE_FRAC = 0.6;

/**
 * Per-LINE boxes of an element's own text.
 *
 * `getClientRects()` does NOT return one rect per line — it returns one per FONT RUN, and a mixed
 * CJK+Latin string is at least two runs on the same line, set in different faces with different box
 * heights. Comparing those raw rects reported a folio reading `交付可验收的成果.CO — 01` — visibly one
 * clean line — as a 31px collision, which is exactly the kind of false positive that teaches a reader to
 * stop believing a gate. So runs are grouped into LINES first: two rects belong to the same line when
 * their vertical ranges overlap by most of the smaller one's height, which is true of two faces on a
 * shared baseline and false of two stacked lines.
 */
const lineRects = (el: Element): DOMRect[] => {
  const doc = el.ownerDocument;
  if (!doc?.createRange) return [];
  const runs: DOMRect[] = [];
  el.childNodes.forEach((n) => {
    if (n.nodeType !== 3 || !(n.textContent ?? '').trim()) return;
    const range = doc.createRange();
    range.selectNodeContents(n);
    Array.from(range.getClientRects()).forEach((r) => {
      if (r.width > 0 && r.height > 0) runs.push(r as DOMRect);
    });
    range.detach?.();
  });
  runs.sort((a, b) => a.top - b.top);
  const lines: {top: number; bottom: number; left: number; right: number}[] = [];
  runs.forEach((r) => {
    const cur = lines[lines.length - 1];
    if (cur) {
      const overlap = Math.min(cur.bottom, r.bottom) - Math.max(cur.top, r.top);
      const smaller = Math.min(cur.bottom - cur.top, r.height);
      if (smaller > 0 && overlap / smaller > SAME_LINE_FRAC) {   // same baseline, another face
        cur.top = Math.min(cur.top, r.top);
        cur.bottom = Math.max(cur.bottom, r.bottom);
        cur.left = Math.min(cur.left, r.left);
        cur.right = Math.max(cur.right, r.right);
        return;
      }
    }
    lines.push({top: r.top, bottom: r.bottom, left: r.left, right: r.right});
  });
  return lines.map((l) => new DOMRect(l.left, l.top, l.right - l.left, l.bottom - l.top));
};

// ── ROTATED TYPE ────────────────────────────────────────────────────────────────────────────────────────
//
// A client rect is AXIS-ALIGNED. For type drawn straight that is the line box, and comparing consecutive
// rects is a measurement. For type drawn on a TILT it is the bounding box of a tilted line, which is taller
// than the line by `width·|sin θ|` — so consecutive rects of perfectly-set copy overlap enormously and the
// rect instrument reports a collision that is not there.
//
// This shipped. `CardStack3D` fans its cards on the Z axis (±13° at three cards), and a card label set at
// `46px/1` — tight, but its three lines are visibly separate — was reported as a 64px collision on a real
// film. The same label in the same register with ONE card, where the fan angle is 0, reported clean. The
// whole 64px was the tilt. 27 of the library's 153 registers rotate something.
//
// So a rotated element is measured with an instrument that has no orientation at all: the font's own box
// height (canvas `fontBoundingBox*`, which is layout- and transform-free) against the resolved
// `line-height`. That is the same quantity the rect path measures — a client rect's height IS the font box —
// so one threshold covers both, and the two paths agree where they overlap (checked in the controls).
const ROT_EPS = 0.02;   // ≈1.1°, below which the inflation is sub-pixel at the sizes this library sets

/** Is THIS element's own transform a rotation or a skew? */
const selfRotated = (cs: CSSStyleDeclaration): boolean => {
  const tr = cs.transform;
  if (tr && tr !== 'none' && tr.indexOf('(') > 0) {
    const n = tr.slice(tr.indexOf('(') + 1, tr.lastIndexOf(')')).split(',').map((x) => parseFloat(x) || 0);
    // matrix(a,b,c,d,e,f) → the off-diagonals are 1,2. matrix3d is column-major 4×4: the terms that can
    // tilt the PROJECTED box are m12/m21 (in-plane) and m13/m31/m23/m32 (out-of-plane, which tilt it once
    // a `perspective` ancestor turns the quad into a trapezoid).
    const idx = n.length === 6 ? [1, 2] : n.length === 16 ? [1, 4, 2, 8, 6, 9] : [];
    if (idx.some((i) => Math.abs(n[i]) > ROT_EPS)) return true;
  }
  const rot = (cs as unknown as {rotate?: string}).rotate;   // the `rotate` longhand, independent of `transform`
  return Boolean(rot && rot !== 'none' && !/^(0deg|0rad|0turn|0grad|0)$/.test(rot.trim()));
};

/**
 * Does any transform up this element's chain rotate or skew it? Deliberately over-inclusive.
 *
 * MEMOISED PER AUDIT, because the naive walk is quadratic in a way this library actually reaches: a
 * character FIELD draws a thousand text elements and each walk repeats its ancestors' `getComputedStyle`,
 * which is the expensive call. An element's answer is its own transform OR its parent's answer, so one
 * cache turns the whole tree into a single pass.
 */
const rotatedUnder = (el: Element, win: Window, memo: Map<Element, boolean>): boolean => {
  const chain: Element[] = [];
  let node: Element | null = el;
  let acc = false;
  while (node) {
    const hit = memo.get(node);
    if (hit !== undefined) {
      acc = hit;
      break;
    }
    chain.push(node);
    node = node.parentElement;
  }
  for (let i = chain.length - 1; i >= 0; i--) {
    acc = acc || selfRotated(win.getComputedStyle(chain[i]));
    memo.set(chain[i], acc);
  }
  return acc;
};

let _ctx: CanvasRenderingContext2D | null | undefined;
const measureCtx = (doc: Document): CanvasRenderingContext2D | null => {
  if (_ctx === undefined) _ctx = doc.createElement('canvas').getContext('2d');
  return _ctx ?? null;
};

/**
 * Leading overlap of a ROTATED element, read without touching a single client rect.
 *
 * Returns the overlap depth in px and the font box it is a fraction of, or a reason it could not be read.
 * A block that does not wrap has no leading collision by definition, so the wrap test comes first — and it
 * is done in LAYOUT pixels (`clientWidth`, immune to transforms) against a canvas measurement of the same
 * string in the same face.
 */
const metricLeading = (
  el: Element, cs: CSSStyleDeclaration, text: string,
): {depth: number; box: number; wraps: boolean} | {why: string} => {
  const ctx = measureCtx(el.ownerDocument);
  if (!ctx) return {why: 'no 2d canvas in this renderer'};
  const lineH = parseFloat(cs.lineHeight || '');
  // `normal` IS the font's own leading, which is the one value that cannot collide with itself.
  if (!isFinite(lineH) || lineH <= 0) return {depth: 0, box: 0, wraps: false};
  // A font string the canvas REFUSES is not an error — the browser silently keeps the previous value, and
  // the whole measurement would then be of 10px sans-serif and read as an enormous overlap. Assign, then
  // read back the size it actually took.
  ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize}/${cs.lineHeight} ${cs.fontFamily}`;
  const want = parseFloat(cs.fontSize || '');
  const took = parseFloat((/(\d+(?:\.\d+)?)px/.exec(ctx.font) ?? [])[1] ?? '');
  if (!(isFinite(want) && isFinite(took) && Math.abs(took - want) < 0.51)) {
    return {why: `the canvas would not take this face (asked ${cs.fontSize}, measuring "${ctx.font}")`};
  }
  const ls = (ctx as unknown as {letterSpacing?: string});
  if ('letterSpacing' in ctx) ls.letterSpacing = cs.letterSpacing === 'normal' ? '0px' : cs.letterSpacing;
  const m = ctx.measureText(text);
  const asc = (m as unknown as {fontBoundingBoxAscent?: number}).fontBoundingBoxAscent;
  const desc = (m as unknown as {fontBoundingBoxDescent?: number}).fontBoundingBoxDescent;
  if (typeof asc !== 'number' || typeof desc !== 'number' || !(asc + desc > 0)) {
    return {why: 'this renderer reports no fontBoundingBox metrics'};
  }
  // The width a line has to fill before it wraps is the CONTAINING BLOCK's, and for an INLINE element
  // `clientWidth` is 0 — the case `HalftonePop` reported as unmeasurable. Walk out to the first ancestor
  // that has a layout width; that is the box the text actually wraps inside. Layout values throughout, so
  // the tilt never enters the measurement.
  let avail = 0;
  for (let n: Element | null = el; n && !(avail > 0); n = n.parentElement) {
    const w = (n as HTMLElement).clientWidth;
    if (!(w > 0)) continue;
    const c = n === el ? cs : (el.ownerDocument.defaultView?.getComputedStyle(n) ?? cs);
    avail = w - (parseFloat(c.paddingLeft || '0') || 0) - (parseFloat(c.paddingRight || '0') || 0);
  }
  if (!(avail > 0)) return {why: 'no layout width anywhere up the chain to test wrapping against'};
  if (m.width <= avail + 1 && text.indexOf('\n') < 0) return {depth: 0, box: 0, wraps: false};
  return {depth: asc + desc - lineH, box: asc + desc, wraps: true};
};

/**
 * Is any TYPE colliding with other type? — the question a CJK film needs and no existing gate asks.
 *
 * `auditTextSafety` asks whether type falls OFF the canvas. A film in Chinese fails a different way: the
 * copy is still inside the frame and still unreadable, because a register sized for short English words
 * wrapped a Chinese sentence into three lines set at a leading that assumed one. Measured on a real film,
 * three registers broke exactly this way in one evening — KineticManifesto, BrutalistType and
 * MagazineSpread — and text_safe passed all three, correctly: nothing was cut.
 *
 * Two kinds, and they are not equally certain. An element whose OWN wrapped lines overlap is never intended
 * (nobody sets a paragraph to collide with itself), so `leading` is a defect. Two DIFFERENT elements
 * overlapping is sometimes the technique, so `overlap` is a candidate for a human to look at.
 */
/** A SECOND rendering of type this frame already shows — not new type, and not the viewer's to read twice.
 *
 *  `PointerTour` draws its page twice, sharp and softened, and masks the soft copy so the part the lens is
 *  not on falls out of focus. Every label therefore exists twice at the same place, and the collision audit
 *  correctly reported each one overlapping itself: two boxes, same rect, different elements. The gate was not
 *  wrong — the frame really does hold two copies — but the finding is noise, and noise on a register is how a
 *  gate stops being read at all.
 *
 *  So a duplicate declares itself. The rule is deliberately narrow and named for what it means: `data-echo`
 *  marks a subtree whose type is ALREADY MEASURED elsewhere on the same frame. It is not a way to hide type
 *  from the gates — `tests/test_text_safe_qa.py` pins that PointerTour's sharp copy is unmarked, so every
 *  string it draws is still audited exactly once. An element must also carry `aria-hidden`, because a
 *  duplicate nobody should read twice is a duplicate no screen reader should announce twice either.
 */
const isEcho = (el: Element): boolean => !!el.closest?.('[data-echo]');

export const auditTypeCollisions = (root: Element, frame: DOMRect): Collision[] => {
  const win = root.ownerDocument?.defaultView;
  if (!win) return [];
  const out: Collision[] = [];
  const boxes: {el: Element; r: DOMRect; text: string; font: string; cls: string; rot: boolean}[] = [];
  const rotMemo = new Map<Element, boolean>();
  root.querySelectorAll('*').forEach((el) => {
    const text = hasOwnText(el);
    if (!text) return;
    if (isEcho(el)) return;                           // already measured on its sharp original
    const cs = win.getComputedStyle(el);
    if (parseFloat(cs.opacity || '1') < MIN_OPACITY || cs.visibility === 'hidden') return;
    const r = visibleRect(el, frame);
    if (!r || r.width <= 0 || r.height <= 0) return;
    const font = `${cs.fontSize} ${(cs.fontFamily || '').split(',')[0]}`;
    const cls = (el.getAttribute('class') ?? '').slice(0, 40);
    const short = text.length > 40 ? text.slice(0, 40) + '…' : text;
    // 1. this element's own lines, against each other. Rotated type gets the orientation-free instrument —
    //    its client rects are bounding boxes of tilted lines and overlap by construction.
    const rot = rotatedUnder(el, win, rotMemo);
    let worst = 0, box = 0, wraps = false;
    if (rot) {
      const m = metricLeading(el, cs, text);
      if ('why' in m) {
        out.push({kind: 'unmeasured', depth: 0, text: short, font, cls, rot: true, why: m.why});
      } else {
        worst = m.depth; box = m.box; wraps = m.wraps;
      }
    } else {
      const lines = lineRects(el);
      wraps = lines.length > 1;
      for (let i = 1; i < lines.length; i++) {
        const gap = lines[i - 1].bottom - lines[i].top;    // > 0 means the boxes overlap
        if (gap > worst) {
          worst = gap;
          box = Math.min(lines[i - 1].height, lines[i].height);
        }
      }
    }
    if (box > 0 && worst > box * LEADING_OVERLAP_FRAC) {
      out.push({kind: 'leading', depth: Math.round(worst), text: short, font, cls, ...(rot ? {rot: true} : {})});
    } else if (wraps && hasCJK(text)) {
      // BELOW THE FLOOR BUT NOT YET A PILE. `leading` only fires once lines eat into each other, which is
      // the broken end of a spectrum. `line-height: 1` is the other end: CJK glyphs fill their em box, so
      // wrapped lines abut with no air at all — tight, readable, and below the floor the library states for
      // itself (`CJK_MIN_LEADING`). It is reported, not failed, because nothing is destroyed.
      //
      // It exists because the STATIC rule could not see this case: its regex required a decimal point, so
      // `px/1` — 97 of the 153 registers — was invisible to it, and `CardStack3D` shipped a three-line
      // Chinese card label at exactly 1.0. A measurement does not need the leading to be spelled a
      // particular way.
      //
      // MEASURED IN PIXELS OF MISSING AIR, with a one-pixel floor, because the ratio comparison alone
      // reports registers that already MEET the floor. `line-height: 1.06` on a 243px face is a used value
      // the browser rounds to whole pixels, so the ratio reads 1.0599… and `< 1.06` is true — `BrutalistType`
      // and `HalftonePop` both pass their copy through `leading()` and both were reported, at a shortfall of
      // 0px and 1px. A finding about missing air that names zero pixels of it is a false positive, and this
      // is exactly the kind that teaches a reader to stop believing a gate. The real cases are not close to
      // the boundary: `CardStack3D` at 46px/1.0 was 2.8px short and `MapRoutes` at 30px/1.0 was 1.8px.
      const fs = parseFloat(cs.fontSize || ''), lh = parseFloat(cs.lineHeight || '');
      const shortPx = isFinite(fs) && fs > 0 && isFinite(lh) ? (CJK_MIN_LEADING - lh / fs) * fs : 0;
      if (shortPx > TIGHT_MIN_PX) {
        out.push({kind: 'tight', depth: Math.round(shortPx), text: short, font, cls,
                  ...(rot ? {rot: true} : {})});
      }
    }
    // A LAST LINE HOLDING ONE CHARACTER. Chinese breaks between any two characters, so a label one unit too
    // wide for its box drops a single glyph onto a line of its own, which reads as a typo rather than as a
    // line break: a delivered film's card said 「Craft · 直接开」 over a line holding just 「干」. Nothing is
    // cut and nothing collides, so no other gate can see it. `text-wrap: balance` is the fix in the
    // register; this is how you find them.
    if (wraps && hasCJK(text) && text.length <= 40) {
      const lines = charLines(el, parseFloat(cs.lineHeight || ''));
      const tail = lines && lines.length > 1 ? lines[lines.length - 1] : null;
      if (tail && tail.length === 1 && hasCJK(tail[0])) {
        out.push({kind: 'orphan', depth: 1, text: short, font, cls, other: tail[0],
                  ...(rot ? {rot: true} : {})});
      }
    }
    boxes.push({el, r, text: short, font, cls, rot});
  });
  // 2. element against element — skip any pair where one contains the other (a label inside its own card
  //    is not a collision; its box is supposed to be inside)
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (w <= MIN_OVERLAP_PX || h <= MIN_OVERLAP_PX) continue;
      const area = w * h;
      const smaller = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
      if (smaller <= 0 || area / smaller < OVERLAP_AREA_FRAC) continue;
      // A tilted element's box is its bounding box, so a pair involving one overlaps more than the ink
      // does. `overlap` is advisory either way; the flag says which numbers to discount.
      out.push({kind: 'overlap', depth: Math.round(Math.min(w, h)), text: a.text, other: b.text,
                font: a.font, cls: a.cls, ...(a.rot || b.rot ? {rot: true} : {})});
    }
  }
  return out;
};

/**
 * An element's own characters, grouped into the LINES they were actually laid out on.
 *
 * WHY NOT `getClientRects()` GROUPED BY `top`. Because the library rotates type, and under a tilt every
 * axis-aligned quantity lies (see ROTATED TYPE above). The direction of a line is not assumed here — it is
 * MEASURED from the copy, as the median direction between consecutive characters, most pairs of which are
 * neighbours on one line whatever the tilt. Characters are then grouped by their distance along the
 * PERPENDICULAR of that direction, which is the line advance in any orientation.
 *
 * Deliberately bounded: this answers a question about LABELS, so anything past `limit` characters returns
 * null rather than paying for a paragraph.
 */
// `limit` sits ABOVE the caller's own 40-character gate on purpose: at 40 a label of exactly 40
// characters trips the bound on its last glyph and comes back unmeasured, which is the quiet kind of
// skip this file exists to avoid.
const charLines = (el: Element, lineH: number, limit = 48): string[][] | null => {
  const doc = el.ownerDocument;
  if (!doc?.createRange || !(lineH > 0)) return null;
  const nodes: Text[] = [];
  el.childNodes.forEach((n) => {
    if (n.nodeType === 3 && (n.textContent ?? '').trim()) nodes.push(n as Text);
  });
  const chars: {ch: string; cx: number; cy: number}[] = [];
  for (const n of nodes) {
    const t = n.textContent ?? '';
    for (let i = 0; i < t.length; i++) {
      if (chars.length >= limit) return null;
      const r = doc.createRange();
      r.setStart(n, i);
      r.setEnd(n, i + 1);
      const b = r.getBoundingClientRect();
      r.detach?.();
      if (b.width <= 0 || b.height <= 0) continue;       // a collapsed space at a line break
      chars.push({ch: t[i], cx: b.left + b.width / 2, cy: b.top + b.height / 2});
    }
  }
  if (chars.length < 4) return null;
  const angles: number[] = [];
  for (let i = 1; i < chars.length; i++) {
    const dx = chars[i].cx - chars[i - 1].cx, dy = chars[i].cy - chars[i - 1].cy;
    if (Math.abs(dx) + Math.abs(dy) < 0.5) continue;
    let a = Math.atan2(dy, dx);
    if (a > Math.PI / 2) a -= Math.PI;                    // direction, not heading: fold to (-90°, 90°]
    if (a <= -Math.PI / 2) a += Math.PI;
    angles.push(a);
  }
  if (!angles.length) return null;
  angles.sort((x, y) => x - y);
  const th = angles[Math.floor(angles.length / 2)];       // the median: line-internal steps outvote breaks
  const px = -Math.sin(th), py = Math.cos(th);            // the perpendicular — the direction lines advance
  const lines: string[][] = [];
  let last = NaN;
  chars.forEach((c) => {
    const s = c.cx * px + c.cy * py;
    if (!isFinite(last) || Math.abs(s - last) > lineH * 0.5) lines.push([]);
    last = s;
    lines[lines.length - 1].push(c.ch);
  });
  return lines;
};

/**
 * Which of the strings a caller FED this register never reached the screen?
 *
 * WHY IT IS ASKED OF THE DOM. A gate that hands a register a wrong-shaped fixture gets a frame drawn from
 * `undefined` — empty rows, blank cards — and every measurement of that frame is a measurement of an empty
 * plate. The first guard for it compared the frame's INK against the register's own demo defaults, which is
 * a proxy for the question and got the answer wrong on the first legitimately sparse frame it met: a
 * four-panel `QuadSplit` on a warm-white product palette drew 3% and was reported as never fed, with all
 * five of its strings plainly on screen. The DOM knows the real answer exactly.
 *
 * MATCHING IS DELIBERATELY LOOSE, because reaching the screen is not the same as surviving unchanged. A
 * register may set one character per element, fit a headline down, or truncate a long line — all of which
 * are the register working. So a string counts as arrived when it appears whole, OR when most of its
 * characters do. Only copy that is essentially absent is reported.
 */
const FED_CHAR_COVERAGE = 0.6;
export const auditFedText = (root: Element, fed: unknown[]): string[] => {
  const norm = (s: string) => s.replace(/\s+/g, '');
  let all = '';
  root.querySelectorAll('*').forEach((el) => {
    if (isEcho(el)) return;                           // counting a duplicate twice cannot make copy arrive
    all += hasOwnText(el);
  });
  const hay = norm(all);
  const pool = new Map<string, number>();
  for (const ch of hay) pool.set(ch, (pool.get(ch) ?? 0) + 1);
  const missing: string[] = [];
  fed.forEach((raw) => {
    const n = norm(String(raw ?? ''));
    if (!n) return;
    if (hay.indexOf(n) >= 0) return;
    const left = new Map(pool);
    let hit = 0;
    for (const ch of n) {
      const c = left.get(ch) ?? 0;
      if (c > 0) {
        hit += 1;
        left.set(ch, c - 1);
      }
    }
    if (hit / n.length < FED_CHAR_COVERAGE) missing.push(n.length > 40 ? n.slice(0, 40) + '\u2026' : n);
  });
  return missing;
};

/** Every text element whose VISIBLE box crosses the canvas edge, with no ancestor claiming the clip. */
export const auditTextSafety = (root: Element, frame: DOMRect): Violation[] => {
  const win = root.ownerDocument?.defaultView;
  if (!win) return [];
  const out: Violation[] = [];
  root.querySelectorAll('*').forEach((el) => {
    const text = hasOwnText(el);
    if (!text) return;
    if (isEcho(el)) return;                           // already measured on its sharp original
    if (el.closest?.('[data-bleed]')) return;         // an explicit, rare escape from a clip
    const r = visibleRect(el, frame);
    if (!r) return;
    const over = {
      left: frame.left - r.left,
      top: frame.top - r.top,
      right: r.right - frame.right,
      bottom: r.bottom - frame.bottom,
    };
    const cs = win.getComputedStyle(el);
    const floor = Math.max(TOL, parseFloat(cs.fontSize || '16') * CUT_FRAC_OF_GLYPH);
    const sides: Violation['out'] = {};
    (Object.keys(over) as (keyof typeof over)[]).forEach((k) => {
      if (over[k] > floor) sides[k] = Math.round(over[k]);
    });
    // The caption strip is not a canvas edge — text inside it is not cut, it is COLLIDING with copy that
    // will be burned over it later. Same glyph-scaled floor, so a descender grazing the boundary is not a
    // finding and a whole title sitting in it is.
    const bandTop = frame.bottom - captionBand(frame.width, frame.height);
    const intoBand = r.bottom - bandTop;
    const band = intoBand > floor ? Math.round(Math.min(intoBand, r.height)) : 0;
    if (!Object.keys(sides).length && !band) return;
    out.push({
      out: sides,
      ...(band ? {band} : {}),
      text: text.length > 48 ? text.slice(0, 48) + '…' : text,
      tag: el.tagName.toLowerCase(),
      cls: (el.getAttribute('class') ?? '').slice(0, 40),
      font: `${cs.fontSize} ${(cs.fontFamily || '').split(',')[0]}`,
    });
  });
  return out;
};

/**
 * Mount inside a composition to audit it. INERT unless `enabled` — a normal render must not pay a DOM walk,
 * and must not gain a delayRender that could time out.
 *
 * Reports by CANCELLING the render with a JSON payload, which is the only channel a still render has back to
 * its caller. That makes a violation loud and per-scene: `scripts/text_safe_qa.py` renders each beat on its
 * own and collects the failures rather than stopping at the first.
 */
export const TextSafeAudit: React.FC<{enabled?: boolean; mode?: 'safe' | 'collisions' | 'fed';
  fed?: unknown[]}> = ({enabled = false, mode = 'safe', fed}) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [handle] = React.useState(() =>
    enabled ? delayRender('text-safe audit', {timeoutInMilliseconds: 60000}) : null);

  React.useEffect(() => {
    if (!enabled || handle === null) return;
    let dead = false;
    (async () => {
      try {
        // Fonts change every metric this audit measures; auditing before they load reports the fallback
        // face's geometry, which is a different layout than the one that ships.
        await (document as unknown as {fonts?: {ready: Promise<unknown>}}).fonts?.ready;
      } catch {
        /* a browser without the API still lays out; measure what it has */
      }
      await new Promise((res) => requestAnimationFrame(() => res(null)));
      if (dead) return;
      const host = ref.current;
      if (!host) {
        continueRender(handle);
        return;
      }
      const frame = host.getBoundingClientRect();
      const body = host.ownerDocument.body;
      // `fed` ALWAYS cancels: its answer is the empty list as often as not, and a still render has no other
      // channel back to its caller. The caller asks for this mode only when it already has a reason to.
      if (mode === 'fed') {
        cancelRender(new Error(FED_TEXT_TAG + JSON.stringify({missing: auditFedText(body, fed ?? [])})));
        return;
      }
      if (mode === 'collisions') {
        const hits = auditTypeCollisions(body, frame);
        if (hits.length) {
          const head = hits.slice(0, MAX_REPORTED);
          if (hits.length > head.length) {
            head.push({kind: 'overlap', depth: 0, text: `…and ${hits.length - head.length} more`,
                       font: '', cls: ''});
          }
          cancelRender(new Error(TYPE_COLLISION_TAG + JSON.stringify(head)));
        } else continueRender(handle);
        return;
      }
      const viol = auditTextSafety(body, frame);
      if (viol.length) {
        const head = viol.slice(0, MAX_REPORTED);
        if (viol.length > head.length) {
          head.push({out: {}, text: `…and ${viol.length - head.length} more`, tag: '', cls: '', font: ''});
        }
        cancelRender(new Error(TEXT_SAFE_TAG + JSON.stringify(head)));
      }
      else continueRender(handle);
    })();
    return () => {
      dead = true;
    };
  }, [enabled, handle, mode, fed]);

  if (!enabled) return null;
  // Its own box IS the canvas rect — measured rather than assumed, so the audit is correct at any aspect
  // and under any render scale.
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
};

export default TextSafeAudit;
