// MOTION BLUR, from the speed a thing is actually moving at. Pure — no React, no DOM — so the numbers are tested
// in node (tests/test_motion_blur.py) and the component (runtime/motionBlur.tsx) only draws them.
//
// A camera's shutter is open for part of each frame; whatever moves during that time smears along its path. The
// smear's length is the distance travelled while the shutter is open (`shutter` = the open fraction of a frame:
// 0.5 is the film-standard 180-degree shutter), and it is a BOX of that length, so the Gaussian that stands in for
// it has sd = L / sqrt(12). Two rules make it usable on type:
//   - at rest the result is null, never a zero-radius filter: a filter of any radius re-rasterises the layer, and
//     settled type must be drawn exactly as an unfiltered element is;
//   - under `minLength` (one pixel) it is null too: sub-pixel smear is noise, and toggling a filter on for it
//     flickers.
// The peer library drives blur from per-frame speed in ~10 shots (scroll brakes, cards whipping past the lens,
// dials, speed-ghosted glides); this library had three hand-drawn streak layers, each with its own constants.

export type Pose = {x: number; y: number; s?: number; r?: number};

export type SmearOpts = {
  /** fraction of a frame the shutter is open (0.5 = 180 degrees) */
  shutter?: number;
  /** sd cap in px: past it a whip reads as a grey bar rather than as speed */
  maxSigma?: number;
  /** smear lengths under this many px are not drawn */
  minLength?: number;
};

export type Smear = {angle: number; length: number; sigma: number};

/** The smear an element moving from `prev` to `now` (its pose one frame apart) leaves, or null at rest. */
export const smear = (now: Pose, prev: Pose, o: SmearOpts = {}): Smear | null => {
  const shutter = o.shutter ?? 0.5;
  const dx = now.x - prev.x, dy = now.y - prev.y;
  const length = Math.hypot(dx, dy) * shutter;
  if (!(length >= (o.minLength ?? 1))) return null;
  const sigma = Math.min(o.maxSigma ?? 24, length / Math.sqrt(12));
  return {angle: (Math.atan2(dy, dx) * 180) / Math.PI, length, sigma};
};

export type Ghost = Pose & {opacity: number};

export type GhostOpts = {
  count?: number;
  /** frames between ghosts */
  spacing?: number;
  /** opacity of the nearest ghost; each older one is `falloff` times the one before */
  opacity?: number;
  falloff?: number;
  /** a ghost nearer than this many px to the current pose is not drawn (it would only thicken the element) */
  minGap?: number;
};

/** Copies of the element at its EARLIER poses — speed ghosting for a scale or rotation change a directional blur
 *  cannot express (a crash zoom, a card spinning toward camera). Empty at rest. */
export const ghosts = (at: (frame: number) => Pose, frame: number, o: GhostOpts = {}): Ghost[] => {
  const n = o.count ?? 3, sp = o.spacing ?? 1, falloff = o.falloff ?? 0.55, minGap = o.minGap ?? 2;
  const now = at(frame);
  const out: Ghost[] = [];
  let op = o.opacity ?? 0.35;
  for (let i = 1; i <= n; i++) {
    const p = at(frame - i * sp);
    const moved = Math.hypot(p.x - now.x, p.y - now.y) + Math.abs((p.s ?? 1) - (now.s ?? 1)) * 400 +
      Math.abs((p.r ?? 0) - (now.r ?? 0)) * 4;
    if (moved < minGap) break;
    out.push({...p, opacity: op});
    op *= falloff;
  }
  return out;
};
