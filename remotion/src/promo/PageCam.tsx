// PROMO · PageCam — a 2.5D camera over a real product capture (references/promo-film.md §camera).
//
// The capture is a 2x screenshot shown at its CSS size (w x h = pixels / 2). A key {f, cx, cy, zoom, rx, ry, rz}
// puts the page point (cx, cy) at the frame's centre at `zoom` screen px per CSS px, tilted rx (top leans away),
// ry (right edge recedes), rz (roll). Children are positioned in the SAME page CSS px, so an overlay sits on the
// element it belongs to at every camera pose.
//
// SHARPNESS AND STILLNESS (runtime/surfaceView.tsx raster mode). The page is laid out ONCE at the largest scale the
// shot reaches (CSS `zoom`, constant for the shot) and moved by ONE 3D transform at zoom/raster <= 1: the capture is
// rasterised from its 2x pixels at full size and the compositor only resamples it, so a close-up is sharp AND a slow
// push glides. A key's zoom may not exceed the capture's density (`maxZoom`, 2 for a 2x capture) — past it the
// texture is upsampled and the film shows it; the camera clamps there and says so once.
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {track, span, useLook, isDarkHex, type Key, type Box} from './kit';
import {unlockFor, BaselineUnlockContext} from '../runtime/glide';

export type CamKey = Key & {f: number; cx: number; cy: number; zoom: number; rx?: number; ry?: number; rz?: number; persp?: number};

const warned = new Set<string>();

/** A CLOSE-UP'S OWN PIXELS. The page is a 2x capture, so past an effective zoom of 2 it is upsampled and soft; a
 *  macro is ONE element captured again at 4x (promo_capture --hires) and drawn over its slot on a layer of its own,
 *  laid out once at the shot's largest zoom and moved by the same pose — so the camera can push to 4x onto it and the
 *  subject stays sharp while the page around it softens like a background out of a lens's depth. */
export type Macro = {kind?: 'macro'; box: Box; src: string; scale?: number; at?: number; radius?: number};

export type Pose = {cx: number; cy: number; zoom: number; rx: number; ry: number; rz: number; persp: number};
/** The camera, readable by what it films: where a page point lands on the frame at ANY frame of the shot (rotation
 *  ignored — a label decides its side from this, once, at the frame it lands). */
export type PageCamInfo = {W: number; H: number; focusY: number; poseAt: (frame: number) => Pose;
  toScreen: (frame: number, x: number, y: number) => {x: number; y: number}};
export const PageCamContext = React.createContext<PageCamInfo | null>(null);

export const PageCam: React.FC<{
  src: string;               // a file in the film's public dir (render --public-dir), or an absolute URL
  w: number; h: number;      // the capture's CSS size
  keys: CamKey[];
  radius?: number;           // window corner radius, CSS px
  maxZoom?: number;          // capture density: 2 for a 2x capture
  frameOverride?: number;    // drive the camera from an outer clock
  blur?: number;             // screen-space defocus (an outro's back row)
  contain?: boolean;         // keep a straight-on view inside the capture (default)
  focusY?: number;           // where (cx, cy) lands, as a share of the frame height: 0.5, or higher up when a caption
                             // band owns the bottom of the frame (a narrated film)
  macros?: Macro[];          // 4x captures of the elements a close-up pushes into (see Macro)
  video?: string;            // a RECORDING of the page (promo_record) played in the capture's place, from `videoStart`
  videoStart?: number;
  overlay?: React.ReactNode; // acts that sit ON TOP of everything, macros included (callouts, rings, the cursor), in
                             // page CSS px — drawn on a layer of their own at the close-up's raster, so they stay sharp
  children?: React.ReactNode;
}> = ({src, w, h, keys, radius = 12, maxZoom = 2, frameOverride, blur = 0, contain = true, focusY = 0.5, macros = [], overlay, video,
  videoStart = 0, children}) => {
  const f0 = useCurrentFrame();
  const frame = frameOverride ?? f0;
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const allowed = React.useContext(BaselineUnlockContext);
  // a close-up may pass the page's density only onto a macro: the cap is the sharpest capture the shot carries
  const cap = Math.max(maxZoom, ...macros.map((m) => m.scale ?? 4)) * 1.0001;
  // NO SUB-PIXEL CREEP ON A PAGE. A segment whose fastest point moves the picture less than CREEP px a frame is
  // collapsed into a HOLD (its end pose becomes its start pose, so the camera stays continuous). Measured: a sharp
  // capture drifting 0.17 px a frame pulsed in sharpness by ~5-10 % every few frames — the compositor's bilinear
  // resample is crisp on a whole pixel and soft half-way — a 5-7 Hz shimmer the viewer reads as 抖动; held still it is
  // 0.0 %, moving ≥ 1 px a frame the phase sweeps too fast to see. Life on a held page comes from its acts.
  // 8 px a frame at the PEAK: a move's landing passes through the creep band for ~(0.9 / peak) of the segment's time, so
  // a slower move spends a fifth or more of itself shimmering (measured: segments peaking at 4-5 px a frame shimmered
  // 6-8 %). A page camera either holds or makes a decisive move.
  const CREEP = 8;
  const camKeys = React.useMemo(() => {
    // A CAMERA LANDS WITH CONSTANT DECELERATION. The craft curves (expo, swift, snappy) end on a long, ever-slower tail:
    // the last 1 % of a move spread over a third of its time — a creep, and on a sharp page a shimmer as it lands. A
    // page camera's moves use a two-piece quadratic instead (accelerate to the peak at `p`, decelerate linearly to
    // rest): velocity is continuous, and the landing spends 1-2 frames under a pixel a frame instead of 10-15. The
    // named curve keeps its character through `p` (where the move peaks): snappy/expo/out leave fast, smooth is
    // symmetric, swift leaves briskly. `linear` stays linear.
    const PEAK: Record<string, number> = {snappy: 0.12, expo: 0.1, out: 0.18, overshoot: 0.15, swift: 0.38, smooth: 0.5, anticip: 0.55, exit: 0.7};
    // velocity a sine bump over a warped clock: it peaks at `p` (t^q = 1/2) and, like a constant deceleration, falls
    // LINEARLY to rest — the shortest landing — while staying smooth (a two-piece quadratic had a corner in its
    // acceleration at the peak, which read as a bump)
    const land = (p: number) => {
      const q = Math.log(0.5) / Math.log(Math.min(0.9, Math.max(0.05, p)));
      return (t: number) => (1 - Math.cos(Math.PI * Math.pow(Math.min(1, Math.max(0, t)), q))) / 2;
    };
    const ks = keys.map((k) => {
      const e = k.ease;
      if (e === 'linear' || typeof e === 'function') return {...k};
      return {...k, ease: land(PEAK[String(e ?? 'smooth')] ?? 0.5)};
    });
    const scr = (k: CamKey) => ({x: k.cx, y: k.cy, z: Number(k.zoom ?? 1) * (W / 1920)});
    for (let i = 1; i < ks.length; i++) {
      const a = scr(ks[i - 1]), b = scr(ks[i]);
      const n = Math.max(1, ks[i].f - ks[i - 1].f);
      // the picture's travel on screen: the pan at the larger zoom, plus a push measured at the frame's edge
      const travel = Math.hypot(b.x - a.x, b.y - a.y) * Math.max(a.z, b.z) + Math.abs(b.z - a.z) / Math.max(a.z, b.z) * Math.hypot(W, H) / 2;
      // a tilt moves the picture too: a degree swings the frame's edge by ~W/2 x π/180
      const tilt = (Math.abs(Number(ks[i].rx ?? 0) - Number(ks[i - 1].rx ?? 0)) + Math.abs(Number(ks[i].ry ?? 0) - Number(ks[i - 1].ry ?? 0))
        + Math.abs(Number(ks[i].rz ?? 0) - Number(ks[i - 1].rz ?? 0))) * (Math.PI / 180) * (W / 2);
      const peak = ((travel + tilt) / n) * 2;      // an eased segment peaks at ~2x its mean speed
      if (peak < CREEP) {
        ks[i] = {...ks[i], cx: ks[i - 1].cx, cy: ks[i - 1].cy, zoom: ks[i - 1].zoom, rx: ks[i - 1].rx, ry: ks[i - 1].ry, rz: ks[i - 1].rz};
      }
    }
    return ks;
  }, [keys, W, H]);
  // `zoom` is authored at a 1920-wide reference (1 = one CSS px per screen px on a 1920 frame); what the texture must
  // carry is the EFFECTIVE density on this frame — at 9:16 the same key is 0.5625 of it.
  // CONTAINMENT IS APPLIED TO THE KEYS, NOT TO THE FRAMES. A straight-on view stays inside the capture — the edge of a
  // web page and the ground past it are not the product; where the view is wider (taller) than the page it is centred.
  // A tilted key is an object shot (the window on its ground), so its containment fades with the tilt (Gaussian, smooth
  // in the angle). Clamping every FRAME put a corner in the camera's path wherever a move crossed the bound or its tilt
  // changed the clamp's weight (measured: 0.13-0.20 px glide failures), and a soft clamp pulled a key near the edge
  // inward; clamped once per key, the camera interpolates between contained poses and has no corner to turn.
  const containedKeys = React.useMemo(() => camKeys.map((k) => {
    if (!contain) return k;
    const z = Math.min(cap, Number(k.zoom ?? 1) * (W / 1920));
    const rx = Number(k.rx ?? 0), ry = Number(k.ry ?? 0), rz = Number(k.rz ?? 0);
    const wgt = Math.exp(-(rx * rx + ry * ry + rz * rz) / 18);
    const vw = W / z, vh = H / z;
    const clampTo = (c: number, v: number, size: number, fr = 0.5) => (v >= size ? size / 2 : Math.min(size - v * (1 - fr), Math.max(v * fr, c)));
    return {...k, cx: k.cx + (clampTo(k.cx, vw, w) - k.cx) * wgt, cy: k.cy + (clampTo(k.cy, vh, h, focusY) - k.cy) * wgt};
  }), [camKeys, contain, cap, W, H, w, h, focusY]);
  const poseAt = (f: number): Pose => {
    const cx = track(containedKeys, f, 'cx'), cy = track(containedKeys, f, 'cy');
    const zoom = Math.max(1e-3, Math.min(cap, track(containedKeys, f, 'zoom', 1) * (W / 1920)));
    const rx = track(containedKeys, f, 'rx'), ry = track(containedKeys, f, 'ry'), rz = track(containedKeys, f, 'rz');
    return {cx, cy, zoom, rx, ry, rz, persp: track(containedKeys, f, 'persp', 1600)};
  };
  const P = poseAt(frame);
  // MOTION BLUR ON A FAST MOVE (as a camera's shutter would): the picture's speed at this frame, in screen px a frame —
  // the pan at this zoom plus a push measured at the frame's edge — over a threshold becomes a blur that rises with it
  // and is gone by the time the move lands (6-10 px at the peak of a whip; a settle or a hold is never blurred).
  const P0 = poseAt(frame - 1), P1 = poseAt(frame + 1);
  const speed = (Math.hypot(P1.cx - P0.cx, P1.cy - P0.cy) * P.zoom + (Math.abs(P1.zoom - P0.zoom) / P.zoom) * Math.hypot(W, H) / 2) / 2;
  const mblur = Math.min(10, Math.max(0, (speed - 14) * 0.18));
  const maxKey = Math.max(...keys.map((k) => Number(k.zoom ?? 1))) * (W / 1920);
  if (maxKey > cap && !warned.has(src)) {
    warned.add(src);
    console.warn(`[PageCam] ${src}: zoom ${maxKey.toFixed(2)} past the capture's density ${maxZoom}; clamped`);
  }
  // THE RASTER (runtime/surfaceView.tsx, raster mode). The page is laid out ONCE, at the largest scale this shot
  // reaches, and every frame is one 3D transform at zoom/raster <= 1 that the compositor resamples. The first version
  // set CSS `zoom` per frame: every frame re-laid the page out, the capture's box and every line of overlay type were
  // rounded to whole pixels at a new size, and the viewer saw the page and its type tremble during each push
  // (measured on a zh film over a Wikipedia capture: overlay type 0.33-0.59 px RMS with 0.9 px pops; the picture
  // stepped the same way). Laid out once, nothing is rounded per frame.
  // the page's raster never exceeds its own density (past it there is nothing to rasterise but upsampled pixels);
  // a push beyond it magnifies the page (soft, a background) while the macro layer carries the subject
  const raster = Math.max(1e-3, Math.min(maxZoom, maxKey)) * 1.1;      // headroom for a lifted element (scale <= 1.1)
  const s = P.zoom / raster;
  const mRaster = Math.max(1e-3, Math.min(cap, maxKey)) * 1.02;
  const ms = P.zoom / mRaster;
  const urlOf = (u: string) => (/^(https?:|data:|\/)/.test(u) ? u : staticFile(u));
  const url = /^(https?:|data:|\/)/.test(src) ? src : staticFile(src);
  const info: PageCamInfo = {W, H, focusY, poseAt, toScreen: (f, x, y) => {
    const q = poseAt(f);
    return {x: W / 2 + (x - q.cx) * q.zoom, y: H * focusY + (y - q.cy) * q.zoom};
  }};
  return (
    <AbsoluteFill style={{overflow: 'hidden', filter: blur + mblur > 0.3 ? `blur(${blur + mblur}px)` : undefined}}>
      <div style={{position: 'absolute', inset: 0, perspective: `${P.persp * P.zoom}px`, perspectiveOrigin: `${W / 2}px ${H * focusY}px`}}>
        <div data-surface-view="raster" style={{
          position: 'absolute', left: 0, top: 0, width: w * raster, height: h * raster,
          transformOrigin: `${P.cx * raster}px ${P.cy * raster}px`,
          // PIN THE RASTER. Without it Chrome picks the layer's raster scale from the transform it first sees, and a
          // render runs in parallel tabs that each start on a different frame: every chunk rasterised the page at its own
          // scale, and the film stepped at each chunk boundary (a 0.5-0.7 px pop at frames 2-3 and 80-82 of a probe
          // push). `will-change: transform` rasterises the layer once at its layout size — the LARGEST scale of the shot
          // — in every tab; each frame only scales it down.
          willChange: 'transform',
          transform: `translate3d(${W / 2 - P.cx * raster}px, ${H * focusY - P.cy * raster}px, 0) rotateY(${P.ry}deg) rotateX(${P.rx}deg) ` +
            `rotateZ(${P.rz}deg) scale3d(${s}, ${s}, 1)`,
        }}>
          {/* laid out ONCE at `raster`, in page units; the unlock inside the layer keeps type that moves WITHIN the
              page (a callout rising, a field being typed) off the whole-pixel baseline grid */}
          <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, zoom: raster, transformOrigin: '0 0',
            transform: allowed ? unlockFor(1) : undefined}}>
            <div style={{position: 'absolute', inset: 0, borderRadius: radius, overflow: 'hidden',
              boxShadow: `0 2px 6px rgba(0,0,0,0.10), 0 30px 80px rgba(0,0,0,${isDarkHex(look.ground) ? 0.5 : 0.16}), 0 0 0 1px ${look.groundEdge}`}}>
              {video ? (
                // the product IN MOTION: its recording, frame-exact, in the capture's place (the poster under it)
                <>
                  <Img src={url} style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
                  <Sequence from={-videoStart} layout="none">
                    <OffthreadVideo src={/^(https?:|data:|\/)/.test(video) ? video : staticFile(video)} muted
                      style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
                  </Sequence>
                </>
              ) : (
                <Img src={url} style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
              )}
            </div>
            <PageCamContext.Provider value={info}>{children}</PageCamContext.Provider>
          </div>
        </div>
        {macros.length ? (
          <div data-surface-view="raster" style={{
            position: 'absolute', left: 0, top: 0, width: w * mRaster, height: h * mRaster, pointerEvents: 'none',
            transformOrigin: `${P.cx * mRaster}px ${P.cy * mRaster}px`, willChange: 'transform',
            transform: `translate3d(${W / 2 - P.cx * mRaster}px, ${H * focusY - P.cy * mRaster}px, 0) rotateY(${P.ry}deg) rotateX(${P.rx}deg) ` +
              `rotateZ(${P.rz}deg) scale3d(${ms}, ${ms}, 1)`,
          }}>
            {macros.map((m, i) => (
              <div key={i} style={{position: 'absolute', left: m.box.x * mRaster, top: m.box.y * mRaster, width: m.box.w * mRaster,
                height: m.box.h * mRaster, borderRadius: (m.radius ?? 0) * mRaster, overflow: 'hidden',
                opacity: m.at === undefined ? 1 : span(frame, m.at, m.at + 6, 'smooth'),
                backgroundImage: `url(${urlOf(m.src)})`, backgroundSize: '100% 100%', backgroundRepeat: 'no-repeat'}} />
            ))}
          </div>
        ) : null}
        {overlay ? (
          <div style={{
            position: 'absolute', left: 0, top: 0, width: w * mRaster, height: h * mRaster, pointerEvents: 'none',
            transformOrigin: `${P.cx * mRaster}px ${P.cy * mRaster}px`, willChange: 'transform',
            transform: `translate3d(${W / 2 - P.cx * mRaster}px, ${H * focusY - P.cy * mRaster}px, 0) rotateY(${P.ry}deg) rotateX(${P.rx}deg) ` +
              `rotateZ(${P.rz}deg) scale3d(${ms}, ${ms}, 1)`,
          }}>
            <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, zoom: mRaster, transformOrigin: '0 0',
              transform: allowed ? unlockFor(1) : undefined}}>
              <PageCamContext.Provider value={info}>{overlay}</PageCamContext.Provider>
            </div>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

/** The ground the window floats on: the look's ground with a soft top light and a vignette. */
export const Ground: React.FC<{light?: {x: number; y: number}}> = ({light = {x: 0.5, y: 0.32}}) => {
  const look = useLook();
  const dark = isDarkHex(look.ground);
  return (
    <AbsoluteFill style={{background: look.ground}}>
      <AbsoluteFill style={{background: `radial-gradient(70% 60% at ${light.x * 100}% ${light.y * 100}%, ${dark ? 'rgba(255,255,255,0.10)' : 'rgba(255,255,255,0.75)'}, rgba(255,255,255,0) 70%)`}} />
      <AbsoluteFill style={{background: `radial-gradient(120% 90% at 50% 45%, rgba(0,0,0,0) 60%, ${dark ? 'rgba(0,0,0,0.5)' : 'rgba(30,26,20,0.10)'} 100%)`}} />
    </AbsoluteFill>
  );
};
