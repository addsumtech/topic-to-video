// THE WORLD STAGE'S MATHS — pure functions of the run's state and a frame, kept out of React so tests can hold them
// under node (tests/test_world_stage.py) and so the component is only drawing.
//
// THE MODEL. A world is a set of named OBJECTS at places in one space (world units: 1 = the frame's short side), and a
// CAMERA that looks at it. The convention is runtime/stage3d's — +x right, +y DOWN, +z toward the viewer, and the
// camera is the inverse of its own pose — written as an EYE (where the lens is) and two turns (yaw, pitch), because a
// camera that tilts must pivot at the lens, and a stage3d Pose pivots at a point a perspective-distance in front of it.
//
// EVERY OBJECT IS A PLANE THAT FACES THE LENS (a multiplane camera, the way Disney's and the Eames' films were shot).
// That is what keeps the whole world in the 2D paint path: a plane parallel to the image plane projects to an exact
// scale and translate — no perspective residual for an affine to miss (stage3d `planeAffine` is exact here, not
// approximate) — so a photograph, a vector shape and a word are each painted at their final size every frame, never
// rasterised once and scaled by the compositor (runtime/depth measured that at 91 → 56 glyph edge strength). Depth is
// still real: each plane sits at its own distance, so a camera that travels gives every plane its own parallax.
//
// THE CAMERA MOVES. A keyframe frames a named object; the move INTO it is one of:
//   dolly       the lens travels in a straight line to its new place (parallax by depth is real)
//   crane       the lens rises or falls (or slides) at the distance it already had: the framed thing keeps its size
//   tilt        the lens stays where it is and turns to look at the thing (a pure turn: no parallax, as in a real tilt)
//   orbit       the lens swings round the framed thing on an arc (yaw/pitch say where round it), its distance eased
//   scale-zoom  POWERS OF TEN: an exponential zoom about the one point that stays still on screen, at a constant
//               perceived speed, through objects nested one inside the next (`in`); each passes the screen and gives
//               way to the next — see `nestFade`
// Every keyframe's camera move is a DISPLACEMENT along its own path, summed the way runtime/stageRun springSum sums
// keyframe changes: a move that begins before the last has landed carries its speed on, and the camera lands exactly
// on the last keyframe's framing when every move has arrived.
import {feelShare} from '../runtime/stageRun';

export const D2R = Math.PI / 180;
export type V3 = [number, number, number];

/** A camera: the lens's place (world px), its yaw and pitch (radians; +yaw swings the view round to the left, +pitch
 *  looks DOWN — +y is down) and `fd`, the distance it is focused at (px along its view axis). */
export type Cam = {e: V3; yaw: number; pitch: number; fd: number};

export type ObjSpec = {
  kind?: string; at?: number[]; w?: number; h?: number; aspect?: number; imageAspect?: number; imageW?: number;
  in?: string; uv?: number[]; span?: number; dz?: number; on?: number; [k: string]: unknown;
};
/** An object laid out in the world: its centre, its size (world px), how deep in a nest it sits. */
export type Placed = {id: string; x: number; y: number; z: number; w: number; h: number; level: number; order: number;
  parent: string | null; spec: ObjSpec};

const finite = (v: unknown): v is number => typeof v === 'number' && isFinite(v);

/** Where every object of the world stands, in world px (U = the frame's short side). A nested object (`in`) is placed
 *  inside its parent: `uv` its centre on the parent's face (0..1), `span` its width as a share of the parent's, `dz`
 *  how far in front of the parent's plane it sits, in its own widths (0: on it). Throws on what cannot be laid out —
 *  a parent that is not an object, a nest that loops, a size that is not a positive number — naming the object. */
export const layoutWorld = (objects: Record<string, ObjSpec>, U: number, where = 'WorldStage'): Map<string, Placed> => {
  const out = new Map<string, Placed>();
  const ids = Object.keys(objects);
  const visiting = new Set<string>();
  const place = (id: string): Placed => {
    const got = out.get(id);
    if (got) return got;
    const o = objects[id];
    if (!o || typeof o !== 'object') throw new Error(`${where}: there is no object "${id}" in the world (objects: ${ids.join(', ') || 'none'})`);
    if (visiting.has(id)) throw new Error(`${where}: object "${id}" is nested inside itself (${[...visiting].join(' → ')} → ${id})`);
    visiting.add(id);
    const asp = finite(o.aspect) && o.aspect > 0 ? o.aspect
      : finite(o.imageAspect) && o.imageAspect > 0 ? o.imageAspect
      : finite(o.h) && o.h > 0 && finite(o.w) && o.w > 0 ? o.w / o.h : 1;
    let p: Placed;
    if (typeof o.in === 'string') {
      const par = place(o.in);
      const span = o.span;
      if (!finite(span) || span <= 0 || span >= 1) {
        throw new Error(`${where}: object "${id}" is nested in "${o.in}" with span ${JSON.stringify(span)} — a nested ` +
          'object is SMALLER than its parent: span is its width as a share of the parent\'s, between 0 and 1');
      }
      const uv = Array.isArray(o.uv) && o.uv.length === 2 && o.uv.every(finite) ? o.uv : [0.5, 0.5];
      const w = par.w * span;
      p = {id, x: par.x + (uv[0] - 0.5) * par.w, y: par.y + (uv[1] - 0.5) * par.h,
        z: par.z + (finite(o.dz) ? o.dz : 0) * w, w, h: w / asp, level: par.level + 1, order: ids.indexOf(id),
        parent: o.in, spec: o};
    } else {
      const at = o.at;
      if (!Array.isArray(at) || at.length !== 3 || !at.every(finite)) {
        throw new Error(`${where}: object "${id}" needs \`at\`: [x, y, z] in world units (1 = the frame's short side), ` +
          `or \`in\` a parent — got ${JSON.stringify(at)}`);
      }
      // a word's box comes from its size and its words (WorldStage measures the ink; this is what it culls and frames by)
      const isType = o.kind === 'type';
      const size = finite(o.size) && (o.size as number) > 0 ? (o.size as number) : 0.08;
      const tw = isType ? size * Math.max(1, [...String(o.text ?? '')].length) * 0.9 : NaN;
      if (!isType && (!finite(o.w) || o.w <= 0)) {
        throw new Error(`${where}: object "${id}" needs a width \`w\` > 0 (world units), got ${JSON.stringify(o.w)}`);
      }
      const w = (isType ? tw : (o.w as number)) * U;
      p = {id, x: at[0] * U, y: at[1] * U, z: at[2] * U, w, h: isType ? size * 1.2 * U : w / asp, level: 0,
        order: ids.indexOf(id), parent: null, spec: o};
    }
    visiting.delete(id);
    out.set(id, p);
    return p;
  };
  ids.forEach(place);
  return out;
};

/** The chain of parents above an object, nearest first. */
export const ancestors = (lay: Map<string, Placed>, id: string): string[] => {
  const out: string[] = [];
  for (let p = lay.get(id)?.parent; p; p = lay.get(p)?.parent ?? null) out.push(p);
  return out;
};

// ── the lens ────────────────────────────────────────────────────────────────────────────────────────────────────
/** camera space → world: R = Ry(yaw) · Rx(pitch) */
const rot = (v: V3, yaw: number, pitch: number): V3 => {
  const [x, y, z] = v;
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const y1 = y * cp - z * sp, z1 = y * sp + z * cp;
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  return [x * cy + z1 * sy, y1, -x * sy + z1 * cy];
};
/** world → camera space: Rᵀ */
const unrot = (v: V3, yaw: number, pitch: number): V3 => {
  const [x, y, z] = v;
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const x1 = x * cy - z * sy, z1 = x * sy + z * cy;
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  return [x1, y * cp + z1 * sp, -y * sp + z1 * cp];
};
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const scl = (a: V3, k: number): V3 => [a[0] * k, a[1] * k, a[2] * k];
const len = (a: V3) => Math.hypot(a[0], a[1], a[2]);

export type View = {W: number; H: number; P: number};
/** Where a world point lands: screen px, the scale there (px per world px) and its depth; `behind` when it is at or
 *  behind the lens (nothing is drawn rather than a value with a sign flip in it). */
export const project = (cam: Cam, v: View, p: V3): {x: number; y: number; k: number; depth: number; behind: boolean} => {
  const q = unrot(sub(p, cam.e), cam.yaw, cam.pitch);
  const depth = -q[2];
  // RELATIVE, not absolute: a powers-of-ten zoom legitimately puts the lens a few px from a plane whose objects are a
  // few px wide; only a point at or behind the lens has no projection
  if (!(depth > v.P * 1e-9)) return {x: v.W / 2, y: v.H / 2, k: 0, depth, behind: true};
  const k = v.P / depth;
  return {x: v.W / 2 + q[0] * k, y: v.H / 2 + q[1] * k, k, depth, behind: false};
};

export type Zone = {x0: number; y0: number; x1: number; y1: number};
export type Framing = {frame?: string; fill?: number; offset?: number[]; yaw?: number; pitch?: number; move?: string;
  fit?: 'contain' | 'cover'};

/** The framing a keyframe asks for. A keyframe that names a NEW `frame` frames it its own way: its `fill`, `fit` and
 *  `offset` are its own (or the defaults) — merged from the state, the last framing's `fill: 0.13` made a cover zoom
 *  stop at a thirteenth of its size. The lens's TURN (yaw, pitch) carries on from the state unless it says otherwise:
 *  a dolly after an orbit keeps the angle the orbit reached. A keyframe that names no frame adjusts the held one (a
 *  push in is `{"fill": 0.8}`). */
export const framingOf = (merged: Framing, own: Framing | null): Framing => {
  if (!own || typeof own.frame !== 'string') return merged;
  const {fill: _f, fit: _t, offset: _o, ...held} = merged;
  return {...held, ...own};
};

const centreOf = (o: Placed): V3 => [o.x, o.y, o.z];
/** Where on screen a framing puts its object: the zone's centre, moved by `offset` (shares of the zone). */
const aimAt = (zone: Zone, f: Framing) => {
  const off = Array.isArray(f.offset) && f.offset.length === 2 && f.offset.every(finite) ? f.offset : [0, 0];
  return {x: (zone.x0 + zone.x1) / 2 + off[0] * (zone.x1 - zone.x0), y: (zone.y0 + zone.y1) / 2 + off[1] * (zone.y1 - zone.y0)};
};

/** The camera that looks at object `o` from the direction (yaw, pitch) at distance `dist`, with the object landing on
 *  screen point S. */
const camAt = (o: Placed, v: View, S: {x: number; y: number}, yaw: number, pitch: number, dist: number): Cam => {
  const k = v.P / dist;
  const q: V3 = [(S.x - v.W / 2) / k, (S.y - v.H / 2) / k, -dist];
  return {e: sub(centreOf(o), rot(q, yaw, pitch)), yaw, pitch, fd: dist};
};

/** The fill a framing asks for when it says none: the framed thing takes about 60% of the zone. */
export const DEFAULT_FILL = 0.6;

/** The camera a keyframe asks for. `prev` is the camera of the keyframe before (a crane keeps its distance, a tilt
 *  its lens). Throws when the framing names nothing in the world. */
export const targetCam = (f: Framing, lay: Map<string, Placed>, v: View, zone: Zone, prev: Cam | null,
  where = 'WorldStage'): Cam => {
  if (typeof f.frame !== 'string' || !f.frame) {
    throw new Error(`${where}: the camera frames nothing — give it {"frame": "<object id>"} (objects: ${[...lay.keys()].join(', ')})`);
  }
  const o = lay.get(f.frame);
  if (!o) {
    throw new Error(`${where}: the camera frames "${f.frame}", which is not an object of the world (objects: ` +
      `${[...lay.keys()].join(', ') || 'none'})`);
  }
  // `cover`: the thing fills the whole FRAME (a photograph that is the picture), centred on the frame; `contain` (the
  // default): it fits the content zone, between the title and the caption band
  const cover = f.fit === 'cover';
  const S = cover ? {x: v.W / 2 + (Array.isArray(f.offset) && finite(f.offset[0]) ? f.offset[0] * v.W : 0),
    y: v.H / 2 + (Array.isArray(f.offset) && finite(f.offset[1]) ? f.offset[1] * v.H : 0)} : aimAt(zone, f);
  const fill = finite(f.fill) && f.fill > 0 ? f.fill : cover ? 1 : DEFAULT_FILL;
  const zw = zone.x1 - zone.x0, zh = zone.y1 - zone.y0;
  const yaw = finite(f.yaw) ? f.yaw * D2R : 0;
  // authored pitch is positive UP (the intuitive sign); the lens's own pitch is positive down, as +y is
  const pitch = finite(f.pitch) ? -f.pitch * D2R : 0;
  const kind = f.move ?? 'dolly';
  if (kind === 'tilt' && prev) {
    // keep the lens; turn it so the object lands on S
    const d = sub(centreOf(o), prev.e);
    const dl = len(d);
    if (!(dl > 1e-6)) throw new Error(`${where}: a tilt toward "${f.frame}" from a lens standing on it`);
    const dn = scl(d, 1 / dl);
    const a = (S.x - v.W / 2) / v.P, b = (S.y - v.H / 2) / v.P;
    const un = Math.hypot(a, b, 1);
    const u: V3 = [a / un, b / un, -1 / un];
    // pitch first (y), then yaw (the xz turn)
    const c = -u[2], rho = Math.hypot(u[1], c), alpha = Math.atan2(u[1], c);
    const th = Math.asin(Math.max(-1, Math.min(1, dn[1] / rho))) - alpha;
    const vx = u[0], vz = u[1] * Math.sin(th) + u[2] * Math.cos(th);
    let ph = Math.atan2(dn[0], dn[2]) - Math.atan2(vx, vz);
    ph = prev.yaw + wrap(ph - prev.yaw);
    const q = unrot(d, ph, th);
    return {e: prev.e, yaw: ph, pitch: th, fd: -q[2]};
  }
  if (kind === 'crane' && prev) {
    // keep the distance the lens already had to the object's plane, and its turn
    const q = unrot(sub(centreOf(o), prev.e), prev.yaw, prev.pitch);
    const dist = Math.max(v.P * 0.05, -q[2]);
    return camAt(o, v, S, prev.yaw, prev.pitch, dist);
  }
  const k = cover ? fill * Math.max(v.W / Math.max(1e-6, o.w), v.H / Math.max(1e-6, o.h))
    : fill * Math.min(zw / Math.max(1e-6, o.w), zh / Math.max(1e-6, o.h));
  if (kind === 'scale-zoom' && prev) {
    // a zoom keeps the lens's turn: only its scale and its place across the plane change
    return camAt(o, v, S, prev.yaw, prev.pitch, v.P / k);
  }
  return camAt(o, v, S, yaw, pitch, v.P / k);
};

const wrap = (a: number) => Math.atan2(Math.sin(a), Math.cos(a));

/** The camera part-way along a move of kind `kind` from A to B (s: 0..1 along the path). */
export const pathCam = (kind: string, A: Cam, B: Cam, s: number, centre: V3 | null): Cam => {
  if (s <= 0) return A;
  if (s >= 1) return B;
  const lerp = (a: number, b: number) => a + (b - a) * s;
  if (kind === 'orbit' && centre) {
    const ra = sub(A.e, centre), rb = sub(B.e, centre);
    const la = len(ra), lb = len(rb);
    if (la > 1e-6 && lb > 1e-6) {
      // the lens's direction from the centre, as yaw/pitch of a vector, interpolated round the arc
      const ya = Math.atan2(ra[0], ra[2]), yb = ya + wrap(Math.atan2(rb[0], rb[2]) - ya);
      const pa = Math.asin(Math.max(-1, Math.min(1, ra[1] / la))), pb = Math.asin(Math.max(-1, Math.min(1, rb[1] / lb)));
      const yy = lerp(ya, yb), pp = lerp(pa, pb), rr = Math.exp(lerp(Math.log(la), Math.log(lb)));
      const dir: V3 = [Math.cos(pp) * Math.sin(yy), Math.sin(pp), Math.cos(pp) * Math.cos(yy)];
      return {e: add(centre, scl(dir, rr)), yaw: lerp(A.yaw, A.yaw + wrap(B.yaw - A.yaw)), pitch: lerp(A.pitch, B.pitch),
        fd: Math.exp(lerp(Math.log(A.fd), Math.log(B.fd)))};
    }
  }
  if (kind === 'scale-zoom' && centre) {
    // POWERS OF TEN: in the lens's own frame (A's turn — a zoom does not turn), the plane of the target is a flat
    // map at depth zp; the screen scale k runs EXPONENTIALLY from A's to B's, and the lens slides across the plane so
    // the one point that lands on the same screen place in both framings (the zoom's fixed point) stays there.
    const ea = unrot(A.e, A.yaw, A.pitch), eb = unrot(B.e, A.yaw, A.pitch), c = unrot(centre, A.yaw, A.pitch);
    const da = ea[2] - c[2], db = eb[2] - c[2];
    if (da > 1e-9 && db > 1e-9) {
      const ka = 1 / da, kb = 1 / db;                         // scale up to the constant P: only ratios matter
      const k = Math.exp(lerp(Math.log(ka), Math.log(kb)));
      let ex: number, ey: number;
      if (Math.abs(ka - kb) / Math.max(ka, kb) < 1e-6) {
        ex = lerp(ea[0], eb[0]); ey = lerp(ea[1], eb[1]);
      } else {
        const Fx = (ka * ea[0] - kb * eb[0]) / (ka - kb), Fy = (ka * ea[1] - kb * eb[1]) / (ka - kb);
        ex = Fx - (ka / k) * (Fx - ea[0]); ey = Fy - (ka / k) * (Fy - ea[1]);
      }
      const e = rot([ex, ey, c[2] + 1 / k], A.yaw, A.pitch);
      return {e, yaw: A.yaw, pitch: A.pitch, fd: Math.exp(lerp(Math.log(A.fd), Math.log(B.fd)))};
    }
  }
  // dolly, crane, tilt: the lens's place and turn in straight lines (a tilt's place does not move)
  return {e: [lerp(A.e[0], B.e[0]), lerp(A.e[1], B.e[1]), lerp(A.e[2], B.e[2])],
    yaw: lerp(A.yaw, A.yaw + wrap(B.yaw - A.yaw)), pitch: lerp(A.pitch, B.pitch),
    fd: Math.exp(lerp(Math.log(Math.max(1e-6, A.fd)), Math.log(Math.max(1e-6, B.fd))))};
};

/** The share of a scale-zoom at u (0..1 of its frames): it gathers speed over the first fifth, CRUISES — a constant
 *  rate of zoom, which is what makes the scales read as one journey — and settles over the last quarter. Velocity is
 *  continuous and zero at both ends, and it lands exactly on 1. */
export const cruise = (u: number, ein = 0.2, eout = 0.25): number => {
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  const vmax = 1 / (1 - ein / 2 - eout / 2);
  if (u < ein) return vmax * (u * u) / (2 * ein);
  const s1 = vmax * ein / 2;
  if (u <= 1 - eout) return s1 + vmax * (u - ein);
  const r = 1 - u;
  return 1 - vmax * (r * r) / (2 * eout);
};

export type CamKey = {from: number; to: number; kind: string; target: Cam; centre: V3 | null};

/** The camera at frame f: the first keyframe's framing plus every later keyframe's move along its own path, each
 *  sprung from its own start (runtime/stageRun springSum's model, on paths): a move that starts before the last has
 *  landed carries its speed on, and once every move has arrived the camera IS the last keyframe's framing. */
export const camAtFrame = (keys: CamKey[], f: number, fps: number, reduced: boolean): Cam => {
  if (!keys.length) throw new Error('WorldStage: no camera keyframe');
  let acc: Cam = {e: [...keys[0].target.e] as V3, yaw: keys[0].target.yaw, pitch: keys[0].target.pitch, fd: keys[0].target.fd};
  for (let i = 1; i < keys.length; i++) {
    const kf = keys[i], A = keys[i - 1].target, B = kf.target;
    if (f < kf.from) break;
    const d = Math.max(1, kf.to - kf.from);
    const s = reduced ? 1 : kf.kind === 'scale-zoom' ? cruise((f - kf.from) / d) : feelShare(f - kf.from, d, fps, 'glide');
    if (s <= 0) continue;
    const P = pathCam(kf.kind, A, B, s, kf.centre);
    acc = {e: add(acc.e, sub(P.e, A.e)), yaw: acc.yaw + (P.yaw - A.yaw), pitch: acc.pitch + (P.pitch - A.pitch),
      fd: acc.fd * (P.fd / Math.max(1e-9, A.fd))};
  }
  return acc;
};

// ── what the lens does to what it sees ──────────────────────────────────────────────────────────────────────────
/** How defocused a plane at `depth` is when the lens is focused at `fd`: 0 in focus, rising to 1 at twice (or half)
 *  the distance — the circle of confusion of a thin lens grows with |1 − fd/depth|. */
export const defocus = (depth: number, fd: number): number =>
  depth > 0 && fd > 0 ? Math.min(1, Math.abs(1 - fd / depth)) : 0;

/** How present an object is as it PASSES the screen: a plane the lens has come so close to that it is several frames
 *  across is no longer a picture of anything (a vector stroke is a wall of colour, a photograph its own pixels) — it
 *  gives way between `lo` and `hi` frame-diagonals, as the Eames' layers dissolve as they pass. */
export const passFade = (projW: number, projH: number, W: number, H: number, lo = 3, hi = 6): number => {
  const d = Math.hypot(W, H), r = Math.max(projW, projH) / d;
  const t = Math.max(0, Math.min(1, (r - lo) / Math.max(1e-6, hi - lo)));
  return 1 - t * t * (3 - 2 * t);
};

/** How present a NESTED object is from how large it is on screen — the scale-zoom's hand-over. A nest's child is
 *  the NEXT scale: it is not shown while the camera holds on the scale around it (a picture inside a picture reads
 *  as a collage), and it arrives as the zoom carries it toward the frame — fading in between 30% and 65% of the
 *  zone's width — while a parent leaves once a child it holds covers the frame. 1 for an object that is not nested. */
export const nestFade = (projW: number, zoneW: number, level: number): number => {
  if (level <= 0) return 1;
  const r = projW / Math.max(1, zoneW);
  const t = Math.max(0, Math.min(1, (r - 0.3) / 0.35));
  return t * t * (3 - 2 * t);
};
