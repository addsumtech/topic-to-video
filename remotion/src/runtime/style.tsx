// THE STYLE ENGINE — the film's drawing style (runtime/styleSpec.ts) applied to what every register DRAWS.
//
// WHY HERE AND NOT IN THE REGISTERS. 218 shots read the DNA's colours, but they draw their own lines: 134 write raw
// <svg>, 111 set their own stroke widths, 148 roll their own gradients, 72 their own shadows, and 19 go through
// the shared line module (measured 2026-10-31). A style taught to registers one at a time never finishes, and the
// next register misses it again. Every register ends as the same few things in the DOM — strokes, fills,
// gradients, shadows, text — so the engine restyles THOSE, after React has drawn the frame.
//
// THE PASS IS A PURE FUNCTION OF THE DOM IT FINDS. React re-renders every frame and rewrites what it manages; what
// it does not touch keeps our last write. So every property the pass writes remembers what it found and what it
// wrote: when the element still carries our write, the original is the one remembered; when React has written
// something else since, that is the new original. Writing twice never compounds, and the result never depends on
// which frame came before — seeks are out of order and spread across tabs.
//
// NULL STYLE, NOTHING MOUNTS. With no style the layer returns its children: no wrapper, no pass, the same tree.
import React, {useLayoutEffect, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {useStyle, type ResolvedStyle} from './styleSpec';

export type DomPassReport = {shapes: number; text: number; images: number; canvas: number; changed: number};

const SHAPES = new Set(['path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon']);
const TEXTISH = new Set(['text', 'tspan', 'textPath']);

type Mem = {found: string; wrote: string};
const memory = new WeakMap<Element, Map<string, Mem>>();

/** Put back what the element had before our last write, wherever our write is still in place. React may have
 *  written since: then what is there now IS the original, and our memory of it is dropped. */
const restore = (el: Element) => {
  const m = memory.get(el);
  if (!m) return;
  const st = (el as HTMLElement).style;
  for (const [prop, rec] of m) {
    if (st.getPropertyValue(prop) === rec.wrote) st.setProperty(prop, rec.found);
  }
  memory.delete(el);
};

const write = (el: Element, prop: string, value: string): boolean => {
  const st = (el as HTMLElement).style;
  let m = memory.get(el);
  if (!m) { m = new Map(); memory.set(el, m); }
  const now = st.getPropertyValue(prop);
  m.set(prop, {found: now, wrote: value});
  if (now === value) return false;
  st.setProperty(prop, value);
  return true;
};

const RGB = /rgba?\(([^)]+)\)/g;
/** The mean of the colours in a computed colour or gradient string (Chrome serialises them as rgb()/rgba()). */
export const meanColor = (css: string): string | null => {
  const cs = [...css.matchAll(RGB)].map((m) => m[1].split(',').map((x) => parseFloat(x)));
  if (!cs.length) return null;
  const n = cs.length;
  const avg = (i: number, d: number) => cs.reduce((s, c) => s + (c[i] ?? d), 0) / n;
  const [r, g, b, a] = [avg(0, 0), avg(1, 0), avg(2, 0), avg(3, 1)];
  return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${+a.toFixed(3)})`;
};

const inText = (el: Element): boolean => {
  for (let e: Element | null = el; e; e = e.parentElement) if (TEXTISH.has(e.tagName)) return true;
  return false;
};

/** Restyle everything under `root` for `spec`. Three phases — put back every write of ours, read the originals,
 *  write — so the result depends only on what the registers drew this frame, and the style is recomputed once. */
export const applyDomPass = (root: Element, spec: ResolvedStyle, scale: number): DomPassReport => {
  const rep: DomPassReport = {shapes: 0, text: 0, images: 0, canvas: 0, changed: 0};
  const line = spec.line as Record<string, unknown>;
  const fill = spec.fill as Record<string, unknown>;
  const weight = typeof line.weight === 'number' ? (line.weight as number) * scale : null;
  const flat = fill.mode === 'flat';
  const els = Array.from(root.querySelectorAll('*'));
  for (const el of els) restore(el);
  const plan: [Element, string, string][] = [];
  for (const el of els) {
    const tag = el.tagName;
    if (tag === 'IMG' || tag === 'image' || tag === 'VIDEO') { rep.images++; continue; }
    if (tag === 'CANVAS') { rep.canvas++; continue; }
    if (TEXTISH.has(tag)) { rep.text++; continue; }
    if (!(el as HTMLElement).style) continue;
    if (SHAPES.has(tag) && !inText(el)) {
      rep.shapes++;
      if (weight !== null) {
        const cs = getComputedStyle(el);
        if (cs.stroke !== 'none' && parseFloat(cs.strokeWidth) > 0) {
          plan.push([el, 'stroke-width', `${weight}px`], [el, 'vector-effect', 'non-scaling-stroke']);
        }
      }
    }
    if (!flat) continue;
    if (tag === 'linearGradient' || tag === 'radialGradient') {
      const stops = Array.from(el.querySelectorAll('stop'));
      const mean = meanColor(stops.map((s) => getComputedStyle(s).stopColor).join(' '));
      if (mean) for (const s of stops) plan.push([s, 'stop-color', mean]);
      continue;
    }
    const bg = getComputedStyle(el).backgroundImage;
    if (bg.includes('gradient(')) {
      const mean = meanColor(bg);
      plan.push([el, 'background-image', 'none']);
      if (mean) plan.push([el, 'background-color', mean]);
    }
  }
  for (const [el, prop, value] of plan) if (write(el, prop, value)) rep.changed++;
  return rep;
};

/** Wraps a beat's register. With no style it is its children. */
export const StyleLayer: React.FC<{beat?: number; children: React.ReactNode}> = ({beat, children}) => {
  const spec = useStyle();
  if (!spec) return <>{children}</>;
  return <StyledLayer spec={spec} beat={beat}>{children}</StyledLayer>;
};

const StyledLayer: React.FC<{spec: ResolvedStyle; beat?: number; children: React.ReactNode}> = ({spec, beat, children}) => {
  const ref = useRef<HTMLDivElement>(null);
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const scale = Math.min(width, height) / 1080;
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    let busy = false;
    const run = () => {
      if (busy) return;
      busy = true;
      obs.disconnect();
      const rep = applyDomPass(root, spec, scale);
      root.setAttribute('data-style-pass', `${rep.shapes}/${rep.changed}`);
      obs.takeRecords();
      obs.observe(root, {subtree: true, childList: true, attributes: true, attributeFilter: ['style', 'class', 'stroke-width', 'stop-color', 'fill', 'stroke']});
      busy = false;
    };
    const obs = new MutationObserver(run);
    run();
    return () => obs.disconnect();
  }, [frame, spec, scale]);
  return <div ref={ref} data-style-layer={beat ?? ''} style={{display: 'contents'}}>{children}</div>;
};
