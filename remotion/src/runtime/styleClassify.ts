// WHAT AN ELEMENT IS, TO THE STYLE ENGINE — and the colour arithmetic the engine draws with.
//
// Pure functions over Element-shaped objects (tag, parent, attributes, text children), so node can ask them without
// a browser. The engine (runtime/style.tsx) restyles SHAPES and BOXES; it never touches type, a photograph or a
// canvas, and it leaves anything a caption or a margin echo owns to them. Those are rules of the spec
// (docs/superpowers/specs/2026-10-31-style-engine-design.md), not taste: a wobbled glyph reads worse, and a repainted
// photograph is no longer evidence.
import {readableOn, contrastOf, type DesignDNA} from './dna';

export type Role = 'text' | 'shape' | 'box' | 'image' | 'canvas' | 'echo' | 'caption';

type ElLike = {tagName: string; parentElement: ElLike | null; getAttribute(k: string): string | null;
  childNodes?: ArrayLike<{nodeType: number; textContent: string | null}>};

const SVG_TEXT = new Set(['text', 'tspan', 'textPath']);
const SHAPES = new Set(['path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon']);
const IMAGES = new Set(['IMG', 'image', 'VIDEO', 'img', 'video']);

const ownText = (el: ElLike): boolean => {
  const kids = el.childNodes;
  if (!kids) return false;
  for (let i = 0; i < kids.length; i++) {
    const k = kids[i];
    if (k.nodeType === 3 && (k.textContent ?? '').trim()) return true;
  }
  return false;
};

/** What `el` is. An element drawing its own glyphs is `text` whatever else it is; inside an SVG text run, too. */
export const classify = (el: ElLike): Role => {
  for (let e: ElLike | null = el; e; e = e.parentElement) {
    if (e.getAttribute('data-caption') !== null) return 'caption';
    if (e.getAttribute('data-echo') !== null) return 'echo';
  }
  const tag = el.tagName;
  if (IMAGES.has(tag)) return 'image';
  if (tag === 'CANVAS' || tag === 'canvas') return 'canvas';
  for (let e: ElLike | null = el; e; e = e.parentElement) if (SVG_TEXT.has(e.tagName)) return 'text';
  if (SHAPES.has(tag)) return 'shape';
  if (ownText(el)) return 'text';
  return 'box';
};

const RGB = /rgba?\(([^)]+)\)/g;
const HEX = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

/** '#rrggbb' for a hex or an rgb()/rgba() string (alpha dropped); null for anything else. */
export const toHex = (css: string): string | null => {
  const s = css.trim();
  const h = HEX.exec(s);
  if (h) return h[1].length === 3 ? '#' + h[1].split('').map((c) => c + c).join('') : '#' + h[1].toLowerCase();
  const m = /^rgba?\(([^)]+)\)$/.exec(s);
  if (!m) return null;
  const [r, g, b] = m[1].split(',').map((x) => Math.max(0, Math.min(255, Math.round(parseFloat(x)))));
  if ([r, g, b].some((v) => !Number.isFinite(v))) return null;
  return '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('');
};

/** The mean of the colours in a computed colour or gradient string (Chrome serialises them as rgb()/rgba()). */
export const meanColor = (css: string): string | null => {
  const cs = [...css.matchAll(RGB)].map((m) => m[1].split(',').map((x) => parseFloat(x)));
  if (!cs.length) return null;
  const n = cs.length;
  const avg = (i: number, d: number) => cs.reduce((s, c) => s + (c[i] ?? d), 0) / n;
  const [r, g, b, a] = [avg(0, 0), avg(1, 0), avg(2, 0), avg(3, 1)];
  return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${+a.toFixed(3)})`;
};

/** The outline ink for a shape filled with `fill`: whichever of the film's own fg/bg contrasts more with it, and
 *  black or white when neither reaches 3:1 — an outline that cannot be seen is no outline. */
export const inkFor = (fill: string, dna: DesignDNA | null): string => {
  const f = toHex(fill) ?? '#808080';
  const own = dna ? [toHex(dna.fg), toHex(dna.bg)].filter((c): c is string => Boolean(c)) : [];
  const pick = own.length ? readableOn(f, ...own) : readableOn(f, '#111111', '#ffffff');
  return contrastOf(pick, f) >= 3 ? pick : readableOn(f, '#000000', '#ffffff');
};

const lerp = (a: number[], b: number[], t: number) => a.map((v, i) => v + (b[i] - v) * t);
const parse = (c: string): number[] | null => {
  const h = toHex(c);
  return h ? [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)) : null;
};

/** `steps` flat colours standing for a gradient through `colors` (evenly spaced): each band's colour is the gradient
 *  sampled at the band's centre. */
export const quantizeStops = (colors: string[], steps: number): string[] => {
  const cs = colors.map(parse).filter((c): c is number[] => c !== null);
  if (!cs.length) return [];
  const out: string[] = [];
  for (let k = 0; k < steps; k++) {
    const t = (k + 0.5) / steps * (cs.length - 1);
    const i = Math.min(cs.length - 2, Math.floor(t));
    const c = cs.length === 1 ? cs[0] : lerp(cs[i], cs[i + 1], t - i);
    out.push('#' + c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join(''));
  }
  return out;
};

/** A computed CSS gradient redrawn as `steps` hard bands of its own colours, its shape and direction kept; null when
 *  `css` is not a gradient. Alpha is carried as the mean alpha of the stops, so a glow stays as faint as it was. */
export const steppedGradient = (css: string, steps: number): string | null => {
  const m = /^(repeating-)?(linear|radial|conic)-gradient\((.*)\)$/s.exec(css.trim());
  if (!m) return null;
  const body = m[3];
  const first = body.search(/rgba?\(/);
  if (first < 0) return null;
  const head = body.slice(0, first).trim().replace(/,\s*$/, '');
  const stops = [...body.matchAll(RGB)].map((x) => x[0]);
  const alphas = [...body.matchAll(RGB)].map((x) => parseFloat(x[1].split(',')[3] ?? '1'));
  const a = +(alphas.reduce((s, v) => s + v, 0) / alphas.length).toFixed(3);
  const bands = quantizeStops(stops, steps);
  const parts = bands.map((c, k) => {
    const [r, g, b] = parse(c) as number[];
    const col = a < 1 ? `rgba(${r}, ${g}, ${b}, ${a})` : `rgb(${r}, ${g}, ${b})`;
    const p0 = +(k / steps * 100).toFixed(2), p1 = +((k + 1) / steps * 100).toFixed(2);
    return `${col} ${p0}% ${p1}%`;
  });
  return `${m[1] ?? ''}${m[2]}-gradient(${head ? head + ', ' : ''}${parts.join(', ')})`;
};
