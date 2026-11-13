// PROMO KIT — the shared ground of the product-promo layer (references/promo-film.md).
//
// WHY (2026-11-13). Measured against video-shotcraft's showcase films, the gap was not one register: those films are
// a different KIND of film. The product is shown AS ITSELF (real 2x captures under a 2.5D camera, never a redrawn
// mock), between serif title cards that breathe, with one restrained look, shots of 1.5-6 s, flash cuts on the hard
// cuts and sound pinned to each action. This layer is our own implementation of that grammar (the peer's template,
// Apache-2.0, was studied, not copied): a film is a SHOT TABLE (data), every shot is a pure function of its frame.
import React from 'react';
import {continueRender, delayRender, cancelRender} from 'remotion';
import {EASE, type EaseName} from '../runtime/craftMotion';
import serifItalicUrl from '../../../assets/fonts/SourceSerif4-Italic-VF.ttf';

// The accent word of a title card is set in the serif's TRUE italic. The upright Source Serif 4 is loaded film-wide
// by runtime/fonts; the italic is loaded only here, so the library's measured registers do not depend on its file.
if (typeof document !== 'undefined' && !(globalThis as {__promoItalic?: boolean}).__promoItalic) {
  (globalThis as {__promoItalic?: boolean}).__promoItalic = true;
  const h = delayRender('promo serif italic', {timeoutInMilliseconds: 300000});
  const face = new FontFace('Source Serif 4', `url(${serifItalicUrl}) format('truetype')`, {weight: '200 900', style: 'italic'});
  face.load().then((f) => { document.fonts.add(f); continueRender(h); }).catch((e) => cancelRender(e));
}

export const SERIF = '"Source Serif 4", "Noto Serif SC", Georgia, serif';
export const SANS = 'Inter, "Noto Sans SC", system-ui, sans-serif';
export const MONO = '"JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace';

/** ONE look per film: a ground the product floats on, the paper of the title cards, ink, a muted ink and ONE accent
 *  (the product's own colour; `accentInk` is its darker cut for type on paper, ≥4.5:1). */
export type Look = {ground: string; groundEdge: string; paper: string; ink: string; muted: string; accent: string; accentInk: string};
export const DEFAULT_LOOK: Look = {
  ground: '#efeee9', groundEdge: '#dcdad3', paper: '#f6f5f1', ink: '#151513', muted: '#6a6862', accent: '#3a7bd5', accentInk: '#1f5bb0',
};
export const LookContext = React.createContext<Look>(DEFAULT_LOOK);
export const useLook = () => React.useContext(LookContext);

export type Box = {x: number; y: number; w: number; h: number};
export type Ease = EaseName | ((t: number) => number);
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
export const easeOf = (e: Ease | undefined, dflt: EaseName = 'smooth') =>
  typeof e === 'function' ? e : EASE[e ?? dflt] ?? EASE[dflt];

/** A keyframe track: [{f, ...numbers, ease?}] sorted by f. `value(frame, 'cx')` interpolates with the ease of the
 *  segment's END key (the move that arrives at a key is described on that key). Holds outside the first/last key. */
export type Key = {f: number; ease?: Ease} & Record<string, number | Ease | undefined>;
export const track = <K extends Key>(keys: K[], frame: number, field: string, dflt = 0): number => {
  if (!keys.length) throw new Error('promo.track: an empty keyframe list');
  for (let i = 1; i < keys.length; i++) {
    if (keys[i].f < keys[i - 1].f) throw new Error(`promo.track: keys out of order at f=${keys[i].f}`);
  }
  const num = (k: K) => {
    const v = k[field];
    return typeof v === 'number' ? v : dflt;
  };
  if (frame <= keys[0].f) return num(keys[0]);
  const last = keys[keys.length - 1];
  if (frame >= last.f) return num(last);
  let i = 1;
  while (keys[i].f < frame) i++;
  const a = keys[i - 1], b = keys[i];
  const t = clamp01((frame - a.f) / Math.max(1e-6, b.f - a.f));
  return num(a) + (num(b) - num(a)) * easeOf(b.ease)(t);
};

/** 0→1 between two frames (a named curve), the promo layer's one ramp. */
export const span = (frame: number, a: number, b: number, e: Ease = 'snappy') => easeOf(e)(clamp01((frame - a) / Math.max(1e-6, b - a)));

/** `*word*` marks the accent word(s) of a line. */
export const parseWords = (text: string) => text.split(/\s+/).filter(Boolean).map((w) => {
  const m = w.match(/^\*(.+)\*([.,!?;:]?)$/);
  return m ? {text: m[1] + m[2], accent: true} : {text: w, accent: false};
});

/** Deterministic pseudo-random in [0,1) from an integer (no Math.random anywhere in a render). */
export const hash01 = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
