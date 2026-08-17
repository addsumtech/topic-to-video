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
export function useT(): number {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const reduced = React.useContext(ReducedMotionContext);
  if (reduced) return REDUCED_MOTION_T;
  const dur = sceneDur ?? durationInFrames;
  return clamp01(frame / Math.max(1, dur - 1));
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
