// STAGE · CardStage — ONE card that stays on stage across a run of beats and changes with them: where it sits, how it
// is turned, how big it is, what shape it is, what is on its face — and what happens TO it: a cursor that points at a
// part of it and clicks, marks that box a part and name it, parts that lift off it in depth, a camera that leans in on
// a part, a figure that counts up beside it. Over the card, the beat's title — one place, one size for the run, the key
// word marked — changes as the beat changes: the old line leaves, then the new one arrives.
//
// What it is for: a product promo's hero object (a deck page, a screenshot, a document) that the film keeps turning
// over and acting on instead of cutting away from — the shape of "the same thing, shown one more way" that a run of
// separate shots cannot draw. Every word, number and picture comes from props.
//
// ONE COORDINATE SYSTEM. Everything that points at the card names a place ON ITS FACE: (u, v), 0..1 across and down
// the face, or a rect [u0, v0, u1, v1]. The stage carries that place through the card's 3D pose to the screen, so a
// cursor stays on the button it clicked while the card turns.
//
// THE STATE (each beat's shot_props, and each of its `steps`, say what changes — runtime/stageRun.tsx):
//   image | page, fit           the face: a file the film serves, or a page the card draws (`image: null` to switch)
//   title, highlight            the title line and the word of it to mark
//   card {x,y,s,rx,ry,rz,aspect}  the pose; with no `aspect` the card takes its face's shape
//   cursor {u,v,click}          a pointer on the face; `click: true` clicks as it arrives (and sfx plays a click there)
//   marks [{rect, label?}]      boxes on the face, each with an optional name beside it
//   lift [{rect, z?}]           parts of the face lifted off it in depth (z: 1 = the default height)
//   camera {zoom, u, v}         lean in on a place of the face (zoom 1 = no camera move)
//   count {value, from?, label?, u?, v?}  a figure counting to `value` beside a place of the face — a SOURCED figure
//   backdrop                    the DNA colour the stage is lit in (bg by default; fg, accent…) — set on a beat
//   hero                        false hides the hero card (a wall or the side cards hold the stage alone)
//   cards [{id, image|page, x, y, w, rx, ry, rz, aspect, front?}]  more cards on the stage, each its own face and pose
//   trace {card, from, to, label?}  a rect of a side card tied to a rect of the hero's face — "this came from there"
//   wall {images, cols?, aspect?, pick?}  a wall of thumbnails across the zone; `pick` lifts one out of it
//   panel {u, v, title?, rows: [[name, value]…], highlight?}  a panel opening at a place of the face (sourced data)
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, mix, relLum} from '../runtime/dna';
import {hex6} from '../runtime/hexColor';
import {measureText} from '@remotion/layout-utils';
import {TITLE_Y, contentBottom, CONTENT_TOP, CAPTION_SIZE_FRAC, CAPTION_MARGIN_FRAC, CAPTION_LEAD_CJK,
  CAPTION_LINES} from '../runtime/layout';
import {SafeZoneContext, captionBottomY, SAFE_CAPTION_SCALE} from '../runtime/safeZone';
import {CursorArrow, TapRipple} from '../runtime/gesture';
import {usePlaceGlide, useGlide} from '../runtime/glide';
import {useStageRun, lerpState, actor, sinceEvent, springSum, moveShare, State, Normalize} from '../runtime/stageRun';

/** The card's pose. x/y: offset of its centre from the content zone's centre, as fractions of the frame's width/height;
 *  s: scale (1 = as large as the zone allows); rx/ry/rz: degrees; aspect: width over height. */
export type CardPose = {x?: number; y?: number; s?: number; rx?: number; ry?: number; rz?: number; aspect?: number};
type Pose = Required<CardPose>;
const POSE: Pose = {x: 0, y: 0, s: 1, rx: 0, ry: 0, rz: 0, aspect: 16 / 9};
type Page = {kicker?: string; title?: string; lines?: string[]; code?: string; tone?: 'paper' | 'accent'};
type Face = {image?: string; page?: Page; aspect?: number};
type Rect = [number, number, number, number];
type Mark = {rect: Rect; label?: string};
type Lift = {rect: Rect; z?: number};
type Cursor = {u: number; v: number; click?: boolean};
type Camera = {zoom?: number; u?: number; v?: number};
type Count = {value: number; from?: number; label?: string; u?: number; v?: number};
/** another card on the stage beside the hero: its own face and pose, in the same coordinates (x/y from the zone's
 *  centre as fractions of the frame, w its width as a fraction of the frame's width) */
type SideCard = {id: string; image?: string; page?: Page; imageAspect?: number; fit?: 'cover' | 'contain'; x?: number;
  y?: number; w?: number; rx?: number; ry?: number; rz?: number; aspect?: number; front?: boolean};
/** the same thing in two places: a rect on a side card (`from`) tied to a rect on the hero's face (`to`) */
type Trace = {card: string; from: Rect; to: Rect; label?: string};
/** a wall of thumbnails filling the zone; `pick` marks one */
type Wall = {images: string[]; cols?: number; aspect?: number; pick?: number};
/** a panel that opens at a place of the hero's face: a title and rows of [name, value] — the film's own data */
type Panel = {u: number; v: number; title?: string; rows: [string, string][]; highlight?: number};

// a character a line may break before or after (layout.ts keeps its own copy private: exporting it would re-key every
// register that imports layout.ts)
const CJK_CH = /[⺀-鿿豈-﫿！-｠　-〿]/;

const faceOf = (s: State): Face => ({image: typeof s.image === 'string' ? s.image : undefined,
  page: s.page as Page | undefined,
  aspect: typeof s.image === 'string' && typeof s.imageAspect === 'number' && s.imageAspect > 0 ? s.imageAspect : undefined});
const sameFace = (a: Face, b: Face) => a.image === b.image && JSON.stringify(a.page) === JSON.stringify(b.page);
/** A keyframe that changes the face and says nothing of the card's shape lets the card take the NEW face's shape: a
 *  shape set for the old face (`aspect`) held on under a merge, and a portrait face sat cropped in a landscape card. */
const normalize: Normalize = (merged, change) => {
  const newFace = change.image !== undefined || change.page !== undefined;
  const saysShape = !!change.card && typeof change.card === 'object' && 'aspect' in (change.card as object);
  if (!newFace || saysShape || !merged.card || typeof merged.card !== 'object') return merged;
  const {aspect: _held, ...card} = merged.card as CardPose;
  return {...merged, card};
};
/** The pose a state holds: its card's pose over the defaults, its shape the pose's own `aspect`, else the face's. */
const poseOf = (s: State): Pose => {
  const card = (s.card ?? {}) as CardPose;
  return {...POSE, ...card, aspect: card.aspect ?? faceOf(s).aspect ?? POSE.aspect};
};
const rectOk = (r: unknown): r is Rect => Array.isArray(r) && r.length === 4 && r.every((x) => typeof x === 'number');
/** Items of a list actor with how present each is: one only the new state has comes in with the move, one only the old
 *  state has goes out with it, one both have stays (matched by `id`, so a list can change one item at a time). */
const presence = <T,>(a: unknown, b: unknown, pIn: number, pOut: number, id: (x: T) => string): {item: T; on: number}[] => {
  const A = (Array.isArray(a) ? a : []) as T[], B = (Array.isArray(b) ? b : []) as T[];
  const inB = new Set(B.map(id)), inA = new Set(A.map(id));
  return [...A.filter((x) => !inB.has(id(x))).map((item) => ({item, on: 1 - pOut})),
    ...B.map((item) => ({item, on: inA.has(id(item)) ? 1 : pIn}))];
};

/** A point of the card's plane (x, y from its centre, z toward the viewer) turned as CSS turns it — `rotateX rotateY
 *  rotateZ scale` applies scale, then Z, then Y, then X — and put through the perspective: its offset on screen from
 *  the card's centre. */
const turn = (x0: number, y0: number, p: Pose, persp: number, z0 = 0) => {
  const rad = Math.PI / 180;
  let x = x0 * p.s, y = y0 * p.s, z = z0 * p.s;
  [x, y] = [x * Math.cos(p.rz * rad) - y * Math.sin(p.rz * rad), x * Math.sin(p.rz * rad) + y * Math.cos(p.rz * rad)];
  [x, z] = [x * Math.cos(p.ry * rad) + z * Math.sin(p.ry * rad), -x * Math.sin(p.ry * rad) + z * Math.cos(p.ry * rad)];
  [y, z] = [y * Math.cos(p.rx * rad) - z * Math.sin(p.rx * rad), y * Math.sin(p.rx * rad) + z * Math.cos(p.rx * rad)];
  const f = persp / Math.max(1, persp - z);
  return {x: x * f, y: y * f};
};
/** Half the width and height a w×h card covers on screen in pose p (its four corners turned; they are symmetric, so
 *  the extent does not depend on which way each turn goes). */
const extent = (w: number, h: number, p: Pose, persp: number) => {
  let hx = 0, hy = 0;
  for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
    const q = turn((sx * w) / 2, (sy * h) / 2, p, persp);
    hx = Math.max(hx, Math.abs(q.x));
    hy = Math.max(hy, Math.abs(q.y));
  }
  return {hx, hy};
};
const fmtNumber = (v: number, like: number) => {
  const dec = Math.min(3, (String(like).split('.')[1] ?? '').length);
  const s = Math.abs(v).toFixed(dec);
  const [i, d] = s.split('.');
  return (v < 0 ? '-' : '') + i.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (d ? '.' + d : '');
};

export const CardStage: React.FC<{
  image?: string; imageAspect?: number; page?: Page; fit?: 'cover' | 'contain'; title?: string; highlight?: string;
  card?: CardPose; cursor?: Cursor | null; marks?: Mark[] | null; lift?: Lift[] | null; camera?: Camera | null;
  backdrop?: string | null;
  count?: Count | null; steps?: unknown[]; hero?: boolean; cards?: SideCard[] | null; trace?: Trace | null;
  wall?: Wall | null; panel?: Panel | null;
}> = () => {
  const dna = useDNA();
  const now = useStageRun(normalize);
  const place = usePlaceGlide();
  // a 9:16 film for the platforms (runtime/safeZone): the title starts below the platform's tabs, the zone ends
  // above the caption (which sits above the platform's description), labels keep out of the button column
  const safeP = React.useContext(SafeZoneContext);
  const glide = useGlide();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const ink = {bg: hex6(dna?.bg ?? '#F4F5F8'), fg: dna?.fg ?? '#15161A', dim: dna?.dim ?? '#6B6E78',
    acc: dna?.accent ?? '#2B5BFF', surface: dna?.surface ?? '#FFFFFF', on: dna?.onAccent ?? '#FFFFFF'};
  const portrait = W < H;
  const {before, state, p, keys} = now;
  // ── the backdrop: the DNA colour the stage is lit in (`backdrop`: a token — bg, fg, accent, surface…), carried across a
  // move. A light studio can go dark for a showroom beat and close on the brand's accent: one continuous scene still
  // needs its exposure to MOVE (film_energy_qa's light arc), and the title, its marked word and the captions
  // (render_remotion `stageGround`) are inked for the backdrop that is actually there ──
  const backdropOf = (st: State) => {
    const tok = typeof st.backdrop === 'string' ? st.backdrop : 'bg';
    const c = (dna as unknown as Record<string, unknown> | null)?.[tok];
    return hex6(typeof c === 'string' && /^#/.test(c) ? c : ink.bg);
  };
  const ground = p >= 1 ? backdropOf(state) : hex6(mix(backdropOf(before), backdropOf(state), p));
  const dark = relLum(ground) < 0.18;
  const lightInk = relLum(ink.fg) > relLum(ink.bg) ? ink.fg : ink.bg, darkInk = lightInk === ink.fg ? ink.bg : ink.fg;
  const titleInk = relLum(ground) < 0.3 ? lightInk : darkInk;
  // the marked word's block is the accent — unless the stage itself is lit in the accent, where it takes accent2
  const onAccentGround = Math.abs(relLum(ground) - relLum(hex6(ink.acc))) < 0.02;
  const hiBg = onAccentGround ? hex6(dna?.accent2 ?? ink.on) : ink.acc;
  const hiInk = relLum(hiBg) > 0.4 ? darkInk : ink.on;

  // ── the title: one size for the whole run, at most TWO lines — the largest size at which every title fits in two and
  // its longest word in one. Widths are MEASURED in the face that draws them: forcing one line shrank every title of a
  // portrait run to a caption's size because one of them was long, and the runtime's generous estimate (0.72 em a
  // character) read a 0.39 em serif as twice its width ──
  const sx = W * 0.065;
  // big enough to be the frame's headline on a phone (a short-video title is read before anything else on it)
  const titleBase = Math.round(U * (portrait ? 0.085 : 0.066));
  const lineW = W - 2 * sx;
  const family = dna?.uniformType ? dna.fontMono : (dna?.fontDisplay ?? 'system-ui');
  // launch-film display type: line-height ~1.05-1.1, negative tracking (Apple 1.05 / -0.015em, Linear -0.022em)
  const per = (t: string) => measureText({text: t, fontFamily: family, fontSize: 100, fontWeight: '700',
    letterSpacing: '-0.02em'}).width / 100;
  const titles = [...new Set(keys.map((kf) => String(kf.state.title ?? '')).filter(Boolean))];
  const titlePx = Math.max(12, Math.floor(titles.reduce((px, t) => {
    const longestWord = Math.max(...t.split(/\s+/).filter(Boolean).map((w) => (CJK_CH.test(w) ? 0 : per(w))), 0);
    return Math.min(px, (lineW * 2 * 0.92) / Math.max(0.01, per(t)), lineW / Math.max(0.01, longestWord));
  }, titleBase)));
  const titleLines = titles.reduce((n, t) => Math.max(n, per(t) * titlePx > lineW * 0.99 ? 2 : 1), 1);

  // ── the card's zone: below the title, above the caption band ──
  const titleY = safeP ? Math.max(TITLE_Y, Math.round(safeP.top * H)) : TITLE_Y;
  const zoneTop = Math.max(CONTENT_TOP, titleY + titleLines * titlePx * 1.08 + U * 0.04);
  // the caption's top on a platform-safe film: its bottom edge (Film.tsx, the same function) less a two-line CJK block
  const safeCapTop = safeP ? captionBottomY(H, safeP, Math.round(U * CAPTION_MARGIN_FRAC))
    - CAPTION_LINES * Math.round(U * CAPTION_SIZE_FRAC * SAFE_CAPTION_SCALE) * CAPTION_LEAD_CJK : null;
  const zoneBot = (safeCapTop ?? contentBottom(W, H)) - U * 0.02;
  const zoneMid = {x: W / 2, y: (zoneTop + zoneBot) / 2};
  const side = W * (portrait ? (safeP ? Math.max(0.07, safeP.right * 0.75) : 0.07) : 0.19);

  // ── the card: one object, posed in 3D, alive while it holds ──
  // the card moves on springs that ADD UP across keyframes (runtime/stageRun springSum): front-loaded, a touch of
  // settle, and no stall when the next move begins before this one has landed
  const pose = (springSum<Pose>(now, (st) => poseOf(st), {feel: 'settle'}) ?? poseOf(state)) as Pose;
  const sec = now.frame / now.fps;
  const idle = now.reduced ? 0 : 1;
  // ALIVE WHILE IT HOLDS: three quarters of a run is held states, so the hold's own motion is most of the film's —
  // at 0.6% float and 1.2 degrees of sway a choreographed run measured under film_energy_qa's motion floor (p75 0.0031)
  const SWAY = 2.2;
  const floatY = idle * Math.sin((2 * Math.PI * sec) / 6.5) * U * 0.011;
  const sway = idle * Math.sin((2 * Math.PI * sec) / 9 + 1.1) * SWAY;
  const persp = U * 1.6;
  const centre = (q: Pose) => ({cx: W / 2 + q.x * W, cy: zoneMid.y + q.y * H});
  // the card's size in a pose: as large as the zone allows at its shape, then shrunk until the TURNED card (sway
  // included) stays inside it
  const sizeIn = (q: Pose) => {
    const {cx: x, cy: y} = centre(q);
    const a = Math.max(0.3, q.aspect);
    const room = {x: Math.max(1, Math.min(x - side, W - side - x)), y: Math.max(1, Math.min(y - zoneTop, zoneBot - y))};
    const w = Math.min(2 * room.x, 2 * room.y * a), h = w / a;
    const e = extent(w, h, {...q, ry: Math.abs(q.ry) + SWAY}, persp);
    const f = Math.min(1, room.x / e.hx, room.y / e.hy);
    return {w: w * f, h: h * f, hy: e.hy * f};
  };
  // during a move the SIZE travels between the two states' sizes: sizing each in-between shape to the zone swelled the
  // card mid-move (a squarish in-between fills the zone both ways) and shrank it back as it arrived
  const size = (springSum(now, (st) => sizeIn(poseOf(st)), {feel: 'glide'}) ?? sizeIn(poseOf(state))) as
    {w: number; h: number; hy: number};
  const {cx, cy} = centre(pose);
  const cw = size.w, ch = size.h;
  const heroW = cw;
  const live: Pose = {...pose, ry: pose.ry + sway};
  // what sits ON the face (lifted parts, marks) belongs to that face: when the face changes in the same move, the old
  // face's parts are gone before the swap at the middle of the move and the new face's arrive after it — they used
  // to fade across the swap and printed the old page's holes on the new one
  const faceNow = faceOf(state), faceBefore = faceOf(before);
  const swapping = p < 1 && !sameFace(faceBefore, faceNow);
  const pOut = swapping ? clamp01(p / 0.42) : p, pIn = swapping ? clamp01((p - 0.58) / 0.42) : p;
  // parts lifted off the face: how high each stands right now (they rise with the move that lifts them)
  const rid = (x: {rect: Rect}) => JSON.stringify(x.rect);
  const pct = (x: number) => `${x * 100}%`;
  const lifts = presence<Lift>(before.lift, state.lift, pIn, pOut, rid).filter((x) => rectOk(x.item.rect) && x.on > 0);
  const depth = U * 0.07;
  const liftOf = (x: {item: Lift; on: number}) => (x.item.z ?? 1) * depth * easeOutCubic(x.on);
  /** a place on the face → where it is on screen (before the camera) — on top of a lifted part when it is on one, so
   *  a cursor clicks the part that has risen, not the page under it */
  const onScreen = (u: number, v: number) => {
    const z = Math.max(0, ...lifts.filter(({item: {rect: rc}}) => u >= rc[0] && u <= rc[2] && v >= rc[1] && v <= rc[3])
      .map(liftOf));
    const q = turn((u - 0.5) * cw, (v - 0.5) * ch, live, persp, z);
    return {x: cx + q.x, y: cy + floatY + q.y};
  };
  const r = U * 0.014;
  const transform = `translate(${cx - cw / 2}px, ${cy + floatY - ch / 2}px) perspective(${persp}px) ` +
    `rotateX(${pose.rx}deg) rotateY(${pose.ry + sway}deg) rotateZ(${pose.rz}deg) scale(${pose.s})`;

  // ── the camera: lean in on a place of the face. At zoom 1 nothing moves; by zoom 2 that place sits at the middle of
  // the zone ──
  // a camera that comes in leans from where it would be at zoom 1, and one that goes away settles back to it
  // it leans in on springs that add up, and lands 0.2 s before its keyframe (a click lands on a camera that is already
  // there — the open screen-demo tools all start the zoom before the click; references/craft-research.md §1)
  const cam = (springSum<Camera>(now, (st) => (st.camera ? {zoom: 1, u: 0.5, v: 0.5, ...(st.camera as Camera)} : {zoom: 1}),
    {feel: 'glide', lead: Math.round(now.fps * 0.2)}) ?? {zoom: 1}) as Camera;
  const zoom = Math.max(1, cam.zoom ?? 1);
  const focus = onScreen(cam.u ?? 0.5, cam.v ?? 0.5);
  const pull = clamp01(zoom - 1);
  const fade = U * 0.035;
  const viewport = `linear-gradient(180deg, transparent ${zoneTop - fade}px, #000 ${zoneTop + fade}px, ` +
    `#000 ${zoneBot - fade}px, transparent ${zoneBot + fade * 0.5}px)`;
  const camX = focus.x + (zoneMid.x - focus.x) * pull - focus.x * zoom;
  const camY = focus.y + (zoneMid.y - focus.y) * pull - focus.y * zoom;
  /** a place on the face → where it is in the FRAME, the camera included. What points at the card — the cursor, a
   *  name, a count — is drawn outside the camera at its own size and kept inside the frame there: drawn inside it, a
   *  name was placed for the unzoomed card and then pushed past the frame's edge by the zoom */
  const onView = (u: number, v: number) => {
    const q = onScreen(u, v);
    return zoom > 1 ? {x: camX + q.x * zoom, y: camY + q.y * zoom} : q;
  };
  const viewCx = zoom > 1 ? camX + cx * zoom : cx;
  /** a point of the camera's world → where it is in the frame */
  const toView = (q: {x: number; y: number}) => (zoom > 1 ? {x: camX + q.x * zoom, y: camY + q.y * zoom} : q);

  // ── the hero can leave the stage to the others (a wall, side cards) and come back ──
  const heroOn = (before.hero === false ? 0 : 1) + ((state.hero === false ? 0 : 1) - (before.hero === false ? 0 : 1)) * p;

  // ── side cards: each its own face and pose, keyed by id; one that stays moves between its poses ──
  const sideOf = (st: State) => (Array.isArray(st.cards) ? (st.cards as SideCard[]) : [])
    .filter((c) => c && typeof c.id === 'string');
  const sides = presence<SideCard>(before.cards, state.cards, p, p, (c) => c.id).map(({item, on}) => {
    const a = sideOf(before).find((c) => c.id === item.id), b = sideOf(state).find((c) => c.id === item.id);
    const c = (a && b && p < 1 ? lerpState(a, b, p) : item) as SideCard;
    const asp = Math.max(0.3, c.aspect ?? (c.image && c.imageAspect ? c.imageAspect : 16 / 9));
    let w = (c.w ?? 0.45) * W, h = w / asp;
    if (h > (zoneBot - zoneTop) * 0.96) { h = (zoneBot - zoneTop) * 0.96; w = h * asp; }
    const pose: Pose = {x: c.x ?? 0, y: c.y ?? 0, s: 1, rx: c.rx ?? 0, ry: (c.ry ?? 0) + sway, rz: c.rz ?? 0, aspect: asp};
    return {c, on, w, h, cx: W / 2 + pose.x * W, cy: zoneMid.y + pose.y * H, pose};
  });
  type SideG = (typeof sides)[number];
  /** a place on a side card's face → where it is in the frame */
  const onSide = (g: SideG, u: number, v: number) => {
    const q = turn((u - 0.5) * g.w, (v - 0.5) * g.h, g.pose, persp);
    return toView({x: g.cx + q.x, y: g.cy + floatY + q.y});
  };

  // ── the wall: thumbnails across the zone, arriving one after another; `pick` lifts one out of the rest ──
  const wallA = before.wall as Wall | undefined, wallB = state.wall as Wall | undefined;
  const wall = wallB ?? wallA;
  const wallOn = wallA && wallB ? 1 : wallB ? p : wallA ? 1 - p : 0;
  const wallCells = (() => {
    if (!wall || !Array.isArray(wall.images) || !wall.images.length || wallOn <= 0) return [];
    const n = wall.images.length, cols = Math.max(1, Math.min(n, Math.round(wall.cols ?? (portrait ? 3 : 4))));
    const rows = Math.ceil(n / cols), asp = Math.max(0.3, wall.aspect ?? 16 / 9);
    // a wall of pages is type: on a platform-safe film it keeps out of the button column (both sides, to stay centred)
    const gap = U * 0.018, availW = W * (portrait ? (safeP ? 1 - 2 * safeP.right : 0.88) : 0.76), availH = zoneBot - zoneTop;
    let w = (availW - gap * (cols - 1)) / cols, h = w / asp;
    if (rows * h + gap * (rows - 1) > availH) { h = (availH - gap * (rows - 1)) / rows; w = h * asp; }
    const x0 = W / 2 - (cols * w + gap * (cols - 1)) / 2, y0 = zoneMid.y - (rows * h + gap * (rows - 1)) / 2;
    const pa = typeof wallA?.pick === 'number' ? wallA.pick : undefined, pb = typeof wallB?.pick === 'number' ? wallB.pick : undefined;
    const pick = pb === undefined ? (p < 0.5 ? pa : undefined) : pa === undefined ? (p >= 0.5 ? pb : undefined)
      : Math.round(pa + (pb - pa) * p);
    return wall.images.map((img, i) => ({img, i, x: x0 + (i % cols) * (w + gap), y: y0 + Math.floor(i / cols) * (h + gap), w, h,
      a: easeOutCubic(clamp01(wallOn * 1.8 - (i / n) * 0.8)), picked: pick === i, dim: pick !== undefined && pick !== i}));
  })();

  // ── the face. A face that changes is swapped at the middle of the move, where the card travels fastest: a cross-fade
  // across the whole move read as a double exposure, and fading out through the card's surface blinked the card to the
  // ground's colour on a dark DNA ──
  const fit = (state.fit as 'cover' | 'contain' | undefined) ?? 'cover';
  const drawFace = (f: Face, cw: number = heroW, fitAs: 'cover' | 'contain' = fit) => f.image ? (
    <Img src={staticFile(f.image)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: fitAs,
      display: 'block'}} />
  ) : f.page ? (
    // a page the card draws reads at the card's own size — its type was 2.8% of the card's width, under the floor on a
    // portrait film's card — and keeps its words exactly as given: no case is forced (a command or a name is copy)
    // `tone: accent` floods the card with the film's accent (a closing card); `code` is a command set in the mono face
    // on its own plate, exactly as written — copied off the screen it has to work
    <div style={{position: 'absolute', inset: 0, padding: cw * 0.07, boxSizing: 'border-box', overflowWrap: 'anywhere',
      display: 'flex', flexDirection: 'column', justifyContent: f.page.tone === 'accent' ? 'center' : 'flex-start',
      background: f.page.tone === 'accent' ? ink.acc : undefined}}>
      {f.page.kicker ? <div style={{color: f.page.tone === 'accent' ? (dna?.accent2 ?? ink.on) : ink.acc,
        font: `700 ${Math.round(cw * 0.034)}px/1.25 var(--f-body, system-ui)`, letterSpacing: '0.04em'}}>{f.page.kicker}</div> : null}
      {f.page.title ? <div style={{color: f.page.tone === 'accent' ? ink.on : ink.fg, marginTop: cw * 0.02,
        font: `800 ${Math.round(cw * 0.075)}px/1.12 var(--f-display, system-ui)`}}>{f.page.title}</div> : null}
      {(f.page.lines ?? []).map((l, i) => <div key={i} style={{color: f.page.tone === 'accent' ? ink.on : ink.dim,
        marginTop: cw * 0.03, opacity: f.page.tone === 'accent' ? 0.85 : 1,
        font: `500 ${Math.round(cw * 0.042)}px/1.35 var(--f-body, system-ui)`}}>{l}</div>)}
      {f.page.code ? <div style={{marginTop: cw * 0.05, alignSelf: 'flex-start', maxWidth: '100%', boxSizing: 'border-box',
        padding: `${cw * 0.022}px ${cw * 0.03}px`, borderRadius: cw * 0.018,
        background: f.page.tone === 'accent' ? 'rgba(0,0,0,0.28)' : mix(ink.fg, ink.surface, 0.92),
        color: f.page.tone === 'accent' ? ink.on : ink.fg, overflowWrap: 'anywhere',
        font: `600 ${Math.round(cw * 0.038)}px/1.3 var(--f-mono, ui-monospace, monospace)`}}>{f.page.code}</div> : null}
    </div>
  ) : null;
  const faceLayer = (f: Face, opacity: number) => (
    <div style={{position: 'absolute', inset: 0, opacity, background: ink.surface}}>{drawFace(f)}</div>
  );

  // ── marks: a box on the face, and its name beside it. A box inside a lifted part rises with the part (drawn on the
  // page under it, the part covered it) ──
  const marks = presence<Mark>(before.marks, state.marks, pIn, pOut, rid).filter((x) => rectOk(x.item.rect) && x.on > 0);
  const stroke = Math.max(2, Math.round(U * 0.004));
  const tileOf = (rc: Rect) => lifts.find(({item: {rect: t}}) => rc[0] >= t[0] - 1e-6 && rc[1] >= t[1] - 1e-6 &&
    rc[2] <= t[2] + 1e-6 && rc[3] <= t[3] + 1e-6)?.item;
  /** a mark's box, placed within `inside` (the face, or the lifted part it sits on) */
  const markBox = (m: Mark, on: number, inside: Rect) => {
    const iw = inside[2] - inside[0], ih = inside[3] - inside[1];
    return <div key={`m${rid(m)}`} style={{position: 'absolute', left: pct((m.rect[0] - inside[0]) / iw),
      top: pct((m.rect[1] - inside[1]) / ih), width: pct((m.rect[2] - m.rect[0]) / iw),
      height: pct((m.rect[3] - m.rect[1]) / ih), border: `${stroke}px solid ${ink.acc}`, borderRadius: stroke * 2,
      background: `${hex6(ink.acc)}1f`, boxSizing: 'border-box', opacity: on, transform: `scale(${1.06 - 0.06 * on})`}} />;
  };

  // ── the cursor: on a place of the face; it comes in from below-right, and a click lands as it arrives ──
  const cb = before.cursor as Cursor | undefined, cs = state.cursor as Cursor | undefined;
  // a pointer is spring-chased and settles 0.15 s before its click; it leans into its travel (up to 12 degrees)
  const cursorAt = (frame?: number) => springSum<Cursor>(now, (st) => (st.cursor && typeof (st.cursor as Cursor).u === 'number'
    ? {u: (st.cursor as Cursor).u, v: (st.cursor as Cursor).v} as Cursor : undefined),
    {feel: 'glide', lead: Math.round(now.fps * 0.15), frame});
  const cursorNow = cursorAt();
  const cursorPrev = cursorAt(now.frame - 1);
  const tilt = cursorNow && cursorPrev && !now.reduced
    ? Math.max(-12, Math.min(12, (cursorNow.u - cursorPrev.u) * cw * 0.9)) : 0;
  let cursor: {x: number; y: number; o: number} | null = null;
  if (cursorNow && typeof cursorNow.u === 'number' && typeof cursorNow.v === 'number') {
    const at = onView(cursorNow.u, cursorNow.v);
    const entering = !cb && cs, leaving = cb && !cs;
    const k = entering ? 1 - p : leaving ? p : 0;
    // a place the camera has pushed out of the content zone has no cursor on it (it would sit over the caption)
    const seen = zoom <= 1.001 || (at.y >= zoneTop && at.y <= zoneBot);
    cursor = {x: at.x + k * U * 0.12, y: at.y + k * U * 0.16, o: (entering ? p : leaving ? 1 - p : 1) * (seen ? 1 : 0)};
  }
  const clickKey = (q: State) => !!(q.cursor && (q.cursor as Cursor).click);
  const lastClick = sinceEvent(now, clickKey);
  const curKey = keys[now.ki];
  const toClick = clickKey(curKey.props) && now.frame <= curKey.to ? curKey.to - now.frame : null;
  const pressFrames = Math.max(2, Math.round(now.fps * 0.1));
  const press = toClick !== null ? clamp01(1 - toClick / pressFrames)
    : lastClick && lastClick.f < pressFrames * 2 ? 1 - lastClick.f / (pressFrames * 2) : 0;
  const rippleU = lastClick ? lastClick.f / Math.max(1, Math.round(now.fps * 0.55)) : -1;
  const clicked = lastClick ? (lastClick.props.cursor as Cursor) : null;
  const clickAt = clicked && typeof clicked.u === 'number' && typeof clicked.v === 'number'
    ? onView(clicked.u, clicked.v) : null;

  // ── the count: a figure counting to its value beside a place of the face ──
  const countNow = actor<Count>(now, 'count');
  const countIn = !before.count && state.count ? p : before.count && !state.count ? 1 - p : 1;
  const countShown = countNow && typeof countNow.value === 'number'
    ? (!before.count && state.count ? (countNow.from ?? 0) + (countNow.value - (countNow.from ?? 0)) * p : countNow.value)
    : null;

  // ── the title line: the old one leaves in the first part of the move, then the new one arrives — never both ──
  const curTitle = String(state.title ?? ''), prevTitle = String(before.title ?? '');
  const changed = p < 1 && prevTitle !== curTitle;
  const inP = changed ? clamp01((p - 0.38) / 0.62) : 1;
  const outP = changed ? 1 - clamp01(p / 0.36) : 0;
  const titleLine = (text: string, hi: string | undefined, q: number, leaving: boolean) => {
    if (!text) return null;
    const chars = [...text];
    const at = hi ? text.indexOf(hi) : -1;
    const hiFrom = at >= 0 ? [...text.slice(0, at)].length : -1, hiTo = at >= 0 ? hiFrom + [...hi!].length : -1;
    const nHi = Math.max(1, hiTo - hiFrom);
    // characters arrive left to right; then the marked word's block SWEEPS across it, one character after the next,
    // so it reads as one block growing (each character growing its own block at once read as a row of stripes) and
    // carries on over a line break; a character turns to the on-accent ink once the block is under it
    const sweep = leaving ? nHi : easeInOutCubic(clamp01(q * 1.4 - 0.3)) * nHi;
    const glyph = (c: string, i: number) => {
      const a = leaving ? 1 : easeOutCubic(clamp01(q * 1.6 - (i / Math.max(1, chars.length)) * 0.6));
      const fill = i >= hiFrom && i < hiTo ? clamp01(sweep - (i - hiFrom)) : -1;
      // the rise carries the baseline unlock over the arrival (runtime/glide): its slow tail stepped whole pixels
      return <span key={i} style={{position: 'relative', zIndex: 0, display: 'inline-block', whiteSpace: 'pre', opacity: a,
        transform: glide(`translateY(${(1 - a) * titlePx * 0.3}px)`, !leaving && q < 1),
        color: fill > 0.5 ? hiInk : titleInk}}>
        {fill > 0 ? <span style={{position: 'absolute', left: -titlePx * 0.03, right: -titlePx * 0.03, top: '8%', bottom: '2%',
          background: hiBg, zIndex: -1, transformOrigin: 'left center', transform: `scaleX(${fill})`}} /> : null}
        {c}
      </span>;
    };
    // where a line may break: between words, at any CJK character — never inside a word (each character is its own
    // box, and a browser breaks between any two boxes, so a word is held together in one)
    const tokens: React.ReactNode[] = [];
    let word: React.ReactNode[] = [];
    const flush = () => { if (word.length) tokens.push(<span key={`w${tokens.length}`} style={{display: 'inline-block',
      whiteSpace: 'nowrap'}}>{word}</span>); word = []; };
    chars.forEach((c, i) => {
      if (/\s/.test(c) || CJK_CH.test(c)) { flush(); tokens.push(glyph(c, i)); } else word.push(glyph(c, i));
    });
    flush();
    return (
      // a leaving line rises by a TRANSFORM with the unlock — moved by `top` it stepped whole pixels (text_safe --glide)
      <div style={{position: 'absolute', left: sx, top: titleY, width: lineW,
        transform: leaving ? glide(`translateY(${-(1 - q) * U * 0.03}px)`, true) : undefined,
        opacity: leaving ? q : 1, color: titleInk, font: `700 ${titlePx}px/1.08 var(--f-display, system-ui)`,
        letterSpacing: '-0.02em'}}>
        {tokens}
      </div>
    );
  };

  // ── a name beside a place: a pill on the side of the card with more room, joined to the place by a short line ──
  const labelPx = Math.round(U * 0.034);
  /** Where a pw×ph thing goes beside a box on screen: right or left of it (the side its centre leans to first), else
   *  above or below it — the first place that stays in the frame and off the box — with the two ends of the line that
   *  joins them (a: on the box, b: on the thing). */
  const spotNear = (box: {x0: number; y0: number; x1: number; y1: number}, pw: number, ph: number) => {
    const gap = U * 0.045, margin = W * 0.03, top = zoneTop - U * 0.02, bottom = zoneBot;
    const midX = (box.x0 + box.x1) / 2, midY = (box.y0 + box.y1) / 2;
    // the right edge a thing may reach at height y: the frame's margin, or — on a platform-safe film, beside the
    // button column — the column's left edge
    const rightAt = (y: number) => (safeP && y + ph > H * safeP.rightFrom ? W * (1 - safeP.right) : W - margin);
    const clampX = (x: number, y: number) => Math.min(Math.max(x, margin), rightAt(y) - pw);
    const clampY = (y: number) => Math.min(Math.max(y, top), bottom - ph);
    type Spot = {x: number; y: number; ax: number; ay: number; bx: number; by: number; ok: boolean};
    const ry = clampY(midY - ph / 2);
    const right: Spot = {x: box.x1 + gap, y: ry, ax: box.x1, ay: midY, bx: box.x1 + gap, by: midY,
      ok: box.x1 + gap + pw <= rightAt(ry)};
    const left: Spot = {x: box.x0 - gap - pw, y: clampY(midY - ph / 2), ax: box.x0, ay: midY, bx: box.x0 - gap, by: midY,
      ok: box.x0 - gap - pw >= margin};
    const ay = box.y0 - gap * 0.6 - ph, by = box.y1 + gap * 0.6;
    const above: Spot = {x: clampX(midX - pw / 2, ay), y: ay, ax: midX, ay: box.y0, bx: midX,
      by: box.y0 - gap * 0.6, ok: ay >= top};
    const below: Spot = {x: clampX(midX - pw / 2, by), y: by, ax: midX, ay: box.y1, bx: midX,
      by: box.y1 + gap * 0.6, ok: by + ph <= bottom};
    const order = midX >= viewCx ? [right, left, above, below] : [left, right, above, below];
    return order.find((o) => o.ok) ?? {...right, x: clampX(right.x, right.y)};
  };
  /** A name for a part of the face: a pill beside the part's box on screen — right or left of it (the side its centre
   *  leans to first), else above or below it — the first place that stays in the frame and off the part, joined to the
   *  part by a short line. In a portrait frame the card is nearly as wide as the frame, so beside it there is no room
   *  and a pill set there covered the very part it named. */
  const pill = (key: string, box: {x0: number; y0: number; x1: number; y1: number}, text: string, on: number,
    big?: string, bigRange?: string[], badge?: boolean) => {
    const bodyFamily = dna?.uniformType ? dna.fontMono : (dna?.fontBody ?? 'system-ui');
    const bigPx = Math.round(labelPx * 1.9);
    const wText = text ? measureText({text, fontFamily: bodyFamily, fontSize: labelPx, fontWeight: '700'}).width : 0;
    // a counting figure is measured at its WIDEST, so the plate holds one size while it counts — re-measured each
    // frame, the plate (and the name under the figure) re-laid itself as the digits changed
    const wBig = Math.max(0, ...(bigRange ?? (big !== undefined ? [big] : [])).map((b) => measureText({text: b,
      fontFamily: family, fontSize: bigPx, fontWeight: '800'}).width));
    const padY = labelPx * 0.3, padX = labelPx * 0.55;
    const pw = Math.max(wText, wBig) + 2 * padX, ph = (text ? labelPx * 1.2 : 0) + (big !== undefined ? bigPx * 1.05 : 0) + 2 * padY;
    // a BADGE has no place on the hero to point at (the hero has left the stage): it stands at the title's right end
    const at = badge ? {x: W - W * 0.065 - pw, y: titleY, ax: 0, ay: 0, bx: 0, by: 0} : spotNear(box, pw, ph);
    const len = badge ? 0 : Math.hypot(at.bx - at.ax, at.by - at.ay), ang = Math.atan2(at.by - at.ay, at.bx - at.ax);
    return (
      <React.Fragment key={key}>
        <div style={{position: 'absolute', left: at.ax, top: at.ay - stroke / 2, width: len, height: stroke,
          background: ink.acc, opacity: on, transformOrigin: '0 50%', transform: `rotate(${ang}rad) scaleX(${on})`}} />
        {/* placed by a translate that carries the baseline unlock (runtime/glide): the card floats while it holds,
            so a name on it crawls under a pixel a frame, and type moved by left/top stepped a whole pixel at a time
            (text_safe_qa --glide: '可编辑' stepped 4px over 43 frames) */}
        <div style={{position: 'absolute', ...place(!now.reduced, at.x, at.y, `scale(${0.94 + 0.06 * on})`),
          width: pw, height: ph, boxSizing: 'border-box', transformOrigin: `${at.bx - at.x}px ${at.by - at.y}px`,
          opacity: on, background: ink.acc, color: ink.on, borderRadius: labelPx * 0.4, padding: `${padY}px ${padX}px`,
          whiteSpace: 'nowrap', boxShadow: `0 ${U * 0.006}px ${U * 0.02}px ${dark ? 'rgba(0,0,0,0.5)' : mix(ink.fg, ink.bg, 0.8)}`}}>
          {big !== undefined ? <div style={{font: `800 ${bigPx}px/1.05 var(--f-display, system-ui)`,
            fontVariantNumeric: 'tabular-nums lining-nums'}}>{big}</div> : null}
          {text ? <div style={{font: `700 ${labelPx}px/1.2 var(--f-body, system-ui)`}}>{text}</div> : null}
        </div>
      </React.Fragment>
    );
  };
  const boxPts = (pts: {x: number; y: number}[]) => ({x0: Math.min(...pts.map((q) => q.x)), y0: Math.min(...pts.map((q) => q.y)),
    x1: Math.max(...pts.map((q) => q.x)), y1: Math.max(...pts.map((q) => q.y))});
  const poly = (pts: {x: number; y: number}[]) => pts.map((q) => `${q.x},${q.y}`).join(' ');

  // ── trace: the same thing in two places — a box on a side card, a box on the hero, a line drawn between them ──
  const traceOf = (st: State) => (st.trace && typeof st.trace === 'object' ? [st.trace as Trace] : []);
  const traceArt = presence<Trace>(traceOf(before), traceOf(state), p, p, (t) => JSON.stringify(t))
    .filter(({item, on}) => on > 0 && rectOk(item.from) && rectOk(item.to) && sides.some((g) => g.c.id === item.card))
    .map(({item, on}) => {
      const g = sides.find((x) => x.c.id === item.card)!;
      const [a0, b0, a1, b1] = item.from, [c0, d0, c1, d1] = item.to;
      const fp = [onSide(g, a0, b0), onSide(g, a1, b0), onSide(g, a1, b1), onSide(g, a0, b1)];
      const tp = [onView(c0, d0), onView(c1, d0), onView(c1, d1), onView(c0, d1)];
      const fb = boxPts(fp), tb = boxPts(tp);
      // the line leaves the side card's box on the side facing the hero's box, and lands on the hero's box
      const down = (tb.y0 + tb.y1) / 2 > (fb.y0 + fb.y1) / 2;
      const s0 = {x: (fb.x0 + fb.x1) / 2, y: down ? fb.y1 : fb.y0}, e0 = {x: (tb.x0 + tb.x1) / 2, y: down ? tb.y0 : tb.y1};
      const dy = e0.y - s0.y;
      return {key: JSON.stringify(item), on, fp, tp, tb, label: item.label, draw: clamp01(on * 1.4 - 0.2),
        path: `M ${s0.x} ${s0.y} C ${s0.x} ${s0.y + dy * 0.5}, ${e0.x} ${e0.y - dy * 0.5}, ${e0.x} ${e0.y}`};
    });

  // ── panel: a panel opening at a place of the hero's face — its title and rows are the film's own data ──
  const panelA = before.panel as Panel | undefined, panelB = state.panel as Panel | undefined;
  const panel = panelB ?? panelA;
  // a panel is what a click OPENS: it comes in after its keyframe has landed (the click), never on the way to it — it
  // used to fade in with the move toward the click and was open before the cursor had pressed
  const opened = sinceEvent(now, (q) => !!q.panel);
  const panelOn = panelB ? (panelA && (!opened || opened.f > Math.round(now.fps * 0.35)) ? 1
    : opened ? moveShare(opened.f, Math.round(now.fps * 0.3), now.fps) : 0) : panelA ? 1 - p : 0;
  const panelArt = (() => {
    if (!panel || !Array.isArray(panel.rows) || !panel.rows.length || panelOn <= 0 ||
        typeof panel.u !== 'number' || typeof panel.v !== 'number') return null;
    const rowPx = Math.round(labelPx * 0.95), rowH = rowPx * 1.75, headH = panel.title ? rowPx * 2.1 : 0;
    const pad = rowPx * 0.7, pw = W * (portrait ? 0.62 : 0.3), ph = headH + panel.rows.length * rowH + pad * 2;
    const at0 = onView(panel.u, panel.v);
    return {sp: spotNear({x0: at0.x, y0: at0.y, x1: at0.x, y1: at0.y}, pw, ph), pw, ph, rowPx, rowH, headH, pad};
  })();

  /** the screen box of a rect of the face (its four corners carried through the pose) */
  const boxOf = (rc: Rect) => {
    const pts = [onView(rc[0], rc[1]), onView(rc[2], rc[1]), onView(rc[2], rc[3]), onView(rc[0], rc[3])];
    return {x0: Math.min(...pts.map((q) => q.x)), y0: Math.min(...pts.map((q) => q.y)),
      x1: Math.max(...pts.map((q) => q.x)), y1: Math.max(...pts.map((q) => q.y))};
  };

  // ── the stage: the film's own ground, lit where the card stands (lighter on a light ground, a soft lift on a dark
  // one — a mix toward white on a dark ground turned the whole top of the frame grey) ──
  const glow = dark ? mix(ground, '#ffffff', 0.08) : mix(ground, '#ffffff', 0.6);
  const rim = dark ? ground : mix(ground, '#000000', 0.035);
  const shadowTop = Math.min(cy + size.hy * 0.96, zoneBot - U * 0.03);
  const cardShadow = dark ? 'rgba(0,0,0,0.55)' : mix(ink.fg, ink.bg, 0.75);
  const sideCard = (g: SideG) => {
    const e = easeOutCubic(g.on);
    const t = `translate(${g.cx - g.w / 2}px, ${g.cy + floatY - g.h / 2 + (1 - e) * U * 0.04}px) perspective(${persp}px) ` +
      `rotateX(${g.pose.rx}deg) rotateY(${g.pose.ry}deg) rotateZ(${g.pose.rz}deg) scale(${0.96 + 0.04 * e})`;
    return <div key={`c${g.c.id}`} style={{position: 'absolute', left: 0, top: 0, width: g.w, height: g.h, transform: t,
      transformOrigin: 'center center', opacity: g.on, borderRadius: r, overflow: 'hidden', background: ink.surface,
      boxShadow: `0 ${U * 0.02}px ${U * 0.06}px ${cardShadow}, 0 0 0 1px ${mix(ink.fg, ink.bg, 0.88)}`}}>
      {drawFace({image: g.c.image, page: g.c.page}, g.w, g.c.fit ?? 'cover')}
    </div>;
  };
  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 55% at 50% ${(zoneMid.y / H) * 100}%, ` +
      `${glow} 0%, ${ground} 72%, ${rim} 100%)`}}>
      {/* while the camera leans in, what it shows stays inside the content zone, its edges faded: the caption is inked
          for the stage's ground, not for a card pushed under it, and the title likewise */}
      <div style={{position: 'absolute', inset: 0, ...(zoom > 1.001 ? {
        WebkitMaskImage: viewport, maskImage: viewport} : {})}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0',
        transform: zoom > 1 ? `translate(${camX}px, ${camY}px) scale(${zoom})` : undefined}}>
        {wallCells.map((c) => (
          <div key={`w${c.i}`} style={{position: 'absolute', left: c.x, top: c.y, width: c.w, height: c.h, overflow: 'hidden',
            borderRadius: r * 0.6, background: ink.surface, opacity: c.a * (c.dim ? 0.5 : 1), zIndex: c.picked ? 2 : 1,
            transform: `translateY(${(1 - c.a) * U * 0.05 + idle * Math.sin((2 * Math.PI * sec) / 5.5 + c.i * 0.9) * U * 0.006}px) ` +
              `scale(${(0.96 + 0.04 * c.a) * (c.picked ? 1.1 : 1)})`,
            boxShadow: c.picked ? `0 0 0 ${stroke * 1.5}px ${ink.acc}, 0 ${U * 0.02}px ${U * 0.05}px ${cardShadow}`
              : `0 ${U * 0.008}px ${U * 0.02}px ${cardShadow}`}}>
            <Img src={staticFile(c.img)} style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block'}} />
          </div>
        ))}
        {sides.filter((g) => !g.c.front).map(sideCard)}
        {/* the card's shadow on the floor of the stage */}
        <div style={{position: 'absolute', left: cx - cw * 0.42 * pose.s, top: shadowTop, width: cw * 0.84 * pose.s,
          height: U * 0.04, borderRadius: '50%', background: dark ? '#000000' : mix(ink.fg, ink.bg, 0.6),
          opacity: (dark ? 0.6 : 0.35) * heroOn, filter: `blur(${U * 0.028}px)`}} />
        {/* opacity only while it fades: below 1 it flattens the 3D of the lifted parts */}
        <div style={{position: 'absolute', left: 0, top: 0, width: cw, height: ch, transform, transformOrigin: 'center center',
          transformStyle: 'preserve-3d', opacity: heroOn < 1 ? heroOn : undefined}}>
          {/* the face itself: a shadow is darker than the ground on any ground — a mix toward the ink was a pale halo */}
          <div style={{position: 'absolute', inset: 0, borderRadius: r, overflow: 'hidden', background: ink.surface,
            boxShadow: `0 ${U * 0.02}px ${U * 0.06}px ${cardShadow}, 0 0 0 1px ${mix(ink.fg, ink.bg, 0.88)}`}}>
            {swapping ? faceLayer(faceBefore, 1) : null}
            {faceLayer(faceNow, swapping ? clamp01((p - 0.42) / 0.16) : 1)}
            {lifts.map(({item, on}) => (
              <div key={`h${rid(item)}`} style={{position: 'absolute', left: pct(item.rect[0]), top: pct(item.rect[1]),
                width: pct(item.rect[2] - item.rect[0]), height: pct(item.rect[3] - item.rect[1]),
                background: dark ? 'rgba(0,0,0,0.45)' : mix(ink.fg, ink.surface, 0.9), opacity: on}} />
            ))}
            {marks.filter(({item}) => !tileOf(item.rect)).map(({item, on}) => markBox(item, on, [0, 0, 1, 1]))}
          </div>
          {lifts.map(({item, on}) => {
            const [u0, v0, u1, v1] = item.rect;
            // a part on its way down is a part of the face it rose from (cropped from the new face it went blank)
            const going = !(Array.isArray(state.lift) && (state.lift as Lift[]).some((x) => rid(x) === rid(item)));
            const ownFace = going ? faceBefore : faceNow;
            return (
              <div key={`l${rid(item)}`} style={{position: 'absolute', left: u0 * cw, top: v0 * ch, width: (u1 - u0) * cw,
                height: (v1 - v0) * ch, overflow: 'hidden', borderRadius: r * 0.5, background: ink.surface,
                transform: `translateZ(${liftOf({item, on})}px)`,
                boxShadow: `0 ${U * 0.012 * on}px ${U * 0.04 * on}px ${cardShadow}`}}>
                <div style={{position: 'absolute', left: -u0 * cw, top: -v0 * ch, width: cw, height: ch}}>{drawFace(ownFace)}</div>
                {marks.filter(({item: m}) => tileOf(m.rect) === item).map(({item: m, on: mo}) => markBox(m, mo, item.rect))}
              </div>
            );
          })}
        </div>
        {sides.filter((g) => g.c.front).map(sideCard)}
      </div>
      </div>
        {marks.filter(({item}) => item.label).map(({item, on}) => pill(`p${rid(item)}`, boxOf(item.rect), item.label!, on))}
        {traceArt.length ? (
          <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
            {traceArt.map((t) => (
              <g key={t.key} opacity={t.on}>
                <polygon points={poly(t.fp)} fill={`${hex6(ink.acc)}22`} stroke={ink.acc} strokeWidth={stroke} strokeLinejoin="round" />
                <polygon points={poly(t.tp)} fill={`${hex6(ink.acc)}22`} stroke={ink.acc} strokeWidth={stroke} strokeLinejoin="round" />
                <path d={t.path} fill="none" stroke={ink.acc} strokeWidth={stroke * 1.2} strokeLinecap="round" pathLength={1}
                  strokeDasharray="1 1" strokeDashoffset={1 - t.draw} />
              </g>
            ))}
          </svg>
        ) : null}
        {traceArt.filter((t) => t.label).map((t) => pill(`t${t.key}`, t.tb, t.label!, t.on))}
        {panel && panelArt ? (() => {
          const {sp, pw, ph, rowPx, rowH, headH, pad} = panelArt;
          const len = Math.hypot(sp.bx - sp.ax, sp.by - sp.ay), ang = Math.atan2(sp.by - sp.ay, sp.bx - sp.ax);
          return (
            <React.Fragment>
              <div style={{position: 'absolute', left: sp.ax, top: sp.ay - stroke / 2, width: len, height: stroke,
                background: ink.acc, opacity: panelOn, transformOrigin: '0 50%', transform: `rotate(${ang}rad) scaleX(${panelOn})`}} />
              <div style={{position: 'absolute', ...place(!now.reduced, sp.x, sp.y, `scale(${0.96 + 0.04 * panelOn})`),
                width: pw, height: ph, boxSizing: 'border-box', transformOrigin: `${sp.bx - sp.x}px ${sp.by - sp.y}px`,
                opacity: panelOn, background: ink.surface, color: ink.fg, borderRadius: rowPx * 0.5, padding: pad,
                boxShadow: `0 ${U * 0.012}px ${U * 0.04}px ${dark ? 'rgba(0,0,0,0.5)' : mix(ink.fg, ink.bg, 0.75)}, ` +
                  `0 0 0 1px ${mix(ink.fg, ink.surface, 0.85)}`}}>
                {panel.title ? <div style={{height: headH, display: 'flex', alignItems: 'center', color: ink.dim,
                  font: `700 ${rowPx}px/1.2 var(--f-body, system-ui)`, borderBottom: `1px solid ${mix(ink.fg, ink.surface, 0.88)}`,
                  boxSizing: 'border-box'}}>{panel.title}</div> : null}
                {panel.rows.map(([k, v], i) => (
                  <div key={i} style={{height: rowH, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: `0 ${rowPx * 0.4}px`, borderRadius: rowPx * 0.3,
                    background: i === panel.highlight ? `${hex6(ink.acc)}1f` : undefined,
                    color: i === panel.highlight ? ink.acc : ink.fg}}>
                    <span style={{font: `600 ${rowPx}px/1 var(--f-body, system-ui)`, whiteSpace: 'nowrap'}}>{k}</span>
                    <span style={{font: `700 ${rowPx}px/1 var(--f-mono, ui-monospace, monospace)`,
                      fontVariantNumeric: 'tabular-nums lining-nums', whiteSpace: 'nowrap'}}>{v}</span>
                  </div>
                ))}
              </div>
            </React.Fragment>
          );
        })() : null}
        {countNow && countShown !== null ? (() => {
          const at = onView(countNow.u ?? 0.92, countNow.v ?? 0.1);
          const lo = countNow.from ?? 0;
          // with the hero off the stage a count has no place on it to stand beside: it becomes the title's badge
          return pill('count', {x0: at.x, y0: at.y, x1: at.x, y1: at.y}, countNow.label ?? '', countIn,
            fmtNumber(countShown, countNow.value), [fmtNumber(lo, countNow.value), fmtNumber(countNow.value, countNow.value)],
            heroOn < 0.5);
        })() : null}
        {clickAt && rippleU > 0 && rippleU < 1 ? <TapRipple x={clickAt.x} y={clickAt.y} u={rippleU} color={ink.acc}
          size={U * 0.06} /> : null}
        {cursor ? <div style={{position: 'absolute', left: 0, top: 0, opacity: cursor.o, transformOrigin: `${cursor.x}px ${cursor.y}px`,
          transform: tilt ? `rotate(${tilt}deg)` : undefined}}><CursorArrow x={cursor.x} y={cursor.y} size={U * 0.056} press={press} /></div>
          : null}
      {outP > 0 ? titleLine(prevTitle, before.highlight as string | undefined, outP, true) : null}
      {titleLine(curTitle, state.highlight as string | undefined, inP, false)}
    </AbsoluteFill>
  );
};
