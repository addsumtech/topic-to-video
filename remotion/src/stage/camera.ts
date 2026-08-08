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
export type ResolvedShot = {
  start: number;
  end: number;
  startPose: Pose;
  endPose: Pose;
  keys: {at: number; pose: Pose}[]; // ALL waypoints (a rack-focus is [open, HOLD@mid, land]); poseAtFrame
  // interpolates through them so a hold-then-rack doesn't flatten to one linear pull. startPose/endPose are
  // kept for reducedPoseAtFrame + back-compat (they equal keys[0]/keys[last]).
  easing: string;
  flowThrough?: boolean; // interior waypoint of a carry-chain: its 'linear' easing is a CONSTANT-VELOCITY
  // continuity contract (not a per-shot choice), so the atmosphere camera-grammar must NOT override it.
};

const EASE: Record<string, (n: number) => number> = {
  linear: Easing.linear,
  in: Easing.in(Easing.cubic),
  out: Easing.out(Easing.cubic),
  inout: Easing.inOut(Easing.cubic),
  // HOUSE_EASE — the shared premium "quick-out, long-settle" curve (expo-out). The default camera settle so
  // every move lands with the same restrained confidence (one motion physics, not per-shot ad-hoc eases).
  house: Easing.bezier(0.16, 1, 0.3, 1),
};

// Per-ATMOSPHERE camera GRAMMAR for the shot tier — the WORLD's camera character between shot framings,
// mirroring ThreeScene.camGrammarEase so both cinematic tiers move the same per world. When set, it OVERRIDES
// the per-shot easing (one camera character for the whole film). whip=fast-then-stop, punch=snap-first-third-
// then-lock, turntable=linear/constant, dolly/undefined=fall through to the shot's own ease. Deterministic.
function camGrammar(grammar: string | undefined, x: number): number | null {
  const t = Math.max(0, Math.min(1, x));
  switch (grammar) {
    case 'whip': return 1 - Math.pow(1 - t, 4);
    case 'punch': return Math.min(1, t / 0.32);
    case 'turntable': return t;
    default: return null;   // dolly / unknown -> use the shot's own easing (no override)
  }
}

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
  ampScale: number = 1, // motion_personality: scales every move's amplitude (calm 0.72 … energetic 1.4)
): ResolvedShot[] {
  const out: ResolvedShot[] = [];
  let prevEnd: Pose | null = null;
  for (let i = 0; i < shots.length; i++) {
    const sh = shots[i];
    const start = sh.startFrame ?? 0;
    const dur = Math.max(1, sh.durationFrames ?? 1);
    // A carry shot whose NEXT shot ALSO carries is an INTERIOR waypoint of a continuous move — it must NOT
    // decelerate to a stop at its end (an 'inout'/'out' ease zeroes velocity at the boundary, so a run of
    // carries reads as hesitant eased HOPS). Glide through it at constant velocity ('linear'); the LAST
    // carry of the run keeps its settling ease so the move still lands softly.
    const nextCarries = i + 1 < shots.length && !!shots[i + 1].carry;
    const flowThrough = !!sh.carry && nextCarries;

    // Manual keyframe override: use first/last as the window's poses (advanced escape hatch).
    if (sh.lens && sh.lens.length) {
      const startPose = toPose(sh.lens[0]);
      const endPose = toPose(sh.lens[sh.lens.length - 1]);
      const keys = [{at: start, pose: startPose}, {at: start + dur, pose: endPose}];
      out.push({start, end: start + dur, startPose, endPose, keys, flowThrough, easing: flowThrough ? 'linear' : sh.easing || 'inout'});
      prevEnd = endPose;
      continue;
    }

    // Framing: where does this shot type place the camera to see its target? This ALWAYS anchors the
    // shot's END, so a shot that targets a new element actually moves to frame it.
    const targetPos: Position = sh.targetPos ?? (sh.target ? resolveTarget({kind: 'element', id: sh.target}, registry) : [0, 0, -500]);
    const framing = calculateShotFrame(sh.type, targetPos, aspect);

    // The shot settles at its framing (+ its motion pattern applied on top), scaled by the shot's ENERGY
    // so a bold beat pushes harder and a subtle one drifts — varied motion, not one uniform push.
    const amp = (sh.energy === 'bold' ? 1.6 : sh.energy === 'subtle' ? 0.55 : 1) * ampScale;
    const settled = generateMotion(parseMotionPattern(sh.motion), framing, dur, sh.easing || 'house', amp);
    const endPose = toPose(settled[settled.length - 1]);

    // carry => GLIDE from the previous shot's end pose to this framing (continuous move to the new
    // subject); non-carry => CUT: sit at the framing and apply the motion (start == the framing pose).
    const startPose: Pose = sh.carry && prevEnd ? prevEnd : toPose(settled[0]);

    // Honour EVERY interior keyframe (RACK_FOCUS returns [open, HOLD@mid, land]) — map each settled keyframe
    // to its absolute frame; only the FIRST pose is overridden by carry. A 2-keyframe motion yields exactly
    // one segment == the old start->end behaviour, so nothing else changes.
    const keys = settled.map((k, idx) => ({
      at: start + Math.min(dur, Math.max(0, k.atFrame ?? (idx === settled.length - 1 ? dur : 0))),
      pose: idx === 0 ? startPose : toPose(k),
    }));

    out.push({start, end: start + dur, startPose, endPose, keys, flowThrough, easing: flowThrough ? 'linear' : sh.easing || 'house'});
    prevEnd = endPose;
  }
  return out;
}

// Reduced-motion pose: HARD-CUT to the active shot's SETTLED (end) framing and hold — no camera travel
// (accessibility), but each beat still appears at ITS intended scale. Freezing on the first shot's wide
// establish (the old behaviour) showed every close-up/hero payload at its smallest, most distant framing.
export function reducedPoseAtFrame(timeline: ResolvedShot[], frame: number): Pose {
  if (!timeline.length) return {dolly: 0, pitch: 0, yaw: 0, roll: 0, zoom: 1, focusZ: null};
  let rs = timeline[0];
  for (const t of timeline) if (frame >= t.start) rs = t;
  return rs.endPose;
}

// Interpolate the camera pose at a given absolute frame (eased within the active shot window). `grammar`
// (the atmosphere camera character, optional) OVERRIDES the shot easing when set, so a world moves in
// character (whip/punch/turntable) on the shot tier just as it does on the cinematic3d tier.
export function poseAtFrame(timeline: ResolvedShot[], frame: number, grammar?: string): Pose {
  if (!timeline.length) return {dolly: 0, pitch: 0, yaw: 0, roll: 0, zoom: 1, focusZ: null};
  let rs = timeline[0];
  for (const t of timeline) if (frame >= t.start) rs = t; // last window whose start we've reached
  const keys = rs.keys && rs.keys.length >= 2 ? rs.keys
    : [{at: rs.start, pose: rs.startPose}, {at: rs.end, pose: rs.endPose}];
  // Find the sub-segment [keys[j], keys[j+1]] containing `frame` and interpolate WITHIN it — this honours
  // interior waypoints (a rack-focus HOLD-then-rack). A 2-keyframe shot has exactly one segment == the old
  // start->end behaviour, so nothing regresses for the common case. Easing is applied per segment.
  let j = 0;
  while (j < keys.length - 1 && frame >= keys[j + 1].at) j++;
  const jn = Math.min(j + 1, keys.length - 1);
  const a = keys[j].pose;
  const b = keys[jn].pose;
  const span = Math.max(1, keys[jn].at - keys[j].at);
  const raw = Math.min(1, Math.max(0, (frame - keys[j].at) / span));
  // The atmosphere camera character overrides the shot ease — EXCEPT on a flowThrough (interior carry-chain)
  // segment, whose 'linear' is a constant-velocity CONTINUITY contract: a whip/punch curve there zeroes
  // velocity at the boundary and turns a carry-glide into hesitant hops. The last carry of a run is NOT
  // flowThrough, so it still lands in the world's character.
  const g = rs.flowThrough ? null : camGrammar(grammar, raw);
  const e = g != null ? g : (EASE[rs.easing] || EASE.inout)(raw);
  const L = (x: number, y: number) => x + (y - x) * e;
  const fz =
    a.focusZ == null && b.focusZ == null
      ? null
      : L(a.focusZ ?? b.focusZ ?? 0, b.focusZ ?? a.focusZ ?? 0);
  return {
    dolly: L(a.dolly, b.dolly),
    pitch: L(a.pitch, b.pitch),
    yaw: L(a.yaw, b.yaw),
    roll: L(a.roll, b.roll),
    zoom: L(a.zoom, b.zoom),
    focusZ: fz,
  };
}
