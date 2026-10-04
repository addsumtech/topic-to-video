// A STAGE WITH SPACE IN IT — cards posed anywhere in 3D, a camera that flies to align with any one of them,
// and type that stays type.
//
// WHY THIS EXISTS. Measured against the peer library on 2026-09-05 (references/launch-film-study.md): they
// carry `rotateX` in 24 shots, this library in TWO; `perspective` 34 against 10. The gap is not a missing
// effect, it is that our camera has push and pull and no SPACE — `SceneCamera` is a scale and a 2D
// translate, so paging through an argument can never be travel through its space. Their whole 3D line rests
// on one formula, `camera = stepTransform.inverse()`: pose the cards anywhere, and to visit one, apply the
// INVERSE of its own transform to the world. `basic-3d-scene`, `cube-navigation`, `terminal-3d` and
// `flying-words` are all that one idea. It is also cheap and exact — no GL context, no readback, and the
// same numbers every render, which is the property this library is built on.
//
// AND TYPE DOES NOT RIDE THE Z PLANE. `runtime/depth` measured what happens when it does, on this renderer:
// glyph edge strength 91 flat, 86 under a plain 2D scale (explained by the glyphs being larger, not softer)
// and 56 under `perspective(1200px) translateZ(50px)` — a 38% loss that is plainly fuzzy. A 3D-composited
// layer is rasterized once at layout size and upscaled by the GPU. So the stage carries SURFACES, and every
// label is an ordinary 2D DOM element over them — crisp, in the film's own face, and visible to every type
// gate. BUT 2D DOES NOT MEAN UPRIGHT: a word ON a face takes that face's plane through a 2D affine
// (`<OnSurface>`), and only a word IN the space — hovering beside an object, flying at the lens — is a
// billboard placed by `projectPose`. This header used to say every label was placed by `projectPose`, and
// two registers took it at its word and drew their text level over tilted glass; see `OnSurface`. That is the same split `runtime/project3d` makes for the GL registers and
// `runtime/pageCam2D` makes for the flat ones, and it is made here for the same recorded reason: two
// cameras that agree until they quietly do not put all six of PortRail's labels 215px off their modules, on
// a frame that read as correct with the wrong words on it. One camera, described once, projection derived
// from the same matrix.
//
// COORDINATES. Stage space is CSS pixels on a W x H plane at z = 0, origin at the CENTRE of the frame, +x
// right, +y DOWN (CSS's own convention, not three's), +z toward the viewer. A `Pose` is applied in CSS's
// own order — translate, rotateX, rotateY, rotateZ, scale — so a pose written here and the same numbers
// written in a `transform` string mean the same thing.

import React from 'react';
import {useVideoConfig} from 'remotion';
import {useGlide} from './glide';

/** Where a thing stands on the stage. Every field optional; an empty pose is the centre of the frame. */
export type Pose = {x?: number; y?: number; z?: number; rx?: number; ry?: number; rz?: number; s?: number};

/** Column-major 4x4, the order CSS `matrix3d()` takes its sixteen numbers in. Kept column-major end to end
 *  so nothing is ever transposed on the way out — a transpose that is right for a symmetric test case and
 *  wrong for a rotated one is the classic way this maths ships broken. */
export type Mat4 = number[];

const RAD = Math.PI / 180;

export const identity = (): Mat4 => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];

/** `a` then… no: C = A·B applies B FIRST, then A — the same order the symbols read in a CSS transform. */
export const mul = (a: Mat4, b: Mat4): Mat4 => {
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) {
    for (let r = 0; r < 4; r++) {
      let s = 0;
      for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
      o[c * 4 + r] = s;
    }
  }
  return o;
};

const translate = (x: number, y: number, z: number): Mat4 =>
  [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1];
const scaleM = (s: number): Mat4 => [s, 0, 0, 0, 0, s, 0, 0, 0, 0, s, 0, 0, 0, 0, 1];
const rotX = (d: number): Mat4 => {
  const c = Math.cos(d * RAD), s = Math.sin(d * RAD);
  return [1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1];
};
const rotY = (d: number): Mat4 => {
  const c = Math.cos(d * RAD), s = Math.sin(d * RAD);
  return [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1];
};
const rotZ = (d: number): Mat4 => {
  const c = Math.cos(d * RAD), s = Math.sin(d * RAD);
  return [c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
};

/** The matrix a `Pose` means, in CSS's own application order: translate, rotateX, rotateY, rotateZ, scale. */
export const matrixOf = (p: Pose): Mat4 => {
  const {x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, s = 1} = p;
  return mul(mul(mul(mul(translate(x, y, z), rotX(rx)), rotY(ry)), rotZ(rz)), scaleM(s));
};

/** The INVERSE of a pose, built as the reversed product of each part's own inverse rather than by a general
 *  4x4 inversion. A TRS inverse is exact in closed form; a determinant-based one is not, and the error it
 *  carries is worst exactly where this is used — a camera aligned with a steeply rotated card. */
export const inverseOf = (p: Pose): Mat4 => {
  const {x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, s = 1} = p;
  const inv = s === 0 ? 1 : 1 / s;
  return mul(mul(mul(mul(scaleM(inv), rotZ(-rz)), rotY(-ry)), rotX(-rx)), translate(-x, -y, -z));
};

/** The sixteen numbers as CSS takes them. */
export const css = (m: Mat4): string => `matrix3d(${m.map((n) => (Math.abs(n) < 1e-6 ? 0 : n)).join(',')})`;

/** Where the origin of `pose` lands on the frame, under `cam`, with the stage's perspective.
 *
 *  `k` is the perspective scale at that depth — the factor CSS itself applies — so a 2D overlay can size
 *  itself the way the surface under it was sized without guessing. `behind` is true when the point is at or
 *  past the eye, where the divide is meaningless: callers draw nothing rather than a value with a sign flip
 *  in it, which is what a bare division gives you one frame before a card crosses the lens.
 */
export const projectPose = (
  pose: Pose, cam: Pose, persp: number, W: number, H: number,
): {x: number; y: number; k: number; behind: boolean} => {
  const m = mul(inverseOf(cam), matrixOf(pose));
  const ex = m[12], ey = m[13], ez = m[14];          // the pose's origin in eye space
  const denom = persp - ez;
  if (!(denom > 1e-3)) return {x: W / 2, y: H / 2, k: 0, behind: true};
  const k = persp / denom;
  return {x: W / 2 + ex * k, y: H / 2 + ey * k, k, behind: false};
};

/** Where a LOCAL point on a surface's plane lands on the frame. `lx, ly` are px from the surface's centre
 *  in its own unrotated coordinates — the space `Surface` lays its children out in, since it is placed at
 *  `left: -w/2, top: -h/2`. `projectPose` is this at (0, 0). */
export const projectLocal = (
  pose: Pose, cam: Pose, persp: number, W: number, H: number, lx: number, ly: number,
): {x: number; y: number; behind: boolean} => {
  const m = mul(inverseOf(cam), matrixOf(pose));
  const ex = m[0] * lx + m[4] * ly + m[12];
  const ey = m[1] * lx + m[5] * ly + m[13];
  const ez = m[2] * lx + m[6] * ly + m[14];
  const denom = persp - ez;
  if (!(denom > 1e-3)) return {x: W / 2, y: H / 2, behind: true};
  const k = persp / denom;
  return {x: W / 2 + ex * k, y: H / 2 + ey * k, behind: false};
};

/**
 * The 2D AFFINE transform that lays a FLAT element onto a surface's plane, fitted to the local rect it covers.
 *
 * WHY THIS EXISTS. Type over a posed surface was placed by `projectPose` — the surface's ORIGIN projected to a
 * point, plus one uniform scale — so it could translate and grow but never turn. A viewer looking at the
 * first beat of a real film said it plainly: the windows tilt with the room and the words on them do not;
 * they float upright over the glass like a sticker instead of lying on the screen.
 *
 * WHY AFFINE AND NOT THE SURFACE'S OWN `matrix3d`. Putting the type INSIDE the posed surface is what the stage
 * was built to avoid: a 3D-composited layer is rasterised once and scaled, and `runtime/depth` measured the
 * cost at 91 flat against 56 under Z. A 2D `matrix()` — rotate, skew, scale, no perspective term — stays in the
 * 2D path, where the browser rasterises glyphs at their final transform. Three projected corners of the text's
 * own local rect define it exactly at those corners; perspective foreshortening ACROSS a text block is the one
 * thing an affine cannot represent, and over a block that small against the stage's perspective distance the
 * residual is sub-pixel. Measured, not assumed: see `scripts/type_sharpness.py --ab`.
 *
 * Returns null when any corner is at or behind the eye — the caller draws nothing, as with `projectPose`.
 */
export const planeAffine = (
  pose: Pose, cam: Pose, persp: number, W: number, H: number,
  left: number, top: number, width: number, height: number,
): {m11: number; m12: number; m21: number; m22: number; tx: number; ty: number; scale: number} | null => {
  if (!(width > 0) || !(height > 0)) return null;
  const a = projectLocal(pose, cam, persp, W, H, left, top);
  const b = projectLocal(pose, cam, persp, W, H, left + width, top);
  const c = projectLocal(pose, cam, persp, W, H, left, top + height);
  if (a.behind || b.behind || c.behind) return null;
  const m11 = (b.x - a.x) / width, m12 = (b.y - a.y) / width;
  const m21 = (c.x - a.x) / height, m22 = (c.y - a.y) / height;
  // the local-to-screen area ratio, square-rooted: what a uniform scale would have been, for callers that
  // still size or cull by it
  return {m11, m12, m21, m22, tx: a.x, ty: a.y, scale: Math.sqrt(Math.abs(m11 * m22 - m12 * m21))};
};

/**
 * TYPE THAT BELONGS TO A SURFACE, placed ON that surface — the one way to do it, so no register has to
 * remember the matrix.
 *
 * THE RULE THIS COMPONENT ENFORCES. A word on the stage is one of two things, and they must not be drawn the
 * same way:
 *
 *   ON a surface      a console's prompt, a card's title, a screen's label. It belongs to that face, so it
 *                     takes that face's plane: when the card turns, the word turns with it. Use <OnSurface>.
 *   IN the space      a label hovering beside an object, a word flying at the lens. It belongs to no face, so
 *                     it faces the viewer: a billboard, placed by `projectPose`. A register that draws these
 *                     says so with `// @billboard: <why>` so the choice is visible and the library test can
 *                     tell a deliberate billboard from a forgotten one.
 *
 * WHY IT EXISTS AS A COMPONENT. The stage's original pattern placed EVERY word by `projectPose` — the surface's
 * origin projected to a point, one uniform scale — which is right for a billboard and wrong for a word on a
 * face: it can move and grow but never turn. Two registers built on that pattern drew their words upright over
 * tilted glass. A viewer caught it on one (TermSpace, "not aligned like the terminal window is"); an audit of
 * every 3D register then found the other (SpatialSlides, where each card's own rules tilt and its title does
 * not). Fixing them one at a time is how the third would have shipped.
 *
 * `left, top, width, height` are the text block's rect in the surface's LOCAL px, measured from its centre —
 * the space `Surface` lays its children out in. Children are laid out in those local px, unscaled; the
 * matrix carries both the turn and the perspective scale. Pass `affine` when the caller has already computed
 * it (to cull or fade on its screen size) so it is not solved twice.
 *
 * `glide`: the stage's camera moves somewhere in this beat. A face that squarely faces the lens is a pure scale
 * and translate — the matrix under which Skia rounds a line of type to whole pixels (runtime/glide.ts) — so a word
 * on it steps against its own card while the camera flies. With `glide` the word carries the baseline unlock for
 * the whole beat, raised for the size the face is drawn at; a stage whose camera never moves leaves it off.
 */
export const OnSurface: React.FC<{
  pose: Pose; cam: Pose; persp: number; W: number; H: number;
  left: number; top: number; width: number; height: number;
  affine?: ReturnType<typeof planeAffine>;
  glide?: boolean;
  style?: React.CSSProperties; children?: React.ReactNode;
}> = ({pose, cam, persp, W, H, left, top, width, height, affine, glide = false, style, children}) => {
  const unlock = useGlide();
  const a = affine ?? planeAffine(pose, cam, persp, W, H, left, top, width, height);
  if (!a) return null;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width, transformOrigin: '0 0',
      transform: unlock(`matrix(${a.m11},${a.m12},${a.m21},${a.m22},${a.tx},${a.ty})`, glide,
        Math.max(1e-3, a.scale)), ...style}}>
      {children}
    </div>
  );
};

/** The box on the frame a projected label may occupy — the same shape `runtime/fitCamera` takes, and for the
 *  same reason: "does it fit" and "does it collide with the caption band" are one question. */
export type StageBox = {left: number; top: number; right: number; bottom: number};

/**
 * The camera that brings every one of `poses` inside `box`, found by PROJECTING them and backing off until
 * they land — never by a closed form.
 *
 * `runtime/fitCamera` records why it bisects: solving the distance from an object's radius and the
 * half-angle under-reports the extent by exactly the amount perspective adds, because the half of an object
 * nearer the lens projects larger than its centre depth predicts. It came within 14px of failing at 4:3.
 *
 * TWO THINGS IT MUST DO, AND THE FIRST VERSION DID ONLY ONE. Backing off shrinks the cluster toward the
 * VANISHING POINT, which is wherever the lens happens to be aimed — not the middle of the box. Bisecting on
 * distance alone, with a camera that was not aimed, the five poses converged on y=413 against a window of
 * 445..611 and NEVER fitted at any distance: `fits` came back false, the caller took the fallback of 40000,
 * and the whole route rendered as an illegible clump of 8px words in the middle of a black frame. It was a
 * frame, so it looked like a design choice. So the camera is AIMED first — at the centroid of what it has to
 * hold, offset to the box's own centre — and only then does the distance bisect.
 *
 * `radius` is each pose's half-extent in stage units (a card's half-diagonal, say). It is scaled by the
 * perspective factor at that pose's depth rather than added to the centre flat, because a flat pad is the
 * card's size at the lens and the card is not at the lens.
 */
export const fitStage = (
  poses: Pose[], cam: Pose, box: StageBox, persp: number, W: number, H: number,
  opts: {radius?: number; steps?: number; maxZ?: number} = {},
): {cam: Pose; fits: boolean} => {
  const {radius = 0, steps = 26, maxZ = 60000} = opts;
  if (!poses.length) return {cam, fits: true};
  // aim: the centroid of the poses, shifted so that centroid lands on the box's centre rather than the
  // frame's — the band belongs to the renderer, so the usable middle is not H/2.
  const cx = poses.reduce((a, p) => a + (p.x ?? 0), 0) / poses.length;
  const cy = poses.reduce((a, p) => a + (p.y ?? 0), 0) / poses.length;
  const aimed: Pose = {...cam,
    x: cx - ((box.left + box.right) / 2 - W / 2),
    y: cy - ((box.top + box.bottom) / 2 - H / 2)};
  const inside = (z: number) => {
    const c = {...aimed, z};
    for (const p of poses) {
      const q = projectPose(p, c, persp, W, H);
      if (q.behind) return false;
      const r = radius * q.k;
      if (q.x - r < box.left || q.x + r > box.right) return false;
      if (q.y - r < box.top || q.y + r > box.bottom) return false;
    }
    return true;
  };
  let lo = 0, hi = 0;
  for (let i = 0; i < 30 && !inside(hi); i++) hi = hi === 0 ? 240 : Math.min(maxZ, hi * 1.7);
  // Pulling back shrinks the spread AND the radius toward the aim point, so a distance that fits exists for
  // any finite route. `fits:false` therefore means the box itself is smaller than the pad — a caller error
  // worth reporting rather than a framing to paper over.
  if (!inside(hi)) return {cam: {...aimed, z: hi}, fits: false};
  for (let i = 0; i < steps; i++) {
    const mid = (lo + hi) / 2;
    if (inside(mid)) hi = mid; else lo = mid;
  }
  return {cam: {...aimed, z: hi}, fits: true};
};

/**
 * The camera that brings every one of these SURFACES inside `box` — the same search as `fitStage`, asked of
 * the thing a register actually draws.
 *
 * `fitStage` takes POSES and an optional `radius`, which treats each surface as a sphere around its origin.
 * For a wide, tilted plane that is badly wrong in both directions at once: the sphere is far larger than the
 * plane's projected height (so the camera backs off and the stack sits small in a mostly empty frame) and it
 * ignores which way the plane is turned (so a yaw that swings a corner outward is not seen at all). The first
 * render of `PlaneStack` lost about a third of the content zone to that over-estimate.
 *
 * The corners are projected through `projectLocal`, which is the same matrix path `Surface` and `OnSurface`
 * use — so there is no second convention here to drift against the first, which is the failure this whole
 * file is shaped around.
 */
export const fitSurfaces = (
  planes: {pose: Pose; w: number; h: number}[], cam: Pose, box: StageBox, persp: number, W: number, H: number,
  opts: {steps?: number; maxZ?: number; pad?: number} = {},
): {cam: Pose; fits: boolean} => {
  const {steps = 26, maxZ = 60000, pad = 0} = opts;
  if (!planes.length) return {cam, fits: true};
  const cx = planes.reduce((a, p) => a + (p.pose.x ?? 0), 0) / planes.length;
  const cy = planes.reduce((a, p) => a + (p.pose.y ?? 0), 0) / planes.length;
  const aimed: Pose = {...cam,
    x: cx - ((box.left + box.right) / 2 - W / 2),
    y: cy - ((box.top + box.bottom) / 2 - H / 2)};
  const inside = (z: number) => {
    const c = {...aimed, z};
    for (const {pose, w, h} of planes) {
      for (const [dx, dy] of [[-w / 2, -h / 2], [w / 2, -h / 2], [-w / 2, h / 2], [w / 2, h / 2]] as const) {
        const q = projectLocal(pose, c, persp, W, H, dx, dy);
        if (q.behind) return false;
        if (q.x - pad < box.left || q.x + pad > box.right) return false;
        if (q.y - pad < box.top || q.y + pad > box.bottom) return false;
      }
    }
    return true;
  };
  const solve = (): number | null => {
    let hi = 0;
    for (let i = 0; i < 30 && !inside(hi); i++) hi = hi === 0 ? 240 : Math.min(maxZ, hi * 1.7);
    if (!inside(hi)) return null;
    let lo = 0;
    for (let i = 0; i < steps; i++) {
      const mid = (lo + hi) / 2;
      if (inside(mid)) hi = mid; else lo = mid;
    }
    return hi;
  };
  // ...AND THEN CENTRED ON WHAT IS ACTUALLY DRAWN. Aiming at the centroid of the poses centres the stack's
  // ORIGINS, which is not the same picture: a yaw swings the far corners one way and perspective enlarges the
  // near ones, so the ink lands off to one side with a wide empty margin opposite. `PlaneStack` first read as
  // a stack shoved to the right of an empty frame. The projected bounding box is measured and the camera slid
  // so ITS centre lands on the box's, then the distance is solved again because the slide changes what fits.
  let z = solve();
  if (z === null) return {cam: {...aimed, z: 0}, fits: false};
  for (let pass = 0; pass < 2; pass++) {
    const c = {...aimed, z};
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, kSum = 0, kN = 0;
    for (const {pose, w, h} of planes) {
      for (const [dx, dy] of [[-w / 2, -h / 2], [w / 2, -h / 2], [-w / 2, h / 2], [w / 2, h / 2]] as const) {
        const q = projectLocal(pose, c, persp, W, H, dx, dy);
        if (q.behind) return {cam: c, fits: false};
        x0 = Math.min(x0, q.x); x1 = Math.max(x1, q.x);
        y0 = Math.min(y0, q.y); y1 = Math.max(y1, q.y);
      }
      const o = projectPose(pose, c, persp, W, H);
      if (!o.behind) { kSum += o.k; kN += 1; }
    }
    const k = kN ? kSum / kN : 1;
    if (!(k > 1e-6)) break;
    const dxPx = (box.left + box.right) / 2 - (x0 + x1) / 2;
    const dyPx = (box.top + box.bottom) / 2 - (y0 + y1) / 2;
    if (Math.abs(dxPx) < 1 && Math.abs(dyPx) < 1) break;
    aimed.x = (aimed.x ?? 0) - dxPx / k;              // camera right moves the picture left
    aimed.y = (aimed.y ?? 0) - dyPx / k;
    const again = solve();
    if (again === null) break;
    z = again;
  }
  return {cam: {...aimed, z}, fits: true};
};

/** The perspective this library stages at, as a fraction of the frame's short side. Written once because the
 *  projection and the CSS must use the SAME number — that is the whole failure this file is shaped around. */
export const PERSP_FRAC = 1.15;

export const StageContext = React.createContext<{cam: Pose; persp: number}>({cam: {}, persp: 1200});
export const useStage = () => React.useContext(StageContext);

/**
 * The 3D world. Everything inside is posed in stage space and moves under one camera; everything that is
 * TYPE belongs OUTSIDE it, positioned by `projectPose`.
 *
 * The world is the camera's inverse, exactly as the peer library's `basic-3d-scene` does it — to visit a
 * card you hand its own pose in as the camera and the world swings round to face you.
 */
export const Stage3D: React.FC<{cam?: Pose; persp?: number; children?: React.ReactNode}> = ({
  cam = {}, persp, children,
}) => {
  const {width: W, height: H} = useVideoConfig();
  const P = persp ?? Math.round(Math.min(W, H) * PERSP_FRAC);
  return (
    <StageContext.Provider value={{cam, persp: P}}>
      <div style={{position: 'absolute', inset: 0, perspective: `${P}px`, perspectiveOrigin: '50% 50%',
        transformStyle: 'preserve-3d', pointerEvents: 'none'}}>
        <div style={{position: 'absolute', left: '50%', top: '50%', width: 0, height: 0,
          transformStyle: 'preserve-3d', transform: css(inverseOf(cam))}}>
          {children}
        </div>
      </div>
    </StageContext.Provider>
  );
};

/** One posed surface on the stage. Sized in px and centred on its own origin, so `projectPose` with the same
 *  pose lands on the middle of what you see. */
export const Surface: React.FC<{pose: Pose; w: number; h: number; style?: React.CSSProperties;
  children?: React.ReactNode}> = ({pose, w, h, style, children}) => (
  <div style={{position: 'absolute', left: -w / 2, top: -h / 2, width: w, height: h,
    transformStyle: 'preserve-3d', backfaceVisibility: 'hidden', transform: css(matrixOf(pose)),
    ...style}}>{children}</div>
);

/** The lighting a face gets from the way it is turned — the peer library's `cube-navigation` shades each
 *  face live by its normal, which is what stops a CSS cube reading as six flat rectangles. Lambert against a
 *  key from the front and slightly above, clamped so a face turned away still reads as a surface rather than
 *  a hole. */
export const faceShade = (pose: Pose, cam: Pose, floor = 0.34): number => {
  const m = mul(inverseOf(cam), matrixOf(pose));
  // the surface normal is the third column of the rotation part, pointing out of the face
  const nx = m[8], ny = m[9], nz = m[10];
  const len = Math.hypot(nx, ny, nz) || 1;
  const key = [0, -0.35, 1];                         // from the front, a little above (+y is DOWN here)
  const kl = Math.hypot(key[0], key[1], key[2]);
  const d = (nx * key[0] + ny * key[1] + nz * key[2]) / (len * kl);
  return floor + (1 - floor) * Math.max(0, d);
};
