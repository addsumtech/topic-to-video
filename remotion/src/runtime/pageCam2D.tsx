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
import {BaselineUnlockContext, baselineUnlockOverscan, unlockSkewFor} from './glide';

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

// ── the baseline unlock, for a camera over a page ─────────────────────────────────────────────────────────
// A tour is a translate and a scale — exactly the matrix under which Skia rounds every line of type on the page to
// a whole pixel (runtime/glide.ts), so a page drifting under the lens steps a pixel at a time against its own
// rules and pictures. A tour whose keys move carries the unlock for its whole beat; one that never moves carries
// nothing and draws exactly what it drew before.
//
// Two things are particular to a page. Its scale goes far below 1 at the overview, and Skia judges the skew TIMES
// that scale, so the skew is raised for the smallest scale the tour reaches (`under`). And the skew is applied in
// SCREEN space about the view's centre, so its tilt is the same at every zoom and `pageToScreen` can say exactly
// where a point lands — the cursor, the ripple and the labels drawn over the page stay registered to it. `cover`
// adds the overscan the tilt needs when the page fills the view to its edge (runtime/glide.ts
// `baselineUnlockOverscan`), folded into the scale so the camera and `pageToScreen` still agree.
export type CamUnlock = {on: boolean; under: number; cover: boolean};

/** Does a tour move at all? Its unlock rides the whole beat if any key differs from the first. */
export const camMoves = (keys: CamKey[]): boolean =>
  keys.some((k) => k.x !== keys[0].x || k.y !== keys[0].y || k.s !== keys[0].s);

/** The unlock a tour over these keys carries. `cover`: the page can fill the view to its edges. */
export const camUnlock = (keys: CamKey[], cover = true): CamUnlock => ({
  on: keys.length > 0 && camMoves(keys), under: Math.min(1, ...keys.map((k) => k.s)), cover,
});

/** `unlock` with the identity proofs' off switch applied (runtime/glide.ts BaselineUnlockContext). */
export const useCamUnlock = (unlock?: CamUnlock): CamUnlock | undefined => {
  const allowed = React.useContext(BaselineUnlockContext);
  return unlock && unlock.on && allowed ? unlock : undefined;
};

/** The scale the camera actually draws at: `cam.s`, plus the unlock's overscan when the page covers the view. */
const drawnScale = (cam: Cam, W: number, H: number, unlock?: CamUnlock) =>
  unlock && unlock.on && unlock.cover ? cam.s * (1 + baselineUnlockOverscan(W, H, H / 2)) : cam.s;

/** The css transform that puts page point (cam.x, cam.y) at the centre of a W x H view — and the unlock with it.
 *  Applied with `transform-origin: 0 0`. One description of the camera for every register that tours a page. */
export const pageCamTransform = (cam: Cam, W: number, H: number, unlock?: CamUnlock): string => {
  const s = drawnScale(cam, W, H, unlock);
  const move = `translate(${W / 2 - cam.x * s}px, ${H / 2 - cam.y * s}px) scale(${s})`;
  if (!unlock || !unlock.on) return move;
  const k = unlockSkewFor(unlock.under);
  return `translate(${W / 2}px, ${H / 2}px) matrix(1, ${k}, 0, 1, 0, 0) translate(${-W / 2}px, ${-H / 2}px) ${move}`;
};

/** Where a page point lands in the frame, under `cam`. The inverse of what the wrapper transform does — with the
 *  same unlock the wrapper was given, or a mark drawn over the page lands up to a pixel off what it names. */
export const pageToScreen = (cam: Cam, W: number, H: number, px: number, py: number, unlock?: CamUnlock) => {
  const s = drawnScale(cam, W, H, unlock);
  const x = W / 2 + (px - cam.x) * s;
  const y = H / 2 + (py - cam.y) * s;
  return unlock && unlock.on ? {x, y: y + unlockSkewFor(unlock.under) * (x - W / 2)} : {x, y};
};

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
  /** the tour's unlock (`camUnlock(keys)`); pass the SAME value to `pageToScreen` */
  unlock?: CamUnlock;
  children?: React.ReactNode;
}> = ({cam, W, H, pageW, pageH, unlock, children}) => {
  if (!(pageW > 0 && pageH > 0)) {
    throw new Error(`pageCam2D: the page has no size (${pageW}x${pageH}). A camera over nothing renders an ` +
      'empty frame, which looks like a shot that has not started rather than like the bug it is.');
  }
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: pageW, height: pageH,
        transformOrigin: '0 0', transform: pageCamTransform(cam, W, H, unlock)}}>
        {children}
      </div>
    </div>
  );
};

export default PageCam2D;
