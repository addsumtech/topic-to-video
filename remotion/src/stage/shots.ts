// Shot framing types and camera position calculators for scene-space staging.
// A shot TYPE defines the initial camera position/angle that frames the subject.
// Combined with a MOTION pattern (motions.ts), it generates the full lens keyframe sequence.

import type {LensKeyframe} from '../Camera';

// Shot framing vocabulary (cinematography-derived)
export type ShotType =
  | 'ESTABLISH' // wide, shows full context
  | 'MEDIUM' // balanced, default conversational framing
  | 'CLOSEUP' // tight on subject
  | 'OVER_SHOULDER' // partial foreground + background subject
  | 'REVEAL' // starts obscured, camera reveals
  | 'HERO'; // isolated subject, dramatic

// Element position in scene-space (x, y, z in stage units)
export type Position = [number, number, number];

// Camera targeting: frame an element or use manual lens keyframes
export type CameraTarget =
  | {kind: 'element'; id: string} // auto-frame this element
  | {kind: 'position'; pos: Position} // aim at this point
  | {kind: 'manual'; lens: LensKeyframe[]}; // explicit keyframes (legacy)

// Shot specification. One entry in a scene's ordered `shots` list; the camera moves between framings
// of ONE staged set. startFrame/durationFrames are assigned by render_remotion._clean_shots so the
// windows tile the scene exactly (A/V-safe); the authoring fields are type/target/motion/carry/easing.
export type ShotSpec = {
  type: ShotType;
  target?: string; // element ID to frame (shorthand for {kind: 'element', id})
  targetPos?: Position; // position to frame (shorthand for {kind: 'position', pos})
  lens?: LensKeyframe[]; // manual keyframe override (advanced escape hatch)
  motion?: string; // motion pattern name (motions.ts), default 'STATIC'
  easing?: string; // 'linear' | 'in' | 'out' | 'inout'
  energy?: 'subtle' | 'balanced' | 'bold'; // motion amplitude (drift ... hard push); default balanced
  carry?: boolean; // start at the previous shot's END pose (continuous move, not a cut)
  startFrame?: number; // absolute window start (assigned by build_props)
  durationFrames?: number; // window length in frames (assigned by build_props)
};

// Calculate initial camera position to frame a target at the given shot type.
// Returns a starting LensKeyframe (dolly, pitch, yaw, zoom).
//
// DEPTH: the WORLD node gets translateZ(dolly) and the TARGET element also carries its own translate3d(tz),
// so the target's final camera-space depth = dolly + tz. To hold the subject at a CONSTANT distance DIST
// regardless of where it sits in the set, dolly = -DIST - tz (final depth = -DIST for every shot). The
// earlier `dolly = tz - DIST` double-counted tz (final depth 2·tz - DIST), so deeper targets rendered
// SMALLER and the establish→hero size ladder inverted on any multi-depth stage. DIST + zoom now order the
// ladder; tz cancels out. Distances are the same magnitudes as before, only the tz sign is corrected.
export function calculateShotFrame(
  shotType: ShotType,
  target: Position,
  aspectRatio: number = 16 / 9,
): LensKeyframe {
  const [tx, ty, tz] = target;

  // FRAMING LADDER — compressed into ONE legible band so content can never go tiny→huge (the widest:tightest
  // content-size ratio across a scene stays ~≤1.25×), and READ shots are FRONTAL (0° pitch/yaw/roll) so type
  // never keystones. This is the generalizable cure for the 'opens tiny then pushes in so close it overflows /
  // distorts' failure: MEDIUM is home base, ESTABLISH is only ~one step wider (not a 0.85→1.5 swing), and the
  // old oblique REVEAL (pitch 10 / yaw −15 / zoom 1.8 — the main distortion culprit) is recast as a FRONTAL
  // soft arrival the motion reveals. Distortion is a lens+distance thing: keep the rig perspective long
  // (≥~2000, set in SceneStage/Camera) and the push a small clamped zoom, not a deep dolly. (Sources: shot-size
  // + safe-area + motivated-movement cinematography research — see references/camera-and-bridges.md.)
  let base: LensKeyframe;
  switch (shotType) {
    case 'ESTABLISH': {
      // Section/title opener — one step WIDER than medium, still readable (never tiny). Frontal.
      const dolly = -750 - tz;
      base = {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 0.95, focusZ: tz};
      break;
    }
    case 'MEDIUM': {
      // HOME BASE — the default resting framing (read-card ~60–70% of frame). Balanced, frontal, neutral.
      const dolly = -500 - tz;
      base = {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.0, focusZ: tz};
      break;
    }
    case 'CLOSEUP': {
      // Tight — but only a small step in from MEDIUM (~1.10, was 1.5). Frontal; endpoint stays action-safe.
      const dolly = -350 - tz;
      base = {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.1, focusZ: tz};
      break;
    }
    case 'OVER_SHOULDER': {
      // Foreground element partially in frame, subject behind — kept frontal for read legibility (was yaw 8).
      const dolly = -420 - tz;
      base = {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.04, focusZ: tz};
      break;
    }
    case 'REVEAL': {
      // FRONTAL soft arrival the motion reveals (rack-focus / pull-out) — NOT an oblique high-zoom pose.
      // Opens a touch wide + soft (focusZ pushed off the plane); the shot's motion racks/pulls to sharp.
      const dolly = -620 - tz;
      base = {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 0.98, focusZ: tz + 500};
      break;
    }
    case 'HERO': {
      // Isolation/emphasis — a modest step in (~1.06, was 1.3), frontal, strong DoF via focusZ.
      const dolly = -380 - tz;
      base = {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.06, focusZ: tz};
      break;
    }
    default: {
      // Fallback to MEDIUM
      const dolly = -500 - tz;
      base = {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.0, focusZ: tz};
    }
  }

  // ASPECT-AWARE FRAMING: the stage elements are sized in world px tuned for a 1920-wide (16:9) frame, so a
  // narrower (portrait) frame shows less world-width at the same zoom and crops wide elements (panel 1040,
  // display 1680). Scale zoom by the width ratio so the same horizontal extent stays framed. This is
  // MONOTONIC and regression-safe: for landscape (aspect >= 16/9) the factor is exactly 1 (poses unchanged);
  // for portrait it only zooms OUT (can never worsen overflow). Floored at 0.5 so it never shrinks to nothing.
  const aspectZoom = Math.max(0.5, Math.min(1, aspectRatio / (16 / 9)));
  return {...base, zoom: base.zoom * aspectZoom};
}

// Resolve a CameraTarget to a Position in scene-space.
// For element targeting, looks up the element's position from the stage.
export function resolveTarget(
  target: CameraTarget,
  elementRegistry: Map<string, Position>,
): Position {
  if (target.kind === 'element') {
    const pos = elementRegistry.get(target.id);
    if (!pos) {
      console.warn(`[shots] element "${target.id}" not found, defaulting to origin`);
      return [0, 0, -500];
    }
    return pos;
  }
  if (target.kind === 'position') {
    return target.pos;
  }
  // 'manual' lens has no single target position
  return [0, 0, -500];
}
