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
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {track, useLook, isDarkHex, type Key} from './kit';
import {unlockFor, BaselineUnlockContext} from '../runtime/glide';

export type CamKey = Key & {f: number; cx: number; cy: number; zoom: number; rx?: number; ry?: number; rz?: number; persp?: number};

const warned = new Set<string>();

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
  children?: React.ReactNode;
}> = ({src, w, h, keys, radius = 12, maxZoom = 2, frameOverride, blur = 0, contain = true, focusY = 0.5, children}) => {
  const f0 = useCurrentFrame();
  const frame = frameOverride ?? f0;
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const allowed = React.useContext(BaselineUnlockContext);
  const cap = maxZoom * 1.0001;
  // `zoom` is authored at a 1920-wide reference (1 = one CSS px per screen px on a 1920 frame); what the texture must
  // carry is the EFFECTIVE density on this frame — at 9:16 the same key is 0.5625 of it.
  const poseAt = (f: number): Pose => {
    let cx = track(keys, f, 'cx'), cy = track(keys, f, 'cy');
    let zoom = Math.min(cap, track(keys, f, 'zoom', 1) * (W / 1920));
    const rx = track(keys, f, 'rx'), ry = track(keys, f, 'ry'), rz = track(keys, f, 'rz');
    // CONTAIN: a straight-on view stays inside the capture — the edge of a web page and the ground past it are not
    // part of the product. Where the view is wider (taller) than the page it is centred instead. A tilted view is a
    // deliberate object shot (the window on its ground), so containment fades out as the tilt grows (none from 6°).
    if (contain) {
      // how much containment applies, SMOOTH in the tilt: `1 - |tilt|/6` clamped at 0 had a corner where a tilt crossed
      // zero (|x|) and another at 6° (the clamp) — each a corner in the camera's path, measured as a stepping shot
      const k = Math.exp(-(rx * rx + ry * ry + rz * rz) / 18);
      const vw = W / zoom, vh = H / zoom;
      // a SOFT clamp: a hard min/max puts a corner in the camera's path the frame the view meets the page edge (the
      // pan speed jumps — measured as a 1.25 px step across every tile of a probe push); smoothed over ~40 px of page,
      // the view eases onto the edge instead
      const sMax = (a: number, b: number, kk = 40) => (a + b + Math.sqrt((a - b) * (a - b) + kk * kk)) / 2;
      const sMin = (a: number, b: number, kk = 40) => (a + b - Math.sqrt((a - b) * (a - b) + kk * kk)) / 2;
      const clampTo = (c: number, v: number, size: number, fr = 0.5) => (v >= size ? size / 2
        : sMin(size - v * (1 - fr), sMax(v * fr, c)));
      cx = cx + (clampTo(cx, vw, w) - cx) * k;
      cy = cy + (clampTo(cy, vh, h, focusY) - cy) * k;
    }
    zoom = Math.max(1e-3, zoom);
    return {cx, cy, zoom, rx, ry, rz, persp: track(keys, f, 'persp', 1600)};
  };
  const P = poseAt(frame);
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
  const raster = Math.max(1e-3, Math.min(cap, maxKey)) * 1.1;          // headroom for a lifted element (scale <= 1.1)
  const s = P.zoom / raster;
  const url = /^(https?:|data:|\/)/.test(src) ? src : staticFile(src);
  const info: PageCamInfo = {W, H, focusY, poseAt, toScreen: (f, x, y) => {
    const q = poseAt(f);
    return {x: W / 2 + (x - q.cx) * q.zoom, y: H * focusY + (y - q.cy) * q.zoom};
  }};
  return (
    <AbsoluteFill style={{overflow: 'hidden', filter: blur > 0 ? `blur(${blur}px)` : undefined}}>
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
              <Img src={url} style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
            </div>
            <PageCamContext.Provider value={info}>{children}</PageCamContext.Provider>
          </div>
        </div>
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
