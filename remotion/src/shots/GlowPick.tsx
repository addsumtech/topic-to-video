// SHOT · Glow Pick — one light travels across a working interface, gathers into a capsule, and from where it
// lands draws the outline of the ONE element that matters. The light becomes the UI it was pointing at.
//
// WHAT IT ARGUES. "Look here" is the hardest thing a product film has to do without saying it, and the usual
// answers all cheat: cut to a close-up (and lose where you are), dim everything else (and admit the interface
// is noise), draw an arrow (and admit the picture could not carry it). A single light that crosses the whole
// surface and then RESOLVES into a border keeps the context on screen the entire time — the viewer sees the
// element in its place, and sees the frame choose it.
//
// IT IS ONE CONTINUOUS THING, WHICH IS THE WHOLE CRAFT. Roam, gather, draw, settle: four moves of the same
// light, each starting where the last one stopped. The draw begins at the capsule's own landing point rather
// than at a corner, and the stroke converges from a hot wide glow to a thin accent border, so the shot ends
// with a piece of INTERFACE rather than with an effect still playing. Break the chain anywhere — start the
// outline at a fixed corner, let the light fade before the border starts — and it reads as three unrelated
// animations that happen to be in the same shot.
//
// NO BLEND MODES. The surface sits under a `perspective`, which isolates blending: `mix-blend-mode: screen`
// comes out grey there. The light is a solid bright core with its glow thrown by box-shadow, which composites
// the same on every ground.
//
// THE PICK IS THE FILM'S, AND IT MUST LAND ON ONE OF THE FILM'S ELEMENTS. `target` defaulted to 4 and was only
// clamped to the six card RECTANGLES, never to the items. A film that gave three items and no target got the
// light, the dim and the border on the fifth card — a placeholder with no label — so the whole shot said
// "look here" at nothing. And the rectangle it aimed at is a CARD rectangle on every page: on `page: 'table'`
// the border was drawn across the middle of three rows (seen on a render), on 'form' and 'chart' likewise over
// a region that is not an element. So now:
//   * `target` has no default for a film. The standalone preview (no `items` given) still picks its demo card;
//     a film that passes `items` must say which one, as an index into them, or the register throws.
//   * the target must be a real item — an integer in 0..items-1.
//   * the pick is only offered on the `cards` page, the one page whose element geometry runtime/uiSurface
//     exports (`uiCardRects`). Other pages throw until the surface can say where their rows are.
//   * `series` (the chart page's numbers) therefore cannot reach the frame, and throws rather than vanish.
//   * six cards is the page: a seventh item, or a seventh nav entry, used to vanish without a word; it throws.
//     An empty item used to be filtered out, which silently shifted every index after it — it throws too.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {UiSurface, uiCardRects, type UiContent, type UiPage} from '../runtime/uiSurface';
import {captionBand, CONTENT_TOP, fitTextPx, fitBlockPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

// SHORT ON PURPOSE. The reference packs all four moves — rise, roam, draw, settle — into two seconds, and
// the density IS the effect: a hand-off that takes its time stops reading as one light doing four things and
// starts reading as four animations sharing a frame. Stretched to five seconds it measured among the
// quietest registers in the library, which was the number agreeing with the picture.
export const DURATION = 96; // 3.2s

const BG_D0 = '#0a0c12', FG_D0 = '#eef2f8', DIM_D0 = '#8f97a8', ACC_D0 = '#f0b429';

// The light's route, as fractions of the surface. Monotone toward the target on purpose: a path that doubles
// back reads as the light SEARCHING, and this light is not searching — the frame already knows the answer.
const ROAM: {at: number; x: number; y: number; w: number; h: number}[] = [
  {at: 0.06, x: 0.86, y: 0.22, w: 0.055, h: 0.075},
  {at: 0.20, x: 0.70, y: 0.34, w: 0.075, h: 0.080},
  {at: 0.32, x: 0.52, y: 0.48, w: 0.110, h: 0.070},
  {at: 0.44, x: 0.00, y: 0.00, w: 0.230, h: 0.045},   // x/y filled from the target below — it lands ON it
];

// The standalone preview's surface and the card it picks. The demo target applies ONLY to these demo items:
// identity (`ITEMS === DEFAULT_ITEMS`) is how the register knows no film supplied the list.
const DEFAULT_ITEMS = ['Runs', 'Queue', 'Alerts', 'Sources', 'Access', 'Audit'];
const DEMO_TARGET = 4;
export const MAX_GLOWPICK_ITEMS = 6;      // the cards page is a 3x2 grid (`uiCardRects`)
export const MAX_GLOWPICK_NAV = 6;        // the surface's sidebar draws six entries

export const GlowPick: React.FC<{
  screen?: string;
  items?: string[];
  nav?: string[];
  page?: UiPage;
  /** the chart page's numbers. The chart page cannot be picked from (only `cards` exposes element geometry),
   *  so passing `series` THROWS rather than accept numbers that would never reach the frame. */
  series?: number[];
  /** index into `items` of the ONE element the light picks — required whenever the film passes `items` */
  target?: number | null;
  note?: string;
}> = ({screen: SCREEN = 'Overview', items: ITEMS = DEFAULT_ITEMS,
  nav: NAV = ['Home', 'Overview', 'Runs', 'Sources', 'Team', 'Settings'],
  page: PAGE = 'cards', series: SERIES, target: TARGET = null, note: NOTE = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0;
  const U = Math.min(W, H);

  if (!Array.isArray(ITEMS) || ITEMS.length < 1) {
    throw new Error(
      'GlowPick needs at least one `items` entry. The whole form is a light choosing ONE element ' +
      'out of a working interface; with an empty interface it draws a border around nothing, which composes ' +
      'and argues nothing.');
  }
  if (ITEMS.length > MAX_GLOWPICK_ITEMS) {
    throw new Error(`GlowPick: the cards page holds ${MAX_GLOWPICK_ITEMS} cards and \`items\` has ${ITEMS.length}. ` +
      'Pass the six that frame the pick; a seventh would not be drawn.');
  }
  const list = ITEMS.map((x, i) => {
    const v = String(x ?? '').trim();
    if (!v) throw new Error(`GlowPick: items[${i}] is empty — every card the light can pick needs its title.`);
    return v;
  });
  if (Array.isArray(NAV) && NAV.length > MAX_GLOWPICK_NAV) {
    throw new Error(`GlowPick: the sidebar draws ${MAX_GLOWPICK_NAV} entries and \`nav\` has ${NAV.length}.`);
  }
  if (PAGE !== 'cards') {
    throw new Error(`GlowPick picks a CARD, and \`page: '${PAGE}'\` has no cards: runtime/uiSurface exports element ` +
      'geometry only for the cards page, so on any other page the border would be drawn around a region that is ' +
      "not an element. Use page 'cards' (the default), or a register that does not single one element out.");
  }
  if (SERIES != null) {
    // `series` fills the chart page, and the chart page cannot be picked from (above). Accepted and ignored,
    // the film's numbers would simply never reach the frame.
    throw new Error('GlowPick: `series` is drawn only on the chart page, which this register cannot aim at. ' +
      'Put the numbers in a chart register, or drop `series` here.');
  }
  const target = TARGET == null && ITEMS === DEFAULT_ITEMS ? DEMO_TARGET : TARGET;
  if (target == null) {
    throw new Error('GlowPick: pass `target` — the index into `items` of the element the light picks. Without it ' +
      'the register would have to choose one of the film\'s items itself.');
  }
  if (!Number.isInteger(target) || target < 0 || target >= list.length) {
    throw new Error(`GlowPick: \`target\` must be an index into \`items\` (0-${list.length - 1}), got ` +
      `${JSON.stringify(target)}. A pick past the last item lands on an empty placeholder card.`);
  }

  // THE SURFACE IS SIZED FROM THE ROOM LEFT AFTER THE COPY, not from a fraction of the frame — the note sits
  // under it and the caption band is not the shot's.
  const band = H - captionBand(W, H);
  const notePx = NOTE ? Math.round(U * 0.030) : 0;
  const noteH = NOTE ? Math.round(notePx * 2.6) : 0;
  const gap = Math.round(U * 0.030);
  const zoneTop = CONTENT_TOP;
  const zoneH = Math.max(Math.round(U * 0.25), band - zoneTop - gap - noteH - (NOTE ? gap : 0));
  const surfW = Math.round(Math.min(W * 0.82, zoneH * 1.62));
  const surfH = Math.round(Math.min(zoneH, surfW / 1.62));
  const sx = Math.round((W - surfW) / 2), sy = Math.round(zoneTop + (zoneH - surfH) / 2);

  // The element the light picks, from the SAME function that draws the cards — so the border lands on the
  // rectangle a card is actually in and not on a number written down twice.
  const rects = uiCardRects(surfW, surfH, true);
  const tgt = rects[target];

  // ── the four moves, each starting where the last one stopped ────────────────────────────────────────────
  const rise = easeOutCubic(clamp01(seg(t, 0, 0.12)));
  const drift = Math.sin(t * Math.PI * 1.15);            // never stops: a still surface reads as a bitmap
  const roam = (() => {
    const path = ROAM.map((k, i) => i === ROAM.length - 1
      ? {...k, x: (tgt.x + tgt.w * 0.5) / surfW, y: (tgt.y + tgt.h * 0.86) / surfH}
      : k);
    let k = path[0];
    for (let i = 0; i < path.length - 1; i++) {
      const a = path[i], b = path[i + 1];
      if (t >= a.at && t <= b.at) {
        const u = easeInOutCubic(clamp01((t - a.at) / (b.at - a.at)));
        k = {at: t, x: lerp(a.x, b.x, u), y: lerp(a.y, b.y, u),
             w: lerp(a.w, b.w, u), h: lerp(a.h, b.h, u)};
      }
    }
    if (t > path[path.length - 1].at) k = path[path.length - 1];
    return k;
  })();
  const lightOn = clamp01(seg(t, 0.03, 0.09)) * (1 - clamp01(seg(t, 0.44, 0.50)) ** 2);
  const draw = easeOutCubic(clamp01(seg(t, 0.46, 0.66)));
  const settle = easeInOutCubic(clamp01(seg(t, 0.66, 0.84)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.70, 0.86)));
  // EVERYTHING ELSE RECEDES; THE PICKED THING DOES NOT. Blurring the surface was the obvious move and it
  // blurs the target with it — the element the whole shot exists to choose came out the softest thing on the
  // frame. So the recession is a dim with a HOLE at the target instead, and it stays light: this register's
  // claim is that the context can stay on screen, and a heavy scrim concedes that the interface is noise.
  const dim = 0.30 * easeInOutCubic(clamp01(seg(t, 0.50, 0.68)))
    * (1 - 0.45 * easeInOutCubic(clamp01(seg(t, 0.84, 0.97))));

  // The outline STARTS where the light landed. Written as a fixed corner it looks identical on the frame the
  // border is complete and wrong on every frame before it — the hand-off is the point of the shot.
  const startFrac = clamp01((roam.x * surfW - tgt.x) / Math.max(1, tgt.w)) * 0.25 + 0.5;
  const content: UiContent = {title: SCREEN, nav: NAV, items: list, series: SERIES};
  // CONVERGED, NOT VANISHED. The reference converges to 1.0px on a 480-wide design stage, which is about
  // 4px at 1920 — taken literally the border thinned to 1.2px and disappeared, so the shot ended on a card
  // with nothing around it and the whole hand-off was for nothing.
  const stroke = lerp(Math.max(3, U * 0.0042), Math.max(2, U * 0.0022), settle);

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, perspective: `${Math.round(U * 1.6)}px`}}>
        <div style={{position: 'absolute', left: sx, top: sy, width: surfW, height: surfH,
          transformStyle: 'preserve-3d',
          transform: `translateY(${(1 - rise) * surfH * 0.22}px) scale(${lerp(1.16, 1, rise)}) `
            + `rotateX(${lerp(24, 3.2, rise) + drift * 0.7}deg) rotateY(${lerp(-11, 2.4, rise) + drift * 1.6}deg)`,
          opacity: rise}}>
          <UiSurface page={PAGE as UiPage} W={surfW} H={surfH} dna={dna} content={content} seed={3} />

          {/* THE LIGHT — a solid core with its glow thrown by box-shadow. Under this `perspective` a blend
              mode is isolated and comes out grey, which is how the first version lost its light entirely. */}
          {lightOn > 0.01 ? (
            <div style={{position: 'absolute',
              left: roam.x * surfW - (roam.w * surfW) / 2, top: roam.y * surfH - (roam.h * surfH) / 2,
              width: roam.w * surfW, height: roam.h * surfH, borderRadius: 999,
              background: ACC, opacity: 0.85 * lightOn,
              boxShadow: `0 0 ${Math.round(U * 0.05)}px ${Math.round(U * 0.018)}px ${ACC}`,
              pointerEvents: 'none'}} />
          ) : null}

          {/* the recession: one element the size of the target throwing a huge spread shadow, so the dim is
              everywhere EXCEPT on the thing being picked, and no second copy of the surface is needed */}
          {dim > 0.005 ? (
            <div style={{position: 'absolute', left: tgt.x, top: tgt.y, width: tgt.w, height: tgt.h,
              borderRadius: Math.round(U * 0.012), pointerEvents: 'none',
              boxShadow: `0 0 0 ${Math.round(Math.max(W, H))}px rgba(6, 9, 14, ${dim.toFixed(3)})`}} />
          ) : null}

          {/* THE OUTLINE AND THE CALLOUT SHARE ONE BOX AND A 1:1 VIEWBOX. Given a viewBox of its own and
              `preserveAspectRatio="none"` the stroke is scaled unevenly — round corners turn to ellipses,
              the width differs horizontally and vertically, and the whole border floats off the element it
              is supposed to be around. `pathLength={1}` makes the draw a fraction rather than a perimeter
              nobody can compute for a rounded rect. */}
          <svg width={surfW} height={surfH} viewBox={`0 0 ${surfW} ${surfH}`}
            style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}}>
            <rect x={tgt.x} y={tgt.y} width={tgt.w} height={tgt.h} rx={Math.round(U * 0.012)}
              fill="none" stroke={settle > 0 ? ACC : '#fff3cf'} strokeWidth={stroke}
              // THE START POINT IS A DASH OFFSET, NOT A ROTATION. Rotating the rect to move where the
              // stroke begins turns the border into a diamond sitting over the card — which is the same
              // "the outline is not around the element" failure as an uneven viewBox, arrived at from the
              // other direction. Offsetting the dash pattern moves the pen; the shape never moves.
              // ONE DASH OF LENGTH `draw` STARTING AT `startFrac`, on a period of exactly one perimeter so it wraps
              // past the path's origin. It was `"1 1"` with offset `1 + startFrac - draw`, which at draw = 1 inks
              // only [0, 1 - startFrac] — the settled border covered a quarter to a half of the card, and the shot
              // ended on an outline with a gap in it (seen on the 3.2s still).
              pathLength={1} strokeDasharray={`${draw} ${Math.max(0, 1 - draw)}`} strokeDashoffset={-startFrac}
              style={{filter: `drop-shadow(0 0 ${Math.round(U * 0.016 * (1 - settle))}px ${ACC})`,
                opacity: draw > 0 ? 1 : 0}} />
          </svg>
        </div>
      </div>

      {/* the note names what was picked, and lands AFTER the border does — a caption that arrives with the
          outline reads as a label printed on the frame, not as a conclusion the shot arrived at */}
      {NOTE ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: sy + surfH + gap,
          padding: `0 ${Math.round(W * 0.12)}px`, textAlign: 'center', color: DIM,
          opacity: noteIn, textWrap: 'balance',
          font: `500 ${fitBlockPx(NOTE, W * 0.72, noteH, notePx, {usable: 0.92, leading: 1.35})}px/`
            + `${leading(NOTE, 1.35)} var(--f-body, system-ui, sans-serif)`}}>{NOTE}</div>
      ) : null}
      <div style={{position: 'absolute', left: 0, right: 0, top: CONTENT_TOP - Math.round(U * 0.055),
        textAlign: 'center', color: FG, opacity: clamp01(seg(t, 0.02, 0.14)),
        font: `800 ${fitTextPx(SCREEN, W * 0.6, Math.round(U * 0.040), {usable: 1.0})}px/`
          + `${leading(SCREEN, 1.1)} var(--f-display, system-ui, sans-serif)`}}>{SCREEN}</div>
    </AbsoluteFill>
  );
};
export default GlowPick;
