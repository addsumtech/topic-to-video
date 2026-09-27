// The gestures a device beat performs — ONE implementation. Four registers used to draw their own cursor;
// CommandSummon's caret blinked 5.6 times a second on a 5-second beat because its rate was tied to the beat's
// length. Everything here runs on frames or on the schedule it is handed, never on a beat-relative rate.
import React from 'react';
import spec from './deviceSpec.json';
import {clamp01, hash01} from './motion';
import {alpha} from './device';

const CJK = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7a3]/;   // the same set as device_script._CJK, in ASCII escapes (rulings R5/R5a)

/** Latin one character per keystroke, CJK a two-glyph word per commit, or exactly the author's list.
 *  scripts/device_script.type_chunks is the same function; a parity test holds them together. */
export const typeChunks = (value: string | string[]): string[] => {
  if (Array.isArray(value)) return value.map(String).filter((s) => s.length > 0);
  const out: string[] = [];
  let run = '';
  for (const ch of Array.from(String(value ?? ''))) {
    if (CJK.test(ch)) {
      run += ch;
      if (Array.from(run).length === 2) { out.push(run); run = ''; }
    } else {
      if (run) { out.push(run); run = ''; }
      out.push(ch);
    }
  }
  if (run) out.push(run);
  return out;
};

/** How many chunks are on screen at t: each lands at the START of its share of [ta, t1]; shares follow the
 *  chunk's nominal time with a deterministic jitter. */
export const typedCount = (t: number, ta: number, t1: number, chunks: string[], seed = 1): number => {
  if (!chunks.length || t < ta) return 0;
  if (t >= t1) return chunks.length;
  const w = chunks.map((c, i) =>   // @decor: keystroke rhythm, not a reading about anything the film named
    (CJK.test(c) ? spec.minSeconds.typeCjkWord : spec.minSeconds.typeLatinKey) * (0.65 + 0.7 * hash01(seed * 131 + i)));
  const total = w.reduce((a, b) => a + b, 0);
  const u = ((t - ta) / Math.max(1e-6, t1 - ta)) * total;
  let acc = 0, n = 0;
  for (const x of w) { if (u >= acc) n += 1; acc += x; }
  return Math.min(chunks.length, n);
};

/** Solid until the last keystroke; then on/off in phases of `caretPhaseFrames` (the TermLog/TermThink
 *  standard, ~0.53 s at 30 fps). Reduced motion: solid. */
export const caretOn = (framesSinceLastKey: number | null, reduced: boolean): boolean => {
  if (reduced || framesSinceLastKey === null || framesSinceLastKey <= 0) return true;
  return Math.floor(framesSinceLastKey / spec.caretPhaseFrames) % 2 === 0;
};

/** Frames between two useT moments: `span` frames (useAnimSpan) cover (1 - ENTRY_T) of t. */
export const framesBetween = (tFrom: number, tTo: number, span: number, entryT: number): number =>
  ((tTo - tFrom) * span) / Math.max(1e-6, 1 - entryT);

/** The brand tap: an accent ring that lands, and ONE ripple that spreads and fades. u runs 0..1 over the tap. */
export const TapRipple: React.FC<{x: number; y: number; u: number; color: string; size: number}> = ({x, y, u, color, size}) => {
  if (!(u > 0 && u < 1)) return null;
  const land = clamp01(u / 0.15), fade = u > 0.7 ? 1 - (u - 0.7) / 0.3 : 1, wave = clamp01((u - 0.1) / 0.6);
  const ring = (scale: number, op: number, fill: boolean) => (
    <div style={{position: 'absolute', left: x - size / 2, top: y - size / 2, width: size, height: size,
      borderRadius: '50%', border: `${Math.max(2, Math.round(size * 0.06))}px solid ${color}`,
      background: fill ? alpha(color, 0.16) : 'transparent', opacity: op, transform: `scale(${scale})`}} />
  );
  return <>{ring(0.4 + 0.6 * land, fade, true)}{ring(1 + 1.4 * wave, (1 - wave) * 0.9 * fade, false)}</>;
};

/** A fingertip held on the glass while it moves (a drag, a scroll): one filled disc, no ripple. A ripple is a tap
 *  LANDING; frozen mid-spread for a whole drag it read as a static double ring. */
export const TouchPoint: React.FC<{x: number; y: number; color: string; size: number}> = ({x, y, color, size}) => (
  <div style={{position: 'absolute', left: x - size * 0.35, top: y - size * 0.35, width: size * 0.7, height: size * 0.7,
    borderRadius: '50%', background: alpha(color, 0.28), border: `${Math.max(2, Math.round(size * 0.05))}px solid ${color}`,
    boxShadow: `0 0 ${Math.round(size * 0.25)}px ${alpha(color, 0.35)}`}} />
);

/** A system arrow whose tip sits exactly on (x, y); `press` 0..1 shrinks it as a click lands. */
export const CursorArrow: React.FC<{x: number; y: number; size: number; press?: number}> = ({x, y, size, press = 0}) => (
  <svg viewBox="0 0 24 24" width={size} height={size} style={{position: 'absolute', left: x - size * (4 / 24),
    top: y - size * (2 / 24), overflow: 'visible', transformOrigin: `${(4 / 24) * 100}% ${(2 / 24) * 100}%`,
    transform: `scale(${1 - 0.18 * clamp01(press)})`}}>
    <path d="M4 2l16 9-7 2-3 7z" fill="#111111" stroke="#ffffff" strokeWidth={1.6} strokeLinejoin="round" />
  </svg>
);
