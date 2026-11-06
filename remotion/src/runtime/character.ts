// CHARACTER — an object that moves like a character, not a sprite (spec 2026-11-06 C3).
//
// WHY. A thing that hops without gathering itself, flies at one speed and stops dead reads as a slide being moved.
// The animator's oldest rules fix it: ANTICIPATION (it crouches before it jumps), an ARC, a LANDING squash and its
// recovery, and FOLLOW-THROUGH (its parts settle one after another). Squash and stretch keep the VOLUME: sx * sy == 1
// on every frame, or the object visibly gains and loses mass.
//
// hop(t01) is one hop over its own clock (0..1): y is the lift in units of `height` (negative = up), sx/sy the
// scale about the object's base. Every phase meets the next at the same value, so nothing pops between phases.
export type HopOpts = {antic?: number; land?: number; height?: number; squash?: number; stretch?: number};
export type HopPose = {y: number; sx: number; sy: number};

export const hop = (t01: number, o: HopOpts = {}): HopPose => {
  const antic = o.antic ?? 0.15, land = o.land ?? 0.15;
  const height = o.height ?? 0.3, squash = o.squash ?? 0.25, stretch = o.stretch ?? 0.1;
  const t = Math.min(1, Math.max(0, t01));
  if (t <= 0 || t >= 1) return {y: 0, sx: 1, sy: 1};
  let y = 0, sy = 1;
  if (t < antic) {                                   // crouch, and spring back to 1 at take-off
    sy = 1 - squash * Math.sin(Math.PI * (t / antic));
  } else if (t < 1 - land) {                         // the arc: stretched while fast, round at the top
    const u = (t - antic) / (1 - antic - land);
    y = -height * Math.sin(Math.PI * u);
    sy = 1 + stretch * Math.abs(Math.sin(2 * Math.PI * u));
  } else {                                           // land: squash and recover
    sy = 1 - squash * Math.sin(Math.PI * ((t - (1 - land)) / land));
  }
  return {y: y === 0 ? 0 : y, sx: 1 / sy, sy};
};

// Follow-through: part i of n starts `lag * i / (n - 1)` of the clock late and all finish together at 1.
export const stagger = (i: number, n: number, t01: number, lag = 0.2): number => {
  if (n <= 1) return Math.min(1, Math.max(0, t01));
  const start = (lag * i) / (n - 1);
  return Math.min(1, Math.max(0, (t01 - start) / (1 - lag)));
};
