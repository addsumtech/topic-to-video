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
 * THIS element's own 2x2 LINEAR transform — rotation, scale, skew, or any combination — or null.
 *
 * Null for `matrix3d`: under a `perspective` ancestor that projects to something which is not an affine
 * image of the box at all, and guessing there would replace a known over-report with an unknown wrong one.
 */
export const selfMatrix = (cs: CSSStyleDeclaration): [number, number, number, number] | null => {
  let M: [number, number, number, number] = [1, 0, 0, 1];
  const rotLong = (cs as unknown as {rotate?: string}).rotate;
  if (rotLong && rotLong !== 'none') {
    const m = /(-?[\d.]+)(deg|rad|turn|grad)?/.exec(rotLong.trim());
    if (!m) return null;
    const v = parseFloat(m[1]), u = m[2] || 'deg';
    const ang = u === 'rad' ? v : u === 'turn' ? v * 2 * Math.PI : u === 'grad' ? (v * Math.PI) / 200
      : (v * Math.PI) / 180;
    M = [Math.cos(ang), Math.sin(ang), -Math.sin(ang), Math.cos(ang)];
  }
  const tr = cs.transform;
  if (!tr || tr === 'none') return M;
  if (tr.indexOf('(') < 0) return null;
  const n = tr.slice(tr.indexOf('(') + 1, tr.lastIndexOf(')')).split(',').map((x) => parseFloat(x) || 0);
  if (n.length !== 6) return null;
  const T: [number, number, number, number] = [n[0], n[1], n[2], n[3]];
  return [M[0] * T[0] + M[2] * T[1], M[1] * T[0] + M[3] * T[1],
          M[0] * T[2] + M[2] * T[3], M[1] * T[2] + M[3] * T[3]];
};

/**
 * The QUADRILATERAL an element actually occupies, from its untransformed size and its accumulated 2x2.
 *
 * `offsetWidth`/`offsetHeight` are LAYOUT numbers — transforms do not touch them — so they give the box
 * before anything tilted it. An affine image of a rectangle is a parallelogram, and a parallelogram is
 * centrally symmetric, so its axis-aligned bounding box (which is what the DOM hands back) is centred on
 * exactly the same point. Centre plus the two edge vectors is therefore the whole shape, exactly, with no
 * matrix-to-viewport walk and no reliance on `transform-origin`.
 *
 * This is what a client rect cannot say. Measured on the case it was written for: two parallel lines at 14
 * degrees with a clear 44px gap between them report 66.5% overlap as axis-aligned boxes, against a 22%
 * threshold, and 0% as the shapes they are. `Element.getBoxQuads()` would answer this directly and is
 * undefined in the Chrome this renderer ships (149, headless shell) — asked, not assumed.
 */
export const quadOf = (el: Element, r: {left: number; top: number; width: number; height: number},
                       M: [number, number, number, number]): Array<[number, number]> | null => {
  const he = el as HTMLElement;
  const w = he.offsetWidth, h = he.offsetHeight;
  if (!(w > 0) || !(h > 0)) return null;           // SVG and inline boxes have no offset size
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const hx = w / 2, hy = h / 2;
  return ([[-hx, -hy], [hx, -hy], [hx, hy], [-hx, hy]] as Array<[number, number]>)
    .map(([x, y]) => [cx + M[0] * x + M[2] * y, cy + M[1] * x + M[3] * y] as [number, number]);
};

/** Sutherland-Hodgman: the convex intersection of two convex polygons. */
const clipPoly = (subject: Array<[number, number]>, clip: Array<[number, number]>) => {
  let out = subject;
  for (let i = 0; i < clip.length && out.length; i++) {
    const [ax, ay] = clip[i], [bx, by] = clip[(i + 1) % clip.length];
    const ex = bx - ax, ey = by - ay;
    const inside = (p: [number, number]) => (ex * (p[1] - ay) - ey * (p[0] - ax)) >= 0;
    const next: Array<[number, number]> = [];
    for (let k = 0; k < out.length; k++) {
      const P = out[k], Q = out[(k + 1) % out.length];
      const pin = inside(P), qin = inside(Q);
      if (pin) next.push(P);
      if (pin !== qin) {
        const dx = Q[0] - P[0], dy = Q[1] - P[1];
        const den = ex * dy - ey * dx;
        if (Math.abs(den) > 1e-9) {
          const u = (ex * (P[1] - ay) - ey * (P[0] - ax)) / -den;
          next.push([P[0] + u * dx, P[1] + u * dy]);
        }
      }
    }
    out = next;
  }
  return out;
};

const polyArea = (pts: Array<[number, number]>) => {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
    a += x1 * y2 - x2 * y1;
  }
  return Math.abs(a) / 2;
};

/** Two quads' true overlap: {area, depth} in px, depth being the shallowest penetration over both shapes'
 *  edge normals — the separating-axis quantity, which is what "how deep" means for a tilted pair. */
export const quadOverlap = (pa: Array<[number, number]>, pb: Array<[number, number]>) => {
  const area = polyArea(clipPoly(pa, pb));
  if (area <= 0) return {area: 0, depth: 0};
  let depth = Infinity;
  for (const poly of [pa, pb]) {
    for (let i = 0; i < poly.length; i++) {
      const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % poly.length];
      const len = Math.hypot(x2 - x1, y2 - y1);
      if (len < 1e-9) continue;
      const nx = -(y2 - y1) / len, ny = (x2 - x1) / len;
      const proj = (q: Array<[number, number]>) => {
        const v = q.map(([x, y]) => x * nx + y * ny);
        return [Math.min(...v), Math.max(...v)] as [number, number];
      };
      const [a0, a1] = proj(pa), [b0, b1] = proj(pb);
      depth = Math.min(depth, Math.min(a1, b1) - Math.max(a0, b0));
    }
  }
  return {area, depth: Math.max(0, depth)};
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

/**
 * The accumulated 2x2 up this element's chain, or null when any link is not an affine we can compose.
 *
 * The boolean twin above answers "should these numbers be discounted"; this answers "by exactly what",
 * which is what turns a bounding box back into the shape it bounds. Null propagates: one `matrix3d`
 * ancestor and the reconstruction is not valid, so the pair falls back to the advisory path rather than to
 * a confident wrong number. Memoised for the same reason its twin is.
 */
const matrixUnder = (el: Element, win: Window,
                     memo: Map<Element, [number, number, number, number] | null>) => {
  const chain: Element[] = [];
  let node: Element | null = el;
  let acc: [number, number, number, number] | null = [1, 0, 0, 1];
  while (node) {
    if (memo.has(node)) {
      acc = memo.get(node) as [number, number, number, number] | null;
      break;
    }
    chain.push(node);
    node = node.parentElement;
  }
  for (let i = chain.length - 1; i >= 0; i--) {
    const own = selfMatrix(win.getComputedStyle(chain[i]));
    acc = acc === null || own === null ? null
      : [acc[0] * own[0] + acc[2] * own[1], acc[1] * own[0] + acc[3] * own[1],
         acc[0] * own[2] + acc[2] * own[3], acc[1] * own[2] + acc[3] * own[3]];
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
  const boxes: {el: Element; r: DOMRect; text: string; font: string; cls: string; rot: boolean;
                mat: [number, number, number, number] | null}[] = [];
  const rotMemo = new Map<Element, boolean>();
  const matMemo = new Map<Element, [number, number, number, number] | null>();
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
    const mat = rot ? matrixUnder(el, win, matMemo) : null;
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
    boxes.push({el, r, text: short, font, cls, rot, mat});
  });
  // 2. element against element — skip any pair where one contains the other (a label inside its own card
  //    is not a collision; its box is supposed to be inside)
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      // A TILTED PAIR IS MEASURED AS THE RECTANGLES IT IS, NOT AS THE BOXES THAT BOUND THEM. A client rect
      // is axis-aligned, so for sloping type it is larger than the glyphs on the side they slope toward —
      // and the error runs BOTH ways, so a real collision between two tilted lines could equally be missed.
      // Measured on the case this was written for: two parallel lines at 14 degrees with a clear 44px gap
      // between them report 66.5% overlap axis-aligned, against a threshold of 22%, and 0% as rectangles.
      // (That is TermSpace's «交付可验收的成果» x «自动归档», reported at 9:16, 1:1 and 4:5 and clean on
      // the frame.) Bounded to pairs that actually involve a rotation, so every other pair keeps the fast
      // path and the same numbers it has always produced.
      let w: number, h: number, area: number, smaller: number, depth: number;
      const qa = a.rot || b.rot
        ? quadOf(a.el, a.r, a.mat ?? [1, 0, 0, 1]) : null;
      const qb = qa ? quadOf(b.el, b.r, b.mat ?? [1, 0, 0, 1]) : null;
      const exact = (a.rot ? a.mat !== null : true) && (b.rot ? b.mat !== null : true) && qa && qb
        ? {qa, qb} : null;
      if (exact) {
        const {area: ar, depth: dp} = quadOverlap(exact.qa, exact.qb);
        area = ar;
        depth = dp;
        w = h = dp;                                   // the gates below read these as "is it deep enough"
        const sizeOf = (q: Array<[number, number]>) =>
          Math.abs((q[1][0] - q[0][0]) * (q[3][1] - q[0][1]) - (q[3][0] - q[0][0]) * (q[1][1] - q[0][1]));
        smaller = Math.min(sizeOf(exact.qa), sizeOf(exact.qb));
      } else {
        w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        area = w * h;
        smaller = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
        depth = Math.min(w, h);
      }
      if (w <= MIN_OVERLAP_PX || h <= MIN_OVERLAP_PX) continue;
      if (smaller <= 0 || area / smaller < OVERLAP_AREA_FRAC) continue;
      // `rot` still rides along: on the oriented path it says the numbers came from the exact instrument,
      // and on the fallback that they are a bounding-box over-report.
      out.push({kind: 'overlap', depth: Math.round(depth), text: a.text, other: b.text,
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
    // TRUNCATION IS NOT OMISSION. A terminal cuts a line and marks it — `TermTree` clips a note to its
    // column and writes an ellipsis, which is the FORM, not a register dropping copy a film supplied. The
    // character-coverage test below cannot tell the two apart: twelve glyphs of a twenty-seven glyph note
    // score 0.44 and read as missing, at every aspect, for as long as the clip has existed. A prefix of the
    // fed string followed by an ellipsis IS the string, shown the way the medium shows it.
    for (let k = n.length; k >= 4; k--) {
      if (hay.indexOf(n.slice(0, k) + '\u2026') >= 0) return;
    }
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
/**
 * THE CONTENT CONTRACT, ON THE FRAME: the words a viewer can read that no prop supplied.
 *
 * `fed` asks whether the film's copy ARRIVED; this asks the opposite question — whether anything arrived that the
 * film never said. A built thing (scripts/workshop.py) takes every word from props; the static scan
 * (scripts/jsx_words.cjs) catches the words written into its code, and cannot see a word that reaches the
 * screen through a constant list, a one-word default, or a wrapped library register's own copy. This can.
 *
 * TWO QUESTIONS, ANSWERED SEPARATELY: what counts as ONE RUN of text (below the matcher), and whether a
 * run's TOKENS are fed — case- and width-folded, so a register may re-case a label, join two with a
 * separator, split one across elements, or set each glyph in its own element, all of which are the register
 * working:
 *
 *   - a TOKEN is a maximal run of characters of one CLASS — CJK (Han/kana/Hangul, by Unicode's SCRIPT
 *     EXTENSIONS rather than a character's primary Script, which puts a mark several scripts share into
 *     "Common" and reads it as a token break: ー and 々 stay inside a CJK run), DIGIT (`\p{Nd}`, with an
 *     internal `.`/`,` allowed as a numeral's own separator), or LETTER (everything else `\p{L}`/`\p{N}`
 *     matches) — any change of class ends a token, so a value joined to its unit ("9bar", "5ms") tokenizes as
 *     the number and the unit separately. Fed strings tokenize the same way, so a fed "H2O" still licenses
 *     an "H2O" shown split into "H"/"2"/"O": each of the three pools its own class identically on both sides.
 *   - a WORD or CJK token matches by pooled PROVENANCE: a fed word may appear ANYWHERE on the frame, in any
 *     fed string, so a run's WORD tokens are checked against the pool of every fed string's own word tokens,
 *     not a contiguous run inside one of them. A CJK token has no internal word boundaries at all (CJK has no
 *     spaces, so a line or element break can fall anywhere in a phrase, and two joined phrases arrive as one
 *     token) — it is covered by PIECES of a fed CJK token instead, each piece either ≥2 characters and a
 *     substring of one fed CJK token, or exactly 1 character and itself a whole fed CJK token (at any
 *     position in the run, not only the last), found by DYNAMIC PROGRAMMING rather than a greedy
 *     longest-piece search: greedy commits to the first long match and cannot back out of it, so "数据中心化"
 *     fed "数据中心" + "中心化" (the split 数据｜中心化) was missed — the greedy pass ate "数据中心" whole
 *     and was left with a lone "化". The piece length tried is bounded to a small constant regardless of how
 *     long a fed token is: a longer fed substring always splits into short pieces that are substrings too,
 *     so the bound changes nothing about which runs are coverable, only how many pieces prove it.
 *   - TRUNCATION is an exception on the run's own FINAL token alone (whichever class it is), and only when
 *     the run's text ends with an ellipsis ("…", "...", or "⋯"): that token may then be a proper prefix of a
 *     fed token of the same class ("wa" of "water" when a run reads "…wa…"), or — for a CJK run — the DP's
 *     final piece specifically may be a prefix of a fed CJK token ("压" of "压粉均匀" when a run reads
 *     "研磨更细压…", the DP covering 研磨更细 whole and "压" as that trailing piece). Elsewhere a short token
 *     is not "maybe truncated", it is a different word — "Step 1" is not licensed by a fed "Steps", and a
 *     bare "O" is not licensed by "Output".
 *   - a WORD token made only of digits (internal `.`/`,` allowed) is a NUMERAL, compared by VALUE (thousands
 *     separators stripped, so "87" matches a fed 87.0 and "1,200" matches a fed 1200) when that value is a
 *     finite number, and as a plain STRING otherwise — a numeral no `Number()` call parses (Arabic-Indic or
 *     Devanagari digits, two separators in one run) never joins the pool as the same value as every OTHER
 *     numeral no `Number()` parses; it is judged only against a fed numeral written the same way.
 *     FIGURE-SHAPED (holds `.`/`,`; sits, across whitespace, against `%`, `‰` or a currency sign; or sits,
 *     with NO whitespace at all, directly against the letter x/X) means fabricated unless its value equals a
 *     numeral of a fed string or a numeric prop value ("87%", "3.2×", "$1,200", "3x" baked with no source are
 *     exactly this). A plain integer with no figure mark is presumed DERIVED (an index, a step number, an
 *     axis tick) and passes untested — ticks "0"/"25"/"50", and a bare "3" next to an unrelated word that
 *     merely ENDS or STARTS with the letter x ("Box 3", "3 xylophones"), are not copy.
 *   - every string this audits is folded FIRST (Unicode canonical composition, so an NFD "e" + a combining
 *     accent recomposes into the one letter an NFC fed string spells, before any per-character script test can
 *     be confused by the accent alone) and each character is folded again for the STRUCTURAL questions only —
 *     is it a digit, is a `.`/`,` a numeral's own separator, is a neighbour a figure mark — so "８７％" reads
 *     as the figure 87% and "１，２００" as one numeral, though what gets REPORTED keeps the run's own written
 *     form. "One character" is a GRAPHEME, not a code point — an NFD accent held in its own span is still one
 *     glyph of the letter it paints onto.
 *   - config-like prop strings (an enum value, a file name) stay in the same fed pool on purpose: the pool is
 *     every word the film handed this beat, not a sentence parser that only trusts prose.
 *
 * `scope: 'slots'` asks only the text inside objects (`[data-object-slot]`), for a library register holding a
 * film's object: the register's own words are judged elsewhere.
 *
 * BLIND SPOTS, by construction: a DOM walk cannot see text painted by a CSS `content:` rule, drawn onto a
 * `<canvas>`, or baked into a raster image — none of those write a text node this can read.
 */
export const UNFED_TEXT_TAG = 'UNFED-TEXT ';
// Script EXTENSIONS, not a character's primary Script: a Katakana/Hiragana run's own prolonged-sound mark
// "ー" and the CJK iteration mark "々" both carry the primary Script value "Common" (several scripts write
// with them), which primary-Script scanning reads as a token break — "コーヒー" tokenized as four pieces,
// two of them a bare "ー" belonging to neither neighbour. Script Extensions is Unicode's own answer to "which
// scripts actually use this character", and both "ー" and "々" extend into Han/Hiragana/Katakana/Hangul.
const CJK_SCRIPT_RE = /[\p{Script_Extensions=Han}\p{Script_Extensions=Hiragana}\p{Script_Extensions=Katakana}\p{Script_Extensions=Hangul}]/u;
// A letter-or-digit gate BEFORE the CJK sub-check: several punctuation marks (the interpunct "·" among them)
// carry Script Extensions into Han/Hiragana/Katakana/Hangul too (Unicode marks them shared with those
// scripts' own punctuation) without being a letter or digit at all — un-gated, "Mix 2 · Grind 3" tokenized
// the dot itself as a lone one-character CJK token, fed by nothing.
const LETTER_DIGIT_RE = /[\p{L}\p{N}]/u;
const DIGIT_RE = /\p{Nd}/u;
// `\p{Sc}` is every currency symbol (a hardcoded {$,¥,€,£} list would miss the one a topic actually uses). The
// letter x/X is judged separately, with no whitespace tolerance at all (see isFigureShaped) — it is common
// English prose ("Box 3", "3 x 4") far more often than a multiplication sign, and only the character DIRECTLY
// against a numeral, with nothing at all between them, disambiguates it.
const SYMBOL_MARK_RE = /[%×‰]/u;
const FIGURE_X_RE = /x/i;
const CURRENCY_RE = /\p{Sc}/u;
const WHITESPACE_RE = /\p{White_Space}/u;              // incl. no-break (U+00A0) and thin (U+2009) spaces
const ENDS_WITH_ELLIPSIS_RE = /(…|\.\.\.|⋯)\s*$/;
const COMBINING_MARK_RE = /^\p{M}+$/u;

type UnfedTok = {raw: string; norm: string; cjk: boolean; numeral: boolean; start: number; end: number};

/** A single character's fold for a STRUCTURAL question (is it a digit, a numeral separator, a figure mark) —
 * fullwidth/compatibility forms collapse to their ASCII selves. Never the basis for the reported text: `.raw`
 * keeps the run's own written form (a fullwidth run is reported as written). A fold that expands past one
 * character (rare) is not trusted — the source character stands in for itself rather than desyncing `.raw`
 * from what is actually being scanned. */
const foldCh = (ch: string): string => {
  const f = ch.normalize('NFKC').toLowerCase();
  return [...f].length === 1 ? f : ch;
};

type CharClass = 'cjk' | 'digit' | 'letter' | null;
const classOf = (fch: string): CharClass => {
  if (!LETTER_DIGIT_RE.test(fch)) return null;
  if (DIGIT_RE.test(fch)) return 'digit';
  return CJK_SCRIPT_RE.test(fch) ? 'cjk' : 'letter';
};

/**
 * Split text into script-class tokens. The WHOLE string is canonically composed first (NFC — composition
 * only, no compatibility folding, so a fullwidth run stays fullwidth in `.raw`): composing needs a
 * character's neighbour, which a per-character fold cannot see, so an NFD "café" (e + a combining acute)
 * would otherwise split into a token "cafe" plus a lone, unclassifiable accent mark, never matching an NFC
 * fed "café". `.raw` is the run's own text; `.norm` is `.raw` folded (NFKC + lowercase) for equality and
 * value comparisons. A CJK/digit/letter class change always ends a token — "9bar" is "9" then "bar", "5ms"
 * is "5" then "ms" — except that a `.`/`,` continues a DIGIT token between two (possibly fullwidth) digits, a
 * numeral's own separator, so "3.2×" tokenizes as the numeral "3.2" then the mark "×", never "3" then ".2×",
 * and a fullwidth "１，２００" tokenizes as one numeral, not "1" then "200".
 */
export const tokenizeUnfed = (raw: string): UnfedTok[] => {
  const chars = Array.from(raw.normalize('NFC'));
  const toks: UnfedTok[] = [];
  let cur = '', curCls: CharClass = null, curStart = 0;
  const flush = (endIdx: number) => {
    if (cur) {
      const norm = cur.normalize('NFKC').toLowerCase();
      toks.push({raw: cur, norm, cjk: curCls === 'cjk', numeral: curCls === 'digit', start: curStart, end: endIdx});
    }
    cur = '';
    curCls = null;
  };
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i], fch = foldCh(ch);
    const cls = classOf(fch);
    if (cls) {
      if (curCls === null) {
        curCls = cls;
        cur = ch;
        curStart = i;
      } else if (curCls === cls) {
        cur += ch;
      } else {
        flush(i);
        curCls = cls;
        cur = ch;
        curStart = i;
      }
    } else if ((fch === '.' || fch === ',') && curCls === 'digit' &&
               i + 1 < chars.length && DIGIT_RE.test(foldCh(chars[i + 1]))) {
      cur += ch;                                          // a numeral's own internal separator
    } else {
      flush(i);
    }
  }
  flush(chars.length);
  return toks;
};

const stripCommas = (s: string) => s.replace(/,/g, '');
/** A numeral's comparison KEY: its parsed VALUE when `Number()` reads that value as finite, else its own
 * folded STRING. `Set.has` uses SameValueZero, under which every `NaN` is the SAME value — comparing by a bare
 * `Number(...)` let one fed numeral no parser reads (Arabic-Indic or Devanagari digits, two separators in one
 * run) license every OTHER unparseable numeral regardless of its actual digits, purely because both sides
 * became `NaN`. Falling back to the string keeps two different unparseable numerals apart. */
const numeralKey = (t: UnfedTok): number | string => {
  const v = Number(stripCommas(t.norm));
  return Number.isFinite(v) ? v : t.norm;
};

/** Does this numeral CLAIM to be a real figure (a measurement, a percentage, a price) rather than an index?
 * A symbol mark may sit across whitespace ("87 %", a no-break space included) — the run already glues
 * `87<span>%</span>` into one run, so this only has to look past real space characters, not across elements.
 * The letter x/X is judged differently, with NO whitespace tolerance at all: it is a common word's own last or
 * first letter far more often than a multiplication sign ("Box 3", "Max 5", "3 xylophones" are plain
 * integers, their neighbouring word's x nowhere near them once even one space sits between), so only a
 * character directly, immediately against the numeral counts ("3x", "x3"). */
const isFigureShaped = (t: UnfedTok, chars: string[]): boolean => {
  if (t.norm.includes('.') || t.norm.includes(',')) return true;   // .norm is ASCII-folded; a fullwidth "，" is not
  const before = t.start > 0 ? chars[t.start - 1] : '';
  const after = t.end < chars.length ? chars[t.end] : '';
  if ((before && FIGURE_X_RE.test(foldCh(before))) || (after && FIGURE_X_RE.test(foldCh(after)))) return true;
  const isSymbol = (ch: string) => !!ch && (SYMBOL_MARK_RE.test(foldCh(ch)) || CURRENCY_RE.test(ch));
  let i = t.start - 1;
  while (i >= 0 && WHITESPACE_RE.test(chars[i])) i--;
  if (i >= 0 && isSymbol(chars[i])) return true;
  let j = t.end;
  while (j < chars.length && WHITESPACE_RE.test(chars[j])) j++;
  return j < chars.length && isSymbol(chars[j]);
};

type FedContext = {wordPool: Set<string>; wordList: string[]; cjkPool: string[]; cjkSubstrings: Set<string>;
  cjkSingles: Set<string>; numeralPool: Set<number | string>};

const CJK_PIECE_MAX = 16;

const buildFedContext = (fed: unknown[]): FedContext => {
  const entries = fed.map((f) => tokenizeUnfed(String(f ?? ''))).filter((toks) => toks.length > 0);
  const wordToks = entries.flatMap((toks) => toks.filter((t) => !t.cjk && !t.numeral));
  const cjkToks = entries.flatMap((toks) => toks.filter((t) => t.cjk));
  const numeralToks = entries.flatMap((toks) => toks.filter((t) => t.numeral));
  // Every substring of length 2..16 of every fed CJK token, precomputed once — coverCjk below then tests
  // membership in this set rather than scanning the fed pool itself at every position, and a piece longer
  // than 16 characters is never tried: a longer fed substring always splits into pieces of at most 16
  // characters that are themselves substrings of it, so bounding the search here changes nothing about which
  // runs are coverable. A single-character fed token is kept in its OWN set — it may cover a piece anywhere
  // in a run, but only as a whole token match, never as a substring of something longer.
  const cjkSubstrings = new Set<string>();
  const cjkSingles = new Set<string>();
  for (const t of cjkToks) {
    const cs = Array.from(t.norm);
    if (cs.length === 1) cjkSingles.add(t.norm);
    for (let start = 0; start < cs.length; start++) {
      for (let len = 2; len <= Math.min(CJK_PIECE_MAX, cs.length - start); len++) {
        cjkSubstrings.add(cs.slice(start, start + len).join(''));
      }
    }
  }
  return {
    wordPool: new Set(wordToks.map((t) => t.norm)),
    wordList: wordToks.map((t) => t.norm),               // kept as a list too, for the truncation prefix search
    cjkPool: cjkToks.map((t) => t.norm),
    cjkSubstrings,
    cjkSingles,
    numeralPool: new Set(numeralToks.map(numeralKey)),
  };
};

/**
 * A CJK token is fed when it splits into pieces each either ≥2 characters and a substring of ONE fed CJK
 * token, or exactly 1 character and itself a WHOLE fed CJK token — at ANY position, not only the run's last
 * character ("研磨与压粉", fed 研磨/与/压粉, splits 研磨｜与｜压粉 with "与" the middle piece) — dynamic
 * programming, not greedy. `canCover[i]` is true when the prefix of length `i` is fully covered by pieces.
 * Under an ellipsis, the FINAL piece (the one reaching the very end of the run) may instead be a proper,
 * shorter prefix of a fed CJK token ("研磨更细压…" splits 研磨更细｜压…, "压" a prefix of "压粉均匀").
 */
const coverCjk = (text: string, ctx: FedContext, endsEllipsis: boolean): boolean => {
  if (ctx.cjkPool.some((f) => f === text)) return true;
  const cs = Array.from(text);
  const n = cs.length;
  const canCover = new Array<boolean>(n + 1).fill(false);
  canCover[0] = true;
  for (let i = 0; i < n; i++) {
    if (!canCover[i]) continue;
    for (let len = Math.min(CJK_PIECE_MAX, n - i); len >= 1; len--) {
      const end = i + len;
      if (canCover[end]) continue;
      const piece = cs.slice(i, end).join('');
      if (len >= 2 && ctx.cjkSubstrings.has(piece)) {
        canCover[end] = true;
      } else if (len === 1 && ctx.cjkSingles.has(piece)) {
        canCover[end] = true;
      } else if (endsEllipsis && end === n && ctx.cjkPool.some((f) => f.length > piece.length && f.startsWith(piece))) {
        canCover[end] = true;
      }
    }
  }
  return canCover[n];
};

/** WORD-LEVEL PROVENANCE (see the docstring above): a fed word may appear anywhere on the frame, so this is
 * pool membership, not a search for a contiguous run inside one fed string. `isTruncatable` is true only for
 * the run's own final token, and only when the run's text ends with an ellipsis. */
const isWordFed = (t: UnfedTok, ctx: FedContext, isTruncatable: boolean): boolean => {
  if (ctx.wordPool.has(t.norm)) return true;
  if (!isTruncatable) return false;
  return ctx.wordList.some((f) => f.length > t.norm.length && f.startsWith(t.norm));
};

const REPORT_CAP = 40;
const capped = (s: string) => (s.length > REPORT_CAP ? s.slice(0, REPORT_CAP) + '…' : s);

/** Every unfed token of ONE run's already-tokenized text (`chars` is the same run text, for the figure-mark
 * neighbour lookup). Truncation is scoped to the run's true final token, whatever its class — a numeral is
 * never "truncated", so it is exempt regardless of position. */
const unfedTokensOf = (toks: UnfedTok[], chars: string[], endsEllipsis: boolean, ctx: FedContext): string[] => {
  const out: string[] = [];
  const lastIdx = toks.length - 1;
  toks.forEach((t, i) => {
    const isFinal = i === lastIdx && endsEllipsis;
    if (t.cjk) {
      if (!coverCjk(t.norm, ctx, isFinal)) out.push(capped(t.raw));
    } else if (t.numeral) {
      if (isFigureShaped(t, chars) && !ctx.numeralPool.has(numeralKey(t))) out.push(capped(t.raw));
    } else if (!isWordFed(t, ctx, isFinal)) {
      out.push(capped(t.raw));
    }
  });
  return out;
};

// ── WHAT ONE RUN OF TEXT IS ─────────────────────────────────────────────────────────────────────────────
//
// The unit of judgement is an element's RUN, built from its own child nodes in order — not "every element
// with its own direct text node": a `<br>` breaks the run without gluing the text on either side; an
// `inline` child with real text of its own is ABSORBED into the run, proximity-gated the same way a glyph
// is (below); a child rendering exactly one grapheme is a GLYPH, glued to (or, past the glue distance, space
// separated from) an immediately preceding glyph or absorbed child by the gap between their boxes; a child
// with no rendered text but a real box width is a SPACER and contributes a space; anything else (block-level,
// a flex/grid item, inline-block) is its OWN unit, judged separately and recursively — never folded into
// this run, so one such child among a row of glyphs breaks nothing else in that row. An echoed duplicate is
// pruned before any of this, so it is never read as content at all.
const NOT_LIVE_TAGS = new Set(['script', 'style', 'template', 'noscript']);
const isPrunedTag = (el: Element): boolean => NOT_LIVE_TAGS.has(el.tagName.toLowerCase());

/** Is this TEXT NODE actually painted? A Range over the node itself, never the ancestor element's own box —
 * the only way to tell it apart from an ancestor whose `display: contents` gives it no box of its own (the
 * text still paints, inherited into whichever ancestor DOES have one) and from text that legitimately
 * overflows a zero-size container the author sized on purpose. A text node holding combining marks only is
 * kept regardless of its own rect: it paints onto the PRECEDING glyph, not one of its own, so it commonly
 * measures a zero-area rect of its own (the library's `[...s]` per-character idiom splits "é" into an "e"
 * span and a lone U+0301 span) — dropping it for having no area of its own read "Café" as "Cafe". */
const textNodeIsRendered = (n: Node, doc: Document): boolean => {
  if (COMBINING_MARK_RE.test(n.textContent ?? '')) return true;
  if (!doc.createRange) return true;      // no Range API in this engine: assume rendered, not silently dropped
  const r = doc.createRange();
  r.selectNodeContents(n);
  const rects = Array.from(r.getClientRects());
  r.detach?.();
  return rects.some((rc) => rc.width > 0 && rc.height > 0);
};

/** THE prune rule for an element child — echo, a tag that is never content, or computed `display: none` —
 * and ONLY these: never the element's own box, which `display: contents` legitimately lacks. */
const isPrunedChild = (el: Element, win: Window): boolean =>
  isEcho(el) || isPrunedTag(el) || win.getComputedStyle(el).display === 'none';

/** The text a subtree would show, read through `display: contents` and pruned the same way a run is — used
 * only to CLASSIFY a child (is it one grapheme? is it empty?), not itself a matching unit. */
const renderedTextOf = (el: Element, win: Window): string => {
  let s = '';
  el.childNodes.forEach((n) => {
    if (n.nodeType === 3) {
      if (textNodeIsRendered(n, el.ownerDocument)) s += n.textContent ?? '';
    } else if (n.nodeType === 1) {
      const c = n as Element;
      if (!isPrunedChild(c, win)) s += renderedTextOf(c, win);
    }
  });
  return s;
};

let _segmenter: {segment: (s: string) => Iterable<unknown>} | null | undefined;
/** GRAPHEMES, not code points: an NFD "é" (e + a combining acute) is ONE user-perceived character, but a
 * code-point count reads it as two, so a "é" held whole in one glyph span failed the "exactly one grapheme"
 * test and was never glued to its neighbours. `Intl.Segmenter` (grapheme granularity) is the grapheme-cluster
 * aware count; an engine without it falls back to code points rather than throwing — a coarser count on a
 * rare cluster, not a broken audit. */
const graphemeLen = (s: string): number => {
  if (_segmenter === undefined) {
    try {
      const Ctor = (Intl as unknown as {Segmenter?: new (l?: string, o?: object) =>
        {segment: (s: string) => Iterable<unknown>}}).Segmenter;
      _segmenter = Ctor ? new Ctor(undefined, {granularity: 'grapheme'}) : null;
    } catch {
      _segmenter = null;
    }
  }
  if (!_segmenter) return Array.from(s).length;
  let n = 0;
  for (const _ of _segmenter.segment(s)) n++;
  return n;
};

/** The innermost element that directly holds the glyph's own text node(s) — walking down through wrapper
 * elements that hold no text of their own and have exactly one (unpruned) element child. A rotated "scrap"
 * that positions a per-glyph letter commonly inherits the page's own font size, while the SPAN actually
 * sized to the letter carries its real one — measuring the glue distance against the wrapper's size reads a
 * large letter's real gaps as many multiples of a small, unrelated number. */
const innermostTextHolder = (el: Element, win: Window): Element => {
  let cur = el;
  for (;;) {
    const ownText = Array.from(cur.childNodes).some((n) => n.nodeType === 3 && textNodeIsRendered(n, cur.ownerDocument));
    if (ownText) return cur;
    const kids = Array.from(cur.children).filter((k) => !isPrunedChild(k, win));
    if (kids.length !== 1) return cur;
    cur = kids[0];
  }
};

type Rect = {left: number; top: number; right: number; bottom: number};

/** The gap between two boxes, measured along whichever axis they are actually adjacent on — same ROW (their
 * vertical ranges overlap) reads the horizontal gap, same COLUMN (horizontal ranges overlap) reads the
 * vertical one, and boxes on neither axis are not glued at all. Always an ABSOLUTE distance: a signed
 * left-to-right gap reads an RTL pair, or a row-reverse or bottom-to-top one, as touching regardless of how
 * far apart they actually sit — the "next" box in DOM order sits to the LEFT of or ABOVE the previous one,
 * giving a large negative number that a signed comparison against a small positive threshold always passes. */
const rectGap = (a: Rect, b: Rect): number => {
  const vOverlap = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
  if (vOverlap > 0) return Math.max(0, Math.max(a.left, b.left) - Math.min(a.right, b.right));
  const hOverlap = Math.min(a.right, b.right) - Math.max(a.left, b.left);
  if (hOverlap > 0) return Math.max(0, Math.max(a.top, b.top) - Math.min(a.bottom, b.bottom));
  return Infinity;
};

/** The union box of a text node's own painted rects (never an ancestor's), for gap measurement against a
 * neighbouring glyph or absorbed child — `null` when the node paints nothing of its own to measure. */
const rangeBoxOf = (n: Node, doc: Document): Rect | null => {
  if (!doc.createRange) return null;
  const r = doc.createRange();
  r.selectNodeContents(n);
  const rects = Array.from(r.getClientRects()).filter((rc) => rc.width > 0 && rc.height > 0);
  r.detach?.();
  if (!rects.length) return null;
  return {
    left: Math.min(...rects.map((x) => x.left)), top: Math.min(...rects.map((x) => x.top)),
    right: Math.max(...rects.map((x) => x.right)), bottom: Math.max(...rects.map((x) => x.bottom)),
  };
};

const GLUE_EM = 0.6;

/**
 * Build ONE element's run from its child nodes, in order, and collect the OWN-UNIT children found along the
 * way (block-level, a flex/grid item, inline-block — anything not `inline`/`contents` — judged separately,
 * never folded into this run). A GLYPH (rendered text of exactly one grapheme, nesting included — a glyph
 * inside wrapper spans is still a glyph) and an ABSORBED `inline` child both glue to whatever content came
 * immediately before them when the gap between their boxes (see `rectGap`) is within `GLUE_EM` of the font
 * size of the element that actually holds THEIR OWN text (see `innermostTextHolder`), else they are space
 * separated — a chip row `<span>Grind</span><span>Tamp</span>` set apart with margins reads "Grind Tamp", not
 * "GrindTamp"; a child with no rendered text but a real box width is a SPACER and contributes a space (an
 * empty flex-gap div, a caret); `<br>` and any own-unit boundary both just break the run so neither side
 * glues across it.
 */
const buildRun = (el: Element, win: Window): {text: string; ownUnits: Element[]; lastBox: Rect | null} => {
  const ownUnits: Element[] = [];
  let text = '';
  let lastBox: Rect | null = null;
  const append = (piece: string, glue: boolean) => {
    if (!piece) return;
    if (glue || !text) text += piece;
    else text += (/\s$/.test(text) ? '' : ' ') + piece;
  };
  const glueDecision = (r: Rect, fontSize: number): boolean => {
    if (!lastBox) return true;
    const gap = rectGap(lastBox, r);
    return fontSize > 0 ? gap <= GLUE_EM * fontSize : gap === 0;
  };
  const breakRun = () => {
    if (text && !/\s$/.test(text)) text += ' ';
    lastBox = null;
  };
  el.childNodes.forEach((n) => {
    if (n.nodeType === 3) {
      if (textNodeIsRendered(n, el.ownerDocument)) {
        append(n.textContent ?? '', true);
        const b = rangeBoxOf(n, el.ownerDocument);
        if (b) lastBox = b;                    // a mark-only node with no box of its own leaves lastBox as-is
      }
      return;
    }
    if (n.nodeType !== 1) return;
    const child = n as Element;
    if (isPrunedChild(child, win)) return;      // echoes never update lastBox or contribute a gap endpoint
    if (child.tagName.toLowerCase() === 'br') {
      breakRun();
      return;
    }
    const cs = win.getComputedStyle(child);
    if (cs.display === 'contents') {
      // No box of its own and no line break either — its children join THIS run exactly where it sits.
      const sub = buildRun(child, win);
      append(sub.text, true);
      ownUnits.push(...sub.ownUnits);
      if (sub.lastBox) lastBox = sub.lastBox;
      return;
    }
    const rendered = renderedTextOf(child, win);
    if (graphemeLen(rendered) === 1) {
      const r = child.getBoundingClientRect();
      const fontSize = parseFloat(win.getComputedStyle(innermostTextHolder(child, win)).fontSize || '0') || 0;
      append(rendered, glueDecision(r, fontSize));
      lastBox = r;
      return;
    }
    if (!rendered.trim()) {
      if (child.getBoundingClientRect().width > 0) append(' ', false);   // a spacer, not silence
      lastBox = null;
      return;
    }
    if (cs.display === 'inline') {
      const r = child.getBoundingClientRect();
      const fontSize = parseFloat(win.getComputedStyle(innermostTextHolder(child, win)).fontSize || '0') || 0;
      const glue = glueDecision(r, fontSize);
      const sub = buildRun(child, win);
      append(sub.text, glue);
      ownUnits.push(...sub.ownUnits);
      lastBox = r;
      return;
    }
    breakRun();
    ownUnits.push(child);
  });
  return {text, ownUnits, lastBox};
};

const collectUnfed = (el: Element, win: Window, out: string[], ctx: FedContext) => {
  if (isEcho(el)) return;
  const {text, ownUnits} = buildRun(el, win);
  if (text) {
    const toks = tokenizeUnfed(text);
    if (toks.length) {
      const chars = Array.from(text.normalize('NFC'));
      const endsEllipsis = ENDS_WITH_ELLIPSIS_RE.test(text);
      for (const w of unfedTokensOf(toks, chars, endsEllipsis, ctx)) {
        if (!out.includes(w)) out.push(w);
      }
    }
  }
  for (const u of ownUnits) collectUnfed(u, win, out, ctx);
};

export const auditUnfedText = (root: Element, fed: unknown[], scope: 'all' | 'slots'): string[] => {
  const win = root.ownerDocument?.defaultView;
  if (!win) return [];
  const ctx = buildFedContext(fed);
  const out: string[] = [];
  const starts = scope === 'slots' ? Array.from(root.querySelectorAll('[data-object-slot]')) : [root];
  for (const s of starts) collectUnfed(s, win, out, ctx);
  return out;
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
export const TextSafeAudit: React.FC<{enabled?: boolean; mode?: 'safe' | 'collisions' | 'fed' | 'unfed';
  fed?: unknown[]; scope?: 'all' | 'slots'}> = ({enabled = false, mode = 'safe', fed, scope = 'all'}) => {
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
      if (mode === 'unfed') {
        // Capped like every other audit's payload (MAX_REPORTED) — an uncapped list on a badly-broken beat is
        // cut mid-JSON in the CLI's error message and arrives as nothing parseable at all. `total` carries the
        // true count past the cap, so the caller's message still says how many, not just which twelve.
        const hits = auditUnfedText(body, fed ?? [], scope);
        cancelRender(new Error(UNFED_TEXT_TAG +
          JSON.stringify({unfed: hits.slice(0, MAX_REPORTED), total: hits.length})));
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
  }, [enabled, handle, mode, fed, scope]);

  if (!enabled) return null;
  // Its own box IS the canvas rect — measured rather than assumed, so the audit is correct at any aspect
  // and under any render scale.
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
};

export default TextSafeAudit;
