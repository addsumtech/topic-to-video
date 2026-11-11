// COVERAGE — one beat, several framings, cut on the voice.
//
// WHY (measured, 2026-11-10 craft study: ~/code_project/film_work/craft_study). Our films cut once per beat: a narrated
// sentence is one shot of 4-8 s, so the shot lengths are a metronome — p90/p10 of 1.6-1.9 on four films against 2.7-37
// on every published film with cuts (Apple, B&O, Nothing, Dyson, TE, Arc, Framer…), and not one shot under 1.5 s
// against 7-68% of theirs. The same films hold the subject at one scale (foreground share p90-p10 0.18-0.26 on our
// explainers, 0.45-0.68 on theirs). An editor's oldest answer to both is COVERAGE: the same moment seen wide, then
// closer on the thing being talked about, cut on the word that names it — a list read aloud becomes a burst of
// close-ups that ends on the whole.
//
// WHAT IT DRAWS. A plan of steps on the beat's clock (scripts/coverage_plan.py): `wide` (the register as composed),
// `{key}` (a close-up on the listed item the voice names — found in the DOM by its own text, as the focus lead finds
// it) or `{punch}` (a tighter crop around the composition's centre on a clause boundary). Each step is a STATIC
// framing that changes on a hard cut; nothing glides, so no type is re-positioned frame by frame (camera steps on
// unauthored beats made type tremble 0.19-0.47 px — craft-vs-skillry, 2026-11-01).
//
// WHY A FROZEN PROBE. The framing must be a pure function of the frame: Remotion renders frames out of order, in
// parallel tabs. Measured on the live register, a framing would follow every entrance as it slides in. So each step is
// measured on hidden copies of the register frozen at three frames of that step (Remotion's <Freeze>: just after the
// cut, the middle, just before it ends) — the same DOM whichever frame asks — and the result is cached per step. A
// register that moves its content inside the step is framed safely at all three (WorkBuddy's tilting window cut its
// sidebar's type at the step's start when only the end was measured). The copy is `visibility: hidden` + opacity 0 + aria-hidden,
// which every census (runtime/textSafe.tsx) already skips; it is also `data-echo` (a duplicate measured elsewhere).
//
// WHAT IT REFUSES (the framing is then `wide` — the beat renders exactly as composed):
//   * a line of type the crop would cut (it is fully in the frame or fully out of it);
//   * (the caption band stays the frame's own ground: a framed layer is masked to the content zone, soft-edged,
//     so what a close-up pushes down fades out above the caption the way it would at a frame edge);
//   * a raster drawn past its own pixels (an <img>/<canvas>/<video> limits the scale to its natural size);
//   * a gain under MIN_GAIN (a 1.08x "cut" reads as a jump, not a new framing);
//   * an item the DOM does not separate (focusLead.findContainers says null).
import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, Freeze, useCurrentFrame, useVideoConfig} from 'remotion';
import {findContainers} from './focusLead';
import {contentBottom} from './layout';

export type CoverFrame = 'wide' | {key: string} | {punch: number};
export type CoverStep = {t: number; frame: CoverFrame};
export type Rect = {x: number; y: number; w: number; h: number};
export type Framing = {s: number; tx: number; ty: number};

export const MAX_SCALE = 2.4;          // a close-up past this reads as a different picture, and DOM rasters soften
export const MIN_GAIN = 1.15;          // below this a cut is a jump: the two framings are too alike to read as two
export const ITEM_FILL = 0.62;         // a close-up gives the item this share of the content zone (its longer fit)
export const ITEM_PAD = 0.14;          // breathing room around the item, as a share of its own larger side
export const PUNCH_CORE = 0.45;        // a punch keeps the middle 45% of the composition in frame (60% left no room to push a cut label out)
export const BAND_FADE = 0.03;         // the framed layer fades out over this share of H above the caption band
export const STILL_IOU = 0.7;          // the composition's hull must overlap itself this much across a step's probes
export const JUMP_SCALE = 1.2;        // two framings this close in scale…
export const JUMP_SHIFT = 0.25;       // …and centred this close (share of the frame) are one framing, not a cut
const EDGE_TOL = 2;                    // px: a box this close to an edge counts as inside it
// A line of type a framing keeps in view sits at least this share of the frame's short side inside the zone's edges:
// a crop that keeps a label whole but presses its last glyph against the frame edge reads as cut (the fridge film's
// "在这儿沸腾吸热" touched the right edge under a punch-in, 2026-11-11). Otherwise it goes fully out.
export const TEXT_SAFE = 0.025;
const GROUND_FRAC = 0.45;              // an element covering this share of the frame is ground, not content
const BOX_MAX_FRAC = 0.3;
const REGION_MAX_FRAC = 0.35;          // an item's region past this share of the frame is the whole diagram              // a card up to this share of the frame is kept whole; a bigger panel may be cropped
export const ITEM_MAX_SCALE = 2.0;     // a close-up on ONE item: past this a small card fills the frame like a crop error

/** The step in force at second t (the last one at or before it), or null before the first. Pure. */
export const stepAt = (plan: CoverStep[], t: number): {i: number; step: CoverStep} | null => {
  let hit: {i: number; step: CoverStep} | null = null;
  plan.forEach((s, i) => { if (s.t <= t + 1e-6) hit = {i, step: s}; });
  return hit;
};

/** The frames (beat clock) a step is measured at: just after its cut, its middle and just before it ends — a register
 *  that keeps moving inside the step must be framed safely at all three; its target is read on the last. Pure. */
export const probeFrames = (plan: CoverStep[], i: number, durF: number, fps: number): number[] => {
  const end = probeFrame(plan, i, durF, fps);
  const start = Math.min(end, Math.ceil(plan[i].t * fps) + 2);
  return Array.from(new Set([start, Math.round((start + end) / 2), end]));
};

/** The frame (beat clock) a step's target is read at: just before it ends, when what it shows has entered. Pure. */
export const probeFrame = (plan: CoverStep[], i: number, durF: number, fps: number): number => {
  const end = i + 1 < plan.length ? plan[i + 1].t * fps : durF;
  const start = plan[i].t * fps;
  return Math.max(Math.ceil(start), Math.min(Math.floor(end) - 2, durF - 1));
};

const inside = (r: Rect, x0: number, y0: number, x1: number, y1: number) =>
  r.x >= x0 - EDGE_TOL && r.y >= y0 - EDGE_TOL && r.x + r.w <= x1 + EDGE_TOL && r.y + r.h <= y1 + EDGE_TOL;
const outside = (r: Rect, x0: number, y0: number, x1: number, y1: number) =>
  r.x + r.w <= x0 + EDGE_TOL || r.x >= x1 - EDGE_TOL || r.y + r.h <= y0 + EDGE_TOL || r.y >= y1 - EDGE_TOL;
const map = (r: Rect, f: Framing): Rect => ({x: r.x * f.s + f.tx, y: r.y * f.s + f.ty, w: r.w * f.s, h: r.h * f.s});

/**
 * The framing that shows `target` large in the content zone [0, W] x [0, bandTop], or null. Pure.
 *   target   the region the cut is about (an item's region, or a punch's core)
 *   see      what must be fully visible (default: target). A region too big to fit is framed by its width, and
 *            then only its label and its horizontal span must be seen.
 *   want     a punch asks for this scale; an item close-up derives its own from ITEM_FILL
 *   content  every content box (ground excluded) — kept for the punch's core and future rules
 *   texts    every line of type, none of which may be cut by the frame
 *   cap      the largest scale the rasters in view allow (their natural size over their drawn size)
 * The search tries scales on both sides of the wanted one and, for each, the translations that centre the target or
 * push a line of type the crop would cut fully out of the frame; of the framings that pass, the one closest to the
 * wanted scale with the target nearest the zone's centre wins.
 */
export const coverFraming = (o: {W: number; H: number; bandTop: number; target: Rect; see?: Rect; want?: number;
  content: Rect[]; texts: Rect[]; boxes?: Rect[]; cap?: number}): Framing | null => {
  const {W, H, bandTop, content, texts} = o;
  const pad = o.want ? 0 : Math.max(ITEM_PAD * Math.max(o.target.w, o.target.h), 0.03 * Math.min(W, H));
  const t: Rect = {x: o.target.x - pad, y: o.target.y - pad, w: o.target.w + 2 * pad, h: o.target.h + 2 * pad};
  if (!(t.w > 0 && t.h > 0)) return null;
  const see = o.see ?? o.target;
  const cap = Math.min(o.want ? MAX_SCALE : ITEM_MAX_SCALE, o.cap ?? MAX_SCALE);
  if (cap < MIN_GAIN) return null;
  let fit = Math.min((W * ITEM_FILL) / t.w, (bandTop * ITEM_FILL) / t.h);
  // a tall subject gets its gain from fitting itself, unpadded, in the zone: a close-up that crops nothing of it
  if (fit < MIN_GAIN) fit = Math.min((W * ITEM_FILL) / t.w, (bandTop * 0.96) / o.target.h);
  const s0 = Math.max(MIN_GAIN, Math.min(cap, o.want ?? fit));
  const scales: number[] = [s0];
  for (let k = 1; k < 14; k++) {
    const dn = s0 * Math.pow(0.95, k), up = s0 * Math.pow(1.05, k);
    if (dn >= MIN_GAIN) scales.push(dn);
    if (up <= cap && !o.want) scales.push(up);
    else if (up <= cap && o.want && up <= o.want * 1.25) scales.push(up);
  }
  const cx = t.x + t.w / 2, cy = t.y + t.h / 2;
  const M = TEXT_SAFE * Math.min(W, H);
  const textOk = (m: Rect) => inside(m, M, M, W - M, bandTop - M) || outside(m, 0, 0, W, bandTop);
  let best: {f: Framing; score: number} | null = null;
  for (const s of scales) {
    const clampX = (x: number) => Math.min(0, Math.max(W - s * W, x));
    // the framed layer only has to cover the content zone: the caption band beneath is drawn by the composed register
    const clampY = (y: number) => Math.min(0, Math.max(bandTop - s * H, y));
    const txs = new Set<number>([Math.round(clampX(W / 2 - s * cx))]);
    for (const r of texts.concat(o.boxes ?? [])) {
      txs.add(Math.round(clampX(W - s * r.x + 1)));            // push it out past the right edge
      txs.add(Math.round(clampX(-s * (r.x + r.w) - 1)));       // push it out past the left edge
    }
    for (const r of texts) {
      txs.add(Math.round(clampX(W - M - s * (r.x + r.w))));    // or bring it in, clear of the right edge
      txs.add(Math.round(clampX(M - s * r.x)));                // or clear of the left edge
    }
    for (const tx0 of txs) {
      const ty0 = clampY(bandTop / 2 - s * cy);
      const tys = new Set<number>([Math.round(ty0)]);
      for (const r of texts.concat(o.boxes ?? [])) {
        // or move a line the zone's top or bottom edge would cut fully out of the zone (above the frame, or into the
        // caption band, which the framed layer does not draw into — Coverage masks it to the zone)
        for (const v of [-s * (r.y + r.h) - 1, bandTop - s * r.y + 1]) if (v <= 0 && v >= bandTop - s * H) tys.add(Math.round(v));
      }
      for (const ty1 of tys) {
        const f = {s, tx: tx0, ty: ty1};
        if (!inside(map(see, f), 0, 0, W, bandTop)) continue;
        if (texts.some((r) => !textOk(map(r, f)))) {
          continue;                                            // a line of type would be cut by, or pressed against, the edge
        }
        // (a card is judged by its own size as composed: one that a close-up enlarges is still one object)
        if ((o.boxes ?? []).some((r) => { const m = map(r, f);
          return !inside(m, 0, 0, W, bandTop) && !outside(m, 0, 0, W, bandTop); })) {
          continue;                                            // a card would be cut in half
        }
        const mt = map(t, f);
        const off = Math.hypot((mt.x + mt.w / 2 - W / 2) / W, (mt.y + mt.h / 2 - bandTop / 2) / bandTop);
        const score = Math.abs(Math.log(s / s0)) * 2 + off;
        if (!best || score < best.score) best = {f: {s: Math.round(s * 1000) / 1000, tx: f.tx, ty: f.ty}, score};
      }
    }
  }
  return best ? best.f : null;
};

/** An item's REGION: its label plus its DRAWING — every non-text content box nearer to its label than to any other
 *  item's label and within reach — so "the low-pressure side" frames the cylinder, not only the words under it. A box
 *  shared by the items (it spans another label's column too, or most of the frame) belongs to none of them. Pure. */
export const itemRegion = (label: Rect, others: Rect[], content: Rect[], isText: boolean[], W: number, H: number):
  {region: Rect; drawing: Rect | null} => {
  const d = (a: Rect, r: Rect) => {
    const px = Math.max(a.x - (r.x + r.w), 0, r.x - (a.x + a.w)), py = Math.max(a.y - (r.y + r.h), 0, r.y - (a.y + a.h));
    return Math.hypot(px, py);
  };
  const xo = (a: Rect, r: Rect) => a.x < r.x + r.w && r.x < a.x + a.w;
  const reach = 0.2 * H;                       // measured on FridgeLoop: at 0.42H one label claimed the whole drawing
  let dx0 = Infinity, dy0 = Infinity, dx1 = -Infinity, dy1 = -Infinity;
  content.forEach((r0, j) => {
    // what the frame shows of it: a pipe that runs on far past the frame is drawn as a box thousands of px tall
    const x = Math.max(0, r0.x), y = Math.max(0, r0.y);
    const r = {x, y, w: Math.min(W, r0.x + r0.w) - x, h: Math.min(H, r0.y + r0.h) - y};
    if (r.w <= 0 || r.h <= 0) return;
    // a line or panel running across most of the frame is structure the items share, not part of one of them
    if (isText[j] || r.w > 0.4 * W || r.h > 0.6 * H) return;
    if (others.some((o) => xo(o, r)) && xo(label, r)) return;          // spans two items' columns: shared
    const mine = d(label, r);
    if (mine > reach || others.some((o) => d(o, r) < mine)) return;
    dx0 = Math.min(dx0, r.x); dy0 = Math.min(dy0, r.y); dx1 = Math.max(dx1, r.x + r.w); dy1 = Math.max(dy1, r.y + r.h);
  });
  let drawing: Rect | null = dx1 > dx0 ? {x: dx0, y: dy0, w: dx1 - dx0, h: dy1 - dy0} : null;
  // a "drawing" that is most of the frame is the shared diagram, not this item: take the label's own neighbourhood
  if (drawing && drawing.w * drawing.h > REGION_MAX_FRAC * W * H) {
    const gx = label.w * 0.6, gy = label.h * 0.6;
    drawing = {x: Math.max(0, label.x - gx), y: Math.max(0, label.y - gy), w: label.w + 2 * gx, h: label.h + 2 * gy};
  }
  const u = drawing ? [label, drawing] : [label];
  const x0 = Math.min(...u.map((r) => r.x)), y0 = Math.min(...u.map((r) => r.y));
  return {region: {x: x0, y: y0, w: Math.max(...u.map((r) => r.x + r.w)) - x0, h: Math.max(...u.map((r) => r.y + r.h)) - y0},
    drawing};
};

/** Intersection over union of two boxes. Pure. */
export const iou = (a: Rect, b: Rect): number => {
  const ix = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
  const iy = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
  const i = ix * iy;
  const u = a.w * a.h + b.w * b.h - i;
  return u > 0 ? i / u : 0;
};

/** Two framings too alike to cut between (a jump cut reads as the picture slipping, not as a new shot). Pure. */
export const tooAlike = (a: Framing | null, b: Framing | null, W: number, H: number): boolean => {
  const fa = a ?? {s: 1, tx: 0, ty: 0}, fb = b ?? {s: 1, tx: 0, ty: 0};
  const ratio = Math.max(fa.s, fb.s) / Math.min(fa.s, fb.s);
  if (ratio >= JUMP_SCALE) return false;
  // where the frame's centre lands in the register's own coordinates, under each framing
  const c = (f: Framing) => [(W / 2 - f.tx) / f.s, (H / 2 - f.ty) / f.s];
  const [ax, ay] = c(fa), [bx, by] = c(fb);
  return Math.hypot((ax - bx) / W, (ay - by) / H) < JUMP_SHIFT;
};

/** The punch's core: the middle PUNCH_CORE of the content's bounding box. Pure. */
export const punchCore = (content: Rect[], frac = PUNCH_CORE): Rect | null => {
  if (!content.length) return null;
  const x0 = Math.min(...content.map((r) => r.x)), y0 = Math.min(...content.map((r) => r.y));
  const x1 = Math.max(...content.map((r) => r.x + r.w)), y1 = Math.max(...content.map((r) => r.y + r.h));
  const w = (x1 - x0) * frac, h = (y1 - y0) * frac;
  return {x: (x0 + x1) / 2 - w / 2, y: (y0 + y1) / 2 - h / 2, w, h};
};

// ---- the DOM side: measure the frozen probe ----------------------------------------------------------------------

const LEAF_TAGS = new Set(['path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'image', 'img',
  'canvas', 'video', 'use']);

const hasOwnText = (el: Element) => Array.from(el.childNodes).some((n) => n.nodeType === 3 && (n.textContent ?? '').trim());

type Measured = {content: Rect[]; texts: Rect[]; boxes: Rect[]; rasters: {r: Rect; cap: number}[]; els: Element[]};

const measure = (probe: HTMLElement, W: number, H: number): Measured => {
  const win = probe.ownerDocument.defaultView!;
  const host = probe.getBoundingClientRect();
  const k = host.width / (probe.offsetWidth || W) || 1;          // an outer scale (a safe frame, a camera) undone
  const local = (b: DOMRect): Rect => ({x: (b.left - host.left) / k, y: (b.top - host.top) / k,
    w: b.width / k, h: b.height / k});
  const op = new Map<Element, number>();
  const opacity = (el: Element): number => {
    if (el === probe) return 1;
    const hit = op.get(el);
    if (hit !== undefined) return hit;
    const cs = win.getComputedStyle(el);
    const v = (cs.display === 'none' ? 0 : parseFloat(cs.opacity || '1')) * (el.parentElement ? opacity(el.parentElement) : 1);
    op.set(el, v);
    return v;
  };
  const d3 = new Map<Element, boolean>();
  const in3d = (el: Element): boolean => {
    if (el === probe || !el.parentElement) return false;
    const hit = d3.get(el);
    if (hit !== undefined) return hit;
    const cs = win.getComputedStyle(el);
    const v = /matrix3d/.test(cs.transform) || (cs.perspective && cs.perspective !== 'none')
      || cs.transformStyle === 'preserve-3d' || in3d(el.parentElement);
    d3.set(el, !!v);
    return !!v;
  };
  const out: Measured = {content: [], texts: [], boxes: [], rasters: [], els: []};
  probe.querySelectorAll('*').forEach((el) => {
    const tag = el.tagName.toLowerCase();
    // a CARD — a painted HTML box (fill, border or shadow) or an image — is one object: cut in half by a crop it reads
    // as a mistake, where a drawing cropped by the frame reads as a framing (ConnectorHub's logo card, 2026-11-10)
    if ((el instanceof HTMLElement && tag !== 'svg') || tag === 'img' || tag === 'image') {
      const bb = el.getBoundingClientRect();
      const rb = local(bb);
      if (rb.w >= 8 && rb.h >= 8 && rb.w * rb.h <= BOX_MAX_FRAC * W * H && opacity(el) >= 0.05
        && !(rb.x + rb.w <= 0 || rb.x >= W || rb.y + rb.h <= 0 || rb.y >= H)) {
        let card = tag === 'img' || tag === 'image';
        if (!card) {
          const cs = win.getComputedStyle(el);
          card = (!!cs.backgroundColor && !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor))
            || cs.backgroundImage !== 'none' || parseFloat(cs.borderTopWidth || '0') > 0.5 || cs.boxShadow !== 'none';
        }
        if (card) out.boxes.push(rb);
      }
    }
    const text = hasOwnText(el);
    const leaf = text || LEAF_TAGS.has(tag) || (el.children.length === 0 && el instanceof HTMLElement);
    if (!leaf) return;
    let b = el.getBoundingClientRect();
    if (text && !in3d(el)) {
      // (inside a 3D transform a Range's box is NOT projected — measured on WorkBuddy's tilted window, it reported
      // the layout position and a crop cut the sidebar's type — so there the element's own projected box is used)
      // a line of type is its glyphs, not its block: a full-width <div> around a short label is not a wide label
      const rg = el.ownerDocument.createRange();
      rg.selectNodeContents(el);
      const tb = rg.getBoundingClientRect();
      if (tb.width > 0 && tb.height > 0) b = tb;
    }
    const r = local(b);
    if (r.w < 1 || r.h < 1 || r.w * r.h > GROUND_FRAC * W * H) return;
    if (r.x + r.w <= 0 || r.x >= W || r.y + r.h <= 0 || r.y >= H) return;
    if (opacity(el) < 0.05) return;
    // a plain HTML leaf with no paint (an empty spacer) is not content
    if (!text && el instanceof HTMLElement && !LEAF_TAGS.has(tag)) {
      const cs = win.getComputedStyle(el);
      const paints = (cs.backgroundColor && !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor))
        || cs.backgroundImage !== 'none' || parseFloat(cs.borderTopWidth || '0') > 0 || cs.boxShadow !== 'none';
      if (!paints) return;
    }
    out.content.push(r);
    out.els.push(el);
    if (text) out.texts.push(r);
    if (tag === 'img' || tag === 'canvas' || tag === 'video' || tag === 'image') {
      const nat = tag === 'img' ? (el as HTMLImageElement).naturalWidth
        : tag === 'canvas' ? (el as HTMLCanvasElement).width
        : tag === 'video' ? (el as HTMLVideoElement).videoWidth : 0;
      // an SVG <image> or a raster whose size is unknown allows no magnification at all
      out.rasters.push({r, cap: nat > 0 ? nat / Math.max(1, r.w) : 1});
    }
  });
  return out;
};

const overlaps = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

/** The framing for one step, measured on its frozen probe; null = wide. */
export const frameStep = (probesIn: HTMLElement[], step: CoverStep, items: Record<string, string> | null,
  W: number, H: number): Framing | null => {
  lastWhy = '';
  if (step.frame === 'wide' || !probesIn.length) { lastWhy = 'wide/no probe'; return null; }
  const probe = probesIn[probesIn.length - 1];
  const m = measure(probe, W, H);
  // every line of type the step will show, wherever the register has moved it inside the step
  const earlier = probesIn.slice(0, -1).map((p) => measure(p, W, H));
  // a register that re-composes its frame inside the step IS its own camera: a static crop measured on one of its
  // compositions frames another (ExpertTeam's cards flew in large and settled small; the close-up met the fly-in)
  // (a punch is checked on the whole composition's hull; an item close-up on the item's own region, below — the frame
  // around an item may re-pose while the item holds still, as FridgeLoop's view does over its first second)
  const hull = (rs: Rect[]): Rect | null => (rs.length ? punchCore(rs, 1) : null);
  const still = (a: Rect | null, bs: (Rect | null)[], what: string): boolean => {
    const ious = bs.map((b) => (a && b ? iou(a, b) : 0));
    if (ious.some((v) => v < STILL_IOU)) {
      lastWhy = `recomposes (${what} iou ${ious.map((v) => v.toFixed(2)).join(',')})`;
      return false;
    }
    return true;
  };
  if (!('key' in step.frame) && !still(hull(m.content), earlier.map((e) => hull(e.content)), 'hull')) return null;
  const allTexts = m.texts.concat(...earlier.map((e) => e.texts));
  const allContent = m.content.concat(...earlier.map((e) => e.content));
  const allBoxes = m.boxes.concat(...earlier.map((e) => e.boxes));
  const bandTop = contentBottom(W, H);
  let target: Rect | null = null;
  let want: number | undefined;
  let see: Rect | undefined;
  if ('key' in step.frame) {
    if (!items) return null;
    const key = step.frame.key;
    const box = (els: Element[]): Rect | null => {
      const mine = m.content.filter((_, j) => els.some((e) => e === m.els[j] || e.contains(m.els[j])));
      if (!mine.length) return null;
      const x0 = Math.min(...mine.map((r) => r.x)), y0 = Math.min(...mine.map((r) => r.y));
      return {x: x0, y: y0, w: Math.max(...mine.map((r) => r.x + r.w)) - x0, h: Math.max(...mine.map((r) => r.y + r.h)) - y0};
    };
    // a register that knows what its item looks like says so: data-cover="<prop path>" on the item's drawing
    const marked = Array.from(probe.querySelectorAll(`[data-cover="${key}"]`));
    if (marked.length) target = box(marked);
    if (!target) {
      // the item's label (the DOM's container of its text, the focus lead's finder) and its region around it
      const found = findContainers(probe, items, W * H);
      if (!found?.[key]) { lastWhy = 'item not separable in the DOM'; return null; }
      const label = box([found[key]]);
      if (!label) return null;
      const others = Object.entries(found).filter(([k]) => k !== key).map(([, e]) => box([e])).filter(Boolean) as Rect[];
      const isText = m.els.map((e, j) => m.texts.includes(m.content[j]) && !found[key].contains(e));
      const {region, drawing} = itemRegion(label, others, m.content, isText, W, H);
      // the item's region on each earlier probe (an item not drawn yet there will enter where it is framed: skipped)
      const earlierRegions = probesIn.slice(0, -1).map((p, pi) => {
        const e = earlier[pi];
        const fe = findContainers(p, items, W * H);
        const el = fe?.[key];
        if (!el) return undefined;
        const mine = e.content.filter((_, j) => el === e.els[j] || el.contains(e.els[j]));
        if (!mine.length) return undefined;
        const x0 = Math.min(...mine.map((r) => r.x)), y0 = Math.min(...mine.map((r) => r.y));
        const lab = {x: x0, y: y0, w: Math.max(...mine.map((r) => r.x + r.w)) - x0, h: Math.max(...mine.map((r) => r.y + r.h)) - y0};
        const oth = Object.entries(fe!).filter(([k]) => k !== key).map(([, o]) => {
          const ms = e.content.filter((_, j) => o === e.els[j] || o.contains(e.els[j]));
          if (!ms.length) return null;
          const a0 = Math.min(...ms.map((r) => r.x)), b0 = Math.min(...ms.map((r) => r.y));
          return {x: a0, y: b0, w: Math.max(...ms.map((r) => r.x + r.w)) - a0, h: Math.max(...ms.map((r) => r.y + r.h)) - b0};
        }).filter(Boolean) as Rect[];
        const txt = e.els.map((x, j) => e.texts.includes(e.content[j]) && !el.contains(x));
        return itemRegion(lab, oth, e.content, txt, W, H).region;
      }).filter((r): r is Rect => r !== undefined);
      if (!still(region, earlierRegions, 'item')) return null;
      const cap0 = m.rasters.reduce((c, x) => (overlaps(x.r, region) ? Math.min(c, x.cap) : c), MAX_SCALE);
      const args = {W, H, bandTop: contentBottom(W, H), content: allContent, texts: allTexts, boxes: allBoxes, cap: cap0};
      // the item with its label, if that framing exists; else its drawing alone (the voice names it anyway)
      const f = coverFraming({...args, target: region}) ?? (drawing ? coverFraming({...args, target: drawing}) : null);
      if (!f) lastWhy = 'no framing passes (type/cards/zone)';
      return f;
    }
  } else {
    target = punchCore(m.content);
    want = step.frame.punch;
  }
  if (!target) return null;
  const cap = m.rasters.reduce((c, x) => (overlaps(x.r, target as Rect) ? Math.min(c, x.cap) : c), MAX_SCALE);
  const f = coverFraming({W, H, bandTop, target, see, want, content: allContent, texts: allTexts, boxes: allBoxes, cap});
  if (!f) lastWhy = 'no framing passes (type/cards/zone)';
  return f;
};

/** Why the last frameStep returned null (diagnostics: Coverage logs it once per step, visible with --log=verbose). */
export let lastWhy = '';

// one framing per (beat, step), computed once per worker: it is a pure function of the frozen probe, so the order in
// which frames are rendered cannot change it
const cache = new Map<string, Framing | null>();

export const Coverage: React.FC<{plan?: CoverStep[] | null; items?: Record<string, string> | null; beat: number;
  durF: number; children: React.ReactNode}> = ({plan, items, beat, durF, children}) => {
  if (!plan || !plan.length || plan.every((s) => s.frame === 'wide')) return <>{children}</>;
  return <CoverageOn plan={plan} items={items ?? null} beat={beat} durF={durF}>{children}</CoverageOn>;
};

const CoverageOn: React.FC<{plan: CoverStep[]; items: Record<string, string> | null; beat: number; durF: number;
  children: React.ReactNode}> = ({plan, items, beat, durF, children}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  const live = useRef<HTMLDivElement>(null);
  const zone = useRef<HTMLDivElement>(null);
  const probes = useRef<Map<string, HTMLDivElement>>(new Map());
  const at = stepAt(plan, frame / fps);
  const upto = at ? at.i : -1;
  const keyOf = (j: number) => `${beat}:${j}:${JSON.stringify(plan[j].frame)}:${probeFrame(plan, j, durF, fps)}:${W}x${H}`;
  // every framed step up to this one whose framing is not known yet in this worker: the one in force is cut against
  // the one before it, so each is measured (on its own frozen frame) — never on the live, moving register
  const framedNow = !!at && at.step.frame !== 'wide';
  const need: number[] = [];
  for (let j = 0; j <= upto; j++) if (plan[j].frame !== 'wide' && !cache.has(keyOf(j))) need.push(j);
  useLayoutEffect(() => {
    const el = live.current;
    if (!el) return;
    // THE FRAMING IN FORCE: a step's own framing, unless it was refused or is too alike to the one before it to be a
    // cut — then the picture simply stays as it was (a jump cut reads as the picture slipping)
    let eff: Framing | null = null;
    let why = 'wide';
    for (let j = 0; j <= upto; j++) {
      const st = plan[j];
      if (st.frame === 'wide') { eff = null; why = 'wide'; continue; }
      const k = keyOf(j);
      if (!cache.has(k)) {
        const prs = probeFrames(plan, j, durF, fps).map((pf) => probes.current.get(`${j}@${pf}`))
          .filter(Boolean) as HTMLDivElement[];
        cache.set(k, prs.length ? frameStep(prs, st, items, W, H) : null);
        // eslint-disable-next-line no-console
        console.log(`[coverage] beat ${beat} step ${j} ${JSON.stringify(st.frame)} -> ${JSON.stringify(cache.get(k))} ${lastWhy}`);
      }
      const raw = cache.get(k) ?? null;
      if (!raw) { why = `refused:${j}`; continue; }
      if (tooAlike(eff, raw, W, H)) { why = `alike:${j}`; continue; }
      eff = raw; why = `${j}:${raw.s}`;
    }
    el.style.transform = eff ? `translate(${eff.tx}px, ${eff.ty}px) scale(${eff.s})` : '';
    // a framed layer draws into the content zone only: the caption band stays the beat's own ground beneath it
    const z = zone.current;
    if (z) {
      const bt = contentBottom(W, H), fade = Math.round(H * BAND_FADE);
      const m = eff ? `linear-gradient(to bottom, #000 0, #000 ${bt - fade}px, transparent ${bt}px)` : '';
      z.style.webkitMaskImage = m;
      z.style.maskImage = m;
    }
    el.setAttribute('data-coverage', why);
  });
  return (
    <AbsoluteFill>
      {/* under a framed step, the register AS COMPOSED paints the caption band (its own ground there — registers keep
          the band empty), so the band is the beat's own ground whatever the register painted it. A duplicate whose
          type is measured on the live layer: data-echo + aria-hidden, which every census skips. */}
      {!framedNow ? null : (
        <AbsoluteFill data-echo="" aria-hidden
          style={{clipPath: `inset(${contentBottom(W, H) - Math.round(H * BAND_FADE)}px 0 0 0)`, pointerEvents: 'none'}}>
          {children}
        </AbsoluteFill>
      )}
      <AbsoluteFill ref={zone}>
        <AbsoluteFill ref={live} style={{transformOrigin: '0 0'}}>{children}</AbsoluteFill>
      </AbsoluteFill>
      {need.flatMap((j) => probeFrames(plan, j, durF, fps).map((pf) => {
        const id = `${j}@${pf}`;
        return (
          <AbsoluteFill key={id} ref={(n: HTMLDivElement | null) => { if (n) probes.current.set(id, n); else probes.current.delete(id); }}
            aria-hidden data-echo="" data-coverage-probe="" style={{visibility: 'hidden', opacity: 0, pointerEvents: 'none'}}>
            <Freeze frame={pf}>{children}</Freeze>
          </AbsoluteFill>
        );
      }))}
    </AbsoluteFill>
  );
};
