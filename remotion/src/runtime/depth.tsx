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
import {useT, ReducedMotionContext, clamp01, easeInOutCubic, hash01} from './motion';
import {CONTENT_TOP, contentBottom, maxCameraPush, captionSlackPx} from './layout';

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
// THE SATURATION ANCHOR. A receding plane loses a little colour as well as a little sharpness — atmospheric
// perspective, the oldest depth cue there is. Borrowed from a peer library's depth case law, which states
// the failure it prevents in one line: without the blur AND saturation anchors, layered planes read as
// stickers flying rather than as depth. This tier had the blur and not the saturation.
const DESAT_PER_UNIT = 0.045;     // measured against their 0.92 at their far layer
// FOREGROUND DEFOCUS. The comment this replaces said a lifted plane is never blurred, because "nearer is
// not blurrier in any lens a viewer has ever looked through". That is wrong, and it is the reason this
// tier's depth reads flat: in any shallow depth of field, a plane in FRONT of the focal plane is exactly
// as defocused as one behind it — a foreground element sweeping past the lens is the classic soft frame.
// Their own layer recipe blurs the 1.4x foreground by 3px while the reading layer stays perfectly sharp.
//
// It is deliberately gentler per unit than the background's, and it has a DEAD ZONE: the first unit of lift
// stays sharp. That is what keeps an annotation resting on a print — this tier's actual use of a lifted
// plane, where legibility is the whole job — untouched, while a plane lifted far enough to be read as
// "between the camera and the subject" softens.
const FG_DOF_PER_UNIT = 0.0011;
const FG_DOF_DEAD_ZONE = 1.0;     // lift below this is an annotation resting on the subject: never blurred
// The lateral travel a drifting plane takes per depth unit, as a fraction of min(W,H). Small: this is the
// ambient separation that makes layers read as layers, not a move. A foreground plane (negative depth) is
// given 1.6x of it, because a plane nearer the lens travels further across the frame for the same camera
// movement — that ratio IS the parallax.
const DRIFT_PER_UNIT = 0.018;

export type CameraState = {push: number; amount: number};
export const CameraContext = React.createContext<CameraState>({push: 0, amount: 0});
export const useCamera = () => React.useContext(CameraContext);

/** A depth plane. Everything inside reads as sitting at `depth` relative to the subject plane. */
export const Plane: React.FC<{
  depth?: number;
  /**
   * Opt in to an ambient lateral DRIFT in this plane's own depth ratio, so the planes separate on a beat
   * whose camera holds. 1 is the house amount; the subject plane (depth 0) never moves whatever this says.
   */
  drift?: number;
  children?: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
}> = ({depth = 0, drift = 0, children, style, className}) => {
  const {width: W, height: H} = useVideoConfig();
  const {push, amount} = useCamera();
  const base = Math.min(W, H);

  // FOCUS. Only planes BEHIND the subject soften; a lifted plane is nearer, and nearer is not blurrier in
  // any lens a viewer has ever looked through — it would read as a mistake.
  const blur = Math.max(0, depth) * DOF_PER_UNIT * base;
  const desat = Math.max(0, depth) * DESAT_PER_UNIT;
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
  // ...AND PARALLAX NEEDS A DRIVE, WHICH THE CAMERA MAY NOT BE PROVIDING. The counter-scale above is a
  // share of `amount * push`: on a beat whose camera holds, push is 0, and every plane counter-scales by
  // exactly 1. The separation the component exists to create simply does not happen — the planes differ in
  // blur and in nothing else, which is a blurred region, not depth.
  //
  // The peer library's layer recipe drives its planes from an independent lateral `drive`, not from a zoom,
  // with coefficients 0.35 / 0.7 / 1.4 — a background that lags, a reading layer that carries the shot, a
  // foreground that overtakes. `drift` is that drive: a slow lateral travel in the plane's own depth ratio,
  // opt-in per plane, and it is the only thing here that moves a plane on a held beat.
  //
  // It CANNOT vibrate: the travel is a single monotone ramp across the beat (no reversal within a shot), so
  // the frame's displacement path equals its net displacement — the signature scripts/shake_qa.py measures
  // as clean. And the subject plane (depth 0) is exempt by construction: `driftPx` is scaled by the depth
  // ratio, which is zero there, so the layer the viewer is reading never moves.
  const t = useT();                                   // unconditional: a hook inside a ternary is a hook violation
  const reducedMotion = React.useContext(ReducedMotionContext);
  const driftPx = (drift && !reducedMotion)
    ? drift * (depth >= 0 ? depth : depth * 1.6) * base * DRIFT_PER_UNIT * panAt(t)
    : 0;
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
  // the foreground's own defocus, past the dead zone that protects annotations
  const fgBlur = Math.max(0, lift - FG_DOF_DEAD_ZONE) * FG_DOF_PER_UNIT * base;
  const shadow = lift > 0
    ? `drop-shadow(0 ${(lift * base * 0.006).toFixed(1)}px ${(lift * base * 0.008).toFixed(1)}px rgba(0,0,0,${(0.30 * lift).toFixed(3)}))`
    : undefined;

  return (
    <div
      className={className}
      style={{
        position: 'absolute', inset: 0,
        transform: `${driftPx ? `translateX(${driftPx.toFixed(2)}px) ` : ''}scale(${(size * counter).toFixed(5)})`,
        // One `filter`, composed from whichever cues this depth actually has. A receding plane recedes in
        // sharpness AND in colour; a lifted one casts a shadow and, once it is far enough forward to be
        // between the camera and the subject, defocuses too.
        filter: [
          blur > 0.2 ? `blur(${blur.toFixed(2)}px)` : '',
          desat > 0.01 ? `saturate(${(1 - desat).toFixed(3)})` : '',
          fgBlur > 0.2 ? `blur(${fgBlur.toFixed(2)}px)` : '',
          shadow ?? '',
        ].filter(Boolean).join(' ') || undefined,
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
/** A pan's position over the shot: a gentle ramp that is CONSTANT-velocity through the middle, starting and
 *  ending at rest so a cross-dissolve never runs over a moving frame. -0.5..0.5 so the travel is centred. */
export const panAt = (t: number): number => {
  const e = 0.12;                                   // the eased fraction at each end
  const u = clamp01(t);
  // Three pieces that JOIN: accelerate to unit speed over e, hold it, decelerate over e. Written as a
  // shorthand first, its third piece did not meet the second — the travel ended at 0.636 instead of 0.5 and
  // the frame jumped at the hand-over. The distance covered is (1 - 2e) at speed plus e/2 at each end.
  const p = u < e
    ? (u * u) / (2 * e)
    : u <= 1 - e
      ? e / 2 + (u - e)
      : (1 - 1.5 * e) + ((u - (1 - e)) - ((u - (1 - e)) * (u - (1 - e))) / (2 * e));
  return p / (1 - e) - 0.5;                         // centred: -0.5 at rest, +0.5 at rest
};

/** A pan request, validated. Returns null for "no pan"; THROWS on a shape that cannot be a direction, so a
 *  malformed prop is a loud failure rather than a camera that silently holds. */
export const clampPan = (pan: unknown): [number, number] | null => {
  if (pan === undefined || pan === null) return null;
  if (!Array.isArray(pan) || pan.length !== 2 || !pan.every((v) => typeof v === 'number' && isFinite(v))) {
    throw new Error(`SceneCamera pan must be [x, y] with two finite numbers in -1..1, got ${JSON.stringify(pan)}`);
  }
  const [x, y] = pan as [number, number];
  if (x === 0 && y === 0) return null;
  const clamp1 = (v: number) => Math.max(-1, Math.min(1, v));
  return [clamp1(x), clamp1(y)];
};

/**
 * The camera BED — the default stance of a beat nobody authored a camera for: a slow, near-linear lateral
 * drift, the same gesture the html tier has always shipped as its Ken Burns floor.
 *
 * WHY THE DEFAULT CHANGED, with the numbers. The lock ("a pan that appeared on its own would be a
 * regression") dates from when shake could not be proven absent, so the only safe camera was none — a floor
 * on shake bought by a ceiling on motion. Both instruments now exist (scripts/shake_qa.py: global wander;
 * flicker(): local reversals), and the measurements are unambiguous: the planner's punctuation alone covers
 * 2-4 beats of a 20-30 beat film (~10% of runtime) while the delivery gate's p75 needs motion on >25% of
 * frames — mathematically out of reach; the whole-film ambient drift moves the number +9%; a scale-only
 * push stamped on every beat +32% (recorded above `pan`); a lateral pan reached 0.0112 against the 0.0037
 * floor. The missing operation was a translate on the beats that hold.
 *
 * WHY IT CANNOT BE THE OLD SHAKE, structurally rather than by promise: `panAt` is a monotone three-piece
 * ramp (pinned by test_camera_pan), so within any beat the frame TRAVELS — path equals net displacement,
 * wander ~1, the exact signature shake_qa calls clean; direction changes only at a cut, where continuity is
 * not expected. The travel is bounded by the overscan (no edge is ever revealed) and by captionSlackPx
 * downward (the burned caption's band is not the camera's to spend). Amplitude is derived from the same cap
 * as everything else, at BED_AMOUNT_FRAC of it — deliberately under the 0.75 a motivated move takes, so
 * punctuation stays punctuation.
 *
 * WHO GETS IT: themed films only (the null-DNA rule keeps machinery out of the un-themed look), beats with
 * NO authored camera (an authored move — even `hold` — wins outright), never under reduced motion, and
 * never alongside the whole-film ambient drift (two beds are the coexistence the shake guard exists to
 * refuse). `meta.camera_bed: false` switches it off film-wide.
 */
export const BED_AMOUNT_FRAC = 0.45;
export const bedPan = (
  index: number,
  themed: boolean,
  ambientAmp: number,
  authored?: {move?: CameraMove; amount?: number; pan?: [number, number]} | null,
  enabled = true,
): {pan: [number, number]; bed: true} | null => {
  if (!enabled || !themed || ambientAmp > 0 || authored) return null;
  // Deterministic per-beat direction: lateral alternates so two adjacent holds do not read as one long
  // drift a cut interrupted; the vertical component drifts UPWARD only, because downward is the caption's
  // direction and, although the clamp would stop it, a bed that leans on a safety clamp is a bed designed
  // wrong. hash01 keeps the amplitude from being metronomic without ever being random.
  const dx = (index % 2 === 0 ? 1 : -1) * (0.5 + 0.25 * hash01(index * 7 + 1));
  const dy = -(0.1 + 0.12 * hash01(index * 13 + 5));
  return {pan: [dx, dy], bed: true};
};

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
  /**
   * A lateral TRAVEL across the shot, as a fraction (-1..1 per axis) of the overscan the push already buys.
   *
   * WHY THIS EXISTS, measured. A scale-only camera barely moves a frame: pixels near the transform origin
   * travel almost nothing, and most of a composed frame's content sits near the middle. Stamping a camera on
   * every one of a 30-beat film's beats took its frame-diff p75 from 0.0022 to 0.0029 — a 32% gain, still
   * under the 0.0037 floor, against 0.0112 measured for the same film under a constant-velocity pan. The
   * missing operation is a translate, not a bigger zoom.
   *
   * SAFE BY CONSTRUCTION, which is why it needs no cap of its own: at scale s the layer covers (s-1)/2 of
   * the frame beyond each edge, and the travel is budgeted from exactly that, so a pan can never reveal an
   * edge or push content further toward the caption band than `maxCameraPush` already allows. A pan asked
   * for on a HOLD gets the same base overscan a gentle push would have used, so it is a real move and not a
   * silent no-op — a camera that quietly does nothing is the failure this runtime keeps finding.
   */
  pan?: [number, number];
  // the largest EXTRA scale the film-wide ambient drift is adding on top of this move. The two layers
  // multiply, so the per-beat budget has to be whatever the drift has not already spent.
  driftExtra?: number;
  driftTranslate?: number;
  children?: React.ReactNode;
  /** this camera is the BED: derive the smaller BED_AMOUNT_FRAC of the cap instead of a move's 0.75 */
  bed?: boolean;
}> = ({move = 'hold', amount, pan, driftExtra = 0, driftTranslate = 0, bed = false, children}) => {
  const {width: W, height: H} = useVideoConfig();
  const reduced = React.useContext(ReducedMotionContext);
  const t = useT();
  const cap = maxCameraPush(W, H, driftExtra, driftTranslate);
  // THE DEFAULT AMOUNT IS DERIVED FROM THE ROOM, not hand-set. 0.045 was a number chosen once at 16:9 and
  // then clamped everywhere else — at 9:16 the cap is 4.7%, so the "default" was 96% of the maximum there
  // and 45% of it at 16:9: the same authored intent produced two different moves. Three-quarters of the
  // cap is the same fraction of the available headroom at every aspect and every drift level, which is
  // what "a gentle push" should mean.
  const amp = reduced ? 0 : Math.max(0, Math.min(amount ?? cap * (bed ? BED_AMOUNT_FRAC : 0.75), cap));
  const push = amp > 0 ? cameraAt(move, t) : 0;
  // A pan needs overscan to travel in. On a HOLD the push provides none, so the pan brings its own — the
  // same three-quarters-of-the-cap a gentle push would have taken, held CONSTANT so the frame does not also
  // zoom. Reduced motion zeroes it with everything else.
  const px = reduced ? 0 : clampPan(pan);
  const panning = px !== null;
  const base = panning && amp * push < amp * 0.5 ? amp : 0;
  const scale = 1 + Math.max(amp * push, base);
  const over = (scale - 1) / 2;                     // fraction of the frame available beyond EACH edge
  // Near-LINEAR travel. An ease-in-out spends most of its frames at the flat ends, which is where the
  // measured motion went missing; a gentle constant drift is what a Ken Burns move actually is.
  const trav = panning ? panAt(t) : 0;
  const tx = panning ? px[0] * over * W * trav : 0;
  // THE VERTICAL COMPONENT IS BOUNDED BY THE CAPTION BAND, not only by the overscan. The overscan budget
  // guarantees no frame EDGE is revealed and says nothing about the one band reserved for something else:
  // measured on a delivered film, a beat panned downward put the register's own title on top of the burned
  // subtitle and made both unreadable. The caption rides a HUD track that does not move with the camera, so
  // only the scene can close that gap — and it must not.
  const downRoom = captionSlackPx(W, H, driftExtra, driftTranslate);
  const tyRaw = panning ? px[1] * over * H * trav : 0;
  const ty = Math.min(tyRaw, downRoom);              // upward travel is unconstrained; downward is not
  const originY = (CONTENT_TOP + contentBottom(W, H)) / 2;
  const xf = [
    tx || ty ? `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px)` : '',
    scale === 1 ? '' : `scale(${scale.toFixed(5)})`,
  ].filter(Boolean).join(' ');

  return (
    <CameraContext.Provider value={{push, amount: amp}}>
      <div style={{
        position: 'absolute', inset: 0,
        transform: xf || undefined,
        transformOrigin: `50% ${originY.toFixed(1)}px`,
      }}>
        {children}
      </div>
    </CameraContext.Provider>
  );
};
