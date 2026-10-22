// HELPER · Kit — the pieces every shot of this film is drawn from, so the film reads as ONE world: the white page of
// a tokenizer viewer; a token as a tile tinted the way that viewer tints consecutive pieces (its leading space
// inside the tint); the blue caret where writing stops; a branch as thick as a chance; the hairline spray that
// stands for every other token in the vocabulary; and the title / source lines every frame places the same way.
// No words of its own: every string arrives from the calling shot's props. Pure functions of the values handed in.
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {ReducedMotionContext, clamp01, life, hash01} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx} from '../runtime/layout';
import {mix} from '../runtime/dna';
import type {DesignDNA} from '../runtime/dna';
import {usePlaceGlide} from '../runtime/glide';
import {leading} from '../runtime/cjkType';

export const MONO = 'var(--f-mono, "IBM Plex Mono", ui-monospace, monospace)';
export const DISPLAY = 'var(--f-display, "Source Serif 4", Georgia, serif)';
export const BODY = 'var(--f-body, "IBM Plex Sans", system-ui, sans-serif)';
export const MONO_ADV = 0.6;          // the token face is the DNA's monospace: every glyph is 0.6 em, so a tile is exact
export const TILE_PAD = 0.7;          // em of tint around a token's glyphs
// the tokenizer viewer's pastel cycle (the film's palette_source): a tint says "the next piece", nothing about it
export const TINTS = ['#D9CFF6', '#CDF2D4', '#FBE3BC', '#F9CDCE', '#C6EAF8'];
// @cycles: a tokenizer viewer cycles its tints by a token's POSITION so the seams between pieces show
export const tintAt = (i: number) => TINTS[((i % TINTS.length) + TINTS.length) % TINTS.length];

/** The film's palette, read from the DNA with the direction's own values as fallbacks. */
export type Ink = {bg: string; fg: string; dim: string; acc: string; acc2: string; surface: string; border: string;
  line: string; on: string};
export const inkOf = (dna: DesignDNA | null | undefined): Ink => ({
  bg: dna?.bg ?? '#FAFAF7', fg: dna?.fg ?? '#1F1F24', dim: dna?.dim ?? '#6E6E78', acc: dna?.accent ?? '#6B40D8',
  acc2: dna?.accent2 ?? '#1E9BD0', surface: dna?.surface ?? '#FFFFFF', border: dna?.surfaceBorder ?? '#E2E2E8',
  line: dna?.line ?? '#E8E8ED', on: dna?.onAccent ?? '#FFFFFF',
});

/** Frame measures every shot shares: the short side, the side margin (kept well inside action-safe), the zone. */
export const frameOf = (W: number, H: number) => {
  const U = Math.min(W, H);
  return {U, sx: W * 0.065, zTop: CONTENT_TOP, zBot: contentBottom(W, H), lw: Math.max(1, U * 0.0016),
    label: Math.max(31, Math.round(U * 0.0285)), portrait: W < H};
};

// ── tokens ──────────────────────────────────────────────────────────────────────────────────────────────────
export const tileW = (s: string, px: number) => ([...s].length * MONO_ADV + TILE_PAD) * px;
export const tileH = (px: number) => px * 1.5;
export const rowW = (tokens: string[], px: number, gap = 0) =>
  tokens.reduce((s, k) => s + tileW(k, px), 0) + gap * Math.max(0, tokens.length - 1);

/** Where each token of a running text sits when it wraps at `maxW`: token centres-lines and left edges, plus the
 *  caret's place after the last one. Lines go DOWN from `y` by `lineH`; a token never splits across lines. */
export const flow = (tokens: string[], px: number, x: number, y: number, maxW: number, lineH: number) => {
  const pos: {x: number; y: number}[] = [];
  let cx = x, cy = y;
  tokens.forEach((k) => {
    const w = tileW(k, px);
    if (cx > x && cx + w > x + maxW) { cx = x; cy += lineH; }
    pos.push({x: cx, y: cy});
    cx += w;
  });
  return {pos, end: {x: cx, y: cy}, lines: Math.round((cy - y) / Math.max(1, lineH)) + 1};
};

/** One token: a tinted tile, its text set in the mono face with its leading space kept. `y` is its centre line.
 *  `w` overrides the width for a tile whose words are not shown (a piece the film cannot spell out). */
export const Tile: React.FC<{text: string; x: number; y: number; px: number; fill: string; ink: string;
  opacity?: number; scale?: number; moving?: boolean; ring?: string; w?: number; weight?: number; dark?: boolean}> = (
  {text, x, y, px, fill, ink, opacity = 1, scale = 1, moving = false, ring, w, weight = 500, dark = false}) => {
  const place = usePlaceGlide();
  const tw = w ?? tileW(text, px), th = tileH(px);
  return (
    <div style={{position: 'absolute', ...place(moving, x, y - th / 2, scale !== 1 ? `scale(${scale})` : undefined),
      width: tw, height: th, boxSizing: 'border-box', display: 'flex', alignItems: 'center',
      padding: `0 ${(TILE_PAD / 2) * px}px`, borderRadius: Math.max(3, px * 0.16), background: fill,
      color: ink, whiteSpace: 'pre', opacity, font: `${weight} ${px}px/1 ${MONO}`, transformOrigin: 'left center',
      boxShadow: ring ? `0 0 0 ${Math.max(2, px * 0.08)}px ${ring}` : dark ? 'none' : undefined}}>{text}</div>
  );
};

/** A run of tokens at the positions `flow` gave, each appearing on its own share of `on` (0..1), tinted by
 *  position from `tint0`. */
export const TileRow: React.FC<{tokens: string[]; pos: {x: number; y: number}[]; px: number; on: number;
  tint0?: number; ink: string; opacity?: number}> = ({tokens, pos, px, on, tint0 = 0, ink, opacity = 1}) => {
  const n = Math.max(1, tokens.length);
  return (
    <>
      {tokens.map((k, i) => {
        const a = clamp01(on * n - i);
        return <Tile key={i} text={k} x={pos[i].x} y={pos[i].y} px={px} fill={tintAt(tint0 + i)} ink={ink}
          opacity={a * opacity} scale={0.9 + 0.1 * a} moving={a > 0 && a < 1} />;
      })}
    </>
  );
};

/** The caret where writing stops — blue, blinking at the screen's rate; steady under reduced motion. */
export const Caret: React.FC<{x: number; y: number; h: number; color: string; on: number; U: number}> = (
  {x, y, h, color, on, U}) => {
  const frame = useCurrentFrame();
  const reduced = React.useContext(ReducedMotionContext);
  // @positional: a caret blinks at a fixed rate of the screen; the blink carries no reading
  const blink = reduced ? 1 : Math.floor(frame / 16) % 2 === 0 ? 1 : 0.25;
  return <div style={{position: 'absolute', left: x, top: y - h / 2, width: Math.max(4, U * 0.0045), height: h,
    background: color, opacity: on * blink, borderRadius: 1}} />;
};

// ── chance ──────────────────────────────────────────────────────────────────────────────────────────────────
/** A branch from one point to the next piece: a cubic that leaves level and arrives level. */
export const branchD = (x1: number, y1: number, x2: number, y2: number) => {
  const dx = x2 - x1;
  return `M${x1},${y1} C${x1 + dx * 0.55},${y1} ${x2 - dx * 0.55},${y2} ${x2},${y2}`;
};
/** A branch's stroke: as thick as its chance (a full-width branch at 100%), never thinner than a hairline. */
export const branchW = (p: number, U: number, lw: number) => Math.max(lw * 1.3, U * 0.026 * clamp01(p / 100));

/** Every OTHER token in the vocabulary, each with a sliver of chance: a spray of hairlines from one point that keeps
 *  stirring while the slot is open (the scoring is still running). */
export const Spray: React.FC<{x: number; y: number; len: number; n: number; spread: number; ink: string; lw: number;
  grow: number; t: number; durF: number; fps: number; seed?: number; dir?: number; opacity?: number}> = (
  {x, y, len, n, spread, ink, lw, grow, t, durF, fps, seed = 0, dir = 0, opacity = 1}) => {
  const reduced = React.useContext(ReducedMotionContext);
  const lines: React.ReactNode[] = [];
  for (let k = 0; k < n; k++) {
    // @decor: a hairline's angle and length are texture — the spray stands for "every other token", never for one
    const a = dir + ((k + 0.5) / n - 0.5) * spread + (hash01(seed + k * 3) - 0.5) * (spread / n) * 0.8;
    // @decor: as above — the length is texture
    const base = len * (0.45 + 0.55 * hash01(seed + k * 3 + 1));
    const stir = reduced ? 1 : 0.72 + 0.28 * life(t, durF, fps, 3 + 2.4 * hash01(seed + k * 3 + 2), hash01(seed + k));
    const L = base * stir * grow;
    lines.push(<line key={k} x1={x} y1={y} x2={x + Math.cos(a) * L} y2={y + Math.sin(a) * L} stroke={ink}
      strokeWidth={lw * 0.7} strokeLinecap="round" opacity={(0.1 + 0.16 * (1 - Math.abs(a - dir) / spread)) * opacity} />);
  }
  return <g>{lines}</g>;
};

// ── marks (drawn, never typed — a tick or a cross is a picture, not copy) ─────────────────────────────────────
export const Tick: React.FC<{x: number; y: number; s: number; color: string; p: number; lw: number}> = (
  {x, y, s, color, p, lw}) => (
  <path d={`M${x - s * 0.5},${y} L${x - s * 0.12},${y + s * 0.38} L${x + s * 0.55},${y - s * 0.42}`} fill="none"
    stroke={color} strokeWidth={lw} strokeLinecap="round" strokeLinejoin="round" pathLength={1}
    strokeDasharray={1} strokeDashoffset={1 - clamp01(p)} />
);
export const Cross: React.FC<{x: number; y: number; s: number; color: string; p: number; lw: number}> = (
  {x, y, s, color, p, lw}) => (
  <g>
    <path d={`M${x - s / 2},${y - s / 2} L${x + s / 2},${y + s / 2}`} stroke={color} strokeWidth={lw}
      strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - clamp01(p * 2)} />
    <path d={`M${x + s / 2},${y - s / 2} L${x - s / 2},${y + s / 2}`} stroke={color} strokeWidth={lw}
      strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - clamp01(p * 2 - 1)} />
  </g>
);

// ── title and source ────────────────────────────────────────────────────────────────────────────────────────
/** Where a frame sets its title, in ninths: top/middle/bottom × left/centre/right, or none. */
export type TitleAt = 'tl' | 'tc' | 'tr' | 'ml' | 'mc' | 'mr' | 'bl' | 'bc' | 'br' | 'none';

/** The title block: a kicker in the body face over a display-serif claim, placed in its ninth. `maxW` is the measure
 *  the claim may take; it wraps to at most `lines` lines. Returns null when there is nothing to set. */
export const Title: React.FC<{title?: string; kicker?: string; at?: TitleAt; W: number; H: number; on: number;
  kOn?: number; maxW?: number; lines?: number; ink: string; dim: string; size?: number}> = (
  {title = '', kicker = '', at = 'tl', W, H, on, kOn, maxW, lines = 1, ink, dim, size}) => {
  if (at === 'none' || (!title && !kicker)) return null;
  const f = frameOf(W, H);
  const measure = maxW ?? W * 0.62;
  const base = size ?? Math.round(f.U * 0.058);
  const tPx = title ? Math.max(f.label + 6, fitTextPx(title, measure * lines * 0.94, base, {adv: 0.5, usable: 1})) : 0;
  const kPx = f.label;
  const tLines = title ? Math.max(1, Math.min(lines, Math.ceil(([...title].length * 0.5 * tPx) / (measure * 0.94)))) : 0;
  const blockH = (kicker ? kPx * 1.35 : 0) + tLines * tPx * 1.12;
  const row = at[0], col = at[1];
  const top = row === 't' ? (kicker ? TITLE_Y - kPx * 0.75 : TITLE_Y - tPx * 0.12)
    : row === 'm' ? (f.zTop + f.zBot) / 2 - blockH / 2
    : f.zBot - f.U * 0.018 - blockH;
  const align = col === 'l' ? 'left' : col === 'c' ? 'center' : 'right';
  const box: React.CSSProperties = col === 'l' ? {left: f.sx, width: measure}
    : col === 'c' ? {left: (W - measure) / 2, width: measure} : {left: W - f.sx - measure, width: measure};
  return (
    <div style={{position: 'absolute', top, ...box, textAlign: align as React.CSSProperties['textAlign']}}>
      {kicker ? <div style={{color: dim, opacity: kOn ?? on, font: `500 ${kPx}px/1.25 ${BODY}`,
        marginBottom: kPx * 0.1}}>{kicker}</div> : null}
      {title ? <div style={{color: ink, opacity: on, font: `600 ${tPx}px/${leading(title, 1.12)} ${DISPLAY}`,
        letterSpacing: '-0.01em'}}>{title}</div> : null}
    </div>
  );
};

/** Where a number or a split came from — one quiet line in a corner, above the caption band. */
export const Source: React.FC<{text?: string; at?: 'bl' | 'br' | 'tl' | 'tr'; W: number; H: number; on: number;
  ink: string}> = ({text = '', at = 'br', W, H, on, ink}) => {
  if (!text) return null;
  const f = frameOf(W, H);
  const px = f.label;
  const top = at[0] === 't' ? TITLE_Y - px * 0.2 : f.zBot - px * 1.3;
  const side: React.CSSProperties = at[1] === 'l' ? {left: f.sx} : {right: f.sx};
  return <div style={{position: 'absolute', top, ...side, color: ink, opacity: on, whiteSpace: 'nowrap',
    font: `400 ${px}px/1.2 ${BODY}`}}>{text}</div>;
};

/** A soft paper ground: the DNA's own gradient, or its flat ground. */
export const groundOf = (dna: DesignDNA | null | undefined, ink: Ink) => dna?.bgGrad ?? ink.bg;

/** Mix toward the ground — the film's one way to fade a thing back without changing its hue. */
export const fade = (c: string, ink: Ink, f: number) => mix(c, ink.bg, f);
