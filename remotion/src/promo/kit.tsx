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
export type Look = {ground: string; groundEdge: string; paper: string; ink: string; muted: string; accent: string; accentInk: string;
  display?: string};   // the statement face (a film's DNA display face); default Inter
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

/** `*…*` marks the accent span of a line (any language). Returns reveal UNITS: a Latin word, or one CJK character
 *  (a Chinese line has no spaces to split on — read word by word it would arrive as one block), each knowing whether
 *  it is accented and whether a space follows it. */
export type Unit = {text: string; accent: boolean; space: boolean};
const CJK_RE = /[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]/;
export const isCJK = (t: string) => CJK_RE.test(t);
export const parseUnits = (text: string): Unit[] => {
  const out: Unit[] = [];
  const parts = text.split(/(\*[^*]+\*)/).filter((x) => x !== '');
  for (const part of parts) {
    const accent = /^\*[^*]+\*$/.test(part);
    const body = accent ? part.slice(1, -1) : part;
    for (const tok of body.match(/\s+|[^\s]+/g) ?? []) {
      if (/^\s+$/.test(tok)) { if (out.length) out[out.length - 1].space = true; continue; }
      if (isCJK(tok)) {
        // a CJK run: one unit per character, but closing punctuation rides with the character before it
        for (const ch of Array.from(tok)) {
          if (/[，。、！？；：,.!?;:）」』”]/.test(ch) && out.length) out[out.length - 1].text += ch;
          else out.push({text: ch, accent, space: false});
        }
      } else out.push({text: tok, accent, space: false});
    }
  }
  return out;
};
/** Back-compat: whole words with their accent flag. */
export const parseWords = (text: string) => parseUnits(text).map((u) => ({text: u.text, accent: u.accent}));

/** Type scale for screen-level type: 1 at 1080 on the SHORT side, so a 9:16 card is not set at half size. */
export const typeScale = (W: number, H: number) => Math.min(W, H) / 1080;

const lum = (hex: string) => {
  const n = parseInt(hex.replace('#', '').slice(0, 6), 16);
  return (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
};
export const isDarkHex = (hex: string) => lum(hex) < 0.45;
/** #rrggbb + alpha 0..1 -> rgba() */
export const alpha = (hex: string, a: number) => {
  const n = parseInt(hex.replace('#', '').slice(0, 6), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${Math.max(0, Math.min(1, a))})`;
};

/** Deterministic pseudo-random in [0,1) from an integer (no Math.random anywhere in a render). */
export const hash01 = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

const relLum = (hex: string) => {
  const n = parseInt(hex.replace('#', '').slice(0, 6), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const x = v / 255;
    return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
export const contrast = (a: string, b: string) => {
  const [x, y] = [relLum(a), relLum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};
const mixHex = (a: string, b: string, t: number) => {
  const pa = parseInt(a.slice(1, 7), 16), pb = parseInt(b.slice(1, 7), 16);
  const ch = (sh: number) => Math.round(((pa >> sh) & 255) + (((pb >> sh) & 255) - ((pa >> sh) & 255)) * t);
  return '#' + [16, 8, 0].map((sh) => ch(sh).toString(16).padStart(2, '0')).join('');
};
const hex6 = (c: string | undefined, d: string) => (c && /^#[0-9a-fA-F]{6}$/.test(c) ? c : d);
/** A film's DNA as the promo layer's Look: paper = its ground, ink = its ink, ONE accent, and accentInk walked toward
 *  the ink until it reads at 4.5:1 on the paper (mirrors scripts/promo_film.derive_look). Absent DNA: the default. */
export const lookFromDna = (dna: {bg: string; fg: string; dim: string; accent: string; surfaceBorder?: string; fontDisplay?: string} | null): Look => {
  if (!dna) return DEFAULT_LOOK;
  const paper = hex6(dna.bg, DEFAULT_LOOK.paper), ink = hex6(dna.fg, DEFAULT_LOOK.ink), accent = hex6(dna.accent, DEFAULT_LOOK.accent);
  let accentInk = accent;
  for (let i = 0; i <= 40 && contrast(accentInk, paper) < 4.6; i++) accentInk = mixHex(accent, ink, i / 40);
  const dark = isDarkHex(paper);
  return {paper, ink, accent, accentInk, muted: hex6(dna.dim, DEFAULT_LOOK.muted),
    ground: mixHex(paper, dark ? '#000000' : '#d9d6cf', dark ? 0.25 : 0.35), groundEdge: hex6(dna.surfaceBorder, DEFAULT_LOOK.groundEdge),
    display: dna.fontDisplay};
};
