// PROJECT A 3D POINT INTO THE 2D FRAME — so type can be ANCHORED to a three.js object and still be real type.
//
// WHY THIS EXISTS. The moment a WebGL shot wants a label ON a thing in space — this segment, that socket —
// you need the thing's screen position, and both obvious ways to get it are wrong here:
//
//   * Texturing the text onto a mesh destroys it. A CJK glyph on a 512px texture is mush at render scale,
//     and it inherits the surface's lighting, so the copy DIMS whenever its part turns away from the key.
//     A label that fades because the object rotated is a label that failed.
//   * drei's <Html> is not a dependency here, and it injects a second DOM layer positioned by the GL loop,
//     which the text-safety and CJK audits cannot reason about.
//
// So the label stays an ordinary DOM element — crisp, hinted, in the film's own face, and visible to every
// type gate — and this computes where to put it. The camera convention is three's own (vertical fov in
// degrees, +Y up, right-handed), so a caller that passes the SAME camera it hands <ThreeCanvas> gets a label
// that sits on the object to the pixel.
//
// It is pure arithmetic on numbers the shot already has. Nothing is read back from the GL context, so two
// renders of the same frame cannot disagree — which is the property the whole library is built on.

export type Vec3 = [number, number, number];

const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a: Vec3, b: Vec3): Vec3 =>
  [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a: Vec3): Vec3 => {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};

/**
 * Where a point in the scene lands in the frame, and how far in front of the lens it is.
 *
 * Returns `null` when the point is behind the camera — which a caller MUST handle rather than clamp, because
 * a label for something behind you has no honest position and drawing it at the frame edge is a lie about
 * where the thing is.
 */
export const project = (
  p: Vec3, camera: Vec3, target: Vec3, fovDeg: number, W: number, H: number,
): {x: number; y: number; depth: number} | null => {
  const fwd = norm(sub(target, camera));
  // A camera looking straight down or straight up has no right-vector against world up. Nudging the
  // reference is not a nicety: a shot that tilts to a top-down beat is an ordinary move, and without this
  // every label on that frame becomes NaN and silently vanishes.
  const upRef: Vec3 = Math.abs(fwd[1]) > 0.999 ? [0, 0, 1] : [0, 1, 0];
  const right = norm(cross(fwd, upRef));
  const up = cross(right, fwd);
  const d = sub(p, camera);
  const z = dot(d, fwd);
  if (!(z > 1e-3)) return null;                     // behind the lens (and NaN-safe: !(NaN > x) is true)
  const tanH = Math.tan((fovDeg * Math.PI) / 360);  // three's fov is VERTICAL, in degrees
  const ndcX = dot(d, right) / z / (tanH * (W / H));
  const ndcY = dot(d, up) / z / tanH;
  return {x: (ndcX * 0.5 + 0.5) * W, y: (0.5 - ndcY * 0.5) * H, depth: z};
};

/** A point on a circle in the ground plane — the arrangement a "things around a centre" shot wants. */
export const onRing = (i: number, n: number, radius: number, y = 0, phase = 0): Vec3 => {
  const a = phase + (i / Math.max(1, n)) * Math.PI * 2;
  return [Math.cos(a) * radius, y, Math.sin(a) * radius];
};

/** Rotate a point about the Y axis — the same yaw a shot applies to its <group>, so labels track it. */
export const yawPoint = (p: Vec3, yaw: number): Vec3 => {
  const c = Math.cos(yaw), s = Math.sin(yaw);
  return [p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c];
};
