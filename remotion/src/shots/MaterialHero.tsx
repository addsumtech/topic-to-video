// SHOT · Material Hero — the premium product-reveal language, with the film's OWN claim as the object: the
// parts arrive from outside the frame and close into ONE turned ring under a sweeping rake-light. Genuine
// WebGL — real lights, real shadows, real occlusion — which is the edge the flat HTML tier structurally
// cannot make.
//
// WHY IT WAS REBUILT, because the previous version is the reason a viewer said they had never seen the 3D
// work. It drew a TORUS KNOT and took a single `title` prop. Nothing about the shape could be affected by
// anything the film said — there was no prop that could have changed it — so it was a beautiful blob with a
// headline laid over the top, in a library whose first rule is that a visual must ENCODE the frame's
// content. It rendered perfectly and argued nothing, which is the worst of both: the expense of WebGL and
// the meaning of a stock image.
//
// So the geometry now comes from `items`. Each part is an arc of one ring, they fly in on their own axes and
// seat into a closed circle, and the claim the form makes is "many pieces, ONE thing". That claim is
// falsifiable, which is the point: give it five parts and the ring closes with five arcs; the form cannot
// say something the props do not.
//
// WHY THE TYPE IS NOT IN THE SCENE. A CJK glyph baked onto a texture is mush at render scale and takes the
// surface's lighting, so the copy would DIM every time its arc turned away from the key. Every label here is
// an ordinary DOM element placed by `runtime/project3d` at its arc's screen position: crisp type in the
// film's own face, anchored to a real object, and still visible to the text-safety and CJK gates, which
// cannot see inside a canvas.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useDNA, dnaPalette} from '../runtime/dna';
import {project, yawPoint, type Vec3} from '../runtime/project3d';
import {AimCamera} from '../runtime/aimCamera';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useT, seg, clamp01, easeOutCubic, easeOutBack, lerp} from '../runtime/motion';

export const DURATION = 150; // 5s

const BG_D0 = 'radial-gradient(120% 120% at 50% 42%, #10131d, #05070c 72%)';
const FG_D0 = '#f2f5fb', DIM_D0 = '#8b93a8', ACC_D0 = '#5B8CFF';
const TONES0 = ['#5b8cff', '#37d4a6', '#f6a531', '#c07bff', '#ff6f91', '#4dd0e1'];

// The stage, in world units. The camera and every label read these, so the frame composes from ONE geometry.
const RING_R = 1.24;        // the closed ring's radius
// THICK ENOUGH TO BE AN OBJECT. The rebuild took the frame from 29.5% ink to 8.0%: the torus knot it
// replaced was a fat blob that meant nothing, but a hero beat that under-fills its frame is the
// other failure this library keeps meeting. The ring is sized to OWN the zone it is given.
const TUBE = 0.235;         // how thick each arc is
// LOOK DOWN ON IT. At a shallow angle a ring has the same defect a ring of objects has, and I walked
// into it twice: the near arc is huge and low, crossing the copy block, while the far arc is a
// sliver. Seen from above the circle reads as a circle, every arc is the same size, and the labels
// can sit around it evenly instead of being flung to the frame corners.
const CAM0: Vec3 = [0, 3.95, 3.48];
// aimed at the ring itself; the object is lifted in world space instead, which keeps the lower
// third of the frame clear for the copy without tilting the lens off the subject.
const AIM: Vec3 = [0, 0.58, 0];
const RING_Y = 0.58;   // the ring's height, so the frame's lower third stays free
const FOV = 32;

// THE LENS BACKS OFF UNTIL THE RING FITS THE FRAME IT WAS GIVEN. A circle has the same width whatever the
// aspect, so a camera framed on 16:9 runs it straight off both edges of a 9:16 cut — two arcs sliced away and
// their labels pointing at nothing. The distance is therefore SOLVED, not tuned: a vertical fov of `FOV`
// shows `2*d*tan(FOV/2) * (W/H)` of world width, so `d` is whatever makes that at least the ring's diameter
// plus a margin. The direction is untouched, so every aspect gets the same look-down-on-it view, just framed.
const OUTER = RING_R + TUBE;
const camAt = (W: number, H: number): Vec3 => {
  const tanW = Math.tan((FOV * Math.PI) / 360) * (W / H);
  const back: Vec3 = [CAM0[0] - AIM[0], CAM0[1] - AIM[1], CAM0[2] - AIM[2]];
  const base = Math.hypot(back[0], back[1], back[2]);
  const k = Math.max(1, (OUTER * 1.16) / tanW / base);
  return [AIM[0] + back[0] * k, AIM[1] + back[1] * k, AIM[2] + back[2] * k];
};
/** How many pixels one world unit spans across the frame at the ring's own depth — used to size the copy
 *  that lives in the ring's HOLE, which is a hole in the OBJECT and so scales with the object, not the frame. */
const pxPerUnit = (W: number, H: number) => {
  const tanW = Math.tan((FOV * Math.PI) / 360) * (W / H);
  const cam = camAt(W, H);
  const d = Math.hypot(cam[0] - AIM[0], cam[1] - AIM[1], cam[2] - AIM[2]);
  return W / 2 / (d * tanW);
};
const YAW = (frame: number) => Math.sin(frame * 0.0075) * 0.20;   // a slow settle, not a turntable spin

/** Each arc's arrival, staggered so the eye can follow one piece at a time. */
const seatAt = (t: number, i: number, n: number) =>
  easeOutBack(clamp01(seg(t, 0.10 + (i / Math.max(1, n)) * 0.40, 0.40 + (i / Math.max(1, n)) * 0.40)));

/** The angle at the CENTRE of arc `i` — where its label belongs, and where it flies in from. */
const arcMid = (i: number, n: number) => -Math.PI / 2 + ((i + 0.5) / n) * Math.PI * 2;

const Scene: React.FC<{n: number; tones: string[]; t: number}> = ({n, tones, t}) => {
  const frame = useCurrentFrame();
  const gap = 0.055;                                   // a hair of air between arcs, so the parts stay parts
  return (
    <>
      {/* r3f aims a camera it made at the world origin; every label here is placed from AIM. Without this the
          two cameras disagree by the aim offset and the whole label ring rides above its own arcs. */}
      <AimCamera at={AIM} />
      {/* A key that carves the form, a cool fill so the shadow side is not black, and a warm rake that
          sweeps — the rake is what makes a turned metal surface read as turned rather than as flat shading. */}
      <ambientLight intensity={0.52} />
      <hemisphereLight args={['#93a9d6', '#0a0d14', 0.78]} />
      <directionalLight position={[4.2, 6.4, 5.0]} intensity={2.2} castShadow
        shadow-mapSize-width={2048} shadow-mapSize-height={2048}
        shadow-camera-left={-4} shadow-camera-right={4} shadow-camera-top={4} shadow-camera-bottom={-4} />
      <directionalLight position={[-5.2, 2.0, 2.2]} intensity={0.8} color={'#cfe0ff'} />
      <pointLight position={[Math.sin(frame * 0.03) * 6, -0.6, 3.2]} color={'#ffd0a0'} intensity={4.2} />

      <group rotation={[0, YAW(frame), 0]} position={[0, RING_Y, 0]}>
        {Array.from({length: n}).map((_, i) => {
          const s = seatAt(t, i, n);
          const mid = arcMid(i, n);
          const span = (Math.PI * 2) / n - gap;
          // Each arc flies in ALONG ITS OWN RADIUS, so the closing is read as parts meeting, not as a spin.
          const r = lerp(RING_R + 2.6, RING_R, s);
          return (
            <group key={i} position={[0, 0, 0]} rotation={[0, 0, 0]}>
              <mesh castShadow receiveShadow
                position={[Math.cos(mid) * (r - RING_R), 0, Math.sin(mid) * (r - RING_R)]}
                rotation={[-Math.PI / 2, 0, -mid + span / 2]}>
                {/* a torus SEGMENT: the ring is not one solid, it is these parts and nothing else */}
                <torusGeometry args={[RING_R, TUBE, 20, 64, span]} />
                {/* ONE MATERIAL FOR EVERY ARC. Six saturated hues turn a turned-metal hero into a pie chart:
                    a product photograph identifies its parts by a MARK, never by dyeing each one. (The same
                    wrong instinct had to be corrected on the rail shot — worth naming, because `dnaPalette`
                    hands you six maximally-different hues and they are the right answer for a diagram and
                    the wrong one for an object.) The tone survives as a thin inlay, which is enough to tell
                    the parts apart and keeps the ring manufactured. */}
                <meshStandardMaterial color={'#5d657f'} metalness={0.68} roughness={0.22} />
              </mesh>
              {/* the tone, as an inlay band riding the arc's outer face */}
              <mesh position={[Math.cos(mid) * (r - RING_R), 0, Math.sin(mid) * (r - RING_R)]}
                rotation={[-Math.PI / 2, 0, -mid + span * 0.5]}>
                <torusGeometry args={[RING_R, TUBE * 1.05, 10, 64, span * 0.11]} />
                <meshStandardMaterial color={tones[i % tones.length]} emissive={tones[i % tones.length]}
                  emissiveIntensity={0.45 + 0.45 * s} roughness={0.45} />
              </mesh>
            </group>
          );
        })}

        {/* the stage floor exists to CATCH the shadow — without it the ring floats and the depth dies. Its
            colour is the ground's own, so its rim is never a visible arc across the frame. */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.70, 0]} receiveShadow>
          <circleGeometry args={[7, 64]} />
          <meshStandardMaterial color={'#0b0e16'} metalness={0.1} roughness={0.95} />
        </mesh>
      </group>
    </>
  );
};

export const MaterialHero: React.FC<{title?: string; items?: string[]; note?: string}> = ({
  title: TITLE = 'One tool. Your whole team.',
  items: ITEMS = ['Docs', 'Chat', 'Tasks', 'Code', 'Data', 'Calls'], note: NOTE = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const TONES = dnaPalette(dna, 6) ?? TONES0;
  const list = ITEMS.filter((x) => String(x ?? '').trim()).slice(0, 6);
  // THE RING IS THE PARTS. With none it would close into a plain torus and quietly become the decorative
  // blob this rebuild exists to remove — a frame that composes beautifully and argues nothing.
  if (!list.length) {
    throw new Error(
      'MaterialHero needs at least one non-empty `items` entry. The hero object IS the parts closing into ' +
      'one ring; with nothing to close it draws a plain torus, which is the stock 3D blob this register was ' +
      'rebuilt to stop being.');
  }
  const n = list.length;
  const U = Math.min(W, H);
  const yaw = YAW(frame);
  const CAM = camAt(W, H);

  // A LABEL IS PUSHED OUT IN SCREEN SPACE, NOT IN WORLD SPACE.
  //
  // Offsetting along the ring's own radius looks right in the model and is wrong in the frame: seen from
  // above, perspective foreshortens the near arcs far more than the far ones, so the same world-space push
  // threw the bottom labels a long way from their metal and one of them clean off the frame. Projecting the
  // arc AND the ring's centre, then pushing along the 2D vector between them by a fixed number of PIXELS,
  // gives every label the same visual gap from its own arc whatever the camera is doing.
  //
  // THE GAP IS MEASURED FROM THE ARC'S SILHOUETTE, NOT FROM ITS CENTRELINE. A fixed push off the centreline
  // gives the same gap only where the tube is the same size on screen, and on a ring seen from above it is
  // not: the near arcs are both closer AND turned broadside, so the bottom labels came out printed on their
  // own metal while the far ones floated. So the tube's cross-section is sampled, projected, and the label
  // starts where the metal actually ENDS in this frame — which needs no per-camera tuning to stay true.
  const hub = project([0, RING_Y, 0], CAM, AIM, FOV, W, H);
  const GAP_PX = Math.round(Math.min(W, H) * 0.030);
  const RIM = 16;
  const labels = list.map((text, i) => {
    const s = seatAt(t, i, n);
    const mid = arcMid(i, n);
    const r = lerp(RING_R + 2.6, RING_R, s);
    const at = project(yawPoint([Math.cos(mid) * r, RING_Y, Math.sin(mid) * r], yaw), CAM, AIM, FOV, W, H);
    if (!at || !hub) return {text, i, s, at: null};
    const dx = at.x - hub.x, dy = at.y - hub.y;
    const len = Math.hypot(dx, dy) || 1;
    let reach = len;
    for (let k = 0; k < RIM; k++) {
      const a = (k / RIM) * Math.PI * 2;
      const rr = r + Math.cos(a) * TUBE;
      const rim = project(yawPoint([Math.cos(mid) * rr, RING_Y + Math.sin(a) * TUBE, Math.sin(mid) * rr], yaw),
                          CAM, AIM, FOV, W, H);
      if (rim) reach = Math.max(reach, ((rim.x - hub.x) * dx + (rim.y - hub.y) * dy) / len);
    }
    const OUT_PX = reach - len + GAP_PX;
    // ...AND KEPT INSIDE THE ZONE IT IS ALLOWED. A projected label follows its object wherever perspective
    // puts it, and the arcs nearest the lens sit low: two of six landed under the burned subtitle, which is
    // the one region of the frame a shot does not own. Clamped, a label can be crowded but never hidden.
    const pad = Math.round(Math.min(W, H) * 0.035);
    const x = Math.min(Math.max(at.x + (dx / len) * OUT_PX, Math.round(W * 0.09)), Math.round(W * 0.91));
    const y = Math.min(Math.max(at.y + (dy / len) * OUT_PX, CONTENT_TOP + pad),
                       H - captionBand(W, H) - pad);
    return {text, i, s, at: {x, y, depth: at.depth}};
  });

  // THE COPY GOES IN THE RING'S HOLE, which is the whole reason this composition works.
  //
  // Three cuts were spent moving the camera to stop the title crossing the near arc, and it never converged:
  // a copy block anchored to the bottom of the frame and a ring centred in it will always fight, because
  // the ring's nearest arc IS the bottom of the object. The hole was dead space I kept steering around. Put
  // the name of the whole thing at the centre of its parts and the collision cannot happen — and the frame
  // stops being an object with a caption under it and becomes one composition.
  const centre = project([0, RING_Y, 0], CAM, AIM, FOV, W, H);
  // the copy is fitted to the HOLE's real width in this frame, not to a fraction of the frame: at 9:16 a
  // frame-relative box shrank the name of the whole thing to a caption while the hole beside it sat empty.
  const holeW = (RING_R - TUBE) * 2 * pxPerUnit(W, H);
  const titlePx = fitTextPx(TITLE, holeW * 0.74, Math.round(U * 0.044), {usable: 1.0});
  const notePx = Math.round(U * 0.024);
  const band = H - captionBand(W, H);

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <ThreeCanvas width={W} height={H} camera={{position: CAM, fov: FOV}} shadows
        style={{position: 'absolute', inset: 0}}>
        <Scene n={n} tones={TONES} t={t} />
      </ThreeCanvas>

      {/* A label appears only once its arc is nearly home; drawn from frame one they ride outside the frame
          and read as debris. */}
      {labels.map(({text, i, s, at}) => at ? (
        <div key={i} style={{position: 'absolute', left: at.x, top: at.y, width: Math.round(W * 0.15),
          transform: 'translate(-50%, -50%)', textAlign: 'center', textWrap: 'balance',
          opacity: clamp01(s * 2.6 - 1.3), color: FG,
          font: `700 ${Math.round(U * 0.027)}px/${leading(text, 1.15)} var(--f-body, system-ui, sans-serif)`,
          textShadow: '0 2px 14px #000b'}}>{text}</div>
      ) : null)}

      {centre ? (
        <div style={{position: 'absolute', left: centre.x, top: Math.min(centre.y, band - Math.round(U * 0.06)),
          transform: 'translate(-50%, -50%)', width: Math.round(W * 0.34), textAlign: 'center',
          textWrap: 'balance', color: FG, opacity: clamp01(seg(t, 0.55, 0.75)),
          font: `800 ${titlePx}px/${leading(TITLE, 1.12)} var(--f-display, Inter,system-ui,sans-serif)`,
          letterSpacing: '-0.02em'}}>
          {TITLE}
          {NOTE ? (
            <div style={{marginTop: Math.round(U * 0.018), color: DIM, letterSpacing: 0,
              opacity: clamp01(seg(t, 0.74, 0.90)),
              font: `500 ${notePx}px/${leading(NOTE, 1.4)} var(--f-body, system-ui, sans-serif)`}}>{NOTE}</div>
          ) : null}
        </div>
      ) : null}

    </AbsoluteFill>
  );
};
export default MaterialHero;
