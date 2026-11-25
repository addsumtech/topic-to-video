// A REAL RECORDING OF AN APP, EDITED AS A TUTORIAL — on a director-path film page. Bundled by
// scripts/build_screenrec_page.sh into assets/html/screenrec.js (window.ScreenRec).
//
// The recording is scripts/app_record.py's: the app driven by the real cursor, its window at its own pixels, every
// action logged (clips/<name>/rec.json + frames/NNNNN.jpg). This file is the edit a tutorial gets, as pure functions
// of the film's time:
//   TIME   each anchored action lands on the film second the narration names it; the stretch before it plays at real
//          speed after the last action settles (1 s, or to the end of an action that starts in it: a drag, typing), then HOLDS while the voice catches up, or is SPED UP (to `maxSpeed`)
//          when the voice is quicker than the hand — never faster, which is refused with the time it would need;
//   CAMERA a close-up that follows the action: remotion/src/runtime/focusTrack.ts (the Remotion tier's tuned track:
//          eased between keys, at a fixed magnification, refused when it would whip), never past the recording's
//          own pixels;
//   RINGS  a ring where each anchored click lands, so the eye finds it.
// The cursor is the recording's own (app_record moves the real one at a human pace); nothing is drawn in its place.
import {checkFocusTrack, focusAt} from '../../../remotion/src/runtime/focusTrack.ts';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const smoothstep = (u) => { const x = clamp(u, 0, 1); return x * x * (3 - 2 * x); };
const SETTLE = 1.0;    // seconds an action's result plays at real speed before a hold
const LEAD = 0.1;      // the recording a hold leaves before the next anchored action (its own approach)

/**
 * rec: the parsed rec.json. opts:
 *   base      the frames folder, relative to the page ('clips/rec/frames/')
 *   box       {x, y, w} on the frame (px); h follows the window's own proportions (a given h must match them)
 *   start, end  film seconds the recording is on screen
 *   anchors   [{action: i, at: s}]: logged action i lands at film second s (the word that names it)
 *   maxSpeed  the fastest the recording may run between anchors (default 3)
 *   zoom      a number, or [{at: s, z}] eased between (1 = the whole window)
 *   rings     true (default): a ring on each anchored click or drag
 */
export function edit(rec, opts) {
  const {base, box, start, end, anchors = [], maxSpeed = 3, zoom = 1, rings = true} = opts || {};
  if (!rec || !(rec.n > 0) || !Array.isArray(rec.actions)) throw new Error('ScreenRec.edit: rec is a parsed rec.json');
  if (typeof base !== 'string' || !base) throw new Error('ScreenRec.edit: base is the frames folder');
  if (!(end > start)) throw new Error('ScreenRec.edit: end must come after start');
  const fps = rec.fps || 30, dur = (rec.n - 1) / fps, W = rec.width, H = rec.height;
  const bh = box.w * H / W;
  if (box.h != null && Math.abs(box.h - bh) > 0.02 * bh) {
    throw new Error(`ScreenRec.edit: box ${box.w}x${box.h} is not the window's proportions (${W}x${H}); give w only`);
  }
  const B = {x: box.x, y: box.y, w: box.w, h: bh};
  const zKeys = typeof zoom === 'number' ? [{at: start, z: zoom}] : zoom;
  const zMax = Math.max(...zKeys.map((k) => k.z));
  if (!(zKeys.every((k) => k.z >= 1))) throw new Error('ScreenRec.edit: zoom is 1 (the whole window) or more');
  if (W / zMax < B.w - 0.5) {
    throw new Error(`ScreenRec.edit: zoom ${zMax} draws the recording past its pixels (${(W / zMax).toFixed(0)} px ` +
      `of it across ${B.w} px of frame); the most at this size is ${(W / B.w).toFixed(2)}`);
  }
  const A = anchors.map((a) => {
    const act = rec.actions[a.action];
    if (!act) throw new Error(`ScreenRec.edit: there is no action ${a.action} in rec.json`);
    return {...a, r: act.t, act};
  }).sort((p, q) => p.at - q.at);
  // how long each anchor's result plays at real speed before a hold: SETTLE, stretched to the end of every action
  // that starts inside it (a drag, the typing after a double-click: a hold must never freeze an action halfway), and
  // always ending LEAD before the next anchored action, so that action plays on its word, not early (a Return 0.6 s
  // after its cell's click landed 1.7 s before "Watch the chart", the Numbers film, 2026-11-25)
  A.forEach((a, k) => {
    const nextR = k + 1 < A.length ? A[k + 1].r : Infinity;
    let s = SETTLE;
    for (const b of rec.actions) {
      if (b.t >= a.r && b.t <= a.r + s && b.t < nextR && b.t_end != null) s = Math.max(s, b.t_end - a.r + 0.3);
    }
    a.settle = Math.max(0, Math.min(s, nextR - a.r - LEAD));
  });
  A.forEach((a, k) => {
    if (k && !(a.r > A[k - 1].r)) throw new Error('ScreenRec.edit: anchors must follow the recording\'s own order');
    if (k) {
      const F = a.at - A[k - 1].at, R = a.r - A[k - 1].r;
      if (R / F > maxSpeed + 1e-9) {
        throw new Error(`ScreenRec.edit: action ${A[k - 1].action} to ${a.action} would play at ${(R / F).toFixed(1)}x ` +
          `(limit ${maxSpeed}x): give it at least ${(R / maxSpeed).toFixed(2)} s of film, or cut a wait from the recording`);
      }
    }
  });

  /** The recording's second at film second t. */
  const recAt = (t) => {
    let r;
    if (!A.length) r = t - start;
    else if (t <= A[0].at) r = A[0].r - (A[0].at - t);
    else if (t >= A[A.length - 1].at) r = A[A.length - 1].r + (t - A[A.length - 1].at);
    else {
      const k = A.findIndex((a) => a.at > t), p = A[k - 1], q = A[k];
      const F = q.at - p.at, R = q.r - p.r, df = t - p.at;
      if (F >= R) {
        const s = p.settle, holdEnd = F - (R - s);
        r = df < s ? p.r + df : df < holdEnd ? p.r + s : p.r + s + (df - holdEnd);
      } else r = p.r + df * (R / F);
    }
    return clamp(r, 0, dur);
  };

  const zAt = (t) => {
    if (t <= zKeys[0].at) return zKeys[0].z;
    for (let i = 1; i < zKeys.length; i++) {
      if (t < zKeys[i].at) return zKeys[i - 1].z + (zKeys[i].z - zKeys[i - 1].z) * smoothstep((t - zKeys[i - 1].at) / (zKeys[i].at - zKeys[i - 1].at));
    }
    return zKeys[zKeys.length - 1].z;
  };

  // the close-up arrives a little before the click, where the cursor is already heading
  const track = A.filter((a) => a.act.x != null).map((a) => ({t: Math.max(0, a.at - 0.35 - start), x: a.act.x / W, y: a.act.y / H}));
  track.forEach((k, i) => { if (i && k.t <= track[i - 1].t) k.t = track[i - 1].t + 1e-3; });
  if (track.length && zMax > 1) checkFocusTrack(track, {w: 1 / zMax}, fps);

  return {
    box: B, recAt,
    at(t) {
      const r = recAt(t);
      const frame = clamp(Math.round(r * fps) + 1, 1, rec.n);
      const z = zAt(t);
      let vx = 0, vy = 0;
      if (z > 1 && track.length) {
        const tl = focusAt(track, t - start, {w: 1 / z}, 1 / z);
        vx = tl.x * W; vy = tl.y * H;
      } else if (z > 1) { vx = (W - W / z) / 2; vy = (H - H / z) / 2; }
      const view = [vx, vy, W / z, H / z];
      const ringList = !rings ? [] : A.filter((a) => (a.act.kind === 'click' || a.act.kind === 'drag') && a.act.x != null)
        .map((a) => ({x: B.x + (a.act.x - view[0]) / view[2] * B.w, y: B.y + (a.act.y - view[1]) / view[3] * B.h,
          p: (t - a.at) / 0.55}))
        .filter((g) => g.p >= 0 && g.p <= 1);
      return {src: `${base}${String(frame).padStart(5, '0')}.jpg`, frame, view, box: B, rec: [W, H], rings: ringList,
        visible: t >= start && t <= end};
    },
  };
}

/**
 * Draw a state into `el`: a <div> holding one <img> (the recording) and one <svg> (the rings), positioned by this
 * call at the state's box. Returns a promise that settles when the frame's picture is decoded: return it from
 * window.seek so the capture waits for it.
 */
export function draw(el, state, {accent = '#2f80ed', radius = 26} = {}) {
  const img = el.querySelector('img'), svg = el.querySelector('svg');
  if (!img || !svg) throw new Error('ScreenRec.draw: the element needs one <img> and one <svg> inside');
  const B = state.box, [vx, vy, vw] = state.view, k = B.w / vw;      // frame px per recording px
  Object.assign(el.style, {position: 'absolute', left: `${B.x}px`, top: `${B.y}px`, width: `${B.w}px`,
    height: `${B.h}px`, overflow: 'hidden', display: state.visible ? 'block' : 'none'});
  // laid out ONCE at the recording's own size; the camera is a transform (sub-pixel, no re-layout): per-frame
  // left/top/width in whole px made a 0.9 s push STEP (picture_glide red, the Numbers film, 2026-11-25)
  Object.assign(img.style, {position: 'absolute', left: '0px', top: '0px', width: `${state.rec[0]}px`,
    height: `${state.rec[1]}px`, maxWidth: 'none', transformOrigin: '0 0', willChange: 'transform',
    transform: `translate(${(-vx * k).toFixed(3)}px, ${(-vy * k).toFixed(3)}px) scale(${k.toFixed(6)})`});
  svg.setAttribute('width', B.w); svg.setAttribute('height', B.h);
  Object.assign(svg.style, {position: 'absolute', left: '0px', top: '0px', overflow: 'visible'});
  svg.innerHTML = state.rings.map((g) => {
    const e = 1 - Math.pow(1 - g.p, 3);
    return `<circle cx="${g.x - B.x}" cy="${g.y - B.y}" r="${(0.35 + 0.65 * e) * radius}" fill="none" ` +
      `stroke="${accent}" stroke-width="4" opacity="${(1 - g.p).toFixed(3)}"/>`;
  }).join('');
  if (img.getAttribute('src') !== state.src) img.setAttribute('src', state.src);
  return img.decode ? img.decode().catch(() => { throw new Error(`ScreenRec: cannot load ${state.src}`); }) : Promise.resolve();
}
