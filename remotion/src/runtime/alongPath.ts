// WHERE A THING IS WHEN IT IS TRAVELLING ALONG A PATH.
//
// A register draws a curve and sends something down it — a packet along a route, a bright head leading the
// stroke that is drawing. The two have to agree about where the curve IS, and in this library they did not,
// because the travelling thing was placed by re-deriving the geometry by hand:
//
//   · `MapRoutes` draws each route as a quadratic `M hx,hy Q midx,midy px,py` and placed its packet at
//     `lerp(hub, pin, p)` minus a sine hump. Measured against the route's own arc length, the packet was up
//     to 140px away from the line it is supposed to be riding — visibly floating in the dark beside it.
//   · `LightTrails` draws a two-leg checkmark and split it at u=0.4, but the legs are 318 and 630 units, so
//     the elbow is at 33.6% of the length. Its head lagged the stroke tip it leads by up to 61px.
//
// Both are the same mistake: a SECOND model of a curve that already exists as a `d` string. Ask the path.
//
// AND ASK IT BY ARC LENGTH, not by parameter. `getPointAtLength(d, L * u)` moves at constant speed along the
// curve; the Bézier parameter does not, and neither does a hand-split at a round number. Constant speed is
// also what `pathLength={1}` gives the stroke (see runtime/draw), so a head placed this way stays welded to
// the tip of the stroke it is leading, at every frame and on every path.

// THE WALK IS runtime/pathWalk's — the browser's own arc length, the one kinetic's type on a path is placed by. This
// file asked @remotion/paths, whose points jitter backwards along a curve (GenerationLoop's return stroke went back 50
// of 66 times in 2048 steps) and whose tangent is reversed on arcs (audit 2026-11-15, step 6).
import {walkAt, walkLength, _walkInternals} from './pathWalk';

// NaN-SAFE: `Math.max(0, Math.min(1, NaN))` is NaN, and NaN reaching the DOM as `cx="NaN"` is dropped by the browser,
// parking the object at the frame's origin. A comparison that is false for NaN sends it to the start instead.
const clamp01 = (x: number) => (x > 0 ? (x < 1 ? x : 1) : 0);

/** The point `u` of the way along `d`, measured in ARC LENGTH (0 = start, 1 = end). */
export const pointAt = (d: string, u: number): {x: number; y: number} => {
  const p = walkAt(d, walkLength(d) * clamp01(u));
  return {x: p.x, y: p.y};
};

/**
 * The direction of travel at `u`, in DEGREES, for turning a travelling object to face where it is going.
 *
 * Returned in degrees because that is what a CSS/SVG `rotate()` takes — a caller converting from radians
 * every time is a caller with a chance to convert wrong.
 */
export const angleAt = (d: string, u: number): number => walkAt(d, walkLength(d) * clamp01(u)).deg;

/** The path's own length, memoised — for a register that needs to reason about it directly. */
export const pathLength = walkLength;

// for the test that holds the memo to its bound — a cache with no ceiling is a leak that only shows up on a
// register whose paths change every frame
export const _internals = {LENGTHS: _walkInternals.SEEN, MAX: _walkInternals.MAX_SEEN,
  TABLES: _walkInternals.TABLES, MAX_TABLES: _walkInternals.MAX_TABLES};
