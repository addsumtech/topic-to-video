// SHOT · PlaneStack — a system drawn as the LAYERS it is actually made of, seen at an angle, with the layer
// the beat is about held in focus.
//
// WHY THIS FORM. "A thing is made of layers, and this beat is about one of them" is one of the commonest
// claims an explainer makes — interface over service over store, road over pipes over soil, scalp over skull
// over cortex — and this library could not draw it. `StrataColumn` draws a section (what lies UNDERNEATH,
// measured, at its own depth), `PhysicsStack` draws quantities, `CardStack3D` draws a set in hand. None of
// them says "these are planes, each carries its own things, and they sit one on top of another". Measured
// against the peer library on 2026-09-05 (references/launch-film-study.md), 17% of their shots reach for 3D
// against 4% of ours, and the gap is not decoration: it is meanings like this one going unsaid.
//
// WHAT THE PICTURE CLAIMS, and nothing more. The ORDER of the planes is the film's order. What sits on each
// plane is what the film put there. Which one matters is the film's `focal` — absent, no layer is picked and
// every plane is drawn alike, because choosing one by position would be the frame making a claim the film
// did not (content contract rule 5, case law E14).
//
// DEPTH IS ANCHORED, NOT SUGGESTED. The recede runs through `runtime/focus` — one lens for the whole library
// — with BOTH its anchors: blur and desaturation. The peer's own case law is that without the two together
// layered material reads as stickers flying rather than as depth, and that is the failure this form is most
// exposed to, since every layer is the same rectangle.
//
// TYPE DOES NOT RIDE THE Z PLANE. Every word here belongs TO a plane — it is that layer's own label, note or
// item — so it is placed by `<OnSurface>`, which takes the plane's 2D affine: the word turns with the layer
// and stays a flat, crisp DOM element the type gates can see. The tilt is deliberately moderate (rx -32°):
// past about 45° the foreshortening costs more legibility than the depth buys.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, REDUCED_MOTION_T} from '../runtime/motion';
import {useDNA, contrastOf, dimOn, readableOn, shade as darken} from '../runtime/dna';
import {ACCENT_CONTRAST_MIN, groundFrom, hexGround} from '../runtime/light';
import {CONTENT_TOP, contentBottom, fitTextPx, inkBlockH, textWidthPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {Stage3D, Surface, OnSurface, planeAffine, fitSurfaces, faceShade, PERSP_FRAC,
        type Pose} from '../runtime/stage3d';
import {focusAt, focusFilter} from '../runtime/focus';

export const DURATION = 165; // 5.5s

/** A sixth plane makes each one thinner than its own type, and the stack stops reading as a stack. */
export const MAX_LAYERS = 5;
/** Four chips is what a plane this size holds at the type floor; a fifth would set them below it. */
export const MAX_ITEMS = 4;
/** Every plane has landed by here — the shared settling point the whole library holds to. */
const LAND_BY = REDUCED_MOTION_T - 0.02;

export type StackLayer = {
  /** what this layer IS — the film's word for it */
  label: string;
  /** a second line under the label, when the film gives one */
  note?: string;
  /** what sits ON this layer, as chips across it */
  items?: string[];
};

const DEFAULT_LAYERS: StackLayer[] = [
  {label: 'Interface', note: 'what a person touches', items: ['pages', 'forms']},
  {label: 'Service', note: 'what decides', items: ['rules', 'queue']},
  {label: 'Store', note: 'what remembers', items: ['tables', 'files']},
];

export const PlaneStack: React.FC<{title?: string; layers?: StackLayer[]; focal?: number | null;
  note?: string}> = ({
  title: TITLE = 'What it is made of', layers: LAYERS = DEFAULT_LAYERS, focal: FOCAL, note: NOTE = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const P = Math.round(U * PERSP_FRAC);

  const FG = dna?.fg ?? '#f2f5fa';
  const DIM = dna?.dim ?? '#8b97a8';
  const ACC = dna?.accent ?? '#5ac8fa';
  const LINE = dna?.line ?? 'rgba(255,255,255,0.14)';
  const SURF = dna?.surface ?? 'rgba(255,255,255,0.05)';
  const BG = dna?.bg ?? '#080b11';

  // A LAYER WITH NO NAME IS NOT A LAYER, and a sixth has nowhere to sit. The rest of this library refuses
  // past its capacity rather than cutting the film's list in silence (case law E14), and a stack is the
  // worst place to cut: the layer that goes missing is the bottom one, which is usually the point.
  if (!Array.isArray(LAYERS) || LAYERS.length < 2 || LAYERS.length > MAX_LAYERS) {
    throw new Error(
      `PlaneStack draws 2-${MAX_LAYERS} layers (got ${Array.isArray(LAYERS) ? LAYERS.length : typeof LAYERS}). ` +
      'One layer is not a stack — draw it as a card. Past five, each plane is thinner than the type on it: ' +
      'merge two layers, or split the system across two beats.');
  }
  const layers = LAYERS.map((l, i) => {
    const label = String(l?.label ?? '').trim();
    if (!label) {
      throw new Error(`PlaneStack: layer ${i + 1} has no \`label\`. Every plane in the stack is named by the film.`);
    }
    const raw = l?.items;
    if (raw !== undefined && !Array.isArray(raw)) {
      throw new Error(`PlaneStack: layer ${i + 1}'s \`items\` must be a list of words, got ${typeof raw}.`);
    }
    const items = (raw ?? []).map((s) => String(s ?? '').trim());
    if (items.some((s) => !s)) {
      throw new Error(`PlaneStack: layer ${i + 1} has an empty item. A chip with no word is furniture.`);
    }
    if (items.length > MAX_ITEMS) {
      throw new Error(
        `PlaneStack holds up to ${MAX_ITEMS} items on a layer; layer ${i + 1} ("${label}") was given ` +
        `${items.length}. A fifth chip sets the row below the type floor — name the group instead of listing it.`);
    }
    return {label, note: String(l?.note ?? '').trim(), items};
  });
  const n = layers.length;

  // WHICH LAYER MATTERS IS THE FILM'S CALL. Absent, no plane is picked: they are drawn alike and nothing is
  // blurred. A default of 0 would have the frame claiming "the top one is the point" of every film that
  // never said so.
  if (FOCAL !== undefined && FOCAL !== null && !(Number.isInteger(FOCAL) && FOCAL >= 0 && FOCAL < n)) {
    throw new Error(
      `PlaneStack: \`focal\` must be a layer index 0-${n - 1} or null (no layer picked), got ${JSON.stringify(FOCAL)}.`);
  }
  const focal = FOCAL === undefined || FOCAL === null ? null : FOCAL;

  // ── the stack in stage px ────────────────────────────────────────────────────────────────────────────
  const noteRoom0 = NOTE ? inkBlockH(Math.round(U * 0.024), 1) + Math.round(U * 0.03) : 0;
  const zoneW = W - U * 0.10, zoneH = contentBottom(W, H) - CONTENT_TOP - noteRoom0;
  const planeW = Math.round(U * 0.66);
  const planeH = Math.round(U * 0.26);
  // THE SEPARATION FOLLOWS THE ROOM. A stack sized for a landscape zone leaves a portrait frame two thirds
  // empty: the planes are wide and short, so width is what limits them and the vertical room goes unused.
  // Spreading them further apart is the honest way to use it — the layers stay the same size and the same
  // order, they just stand further apart, which is the one thing in this picture that carries no meaning.
  const gapY = Math.round(planeH * (zoneH > zoneW * 0.9 ? 1.15 : 0.80));
  const gapZ = Math.round(U * 0.05);               // and a little depth, so the stack is not a flat fan
  // TILT IS A TRADE, and it is set by the type. At -32° the planes read as a fan of cards rather than a
  // stack; past about -60° the words on them are squashed to half height and a CJK label stops being
  // legible at all. -48° reads as slabs and keeps the vertical squash at cos48 ~ 0.67.
  // The YAW is small on purpose. It is what makes the slabs read as objects rather than as rectangles, but
  // it also SHEARS every word on them, and a sheared line's axis-aligned DOM rect is wider than the glyphs —
  // which is how the CJK sweep's overlap check reads collisions between lines that do not touch (the same
  // blindness `runtime/depth` records for rotated type). -8° keeps the depth cue and halves the shear.
  const TILT = -48, YAW = -8;

  const pad = Math.round(planeH * 0.16);
  const titlePx = Math.round(U * 0.036);
  const notePxOuter = Math.round(U * 0.024);

  const lift = Math.round(U * 0.045);              // how far the focal plane comes out of the stack
  const landDrop = Math.round(U * 0.10);

  // Each plane lands in order, top to bottom, and the STEP compresses with the count so the last one is
  // settled by LAND_BY however many there are (the library-wide stagger rule).
  const START = 0.08, SPAN = 0.26;
  const step = n > 1 ? Math.min(0.10, Math.max(0.02, (LAND_BY - START - SPAN) / (n - 1))) : 0;
  const landOf = (i: number) => easeOutCubic(clamp01(seg(t, START + step * i, START + step * i + SPAN)));
  // the focal layer is chosen AFTER the stack exists, or the beat is over before the claim is made
  const pick = focal === null ? 0 : easeOutCubic(clamp01(seg(t, 0.52, 0.70)));

  const poseOf = (i: number, landed: number): Pose => {
    const centred = i - (n - 1) / 2;
    const out = focal === null ? 0 : (i === focal ? pick : 0);
    return {
      x: 0,
      y: centred * gapY - out * lift + (1 - landed) * -landDrop,
      z: -centred * gapZ + out * lift * 1.6,
      rx: TILT, ry: YAW, rz: 0,
    };
  };
  // the camera is fitted to the SETTLED stack (including the lift), so nothing jumps when the focal plane
  // comes forward and nothing is framed for a position the beat never holds
  const settled = layers.map((_, i) => ({pose: poseOf(i, 1), w: planeW, h: planeH}));
  // THE NOTE'S ROOM IS TAKEN OUT OF THE BOX BEFORE THE STACK IS FITTED. Drawn after the fit, it lands ON the
  // bottom plane — which is what the first Chinese render did, printing the beat's own note across the last
  // layer's face.
  const box = {left: U * 0.05, top: CONTENT_TOP, right: W - U * 0.05,
    bottom: contentBottom(W, H) - noteRoom0};
  // the SURFACES are fitted, not their centres: a wide tilted plane's bounding sphere is far bigger than the
  // plane, and fitting that sphere left this shot sitting small in a mostly empty frame
  const {cam} = fitSurfaces(settled, {rx: 0, ry: 0}, box, P, W, H, {pad: Math.round(U * 0.01)});

  // ── type sizes, in the planes' LOCAL px ──────────────────────────────────────────────────────────────
  // EVERY BLOCK ON A PLANE IS MEASURED AGAINST THE PLANE, and the sizes are SOLVED down to their floors
  // before anything is refused. The first Chinese sweep ran a 30-glyph note clean off the right edge of every
  // layer and through the chips beside it — the words were all on screen, so `text_safe_qa` saw nothing
  // missing, and only the CJK sweep's overlap check caught it. The first repair then refused a perfectly
  // ordinary four-layer beat, which is the opposite failure: a register that refuses what it could have set
  // smaller is not robust, it is brittle.
  //
  // ONE SIZE FOR EVERY LAYER, fitted to the LONGEST of each kind — a stack whose labels are set at different
  // sizes reads as a ranking the film never made.
  const innerW = planeW - pad * 2, innerH = planeH - pad * 2;
  const longest = (xs: string[]) => xs.reduce((a, b) => (textWidthPx(b, 1) > textWidthPx(a, 1) ? b : a), xs[0] ?? '');
  const LABEL_FLOOR = Math.round(planeH * 0.105), NOTE_FLOOR = Math.round(planeH * 0.062);
  const CHIP_FLOOR = Math.round(planeH * 0.058);

  const widestLabel = longest(layers.map((l) => l.label));
  const notes = layers.map((l) => l.note).filter(Boolean) as string[];
  const longestNote = notes.length ? longest(notes) : '';
  const hasItems = layers.some((l) => l.items.length);

  let labelPx = fitTextPx(widestLabel, innerW * 0.62, Math.round(planeH * 0.24));
  let notePx = notes.length ? Math.min(Math.round(labelPx * 0.56), Math.round(planeH * 0.10)) : 0;
  let chipPx = hasItems ? Math.round(labelPx * 0.44) : 0;
  // the note wraps, so its height is its MEASURED line count (at most two — a third line is a paragraph, and
  // a paragraph on a layer is the beat's narration in the wrong place)
  const noteLines = (px: number) =>
    Math.min(2, Math.max(1, Math.ceil(textWidthPx(longestNote, px) / Math.max(1, innerW))));
  const chipRow = (px: number) => layers.reduce((w, l) => Math.max(w, l.items.reduce(
    (acc, str) => acc + textWidthPx(str, px, {adv: 0.62}) + px * 1.5, 0)), 0);
  const blockH = () => inkBlockH(labelPx, 1)
    + (notePx ? inkBlockH(notePx, noteLines(notePx)) + notePx * 0.25 : 0)
    + (chipPx ? inkBlockH(chipPx, 1) + chipPx * 0.85 : 0);

  for (let guard = 0; guard < 400; guard++) {
    const tall = blockH() > innerH;
    const wide = chipPx > 0 && chipRow(chipPx) > innerW;
    const noteWide = notePx > 0 && noteLines(notePx) > 2;
    if (!tall && !wide && !noteWide) break;
    let moved = false;
    if (wide && chipPx > CHIP_FLOOR) { chipPx -= 1; moved = true; }
    if (tall || noteWide) {
      if (notePx > NOTE_FLOOR) { notePx -= 1; moved = true; }
      if (labelPx > LABEL_FLOOR) { labelPx -= 1; moved = true; }
      if (chipPx > CHIP_FLOOR) { chipPx -= 1; moved = true; }
    }
    if (!moved) break;                                  // everything is at its floor; the refusals below fire
  }

  if (labelPx < LABEL_FLOOR) {
    throw new Error(
      `PlaneStack: "${widestLabel}" is too long for a layer's label — it sets at ${labelPx}px where this ` +
      `plane's floor is ${LABEL_FLOOR}px. A layer is named in a word or two; a sentence belongs in \`note\`.`);
  }
  if (chipPx > 0 && chipRow(chipPx) > innerW) {
    throw new Error(
      `PlaneStack: a layer's items do not fit across the plane even at the ${CHIP_FLOOR}px floor ` +
      `(they measure ${Math.round(chipRow(chipPx))}px against ${Math.round(innerW)}px of plane). Fewer chips, ` +
      'or shorter words — a chip is a name, not a phrase.');
  }
  if (blockH() > innerH) {
    throw new Error(
      `PlaneStack: a layer's name, note and items need ${Math.round(blockH())}px of plane and the plane holds ` +
      `${Math.round(innerH)}px, with every size already at its floor. Drop the notes, or the items — a layer ` +
      'says what it IS and what sits on it, not both at length.');
  }

  // ONE lens for every plane, so the recede is the same relationship everywhere (runtime/focus).
  const FOCUS_OPTS = {minOpacity: 0.5, minBrightness: 0.72, minScale: 1, blurFrac: 0.0030, desat: 0.55};

  // ── the ink on a plane is read against the PLANE, not against the page ───────────────────────────────
  // A word here sits on a slab, and the slab is not the film's ground: `faceShade` multiplies the surface's
  // brightness by how far the plane has turned away from the key, which is a lighting model written for a
  // dark room. On a light film `surface` is white and a turned plane comes out a mid grey — while `dim`,
  // `line` and `accent` are still the values the film calibrated against its own paper. Measured by
  // `ink_contrast_qa` on a light film: 32.7% of this register's marks under 3:1, its largest hole 0.34% of
  // the frame, and that hole was the gloss NOTE and the item CHIPS on a slab — every one of them content
  // the film supplied. So the face is reconstructed here (the same multiply the `filter` applies) and each
  // token is KEPT where it still clears the floor on that face and derived only where it does not; on every
  // dark preset the film's own tokens clear it, so nothing moves.
  //
  // THE CHIP'S 1PX RIM IS NOT IN HERE. It is a hairline, it is the one thing `ink_contrast_qa`'s own header
  // names as its false positive, and on the rendered light frame the chips read as pills — the rim is doing
  // its job at a ratio a rim is allowed to have.
  //
  // What is modelled is the FACE SHADE and nothing else. The focus recede (brightness, saturation,
  // opacity) dims the words and the plane they are on by the same amount and is the register's own way of
  // saying "this layer is not the one" — folding it in would fight the recede. `faceShade` is different in
  // kind: it moves the PLANE and not the type, so it is what changes the relationship between them.
  const PLANE_FLOOR = ACCENT_CONTRAST_MIN;        // the same 3.0 the ink gate fails under
  const surfHex = dna ? hexGround(SURF) : null;   // a translucent `surface` is ~the ground: nothing to model
  /** The tokens for a plane the lighting has multiplied to `k` of the film's `surface`. */
  const inkOnPlane = (k: number) => {
    if (!dna || !surfHex) return {fg: FG, dim: DIM, acc: ACC};
    const face = darken(surfHex, clamp01(1 - k));
    const keep = (c: string) => contrastOf(c, face) >= PLANE_FLOOR;
    // the ink the plane can definitely carry — the film's own two poles, measured against the face
    const pole = readableOn(face, FG, BG);
    return {
      fg: keep(FG) ? FG : pole,
      dim: keep(DIM) ? DIM : dimOn(face, pole, PLANE_FLOOR),
      // the focal layer's accent keeps its HUE and moves only its exposure, like any other ground — asked
      // for only when the film named a focal layer, since nothing else on a plane is drawn in the accent
      acc: focal === null || keep(ACC) ? ACC : groundFrom(dna, {bg: face}).accent,
    };
  };

  // TYPE LIVES OUTSIDE THE STAGE. `Stage3D`'s own header says it: everything inside is composited in 3D, so
  // a word placed there is rasterized at layout size and upscaled. `<OnSurface>` returns a screen-space 2D
  // matrix and belongs beside the stage, not in it — put inside, the stage's camera transform is applied to
  // it a SECOND time, and the first render of this shot drew every label in a huddle off the bottom-right
  // corner while the planes sat in the middle of the frame.
  const textBlocks = layers.map((l, i) => {
    const landed = landOf(i);
    if (landed <= 0.001) return null;
    const pose = poseOf(i, landed);
    const d = focal === null ? 0 : clamp01((Math.abs(i - focal) / Math.max(1, n - 1)) * pick);
    const f = focusAt(d, U, FOCUS_OPTS);
    const isFocal = focal !== null && i === focal;
    // the plane these words are actually on — the same multiply the Surface's own filter applies below
    const ink = inkOnPlane(faceShade(pose, cam, 0.42));
    const aff = planeAffine(pose, cam, P, W, H, -planeW / 2 + pad, -planeH / 2 + pad,
      planeW - pad * 2, planeH - pad * 2);
    if (!aff) return null;
    return (
      <OnSurface key={i} pose={pose} cam={cam} persp={P} W={W} H={H} affine={aff}
        left={-planeW / 2 + pad} top={-planeH / 2 + pad}
        width={planeW - pad * 2} height={planeH - pad * 2}
        style={{opacity: landed * f.opacity, filter: focusFilter(f), height: innerH,
          display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
        <div style={{font: `800 ${labelPx}px/${leading(l.label, 1.1)} ${dna?.fontDisplay ?? 'Inter, sans-serif'}`,
          color: isFocal ? ink.acc : ink.fg, letterSpacing: '-0.01em', whiteSpace: 'nowrap'}}>{l.label}</div>
        {l.note ? (
          <div style={{font: `500 ${notePx}px/${leading(l.note, 1.25)} ${dna?.fontBody ?? 'Inter, sans-serif'}`,
            color: ink.dim, marginTop: Math.round(notePx * 0.25), maxWidth: innerW}}>{l.note}</div>
        ) : null}
        {l.items.length ? (
          <div style={{display: 'flex', gap: pad * 0.5, marginTop: pad * 0.5, flexWrap: 'nowrap'}}>
            {l.items.map((s, j) => (
              <div key={j} style={{
                font: `600 ${chipPx}px/${leading(s, 1.2)} ${dna?.fontMono ?? 'ui-monospace, monospace'}`,
                color: isFocal ? ink.fg : ink.dim, padding: `${Math.round(chipPx * 0.26)}px ${Math.round(chipPx * 0.5)}px`,
                border: `1px solid ${LINE}`, borderRadius: Math.round(chipPx * 0.4),
                whiteSpace: 'nowrap'}}>{s}</div>
            ))}
          </div>
        ) : null}
      </OnSurface>
    );
  });

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <Stage3D cam={cam} persp={P}>
        {layers.map((l, i) => {
          const landed = landOf(i);
          if (landed <= 0.001) return null;
          const pose = poseOf(i, landed);
          const d = focal === null ? 0 : clamp01((Math.abs(i - focal) / Math.max(1, n - 1)) * pick);
          const f = focusAt(d, U, FOCUS_OPTS);
          const shade = faceShade(pose, cam, 0.42);
          const isFocal = focal !== null && i === focal;
          // the focal ring is the accent exposed for THIS plane — the same value its label takes, so the
          // ring and the word it rings stay one decision
          return (
            <Surface key={i} pose={pose} w={planeW} h={planeH}
              style={{
                background: SURF,
                border: `${Math.max(1, Math.round(U * 0.0016))}px solid ${isFocal ? inkOnPlane(shade).acc : LINE}`,
                borderRadius: Math.round(U * 0.012),
                opacity: landed * f.opacity,
                filter: focusFilter({...f, brightness: f.brightness * shade}),
                boxShadow: isFocal ? `0 0 ${Math.round(U * 0.06)}px ${ACC}22` : undefined,
              }} />
          );
        })}
      </Stage3D>
      {textBlocks}

      {TITLE ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: Math.round(CONTENT_TOP - U * 0.055),
          textAlign: 'center', font: `700 ${titlePx}px/${leading(TITLE, 1.2)} ${dna?.fontDisplay ?? 'Inter, sans-serif'}`,
          color: FG, opacity: clamp01(seg(t, 0.02, 0.16)), letterSpacing: '0.01em'}}>{TITLE}</div>
      ) : null}
      {NOTE ? (
        <div style={{position: 'absolute', left: U * 0.08, right: U * 0.08,
          top: contentBottom(W, H) - inkBlockH(notePxOuter, 1) - Math.round(U * 0.012), textAlign: 'center',
          font: `500 ${notePxOuter}px/${leading(NOTE, 1.3)} ${dna?.fontBody ?? 'Inter, sans-serif'}`,
          color: DIM, opacity: clamp01(seg(t, 0.62, 0.78))}}>{NOTE}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default PlaneStack;
