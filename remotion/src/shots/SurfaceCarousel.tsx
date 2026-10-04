// SHOT · Surface Carousel — the product's own screens queue up and step past, one at a time in the middle,
// its neighbours held at the frame edges so the queue never looks finished.
//
// WHAT IT ARGUES. "One product, several surfaces" — and specifically that they are the SAME product, seen one
// at a time. Cutting four full-screen shots says the same words and loses the claim: each cut re-establishes a
// place, and the viewer spends the first beat of every one working out where they are. A corridor holds one
// subject with a slice of its neighbours always visible, so the queue is a fact on screen rather than
// something the narration has to assert.
//
// WHY IT NEEDED A NEW PRIMITIVE, AND NOT A NEW TECHNIQUE. This library could draw an abstraction OF a piece of
// software and could not show one: no window chrome outside the terminal, no sidebar in any of 155 registers.
// The carousel is a dozen lines of arithmetic; the missing part was the SUBJECT. `runtime/uiSurface` is that
// subject, and it takes the topic's own nav and card titles rather than grey bars, so this stays a shot about
// a product instead of a shot about a wireframe.
//
// WHAT KIND OF SCREEN A SURFACE IS, IS THE FILM'S CALL. Each surface without a `page` used to get one by its
// POSITION — `PAGES[i % PAGES.length]`, so the second surface was a chart (or, lacking data, a form), the third
// a table, the fourth a form, whatever they were called. A film naming its surfaces 「首页 · 订单 · 设置」 got
// 订单 drawn as a settings form and 设置 as a table of rows: claims about what each screen looks like that the
// film never made. A surface now shows the page it is given; one given a real `series` and no page shows it
// as the chart (dropping the film's numbers would be worse); every other surface gets the SAME neutral page,
// the cards overview, so no two surfaces are told apart by anything but their names. The standalone demo keeps
// its cards · form · table · form rotation in its own data.
//
// AND EVERY SURFACE GETS CENTRE STAGE. The queue silently kept the first six names (`.slice(0, 6)`) and dropped
// the rest, and the corridor steps only three times, so a fifth or sixth surface was never the subject — only
// ever a blurred sliver at the edge. Four is what three steps bring to centre stage; past it the register
// throws. An empty name used to be filtered out too, which quietly shifted every later `surfaces[i]` onto the
// wrong name; it throws now.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {UiSurface, type UiPage, type UiContent} from '../runtime/uiSurface';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {focusAt, focusFilter} from '../runtime/focus';
import {leading} from '../runtime/cjkType';
import {useGlide} from '../runtime/glide';

export const DURATION = 120; // 4.0s

const BG_D0 = '#dfe3ea', FG_D0 = '#20242c', ACC_D0 = '#5b6b86';
// the one page a surface gets when the film names no page and gives no series — the same for every surface
const NEUTRAL_PAGE: UiPage = 'cards';
const DEFAULT_ITEMS = ['Overview', 'Reports', 'Records', 'Settings'];
// the standalone demo's own page per surface, used only while the demo's own names are showing and no
// `surfaces` were passed. (It was the old position rotation with its chart swapped for a form: the demo has no
// series, and an empty chart on centre stage reads as a broken register.)
const DEMO_PAGES: UiPage[] = ['cards', 'form', 'table', 'form'];
export const MAX_SURFACES = 4;

// THREE BEATS, NOT A CONSTANT SCROLL. A carousel that slides at one speed reads as a screensaver; three
// discrete steps read as someone moving through a list. The first carries a long tail so the shot opens
// softer than it closes — the same trick a rack of slides has when the first push is the hesitant one.
const BEATS = [
  {at: 0.200, run: 0.185, tail: 0.28},
  {at: 0.483, run: 0.150, tail: 0},
  {at: 0.688, run: 0.150, tail: 0},
];

// ONE PROP PER JOB. `items` names the surfaces — always, in every form of this register — and `surfaces`
// only says what each panel SHOWS. They were interchangeable once, and that made `items`' demo default
// unknowable statically: supplied through `surfaces`, the default never printed; not supplied, six English
// labels shipped onto a Chinese frame. The gate that hunts exactly that could not tell the two apart and
// errored on every correct beat, which is worse than the bug — an author's only way out was to switch a
// prop off. A prop whose default may or may not be read is a prop with two meanings.
export type Surface = {page?: UiPage; items?: string[]; nav?: string[]; series?: number[]};

export const SurfaceCarousel: React.FC<{
  // @supersedes surfaces: items, nav
  surfaces?: Surface[];
  items?: string[];
  nav?: string[];
}> = ({surfaces: SURFACES, items: ITEMS = DEFAULT_ITEMS,
  nav: NAV = ['Home', 'Overview', 'Reports', 'Records', 'Team', 'Settings']} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const U = Math.min(W, H);

  if (!Array.isArray(ITEMS) || !ITEMS.length) {
    throw new Error(
      'SurfaceCarousel needs at least one non-empty `items` entry — the names of the surfaces. The whole ' +
      "form is a queue of the product's own screens stepping past; with nothing in the queue it draws an " +
      'empty corridor, which composes and argues nothing.');
  }
  if (ITEMS.length > MAX_SURFACES) {
    throw new Error(`SurfaceCarousel takes at most ${MAX_SURFACES} surfaces (got ${ITEMS.length}). The corridor steps three ` +
      'times, so four surfaces reach centre stage; a fifth would only ever be a blurred sliver at the edge. Split ' +
      'the surfaces across two beats.');
  }
  ITEMS.forEach((x, i) => {
    if (!String(x ?? '').trim()) {
      throw new Error(`SurfaceCarousel: surface ${i + 1} has an empty name — every surface in \`items\` needs one ` +
        '(an empty entry used to be skipped, which put every later `surfaces[i]` under the wrong name).');
    }
  });
  const labels = ITEMS.map((x) => String(x).trim());
  const demo = ITEMS === DEFAULT_ITEMS && SURFACES === undefined;
  const list = labels.map((label, i): Surface & {label: string} => ({label, ...(SURFACES?.[i] ?? {})}));
  const n = list.length;

  // ROOM FIRST, THEN THE PANEL. The pills ride above the panels and the caption band is not the shot's, so
  // the panel is whatever is left — sized from that zone rather than from a fraction of the frame, which is
  // how a 16:9 composition ends up hanging into the subtitle at 9:16.
  const band = H - captionBand(W, H);
  const pillPx = list.reduce(
    (px, s) => Math.min(px, fitTextPx(String(s.label ?? ''), W * 0.24, Math.round(U * 0.036), {usable: 1.0})),
    Math.round(U * 0.036));
  const pillH = Math.round(pillPx * 2.0);
  const gap = Math.round(U * 0.030);
  // THE CORRIDOR TURNS IN PORTRAIT, for the reason a rail does: it is a ROW, and a row in a 9:16 frame either
  // runs off both edges or shrinks until it is a stamp in the middle of nothing. Held horizontal here the
  // panel came out 562px wide in a 1920-tall frame and used a quarter of it. Stepping the queue UPWARD keeps
  // the argument exactly — one subject at a time, more of it visible at both edges — and spends the axis the
  // frame actually has.
  const vert = W / H < 0.95;
  const zoneTop = CONTENT_TOP + pillH + gap;
  const zoneH = Math.max(Math.round(U * 0.2), band - zoneTop - gap);
  // An app window is a landscape object. Sized to the frame alone it turns into a tall slab in portrait and
  // stops reading as a screen at all, so the width is capped by what the available cross-axis can carry.
  const panelW = Math.round(vert ? W * 0.80 : Math.min(W * 0.52, zoneH * 1.55));
  const panelH = Math.round(vert ? panelW / 1.55 : Math.min(zoneH, panelW / 1.55));
  // Upright, pitch < panel width so neighbours' edges always overlap the frame. Standing up, the pitch has to
  // clear the pill as well, or every label lands on the window above it.
  const SP = Math.round(vert ? panelH + pillH * 0.75 + gap : panelW * 0.92);
  const RING = SP * n;

  // The track: three eased steps, the first blended with a slower curve so 15% of its travel arrives late.
  // `seg` returns a RAW 0→1 ramp and takes no easing — the curve is applied around it. Written the other way
  // (`seg(t, a, b, easeInOutCubic)`) the argument is silently dropped, nothing errors, and every beat runs
  // linear: the corridor still steps, still lands, and simply has no acceleration. It cost a render and a
  // node probe to see, because there is no typecheck in this project to say the call has the wrong arity.
  const trackX = BEATS.reduce((x, b) => x + SP * (b.tail
    ? 0.85 * easeInOutCubic(seg(t, b.at, b.at + b.run)) + 0.15 * easeOutCubic(seg(t, b.at, b.at + b.tail))
    : easeInOutCubic(seg(t, b.at, b.at + b.run))), 0)
    // and it opens mid-move: the corridor is already settling when the shot starts, so the first frame is
    // never a still photograph of a queue that has not begun.
    - SP * 0.05 * (1 - easeOutExpo(seg(t, 0, 0.19)));

  const cx = Math.round(W / 2), cy = Math.round(zoneTop + zoneH / 2);

  // WHICH PANEL IS THE SUBJECT. The corridor's whole argument is that its neighbours are only PARTLY there —
  // a queue you can see the ends of. In portrait that means the panel above centre stage really does run off
  // the top of the frame, taking its nav labels with it, and the type-safety gate reported exactly that: 8
  // strings cut off at 9:16. The gate is right and so is the composition, which is what the bleed exemption
  // exists for.
  //
  // But the exemption is put on the NEIGHBOURS only, never on the panel the shot is about. Marked wholesale
  // this register would stop being audited at all, and the one frame that matters — the screen on centre
  // stage, the one the viewer is asked to read — is precisely the one that must never bleed.
  const offsets = list.map((_, i) => ((trackX - i * SP) % RING + RING * 1.5) % RING - RING / 2);
  // the corridor moves until its last beat lands; its words carry the unlock that long
  const trackEnd = Math.max(...BEATS.map((b) => b.at + Math.max(b.run, b.tail)));
  const moving = t < trackEnd;
  const glide = useGlide();
  // WHERE EACH SURFACE COMES TO REST, on whole pixels. As `left`/`top` the browser rounded its place to the pixel;
  // as a translate it would rest at the sub-pixel, and every settled frame would move by up to half a pixel. So the
  // last beat eases each surface's place onto the rounded one, and the corridor lands exactly where it always did —
  // never rounded on the landing frame, which would be a half-pixel jump.
  const last = BEATS[BEATS.length - 1];
  const landing = easeInOutCubic(seg(t, last.at, trackEnd));
  const restOf = (i: number) => {
    const wEnd = ((SP * BEATS.length - i * SP) % RING + RING * 1.5) % RING - RING / 2;
    const sEnd = Math.min(1, Math.abs(wEnd) / SP) * (vert ? panelW : panelH) * 0.30;
    const pEnd = Math.min(1, Math.abs(wEnd) / SP) * (vert ? panelW : panelH) * 0.045;   // its pill's sink
    return vert ? [cx + sEnd, cy + wEnd, pEnd] : [cx + wEnd, cy + sEnd, pEnd];
  };
  const subject = offsets.reduce((best, w, i) => (Math.abs(w) < Math.abs(offsets[best]) ? i : best), 0);

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {list.map((s, i) => {
        // Wrapped into a ±RING/2 window, so however far the track has run there is always a panel entering
        // each edge. A non-wrapping row empties itself at the end and the corridor stops being a corridor.
        const w = ((trackX - i * SP) % RING + RING * 1.5) % RING - RING / 2;
        const d = Math.min(1, Math.abs(w) / SP);            // 0 = centre stage, 1 = a neighbour at the edge
        // THE RECESSION IS THE SHARED LENS, not this shot's own three numbers. Scale, opacity, brightness and
        // blur were four literals here, and the next register wanting a corridor would have written a fifth
        // set — so a film's off-focus material would recede differently in every shot that had any. One
        // function means it reads as one lens. `focusAt` also darkens, which this did not: a neighbour that
        // is paler but just as bright reads as translucent rather than as further away.
        const f = focusAt(d, U);
        const scale = f.scale;
        const fade = Math.min(1, f.opacity * 1.35);        // this corridor keeps its neighbours more present
        // the neighbours fall AWAY from the axis they travel on, so the corridor has a floor as well as a
        // direction; drifting along the same axis would just read as uneven spacing.
        const sink = d * (vert ? panelW : panelH) * 0.30;
        // WHICH PAGE: the film's `page`; else the chart, if the film gave this surface a real `series` (a chart
        // is only ever offered to a surface that has data — `UiSurface` refuses to invent one, and an empty
        // chart window on centre stage reads as a broken register); else the one neutral page for every
        // surface. Only the untouched demo uses its own rotation.
        const hasData = Array.isArray(s.series) && s.series.some((v) => typeof v === 'number' && isFinite(v));
        const page: UiPage = s.page ?? (hasData ? 'chart' : demo ? DEMO_PAGES[i] : NEUTRAL_PAGE);
        const content: UiContent = {title: s.label, nav: s.nav ?? NAV, items: s.items, series: s.series};
        return (
          <div key={i}
            // data-bleed: a NEIGHBOUR in the queue, shown partly on purpose — see `subject` above. The panel
            // on centre stage carries no marker and is audited like any other shot's content.
            {...(i === subject ? {} : {'data-bleed': true})}
            // The corridor travels by TRANSLATE — as `left`/`top` every surface and every word on it moved in
            // whole pixels (layout is rounded before anything draws) — and the words carry the baseline unlock
            // INSIDE the lens's blur, until the track lands (runtime/glide.ts).
            style={{position: 'absolute', left: 0, top: 0,
            transform: `translate(${(vert ? cx + sink : cx + w) + (Math.round(restOf(i)[0]) - restOf(i)[0]) * landing}px, `
              + `${(vert ? cy + w : cy + sink) + (Math.round(restOf(i)[1]) - restOf(i)[1]) * landing}px) `
              + `translate(-50%, -50%) scale(${scale})`,
            opacity: fade,
            filter: focusFilter(f),
            zIndex: 1 - d > 0.5 ? 2 : 1}}>
            <div style={{transform: glide(undefined, moving)}}>
            {/* the pill sinks FASTER than its panel, so a neighbour's label settles onto its own window
                instead of floating in the gap between two of them */}
            {s.label ? (
              <div style={{position: 'absolute', left: '50%', top: -(pillH + gap),
                transform: `translate(-50%, ${d * (vert ? panelW : panelH) * 0.045
                  + (Math.round(restOf(i)[2]) - restOf(i)[2]) * landing}px)`, height: pillH,
                display: 'flex', alignItems: 'center',
                padding: `0 ${Math.round(pillH * 0.62)}px`, borderRadius: 999, whiteSpace: 'nowrap',
                color: dna?.onAccent ?? '#fff',
                // gloss is three layers, not one: a vertical ramp, an inner light top and dark bottom, and a
                // short sheen over the upper third. One gradient reads as a flat coloured lozenge.
                background: `linear-gradient(180deg, ${ACC}f2, ${ACC}, ${ACC}cc)`,
                boxShadow: `inset 0 2px 3px rgba(255,255,255,.55), inset 0 -4px 8px rgba(20,24,30,.35),`
                  + ` 0 ${Math.round(U * 0.008)}px ${Math.round(U * 0.020)}px rgba(20,24,30,.18)`,
                font: `700 ${pillPx}px/${leading(String(s.label), 1.1)} var(--f-body, system-ui, sans-serif)`}}>
                <span style={{position: 'absolute', left: '12%', right: '12%', top: '8%', height: '38%',
                  borderRadius: 999, background: 'linear-gradient(180deg, rgba(255,255,255,.42), rgba(255,255,255,0))',
                  pointerEvents: 'none'}} />
                {s.label}
              </div>
            ) : null}
            <UiSurface page={page} W={panelW} H={panelH} dna={dna} content={content} seed={i + 1} />
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default SurfaceCarousel;
