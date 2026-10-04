// SHOT · Pointer Tour — one screen, one continuous camera, and a cursor that walks the viewer to each place
// on it in turn, leaving a click where it stops.
//
// WHAT IT ARGUES, and why it is not four cuts. Cutting to four features says "here are four things" and
// throws away the one claim a product most needs to make: that they are four parts of the SAME place. Every
// cut costs the viewer a beat of re-orientation, and after the fourth they still could not tell you where the
// reports live relative to the settings. A single camera that travels between the stops makes the spatial
// relationship a fact on screen, and the cursor is the viewer's own attention standing in for them — it goes
// where they should look, and clicking is how it says "this one".
//
// HOW THE CURSOR AND THE CAMERA STAY WELDED. Both read `runtime/pageCam2D`: the lens is a transform on the
// page, and the cursor is ordinary DOM placed by `pageToScreen` from the SAME camera — so it cannot drift
// off the thing it is pointing at, and it stays crisp and constant-sized instead of being scaled up with the
// page. The stops themselves come from `uiCardRects`, the same function that draws the cards, so "fly to the
// third card" aims at the rectangle the third card is actually in rather than at a number written twice.

import React from 'react';
import {AbsoluteFill, useVideoConfig, staticFile} from 'remotion';
import {useT, seg, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {rows} from '../runtime/rows';
import {useDNA} from '../runtime/dna';
import {UiSurface, uiCardRects, type UiContent} from '../runtime/uiSurface';
import {captionBand} from '../runtime/layout';
import {PageCam2D, camAt, pageToScreen, fitScale, clampToPage, camUnlock, useCamUnlock,
  type CamKey} from '../runtime/pageCam2D';
import {focusAt} from '../runtime/focus';

export const DURATION = 180; // 6.0s

const BG_D0 = '#dfe3ea', ACC_D0 = '#5b6b86';
const OPEN = 0.12;        // the overview holds this long — long enough to read "this is one screen"
const STEP = 0.20;        // per stop: the move plus the pause on arrival
const MOVE = 0.12;        // how much of a step is travel; the rest is the pause that makes it a visit

export type TourBlock = {x: number; y: number; w: number; h: number; tag?: string; text?: string};

/** Which places on a CAPTURED page are worth visiting: LEAVES, biggest first, none overlapping, read order.
 *
 *  A capture returns every measurable box, which is the DOM again and not a route. Ranking them by area — the
 *  obvious rule, and the one written here first — tours the CONTAINERS: on a three-column report the four
 *  largest boxes are the nav, the main column and the sidebar, so the camera flew to the centre of a column
 *  and the cursor pointed at the white space in the middle of it. A container is exactly "a box with other
 *  candidate boxes inside it", so that is what disqualifies one; what is left are the things a reader would
 *  actually point at, and among those, area is a fair proxy for importance. */
const tourStops = (blocks: TourBlock[], pageW: number, max = 4): TourBlock[] => {
  const hit = (a: TourBlock, b: TourBlock) =>
    a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const holds = (a: TourBlock, b: TourBlock) =>            // a fully contains b, and is not b itself
    a !== b && a.x <= b.x && a.y <= b.y && a.x + a.w >= b.x + b.w && a.y + a.h >= b.y + b.h;
  const cand = blocks.filter((b) => b.w > pageW * 0.14 && b.h >= 14);
  // Containment is judged against EVERY block, not against the candidates. A nav rail holding five links
  // that are each too narrow to be a stop contains no CANDIDATE, so testing within the shortlist called it a
  // leaf and toured it — the camera flew to the middle of a column and the cursor pointed at white space.
  // And the threshold is TWO children, not one: a paragraph with a link in it is not a container, it is a
  // paragraph, and dropping it would throw away the body of the page.
  const leaves = cand.filter((b) => blocks.filter((o) => holds(b, o)).length < 2);
  const kept: TourBlock[] = [];
  for (const b of [...leaves].sort((p, q) => q.w * q.h - p.w * p.h)) {
    if (kept.length >= max) break;
    if (!kept.some((k) => hit(k, b))) kept.push(b);
  }
  return kept.sort((a, b) => a.y - b.y || a.x - b.x);
};

export const PointerTour: React.FC<{
  screen?: string;
  items?: string[];
  nav?: string[];
  // A CAPTURED page instead of a drawn one. The argument is identical either way — several places on ONE
  // screen and the path between them — so this is the same register with a different subject, not a second
  // one. Given a capture it films that; given none it draws a surface, which is what a beat about a product
  // that does not exist yet has to do.
  src?: string;
  pageW?: number;
  pageH?: number;
  blocks?: TourBlock[];
}> = ({screen: SCREEN = 'Workspace',
  items: ITEMS = ['Overview', 'Reports', 'Records', 'Settings', 'Team', 'Billing'],
  nav: NAV = ['Home', 'Overview', 'Reports', 'Records', 'Team', 'Settings'],
  src: SRC, pageW: SRC_W, pageH: SRC_H, blocks: SRC_BLOCKS_IN} = {}) => {
  const SRC_BLOCKS = rows<TourBlock>(SRC_BLOCKS_IN, 'blocks', 'PointerTour');
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // THE CAMERA FILLS THE CONTENT ZONE, NOT THE FRAME. A page camera that covers the whole frame puts the
  // page's own type into the caption band, and the burned subtitle then lands on it — measured on a real
  // film, this shot's band ground read 0.95 mid-beat (a white page) against a film that declares itself
  // dark, so the caption was white on white and unreadable, and one beat later the same band was 0.03.
  // No static declaration can follow a ground that flips inside one shot; reserving the band means the
  // caption always sits on the film's own ground, which is the contract every other register keeps.
  const VIEW_H = H - captionBand(W, H);
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const U = Math.min(W, H);

  const captured = !!(SRC && SRC_BLOCKS && SRC_BLOCKS.length && SRC_W && SRC_H);
  const list = (ITEMS ?? []).filter((x) => String(x ?? '').trim());
  if (!captured && !list.length) {
    throw new Error(
      'PointerTour needs either a capture (`src` + `blocks` + `pageW`/`pageH`, from scripts/capture_page.py) ' +
      'or at least one non-empty `items` entry. The whole form is a cursor visiting places on one screen; ' +
      'with neither it flies an empty page, which composes and argues nothing.');
  }
  if (SRC && !(SRC_BLOCKS && SRC_BLOCKS.length)) {
    throw new Error(
      'PointerTour was given `src` without `blocks`. With the picture and no boxes it can only pan across a ' +
      'screenshot — there is nothing to fly TO — and the layout json sits beside the texture the capture ' +
      'wrote. Passing one without the other is the state where the shot looks composed and visits nothing.');
  }

  // THE PAGE IS BIGGER THAN THE FRAME ON PURPOSE — that is what makes this a fly-over rather than a zoom.
  // Sized off the frame's LONG side so a portrait cut gets the same landscape window rather than a squeezed
  // one; the camera then does the work of fitting it.
  const pageW = captured ? SRC_W! : Math.round(Math.max(W, H) * 1.40);
  const pageH = captured ? SRC_H! : Math.round(pageW / 1.55);
  const cards = captured ? tourStops(SRC_BLOCKS!, pageW) : uiCardRects(pageW, pageH, true);
  if (!cards.length) {
    throw new Error(
      'PointerTour found nothing on the captured page big enough to visit — every box was under 14% of the ' +
      'page width. A tour of a page with no landmarks is a camera wandering, so it says so instead.');
  }
  const stops = captured ? cards : list.slice(0, Math.min(4, cards.length));
  const n = stops.length;

  // The route, as a list of places to look. Each stop gets the same travel and the same pause, because an
  // even step is what reads as walking a room; uneven ones read as the camera hunting for something.
  const keys: CamKey[] = [
    {at: 0, x: pageW / 2, y: pageH / 2, s: fitScale(W, VIEW_H, pageW, pageH)},
    {at: OPEN, x: pageW / 2, y: pageH / 2, s: fitScale(W, VIEW_H, pageW, pageH)},
  ];
  // A stop is INSIDE the screen, so the close-up is never allowed to be wider than the screen itself: at 9:16
  // the card-relative scale left the page 75px short of the frame and a strip of backdrop ran along the top
  // and bottom of every stop, which reads as the window having come loose from the shot.
  const cover = Math.max(W / pageW, VIEW_H / pageH);
  const closeS = (r: {w: number; h: number}) => Math.max(cover, Math.min(W * 0.60 / r.w, VIEW_H * 0.60 / r.h));
  stops.forEach((_, i) => {
    const r = cards[i];
    const arrive = OPEN + i * STEP + MOVE;
    keys.push({at: arrive, x: r.x + r.w / 2, y: r.y + r.h / 2, s: closeS(r)});
    keys.push({at: arrive + (STEP - MOVE), x: r.x + r.w / 2, y: r.y + r.h / 2, s: closeS(r)});
  });
  // Clamped AFTER interpolating, not per key: a lens that only obeys the page at its stops still drifts off
  // the edge on the way between two of them, and the frame with the fault in it is the one nobody rendered.
  const cam = clampToPage(camAt(keys, t, easeInOutCubic), W, VIEW_H, pageW, pageH);
  // the tour moves for the whole beat, so the page's type carries the baseline unlock for all of it
  // (runtime/pageCam2D) — the same value goes to every pageToScreen below, so the pointer stays on its mark
  const unlock = useCamUnlock(camUnlock(keys));

  // THE CURSOR AND THE CAMERA ARE ONE SYSTEM. The cursor's PAGE position runs on a table with the same
  // timings as the lens, so the two arrive together and, during a move, the pointer holds its place on the
  // frame instead of sliding across it. Picking the cursor's target by "whichever stop we have passed"
  // instead — the obvious way, and the way this was first written — teleports it to the next card at the
  // instant the move BEGINS, while the lens is still on the previous one: for the length of the travel the
  // pointer is somewhere off the side of the frame, and it is the shot's only actor.
  //
  // It is drawn in SCREEN space, at a fixed size. Living inside the page and scaled with it, a cursor stops
  // reading as the UI layer and starts reading as a picture of one.
  // `keys` is [overview, overview-hold, then per stop: arrive, hold-end], so a key's stop is fixed by its
  // index. During the overview the pointer waits at the middle of the page and travels in with the lens.
  // @positional: `keys` is built as [overview, hold, then arrive/hold per stop], so a key's stop IS its index
  const stopOf = (idx: number) => (idx < 2 ? -1 : Math.floor((idx - 2) / 2));
  const cursorKeys: CamKey[] = keys.map((k, idx) => {
    const i = stopOf(idx);
    if (i < 0) return {at: k.at, x: pageW / 2, y: pageH * 0.58, s: 1};
    const r = cards[i];
    return {at: k.at, x: r.x + r.w * 0.58, y: r.y + r.h * 0.62, s: 1};
  });
  const cur = camAt(cursorKeys, t, easeInOutCubic);
  const target = pageToScreen(cam, W, VIEW_H, cur.x, cur.y, unlock);
  const curPx = Math.round(U * 0.055);
  const shown = clamp01(seg(t, OPEN * 0.6, OPEN));

  // A ripple is fired at each arrival — the beat that says "this one", and the shot's only percussion.
  const ripples = stops.map((_, i) => {
    const at = OPEN + i * STEP + MOVE;
    const u = seg(t, at, at + 0.055);
    return {i, u: u > 0 && u < 1 ? easeOutCubic(u) : (t >= at + 0.055 ? 1 : 0), live: t >= at && t < at + 0.055};
  });

  const content: UiContent = {title: SCREEN, nav: NAV, items: list};

  // THE GRAZE. A flat interface under a moving camera reads as a page SCROLLING, not as a surface being
  // examined — every part of it equally sharp is the one thing no real lens does, and it is why a fly-over of
  // a screenshot can look like a slideshow with a pan on it. So the page is drawn twice: sharp, and again
  // softened with a hole cut where the lens is looking. What the cursor is pointing at is in focus; the rest
  // of the page falls away, which is what says "this part" without an arrow saying it.
  //
  // The blur is the shared lens at a HEAVIER setting than the carousel's, and deliberately: there the
  // out-of-focus material also shrinks and fades, so the blur is the third cue; here the periphery is the
  // same page at the same size and brightness, so the blur is the only one. It arrives with the tour rather
  // than at frame 0 — during the opening overview the whole page IS the subject, and defocusing its edges
  // then would just look like a lens fault.
  const dof = easeOutCubic(clamp01(seg(t, OPEN * 0.7, OPEN + STEP * 0.35)));
  const dofPx = focusAt(1, U, {blurFrac: 0.008}).blurPx;
  const sharpR = U * 0.30, softR = U * 0.78;
  const mask = `radial-gradient(circle at ${Math.round(target.x)}px ${Math.round(target.y)}px, `
    + `transparent 0px, transparent ${Math.round(sharpR)}px, #000 ${Math.round(softR)}px)`;
  const page = captured ? (
    <img src={staticFile(SRC!)} width={pageW} height={pageH} alt=""
      style={{display: 'block', width: pageW, height: pageH}} />
  ) : (
    <UiSurface page="cards" W={pageW} H={pageH} dna={dna} content={content} seed={7} />
  );

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: VIEW_H, overflow: 'hidden'}}>
      <PageCam2D cam={cam} W={W} H={VIEW_H} pageW={pageW} pageH={pageH} unlock={unlock}>{page}</PageCam2D>
      {dof > 0.002 ? (
        // `data-echo`: every string in here is the SAME string the sharp copy above already draws, at the
        // same place. Without the marker the type gates measure the page twice and report each label
        // colliding with itself — a true observation and a useless one. See runtime/textSafe.tsx.
        <div aria-hidden data-echo style={{position: 'absolute', inset: 0, opacity: dof,
          filter: `blur(${dofPx.toFixed(2)}px)`, WebkitMaskImage: mask, maskImage: mask}}>
          <PageCam2D cam={cam} W={W} H={VIEW_H} pageW={pageW} pageH={pageH} unlock={unlock}>{page}</PageCam2D>
        </div>
      ) : null}
      </div>

      {ripples.filter((r) => r.live).map((r) => {
        const rect = cards[r.i];
        const c = pageToScreen(cam, W, VIEW_H, rect.x + rect.w * 0.58, rect.y + rect.h * 0.62, unlock);
        const d = Math.round(U * 0.055) * (0.3 + r.u * 1.6);
        return (
          <div key={r.i} style={{position: 'absolute', left: c.x - d / 2, top: c.y - d / 2, width: d, height: d,
            borderRadius: '50%', border: `${Math.max(2, Math.round(U * 0.004))}px solid ${ACC}`,
            opacity: 1 - r.u}} />
        );
      })}

      {/* the cursor itself: a plain arrow with a drop shadow, sized once in screen pixels */}
      <svg width={curPx} height={curPx} viewBox="0 0 24 24"
        style={{position: 'absolute', left: target.x, top: target.y, opacity: shown,
          filter: 'drop-shadow(0 2px 3px rgba(12,16,24,.45))'}}>
        <path d="M4 2 L4 19 L8.6 14.6 L11.4 21 L14.3 19.7 L11.6 13.6 L18 13.4 Z"
          fill={dna?.fg ?? '#1c2029'} stroke="#fff" strokeWidth="1.4" strokeLinejoin="round" />
      </svg>
    </AbsoluteFill>
  );
};
export default PointerTour;
