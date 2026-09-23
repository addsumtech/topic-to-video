// SHOT · Crane Up — from down here it was a line of edges; the camera rises and tilts down, and it is an
// arrangement. The items lie FLAT on the ground, so at eye level they are foreshortened to almost nothing
// and only their fronts read; the lift is what makes the shape they are in visible at all.
//
// WHAT IT ARGUES, AND WHY NO LENS CAN SAY IT. The library already changes the lens in every direction:
// `CrashZoom` punches in, `InfiniteCanvas` zooms deep, `DollyZoom` swells the room while the subject holds,
// `RackFocus` moves the attention through depth, `PageWrite` and `TermSpace` pull back to show the whole.
// Every one of them keeps the camera's EYE where it was. A crane moves the eye, and that is a different
// claim: not "look closer", not "look at more of it", but "you could not see this from where you were
// standing". Zooming out from a plane seen edge-on shows you more edge; only elevation resolves it.
//
// So the arrangement is on the FLOOR, never upright. Upright cards read from eye level and the lift would
// be decoration — a camera move with nothing to reveal, which is the failure mode a camera register has to
// avoid to be a register rather than a preset. On the floor the foreshortening does the argument's work:
// what the frame withholds at the start is the same information it hands over at the end.
//
// THE CAMERA IS ON AN ARC, NOT A LADDER. Raising `y` alone walks the subject out of frame — the eye keeps
// pointing where it pointed. The position is derived from the AIM: `cam = target + D · forward(rx, ry)`,
// where a pose's forward axis in CSS's own order (translate, rotateX, rotateY) is
// (sin ry cos rx, −sin rx cos ry… ) as `runtime/stage3d` composes it, so the target stays centred through
// the whole move and the only thing that changes is where it is being seen FROM. `TermSpace` derives its
// fly-to the same way, for the same reason, and its header records what the naive version cost.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, lerp, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, readableOn, dimOn, plane} from '../runtime/dna';
import {Stage3D, Surface, projectPose, PERSP_FRAC, type Pose} from '../runtime/stage3d';

export const DURATION = 195; // 6.5s

/** Three is the fewest that can form a SHAPE a viewer could not read edge-on — two things in a row look
 *  the same from any height. Past twelve the tiles are smaller than their own labels at the top of the
 *  move, and the reveal resolves into something still unreadable. */
export const MIN_TILES = 3, MAX_TILES = 12;

/** Where the camera starts and ends, in degrees of downward tilt. The low angle is not zero: dead level
 *  puts the floor exactly edge-on, which renders as a mathematically invisible plane rather than as a
 *  view along it, and the shot opens on nothing at all. */
const RX_LOW = 7, RX_HIGH = 52;

const BG_D0 = '#0c0f14', FG_D0 = '#e9eef6', DIM_D0 = '#727d8d';
const ACC_D0 = '#e0a33c', LINE_D0 = '#1e242e';

// Placeholder copy in the library's placeholder voice — the preview and all three measurement scripts
// render with defaults, and a prop left at '' does not draw at all.
const DEMO = ['one', 'another', 'another', 'another', 'another', 'another'];

export const CraneUp: React.FC<{
  kicker?: string;
  /** what is lying there — the labels, in the order they are laid out */
  tiles?: string[];
  /** what it looked like from down here, before the lift */
  near?: string;
  /** what the shape turns out to be, named once the camera is high enough to see it */
  reveal?: string;
  /** one line under the frame, in the film's voice */
  note?: string;
}> = ({kicker = 'FROM DOWN HERE', tiles = DEMO, near = 'it looked like one of them',
       reveal = 'from up here it is the whole set',
       note = 'the arrangement was never visible at eye level'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();

  // ── the film's data, refused rather than trimmed ────────────────────────────────────────────────────
  const TL = (Array.isArray(tiles) ? tiles : []).map((s) => String(s ?? '').trim());
  if (TL.length < MIN_TILES) {
    throw new Error(
      `CraneUp needs at least ${MIN_TILES} tiles, got ${TL.length}. The claim is that the ARRANGEMENT was ` +
      'invisible from eye level, and two things in a row look the same from any height — there is no ' +
      'shape for the lift to reveal.');
  }
  if (TL.length > MAX_TILES) {
    throw new Error(
      `CraneUp holds at most ${MAX_TILES} tiles, got ${TL.length}. Past that the tiles are smaller than ` +
      'their own labels at the top of the move, and the reveal resolves into something still unreadable.');
  }
  const blank = TL.findIndex((s) => !s);
  if (blank >= 0) {
    throw new Error(
      `CraneUp was given an empty tile (index ${blank}). An unlabelled tile in a revealed arrangement is ` +
      'furniture: name what is lying there, or lay out fewer.');
  }

  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const BG = dna?.bg ?? BG_D0;
  // A STEP FROM THE GROUND, not a named surface colour. `dna.surface` on a dark preset is within a few
  // points of `dna.bg`, and the first render put six tiles on a ground they were almost the same value as
  // — an arrangement being revealed that a viewer cannot see. `plane` steps AWAY from the ground in
  // whichever direction the ground allows, so this holds on a light film as well as a dark one.
  const SURF = plane(BG, 0.12);
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const U = Math.min(W, H);
  const strong = readableOn(BG, FG, FG_D0);
  const soft = dimOn(BG, DIM, 3);
  const P = Math.round(U * PERSP_FRAC);

  // ── the arrangement, ON THE FLOOR ───────────────────────────────────────────────────────────────────
  // A grid, because a single row still reads as a row from eye level and the lift would reveal only its
  // length. Columns come from the count so the shape is as square as the count allows — the thing being
  // revealed is a SHAPE, and a 1×N shape is the one the low angle already gave away.
  // Columns follow the FRAME, not just the count: a square-ish grid of six is 2x3, which at 16:9 is a
  // narrow column down the middle of a wide frame and at 9:16 is the opposite. Weighting the count by the
  // aspect gives 3x2 on a landscape frame and 2x3 on a portrait one, from one expression.
  const cols = Math.min(4, Math.max(2, Math.min(TL.length, Math.round(Math.sqrt(TL.length * (W / H))))));
  const rows = Math.ceil(TL.length / cols);
  const tileW = U * 0.30, tileH = U * 0.19, gap = U * 0.045;
  const poses: Pose[] = TL.map((_, i) => ({
    x: ((i % cols) - (cols - 1) / 2) * (tileW + gap),
    y: 0,
    z: (Math.floor(i / cols) - (rows - 1) / 2) * (tileH + gap),
    rx: 90,                                           // lying flat: the whole reason the low angle hides it
  }));

  // ── the move. One eased lift, no cuts. ──────────────────────────────────────────────────────────────
  const lift = easeInOutCubic(clamp01(seg(t, 0.12, 0.84)));
  const rx = lerp(RX_LOW, RX_HIGH, lift);
  const rxR = (rx * Math.PI) / 180;
  // The camera sits at a fixed distance from the arrangement's centre, on the arc its own aim describes.
  // Derived from the aim rather than set as a height, or the subject leaves the frame as the shot rises.
  // DISTANCE IS DERIVED FROM THE ARRANGEMENT, so a grid of three and a grid of twelve both fill the frame
  // rather than one of them sitting in the middle as a postage stamp. A CSS perspective P scales an object
  // at eye-space depth D by P/(P+D), so asking for a target on-screen radius inverts to a distance. The
  // first render used a flat U * 1.35 and the whole arrangement occupied about a fifth of the frame width.
  const R = Math.hypot(cols * (tileW + gap), rows * (tileH + gap)) / 2;
  const TARGET_R = U * 0.40;
  const D = Math.max(U * 0.5, P * (R / TARGET_R - 1));
  const cam: Pose = {x: 0, y: -D * Math.sin(rxR), z: D * Math.cos(rxR), rx, ry: 0};

  // ── type ────────────────────────────────────────────────────────────────────────────────────────────
  // @billboard: the tiles lie at rx 90, so type SET ON them is foreshortened to nothing at exactly the
  // angle this register opens on, and invisible to every type gate, which reads the DOM. The argument is
  // that the low angle hides the ARRANGEMENT; it must not also hide the words. So the labels are flat,
  // positioned at each tile's projected centre and scaled by its own perspective factor.
  const LABEL_PX = Math.round(U * 0.021);
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019);
  const LINE_PX = Math.round(U * 0.034);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);

  // Labels appear as the angle makes them worth reading — below about 20 degrees the tiles are slivers and
  // a label over one points at a sliver. Tied to the ANGLE, not to the clock, so it stays true if the
  // move's timing changes.
  const legible = clamp01((rx - 20) / 18);

  const nearIn = clamp01(seg(t, 0.06, 0.16)) * (1 - clamp01(seg(t, 0.30, 0.44)));
  const revealIn = clamp01(seg(t, 0.70, 0.84));
  const kickIn = clamp01(seg(t, 0.02, 0.1)) * (1 - clamp01(seg(t, 0.74, 0.86)));
  const noteIn = clamp01(seg(t, 0.86, 0.96));

  const revealLines = reveal ? wrapLines(String(reveal), LINE_PX, W * 0.7) : 0;
  const noteLines = note ? wrapLines(String(note), NOTE_PX, W * 0.82) : 0;

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <Stage3D cam={cam} persp={P}>
        {poses.map((pose, i) => (
          <Surface key={i} pose={pose} w={tileW} h={tileH}
            style={{background: SURF, border: `${Math.max(1, Math.round(U * 0.0016))}px solid ${LINE}`,
              borderRadius: U * 0.008}} />
        ))}
      </Stage3D>

      {/* the labels, flat on the screen over their own tiles */}
      {poses.map((pose, i) => {
        const pt = projectPose(pose, cam, P, W, H);
        // A tile behind the lens has no on-screen position, and `projectPose` says so rather than
        // returning a number that happens to be finite. Drawing it anyway puts a label where nothing is.
        if (!pt || pt.behind || !Number.isFinite(pt.x) || !Number.isFinite(pt.y)) return null;
        // SCALED BY THE SAME PERSPECTIVE FACTOR AS ITS TILE. Flat type at a fixed size over a floor in
        // perspective makes the far row's labels as large as the near row's, which reads as a caption
        // layer floating over the shot instead of as writing on the arrangement.
        const kw = tileW * pt.k, kp = Math.max(9, LABEL_PX * pt.k);
        return (
          <div key={i} style={{position: 'absolute', left: pt.x - kw / 2, top: pt.y - kp,
            width: kw, textAlign: 'center', opacity: legible,
            font: `600 ${kp}px/${leading(TL[i], 1.2)} ${disp}`, color: strong}}>{TL[i]}</div>
        );
      })}

      {kicker ? (
        <div style={{position: 'absolute', left: W * 0.08, top: zoneTop - U * 0.05, opacity: kickIn,
          font: `600 ${KICK_PX}px/1.2 ${mono}`, letterSpacing: '0.16em', color: ACC}}>{kicker}</div>
      ) : null}

      {/* what it looked like from down there — and then what it is */}
      {near ? (
        <div style={{position: 'absolute', left: W * 0.15, width: W * 0.7, textAlign: 'center',
          top: zoneTop + U * 0.02, opacity: nearIn,
          font: `500 ${LINE_PX}px/${leading(String(near), 1.2)} ${disp}`, color: soft}}>{near}</div>
      ) : null}
      {reveal ? (
        <div style={{position: 'absolute', left: W * 0.15, width: W * 0.7, textAlign: 'center',
          top: zoneTop + U * 0.02, opacity: revealIn,
          transform: `translateY(${(1 - easeOutCubic(revealIn)) * U * 0.02}px)`,
          font: `700 ${LINE_PX}px/${leading(String(reveal), 1.2)} ${disp}`,
          color: readableOn(BG, ACC, strong)}}>{reveal}</div>
      ) : null}

      {note ? (
        <div style={{position: 'absolute', left: W * 0.09, width: W * 0.82, opacity: noteIn,
          top: zoneBot - noteLines * NOTE_PX * 1.4 - U * 0.01,
          font: `400 ${NOTE_PX}px/${leading(String(note), 1.4)} ${mono}`, color: soft}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default CraneUp;
