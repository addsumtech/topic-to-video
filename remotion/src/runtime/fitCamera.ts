// FRAME THE SHOT AT THE ASPECT IT WAS GIVEN — by asking the projection, not by trusting a formula.
//
// WHY THIS EXISTS. A 3D register is composed at one aspect and then rendered at four others, and the camera
// that framed it at 16:9 is simply wrong at 4:3: the same object, the same lens, a third less horizontal
// field. `PortRail` ran its rail off both edges there. The obvious repair — solve the distance in closed form
// from the object's radius and the horizontal half-angle — is what `MaterialHero` did first, and it is only
// approximately right: the half of an object NEARER the lens projects LARGER than its centre depth predicts,
// so the formula under-reports the extent by exactly the amount perspective adds, and the error grows as the
// frame narrows. It fitted at 9:16 because the margin absorbed it, and came within 14px of failing at 4:3.
//
// So nothing is derived twice. The distance is found by PROJECTING the object's own extreme points with the
// same `project()` the shot's labels use and backing off until they land inside the box the shot may use.
// Extent is monotone in distance, so a bisection converges in a handful of steps and costs nothing.
//
// The BOX is the second half of the idea. A shot does not own the whole frame: the caption band belongs to
// the renderer, a copy block under the object belongs to the copy, and a row of labels above it needs room to
// exist. Handing those in as a box means "does it fit" and "does it collide with my own type" are one
// question with one answer, instead of a fit followed by a clamp that pushes the title onto the object.

import {project, type Vec3} from './project3d';

/** The region of the frame, in pixels, that the object is allowed to occupy. */
export type FitBox = {left: number; right: number; top: number; bottom: number};

const norm = (a: Vec3): Vec3 => {
  const l = Math.hypot(a[0], a[1], a[2]);
  if (!(l > 1e-9)) {
    throw new Error('fitCamera: the camera direction is a zero vector — the lens and its target are the ' +
      'same point, which has no framing.');
  }
  return [a[0] / l, a[1] / l, a[2] / l];
};

const at = (aim: Vec3, dir: Vec3, d: number): Vec3 => [aim[0] + dir[0] * d, aim[1] + dir[1] * d, aim[2] + dir[2] * d];

/** The projected bounding box of `pts`, or null if any point is behind the lens. */
export const screenBounds = (
  pts: Vec3[], cam: Vec3, aim: Vec3, fovDeg: number, W: number, H: number,
): {x0: number; x1: number; y0: number; y1: number} | null => {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of pts) {
    const s = project(p, cam, aim, fovDeg, W, H);
    if (!s) return null;                       // behind the lens: there is no honest bounding box
    x0 = Math.min(x0, s.x); x1 = Math.max(x1, s.x);
    y0 = Math.min(y0, s.y); y1 = Math.max(y1, s.y);
  }
  return pts.length ? {x0, x1, y0, y1} : null;
};

/**
 * The smallest distance along the camera's own axis at which every point of `pts` lands inside `box`.
 *
 * Never returns less than `d0`: the composed framing is a design decision, and this exists to rescue the
 * aspects that do not fit it, not to re-crop the one it was drawn for.
 */
export type FitGroup = {pts: Vec3[]; box: FitBox};

/**
 * Groups exist because different parts of a shot are owed different amounts of room AT DIFFERENT MOMENTS.
 *
 * PortRail's modules ARRIVE from above; while a module is still travelling its label is not drawn, so it owes
 * the label row nothing and only has to be inside the frame. Fitting the travelling pose against the settled
 * pose's reservations shrank the whole composition by a third to protect a row of type that does not exist
 * yet. One box for the settled shot, a looser one for the move, and the frame is sized by what is actually
 * on it.
 */
export const fitDistanceMulti = (
  groups: FitGroup[], aim: Vec3, dir: Vec3, fovDeg: number, W: number, H: number, d0: number,
): number => {
  if (!groups.length) throw new Error('fitCamera: nothing to frame — no groups.');
  for (const g of groups) {
    if (!(g.box.right > g.box.left && g.box.bottom > g.box.top)) {
      throw new Error(`fitCamera: a box has no area (left ${g.box.left} right ${g.box.right} ` +
        `top ${g.box.top} bottom ${g.box.bottom}). A shot given no room to draw in cannot be framed, and ` +
        'silently returning some distance would hide whichever reservation grew past the frame.');
    }
    if (!g.pts.length) throw new Error('fitCamera: nothing to frame — a group has no points.');
  }
  const u = norm(dir);
  const fits = (d: number) => {
    const cam = at(aim, u, d);
    for (const g of groups) {
      const b = screenBounds(g.pts, cam, aim, fovDeg, W, H);
      if (!b || b.x0 < g.box.left || b.x1 > g.box.right || b.y0 < g.box.top || b.y1 > g.box.bottom) return false;
    }
    return true;
  };
  if (fits(d0)) return d0;
  let hi = d0;
  for (let i = 0; i < 48 && !fits(hi); i++) hi *= 1.2;
  let lo = d0;
  for (let i = 0; i < 26; i++) {
    const mid = (lo + hi) / 2;
    if (fits(mid)) hi = mid; else lo = mid;
  }
  return hi;
};

export const fitDistance = (
  pts: Vec3[], aim: Vec3, dir: Vec3, fovDeg: number, W: number, H: number, box: FitBox, d0: number,
): number => {
  if (!(box.right > box.left && box.bottom > box.top)) {
    throw new Error(`fitCamera: the box has no area (left ${box.left} right ${box.right} top ${box.top} ` +
      `bottom ${box.bottom}). A shot given no room to draw in cannot be framed, and silently returning some ` +
      'distance would hide whichever reservation grew past the frame.');
  }
  if (!pts.length) throw new Error('fitCamera: nothing to frame — `pts` is empty.');
  const u = norm(dir);
  const fits = (d: number) => {
    const b = screenBounds(pts, at(aim, u, d), aim, fovDeg, W, H);
    return !!b && b.x0 >= box.left && b.x1 <= box.right && b.y0 >= box.top && b.y1 <= box.bottom;
  };
  if (fits(d0)) return d0;
  let hi = d0;
  for (let i = 0; i < 48 && !fits(hi); i++) hi *= 1.2;
  let lo = d0;
  for (let i = 0; i < 26; i++) {
    const mid = (lo + hi) / 2;
    if (fits(mid)) hi = mid; else lo = mid;
  }
  return hi;
};

/**
 * Distance AND position: fit, then slide the rig sideways so the object sits in the MIDDLE of the box it is
 * allowed, then fit again because moving changed what fits.
 *
 * Fitting alone is not enough when the box is lopsided — reserve a copy block under the object and a pure
 * pull-back answers by shrinking the object until it clears the copy, leaving the air at the top. Panning
 * spends that air instead, which is what a camera operator would do.
 */
export const frameCamera = (
  groups: FitGroup[], aim0: Vec3, dir: Vec3, fovDeg: number, W: number, H: number, d0: number,
  axes: {x: boolean; y: boolean} = {x: true, y: true}, rounds = 3,
): {cam: Vec3; aim: Vec3; dist: number} => {
  const u = norm(dir);
  let aim: Vec3 = [aim0[0], aim0[1], aim0[2]];
  let d = d0;
  // Centring follows the FIRST group: that is the settled composition, the frame a viewer actually reads.
  // Centring on the union would let a pose that exists for a third of a second decide where the shot sits.
  const lead = groups[0];
  for (let r = 0; r < rounds; r++) {
    d = fitDistanceMulti(groups, aim, u, fovDeg, W, H, d0);
    const cam = at(aim, u, d);
    const b = screenBounds(lead.pts, cam, aim, fovDeg, W, H);
    if (!b) break;
    // pixels the object must move to sit centred, converted through the local scale at the aim's depth
    const dxPx = (lead.box.left + lead.box.right) / 2 - (b.x0 + b.x1) / 2;
    const dyPx = (lead.box.top + lead.box.bottom) / 2 - (b.y0 + b.y1) / 2;
    const tanH = Math.tan((fovDeg * Math.PI) / 360);
    const perUnitY = H / 2 / (d * tanH);
    const perUnitX = W / 2 / (d * tanH * (W / H));
    // The rig TRANSLATES: lens and target move together, so the view direction never changes and the
    // look-down angle the shot was composed at survives every aspect.
    if (axes.x) aim = [aim[0] - dxPx / perUnitX, aim[1], aim[2]];
    if (axes.y) aim = [aim[0], aim[1] + dyPx / perUnitY, aim[2]];
  }
  d = fitDistanceMulti(groups, aim, u, fovDeg, W, H, d0);
  return {cam: at(aim, u, d), aim, dist: d};
};

/** The 8 corners of an axis-aligned box — the point set a rectangular part contributes to a fit. */
export const boxCorners = (centre: Vec3, half: Vec3): Vec3[] => {
  const out: Vec3[] = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) {
    out.push([centre[0] + half[0] * sx, centre[1] + half[1] * sy, centre[2] + half[2] * sz]);
  }
  return out;
};
