// RAW EASINGS — the curves as drawn, never bent by the film's easing personality (motion.ts `personal`).
//
// A drawing style that moves with an overshoot (meta.style.motion.easing "overshoot") bends motion.ts's easings for
// every register — rightly, for the things a register draws. The CAMERA and the SEAMS are the film's language, not
// the drawing's: bent, a push overshot its framing by ~5 % and came back, and a seam swung past its end — a return
// on every beat of every film with that style (audit 2026-11-15, A3; 13 storyboards under film_work use it). Kept
// out of motion.ts on purpose: an export there re-keys every register that imports it.
export const rawEaseInOutCubic = (t: number): number =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
export const rawEaseOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);
