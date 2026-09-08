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
