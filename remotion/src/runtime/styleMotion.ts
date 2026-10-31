// THE STYLE'S MOTION — how a drawn film moves, where a tweened one glides.
//
// `stepFrame` holds the register's clock on every 2nd or 3rd frame ("on twos", "on threes"): drawn animation is
// drawn that often, and a line that updates every frame reads as a tween however it is drawn. Film.tsx's BeatClock
// applies it AFTER the sync warp, to the register alone — the caption, the voice, the camera and the seams stay on
// ones. `squashAt` is the squash-and-stretch of a landing, area kept (sx·sy = 1). The easing personality lives with
// the easings it bends (runtime/motion.ts `setStyleEase`).

/** The frame a drawing stepped on `step`s shows at frame `f`: the last multiple of `step`. Monotone in `f`. */
export const stepFrame = (f: number, step: number): number => {
  const s = Math.max(1, Math.round(step));
  return s === 1 ? f : f - (((f % s) + s) % s);
};

/** Squash-and-stretch through a move at progress `p` (0..1), `amount` 0..1: a stretch along the move early, a
 *  squash on landing, nothing at rest — the area never changes. */
export const squashAt = (p: number, amount: number): {sx: number; sy: number} => {
  if (!(amount > 0) || p <= 0 || p >= 1) return {sx: 1, sy: 1};
  const s = 1 + amount * 0.35 * Math.sin(Math.PI * 2 * p) * (1 - p);
  return {sx: 1 / s, sy: s};
};
