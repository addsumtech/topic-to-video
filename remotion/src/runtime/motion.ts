// The tuning kit every bespoke shot uses. Deterministic (pure fn of frame — never Date.now/Math.random,
// which strobe under Remotion's off-thread capture). Adapted clean-room from the video-shotcraft Motion
// pattern (Apache-2.0): a normalized-time hook + easing/seg/lerp + a frame-stable hash.

import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, type SpringConfig} from 'remotion';

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

/** How many frames the shot's own 0→1 actually spans — the same window `useT` compresses into.
 *
 *  Exported because anything driven by REAL time rather than by a normalized ramp needs it: a spring is a
 *  physical simulation in frames, and running one against the composition's frame counter would animate it
 *  straight through the cross-dissolve that `useT` exists to keep still. */
export function useAnimSpan(): number {
  const {durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const dur = sceneDur ?? durationInFrames;
  const pad = Math.min(SEAM_FRAMES, Math.floor(Math.max(0, dur - 1) / 3));
  return Math.max(1, dur - 1 - 2 * pad);
}

/** The library's default spring: a settled arrival with a small, honest overshoot. */
export const SPRING_LAND: SpringConfig = {damping: 14, stiffness: 120, mass: 1, overshootClamping: false};
/** A heavier landing — a part seating into a socket, a card dealt onto a table. */
export const SPRING_SEAT: SpringConfig = {damping: 16, stiffness: 110, mass: 1.1, overshootClamping: false};
/** A light pop — a tick, a chip, a badge. */
export const SPRING_POP: SpringConfig = {damping: 10, stiffness: 260, mass: 1, overshootClamping: false};

/**
 * A SPRING on the shot's own clock, starting at normalized time `a`.
 *
 * WHY A SPRING AND NOT ANOTHER EASING. This library animated 160 registers with hand-rolled cubics, and the
 * closest thing it had to an arrival was `easeOutBack` — one fixed curve, so every element in every shot
 * lands with the same weight. The reference library this was measured against writes its landings in mass
 * and damping instead, and its own parameter notes say why: "落进框内是语义关键", "发牌落桌的手感；换
 * outCubic 会变成平淡的浮上来". The OVERSHOOT is the meaning — a thing that settles past its mark and comes
 * back reads as having weight; a thing that eases into place reads as being faded in.
 *
 * It is driven by `useT`, not by the raw frame, and that is not a detail: `useT` compresses the shot's whole
 * animation into the window where no cross-dissolve is running and freezes it under reduced motion. A spring
 * on the composition's own frame counter would keep bouncing through the seam — which is the exact flicker
 * `useT` was written to end — and would ignore the accessibility freeze.
 */
export const springAt = (t: number, span: number, fps: number, a = 0,
                        config: SpringConfig = SPRING_LAND): number =>
  spring({frame: Math.max(0, (t - a) * span), fps, config});

/**
 * The hook form, for a single spring. A STAGGERED LIST must use `springAt` instead, with `useT()`,
 * `useAnimSpan()` and `fps` read once above the loop: a hook called per item inside `.map()` is a hook
 * whose call count depends on the data, and the one thing a staggered deal changes between films is how
 * many things are dealt.
 */
export function useSpringAt(a = 0, config: SpringConfig = SPRING_LAND): number {
  const t = useT();
  const {fps} = useVideoConfig();
  const span = useAnimSpan();
  return springAt(t, span, fps, a, config);
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

// ── CONTINUING LIFE ───────────────────────────────────────────────────────────────────────────────────
//
// WHAT THIS IS FOR. Frame difference measured by quarter of each register's own clip says the motion
// deficit is not the camera and not the reveal — it is the HOLD. CinematicTitle runs 0.0015 -> 0.0009 ->
// 0.0001 -> 0.0000; BentoReveal 0.0061 -> 0.0006 -> 0.0005 -> 0.0002. Most registers finish their argument
// in the first half of the clip and then show a STILL PHOTOGRAPH for the rest, while the narration keeps
// going. MorphForms, the one register that clears the delivery floor comfortably, is the one that never
// stops developing. A frozen frame is a screenshot; this tier is supposed to be film.
//
// WHAT IT IS NOT. It is not a drift applied to every register to raise a number — that would be movement
// that means nothing, which this repo's own design rule forbids ("hide the caption: does the frame still
// carry THIS idea?"). It is a primitive for a register to keep doing the thing it already does: a dashboard
// whose gauges keep reading, a graph whose nodes keep orbiting, a counter that keeps counting.
//
// WHY IT CANNOT SHAKE, STRUCTURALLY. `life()` is a slow, continuous phase — one cycle over SECONDS — meant
// to drive a property of CONTENT, never a transform of the whole frame. Two guarantees follow. Global: the
// frame does not translate, so scripts/shake_qa.py (which measures global translation) is blind to it by
// construction, and no amount of it can trip that gate. Local: within any half-second window a cycle this
// slow is monotone, so even applied to a whole-frame transform it would read as travel, not vibration —
// the ratio that separates the two would still say "travelling". The period floor is enforced, not
// documented: `life()` THROWS below MIN_LIFE_PERIOD_S rather than letting a caller tune its way into a
// vibration.
export const MIN_LIFE_PERIOD_S = 3;

/**
 * A continuous 0→1→0 phase for a register's settled state, at `periodS` seconds per cycle.
 *
 * @param t        the shot's normalized time from useT()
 * @param durF     the shot's duration in frames (useVideoConfig().durationInFrames)
 * @param fps      frames per second
 * @param periodS  seconds per full cycle — at least MIN_LIFE_PERIOD_S
 * @param phase    0..1 offset, so several elements can live out of step with each other
 */
export function life(t: number, durF: number, fps: number, periodS = 6, phase = 0): number {
  if (!(periodS >= MIN_LIFE_PERIOD_S)) {
    throw new Error(
      `life() period ${periodS}s is below MIN_LIFE_PERIOD_S (${MIN_LIFE_PERIOD_S}s). Faster than this stops ` +
      'reading as a thing continuing to happen and starts reading as a wobble, which is the defect this ' +
      'tier has shipped before. Drive more elements, or a larger amplitude, rather than a shorter period.');
  }
  const seconds = t * (durF / Math.max(1, fps));
  return 0.5 - 0.5 * Math.cos((2 * Math.PI * (seconds / periodS + phase)));
}

/**
 * A continuous ANGLE in radians for the same clock — `life()`'s sibling, for oscillators written as
 * `Math.sin(...)` rather than as a 0→1 modulator.
 *
 * THE BUG THIS FIXES IS SYSTEMATIC, not a preference. Across the library, thirteen oscillators are written
 * `Math.sin(t * k)` with k between 1.2 and 5 — which reads like radians per second and is nothing of the
 * kind, because `t` runs 0→1 across the WHOLE clip. `Math.sin(t * 2)` delivers two radians of phase in five
 * seconds: a third of one cycle. Every one of them was authored as "this keeps breathing" and every one of
 * them renders as a slow one-way drift, which is a large part of why registers measure as frozen. The fix
 * is to say the period in the unit a period is actually in.
 */
export function radians(t: number, durF: number, fps: number, periodS = 6, phase = 0): number {
  if (!(periodS >= MIN_LIFE_PERIOD_S)) {
    throw new Error(`radians() period ${periodS}s is below MIN_LIFE_PERIOD_S (${MIN_LIFE_PERIOD_S}s) — see life().`);
  }
  const seconds = t * (durF / Math.max(1, fps));
  return 2 * Math.PI * (seconds / periodS) + phase;
}
