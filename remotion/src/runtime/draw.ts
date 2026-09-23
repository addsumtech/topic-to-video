// DRAWING A STROKE ON, WITHOUT KNOWING HOW LONG IT IS.
//
// The technique is `stroke-dasharray` + `stroke-dashoffset`: one dash as long as the path, slid off the end
// and pulled back. It needs the path's LENGTH, and that is where this library kept getting it wrong — nine
// call sites passed a constant that had nothing to do with the geometry.
//
// The failure is silent and it runs in one direction. Drawn length is `declared × p`, capped at the real
// length, so:
//   · declared TOO LARGE → the stroke completes at `real / declared` and then holds. Measured on the library:
//     `MapRoutes` declares 1600 for routes that are 280–460 long, so every route finishes drawing between
//     p=0.17 and p=0.29 of its own reveal window and sits still for the remaining three quarters — a register
//     whose premise is "routes DRAW between pins" draws them almost instantly. `WireGlobe` (1400 against
//     ~440) completes at 0.31. Others land at 0.83–0.91, which only slightly clips the tail of the move.
//   · declared TOO SMALL → at p=1 only `declared` of the path is ever inked: the stroke NEVER completes, and
//     the frame ships with half a line on it.
// Nothing errors either way, and a still at the settled frame looks correct in the first case and merely
// "unfinished-looking" in the second.
//
// SO DO NOT MEASURE IT — MAKE THE MEASUREMENT UNNECESSARY. `pathLength={1}` tells SVG to scale the element's
// own length to 1 for every dash calculation, so a dash of 1 is exactly the whole path, whatever it is. It is
// exact for a `<path>` built from props at render time, for a `<polyline>`, and for a `<circle>`; it costs
// nothing; and there is no number left to get wrong.
//
// WHY NOT `@remotion/paths`. `evolvePath(p, d)` measures the real length in JS and returns the same two
// properties — correct, but it needs the `d` string, parses it every frame, and does not help `<polyline>` or
// `<circle>` at all. Reach for that package where the LENGTH ITSELF is the thing you need: a point or tangent
// somewhere along the path, or a morph between two paths. For drawing a stroke on, this is exact and free.

// NaN-SAFE, and the asymmetry is deliberate. `Math.max(0, Math.min(1, NaN))` is NaN, and a NaN
// `stroke-dashoffset` is an INVALID attribute: the browser drops it and falls back to 0, which renders the
// stroke FULLY DRAWN on every frame. A reveal that silently stops revealing looks finished, so nothing
// downstream can see it — whereas this comparison sends NaN to 0, where the stroke never starts and the
// defect is on the frame for anyone to notice. Fail toward the visible failure.
const clamp01 = (x: number) => (x > 0 ? (x < 1 ? x : 1) : 0);

/**
 * Spread onto any stroked SVG element to reveal it from its start to `p` (0 → nothing, 1 → the whole path).
 *
 * ```tsx
 * <path d={d} fill="none" stroke={ink} strokeWidth={3} {...drawOn(draw)} />
 * ```
 *
 * Nothing else in the element needs to know the geometry, so the same call is right for a straight line, a
 * quadratic arc built from two props, and a circle.
 */
export const drawOn = (p: number) => ({
  pathLength: 1,
  strokeDasharray: 1,
  strokeDashoffset: 1 - clamp01(p),
});

/**
 * The same reveal for a stroke that is itself DASHED — where `drawOn` cannot help, because the dash pattern
 * is carrying meaning (a planned route, a boundary) and cannot be spent on the reveal.
 *
 * The pattern is given in the element's own units and `pathLength` is deliberately NOT set, so the dashes
 * keep the size the design chose. What animates is the offset, which slides the pattern rather than growing
 * it — the honest thing to do when the dash is content.
 */
export const dashedStroke = (dash: number, gap: number, travel: number) => ({
  strokeDasharray: `${dash} ${gap}`,
  strokeDashoffset: -travel * (dash + gap),
});

// ── LINE BOIL ────────────────────────────────────────────────────────────────────────────────────────
//
// A hand-drawn line in this library does not move. `HandDrawn` jitters its rectangles with
// `hash01(s * 7 + k)` where `s` is the SHAPE's index — so the irregularity is decided once and then holds
// perfectly still for the whole shot, which is the one thing a hand cannot do. The register's Use clause
// says "human / hand-made"; a frozen wobble is a PHOTOGRAPH of a hand-made thing, and the stillness is
// exactly what reads as digital.
//
// Real boil is not per-frame noise. An animator draws the same shape two or three times and CYCLES those
// drawings; the line appears to breathe because the eye keeps recognising the same few variants. Drawing a
// fresh random variant every frame instead reads as static — television snow — which is why this returns a
// PHASE out of a small set rather than an ever-increasing seed.
//
// Frame-rate independent, because the rate is a property of the eye and not of the render: a boil pinned to
// "every 3 frames" doubles in speed on a 60fps film. Deterministic — a pure function of the shot's own
// normalised time, so two renders of one frame are the same bytes, and FROZEN under reduced motion for
// free, because `useT()` is frozen there and this reads nothing else.
/** Which of `phases` drawings of the same shape is on screen now. Add it to your own shape seed.
 *
 *  @param t      the shot's normalised time, from `useT()`
 *  @param durF   the shot's duration in frames
 *  @param fps    the film's frame rate
 *  @param hz     redraws per second — 8–12 is the animator's "on twos/threes" at 24–30fps
 *  @param phases how many drawings are cycled; 2 breathes, 3 is the classic, past 4 it reads as noise */
export const BOIL_HZ_MIN = 4, BOIL_HZ_MAX = 15, BOIL_PHASES_MAX = 4;

export const boilPhase = (t: number, durF: number, fps: number, hz = 10, phases = 3): number => {
  if (!(hz >= BOIL_HZ_MIN && hz <= BOIL_HZ_MAX)) {
    throw new Error(
      `boilPhase() rate ${hz}Hz is outside ${BOIL_HZ_MIN}–${BOIL_HZ_MAX}Hz. Slower reads as the drawing ` +
      'being REPLACED — a slideshow of sketches — and faster stops being a line that breathes and becomes ' +
      'television snow. Change the jitter amplitude at the call site instead of the rate.');
  }
  const n = Math.max(2, Math.min(BOIL_PHASES_MAX, Math.round(phases)));
  const seconds = clamp01(t) * (durF / Math.max(1, fps));
  return Math.floor(seconds * hz) % n;
};
