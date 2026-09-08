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

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {UiSurface, type UiPage, type UiContent} from '../runtime/uiSurface';
import {captionBand, CONTENT_TOP, fitTextPx} from '../runtime/layout';
import {focusAt, focusFilter} from '../runtime/focus';
import {leading} from '../runtime/cjkType';

export const DURATION = 120; // 4.0s

const BG_D0 = '#dfe3ea', FG_D0 = '#20242c', ACC_D0 = '#5b6b86';
const PAGES: UiPage[] = ['cards', 'chart', 'table', 'form'];

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
  surfaces?: Surface[];
  items?: string[];
  nav?: string[];
}> = ({surfaces: SURFACES, items: ITEMS = ['Overview', 'Reports', 'Records', 'Settings'],
  nav: NAV = ['Home', 'Overview', 'Reports', 'Records', 'Team', 'Settings']} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const U = Math.min(W, H);

  const labels = (ITEMS ?? []).filter((x) => String(x ?? '').trim()).slice(0, 6);
  if (!labels.length) {
    throw new Error(
      'SurfaceCarousel needs at least one non-empty `items` entry — the names of the surfaces. The whole ' +
      "form is a queue of the product's own screens stepping past; with nothing in the queue it draws an " +
      'empty corridor, which composes and argues nothing.');
  }
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
        // A CHART IS ONLY OFFERED TO A SURFACE THAT HAS DATA. `UiSurface` refuses to invent a series — right,
        // and it means an un-supplied chart page draws a baseline and a grid and nothing else. In the demo
        // that put an EMPTY WINDOW on centre stage for a third of the shot, which reads as the register
        // having failed rather than as a product with a chart in it. So the rotation skips the chart for a
        // surface that was given no `series`, and the author who has real numbers gets the chart by passing
        // them. Neither half works alone: without the pass-through the chart is unreachable, and without the
        // skip the default is an empty box.
        const wanted = PAGES[i % PAGES.length];
        const hasData = Array.isArray(s.series) && s.series.some((v) => typeof v === 'number' && isFinite(v));
        // The stand-in is the FORM page, not the table: the rotation already ends on a table, and two
        // identical-looking screens side by side in a corridor whose whole claim is "several surfaces"
        // argues against itself. cards · form · table · form has no two neighbours alike, ring included.
        const page: UiPage = s.page ?? (wanted === 'chart' && !hasData ? 'form' : wanted);
        const content: UiContent = {title: s.label, nav: s.nav ?? NAV, items: s.items, series: s.series};
        return (
          <div key={i} style={{position: 'absolute',
            left: vert ? cx + sink : cx + w, top: vert ? cy + w : cy + sink,
            transform: `translate(-50%, -50%) scale(${scale})`, opacity: fade,
            filter: focusFilter(f),
            zIndex: 1 - d > 0.5 ? 2 : 1}}>
            {/* the pill sinks FASTER than its panel, so a neighbour's label settles onto its own window
                instead of floating in the gap between two of them */}
            {s.label ? (
              <div style={{position: 'absolute', left: '50%',
                top: -(pillH + gap) + d * (vert ? panelW : panelH) * 0.045,
                transform: 'translateX(-50%)', height: pillH, display: 'flex', alignItems: 'center',
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
        );
      })}
    </AbsoluteFill>
  );
};
export default SurfaceCarousel;
