// THE CUT CARRY — a hard cut on a kinetic film carries the motion THROUGH it instead of joining two still frames.
//
// Every beat is held still for SEAM_FRAMES at both ends (motion.ts useT) so a dissolve never runs over a moving shot,
// and a hard cut — which superimposes nothing — inherited the hold: the picture changes on the overlap's middle frame
// (seams.tsx CUT_AT), so about six still frames sat on each side of every cut of a promo. The launch-film peers say the
// opposite: "nothing is allowed to sit still at a cut" (skillry's velocity-matched sting, reviewed 2026-11-03).
//
// The carry is a camera move on the beat's picture, not on its content: the leaving beat drifts and leans in,
// ACCELERATING into the cut (x = -D·u², s = 1 + S·u²), and the arriving beat comes out of the same drift, DECELERATING
// (x = +D·(1-v)², s = 1 + S·(1-v)²) — both sides move the same way at the same speed (2D/K a frame) on the cut frame,
// so the eye reads one move through it. The lean always covers the drift (S·W/2 ≥ D), so no edge of the picture shows,
// and it never exceeds 1 + S, so a raster drawn at its own pixels is magnified at most 6% for a few frames.
// Outside its two windows a beat is exactly where it was. Pure; Film.tsx applies it (CutCarry) with the baseline unlock.

/** frames each side of a cut the carry spans, at most */
export const CARRY_F = 8;
/** the drift, as a share of the frame's width, and the lean that covers it */
export const CARRY_DRIFT = 0.025;
export const CARRY_LEAN = 0.06;

/** the overlap frame a hard cut changes the picture on — seams.tsx CUT_AT (0.5) of the seam */
export const cutFrame = (tr: number): number => Math.round(tr * 0.5);

export type Carry = {x: number; s: number};

/** The carry at a beat's own frame `f` (0-based, its Sequence's clock), for a beat of `durF` frames whose seams overlap
 *  by `tr` frames, cut in (`inCut`) and/or cut out (`outCut`), on a frame `W` wide. */
export const cutCarryAt = (f: number, durF: number, tr: number, inCut: boolean, outCut: boolean, W: number): Carry => {
  const c = cutFrame(tr);
  const first = inCut ? c : 0;                         // the first frame the viewer sees of this beat
  const end = outCut ? durF - tr + c : durF;           // the first frame they no longer do
  const K = Math.max(0, Math.min(CARRY_F, Math.floor((end - first) / 2) - 1));
  const D = CARRY_DRIFT * W;
  let e = 0, x = 0;
  if (K > 0 && outCut && f >= end - K && f < end) {
    const u = (f - (end - K) + 1) / K;                  // 1/K .. 1 on the last visible frame
    e = u * u;
    x = -D * e;
  } else if (K > 0 && inCut && f >= first && f < first + K) {
    const v = (f - first) / K;                          // 0 on the first visible frame
    e = (1 - v) * (1 - v);
    x = D * e;
  }
  return e === 0 ? {x: 0, s: 1} : {x, s: 1 + CARRY_LEAN * e};
};
