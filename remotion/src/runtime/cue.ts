// PER-ELEMENT CUES — an item a register lists (a callout, a step, a question, a caption) arrives when the voice
// names it, even when the register's own order and the narration's disagree.
//
// THE GAP THIS CLOSES. A register times its entrances as fixed fractions of its beat (`seg(t, 0.60 + i * step,
// ...)`), and Film.tsx's BeatClock can only WARP that clock: one monotone map per beat, its slope held to
// 0.4-2.5x. A warp cannot REORDER. When the voice names a caption first and the register shows it last, or names
// five callouts across the whole beat while the register deals them in its last fifth, the later-said item cannot
// be pulled earlier without breaking monotonicity or the slope bound — measured on five delivered films, ten text
// elements stayed more than 1.5 s late after the warp (worst +5.0 s), every one of them an item in a list or a
// caption shown after the things it introduces.
//
// THE MECHANISM. render_remotion matches each text item in a beat's props to the narration (scripts/sync_qa.py
// `item_cues`, the same matching the sync audit uses) and hands the beat `cues`: {prop path: the film second by
// which it should READ}. Film provides them here. A register that ADOPTS the hook asks for each item's start:
//
//     const cue = useCues();
//     const [a, b] = cue.win('labels.' + i, 0.60 + i * step, 0.72 + i * step, REACH_CUBIC);
//     const on = easeOutCubic(clamp01(seg(t, a, b)));
//
// `win` returns the register's own window, or the same window moved EARLIER that makes the item readable at its word — never a
// later one, so an item the voice names late keeps the register's composition. A register that does not import
// this file is untouched, and so is any render with no cues (a library sweep, a still, a standalone shot): every
// `win` then returns the register's own [a, b] — the very numbers, not a recomputed sum — and the frame is identical
// to one drawn before this file existed.
//
// THE CUE IS IN FILM TIME, AND THE WARP IS UNDONE FOR IT. A cue says "readable at film second s". The register
// sees its WARPED clock (BeatClock hands it warpFrame(frame)), so `win` converts s through the same warp before
// comparing: an item on its cue stays on its word whatever warp the rest of the beat is given, and the warp
// derivation (sync_qa.derive_warp) treats it as fixed.
//
// PATHS. A key is the prop's path: `caption`, `note`, `questions.1`, `labels.0`, `parts.3`. For a list of objects the
// item's text is its `text`/`label`/`title`/`name`/`caption` field; sync_qa.item_texts is the one definition.
import React from 'react';
import {useVideoConfig} from 'remotion';
import {SceneDurationContext, SEAM_FRAMES, ENTRY_T, clamp01} from './motion';

export type Warp = [number, number][];

/** The register frame a beat with knots `warp` sees at its film frame `f`: piecewise linear between knots, the
 *  identity outside them (the seams' held edges are never warped). Mirrors scripts/sync_qa.py `warp_frame`. */
export const warpFrame = (f: number, warp?: Warp | null): number => {
  if (!warp || warp.length < 2 || f <= warp[0][0] || f >= warp[warp.length - 1][0]) return f;
  for (let k = 1; k < warp.length; k++) {
    const [f0, g0] = warp[k - 1];
    const [f1, g1] = warp[k];
    if (f <= f1) return g0 + ((g1 - g0) * (f - f0)) / (f1 - f0);
  }
  return f;
};

/** What Film provides a beat: `at` = {prop path: film second at which the item should read}, and the beat's warp. */
export type BeatCues = {at: Record<string, number>; warp?: Warp | null};
export const CueContext = React.createContext<BeatCues | null>(null);

// THE FRACTION OF AN ENTRANCE WINDOW AT WHICH AN ITEM READS — composed opacity 0.5, the sync audit's "appeared".
// easeOutCubic crosses 0.5 at 0.206 of its window, easeOutExpo at 0.1, a linear fade at 0.5. Passing the
// register's own easing lands the item on its word; a value too high only makes it read a little early.
export const REACH_LINEAR = 0.5;
export const REACH_CUBIC = 0.21;
export const REACH_EXPO = 0.1;
// the shortest entrance a cued item is given when its word comes too early for its own window (seconds)
export const MIN_ENTRANCE_S = 0.3;

export type Cues = {
  /** The register-t at which the item `key` should READ, or null when the beat gives it no cue. */
  readT: (key: string) => number | null;
  /** The item's entrance window: [a, b] itself, or the same length moved EARLIER so the item reads at its cue —
   *  never later, never starting before `floor` (default: the end of the entry hold, so nothing fades in under the
   *  incoming dissolve). `reach` is the fraction of the window at which the item reads (REACH_*). */
  win: (key: string, a: number, b: number, reach?: number, floor?: number) => [number, number];
};

export function useCues(): Cues {
  const ctx = React.useContext(CueContext);
  const {fps, durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const dur = sceneDur ?? durationInFrames;
  // the same held-edge mapping runtime/motion `useT` uses — frame -> t
  const pad = Math.min(SEAM_FRAMES, Math.floor(Math.max(0, dur - 1) / 3));
  const span = Math.max(1, dur - 1 - 2 * pad);
  const tOf = (g: number) => ENTRY_T + (1 - ENTRY_T) * clamp01((g - pad) / span);
  const readT = (key: string): number | null => {
    const s = ctx?.at?.[key];
    if (typeof s !== 'number' || !Number.isFinite(s)) return null;
    return tOf(warpFrame(s * fps, ctx?.warp));
  };
  const win = (key: string, a: number, b: number, reach = REACH_LINEAR, floor = ENTRY_T): [number, number] => {
    const r = readT(key);
    if (r === null) return [a, b];
    const len = Math.max(0, b - a);
    const s = r - reach * len;
    if (s >= a) return [a, b];
    if (s >= floor || reach <= 0) return [Math.max(floor, s), Math.max(floor, s) + len];
    // NAMED IN THE VOICE'S FIRST BREATH: the window cannot start before `floor`, so it is SHORTENED to read on the
    // word anyway — a long fade started at the floor read a second late (an open question said 0.6 s in read at
    // 1.5 s). Never shorter than MIN_ENTRANCE_S; never longer than the register's own.
    const minLen = Math.min(len, ((1 - ENTRY_T) * MIN_ENTRANCE_S * fps) / span);
    const fit = Math.min(len, Math.max(minLen, (r - floor) / reach));
    return [floor, floor + fit];
  };
  return {readT, win};
}
