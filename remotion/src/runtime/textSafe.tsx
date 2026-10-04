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
import {cancelRender, continueRender, delayRender, useCurrentFrame} from 'remotion';
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
 * ONE STREAM, TWO KINDS OF BOUNDARY. The audited scope is read in document order as one character stream, and
 * no distance between glyphs is ever measured: letter spacing, fixed slots, wrapped lines and stacked labels
 * set a word's own letters as far apart as two words, so no gap tells the two apart. Instead:
 *
 *   - a HARD boundary is where a word certainly ends: a separator character (whitespace, punctuation, a symbol
 *     — anything but a letter, a digit or a combining mark), a `<br>`, a whitespace-only text node or element
 *     (rendered or not — a zero-width space included), an element with no text whose box takes room in the
 *     flow (a spacer, a caret — never an absolutely or fixed positioned decoration laid over the text), both
 *     edges of a child that is block-level, a flex or grid item, or inline-block AND holds more than one
 *     grapheme (an element EDGE: beyond it is another label), and a change of class among CJK (Han/kana/Hangul
 *     by Unicode's Script Extensions, so ー and 々 stay inside their run), other letters (WORD) and digits
 *     (NUM) — "9bar" is a value and a unit;
 *   - a SOFT boundary is every other place two text pieces meet — the edges of an inline child, of a child of
 *     any display holding one grapheme (type set a glyph per element, one-letter labels), a text node against
 *     an inline element. It may or may not end a word: the fed words decide.
 *
 * The stream splits at its hard boundaries into SEGMENTS, each of one class:
 *
 *   - a WORD segment is fed when some of its soft boundaries cut it into parts that are each exactly a word of
 *     a fed string: per-glyph "G r i n d" is "grind" uncut, stacked labels "A" "B" "C" are three cuts, a
 *     two-line per-glyph label is "grind" | "tamp", "Pre<b>view</b>" is "preview". Immediately before an
 *     ellipsis ("…", "...", "⋯") the last part may instead be a prefix of a fed word ("Outp…"); anywhere else
 *     a shorter word is a different word — "Step" is not licensed by a fed "Steps", a bare "O" not by
 *     "Output". The price of reading no geometry: baked one-letter labels that together spell a fed word read
 *     as that word ("O" stacked over "K", with "OK" fed).
 *   - a CJK segment has no word boundaries of its own (a line or element break can fall anywhere in a phrase),
 *     so its soft boundaries play no part: it is fed when it is covered by pieces that are each two or more
 *     characters of ONE fed CJK token, or one character that is itself a whole fed CJK token, at any position
 *     ("研磨与压粉" fed 研磨 / 与 / 压粉); before an ellipsis the final piece may be a prefix of a fed CJK token
 *     ("研磨更细压…"). A lone character that is only part of a fed token is not covered, or nearly every glyph
 *     in the language would pass. The cover is found by dynamic programming over pieces of at most
 *     CJK_PIECE_MAX characters — any longer piece splits into shorter ones that are substrings too, so the
 *     bound changes no verdict and keeps the work linear in the segment's length.
 *   - a NUM segment (digits, a `.`/`,` between two digits being the numeral's own separator) compares by VALUE
 *     when it parses to a finite number and as its folded STRING otherwise, so two numerals no parser reads
 *     (Arabic-Indic or Devanagari digits, two separators in one numeral) never match by both being NaN. A
 *     FIGURE-SHAPED numeral — holding `.`/`,`; with `%`, `×`, `‰` or a currency sign beside it across
 *     whitespace, a `<br>` or a spacer, never across an element EDGE (a table's next cell, a chart title under
 *     its last tick); or with a letter x directly against it, in the same text or across an inline element's
 *     edge — is fabricated unless a fed string holds the same numeral or a prop the value ("87%", "3.2×",
 *     "$1,200", "3x"). A plain integer is presumed DERIVED (an index, a step number, an axis tick) and passes;
 *     so does a numeral next to a word that merely ends or starts with an x ("Box 3", "3 xylophones"), or next
 *     to an "x" set as a label of its own (an axis letter, a close button).
 *
 * Every string, the fed ones included, is folded BEFORE it is tokenized — NFKC, then lower case — so "８７％" is
 * the figure 87%, an NFD "Café" is the fed "Café" and "ＧＲＩＮＤ" is "grind"; and the stream is cut into
 * GRAPHEMES before it is folded, so an accent held in its own span still lands on the letter before it. What
 * is reported is each unfed segment as the frame shows it (original case, capped at REPORT_CAP characters) —
 * for a CJK segment, each maximal run of characters no cover reaches. Config-like prop strings (an enum value,
 * a file name) stay in the fed pool on purpose: the pool is every word the film handed this beat.
 *
 * What is read: every text node a Range paints with some height (the width may be zero — tight negative letter
 * spacing collapses a narrow glyph), whatever its opacity, visibility or clipping at this frame (a cycling
 * constant list shows one word per frame, and the others are still words the film puts on screen), read
 * through `display: contents`; never an echo (`[data-echo]`), a `script`/`style`/`template`/`noscript`, or a
 * `display: none` subtree. `scope: 'slots'` asks only the text inside objects (`[data-object-slot]`), for a
 * library register holding a film's object: the register's own words are judged elsewhere.
 *
 * BLIND SPOTS, by construction: a DOM walk cannot see text painted by a CSS `content:` rule, drawn onto a
 * `<canvas>`, or baked into a raster image — none of those write a text node this can read.
 */
export const UNFED_TEXT_TAG = 'UNFED-TEXT ';
const CJK_SCRIPT_RE = /[\p{Script_Extensions=Han}\p{Script_Extensions=Hiragana}\p{Script_Extensions=Katakana}\p{Script_Extensions=Hangul}]/u;
const LETTER_DIGIT_RE = /[\p{L}\p{N}]/u;
const DIGIT_RE = /\p{Nd}/u;
const MARK_RE = /\p{M}/u;
const COMBINING_MARKS_RE = /^\p{M}+$/u;
const SPACE_RE = /[\p{White_Space}\u200B]/u;            // incl. no-break (U+00A0), thin and zero-width spaces
const SPACE_ONLY_RE = /^[\p{White_Space}\u200B]+$/u;
const VISIBLE_RE = /[^\p{White_Space}\u200B]/u;
const FIGURE_SYMBOL_RE = /[%×‰\p{Sc}]/u;                // `\p{Sc}`: every currency sign, not a hand-kept list
const NOT_LIVE_TAGS = new Set(['script', 'style', 'template', 'noscript']);
const CJK_PIECE_MAX = 16;
const REPORT_CAP = 40;

type CharClass = 'cjk' | 'word' | 'num';

/** The class of one folded code point: a combining mark continues whatever it follows, and anything that is
 * not a letter, digit or mark separates (null). Letter-or-digit is asked BEFORE the CJK script: several
 * punctuation marks (the interpunct "·" among them) carry CJK Script Extensions without being letters. */
const classOf = (c: string): CharClass | 'mark' | null => {
  if (MARK_RE.test(c)) return 'mark';
  if (!LETTER_DIGIT_RE.test(c)) return null;
  if (DIGIT_RE.test(c)) return 'num';
  return CJK_SCRIPT_RE.test(c) ? 'cjk' : 'word';
};

let _segmenter: {segment: (s: string) => Iterable<{segment: string}>} | null | undefined;
/** The text's GRAPHEMES, lazily: an NFD "é" (e + a combining acute) or a Devanagari cluster is one
 * user-perceived character, however many code points or elements it spans. Without `Intl.Segmenter`, a code
 * point with the combining marks after it is the nearest cluster. */
function* graphemesOf(s: string): Generator<string> {
  if (_segmenter === undefined) {
    try {
      const Ctor = (Intl as unknown as {Segmenter?: new (l?: string, o?: object) =>
        {segment: (s: string) => Iterable<{segment: string}>}}).Segmenter;
      _segmenter = Ctor ? new Ctor(undefined, {granularity: 'grapheme'}) : null;
    } catch {
      _segmenter = null;
    }
  }
  if (_segmenter) {
    for (const g of _segmenter.segment(s)) yield g.segment;
  } else {
    yield* s.match(/\P{M}\p{M}*|\p{M}+/gu) ?? [];
  }
}

/** More than one visible grapheme — whitespace is a boundary of its own, never a glyph. */
const holdsSeveralGraphemes = (s: string): boolean => {
  let n = 0;
  for (const g of graphemesOf(s)) {
    if (!SPACE_ONLY_RE.test(g) && ++n > 1) return true;
  }
  return false;
};

/** Is this TEXT NODE painted? A Range over the node itself, never an ancestor's box — the only way to read
 * text inside a `display: contents` wrapper (no box of its own) or overflowing a zero-size container the
 * author sized on purpose. Some height is enough: tight negative letter spacing collapses a narrow glyph's
 * width to zero while it still paints. A node of combining marks only is kept whatever its rect: it paints
 * onto the PRECEDING glyph (the library's `[...s]` per-character idiom splits "é" into an "e" span and a lone
 * U+0301 span), so it commonly measures nothing of its own. */
const textNodeIsRendered = (n: Node, doc: Document): boolean => {
  if (COMBINING_MARKS_RE.test(n.textContent ?? '')) return true;
  if (!doc.createRange) return true;      // no Range API in this engine: assume rendered, not silently dropped
  const r = doc.createRange();
  r.selectNodeContents(n);
  const rects = Array.from(r.getClientRects());
  r.detach?.();
  return rects.some((rc) => rc.height > 0);
};

/** Does an element with no text take room in the flow (a spacer, a caret, an icon)? An absolutely or fixed
 * positioned box is out of the flow — a decoration laid over the text (a split-flap tile's face, a highlight)
 * holds nothing apart. An empty INLINE box is its line's strut — as tall as the line and as wide as nothing —
 * so it needs a width too (padding, a border); any other box that extends at all (ElasticType's 56×0 flex-gap
 * div) takes room. */
const takesRoom = (el: Element, cs: CSSStyleDeclaration): boolean => {
  if (cs.position === 'absolute' || cs.position === 'fixed') return false;
  const r = el.getBoundingClientRect();
  return cs.display === 'inline' ? r.width > 0 && r.height > 0 : r.width > 0 || r.height > 0;
};

// What separates two text pieces, weakest first. INLINE and GLYPH are SOFT; BREAK and EDGE are HARD.
const INLINE = 1;       // two pieces meeting directly, or across an inline element's edge
const GLYPH = 2;        // across the edge of an element of any other display that holds one grapheme
const BREAK = 3;        // a <br>, whitespace, a spacer box
const EDGE = 4;         // the edge of a block-level / flex / grid / inline-block child holding several graphemes

/** The stream: a rendered text node's text, or a boundary between text pieces — a `<br>`, a whitespace-only text
 * node, a child's edge (0: none). */
type StreamItem = string | number;

/**
 * Append an element's children to the stream in document order, and return the text they show — rendered text,
 * plus whitespace-only text rendered or not — so the caller can tell how many graphemes the element holds.
 * Pruned: an echo, a tag that is never content, a `display: none` subtree. `display: contents` adds no edges.
 */
const walk = (el: Element, win: Window, out: StreamItem[]): string => {
  let text = '';
  el.childNodes.forEach((n) => {
    if (n.nodeType === 3) {
      const t = n.textContent ?? '';
      if (SPACE_ONLY_RE.test(t)) {
        out.push(BREAK);
        text += t;
      } else if (t && textNodeIsRendered(n, el.ownerDocument)) {
        out.push(t);
        text += t;
      }
      return;
    }
    if (n.nodeType !== 1) return;
    const child = n as Element;
    if (isEcho(child) || NOT_LIVE_TAGS.has(child.tagName.toLowerCase())) return;
    const cs = win.getComputedStyle(child);
    if (cs.display === 'none') return;
    if (child.tagName.toLowerCase() === 'br') {
      out.push(BREAK);
      return;
    }
    const lead = out.length;
    out.push(0);                                  // the child's leading edge, decided once its content is known
    const inner = walk(child, win, out);
    text += inner;
    const edge = cs.display === 'contents' ? 0
      : !VISIBLE_RE.test(inner) ? (inner.length > 0 || takesRoom(child, cs) ? BREAK : 0)
      : cs.display === 'inline' ? INLINE
      : holdsSeveralGraphemes(inner) ? EDGE : GLYPH;
    out[lead] = edge;
    out.push(edge);
  });
  return text;
};

/** One folded code point of the stream, the grapheme it came from, and the boundary between it and the code
 * point before it: 0 inside one text piece, else the strongest boundary between the two pieces. */
type Ch = {c: string; glyph: number; junction: number};

/**
 * The stream as folded code points. Each stretch between two HARD boundaries is cut into graphemes as one
 * string, so a combining mark in its own element joins the letter before it; a text piece that starts between
 * two graphemes carries the boundary before it, and one that starts inside a grapheme carries none.
 * `glyphs` keeps every grapheme as written, for reporting.
 */
const charsOf = (items: StreamItem[]): {glyphs: string[]; chars: Ch[]} => {
  const glyphs: string[] = [];
  const chars: Ch[] = [];
  let stretch: Array<{text: string; before: number}> = [];
  const flush = () => {
    const starts = new Map<number, number>();
    let at = 0;
    for (const p of stretch) {
      starts.set(at, p.before);
      at += p.text.length;
    }
    let pos = 0;
    for (const g of graphemesOf(stretch.map((p) => p.text).join(''))) {
      const junction = starts.get(pos) ?? 0;
      const glyph = glyphs.push(g) - 1;
      Array.from(g.normalize('NFKC').toLowerCase()).forEach((c, k) =>
        chars.push({c, glyph, junction: k === 0 ? junction : 0}));
      pos += g.length;
    }
    stretch = [];
  };
  let pending = EDGE;                             // nothing comes before the stream
  for (const it of items) {
    if (typeof it === 'number') {
      pending = Math.max(pending, it);
      continue;
    }
    const before = Math.max(pending, INLINE);
    if (before >= BREAK) flush();
    stretch.push({text: it, before});
    pending = 0;
  }
  flush();
  return {glyphs, chars};
};

/** A maximal run of one class between HARD boundaries: `chars[from..to)`, folded into `norm`; `cuts` are its
 * SOFT junctions, as offsets into `norm`. */
type Segment = {cls: CharClass; from: number; to: number; norm: string; cuts: number[]};

const segmentsOf = (chars: Ch[]): Segment[] => {
  const segs: Segment[] = [];
  let cur: Segment | null = null;
  for (let i = 0; i < chars.length; i++) {
    const {c, junction} = chars[i];
    const cls = classOf(c);
    if (cur && junction < BREAK) {
      if (cls === cur.cls) {
        if (junction > 0) cur.cuts.push(cur.norm.length);        // INLINE or GLYPH: a SOFT boundary
        cur.norm += c;
        continue;
      }
      if (cls === 'mark') {
        cur.norm += c;
        continue;
      }
      const next = chars[i + 1];
      if (cur.cls === 'num' && (c === '.' || c === ',') && next && next.junction < BREAK &&
          classOf(next.c) === 'num') {
        cur.norm += c;                                  // a numeral's own separator: "3.2", "1,200"
        continue;
      }
    }
    if (cur) {
      cur.to = i;
      segs.push(cur);
      cur = null;
    }
    if (cls !== null && cls !== 'mark') cur = {cls, from: i, to: i + 1, norm: c, cuts: []};
  }
  if (cur) {
    cur.to = chars.length;
    segs.push(cur);
  }
  return segs;
};

/** An ellipsis starting at `chars[i]` ("…" and a vertical "︙" fold to "..."). */
const ellipsisAt = (chars: Ch[], i: number): boolean =>
  chars[i]?.c === '⋯' || (chars[i]?.c === '.' && chars[i + 1]?.c === '.' && chars[i + 2]?.c === '.');

type FedContext = {words: Set<string>; wordList: string[]; wordLengths: number[]; cjkTokens: string[];
  cjkPieces: Set<string>; cjkSingles: Set<string>; numerals: Set<number | string>};

/** A numeral's comparison KEY: its value when `Number()` reads a finite one, else its folded string —
 * `Set.has` compares by SameValueZero, under which every NaN is the same value. */
const numeralKey = (norm: string): number | string => {
  const v = Number(norm.replace(/,/g, ''));
  return Number.isFinite(v) ? v : norm;
};

/** The fed strings, tokenized by the stream's own rules: every WORD token (with the distinct lengths the WORD
 * cover tries), every CJK token with each of its substrings of 2..CJK_PIECE_MAX characters (and the tokens of
 * one character, which cover only as themselves), every numeral's key. */
const buildFedContext = (fed: unknown[]): FedContext => {
  const words = new Set<string>();
  const cjkTokens: string[] = [];
  const numerals = new Set<number | string>();
  for (const f of fed) {
    for (const s of segmentsOf(charsOf([String(f ?? '')]).chars)) {
      if (s.cls === 'word') words.add(s.norm);
      else if (s.cls === 'cjk') cjkTokens.push(s.norm);
      else numerals.add(numeralKey(s.norm));
    }
  }
  const cjkPieces = new Set<string>();
  const cjkSingles = new Set<string>();
  for (const t of cjkTokens) {
    const cs = Array.from(t);
    if (cs.length === 1) cjkSingles.add(t);
    for (let a = 0; a < cs.length; a++) {
      for (let len = 2; len <= Math.min(CJK_PIECE_MAX, cs.length - a); len++) {
        cjkPieces.add(cs.slice(a, a + len).join(''));
      }
    }
  }
  const wordList = Array.from(words);
  const wordLengths = Array.from(new Set(wordList.map((w) => w.length))).sort((a, b) => a - b);
  return {words, wordList, wordLengths, cjkTokens, cjkPieces, cjkSingles, numerals};
};

/** Can the segment's soft junctions cut it into fed words? `fits[j]`: its first `j` code units split into fed
 * words, each part ending at a soft junction or at the segment's end; `truncatable` lets the last part be a
 * prefix of a fed word instead. */
const wordFed = (seg: Segment, truncatable: boolean, ctx: FedContext): boolean => {
  const s = seg.norm;
  const ends = new Set(seg.cuts.concat(s.length));
  const fits = new Array<boolean>(s.length + 1).fill(false);
  fits[0] = true;
  for (let i = 0; i < s.length; i++) {
    if (!fits[i]) continue;
    for (const len of ctx.wordLengths) {
      if (i + len > s.length) break;
      if (ends.has(i + len) && ctx.words.has(s.slice(i, i + len))) fits[i + len] = true;
    }
    if (truncatable) {
      const rest = s.slice(i);
      if (ctx.wordList.some((w) => w.length > rest.length && w.startsWith(rest))) return true;
    }
  }
  return fits[s.length];
};

/** The characters of a CJK segment its best cover leaves uncovered — none when the segment is fed. `cost[j]`
 * is the fewest uncovered characters in the first `j`; `step[j]` is where the step reaching `j` began, and
 * `covered[j]` whether that step was a covering piece rather than one uncovered character. */
const cjkUncovered = (seg: Segment, truncatable: boolean, ctx: FedContext): boolean[] => {
  const cs = Array.from(seg.norm);
  const n = cs.length;
  const cost = new Array<number>(n + 1).fill(Infinity);
  const step = new Array<number>(n + 1).fill(0);
  const covered = new Array<boolean>(n + 1).fill(false);
  cost[0] = 0;
  for (let i = 0; i < n; i++) {
    for (let len = Math.min(CJK_PIECE_MAX, n - i); len >= 1; len--) {
      const j = i + len;
      if (cost[i] >= cost[j]) continue;
      const piece = cs.slice(i, j).join('');
      const fed = len >= 2 ? ctx.cjkPieces.has(piece) : ctx.cjkSingles.has(piece);
      const truncated = !fed && truncatable && j === n &&
        ctx.cjkTokens.some((t) => t.length > piece.length && t.startsWith(piece));
      if (fed || truncated) {
        cost[j] = cost[i];
        step[j] = i;
        covered[j] = true;
      }
    }
    if (cost[i] + 1 < cost[i + 1]) {
      cost[i + 1] = cost[i] + 1;
      step[i + 1] = i;
      covered[i + 1] = false;
    }
  }
  const uncovered = new Array<boolean>(n).fill(false);
  for (let j = n; j > 0; j = step[j]) {
    if (!covered[j]) uncovered[j - 1] = true;
  }
  return uncovered;
};

/** Is the nearest code point that is not whitespace, from `chars[i]` on in the direction `step`, a figure mark
 * found without crossing an element EDGE? Whitespace, a `<br>`, a spacer and a SOFT boundary are crossed. */
const markBeside = (chars: Ch[], i: number, step: 1 | -1): boolean => {
  for (; i >= 0 && i < chars.length; i += step) {
    if (chars[step === 1 ? i : i + 1].junction === EDGE) return false;
    if (!SPACE_RE.test(chars[i].c)) return FIGURE_SYMBOL_RE.test(chars[i].c);
  }
  return false;
};

/** Does this numeral CLAIM to be a real figure (a measurement, a percentage, a price) rather than an index?
 * A symbol mark counts across whitespace ("87 %", a no-break space included), a `<br>` or a spacer, never
 * across an element EDGE — beyond it is another label (a table's next cell, a chart title under its last
 * tick). The letter x counts only directly against the numeral, in the same text piece or across an inline
 * element's edge ("3x", "x3", `3<span>x</span>`): it is a word's own first or last letter ("Box 3",
 * "3 xylophones"), or a label of its own (an "x" axis letter, a close button), far more often than a sign. */
const isFigure = (seg: Segment, chars: Ch[]): boolean => {
  if (seg.norm.includes('.') || seg.norm.includes(',')) return true;
  const before = chars[seg.from - 1];
  const after = chars[seg.to];
  if (before?.c === 'x' && chars[seg.from].junction <= INLINE) return true;
  if (after?.c === 'x' && after.junction <= INLINE) return true;
  return markBeside(chars, seg.from - 1, -1) || markBeside(chars, seg.to, 1);
};

const capped = (s: string) => (s.length > REPORT_CAP ? s.slice(0, REPORT_CAP) + '…' : s);

/** Judge one stream, adding each unfed item — as the frame shows it — to `out` once. */
const judgeStream = (items: StreamItem[], ctx: FedContext, out: string[]) => {
  const {glyphs, chars} = charsOf(items);
  const shown = (a: number, b: number) =>
    glyphs.slice(chars[a].glyph, chars[b - 1].glyph + 1).join('').normalize('NFC');
  const report = (s: string) => {
    const w = capped(s);
    if (!out.includes(w)) out.push(w);
  };
  for (const seg of segmentsOf(chars)) {
    const truncatable = ellipsisAt(chars, seg.to);
    if (seg.cls === 'word') {
      if (!wordFed(seg, truncatable, ctx)) report(shown(seg.from, seg.to));
    } else if (seg.cls === 'num') {
      if (isFigure(seg, chars) && !ctx.numerals.has(numeralKey(seg.norm))) report(shown(seg.from, seg.to));
    } else {
      const miss = cjkUncovered(seg, truncatable, ctx);
      for (let a = 0; a < miss.length; a++) {
        if (!miss[a]) continue;
        let b = a;
        while (b + 1 < miss.length && miss[b + 1]) b++;
        report(shown(seg.from + a, seg.from + b + 1));
        a = b;
      }
    }
  }
};

export const auditUnfedText = (root: Element, fed: unknown[], scope: 'all' | 'slots'): string[] => {
  const win = root.ownerDocument?.defaultView;
  if (!win) return [];
  const ctx = buildFedContext(fed);
  const out: string[] = [];
  // Each object is a stream of its own; an object nested inside another is read once, as part of the outer.
  const scopes = scope === 'slots'
    ? Array.from(root.querySelectorAll('[data-object-slot]'))
      .filter((s) => !s.parentElement?.closest('[data-object-slot]'))
    : [root];
  for (const s of scopes) {
    if (isEcho(s)) continue;
    const items: StreamItem[] = [];
    walk(s, win, items);
    judgeStream(items, ctx, out);
  }
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

// ── THE TYPE-GLIDE CENSUS ────────────────────────────────────────────────────────────────────────────────
//
// WHAT IT ASKS. Does any type MOVE while Skia snaps its baseline to whole pixels? That is the defect in
// runtime/glide.ts: under an axis-aligned matrix a glyph run's baseline is rounded to the device pixel, so type
// that crawls by less than a pixel a frame holds still and then jumps, while everything drawn beside it glides.
// No still can show it and no single frame can either — it is a property of consecutive frames — so this records,
// per frame, every visible line of type whose composed matrix is axis-aligned, with its TRUE position, and
// `scripts/text_safe_qa.py --glide` reads the frames in order.
//
// WHY THE DOM AND NOT PIXELS. Both halves of the defect are things the layout engine knows exactly: the composed
// 2x2 the type is drawn under (Skia's own test is whether its skewY entry survives rounding to 1/1024), and where
// the line box truly sits — client rects are computed from the transform, before paint rounds anything. A pixel
// measure has to guess where the type is and what it should have done; this reads both.
//
// WHAT IS LISTED. Only type that CAN snap: a line under a matrix whose skewY entry rounds to zero. Type under the
// unlock, under a rotation, or tilted by a surface is counted (`u`) and not listed; type under a 3D chain, whose
// raster path this cannot read, is counted separately (`z`). An element or ancestor carrying `data-type-steps`
// is listed with flag `s`: type that is MEANT to step (a glitch's offset copies, a mechanical counter) — the
// reader excuses it and names it.

/** Prefix on each frame's census line in the browser log. */
export const TYPE_GLIDE_TAG = 'TYPE-GLIDE ';

/** One line of type that can snap, on one frame: key, true top of its first line box in px, effective opacity,
 *  its text (cut), and flags — `f` drawn through a blur or drop-shadow filter, `s` declared stepped. */
export type GlideLine = {k: string; y: number; o: number; t: string; fl?: string};

type Mat2 = [number, number, number, number];
type GlideChain = {M: Mat2 | null; L: Mat2 | null; ls: number; op: number; spatial: boolean; will: boolean;
  steps: boolean; key: string};

/** Skia's own test: the skewY entry, rounded to 1/1024 (`sk_relax`), is zero. */
export const snapsBaseline = (b: number): boolean => Math.round(Math.abs(b) * 1024) === 0;

// A BLUR OR A DROP-SHADOW RE-SNAPS TYPE THAT AN UNLOCK ABOVE IT HAD FREED. Measured on CameraTypeProbe's push:
// with the camera's unlock, type inside `filter: blur(0.6px)` or `drop-shadow(…)` stepped exactly as if there were
// no unlock (residual 0.267px against 0.011px without the filter) — Skia draws a spatial filter's content into a
// layer whose matrix keeps only the SCALE of the transform above it, so the skew is applied to the finished layer
// and never reaches the glyphs. Put the unlock INSIDE the filtered element and it works (0.012px). A colour filter
// (`saturate`, `brightness`, …) needs no layer of that kind and passes the unlock through (0.011px). So the skew
// that counts is the one composed BELOW the nearest blur/drop-shadow, times the scale that layer keeps.
const SPATIAL_FILTER = /blur\(|drop-shadow\(|url\(/;
const mul2 = (a: Mat2, b: Mat2): Mat2 =>
  [a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3]];

export const auditGlide = (root: Element, frame: DOMRect): {lines: GlideLine[]; u: number; z: number} => {
  const win = root.ownerDocument?.defaultView;
  if (!win) return {lines: [], u: 0, z: 0};
  // ONE getComputedStyle per element, memoised down the tree: the matrix, the opacity and the flags of an element
  // are its parent's composed with its own. A character field draws a thousand text elements; walking each one's
  // ancestors from scratch is the quadratic cost `rotatedUnder` already learned to avoid.
  const memo = new Map<Element, GlideChain>();
  const childIndex = new Map<Element, number>();
  const chain = (el: Element): GlideChain => {
    const hit = memo.get(el);
    if (hit) return hit;
    const parent = el.parentElement;
    const up: GlideChain = parent ? chain(parent)
      : {M: [1, 0, 0, 1], L: [1, 0, 0, 1], ls: 1, op: 1, spatial: false, will: false, steps: false, key: ''};
    const cs = win.getComputedStyle(el);
    const own = selfMatrix(cs);
    const M = up.M === null || own === null ? null : mul2(up.M, own);
    // `L` is the matrix composed BELOW the nearest blur/drop-shadow — what the glyphs are drawn under inside that
    // filter's layer — and `ls` the scale the layer keeps. An element carrying such a filter starts a new layer:
    // its own transform is above the layer, so the composition below it restarts at identity.
    const spatial = SPATIAL_FILTER.test(cs.filter || '');
    const L = spatial ? [1, 0, 0, 1] as Mat2 : (up.L === null || own === null ? null : mul2(up.L, own));
    const ls = spatial && M ? Math.sqrt(Math.abs(M[0] * M[3] - M[1] * M[2])) : up.ls;
    if (parent && !childIndex.has(el)) Array.from(parent.children).forEach((c, i) => childIndex.set(c, i));
    const info: GlideChain = {
      M, L, ls,
      op: up.op * (parseFloat(cs.opacity || '1') || 0),
      spatial: up.spatial || spatial,
      will: up.will || /transform/.test(cs.willChange || ''),
      steps: up.steps || el.hasAttribute('data-type-steps'),
      key: `${up.key}/${el.tagName.toLowerCase()}${childIndex.get(el) ?? 0}`,
    };
    memo.set(el, info);
    return info;
  };
  const lines: GlideLine[] = [];
  let u = 0, z = 0;
  root.querySelectorAll('*').forEach((el) => {
    const text = hasOwnText(el);
    if (!text || isEcho(el)) return;
    if (!visibleRect(el, frame)) return;             // hidden, fully transparent, or clipped away entirely
    const c = chain(el);
    // A 3D chain or a will-change layer is rasterised once and moved by the compositor — not this path. Measured:
    // under will-change the unlock trades the y staircase for an x jitter of 0.6px. Counted, never listed.
    if (c.M === null || c.will) { z += 1; return; }
    // SVG type outside any filter: the screen CTM is exact — it carries the viewBox's scale, which no css transform
    // states. Inside a blur/drop-shadow layer the skew that reaches the glyphs is the one composed below it.
    const ctm = c.spatial ? null : (el as unknown as {getScreenCTM?: () => DOMMatrix | null}).getScreenCTM?.();
    const b = ctm ? ctm.b : c.spatial ? (c.L === null ? null : c.L[1] * c.ls) : c.M[1];
    if (b === null) { z += 1; return; }
    if (!snapsBaseline(b)) { u += 1; return; }
    const r = inkRect(el) ?? el.getBoundingClientRect();
    const fl = (c.spatial ? 'f' : '') + (c.steps ? 's' : '');
    lines.push({k: c.key, y: Math.round(r.top * 1e4) / 1e4, o: Math.round(c.op * 100) / 100,
      t: text.length > 32 ? text.slice(0, 32) + '…' : text, ...(fl ? {fl} : {})});
  });
  return {lines, u, z};
};

/**
 * The census, mounted. INERT unless rendered — a composition mounts it only when asked (`typeGlide`).
 *
 * Every frame logs one line, `TYPE-GLIDE {"f": frame, "lines": [...], "u": n, "z": n}`, and never cancels the
 * render: unlike the other audits this is read across frames, so the caller renders a range with no picture taken
 * (scripts/glide_frames.cjs) and collects the lines from the browser log. Each frame holds its own delayRender
 * until the walk is done, so the walk sees the frame the renderer would have captured.
 */
export const TypeGlideAudit: React.FC = () => {
  const frame = useCurrentFrame();
  const ref = React.useRef<HTMLDivElement>(null);
  React.useLayoutEffect(() => {
    const handle = delayRender(`type-glide census, frame ${frame}`, {timeoutInMilliseconds: 60000});
    let released = false;
    const release = () => {
      if (!released) {
        released = true;
        continueRender(handle);
      }
    };
    (async () => {
      try {
        await (document as unknown as {fonts?: {ready: Promise<unknown>}}).fonts?.ready;
      } catch {
        /* a browser without the API still lays out; measure what it has */
      }
      // after this frame's layout AND after any effect that re-renders on mount: one frame of the event loop
      await new Promise((res) => requestAnimationFrame(() => res(null)));
      await new Promise((res) => setTimeout(res, 0));
      if (!released && ref.current) {
        const host = ref.current;
        const rec = auditGlide(host.ownerDocument.body, host.getBoundingClientRect());
        // eslint-disable-next-line no-console
        console.log(TYPE_GLIDE_TAG + JSON.stringify({f: frame, ...rec}));
      }
      release();
    })();
    return release;
  }, [frame]);
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
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
