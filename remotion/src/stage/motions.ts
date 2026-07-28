// Camera motion patterns that generate lens keyframe sequences.
// A MOTION defines how the camera moves from the initial shot frame over the duration.

import type {LensKeyframe} from '../Camera';

export type MotionPattern =
  | 'STATIC' // no move, clean hold
  | 'PUSH_IN' // dolly forward, intensifies
  | 'PULL_OUT' // dolly backward, reveals context
  | 'PAN_RIGHT' // horizontal yaw right
  | 'PAN_LEFT' // horizontal yaw left
  | 'TILT_UP' // vertical pitch up (bird's-eye)
  | 'TILT_DOWN' // vertical pitch down (intimacy)
  | 'ORBIT_RIGHT' // arc around subject
  | 'ORBIT_LEFT' // arc around subject (counter)
  | 'RACK_FOCUS'; // static camera, pull focus bg→fg or fg→bg

// Generate lens keyframes for a motion pattern given the starting frame and duration.
// The starting frame comes from shots.ts calculateShotFrame().
// Returns an array of LensKeyframes (including the start frame at atFrame:0).
export function generateMotion(
  pattern: MotionPattern,
  startFrame: LensKeyframe,
  durationFrames: number,
  easing: string = 'out',
): LensKeyframe[] {
  const start = {...startFrame, atFrame: 0, easing: undefined}; // force frame 0, no easing
  const end = {...startFrame, atFrame: durationFrames, easing}; // end state with easing

  switch (pattern) {
    case 'STATIC': {
      // No motion: single keyframe
      return [start];
    }

    case 'PUSH_IN': {
      // Dolly forward: increase dolly (push world toward camera)
      const delta = 150; // move 150px forward
      end.dolly = (start.dolly || 0) + delta;
      end.zoom = (start.zoom || 1.0) * 1.08; // subtle zoom boost
      return [start, end];
    }

    case 'PULL_OUT': {
      // Dolly backward: decrease dolly
      const delta = -180;
      end.dolly = (start.dolly || 0) + delta;
      end.zoom = (start.zoom || 1.0) * 0.92; // subtle zoom reduction
      return [start, end];
    }

    case 'PAN_RIGHT': {
      // Horizontal yaw right
      end.yaw = (start.yaw || 0) + 12;
      return [start, end];
    }

    case 'PAN_LEFT': {
      // Horizontal yaw left
      end.yaw = (start.yaw || 0) - 12;
      return [start, end];
    }

    case 'TILT_UP': {
      // Vertical pitch up (look down / bird's-eye)
      end.pitch = (start.pitch || 0) + 8;
      return [start, end];
    }

    case 'TILT_DOWN': {
      // Vertical pitch down (look up / worm's-eye)
      end.pitch = (start.pitch || 0) - 8;
      return [start, end];
    }

    case 'ORBIT_RIGHT': {
      // Arc around subject: yaw + dolly adjustment to maintain distance
      end.yaw = (start.yaw || 0) + 15;
      end.dolly = (start.dolly || 0) + 50; // slight push to compensate arc
      return [start, end];
    }

    case 'ORBIT_LEFT': {
      // Arc around subject (counter)
      end.yaw = (start.yaw || 0) - 15;
      end.dolly = (start.dolly || 0) + 50;
      return [start, end];
    }

    case 'RACK_FOCUS': {
      // Static camera, pull focus from background to foreground
      // Assumes start.focusZ is on background; pull to -200 (near foreground)
      const startZ = start.focusZ || -500;
      const endZ = -200;
      const mid = {...start, atFrame: Math.floor(durationFrames / 2), focusZ: startZ};
      end.focusZ = endZ;
      return [start, mid, end];
    }

    default: {
      // Unknown pattern: fallback to STATIC
      console.warn(`[motions] unknown pattern "${pattern}", fallback to STATIC`);
      return [start];
    }
  }
}

// Parse motion pattern name from storyboard (case-insensitive, default STATIC)
export function parseMotionPattern(name?: string): MotionPattern {
  if (!name) return 'STATIC';
  const normalized = name.toUpperCase().replace(/[-_\s]/g, '_') as MotionPattern;
  const valid: MotionPattern[] = [
    'STATIC',
    'PUSH_IN',
    'PULL_OUT',
    'PAN_RIGHT',
    'PAN_LEFT',
    'TILT_UP',
    'TILT_DOWN',
    'ORBIT_RIGHT',
    'ORBIT_LEFT',
    'RACK_FOCUS',
  ];
  return valid.includes(normalized) ? normalized : 'STATIC';
}
