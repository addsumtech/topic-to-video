// A CAMERA OVER A PAGE — move a lens across something bigger than the frame, and know where things landed.
//
// WHY THIS EXISTS. Every "camera" in this library is welded into one register's own composition: CrashZoom
// punches into its own grid, TerrainFly flies its own heightmap. Not one of them can be handed an arbitrary
// page and asked to visit four places on it — which is the whole of the flyover/tour language, and the reason
// a tour of a product's screen was unreachable here.
//
// THE SECOND HALF IS THE POINT. Moving a page under a lens is a `transform` and takes four lines. Knowing
// where a page point ENDED UP on screen is what lets a cursor arrive with the camera, a label sit on the
// thing being pointed at, and a ripple land where the click was — all as ordinary DOM, in the film's own
// face, visible to the type gates. So `pageToScreen` is exported beside the transform and derived from the
// same numbers: one camera, described once. The alternative is what the 3D registers already taught this
// repo the hard way — two cameras that agree until they quietly do not, and a frame that reads as correct
// with everything labelled one position out.
//
// COORDINATES. Page space is plain CSS pixels inside a `pageW x pageH` box. A key names the page point that
// should sit at the CENTRE of the frame and the scale to see it at, so a keyframe table reads as a list of
// places to look rather than as a list of transforms.

import React from 'react';
import {clamp01} from './motion';

export type CamKey = {
  at: number;      // normalised time this key is reached
  x: number;       // page point that sits at frame centre, in page pixels
  y: number;
  s: number;       // scale: 1 = page pixels are frame pixels
};

export type Cam = {x: number; y: number; s: number};

const lerpN = (a: number, b: number, u: number) => a + (b - a) * u;

/**
 * The camera at time `t`, interpolated between the two keys around it.
 *
 * Holds before the first key and after the last on purpose: a tour that eases out of nowhere before its first
 * stop reads as the shot starting late.
 */
export const camAt = (keys: CamKey[], t: number, ease: (u: number) => number = (u) => u): Cam => {
  if (!keys.length) throw new Error('pageCam2D: a camera needs at least one key.');
  const ks = [...keys].sort((a, b) => a.at - b.at);
  if (t <= ks[0].at) return {x: ks[0].x, y: ks[0].y, s: ks[0].s};
  const last = ks[ks.length - 1];
  if (t >= last.at) return {x: last.x, y: last.y, s: last.s};
  for (let i = 0; i < ks.length - 1; i++) {
    const a = ks[i], b = ks[i + 1];
    if (t >= a.at && t <= b.at) {
      const u = ease(clamp01((t - a.at) / Math.max(1e-6, b.at - a.at)));
      return {x: lerpN(a.x, b.x, u), y: lerpN(a.y, b.y, u), s: lerpN(a.s, b.s, u)};
    }
  }
  return {x: last.x, y: last.y, s: last.s};
};

/** Where a page point lands in the frame, under `cam`. The inverse of what the wrapper transform does. */
export const pageToScreen = (cam: Cam, W: number, H: number, px: number, py: number) =>
  ({x: W / 2 + (px - cam.x) * cam.s, y: H / 2 + (py - cam.y) * cam.s});

/**
 * Keep the lens inside the page, so a close-up never shows the void beside it.
 *
 * A camera aimed at the top-left card is aimed near the EDGE of the page, and at close-up scale half the
 * frame then falls outside it — the screen the shot is touring appears to float with the backdrop showing
 * above it, which reads as a compositing mistake rather than as a camera move. Clamping the CENTRE by half a
 * frame in page units is the whole fix.
 *
 * When the page cannot cover the frame at this scale — the overview of a tour, where seeing the window whole
 * with ground around it IS the shot — there is nothing to clamp to, and it centres instead. That case is
 * detected rather than configured, so the same call is correct at both ends of a move.
 */
export const clampToPage = (cam: Cam, W: number, H: number, pageW: number, pageH: number): Cam => {
  const halfW = W / 2 / cam.s, halfH = H / 2 / cam.s;
  return {
    s: cam.s,
    x: pageW <= halfW * 2 ? pageW / 2 : Math.min(Math.max(cam.x, halfW), pageW - halfW),
    y: pageH <= halfH * 2 ? pageH / 2 : Math.min(Math.max(cam.y, halfH), pageH - halfH),
  };
};

/** The scale at which the whole page is just inside the frame — the "overview" a tour opens on. */
export const fitScale = (W: number, H: number, pageW: number, pageH: number, margin = 0.92) =>
  Math.min(W / pageW, H / pageH) * margin;

/**
 * The page, moved under the lens.
 *
 * `transform-origin: 0 0` and an explicit translate, rather than percentage translates: a percentage is
 * resolved against the element's own size, so the same declaration means something different the moment the
 * page's dimensions change, and the camera stops agreeing with `pageToScreen`.
 */
export const PageCam2D: React.FC<{
  cam: Cam;
  W: number;
  H: number;
  pageW: number;
  pageH: number;
  children?: React.ReactNode;
}> = ({cam, W, H, pageW, pageH, children}) => {
  if (!(pageW > 0 && pageH > 0)) {
    throw new Error(`pageCam2D: the page has no size (${pageW}x${pageH}). A camera over nothing renders an ` +
      'empty frame, which looks like a shot that has not started rather than like the bug it is.');
  }
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: pageW, height: pageH,
        transformOrigin: '0 0',
        transform: `translate(${W / 2 - cam.x * cam.s}px, ${H / 2 - cam.y * cam.s}px) scale(${cam.s})`}}>
        {children}
      </div>
    </div>
  );
};

export default PageCam2D;
