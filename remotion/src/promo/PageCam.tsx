// PROMO · PageCam — a 2.5D camera over a real product capture (references/promo-film.md §camera).
//
// The capture is a 2x screenshot shown at its CSS size (w x h = pixels / 2). A key {f, cx, cy, zoom, rx, ry, rz}
// puts the page point (cx, cy) at the frame's centre at `zoom` screen px per CSS px, tilted rx (top leans away),
// ry (right edge recedes), rz (roll). Children are positioned in the SAME page CSS px, so an overlay sits on the
// element it belongs to at every camera pose.
//
// SHARPNESS. The magnification is the CSS `zoom` property, not transform: scale(). A 3D-transformed layer is
// rasterised at its LAYOUT size and then scaled by the compositor, so with scale() a 2x capture is first sampled
// down to 1x and then blown up — soft text at exactly the close-ups that matter. `zoom` enlarges the layout box
// itself, so the capture is rasterised at the enlarged size from its 2x pixels. The rule that follows: a key's
// zoom may not exceed the capture's density (`maxZoom`, 2 for a 2x capture) — past it the texture is upsampled and
// the film shows it. The camera clamps there and says so once.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {track, useLook, type Key} from './kit';

export type CamKey = Key & {f: number; cx: number; cy: number; zoom: number; rx?: number; ry?: number; rz?: number; persp?: number};

const warned = new Set<string>();

export const PageCam: React.FC<{
  src: string;               // a file in the film's public dir (render --public-dir), or an absolute URL
  w: number; h: number;      // the capture's CSS size
  keys: CamKey[];
  radius?: number;           // window corner radius, CSS px
  maxZoom?: number;          // capture density: 2 for a 2x capture
  frameOverride?: number;    // drive the camera from an outer clock
  blur?: number;             // screen-space defocus (an outro's back row)
  children?: React.ReactNode;
}> = ({src, w, h, keys, radius = 12, maxZoom = 2, frameOverride, blur = 0, children}) => {
  const f0 = useCurrentFrame();
  const frame = frameOverride ?? f0;
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const cx = track(keys, frame, 'cx'), cy = track(keys, frame, 'cy');
  let zoom = track(keys, frame, 'zoom', 1) * (W / 1920);
  const cap = maxZoom * (W / 1920) * 1.0001;
  if (zoom > cap) {
    if (!warned.has(src)) { warned.add(src); console.warn(`[PageCam] ${src}: zoom ${zoom.toFixed(2)} past the capture's density ${maxZoom}; clamped`); }
    zoom = cap;
  }
  const rx = track(keys, frame, 'rx'), ry = track(keys, frame, 'ry'), rz = track(keys, frame, 'rz');
  const persp = track(keys, frame, 'persp', 1600);
  const url = /^(https?:|data:|\/)/.test(src) ? src : staticFile(src);
  return (
    <AbsoluteFill style={{overflow: 'hidden', filter: blur > 0 ? `blur(${blur}px)` : undefined}}>
      <div style={{position: 'absolute', inset: 0, perspective: `${persp * zoom}px`, perspectiveOrigin: `${W / 2}px ${H / 2}px`}}>
        <div style={{
          position: 'absolute', left: 0, top: 0, width: w, height: h, zoom,
          transform: `translate(${W / 2 / zoom - cx}px, ${H / 2 / zoom - cy}px) rotateY(${ry}deg) rotateX(${rx}deg) rotateZ(${rz}deg)`,
          transformOrigin: `${cx}px ${cy}px`, transformStyle: 'preserve-3d',
        }}>
          {/* the window: its own corners and a two-layer shadow on the ground */}
          <div style={{position: 'absolute', inset: 0, borderRadius: radius, overflow: 'hidden',
            boxShadow: `0 2px 6px rgba(20,18,14,0.10), 0 30px 80px rgba(20,18,14,0.16), 0 0 0 1px ${look.groundEdge}`}}>
            <Img src={url} style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
          </div>
          {children}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** The ground the window floats on: the look's ground with a soft top light and a vignette. */
export const Ground: React.FC<{light?: {x: number; y: number}}> = ({light = {x: 0.5, y: 0.32}}) => {
  const look = useLook();
  return (
    <AbsoluteFill style={{background: look.ground}}>
      <AbsoluteFill style={{background: `radial-gradient(70% 60% at ${light.x * 100}% ${light.y * 100}%, rgba(255,255,255,0.75), rgba(255,255,255,0) 70%)`}} />
      <AbsoluteFill style={{background: 'radial-gradient(120% 90% at 50% 45%, rgba(0,0,0,0) 60%, rgba(30,26,20,0.10) 100%)'}} />
    </AbsoluteFill>
  );
};
