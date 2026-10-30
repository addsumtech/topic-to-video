// A LAPTOP IS ONE 3D OBJECT. The lid and the base meet at the hinge and are seen by ONE camera: every point of the
// machine — the deck, its keys, the trackpad, the chamfered edge and thumb scoop, the hinge, the lid's edge, the
// bezel and the screen ON it — is a point in millimetres, carried through the same turn, the same pitch and the
// same perspective, so turning the laptop turns all of it, its screen content included (laptopScreenTransform puts
// the screen's own DOM on the lid's projected rectangle, a homography — never a flat picture tilted).
//
// THE DEFECT THIS EXISTS FOR (2026-10-30). The kit drew a laptop as a front-on lid over a trapezoid sliver of base,
// and a film turned that whole picture in 3D toward a watch: the lid's top edge slanted while the base stayed a
// flat horizontal line — two cameras on one object — and the base had no deck, no keys, no trackpad, no scoop: it
// did not read as a MacBook. Every gate was green; the critic looked only at the watch.
//
// AT REST the camera looks down at `restPitchDeg` and the lid is opened to 90° + that pitch, so the lid faces the
// camera square: the screen and the face project onto EXACTLY deviceGeometry's rects (the legibility and fidelity
// gates keep judging those), and the deck lies below them, foreshortened, its front edge nearer and so wider.
// deviceSpec.json `parts.laptopBase` / `laptopOverhang` are that rest picture's extent (tests/test_device_laptop3d.py
// holds them to it). A turned pose (`yaw`, `pitch`, `open`) is the same machine seen from elsewhere.
//
// Every measurement is in deviceSpec.json `models.<laptop>.body3d`, each under `derived` (with how) or `design`.
import React from 'react';
import spec from './deviceSpec.json';
import type {DeviceGeom, Rect} from './device';

export type V3 = [number, number, number];
export type P2 = {x: number; y: number};
/** degrees. yaw: a turntable turn, positive swings the front of the machine to the right; pitch: how far the camera
 *  looks DOWN onto it; open: the lid's angle from the deck (90 = upright). Omitted: the rest pose. */
export type LaptopPose = {yaw?: number; pitch?: number; open?: number};

type Body3D = {lidMm: number; cornerMm: number; well: number[]; trackpad: number[]; scoopMm: number;
  grille: number[] | null; hingeInsetMm: number; rimMm: number};
type L3 = {restPitchDeg: number; cameraOfWidth: number; hinge: {liftMm: number; backMm: number};
  light: number[]; lidCornerBottomMm: number; keyGapMm: number; maxYaw: number; maxPitch: number};

const MODELS = spec.models as unknown as Record<string, {kind: string; published: {px: number[]; ppi: number;
  caseMm: number[]}; body3d?: Body3D}>;
const KINDS = spec.kinds as unknown as Record<string, {like: string}>;
export const L3D = (spec.parts as unknown as {laptop3d: L3}).laptop3d;

const rad = (d: number) => (d * Math.PI) / 180;
const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul = (a: V3, k: number): V3 => [a[0] * k, a[1] * k, a[2] * k];
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a: V3, b: V3): V3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a: V3): V3 => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

/** The machine in millimetres: the published case, the lid's face as deviceGeometry fitted it (so the lid IS the
 *  kit's face), and the deck's measured layout. */
export type LaptopDims = {W: number; D: number; T: number; lidT: number; baseT: number; kpx: number;
  face: {w: number; h: number}; screen: {x: number; v: number; w: number; h: number};
  lidTopR: number; body: Body3D};

export const laptopDims = (g: DeviceGeom): LaptopDims => {
  const name = g.model ?? KINDS.laptop.like;
  const m = MODELS[name];
  if (!m || m.kind !== 'laptop') throw new Error(`laptop3d: ${name} is not a laptop model`);
  if (!m.body3d) throw new Error(`laptop3d: ${name} has no body3d in deviceSpec.json — measure its deck first`);
  const [W, D, T] = m.published.caseMm;
  // px per mm: the lid's face is the published case width, drawn g.face.w wide
  const kpx = g.face.w / W;
  if (!(kpx > 0) || !isFinite(kpx)) throw new Error(`laptop3d: a face ${g.face.w} px wide cannot be drawn`);
  const lidT = m.body3d.lidMm;
  if (!(lidT > 0 && lidT < T)) throw new Error(`laptop3d: ${name} lid ${lidT} mm must be inside the case's ${T} mm`);
  const s = g.screen, f = g.face;
  return {W, D, T, lidT, baseT: T - lidT, kpx,
    face: {w: f.w / kpx, h: f.h / kpx},
    // the screen on the lid: x from the lid's centre line, v up from the lid's bottom edge
    screen: {x: (s.x + s.w / 2 - (f.x + f.w / 2)) / kpx, v: (f.y + f.h - (s.y + s.h)) / kpx, w: s.w / kpx, h: s.h / kpx},
    lidTopR: g.outerRadius / kpx, body: m.body3d};
};

export type LaptopCamera = {
  dims: LaptopDims; yaw: number; pitch: number; open: number;
  /** model (mm) -> camera space (mm, z toward the viewer) */
  cam: (p: V3) => V3;
  /** model (mm) -> frame px */
  project: (p: V3) => P2;
  /** a point on the lid's FRONT plane: x across, v up from the lid's bottom edge, `depth` behind the front */
  lid: (x: number, v: number, depth?: number) => V3;
  /** the lid's front-face normal, and the lid's up direction, in the model */
  N: V3; L: V3;
  /** the screen's four corners on the frame: top-left, top-right, bottom-right, bottom-left */
  screenQuad: P2[];
  /** how far up the lid its edge comes out of the base: below it the chin has dropped behind the hinge */
  vCut: number;
  atRest: boolean;
};

export const laptopCamera = (g: DeviceGeom, pose: LaptopPose = {}): LaptopCamera => {
  const dims = laptopDims(g);
  const pitch = pose.pitch ?? L3D.restPitchDeg;
  const yaw = pose.yaw ?? 0;
  const open = pose.open ?? 90 + L3D.restPitchDeg;
  if (Math.abs(yaw) > L3D.maxYaw) throw new Error(`laptop3d: yaw ${yaw}° is past ±${L3D.maxYaw}° — the drawing orders ` +
    'the deck before the lid, which holds only while the camera is in front of the machine');
  if (pitch < 0 || pitch > L3D.maxPitch) throw new Error(`laptop3d: pitch ${pitch}° outside 0..${L3D.maxPitch}°`);
  if (open < 70 || open > 140) throw new Error(`laptop3d: a lid open ${open}° is not how a laptop is used (70..140°)`);
  const th = rad(open);
  const L: V3 = [0, Math.sin(th), Math.cos(th)];
  const N: V3 = [0, -Math.cos(th), Math.sin(th)];
  const lid0: V3 = [0, L3D.hinge.liftMm, -L3D.hinge.backMm];
  const lid = (x: number, v: number, depth = 0): V3 => add(add(add(lid0, [x, 0, 0]), mul(L, v)), mul(N, -depth));
  const sc = dims.screen;
  const O = lid(sc.x, sc.v + sc.h / 2);
  const cp = Math.cos(rad(pitch)), sp = Math.sin(rad(pitch)), cy = Math.cos(rad(yaw)), sy = Math.sin(rad(yaw));
  const cam = (p: V3): V3 => {
    const q = sub(p, O);
    const x1 = q[0] * cy + q[2] * sy, z1 = -q[0] * sy + q[2] * cy, y1 = q[1];
    return [x1, y1 * cp - z1 * sp, y1 * sp + z1 * cp];
  };
  const dist = L3D.cameraOfWidth * dims.W;
  const k = dims.kpx;
  const cxp = g.screen.x + g.screen.w / 2, cyp = g.screen.y + g.screen.h / 2;
  const project = (p: V3): P2 => {
    const c = cam(p);
    const s = dist / (dist - c[2]);
    return {x: cxp + k * c[0] * s, y: cyp - k * c[1] * s};
  };
  const x0 = sc.x - sc.w / 2, x1 = sc.x + sc.w / 2, v0 = sc.v, v1 = sc.v + sc.h;
  const screenQuad = [lid(x0, v1), lid(x1, v1), lid(x1, v0), lid(x0, v0)].map(project);
  const vCut = Math.max(0, -lid0[1] / Math.max(1e-6, Math.sin(th)));
  const atRest = yaw === 0 && pitch === L3D.restPitchDeg && open === 90 + L3D.restPitchDeg;
  return {dims, yaw, pitch, open, cam, project, lid, N, L, screenQuad, vCut, atRest};
};

/** Solve the 8x8 system of a homography taking the four corners of a w x h box to `q` (TL, TR, BR, BL). */
const homography = (w: number, h: number, q: P2[]): number[] => {
  const src = [[0, 0], [w, 0], [w, h], [0, h]];
  const A: number[][] = [], b: number[] = [];
  src.forEach(([x, y], i) => {
    const {x: u, y: v} = q[i];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
  });
  const n = 8;
  for (let c = 0; c < n; c++) {
    let piv = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[piv][c])) piv = r;
    [A[c], A[piv]] = [A[piv], A[c]]; [b[c], b[piv]] = [b[piv], b[c]];
    if (Math.abs(A[c][c]) < 1e-12) throw new Error('laptop3d: the screen is seen edge-on — no picture to put on it');
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = A[r][c] / A[c][c];
      for (let k = c; k < n; k++) A[r][k] -= f * A[c][k];
      b[r] -= f * b[c];
    }
  }
  return b.map((v, i) => v / A[i][i]);
};

/** The CSS transform that lays the screen's DOM (a box at g.screen, transform-origin 0 0) onto the lid as this
 *  camera sees it. At rest it is nothing: the screen is exactly g.screen. */
export const laptopScreenTransform = (g: DeviceGeom, c: LaptopCamera): string | undefined => {
  const s = g.screen;
  const q = c.screenQuad.map((p) => ({x: p.x - s.x, y: p.y - s.y}));
  const rest = [[0, 0], [s.w, 0], [s.w, s.h], [0, s.h]];
  if (q.every((p, i) => Math.abs(p.x - rest[i][0]) < 0.02 && Math.abs(p.y - rest[i][1]) < 0.02)) return undefined;
  const [a, b, c0, d, e, f, gg, hh] = homography(s.w, s.h, q);
  const r = (v: number) => (Math.abs(v) < 1e-12 ? 0 : v);
  return `matrix3d(${[a, d, 0, gg, b, e, 0, hh, 0, 0, 1, 0, c0, f, 0, 1].map(r).join(',')})`;
};

/** The same, for a FRAME-sized layer (transform-origin 0 0) holding something drawn over the screen at g.screen —
 *  a glow copy, a sweep: it lands where the screen's content does. */
export const laptopScreenFrameTransform = (g: DeviceGeom, c: LaptopCamera): string | undefined => {
  const m = laptopScreenTransform(g, c);
  return m ? `translate(${g.screen.x}px, ${g.screen.y}px) ${m} translate(${-g.screen.x}px, ${-g.screen.y}px)` : undefined;
};

/** A rounded rectangle's outline as points, x0..x1 by y0..y1 (2D), corners `r` (top: y0 side) and `rb` (y1 side),
 *  clockwise from the top-left corner's start. */
const rrPts = (x0: number, y0: number, x1: number, y1: number, r: number, rb = r, n = 8): Array<[number, number]> => {
  const out: Array<[number, number]> = [];
  const arc = (cx: number, cy: number, rr: number, a0: number, a1: number) => {
    if (rr <= 0) { out.push([cx, cy]); return; }
    for (let i = 0; i <= n; i++) {
      const a = a0 + ((a1 - a0) * i) / n;
      out.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]);
    }
  };
  arc(x0 + r, y0 + r, r, Math.PI, 1.5 * Math.PI);
  arc(x1 - r, y0 + r, r, 1.5 * Math.PI, 2 * Math.PI);
  arc(x1 - rb, y1 - rb, rb, 0, 0.5 * Math.PI);
  arc(x0 + rb, y1 - rb, rb, 0.5 * Math.PI, Math.PI);
  return out;
};

const pts = (ps: P2[], ox: number, oy: number) => ps.map((p) => `${(p.x - ox).toFixed(2)},${(p.y - oy).toFixed(2)}`).join(' ');

/** Lambert shading of a face whose model normal is n, in camera space, under the one key light (upper left front). */
const lit = (c: LaptopCamera, n: V3): number => {
  const nc = norm(sub(c.cam(n), c.cam([0, 0, 0])));
  const l = norm(L3D.light as V3);
  return Math.max(0, dot(nc, l));
};

const hex = (h: string): number[] => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
const lerpC = (a: string, b: string, t: number): string => {
  const A = hex(a), B = hex(b), u = Math.max(0, Math.min(1, t));
  return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * u)).join(',')})`;
};

// ANSI layout in key units, row by row (the 2021-on MacBook Pro: a full-height function row, a Touch ID key, the
// inverted-T arrows). `l`: the legend; '' none. The arrows' middle unit is split in two half-height keys.
type K = [number, string];
const ROWS: K[][] = [
  [[1.5, 'esc'], ...Array.from({length: 12}, (_, i): K => [1, 'F' + (i + 1)]), [1, '']],
  [[1, '`'], ...'1234567890-='.split('').map((ch): K => [1, ch]), [1.5, 'delete']],
  [[1.5, 'tab'], ...'QWERTYUIOP[]'.split('').map((ch): K => [1, ch]), [1, '\\']],
  [[1.75, 'caps lock'], ...'ASDFGHJKL;\''.split('').map((ch): K => [1, ch]), [1.75, 'return']],
  [[2.25, 'shift'], ...'ZXCVBNM,./'.split('').map((ch): K => [1, ch]), [2.25, 'shift']],
  [[1, 'fn'], [1, 'control'], [1, 'option'], [1.25, 'command'], [5, ''], [1.25, 'command'], [1, 'option'],
    [1, '◀'], [1, '▲▼'], [1, '▶']],
];
const UNITS = 14.5;

export const LaptopBody: React.FC<{g: DeviceGeom; c: LaptopCamera; real: boolean; ink: string; bg: string;
  ox: number; oy: number; uid: string; metal: {hi: string; mid: string; lo: string; deep: string}}> =
  ({c, real, ink, bg, ox, oy, uid, metal}) => {
    const d = c.dims, b = d.body;
    const P = (p: V3) => c.project(p);
    const poly = (ps: V3[]) => pts(ps.map(P), ox, oy);
    const id = (n: string) => `lp${uid}${n}`;
    const W2 = d.W / 2, D = d.D, T = d.baseT;
    const tone = (t: number) => (real ? lerpC(metal.deep, metal.hi, t) : lerpC(ink, bg, 0.12 + 0.3 * t));
    const keyC = real ? '#17181b' : lerpC(ink, bg, 0.06);
    const wellC = real ? '#060708' : ink;
    const viewOK = (pt: V3, n: V3) => {
      const pc = c.cam(pt), nc = sub(c.cam(add(pt, n)), pc);
      const dist = L3D.cameraOfWidth * d.W;
      return dot(nc, sub([0, 0, dist], pc)) > 0;
    };
    const out: React.ReactNode[] = [];

    // ── the shadow on the ground under it ──
    const shadow = rrPts(-W2 - 4, -6, W2 + 4, D + 8, b.cornerMm + 4).map(([x, z]) => P([x, -T, z]));
    out.push(<polygon key="shadow" points={pts(shadow, ox, oy)} fill="#000" opacity={real ? 0.55 : 0.14}
      filter={`url(#${id('blur')})`} />);

    // ── the base: an extruded rounded rectangle, its walls lit by their normals, then its top ──
    const foot = rrPts(-W2, 0, W2, D, b.cornerMm, b.cornerMm, 10);
    const walls: Array<{z: number; node: React.ReactNode}> = [];
    for (let i = 0; i < foot.length; i++) {
      const [xa, za] = foot[i], [xb, zb] = foot[(i + 1) % foot.length];
      const n = norm([zb - za, 0, -(xb - xa)]);       // outward for a clockwise (x right, z toward the front) walk
      const mid: V3 = [(xa + xb) / 2, -T / 2, (za + zb) / 2];
      if (!viewOK(mid, n)) continue;
      const q = [[xa, 0, za], [xb, 0, zb], [xb, -T, zb], [xa, -T, za]] as V3[];
      walls.push({z: c.cam(mid)[2], node: <polygon key={'w' + i} points={poly(q)} fill={tone(0.28 + 0.62 * lit(c, n))}
        stroke={tone(0.28 + 0.62 * lit(c, n))} strokeWidth={0.6} />});
    }
    walls.sort((p, q) => p.z - q.z).forEach((w) => out.push(w.node));
    // the thumb scoop: a shallow recess cut down into the middle of the front edge
    const sw2 = b.scoopMm / 2;
    const scoop: V3[] = [];
    for (let i = 0; i <= 16; i++) { const x = -sw2 + (b.scoopMm * i) / 16; scoop.push([x, 0, D]); }
    for (let i = 16; i >= 0; i--) {
      const x = -sw2 + (b.scoopMm * i) / 16, u = (2 * x) / b.scoopMm;
      scoop.push([x, -T * 0.42 * Math.sqrt(Math.max(0, 1 - u * u)), D - 0.2]);
    }
    if (viewOK([0, -T / 2, D], [0, 0, 1])) {
      out.push(<polygon key="scoop" points={poly(scoop)} fill={`url(#${id('scoop')})`} />);
    }
    // the top: aluminium, lit, with a soft fall-off toward the front
    const topPts = foot.map(([x, z]) => P([x, 0, z]));
    out.push(<polygon key="top" points={pts(topPts, ox, oy)} fill={real ? `url(#${id('deck')})` : tone(0.75)} />);
    // the top's edge: the radius catches the key light along the front and the left
    const edgeFront = rrPts(-W2 + 0.3, 0.3, W2 - 0.3, D - 0.3, b.cornerMm, b.cornerMm, 10).map(([x, z]) => P([x, 0, z]));
    // rrPts walks TL, TR, BR, BL corners of 11 points each: from the BR corner on is the front edge, then the left
    out.push(<polyline key="edge" points={pts(edgeFront.slice(22), ox, oy)} fill="none"
      stroke={real ? 'rgba(255,255,255,0.55)' : 'rgba(255,255,255,0.25)'} strokeWidth={Math.max(0.6, d.kpx * 0.35)} />);
    // the scoop's lip on the top face
    out.push(<polyline key="scoopLip" points={poly(Array.from({length: 13}, (_, i): V3 => {
      const x = -sw2 * 0.92 + (b.scoopMm * 0.92 * i) / 12; return [x, 0, D - 0.6];
    }))} fill="none" stroke="rgba(0,0,0,0.28)" strokeWidth={Math.max(0.6, d.kpx * 0.4)} />);

    // ── the deck: speaker grilles, the keyboard well and its keys, the trackpad ──
    const onDeck = (x0: number, z0: number, x1: number, z1: number, r: number, y = 0) =>
      rrPts(x0, z0, x1, z1, r, r, 6).map(([x, z]) => P([x, y, z]));
    if (b.grille) {
      const [gx, gz, gw, gd] = b.grille;
      [-1, 1].forEach((side) => {
        const xa = side < 0 ? -W2 + gx : W2 - gx - gw, xb = xa + gw;
        out.push(<polygon key={'gr' + side} points={pts(onDeck(xa, gz, xb, gz + gd, 0.6), ox, oy)}
          fill={real ? `url(#${id('holes')})` : lerpC(ink, bg, 0.3)} opacity={real ? 0.9 : 1} />);
      });
    }
    const [, wz, ww, wd] = b.well;
    const wx0 = -ww / 2;
    out.push(<polygon key="well" points={pts(onDeck(wx0, wz, wx0 + ww, wz + wd, 3.2), ox, oy)} fill={wellC} />);
    const unit = ww / UNITS, gap = L3D.keyGapMm, rowD = wd / ROWS.length;
    const legend = d.kpx * unit > 9;      // a key under ~9 px wide is drawn without its legend
    ROWS.forEach((row, ri) => {
      let x = wx0;
      const z0 = wz + ri * rowD;
      row.forEach(([u, l], ki) => {
        const kw = u * unit;
        const split = l === '▲▼';
        const parts: Array<[number, number, string]> = split ? [[z0, rowD / 2, '▲'], [z0 + rowD / 2, rowD / 2, '▼']]
          : ri === 5 && (l === '◀' || l === '▶') ? [[z0 + rowD / 2, rowD / 2, l]] : [[z0, rowD, l]];
        parts.forEach(([kz, kd, lab], pi) => {
          const a: V3 = [x + gap / 2, 0.25, kz + gap / 2], bR: V3 = [x + kw - gap / 2, 0.25, kz + gap / 2];
          const cL: V3 = [x + gap / 2, 0.25, kz + kd - gap / 2];
          const q = onDeck(a[0], a[2], bR[0], cL[2], 0.9, 0.25);
          const key = `k${ri}_${ki}_${pi}`;
          out.push(<polygon key={key} points={pts(q, ox, oy)} fill={keyC}
            stroke={real ? 'rgba(255,255,255,0.07)' : 'none'} strokeWidth={0.6} />);
          if (legend && lab) {
            // the legend lies on the key: an affine map of the key's own box, from three of its projected corners
            const pa = P(a), pb = P(bR), pc = P(cL);
            const kwm = bR[0] - a[0], kdm = cL[2] - a[2];
            const m = [(pb.x - pa.x) / kwm, (pb.y - pa.y) / kwm, (pc.x - pa.x) / kdm, (pc.y - pa.y) / kdm, pa.x - ox, pa.y - oy];
            const word = lab.length > 2;
            out.push(<text key={key + 't'} transform={`matrix(${m.map((v) => v.toFixed(4)).join(',')})`}
              x={word ? kwm * 0.12 : kwm / 2} y={word ? kdm * 0.8 : kdm * 0.62} textAnchor={word ? 'start' : 'middle'}
              fontSize={word ? 2.1 : (ri === 0 ? 2.0 : 3.3)} fontFamily="Inter, 'SF Pro Text', system-ui, sans-serif"
              fill={real ? 'rgba(236,238,242,0.78)' : bg}>{lab}</text>);
          }
        });
        x += kw;
      });
    });
    const [tw, tz, td, tr] = b.trackpad;
    out.push(<polygon key="pad" points={pts(onDeck(-tw / 2, tz, tw / 2, tz + td, tr), ox, oy)}
      fill={real ? `url(#${id('pad')})` : tone(0.6)} stroke={real ? 'rgba(0,0,0,0.22)' : lerpC(ink, bg, 0.4)}
      strokeWidth={Math.max(0.6, d.kpx * 0.3)} />);

    // ── the hinge: the dark band between the deck's back edge and the lid ──
    const hw = W2 - b.hingeInsetMm;
    const hingeA = c.lid(-hw, c.vCut, 0), hingeB = c.lid(hw, c.vCut, 0);
    out.push(<polygon key="hinge" points={poly([[-hw, 0, 0], [hw, 0, 0], hingeB, hingeA])} fill={real ? '#0c0d10' : ink} />);

    // ── the lid: its edge (thickness) where it is seen, then its face — aluminium rim, black glass ──
    const lidOut = rrPts(-d.face.w / 2, 0, d.face.w / 2, d.face.h, d.lidTopR, L3D.lidCornerBottomMm, 10)
      // y down -> v up; the chin below vCut has dropped behind the base at the hinge, so the lid starts there
      .map(([x, y]) => [x, Math.max(c.vCut, d.face.h - y)] as [number, number]);
    const lidWalls: Array<{z: number; node: React.ReactNode}> = [];
    for (let i = 0; i < lidOut.length; i++) {
      const [xa, va] = lidOut[i], [xb, vb] = lidOut[(i + 1) % lidOut.length];
      const ta = c.lid(xa, va), tb = c.lid(xb, vb);
      const along = sub(tb, ta);
      if (Math.hypot(along[0], along[1], along[2]) < 1e-6) continue;
      let n = norm(cross(along, c.N));
      const mid = c.lid((xa + xb) / 2, (va + vb) / 2, d.lidT / 2);
      const centre = c.lid(0, d.face.h / 2, d.lidT / 2);
      if (dot(n, sub(mid, centre)) < 0) n = mul(n, -1);
      if (!viewOK(mid, n)) continue;
      const q = [ta, tb, c.lid(xb, vb, d.lidT), c.lid(xa, va, d.lidT)];
      lidWalls.push({z: c.cam(mid)[2], node: <polygon key={'lw' + i} points={poly(q)} fill={tone(0.3 + 0.6 * lit(c, n))}
        stroke={tone(0.3 + 0.6 * lit(c, n))} strokeWidth={0.6} />});
    }
    lidWalls.sort((p, q) => p.z - q.z).forEach((w) => out.push(w.node));
    if (!viewOK(c.lid(0, d.face.h / 2), c.N)) {
      // seen from behind: the lid's back, aluminium
      out.push(<polygon key="lidBack" points={poly(lidOut.map(([x, v]) => c.lid(x, v, d.lidT)))} fill={tone(0.5)} />);
    } else {
      out.push(<polygon key="lidRim" points={poly(lidOut.map(([x, v]) => c.lid(x, v)))} fill={tone(0.55 + 0.35 * lit(c, c.N))} />);
      const rim = b.rimMm;
      const glass = rrPts(-d.face.w / 2 + rim, rim, d.face.w / 2 - rim, d.face.h - rim * 0.6, Math.max(0, d.lidTopR - rim),
        Math.max(0, L3D.lidCornerBottomMm - rim), 10).map(([x, y]) => c.lid(x, Math.max(c.vCut, d.face.h - y)));
      out.push(<polygon key="glass" points={poly(glass)} fill={real ? '#050608' : ink} />);
      out.push(<polygon key="glassSheen" points={poly(glass)} fill={`url(#${id('sheen')})`} />);
    }
    return <>{out}</>;
  };

/** The gradients and patterns LaptopBody fills with, in its own SVG. */
export const LaptopDefs: React.FC<{uid: string; c: LaptopCamera; ox: number; oy: number; metal: {hi: string;
  mid: string; lo: string; deep: string}}> = ({uid, c, ox, oy, metal}) => {
  const id = (n: string) => `lp${uid}${n}`;
  const d = c.dims;
  const top = lit(c, [0, 1, 0]);
  const deckHi = lerpC(metal.deep, metal.hi, 0.42 + 0.58 * top), deckLo = lerpC(metal.deep, metal.hi, 0.25 + 0.55 * top);
  const back = c.project([-d.W / 2, 0, 0]), front = c.project([d.W / 2, 0, d.D]);
  const hole = Math.max(1.0, d.kpx * 0.5);
  return (
    <defs>
      <filter id={id('blur')} x="-20%" y="-40%" width="140%" height="180%">
        <feGaussianBlur stdDeviation={Math.max(2, d.kpx * 5)} />
      </filter>
      <linearGradient id={id('deck')} gradientUnits="userSpaceOnUse" x1={back.x - ox} y1={back.y - oy} x2={front.x - ox} y2={front.y - oy}>
        <stop offset="0" stopColor={deckHi} /><stop offset="0.55" stopColor={lerpC(metal.deep, metal.hi, 0.36 + 0.56 * top)} />
        <stop offset="1" stopColor={deckLo} />
      </linearGradient>
      <linearGradient id={id('pad')} gradientUnits="userSpaceOnUse" x1={back.x - ox} y1={back.y - oy} x2={front.x - ox} y2={front.y - oy}>
        <stop offset="0" stopColor={lerpC(metal.deep, metal.hi, 0.48 + 0.5 * top)} />
        <stop offset="1" stopColor={lerpC(metal.deep, metal.hi, 0.3 + 0.52 * top)} />
      </linearGradient>
      <linearGradient id={id('scoop')} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor={lerpC(metal.deep, metal.hi, 0.22)} /><stop offset="1" stopColor={lerpC(metal.deep, metal.hi, 0.46)} />
      </linearGradient>
      <linearGradient id={id('sheen')} x1="0" y1="0" x2="0.7" y2="1">
        <stop offset="0" stopColor="#ffffff" stopOpacity="0.10" /><stop offset="0.35" stopColor="#ffffff" stopOpacity="0.02" />
        <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
      </linearGradient>
      <pattern id={id('holes')} width={hole * 2} height={hole * 2} patternUnits="userSpaceOnUse">
        <rect width={hole * 2} height={hole * 2} fill={lerpC(metal.deep, metal.hi, 0.55 + 0.35 * top)} />
        <circle cx={hole} cy={hole} r={hole * 0.42} fill="#1a1c20" />
      </pattern>
    </defs>
  );
};

/** The frame rect a laptop at this pose covers — for a caller that must keep it in frame. */
export const laptopBounds = (c: LaptopCamera): Rect => {
  const d = c.dims, W2 = d.W / 2;
  const ps: P2[] = [];
  rrPts(-W2, 0, W2, d.D, d.body.cornerMm).forEach(([x, z]) => { ps.push(c.project([x, 0, z]), c.project([x, -d.baseT, z])); });
  [[-d.face.w / 2, c.vCut], [d.face.w / 2, c.vCut], [-d.face.w / 2, d.face.h], [d.face.w / 2, d.face.h]].forEach(([x, v]) => {
    ps.push(c.project(c.lid(x, v)), c.project(c.lid(x, v, d.lidT)));
  });
  const xs = ps.map((p) => p.x), ys = ps.map((p) => p.y);
  const x0 = Math.min(...xs), y0 = Math.min(...ys);
  return {x: x0, y: y0, w: Math.max(...xs) - x0, h: Math.max(...ys) - y0};
};
