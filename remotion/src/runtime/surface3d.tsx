// SURFACE3D — ONE lens for every surface a 2D shot poses in space, and everything ON a surface drawn INSIDE it.
//
// WHY (a Grok Bot film, 2026-11-01). Its slab shots drew a slab in CSS 3D and laid each block of content over it with
// a 2D affine: an affine keeps parallel lines parallel, so the slab converged toward its vanishing point while the
// window on it stayed a flat parallelogram — the viewer saw inner frames "not following the carrier's angle". Here a
// surface is ONE element posed by rotateX/rotateY under the shot's ONE perspective; its content is its DOM children,
// so a window, a field, a button and the type on them share the surface's exact angle and vanishing point by
// construction. `project` is the same projection in numbers, for things that only ATTACH from outside.
//
// THICKNESS IS PAINTED IN THE FACE'S PLANE, never stacked translateZ layers: ~2 px apart in a preserve-3d context,
// Chrome re-sorted them over the face for ONE frame whenever the face's content changed — near-black flashes the
// user saw and no gate did (scripts/flash_qa.py now does).
//
// A PHONE is the runtime `Device` (a deviceSpec.json model): `PhoneSlab` poses it like any surface, its side wall the
// case outline repeated in-plane. Never hand-draw a device (scripts/device_fidelity_qa.py hand_drawn_device).
import React from 'react';
import {Device, deviceGeometry, roundRectPath, type DeviceGeom, type Rect} from './device';
import spec from './deviceSpec.json';
import {useGlide} from './glide';

/** The shot's one lens: CSS `perspective` P (px) from the eye, its vanishing point at (vx, vy) on the frame. */
export type Cam = {P: number; vx: number; vy: number};
/** A surface in space: its centre (frame px, z toward the viewer), its size, its turn (radians, CSS order
 *  `rotateX(rx) rotateY(ry)`). Its LOCAL px run from its top-left corner, like any DOM box. */
export type Pose = {cx: number; cy: number; z?: number; w: number; h: number; rx: number; ry: number};

/** A local point (px from the surface's top-left, `lz` toward the viewer) in the world, before the lens. */
export const toWorld = (S: Pose, lx: number, ly: number, lz = 0): [number, number, number] => {
  const x = lx - S.w / 2, y = ly - S.h / 2;
  const c1 = Math.cos(S.ry), s1 = Math.sin(S.ry), c2 = Math.cos(S.rx), s2 = Math.sin(S.rx);
  const x1 = x * c1 + lz * s1, z1 = -x * s1 + lz * c1;          // rotateY
  const y2 = y * c2 - z1 * s2, z2 = y * s2 + z1 * c2;           // rotateX
  return [S.cx + x1, S.cy + y2, (S.z ?? 0) + z2];
};
/** Where a local point of a surface lands on the frame — the projection CSS itself applies. */
export const project = (cam: Cam, S: Pose, lx: number, ly: number, lz = 0): {x: number; y: number} => {
  const [X, Y, Z] = toWorld(S, lx, ly, lz);
  if (!(cam.P - Z > 1)) throw new Error(`surface3d: a point at z=${Z.toFixed(0)} is at or behind the eye (P=${cam.P})`);
  const k = cam.P / (cam.P - Z);
  return {x: cam.vx + (X - cam.vx) * k, y: cam.vy + (Y - cam.vy) * k};
};

/** The CSS transform that poses a w x h element (left 0, top 0, transform-origin at its centre). */
export const poseTransform = (S: Pose): string =>
  `translate3d(${S.cx - S.w / 2}px, ${S.cy - S.h / 2}px, ${S.z ?? 0}px) rotateX(${S.rx}rad) rotateY(${S.ry}rad)`;

/** The lens: a full-frame layer whose children are posed in 3D under it. Every View of a shot takes the SAME cam,
 *  so separate objects (each in its own View, for its own opacity) still share one vanishing point. */
export const View: React.FC<{cam: Cam; opacity?: number; children?: React.ReactNode}> = ({cam, opacity = 1, children}) => (
  <div style={{position: 'absolute', inset: 0, perspective: `${cam.P}px`, perspectiveOrigin: `${cam.vx}px ${cam.vy}px`,
    opacity}}>{children}</div>
);

/** A posed element whose children lie on its plane (type included: it is held on the baseline unlock for the whole
 *  beat — its transform is a turn under a lens). `preserve` keeps 3D for children that stand off the plane. */
export const OnPlane: React.FC<{S: Pose; style?: React.CSSProperties; preserve?: boolean; children?: React.ReactNode}> =
  ({S, style, preserve = false, children}) => {
    const glide = useGlide();
    return (
      <div style={{position: 'absolute', left: 0, top: 0, width: S.w, height: S.h, transformOrigin: `${S.w / 2}px ${S.h / 2}px`,
        transform: glide(poseTransform(S), true), transformStyle: preserve ? 'preserve-3d' : undefined, ...style}}>
        {children}
      </div>
    );
  };

/** A slab: a face with a real thickness `T` (its outline swept back in 3D, `edge` coloured), the face's content its
 *  children — laid out in the face's own px, top-left origin. */
export const Slab: React.FC<{S: Pose; radius: number; T: number; face: string; edge: string; layers?: number;
  faceStyle?: React.CSSProperties; children?: React.ReactNode}> = ({S, radius, T, face, edge, faceStyle, children}) => (
  // ONE plane. The thickness is the face's own solid offset shadow, painted WITH the face. It used to be `layers`
  // stacked divs pushed back by translateZ inside a preserve-3d context, all within ~2 px of the face's depth:
  // when the face's content changed (a field starting to fill, beat 26) Chrome re-sorted the near-coplanar layers
  // and for one frame an edge layer landed IN FRONT of the face — a near-black flash (frames 3222, 3273).
  <OnPlane S={S} style={{borderRadius: radius,
    boxShadow: `0 ${T * 0.55}px 0 0 ${edge}, 0 ${T * 0.55 + 1}px 0 0 rgba(0,0,0,0.25)`}}>
    <div style={{position: 'absolute', inset: 0, borderRadius: radius, background: face, overflow: 'hidden',
      ...faceStyle}}>{children}</div>
  </OnPlane>
);

// ── THE PHONE ──────────────────────────────────────────────────────────────────────────────────────────────────
const MODELS = spec.models as unknown as Record<string, {kind: string; published: {caseMm: number[]}}>;

/** The runtime geometry of a real phone model (the 'real' look), scaled by `k` from the size deviceGeometry gives it
 *  in this frame and moved so its FACE's top-left is (0, 0): every part keeps its published proportion and the case
 *  stays concentric with the screen (both radii scale together). */
export const phoneGeom = (W: number, H: number, model: string, k: number): DeviceGeom => {
  if (!(k > 0 && k <= 1.2)) throw new Error(`surface3d: phone scale ${k} out of 0..1.2`);
  const g = deviceGeometry('phone', 'real', W, H, 'center', false, model);
  const ox = g.face.x, oy = g.face.y;
  const r = (q: Rect): Rect => ({x: (q.x - ox) * k, y: (q.y - oy) * k, w: q.w * k, h: q.h * k});
  const rn = (q: Rect | null) => (q ? r(q) : null);
  return {...g, body: r(g.body), face: r(g.face), screen: r(g.screen), bezel: g.bezel * k,
    bezels: {l: g.bezels.l * k, r: g.bezels.r * k, t: g.bezels.t * k, b: g.bezels.b * k},
    radius: g.radius * k, outerRadius: (g.radius + g.bezel) * k, island: rn(g.island), notch: rn(g.notch),
    base: rn(g.base), strip: rn(g.strip), bands: g.bands.map(r), crown: rn(g.crown), sideButton: rn(g.sideButton),
    buttons: g.buttons.map(r)};
};

/** Where content may go on a phone's screen, in screen px: below the status bar and Dynamic Island, above the home
 *  indicator, clear of the corner radius at the sides. design: iOS's safe-area insets on a 6.3-inch iPhone are
 *  about 15% of the screen's width at the top and 8.5% at the bottom; the side margin is the HIG's 16 pt (4%). */
export const phoneSafe = (g: DeviceGeom): {top: number; bottom: number; side: number} => {
  const sw = g.screen.w;
  const islandBottom = g.island ? g.island.y + g.island.h - g.screen.y : 0;
  return {top: Math.max(sw * 0.154, islandBottom + sw * 0.04), bottom: sw * 0.085, side: sw * 0.045};
};

/** The phone posed in space: the runtime Device on the pose's plane, its case depth (deviceSpec caseMm[2]) swept back
 *  behind it as the metal side wall. `S.w/S.h` must be the geometry's face. Screen content is the children, laid out
 *  in SCREEN px (0,0 = the screen's top-left). */
export const PhoneSlab: React.FC<{S: Pose; g: DeviceGeom; children?: React.ReactNode}> = ({S, g, children}) => {
  const m = g.model ? MODELS[g.model] : null;
  if (!m) throw new Error(`surface3d: PhoneSlab needs a model's geometry (got ${g.model})`);
  if (Math.abs(S.w - g.face.w) > 0.5 || Math.abs(S.h - g.face.h) > 0.5) {
    throw new Error(`surface3d: the pose (${S.w}x${S.h}) is not the phone's face (${g.face.w}x${g.face.h})`);
  }
  const [cw, , depthMm] = m.published.caseMm;
  const T = (depthMm / cw) * g.face.w;
  const n = Math.max(8, Math.ceil(T / 2.5));
  const outline = roundRectPath(0, 0, g.face.w, g.face.h, g.outerRadius, true, false);
  // ONE plane: the side wall is the outline repeated in the face's own plane, stepped down toward the back, so it is
  // painted with the face and can never sort in front of it. Stacked translateZ copies ~2.5 px apart inside a
  // preserve-3d context let Chrome re-sort them over the face when the face's content changed (Slab's flash, beat 26).
  const drop = T * 0.55;
  return (
    <OnPlane S={S}>
      <svg width={g.face.w} height={g.face.h} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {Array.from({length: n}, (_, i) => {
          const f = i / n;                     // 0 = the back, toward 1 = just behind the face
          // the side wall: brushed metal, darker toward the back, a polished band where it meets the glass
          const col = f > 0.86 ? '#c9ccd1' : f < 0.12 ? '#2c2f34' : '#7d828a';
          return <path key={i} d={outline} fill={col} transform={`translate(0 ${drop * (1 - f)})`} />;
        })}
      </svg>
      <div style={{position: 'absolute', left: 0, top: 0, width: g.face.w, height: g.face.h}}>
        <Device g={g} dna={null}>{children}</Device>
      </div>
    </OnPlane>
  );
};
