// The device a DeviceDemo / DeviceHero beat is performed on — its geometry and its three looks.
//
// deviceGeometry() is THE one definition of where a device and its screen sit. The drawing below, the camera
// and the gestures in the registers, and scripts/device_geometry.py (the legibility and fidelity gates) all use
// it; a parity test holds the Python port to it. Numbers come from deviceSpec.json, shared with the Python side.
//
// REAL PROPORTIONS. A device drawn for a screenshot is the MODEL that screenshot came from (deviceSpec.json
// `models`: Apple's published pixels, ppi and case size, read on apple.com — scripts/device_models.py picks it
// from the screenshot's own pixel size). Its screen is px / ppi — the size of the pixels themselves — so the
// screenshot fills it exactly; the case around it is the published case, so the bezel is the real bezel; and
// every corner is CONCENTRIC: the case's corner is the screen's corner plus the bezel. A screenshot no model
// matches is drawn on its generic KIND, in the proportions of the kind's `like` model.
import React from 'react';
import spec from './deviceSpec.json';
import {CONTENT_TOP, contentBottom} from './layout';
import {mix, type DesignDNA} from './dna';
import {keyOf} from './light';
import {CarryAnchor} from './carry';
import {laptopCamera, laptopScreenTransform, laptopBounds, LaptopBody, LaptopDefs, type LaptopPose} from './laptop3d';

export type {LaptopPose} from './laptop3d';

export type DeviceKind = 'phone' | 'watch' | 'tablet' | 'tablet-landscape' | 'laptop' | 'monitor';
export type DeviceLook = 'flat' | 'real' | 'screen';
/** a key of deviceSpec.json `models` — a named type, not `string`: a prop of it is plumbing, never copy */
export type DeviceModel = string;
export type Placement = 'center' | 'left' | 'right';
export type Rect = {x: number; y: number; w: number; h: number};
export type Bezels = {l: number; r: number; t: number; b: number};
export type DeviceGeom = {
  kind: DeviceKind; look: DeviceLook; model: string | null;
  body: Rect; face: Rect; screen: Rect; bezel: number; bezels: Bezels;
  /** the screen's corner radius, and the case's (= radius + bezel: concentric) */
  radius: number; outerRadius: number;
  /** the screen's corners: continuous-curvature (a squircle), or a plain circle (the watch's measured display) */
  smoothScreen: boolean; topRoundOnly: boolean;
  island: Rect | null; notch: Rect | null; base: Rect | null; strip: Rect | null;
  /** a watch's straps (behind the case), crown and side button; a phone's or tablet's side buttons */
  bands: Rect[]; crown: Rect | null; sideButton: Rect | null; buttons: Rect[];
};

type Model = {kind: string; published: {px: number[]; ppi: number; caseMm: number[]}; displayRadiusMm: number;
  island?: boolean; notch?: boolean; topRoundOnly?: boolean; circleDisplay?: boolean; scale?: number[]};
type OldBody = {bezel: number; radius: number; base: number; overhang: number; strip: number};
const MODELS = spec.models as unknown as Record<string, Model>;
const KINDS = spec.kinds as unknown as Record<string, {like: string; landscape?: boolean; notch?: boolean}>;
const RATIO = spec.screenRatio as Record<DeviceKind, number[]>;
const BODY = spec.body as unknown as Record<DeviceLook, Record<string, OldBody>>;
const PLACE = spec.placementX as Record<Placement, number>;
const P = spec.parts;

export const isTouch = (kind: DeviceKind): boolean => Boolean((spec.touch as Record<string, boolean>)[kind]);
export const modelNames = (): string[] => Object.keys(MODELS).filter((k) => !k.startsWith('_'));
const baseKind = (k: DeviceKind): string => (k === 'tablet-landscape' ? 'tablet' : k);

export const alpha = (hex: string, a: number): string => {
  const m = /^#([0-9a-f]{6})$/i.exec(String(hex || '').trim());
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

/** The proportions a kind or a model is drawn in, in units of the SCREEN's width. scripts/device_geometry.py
 *  `proportions` is the same function, held to this one by tests/test_device_runtime.py. */
type Props = {ratio: number; bl: number; bt: number; bb: number; inner: number; ov: number;
  above: number; below: number; base: number; strip: number; island: boolean; notch: boolean;
  smooth: boolean; topRoundOnly: boolean};
export const proportions = (kind: DeviceKind, look: DeviceLook, model: string | null = null): Props => {
  const m = model ? MODELS[model] : null;
  if (model && (!m || model.startsWith('_'))) throw new Error(`device: no model ${model} — one of ${modelNames().join(', ')}`);
  if (m && m.kind !== baseKind(kind)) throw new Error(`device: ${model} is a ${m.kind}, not a ${kind}`);
  const landscape = kind === 'tablet-landscape';
  if (kind === 'monitor') {
    const b = BODY[look]?.monitor;
    if (!b) throw new Error(`device: no geometry for ${kind} / ${look}`);
    const [rw, rh] = RATIO.monitor;
    return {ratio: rh / rw, bl: b.bezel, bt: b.bezel, bb: b.bezel, inner: b.radius, ov: b.overhang, above: 0,
      below: 0, base: b.base, strip: b.strip, island: false, notch: false, smooth: false, topRoundOnly: false};
  }
  const like = m ?? MODELS[KINDS[kind]?.like ?? ''];
  if (!like) throw new Error(`device: no geometry for ${kind} / ${look}`);
  if (!['flat', 'real', 'screen'].includes(look)) throw new Error(`device: no geometry for ${kind} / ${look}`);
  let [pw, ph] = like.published.px;
  let [cw, ch] = like.published.caseMm;
  if (landscape) [pw, ph, cw, ch] = [ph, pw, ch, cw];
  const mm = 25.4 / like.published.ppi;
  const sW = pw * mm, sH = ph * mm;
  const ratio = m ? (landscape ? m.published.px[0] / m.published.px[1] : m.published.px[1] / m.published.px[0])
    : RATIO[kind][1] / RATIO[kind][0];
  const inner = like.displayRadiusMm / sW;
  const bk = baseKind(kind);
  const smooth = !like.circleDisplay;
  const topRoundOnly = Boolean(like.topRoundOnly);
  if (look === 'screen') {
    const strip = bk === 'laptop' ? BODY.screen.laptop.strip : 0;
    return {ratio, bl: 0, bt: 0, bb: 0, inner, ov: 0, above: 0, below: 0, base: 0, strip, island: false,
      notch: false, smooth, topRoundOnly};
  }
  const bl = (cw - sW) / 2 / sW;
  let bt = (ch - sH) / 2 / sW, bb = bt;
  let ov = 0, above = 0, below = 0, base = 0;
  if (bk === 'laptop') {
    bt = bl * P.laptopTopBezelOfSide;
    bb = (ch - sH) / sW - bt;
    ov = P.laptopOverhang;
    base = P.laptopBase;
  } else if (bk === 'watch') {
    const caseW = 1 + 2 * bl, caseH = ratio + 2 * bt;
    ov = P.crown.out * caseW;
    above = below = P.band.len * caseH;
  } else {
    ov = (P.buttonOut as Record<string, number>)[bk] ?? 0;
  }
  const notch = bk === 'laptop' && Boolean(m ? m.notch : KINDS[kind]?.notch);
  const island = bk === 'phone' && (m ? Boolean(m.island) : true);
  return {ratio, bl, bt, bb, inner, ov, above, below, base, strip: 0, island, notch, smooth, topRoundOnly};
};

export const deviceGeometry = (kind: DeviceKind, look: DeviceLook, W: number, H: number,
                               placement: Placement = 'center', kicker = false, model: string | null = null): DeviceGeom => {
  if (!RATIO[kind]) throw new Error(`device: no geometry for ${kind} / ${look}`);
  const p = proportions(kind, look, model);
  const top = kicker ? CONTENT_TOP : Math.round(H * spec.zoneTopFrac);
  const zoneH = Math.max(1, contentBottom(W, H) - top);
  const zoneW = W * spec.zoneWidthFill;
  const faceW = 1 + 2 * p.bl, faceH = p.ratio * (1 + p.strip) + p.bt + p.bb;
  const bwPerSw = faceW + 2 * p.ov;
  const bhPerSw = faceH + p.above + p.below + p.base;
  const sw = Math.min(zoneW / bwPerSw, zoneH / bhPerSw);
  const sh = sw * p.ratio;
  const bodyW = sw * bwPerSw, bodyH = sw * bhPerSw;
  const margin = (W - zoneW) / 2;
  const bodyX = Math.min(Math.max(W * PLACE[placement] - bodyW / 2, margin), W - margin - bodyW);
  const bodyY = top + (zoneH - bodyH) / 2;
  const fx = bodyX + sw * p.ov, fy = bodyY + sw * p.above;
  const sx = fx + sw * p.bl;
  const sy = fy + sw * p.bt + sh * p.strip;
  const R = Math.round;
  const rect = (x: number, y: number, w: number, h: number): Rect => ({x: R(x), y: R(y), w: R(w), h: R(h)});
  const fW = sw * faceW, fH = sw * faceH;
  const bk = baseKind(kind);
  const bands: Rect[] = [], buttons: Rect[] = [];
  let crown: Rect | null = null, sideButton: Rect | null = null;
  if (look !== 'screen' && bk === 'watch') {
    const bw = P.band.w * fW;
    bands.push(rect(fx + (fW - bw) / 2, bodyY, bw, sw * p.above + fH * 0.2));
    bands.push(rect(fx + (fW - bw) / 2, fy + fH * 0.8, bw, sw * p.below + fH * 0.2));
    const tuck = fW * 0.01;
    crown = rect(fx + fW - tuck, fy + fH * (P.crown.y - P.crown.h / 2), sw * p.ov + tuck, fH * P.crown.h);
    sideButton = rect(fx + fW - tuck, fy + fH * (P.sideButton.y - P.sideButton.h / 2), P.sideButton.out * fW + tuck,
      fH * P.sideButton.h);
  } else if (look !== 'screen' && p.ov > 0 && (bk === 'phone' || bk === 'tablet')) {
    const out = sw * p.ov, tuck = Math.max(1, out * 0.5);
    // [side, y, h] as fractions of the case height — design (deviceSpec.json `models.*.design.buttons`)
    const spots: Array<[number, number, number]> = bk === 'phone'
      ? [[-1, 0.19, 0.045], [-1, 0.255, 0.075], [-1, 0.345, 0.075], [1, 0.27, 0.11], [1, 0.6, 0.07]]
      : (kind === 'tablet' ? [[1, 0.08, 0.045], [1, 0.14, 0.045]] : [[1, 0.1, 0.06], [1, 0.19, 0.06]]);
    spots.forEach(([side, y, h]) => buttons.push(rect(side < 0 ? fx - out : fx + fW - tuck, fy + fH * y, out + tuck, fH * h)));
  }
  return {
    kind, look, model,
    body: rect(bodyX, bodyY, bodyW, bodyH),
    face: rect(fx, fy, fW, fH),
    screen: rect(sx, sy, sw, sh),
    bezel: R(sw * p.bl),
    bezels: {l: R(sw * p.bl), r: R(sw * p.bl), t: R(sw * p.bt), b: R(sw * p.bb)},
    radius: R(sw * p.inner),
    outerRadius: look === 'screen' ? R(sw * p.inner) : R(sw * (p.inner + p.bl)),
    smoothScreen: p.smooth, topRoundOnly: p.topRoundOnly,
    island: p.island ? rect(sx + (sw * (1 - P.island.w)) / 2, sy + sw * P.island.top, sw * P.island.w, sw * P.island.h) : null,
    notch: p.notch ? rect(sx + (sw * (1 - P.notch.w)) / 2, sy, sw * P.notch.w, sh * P.notch.h) : null,
    base: p.base > 0 ? rect(bodyX, fy + fH, bodyW, sw * p.base) : null,
    strip: p.strip > 0 ? rect(sx, sy - sh * p.strip, sw, sh * p.strip) : null,
    bands, crown, sideButton, buttons,
  };
};

/** The device's FACE — the screen and its bezel (the 'screen' look: the window panel, title strip included).
 *  Everything the Device draws there stays inside it, and a camera that pushes in stays on it: the BODY also
 *  spans a laptop's base, which overhangs the lid, a monitor's stand, a watch's straps and crown. */
export const deviceFace = (g: DeviceGeom): Rect => {
  const s = g.screen;
  if (g.look === 'screen') {
    const top = g.strip ? g.strip.y : s.y;
    return {x: s.x, y: top, w: s.w, h: s.y + s.h - top};
  }
  return g.face;
};

/** The look a beat gets when it names none: realistic on a dark ground, flat on a light one. */
export const defaultLook = (dna: DesignDNA | null): DeviceLook => (dna && keyOf(dna) === 'dark' ? 'real' : 'flat');

/** A rounded rectangle as an SVG path. `smooth`: a continuous-curvature corner (a superellipse of exponent 3.2
 *  over 1.5 r — the curve meets the edge without the jump in curvature a circular arc has, and its 45° point is
 *  where a circle of radius r would put it, so a radius means the same in both). `topOnly`: the bottom two
 *  corners are square (a laptop's display). Shared by the case outline, the glass and the screen's clip, so
 *  each is the same curve at its own radius — concentric by construction. */
export const roundRectPath = (x: number, y: number, w: number, h: number, r: number, smooth = true,
                              topOnly = false, dx = 0, dy = 0): string => {
  const n = smooth ? 3.2 : 2, k = smooth ? 1.5 : 1;
  const e = Math.max(0, Math.min(r * k, w / 2, h / 2));
  const N = 14;
  const f = (v: number) => (Math.round(v * 100) / 100).toString();
  const pts: string[] = [];
  // One corner: (cx, cy) is the corner's own point, (sx, sy) points into the rectangle. a = 0 is the curve's end
  // on the vertical edge, a = 90° its end on the horizontal one; `rev` walks it the other way, so the four
  // corners are visited clockwise.
  const corner = (cx: number, cy: number, sx: number, sy: number, rev: boolean, ee: number) => {
    for (let i = 0; i <= N; i++) {
      const a = ((rev ? N - i : i) / N) * (Math.PI / 2);
      const u = Math.pow(Math.cos(a), 2 / n), v = Math.pow(Math.sin(a), 2 / n);
      pts.push(`${f(cx + sx * ee * (1 - u) + dx)} ${f(cy + sy * ee * (1 - v) + dy)}`);
    }
  };
  const eb = topOnly ? 0 : e;
  corner(x, y, 1, 1, false, e);                 // top-left: left edge -> top edge
  corner(x + w, y, -1, 1, true, e);             // top-right: top edge -> right edge
  if (eb > 0) {
    corner(x + w, y + h, -1, -1, false, eb);    // bottom-right: right edge -> bottom edge
    corner(x, y + h, 1, -1, true, eb);          // bottom-left: bottom edge -> left edge
  } else {
    pts.push(`${f(x + w + dx)} ${f(y + h + dy)}`, `${f(x + dx)} ${f(y + h + dy)}`);
  }
  return 'M' + pts.join(' L') + ' Z';
};

const INK_D0 = '#14171c', BG_D0 = '#eef1f4';
// @decor: the metals and glass of a realistic device — materials, not a reading about anything the film named
const METAL_HI = '#eef0f3', METAL_MID = '#8d929b', METAL_LO = '#3e434b', METAL_DEEP = '#22252b';
const GLASS = '#050608', BAND = '#2a2d33';

const useSvgId = (): string => React.useId().replace(/[^a-zA-Z0-9_-]/g, '');

/** The metal of a case or a part: a lit gradient across it (the key from the upper left), a polish line on its
 *  edge. `axis` is the direction the gradient runs: across a cylinder (a crown) it is its height. */
const MetalGrad: React.FC<{id: string; hi: string; mid: string; lo: string; deep: string; axis?: 'diag' | 'v' | 'h'}> =
  ({id, hi, mid, lo, deep, axis = 'diag'}) => {
    const xy = axis === 'v' ? {x1: '0', y1: '0', x2: '0', y2: '1'} : axis === 'h' ? {x1: '0', y1: '0', x2: '1', y2: '0'}
      : {x1: '0', y1: '0', x2: '1', y2: '1'};
    return (
      <linearGradient id={id} {...xy}>
        <stop offset="0" stopColor={hi} />
        <stop offset={axis === 'diag' ? '0.18' : '0.3'} stopColor={mid} />
        <stop offset={axis === 'diag' ? '0.5' : '0.55'} stopColor={lo} />
        <stop offset={axis === 'diag' ? '0.78' : '0.8'} stopColor={deep} />
        <stop offset="1" stopColor={mid} />
      </linearGradient>
    );
  };

/** `pose` turns a LAPTOP (runtime/laptop3d.tsx): a laptop is one 3D object, so it is turned by its own camera — the
 *  deck, the hinge, the lid and the screen content on it together — never by a CSS rotate of its flat picture, which
 *  slanted the lid while the base stayed a front-on line. Other devices are slabs and ignore it. */
/** `turned` is for a SLAB (phone, tablet, watch) that the CALLER turns with a CSS rotateX/rotateY: a slab has a
 *  thickness, and turned its near edge shows — the published case depth (caseMm[2]) drawn as the swept outline on the
 *  side the turn brings toward the viewer, so a turned phone is not a sheet of paper. Same degrees as the caller's
 *  rotateY (yaw) and rotateX (pitch). */
export const Device: React.FC<{g: DeviceGeom; dna: DesignDNA | null; pose?: LaptopPose;
  turned?: {yaw?: number; pitch?: number}; children?: React.ReactNode}> =
  ({g, dna, pose, turned, children}) => {
  const uid = useSvgId();
  const ink = dna?.fg ?? INK_D0;
  const bg = dna?.bg ?? BG_D0;
  const s = g.screen;
  const real = g.look === 'real';
  const hi = mix(METAL_HI, bg, 0.08), mid = mix(METAL_MID, bg, 0.08), lo = mix(METAL_LO, bg, 0.08);
  const deep = mix(METAL_DEEP, bg, 0.08);
  const face = deviceFace(g);
  const body = g.body;
  const isWatch = g.kind === 'watch';
  const isLaptop = g.kind === 'laptop';
  // a laptop's ONE camera: the body is drawn by it, and the screen's DOM is put on the lid by the same projection
  const lc = isLaptop && g.look !== 'screen' ? laptopCamera(g, pose) : null;
  const lb = lc ? laptopBounds(lc) : null;
  // The case outline: continuous curvature at the case's own radius (screen radius + bezel — concentric).
  const caseR = g.outerRadius;
  const rim = g.look === 'screen' ? 0
    : Math.max(1, Math.round(s.w * ((P.rim as Record<string, number>)[baseKind(g.kind)] ?? 0.006)));
  const casePath = roundRectPath(face.x, face.y, face.w, face.h, caseR, true, false, -body.x, -body.y);
  const glassR = Math.max(0, caseR - rim);
  // a turned slab's edge (`turned`): the back outline sits T·tan(turn) behind the face on the near side, T the case's
  // published depth; the wall between is swept in steps a pixel or two apart
  const edgeSweep: string[] = [];
  if (turned && !isLaptop && g.look !== 'screen') {
    const pub = g.model ? MODELS[g.model]?.published : MODELS[KINDS[baseKind(g.kind)]?.like ?? '']?.published;
    const depth = pub?.caseMm?.[2];
    if (depth) {
      const across = g.kind === 'tablet-landscape' ? pub!.caseMm[1] : pub!.caseMm[0];
      const k = face.w / across;
      const ex = -depth * k * Math.tan(((turned.yaw ?? 0) * Math.PI) / 180);
      const ey = depth * k * Math.tan(((turned.pitch ?? 0) * Math.PI) / 180);
      const n = Math.min(24, Math.max(1, Math.ceil(Math.hypot(ex, ey) / 1.5)));
      for (let i = n; i >= 1; i--) {
        edgeSweep.push(roundRectPath(face.x + (ex * i) / n, face.y + (ey * i) / n, face.w, face.h, caseR, true, false,
          -body.x, -body.y));
      }
    }
  }
  const glassPath = roundRectPath(face.x + rim, face.y + rim, face.w - 2 * rim, face.h - 2 * rim, glassR, true, false,
    -body.x, -body.y);
  const screenClip = roundRectPath(0, 0, s.w, s.h, g.radius, g.smoothScreen, g.topRoundOnly || Boolean(g.strip));
  const shadowDy = Math.round(face.h * 0.045), shadowBlur = Math.round(face.h * 0.06);
  const id = (n: string) => `dv${uid}${n}`;
  const flatPart = mix(ink, bg, 0.22);

  // a part drawn as a rounded rect, in the body's coordinates
  const part = (r: Rect, rad: number, fill: string, key: string, extra?: React.SVGProps<SVGRectElement>) => (
    <rect key={key} x={r.x - body.x} y={r.y - body.y} width={r.w} height={r.h} rx={rad} ry={rad} fill={fill} {...extra} />
  );

  const crownRidges = (c: Rect): React.ReactNode[] => {
    // the knurling runs along the crown's axis, so seen from the front it is a stack of lines across the crown,
    // closing up toward its top and bottom where the cylinder turns away (spaced by the cosine of the angle)
    const N = P.crown.ridges, out: React.ReactNode[] = [];
    const x0 = c.x - body.x + c.w * 0.32, x1 = c.x - body.x + c.w - Math.max(1, c.w * 0.04);
    for (let i = 1; i < N; i++) {
      const yy = c.y - body.y + c.h / 2 - (c.h / 2) * 0.92 * Math.cos((Math.PI * i) / N);
      const sw = Math.max(0.6, c.h / N * 0.45 * Math.sin((Math.PI * i) / N));
      out.push(<line key={'d' + i} x1={x0} x2={x1} y1={yy} y2={yy} stroke={real ? 'rgba(0,0,0,0.55)' : alpha(bg, 0.55)}
        strokeWidth={sw} />);
      if (real) out.push(<line key={'l' + i} x1={x0} x2={x1} y1={yy + sw} y2={yy + sw} stroke="rgba(255,255,255,0.22)"
        strokeWidth={sw * 0.6} />);
    }
    return out;
  };

  const svgBody = g.look === 'screen' ? null : lc && lb ? (
    <svg data-carry-part="device" data-device-body={g.kind} data-device-model={g.model ?? g.kind}
      width={Math.ceil(lb.w)} height={Math.ceil(lb.h)}
      style={{position: 'absolute', left: Math.floor(lb.x), top: Math.floor(lb.y), overflow: 'visible'}}>
      <LaptopDefs uid={uid} c={lc} ox={Math.floor(lb.x)} oy={Math.floor(lb.y)} metal={{hi, mid, lo, deep}} />
      <LaptopBody g={g} c={lc} real={real} ink={ink} bg={bg} ox={Math.floor(lb.x)} oy={Math.floor(lb.y)} uid={uid}
        metal={{hi, mid, lo, deep}} />
    </svg>
  ) : (
    <svg data-carry-part="device" data-device-body={g.kind} data-device-model={g.model ?? g.kind} width={body.w} height={body.h}
      style={{position: 'absolute', left: body.x, top: body.y, overflow: 'visible'}}>
      <defs>
        <MetalGrad id={id('m')} hi={hi} mid={mid} lo={lo} deep={deep} />
        <MetalGrad id={id('mv')} hi={hi} mid={mid} lo={lo} deep={deep} axis="v" />
        <MetalGrad id={id('mh')} hi={hi} mid={mid} lo={lo} deep={deep} axis="h" />
        <linearGradient id={id('edge')} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.85" />
          <stop offset="0.35" stopColor="#ffffff" stopOpacity="0.12" />
          <stop offset="0.7" stopColor="#ffffff" stopOpacity="0.04" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0.35" />
        </linearGradient>
        <linearGradient id={id('gl')} x1="0" y1="0" x2="0.6" y2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity={isWatch ? 0.5 : 0.32} />
          <stop offset="0.3" stopColor="#ffffff" stopOpacity="0.06" />
          <stop offset="0.75" stopColor="#ffffff" stopOpacity="0.02" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0.2" />
        </linearGradient>
        <radialGradient id={id('glass')} cx="0.35" cy="0.25" r="0.9">
          <stop offset="0" stopColor="#14161b" />
          <stop offset="1" stopColor={GLASS} />
        </radialGradient>
        <linearGradient id={id('band')} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor={mix(BAND, '#000000', 0.55)} />
          <stop offset="0.16" stopColor={mix(BAND, '#ffffff', 0.04)} />
          <stop offset="0.42" stopColor={mix(BAND, '#ffffff', 0.12)} />
          <stop offset="0.7" stopColor={BAND} />
          <stop offset="1" stopColor={mix(BAND, '#000000', 0.6)} />
        </linearGradient>
        <linearGradient id={id('aoUp')} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#000000" stopOpacity="0.55" />
          <stop offset="1" stopColor="#000000" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={id('aoDn')} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#000000" stopOpacity="0.55" />
          <stop offset="1" stopColor="#000000" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={id('lug')} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor={deep} />
          <stop offset="0.25" stopColor={lo} />
          <stop offset="0.5" stopColor={mid} />
          <stop offset="0.75" stopColor={lo} />
          <stop offset="1" stopColor={deep} />
        </linearGradient>
        <pattern id={id('brush')} width="3" height="3" patternUnits="userSpaceOnUse">
          <rect width="3" height="1" fill="#ffffff" opacity="0.05" />
        </pattern>
        <filter id={id('sh')} x="-30%" y="-30%" width="160%" height="170%">
          <feDropShadow dx="0" dy={shadowDy} stdDeviation={shadowBlur / 2} floodColor={real ? '#000000' : ink}
            floodOpacity={real ? 0.5 : 0.16} />
        </filter>
      </defs>
      <g filter={`url(#${id('sh')})`}>
        {/* a watch's straps go BEHIND the case, through its lugs */}
        {g.bands.map((b, i) => {
          const top = i === 0;
          const bx = b.x - body.x, by = b.y - body.y;
          const tap = b.w * P.band.taper / 2;
          const endR = b.w * 0.42;
          // tapering away from the case: the far end is narrower; the end is rounded
          const far = top ? by : by + b.h, near = top ? by + b.h : by;
          const dir = top ? 1 : -1;
          const d = `M${bx} ${near} L${bx + tap} ${far + dir * endR} Q${bx + tap} ${far} ${bx + b.w / 2} ${far} ` +
            `Q${bx + b.w - tap} ${far} ${bx + b.w - tap} ${far + dir * endR} L${bx + b.w} ${near} Z`;
          const holes: React.ReactNode[] = [];
          if (!top) {
            // the sizing holes: a row along the strap's centre, from just inside its end toward the case
            for (let k = 0; k < 7; k++) {
              const cy = far - b.w * (0.45 + k * 0.22);
              if (cy < near + face.h * 0.3) break;
              holes.push(<ellipse key={k} cx={bx + b.w / 2} cy={cy} rx={b.w * 0.05} ry={b.w * 0.045}
                fill={real ? '#07080a' : alpha(bg, 0.7)} stroke={real ? 'rgba(255,255,255,0.12)' : 'none'} strokeWidth={0.8} />);
            }
          }
          const lugH = face.h * 0.032;
          const lugY = top ? face.y - body.y - lugH * 0.85 : face.y - body.y + face.h - lugH * 0.15;
          // the strap's shade where it passes under the case: darkest at the lug, gone a band-width away
          const aoY = top ? lugY - b.w * 0.5 : lugY + lugH;
          return (
            <g key={'band' + i}>
              <path d={d} fill={real ? `url(#${id('band')})` : flatPart} />
              {real ? <path d={d} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={1} /> : null}
              {real ? <rect x={bx} y={aoY} width={b.w} height={b.w * 0.5} fill={`url(#${id(top ? 'aoUp' : 'aoDn')})`} /> : null}
              {top ? (
                // the pin, seated in the strap near its end, with its ring
                <circle cx={bx + b.w / 2} cy={far + b.w * 0.62} r={b.w * 0.07}
                  fill={real ? `url(#${id('m')})` : alpha(bg, 0.6)} stroke={real ? 'rgba(0,0,0,0.6)' : 'none'}
                  strokeWidth={Math.max(1, b.w * 0.012)} />
              ) : holes}
              {/* the lug: the band's connector, seated in the case's slot */}
              <rect x={bx} y={lugY} width={b.w} height={lugH} rx={lugH * 0.35}
                fill={real ? `url(#${id('lug')})` : mix(ink, bg, 0.1)} />
            </g>
          );
        })}
        {g.crown ? (
          <g>
            {/* the crown: a knurled cylinder on a narrower collar */}
            {part({x: g.crown.x, y: g.crown.y + g.crown.h * 0.14, w: g.crown.w * 0.36, h: g.crown.h * 0.72},
              g.crown.h * 0.08, real ? `url(#${id('mv')})` : ink, 'collar')}
            {part({x: g.crown.x + g.crown.w * 0.3, y: g.crown.y, w: g.crown.w * 0.7, h: g.crown.h},
              g.crown.h * 0.14, real ? `url(#${id('mv')})` : ink, 'crown')}
            {crownRidges(g.crown)}
            {real ? part({x: g.crown.x + g.crown.w - Math.max(1.5, g.crown.w * 0.07), y: g.crown.y + g.crown.h * 0.06,
              w: Math.max(1.5, g.crown.w * 0.07), h: g.crown.h * 0.88}, 1, 'rgba(255,255,255,0.35)', 'cap') : null}
          </g>
        ) : null}
        {g.sideButton ? part(g.sideButton, Math.min(g.sideButton.w, g.sideButton.h) / 2,
          real ? `url(#${id('mv')})` : ink, 'side') : null}
        {g.buttons.map((b, i) => part(b, Math.min(b.w, b.h) / 2, real ? `url(#${id('mh')})` : ink, 'btn' + i))}
        {/* the case's EDGE where a turn shows it: the outline swept back by the case's depth, darker than its face */}
        {edgeSweep.map((d, i) => <path key={'edge' + i} d={d} fill={real ? (i === edgeSweep.length - 1 ? lo : deep) : mix(ink, bg, 0.15)} />)}
        {/* the case: the metal, brushed, its polished edge lit from the upper left */}
        <path d={casePath} fill={real ? `url(#${id('m')})` : ink} />
        {real ? (
          <>
            <path d={casePath} fill={`url(#${id('brush')})`} />
            <path d={casePath} fill="none" stroke={`url(#${id('edge')})`} strokeWidth={Math.max(1, rim * 0.35)} />
            {/* the glass: black, a little lit toward the key, its edge catching the light */}
            <path d={glassPath} fill={`url(#${id('glass')})`} />
            <path d={glassPath} fill="none" stroke="rgba(0,0,0,0.85)" strokeWidth={Math.max(1, rim * 0.25)} />
            <path d={roundRectPath(face.x + rim * 1.25, face.y + rim * 1.25, face.w - 2.5 * rim, face.h - 2.5 * rim,
              Math.max(0, caseR - rim * 1.25), true, false, -body.x, -body.y)} fill="none" stroke={`url(#${id('gl')})`}
              strokeWidth={Math.max(1, rim * (isWatch ? 0.5 : 0.3))} />
          </>
        ) : null}
      </g>
      {g.base && g.kind === 'monitor' ? (
        <g>
          <rect x={g.base.w * 0.44} y={g.base.y - body.y} width={g.base.w * 0.12} height={g.base.h * 0.82}
            fill={real ? `url(#${id('mh')})` : ink} />
          <rect x={g.base.w * 0.32} y={g.base.y - body.y + g.base.h * 0.82} width={g.base.w * 0.36} height={g.base.h * 0.18}
            rx={g.base.h * 0.09} fill={real ? `url(#${id('mv')})` : ink} />
        </g>
      ) : null}
    </svg>
  );

  return (
    <>
      {/* TWO carry anchors (runtime/carry): `device`, the whole face — a container carries the device itself — and
          `screen`, the screen alone — a container carries what is ON it into another frame. */}
      <CarryAnchor id="device" x={face.x} y={face.y} w={face.w} h={face.h}
        radius={g.look === 'screen' ? g.radius : g.outerRadius} />
      {svgBody}
      {g.look === 'screen' ? (
        <div data-carry-part="device" data-device-body={g.kind} style={{position: 'absolute', left: face.x, top: face.y,
          width: face.w, height: face.h, borderRadius: g.radius, background: mix(bg, '#ffffff', 0.85),
          boxShadow: `0 ${Math.round(s.h * 0.03)}px ${Math.round(s.h * 0.07)}px ${alpha(ink, 0.22)}`}} />
      ) : null}
      {g.strip ? (
        <div data-carry-part="device" style={{position: 'absolute', left: g.strip.x, top: g.strip.y, width: g.strip.w, height: g.strip.h,
          background: mix(bg, ink, 0.06), borderRadius: `${g.radius}px ${g.radius}px 0 0`}}>
          {[0, 1, 2].map((i) => (   // @positional: a window's three buttons are the same three on every window
            <span key={i} style={{position: 'absolute', top: g.strip!.h * 0.32, left: g.strip!.h * (0.5 + i * 0.55),
              width: g.strip!.h * 0.36, height: g.strip!.h * 0.36, borderRadius: '50%', background: mix(bg, ink, 0.25)}} />
          ))}
        </div>
      ) : null}
      <div data-carry="screen" data-carry-part="device" data-device-screen={g.model ?? g.kind}
        style={{position: 'absolute', left: s.x, top: s.y, width: s.w, height: s.h, overflow: 'hidden',
          borderRadius: g.strip ? `0 0 ${g.radius}px ${g.radius}px` : (g.topRoundOnly ? `${g.radius}px ${g.radius}px 0 0` : g.radius),
          clipPath: g.strip ? undefined : `path('${screenClip}')`, background: '#000',
          transformOrigin: '0 0', transform: lc ? laptopScreenTransform(g, lc) : undefined}}>
        {children}
        {g.notch ? (
          // the notch is ON the screen: drawn inside it, so a turned laptop carries it with the display
          <div data-carry-part="device" style={{position: 'absolute', left: g.notch.x - s.x, top: 0, width: g.notch.w,
            height: g.notch.h + (g.notch.y - s.y), borderRadius: `0 0 ${g.notch.h * 0.32}px ${g.notch.h * 0.32}px`,
            background: real ? GLASS : ink}}>
            {real ? <span style={{position: 'absolute', left: g.notch.w / 2 - g.notch.h * 0.17, top: g.notch.h * 0.33,
              width: g.notch.h * 0.34, height: g.notch.h * 0.34, borderRadius: '50%',
              background: 'radial-gradient(circle at 35% 35%, #26304a, #050608 70%)'}} /> : null}
          </div>
        ) : null}
        {real ? (
          // the glass over the display: one soft reflection from the key, and a faint lit band along its top edge
          <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
            background: 'linear-gradient(122deg, rgba(255,255,255,0.13), rgba(255,255,255,0.03) 30%, rgba(255,255,255,0) 46%), ' +
              'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0) 6%)'}} />
        ) : null}
      </div>
      {g.island ? (
        <div data-carry-part="device" style={{position: 'absolute', left: g.island.x, top: g.island.y, width: g.island.w, height: g.island.h,
          borderRadius: g.island.h, background: real ? '#000000' : ink,
          boxShadow: real ? 'inset 0 0 0 0.5px rgba(255,255,255,0.08)' : undefined}}>
          {real ? <span style={{position: 'absolute', right: g.island.h * 0.32, top: g.island.h * 0.3, width: g.island.h * 0.4,
            height: g.island.h * 0.4, borderRadius: '50%', background: 'radial-gradient(circle at 35% 35%, #2a3550, #07090d 70%)'}} /> : null}
        </div>
      ) : null}
    </>
  );
};
