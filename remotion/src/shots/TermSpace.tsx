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
//
// EVERY SCREEN IS IN THE ROOM, OR THE REGISTER SAYS IT CANNOT BE. The room has four hand-set positions and the
// list used to be `.slice(0, ROOM.length)`, so a film that named five running jobs got a room of four with
// nothing said — the fifth was the one the film had just told the viewer about. Past MAX_SCREENS it now
// throws with the maximum, and an entry with neither a name nor a status (which was silently filtered out,
// changing the count the film believed it had) throws naming the entry.
//
// A SCREEN'S NAME IS PAINTED IN ITS OWN STATE. The name took the accent when the camera was facing it and
// the second accent otherwise — and after the pull-back the camera is still "facing" the last screen it
// visited, so that screen's name ENDED in the accent whatever it was doing. The accent is the colour the film
// uses for "working" (the next beat prints 绿色＝工作中　灰色＝等待中), so a WAITING last screen closed the
// shot painted as working, beside its own grey dot. The name, the focus border and the focus glow now take
// the screen's state colour — accent when it is working, dim when it is waiting — and the camera's attention
// is carried by what does not claim a state: the lit border, the brightness and the opacity of the one faced.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {Stage3D, Surface, OnSurface, projectPose, planeAffine, fitStage, faceShade, PERSP_FRAC, type Pose} from '../runtime/stage3d';

export const DURATION = 190; // ~6.3s

/** Where the screens stand. Hand-set and deterministic: a room whose walls move every render is not a room.
 *  x/y/z are fractions of the frame's short side, scaled below; ry turns each screen to face the middle. */
const ROOM: Pose[] = [
  {x: -0.34, y: -0.10, z: 0.06, rx: 4, ry: 26},
  {x: 0.33, y: -0.14, z: -0.16, rx: -3, ry: -24},
  {x: -0.26, y: 0.22, z: -0.30, rx: 9, ry: 18},
  {x: 0.30, y: 0.18, z: 0.12, rx: -7, ry: -20},
];
export const MAX_SCREENS = ROOM.length;

// THE GLYPH CARRIES RUN-STATE, and for a long time it carried the TYPEWRITER. `done` means "this status
// has finished typing", so by the close every screen showed the same ✓ whatever it said — and a reviewer
// asked the question that settles it: hide the caption, and the frame reads "three terminals in three
// places", not 哪个还在跑，哪个在等你, which is the beat's whole sentence. A mark derived from the animation
// is furniture; `waiting` lets the film say which screens are finished and which are still going.
type Screen = {name?: string; status?: string; waiting?: boolean};

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
    // THE NORMALISER REBUILDS THE ROW, so every field it does not name is dropped — `waiting` was declared,
    // passed by the board, and silently thrown away here, which is the shape of half the defects found in
    // this repo this week: a declared input that never reaches the drawing.
    .map((s) => ({name: String(s?.name ?? '').trim(), status: String(s?.status ?? '').trim(),
                  waiting: s?.waiting === true}));
  if (!list.length) {
    throw new Error(
      'TermSpace needs at least one `screens` entry with a name or a status. The form is a camera moving ' +
      'between consoles that are all running; with no console there is nothing in the room and the shot is ' +
      'an empty stage.');
  }
  if (list.length > MAX_SCREENS) {
    throw new Error(
      `TermSpace takes at most ${MAX_SCREENS} \`screens\` (got ${list.length}): the room has ${MAX_SCREENS} ` +
      'hand-set positions, and a screen with no place in it would be a console the film named and the viewer ' +
      'never sees. Keep the ones running at once, or use a grid/list register for more.');
  }
  list.forEach((s, i) => {
    if (!s.name && !s.status) {
      throw new Error(`TermSpace: screen ${i + 1} has neither a \`name\` nor a \`status\`, so there is nothing ` +
        'to put on it. Give it one, or leave the entry out.');
    }
  });
  const n = list.length;
  const poses: Pose[] = list.map((_, i) => {
    const p = ROOM[i];
    // @fallback: an omitted pose coordinate is the origin of the space: a camera position, not a reading about a screen
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
    // @fallback: an omitted pose coordinate is the origin of the space: a camera position, not a reading about a screen
    x: lerp(tour.x ?? 0, wide.x ?? 0, out), y: lerp(tour.y ?? 0, wide.y ?? 0, out),
    z: lerp(tour.z ?? 0, wide.z ?? 0, out), rx: lerp(tour.rx ?? 0, wide.rx ?? 0, out),
    ry: lerp(tour.ry ?? 0, wide.ry ?? 0, out),
  };

  const INK = dna?.fg ?? '#cdd7e4';
  const DIM = dna?.dim ?? '#5f6b80';
  const ACC = dna?.accent ?? '#3dd6a4';
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
          // the focus ring is lit in THIS screen's state colour, never the working accent on a waiting screen
          const stateCol = list[k].waiting ? DIM : ACC;
          return (
            <Surface key={k} pose={p} w={scrW} h={scrH}
              style={{borderRadius: Math.round(U * 0.012), overflow: 'hidden', opacity: sf,
                background: SURF, border: `1px solid ${focused ? stateCol : LINE}`,
                filter: `brightness(${lit.toFixed(3)})`,
                boxShadow: focused
                  ? `0 0 ${Math.round(U * 0.05)}px ${stateCol}33, inset 0 0 ${Math.round(U * 0.05)}px #0008`
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
        // THE WORDS LIE ON THE SCREEN'S OWN PLANE. They used to be placed at the window's projected CENTRE and
        // scaled by one factor, so they could move and grow but never turn — a viewer of the delivered film
        // saw the windows tilt with the room and the text stay upright over them, like a sticker on the glass.
        // The block is now laid out in the window's LOCAL px and carried onto the plane by a 2D affine fitted
        // to its three projected corners (`planeAffine`). Still outside the posed surface, still a 2D
        // transform — the reason the type was kept off the Z layer in the first place (91 flat vs 56 under Z)
        // is untouched.
        const npx = namePx, spx = statusPx;
        const lw = scrW * 0.88;
        const lleft = -scrW * 0.44;
        const ltop = -scrH / 2 + scrH * 0.17 + npx * 0.5;
        const lblock = inkBlockH(npx) + inkBlockH(spx) * 1.4;
        const aff = planeAffine(p, cam, P, W, H, lleft, ltop, lw, lblock);
        if (!aff) return null;
        const w = lw * aff.scale;
        const block = lblock * aff.scale;
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
          // A CONSOLE'S TEXT STARTS AT THE TOP, under the title bar — centring it in the window is a card's
          // habit, not a terminal's. `ltop` above is that offset in the window's own units.
          <OnSurface key={k} pose={p} cam={cam} persp={P} W={W} H={H}
            left={lleft} top={ltop} width={lw} height={lblock} affine={aff}
            style={{opacity: (0.3 + 0.7 * near) * fade, textShadow: '0 2px 10px rgba(0,0,0,.6)'}}>
            {/* NO `overflow: hidden` HERE. A clipped name is a string the register DECLINED to draw, and
                the one audit that can see that is the one this library keeps learning the same lesson from.
                `namePx` is fitted to the screen's own width, so it fits; if a film ever hands one that does
                not, it wraps and is ugly rather than silently short. */}
            {/* THE NAME IS IN ITS OWN STATE'S COLOUR (see the header): the accent only when it is working. */}
            <div style={{color: s.waiting ? DIM : ACC,
              font: `700 ${npx.toFixed(1)}px/${leading(s.name, 1.2)} ${MONO}`,
              letterSpacing: '0.04em'}}>
              <span style={{opacity: 0.7}}>$ </span>{s.name}
            </div>
            {s.status ? (
              <div style={{marginTop: Math.round(npx * 0.34),
                color: done ? INK : DIM,
                font: `500 ${spx.toFixed(1)}px/${leading(s.status, 1.3)} ${MONO}`}}>
                {/* ONE GLYPH, AND THE COLOUR CARRIES THE STATE — a status LED, not a verdict. A ✓ on the
                    screen that is WAITING reads as "this one finished successfully", which is the opposite
                    of the beat's point: it is the one that needs you. And the colour must be the FILM's,
                    not this register's own idea — the next beat prints the code in words
                    (绿色＝工作中　灰色＝等待中), so green here has to mean working or the film contradicts
                    itself across two consecutive frames. */}
                <span style={{color: done ? (s.waiting ? DIM : ACC) : DIM,
                  marginRight: Math.round(spx * 0.5)}}>
                  {done ? '\u25cf' : '\u2192'}
                </span>
                {s.status.slice(0, cut)}
                {/* the untyped tail stays in the DOM, transparent: revealed, never trimmed */}
                <span style={{opacity: 0}}>{s.status.slice(cut)}</span>
                {!done && caretOn ? (
                  <span style={{color: ACC, marginLeft: 1}}>{'█'}</span>
                ) : null}
              </div>
            ) : null}
          </OnSurface>
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
