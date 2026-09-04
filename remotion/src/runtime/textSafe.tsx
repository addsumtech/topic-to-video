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
    if (node !== el && (cs.overflowX !== 'visible' || cs.overflowY !== 'visible')) {
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

/** Every text element whose VISIBLE box crosses the canvas edge, with no ancestor claiming the clip. */
export const auditTextSafety = (root: Element, frame: DOMRect): Violation[] => {
  const win = root.ownerDocument?.defaultView;
  if (!win) return [];
  const out: Violation[] = [];
  root.querySelectorAll('*').forEach((el) => {
    const text = hasOwnText(el);
    if (!text) return;
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
export const TextSafeAudit: React.FC<{enabled?: boolean}> = ({enabled = false}) => {
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
      const viol = auditTextSafety(host.ownerDocument.body, host.getBoundingClientRect());
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
  }, [enabled, handle]);

  if (!enabled) return null;
  // Its own box IS the canvas rect — measured rather than assumed, so the audit is correct at any aspect
  // and under any render scale.
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
};

export default TextSafeAudit;
