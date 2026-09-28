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
import {mix} from '../runtime/dna';

export const DEMO_ID = 'DemoForm';
export const META: ObjectMeta = {aspect: 1, turns: true, demo: true, provenance: 'motion-graphics'};

const SURF_D0 = '#e9edf3', ACC_D0 = '#3563e9', INK_D0 = '#1c2230';
// the camera, fitted so the whole stack stays inside its box at any yaw (half-height 2.3 units at the aim)
const CAM: Vec3 = [0, 2.6, 8.2], AIM: Vec3 = [0, 0, 0], FOV = 30;
const LIGHT: Vec3 = [-0.45, 0.8, 0.4];

const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const unit = (a: Vec3): Vec3 => {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
};

export const DemoForm: React.FC<ObjectProps & {layers?: number}> = ({w, h, t, dna, yaw, layers = 3}) => {
  if (!Number.isInteger(layers) || layers < 1 || layers > 5) {
    throw new Error(`DemoForm: \`layers\` is a whole number from 1 to 5 (got ${JSON.stringify(layers)})`);
  }
  const surf = dna?.surface ?? SURF_D0, acc = dna?.accent ?? ACC_D0, ink = dna?.fg ?? INK_D0;
  const Y = yaw ?? 0.6;
  const light = unit(LIGHT);
  const faces: {d: string; depth: number; fill: string}[] = [];
  for (let i = 0; i < layers; i++) {
    // each slab drops into its place in turn; the stack is whole by t = 0.9
    const at = (i / layers) * 0.5;
    const drop = easeOutCubic(clamp01(seg(t, at, at + 0.4)));
    const hx = 1.3 - i * 0.18, hz = 0.95 - i * 0.13, hy = 0.18;
    const cy = -0.72 + i * 0.5 + (1 - drop) * 1.4;
    const tone = mix(surf, acc, layers > 1 ? (i / (layers - 1)) * 0.6 : 0.3);
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
      const fill = q.n[1] > 0.5 ? mix(tone, '#ffffff', 0.22) : mix(tone, ink, 0.28 * (1 - lit));
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
