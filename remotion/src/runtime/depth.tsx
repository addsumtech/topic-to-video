// DEPTH + CAMERA — space that MEANS something, without the rasterization penalty.
//
// WHY THIS IS 2D. The obvious way to build depth is `perspective()` + `translateZ()`. Measured on this
// library's own renderer, on a text-dense shot: a plain 2D `scale` left glyph edge strength at 86 against a
// 91 baseline — and the small drop is entirely explained by the glyphs being LARGER, not softer; magnified
// crops are indistinguishable. The same shot under `perspective(1200px) translateZ(50px)` dropped to 56, a
// 38% loss that is plainly fuzzy to the eye. A 3D-composited layer gets promoted, rasterized once at layout
// size and GPU-upscaled, so every word on it softens; a 2D transform is repainted at final resolution each
// frame. (This is the defect video-shotcraft documents as Q2 and answers with layout-level CSS `zoom`; the
// answer here is not to put text on a Z plane in the first place.)
//
// So depth is built from the cues that survive: SIZE, FOCUS, SHADOW and PARALLAX. For parallel planes —
// which is what an explanatory diagram has — those carry the whole reading, and the type stays sharp. A
// shot that genuinely needs converging perspective (a receding wall) can still reach for a 3D transform,
// but it must not carry text it expects anyone to read.
//
// WHY IT MUST MEAN SOMETHING. Depth here is not atmosphere. The near plane is what the narration is
// talking about NOW; the far plane is the context it sits in. Hide the caption and the arrangement should
// still say which is which. A shot that scatters things across planes for the look of it is decoration and
// belongs in neither this file nor the film.

import React from 'react';
import {useVideoConfig} from 'remotion';
import {useT, ReducedMotionContext, clamp01, easeInOutCubic} from './motion';
import {CONTENT_TOP, contentBottom, maxCameraPush} from './layout';

// ── depth planes ────────────────────────────────────────────────────────────────────────────────────────
// Named, because a bare number says nothing about what the author meant. `subject` is the plane the beat is
// about and is always the one in focus; everything else is measured from it.
export const DEPTH = {
  lifted: -1,     // above the ground — casts a shadow: a thing placed ON the page, not printed into it
  subject: 0,     // what the narration is talking about now. Sharp, full size, full parallax.
  behind: 1,      // one step back — still legible, slightly soft
  context: 2,     // the setting the subject sits in
  far: 3,         // background material; never carries anything that must be read
};

const DOF_PER_UNIT = 0.0016;      // blur per depth unit, as a fraction of min(W,H) — ~1.7px at 1080
const SIZE_PER_UNIT = 0.014;      // further planes are slightly smaller
const PARALLAX_PER_UNIT = 0.30;   // how much of the camera's move a plane is EXEMPT from, per depth unit

export type CameraState = {push: number; amount: number};
export const CameraContext = React.createContext<CameraState>({push: 0, amount: 0});
export const useCamera = () => React.useContext(CameraContext);

/** A depth plane. Everything inside reads as sitting at `depth` relative to the subject plane. */
export const Plane: React.FC<{
  depth?: number;
  children?: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
}> = ({depth = 0, children, style, className}) => {
  const {width: W, height: H} = useVideoConfig();
  const {push, amount} = useCamera();
  const base = Math.min(W, H);

  // FOCUS. Only planes BEHIND the subject soften; a lifted plane is nearer, and nearer is not blurrier in
  // any lens a viewer has ever looked through — it would read as a mistake.
  const blur = Math.max(0, depth) * DOF_PER_UNIT * base;
  // SIZE — for planes BEHIND only. A lifted plane scaled about the frame centre DISPLACES everything on
  // it: measured, a mark pinned to a point in a photograph moved 29px, about its own width, and stopped
  // pointing at the thing it named. That is fatal for the one job an annotation layer has. It is also
  // wrong physically — a label resting on a print is a few millimetres above it, not appreciably nearer,
  // and the SHADOW is the whole cue. So a lifted plane keeps its registration and casts a shadow; only
  // depth BEHIND the subject changes size, where nothing is registered to anything.
  const size = depth > 0 ? 1 - depth * SIZE_PER_UNIT : 1;
  // PARALLAX. The Film scales the whole scene by (1 + amount*push). A plane further back should move LESS,
  // so it counter-scales by its share of that move. depth 0 moves with the camera exactly; depth 3 keeps
  // most of its position. This is what makes the planes read as separated rather than as one flat picture
  // that happens to have a blurred region.
  const counter = depth > 0 ? 1 - amount * push * PARALLAX_PER_UNIT * depth : 1;
  // SHADOW. Only a LIFTED plane casts one, and its softness follows how far it is lifted. A shadow under
  // something that is not lifted is the single commonest tell of decoration-grade depth.
  //
  // It is a `drop-shadow` FILTER, not a `box-shadow`. The first version painted a box-shadow onto a child
  // spanning the whole plane — and a plane IS the whole frame, so a non-inset box-shadow drew entirely
  // outside the frame and painted ZERO pixels. Combined with a lifted plane correctly not resizing, the
  // component became a total no-op: a with-Plane and a without-Plane render of PhotoPlate differed on
  // 0.000% of pixels. (That measurement was taken and read as proof the fix worked. It was proof the
  // component did nothing.) `drop-shadow` follows the ALPHA of the content, so each chip, ring and leader
  // gets its own shadow — which is what "these marks are lying on the print" actually looks like.
  const lift = Math.max(0, -depth);
  const shadow = lift > 0
    ? `drop-shadow(0 ${(lift * base * 0.006).toFixed(1)}px ${(lift * base * 0.008).toFixed(1)}px rgba(0,0,0,${(0.30 * lift).toFixed(3)}))`
    : undefined;

  return (
    <div
      className={className}
      style={{
        position: 'absolute', inset: 0,
        transform: `scale(${(size * counter).toFixed(5)})`,
        // A lifted plane is never blurred and a receding one never casts a shadow (they are opposite signs
        // of `depth`), so these two never need to compose — but they share one `filter`, so write it once.
        filter: blur > 0.2 ? `blur(${blur.toFixed(2)}px)` : shadow,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

// ── the camera ──────────────────────────────────────────────────────────────────────────────────────────
// A MOTIVATED move, not ambient drift. The film-wide sinusoidal breathe this replaces had no relationship
// to anything being said, which is exactly why it reads as a wobble the moment a viewer notices it: motion
// with no cause is noise. A push says LOOK CLOSER at what is on screen; a pull says HERE IS THE WHOLE OF
// IT. Both start and end at rest, and both ride useT(), which is already held still for the frames a
// dissolve is running — so a cut never happens over a moving camera.

export type CameraMove = 'push' | 'pull' | 'hold';

// WHEN the move runs, not just how far. Starting at t=0 was measured to waste it: a shot reveals its own
// content over roughly t 0.05-0.45, and a 0 -> 0.78 push is ~70% finished by the time there is anything to
// look closer AT — only 30% of the move is visible on settled content, which is the part a viewer reads as
// a camera. Waiting until the reveal is underway puts 91% of it there instead. It still ARRIVES before the
// end and holds, because a move that is still running when the next shot blends over it reads as a bump.
export const CAMERA_START = 0.28;
export const CAMERA_SPAN = 0.60;    // arrives at 0.88, then rests

/** The scale a scene's camera is at, 0..1 of its move. Pure function of normalized time. */
export const cameraAt = (move: CameraMove, t: number): number => {
  if (move === 'hold') return 0;
  const p = easeInOutCubic(clamp01((t - CAMERA_START) / CAMERA_SPAN));
  return move === 'push' ? p : 1 - p;
};

/**
 * Wraps ONE scene's shot: applies the camera's 2D scale and publishes the push so `Plane`s can parallax.
 *
 * The transform origin is the centre of the CONTENT ZONE, not of the frame. Scaling about the frame centre
 * pushes the shot's lowest content downward into the band reserved for the burned caption — the camera
 * would have quietly re-created the overlap the band exists to prevent. `maxCameraPush()` derives the
 * largest move that cannot do this from the layout itself, and the amount is clamped to it.
 */
export const SceneCamera: React.FC<{
  move?: CameraMove;
  amount?: number;
  // the largest EXTRA scale the film-wide ambient drift is adding on top of this move. The two layers
  // multiply, so the per-beat budget has to be whatever the drift has not already spent.
  driftExtra?: number;
  children?: React.ReactNode;
}> = ({move = 'hold', amount, driftExtra = 0, children}) => {
  const {width: W, height: H} = useVideoConfig();
  const reduced = React.useContext(ReducedMotionContext);
  const t = useT();
  const cap = maxCameraPush(W, H, driftExtra);
  const amp = reduced ? 0 : Math.max(0, Math.min(amount ?? 0.045, cap));
  const push = amp > 0 ? cameraAt(move, t) : 0;
  const scale = 1 + amp * push;
  const originY = (CONTENT_TOP + contentBottom(W, H)) / 2;

  return (
    <CameraContext.Provider value={{push, amount: amp}}>
      <div style={{
        position: 'absolute', inset: 0,
        transform: scale === 1 ? undefined : `scale(${scale.toFixed(5)})`,
        transformOrigin: `50% ${originY.toFixed(1)}px`,
      }}>
        {children}
      </div>
    </CameraContext.Provider>
  );
};
