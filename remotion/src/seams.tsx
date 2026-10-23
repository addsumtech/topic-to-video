// ANCHORED SEAMS — four cuts that take hold of ONE THING on the frame, or land ONE beat.
//
//   container       the shared-element cut. An element marked in both beats (runtime/carry: `data-carry`) stays on
//                   screen while its rect FLIPs from where it sat in A to where it sits in B; the rest of A gives way
//                   to the rest of B around it. "This IS that." Material's container transform.
//   grow            the next beat opens out of an element: the anchor's own shape grows in B's ground until it
//                   covers the frame, and B arrives inside it. "This opens onto that."
//   through-window  the camera pushes into an anchor — a screen, a window — until it fills the frame, and what is
//                   in it is the next beat. "We go inside this."
//   punch           a push cut: A leans in, a hard cut at the fastest frame, B lands from slightly too close with
//                   a two-frame flash of the film's paper. The payoff, once per film.
//
// WHAT WAS SOURCED AND WHAT WAS DERIVED (references/motion-research.md §2 holds the sources). Sourced: the container
// transform keeps the container while its size and position animate, swaps its content at ~30/70, and travels on an
// arc when it travels far (Material); a zoom-through needs an EXPONENTIAL scale to read as constant speed; a push cut
// is a hard cut at 5/11 with scale 1.04 -> 1.07 and a 2-frame 0.2 flash (Remotion's pushCut, not installed here);
// cut at the fastest movement (schoolofmotion match cuts). Derived here, and said so where each number sits: the
// 12-frame window (the narration breath every seam in this film rides), the arc's stagger, the grow's timing.
//
// EVERY ONE OF THEM IS OPAQUE UNDERNEATH (E15). None fades its leaving half over nothing: the container's A stays
// opaque and B fades in over it exactly as `fade` draws; the grow, the window and the punch all draw over an opaque
// A. So none of them can open the black hole `fadethrough` and `focus` once did on a light film.
//
// AN ANCHOR IS FOUND ON THE FRAME OR THE RENDER STOPS. Each seam measures its anchor(s) in the DOM of the beat that
// carries it — both beats are mounted for the whole seam, and `useT` holds the leaving one still at t=1 and the
// arriving one at ENTRY_T, so the rect it measures is the rect on screen — and a missing or invisible anchor is a
// cancelRender naming the beat and the id, never a quiet cross-fade. validate.py refuses the same board earlier, from
// the source (scripts/carry_anchors.py); this is the check that cannot be fooled by a register that declares an
// anchor and then draws it nowhere.
import React from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, Easing, useCurrentFrame} from 'remotion';
import type {TransitionPresentation} from '@remotion/transitions';
import {clamp01, easeInOutCubic, easeOutCubic} from './runtime/motion';
import {useGlide} from './runtime/glide';
import {CONTENT_TOP, contentBottom} from './runtime/layout';

/** Inside a seam's SECOND rendering of a beat (the container's copy): the beat's voice must not play twice. */
export const SeamCopyContext = React.createContext<boolean>(false);

// WHERE EACH SEAM IS FASTEST, as a share of the seam — scripts/sfx.py reads this object (one definition) and puts the
// cue's peak there: the punch's impact on its cut, a whoosh on the frame that moves most.
//   punch           the cut itself (PUNCH_CUT)
//   through-window  the cut: the exponential push accelerates into it (WINDOW_CUT)
//   grow            the middle of its easeInOutCubic over [GROW_FILL, GROW_END] = (0.25 + 0.8) / 2
//   container       Material's standard curve cubic-bezier(0.4, 0, 0.2, 1) is fastest at x = 0.302 (computed from
//                   the curve; its largest step at 12 frames is frames 3->4)
export const SEAM_PEAK = {punch: 5 / 12, 'through-window': 0.5, grow: 0.525, container: 0.3};

// ── measuring an anchor ───────────────────────────────────────────────────────────────────────────────────────
// `outline`: the anchor element draws a box of its own (a fill, a border, a declared radius, or content inside it).
// A MARKER — an empty <CarryAnchor> whose thing is drawn by its parts — has none, and a seam that shows the anchor's
// shape shows a disc for it instead of the marker's bare rectangle.
type Box = {x: number; y: number; w: number; h: number; r: number; outline?: boolean};
type Quad = [number, number, number, number];                      // [cx, cy, w, h], fractions of the frame

/** Runs `fn` once this frame's layout is final — fonts loaded, every layout effect in both beats applied (the scene
 *  camera's edge budget sets its transform in one) — and holds the frame until it has. An exception stops the render
 *  with its message: an anchor that is not on the frame is a fault in the board or the register, never a seam to
 *  quietly draw without. Off the seam (`active` false) it runs `reset` instead, synchronously: the styles a seam
 *  writes are imperative, a render tab may draw a frame before the seam after one inside it, and a clip left over
 *  from the seam would hide a beat that is not in one. */
const useAfterLayout = (active: boolean, fn: () => void, reset: () => void) => {
  React.useLayoutEffect(() => {
    if (!active) { reset(); return; }
    let done = false;
    const handle = delayRender('anchored seam: measuring its anchor', {timeoutInMilliseconds: 20000});
    const finish = () => { if (!done) { done = true; continueRender(handle); } };
    const run = () => {
      if (done) return;
      try {
        fn();
      } catch (e) {
        done = true;
        cancelRender(e instanceof Error ? e : new Error(String(e)));
        return;
      }
      finish();
    };
    let raf1 = 0, raf2 = 0;
    const fonts = (document as any).fonts?.ready ?? Promise.resolve();
    fonts.then(() => { raf1 = requestAnimationFrame(() => { raf2 = requestAnimationFrame(run); }); });
    return () => { cancelAnimationFrame(raf1); cancelAnimationFrame(raf2); finish(); };
  });
};

/**
 * Is this half of the seam INSIDE the seam on this frame? A TransitionSeries wraps the WHOLE of each sequence in its
 * presentations, not only the overlap: the leaving beat sits in its exit presentation at progress 0 for every frame
 * before the seam, and the arriving one in its entrance at progress 1 for every frame after it. Measured: the first
 * container rendered looked for its partner on the leaving beat's first frame and found none. So the leaving half
 * asks its own clock (`lead` is the leaving unit's length, the seam its last `n` frames) and the arriving half its
 * progress (it reaches 1 the frame the seam ends). Outside it every seam here draws its beat exactly as a beat.
 */
const useInSeam = (isEnter: boolean, p: number, lead: number, n: number): boolean => {
  const f = useCurrentFrame();
  return isEnter ? p < 1 : f >= lead - n;
};

/** A half of a seam outside the seam: the beat itself, in the same wrapper the seam frames use (so nothing remounts). */
const Plain: React.FC<{seam: string; half: string; children: React.ReactNode; layer?: React.Ref<HTMLDivElement>}> =
  ({seam, half, children, layer}) => (
    <AbsoluteFill data-seam={seam} data-seam-half={half}>
      {null}
      <div ref={layer} data-seam-layer="rest" style={{position: 'absolute', inset: 0}}>{children}</div>
    </AbsoluteFill>
  );

/** The seam half's root (this presentation's own, or its partner's — both are mounted for the whole seam). */
const halfRoot = (seam: string, half: 'exiting' | 'entering'): HTMLElement | null =>
  document.querySelector(`[data-seam="${seam}"][data-seam-half="${half}"]`);

/** The corner radius an anchor is drawn with, in FRAME px: a declared `data-carry-radius` (in the element's own layout
 *  px, like its CSS), else its own CSS radius. `scale` is frame px per layout px; a percentage resolves on the box. */
const radiusOf = (el: Element, scale: number, w: number, h: number): number => {
  const declared = el.getAttribute('data-carry-radius');
  if (declared !== null && declared !== '' && Number.isFinite(Number(declared))) return Number(declared) * scale;
  const v = getComputedStyle(el).borderTopLeftRadius || '0';
  const first = v.split(' ')[0];
  if (first.endsWith('%')) return (parseFloat(first) / 100) * Math.min(w, h);
  return (parseFloat(first) || 0) * scale;
};

/** How much of the anchor a viewer can see: its own opacity times every ancestor's, up to `stop`. Visibility is
 *  read on the element alone — it is inherited, so the element's own value already says whether it paints, and an
 *  ancestor may be hidden while the element is turned back on (the container's copy does exactly that). */
const shownOpacity = (el: Element, stop: Element): number => {
  if (getComputedStyle(el).visibility === 'hidden') return 0;
  let o = 1;
  for (let n: Element | null = el; n && n !== stop; n = n.parentElement) {
    const cs = getComputedStyle(n);
    if (cs.display === 'none') return 0;
    o *= parseFloat(cs.opacity || '1');
  }
  return o;
};

/**
 * The anchor `id` in one half of a seam, as a box in FRAME px, measured with that half's own seam transform taken
 * off (so either half measures the same rect whatever the other has done to its layer this frame).
 *
 * `where` names the beat for the error. `copy` is the layer the visibility check reads — the rest layer hides a
 * container's anchor on purpose, so a check there would always fail.
 */
const anchorBox = (seam: string, half: 'exiting' | 'entering', id: string, W: number, where: string): Box => {
  const root = halfRoot(seam, half);
  if (!root) throw new Error(`seam ${seam}: the ${half} half is not mounted — cannot measure '${id}'`);
  const layer = root.querySelector(':scope > [data-seam-layer="rest"]') as HTMLElement | null;
  if (!layer) throw new Error(`seam ${seam}: the ${half} half has no rest layer`);
  const el = layer.querySelector(`[data-carry="${id}"]`);
  if (!el) {
    throw new Error(`a ${where} seam needs the anchor '${id}' (data-carry="${id}") on the ${half === 'exiting' ?
      'leaving' : 'arriving'} beat, and that beat's frame has none. The register does not draw it, or it is hidden ` +
      `on this beat. Name an anchor the register draws (scripts/carry_anchors.py lists them), or choose another seam.`);
  }
  const saved = layer.style.transform;
  layer.style.transform = 'none';
  // and the seam's own styles off while it looks: they hide the anchor on purpose (a container's place it leaves, a
  // word fading under its window), and the visibility check below asks what the BEAT draws, not what the seam does
  const sheets = Array.from(root.querySelectorAll('style[data-seam-style]'))
    .map((st) => (st as HTMLStyleElement).sheet).filter((sh): sh is CSSStyleSheet => Boolean(sh));
  sheets.forEach((sh) => { sh.disabled = true; });
  const frame = root.getBoundingClientRect();
  const r = el.getBoundingClientRect();
  layer.style.transform = saved;
  if (!(frame.width > 0)) throw new Error(`seam ${seam}: the frame has no size yet`);
  const k = W / frame.width;
  const box: Box = {x: (r.left - frame.left) * k, y: (r.top - frame.top) * k, w: r.width * k, h: r.height * k, r: 0};
  if (!(box.w > 2 && box.h > 2)) {
    throw new Error(`the anchor '${id}' on the ${half === 'exiting' ? 'leaving' : 'arriving'} beat of a ${where} ` +
      `seam has no size on the frame (${box.w.toFixed(1)}x${box.h.toFixed(1)} px) — it is not drawn there.`);
  }
  // frame px per layout px: the anchor may sit under a camera, a stage's pose or a platform-safe frame's scale
  const layoutW = (el as HTMLElement).offsetWidth;
  box.r = radiusOf(el, layoutW > 0 ? box.w / layoutW : k, box.w, box.h);
  const cs = getComputedStyle(el);
  const painted = !/rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\)|transparent/.test(cs.backgroundColor)
    || parseFloat(cs.borderTopWidth || '0') > 0 || cs.backgroundImage !== 'none';
  box.outline = painted || el.childElementCount > 0 || el.hasAttribute('data-carry-radius');
  // THE ANCHOR MUST BE SEEN, not merely present. A register that reveals its anchor after the seam draws it at
  // opacity 0 on the arriving beat's held frame, and a container landing there would land on nothing; such a register
  // reads runtime/carry `useCarried` and draws the anchor in place. Read on the copy layer when there is one (the
  // rest layer hides a container's anchor on purpose), else on the rest layer itself.
  const copy = root.querySelector(':scope > [data-seam-layer="copy"]');
  const probe = copy ? copy.querySelector(`[data-carry="${id}"]`) : el;
  const shown = probe ? shownOpacity(probe, copy ?? layer) : 0;
  sheets.forEach((sh) => { sh.disabled = false; });
  if (shown < 0.5) {
    throw new Error(`the anchor '${id}' on the ${half === 'exiting' ? 'leaving' : 'arriving'} beat of a ${where} seam ` +
      `is drawn at opacity ${shown.toFixed(2)} on the seam's frames — a seam cannot carry what is not on screen. ` +
      (half === 'entering' ? 'The register must draw it in place when it arrives by a container (runtime/carry useCarried).'
        : 'The leaving beat has already hidden it by its last frame.'));
  }
  return box;
};

const f2 = (v: number) => (Math.round(v * 100) / 100).toString();
/** A rounded rect as an SVG path (clockwise), radius clamped to the rect. */
const roundRect = (x: number, y: number, w: number, h: number, r: number): string => {
  const R = Math.max(0, Math.min(r, w / 2, h / 2));
  if (R < 0.01) return `M${f2(x)} ${f2(y)}H${f2(x + w)}V${f2(y + h)}H${f2(x)}Z`;
  return `M${f2(x + R)} ${f2(y)}H${f2(x + w - R)}A${f2(R)} ${f2(R)} 0 0 1 ${f2(x + w)} ${f2(y + R)}` +
    `V${f2(y + h - R)}A${f2(R)} ${f2(R)} 0 0 1 ${f2(x + w - R)} ${f2(y + h)}H${f2(x + R)}` +
    `A${f2(R)} ${f2(R)} 0 0 1 ${f2(x)} ${f2(y + h - R)}V${f2(y + R)}A${f2(R)} ${f2(R)} 0 0 1 ${f2(x + R)} ${f2(y)}Z`;
};

/** The smallest scale of a rounded rect (half-size hw x hh, radius r) about (cx, cy) that covers the whole W x H
 *  frame, corners included. The corner test is the rounded rect's own: a point past the straight edges must be inside
 *  the corner's circle. Bisection, because a closed form for the four corners at once is not worth its bugs. */
const coverScale = (cx: number, cy: number, hw: number, hh: number, r: number, W: number, H: number): number => {
  const inside = (g: number) => [[0, 0], [W, 0], [0, H], [W, H]].every(([X, Y]) => {
    const dx = Math.abs(X - cx), dy = Math.abs(Y - cy);
    const a = g * hw, b = g * hh, rr = Math.min(g * r, a, b);
    if (dx > a || dy > b) return false;
    if (dx <= a - rr || dy <= b - rr) return true;
    return (dx - (a - rr)) ** 2 + (dy - (b - rr)) ** 2 <= rr * rr;
  });
  let lo = 0, hi = 1;
  while (!inside(hi)) hi *= 2;
  for (let i = 0; i < 40; i++) { const m = (lo + hi) / 2; if (inside(m)) hi = m; else lo = m; }
  return hi;
};

// ── container ─────────────────────────────────────────────────────────────────────────────────────────────────
// Material's STANDARD curve (FastOutSlowIn) — the container transform's own. Fastest at 30% of the seam.
const STANDARD = Easing.bezier(0.4, 0, 0.2, 1);
// THE CONTENT SWAP, 30/70 (Material): the container shows A's element for the first 30% of its travel, then B's
// fades in over it while A's fades out under it. It needs no surface colour of its own: it is always one of the two
// beats' own pixels.
const SWAP_A = 0.3, SWAP_B = 0.8;
// how much of the seam the anchor takes to leave its place, and to arrive at the other (see the hide rule)
const PART_FADE = 0.2;
// THE ARC. A long diagonal travel on one curve is a straight line, which Carbon calls out as harsh (motion-grammar,
// "Two-axis moves"); staggering the two axes' starts turns it into a rounded corner. LONG and DIAGONAL are judged
// here: past 18% of the frame's short side, and with at least a fifth of the travel on the minor axis — below either,
// the stagger reads as a wobble rather than an arc (derived, not sourced). The major axis leads.
const ARC_MIN_TRAVEL = 0.18, ARC_MIN_MINOR = 0.2, ARC_LAG = 0.15;

type ContainerSpec = {seam: string; from?: string; to?: string; fromQuad?: Quad; toQuad?: Quad; radius?: number;
  W: number; H: number; lead: number; n: number};

/** The container's rect at progress p, between A's box and B's. Pure. */
export const containerAt = (p: number, a: Box, b: Box, W: number, H: number): Box => {
  const e = STANDARD(clamp01(p));
  const acx = a.x + a.w / 2, acy = a.y + a.h / 2, bcx = b.x + b.w / 2, bcy = b.y + b.h / 2;
  const dx = bcx - acx, dy = bcy - acy, dist = Math.hypot(dx, dy);
  let ex = e, ey = e;
  if (dist > ARC_MIN_TRAVEL * Math.min(W, H) && Math.min(Math.abs(dx), Math.abs(dy)) > ARC_MIN_MINOR * dist) {
    const lead = STANDARD(clamp01(p / (1 - ARC_LAG))), lag = STANDARD(clamp01((p - ARC_LAG) / (1 - ARC_LAG)));
    if (Math.abs(dx) >= Math.abs(dy)) { ex = lead; ey = lag; } else { ey = lead; ex = lag; }
  }
  const w = a.w + (b.w - a.w) * e, h = a.h + (b.h - a.h) * e;
  const cx = acx + dx * ex, cy = acy + dy * ey;
  return {x: cx - w / 2, y: cy - h / 2, w, h, r: a.r + (b.r - a.r) * e};
};

/** The transform that lays `src` (a box on its own beat's frame) over `dst`, covering it, centre on centre. */
const coverInto = (src: Box, dst: Box): {s: number; tx: number; ty: number} => {
  const s = Math.max(dst.w / src.w, dst.h / src.h);
  return {s, tx: dst.x + dst.w / 2 - s * (src.x + src.w / 2), ty: dst.y + dst.h / 2 - s * (src.y + src.h / 2)};
};

const quadBox = (q: Quad, W: number, H: number, r: number): Box =>
  ({x: (q[0] - q[2] / 2) * W, y: (q[1] - q[3] / 2) * H, w: q[2] * W, h: q[3] * H, r});

/** Both ends of a container, measured (anchors) or declared (a match_cut's rects). */
const containerEnds = (P: ContainerSpec): {a: Box; b: Box} => {
  if (P.fromQuad && P.toQuad) {
    const r = P.radius ?? 0;
    return {a: quadBox(P.fromQuad, P.W, P.H, r), b: quadBox(P.toQuad, P.W, P.H, r)};
  }
  if (!P.from || !P.to) throw new Error(`container seam ${P.seam} names no anchor and no rects`);
  return {a: anchorBox(P.seam, 'exiting', P.from, P.W, 'container'),
          b: anchorBox(P.seam, 'entering', P.to, P.W, 'container')};
};

const ContainerPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const P = passedProps as ContainerSpec;
  const isEnter = presentationDirection === 'entering';
  const half = isEnter ? 'entering' : 'exiting';
  const id = isEnter ? P.to : P.from;
  const rest = React.useRef<HTMLDivElement>(null), clip = React.useRef<HTMLDivElement>(null);
  const move = React.useRef<HTMLDivElement>(null);
  const glide = useGlide();
  const on = useInSeam(isEnter, p, P.lead, P.n);
  useAfterLayout(on, () => {
    const {a, b} = containerEnds(P);
    const c = containerAt(p, a, b, P.W, P.H);
    const own = isEnter ? b : a;
    const m = coverInto(own, c);
    if (move.current) move.current.style.transform =
      glide(`translate(${f2(m.tx)}px, ${f2(m.ty)}px) scale(${m.s.toFixed(5)})`, true) ?? '';
    if (clip.current) clip.current.style.clipPath = `path('${roundRect(c.x, c.y, c.w, c.h, c.r)}')`;
  }, () => undefined);
  if (!on) return <Plain seam={P.seam} half={half} layer={rest}>{children}</Plain>;
  // THE CONTENT SWAP (Material's 30/70): B's element fades in over A's from SWAP_A to SWAP_B, and A's — still
  // drawn under it — fades out over all of the remaining 70%. Each copy is ONLY its element (below), so the space
  // around it is never a box: what is between the elements' pixels is the two beats' rest, crossing as `fade`.
  // A'S EXIT IS SPREAD, NOT LEFT TO THE END. The first build held A's element opaque until B's was whole and
  // dropped it over the last fifth: on the probe's dark stage card carried into a light figure, a third of the
  // frame went dark-to-light in two frames, a 39-level step in the frame mean against the fade's 18.
  const op = isEnter ? clamp01((p - SWAP_A) / (SWAP_B - SWAP_A)) : 1 - clamp01((p - SWAP_A) / (1 - SWAP_A));
  const scope = `[data-seam="${P.seam}"][data-seam-half="${half}"]`;
  const anchorSel = (layer: string) => id ? [`[data-carry="${id}"]`, `[data-carry-part="${id}"]`]
    .map((x) => `${scope} > [data-seam-layer="${layer}"] ${x}`) : [];
  return (
    <AbsoluteFill data-seam={P.seam} data-seam-half={half}>
      {/* the anchor leaves its place in the rest of its beat: the container IS that element now. It (and its parts)
          go over the container's first PART_FADE of travel and come back over its last, while the container still
          covers them — a part reaching outside the anchor's rect (a device's drop shadow) would otherwise blink
          off on the seam's first frame and on again after its last */}
      {id ? <style data-seam-style="">{anchorSel('rest').join(', ') +
        ` { opacity: ${(isEnter ? clamp01((p - (1 - PART_FADE)) / PART_FADE) : 1 - clamp01(p / PART_FADE)).toFixed(3)}` +
        ' !important; }'}</style> : null}
      {/* THE COPY IS THE ELEMENT, NOT A RECTANGLE OF THE FRAME. The first build copied the whole region under the
          anchor's rect, and a figure that stands on the ground (no box of its own) came across as a hard-edged panel
          of the leaving beat's ground drifting over the arriving one — measured on the probe's dark->light figure
          seam as a dark rectangle in the middle of a lightening frame. `visibility` is inherited and can be turned
          back on below: everything in the copy is hidden except the anchor, its parts and what they contain. A
          board's match_cut rects name a REGION, not an element, so they keep the region. */}
      {id ? <style data-seam-style="">{`${scope} > [data-seam-layer="copy"] * { visibility: hidden !important; } ` +
        anchorSel('copy').flatMap((x) => [x, `${x} *`]).join(', ') + ' { visibility: visible !important; }'}</style>
        : null}
      {/* the rest: A opaque underneath, B fading in over it exactly as `fade` draws it */}
      <div ref={rest} data-seam-layer="rest" style={{position: 'absolute', inset: 0, opacity: isEnter ? p : 1}}>
        {children}
      </div>
      {/* the container: a second rendering of the beat, moved onto the container's rect and clipped to it. It is the
          same type the rest layer holds, so the text gates count it once (data-echo); its voice is muted
          (SeamCopyContext). It sits ABOVE both beats' rests (z-index — Film isolates the film's layer while a
          container is on screen, so it cannot rise over the caption), the arriving copy over the leaving one. */}
      <div ref={clip} data-seam-layer="copy" data-echo="seam-container" aria-hidden="true"
        style={{position: 'absolute', inset: 0, opacity: op, zIndex: 2}}>
        <div ref={move} style={{position: 'absolute', inset: 0, transformOrigin: '0 0'}}>
          <SeamCopyContext.Provider value={true}>{children}</SeamCopyContext.Provider>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** A container between two anchors (`from` on the leaving beat, `to` on the arriving one) or two declared rects. */
export const container = (spec: ContainerSpec): TransitionPresentation<any> =>
  ({component: ContainerPresentation, props: spec});

// ── grow ──────────────────────────────────────────────────────────────────────────────────────────────────────
// THE ANCHOR FILLS FIRST, THEN OPENS. Over [0, GROW_FILL] the anchor's own outline fills with the arriving beat's
// ground; then that shape grows about its centre to the frame's far corner by GROW_END and holds; the arriving
// beat's picture comes in over its ground inside the shape from GROW_IN_A to GROW_IN_B, so the ground leads and the
// picture follows ("revealed under it"). Derived for a 12-frame seam (3 frames to fill, ~7 to open). The first build
// grew the shape from NOTHING at the anchor's centre: rendered, it read as a box wipe that happened to start on the
// window, not as the window opening — the anchor's outline is what says which thing this beat came out of.
const GROW_FILL = 0.25, GROW_END = 0.8, GROW_IN_A = 0.4, GROW_IN_B = 0.9;

type GrowSpec = {seam: string; from: string; ground?: string; W: number; H: number; lead: number; n: number};

const GrowPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const P = passedProps as GrowSpec;
  const isEnter = presentationDirection === 'entering';
  const half = isEnter ? 'entering' : 'exiting';
  const shape = React.useRef<HTMLDivElement>(null), fill = React.useRef<HTMLDivElement>(null);
  const on = useInSeam(isEnter, p, P.lead, P.n);
  useAfterLayout(on && isEnter, () => {
    const m = anchorBox(P.seam, 'exiting', P.from, P.W, 'grow');
    const cx = m.x + m.w / 2, cy = m.y + m.h / 2;
    // a MARKER anchor (no box of its own — a figure standing on the ground) opens as a DISC inscribed in its box:
    // measured on the seam probe, its bare layout rectangle filled with the next ground read as a box wipe
    const d = Math.min(m.w, m.h);
    const a = m.outline ? m : {x: cx - d / 2, y: cy - d / 2, w: d, h: d, r: d / 2};
    // THE ANCHOR'S OWN SHAPE, grown about its centre until it covers the frame: a disc anchor is a disc the whole
    // way, a card a rounded card, and the radius grows with it so a disc never squares off on the way out
    const g = coverScale(cx, cy, a.w / 2, a.h / 2, a.r, P.W, P.H) * 1.02;
    const k = 1 + (g - 1) * easeInOutCubic(clamp01((p - GROW_FILL) / (GROW_END - GROW_FILL)));
    const w = a.w * k, h = a.h * k;
    if (shape.current) shape.current.style.clipPath = `path('${roundRect(cx - w / 2, cy - h / 2, w, h, a.r * k)}')`;
    if (fill.current) fill.current.style.opacity = String(clamp01(p / GROW_FILL));
  }, () => { if (shape.current) shape.current.style.clipPath = ''; });
  if (!on || !isEnter) return <Plain seam={P.seam} half={half} layer={shape}>{children}</Plain>;
  return (
    <AbsoluteFill data-seam={P.seam} data-seam-half={half}>
      {null}
      <div ref={shape} data-seam-layer="rest" style={{position: 'absolute', inset: 0}}>
        {P.ground ? <div ref={fill} style={{position: 'absolute', inset: 0, background: P.ground}} /> : null}
        <div style={{position: 'absolute', inset: 0, opacity: clamp01((p - GROW_IN_A) / (GROW_IN_B - GROW_IN_A))}}>
          {children}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** The next beat grows out of the anchor `from` on the leaving beat, in the arriving beat's `ground`. */
export const grow = (spec: GrowSpec): TransitionPresentation<any> => ({component: GrowPresentation, props: spec});

// ── through-window ────────────────────────────────────────────────────────────────────────────────────────────
// WINDOW_CUT: the push reaches the window filling the frame at the middle of the seam — six frames in, six to settle.
// WINDOW_OVER: how far past filling the frame the window is pushed at the cut, which is the scale the arriving beat
// starts at and settles from (the research's 1.06). WINDOW_IN_A/B: the arriving beat comes up inside the window over
// the first part of the push, while the window is still small, so by the time it fills the frame it is the new beat.
const WINDOW_CUT = 0.5, WINDOW_OVER = 1.06, WINDOW_IN_A = 0.05, WINDOW_IN_B = 0.32;

type WindowSpec = {seam: string; from: string; ground?: string; W: number; H: number; lead: number; n: number};

/** Where the leaving beat is at progress p of a push toward the point (cx, cy), reaching scale K at the cut:
 *  x' = tx + k·x. The scale is EXPONENTIAL in an ease-in (constant perceived zoom rate needs an exponential; ease-in
 *  so it starts from rest and is fastest at the cut), the point travels to the frame centre in step with the zoom,
 *  and the translation is clamped so the scaled frame always covers the frame — near an edge the point cannot be
 *  centred early without uncovering the ground. */
export const pushAt = (p: number, cx: number, cy: number, K: number, W: number, H: number):
  {k: number; tx: number; ty: number; K: number} => {
  const q = clamp01(p / WINDOW_CUT);
  const k = Math.pow(K, q * q);
  const along = K > 1 ? (k - 1) / (K - 1) : 1;
  const tx = Math.min(0, Math.max(W * (1 - k), cx + (W / 2 - cx) * along - k * cx));
  const ty = Math.min(0, Math.max(H * (1 - k), cy + (H / 2 - cy) * along - k * cy));
  return {k, tx, ty, K};
};

/** A push into box `a` until it covers the frame with WINDOW_OVER to spare (never below WINDOW_OVER: an anchor as
 *  large as the frame is still pushed into, never pulled out of). */
export const windowAt = (p: number, a: Box, W: number, H: number) =>
  pushAt(p, a.x + a.w / 2, a.y + a.h / 2,
    Math.max(WINDOW_OVER, WINDOW_OVER * coverScale(W / 2, H / 2, a.w / 2, a.h / 2, a.r, W, H)), W, H);

// ── a window shaped like a WORD ────────────────────────────────────────────────────────────────────────────────
// An anchor marked `data-carry-glyph` is a line of type, and the window is its letterforms: the next beat is seen
// THROUGH the word (an SVG clipPath holding the same text, in the same face, size and tracking, where the HTML drew
// it). A box would push into the gaps between the letters as readily as into them, so the push aims at the point
// INSIDE the ink with the most room around it — the centre of the thickest stroke, found by a distance transform of
// the word drawn to a canvas — and goes until the disc of that room covers the frame: then the frame is inside a
// letter, and every pixel of it is the next beat.
type Glyph = {text: string; font: string; family: string; weight: string; style: string; size: number;
  spacing: number; x: number; baseline: number; px: number; py: number; clear: number};

/** Two-pass chamfer (3-4) distance to the nearest non-ink pixel — the room around each ink pixel. */
export const inkRoom = (ink: Uint8Array, w: number, h: number): {i: number; d: number} => {
  const D = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) D[i] = ink[i] ? 1e9 : 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (!D[i]) continue;
    let v = D[i];
    if (x > 0) v = Math.min(v, D[i - 1] + 3);
    if (y > 0) v = Math.min(v, D[i - w] + 3);
    if (x > 0 && y > 0) v = Math.min(v, D[i - w - 1] + 4);
    if (x < w - 1 && y > 0) v = Math.min(v, D[i - w + 1] + 4);
    D[i] = v;
  }
  let best = -1, bd = 0;
  for (let y = h - 1; y >= 0; y--) for (let x = w - 1; x >= 0; x--) {
    const i = y * w + x;
    if (!D[i]) continue;
    let v = D[i];
    if (x < w - 1) v = Math.min(v, D[i + 1] + 3);
    if (y < h - 1) v = Math.min(v, D[i + w] + 3);
    if (x < w - 1 && y < h - 1) v = Math.min(v, D[i + w + 1] + 4);
    if (x > 0 && y < h - 1) v = Math.min(v, D[i + w - 1] + 4);
    D[i] = v;
    if (v >= bd) { bd = v; best = i; }
  }
  return {i: best, d: bd / 3};
};

/** The glyph window of the anchor `id` on the leaving half, or null when the anchor is not marked as one. */
const glyphOf = (seam: string, id: string, W: number): Glyph | null => {
  const root = halfRoot(seam, 'exiting');
  const layer = root?.querySelector(':scope > [data-seam-layer="rest"]') as HTMLElement | null;
  const el = layer?.querySelector(`[data-carry="${id}"]`) as HTMLElement | null;
  if (!root || !layer || !el || !el.hasAttribute('data-carry-glyph')) return null;
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let tn: Node | null = walker.nextNode();
  while (tn && !(tn.textContent ?? '').trim()) tn = walker.nextNode();
  if (!tn || !tn.parentElement) throw new Error(`the glyph anchor '${id}' holds no text — a word window needs a word`);
  const saved = layer.style.transform;
  layer.style.transform = 'none';
  const frame = root.getBoundingClientRect();
  const range = document.createRange();
  range.selectNodeContents(tn);
  const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0 && r.height > 0);
  const elW = el.getBoundingClientRect().width;
  layer.style.transform = saved;
  if (!rects.length) throw new Error(`the glyph anchor '${id}' draws its text nowhere on the frame`);
  if (new Set(rects.map((r) => Math.round(r.top))).size > 1) {
    throw new Error(`the glyph anchor '${id}' wraps to more than one line — a word window is one line of type`);
  }
  const k = W / frame.width;
  const left = Math.min(...rects.map((r) => r.left)), top = Math.min(...rects.map((r) => r.top));
  const right = Math.max(...rects.map((r) => r.right)), bottom = Math.max(...rects.map((r) => r.bottom));
  const cs = getComputedStyle(tn.parentElement);
  const scale = el.offsetWidth > 0 ? (elW / el.offsetWidth) * k : k;       // frame px per layout px
  const size = parseFloat(cs.fontSize) * scale;
  const spacing = (parseFloat(cs.letterSpacing) || 0) * scale;
  let text = (tn.textContent ?? '').trim();
  if (cs.textTransform === 'uppercase') text = text.toUpperCase();
  const font = `${cs.fontStyle} ${cs.fontWeight} ${size.toFixed(2)}px ${cs.fontFamily}`;
  const x = (left - frame.left) * k, y0 = (top - frame.top) * k, w = (right - left) * k, h = (bottom - top) * k;
  // the word, drawn the same way into a canvas at a working scale, to find the stroke with the most room
  const ds = Math.min(1, 480 / Math.max(1, w));
  const cw = Math.ceil(w * ds) + 4, ch = Math.ceil(h * ds) + 4;
  const cv = document.createElement('canvas');
  cv.width = cw; cv.height = ch;
  const ctx = cv.getContext('2d');
  if (!ctx) throw new Error('no 2D canvas to measure the glyph window with');
  ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${(size * ds).toFixed(2)}px ${cs.fontFamily}`;
  (ctx as any).letterSpacing = `${(spacing * ds).toFixed(2)}px`;
  const asc = ctx.measureText(text).fontBoundingBoxAscent;
  ctx.fillStyle = '#000';
  ctx.fillText(text, 2, 2 + asc);
  const img = ctx.getImageData(0, 0, cw, ch).data;
  const ink = new Uint8Array(cw * ch);
  for (let i = 0; i < cw * ch; i++) ink[i] = img[i * 4 + 3] > 127 ? 1 : 0;
  const room = inkRoom(ink, cw, ch);
  if (room.i < 0 || room.d < 1) throw new Error(`the glyph anchor '${id}' has no ink to look through`);
  const ix = room.i % cw, iy = Math.floor(room.i / cw);
  return {text, font, family: cs.fontFamily, weight: cs.fontWeight, style: cs.fontStyle, size, spacing, x,
    baseline: y0 + asc / ds, px: x + (ix - 2) / ds, py: y0 + (iy - 2) / ds, clear: room.d / ds};
};

const WindowPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const P = passedProps as WindowSpec;
  const isEnter = presentationDirection === 'entering';
  const half = isEnter ? 'entering' : 'exiting';
  const layer = React.useRef<HTMLDivElement>(null), inner = React.useRef<HTMLDivElement>(null);
  const word = React.useRef<SVGTextElement>(null);
  const clipId = `seam-glyph-${React.useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const glide = useGlide();
  const on = useInSeam(isEnter, p, P.lead, P.n);
  const cut = p >= WINDOW_CUT;
  useAfterLayout(on, () => {
    const a = anchorBox(P.seam, 'exiting', P.from, P.W, 'through-window');
    const g = glyphOf(P.seam, P.from, P.W);
    // a word window aims at its thickest stroke, until the room around it covers the frame's half-diagonal
    const {k, tx, ty, K} = g
      ? pushAt(p, g.px, g.py, Math.max(WINDOW_OVER, WINDOW_OVER * Math.hypot(P.W / 2, P.H / 2) / g.clear), P.W, P.H)
      : windowAt(p, a, P.W, P.H);
    if (!isEnter) {
      if (layer.current) layer.current.style.transform =
        glide(`translate(${f2(tx)}px, ${f2(ty)}px) scale(${k.toFixed(5)})`, true) ?? '';
      return;
    }
    if (cut) {
      // past the cut the arriving beat is the frame: it settles from WINDOW_OVER to rest, decelerating
      const s = WINDOW_OVER + (1 - WINDOW_OVER) * easeOutCubic(clamp01((p - WINDOW_CUT) / (1 - WINDOW_CUT)));
      if (layer.current) layer.current.style.clipPath = '';
      if (inner.current) inner.current.style.transform = glide(`scale(${s.toFixed(5)})`, true) ?? '';
      return;
    }
    // before it: the window is the anchor carried by the leaving beat's push (its box, or its letterforms), and the
    // arriving beat sits inside it at the scale that reaches WINDOW_OVER exactly as the window fills the frame,
    // centred on the point the push aims at
    const s = WINDOW_OVER * k / K;
    const fx = g ? tx + k * g.px : tx + k * (a.x + a.w / 2), fy = g ? ty + k * g.py : ty + k * (a.y + a.h / 2);
    const ox = fx - s * P.W / 2, oy = fy - s * P.H / 2;
    if (g && word.current) {
      const t = word.current;
      t.textContent = g.text;
      t.setAttribute('x', f2(g.x));
      t.setAttribute('y', f2(g.baseline));
      t.setAttribute('transform', `matrix(${k.toFixed(5)} 0 0 ${k.toFixed(5)} ${f2(tx)} ${f2(ty)})`);
      t.setAttribute('style', `font: ${g.font}; letter-spacing: ${g.spacing.toFixed(2)}px; font-kerning: normal`);
      if (layer.current) layer.current.style.clipPath = `url(#${clipId})`;
    } else if (layer.current) {
      const wx = tx + k * a.x, wy = ty + k * a.y, ww = k * a.w, wh = k * a.h;
      layer.current.style.clipPath = `path('${roundRect(wx, wy, ww, wh, a.r * k)}')`;
    }
    if (inner.current) inner.current.style.transform =
      glide(`translate(${f2(ox)}px, ${f2(oy)}px) scale(${s.toFixed(5)})`, true) ?? '';
  }, () => {
    if (layer.current) { layer.current.style.transform = ''; layer.current.style.clipPath = ''; }
    if (inner.current) inner.current.style.transform = '';
  });
  if (!on) return <Plain seam={P.seam} half={half} layer={layer}>{children}</Plain>;
  if (!isEnter) {
    // PAST THE CUT THE LEAVING BEAT IS GONE, not merely covered: on a platform-safe film the arriving beat is drawn
    // in a scaled frame with faded edges, and measured on the 9:16 probe the zoomed leaving beat showed through
    // those margins until the seam ended, then vanished in one frame (frame mean 19.8 -> 14.7)
    // A WORD'S OWN INK leaves as the next beat fills its letters: the clip's letterforms and the HTML's are the same
    // face at the same size but not the same rasteriser, and measured on the glyph probe the leaving word's
    // anti-aliased edge peeked out round the clip, magnified by the push into white rims along every stroke
    const wordOp = 1 - clamp01((p - WINDOW_IN_A) / (WINDOW_IN_B - WINDOW_IN_A));
    return (
      <AbsoluteFill data-seam={P.seam} data-seam-half={half}>
        <style data-seam-style="">{`[data-seam="${P.seam}"][data-seam-half="exiting"] > [data-seam-layer="rest"] ` +
          `[data-carry="${P.from}"][data-carry-glyph] { opacity: ${wordOp.toFixed(3)} !important; }`}</style>
        <div ref={layer} data-seam-layer="rest" style={{position: 'absolute', inset: 0, transformOrigin: '0 0',
          opacity: cut ? 0 : 1}}>
          {children}
        </div>
      </AbsoluteFill>
    );
  }
  const op = cut ? 1 : clamp01((p - WINDOW_IN_A) / (WINDOW_IN_B - WINDOW_IN_A));
  return (
    <AbsoluteFill data-seam={P.seam} data-seam-half={half}>
      {/* the word window's letterforms (used only when the anchor is a glyph; an empty clipPath clips nothing in) */}
      <svg width={0} height={0} style={{position: 'absolute'}} aria-hidden="true">
        <defs><clipPath id={clipId} clipPathUnits="userSpaceOnUse"><text ref={word} /></clipPath></defs>
      </svg>
      <div ref={layer} data-seam-layer="window" style={{position: 'absolute', inset: 0, opacity: op}}>
        {/* the window shows the next beat's own ground first, so a beat smaller than the window sits on its ground */}
        {P.ground && !cut ? <div style={{position: 'absolute', inset: 0, background: P.ground}} /> : null}
        <div ref={inner} style={{position: 'absolute', inset: 0,
          transformOrigin: cut ? `50% ${f2(((CONTENT_TOP + contentBottom(P.W, P.H)) / 2 / P.H) * 100)}%` : '0 0'}}>
          {children}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** The camera pushes into the anchor `from` on the leaving beat until it fills the frame; the next beat is inside. */
export const throughWindow = (spec: WindowSpec): TransitionPresentation<any> =>
  ({component: WindowPresentation, props: spec});

// ── punch ─────────────────────────────────────────────────────────────────────────────────────────────────────
// Remotion's pushCut, transcribed for a 12-frame seam (the package version that ships it is not installed, and it is
// one curve): a hard cut at 5/12 (theirs is 5/11), the leaving beat leaning in to PUNCH_IN before it, the arriving
// beat landing from PUNCH_FROM, and a FLASH_FRAMES-frame flash of the film's paper at FLASH_OPACITY on the cut.
export const PUNCH_CUT = 5 / 12;
const PUNCH_IN = 1.04, PUNCH_FROM = 1.07, FLASH_FRAMES = 2, FLASH_OPACITY = 0.2;

type PunchSpec = {paper?: string; W: number; H: number; n: number; seam: string; lead: number};

const PunchPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const P = passedProps as PunchSpec;
  const isEnter = presentationDirection === 'entering';
  const half = isEnter ? 'entering' : 'exiting';
  const glide = useGlide();
  const on = useInSeam(isEnter, p, P.lead, P.n);
  // no measurement, but the same hook order on every frame
  useAfterLayout(false, () => undefined, () => undefined);
  if (!on) return <Plain seam={P.seam} half={half}>{children}</Plain>;
  const origin = `50% ${f2(((CONTENT_TOP + contentBottom(P.W, P.H)) / 2 / P.H) * 100)}%`;
  const cut = p >= PUNCH_CUT - 1e-9;
  if (!isEnter) {
    // eased IN: the lean accelerates into the cut, so the cut lands on the fastest frame
    const q = clamp01(p / PUNCH_CUT);
    const s = 1 + (PUNCH_IN - 1) * q * q;
    // a HARD cut: past it the leaving beat is not drawn at all (a platform-safe film's arriving frame has margins)
    return (
      <AbsoluteFill data-seam={P.seam} data-seam-half={half}>
        {null}
        <div data-seam-layer="rest" style={{position: 'absolute', inset: 0, opacity: cut ? 0 : 1,
          transform: glide(`scale(${s.toFixed(5)})`, true), transformOrigin: origin}}>{children}</div>
      </AbsoluteFill>
    );
  }
  const s = PUNCH_FROM + (1 - PUNCH_FROM) * easeOutCubic(clamp01((p - PUNCH_CUT) / (1 - PUNCH_CUT)));
  const flash = cut && p < PUNCH_CUT + FLASH_FRAMES / Math.max(1, P.n) - 1e-9;
  return (
    <AbsoluteFill data-seam={P.seam} data-seam-half={half}>
      {null}
      <div data-seam-layer="rest" style={{position: 'absolute', inset: 0, opacity: cut ? 1 : 0,
        transform: cut ? glide(`scale(${s.toFixed(5)})`, true) : undefined, transformOrigin: origin}}>{children}</div>
      {flash && P.paper ? <AbsoluteFill style={{background: P.paper, opacity: FLASH_OPACITY, pointerEvents: 'none'}} /> : null}
    </AbsoluteFill>
  );
};

/** A push cut: the payoff's one hard landing. `paper` is the film's lightest ground ink, `n` the seam's frames. */
export const punch = (spec: PunchSpec): TransitionPresentation<any> => ({component: PunchPresentation, props: spec});
