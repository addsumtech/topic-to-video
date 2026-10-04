// SHOT · Port Rail — things PLUG IN. One machined rail runs across the stage and, one at a time, modules
// travel down their own axis and seat onto it, the gap closing under real light. Genuine WebGL: real lights,
// real shadows, real occlusion.
//
// WHAT IT ARGUES, AND HOW IT DIFFERS FROM THE OTHER 3D REGISTER. `MaterialHero` says parts form ONE thing —
// arcs closing into a ring, a claim about unity. This says things FIT one standard: a part enters a socket,
// the fit is the same for all of them, nothing is configured. Drawn as a hub-and-spoke graph that claim
// weakens into topology — a graph says "these are related", a seated plug says "this one goes in here and it
// clicks". So the argument IS the seating, and the frame is built to let you watch it: the modules approach
// along the socket axis, decelerate, and stop flush.
//
// WHY A RAIL AND NOT A RING, which cost three cuts to learn twice. From any angle low enough to see a plug
// enter its socket, a RING puts its nearest item huge in the foreground, crossing the caption, and its
// farthest one behind the hub as a sliver. Six things that must each be READ want to be the same distance
// from the lens. A rail gives every label the same size and a clean row to live in — and it is how
// connectors are actually photographed.
//
// WHY THE TYPE IS NOT IN THE SCENE. A CJK glyph baked onto a texture is mush at render scale and takes the
// surface's lighting, so the copy would dim whenever its module turned from the key. Every label is an
// ordinary DOM element placed by `runtime/project3d`: crisp type in the film's own face, anchored to a real
// object, and visible to the text-safety and CJK gates, which cannot see inside a canvas.
//
// EVERY MODULE THE FILM GAVE SEATS, OR THE REGISTER SAYS THE RAIL CANNOT HOLD IT. It used to flatten `groups`
// (or `items`) and take `.slice(0, 6)`: a film's seventh integration never plugged in, and with groups the
// cut fell on whichever kind came last, so a whole named kind could lose members — or vanish — while its
// label still promised it. Empty entries and empty groups were filtered out the same way. Now the whole run
// seats or it THROWS: past MAX_RAIL_MODULES, on an empty entry, on a group with no items, and on a `groups`
// that carries nothing (which used to fall back to `items` — the demo's app names, when the film gave none).
// Six is the standing rail's limit: at 9:16 it is at most 2.6 units long for modules 0.42 tall, so six leave
// 0.10 between neighbours and a seventh leaves 0.01 — the modules touch and the labels beside them collide.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useDNA, dnaPalette, contrastOf, relLum} from '../runtime/dna';
import {project, yawPoint, type Vec3} from '../runtime/project3d';
import {AimCamera} from '../runtime/aimCamera';
import {captionBand, CONTENT_TOP, fitTextPx, fitBlockPx, textWidthPx} from '../runtime/layout';
import {frameCamera, boxCorners} from '../runtime/fitCamera';
import {leading} from '../runtime/cjkType';
import {useT, useAnimSpan, springAt, SPRING_SEAT, seg, clamp01, easeInOutCubic,
        lerp} from '../runtime/motion';
import {useGlide, usePlaceGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s
export const MAX_RAIL_MODULES = 6;

const BG_D0 = '#0b0d13', FG_D0 = '#eef2f8', DIM_D0 = '#8b93a8', ACC_D0 = '#5b8cff';
const TONES0 = ['#5b8cff', '#37d4a6', '#f6a531', '#c07bff', '#ff6f91', '#4dd0e1'];

// The stage, in world units. The camera and every label read these, so the frame composes from ONE geometry.
const SPAN = 4.05;          // the rail's length; short of the frame edge, because the row needs margin
// HOW HIGH A MODULE STARTS is a framing number, not a taste one. Too high and the waiting modules are cut by
// the top edge for the first third of the shot — the final frame looks perfect and the motion is broken,
// which is why a still is not a check for a shot whose argument is the movement.
const LIFT = 1.22;
const CAM: Vec3 = [0, 2.30, 5.55];
const AIM: Vec3 = [0, 0.34, 0];
const FOV = 34;
const YAW = (frame: number) => Math.sin(frame * 0.005) * 0.055;   // a breath, not a turntable

// THE RAIL TURNS IN PORTRAIT, because a row does not fit one. At 9:16 the horizontal rail ran four of its
// six modules clean off both edges — the library's own rule is that a multi-column layout must STACK there,
// and a rail is a row. Pulling the camera back instead would fit it and shrink every label to nothing, so
// the axis rotates: the bar stands up, the modules seat in from the side, and the labels move beside them.
// The argument is unchanged, because "a part enters a socket" does not care which way the socket faces.
// A ROW READS LEFT TO RIGHT AND A STACK READS DOWNWARD, so the axis flips its SIGN as well as its direction.
// World +Y is up, so the untouched formula puts item 1 at the bottom of a standing rail and the last item at
// the top — the list runs backwards, and nothing in the frame says so.
// the module's own body colour — named once so the tone chooser and the mesh cannot drift apart.
const MODULE_FACE = '#5d6889';

const slotAt = (i: number, n: number, span: number, vert = false, slots?: number[]) => {
  // GROUPED MODULES ARE SPACED BY THEIR GROUP, not evenly. A reviewer looked at a rail of six carrying three
  // kinds and reported that "三类" rested entirely on a small legend — the bars said it and the LAYOUT did
  // not, and spacing is the one variable a viewer reads without being told to. With `slots` the run keeps
  // its total span and redistributes it, so the groups separate without the rail growing.
  const s = slots && slots.length === n ? slots[i]
    : (n <= 1 ? 0 : (i / (n - 1) - 0.5) * span);
  return vert ? -s : s;
};

/** Positions across `span` with an extra gap wherever the group changes. */
const groupSlots = (g: number[], span: number): number[] => {
  const n = g.length;
  if (n <= 1) return [0];
  const GAP = 1.9;                                       // a between-group step, in units of a within one
  const steps = g.slice(1).map((x, k) => (x === g[k] ? 1 : GAP));
  const total = steps.reduce((a, b) => a + b, 0);
  let acc = 0;
  return g.map((_, i) => {
    if (i > 0) acc += steps[i - 1];
    return (acc / total - 0.5) * span;
  });
};

// THE SHADOW CATCHER SITS UNDER WHATEVER STANDS ON IT, and that is not a detail. Upright, the row rides just
// above a floor at -0.155. Stood up, the stack reaches well BELOW that plane — and a camera above a plane
// cannot see through it, so the lower modules were hidden BEHIND the floor while their DOM labels, which the
// GL depth buffer knows nothing about, kept drawing: a rail showing three of six modules and six labels.
// Measured at n=3 it hid exactly the one module below the plane and no other, which is the fingerprint of an
// occluder rather than of a layout that ran off frame.
const floorAt = (vert: boolean, span: number) => (vert ? -(span / 2) - 0.75 : -0.155);

/** Each module's seating, staggered left to right so the eye can follow one plug at a time.
 *
 *  IT IS A SEATING, NOT A DRIFT. Spread over a quarter of the shot each module crossed its gap so slowly
 *  that the measured frame-to-frame motion sat under the library's own floor — and the picture agreed with
 *  the number: a part that eases into a socket over a second and a half reads as floating, not as clicking
 *  home.
 *
 *  IT IS A SPRING, because the argument of this whole register is that a part SEATS. `easeOutBack` gave it
 *  one fixed overshoot, the same one every other element in the library lands with; a spring gives the
 *  module mass, so what the eye reads is the weight of the thing arriving rather than a curve applied to it.
 *  Driven off the shot's own clock (`useT`/`useAnimSpan`), so it stays perfectly still through the seam
 *  the cross-dissolve runs over. */
const seatAt = (t: number, span: number, fps: number, i: number, n: number) =>
  springAt(t, span, fps, 0.08 + (i / Math.max(1, n)) * 0.52, SPRING_SEAT);

const Scene: React.FC<{n: number; tones: string[]; toneOf: number[]; slots?: number[]; accent: string; floor: string; vert: boolean;
  span: number; t: number; aim: Vec3; cam: Vec3; animSpan: number; fps: number}> =
  ({n, tones, toneOf, slots, accent, floor, vert, span, t, aim, cam, animSpan, fps}) => {
  const frame = useCurrentFrame();
  return (
    <>
      <AimCamera at={aim} from={cam} />
      {/* A key that carves the form and a cool fill so the shadow side is not black.
          NO KICKER FROM BEHIND, and the reason is worth keeping: the floor is what the camera sees behind
          the row, so a light placed back there lights the BACKDROP rather than the objects. As a point light
          it pooled into a bright blob in the sky of the frame; as a directional it washed the background warm
          and blew out the top faces. */}
      {/* LIT LIKE A PRODUCT, NOT LIKE A NIGHT SCENE. The first pass was dark navy metal on a near-black
          ground: correct materials, murky picture, and a measured ink and light range near the bottom of the
          whole library. A key strong enough to actually MODEL the boxes separates the row from its stage,
          which is what a catalogue photograph does and what a phone-sized frame needs. */}
      <ambientLight intensity={0.52} />
      <hemisphereLight args={['#a8bce8', '#0d1018', 0.78]} />
      <directionalLight position={[3.4, 6.4, 5.2]} intensity={3.6} castShadow
        shadow-mapSize-width={2048} shadow-mapSize-height={2048}
        shadow-camera-left={-6} shadow-camera-right={6} shadow-camera-top={6} shadow-camera-bottom={-6} />
      <directionalLight position={[-5.5, 2.2, 2.4]} intensity={0.85} color={'#c7dbff'} />

      <group rotation={[0, YAW(frame), 0]}>
        {/* THE RAIL — the standard itself, one machined bar every module meets the same way */}
        <mesh position={[0, 0, 0]} castShadow receiveShadow>
          <boxGeometry args={vert ? [0.30, span + 1.15, 0.86] : [span + 1.15, 0.30, 0.86]} />
          <meshStandardMaterial color={'#454e6c'} metalness={0.58} roughness={0.32} />
        </mesh>
        {/* the accent as a machined groove along its face: a MARK on an object, never a light source */}
        <mesh position={vert ? [-0.055, 0, 0.432] : [0, -0.055, 0.432]}>
          <boxGeometry args={vert ? [0.035, span + 1.15, 0.006] : [span + 1.15, 0.035, 0.006]} />
          <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.42} roughness={0.55} />
        </mesh>

        {Array.from({length: n}).map((_, i) => {
          const s = seatAt(t, animSpan, fps, i, n);
          return (
            <group key={i} position={vert
              ? [lerp(LIFT, 0.365, s), slotAt(i, n, span, true, slots), 0]
              : [slotAt(i, n, span, false, slots), lerp(LIFT, 0.365, s), 0]}>
              {/* ONE MATERIAL FOR EVERY MODULE, so the row reads as a manufactured set. Six saturated hues
                  are what `dnaPalette` hands you and they are right for a diagram and wrong for an object:
                  a product photograph identifies its parts by a MARK, not by dyeing each one. */}
              <mesh castShadow receiveShadow>
                <boxGeometry args={[0.56, 0.42, 0.62]} />
                <meshStandardMaterial color={MODULE_FACE} metalness={0.34} roughness={0.40} />
              </mesh>
              {/* the tone, a thin bar on the FRONT face. On a ring it sat on the outward face, which pointed
                  away from the lens for half the modules and left them unidentifiable. */}
              <mesh position={[0, -0.115, 0.312]}>
                <boxGeometry args={[0.34, 0.045, 0.008]} />
                <meshStandardMaterial color={tones[(toneOf[i] ?? i) % tones.length]}
                  emissive={tones[(toneOf[i] ?? i) % tones.length]}
                  emissiveIntensity={0.45} roughness={0.55} />
              </mesh>
              {/* the pin that enters the rail — the part that makes this a PLUG and not a tile. The gap it
                  crosses is visible until the module seats, which is the whole argument. */}
              <mesh position={vert ? [-0.255, 0, 0] : [0, -0.255, 0]} castShadow>
                <boxGeometry args={vert ? [0.14, 0.20, 0.26] : [0.20, 0.14, 0.26]} />
                <meshStandardMaterial color={'#b9c4d8'} metalness={0.92} roughness={0.20} />
              </mesh>
            </group>
          );
        })}

        {/* the floor exists only to CATCH the shadow — without it the row floats and the depth dies. Its
            colour is the ground's own, so its rim is never a visible arc across the frame. */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, floorAt(vert, span), 0]} receiveShadow>
          <circleGeometry args={[7.5, 64]} />
          <meshStandardMaterial color={floor} metalness={0.1} roughness={0.95} />
        </mesh>
      </group>
    </>
  );
};

export const PortRail: React.FC<{
  standard?: string;
  items?: string[];
  /** Items that belong to NAMED KINDS. Given these, each module's tone bar takes its group's colour and a
   *  key is drawn, so the one visual variable on the rail identifies something instead of counting. Without
   *  them the bar is chosen by INDEX — which is furniture: a reviewer looked at a rail of six modules whose
   *  bars ran mint / pale blue / pale cyan / blue / white / teal with no key, under a narration whose claim
   *  was THREE KINDS of channel, and reported that the only visual variable present carried no meaning. */
  // @supersedes groups: items
  groups?: {label?: string; items?: string[]}[];
  note?: string;
}> = ({
  standard: STANDARD = 'One standard', items: ITEMS = ['Docs', 'Chat', 'Mail', 'Calendar', 'Wiki', 'DB'],
  groups: GROUPS, note: NOTE = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H, fps} = useVideoConfig();
  const animSpan = useAnimSpan();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const TONES0_ = dnaPalette(dna, 6) ?? TONES0;
  // The halo behind a label is THE GROUND'S OWN COLOUR, softened — not black. Black is invisible on a dark
  // stage (where it was written and looked fine) and a grey smudge behind dark type on a paper-ground DNA,
  // which is the same declaration reading as craft in one film and as a printing fault in the next. Taking
  // it from the ground needs no light/dark branch: it is always the colour the type is sitting on.
  const SOLID = dna?.bg ?? BG_D0;
  const HALO = /^#[0-9a-f]{6}$/i.test(SOLID) ? `${SOLID}cc` : SOLID;
  // GROUPS WIN WHEN THEY ARE GIVEN, and the rail's cap applies to the flattened run either way. Every
  // entry is drawn once or the register refuses — see the header for what the old filters and cut dropped.
  const entry = (x: unknown, where: string) => {
    const text = String(x ?? '').trim();
    if (!text) throw new Error(`PortRail: ${where} is empty. Every module carries the name of what plugs in.`);
    return text;
  };
  if (GROUPS != null && (!Array.isArray(GROUPS) || GROUPS.length === 0)) {
    throw new Error('PortRail: `groups` was given but holds no groups. Pass `groups: [{label, items: [...]}]`, ' +
      'or omit `groups` and pass `items`.');
  }
  const gs = (GROUPS ?? []).map((g, gi) => {
    if (!Array.isArray(g?.items) || !g.items.length) {
      throw new Error(`PortRail: group ${gi + 1}${g?.label ? ` (${JSON.stringify(g.label)})` : ''} has no items. ` +
        'A named kind with nothing in it would draw a label over an empty stretch of rail.');
    }
    return {label: String(g?.label ?? '').trim(),
            items: g.items.map((x, k) => entry(x, `group ${gi + 1} item ${k + 1}`))};
  });
  const flat: {text: string; g: number}[] = gs.length
    ? gs.flatMap((g, gi) => g.items.map((text) => ({text, g: gi})))
    : (Array.isArray(ITEMS) ? ITEMS : []).map((x, i) => ({text: entry(x, `item ${i + 1}`), g: -1}));
  if (flat.length > MAX_RAIL_MODULES) {
    throw new Error(
      `PortRail seats 1-${MAX_RAIL_MODULES} modules on its rail (got ${flat.length}${gs.length ? ' across the groups' : ''}). ` +
      `A seventh module touches its neighbours on the standing rail (any frame narrower than 5:4). Group the modules into ` +
      `${MAX_RAIL_MODULES} or fewer, or use a list or grid register for a longer set.`);
  }
  const seats = flat;
  const list = seats.map((x) => x.text);
  // the tone INDEX per module: its group when there are groups, its own position when there are not.
  // ONE MARK, ONE COLOUR. Dropping the group-keyed tone left the bar back on `i` — six unrelated hues
  // (measured 169/214/193/205/206/224 deg) that encode nothing, under an adaptation note saying colour had
  // been removed as a variable. Removing a false code and leaving a random one in its place is the same
  // defect with the claim deleted. The bar marks "this is a module", which is what this register's own note
  // asks of it, so every module wears the same one.
  const toneOf = seats.map(() => 0);
  // GROUP TONES ARE CHOSEN BY MEASURED CONTRAST AGAINST THE SURFACE THEY SIT ON, because both of the
  // obvious rules fail and they fail in opposite directions. `dnaPalette` seeds with the film's two accents
  // and derives the rest by shading toward the GROUND, so half its entries are dark:
  //
  //   first N          accent2 measures 1.71:1 on the module face — a reviewer called groups 2 and 3 "close
  //                    in hue AND value", and they were.
  //   spread across    walked group 3 onto #316a96 = 1.05:1. Measured on the delivered frame: 1.00:1. The
  //                    band was the same luminance as the cube it sat on, so the one variable this grouping
  //                    added carried NOTHING on a third of the items — while the adaptation note claimed
  //                    the colours had been pulled apart so the legend would work.
  //
  // Neither is a rule about colour; both are rules about INDEX. Filter to the tones that actually separate
  // from the face, then spread inside that. On TERMINAL_DNA this yields 2.98 / 3.35 / 3.91 : 1.
  // COLOUR DOES NOT CARRY THE GROUPING HERE, and that is a measured conclusion rather than a preference.
  // Three attempts, each fixing the previous one's defect and creating the next:
  //
  //   first N of the palette   groups 2 and 3 "close in hue AND value"      (reviewer, on the frame)
  //   spread across it         group 3 at 1.00:1 on the cube — invisible    (reviewer, measured)
  //   most legible N           legible, and all three pale and alike        (measured here)
  //
  // The cause is structural: the module face is a mid-value blue-grey by design ("one material for every
  // module, so the row reads as a manufactured set"), so anything legible against it must be much lighter,
  // and much-lighter collapses the palette's hues toward white. An exhaustive search over the six tones
  // found no set of three that clears 2.5:1 on the face AND stays apart from the others.
  //
  // So the row keeps its ONE mark — which is what this register's own note asks for, a product photograph
  // identifying its parts by a mark rather than by dyeing each one — and the GROUPING is carried by the two
  // variables that measurably work: the gap between clusters, and a name under each cluster. No legend,
  // because there is no code to decode.
  const TONES = TONES0_;
  // A RAIL WITH NOTHING ON IT still composes — a lit bar with a title under it — and argues nothing. That is
  // the silent-wrong-output this library's evidence guard exists to end, so it throws instead.
  if (!list.length) {
    throw new Error(
      'PortRail needs at least one `items` entry. The whole form is things seating onto one rail; ' +
      'with nothing to seat it draws a bare bar, which composes and argues nothing.');
  }
  const n = list.length;
  const U = Math.min(W, H);
  const yaw = YAW(frame);
  const band = H - captionBand(W, H);
  // A row needs a wide frame; anything squarer or taller stands the rail up instead.
  const vert = W / H < 1.25;
  const span = vert ? Math.min(2.6, 0.52 * n) : SPAN;
  // built here because it needs the resolved `span`, which depends on the aspect and the module count.
  const slots = gs.length ? groupSlots(seats.map((x) => x.g), span) : undefined;
  const pad = Math.round(U * 0.035);

  // THE COPY IS MEASURED BEFORE THE CAMERA IS CHOSEN, because the copy is one of the frame's walls.
  // Sized after the fact it has nowhere to go: the block was clamped up above the caption band, the rail was
  // already there, and the title printed across its own machined face. A title over the object is not a
  // near-miss to be nudged — it is the frame telling you the object was never given a smaller share of it.
  const titlePx = fitTextPx(STANDARD, W * 0.62, Math.round(U * 0.050), {usable: 1.0});
  const notePx = Math.round(U * 0.029);
  const copyH = Math.round(titlePx * 1.6) + (NOTE ? Math.round(notePx * 2.9) : 0);

  // ONE SIZE FOR EVERY LABEL — a first, conservative estimate of it, because the room a label really gets is
  // the module PITCH and the pitch is not known until the camera is. This pass only has to be big enough to
  // reserve honestly; the size is fitted again against the measured pitch once the frame is chosen, and can
  // only come down. Fitted per label instead, six tags print at five sizes.
  const labelW = vert ? Math.round(W * 0.30) : Math.round(Math.min(W * 0.22, (W * 0.86) / n));
  const labelBase = Math.round(U * 0.030);
  const labelH = Math.round(labelBase * 2.6);     // two lines plus leading — the room a label needs to exist
  const labelPx = list.reduce(
    (px, txt) => Math.min(px, fitBlockPx(txt, labelW, labelH, labelBase, {usable: 1.0, leading: 1.15})),
    labelBase);

  // WHAT THE FRAME MUST HOLD, as points, so the fit is asked of the projection rather than of a formula.
  // Both ends of the travel are included: fitted at the seated pose alone, the waiting modules are cut by
  // the top edge for the first third of the shot, which is the defect a still cannot see.
  const railHalf: Vec3 = vert ? [0.15, (span + 1.15) / 2, 0.43] : [(span + 1.15) / 2, 0.15, 0.43];
  const modHalf: Vec3 = [0.28, 0.21, 0.31];
  const posAt = (i: number, travel: number): Vec3 => vert
    ? [travel, slotAt(i, n, span, true, slots), 0]
    : [slotAt(i, n, span, false, slots), travel, 0];
  const seated: Vec3[] = boxCorners([0, 0, 0], railHalf);
  const moving: Vec3[] = [];
  for (let i = 0; i < n; i++) {
    seated.push(...boxCorners(posAt(i, 0.365), modHalf));
    moving.push(...boxCorners(posAt(i, LIFT), modHalf));
    // THE LABELS ARE PART OF THE OBJECT as far as framing is concerned. Left out, the fit centres the metal
    // alone and the column of type hangs off one side of a frame that is empty on the other — which is what
    // a square cut looked like: the rail pinned left, half the picture unused, the labels pointing into it.
    seated.push(vert
      ? [0.365 + 0.62, slotAt(i, n, span, true, slots), 0]
      : [slotAt(i, n, span, false, slots), 0.365 + 0.30, 0]);
  }
  // TWO CLAIMS ON THE FRAME, not one. The settled shot is what a viewer reads, so it clears the caption band,
  // the copy block and the row of labels. A module still on its way owes none of that — its label is not
  // drawn until it is nearly home — and only has to be on screen. Charged the settled reservations, the
  // travelling pose shrank the whole composition by a third to protect type that did not exist yet.
  const marginX = Math.round(W * 0.05);
  // The box stops where the LABEL's own room begins: its anchor is the left edge of a column upright, and the
  // BOTTOM of a two-line block when the rail lies down, so the room each needs is reserved on that side and
  // the anchor itself is what has to land inside.
  const labelRunPx = Math.min(labelW, Math.ceil(list.reduce(
    (w, txt) => Math.max(w, textWidthPx(txt, labelPx)), 0)));
  const settledBox = {
    left: marginX,
    right: W - marginX - (vert ? labelRunPx + pad : 0),
    top: CONTENT_TOP + (vert ? pad : labelH),
    bottom: band - pad - (copyH + pad),
  };
  // ON SCREEN, not inside the content zone. A module still descending owes the top zone nothing either: it
  // is passing through. Held to CONTENT_TOP it became the binding constraint and shrank the settled row by a
  // third — the shot was sized by where things START. The defect the lift was tuned against was different and
  // worse: modules PARKED half-cut by the top edge for the first third of the shot.
  const movingBox = {left: Math.round(W * 0.02), right: W - Math.round(W * 0.02),
                     top: Math.round(H * 0.012), bottom: band};
  const groups = [{pts: seated, box: settledBox}, {pts: moving, box: movingBox}];
  // Only the DIRECTION of these is a design decision now — the look-down angle the shot is composed at. How
  // far back the lens sits is solved against the box above, so the same view survives every aspect instead
  // of being a constant that happened to frame 16:9.
  const rest: Vec3 = vert ? [0.55, 0.55, 9.5] : CAM;
  const aim0: Vec3 = vert ? [0.55, -0.62, 0] : AIM;
  const dir: Vec3 = [rest[0] - aim0[0], rest[1] - aim0[1], rest[2] - aim0[2]];
  // A SLOW PUSH ACROSS THE WHOLE SHOT. The seating is staggered, so past the last module's window nothing in
  // the frame moved at all — a third of the shot was a photograph, and it read as one. A product shot answers
  // this the way a product shot always has: the lens keeps closing on the subject, so the frame is alive even
  // when the subject has stopped. The fit is solved for the TIGHTEST end of that move, so the closest frame
  // of the push is the one that was checked and every other frame has room to spare.
  const PUSH_IN = 0.97, PUSH_OUT = 1.07;
  const fitted = frameCamera(groups, aim0, dir, FOV, W, H, Math.hypot(dir[0], dir[1], dir[2]));
  const aim = fitted.aim;
  const base = fitted.dist / PUSH_IN;
  const push = lerp(PUSH_OUT, PUSH_IN, easeInOutCubic(t));
  const u = base * push / Math.hypot(dir[0], dir[1], dir[2]);
  const cam: Vec3 = [aim[0] + dir[0] * u, aim[1] + dir[1] * u, aim[2] + dir[2] * u];
  // every word placed off the projection moves for the whole beat: the lens closes in until the clock lands, and
  // the rail keeps its slow yaw (YAW is a sine of the raw frame) after that
  const lensMoves = true;
  const place = usePlaceGlide();
  const glide = useGlide();

  // THE LABEL IS SIZED TO THE PITCH IT ACTUALLY GETS, which is only knowable once the camera is chosen.
  //
  // A width picked from the frame is a guess about the row: at six modules `W * 0.86 / n` reserved 275px per
  // label while perspective gave each one 250px, so 'Shared calendars' and 'Internal knowledge base' printed
  // into each other — one register showing two neighbouring ideas as a single run of words. So the row is
  // measured after the fit: project two adjacent slots, take the gap between them, and fit every label into
  // that. The size can only come DOWN from the one the frame was reserved for, so the reservation stays
  // valid — a second pass that could grow the type would invalidate the box it was fitted against.
  const pitchPx = (() => {
    if (n < 2) return vert ? H : W;
    const a = project(posAt(0, 0.365), cam, aim, FOV, W, H);
    const b = project(posAt(1, 0.365), cam, aim, FOV, W, H);
    if (!a || !b) return vert ? H : W;
    return Math.abs(vert ? b.y - a.y : b.x - a.x);
  })();
  const labelBoxW = vert ? labelW : Math.max(Math.round(U * 0.06), Math.round(pitchPx - pad));
  const labelBoxH = vert ? Math.min(labelH, Math.max(labelBase, Math.round(pitchPx - pad * 0.5))) : labelH;
  const labelFitted = list.reduce(
    (px, txt) => Math.min(px, fitBlockPx(txt, labelBoxW, labelBoxH, labelPx, {usable: 1.0, leading: 1.15})),
    labelPx);

  // A label rides its own module, straight up. On a rail that direction is clear for every module at once,
  // and it is CLAMPED to the content zone: a projected label follows its object wherever perspective puts it,
  // and the band at the bottom is the one region of the frame a shot does not own.
  const labels = list.map((text, i) => {
    const s = seatAt(t, animSpan, fps, i, n);
    const travel = lerp(LIFT, 0.365, s);
    // Upright, a label sits ABOVE its module; on the standing rail it sits BESIDE it, because above is where
    // the next module in the stack is.
    const p = vert
      ? yawPoint([travel + 0.62, slotAt(i, n, span, true, slots), 0], yaw)
      : yawPoint([slotAt(i, n, span, false, slots), travel + 0.30, 0], yaw);
    const at = project(p, cam, aim, FOV, W, H);
    if (!at) return {text, i, s, at: null};
    return {text, i, s,
      at: {x: at.x, y: Math.min(Math.max(at.y, CONTENT_TOP + labelH), band - pad), depth: at.depth}};
  });

  // A GROUP'S NAME SITS UNDER ITS OWN CLUSTER. The gap already separates the runs; a name under each one
  // says which kind it is with nothing to decode, because it is in the same place as the thing it names —
  // which a swatch legend, sitting elsewhere and keyed by colour, is not.
  const groupTags = gs.length ? gs.map((g, gi) => {
    const mine = seats.map((x, i) => (x.g === gi ? i : -1)).filter((i) => i >= 0);
    if (!mine.length || !g.label) return null;
    const mid = mine.reduce((a, i) => a + slotAt(i, n, span, vert, slots), 0) / mine.length;
    const at = project(yawPoint(vert ? [-0.46, mid, 0] : [mid, -0.46, 0], yaw), cam, aim, FOV, W, H);
    return at ? {label: g.label, x: at.x, y: at.y} : null;
  }).filter(Boolean) as {label: string; x: number; y: number}[] : [];

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <ThreeCanvas width={W} height={H} camera={{position: cam, fov: FOV}} shadows
        style={{position: 'absolute', inset: 0}}>
        <Scene n={n} tones={TONES} toneOf={toneOf} slots={slots} accent={ACC} floor={dna?.bg ?? BG_D0} vert={vert} span={span} t={t}
          aim={aim} cam={cam} animSpan={animSpan} fps={fps} />
      </ThreeCanvas>

      {/* A label appears only once its module is most of the way home. Drawn from the first frame, the ones
          still waiting rode above the row and read as debris. */}
      {labels.map(({text, i, s, at}) => at ? (
        // placed by a TRANSLATE with the unlock while the lens closes in (runtime/glide.ts usePlaceGlide): a label
        // moved by `left`/`top` steps a whole pixel at a time against the module it names
        <div key={i} style={{position: 'absolute',
          ...place(lensMoves, at.x, at.y, vert ? 'translate(0, -50%)' : 'translate(-50%, -100%)'), width: labelBoxW,
          textAlign: vert ? 'left' : 'center', textWrap: 'balance',
          opacity: clamp01(s * 2.6 - 1.25), color: FG,
          font: `700 ${labelFitted}px/${leading(text, 1.15)} var(--f-body, system-ui, sans-serif)`,
          // the halo is the GROUND's own colour, not black. A black glow is invisible on a dark stage and a
          // grey smudge behind dark type on a paper one — the same declaration reading as craft in one film
          // and as a printing fault in the next.
          textShadow: `0 2px 14px ${HALO}`}}>{text}</div>
      ) : null)}

      {groupTags.map((g, i) => (
        <div key={'g' + i} style={{position: 'absolute',
          ...place(lensMoves, g.x, Math.min(g.y, band - Math.round(U * 0.03)), 'translate(-50%, -50%)'),
          textAlign: 'center', whiteSpace: 'nowrap',
          opacity: clamp01(seg(t, 0.50, 0.70)), color: DIM,
          font: `600 ${Math.round(notePx * 0.94)}px/1.25 var(--f-mono, "JetBrains Mono", monospace)`,
          letterSpacing: '0.04em', textShadow: `0 2px 12px ${HALO}`}}>{g.label}</div>
      ))}

      {/* THE NAME AND THE NOTE ARE STACKED FROM ONE MEASURED ANCHOR — the rail's own front-bottom edge,
          projected once — and clamped above the caption band. Placed independently they drifted into the
          same row the moment the camera aim moved, which is two pieces of copy on top of each other. */}
      {(() => {
        const rail = project(yawPoint(vert ? [0, -(span / 2) - 0.55, 0.43] : [0, -0.17, 0.43], yaw),
                             cam, aim, FOV, W, H);
        if (!rail) return null;
        const keyH = 0;   // the group names live on the rail now, under their own clusters
        const blockH = Math.round(titlePx * 1.6) + keyH + (NOTE ? Math.round(notePx * 1.5) : 0);
        const top = Math.min(rail.y + Math.round(U * 0.075), band - blockH - Math.round(U * 0.02));
        return (
          <>
            <div style={{position: 'absolute', left: 0, right: 0, top: 0, transform: glide(`translateY(${top}px)`, lensMoves),
              textAlign: 'center', color: FG,
              opacity: clamp01(seg(t, 0.02, 0.16)), textWrap: 'balance',
              padding: `0 ${Math.round(W * 0.14)}px`,
              font: `800 ${fitTextPx(STANDARD, W * 0.6, titlePx, {usable: 1.0})}px/${leading(STANDARD, 1.1)} var(--f-display, system-ui, sans-serif)`}}>
              {STANDARD}
            </div>

            {NOTE ? (
              <div style={{position: 'absolute', left: 0, right: 0, top: 0,
                transform: glide(`translateY(${top + Math.round(titlePx * 1.6) + keyH}px)`, lensMoves),
                textAlign: 'center', color: DIM, padding: `0 ${Math.round(W * 0.16)}px`, textWrap: 'balance',
                opacity: clamp01(seg(t, 0.66, 0.84)),
                font: `500 ${notePx}px/${leading(NOTE, 1.4)} var(--f-body, system-ui, sans-serif)`}}>
                {NOTE}
              </div>
            ) : null}
          </>
        );
      })()}
    </AbsoluteFill>
  );
};
export default PortRail;
