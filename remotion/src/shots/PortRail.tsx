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

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useDNA, dnaPalette} from '../runtime/dna';
import {project, yawPoint, type Vec3} from '../runtime/project3d';
import {AimCamera} from '../runtime/aimCamera';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useT, seg, clamp01, easeOutBack, easeInOutCubic, lerp} from '../runtime/motion';

export const DURATION = 165; // 5.5s

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
const slotAt = (i: number, n: number, span: number, vert = false) => {
  const s = n <= 1 ? 0 : (i / (n - 1) - 0.5) * span;
  return vert ? -s : s;
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
 *  home. Halving each window and lengthening the approach makes the same move decisive, and still leaves the
 *  last third of the shot at rest for the note. */
const seatAt = (t: number, i: number, n: number) =>
  easeOutBack(clamp01(seg(t, 0.08 + (i / Math.max(1, n)) * 0.52, 0.24 + (i / Math.max(1, n)) * 0.52)));

const Scene: React.FC<{n: number; tones: string[]; accent: string; floor: string; vert: boolean;
  span: number; t: number; aim: Vec3; cam: Vec3}> = ({n, tones, accent, floor, vert, span, t, aim, cam}) => {
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
          const s = seatAt(t, i, n);
          return (
            <group key={i} position={vert
              ? [lerp(LIFT, 0.365, s), slotAt(i, n, span, true), 0]
              : [slotAt(i, n, span), lerp(LIFT, 0.365, s), 0]}>
              {/* ONE MATERIAL FOR EVERY MODULE, so the row reads as a manufactured set. Six saturated hues
                  are what `dnaPalette` hands you and they are right for a diagram and wrong for an object:
                  a product photograph identifies its parts by a MARK, not by dyeing each one. */}
              <mesh castShadow receiveShadow>
                <boxGeometry args={[0.56, 0.42, 0.62]} />
                <meshStandardMaterial color={'#5d6889'} metalness={0.34} roughness={0.40} />
              </mesh>
              {/* the tone, a thin bar on the FRONT face. On a ring it sat on the outward face, which pointed
                  away from the lens for half the modules and left them unidentifiable. */}
              <mesh position={[0, -0.115, 0.312]}>
                <boxGeometry args={[0.34, 0.045, 0.008]} />
                <meshStandardMaterial color={tones[i % tones.length]} emissive={tones[i % tones.length]}
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

export const PortRail: React.FC<{standard?: string; items?: string[]; note?: string}> = ({
  standard: STANDARD = 'One standard', items: ITEMS = ['Docs', 'Chat', 'Mail', 'Calendar', 'Wiki', 'DB'],
  note: NOTE = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const TONES = dnaPalette(dna, 6) ?? TONES0;
  const list = ITEMS.filter((x) => String(x ?? '').trim()).slice(0, 6);
  // A RAIL WITH NOTHING ON IT still composes — a lit bar with a title under it — and argues nothing. That is
  // the silent-wrong-output this library's evidence guard exists to end, so it throws instead.
  if (!list.length) {
    throw new Error(
      'PortRail needs at least one non-empty `items` entry. The whole form is things seating onto one rail; ' +
      'with nothing to seat it draws a bare bar, which composes and argues nothing.');
  }
  const n = list.length;
  const U = Math.min(W, H);
  const yaw = YAW(frame);
  const band = H - captionBand(W, H);
  // A row needs a wide frame; anything squarer or taller stands the rail up instead.
  const vert = W / H < 1.25;
  // SIZED FROM THE CAMERA MATHS, not by eye. A 34 degree vertical fov shows 2*d*tan(17 deg) of world height,
  // so a six-module stack 3.0 units tall wants a lens about 9.5 units back to sit at half the frame — the
  // first guess put it at 6.15 and ran three modules and their labels off the bottom edge. The aim sits
  // BELOW the stack's centre, which lifts the stack in frame and leaves the lower third for the copy.
  const span = vert ? Math.min(2.6, 0.52 * n) : SPAN;
  const aim: Vec3 = vert ? [0.55, -0.62, 0] : AIM;
  // A SLOW PUSH ACROSS THE WHOLE SHOT. The seating is staggered, so past the last module's window nothing in
  // the frame moved at all — a third of the shot was a photograph, and it read as one. A product shot answers
  // this the way a product shot always has: the lens keeps closing on the subject, so the frame is alive even
  // when the subject has stopped. It is one continuous eased move, never a lurch, and the camera the labels
  // are projected from is this same moving camera, so the type stays welded to the metal.
  const rest: Vec3 = vert ? [0.55, 0.55, 9.5] : CAM;
  // The move is centred on the framing the shot was composed at rather than added in front of it: a push that
  // only ever backs OFF spends most of its frames wider than the composition, and the measured ink fell for
  // it. This opens a little wide and closes a little tight, so the average is the frame that was designed.
  const push = lerp(1.07, 0.97, easeInOutCubic(t));
  const cam: Vec3 = [aim[0] + (rest[0] - aim[0]) * push,
                     aim[1] + (rest[1] - aim[1]) * push,
                     aim[2] + (rest[2] - aim[2]) * push];

  // A label rides its own module, straight up. On a rail that direction is clear for every module at once,
  // and it is CLAMPED to the content zone: a projected label follows its object wherever perspective puts it,
  // and the band at the bottom is the one region of the frame a shot does not own.
  const pad = Math.round(U * 0.035);
  const labels = list.map((text, i) => {
    const s = seatAt(t, i, n);
    const travel = lerp(LIFT, 0.365, s);
    // Upright, a label sits ABOVE its module; on the standing rail it sits BESIDE it, because above is where
    // the next module in the stack is.
    const p = vert
      ? yawPoint([travel + 0.62, slotAt(i, n, span, true), 0], yaw)
      : yawPoint([slotAt(i, n, span), travel + 0.52, 0], yaw);
    const at = project(p, cam, aim, FOV, W, H);
    if (!at) return {text, i, s, at: null};
    return {text, i, s,
      at: {x: at.x, y: Math.min(Math.max(at.y, CONTENT_TOP + pad), band - pad), depth: at.depth}};
  });

  const titlePx = Math.round(U * 0.050);
  const notePx = Math.round(U * 0.029);

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <ThreeCanvas width={W} height={H} camera={{position: cam, fov: FOV}} shadows
        style={{position: 'absolute', inset: 0}}>
        <Scene n={n} tones={TONES} accent={ACC} floor={dna?.bg ?? BG_D0} vert={vert} span={span} t={t}
          aim={aim} cam={cam} />
      </ThreeCanvas>

      {/* A label appears only once its module is most of the way home. Drawn from the first frame, the ones
          still waiting rode above the row and read as debris. */}
      {labels.map(({text, i, s, at}) => at ? (
        <div key={i} style={{position: 'absolute', left: at.x, top: at.y, width: Math.round(W * 0.15),
          transform: vert ? 'translate(0, -50%)' : 'translate(-50%, -100%)',
          textAlign: vert ? 'left' : 'center', textWrap: 'balance',
          opacity: clamp01(s * 2.6 - 1.25), color: FG,
          font: `700 ${Math.round(U * 0.030)}px/${leading(text, 1.15)} var(--f-body, system-ui, sans-serif)`,
          textShadow: '0 2px 14px #000c'}}>{text}</div>
      ) : null)}

      {/* THE NAME AND THE NOTE ARE STACKED FROM ONE MEASURED ANCHOR — the rail's own front-bottom edge,
          projected once — and clamped above the caption band. Placed independently they drifted into the
          same row the moment the camera aim moved, which is two pieces of copy on top of each other. */}
      {(() => {
        const rail = project(yawPoint(vert ? [0, -(span / 2) - 0.55, 0.43] : [0, -0.17, 0.43], yaw),
                             cam, aim, FOV, W, H);
        if (!rail) return null;
        const blockH = Math.round(titlePx * 1.6) + (NOTE ? Math.round(notePx * 1.5) : 0);
        const top = Math.min(rail.y + Math.round(U * 0.075), band - blockH - Math.round(U * 0.02));
        return (
          <>
            <div style={{position: 'absolute', left: 0, right: 0, top, textAlign: 'center', color: FG,
              opacity: clamp01(seg(t, 0.02, 0.16)), textWrap: 'balance',
              padding: `0 ${Math.round(W * 0.14)}px`,
              font: `800 ${fitTextPx(STANDARD, W * 0.6, titlePx, {usable: 1.0})}px/${leading(STANDARD, 1.1)} var(--f-display, system-ui, sans-serif)`}}>
              {STANDARD}
            </div>
            {NOTE ? (
              <div style={{position: 'absolute', left: 0, right: 0, top: top + Math.round(titlePx * 1.6),
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
