// Shot LIST -> a continuous camera-pose timeline over ONE staged set.
//
// This is the heart of the shot paradigm: a scene is a set of elements placed ONCE, and the camera
// moves between framings (shots) of that set. Each shot resolves to a [startPose -> endPose] window;
// a shot with `carry` STARTS at the previous shot's END pose, so the camera flows through the space
// with no reset (motivated continuity across cuts). Non-carry shots jump to their own framing (a cut).
//
// Reuses the proven framing math (shots.calculateShotFrame) and motion deltas (motions.generateMotion),
// so this file only stitches per-shot windows into one timeline. Deterministic: pure function of frame.

import {Easing} from 'remotion';
import type {LensKeyframe} from '../Camera';
import type {ShotSpec, Position} from './shots';
import {calculateShotFrame, resolveTarget} from './shots';
import {generateMotion, parseMotionPattern} from './motions';

export type Pose = {dolly: number; pitch: number; yaw: number; roll: number; zoom: number; focusZ: number | null};
export type ResolvedShot = {start: number; end: number; startPose: Pose; endPose: Pose; easing: string};

const EASE: Record<string, (n: number) => number> = {
  linear: Easing.linear,
  in: Easing.in(Easing.cubic),
  out: Easing.out(Easing.cubic),
  inout: Easing.inOut(Easing.cubic),
};

function toPose(k: LensKeyframe): Pose {
  return {
    dolly: k.dolly || 0,
    pitch: k.pitch || 0,
    yaw: k.yaw || 0,
    roll: k.roll || 0,
    zoom: k.zoom == null ? 1 : k.zoom,
    focusZ: k.focusZ == null ? null : k.focusZ,
  };
}

// Resolve the ordered shots into absolute-frame windows with start/end poses.
// `registry` maps element id -> world position (for element-targeted framing).
export function computeTimeline(
  shots: ShotSpec[],
  registry: Map<string, Position>,
  aspect: number,
): ResolvedShot[] {
  const out: ResolvedShot[] = [];
  let prevEnd: Pose | null = null;
  for (const sh of shots) {
    const start = sh.startFrame ?? 0;
    const dur = Math.max(1, sh.durationFrames ?? 1);

    // Manual keyframe override: use first/last as the window's poses (advanced escape hatch).
    if (sh.lens && sh.lens.length) {
      const startPose = toPose(sh.lens[0]);
      const endPose = toPose(sh.lens[sh.lens.length - 1]);
      out.push({start, end: start + dur, startPose, endPose, easing: sh.easing || 'inout'});
      prevEnd = endPose;
      continue;
    }

    // Framing: where does this shot type place the camera to see its target? This ALWAYS anchors the
    // shot's END, so a shot that targets a new element actually moves to frame it.
    const targetPos: Position = sh.targetPos ?? (sh.target ? resolveTarget({kind: 'element', id: sh.target}, registry) : [0, 0, -500]);
    const framing = calculateShotFrame(sh.type, targetPos, aspect);

    // The shot settles at its framing (+ its motion pattern applied on top), scaled by the shot's ENERGY
    // so a bold beat pushes harder and a subtle one drifts — varied motion, not one uniform push.
    const amp = sh.energy === 'bold' ? 1.6 : sh.energy === 'subtle' ? 0.55 : 1;
    const settled = generateMotion(parseMotionPattern(sh.motion), framing, dur, sh.easing || 'out', amp);
    const endPose = toPose(settled[settled.length - 1]);

    // carry => GLIDE from the previous shot's end pose to this framing (continuous move to the new
    // subject); non-carry => CUT: sit at the framing and apply the motion (start == the framing pose).
    const startPose: Pose = sh.carry && prevEnd ? prevEnd : toPose(settled[0]);

    out.push({start, end: start + dur, startPose, endPose, easing: sh.easing || 'out'});
    prevEnd = endPose;
  }
  return out;
}

// Interpolate the camera pose at a given absolute frame (eased within the active shot window).
export function poseAtFrame(timeline: ResolvedShot[], frame: number): Pose {
  if (!timeline.length) return {dolly: 0, pitch: 0, yaw: 0, roll: 0, zoom: 1, focusZ: null};
  let rs = timeline[0];
  for (const t of timeline) if (frame >= t.start) rs = t; // last window whose start we've reached
  const span = Math.max(1, rs.end - rs.start);
  const raw = Math.min(1, Math.max(0, (frame - rs.start) / span));
  const e = (EASE[rs.easing] || EASE.inout)(raw);
  const L = (a: number, b: number) => a + (b - a) * e;
  const fz =
    rs.startPose.focusZ == null && rs.endPose.focusZ == null
      ? null
      : L(rs.startPose.focusZ ?? rs.endPose.focusZ ?? 0, rs.endPose.focusZ ?? rs.startPose.focusZ ?? 0);
  return {
    dolly: L(rs.startPose.dolly, rs.endPose.dolly),
    pitch: L(rs.startPose.pitch, rs.endPose.pitch),
    yaw: L(rs.startPose.yaw, rs.endPose.yaw),
    roll: L(rs.startPose.roll, rs.endPose.roll),
    zoom: L(rs.startPose.zoom, rs.endPose.zoom),
    focusZ: fz,
  };
}
