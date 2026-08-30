// The tuning kit every bespoke shot uses. Deterministic (pure fn of frame — never Date.now/Math.random,
// which strobe under Remotion's off-thread capture). Adapted clean-room from the video-shotcraft Motion
// pattern (Apache-2.0): a normalized-time hook + easing/seg/lerp + a frame-stable hash.

import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// When a shot is embedded in the film (SceneWrapper), the composition's durationInFrames is the WHOLE film,
// not this scene — so a scene provides its own frame-length here and useT() normalizes against it. Standalone
// (no provider) it falls back to the composition duration, so each shot still works as its own Composition.
export const SceneDurationContext = React.createContext<number | null>(null);

// REDUCED MOTION (accessibility). When on, useT() FREEZES at a settled value so the shot renders a static,
// fully-revealed frame instead of animating — the flagship-tier equivalent of the html/image tier's static
// variant. 0.86 lands in the "reveal complete, exit not begun" zone for the library's shots (mirrors the contest
// still frame). Covers the 122 shots driven by useT; the ~10 that read useCurrentFrame directly are unaffected.
export const ReducedMotionContext = React.createContext<boolean>(false);
export const REDUCED_MOTION_T = 0.86;

// Normalized time 0→1 across the shot (or the embedded scene). Frozen at REDUCED_MOTION_T under reduced motion.
// SEAM_FRAMES must equal Film.tsx's cross-dissolve length. Exported so the two cannot drift: the whole
// point below is that a shot is STILL for exactly the frames a dissolve is running over it.
export const SEAM_FRAMES = 12;
// The t a shot is HELD at while the incoming dissolve runs over it — see useT below.
export const ENTRY_T = 0.06;

/** Normalized time 0→1 across the shot — but SETTLED at both edges.
 *
 *  Naively this was `frame / (dur - 1)`, so a shot animated right up to its last frame while the
 *  cross-dissolve was already blending the next shot in over it, and the incoming shot began its
 *  entrance while still半-transparent. Every seam therefore showed TWO shots at once with at least one
 *  of them moving — the flicker. Measured on a sample: motion energy at the seams was ~11 against a
 *  settled baseline of 0.12-0.5, i.e. 20-90x, and the incoming shot's entrance spiked to ~20 DURING
 *  the dissolve.
 *
 *  Studio motion design cuts between SETTLED states, never mid-animation. So compress the shot's whole
 *  0→1 into the window where no dissolve is running: hold t=0 while the incoming dissolve plays, animate
 *  alone in the middle, hold t=1 (fully landed) while the outgoing dissolve plays. Content lands sooner
 *  and holds longer, which is also better pacing.
 *
 *  The pad never eats more than a third of a scene, so a very short scene degrades to "animates faster",
 *  never to "never animates". */
export function useT(): number {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const reduced = React.useContext(ReducedMotionContext);
  if (reduced) return REDUCED_MOTION_T;
  const dur = sceneDur ?? durationInFrames;
  const pad = Math.min(SEAM_FRAMES, Math.floor(Math.max(0, dur - 1) / 3));
  const span = Math.max(1, dur - 1 - 2 * pad);
  // ENTRY_T, not 0. The incoming shot is HELD for `pad` frames while the dissolve runs over it — which is
  // what stopped the seam flicker, and stays. But holding at exactly 0 means it is held at NOTHING: every
  // register's first reveal step has not begun, so a cut resolves onto an empty page. Measured across a
  // delivered film's seams, mid-dissolve ink fell to 0.63% against a 3.10% settled frame — no cut in the
  // film ever cut between two images. Held at a small positive t the shot is still perfectly STILL (the
  // value is constant across the pad, so the flicker fix is untouched), but what is held is its composed
  // skeleton — ground, frame, kicker — rather than a blank. Registers reveal content from ~0.1 onward, so
  // this lands after the shell and before anything the eye would see move.
  //
  // The clamp goes on the PROGRESS, not on the remapped value. Written the other way round —
  // `clamp01(ENTRY_T + (1 - ENTRY_T) * p)` — the negative progress of the hold frames drags the sum BELOW
  // zero and clamp01 pins it to 0, so ENTRY_T was a complete no-op at exactly the edge it was written for:
  // t ramped 0 -> 0.0299 -> 0.06 across the pad instead of resting at 0.06, and the shot was held at the
  // blank state after all. The claim two paragraphs up that "the value is constant across the pad" was
  // false as written, and the 0.63% mid-dissolve ink quoted there was re-measured AFTER the change and had
  // not moved — the number was the proof it had not worked, read as the motivation for it.
  return ENTRY_T + (1 - ENTRY_T) * clamp01((frame - pad) / span);
}

// Re-map a sub-window [a,b] of global t to a local 0→1 (for phase timing within a shot).
export const seg = (t: number, a: number, b: number) => clamp01((t - a) / Math.max(1e-6, b - a));

// Easings.
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
export const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)); // the "house" quick-out settle
export function easeOutBack(t: number): number {
  const c1 = 1.70158, c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}
// The "superhuman" cursor ease: slow-start, rapid-middle, slow-stop (Raycast/Linear cursor narrative).
export const easeCursor = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2);

// Frame-STABLE hash → [0,1). Same input always yields the same value (deterministic scatter, never a
// per-frame RNG). Use an integer seed (an index), NOT the frame.
export function hash01(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}
