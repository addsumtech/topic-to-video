// SHOT · SpatialSlides — an argument that is a JOURNEY through places, not a list of them.
//
// Each step is posed somewhere in 3D and the camera FLIES TO ALIGN with it by inverting that pose, then
// pulls back so the whole route reads as one space. That is the peer library's `basic-3d-scene` formula —
// `camera = stepTransform.inverse()` — and the reason it is worth having is in the measurement this repo
// made of its own library on 2026-09-05: `rotateX` appeared in TWO of 152 registers. Our camera had push
// and pull and no SPACE, so paging through an argument could never be travel through it.
//
// TYPE DOES NOT RIDE THE Z PLANE. `runtime/depth` measured what happens when it does: glyph edge strength
// 91 flat, 56 under `perspective + translateZ` — a 38% loss that is plainly fuzzy, because a 3D-composited
// layer is rasterized once at layout size and upscaled. So the stage carries SURFACES and every word is an
// ordinary 2D element positioned over them by `projectPose`, crisp and visible to every type gate. The
// surfaces are numbered and toned; the words are flat.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {Stage3D, Surface, OnSurface, projectPose, planeAffine, fitStage, faceShade, PERSP_FRAC, type Pose} from '../runtime/stage3d';

export const DURATION = 180; // 6s

/** The route, as poses. Deterministic and hand-set rather than random: a journey whose stops move every
 *  render is not a place. The spread is in stage px and scales with the frame below. */
const ROUTE: Pose[] = [
  {x: -0.30, y: -0.16, z: 0.10, rx: 8, ry: 22, rz: -3},
  {x: 0.26, y: -0.20, z: -0.22, rx: -10, ry: -26, rz: 4},
  {x: -0.22, y: 0.20, z: -0.05, rx: 14, ry: 18, rz: -5},
  {x: 0.30, y: 0.16, z: 0.18, rx: -6, ry: -20, rz: 3},
  {x: 0, y: 0, z: -0.34, rx: 4, ry: 6, rz: 0},
];

export const SpatialSlides: React.FC<{steps?: string[]; notes?: string[]; overview?: string}> = ({
  steps: STEPS = ['Collect', 'Plan', 'Act', 'Verify', 'Deliver'], notes: NOTES = [], overview: OVER = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const P = Math.round(U * PERSP_FRAC);

  // A STEP WITH NO WORD IS NOT A PLACE. The route is as long as the copy the film supplied, capped at what
  // the poses describe — a sixth stop would have to be invented, and an invented stop is furniture.
  const list = STEPS.map((s) => String(s ?? '').trim()).filter(Boolean).slice(0, ROUTE.length);
  if (!list.length) {
    throw new Error(
      'SpatialSlides needs at least one non-empty `steps` entry. The whole form is a camera travelling ' +
      'between places; with no places it draws an empty room, which composes and argues nothing.');
  }
  const n = list.length;
  // stage px — the route is written in frame fractions so it reflows, and depth scales with the short side
  const poses: Pose[] = ROUTE.slice(0, n).map((p) => ({
    // @fallback: an omitted pose coordinate is the origin of the space: a camera position, not a reading about a slide
    ...p, x: (p.x ?? 0) * W, y: (p.y ?? 0) * H, z: (p.z ?? 0) * U,
  }));

  const cardW = Math.round(U * 0.30), cardH = Math.round(U * 0.19);

  // THE TOUR. Each stop holds, then the camera swings to the next; the last quarter pulls back to the
  // overview. `useT` freezes under reduced motion like every other clock here, so the still is a stop.
  const TOUR_END = 0.78;
  const leg = clamp01(t / TOUR_END) * (n - 1);
  const i = Math.min(n - 2, Math.floor(leg));
  const f = n > 1 ? easeInOutCubic(clamp01(leg - i)) : 1;
  const at = (k: keyof Pose, a: Pose, b: Pose) => lerp((a[k] ?? 0) as number, (b[k] ?? 0) as number, f);
  const a = poses[Math.min(i, n - 1)], b = poses[Math.min(i + 1, n - 1)];
  // ALIGNING WITH A CARD IS BECOMING ITS POSE. The camera IS the step's transform; Stage3D applies the
  // inverse, so the world swings round until that card is square to the lens.
  const tour: Pose = {x: at('x', a, b), y: at('y', a, b), z: at('z', a, b) + U * 0.58,
    rx: at('rx', a, b), ry: at('ry', a, b), rz: at('rz', a, b)};

  // THE OVERVIEW IS FITTED, NOT GUESSED. The box is the shot's own — the caption band is not in it — so
  // "does the route fit" and "does a card sit on the subtitle" are one question with one answer.
  // `runtime/fitCamera` records why this is a bisection on the projection and not a closed form.
  const pad = Math.round(Math.hypot(cardW, cardH) / 2);   // a card's half-diagonal, in stage units
  const box = {left: U * 0.04, top: CONTENT_TOP, right: W - U * 0.04, bottom: contentBottom(W, H)};
  const wide = fitStage(poses, {rx: 6, ry: -4}, box, P, W, H, {radius: pad}).cam;

  const out = easeOutCubic(clamp01(seg(t, TOUR_END, 0.94)));
  const cam: Pose = {
    // @fallback: an omitted pose coordinate is the origin of the space: a camera position, not a reading about a slide
    x: lerp(tour.x ?? 0, wide.x ?? 0, out), y: lerp(tour.y ?? 0, wide.y ?? 0, out),
    z: lerp(tour.z ?? 0, wide.z ?? 0, out), rx: lerp(tour.rx ?? 0, wide.rx ?? 0, out),
    ry: lerp(tour.ry ?? 0, wide.ry ?? 0, out), rz: lerp(tour.rz ?? 0, wide.rz ?? 0, out),
  };

  const INK = dna?.fg ?? '#e9eef7';
  const DIM = dna?.dim ?? '#8d99ad';
  const ACC = dna?.accent ?? '#5b8cff';
  const SURF = dna?.surface ?? '#141a26';
  const LINE = dna?.surfaceBorder ?? '#2a3446';

  const labelPx = list.reduce(
    (px, s) => Math.min(px, fitTextPx(s, cardW * 0.92, Math.round(U * 0.042), {usable: 1})),
    Math.round(U * 0.042));
  const notePx = Math.round(U * 0.021);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(130% 120% at 50% 12%, #131a28, #070a11 72%)'}}>
      <Stage3D cam={cam} persp={P}>
        {poses.map((p, k) => {
          const lit = faceShade(p, cam);
          const here = out < 0.5 && Math.abs(leg - k) < 0.5;
          return (
            <Surface key={k} pose={p} w={cardW} h={cardH}
              style={{background: SURF, border: `${Math.max(1, Math.round(U * 0.0016))}px solid ${here ? ACC : LINE}`,
                borderRadius: Math.round(U * 0.014), opacity: 0.35 + 0.65 * lit,
                boxShadow: `0 ${Math.round(U * 0.02)}px ${Math.round(U * 0.05)}px rgba(0,0,0,.45)`}}>
              {/* the card's own surface furniture — shapes only, never words */}
              {/* THE MIDDLE OF THE CARD BELONGS TO THE WORD. The first version put the rules at 52/66/80%
                  and the flat label is centred at 50%, so every card had a line drawn through its own name.
                  A surface's furniture goes above and below the type it carries, never behind it. */}
              <div style={{position: 'absolute', left: '8%', top: '13%', width: '34%', height: 3,
                background: here ? ACC : LINE, opacity: 0.9}} />
              {[0, 1].map((r) => (
                <div key={r} style={{position: 'absolute', left: '8%', top: `${76 + r * 11}%`,
                  width: `${38 + hash01(k * 3 + r) * 34}%`, height: 2, background: LINE, opacity: 0.7}} />
              ))}
            </Surface>
          );
        })}
      </Stage3D>

      {/* THE WORDS LIE ON THEIR CARD. They were placed at the card's projected centre with one uniform scale,
          so they could move and grow but never turn — an audit of every 3D register, prompted by a viewer
          catching the same thing on TermSpace, found each card's own rules tilting while its title stayed
          level. Still outside the posed surface and still a 2D transform, so still crisp. */}
      {poses.map((p, k) => {
        const q = projectPose(p, cam, P, W, H);
        if (q.behind || q.k <= 0.02) return null;
        const near = out < 0.5 ? clamp01(1.15 - Math.abs(leg - k)) : 1;
        const px = labelPx;
        const lw = cardW * 0.92;
        const lblock = inkBlockH(px) * (NOTES[k] ? 2.2 : 1);
        const aff = planeAffine(p, cam, P, W, H, -lw / 2, -inkBlockH(px) / 2, lw, lblock);
        if (!aff) return null;
        const w = lw * aff.scale;
        // A WORD GOES WITH ITS CARD. When the camera has travelled past a stop the card leaves frame, and a
        // label that stays is text cut by the canvas in every gate and unreadable to a viewer besides. The
        // same test keeps it out of the caption band, which is the other edge a projected position can wander
        // across: the stage may put a surface anywhere, so the TYPE is what gets bounded.
        const half = w / 2, deep = (lblock * aff.scale) / 2;
        if (q.x - half < 0 || q.x + half > W) return null;
        if (q.y - deep < CONTENT_TOP * 0.4 || q.y + deep > contentBottom(W, H)) return null;
        return (
          <OnSurface key={k} pose={p} cam={cam} persp={P} W={W} H={H}
            left={-lw / 2} top={-inkBlockH(px) / 2} width={lw} height={lblock} affine={aff}
            style={{textAlign: 'center', opacity: 0.25 + 0.75 * near,
            color: INK, font: `700 ${px.toFixed(1)}px/${leading(list[k], 1.08)} var(--f-display, Inter, system-ui, sans-serif)`,
            textWrap: 'balance', textShadow: '0 2px 10px rgba(0,0,0,.55)'}}>
            {list[k]}
            {NOTES[k] ? (
              <div style={{marginTop: Math.round(px * 0.32), color: DIM,
                font: `500 ${notePx.toFixed(1)}px/${leading(String(NOTES[k]), 1.25)} var(--f-body, Inter, system-ui, sans-serif)`}}>
                {NOTES[k]}
              </div>
            ) : null}
          </OnSurface>
        );
      })}

      {/* the closing line, drawn only when the film supplied one */}
      {OVER ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: CONTENT_TOP - Math.round(U * 0.055),
          textAlign: 'center', color: DIM, opacity: easeOutCubic(clamp01(seg(t, 0.82, 0.96))),
          font: `600 ${Math.round(U * 0.026)}px/${leading(OVER, 1.2)} var(--f-mono, "JetBrains Mono", monospace)`,
          letterSpacing: '0.14em'}}>{OVER}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default SpatialSlides;
