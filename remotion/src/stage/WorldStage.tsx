// STAGE · WorldStage — ONE world that a camera travels through across a run of beats: the film's own objects (its
// photographs, its drawn things, its words) stand at places in one space, and each beat of the run is a CAMERA
// KEYFRAME — which object it frames, from where, and how it gets there — plus what appears or changes. It is the shape
// of a Kurzgesagt or Powers-of-Ten film: a dolly from the Sun to the Earth, a crane up through the bands of the sky, a
// zoom from a planet down to the town under its aurora, without a cut, because it is one place.
//
// What it is for: a subject that HAS a geography — scales, distances, layers, a route — which a row of flat beats
// cannot show, because each beat starts in its own frame. Every word, picture and shape comes from props.
//
// THE STATE (each beat's shot_props, and each of its `steps`, say what changes — runtime/stageRun.tsx):
//   world.objects {id: {...}}   the world: each object `kind` image | globe | disc | field | stream | stars | band |
//                               glow | volume (runtime/volume: `form` curtain | shafts | nebula | flame | layer) | type, standing `at` [x, y, z] (world units: 1 = the frame's short side; +y is
//                               DOWN, +z toward the viewer) with width `w`, or nested `in` a parent (`uv` its centre
//                               on the parent, `span` its width as a share of the parent's, `dz` its depth in its own
//                               widths). `on` 0..1 fades it; `label` names it (shown while `labels` lists it).
//   camera {frame, fill?, offset?, yaw?, pitch?, move?}   frame a named object (fill: its share of the content zone;
//                               offset [dx, dy]: shares of the zone; yaw/pitch: degrees round it — +pitch looks up);
//                               `move` is HOW this keyframe's camera gets there: dolly | crane | tilt | orbit |
//                               scale-zoom (stage/worldCore.ts says what each does)
//   labels [ids]                which objects' names are shown, each beside its object, kept in the content zone
//   title, highlight            the beat's title line and the word of it to mark (optional)
//   backdrop                    the DNA colour the world's space is (bg by default)
//   drift                       0 stops the camera's breathing while it holds (default 1)
//   move (a beat's own)         seconds its keyframe's move takes (runtime/stageRun beatMoveFrames)
//
// HOW IT IS DRAWN, and why (stage/worldCore.ts has the maths). Every object is a plane facing the lens, so each one
// projects to an exact scale and translate and is painted as a flat 2D element at its final size — sharp photographs
// and sharp type at every distance, no compositor rescaling. The camera's moves are summed along their own paths
// (an arc, an exponential zoom), on the stage's springs. Depth of field comes from distance to what the camera
// frames; motion blur from each object's own speed on screen. Type in the world is a word ON a plane that faces the
// lens (it scales with its distance and fades out before it is too small to read), or a label standing beside an
// object at a reading size. A missing object is a loud error, never an empty frame.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {geoCircle} from 'd3-geo';
import {clamp01, hash01} from '../runtime/motion';
import {useDNA, mix, relLum} from '../runtime/dna';
import {hex6} from '../runtime/hexColor';
import {TITLE_Y, contentBottom, CONTENT_TOP, CAPTION_SIZE_FRAC, CAPTION_MARGIN_FRAC, CAPTION_LEAD_CJK,
  CAPTION_LINES} from '../runtime/layout';
import {SafeZoneContext, captionBottomY, SAFE_CAPTION_SCALE} from '../runtime/safeZone';
import {useGlide, usePlaceGlide} from '../runtime/glide';
import {PERSP_FRAC} from '../runtime/stage3d';
import {Earth} from '../runtime/earth';
import {resFor} from '../runtime/geo';
import {useStageRun, State} from '../runtime/stageRun';
import {Volume, type VolumeSpec, type VolumeForm} from '../runtime/volume';
import {blurOf} from './surface';
import {layoutWorld, targetCam, framingOf, camAtFrame, project, defocus, nestFade, passFade, ancestors, D2R, type Cam, type CamKey,
  type Framing, type ObjSpec, type Placed, type View, type Zone, type V3} from './worldCore';

const BASE_TYPE_PX = 100;            // a world word is laid out at this size and scaled by its projection
const LOCAL = 1000;                  // a drawn object's local width (its SVG's user units)
const CJK_CH = /[⺀-鿿豈-﫿！-｠　-〿]/;

type Obj = ObjSpec & {
  image?: string; edge?: 'feather' | 'circle' | 'hard' | 'none'; color?: string; color2?: string; label?: string;
  text?: string; size?: number; weight?: number; bloom?: number; dof?: number; lon?: number; lat?: number;
  ring?: {lon: number; lat: number; radius: number; color?: string; width?: number} | null;
  obstacle?: number[]; seed?: number; count?: number; speed?: number; sun?: 'left' | 'right'; rays?: boolean;
  imageZoom?: number; labelAt?: number[]; credit?: string;
  /** a `volume` object: runtime/volume's form and its knobs */
  form?: VolumeForm; intensity?: number; bands?: VolumeSpec['bands']; sheets?: number; source?: [number, number];
  occluder?: VolumeSpec['occluder']; open?: number; star?: [number, number]; base?: [number, number]; spread?: number;
};

const objectsOf = (st: State): Record<string, Obj> => {
  const w = st.world as {objects?: unknown} | undefined;
  const o = w && typeof w === 'object' ? w.objects : undefined;
  return o && typeof o === 'object' && !Array.isArray(o) ? (o as Record<string, Obj>) : {};
};

export const WorldStage: React.FC<Record<string, unknown>> = () => {
  const dna = useDNA();
  const now = useStageRun();
  const glide = useGlide();
  const place = usePlaceGlide();
  const safeP = React.useContext(SafeZoneContext);
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const portrait = W < H;
  const where = `WorldStage (beat ${now.beat.index + 1})`;
  const ink = {bg: hex6(dna?.bg ?? '#05070f'), fg: dna?.fg ?? '#eef3f8', dim: dna?.dim ?? '#8d97ab',
    acc: dna?.accent ?? '#7cf2a4', acc2: dna?.accent2 ?? '#ff5c7a'};
  /** a colour a prop names: a DNA token (bg, fg, accent, accent2, dim, surface…) or a #hex */
  const col = (c: unknown, fallback: string): string => {
    if (typeof c !== 'string' || !c) return fallback;
    if (/^#/.test(c)) return hex6(c);
    const v = (dna as unknown as Record<string, unknown> | null)?.[c];
    return typeof v === 'string' && /^#/.test(v) ? hex6(v) : fallback;
  };
  const {before, state, p, keys} = now;

  // ── the backdrop: the space the world stands in ──
  const backdropOf = (st: State) => col(typeof st.backdrop === 'string' ? st.backdrop : 'bg', ink.bg);
  const ground = p >= 1 ? backdropOf(state) : hex6(mix(backdropOf(before), backdropOf(state), p));
  const lightInk = relLum(hex6(ink.fg)) > relLum(ink.bg) ? ink.fg : ink.bg;
  const darkInk = lightInk === ink.fg ? ink.bg : ink.fg;
  const textInk = relLum(ground) < 0.3 ? lightInk : darkInk;

  // ── the title (optional): one size for the run, up to two lines, measured in the face that draws it ──
  const family = dna?.uniformType ? dna.fontMono : (dna?.fontDisplay ?? 'system-ui');
  const titles = [...new Set(keys.map((kf) => String(kf.state.title ?? '')).filter(Boolean))];
  const sx = W * 0.065, lineW = W - 2 * sx;
  const per = (t: string) => measureText({text: t, fontFamily: family, fontSize: 100, fontWeight: '700',
    letterSpacing: '-0.02em'}).width / 100;
  const titleBase = Math.round(U * (portrait ? 0.075 : 0.058));
  const titlePx = titles.length ? Math.max(12, Math.floor(titles.reduce((px, t) => {
    const longest = Math.max(...t.split(/\s+/).filter(Boolean).map((w) => (CJK_CH.test(w) ? 0 : per(w))), 0);
    return Math.min(px, (lineW * 2 * 0.92) / Math.max(0.01, per(t)), lineW / Math.max(0.01, longest));
  }, titleBase))) : 0;
  const titleLines = titles.reduce((n, t) => Math.max(n, per(t) * titlePx > lineW * 0.99 ? 2 : 1), titles.length ? 1 : 0);
  const titleY = safeP ? Math.max(TITLE_Y, Math.round(safeP.top * H)) : TITLE_Y;

  // ── the content zone: below the title, above the caption band; type in the world keeps inside it ──
  const zoneTop = titles.length ? Math.max(CONTENT_TOP, titleY + titleLines * titlePx * 1.08 + U * 0.035)
    : Math.max(safeP ? Math.round(safeP.top * H) : 0, U * 0.06);
  const safeCapTop = safeP ? captionBottomY(H, safeP, Math.round(U * CAPTION_MARGIN_FRAC))
    - CAPTION_LINES * Math.round(U * CAPTION_SIZE_FRAC * SAFE_CAPTION_SCALE) * CAPTION_LEAD_CJK : null;
  const capTop = safeCapTop ?? contentBottom(W, H);          // where the caption band begins
  const zoneBot = capTop - U * 0.02;
  const zx0 = W * 0.05, zx1 = W * (1 - (safeP && portrait ? Math.max(0.05, safeP.right) : 0.05));
  const zone: Zone = {x0: zx0, y0: zoneTop, x1: zx1, y1: zoneBot};
  const view: View = {W, H, P: U * PERSP_FRAC};

  // ── every keyframe's camera: its framing in the world as it stands at that keyframe ──
  const camKeys: CamKey[] = React.useMemo(() => {
    const out: CamKey[] = [];
    let prev: Cam | null = null;
    keys.forEach((kf, i) => {
      const lay = layoutWorld(objectsOf(kf.state), U, `WorldStage (beat ${now.beats[kf.beat].index + 1})`);
      const fr = (kf.state.camera ?? {}) as Framing;
      const own = (kf.props.camera && typeof kf.props.camera === 'object' ? kf.props.camera : null) as Framing | null;
      const kind = typeof own?.move === 'string' ? own.move : 'dolly';
      if (!['dolly', 'crane', 'tilt', 'orbit', 'scale-zoom'].includes(kind)) {
        throw new Error(`WorldStage (beat ${now.beats[kf.beat].index + 1}): camera move "${kind}" is not one this stage ` +
          'draws — dolly, crane, tilt, orbit or scale-zoom');
      }
      const target = targetCam({...framingOf(fr, own), move: kind}, lay, view, zone, prev,
        `WorldStage (beat ${now.beats[kf.beat].index + 1})`);
      const o = lay.get(fr.frame as string)!;
      out.push({from: kf.from, to: kf.to, kind: i === 0 ? 'dolly' : kind, target, centre: [o.x, o.y, o.z] as V3});
      prev = target;
    });
    return out;
  }, [keys, U, W, H, zoneTop, zoneBot, zx0, zx1]);

  // ── the camera now (and a frame ago, for motion blur), breathing while it holds ──
  const driftOn = now.reduced ? 0 : (typeof state.drift === 'number' ? state.drift : 1);
  const camOf = (f: number): Cam => {
    const c = camAtFrame(camKeys, f, now.fps, now.reduced);
    if (!driftOn) return c;
    const t = f / now.fps, a = driftOn * 0.005 * c.fd;
    const dx = a * Math.sin((2 * Math.PI * t) / 11), dy = a * 0.6 * Math.sin((2 * Math.PI * t) / 13 + 1);
    // the breath is a sideways move of the lens in its own frame: near planes sway more than far ones (parallax)
    const cy = Math.cos(c.yaw), sy = Math.sin(c.yaw);
    return {...c, e: [c.e[0] + dx * cy, c.e[1] + dy, c.e[2] - dx * sy]};
  };
  const cam = camOf(now.frame);
  const camPrev = camOf(now.frame - 1);
  // the camera moves somewhere in this run (its framings differ, or it breathes): the whole run's type carries the
  // baseline unlock (runtime/glide — a span, never a frame)
  const camMoves = driftOn > 0 || camKeys.some((k, i) => i > 0 && JSON.stringify(k.target) !== JSON.stringify(camKeys[i - 1].target));

  // ── the world as it stands now: positions and presences carried across the move ──
  const layBefore = layoutWorld(objectsOf(before), U, where);
  const layNow = layoutWorld(objectsOf(state), U, where);
  const placed: (Placed & {on: number})[] = [];
  const ids = new Set([...layBefore.keys(), ...layNow.keys()]);
  for (const id of ids) {
    const a = layBefore.get(id), b = layNow.get(id);
    const onA = a ? clamp01(typeof a.spec.on === 'number' ? a.spec.on : 1) : 0;
    const onB = b ? clamp01(typeof b.spec.on === 'number' ? b.spec.on : 1) : 0;
    const on = p >= 1 ? onB : onA + (onB - onA) * p;
    const base = b ?? a!;
    const mv = a && b && p < 1 ? {x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, z: a.z + (b.z - a.z) * p,
      w: a.w + (b.w - a.w) * p, h: a.h + (b.h - a.h) * p} : {};
    if (on > 0.001) placed.push({...base, ...mv, on});
  }
  const lay = layNow.size ? layNow : layBefore;

  // ── what each object looks like through the lens right now ──
  const uid = React.useId().replace(/[^a-zA-Z0-9_-]/g, '');
  type Seen = {o: Placed & {on: number}; sx: number; sy: number; k: number; pw: number; ph: number; depth: number;
    alpha: number; blur: {sx: number; sy: number} | null};
  const seen: Seen[] = [];
  const frameBox = {x0: -W * 0.1, y0: -H * 0.1, x1: W * 1.1, y1: H * 1.1};
  for (const o of placed) {
    const c = project(cam, view, [o.x, o.y, o.z]);
    if (c.behind) continue;
    const pw = o.w * c.k, ph = o.h * c.k;
    if (pw > U * 40 || pw < 0.5) continue;
    if (c.x + pw / 2 < frameBox.x0 || c.x - pw / 2 > frameBox.x1 || c.y + ph / 2 < frameBox.y0 || c.y - ph / 2 > frameBox.y1) continue;
    // a nested object arrives as it grows into view; anything the lens has come too close to gives way as it passes
    // line art (a field, a wind) turns into slabs of colour sooner than a picture does
    const art = ['field', 'stream'].includes(String(o.spec.kind ?? 'image'));
    let alpha = o.on * nestFade(pw, zone.x1 - zone.x0, o.level) * passFade(pw, ph, W, H, art ? 1.2 : 3, art ? 2.6 : 6);
    // DEPTH OF FIELD from the distance the lens is focused at (restrained: ~5 px at 1080 at most)
    const dof = (typeof o.spec.dof === 'number' ? o.spec.dof : 1) * defocus(c.depth, cam.fd) * U * 0.005;
    // MOTION BLUR from this object's own speed on screen (a 180-degree shutter, stage/surface blurOf)
    const q = project(camPrev, view, [o.x, o.y, o.z]);
    const mb = now.reduced || q.behind ? null : blurOf(c.x - q.x, c.y - q.y, 1);
    const sxB = Math.hypot(dof, mb?.sx ?? 0), syB = Math.hypot(dof, mb?.sy ?? 0);
    // restrained: a fast zoom moves a huge plane's centre faster than any of it a viewer reads, so the smear is capped
    // at ~13 px at 1080 (a 40 px cap blurred the globe's coastlines to mush mid-zoom)
    const cap = U * 0.012;
    const blur = sxB > 0.6 || syB > 0.6 ? {sx: Math.min(cap, sxB), sy: Math.min(cap, syB)} : null;
    if (alpha > 0.002) seen.push({o, sx: c.x, sy: c.y, k: c.k, pw, ph, depth: c.depth, alpha, blur});
  }
  // A PARENT GIVES WAY to a nested child that covers the frame (the scale-zoom's hand-over): its picture would only be
  // its own pixels blown up behind the child. A feathered child counts by its opaque core.
  for (const s of seen) {
    if (s.o.level < 0) continue;
    for (const c of seen) {
      if (c === s || c.o.level <= s.o.level || !ancestors(lay, c.o.id).includes(s.o.id)) continue;
      const cs = c.o.spec as Obj;
      const feathered = cs.edge === 'feather' || (cs.edge === undefined && (cs.kind ?? 'image') === 'image');
      const core = feathered ? 0.55 : 1;
      const hw = (c.pw * core) / 2, hh = (c.ph * core) / 2;
      // how far the child's (core) box reaches past the frame on its tightest side; > 0 when it covers the frame
      const over = Math.min(hw - Math.abs(c.sx - W / 2) - W / 2, hh - Math.abs(c.sy - H / 2) - H / 2);
      const cover = clamp01(over / (U * 0.25)) * c.alpha;
      s.alpha *= 1 - cover;
    }
  }
  // far first; a nested object over its parent; then the order the world declares them in
  seen.sort((a, b) => (b.depth - a.depth) || (a.o.level - b.o.level) || (a.o.order - b.o.order));

  const sec = now.frame / now.fps;
  const drawLocal = (s: Seen): React.ReactNode => {
    const o = s.o.spec as Obj, kind = o.kind ?? 'image';
    const Lw = kind === 'image' ? Math.max(200, Math.min(4096, typeof o.imageW === 'number' ? o.imageW : 1600)) : LOCAL;
    const Lh = Lw / (s.o.w / s.o.h);
    const m = s.pw / Lw;
    const tx = s.sx - (m * Lw) / 2, ty = s.sy - (m * Lh) / 2;
    const fid = `wb-${uid}-${s.o.id.replace(/[^a-zA-Z0-9_-]/g, '')}`;
    const blur = s.blur ? {sx: s.blur.sx / m, sy: s.blur.sy / m} : null;
    // THE CAPTION SITS ON THE WORLD'S OWN SPACE: an object that reaches down into the caption band falls off into the
    // ground there, measured in screen px (a photograph framed to cover the picture overflows below it; a glowing
    // layer's halo hangs into it). Stars are the space itself and stay. Not a strip laid over the band — nothing is
    // drawn there; the world's things simply end at it, as type does at the zone.
    // A LONG, EASED fall-off: a short linear one read as a straight cut across a wide frame (a horizon that is not
    // there); spread over a fifth of the short side and eased at both ends it reads as the world dimming into space
    const fallTop = capTop - U * 0.16, fallBot = capTop + U * 0.04;
    const reaches = kind !== 'stars' && ty + m * Lh > fallTop;
    const fall = reaches ? (() => {
      const pc = (v: number) => `${((((v - ty) / m) / Lh) * 100).toFixed(3)}%`;   // a screen y in the object's own %
      const stops = [0, 0.2, 0.4, 0.6, 0.8, 1].map((u) => {
        const a = 1 - u * u * (3 - 2 * u);                                         // smoothstep, 1 → 0
        return `rgba(0,0,0,${a.toFixed(3)}) ${pc(fallTop + (fallBot - fallTop) * u)}`;
      });
      return `linear-gradient(180deg, #000 0%, ${stops.join(', ')}, transparent 100%)`;
    })() : undefined;
    const body = drawObject(o, kind, Lw, Lh, s, fid);
    return (
      <div key={s.o.id} data-world-object={s.o.id} style={{position: 'absolute', left: 0, top: 0, width: Lw, height: Lh,
        transformOrigin: '0 0', transform: `matrix(${m}, 0, 0, ${m}, ${tx}, ${ty})`, opacity: s.alpha,
        filter: blur ? `url(#${fid}-b)` : undefined,
        // light ADDS to the world behind it: the blend sits on this, the outermost wrapper — its opacity and blur make
        // it an isolated group, inside which a screen would meet nothing and land as an opaque black box
        mixBlendMode: kind === 'volume' || kind === 'band' ? 'screen' : undefined}}>
        {blur ? (
          <svg width={0} height={0} style={{position: 'absolute'}} aria-hidden>
            <filter id={`${fid}-b`} x={-(3 * blur.sx) / Lw} y={-(3 * blur.sy) / Lh} width={1 + (6 * blur.sx) / Lw}
              height={1 + (6 * blur.sy) / Lh} colorInterpolationFilters="sRGB">
              <feGaussianBlur stdDeviation={`${blur.sx.toFixed(2)} ${blur.sy.toFixed(2)}`} edgeMode="none" />
            </filter>
          </svg>
        ) : null}
        {fall ? <div style={{position: 'absolute', inset: 0, WebkitMaskImage: fall, maskImage: fall}}>{body}</div> : body}
      </div>
    );
  };

  /** One object's own picture, in its local box (Lw × Lh). */
  const drawObject = (o: Obj, kind: string, Lw: number, Lh: number, s: Seen, fid: string): React.ReactNode => {
    const c1 = col(o.color, ink.acc), c2 = col(o.color2, ink.acc2);
    if (kind === 'image') {
      if (typeof o.image !== 'string' || !o.image.trim()) {
        throw new Error(`${where}: object "${s.o.id}" is an image with no \`image\` file`);
      }
      const edge = o.edge ?? 'feather';
      const mask = edge === 'feather' ? 'radial-gradient(closest-side, #000 58%, rgba(0,0,0,0.6) 78%, transparent 100%)'
        : edge === 'circle' ? 'radial-gradient(closest-side, #000 97%, transparent 100%)' : undefined;
      // `imageZoom` crops into the picture's centre (a Sun photographed with black sky round its disc fills its circle)
      const iz = typeof o.imageZoom === 'number' && o.imageZoom >= 1 ? o.imageZoom : 1;
      return <div style={{position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: edge === 'hard' ? Lw * 0.012 : undefined,
        WebkitMaskImage: mask, maskImage: mask}}>
        <Img src={staticFile(o.image)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%',
          objectFit: 'cover', display: 'block', transform: iz > 1 ? `scale(${iz})` : undefined}} />
      </div>;
    }
    if (kind === 'disc' || kind === 'glow') {
      const g = kind === 'glow'
        ? `radial-gradient(closest-side, ${c1}cc 0%, ${c1}44 45%, ${c1}00 100%)`
        : `radial-gradient(circle at 36% 32%, ${mix(c1, '#ffffff', 0.35)} 0%, ${c1} 42%, ${mix(c1, '#000000', 0.7)} 100%)`;
      return <div style={{position: 'absolute', inset: 0, borderRadius: '50%', background: g}} />;
    }
    if (kind === 'globe') {
      const R = Lw * 0.5;
      const ring = o.ring;
      const res = resFor(s.pw / 2, W, H);
      return (
        <Earth uid={`${fid}-g`} W={Lw} H={Lh} res={res}
          ink={{bg: ink.bg, fg: ink.fg, accent: col(o.color, '#3f7fd8'), lit: c2}}
          view={{lon0: (typeof o.lon === 'number' ? o.lon : 0) + cam.yaw / D2R,
            lat0: Math.max(-89, Math.min(89, (typeof o.lat === 'number' ? o.lat : 0) - cam.pitch / D2R)), R, cx: Lw / 2, cy: Lh / 2}}>
          {ring ? (path) => {
            const d = path(geoCircle().center([ring.lon, ring.lat]).radius(ring.radius)() as any) ?? '';
            const rc = col(ring.color, ink.acc), wd = (ring.width ?? 0.035) * R;
            return <g>
              <path d={d} fill="none" stroke={rc} strokeOpacity={0.35} strokeWidth={wd * 2.4} style={{filter: `blur(${wd * 0.9}px)`}} />
              <path d={d} fill="none" stroke={rc} strokeOpacity={0.9} strokeWidth={wd * 0.7} />
            </g>;
          } : undefined}
        </Earth>
      );
    }
    if (kind === 'field') {
      // a dipole's field lines in the plane through its poles, squeezed on the side facing the Sun and drawn out into
      // a tail on the far side; the Earth sits at the box's centre and is `r` of the box wide
      const cx = Lw / 2, cy = Lh / 2, R = Lw * 0.06;
      const toSun = o.sun === 'right' ? 1 : -1;
      const lines: string[] = [];
      for (const L of [2.2, 3.2, 4.6, 6.4]) {
        for (const side of [-1, 1]) {
          const pts: string[] = [];
          const day = side === toSun;
          for (let i = 0; i <= 48; i++) {
            const th = 0.12 + (Math.PI - 0.24) * (i / 48);
            let r = L * R * Math.sin(th) ** 2;
            let x = side * r * Math.sin(th), y = -r * Math.cos(th);
            if (day) x *= 0.72;
            else {
              // the night side is drawn out: the outer lines open into the tail toward the box's edge
              const pull = L > 4 ? 1 + (L - 4) * 0.9 * Math.sin(th) ** 6 : 1;
              x *= pull;
            }
            pts.push(`${(cx + x).toFixed(1)},${(cy + y).toFixed(1)}`);
          }
          lines.push(pts.join(' '));
        }
      }
      for (const yy of [-1, 1]) {
        const tail: string[] = [];
        for (let i = 0; i <= 24; i++) {
          const u = i / 24;
          tail.push(`${(cx - toSun * (R * 2.2 + u * (Lw / 2 - R * 2.2))).toFixed(1)},${(cy + yy * R * (2.6 + 1.6 * Math.sqrt(u))).toFixed(1)}`);
        }
        lines.push(tail.join(' '));
      }
      const flow = (sec * 40) % 40;
      return <svg width={Lw} height={Lh} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        {/* the bow shock: where the wind first meets the field */}
        <defs>
          <linearGradient id={`${fid}-bow`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={c2} stopOpacity="0" /><stop offset="0.5" stopColor={c2} stopOpacity="0.7" />
            <stop offset="1" stopColor={c2} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`M ${cx + toSun * R * 3.2} ${cy - R * 5.6} C ${cx + toSun * R * 7.2} ${cy - R * 4}, ${cx + toSun * R * 7.2} ${cy + R * 4}, ${cx + toSun * R * 3.2} ${cy + R * 5.6}`}
          fill="none" stroke={`url(#${fid}-bow)`} strokeWidth={R * 0.12} strokeLinecap="round" />
        {lines.map((d, i) => <polyline key={i} points={d} fill="none" stroke={c1} strokeOpacity={0.62}
          strokeWidth={R * 0.07} strokeLinecap="round" strokeDasharray={`${R * 0.5} ${R * 0.25}`} strokeDashoffset={-flow * R * 0.02} />)}
      </svg>;
    }
    if (kind === 'stream') {
      // the wind: streaks flowing along +x, round an obstacle at `obstacle` [u, v, r] (potential flow past a disc)
      const n = Math.max(4, Math.min(120, Math.round(o.count ?? 36)));
      const ob = Array.isArray(o.obstacle) && o.obstacle.length === 3 ? o.obstacle : null;
      const obx = ob ? ob[0] * Lw : 0, oby = ob ? ob[1] * Lh : 0, obr = ob ? ob[2] * Lw : 0;
      const speed = (typeof o.speed === 'number' ? o.speed : 1) * Lw * 0.18;
      const seed = typeof o.seed === 'number' ? o.seed : 7;
      const streaks: React.ReactNode[] = [];
      for (let i = 0; i < n; i++) {
        const y0 = (hash01(seed * 101 + i) * 0.9 + 0.05) * Lh;
        const segL = Lw * (0.05 + 0.09 * hash01(seed * 37 + i));
        const phase = hash01(seed * 13 + i) * Lw;
        const x = ((phase + sec * speed * (0.75 + 0.5 * hash01(seed * 7 + i))) % (Lw + segL)) - segL;
        const yAt = (xx: number) => {
          if (!ob) return y0;
          // potential flow past a disc: the streamline ψ = y (1 − r²/(x² + y²)) through this streak's far-upstream
          // height. Multiplied out it is the cubic y³ − ψy² + (x² − r²)y − ψx² = 0, whose OUTERMOST root (the one
          // outside the disc, on ψ's side) is the streamline; Newton from beyond it converges onto it monotonically
          // (the cubic is convex there) — started inside, it wandered between roots and drew spikes.
          const sgn = y0 - oby >= 0 ? 1 : -1;
          const psi = Math.max(Math.abs(y0 - oby), obr * 1e-3);
          const dx = xx - obx, x2 = dx * dx, r2 = obr * obr;
          let y = psi + obr * 1.5;
          for (let it = 0; it < 30; it++) {
            const f = y * y * y - psi * y * y + (x2 - r2) * y - psi * x2;
            const df = 3 * y * y - 2 * psi * y + (x2 - r2);
            if (!(df > 1e-9)) break;
            const step = f / df;
            y -= step;
            if (Math.abs(step) < 1e-4 * obr) break;
          }
          return oby + sgn * Math.max(psi, y);
        };
        const pts = [0, 0.25, 0.5, 0.75, 1].map((u) => `${(x + u * segL).toFixed(1)},${yAt(x + u * segL).toFixed(1)}`);
        const a = 0.35 + 0.5 * hash01(seed * 3 + i);
        streaks.push(<polyline key={i} points={pts.join(' ')} fill="none" stroke={c1} strokeOpacity={a}
          strokeWidth={Lw * 0.0028} strokeLinecap="round" />);
      }
      const soft = 'linear-gradient(90deg, transparent 0%, #000 14%, #000 86%, transparent 100%)';
      return <svg width={Lw} height={Lh} style={{position: 'absolute', inset: 0, overflow: 'visible', WebkitMaskImage: soft,
        maskImage: soft}}>{streaks}</svg>;
    }
    if (kind === 'stars') {
      const n = Math.max(10, Math.min(900, Math.round(o.count ?? 260)));
      const seed = typeof o.seed === 'number' ? o.seed : 3;
      return <svg width={Lw} height={Lh} style={{position: 'absolute', inset: 0}}>
        {Array.from({length: n}, (_, i) => {
          const r = Lw * 0.0011 * (0.6 + 1.6 * hash01(seed * 17 + i) ** 3);
          return <circle key={i} cx={hash01(seed * 5 + i) * Lw} cy={hash01(seed * 11 + i) * Lh} r={r}
            fill={col(o.color, ink.fg)} fillOpacity={0.35 + 0.6 * hash01(seed * 23 + i)} />;
        })}
      </svg>;
    }
    if (kind === 'band' || kind === 'volume') {
      // LIGHT IN A VOLUME (runtime/volume). A `band` is a glowing layer of the sky — once a blurred striped rectangle
      // (the WorldStage probe's bands read as one), now the volume's `layer` form: soft wandering edges, faint
      // field-aligned rays, ragged ends. A `volume` is any form — a curtain hung in the world, a nebula, shafts, a
      // flame — drawn at about its size on screen (a far plane is not drawn at full resolution, a near one is capped).
      const form: VolumeForm = kind === 'band' ? 'layer' : (o.form as VolumeForm);
      const spec: VolumeSpec = {form, seed: typeof o.seed === 'number' ? o.seed : 3,
        ...(typeof o.intensity === 'number' ? {intensity: o.intensity} : {}),
        ...(o.color || kind === 'band' ? {colors: o.color2 ? [c1, c2] : [c1]} : {}),
        ...(o.bands ? {bands: o.bands} : {}), ...(typeof o.sheets === 'number' ? {sheets: o.sheets} : {}),
        ...(o.source ? {source: o.source} : {}), ...(o.occluder ? {occluder: o.occluder} : {}),
        ...(typeof o.open === 'number' ? {open: o.open} : {}), ...(o.star ? {star: o.star} : {}),
        ...(o.base ? {base: o.base} : {}), ...(typeof o.spread === 'number' ? {spread: o.spread} : {}),
        ...(now.reduced ? {speed: 0} : {})};
      const res = Math.max(0.2, Math.min(1.5, s.pw / Lw, 2048 / Lw));
      return <Volume spec={spec} width={Lw} height={Lh} res={res} blend="none" soft where={`${where} object "${s.o.id}"`} />;
    }
    if (kind === 'type') return null;           // drawn in the type layer (flat, over the world)
    if (kind === 'frame') return null;          // a place to frame and to nest in, with nothing of its own to draw
    throw new Error(`${where}: object "${s.o.id}" has kind "${kind}" — image, globe, disc, field, stream, stars, band, ` +
      'glow, volume, type or frame');
  };

  // ── type IN the world: a word on a plane facing the lens. It scales with its distance, and it is only drawn while
  // it is readable — gone before it is under the type floor, gone before it is a wall of letters at the lens, and
  // faded as it leaves the content zone (the type layer is a window onto the world, cut at the zone) ──
  const warnPx = U * 0.0275;
  const typeLayer: React.ReactNode[] = [];
  for (const s of seen) {
    const o = s.o.spec as Obj;
    if ((o.kind ?? 'image') !== 'type') continue;
    if (typeof o.text !== 'string' || !o.text.trim()) throw new Error(`${where}: type object "${s.o.id}" has no \`text\``);
    const px = (typeof o.size === 'number' && o.size > 0 ? o.size : 0.08) * U * s.k;
    const sizeIn = clamp01((px - warnPx) / (warnPx * 0.4)) * (1 - clamp01((px - U * 0.22) / (U * 0.1)));
    const m = px / BASE_TYPE_PX;
    const tw = measureText({text: o.text, fontFamily: family, fontSize: BASE_TYPE_PX, fontWeight: String(o.weight ?? 700)}).width * m;
    const th = px * 1.2;
    const bx0 = s.sx - tw / 2, by0 = s.sy - th / 2;
    const inside = Math.min(bx0 - zone.x0, zone.x1 - (bx0 + tw), by0 - zone.y0, zone.y1 - (by0 + th));
    const edgeIn = clamp01(1 + inside / Math.max(1, px * 0.6));
    const a = s.alpha * sizeIn * edgeIn;
    if (a < 0.01) continue;
    typeLayer.push(
      <div key={`t${s.o.id}`} style={{position: 'absolute', left: 0, top: 0, whiteSpace: 'nowrap', transformOrigin: '0 0',
        transform: glide(`matrix(${m}, 0, 0, ${m}, ${bx0}, ${by0})`, camMoves, m), opacity: a,
        color: col(o.color, textInk), font: `${o.weight ?? 700} ${BASE_TYPE_PX}px/1.2 var(--f-display, system-ui)`,
        letterSpacing: '-0.01em'}}>{o.text}</div>);
  }

  // ── labels: an object's name beside it at a reading size, the first side that stays in the zone and off the other
  // labels; joined to it by a hairline ──
  const labelPx = Math.round(U * 0.036);
  const bodyFamily = dna?.uniformType ? dna.fontMono : (dna?.fontBody ?? 'system-ui');
  const shownOf = (st: State) => new Set(Array.isArray(st.labels) ? (st.labels as unknown[]).filter((x): x is string => typeof x === 'string') : []);
  const lA = shownOf(before), lB = shownOf(state);
  for (const id of [...lA, ...lB]) {
    if (!lay.has(id) && !layBefore.has(id)) {
      throw new Error(`${where}: \`labels\` names "${id}", which is not an object of the world`);
    }
  }
  const placedLabels: {x0: number; y0: number; x1: number; y1: number}[] = [];
  const labelArt: React.ReactNode[] = [];
  for (const id of [...new Set([...lA, ...lB])]) {
    const s = seen.find((x) => x.o.id === id);
    const text = String((s?.o.spec as Obj | undefined)?.label ?? (lay.get(id)?.spec as Obj | undefined)?.label ?? '');
    if (!s || !text) continue;
    const pres = lA.has(id) && lB.has(id) ? 1 : lB.has(id) ? clamp01((p - 0.35) / 0.65) : 1 - clamp01(p / 0.5);
    const inView = clamp01((s.pw / (zone.x1 - zone.x0) - 0.03) / 0.05);
    const a = pres * inView * Math.min(1, s.alpha * 1.5);
    if (a < 0.02) continue;
    const tw = measureText({text, fontFamily: bodyFamily, fontSize: labelPx, fontWeight: '600'}).width;
    const lh = labelPx * 1.25, gap = U * 0.03;
    // a diffuse thing (a wind, a field) is named at a place on it (`labelAt`, 0..1 of its box), not beside its box
    const la = (s.o.spec as Obj).labelAt;
    const anchored = Array.isArray(la) && la.length === 2 && la.every((x) => typeof x === 'number' && isFinite(x));
    const half = anchored ? {w: U * 0.01, h: U * 0.01} : {w: Math.min(s.pw, U * 3) / 2, h: Math.min(s.ph, U * 3) / 2};
    const ax = anchored ? s.sx + ((la as number[])[0] - 0.5) * s.pw : s.sx, ay = anchored ? s.sy + ((la as number[])[1] - 0.5) * s.ph : s.sy;
    const box = {x0: ax - half.w, y0: ay - half.h, x1: ax + half.w, y1: ay + half.h};
    const cands = [
      {x: box.x1 + gap, y: ay - lh / 2, ax: box.x1, ay},
      {x: box.x0 - gap - tw, y: ay - lh / 2, ax: box.x0, ay},
      {x: ax - tw / 2, y: box.y0 - gap - lh, ax, ay: box.y0},
      {x: ax - tw / 2, y: box.y1 + gap, ax, ay: box.y1},
      // inside the object, low on it (a big framed thing has no room beside it)
      {x: ax - tw / 2, y: Math.min(box.y1, zone.y1) - lh - gap * 1.5, ax: NaN, ay: NaN},
    ];
    const fits = (c: {x: number; y: number}) => c.x >= zone.x0 && c.x + tw <= zone.x1 && c.y >= zone.y0 && c.y + lh <= zone.y1 &&
      !placedLabels.some((b) => c.x < b.x1 && c.x + tw > b.x0 && c.y < b.y1 && c.y + lh > b.y0);
    const c = cands.find(fits);
    if (!c) continue;
    placedLabels.push({x0: c.x - gap * 0.3, y0: c.y - gap * 0.3, x1: c.x + tw + gap * 0.3, y1: c.y + lh + gap * 0.3});
    const lineTo = {x: c.x < c.ax ? c.x + tw + gap * 0.25 : c.x - gap * 0.25, y: c.y + lh / 2};
    labelArt.push(
      <React.Fragment key={`l${id}`}>
        {isFinite(c.ax) ? <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, opacity: a * 0.8}}>
          <line x1={c.ax} y1={c.ay} x2={Math.abs(c.ay - lineTo.y) > lh ? c.ax : lineTo.x} y2={Math.abs(c.ay - lineTo.y) > lh ? (c.ay < lineTo.y ? c.y : c.y + lh) : lineTo.y}
            stroke={textInk} strokeWidth={Math.max(1, U / 900)} />
          <circle cx={c.ax} cy={c.ay} r={U * 0.004} fill={ink.acc} />
        </svg> : null}
        <div style={{position: 'absolute', ...place(camMoves, c.x, c.y), opacity: a, whiteSpace: 'nowrap', color: textInk,
          font: `600 ${labelPx}px/1.25 var(--f-body, system-ui)`, letterSpacing: '0.02em',
          textShadow: `0 0 ${U * 0.012}px ${ground}, 0 0 ${U * 0.004}px ${ground}`}}>{text}</div>
      </React.Fragment>);
  }

  // ── credits: a picture in view names who made it (its object's `credit`), small and dim at the zone's top right ──
  const creditPx = Math.round(U * 0.0285);
  // a picture is credited while a viewer can SEE it: on the frame (not just past its edge), large enough, and not
  // hidden behind a nearer picture drawn over it
  const visibleRect = (s: Seen, core = 1) => {
    const hw = (s.pw * core) / 2, hh = (s.ph * core) / 2;
    return {x0: Math.max(0, s.sx - hw), y0: Math.max(0, s.sy - hh), x1: Math.min(W, s.sx + hw), y1: Math.min(H, s.sy + hh)};
  };
  const coreOf = (s: Seen) => ((s.o.spec as Obj).edge ?? 'feather') === 'feather' ? 0.55 : 1;
  const images = seen.filter((s) => (s.o.spec.kind ?? 'image') === 'image');
  const credits = [...new Set(images.filter((s, i) => {
    if (typeof (s.o.spec as Obj).credit !== 'string' || s.alpha <= 0.35) return false;
    const r = visibleRect(s);
    if (r.x1 - r.x0 < (zone.x1 - zone.x0) * 0.25 || r.y1 - r.y0 < (zone.y1 - zone.y0) * 0.2) return false;
    const mx = (r.x0 + r.x1) / 2, my = (r.y0 + r.y1) / 2;
    return !images.slice(i + 1).some((c) => {
      const q = visibleRect(c, coreOf(c));
      return c.alpha > 0.8 && mx >= q.x0 && mx <= q.x1 && my >= q.y0 && my <= q.y1;
    });
  }).map((s) => String((s.o.spec as Obj).credit)))];
  const creditArt = credits.length ? (
    <div key="credits" style={{position: 'absolute', right: W - zone.x1, top: zone.y0, maxWidth: (zone.x1 - zone.x0) * 0.62,
      textAlign: 'right', color: ink.dim, font: `500 ${creditPx}px/1.3 var(--f-body, system-ui)`,
      textShadow: `0 0 ${U * 0.008}px ${ground}`}}>
      {credits.map((c) => <div key={c}>{c}</div>)}
    </div>) : null;

  // ── light: an object with `bloom` lights the space around it on screen ──
  const blooms = seen.filter((s) => typeof (s.o.spec as Obj).bloom === 'number' && ((s.o.spec as Obj).bloom as number) > 0)
    .map((s) => {
      const o = s.o.spec as Obj, r = Math.max(s.pw, s.ph) * 1.7;
      const c = col(o.color, '#ffb070');
      return <div key={`b${s.o.id}`} style={{position: 'absolute', left: s.sx - r, top: s.sy - r, width: 2 * r, height: 2 * r,
        borderRadius: '50%', mixBlendMode: 'screen', opacity: s.alpha * clamp01(o.bloom as number),
        background: `radial-gradient(closest-side, ${c}66 0%, ${c}22 40%, ${c}00 100%)`}} />;
    });

  // ── the title line: the old one leaves in the first part of the move, then the new one arrives ──
  const curTitle = String(state.title ?? ''), prevTitle = String(before.title ?? '');
  const changed = p < 1 && prevTitle !== curTitle;
  const titleLine = (text: string, hi: string | undefined, q: number, leaving: boolean) => {
    if (!text) return null;
    const at = hi ? text.indexOf(hi) : -1;
    const parts = at >= 0 ? [text.slice(0, at), hi!, text.slice(at + hi!.length)] : [text];
    return (
      <div key={leaving ? 'out' : 'in'} style={{position: 'absolute', left: 0, top: 0, width: lineW,
        transform: glide(`translate(${sx}px, ${titleY + (leaving ? -(1 - q) : (1 - q)) * U * 0.025}px)`, true),
        opacity: q, color: textInk, font: `700 ${titlePx}px/1.08 var(--f-display, system-ui)`, letterSpacing: '-0.02em',
        textShadow: `0 0 ${U * 0.02}px ${ground}`}}>
        {parts.map((t, i) => <span key={i} style={i === 1 ? {color: ink.acc} : undefined}>{t}</span>)}
      </div>
    );
  };
  const inP = changed ? clamp01((p - 0.38) / 0.62) : 1, outP = changed ? 1 - clamp01(p / 0.36) : 0;

  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse 90% 75% at 50% 45%, ${mix(ground, '#ffffff', 0.04)} 0%, ${ground} 70%, ${mix(ground, '#000000', 0.3)} 100%)`}}>
      {/* the world: every object a flat element at its projected scale, far first */}
      <AbsoluteFill>{seen.filter((s) => ((s.o.spec as Obj).kind ?? 'image') !== 'type').map(drawLocal)}</AbsoluteFill>
      <AbsoluteFill style={{pointerEvents: 'none'}}>{blooms}</AbsoluteFill>
      {/* type in and beside the world: a window cut at the content zone — a word the camera carries past the zone's
          edge leaves through it, as it leaves the camera's view */}
      <div style={{position: 'absolute', left: zone.x0, top: zone.y0, width: zone.x1 - zone.x0, height: zone.y1 - zone.y0,
        overflow: 'hidden'}}>
        <div style={{position: 'absolute', left: -zone.x0, top: -zone.y0, width: W, height: H}}>
          {typeLayer}
          {labelArt}
          {creditArt}
        </div>
      </div>
      {outP > 0 ? titleLine(prevTitle, before.highlight as string | undefined, outP, true) : null}
      {titleLine(curTitle, state.highlight as string | undefined, inP, false)}
    </AbsoluteFill>
  );
};
