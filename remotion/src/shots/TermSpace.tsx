// SHOT · TermSpace — several consoles, all running, in ONE room.
//
// A 2x2 grid of terminals says "here are four things" and makes them peers on one plane. This poses them in
// space and flies the camera to each in turn, so what the beat says is that they COEXIST and you are moving
// among them. That is the peer library's `terminal-3d`, the last of its 3D line this tier had no answer to
// (`basic-3d-scene` became SpatialSlides, `flying-words` became WordTunnel), and it is the same one formula:
// to visit a screen you hand its own pose in as the camera and the world swings round to face you.
//
// WHY IT IS NOT SpatialSlides WITH A CONSOLE SKIN. A card on a stage is a place; a console is a thing that is
// RUNNING. The screen the camera is facing types its status out under a live caret, and the ones it has left
// hold theirs settled behind a status glyph — so the travel is not a tour of labels, it is arriving at the
// one machine that is still working. Take the console idiom away and the beat stops being about simultaneity.
//
// TYPE DOES NOT RIDE THE Z PLANE. `runtime/depth` measured it on this renderer: glyph edge strength 91 flat,
// 56 under `perspective + translateZ` — a 38% loss, because a 3D-composited layer is rasterized once at
// layout size and upscaled. So the stage carries the SCREENS and every word is an ordinary 2D element put
// over them by `projectPose`: crisp, in the film's own face, and visible to every type gate.
//
// EVERY SCREEN'S WORDS ARE ON FRAME WHEN IT SETTLES, which is a requirement and not a nicety. `WordTunnel`
// shipped with its final phrase culled for width and `text_safe_qa` reported 0 findings at all five aspects,
// because type that is never drawn is never cut off. The close pulls back to a camera `fitStage` has fitted
// to ALL the screens inside the shot's own content box, so the frame the gates sample carries every string
// this register was given.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {Stage3D, Surface, projectPose, fitStage, faceShade, PERSP_FRAC, type Pose} from '../runtime/stage3d';

export const DURATION = 190; // ~6.3s

/** Where the screens stand. Hand-set and deterministic: a room whose walls move every render is not a room.
 *  x/y/z are fractions of the frame's short side, scaled below; ry turns each screen to face the middle. */
const ROOM: Pose[] = [
  {x: -0.34, y: -0.10, z: 0.06, rx: 4, ry: 26},
  {x: 0.33, y: -0.14, z: -0.16, rx: -3, ry: -24},
  {x: -0.26, y: 0.22, z: -0.30, rx: 9, ry: 18},
  {x: 0.30, y: 0.18, z: 0.12, rx: -7, ry: -20},
];

type Screen = {name?: string; status?: string};

export const TermSpace: React.FC<{screens?: Screen[]; summary?: string}> = ({
  screens: SCREENS = [{name: 'ingest', status: 'reading the authorised directory'},
                      {name: 'plan', status: 'ordering the steps'},
                      {name: 'run', status: 'calling the tools'}],
  summary: SUMMARY = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const P = Math.round(U * PERSP_FRAC);

  const list = (Array.isArray(SCREENS) ? SCREENS : [])
    .map((s) => ({name: String(s?.name ?? '').trim(), status: String(s?.status ?? '').trim()}))
    .filter((s) => s.name || s.status)
    .slice(0, ROOM.length);
  if (!list.length) {
    throw new Error(
      'TermSpace needs at least one `screens` entry with a name or a status. The form is a camera moving ' +
      'between consoles that are all running; with no console there is nothing in the room and the shot is ' +
      'an empty stage.');
  }
  const n = list.length;
  const poses: Pose[] = list.map((_, i) => {
    const p = ROOM[i];
    return {x: (p.x ?? 0) * U, y: (p.y ?? 0) * U, z: (p.z ?? 0) * U, rx: p.rx, ry: p.ry};
  });

  const scrW = Math.round(U * 0.40), scrH = Math.round(U * 0.25);

  // THE TOUR. Hold on one screen, swing to the next, hold — then pull back so the room reads as a room.
  // `useT` freezes under reduced motion like every other clock here, so the still lands on a stop.
  const TOUR_END = 0.74;
  const leg = clamp01(t / TOUR_END) * Math.max(0, n - 1);
  const i = Math.max(0, Math.min(n - 2, Math.floor(leg)));
  const f = n > 1 ? easeInOutCubic(clamp01(leg - i)) : 1;
  const at = (k: keyof Pose, a: Pose, b: Pose) => lerp((a[k] ?? 0) as number, (b[k] ?? 0) as number, f);
  const a = poses[Math.min(i, n - 1)], b = poses[Math.min(i + 1, n - 1)];
  // ALIGNING WITH A SCREEN IS BECOMING ITS POSE — Stage3D applies the inverse, so the room swings round
  // until that console is square to the lens. The z offset is how far back the lens stands from it.
  // THE LENS BACKS OFF ALONG ITS OWN AXIS, not along world z. Written the easy way — `z: pose.z + d` — the
  // camera takes the screen's rotation and then steps back in a direction that is no longer behind it, so
  // the screen it just aligned with drifts off centre: measured at 163px on a 1920 frame for a screen at
  // ry 24deg, which reads as the camera missing what it flew to. The forward axis of a pose in CSS's own
  // order (translate, rotateX, rotateY) is (sin ry cos rx, -sin rx, cos ry cos rx).
  const D = U * 0.54;
  const rxR = (at('rx', a, b) * Math.PI) / 180, ryR = (at('ry', a, b) * Math.PI) / 180;
  const tour: Pose = {
    x: at('x', a, b) + D * Math.sin(ryR) * Math.cos(rxR),
    y: at('y', a, b) - D * Math.sin(rxR),
    z: at('z', a, b) + D * Math.cos(ryR) * Math.cos(rxR),
    rx: at('rx', a, b), ry: at('ry', a, b)};

  // THE CLOSE IS FITTED, NOT GUESSED, and the box is the shot's own — the caption band is not in it, so
  // "does the room fit" and "does a screen sit on the subtitle" are one question with one answer.
  const pad = Math.round(Math.hypot(scrW, scrH) / 2);
  const box = {left: U * 0.04, top: CONTENT_TOP, right: W - U * 0.04, bottom: contentBottom(W, H)};
  const wide = fitStage(poses, {rx: 5, ry: -3}, box, P, W, H, {radius: pad}).cam;

  const out = easeOutCubic(clamp01(seg(t, TOUR_END, 0.93)));
  const cam: Pose = {
    x: lerp(tour.x ?? 0, wide.x ?? 0, out), y: lerp(tour.y ?? 0, wide.y ?? 0, out),
    z: lerp(tour.z ?? 0, wide.z ?? 0, out), rx: lerp(tour.rx ?? 0, wide.rx ?? 0, out),
    ry: lerp(tour.ry ?? 0, wide.ry ?? 0, out),
  };

  const INK = dna?.fg ?? '#cdd7e4';
  const DIM = dna?.dim ?? '#5f6b80';
  const ACC = dna?.accent ?? '#3dd6a4';
  const ACC2 = dna?.accent2 ?? '#4d8cff';
  const SURF = dna?.surface ?? '#0d1420';
  const LINE = dna?.surfaceBorder ?? dna?.line ?? '#22304a';
  const MONO = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';

  // WHICH SCREEN IS THE CAMERA AT, and how far into its hold. `leg` is continuous, so the nearest whole
  // number is the screen being faced and the distance to it is how settled that screen is.
  const focusIdx = Math.max(0, Math.min(n - 1, Math.round(leg)));
  const settledOn = (k: number) => (out > 0.25 ? 1 : clamp01(1.25 - Math.abs(leg - k) * 1.6));

  const namePx = list.reduce(
    (px, s) => Math.min(px, fitTextPx(s.name || ' ', scrW * 0.86, Math.round(U * 0.032), {usable: 1})),
    Math.round(U * 0.032));
  const statusPx = list.reduce(
    (px, s) => Math.min(px, fitTextPx(s.status || ' ', scrW * 0.90, Math.round(U * 0.021), {usable: 1})),
    Math.round(U * 0.021));

  // THE CARET IS THE WHOLE REASON THIS IS A CONSOLE. The screen being faced types its status out; the ones
  // behind hold theirs, done. A status is only ever REVEALED, never trimmed away — the full string is in the
  // DOM from the first frame with the untyped tail transparent, so every type gate sees the whole line
  // whatever the clock is doing.
  const typed = (k: number, s: string) => {
    if (out > 0.02 || k !== focusIdx) return s.length;
    const local = clamp01((leg - (focusIdx - 0.42)) / 0.72);
    return Math.max(0, Math.min(s.length, Math.round(easeOutCubic(local) * s.length)));
  };
  const caretOn = Math.floor(t * DURATION / 14) % 2 === 0;

  // How much of a projected thing is still inside the shot's own box — 1 well inside, 0 once it has left.
  // The band is one screen-width wide so a console dims over the time it takes to cross the edge rather
  // than blinking out, and the BOTTOM edge is the caption band's, not the canvas's.
  const edgeFade = (x: number, y: number, w: number, h: number) => {
    const band = Math.max(1, w * 0.6);
    const l = (x - w / 2) / band, r = (W - (x + w / 2)) / band;
    const tp = (y - h / 2 - CONTENT_TOP * 0.4) / band, bt = (contentBottom(W, H) - (y + h / 2)) / band;
    return clamp01(Math.min(l, r, tp, bt) + 1);
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg
      ?? 'radial-gradient(130% 120% at 50% 16%, #0e1622, #05080e 74%)', overflow: 'hidden'}}>
      <Stage3D cam={cam} persp={P}>
        {poses.map((p, k) => {
          const lit = faceShade(p, cam);
          const q0 = projectPose(p, cam, P, W, H);
          const sf = q0.behind ? 0 : edgeFade(q0.x, q0.y, scrW * q0.k * 0.88, scrH * q0.k);
          const focused = k === focusIdx && out < 0.5;
          return (
            <Surface key={k} pose={p} w={scrW} h={scrH}
              style={{borderRadius: Math.round(U * 0.012), overflow: 'hidden', opacity: sf,
                background: SURF, border: `1px solid ${focused ? ACC : LINE}`,
                filter: `brightness(${lit.toFixed(3)})`,
                boxShadow: focused
                  ? `0 0 ${Math.round(U * 0.05)}px ${ACC}33, inset 0 0 ${Math.round(U * 0.05)}px #0008`
                  : `inset 0 0 ${Math.round(U * 0.05)}px #000a`}}>
              {/* the title bar — chrome only; every word on this register is drawn flat, above */}
              <div style={{height: Math.round(scrH * 0.17), borderBottom: `1px solid ${LINE}`,
                display: 'flex', alignItems: 'center', gap: Math.round(U * 0.008),
                padding: `0 ${Math.round(U * 0.012)}px`, background: '#0000002e'}}>
                {[0, 1, 2].map((d) => (
                  <span key={d} style={{width: Math.round(U * 0.008), height: Math.round(U * 0.008),
                    borderRadius: '50%', background: d === 0 ? '#ff5f57' : d === 1 ? '#febc2e' : '#28c840',
                    opacity: 0.85}} />
                ))}
              </div>
              {/* the scanline wash: a screen is emitting light, not printed */}
              <div style={{position: 'absolute', inset: 0, opacity: 0.5,
                background: `repeating-linear-gradient(0deg, #ffffff08 0 1px, transparent 1px 3px)`}} />
            </Surface>
          );
        })}
      </Stage3D>

      {/* THE WORDS ARE FLAT, positioned by the same matrix the stage is drawn with and sized by the
          perspective factor the browser applied — so they sit on their screen and stay crisp. */}
      {poses.map((p, k) => {
        const q = projectPose(p, cam, P, W, H);
        if (q.behind || q.k <= 0.02) return null;
        const w = scrW * q.k * 0.88;
        const npx = Math.max(7, namePx * q.k), spx = Math.max(6, statusPx * q.k);
        const block = inkBlockH(npx) + inkBlockH(spx) * 1.4;
        // A LINE GOES WITH ITS SCREEN. When the camera has travelled past one, the screen leaves frame, and
        // type that stays behind is cut by the canvas in every gate and unreadable besides. The same test
        // keeps it out of the caption band — the stage may put a surface anywhere, so the TYPE is bounded.
        // A SCREEN LEAVING FRAME FADES, IT DOES NOT GO BLANK. Culling the TYPE on its own left the window
        // still drawn — an empty console in the corner, which reads as a screen that failed rather than one
        // the camera is passing. The same factor dims the surface below, so the two always agree.
        const fade = edgeFade(q.x, q.y, w, block);
        if (fade <= 0.01) return null;
        const s = list[k];
        const cut = typed(k, s.status);
        const done = cut >= s.status.length;
        const near = settledOn(k);
        return (
          <div key={k} style={{position: 'absolute', left: q.x - w / 2,
            // A CONSOLE'S TEXT STARTS AT THE TOP, under the title bar — centring it in the window is a card's
            // habit, not a terminal's. Anchored off the screen's own projected height so it stays put.
            top: q.y - (scrH * q.k) / 2 + scrH * q.k * 0.17 + npx * 0.5, width: w,
            opacity: (0.3 + 0.7 * near) * fade, textShadow: '0 2px 10px rgba(0,0,0,.6)'}}>
            {/* NO `overflow: hidden` HERE. A clipped name is a string the register DECLINED to draw, and
                the one audit that can see that is the one this library keeps learning the same lesson from.
                `namePx` is fitted to the screen's own width, so it fits; if a film ever hands one that does
                not, it wraps and is ugly rather than silently short. */}
            <div style={{color: k === focusIdx ? ACC : ACC2,
              font: `700 ${npx.toFixed(1)}px/${leading(s.name, 1.2)} ${MONO}`,
              letterSpacing: '0.04em'}}>
              <span style={{opacity: 0.7}}>$ </span>{s.name}
            </div>
            {s.status ? (
              <div style={{marginTop: Math.round(npx * 0.34), color: done ? INK : DIM,
                font: `500 ${spx.toFixed(1)}px/${leading(s.status, 1.3)} ${MONO}`}}>
                <span style={{color: done ? ACC : DIM, marginRight: Math.round(spx * 0.5)}}>
                  {done ? '✓' : '→'}
                </span>
                {s.status.slice(0, cut)}
                {/* the untyped tail stays in the DOM, transparent: revealed, never trimmed */}
                <span style={{opacity: 0}}>{s.status.slice(cut)}</span>
                {!done && caretOn ? (
                  <span style={{color: ACC, marginLeft: 1}}>{'█'}</span>
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })}

      {/* the closing line, drawn only when the film supplied one */}
      {SUMMARY ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: CONTENT_TOP - Math.round(U * 0.055),
          textAlign: 'center', color: DIM, opacity: easeOutCubic(clamp01(seg(t, 0.80, 0.95))),
          font: `600 ${Math.round(U * 0.025)}px/${leading(SUMMARY, 1.2)} ${MONO}`,
          letterSpacing: '0.14em'}}>{SUMMARY}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default TermSpace;
