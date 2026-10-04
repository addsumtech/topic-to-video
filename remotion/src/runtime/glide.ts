// THE BASELINE UNLOCK — type that MOVES glides with its drawing instead of stepping a whole pixel at a time.
//
// THE DEFECT. Chrome draws text through Skia, and Skia SNAPS a glyph run's baseline to a whole device pixel
// whenever the text's matrix keeps the x axis on the x axis (`SkScalerContextRec::computeAxisAlignmentForHText`:
// skewY == 0 -> kX, y rounded to the pixel; x keeps quarter-pixel positions). A scale plus a translate is exactly
// such a matrix, and so is a `top` that changes. So type that moves SLOWLY — under a camera push, across a page
// tour, on a drift, in the long tail of an ease-out — holds still for several frames and then jumps a pixel, while
// the rules, shapes and pictures beside it glide. A viewer saw it on a delivered film's push (字体还是会有很轻微的
// 抖动): measured as each text block's ink centroid against the camera's own curve, a ±0.5px sawtooth, RMS 0.27px,
// against 0.05px for the sheet border in the same layer.
//
// THE CURE. A skewY makes the matrix non-axis-aligned, and Skia then positions the run to a quarter pixel on BOTH
// axes: on the same push the residual fell to 0.02-0.07px. Skia rounds every matrix entry to 1/1024 before it
// decides (`sk_relax`), so the skew Skia SEES — this constant times every scale above the type — must stay at least
// half of 1/1024 or it rounds to nothing: measured, a 0.02° rotation left the sawtooth intact and 0.03° removed it.
// That is what `under` is for. At 1/1024 the skew tilts a horizontal line by one pixel per 1024 — under a pixel at
// either edge of a 1920-wide frame, and constant while it is on.
//
// WHY ONE FILE. `runtime/depth.tsx` found the defect on the scene camera and fixed it there. Every OTHER path that
// moves type — the film's seams and its whole-film drift, a camera over a page, a stage's labels, a register's own
// drift or scroll — had the same matrix and the same staircase. A fix written once per path is a fix the next path
// forgets, so the unlock is described here once and every path asks for it.
//
// WHEN IT IS ON — over a SPAN, never a frame. The span is the stretch in which the transform CAN change: a beat
// whose camera moves (before the push starts and after it lands included), a seam, a reveal's window. Switched on
// with the motion itself the type would jump from whole-pixel to quarter-pixel on the frame the motion starts — a
// pop in place of the staircase. Outside every span nothing is added, so a frame on which nothing moves is
// byte-identical to one drawn without this file.
//
// WHAT HOLDS IT IN PLACE. `scripts/text_safe_qa.py --glide` walks the DOM on every frame (runtime/textSafe.tsx,
// `auditGlide`) and reports type whose composed matrix is axis-aligned while its true position crawls by less than
// a pixel a frame — so a span somebody forgot is a finding, not a viewer's complaint.
import React from 'react';

/** The skew, in matrix units: the smallest entry Skia's 1/1024 rounding keeps at full size. */
export const BASELINE_UNLOCK_SKEW = 1 / 1024;
// what a skewed full-frame layer must reach past the frame edge, beyond the skew's own tilt: rounding and the
// edge's anti-aliasing, so no sliver of whatever lies under the layer shows along the top or bottom of the frame
const UNLOCK_EDGE_MARGIN_PX = 1;

/**
 * The smallest scale at which a layer carrying the unlock still covers the frame edge nearest its centre.
 *
 * `reach` is the distance from the layer's transform origin to that edge, `halfWidth` how far the layer extends to
 * either side of the origin (the skew lifts one end and drops the other by the skew times that), and `shift` any
 * translation the layer ALSO makes toward the edge, applied inside the scale. Solved for s in
 * s * (reach - |shift| - tilt) >= reach + margin.
 */
export const unlockCoverScale = (reach: number, halfWidth: number, shift = 0): number => {
  const tilt = BASELINE_UNLOCK_SKEW * halfWidth;
  const room = reach - Math.abs(shift) - tilt;
  if (!(room > UNLOCK_EDGE_MARGIN_PX)) {
    throw new Error(`unlockCoverScale: a layer whose origin is ${reach}px from the frame edge, shifted ${shift}px, ` +
      `has no room left for the unlock's ${tilt.toFixed(2)}px tilt; no scale about it keeps the frame covered.`);
  }
  return (reach + UNLOCK_EDGE_MARGIN_PX) / room;
};

/**
 * The extra scale a full-frame layer skewed by BASELINE_UNLOCK_SKEW about (W/2, originY) needs to keep covering
 * the frame.
 *
 * A skewY leaves the left and right edges where they are and tilts the top and bottom ones by the skew times
 * half the width, so at scale 1 a sliver of frame is uncovered at two corners. Solved for the smallest scale at
 * which the nearer of the top and bottom edges still clears the frame: (s-1)*reach >= s*tilt + margin.
 */
export const baselineUnlockOverscan = (W: number, H: number, originY: number): number => {
  const tilt = BASELINE_UNLOCK_SKEW * W / 2;
  const reach = Math.min(originY, H - originY);
  if (!(reach > tilt + UNLOCK_EDGE_MARGIN_PX)) {
    throw new Error(`baselineUnlockOverscan: the camera's origin (y=${originY}) sits on the frame's edge ` +
      `(${W}x${H}); no scale about it can keep a skewed layer covering the frame.`);
  }
  return (tilt + UNLOCK_EDGE_MARGIN_PX) / (reach - tilt);
};

/** The unlock as ONE css transform function. `matrix()` and not `skewY(<deg>)`: the entry Skia reads is then
 *  exactly the constant, with no degree round trip. CSS matrix(a, b, c, d, e, f) puts `b` in the y row's x
 *  column — the skewY entry. */
export const BASELINE_UNLOCK = `matrix(1, ${BASELINE_UNLOCK_SKEW}, 0, 1, 0, 0)`;

/**
 * The unlock for type drawn at scale `under` — the smallest uniform scale the type sits at, counting this
 * transform's own scale and every one above it.
 *
 * Skia judges the skew TIMES that scale, so a page toured at 0.4 under the plain constant shows Skia 0.4/1024,
 * which rounds to zero, and the type snaps again with the unlock written on it. Below full size the skew is raised
 * by exactly what the scale takes away; at or above it the plain constant is already enough. `unlockSkewFor` is the
 * same skew as a number, for code that has to say where a point lands under it (pageCam2D's `pageToScreen`).
 */
export const unlockSkewFor = (under = 1): number => {
  if (!(under > 0) || !isFinite(under)) {
    throw new Error(`unlockFor: the scale type is drawn at must be a positive number, got ${under}.`);
  }
  return under >= 1 ? BASELINE_UNLOCK_SKEW : BASELINE_UNLOCK_SKEW / under;
};
export const unlockFor = (under = 1): string =>
  under >= 1 ? BASELINE_UNLOCK : `matrix(1, ${unlockSkewFor(under)}, 0, 1, 0, 0)`;

/**
 * A transform that MOVES type, carrying the unlock while `on`.
 *
 * `on` is the span, decided over the whole stretch in which this transform can change — never "is it moving on
 * THIS frame" (see the header). `under` as in `unlockFor`. Off the span the transform comes back exactly as given,
 * so a frame outside every span is the frame this file never touched. The unlock goes LAST, innermost: it tilts the
 * element about its own transform origin, before anything else moves it.
 */
export const glide = (transform: string | undefined, on: boolean, under = 1): string | undefined => {
  if (!on) return transform;
  const u = unlockFor(under);
  return transform && transform !== 'none' ? `${transform} ${u}` : u;
};

/**
 * THE OFF SWITCH — for identity proofs, never for a film.
 *
 * Some proofs compare a register's CURRENT source against its source at an older commit, rendered side by side in
 * one bundle (tests/test_slot_identity.py). The old source never asked for the unlock, so any frame on which the
 * current one does would differ for a reason that has nothing to do with what the proof is about. Rendering both
 * with this set false makes every path that honours it draw exactly what it drew before the unlock existed — which
 * is also how the census proves it can SEE the defect (CameraTypeProbe's `legacy` camera).
 */
export const BaselineUnlockContext = React.createContext<boolean>(true);

/** `glide`, honouring the off switch. A hook: call it once at the top of a component, then use what it returns. */
export const useGlide = () => {
  const allowed = React.useContext(BaselineUnlockContext);
  return (transform: string | undefined, on: boolean, under = 1) => glide(transform, allowed && on, under);
};
