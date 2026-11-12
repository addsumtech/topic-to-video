// CRAFT KIT · MOTION — the timing vocabulary every built shot uses (references/craft-standard.md §Motion).
//
// WHY (2026-11-12, the video-shotcraft study): measured on 150 shots of a peer library before and after a redesign pass,
// the moves that read as "professional" peak EARLY and land slowly (median peak at 0.35 of the move, decel ratio 1.9;
// ours: 0.41 and 1.5 — near linear), and nothing sits fully still for more than a second (ours: 85 % of samples do).
// These are the helpers that make the right thing the easy thing: name the curve by what the move MEANS, stagger by a
// curve rather than by a constant, and keep a hold alive with a slow push instead of a frozen frame.
//
// Every function is a pure function of its arguments (frame-seekable, deterministic).
import {Easing} from 'remotion';

const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);

/** Curves by MEANING. Entrances decelerate (snappy / out / expo), exits accelerate (exit), a re-position is an
 *  asymmetric in-out (swift), a big move may wind up (anticip), a seat may overshoot ONCE (overshoot). Linear is for
 *  mechanical meaning only (a progress bar's fill, a clock hand), never for something arriving. */
export const EASE = {
  snappy: Easing.bezier(0.16, 1, 0.3, 1),          // strong out: arrives fast, settles long — the default entrance
  out: Easing.bezier(0.22, 1, 0.36, 1),
  expo: Easing.bezier(0.19, 1, 0.22, 1),
  smooth: Easing.bezier(0.65, 0, 0.35, 1),        // symmetric in-out: a camera move between two rests
  swift: Easing.bezier(0.55, 0, 0.1, 1),          // asymmetric in-out: leaves briskly, lands softly (re-position)
  exit: Easing.bezier(0.7, 0, 0.84, 0),           // ease-in: leaving the frame
  anticip: Easing.bezier(0.36, 0, 0.66, -0.56),   // a small wind-up before a big move
  overshoot: Easing.bezier(0.34, 1.56, 0.64, 1),  // one visible overshoot, then rest
  linear: (t: number) => t,
} as const;
export type EaseName = keyof typeof EASE;

/** 0→1 over frames [a, b] with a named (or given) curve; clamped outside. */
export const ramp = (frame: number, a: number, b: number, ease: EaseName | ((t: number) => number) = 'snappy'): number => {
  const f = typeof ease === 'function' ? ease : EASE[ease];
  return f(clamp01((frame - a) / Math.max(1e-6, b - a)));
};

/** Start frame of item i of n spread over `span` frames along a curve: 'out' = dense first then sparse,
 *  'exit' = accelerating (each lands sooner than the last), 'linear' = even. Constant-gap staggers read mechanical. */
export const stagger = (i: number, n: number, span: number, ease: EaseName | ((t: number) => number) = 'out'): number => {
  if (n <= 1) return 0;
  const f = typeof ease === 'function' ? ease : EASE[ease];
  return f(i / (n - 1)) * span;
};

/** A hold kept alive: a slow push of `amount` (0.02 = 2 %) across [from, to], eased smooth. Use it on the settled
 *  part of a beat so the frame never freezes; 1–3 % is the band (more reads as a camera move, less reads as still). */
export const holdPush = (frame: number, from: number, to: number, amount = 0.022): number =>
  1 + amount * EASE.smooth(clamp01((frame - from) / Math.max(1, to - from)));

/** Follow-through: a child reaches the parent's progress `lag` frames later (2–4 is the band). */
export const follow = (frame: number, a: number, b: number, lag = 3, ease: EaseName = 'snappy'): number =>
  ramp(frame, a + lag, b + lag, ease);

/** A TIMING TABLE written as data at the top of a shot — {name: [startFrame, endFrame]} — and read through `at`.
 *  Writing it first is the brief's rule (prep → main action → follow-through → settled hold); reading every move off it
 *  keeps the shot's rhythm in one place where a reviewer can see it. */
export type TimeTable = Record<string, readonly [number, number]>;
export const at = (tt: TimeTable, name: string, frame: number, ease: EaseName | ((t: number) => number) = 'snappy'): number => {
  const span = tt[name];
  if (!span) throw new Error(`craftMotion.at: no "${name}" in the timing table (${Object.keys(tt).join(', ')})`);
  return ramp(frame, span[0], span[1], ease);
};

/** Scale a timing table written for a nominal length to the beat's actual length, holding the ENTRANCES at their
 *  authored speed (a slow entrance is not a calmer one, it is a late one) and stretching only what comes after. */
export const fitTable = (tt: TimeTable, nominal: number, actual: number, keepUntil = 0.45): TimeTable => {
  if (actual >= nominal) {
    const out: Record<string, [number, number]> = {};
    const pivot = nominal * keepUntil, k = (actual - pivot) / Math.max(1, nominal - pivot);
    const map = (f: number) => (f <= pivot ? f : pivot + (f - pivot) * k);
    for (const [n, [a, b]] of Object.entries(tt)) out[n] = [map(a), map(b)];
    return out;
  }
  const k = actual / nominal, out: Record<string, [number, number]> = {};
  for (const [n, [a, b]] of Object.entries(tt)) out[n] = [a * k, b * k];
  return out;
};
