// THE STYLE ENGINE — the film's drawing style (runtime/styleSpec.ts) applied to what every register DRAWS.
//
// WHY HERE AND NOT IN THE REGISTERS. 218 shots read the DNA's colours, but they draw their own lines: 134 write raw
// <svg>, 111 set their own stroke widths, 148 roll their own gradients, 72 their own shadows, and 19 go through
// the shared line module (measured 2026-10-31). A style taught to registers one at a time never finishes, and the
// next register misses it again. Every register ends as the same few things in the DOM — strokes, fills,
// gradients, shadows, boxes, type — so the engine restyles THOSE, after React has drawn the frame.
//
// THE PASS IS A PURE FUNCTION OF THE DOM IT FINDS. React re-renders every frame and rewrites what it manages; what
// it does not touch keeps our last write. So every property the pass writes remembers what it found and what it
// wrote, and each pass first PUTS BACK every write of ours still in place, then reads, then writes. Writing twice
// never compounds, and nothing depends on which frame came before — seeks are out of order and spread across tabs.
// Measured on 15 registers (references/style-engine-spike.md): 0 px differ twice or out of order; 0.0 px of type moved.
//
// WHAT IT NEVER TOUCHES. Type keeps its glyphs (only display type may take an outline and a face), photographs and
// video keep their pixels, a canvas is beyond the DOM. No write changes layout: a box's line is an inset `outline`,
// never a border width, so no line of type moves. Nothing is inserted into a tree React owns — a stepped gradient
// lives in the layer's own <defs>, which React renders empty and never reconciles.
//
// NULL STYLE, NOTHING MOUNTS. With no style the layer returns its children: no wrapper, no pass, the same tree.
import React, {useLayoutEffect, useRef} from 'react';
import {continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useStyle, type ResolvedStyle} from './styleSpec';
import {useDNA, shade, relLum, type DesignDNA} from './dna';
import {classify, inkFor, meanColor, steppedGradient, quantizeStops, toHex} from './styleClassify';
import {hash01, ReducedMotionContext, SceneDurationContext} from './motion';
import {buildFilter, recipeKey, wobbleSeed, type Recipe} from './styleFilters';
import {surfaceTile} from './styleSurface';
import {withoutAxes} from './styleHooks';

export {meanColor};

export type DomPassReport = {shapes: number; boxes: number; text: number; images: number; canvas: number;
  changed: number; byAxis: Record<string, number>; laidOut: boolean};

type Mem = {found: string; wrote: string};
const memory = new WeakMap<Element, Map<string, Mem>>();

const restore = (el: Element) => {
  const m = memory.get(el);
  if (!m) return;
  const st = (el as HTMLElement).style;
  for (const [prop, rec] of m) if (st.getPropertyValue(prop) === rec.wrote) st.setProperty(prop, rec.found);
  memory.delete(el);
};

/** Write one property, remembering what was there and what we wrote AS THE BROWSER KEEPS IT: it normalises a value
 *  (`rgba(88, 138, 236, 1)` reads back as `rgb(88, 138, 236)`), and a memory of the string we passed would never match
 *  again — the next pass would take our own write for the register's, and a gradient flattened while the layer was
 *  not yet laid out stayed flat when it should have stepped (measured on StyleProbe). */
const write = (el: Element, prop: string, value: string): boolean => {
  const st = (el as HTMLElement).style;
  let m = memory.get(el);
  if (!m) { m = new Map(); memory.set(el, m); }
  const now = st.getPropertyValue(prop);
  const rec = m.get(prop) ?? {found: now, wrote: now};
  m.set(prop, rec);
  st.setProperty(prop, value);
  rec.wrote = st.getPropertyValue(prop);
  return rec.wrote !== now;
};

const GRADIENTS = new Set(['linearGradient', 'radialGradient']);
const SHAPES_TAGS = new Set(['path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon']);
const NON_DRAWING = new Set(['defs', 'stop', 'filter', 'clipPath', 'mask', 'pattern', 'marker', 'symbol', 'style',
  'title', 'desc', 'metadata', 'linearGradient', 'radialGradient', 'STYLE', 'SCRIPT']);
const GRAD_ATTRS = ['x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'fx', 'fy', 'fr', 'gradientUnits', 'gradientTransform',
  'spreadMethod'];
const GROUND_FRAC = 0.9;      // a box or shape covering this much of the layer is its ground: no outline, no shadow
const DISPLAY_FRAC = 0.06;    // type at least this fraction of the short side is display type
const OUTLINE_PX = 2.5;       // an outline's weight when the spec sets `outline` but leaves `weight` as drawn

const alphaOf = (css: string): number => {
  const m = /rgba\(([^)]+)\)/.exec(css);
  return m ? parseFloat(m[1].split(',')[3]) : (css === 'transparent' || css === 'none' ? 0 : 1);
};

const urlId = (paint: string): string | null => {
  const m = /url\(["']?#([^"')]+)["']?\)/.exec(paint);
  return m ? m[1] : null;
};

/** The stops of a gradient as rgba strings, following an href chain for gradients that borrow their stops. */
const stopsOf = (g: Element, doc: Document): string[] => {
  for (let cur: Element | null = g, n = 0; cur && n < 4; n++) {
    const stops = Array.from(cur.querySelectorAll(':scope > stop'));
    if (stops.length) {
      return stops.map((s) => {
        const cs = getComputedStyle(s);
        const h = toHex(cs.stopColor) ?? '#000000';
        const a = alphaOf(cs.stopColor) * parseFloat(cs.stopOpacity || '1');
        const [r, gg, b] = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
        return `rgba(${r}, ${gg}, ${b}, ${+a.toFixed(3)})`;
      });
    }
    const href = cur.getAttribute('href') ?? cur.getAttribute('xlink:href');
    cur = href && href.startsWith('#') ? doc.getElementById(href.slice(1)) : null;
  }
  return [];
};

/** Strip some CSS filter functions from a computed `filter` value ('none' when nothing is left). */
const filterWithout = (f: string, fns: string[]): string => {
  if (!f || f === 'none') return 'none';
  const parts: string[] = f.match(/[a-z-]+\([^()]*(?:\([^()]*\)[^()]*)*\)/g) ?? [];
  const kept = parts.filter((p) => !fns.some((fn) => p.startsWith(fn + '(')));
  return kept.length ? kept.join(' ') : 'none';
};

/** The colour behind `el`: the nearest ancestor box that paints a mostly-opaque ground, else the film's ground. A
 *  line that bounds nothing is inked against THIS — the DNA's bg is not what a register drew under it. */
const groundBehind = (el: Element, stop: Element, dna: DesignDNA | null): string => {
  for (let e: Element | null = el.parentElement; e; e = e.parentElement) {
    if (e instanceof HTMLElement) {
      const cs = getComputedStyle(e);
      if (alphaOf(cs.backgroundColor) > 0.5) return cs.backgroundColor;
      if (cs.backgroundImage.includes('gradient(')) { const m = meanColor(cs.backgroundImage); if (m) return m; }
    }
    if (e === stop) break;
  }
  return dna?.bg ?? '#ffffff';
};

/** The register's frame on screen: the largest box among the layer's own children (the layer is display:contents and
 *  has none). 0 before the composition is laid out — Remotion mounts it off-screen at zero size first. */
const layerRect = (root: Element, owned: (el: Element) => boolean = () => false): DOMRect | null => {
  let best: DOMRect | null = null;
  for (const k of Array.from(root.children)) {
    if (owned(k)) continue;
    const b = k.getBoundingClientRect();
    if (!best || b.width * b.height > best.width * best.height) best = b;
  }
  return best;
};
const layerArea = (root: Element, owned: (el: Element) => boolean = () => false): number => {
  const b = layerRect(root, owned);
  return b ? b.width * b.height : 0;
};

/** TRANSLUCENT IS LIGHT. A gradient with a see-through stop is a vignette, a glow, a fade — light on the picture, not
 *  paint in it; a shape most of the way transparent is a glint or a halo. Treated as paint they went wrong three ways
 *  (looked at on the cartoon-like corpus run): a vignette flattened into a grey veil over CinematicTitle's title, and a
 *  glint (ClayStack) and a halo (KnowledgeGraph) were outlined as if they were things. Light answers to `shade`. */
const LIGHT_ALPHA = 0.6;
/** A ground dark enough that a multiplied tooth would vanish into it (relative luminance). */
const DARK_LUM = 0.18;
const isDark = (css: string): boolean => relLum(toHex(css) ?? '#ffffff') < DARK_LUM;
const translucentStops = (css: string): boolean =>
  [...css.matchAll(/rgba?\(([^)]+)\)/g)].some((m) => parseFloat(m[1].split(',')[3] ?? '1') < 0.95);

type Ctx = {spec: ResolvedStyle; dna: DesignDNA | null; scale: number; root: DOMRect; short: number; beat: string;
  defs: SVGSVGElement | null};

const lineOf = (s: ResolvedStyle) => s.line as {weight: number | 'as-drawn'; variance: number; color: string;
  outline: string; join: string; wobble: number; boil_hz: number};

/** The gradient mode in force: the fill axis when it is set, else what the shade axis implies. */
const gradientMode = (s: ResolvedStyle): {mode: 'as-drawn' | 'flat' | 'cel'; steps: number} => {
  const fill = s.fill as {mode: string; steps: number};
  const shadeMode = (s.shade as {mode: string}).mode;
  if (fill.mode === 'flat' || fill.mode === 'texture') return {mode: 'flat', steps: 1};
  if (fill.mode === 'cel') return {mode: 'cel', steps: fill.steps};
  if (shadeMode === 'none') return {mode: 'flat', steps: 1};
  if (shadeMode === 'cel' || shadeMode === 'hatch') return {mode: 'cel', steps: 2};
  return {mode: 'as-drawn', steps: 0};
};

const shadowCss = (c: Ctx, kind: 'box' | 'filter'): string | null => {
  const sh = c.spec.shadow as {mode: string; offset: number};
  if (sh.mode !== 'hard-offset' && sh.mode !== 'soft') return null;
  const o = +(sh.offset * c.scale).toFixed(2);
  const blur = sh.mode === 'soft' ? +(o * 1.5).toFixed(2) : 0;
  const base = c.dna ? toHex(c.dna.bg) ?? '#000000' : '#000000';
  const col = shade(base, 0.6);
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(col.slice(i, i + 2), 16));
  const rgba = `rgba(${r}, ${g}, ${b}, ${sh.mode === 'soft' ? 0.45 : 0.85})`;
  return kind === 'box' ? `${o}px ${o}px ${blur}px 0px ${rgba}` : `drop-shadow(${o}px ${o}px ${blur}px ${rgba})`;
};

/** The colour a line takes, given the fill it bounds (or the ground, for a line that bounds nothing). */
const lineColor = (c: Ctx, fill: string, current: string): string | null => {
  const color = lineOf(c.spec).color;
  if (color === 'as-drawn') return null;
  if (color === 'none') return 'none';
  if (color === 'ink') return inkFor(fill, c.dna);
  if (color === 'fill-dark') return shade(toHex(fill) ?? toHex(current) ?? '#808080', 0.45);
  return color;
};

/** A line's new weight. `rel` is the line's drawn weight over the drawing's heaviest: the style's weight is the MAIN
 *  line's, and a lighter line keeps its proportion to it (floored at a quarter) — set to one weight, a chart's hairline
 *  grid became as heavy as its series (ChartLive, looked at). */
const lineWeight = (c: Ctx, i: number, fallback: number | null, k = 1, rel = 1): string | null => {
  const ln = lineOf(c.spec);
  const w = typeof ln.weight === 'number' ? ln.weight : fallback;
  if (w === null) return null;
  const v = ln.variance > 0 ? 1 + ln.variance * (hash01(i * 7919 + 13) - 0.5) : 1;
  const r = Math.max(0.25, Math.min(1, rel));
  return `${+(w * c.scale * v * k * r).toFixed(3)}px`;
};

/** A colour that carries hue (a data series, an accent line) rather than neutral ink: its channels spread past 40/255. */
const chromatic = (css: string): boolean => {
  const h = toHex(css);
  if (!h) return false;
  const v = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  return Math.max(...v) - Math.min(...v) > 40;
};

/** Restyle everything under `root` for `spec`. Three phases — put back every write of ours, read the originals,
 *  write — so the result depends only on what the registers drew this frame, and style is recomputed once. */
export const applyDomPass = (root: Element, spec: ResolvedStyle, scale: number, dna: DesignDNA | null = null,
  defs: SVGSVGElement | null = null, beat = '', seed = 1): DomPassReport => {
  const rep: DomPassReport = {shapes: 0, boxes: 0, text: 0, images: 0, canvas: 0, changed: 0, byAxis: {}, laidOut: false};
  const doc = root.ownerDocument;
  const owned = (el: Element) => Boolean(defs && (el === defs || defs.contains(el)));
  const els = Array.from(root.querySelectorAll('*')).filter((el) => !owned(el));
  for (const el of els) restore(el);
  if (defs) while (defs.firstChild) defs.removeChild(defs.firstChild);
  const rr = root.getBoundingClientRect();
  const short = Math.min(rr.width, rr.height) || 1080 * scale;
  const c: Ctx = {spec, dna, scale, root: rr, short, beat, defs};
  const ln = lineOf(spec);
  const grad = gradientMode(spec);
  // how LIGHT (a translucent gradient) is drawn: as drawn unless the shade axis says otherwise
  const shadeAxis = (spec.shade as {mode: string}).mode;
  const lightMode: 'as-drawn' | 'flat' | 'cel' = shadeAxis === 'none' ? 'flat' : shadeAxis === 'cel' || shadeAxis === 'hatch' ? 'cel' : 'as-drawn';
  const shMode = (spec.shadow as {mode: string}).mode;
  const shadeMode = (spec.shade as {mode: string}).mode;
  const form = spec.form as {corner: number; simplify: number};
  const type = spec.type as {display: string; display_outline: boolean};
  const plan: [Element, string, string, string][] = [];
  const put = (el: Element, prop: string, value: string, axis: string) => plan.push([el, prop, value, axis]);
  // An element's CSS `filter` is written ONCE, at the end: what it keeps of its own (`base`, after a shadow or a glow is
  // taken out) and what the style adds to it (a drop shadow, a filter recipe), so no axis overwrites another's.
  const filterBase = new Map<Element, string>();
  const filterAdd = new Map<Element, [string, string][]>();
  const addFilter = (el: Element, f: string | null, axis: string) => {
    if (!f) return;
    const l = filterAdd.get(el) ?? [];
    l.push([f, axis]);
    filterAdd.set(el, l);
  };
  // the register's frame: its root box (the layer itself is display:contents and has none). Measured on screen, so a
  // register drawn in a scaled platform-safe frame is judged against the frame it is drawn in, not the canvas.
  const frameBox = layerRect(root, owned);
  const area = frameBox ? frameBox.width * frameBox.height : 0;
  rep.laidOut = area > 1;
  /** The frame's own furniture — a letterbox bar, a full-width band — spans the register edge to edge: no ring. */
  const furniture = (r: DOMRect) => Boolean(frameBox) &&
    (r.width >= 0.98 * frameBox!.width || r.height >= 0.98 * frameBox!.height);
  const isGround = (r: DOMRect) => r.width * r.height >= GROUND_FRAC * area;
  // WHERE THE TYPE IS. A line that crosses type keeps the weight and colour it was drawn with: the gear's spokes, drawn
  // as hairlines under its label, became 4 px ink through the word "Trigger" (looked at on GearTrain, 2026-10-31).
  const typeRects: DOMRect[] = [];
  for (const el of els) {
    if (classify(el as never, root as never, true) !== 'text') continue;
    if (el.childNodes.length && el instanceof HTMLElement) {
      for (const n of Array.from(el.childNodes)) {
        if (n.nodeType !== 3 || !(n.textContent ?? '').trim()) continue;
        const range = doc.createRange();
        range.selectNodeContents(n);
        const b = range.getBoundingClientRect();
        if (b.width > 0 && b.height > 0) typeRects.push(b);
      }
    } else {
      const b = el.getBoundingClientRect();
      if (b.width > 0 && b.height > 0) typeRects.push(b);
    }
  }
  const meets = (a: DOMRect, b: DOMRect) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  const inside = (a: DOMRect, b: DOMRect) => a.left >= b.left && a.right <= b.right && a.top >= b.top && a.bottom <= b.bottom;
  /** A line here would cross type: an unfilled stroke near any type, or a filled shape whose EDGE type straddles. */
  const crossesType = (r: DOMRect, filled: boolean) =>
    typeRects.some((t) => meets(r, t) && (!filled || !inside(t, r)));
  // the drawing's heaviest line, in screen px — the line the style's weight is the weight OF
  const screenWidth = (el: Element, sw: number) => {
    const m = (el as SVGGraphicsElement).getScreenCTM?.();
    return sw * (m ? Math.hypot(m.a, m.b) : 1);
  };
  let heaviest = 0;
  for (const el of els) {
    if (!SHAPES_TAGS.has(el.tagName)) continue;
    const cs = getComputedStyle(el);
    const sw = parseFloat(cs.strokeWidth) || 0;
    if (cs.stroke !== 'none' && sw > 0) heaviest = Math.max(heaviest, screenWidth(el, sw));
  }
  const stepped = new Map<string, string>();
  const steppedFor = (id: string): string | null => {
    if (!defs) return null;
    if (stepped.has(id)) return stepped.get(id)!;
    const g = doc.getElementById(id);
    if (!g || !GRADIENTS.has(g.tagName)) return null;
    const stops = stopsOf(g, doc);
    if (!stops.length) return null;
    const bands = quantizeStops(stops, grad.steps || 2);
    const a = +(stops.reduce((s, x) => s + alphaOf(x), 0) / stops.length).toFixed(3);
    const ns = 'http://www.w3.org/2000/svg';
    const clone = doc.createElementNS(ns, g.tagName);
    for (const k of GRAD_ATTRS) { const v = g.getAttribute(k); if (v !== null) clone.setAttribute(k, v); }
    const nid = `style-g-${beat}-${stepped.size}`;
    clone.setAttribute('id', nid);
    bands.forEach((col, k) => {
      for (const off of [k / bands.length, (k + 1) / bands.length]) {
        const s = doc.createElementNS(ns, 'stop');
        s.setAttribute('offset', String(off));
        s.setAttribute('stop-color', col);
        s.setAttribute('stop-opacity', String(a));
        clone.appendChild(s);
      }
    });
    defs.appendChild(clone);
    stepped.set(id, `url(#${nid})`);
    return stepped.get(id)!;
  };
  // a GROUND's gradient goes flat even when objects step: stepped, a frame-filling ground draws contour rings that read
  // as things in the picture (the dark radial ground behind GpsSatellite, looked at 2026-10-31)
  const paintFor = (paint: string, ground = false): string | null => {
    const id = urlId(paint);
    if (!id) return null;
    const g = doc.getElementById(id);
    if (!g || !GRADIENTS.has(g.tagName)) return null;
    const stops = stopsOf(g, doc);
    const mode = translucentStops(stops.join(' ')) ? lightMode : grad.mode;
    if (mode === 'as-drawn') return null;
    if (mode === 'flat' || ground) return meanColor(stops.join(' '));
    return steppedFor(id);
  };
  const filterIs = (f: string, prims: string[]): boolean => {
    const id = urlId(f);
    const node = id ? doc.getElementById(id) : null;
    return Boolean(node && prims.some((p) => node.querySelector(p)));
  };

  const surf = spec.surface as {kind: string; strength: number; source: string};
  const tiles = new Map<boolean, string | null>();
  // a GENERATED medium (surface.source 'generated', resolved by the render) replaces the procedural noise everywhere
  const genTile = (dark: boolean): string | null => {
    const t = spec.texture;
    return surf.kind !== 'none' && t ? staticFile(dark ? t.dark : t.light) : null;
  };
  const tileFor = (dark: boolean) => {
    if (!tiles.has(dark)) {
      const g = genTile(dark);
      tiles.set(dark, g ? `url("${g}")` : surf.kind !== 'none' ? surfaceTile(surf.kind, surf.strength, scale, dark) : null);
    }
    return tiles.get(dark)!;
  };
  const recipes = new Map<string, string>();
  /** `url(#id)` of the filter for recipe `r`, built into the layer's defs the first time it is asked for. */
  const filterFor = (r: Recipe): string | null => {
    if (!defs) return null;
    const key = recipeKey(r);
    if (!recipes.has(key)) {
      const id = `style-f-${beat}-${recipes.size}`;
      buildFilter(doc, defs, id, r, scale);
      recipes.set(key, `url(#${id})`);
    }
    return recipes.get(key)!;
  };
  const POSTERIZE = filterFor({wobble: 0, seed: 1, outer: 0, ink: '', surface: null, strength: 0, posterize: true});

  els.forEach((el, i) => {
    const tag = el.tagName;
    let inDefs = false;
    for (let e: Element | null = el; e && e !== root; e = e.parentElement) if (NON_DRAWING.has(e.tagName)) { inDefs = true; break; }
    if (inDefs) return;
    const role = classify(el as never, root as never, true);
    if (role === 'image') { rep.images++; return; }
    if (role === 'canvas') { rep.canvas++; return; }
    if (role === 'caption') return;
    const cs = getComputedStyle(el);
    const isHtml = el instanceof HTMLElement;

    if (role === 'text') {
      rep.text++;
      const px = parseFloat(cs.fontSize) || 0;
      const display = el.getAttribute('data-type-role') === 'display' || px >= DISPLAY_FRAC * short;
      if (display && type.display !== 'as-dna') put(el, 'font-family', type.display, 'type.display');
      if (display && type.display_outline) {
        const w = Math.max(1, +(px * 0.035).toFixed(2));
        put(el, '-webkit-text-stroke', `${w}px ${inkFor(cs.color, dna)}`, 'type.display_outline');
        put(el, 'paint-order', 'stroke fill', 'type.display_outline');
      }
      if (!isHtml) return;          // an HTML element with its own text can still be a box (a chip): fall through
    }

    if (role === 'shape') {
      rep.shapes++;
      const r = el.getBoundingClientRect();
      const ground = isGround(r);
      const fillPaint = cs.fill, strokePaint = cs.stroke;
      const newFill = paintFor(fillPaint, ground);
      if (newFill) put(el, 'fill', newFill, 'fill.mode');
      const newStroke = paintFor(strokePaint, ground);
      if (newStroke) put(el, 'stroke', newStroke, 'fill.mode');
      const filled = tag !== 'line' && fillPaint !== 'none' && parseFloat(cs.fillOpacity || '1') > 0;
      const sw = parseFloat(cs.strokeWidth) || 0;
      let stroked = strokePaint !== 'none' && sw > 0 && parseFloat(cs.strokeOpacity || '1') > 0;
      const solidFill = newFill && !newFill.startsWith('url(') ? newFill : (urlId(fillPaint) ? meanColor(stopsOf(doc.getElementById(urlId(fillPaint)!) ?? el, doc).join(' ')) ?? fillPaint : fillPaint);
      // simplify: a hairline that only decorates goes; a part of an object (fidelity) never does
      if (stroked && !filled && form.simplify > 0 && !el.closest('[data-part]')) {
        const m = (el as SVGGraphicsElement).getScreenCTM?.();
        const k = m ? Math.hypot(m.a, m.b) : 1;
        if (sw * k < form.simplify * 2 * scale) { put(el, 'stroke', 'none', 'form.simplify'); stroked = false; }
      }
      const keepLine = crossesType(r, filled);
      const fillAlpha = parseFloat(cs.fillOpacity || '1') * parseFloat(cs.opacity || '1') *
        (urlId(fillPaint) ? alphaOf(solidFill) : alphaOf(fillPaint));
      const light = filled && fillAlpha < LIGHT_ALPHA;
      const outlineHere = filled && !ground && !stroked && ln.outline === 'all' && !keepLine && !light;
      if (outlineHere) {
        const col = lineColor(c, solidFill, '') ?? inkFor(solidFill, dna);
        put(el, 'stroke', col, 'line.outline');
        // under the fill (paint-order), only the outer half of a stroke shows: draw it twice as wide, so the line a
        // viewer sees outside the edge is the weight the spec asked for and the fill keeps all of its area
        put(el, 'stroke-width', lineWeight(c, i, OUTLINE_PX, 2)!, 'line.outline');
        put(el, 'vector-effect', 'non-scaling-stroke', 'line.outline');
        put(el, 'paint-order', 'stroke fill', 'line.outline');
      } else if (stroked && !keepLine) {
        // a line that bounds nothing and carries hue IS content (a series, an accent): its colour stays; an outline
        // and a neutral line take the style's ink (ChartLive's green series went white)
        const hueLine = !filled && chromatic(strokePaint);
        const col = hueLine ? null : lineColor(c, filled ? solidFill : groundBehind(el, root.parentElement ?? root, dna), strokePaint);
        if (col) put(el, 'stroke', col, 'line.color');
        const w = lineWeight(c, i, null, 1, heaviest > 0 ? screenWidth(el, sw) / heaviest : 1);
        if (w) { put(el, 'stroke-width', w, 'line.weight'); put(el, 'vector-effect', 'non-scaling-stroke', 'line.weight'); }
      }
      if ((stroked || outlineHere) && ln.join !== 'as-drawn') {
        put(el, 'stroke-linejoin', ln.join, 'line.join');
        put(el, 'stroke-linecap', ln.join === 'round' ? 'round' : 'butt', 'line.join');
      }
      if (tag === 'rect' && form.corner !== 1 && !ground) {
        const rx = parseFloat(cs.getPropertyValue('rx')) || 0;
        const v = rx > 0 ? rx * form.corner : form.corner > 1 ? (form.corner - 1) * 4 * scale : 0;
        put(el, 'rx', `${+v.toFixed(2)}px`, 'form.corner');
        put(el, 'ry', `${+v.toFixed(2)}px`, 'form.corner');
      }
      const f = cs.filter;
      if (f && f !== 'none') {
        if (shMode === 'none' && (f.includes('drop-shadow(') || filterIs(f, ['feDropShadow', 'feOffset']))) {
          filterBase.set(el, urlId(f) ? 'none' : filterWithout(f, ['drop-shadow']));
        } else if (shadeMode === 'none' && (f.includes('blur(') || filterIs(f, ['feGaussianBlur']))) {
          filterBase.set(el, urlId(f) ? 'none' : filterWithout(f, ['blur']));
        } else if (shadeMode === 'cel' && (f.includes('blur(') || filterIs(f, ['feGaussianBlur']))) {
          addFilter(el, POSTERIZE, 'shade.mode');       // a soft glow, cut into a hard-edged one
        }
      }
      return;
    }

    if (tag === 'svg') {
      // a drawing standing in the frame casts the style's shadow as one silhouette (its shapes do not each cast one)
      const r = el.getBoundingClientRect();
      const sh = shadowCss(c, 'filter');
      if (sh && !isGround(r) && r.width > 0) {
        filterBase.set(el, filterWithout(cs.filter, ['drop-shadow']));
        addFilter(el, sh, 'shadow.mode');
      }
      return;
    }
    if (!isHtml) return;

    // an HTML box
    rep.boxes++;
    const r = el.getBoundingClientRect();
    const ground = isGround(r);
    const bg = cs.backgroundImage;
    let image: string | null = null;              // the box's background-image as the style leaves it (null: as drawn)
    const bgMode = bg.includes('gradient(') && translucentStops(bg) ? lightMode : grad.mode;
    if (bg.includes('gradient(') && bgMode !== 'as-drawn') {
      if (bgMode === 'flat' && ground && translucentStops(bg)) {
        image = 'none';                         // a vignette or a scrim with no light: gone, never a uniform veil
      } else if (bgMode === 'flat' || ground) {
        const mean = meanColor(bg);
        image = 'none';
        if (mean && alphaOf(cs.backgroundColor) === 0) put(el, 'background-color', mean, 'fill.mode');
      } else {
        const st = bg.split(/,(?![^(]*\))(?![^(]*\([^(]*\))/).length > 1 ? null : steppedGradient(bg, grad.steps || 2);
        if (st) image = st;
      }
    }
    // THE MEDIUM: one more background layer, painted beneath the box's own content — so the ground and the cards take
    // the paper's tooth and the type set on them does not. Only a box that paints a ground of its own: a texture on a
    // transparent wrapper would darken empty space.
    // ...and only where that ground is OPAQUE: the tooth is an opaque layer, and laid on a translucent vignette it
    // covered the whole register (CinematicTitle rendered as a grey frame)
    const gradient = bg.includes('gradient(');
    const stopsOpaque = !gradient || [...bg.matchAll(/rgba?\(([^)]+)\)/g)].every((m) => parseFloat(m[1].split(',')[3] ?? '1') >= 0.95);
    const fills = alphaOf(cs.backgroundColor) >= 0.95 ? stopsOpaque : gradient && stopsOpaque;
    const dark = isDark(alphaOf(cs.backgroundColor) > 0.5 ? cs.backgroundColor : (meanColor(bg) ?? '#ffffff'));
    const tile = tileFor(dark);
    if (tile && fills) {
      const under = image ?? bg;
      put(el, 'background-image', under && under !== 'none' ? `${tile}, ${under}` : tile, 'surface.kind');
      put(el, 'background-blend-mode', dark ? 'screen' : 'multiply', 'surface.kind');
    } else if (image !== null) {
      put(el, 'background-image', image, 'fill.mode');
    }
    if (ground || furniture(r) || r.width < 2 || r.height < 2) return;
    const bw = parseFloat(cs.borderTopWidth) || 0;
    const bordered = bw > 0 && alphaOf(cs.borderTopColor) > 0 && cs.borderTopStyle !== 'none';
    const visibleFill = alphaOf(cs.backgroundColor) * parseFloat(cs.opacity || '1') >= LIGHT_ALPHA ||
      (bg.includes('gradient(') && !translucentStops(bg));
    const fillCol = alphaOf(cs.backgroundColor) > 0.05 ? cs.backgroundColor : (meanColor(bg) ?? dna?.bg ?? '#ffffff');
    const ring = bordered || (ln.outline === 'all' && visibleFill);
    if (ring && (ln.outline === 'all' || ln.color !== 'as-drawn' || typeof ln.weight === 'number')) {
      const w = lineWeight(c, i, bordered ? bw / scale : OUTLINE_PX)!;
      const col = lineColor(c, fillCol, cs.borderTopColor) ?? (bordered ? cs.borderTopColor : inkFor(fillCol, dna));
      if (col !== 'none') {
        put(el, 'outline', `${w} solid ${col}`, 'line.outline');
        put(el, 'outline-offset', `-${w}`, 'line.outline');
      }
    }
    if (form.corner !== 1) {
      const rad = parseFloat(cs.borderTopLeftRadius) || 0;
      const v = rad > 0 ? rad * form.corner : form.corner > 1 ? (form.corner - 1) * 4 * scale : 0;
      if (v !== rad) put(el, 'border-radius', `${+v.toFixed(2)}px`, 'form.corner');
    }
    if (shMode === 'none' && cs.boxShadow !== 'none') put(el, 'box-shadow', 'none', 'shadow.mode');
    const sh = shadowCss(c, 'box');
    if (sh && visibleFill) put(el, 'box-shadow', sh, 'shadow.mode');
    if (shadeMode === 'none' && cs.filter.includes('blur(')) filterBase.set(el, filterWithout(cs.filter, ['blur']));
    else if (shadeMode === 'cel' && cs.filter.includes('blur(')) addFilter(el, POSTERIZE, 'shade.mode');
  });
  // THE DRAWING TARGETS of the per-pixel filters: the largest elements that hold no type, no photograph and no canvas
  // — a filter displaces or textures everything inside the element it is set on, so it is never set above a glyph.
  const wob = (ln as {wobble?: number}).wobble ?? 0;
  const outerW = ln.outline === 'outer' ? (typeof ln.weight === 'number' ? ln.weight : OUTLINE_PX) : 0;
  const svgSurface = surf.kind !== 'none' && surf.strength > 0 ? surf.kind : null;
  // A SHADOW falls from each drawing, not from the frame: most registers draw in ONE frame-sized <svg>, which is its
  // ground, so a shadow set on that root never fell (ClayStack in the axis gallery). It goes on the same targets.
  const dropShadow = shadowCss(c, 'filter');
  const hatching = (spec.shade as {mode: string}).mode === 'hatch';
  if (defs && (wob > 0 || outerW > 0 || svgSurface || dropShadow || hatching)) {
    const guarded = new Set<Element>();
    for (const el of els) {
      const role = classify(el as never, root as never, true);
      if (role === 'text' || role === 'image' || role === 'canvas') {
        for (let e: Element | null = el; e && e !== root; e = e.parentElement) guarded.add(e);
      }
    }
    const pad = (wob * 2 + outerW + 4) * scale;
    /** The target's own box in its own user space, padded so a displaced or ringed edge is not clipped. */
    const placed = (node: Element, r: Recipe): Recipe => {
      if (node instanceof SVGGraphicsElement && !(node instanceof SVGSVGElement)) {
        const m = node.getScreenCTM();
        const px = m ? Math.hypot(m.a, m.b) : 1;            // screen px per user unit
        const k = px > 0 ? 1 / px : 1;
        let bb: DOMRect | SVGRect;
        try { bb = node.getBBox(); } catch { bb = {x: 0, y: 0, width: 0, height: 0} as SVGRect; }
        const p = pad * k;
        return {...r, k, region: [bb.x - p, bb.y - p, bb.width + 2 * p, bb.height + 2 * p]};
      }
      const h = node as HTMLElement;
      const w = h.offsetWidth || node.getBoundingClientRect().width, ht = h.offsetHeight || node.getBoundingClientRect().height;
      return {...r, k: 1, region: [-pad, -pad, w + 2 * pad, ht + 2 * pad]};
    };
    const target = (node: Element, r: Recipe, axis: string) => addFilter(node, filterFor(placed(node, r)), axis);
    const visit = (node: Element): void => {
      if (owned(node) || NON_DRAWING.has(node.tagName)) return;
      const role = classify(node as never, root as never, true);
      if (role === 'text' || role === 'image' || role === 'canvas' || role === 'caption') return;
      const kids = Array.from(node.children);
      if (guarded.has(node)) { kids.forEach(visit); return; }
      const isSvg = node instanceof SVGElement;
      // an HTML wrapper holding SVG drawings: the drawings take the medium through their own filter, so go down to them
      if (!isSvg && svgSurface && node.querySelector('svg')) { kids.forEach(visit); return; }
      const r = node.getBoundingClientRect();
      if (r.width * r.height < 1) { kids.forEach(visit); return; }
      if (isGround(r)) {
        if (kids.length) { kids.forEach(visit); return; }
        if (isSvg && svgSurface) {         // a ground leaf: the medium only — a displaced ground opens gaps at the frame
          const own = getComputedStyle(node).fill;
          target(node, {wobble: 0, seed: 1, outer: 0, ink: '', surface: svgSurface, strength: surf.strength, posterize: false,
            dark: isDark(urlId(own) ? groundBehind(node, root.parentElement ?? root, dna) : own),
            tile: genTile(isDark(urlId(own) ? groundBehind(node, root.parentElement ?? root, dna) : own)) ?? undefined},
            'surface.kind');
        }
        return;
      }
      if (dropShadow && isSvg && !(node instanceof SVGSVGElement)) {
        const cs = getComputedStyle(node);
        const leafAlpha = SHAPES_TAGS.has(node.tagName)
          ? parseFloat(cs.fillOpacity || '1') * parseFloat(cs.opacity || '1') *
            (urlId(cs.fill) ? alphaOf(meanColor(stopsOf(doc.getElementById(urlId(cs.fill)!) ?? node, doc).join(' ')) ?? '') : alphaOf(cs.fill))
          : 1;
        if (leafAlpha >= LIGHT_ALPHA || (SHAPES_TAGS.has(node.tagName) && cs.fill === 'none')) addFilter(node, dropShadow, 'shadow.mode');
      }
      if (!(wob > 0 || outerW > 0 || svgSurface || hatching)) return;
      const behind = groundBehind(node, root.parentElement ?? root, dna);
      const ink = outerW > 0 ? (lineColor(c, behind, '') ?? inkFor(behind, dna)) : '';
      target(node, {wobble: wob, seed: wob > 0 ? seed : 1, outer: outerW, ink, surface: isSvg ? svgSurface : null,
        strength: surf.strength, posterize: false, dark: isDark(behind),
        tile: isSvg && svgSurface ? genTile(isDark(behind)) ?? undefined : undefined,
        hatch: hatching ? (lineColor(c, behind, '') ?? inkFor(behind, dna)) : undefined}, outerW > 0 ? 'line.outline' : wob > 0 ? 'line.wobble' : 'surface.kind');
    };
    for (const k of Array.from(root.children)) if (!owned(k)) visit(k);
  }
  for (const el of new Set([...filterBase.keys(), ...filterAdd.keys()])) {
    const base = filterBase.get(el) ?? getComputedStyle(el).filter;
    const adds = filterAdd.get(el) ?? [];
    const value = [base && base !== 'none' ? base : '', ...adds.map(([f]) => f)].filter(Boolean).join(' ') || 'none';
    put(el, 'filter', value, adds[0]?.[1] ?? 'shadow.mode');
  }
  for (const [el, prop, value, axis] of plan) {
    if (write(el, prop, value)) { rep.changed++; rep.byAxis[axis] = (rep.byAxis[axis] ?? 0) + 1; }
  }
  return rep;
};

/** Wraps a beat's register. With no style it is its children. */
export const StyleLayer: React.FC<{beat?: number; skip?: string[]; children: React.ReactNode}> = ({beat, skip, children}) => {
  const full = useStyle();
  const spec = React.useMemo(() => (full ? withoutAxes(full, skip) : null), [full, skip]);
  if (!spec) return <>{children}</>;
  return <StyledLayer spec={spec} beat={beat}>{children}</StyledLayer>;
};

const StyledLayer: React.FC<{spec: ResolvedStyle; beat?: number; children: React.ReactNode}> = ({spec, beat, children}) => {
  const ref = useRef<HTMLDivElement>(null);
  const defsRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const dna = useDNA();
  const {width, height, fps, durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const reduced = React.useContext(ReducedMotionContext);
  const seed = wobbleSeed(frame, sceneDur ?? durationInFrames, fps, Number((spec.line as {boil_hz?: number}).boil_hz) || 0, reduced);
  const scale = Math.min(width, height) / 1080;
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    let busy = false;
    const obs = new MutationObserver(() => run());
    const run = () => {
      if (busy) return;
      busy = true;
      obs.disconnect();
      const rep = applyDomPass(root, spec, scale, dna, defsRef.current, String(beat ?? ''), seed);
      root.setAttribute('data-style-seed', String(seed));
      root.setAttribute('data-style-pass', JSON.stringify(rep.byAxis));
      obs.takeRecords();
      obs.observe(root, {subtree: true, childList: true, attributes: true,
        attributeFilter: ['style', 'class', 'stroke-width', 'stop-color', 'fill', 'stroke', 'd', 'href']});
      busy = false;
    };
    run();
    // NOT LAID OUT YET. Remotion mounts a composition off-screen at zero size before it shows it, and showing it
    // changes no DOM under this layer, so the observer above never fires: every geometric judgement (a ground, a line
    // crossing type) would be made against empty boxes — measured: every element read as the ground and no outline
    // was drawn. Hold the frame until the register has a size, then pass again.
    let handle: number | null = null;
    let ro: ResizeObserver | null = null;
    if (layerArea(root) <= 1) {
      handle = delayRender('style engine: waiting for the register to be laid out');
      ro = new ResizeObserver(() => {
        if (layerArea(root) <= 1 || handle === null) return;
        run();
        ro?.disconnect();
        continueRender(handle);
        handle = null;
      });
      for (const k of Array.from(root.children)) ro.observe(k);
    }
    return () => {
      obs.disconnect();
      ro?.disconnect();
      if (handle !== null) continueRender(handle);
    };
  }, [frame, spec, scale, dna, beat, seed]);
  return (
    <div ref={ref} data-style-layer={beat ?? ''} style={{display: 'contents'}}>
      <svg ref={defsRef} data-style-defs="" width={0} height={0} aria-hidden
        style={{position: 'absolute', width: 0, height: 0, overflow: 'hidden'}} />
      {children}
    </div>
  );
};
