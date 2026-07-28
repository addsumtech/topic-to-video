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

// Shot specification (storyboard.json schema)
export type ShotSpec = {
  type: ShotType;
  target?: string; // element ID to frame (shorthand for {kind: 'element', id})
  targetPos?: Position; // position to frame (shorthand for {kind: 'position', pos})
  lens?: LensKeyframe[]; // manual override (shorthand for {kind: 'manual', lens})
  duration: number; // frames
  motion?: string; // motion pattern name (motions.ts), default 'STATIC'
  easing?: string; // 'linear' | 'in' | 'out' | 'inout'
};

// Calculate initial camera position to frame a target at the given shot type.
// Returns a starting LensKeyframe (dolly, pitch, yaw, zoom).
export function calculateShotFrame(
  shotType: ShotType,
  target: Position,
  aspectRatio: number = 16 / 9,
): LensKeyframe {
  const [tx, ty, tz] = target;

  switch (shotType) {
    case 'ESTABLISH': {
      // Wide: camera far back, low zoom, see the full stage
      const dolly = tz - 1000; // push world 1000px away from target
      const pitch = -5; // slight bird's-eye
      return {atFrame: 0, dolly, pitch, yaw: 0, zoom: 0.85, focusZ: tz};
    }

    case 'MEDIUM': {
      // Balanced: mid-distance, neutral framing
      const dolly = tz - 500;
      return {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.0, focusZ: tz};
    }

    case 'CLOSEUP': {
      // Tight: close or high zoom
      const dolly = tz - 300;
      return {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.5, focusZ: tz};
    }

    case 'OVER_SHOULDER': {
      // Foreground element partially in frame, subject in background
      // Assume foreground is at z: -100, subject at target z
      const dolly = tz - 400;
      const yaw = 8; // slight angle to see past foreground
      return {atFrame: 0, dolly, pitch: 0, yaw, zoom: 1.1, focusZ: tz};
    }

    case 'REVEAL': {
      // Starts obscured (high zoom or off-angle), motion pattern will reveal
      const dolly = tz - 200;
      return {atFrame: 0, dolly, pitch: 10, yaw: -15, zoom: 1.8, focusZ: tz - 100};
    }

    case 'HERO': {
      // Dramatic isolation: close, strong DoF, centered
      const dolly = tz - 350;
      return {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.3, focusZ: tz};
    }

    default:
      // Fallback to MEDIUM
      const dolly = tz - 500;
      return {atFrame: 0, dolly, pitch: 0, yaw: 0, zoom: 1.0, focusZ: tz};
  }
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
