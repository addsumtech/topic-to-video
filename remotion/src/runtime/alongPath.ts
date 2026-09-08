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

import {getLength, getPointAtLength, getTangentAtLength} from '@remotion/paths';

// Parsing a `d` string is not free and these are called per travelling object per frame — six routes at 30fps
// is 180 parses a second for six strings that change only when the layout does. The key is the string itself,
// so a path that genuinely changes shape is measured again and one that does not is measured once.
const LENGTHS = new Map<string, number>();
const MAX = 512;                       // a register builds a bounded set of paths; this only bounds a leak

const lengthOf = (d: string): number => {
  const hit = LENGTHS.get(d);
  if (hit !== undefined) return hit;
  const L = getLength(d);
  if (LENGTHS.size >= MAX) LENGTHS.clear();
  LENGTHS.set(d, L);
  return L;
};

// The clamp is here for NEGATIVES, which is not a style point: `getPointAtLength` THROWS on a length below
// zero ("Length less than 0 was passed"), and `seg()` and the springs both undershoot at the start of a
// window — so an un-clamped `u` takes the render down. Past the end it saturates on its own, and NaN it
// already answers with the path's start (both verified against the installed version), so the plain form is
// honest here; `runtime/draw` uses a NaN-safe clamp because there the number reaches the DOM unmediated.
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

/** The point `u` of the way along `d`, measured in ARC LENGTH (0 = start, 1 = end). */
export const pointAt = (d: string, u: number): {x: number; y: number} =>
  getPointAtLength(d, lengthOf(d) * clamp01(u));

/**
 * The direction of travel at `u`, in DEGREES, for turning a travelling object to face where it is going.
 *
 * Returned in degrees because that is what a CSS/SVG `rotate()` takes — a caller converting from radians
 * every time is a caller with a chance to convert wrong.
 */
export const angleAt = (d: string, u: number): number => {
  const t = getTangentAtLength(d, lengthOf(d) * clamp01(u));
  return (Math.atan2(t.y, t.x) * 180) / Math.PI;
};

/** The path's own length, memoised — for a register that needs to reason about it directly. */
export const pathLength = lengthOf;

// for the test that holds the memo to its bound — a cache with no ceiling is a leak that only shows up on a
// register whose paths change every frame
export const _internals = {LENGTHS, MAX};
