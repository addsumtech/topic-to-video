// SHOT · WordTunnel — the beat's phrases posed down a CORRIDOR, and the camera travels it.
//
// Each phrase stands at its own depth on the shared stage; the camera moves forward along z, so a phrase
// grows out of the far dark, passes the lens and is gone. The ORDER is the argument — this is the register
// for a beat whose points arrive one after another with weight, where a list would flatten them into peers.
// It is the peer library's `flying-words`, built on the same stage as SpatialSlides: `runtime/stage3d`.
//
// TYPE DOES NOT RIDE THE Z PLANE — the rule SpatialSlides was built on, and the whole reason this register
// can exist at all. `runtime/depth` measured it: glyph edge strength 91 flat, 56 under `perspective +
// translateZ`, a 38% loss, because a 3D-composited layer is rasterized once at layout size and upscaled. A
// tunnel of words is the shape most tempting to build out of `translateZ`, and it is exactly the shape that
// would look worst and be invisible to every type gate. So the stage computes WHERE and HOW BIG, and every
// phrase is then an ordinary flat 2D element: crisp, measurable, and reachable by text_safe_qa.
//
// EVERY PHRASE IS IN THE CORRIDOR, OR THE REGISTER SAYS IT CANNOT BE. There are six hand-set lanes and the list
// used to be `.filter(Boolean).slice(0, LANES.length)`: a seventh phrase was dropped in silence, and an empty
// one was filtered out, so the order the film argued — the whole point of this register — lost a step without
// anyone being told. Past MAX_PHRASES it now throws with the maximum, and an empty phrase throws naming it.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, clamp01, easeInOutCubic, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, shade} from '../runtime/dna';
import {onLight} from '../runtime/light';
import {CONTENT_TOP, contentBottom, fitBlockPx, fitTextPx, textWidthPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
// @billboard: each phrase IS the object in the corridor, not writing on a face — there is no surface for it
// to lie on, and a word flying at the lens must face the viewer or it is unreadable at the one moment it is
// largest. Placed by `projectPose` on purpose; see `OnSurface` in runtime/stage3d for the other case.
import {projectPose, PERSP_FRAC, type Pose} from '../runtime/stage3d';

export const DURATION = 165; // 5.5s

/** Where each phrase stands across the corridor, as a fraction of the frame. Hand-set and deterministic:
 *  a corridor whose walls move every render is not a place. They alternate sides so the camera's path reads
 *  as travel between them rather than as a column of text sliding forward. */
const LANES: Array<{x: number; y: number}> = [
  {x: -0.13, y: -0.06}, {x: 0.14, y: 0.05}, {x: -0.11, y: 0.07},
  {x: 0.12, y: -0.07}, {x: -0.06, y: 0.02}, {x: 0.09, y: -0.03},
];
export const MAX_PHRASES = LANES.length;

export const WordTunnel: React.FC<{phrases?: string[]; tail?: string}> = ({
  phrases: PHRASES = ['First', 'Then', 'And then', 'Finally'], tail: TAIL = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const P = Math.round(U * PERSP_FRAC);

  const list = (Array.isArray(PHRASES) ? PHRASES : []).map((s) => String(s ?? '').trim());
  if (!list.length) {
    throw new Error(
      'WordTunnel needs at least one non-empty `phrases` entry. The form IS the phrases arriving in order; ' +
      'with none it draws an empty corridor, which composes and argues nothing.');
  }
  if (list.length > MAX_PHRASES) {
    throw new Error(
      `WordTunnel takes at most ${MAX_PHRASES} \`phrases\` (got ${list.length}): the corridor has ${MAX_PHRASES} ` +
      'hand-set lanes, and a phrase with no lane would be a step of the argument the viewer never sees. Keep ' +
      'the steps the order turns on, or use a list register for a longer sequence.');
  }
  list.forEach((p, i) => {
    if (!p) {
      throw new Error(`WordTunnel: phrase ${i + 1} is empty. Every phrase is a step in the order; pass its ` +
        'words, or leave the entry out.');
    }
  });
  const n = list.length;

  const FG = dna?.fg ?? '#eef2f8';
  const ACC = dna?.accent ?? '#5b8cff';
  const BG = dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 100% at 50% 50%, #10131c, #05070b 70%)';
  // A DROP SHADOW IS SEPARATION FROM THE GROUND, NOT A CONSTANT BLACK. `rgba(0,0,0,.55)` behind a phrase is
  // invisible on this library's own near-black grounds — where it was authored — and on a film grounded
  // paper it rings the one word on the frame with grey: measured, 60% of this register's marks fell under
  // 3:1 and every one of them was a glyph EDGE, not a glyph. `onLight` is the read this decision needs, and
  // on paper the shadow becomes a soft shade of the room instead of a hole in it.
  const SHADOW = dna && onLight(dna) ? shade(dna.bg, 0.22) : 'rgba(0,0,0,.55)';

  // THE CORRIDOR, in stage units. Depth is a fraction of the short side so the tunnel is as deep at 9:16 as
  // at 16:9 — written in bare px it would be a different room at every aspect (E8).
  const GAP = U * 0.85;                       // between one phrase and the next
  const START = U * 0.30;                     // how far past the lens the first one begins
  // THE LAST PHRASE STANDS IN THE MIDDLE OF THE CORRIDOR. Every other one is off to a side and its offset
  // is multiplied by the perspective scale, so it sweeps outward as it nears and leaves the frame — which is
  // what a corridor does and is right for a point that has been made. The FINAL point must not do that: on a
  // lane it swept out at exactly the moment it should have landed, and the shot played its last fifth on an
  // empty frame. Centred, it grows in place and is held.
  const poses: Pose[] = list.map((_, i) => {
    const lane = i === n - 1 ? {x: 0, y: -0.03} : LANES[i];
    return {x: lane.x * W, y: lane.y * H, z: -(START + i * GAP)};
  });

  // The camera travels the whole corridor and a little past its end, so the last phrase also passes rather
  // than parking in front of the lens. Eased, because a constant crawl is the "uniform motion reads as
  // cheap" failure the peer library's R2 names and this library measured itself clean of.
  // THE SIGN IS THE WHOLE THING. `projectPose` scales by `persp / (persp - ez)`, so a pose FURTHER from the
  // eye has a more negative eye-z and a smaller k. Travelling the corridor therefore means driving the
  // camera's z DOWN, toward the far phrases. Written the other way round — camZ rising from negative to
  // positive — the camera reverses out of the corridor and every phrase shrinks toward the vanishing point
  // together: four words in a clump in the middle of a dark frame, which looks like a composition.
  const travel = easeInOutCubic(clamp01(t / 0.94));
  const camStart = START * 0.55;                                  // just behind the first phrase
  // ...and stops WITH the last phrase, not past it: far enough that it reads large, near enough that it is
  // still in front of the lens when the beat ends. `k = persp / (persp - ez)`, so ez = 0.33U puts it at
  // about 1.4x — held, not sailed through.
  const HELD_EZ = U * 0.33;
  const camEnd = -(START + (n - 1) * GAP) - HELD_EZ;
  // The scale the held phrase ends at, derived from the SAME number that stops the camera — so the size it
  // is fitted to and the size it is drawn at cannot drift apart.
  const K_HELD = P / (P - HELD_EZ);
  const cam: Pose = {z: camStart + travel * (camEnd - camStart)};

  // THE ZONE A PHRASE MAY OCCUPY. A word arriving at speed is exactly the thing that would sail through the
  // caption band unnoticed, so the band is not something this register merely avoids on average — a phrase
  // whose ink would land in it is not drawn at all.
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const HELD_BOX = Math.round(W * 0.86);

  const drawn = list.map((text, i) => {
    const pr = projectPose(poses[i], cam, P, W, H);
    if (!pr || pr.behind) return null;
    const {x, y, k} = pr;
    // k is the perspective scale CSS itself would apply at that depth. Reading it back out is what keeps the
    // flat word the same size the surface under it would have been — no second guess at the projection.
    if (k <= 0.12) return null;                       // still too far to read; drawing it is noise

    // The phrase is fitted at its FULL size and then scaled by k, so the fit is decided once, in a measure
    // that does not depend on where the camera is. Fitted per-phrase against the frame, in the face the DNA
    // actually ships (E2: fitTextPx's default advance covers the widest of them).
    // THE PHRASE THAT IS HELD MAY BE A BLOCK; THE ONES PASSING ARE LINES. A phrase sweeping by is one
    // line by nature — it is in flight, and wrapping it would read as a paragraph thrown at the lens. The
    // LAST one does not sweep by: it stops and carries the frame, so it is allowed to wrap and to grow
    // into the room it has.
    //
    // Both halves came from measurement. Fitted to the bare frame width and then scaled by K_HELD it was
    // 40% too wide, so at 1:1 in Chinese it was culled and the corridor played its ending on an EMPTY
    // frame — and no type gate can see that, because a phrase that is never DRAWN is never cut off; it
    // took `cjk_type_qa --aspect=1:1`, which asks whether the strings FED reached the screen. Fitted to
    // one line it was then legible but tiny in a portrait frame: a 1080x1920 frame has 1.8x the area and
    // the same single line, which `cjk_type_qa` reported as DREW ALMOST NOTHING at 9:16 and 4:5.
    const lh = leading(text, 1.05);
    const held = i === n - 1;
    const HELD_W = HELD_BOX, HELD_H = (zBot - zTop) * 0.55;
    const basePx = held
      ? fitBlockPx(text, HELD_W / K_HELD, HELD_H / K_HELD, Math.round(U * 0.22), {usable: 1, leading: lh})
      : fitTextPx(text, W * 0.82, Math.round(U * 0.12), {usable: 1});
    // The held phrase's base is already fitted to the room DIVIDED by K_HELD, so `basePx * k` grows it
    // into that room as the camera closes and lands exactly on it. Same expression either way.
    const px = Math.max(8, Math.round(basePx * k));
    if (px < 14) return null;                         // below this it is texture, not a phrase

    // A PHRASE LEAVES BEFORE IT IS CUT, it is never clipped. A word rushing past the lens naturally grows
    // past the frame, and every other register in this library is forbidden from letting type do that — so
    // the size at which it would stop fitting IS the size at which it is gone. Measured in the same advance
    // model the fit used, so the two cannot disagree about how wide the phrase is (E2).
    const lines = held ? wrapLines(text, px, HELD_W) : 1;
    const halfW = Math.min(HELD_W, textWidthPx(text, px)) / 2;
    const halfH = (lines * px * lh) / 2;
    if (x - halfW < W * 0.04 || x + halfW > W * 0.96) return null;
    // ...and the caption band is not something this register avoids on average: a phrase whose ink would
    // land in it is not drawn. Culling rather than nudging keeps the corridor honest — a phrase shoved back
    // inside the zone is standing somewhere the camera says it is not.
    if (y - halfH < zTop || y + halfH > zBot) return null;

    // Legibility is the argument's, not the lens's: full strength while it is readable, fading at both ends
    // of that window rather than tracking depth linearly.
    const o = Math.min(1, clamp01((k - 0.12) / 0.30));
    if (o <= 0.02) return null;

    return {text, i, x, y, px, o, k, lh, halfW, halfH, held};
  }).filter(Boolean) as Array<{text: string; i: number; x: number; y: number; px: number; o: number;
    k: number; lh: number; halfW: number; halfH: number; held: boolean}>;

  // A NEAR PHRASE OCCLUDES A FAR ONE — it does not blend with it. The readable window of this corridor is
  // wider than the gap between two phrases, so two or three are in flight at once and their boxes cross.
  // Drawn back-to-front with opacity they came out as one illegible pile in the middle of the frame ('And
  // then' and 'Then' set on top of each other, 'Finally' showing through both), which is what happens when
  // a depth cue is applied to SIZE and not to visibility. Nearest first, and a phrase whose box crosses one
  // already accepted is behind it and is not drawn. That is what the corridor actually looks like.
  drawn.sort((a, b) => b.k - a.k);
  const front: typeof drawn = [];
  for (const d of drawn) {
    const hit = front.some((f) => Math.abs(f.x - d.x) < f.halfW + d.halfW + U * 0.015
                              && Math.abs(f.y - d.y) < f.halfH + d.halfH + U * 0.010);
    if (!hit) front.push(d);
  }
  // ...and painted far-to-near, so the one nearest the lens is on top of the stack it beat.
  front.reverse();

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* the corridor's own light: a soft well at the vanishing point, so the far dark reads as depth
          rather than as an empty frame before the first phrase arrives */}
      <AbsoluteFill style={{background: `radial-gradient(38% 38% at 50% 50%, ${ACC}22, transparent 70%)`}} />

      {front.map((d) => (
        // THE HELD BLOCK IS GIVEN ITS BOX, not a maxWidth. An absolutely positioned element with `left` set
        // and `right` auto shrinks to fit what remains of the containing block — W minus `left` — so a
        // block centred at left:960 on a 1920 frame had 960px to wrap in, not the 1651 its fit measured
        // against, and it came down two lines onto the tail. A measure the fit uses and a measure the
        // browser uses that are not the same number is the defect this library keeps paying for.
        <div key={d.i} style={{position: 'absolute', top: d.y, opacity: d.o, color: d.held ? ACC : FG,
          ...(d.held
            ? {left: Math.round((W - HELD_BOX) / 2), width: HELD_BOX, textAlign: 'center' as const,
               transform: 'translateY(-50%)'}
            : {left: d.x, whiteSpace: 'nowrap' as const, transform: 'translate(-50%, -50%)'}),
          font: `800 ${d.px}px/${d.lh} var(--f-display, Inter, system-ui, sans-serif)`,
          letterSpacing: '-0.02em',
          // The glow rides the phrase's own colour and its nearness, so the corridor has a light in it
          // without any element being lit by a colour the film never declares.
          textShadow: `0 ${Math.round(d.px * 0.06)}px ${Math.round(d.px * 0.5)}px ${SHADOW}`}}>
          {d.text}
        </div>
      ))}

      {/* THE TAIL is drawn only when the film supplies one, and only once the corridor is behind us — a
          closing line competing with a phrase mid-flight is two claims at once.
          ...AND IT IS IN BEFORE THE SETTLED FRAME. It used to start at `t > 0.86`, which is exactly the t
          `useT` freezes at under reduced motion and the frame every gate and the shot-critic read — so on that
          frame the film's closing line was never drawn at all, and under reduced motion it never appeared.
          By 0.74 the camera has covered 96% of its travel and every passing phrase is behind the lens, so the
          tail arrives with the held phrase alone on screen and is fully in by 0.82. */}
      {TAIL && t > 0.74 ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: zBot - Math.round(U * 0.12),
          transform: 'translateY(-100%)', textAlign: 'center', padding: `0 ${Math.round(W * 0.09)}px`,
          opacity: easeOutCubic(clamp01((t - 0.74) / 0.08)), color: FG,
          font: `700 ${fitTextPx(TAIL, W * 0.82, Math.round(U * 0.062), {usable: 1})}px/${leading(TAIL, 1.2)} ` +
                'var(--f-display, Inter, system-ui, sans-serif)'}}>
          {TAIL}
        </div>
      ) : null}

      {/* speed lines — the only thing here that may ride the z plane, because it carries no glyphs */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.22}} aria-hidden>
        {Array.from({length: 14}).map((_, i) => {
          const a = hash01(i * 7.3) * Math.PI * 2;
          const r0 = U * (0.10 + hash01(i * 3.1) * 0.18);
          const r1 = r0 + U * (0.16 + hash01(i * 5.7) * 0.22) * (0.4 + travel * 0.9);
          const cx = W / 2, cy = (zTop + zBot) / 2;
          return <line key={i} x1={cx + Math.cos(a) * r0} y1={cy + Math.sin(a) * r0}
            x2={cx + Math.cos(a) * r1} y2={cy + Math.sin(a) * r1}
            stroke={ACC} strokeWidth={Math.max(1, Math.round(U * 0.0018))} strokeLinecap="round" />;
        })}
      </svg>
    </AbsoluteFill>
  );
};
export default WordTunnel;
