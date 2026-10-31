// OBJECT · GpsSatellite — a GPS satellite that reads as one: a gold-foil body, two blue solar wings, and the
// helix antenna array on the face that points at Earth.
//
// WHAT IT ENCODES. The one part of a GPS satellite the film is about is the face that points DOWN: the array of
// helical antennas that broadcasts "where I am, and when I sent this" to the whole Earth below. So the object is
// always posed with that nadir face toward the bottom of its box and turned enough that the array is SEEN —
// hide the caption and a viewer still finds the thing that talks to the ground. The rest is anatomy drawn so it
// reads as a satellite and not as an icon in a box: a box body wrapped in crinkled gold insulation foil on every
// face, two wings each ONE continuous array of three butted panels on a short yoke, ruled into solar cells, the
// helices standing on a dark frame under the nadir face, and the boom-mounted antenna hanging beside the right
// wing root — every part as both drawings in META.fidelity show it.
//
// HOW. Drawn in 3D (corners rotated by yaw/pitch/roll and projected with a mild perspective), every face painted
// far to near, faces turned away culled by their normals, and a texture laid in each face's OWN (u, v) so foil
// facets and cell rows foreshorten with the face. Three LOOKS share that geometry:
//   engraved — line only, in the film's accent, on the film's ground: foil drawn as crinkle facets, shadow as
//              hatching, the strokes drawing themselves on (a plate's engraving).
//   lit      — the material in sunlight: faceted gold, deep-blue cells with a sheen, a dark antenna frame.
//   flat     — the same anatomy reduced to two tones per material, the way a phone's interface draws a thing.
// It draws no words. It sizes to its box (fits the pose's own extent, held fixed across a turn). A pure function
// of t: the reveal runs 0 -> 1 and holds; `yaw` from a turning stage turns it for real (META.turns).
import React from 'react';
import type {ObjectProps, ObjectMeta} from '../runtime/objectSlot';
import {clamp01, seg, easeOutCubic, easeOutBack, hash01} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {mix} from '../runtime/dna';

export const META: ObjectMeta & {fidelity: object} = {aspect: 2.3, turns: true, provenance: 'scientific', fidelity: {
  // The record's shape is the Fidelity type in runtime/fidelity.tsx, checked by scripts/fidelity.py. It is typed
  // loosely, and this note sits INSIDE the literal, because two measured registers import from this file: a new
  // import or a comment above META would move their source hash (scripts/register_energy.py, the preamble).
  subject: 'GPS Block IIF navigation satellite',
  depicts: 'real',
  references: [
    {kind: 'drawing', source: 'references/object-refs/GpsSatellite/gps-iif.jpg',
      note: 'NASA artist\'s conception of a GPS Block IIF satellite in orbit (Wikimedia Commons, public domain); the same rendering Gunter\'s Space Page credits to Boeing as "GPS-2F": three butted panels per wing, a dark V-yoke to each wing, the helices on a dark frame under the bus, an L-boom antenna by the right wing root'},
    {kind: 'drawing', source: 'references/object-refs/GpsSatellite/navstar-2f.jpg',
      note: 'USAF "Navstar-2F" drawing (Wikimedia Commons, public domain; the Wikipedia GPS Block IIF infobox image): three butted panels per wing on a frame yoke, helices on the nadir face, a boom antenna off the nadir edge'},
    {kind: 'spec', source: 'https://www.airforce-technology.com/projects/global-positioning-system-gps-iif-military-satellite/',
      note: 'each satellite 2.23 m high, 2.48 m wide, 2.03 m deep; three-panel GaAs solar arrays; "thermal coatings, radiator blankets" (no radiator face is located)'},
    {kind: 'spec', source: 'https://www.airandspaceforces.com/weapons/gps',
      note: 'GPS IIF: 9.6 x 6.5 x 12.9 ft, span including solar panels 43.1 ft (13.1 m) — the box disagrees with airforce-technology and names no axes'},
    {kind: 'spec', source: 'https://patents.google.com/patent/US7388559B1/en',
      note: 'the GPS navigation array antenna: an inner ring of four helix elements and an outer ring of eight'},
    {kind: 'spec', source: 'https://space.skyrocket.de/doc_sdat/navstar-2f.htm',
      note: "Gunter's Space Page: 2 deployable solar arrays; its GPS-2F picture [Boeing] is the NASA rendering above"},
  ],
  proportions: {
    span_to_body_width: {value: 5.3, drawn: 5.28, source: ['https://www.airandspaceforces.com/weapons/gps',
      'https://www.airforce-technology.com/projects/global-positioning-system-gps-iif-military-satellite/']},
    panels_per_wing: {value: '3, butted into one array', drawn: '3, butted (seams, no gaps)',
      source: ['https://www.airforce-technology.com/projects/global-positioning-system-gps-iif-military-satellite/',
        'references/object-refs/GpsSatellite/gps-iif.jpg', 'references/object-refs/GpsSatellite/navstar-2f.jpg']},
    helix_elements: {value: '4 inner + 8 outer', drawn: '4 inner + 8 outer',
      source: 'https://patents.google.com/patent/US7388559B1/en'},
    // UNSETTLED: the axes. airforce-technology gives 2.48 wide x 2.23 high x 2.03 deep and does not say which axis
    // points at Earth; Air & Space Forces gives 9.6 x 6.5 x 12.9 ft, which matches neither and names no axes. Drawn
    // with "wide" along the wings and "high" on the Earth axis, the way both drawings pose the craft; the span
    // ratio above is taken against the same 2.48 m, so the two records agree with each other.
    body_w_h_d: {value: '2.48 : 2.23 : 2.03 (wide : high : deep)', drawn: '1.22 : 1.10 : 1.00 (along the wings : Earth axis : depth)',
      source: 'https://www.airforce-technology.com/projects/global-positioning-system-gps-iif-military-satellite/'},
    wing_chord_to_body_height: {value: '~0.6 (read off the drawing, foreshortened — no spec gives the chord)', drawn: 0.65,
      source: 'references/object-refs/GpsSatellite/gps-iif.jpg'},
  },
  parts: ['bus', 'solar-array', 'wing-boom', 'helix-array', 'boom-antenna'],
  // what holds each part (the NASA/Boeing drawing): the wings on their booms off the bus, the arrays on the bus
  mounted_on: {'bus': null, 'wing-boom': 'bus', 'solar-array': 'wing-boom', 'helix-array': 'bus', 'boom-antenna': 'bus'},
  materials: ['gold insulation foil on every face of the bus (both drawings; the spec names "radiator blankets" but locates none, so no radiator face is drawn)', 'dark-blue solar cells', 'bronze helix elements on a dark frame (the NASA/Boeing drawing)', 'a pale boom and collar carrying a bronze cylinder (the NASA/Boeing drawing)'],
}};

export type SatLook = 'engraved' | 'lit' | 'flat';
type V3 = [number, number, number];

// THE SATELLITE'S OWN MATERIALS — identity colours of the thing, not the film's palette (references/
// remotion-shot-authoring.md §C2: semantic colour survives the theme). Used by `lit` and `flat`; `engraved`
// draws in the film's accent instead, because an engraving is one ink.
const FOIL_LIGHT = '#f6d27a', FOIL = '#d9a441', FOIL_DARK = '#8a5a17', FOIL_EDGE = '#5b3a0c';
const CELL = '#1d3a8f', CELL_DEEP = '#0f1f55', CELL_LINE = '#6f8fd8', PANEL_BACK = '#c9cdd4';
const RIB = '#8c96a3';                              // the wing's back structure
const FRAME = '#2b2622', FRAME_LIGHT = '#4a4038';     // the antenna frame under the bus (dark, the NASA/Boeing drawing)
const HELIX = '#d9b77c', HELIX_DARK = '#6b4c22';     // bronze helices (the same drawing)
const BOOM_PALE = '#e3e6ea', CAN = '#b0834c', CAN_DARK = '#6e4c22';   // the boom antenna: pale boom + collar, bronze can
const YOKE = '#4d525c';                              // the wing yoke: dark struts (the same drawing)
const ENG_INK_D0 = '#d9a54a', ENG_GROUND_D0 = '#0b1530';

// GEOMETRY, in body units: +x along the wings, +y zenith (away from Earth), −y nadir (toward Earth), +z toward
// the viewer before the pose turns it.
// The body is 2.48 (along the wings) : 2.23 (Earth axis) : 2.03 (depth) m — META.fidelity.body_w_h_d, which says
// what is and is not settled about those axes. The wing tip sits where span / body width = 13.1 / 2.48.
const HX = 0.611, HY = 0.549, HZ = 0.5;           // the body's half-sizes
const BOOM = 0.34;                                // root of the wing past the body side (the yoke)
const PANELS = 3, PH = 0.36;                      // three panels BUTTED into one array; PH = half the chord
const TIP = HX * 5.28;                            // span / body width 5.28 (13.1 m / 2.48 m)
const PW = (TIP - HX - BOOM) / PANELS;
const FX = 0.44, FZ = 0.38, FD = 0.12;            // the antenna frame: half-sizes under the nadir face, its depth
const DISC_Y = -HY - FD;                          // the frame's underside, where the helices stand
const HELIX_LEN = 0.27, HELIX_R = 0.032;
// the boom antenna: out from the −x face by that wing root, then down; a collar and a can on its end. The drawing
// shows it by the root of the wing nearer the viewer; which side of the real craft that is, one drawing cannot say.
const BA0: V3 = [-HX, -HY * 0.72, HZ * 0.55], BA1: V3 = [-HX - 0.3, -HY * 0.72, HZ * 0.55], BA2: V3 = [-HX - 0.3, -HY * 0.95, HZ * 0.55];
const CAN_LEN = 0.4, CAN_R = 0.075;
const F = 12;                                     // perspective: the camera stands F units in front of the origin

const rotY = (p: V3, a: number): V3 => [p[0] * Math.cos(a) + p[2] * Math.sin(a), p[1], -p[0] * Math.sin(a) + p[2] * Math.cos(a)];
const rotX = (p: V3, a: number): V3 => [p[0], p[1] * Math.cos(a) - p[2] * Math.sin(a), p[1] * Math.sin(a) + p[2] * Math.cos(a)];
const rotZ = (p: V3, a: number): V3 => [p[0] * Math.cos(a) - p[1] * Math.sin(a), p[0] * Math.sin(a) + p[1] * Math.cos(a), p[2]];
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const unit = (a: V3): V3 => {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};

type Quad = {key: string; c: [V3, V3, V3, V3]; n: V3; kind: 'foil' | 'frame' | 'cells'; depth?: number};

/** Every point the pose can carry to the box's edge — what the fit is measured on. */
const extentPoints = (wingTilt: number): V3[] => {
  const pts: V3[] = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) pts.push([sx * HX, sy * HY, sz * HZ]);
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    pts.push([sx * TIP, sy * PH * Math.cos(wingTilt), sy * PH * Math.sin(wingTilt)]);
  }
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) pts.push([sx * FX, DISC_Y - HELIX_LEN - 0.04, sz * FZ]);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    pts.push([BA2[0] + sx * CAN_R, BA2[1] - CAN_LEN, BA2[2] + sz * CAN_R]);
  }
  return pts;
};

/** Where the antenna array's tip lands in a w × h box for a given pose — so a shot can start a signal exactly at
 *  the face that broadcasts it, at any size and any pose (the same fit and projection the drawing uses). */
export const nadirPoint = (w: number, h: number, pose: {yaw0?: number; pitch?: number; roll?: number; wingTilt?: number} = {}) => {
  const {yaw0 = -0.62, pitch = 0.32, roll = 0, wingTilt = 0.42} = pose;
  const P = (p: V3): V3 => rotZ(rotX(rotY(p, yaw0), pitch), roll);
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of extentPoints(wingTilt)) {
    const q = P(p);
    const k = F / (F + q[2]);
    x0 = Math.min(x0, q[0] * k); x1 = Math.max(x1, q[0] * k);
    y0 = Math.min(y0, -q[1] * k); y1 = Math.max(y1, -q[1] * k);
  }
  const s = Math.min((w * 0.96) / Math.max(1e-6, x1 - x0), (h * 0.94) / Math.max(1e-6, y1 - y0));
  const cx = w / 2 - s * (x0 + x1) / 2, cy = h / 2 - s * (y0 + y1) / 2;
  const q = P([0, DISC_Y - HELIX_LEN, 0]);
  const k = F / (F + q[2]);
  return {x: cx + s * q[0] * k, y: cy + s * -q[1] * k};
};

export const GpsSatellite: React.FC<ObjectProps & {
  look?: SatLook;
  yaw0?: number;       // the turn shown when no stage turns it (radians)
  pitch?: number;      // >0 tips the nadir face toward the viewer, so the antenna array is seen
  roll?: number;       // tilts the whole craft in its box (radians)
  wingTilt?: number;   // the wings' turn about their own axis (radians) — tracking the sun
  glint?: number;      // 0..1, how strongly the sunlit wing catches the light (lit only)
}> = ({w, h, t, dna, yaw, look = 'lit', yaw0 = -0.62, pitch = 0.32, roll = 0, wingTilt = 0.42, glint = 0.6}) => {
  if (!(look === 'engraved' || look === 'lit' || look === 'flat')) {
    throw new Error(`GpsSatellite: \`look\` is 'engraved', 'lit' or 'flat' — got ${JSON.stringify(look)}`);
  }
  for (const [k, v] of [['yaw0', yaw0], ['pitch', pitch], ['roll', roll], ['wingTilt', wingTilt], ['glint', glint]] as const) {
    if (!(typeof v === 'number' && Number.isFinite(v))) {
      throw new Error(`GpsSatellite: \`${k}\` must be a finite number — got ${JSON.stringify(v)}`);
    }
  }
  const uid = React.useId().replace(/[^A-Za-z0-9]/g, '');
  const Y = typeof yaw === 'number' && Number.isFinite(yaw) ? yaw : yaw0;
  const turning = typeof yaw === 'number';
  const pose = (p: V3, yy: number): V3 => rotZ(rotX(rotY(p, yy), pitch), roll);

  // ── the fit: the extent of the pose, measured over the whole turn when a stage turns it, so it never breathes ──
  const sweep = turning ? Array.from({length: 24}, (_, i) => (i / 24) * Math.PI * 2) : [Y];
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const yy of sweep) {
    for (const p of extentPoints(wingTilt)) {
      const q = pose(p, yy);
      const k = F / (F + q[2]);
      x0 = Math.min(x0, q[0] * k); x1 = Math.max(x1, q[0] * k);
      y0 = Math.min(y0, -q[1] * k); y1 = Math.max(y1, -q[1] * k);
    }
  }
  const s = Math.min((w * 0.96) / Math.max(1e-6, x1 - x0), (h * 0.94) / Math.max(1e-6, y1 - y0));
  const cx = w / 2 - s * (x0 + x1) / 2, cy = h / 2 - s * (y0 + y1) / 2;
  const P = (p: V3) => {
    const q = pose(p, Y);
    const k = F / (F + q[2]);
    return {x: cx + s * q[0] * k, y: cy + s * -q[1] * k, z: q[2]};
  };
  const cam: V3 = [0, 0, -F];
  const faces = (q: Quad) => {                     // in view space: is it turned toward the camera, and how lit
    const c = pose([(q.c[0][0] + q.c[2][0]) / 2, (q.c[0][1] + q.c[2][1]) / 2, (q.c[0][2] + q.c[2][2]) / 2], Y);
    const n = pose(q.n, Y);
    return {front: dot(n, sub(c, cam)) < 0, n, depth: c[2]};
  };
  const SUN = unit([-0.55, 0.62, -0.56]);         // from upper-left, in front: the key the lit look is shaded by

  // ── the reveal ──
  const on = easeOutCubic(clamp01(seg(t, 0, 0.7)));
  const pop = look === 'flat' ? easeOutBack(clamp01(seg(t, 0, 0.55))) : 1;

  // ── the parts as quads ──
  const quads: Quad[] = [];
  const box = (sx: number, sy: number, sz: number): V3 => [sx * HX, sy * HY, sz * HZ];
  quads.push({key: 'top', kind: 'foil', n: [0, 1, 0], c: [box(-1, 1, 1), box(1, 1, 1), box(1, 1, -1), box(-1, 1, -1)]});
  quads.push({key: 'bot', kind: 'foil', n: [0, -1, 0], c: [box(-1, -1, -1), box(1, -1, -1), box(1, -1, 1), box(-1, -1, 1)]});
  quads.push({key: 'front', kind: 'foil', n: [0, 0, 1], c: [box(-1, 1, 1), box(1, 1, 1), box(1, -1, 1), box(-1, -1, 1)]});
  quads.push({key: 'back', kind: 'foil', n: [0, 0, -1], c: [box(1, 1, -1), box(-1, 1, -1), box(-1, -1, -1), box(1, -1, -1)]});
  quads.push({key: 'right', kind: 'foil', n: [1, 0, 0], c: [box(1, 1, 1), box(1, 1, -1), box(1, -1, -1), box(1, -1, 1)]});
  quads.push({key: 'left', kind: 'foil', n: [-1, 0, 0], c: [box(-1, 1, -1), box(-1, 1, 1), box(-1, -1, 1), box(-1, -1, -1)]});
  // the antenna frame: a shallow dark box under the nadir face, the helices on its underside
  {
    const y0 = -HY, y1 = DISC_Y;
    const fb = (sx: number, yy: number, sz: number): V3 => [sx * FX, yy, sz * FZ];
    quads.push({key: 'fbot', kind: 'frame', n: [0, -1, 0], c: [fb(-1, y1, -1), fb(1, y1, -1), fb(1, y1, 1), fb(-1, y1, 1)]});
    quads.push({key: 'ffront', kind: 'frame', n: [0, 0, 1], c: [fb(-1, y0, 1), fb(1, y0, 1), fb(1, y1, 1), fb(-1, y1, 1)]});
    quads.push({key: 'fback', kind: 'frame', n: [0, 0, -1], c: [fb(1, y0, -1), fb(-1, y0, -1), fb(-1, y1, -1), fb(1, y1, -1)]});
    quads.push({key: 'fright', kind: 'frame', n: [1, 0, 0], c: [fb(1, y0, 1), fb(1, y0, -1), fb(1, y1, -1), fb(1, y1, 1)]});
    quads.push({key: 'fleft', kind: 'frame', n: [-1, 0, 0], c: [fb(-1, y0, -1), fb(-1, y0, 1), fb(-1, y1, 1), fb(-1, y1, -1)]});
  }
  const ct = Math.cos(wingTilt), st = Math.sin(wingTilt);
  const wingN: V3 = [0, st, -ct];               // the cell side: toward the viewer (−z) and up to the sun
  for (const side of [-1, 1]) {
    for (let k = 0; k < PANELS; k++) {
      const a = HX + BOOM + k * PW, b = a + PW;      // butted: one array, the panels' outlines are its seams
      const pt = (x: number, yy: number): V3 => [side * x, yy * ct, yy * st];
      quads.push({key: `w${side}${k}`, kind: 'cells', n: wingN,
        c: side > 0 ? [pt(a, PH), pt(b, PH), pt(b, -PH), pt(a, -PH)] : [pt(b, PH), pt(a, PH), pt(a, -PH), pt(b, -PH)]});
    }
  }

  // ── colours per look ──
  const engInk = dna?.accent ?? ENG_INK_D0;
  const engGround = dna?.bg ?? ENG_GROUND_D0;
  const engFine = mix(engInk, engGround, 0.45);
  const engCell = dna?.accent2 ?? mix(engInk, '#7fa6e8', 0.6);
  const outline = look === 'flat' ? (dna?.fg ?? '#1c2129') : FOIL_EDGE;

  // bilinear map of a face's own (u, v) onto its four projected corners
  const uv = (c: {x: number; y: number}[], u: number, v: number) => ({
    x: (1 - v) * ((1 - u) * c[0].x + u * c[1].x) + v * ((1 - u) * c[3].x + u * c[2].x),
    y: (1 - v) * ((1 - u) * c[0].y + u * c[1].y) + v * ((1 - u) * c[3].y + u * c[2].y),
  });
  const poly = (pts: {x: number; y: number}[]) => pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ') + ' Z';
  const lw = Math.max(0.6, s * 0.012);            // the hairline, scaled to the drawing

  type Item = {depth: number; node: React.ReactNode};
  const items: Item[] = [];

  quads.forEach((q, qi) => {
    const f = faces(q);
    const pc = q.c.map(P);
    const d = poly(pc);
    const clip = `${uid}c${qi}`;
    const lightK = Math.max(0, dot(f.n, SUN));
    const nodes: React.ReactNode[] = [];
    const front = f.front;
    if (q.kind === 'cells' && !front) {
      // the back of a wing: its structure, not cells
      if (look === 'engraved') {
        nodes.push(<path key="b" d={d} fill={engGround} stroke={engFine} strokeWidth={lw} {...drawOn(on)} />);
      } else {
        nodes.push(<path key="b" d={d} fill={mix(PANEL_BACK, '#000000', 0.25 * (1 - lightK))} stroke={outline}
          strokeWidth={lw} strokeOpacity={0.5} />);
        for (let r = 1; r < 3; r++) {
          const p0 = uv(pc, 0, r / 3), p1 = uv(pc, 1, r / 3);
          nodes.push(<line key={`br${r}`} x1={p0.x} y1={p0.y} x2={p1.x} y2={p1.y} stroke={RIB} strokeWidth={lw} />);
        }
      }
      items.push({depth: f.depth, node: <g key={q.key} data-part="solar-array">{nodes}</g>});
      return;
    }
    if (!front && q.kind !== 'cells') return;     // a body face turned away is hidden by the body itself
    if (q.kind === 'frame') {
      // the antenna frame: dark structure, ruled into the bays the helices stand in (the NASA/Boeing drawing)
      const fill = look === 'engraved' ? engGround : look === 'flat' ? (lightK > 0.25 ? FRAME_LIGHT : FRAME)
        : mix(FRAME, FRAME_LIGHT, 0.2 + 0.8 * lightK);
      nodes.push(<path key="f" d={d} fill={fill} stroke={look === 'engraved' ? engInk : outline}
        strokeWidth={lw * (look === 'flat' ? 1.6 : 1)} strokeLinejoin="round" {...(look === 'engraved' ? drawOn(on) : {})} />);
      for (let k = 1; k < 4; k++) {
        const a = uv(pc, k / 4, 0.05), b = uv(pc, k / 4, 0.95);
        nodes.push(<line key={`bay${k}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
          stroke={look === 'engraved' ? engFine : mix(fill, '#000000', 0.45)} strokeWidth={lw * 0.8} />);
      }
      items.push({depth: f.depth, node: <g key={q.key} data-part="helix-array">{nodes}</g>});
      return;
    }
    if (q.kind === 'foil') {
      // crinkled foil: a jittered grid of facets, each catching the light a little differently
      const N = s > 120 ? 6 : s > 60 ? 4 : 3;
      const J = (i: number, j: number) => {
        const edge = i === 0 || j === 0 || i === N || j === N;
        // @decor: the crinkle of insulation foil is texture; no facet stands for any reading
        const du = edge ? 0 : (hash01(qi * 97 + i * 13 + j * 7) - 0.5) * 0.55 / N;
        // @decor: the crinkle of insulation foil is texture; no facet stands for any reading
        const dv = edge ? 0 : (hash01(qi * 89 + i * 11 + j * 5 + 3) - 0.5) * 0.55 / N;
        return uv(pc, i / N + du, j / N + dv);
      };
      if (look === 'lit') {
        const base = mix(FOIL_DARK, FOIL_LIGHT, 0.25 + 0.7 * lightK);
        nodes.push(<path key="f" d={d} fill={base} />);
        for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
          // @decor: each facet's tone is the foil's crinkle, not data
          const tone = hash01(qi * 131 + i * 17 + j * 29);
          const fill = tone > 0.93 ? '#fff0c2'
            : tone > 0.5 ? mix(base, FOIL_LIGHT, (tone - 0.5) * 1.5) : mix(base, FOIL_DARK, (0.5 - tone) * 1.3);
          nodes.push(<path key={`t${i}_${j}`} d={poly([J(i, j), J(i + 1, j), J(i + 1, j + 1), J(i, j + 1)])}
            fill={fill} stroke={mix(fill, FOIL_EDGE, 0.35)} strokeWidth={lw * 0.6} strokeOpacity={0.55} />);
        }
        // a specular streak where the face turns toward the sun
        if (lightK > 0.35) {
          const a = uv(pc, 0.15, 0.2), b = uv(pc, 0.85, 0.55);
          nodes.push(<line key="spec" x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#fff6d8" strokeWidth={lw * 3}
            strokeOpacity={0.35 * (lightK - 0.35)} strokeLinecap="round" />);
        }
        nodes.push(<path key="o" d={d} fill="none" stroke={FOIL_EDGE} strokeWidth={lw * 1.1} strokeOpacity={0.8} />);
      } else if (look === 'flat') {
        const fill = lightK > 0.25 ? FOIL : mix(FOIL, FOIL_DARK, 0.55);
        nodes.push(<path key="f" d={d} fill={fill} stroke={outline} strokeWidth={lw * 1.6} strokeLinejoin="round" />);
        // two sheen strokes along the top edge — the foil catching light, nothing that could read as a mark
        if (lightK > 0.25) {
          for (const [v, u0, u1] of [[0.12, 0.1, 0.62], [0.2, 0.1, 0.38]] as const) {
            const a = uv(pc, u0, v), b = uv(pc, u1, v);
            nodes.push(<line key={`sh${v}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={FOIL_LIGHT}
              strokeWidth={lw * 1.3} strokeLinecap="round" opacity={0.85} />);
          }
        }
      } else {
        nodes.push(<path key="f" d={d} fill={engGround} stroke={engInk} strokeWidth={lw * 1.4} {...drawOn(on)} />);
        for (let i = 1; i < N; i++) {
          const row = Array.from({length: N + 1}, (_, j) => J(i, j));
          const col = Array.from({length: N + 1}, (_, j) => J(j, i));
          nodes.push(<path key={`r${i}`} d={row.map((p, k) => `${k ? 'L' : 'M'}${p.x} ${p.y}`).join(' ')} fill="none"
            stroke={engFine} strokeWidth={lw * 0.7} strokeOpacity={0.75} {...drawOn(on)} />);
          nodes.push(<path key={`c${i}`} d={col.map((p, k) => `${k ? 'L' : 'M'}${p.x} ${p.y}`).join(' ')} fill="none"
            stroke={engFine} strokeWidth={lw * 0.7} strokeOpacity={0.75} {...drawOn(on)} />);
        }
        // shadow said as hatching: the further a face turns from the light, the closer its lines
        const dark = 1 - lightK;
        if (dark > 0.35) {
          // parallel 45° hatching in the frame, clipped to the face — closer as the face turns from the light
          const bx0 = Math.min(...pc.map((p) => p.x)), bx1 = Math.max(...pc.map((p) => p.x));
          const by0 = Math.min(...pc.map((p) => p.y)), by1 = Math.max(...pc.map((p) => p.y));
          const gap = Math.max(2.5, s * (0.11 - 0.06 * dark));
          const span = (bx1 - bx0) + (by1 - by0);
          const n = Math.ceil(span / gap);
          nodes.push(<g key="h" clipPath={`url(#${clip})`}>{Array.from({length: n}, (_, k) => {
            const o = bx0 - (by1 - by0) + k * gap;
            return <line key={k} x1={o} y1={by1} x2={o + (by1 - by0)} y2={by0} stroke={engInk}
              strokeWidth={lw * 0.6} strokeOpacity={0.6 * on} />;
          })}</g>);
        }
      }
    } else {
      // the cells: rows and columns of the panel's face, with the sun's sheen across the lit wing
      const cols = s > 90 ? 6 : 4, rows = s > 90 ? 8 : 5;
      if (look === 'engraved') {
        nodes.push(<path key="f" d={d} fill={engGround} stroke={engInk} strokeWidth={lw * 1.2} {...drawOn(on)} />);
        for (let i = 1; i < cols; i++) {
          const a = uv(pc, i / cols, 0), b = uv(pc, i / cols, 1);
          nodes.push(<line key={`c${i}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={engCell} strokeWidth={lw * 0.7}
            strokeOpacity={0.9 * on} />);
        }
        for (let j = 1; j < rows; j++) {
          const a = uv(pc, 0, j / rows), b = uv(pc, 1, j / rows);
          nodes.push(<line key={`r${j}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={engCell} strokeWidth={lw * 0.7}
            strokeOpacity={0.9 * on} />);
        }
      } else {
        const gid = `${uid}g${qi}`;
        const sheen = look === 'lit' ? clamp01(glint) * (0.25 + 0.75 * Math.max(0, dot(f.n, SUN))) : 0;
        nodes.push(<defs key="d"><linearGradient id={gid} x1={pc[0].x} y1={pc[0].y} x2={pc[2].x} y2={pc[2].y}
          gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor={look === 'flat' ? CELL : CELL_DEEP} />
          <stop offset="0.48" stopColor={look === 'flat' ? CELL : mix(CELL, '#9fc0ff', sheen * 0.55)} />
          <stop offset="1" stopColor={look === 'flat' ? CELL : CELL_DEEP} />
        </linearGradient></defs>);
        nodes.push(<path key="f" d={d} fill={`url(#${gid})`} stroke={look === 'flat' ? outline : '#0a1230'}
          strokeWidth={lw * (look === 'flat' ? 1.6 : 1)} strokeLinejoin="round" />);
        if (look === 'lit' || s > 50) {
          for (let i = 1; i < cols; i++) {
            const a = uv(pc, i / cols, 0.02), b = uv(pc, i / cols, 0.98);
            nodes.push(<line key={`c${i}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={CELL_LINE}
              strokeWidth={lw * 0.6} strokeOpacity={look === 'flat' ? 0.5 : 0.45} />);
          }
          for (let j = 1; j < rows; j++) {
            const a = uv(pc, 0.02, j / rows), b = uv(pc, 0.98, j / rows);
            nodes.push(<line key={`r${j}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={CELL_LINE}
              strokeWidth={lw * 0.6} strokeOpacity={look === 'flat' ? 0.5 : 0.45} />);
          }
        }
      }
    }
    items.push({depth: f.depth, node: (
      <g key={q.key} data-part={q.kind === 'cells' ? 'solar-array' : 'bus'}>
        <defs><clipPath id={clip}><path d={d} /></clipPath></defs>
        {nodes}
      </g>
    )});
  });

  // ── the booms: a rod from each body side to its wing's root, with a yoke across the root ──
  for (const side of [-1, 1]) {
    const a = P([side * HX, 0, 0]), b = P([side * (HX + BOOM), 0, 0]);
    const y0p = P([side * (HX + BOOM), -PH * 0.55 * ct, -PH * 0.55 * st]), y1p = P([side * (HX + BOOM), PH * 0.55 * ct, PH * 0.55 * st]);
    const ink = look === 'engraved' ? engInk : look === 'flat' ? outline : YOKE;
    const depth = (a.z + b.z) / 2 - 0.01;
    items.push({depth, node: (
      <g key={`boom${side}`} data-part="wing-boom">
        <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={ink} strokeWidth={lw * 2.2} strokeLinecap="round"
          {...(look === 'engraved' ? drawOn(on) : {})} />
        <line x1={y0p.x} y1={y0p.y} x2={y1p.x} y2={y1p.y} stroke={ink} strokeWidth={lw * 1.6} strokeLinecap="round"
          {...(look === 'engraved' ? drawOn(on) : {})} />
      </g>
    )});
  }

  // ── the antenna array: twelve helices on the frame's underside, pointing at Earth (4 inner, 8 outer) ──
  {
    const spots: [number, number][] = [];
    for (let k = 0; k < 4; k++) spots.push([Math.cos(k * Math.PI / 2 + Math.PI / 4) * 0.15, Math.sin(k * Math.PI / 2 + Math.PI / 4) * 0.15]);
    for (let k = 0; k < 8; k++) spots.push([Math.cos(k * Math.PI / 4) * 0.33, Math.sin(k * Math.PI / 4) * 0.33]);
    spots.forEach(([hx, hz], i) => {
      const base = P([hx, DISC_Y, hz]), tip = P([hx, DISC_Y - HELIX_LEN, hz]);
      const dx = tip.x - base.x, dy = tip.y - base.y, L = Math.hypot(dx, dy) || 1;
      const nx = -dy / L, ny = dx / L, r = HELIX_R * s;
      // a helix seen from the side: a zig-zag about its axis, turns as many as fit
      const turns = 5;
      const pts = Array.from({length: turns * 2 + 1}, (_, k) => {
        const u = k / (turns * 2), side = k === 0 || k === turns * 2 ? 0 : (k % 2 ? 1 : -1);
        return `${k ? 'L' : 'M'}${(base.x + dx * u + nx * r * side).toFixed(1)} ${(base.y + dy * u + ny * r * side).toFixed(1)}`;
      }).join(' ');
      const ink = look === 'engraved' ? engInk : HELIX;
      items.push({depth: (base.z + tip.z) / 2 - 0.05, node: (
        <g key={`hx${i}`} data-part="helix-array">
          {look === 'lit' ? <line x1={base.x} y1={base.y} x2={tip.x} y2={tip.y} stroke={HELIX_DARK} strokeWidth={Math.max(0.6, lw * 0.8)}
            strokeLinecap="round" /> : null}
          <path d={pts} fill="none" stroke={ink} strokeWidth={Math.max(0.6, lw * 0.9)} strokeLinejoin="round"
            {...(look === 'engraved' ? drawOn(on) : {})} />
        </g>
      )});
    });
  }

  // ── the boom antenna: an L-boom off the −x face by the wing root, a collar, and a can hanging toward Earth ──
  {
    const a = P(BA0), b = P(BA1), c = P(BA2);
    const top = P([BA2[0], BA2[1] - 0.04, BA2[2]]), bot = P([BA2[0], BA2[1] - CAN_LEN, BA2[2]]);
    const dx = bot.x - top.x, dy = bot.y - top.y, L = Math.hypot(dx, dy) || 1;
    const nx = -dy / L, ny = dx / L, r = CAN_R * s;
    const can = poly([{x: top.x + nx * r, y: top.y + ny * r}, {x: bot.x + nx * r, y: bot.y + ny * r},
      {x: bot.x - nx * r, y: bot.y - ny * r}, {x: top.x - nx * r, y: top.y - ny * r}]);
    const ink = look === 'engraved' ? engInk : look === 'flat' ? outline : BOOM_PALE;
    const canFill = look === 'engraved' ? engGround : CAN;
    const bands = [0.3, 0.55, 0.8].map((u) => ({x: top.x + dx * u, y: top.y + dy * u}));
    items.push({depth: Math.min(a.z, c.z) - 0.06, node: (
      <g key="boomant" data-part="boom-antenna">
        <path d={`M${a.x.toFixed(1)} ${a.y.toFixed(1)} L${b.x.toFixed(1)} ${b.y.toFixed(1)} L${c.x.toFixed(1)} ${c.y.toFixed(1)}`}
          fill="none" stroke={ink} strokeWidth={lw * 1.6} strokeLinecap="round" strokeLinejoin="round"
          {...(look === 'engraved' ? drawOn(on) : {})} />
        <path d={can} fill={canFill} stroke={look === 'engraved' ? engInk : look === 'flat' ? outline : CAN_DARK}
          strokeWidth={lw * (look === 'flat' ? 1.4 : 0.9)} strokeLinejoin="round" {...(look === 'engraved' ? drawOn(on) : {})} />
        {bands.map((p, i) => <line key={i} x1={p.x - nx * r} y1={p.y - ny * r} x2={p.x + nx * r} y2={p.y + ny * r}
          stroke={look === 'engraved' ? engFine : CAN_DARK} strokeWidth={lw * 0.8} />)}
        <ellipse cx={top.x} cy={top.y} rx={r * 1.35} ry={r * 0.55} fill={look === 'engraved' ? engGround : BOOM_PALE}
          stroke={look === 'engraved' ? engInk : look === 'flat' ? outline : '#9aa1ab'} strokeWidth={lw * 0.9}
          transform={`rotate(${(Math.atan2(ny, nx) * 180) / Math.PI} ${top.x} ${top.y})`} />
      </g>
    )});
  }

  items.sort((a, b) => b.depth - a.depth);       // far to near
  const rise = look === 'lit' ? (1 - on) * h * 0.04 : 0;
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      <g opacity={look === 'engraved' ? 1 : on}
        transform={look === 'flat'
          ? `translate(${w / 2} ${h / 2}) scale(${Math.max(0.001, pop)}) translate(${-w / 2} ${-h / 2})`
          : `translate(0 ${rise})`}>
        {items.map((it) => it.node)}
      </g>
    </svg>
  );
};
