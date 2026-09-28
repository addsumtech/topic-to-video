// OBJECT · DemoForm — the stages' own preview: slabs stacked into one form, drawn in 3D and turned by `yaw`.
// ObjectStage, ObjectCompare, ObjectPath and ObjectTurntable show it when rendered on their own, so a stage's
// preview — and its measurement — has a real object in it. A FILM never shows it: `demo` is in its META and
// validate.py refuses it by name. It carries no words.
//
// It is also the reference for an object that draws its own 3D turn (`turns: true`): its corners are rotated by
// `yaw` (runtime/project3d yawPoint) and projected into the object's own box (project); faces turned away are
// culled by their normals and the rest painted far to near. references/object-authoring.md points here.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '../runtime/objectSlot';
import {project, yawPoint, type Vec3} from '../runtime/project3d';
import {clamp01, seg, easeOutCubic} from '../runtime/motion';
import {mix, relLum} from '../runtime/dna';

export const DEMO_ID = 'DemoForm';
export const META: ObjectMeta = {aspect: 1, turns: true, demo: true, provenance: 'motion-graphics'};

const SURF_D0 = '#e9edf3', ACC_D0 = '#3563e9', INK_D0 = '#1c2230';
// the camera, fitted so the whole stack stays inside its box at any yaw (half-height 2.3 units at the aim)
const CAM: Vec3 = [0, 2.6, 8.2], AIM: Vec3 = [0, 0, 0], FOV = 30;
const LIGHT: Vec3 = [-0.45, 0.8, 0.4];
// Where the bottom slab's BOTTOM FACE sits, in world-Y — seated flush with the box floor AT THE OBJECT'S
// OWN DEFAULT YAW (0.6, a ~1.5% gap), not at every yaw: the stack is a rigid rotation of a shape wider than
// it is deep, so its lowest corner's distance from the floor varies with which corner that turn currently
// presents, from a 1.9px hairline up to 59px of its own box height at the widest presentation. Solved
// numerically (bisection through `project()`+`yawPoint()` themselves, sweeping every yaw and all four of
// the widest slab's corners): the naive candidate — the Y that puts the box-AXIS (x=z=0) on the floor pixel
// — ignores that a corner near the camera reads LOWER in frame than the axis does at the same Y, and
// seating the axis there ran real corners ~20% past the box. This is the lowest Y at which every corner, at
// every yaw, still lands INSIDE the box — the gap varies, but a clipped corner never happens.
const SEAT_Y = -1.6;

const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const unit = (a: Vec3): Vec3 => {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};
// `runtime/dna.tsx`'s relLum reads a 6-digit hex only and reports 0 (reads as dark) for anything shorter —
// so a DNA authored with the 3-digit shorthand (`fg: '#fff'`) would relLum as dark and shade toward WHITE,
// backwards on the very ground that shorthand most often means. Expanded here, not in dna.tsx (not edited).
const hex6 = (c: string): string =>
  /^#[0-9a-fA-F]{3}$/.test(c) ? '#' + [...c.slice(1)].map((ch) => ch + ch).join('') : c;

export const DemoForm: React.FC<ObjectProps & {layers?: number}> = ({w, h, t, dna, yaw, layers = 3}) => {
  if (!Number.isInteger(layers) || layers < 1 || layers > 5) {
    throw new Error(`DemoForm: \`layers\` is a whole number from 1 to 5 (got ${JSON.stringify(layers)})`);
  }
  const surf = dna?.surface ?? SURF_D0, acc = dna?.accent ?? ACC_D0, ink = dna?.fg ?? INK_D0;
  // THE POLARITY THIS OBJECT OWNS. `ink` (dna.fg) is the film's readable ink, so it is light exactly when
  // its ground is dark (true of all eight shipped presets) and dark exactly when its ground is light (this
  // object's own D0 fallback ground, `eef0f3`). A face in shadow mixes toward BLACK on a dark ground and
  // toward `ink` — already dark there — on a light one; either way it darkens, never the pale glow a flat
  // mix toward `ink` painted when `ink` itself turned out to be the film's near-white text colour.
  const darkGround = relLum(hex6(ink)) > 0.5;
  const shadeInk = darkGround ? '#000000' : ink;
  const Y = yaw ?? 0.6;
  const light = unit(LIGHT);
  const faces: {d: string; depth: number; fill: string}[] = [];
  for (let i = 0; i < layers; i++) {
    // each slab drops into its place in turn; the stack is whole by t = 0.9
    const at = (i / layers) * 0.5;
    const drop = easeOutCubic(clamp01(seg(t, at, at + 0.4)));
    const hx = 1.3 - i * 0.18, hz = 0.95 - i * 0.13, hy = 0.18;
    // SEAT_Y seats the bottom slab's settled underside on the box's own floor; the drop still starts 1.4
    // above wherever a slab settles, and every layer's own corners stay inside the box through that fall at
    // every yaw (checked for 1-5 layers and the full yaw sweep: the tightest is layers=5's own start, 0.8%
    // of the box's height under its ceiling — a real margin, not a coincidence of one angle).
    const cy = SEAT_Y + hy + i * 0.5 + (1 - drop) * 1.4;
    // EVERY LAYER KEEPS A MINIMUM STEP OFF THE MATERIAL'S OWN SURFACE TONE, not just the accent-heavy top
    // ones: at i=0 (layers>1) a 0% mix toward the accent makes `tone` exactly `surf` — indistinguishable
    // from a ground that (on this object's own light D0 fallback) is itself close to `surf`, a container fill
    // designed to sit near a page's own colour. The floor is 0.25, not a round 0.2: the bottom slab's own top
    // face (the closest any face comes to the null-DNA ground) clears `runtime/dna.tsx`'s own TONE_MIN_STEP
    // (0.10, the step a filled region must clear to read as a region rather than as the ground) at 0.25 with
    // nothing to spare — 0.2 cleared only 0.081 of it.
    const tone = mix(surf, acc, layers > 1 ? 0.25 + (i / (layers - 1)) * 0.4 : 0.3);
    const corner = (sx: number, sy: number, sz: number): Vec3 => yawPoint([sx * hx, cy + sy * hy, sz * hz], Y);
    const quads: {pts: Vec3[]; n: Vec3}[] = [
      {pts: [corner(-1, 1, -1), corner(1, 1, -1), corner(1, 1, 1), corner(-1, 1, 1)], n: [0, 1, 0]},
      {pts: [corner(-1, -1, 1), corner(1, -1, 1), corner(1, 1, 1), corner(-1, 1, 1)], n: yawPoint([0, 0, 1], Y)},
      {pts: [corner(-1, -1, -1), corner(1, -1, -1), corner(1, 1, -1), corner(-1, 1, -1)], n: yawPoint([0, 0, -1], Y)},
      {pts: [corner(1, -1, -1), corner(1, -1, 1), corner(1, 1, 1), corner(1, 1, -1)], n: yawPoint([1, 0, 0], Y)},
      {pts: [corner(-1, -1, -1), corner(-1, -1, 1), corner(-1, 1, 1), corner(-1, 1, -1)], n: yawPoint([-1, 0, 0], Y)},
    ];
    for (const q of quads) {
      const c: Vec3 = [0, 1, 2].map((k) => q.pts.reduce((a, p) => a + p[k], 0) / 4) as Vec3;
      if (dot(q.n, sub(CAM, c)) <= 0) continue;                  // turned away: never painted
      const proj = q.pts.map((p) => project(p, CAM, AIM, FOV, w, h));
      if (proj.some((p) => p === null)) continue;
      const lit = clamp01(0.55 + 0.45 * dot(q.n, light));
      // LIT READS LIGHTER AND SHADED READS DARKER THAN THE BASE TONE, on either ground: `bias` recentres
      // `lit` on its own midpoint, so the best-lit face of a side pair is pushed toward white and the
      // worst-lit toward `shadeInk`, rather than the old one-sided "less dark, never actually lighter".
      const bias = (lit - 0.55) / 0.45;
      const fill = q.n[1] > 0.5 ? mix(tone, '#ffffff', 0.22)
        : bias >= 0 ? mix(tone, '#ffffff', 0.14 * bias) : mix(tone, shadeInk, 0.28 * -bias);
      faces.push({d: 'M' + proj.map((p) => `${p!.x.toFixed(1)} ${p!.y.toFixed(1)}`).join(' L') + ' Z',
        depth: Math.hypot(...sub(c, CAM)), fill});
    }
  }
  faces.sort((a, b) => b.depth - a.depth);                         // far to near
  const edge = mix(ink, surf, 0.55);
  return (
    <svg width={w} height={h} style={{display: 'block', overflow: 'visible'}}>
      {faces.map((f, k) => (
        <path key={k} d={f.d} fill={f.fill} stroke={edge} strokeWidth={Math.max(1, w * 0.0025)} strokeLinejoin="round" />
      ))}
    </svg>
  );
};
