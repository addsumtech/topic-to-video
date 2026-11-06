// TRACK — where the film's THROUGH-OBJECT is at a moment of its beat (spec 2026-11-06 C1).
//
// WHY. The ANC film drew its earbud six different ways in six shots: each beat redrew the object from scratch, so it
// jumped in place, size and identity at every cut, and the viewer met six earbuds instead of following one. A beat on
// `meta.through_object` now carries `slide.track = {object, in, out}`: the pose the object enters with and the pose it
// leaves with, in fractions of the frame (rotation in degrees). validate holds beat N's `out` equal to beat N+1's
// `in`, so the object a cut hands on is where the next beat picks it up. A shot reads its `track` prop through this.
//
// The move between the two poses is an ease-in-out (smoothstep): it leaves and arrives at rest, so the pose at the
// cut is a still pose on both sides of it — a velocity jump at the cut reads as a hitch even when the poses agree.
export type Pose = {x: number; y: number; scale: number; rot: number; state?: string};
export type Track = {object: string; in: Pose; out: Pose};

const FIELDS: (keyof Pose)[] = ['x', 'y', 'scale', 'rot'];

const assertPose = (p: unknown, which: string): Pose => {
  const o = p as Record<string, unknown>;
  if (!o || typeof o !== 'object' || !FIELDS.every((k) => typeof o[k] === 'number' && Number.isFinite(o[k] as number))) {
    throw new Error(`track.${which} must be {x, y, scale, rot} with finite numbers, got ${JSON.stringify(p)}`);
  }
  return o as unknown as Pose;
};

export const trackAt = (track: Track, t01: number): Pose => {
  const a = assertPose(track?.in, 'in');
  const b = assertPose(track?.out, 'out');
  const t = Math.min(1, Math.max(0, t01));
  const e = t * t * (3 - 2 * t);
  const pose: Pose = {x: 0, y: 0, scale: 0, rot: 0};
  for (const k of FIELDS) {
    (pose[k] as number) = t <= 0 ? (a[k] as number) : t >= 1 ? (b[k] as number)
      : (a[k] as number) + ((b[k] as number) - (a[k] as number)) * e;
  }
  const state = t < 1 ? a.state : b.state;
  return state === undefined ? pose : {...pose, state};
};
