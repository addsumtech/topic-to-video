// THE CAMERA HAND-OFF — a move that runs into its cut, and the beat after it that inherits the velocity.
// Pure curves on a beat's own frame clock; Film.tsx's HandoffCamera drives SceneCamera with them.
//
// A push that comes to rest before every cut is a camera that stops for each edit; across a CONTINUATION — the same
// thought, one more beat of it — that stop is the seam showing. So a move may hand off (`camera.handoff`): it runs
// INTO its cut instead of resting, and the next beat, which declares no camera of its own, starts at that velocity
// and lets it decay. The push survives the cut.
//
// WHY A MOVING CAMERA IS ALLOWED ACROSS A SEAM HERE. Every other camera in this film rests at both ends because
// `useT` holds a beat still while a seam blends it, and a move still running under a blend read as a bump — two
// images doing different things. Here both halves move at the SAME rate through all of the seam's frames (A keeps
// its end velocity to its last frame, B holds that velocity for the frames it shares with A), so the blend is of
// two images doing one thing, and the decay starts only once B is alone.
//
// THE SHAPES. A: at rest until the frame its move would have started (CAMERA_START on useT's clock), then a
// quadratic ease-in that reaches the seam at velocity v and holds v to its last frame, landing exactly on its amp —
// so the beat spends the same budget it always did. B: velocity held through the shared frames, then an exponential
// decay (a spring whose target is wherever the momentum carries it, so it never reverses), settled to 2% of its
// speed by HANDOFF_SETTLE of the beat. Pulls are the same curves read the other way. One camera channel per beat:
// a hand-off beat has no pan, and the inheriting beat no camera of its own — Film refuses both (and validate.py).
// LIMIT: the edge budget (runtime/depth) can still clamp either beat on the frame for type near an edge; on such a
// frame the speed on screen is lower than the speed handed over. It is measured per frame from the DOM and a plan
// made before the render cannot see it.
import {SEAM_FRAMES, ENTRY_T} from './motion';
import {CAMERA_START} from './depth';

const TR = SEAM_FRAMES;

export const HANDOFF_SETTLE = 0.35;
const HANDOFF_FLOOR = 50;          // the velocity decays to 1/50 by the settle point

/** A move that runs into its cut: the extra scale on beat frame `f`, and the velocity it reaches (extra per frame). */
export const handoffOut = (f: number, durF: number, amp: number, move: 'push' | 'pull'): {extra: number; v: number} => {
  const pad = Math.min(TR, Math.floor(Math.max(0, durF - 1) / 3));
  const span = Math.max(1, durF - 1 - 2 * pad);
  const fs = pad + ((CAMERA_START - ENTRY_T) / (1 - ENTRY_T)) * span;
  const fc = Math.max(fs + 1, durF - TR), fe = Math.max(fc, durF - 1);
  const ramp = fc - fs;
  const v = amp / (ramp / 2 + (fe - fc));
  const e = f <= fs ? 0 : f <= fc ? (v * (f - fs) ** 2) / (2 * ramp) : (v * ramp) / 2 + v * (f - fc);
  const k = Math.max(0, Math.min(amp, e));
  return {extra: move === 'push' ? k : amp - k, v};
};

/** The beat that inherits a hand-off: the extra on frame `f` for a velocity `rate` (extra per frame, negative for a
 *  pull), never past `limit` — held through the frames it shares with the beat before, then decaying. */
export const handoffIn = (f: number, durF: number, rate: number, limit: number): number => {
  const r0 = Math.abs(rate);
  if (!(r0 > 0) || !(limit > 0)) return 0;
  const hold = TR - 1;
  let w = Math.log(HANDOFF_FLOOR) / Math.max(1, HANDOFF_SETTLE * durF - hold);
  let r = r0;
  // the momentum would carry it past the room it has: decay faster rather than slow the hand-off down, which keeps
  // the velocity at the cut the velocity on screen; only when even the shared frames would overrun is it slowed
  if (r * hold + r / w > limit) {
    if (limit > r * hold * 1.25) w = r / (limit - r * hold);
    else r = limit / (hold + 1 / w);
  }
  const travel = f <= hold ? r * f : r * hold + (r / w) * (1 - Math.exp(-w * (f - hold)));
  const total = r * hold + r / w;
  return rate > 0 ? travel : total - travel;
};
