// DEPTH OF FIELD AS A SIGNAL — how far a thing is from what the shot is about, said in optics.
//
// WHY THIS EXISTS. This library had planes (`runtime/depth.tsx`) and no focus: things could sit at different
// depths and every one of them was equally sharp, which is the one thing a real lens never does. Measured
// against the reference library, focus is not decoration there — it is how 18 of its recipes say what
// matters. `terminal-3d` computes each window's focus from its distance to the camera
// (`opacity 0.34–1 + blur 0–2.2px + brightness 0.7–1`) so the off-centre ones recede into background;
// `graze-face-tour` says a flat interface only reads as GRAZED under shallow depth of field — "全清晰读作
// 平面滚动".
//
// SO IT IS ONE FUNCTION, NOT A LOOK. `SurfaceCarousel` already hand-rolled a version of this (scale, opacity
// and a blur, each with its own literal), and the next register to want it would have written a third. A
// shared curve means a film's off-focus material recedes the SAME way in every shot that uses it, which is
// what makes it read as one lens rather than as several effects.
//
// THE PIXEL NUMBERS SCALE, AND THE DEFAULT IS A DEFAULT. Every length here is a fraction of the frame's short
// side, because the reference's 2.2px is on a 480-wide design stage: copied as a number it is a blur nobody
// can see at 1080, and copied as its own proportion (~0.008 of the short side, ~8px) it is a heavy one.
// `blurFrac` defaults to 0.0022 — the value `SurfaceCarousel` arrived at — because there the blur is the
// THIRD cue, after a scale to 0.62 and a fade, and a heavier one just smears the neighbours into fog. A shot
// whose out-of-focus material does NOT shrink or fade has nothing else carrying the depth, and should raise
// it toward the reference's own proportion: `PointerTour` grazes a flat page at 0.008.

/** What an out-of-focus thing looks like at distance `d`. */
export type Focus = {opacity: number; blurPx: number; brightness: number; scale: number};

export type FocusOpts = {
  /** how far the far plane falls: 1 = the reference's own range. */
  depth?: number;
  /** the nearest opacity/brightness/scale an out-of-focus thing keeps. */
  minOpacity?: number;
  minBrightness?: number;
  minScale?: number;
  /** blur at d=1, as a fraction of the frame's short side (0.0022 ≈ 2.4px at 1080). */
  blurFrac?: number;
};

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

/**
 * `d` is 0 for the thing in focus and 1 for the furthest thing the shot still shows.
 *
 * Everything recedes together — dimmer, softer, darker, smaller — because that is what distance does. Moving
 * one of them alone reads as an effect applied to an object rather than as the object being further away.
 */
export const focusAt = (d: number, U: number, o: FocusOpts = {}): Focus => {
  const {depth = 1, minOpacity = 0.34, minBrightness = 0.7, minScale = 0.62, blurFrac = 0.0022} = o;
  const k = clamp01(d) * depth;
  return {
    opacity: 1 - (1 - minOpacity) * k,
    brightness: 1 - (1 - minBrightness) * k,
    scale: 1 - (1 - minScale) * k,
    blurPx: U * blurFrac * k,
  };
};

/**
 * The css `filter` for a focus — and NOTHING when the thing is in focus.
 *
 * Returning `blur(0px) brightness(1)` instead of undefined is not equivalent: any filter promotes the
 * element to its own compositing layer, so the sharp subject gets resampled through a filter pipeline it
 * does not need. On a text-bearing register that is the difference between crisp type and type that has been
 * through a texture unit.
 */
export const focusFilter = (f: Focus): string | undefined => {
  const parts: string[] = [];
  if (f.blurPx > 0.15) parts.push(`blur(${f.blurPx.toFixed(2)}px)`);
  if (Math.abs(f.brightness - 1) > 0.004) parts.push(`brightness(${f.brightness.toFixed(3)})`);
  return parts.length ? parts.join(' ') : undefined;
};

/**
 * Distance from a CAMERA, normalised — the form `pageCam2D` and the carousel both want.
 *
 * `spread` is the distance at which a thing is fully out of focus, in the same units as `dist`. Given 0 it
 * returns 0 rather than dividing by it: a shot with one object has nothing to be out of focus against, and
 * a NaN here would silently blank the frame through the filter.
 */
export const focusDist = (dist: number, spread: number) =>
  spread > 0 ? clamp01(Math.abs(dist) / spread) : 0;
