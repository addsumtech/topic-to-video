// OBJECT FIDELITY — is a built thing TRUE to the thing it depicts? (references/object-authoring.md rule 7)
//
// An object that depicts a real thing — a satellite, a gear train, an espresso puck, a watch — declares what it
// depicts in `META.fidelity`: the references it was drawn from, the proportions it took from them (each with its
// source), the parts without which it is not that thing, and the materials it shows. A workshop SHOT that draws a
// real thing inline declares the same record on its `meta.build_list` entry. scripts/fidelity.py validates the
// record (workshop.py check, validate.py) and builds the fidelity SHEET the critic judges (S16): the references
// beside the render, and a 100% crop of every declared part.
//
// THE PARTS ARE FOUND IN THE DOM, NOT GUESSED FROM PIXELS. The object marks each defining part with
// `data-part="<name>"` on the SVG group or DOM node that draws it (several nodes may share one name: two wings,
// twelve helices). `FidelityProbe` reads every marked node's box after layout — the way runtime/textSafe asks the
// DOM about type — and logs them under FIDELITY_TAG. A part the record declares and the DOM does not draw (absent,
// zero-sized, invisible) is an ERROR: the object claims a part it does not draw. A part whose box touches no other
// part's box is DETACHED — floating where the real one is attached — unless the record says `exploded: true`.
//
// This file is imported only by Root.tsx (the probe) and, for its types, by a film's workshop objects — never by
// a library register, so it is in no register's measured source hash.
import React from 'react';
import {continueRender, delayRender, useCurrentFrame, useVideoConfig, AbsoluteFill} from 'remotion';
import type {ObjectMeta} from './objectSlot';
import {ObjectsContext, resolveObject, fitAspect} from './objectSlot';
import {useDNA} from './dna';

export const FIDELITY_TAG = 'FIDELITY-PARTS ';
export const PART_ATTR = 'data-part';

export type FidelityReference = {
  kind: 'photo' | 'spec' | 'drawing' | 'asset';
  /** a URL, or a path (a film's: relative to its out_dir; the library's: relative to the skill root). A local
   *  photo carries its scripts/imagefetch.py sidecar (`<path>.json`); `asset` is the product's own file. */
  source: string;
  note?: string;
};
export type Fidelity = {
  subject: string;
  depicts: 'real' | 'abstract';
  references?: FidelityReference[];
  /** key ratios, each with the reference it came from: {span_to_body: {value: 5.3, source: '<a reference source>'}} */
  proportions?: Record<string, {value: number | string; source: string | string[]; drawn?: number | string}>;
  /** the defining parts, each marked `data-part="<name>"` where it is drawn */
  parts?: string[];
  materials?: string[];
  /** an exploded view: parts are shown apart on purpose, so the detached-part check does not apply */
  exploded?: boolean;
};
export type FidelityMeta = ObjectMeta & {fidelity: Fidelity};

type Box = {x: number; y: number; w: number; h: number};
export type PartReport = {f: number; canvas: {w: number; h: number}; object?: Box | null;
  parts: Record<string, {boxes: Box[]; leaves: Box[]; hidden: number}>};

// THE LEAVES OF A PART — the shapes that actually put ink down. A group's box is the box AROUND its children, so a
// band drawn as two straps in one <g> has a box that spans the case between them and would read as attached however
// far each strap floats. Attachment is judged on the leaves; the node's own box is kept for outlines and crops.
const SVG_LEAF = new Set(['path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'image', 'text', 'use']);
const NOT_DRAWN = 'defs, clipPath, mask, pattern, marker, symbol, linearGradient, radialGradient, filter';
const leavesOf = (el: Element): Element[] => {
  if (SVG_LEAF.has(el.tagName)) return [el];
  const all = Array.from(el.querySelectorAll('*')).filter((d) => !d.closest(NOT_DRAWN) &&
    (SVG_LEAF.has(d.tagName) || (!(d instanceof SVGElement) && d.childElementCount === 0)));
  return all.length ? all.slice(0, 400) : [el];
};

// A STROKE IS INK THE GEOMETRY BOX LEAVES OUT. getBoundingClientRect() of an SVG shape is its geometry: a horizontal
// rung, a basket's floor, a level wire is a box ZERO pixels tall however thick it is stroked, and the probe read
// every such part as "declared and not drawn" (DNAHelix's base pairs, PuckInSection's floor). A stroked shape's box
// is widened by half its stroke width as rendered; a node whose own box is flat is measured by its leaves.
type Rect = {left: number; top: number; width: number; height: number};
const inked = (el: Element, win: Window): Rect => {
  const r = el.getBoundingClientRect();
  const geo = (win as unknown as {SVGGeometryElement?: typeof SVGGeometryElement}).SVGGeometryElement;
  if (!geo || !(el instanceof geo)) return r;
  const cs = win.getComputedStyle(el);
  if (!cs.stroke || cs.stroke === 'none') return r;
  const m = (el as SVGGraphicsElement).getScreenCTM();
  const pad = ((parseFloat(cs.strokeWidth) || 0) * (m ? Math.hypot(m.a, m.b) : 1)) / 2;
  return {left: r.left - pad, top: r.top - pad, width: r.width + 2 * pad, height: r.height + 2 * pad};
};
const unionOf = (rs: Rect[]): Rect | null => {
  if (!rs.length) return null;
  const l = Math.min(...rs.map((q) => q.left)), t = Math.min(...rs.map((q) => q.top));
  const r = Math.max(...rs.map((q) => q.left + q.width)), b = Math.max(...rs.map((q) => q.top + q.height));
  return {left: l, top: t, width: r - l, height: b - t};
};

const visibleOpacity = (el: Element, win: Window): number => {
  let o = 1;
  for (let n: Element | null = el; n; n = n.parentElement) {
    const cs = win.getComputedStyle(n);
    if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
    o *= parseFloat(cs.opacity || '1');
  }
  return o;
};

/** Every `data-part` node's box, relative to the canvas, after layout; logged once per rendered frame. */
export const FidelityProbe: React.FC = () => {
  const frame = useCurrentFrame();
  const ref = React.useRef<HTMLDivElement>(null);
  React.useLayoutEffect(() => {
    const handle = delayRender(`fidelity parts, frame ${frame}`, {timeoutInMilliseconds: 30000});
    let released = false;
    const release = () => {
      if (!released) {
        released = true;
        continueRender(handle);
      }
    };
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const host = ref.current;
      if (!released && host) {
        const doc = host.ownerDocument;
        const win = doc.defaultView as Window;
        const c = host.getBoundingClientRect();
        const rel = (r: Rect): Box => ({x: r.left - c.left, y: r.top - c.top, w: r.width, h: r.height});
        const parts: PartReport['parts'] = {};
        doc.querySelectorAll(`[${PART_ATTR}]`).forEach((el) => {
          const name = (el.getAttribute(PART_ATTR) || '').trim();
          if (!name) return;
          const slot = parts[name] ?? (parts[name] = {boxes: [], leaves: [], hidden: 0});
          const leaves = leavesOf(el).filter((leaf) => visibleOpacity(leaf, win) > 0.02).map((leaf) => inked(leaf, win))
            .filter((q) => q.width > 0.5 || q.height > 0.5);
          let r: Rect = inked(el, win);
          if (!(r.width > 0.5 && r.height > 0.5)) r = unionOf(leaves) ?? r;
          if (!(r.width > 0.5 && r.height > 0.5 && visibleOpacity(el, win) > 0.02)) {
            slot.hidden += 1;
            return;
          }
          slot.boxes.push(rel(r));
          for (const q of leaves) slot.leaves.push(rel(q));
        });
        const obj = doc.querySelector('[data-fidelity-object]');
        const rec: PartReport = {f: frame, canvas: {w: c.width, h: c.height}, object: obj ? rel(obj.getBoundingClientRect()) : null,
          parts};
        // eslint-disable-next-line no-console
        console.log(FIDELITY_TAG + JSON.stringify(rec));
      }
      release();
    }));
    return release;
  }, [frame]);
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
};

/** THE HERO RENDER: one object alone, settled (t = 1, no idle), as large as the frame allows — the sheet's view of
 *  how finely it is made. `object` is {id, props}; `fill` the share of the frame its box may take. */
export const FidelityHero: React.FC<{object?: {id: string; props?: Record<string, unknown>}; fill?: number}> = (
  {object, fill = 0.9}) => {
  const objects = React.useContext(ObjectsContext);
  const entry = resolveObject(objects, object);
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const f = Number.isFinite(fill) && fill > 0.2 && fill <= 1 ? fill : 0.9;
  const box = fitAspect({x: W * (1 - f) / 2, y: H * (1 - f) / 2, w: W * f, h: H * f}, entry.meta?.aspect);
  const C = entry.C;
  return (
    <AbsoluteFill>
      <div data-fidelity-object="" style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h}}>
        <C {...(object?.props ?? {})} w={box.w} h={box.h} t={1} idle={0} dna={dna} />
      </div>
    </AbsoluteFill>
  );
};
