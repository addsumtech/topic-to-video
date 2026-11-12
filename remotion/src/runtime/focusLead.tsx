// FOCUS LEAD — the listed item the voice is talking about leads the frame; its peers recede until the voice moves on.
//
// WHY. craft_qa measured our beats letting several equal elements share the frame: the largest element held 48% of the
// layout against 63% on 28 published launch films, 3 elements against 2, and 116 of 311 beats had no element leading
// at all. Most were lists — callouts, steps, rows, parts — drawn at one weight for the whole beat while the voice
// talked about one item at a time. scripts/focus_plan.py reads WHICH item from the narration; this draws it.
//
// HOW, WITHOUT TOUCHING A REGISTER. Each item is found in the beat's DOM by its own text (the same text the plan
// matched to the voice), and its CONTAINER is the outermost ancestor that holds this item's text and no other item's:
// the card, the row, the label with its leader line — whatever the register drew the item as. A receding container's
// opacity is MULTIPLIED, never replaced: each frame restores what this layer wrote, reads the register's own value (an
// entrance fading in, a row not yet dealt) and writes that value times the recede. So an item still entering enters,
// and a beat with no plan, or a frame where the items cannot be told apart, is drawn exactly as before.
//
// WHAT IT REFUSES. Nothing is dimmed when an item's text is not found, when two items resolve to one container or one
// holds another (the DOM does not separate them), or when a container would cover half the frame (that is the ground
// or the whole figure, not a peer). Opacity only: the style engine writes `filter` on the same elements, and two
// layers each restoring their own `filter` would read each other's writes as the register's.
import React, {useContext, useLayoutEffect, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {PictureLeadContext} from './motion';

export type FocusStep = {t: number; key: string | null};

export const FOCUS_RECEDE = 0.45;      // a receding peer keeps this share of its own opacity: at 0.32 the fridge film's critic could not read the dimmed labels (S4)
// A hand-over is LINEAR over FOCUS_EASE_S: 0.55 of opacity over 7.5 frames is a 0.073 step every frame. Eased, its two
// ends crawled by under 0.06 a frame, and jitter_qa — which judges a line only while its opacity steps less than 0.06,
// because a fade defeats its estimator — read 0.15-0.17 px of "tremble" on TrainSlab's composited rows during the
// hand-overs (nothing in this layer moves a glyph: it writes opacity only). Linear, the whole fade is a fade. Raising
// FOCUS_RECEDE shortens the step, so the two are held together (tests/test_focus_plan.py): 0.3 s at 0.45 was 0.061.
export const FOCUS_EASE_S = 0.25;
const MAX_CONTAINER_FRAC = 0.5;

const norm = (s: string) => s.replace(/[\s*＊]/g, '');

/** {key: weight 0..1} at second t: 1 = full, 0 = fully receded. Every key is 1 when nobody leads. Pure. */
export const focusWeights = (plan: FocusStep[], keys: string[], t: number): Record<string, number> => {
  const at = (lead: string | null) => Object.fromEntries(keys.map((k) => [k, lead === null || k === lead ? 1 : 0]));
  let prev: Record<string, number> = at(null);
  let cur = prev;
  let since = -Infinity;
  for (const s of plan) {
    if (s.t > t) break;
    const p = Math.min(1, (s.t - since) / FOCUS_EASE_S);
    prev = Object.fromEntries(keys.map((k) => [k, prev[k] + (cur[k] - prev[k]) * ease(p)]));
    cur = at(s.key);
    since = s.t;
  }
  const p = Math.min(1, (t - since) / FOCUS_EASE_S);
  return Object.fromEntries(keys.map((k) => [k, prev[k] + (cur[k] - prev[k]) * ease(p)]));
};

const ease = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x);

const own = new WeakMap<HTMLElement, {found: string; wrote: string}>();

const restore = (el: HTMLElement) => {
  const m = own.get(el);
  if (m && el.style.opacity === m.wrote) el.style.opacity = m.found;
  own.delete(el);
};

const multiply = (el: HTMLElement, k: number) => {
  const found = el.style.opacity;
  const base = found === '' ? 1 : Number(found);
  el.style.opacity = String(Math.round(base * k * 10000) / 10000);
  own.set(el, {found, wrote: el.style.opacity});
};

/** The container of each item, or null when the DOM does not separate them (then nothing is dimmed). */
export const findContainers = (root: HTMLElement, items: Record<string, string>, frameArea: number):
  Record<string, HTMLElement> | null => {
  const keys = Object.keys(items);
  const texts = keys.map((k) => norm(items[k]));
  if (texts.some((t) => !t)) return null;
  const all = Array.from(root.querySelectorAll<HTMLElement>('*')).filter((e) => !(e instanceof SVGElement)
    || e.tagName.toLowerCase() === 'text' || e.tagName.toLowerCase() === 'g');
  const out: Record<string, HTMLElement> = {};
  for (let i = 0; i < keys.length; i++) {
    const mine = texts[i];
    // the DEEPEST element holding this item's text
    let leaf: HTMLElement | null = null;
    for (const e of all) {
      if (!norm(e.textContent ?? '').includes(mine)) continue;
      if (!leaf || leaf.contains(e)) leaf = e;
    }
    if (!leaf) return null;
    const others = texts.filter((_, j) => j !== i);
    const holdsOther = (e: HTMLElement) => {
      const tc = norm(e.textContent ?? '');
      return others.some((o) => tc.includes(o));
    };
    if (holdsOther(leaf)) return null;              // the item's own text also contains a peer's: not separable
    let c = leaf;
    while (c.parentElement && c.parentElement !== root && !holdsOther(c.parentElement)) c = c.parentElement;
    const r = c.getBoundingClientRect();
    if (r.width * r.height > MAX_CONTAINER_FRAC * frameArea) return null;
    out[keys[i]] = c;
  }
  const cs = Object.values(out);
  for (let i = 0; i < cs.length; i++) for (let j = 0; j < cs.length; j++) {
    if (i !== j && (cs[i] === cs[j] || cs[i].contains(cs[j]))) return null;
  }
  return out;
};

export const FocusLayer: React.FC<{plan?: FocusStep[] | null; items?: Record<string, string> | null;
  children: React.ReactNode}> = ({plan, items, children}) => {
  if (!plan || !plan.length || !items || Object.keys(items).length < 2) return <>{children}</>;
  return <FocusLayerOn plan={plan} items={items}>{children}</FocusLayerOn>;
};

const FocusLayerOn: React.FC<{plan: FocusStep[]; items: Record<string, string>; children: React.ReactNode}> =
  ({plan, items, children}) => {
  const ref = useRef<HTMLDivElement>(null);
  // the plan is on the voice's clock; under a carried cut the picture's runs ahead (runtime/motion PictureLeadContext)
  const frame = useCurrentFrame() - useContext(PictureLeadContext);
  const {fps, width, height} = useVideoConfig();
  const touched = useRef<HTMLElement[]>([]);
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    for (const el of touched.current) restore(el);
    touched.current = [];
    const keys = Object.keys(items);
    const w = focusWeights(plan, keys, frame / fps);
    if (keys.every((k) => w[k] >= 0.999)) { root.setAttribute('data-focus-lead', ''); return; }
    const found = findContainers(root, items, width * height);
    if (!found) { root.setAttribute('data-focus-lead', 'unseparated'); return; }
    for (const k of keys) {
      const k01 = FOCUS_RECEDE + (1 - FOCUS_RECEDE) * w[k];
      if (k01 < 0.999) { multiply(found[k], k01); touched.current.push(found[k]); }
    }
    root.setAttribute('data-focus-lead', keys.filter((k) => w[k] > 0.5).join(','));
  });
  return <div ref={ref} data-focus-layer="" style={{display: 'contents'}}>{children}</div>;
};
