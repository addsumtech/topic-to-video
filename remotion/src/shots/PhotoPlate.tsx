// SHOT · PhotoPlate — a REAL photograph mounted as a plate, with the film's own marks placed at points IN
// it as the narration names them. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: "look at the actual thing, and here is what to notice in it." A photograph dropped
// whole into a frame is an illustration — the viewer looks at it, agrees it exists, and moves on. A
// photograph the film POINTS AT is evidence being read: the marks say which parts of the picture carry the
// claim, and they arrive in the order the voice makes it. That is a different act, and no diagram can do it
// — a diagram is the film's drawing of the thing, this is the thing.
//
// WHY THIS REGISTER EXISTS. The library could already show a real image three ways: reconstructed by a
// technique (ScanReconstruct), cited beside a catalogue label (MuseumLabel), or compared against another
// (RealVersus). None of them is "the photograph is the frame". Measured on a delivered film about a
// physical city with license-clean photographs available, the real imagery occupied 5.3%, 8.5% and 16.3% of
// the frame — the evidence was a footnote in a film of drawings. This is the shape that was missing.
//
// The marks sit on a LIFTED plane, so they read as placed ON the print rather than printed into it. That
// separation is the one place in this library where depth is native rather than decorative: a label the
// film has added is genuinely not part of the photograph, and the shadow says so.
//
// Topic-free: any film with a real image and things to point at — a building, a machine, a street, a
// specimen, a screen. `marks` are fractions of the plate, so they travel with any crop or aspect.
//
// A RING ON A PHOTOGRAPH SAYS "HERE", SO "HERE" MUST BE THE FILM'S. Three ways this register used to point
// at places nobody chose. (1) A mark without coordinates was placed at `m.x ?? 0.5`, `m.y ?? 0.5` — a
// labelled ring on the dead centre of a real photograph, asserting the named feature is there. (2) A mark
// outside 0..1 was clamped onto the plate's edge, which is also a place the film did not name. (3) `marks`
// defaulted to two demo chips ("what to notice here", "and here") at fixed points — and because this register
// refuses to draw without `src`, there IS no standalone preview for that default to serve: it only ever
// landed on a film's own photograph. So a mark now needs `x` and `y` in 0..1 or the shot throws, `marks`
// defaults to none (a plate may simply show its photograph), and more than five marks throws instead of the
// old silent `.slice(0, 5)` dropping the sixth.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {requireEvidence} from '../runtime/evidence';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP, placeLabel, latinAdvance, cjkAdvance} from '../runtime/layout';
import {Plane, DEPTH} from '../runtime/depth';
import {useDNA} from '../runtime/dna';

export const DURATION = 175;

// The register's own diagnostic, not any film's copy: a plate with no photograph says so on the frame
// rather than rendering an empty box that looks like a design choice.
export const INTRINSIC_TEXT = ['no image supplied'];

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7', SURF_D0 = '#f6f1e6';

type Mark = {x?: number; y?: number; label?: string; n?: number};   // x/y REQUIRED, 0..1 of the plate

export const MAX_PHOTO_MARKS = 5;

const CHIP_MEASURE = 24;   // characters per line — a callout is a phrase, not a paragraph
// A FULL-WIDTH glyph: Han, kana, Hangul, and the CJK punctuation and full-width forms set among them. The class
// used to stop at the ideographs, so a full-width colon or comma was counted at the Latin advance and rendered
// a whole em wide — 「对岸：深圳」 came out a few pixels short and dropped 「圳」 onto a line of its own.
const WIDE_CH = /[\u2e80-\u9fff\uf900-\ufaff\uac00-\ud7af\uff01-\uff60\uffe0-\uffe6]/;

export const PhotoPlate: React.FC<{
  src?: string;             // the real photograph, relative to the film's public dir
  title?: string;           // the plate's kicker
  caption?: string;         // what the plate IS — set under it, in the display face
  marks?: Mark[];           // things to point at, in fractions of the PLATE — which frames the WHOLE image
  // The photograph's own width/height. render_remotion.py fills it from the file, so the plate can take the
  // picture's proportions and show all of it. Absent, the plate falls back to a landscape default and the
  // image is cropped to fill — which is the behaviour this prop exists to end.
  imageAspect?: number;
  credit?: string;          // the licence line a license-clean image requires
}> = ({
  src,
  title = '',
  caption = 'the thing itself',
  marks: MARKS = [],
  imageAspect,
  credit = ''} = {}) => {
  requireEvidence('PhotoPlate', 'src', src, 'the real photograph this plate frames and points at');
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const disp = dna?.fontDisplay ?? '"Source Serif 4", Georgia, serif';
  const mono = dna?.fontMono ?? 'ui-monospace, monospace';
  const hair = Math.max(1, Math.round(W * 0.0011));
  // Type is sized off the NARROW dimension, which is the rule this library's scaffold states and the reason
  // is visible here: keyed to W, the mark labels came out at 15px on a 1080-wide portrait frame — present
  // and unreadable — while reading correctly at 16:9. The fractions are calibrated so the landscape sizes
  // are unchanged and portrait simply stops shrinking. The ratio between the plate's caption and its
  // auxiliary text (~0.57) is the same one a broadcast readability floor asks for.
  const base = Math.min(W, H);

  // Every mark the film gives is drawn, once, at the point it names — see the header for what used to happen.
  if (!Array.isArray(MARKS) || MARKS.length > MAX_PHOTO_MARKS) {
    throw new Error(
      `PhotoPlate takes 0-${MAX_PHOTO_MARKS} \`marks\` (got ${Array.isArray(MARKS) ? MARKS.length : typeof MARKS}). ` +
      'Past five the callouts stack into a column that no longer reads as pointing at the photograph — keep ' +
      'the marks the narration names, or split the photograph across two beats.');
  }
  const shown = MARKS.map((m, i) => {
    const x = Number(m?.x), y = Number(m?.y);
    if (m?.x == null || m?.y == null || !(x >= 0 && x <= 1) || !(y >= 0 && y <= 1)) {
      throw new Error(
        `PhotoPlate: mark ${i + 1}${m?.label ? ` ("${m.label}")` : ''} needs \`x\` and \`y\` in 0..1 of the plate ` +
        `(got x=${String(m?.x)}, y=${String(m?.y)}). A ring on a real photograph says the feature is THERE; ` +
        'with no point from the film it would ring the centre, or the edge a clamp moved it to.');
    }
    return {...m, x, y};
  });

  // THE PLATE IS THE SUBJECT, so it takes the content zone rather than a polite inset. It keeps a margin
  // only wide enough for the plate's own rule and its caption — the point of this register is that the
  // photograph is large enough to be READ, not acknowledged.
  const top0 = CONTENT_TOP + H * 0.01;
  // THE PLATE TAKES THE PHOTOGRAPH'S OWN PROPORTIONS. A fixed landscape plate plus `objectFit: cover` threw
  // away whatever did not fit: measured on a delivered film, a 1280x1707 portrait photograph in a 2.3:1
  // plate lost 67.4% of its HEIGHT — and the beat's whole claim was that the street and the wharf below it
  // are visible in one picture. It also silently broke this register's core promise, since `marks` are
  // fractions of the plate and a crop makes a plate fraction point somewhere else in the photograph.
  // Framing the image at its own aspect means nothing is cropped and the two spaces coincide.
  // Still capped on BOTH sides: a panorama would become a slit and a very tall image would leave the frame
  // mostly empty, so an extreme original is cropped a little rather than dictating the whole composition.
  const MAX_PLATE_ASPECT = 2.3;
  const MIN_PLATE_ASPECT = 0.62;
  const plateAspect = imageAspect && isFinite(imageAspect) && imageAspect > 0
    ? Math.max(MIN_PLATE_ASPECT, Math.min(MAX_PLATE_ASPECT, imageAspect))
    : MAX_PLATE_ASPECT;
  // The space under the plate is DERIVED from the type that goes in it, not guessed. As a flat fraction of
  // H it held one line, and the caption wraps to two on any narrow frame — the credit was then drawn at a
  // fixed offset straight through the caption's second line. Positions under here are a running sum, the
  // same rule the rest of this library learned after the identical collision in GazetteerEntry.
  const capSize = Math.round(Math.min(W, H) * 0.042);
  const creditSize = Math.round(Math.min(W, H) * 0.019);
  const capGap = Math.round(H * 0.018);
  // Reserve for the lines the caption ACTUALLY needs, not always for two. Reserving the worst case cost the
  // plate ~56px of height on every beat whose caption is one line — and the plate is the subject here, so
  // that height is the whole point of the register. Estimated from the measure the caption wraps in, the
  // same way the burned caption's own fit is estimated; capped at two, because a plate caption longer than
  // that is a paragraph and belongs in the narration.
  // The plate's width and the caption's line count depend on each other: the caption wraps in the plate's
  // width, and the space reserved for it sets the plate's height, which sets its width. A first pass broke
  // the loop with a standing approximation and got a width 30% too wide — it believed 68 characters fitted
  // on a line where 52 do, so a 55-character caption was estimated at one line, reserved one, and then
  // CLIPPED by the line clamp with no signal at all. Two passes settle it: assume one line, derive the real
  // plate, re-count, and if it turned out to be two, derive again against the narrower plate.
  const capText = String(caption || '');
  // CJK sets one glyph per em; Latin averages about half. Estimating a CJK caption at the Latin advance
  // halves its apparent length.
  const cjkShare = capText.length
    ? capText.replace(/[^\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/g, '').length / capText.length : 0;
  const advance = 0.52 + 0.48 * cjkShare;
  const reserveFor = (lines: number) =>
    capGap + Math.round(capSize * 1.25 * lines) + (credit ? Math.round(creditSize * 1.85) : 0) + capGap;
  const plateWidthFor = (lines: number) => {
    const h = Math.max(1, (H - captionBand(W, H) - reserveFor(lines)) - top0);
    return Math.min(W - W * 0.17, h * plateAspect);
  };
  const linesIn = (w0: number) =>
    Math.max(1, Math.min(2, Math.ceil(capText.length
      / Math.max(8, Math.floor(Math.max(w0, W * 0.46) / (capSize * advance))))));
  const capLines = linesIn(plateWidthFor(linesIn(plateWidthFor(1))));
  const capH = reserveFor(capLines);
  const bottom0 = H - captionBand(W, H) - capH;
  // The plate takes the content zone, but its ASPECT is capped. Left to fill the width it came out at
  // 2.78:1 on a 16:9 frame — a cinemascope slit that happened to suit this photograph and would have cut
  // the subject out of a portrait one. The cap is on the WIDE side only: a tall frame wants a tall plate,
  // and cropping a landscape photograph to it is what a portrait film asks for anyway.
  const PH0 = Math.max(1, bottom0 - top0);
  const PW = Math.min(W - W * 0.17, PH0 * plateAspect);
  // ...BUT AN ANNOTATED PLATE MUST FRAME THE WHOLE PHOTOGRAPH, because a mark's x/y are fractions of the image
  // and a cover-crop moves every one of them. Filling a portrait frame's full height with a landscape photo
  // cropped its sides away, and the rings — still placed at plate fractions — landed on different features
  // than the film named (rendered: a mark authored on the brickwork left of a feature sat on the feature's
  // edge at 9:16). With marks, the plate's height follows its width at the photograph's own proportions and
  // the pair is centred in the zone; an unannotated plate keeps the tall crop, since a crop points at nothing.
  const PH = shown.length > 0 ? Math.max(1, Math.min(PH0, PW / plateAspect)) : PH0;
  const top = top0 + (PH0 - PH) / 2;
  const bottom = top + PH;
  // Where the photograph's own fractions land on the plate. Identity whenever the plate has the image's
  // proportions; only an original past the aspect caps is still cropped, and then the marks are carried
  // through the same crop `objectFit: cover` applies — a mark on a part of the photograph the crop removed
  // cannot be pointed at, and says so rather than ringing the plate's edge.
  const imgA = imageAspect && isFinite(imageAspect) && imageAspect > 0 ? imageAspect : PW / PH;
  const boxA = PW / PH;
  const visX = imgA > boxA ? boxA / imgA : 1, visY = imgA < boxA ? imgA / boxA : 1;
  const onPlate = shown.map((m, i) => {
    const u = (m.x - (1 - visX) / 2) / visX, v = (m.y - (1 - visY) / 2) / visY;
    if (u < 0 || u > 1 || v < 0 || v > 1) {
      throw new Error(
        `PhotoPlate: mark ${i + 1}${m.label ? ` ("${m.label}")` : ''} at x=${m.x}, y=${m.y} of the photograph falls ` +
        `outside the part this plate shows — an image of aspect ${imgA.toFixed(2)} is cropped to the plate's ` +
        `${boxA.toFixed(2)} cap. Crop the photograph to its subject first (so the mark is inside it), or drop the mark.`);
    }
    return {u, v};
  });
  // A NARROW plate sits LEFT, not centred. Centred, it leaves two thin margins and the callouts all
  // choose the same one anyway (placeLabel picks by room, and every mark had more room on one side), so
  // the frame came out with a dead half. Left-weighted, the picture and its margin of notes read as one
  // composition — which is what an annotated plate has always been. A plate wide enough to need no margin
  // stays centred, because then the callouts sit inside it.
  // ...and a plate with NO marks has no notes to hold a margin for. Now that `marks` defaults to none (see the
  // header), left-weighting an unannotated plate would leave half the frame as dead ground, so it centres.
  const needsMargin = shown.length > 0 && PW < W * 0.58;
  const px0 = needsMargin ? W * 0.085 : (W - PW) / 2;
  const px1 = px0 + PW;

  const plate = easeOutCubic(clamp01(seg(t, 0.02, 0.26)));
  const land = easeOutExpo(clamp01(seg(t, 0.68, 0.90)));
  const dot = Math.max(8, Math.round(base * 0.013));
  const chipPad = Math.round(base * 0.010);
  const chipFont = Math.round(base * 0.030);


  // ── LAYING THE CALLOUTS OUT AGAINST EACH OTHER ────────────────────────────────────────────────────────
  // Each chip used to be centred on its own mark and nothing else. Marks are wherever the SUBJECT put them,
  // so on any photograph with two features close together the labels landed on top of one another: rendered
  // with three marks 6% apart, the first chip was entirely hidden behind the third and the second's closing
  // words showed through it. That is the decodability floor failing, silently, on content the register is
  // specifically for — a photograph is annotated densely where the interesting part is.
  //
  // So the chips are laid out as a COLUMN that wants to be at its marks' heights: preferred position first,
  // then a downward sweep that pushes any overlap apart, then an upward sweep if that ran past the bottom.
  // Both sweeps stay inside the plate's own vertical extent, so a chip can never drift into the caption
  // block or the burned-subtitle band. When nothing collides, every chip keeps exactly the height it asked
  // for and this is a no-op.
  const laidOut = (() => {
    const gap = dot + Math.round(W * 0.008);
    const items = shown.map((m, i) => {
      const text = String(m.label ?? '');
      const chars = [...text];
      const mShare = chars.length ? chars.filter((ch) => WIDE_CH.test(ch)).length / chars.length : 0;
      const roomL = px0 - W * 0.045, roomR = W - px1 - W * 0.045;
      const marginated = Math.max(roomL, roomR) > W * 0.16;

      // The chip's face is the DNA's MONO stack, and its advance comes from the one place that measured
      // it. A local 0.54 here was neither the mono 0.62 nor the proportional 0.52 — it belonged to no
      // font, and it under-predicted the wrap of every callout this register has ever drawn.
      const adv = chipFont * (latinAdvance(mono) * (1 - mShare) + cjkAdvance(mono) * mShare);
      // A MEASURE IS COUNTED IN CHARACTERS, not in frame width. `W * 0.24` was picked at 1920 (461px, a
      // comfortable chip) and silently became 259px at a 1080-wide portrait or 4:5 frame — about thirteen
      // characters, so the labels stacked one word per line in a margin that had 453px to give. That is the
      // same cramping `marginated` was introduced to cure, reintroduced by the cap meant to bound it. Bound
      // it by the type instead and it holds at any frame size and any type scale.
      // THE CHIP IS AS WIDE AS WHAT IT HOLDS, counted part by part with the advances that render it: the label
      // glyph by glyph; the number in front of it with its two non-breaking spaces, in the Latin advance of the
      // mono face (1.8em for one digit, 2.4em for two — a flat 1.6em under-counted both); and the box's own
      // padding (1.4 pads a side) and border, which sit INSIDE the width under border-box and were budgeted as one
      // pad a side. A short label has no slack to absorb those, so it broke its last glyph onto a second line.
      // A quarter em of give covers the estimate; the measure still caps a long label, which then wraps.
      const w1 = (ch: string) => chipFont * (WIDE_CH.test(ch) ? cjkAdvance(mono) : latinAdvance(mono));
      const prefixW = m.n != null ? (String(m.n).length + 2) * chipFont * latinAdvance(mono) : 0;
      const boxX = chipPad * 1.4 * 2 + hair * 2;
      const chipMax = marginated
        ? Math.min(boxX + prefixW + CHIP_MEASURE * adv, Math.max(roomL, roomR))
        : PW * 0.42;
      const chipW = Math.min(chipMax, boxX + prefixW + chars.reduce((a, c) => a + w1(c), 0) + chipFont * 0.25);
      const mx = px0 + onPlate[i].u * PW;
      const my = top + onPlate[i].v * PH;
      // The SAME advance estimate that sized the chip, reused to predict how the text wraps inside it —
      // one estimate, so the height cannot disagree with the width it was derived from.
      const inner = Math.max(1, chipW - boxX);
      // GREEDY WORD WRAP, simulated — not total-width / line-width. CSS breaks at word boundaries, so a
      // line ends wherever the next word does not fit, and the ideal-packing estimate is optimistic by up
      // to a word per line. It under-counted by one on a 44-character label, and the extra line was CLIPPED
      // by the box height derived from the same count. The chip's face is MONOSPACE, so simulating the
      // break is not an approximation: per-character advance is a constant, taken from runtime/layout's
      // measured table — the same number that sized the chip, so height cannot disagree with width.
      const wordW = (s2: string) => s2.split('').reduce((a, c) => a + w1(c), 0);
      // Standard greedy: the space BEFORE a word is paid only if the word joins the current line. Charging
      // it unconditionally counted a trailing space that CSS drops at a break, and over-counted by a line on
      // a label that fitted — the box then carried an empty line's worth of dead space under its last word.
      const spaceW = w1(' ');
      let lines = 1, used = prefixW;
      for (const word of text.split(/\s+/)) {
        if (!word) continue;
        const ww = wordW(word);
        // A word wider than the whole line breaks INSIDE itself (which is what a CJK run does at every
        // glyph), so it costs the lines it needs rather than one impossible one.
        if (ww > inner) {
          const total = used + ww;
          lines += Math.ceil(total / inner) - 1;
          used = total % inner;
          continue;
        }
        const cost = (used > 0 ? spaceW : 0) + ww;
        if (used + cost > inner) {lines += 1; used = ww;} else {used += cost;}
      }
      lines = Math.max(1, lines);
      const chipH = Math.ceil(lines * chipFont * 1.25 + chipPad * 2 + hair * 2);
      let left: number, align: 'left' | 'right';
      if (marginated) {
        const useRight = roomR >= roomL;
        left = useRight ? px1 + gap : Math.max(W * 0.045, px0 - gap - chipW);
        align = useRight ? 'left' : 'right';
      } else {
        const p = placeLabel(mx, px0 + hair * 3, px1 - hair * 3, chipW, gap);
        left = p.left; align = p.align;
      }
      return {m, i, mx, my, cy: my, chipW, chipH, left, align, text};
    });
    

    const yMin = top, yMax = bottom;
    const need = items.reduce((a, it) => a + it.chipH, 0) + Math.max(0, items.length - 1) * (hair * 6);
    const order = items.map((_, k) => k).sort((a, b) => items[a].my - items[b].my);
    if (need > yMax - yMin) {
      // More label than plate. Nothing can keep them all apart, so spread them EVENLY instead of letting
      // them pile up at whatever heights the marks happened to have — cramped and readable in order beats
      // three labels in one place.
      const step = (yMax - yMin) / items.length;
      order.forEach((k, r) => {items[k].cy = yMin + step * (r + 0.5);});
      return items;
    }
    const pad = hair * 6;
    let cursor = yMin;
    for (const k of order) {                       // downward sweep: never start above the previous bottom
      const it = items[k];
      it.cy = Math.max(it.my, cursor + it.chipH / 2);
      cursor = it.cy + it.chipH / 2 + pad;
    }
    cursor = yMax;
    for (let r = order.length - 1; r >= 0; r--) {  // upward sweep: pull the stack back inside the bottom
      const it = items[order[r]];
      it.cy = Math.min(it.cy, cursor - it.chipH / 2);
      cursor = it.cy - it.chipH / 2 - pad;
    }
    return items;
  })();

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {title ? (
        <div style={{position: 'absolute', left: Math.min(px0, W * 0.085), top: CONTENT_TOP - H * 0.055, opacity: plate,
          font: `600 ${Math.round(base * 0.022)}px/1.2 ${mono}`, color: ACC,
          letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{title}</div>
      ) : null}

      {/* the photograph, filling the plate. `cover` on purpose: a plate is a frame the image fills, and
          `contain` would letterbox the film's own ground into the middle of the picture. */}
      <div style={{position: 'absolute', left: px0, top, width: PW, height: PH, overflow: 'hidden',
        background: SURF, border: `${hair * 2}px solid ${LINE}`, boxSizing: 'border-box',
        opacity: plate, transform: `scale(${0.985 + 0.015 * plate})`}}>
        {src ? (
          // Remotion's <Img> blocks the frame until the file has decoded, and FAILS LOUDLY if it is
          // missing — which is what should happen: a plate with no photograph is not a plate.
          <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        ) : (
          <div style={{width: '100%', height: '100%', display: 'flex', alignItems: 'center',
            justifyContent: 'center', color: DIM, font: `500 ${Math.round(base * 0.025)}px/1.4 ${mono}`}}>
            no image supplied
          </div>
        )}
      </div>

      {/* THE MARKS — placed at points IN the photograph, arriving in the order the voice names them.
          They ride a LIFTED plane: a label the film has added is not part of the photograph, and the
          shadow is what says so. */}
      <Plane depth={DEPTH.lifted}>
        {laidOut.map(({m, i, mx, my, cy, chipW, chipH, left, align, text}) => {
          const st = 0.30 + i * (0.42 / Math.max(1, shown.length));
          const on = easeOutCubic(clamp01(seg(t, st, st + 0.20)));
          if (on <= 0) return null;
          const leftSide = align !== 'left';
          const nearX = leftSide ? left + chipW : left;
          // A mark with no label drew an EMPTY chip with a leader running to it: a rectangle carrying nothing,
          // which is precisely the frame furniture a viewer cannot decode in a second. The ring still marks
          // the point — that is the mark's whole job — and the label that was never supplied is not invented.
          const labelled = text.trim().length > 0 || m.n != null;
          return (
            <React.Fragment key={i}>
              {/* THE LEADER IS AN ELBOW, because the chip no longer sits at its mark's height. It runs
                  horizontally out of the point, then turns and rises or falls to the chip it belongs to —
                  the classic annotated-plate form, and the only one that stays unambiguous once two marks
                  close together have had their labels moved apart. When a chip did not move, the vertical
                  leg is zero-length and this draws exactly the straight leader it always did. */}
              {labelled ? <div style={{position: 'absolute', top: my - hair,
                left: leftSide ? nearX : mx, width: Math.max(0, leftSide ? mx - nearX : left - mx),
                height: hair * 2, background: ACC, opacity: on * 0.9}} /> : null}
              {labelled ? <div style={{position: 'absolute', left: nearX - hair, top: Math.min(my, cy),
                width: hair * 2, height: Math.abs(cy - my), background: ACC, opacity: on * 0.9}} /> : null}
              {/* the point itself — a ring, so it marks WITHOUT covering what it marks */}
              <div style={{position: 'absolute', left: mx - dot, top: my - dot, width: dot * 2, height: dot * 2,
                borderRadius: dot * 2, border: `${hair * 3}px solid ${ACC}`, opacity: on,
                transform: `scale(${0.5 + 0.5 * on})`}} />
              {/* Placed at the height the layout pass gave it — which is its mark's height whenever nothing
                  else wanted that space. Centring every chip on its own mark by transform ignored the other
                  chips entirely: three marks a few percent apart put three labels in the same place, and the
                  first was completely buried under the third. */}
              {/* The predicted height RESERVES the slot; the box itself is sized by its own text. Forcing the
                  prediction onto the box was wrong in both directions — as `height` it CLIPPED the last line
                  when the estimate came in short, and as `minHeight` it left an empty line of dead space
                  whenever the estimate (deliberately conservative, so a caption can never overflow its band)
                  came in long. Centred on `cy`, a box shorter than its slot stays inside it. */}
              {labelled ? (
              <div style={{position: 'absolute', left, top: cy, width: chipW, transform: 'translateY(-50%)',
                opacity: on, background: SURF, border: `${hair}px solid ${LINE}`,
                padding: `${chipPad}px ${chipPad * 1.4}px`, boxSizing: 'border-box',
                font: `600 ${chipFont}px/1.25 ${mono}`, color: FG,
                // A label is whatever the film supplied, and an unbreakable one is not exotic: a URL, a file
                // path, a binomial, a German compound. CSS will not break a word on its own, so a 52-character
                // run walked straight out of its box and across the frame to the far margin — the chip's width
                // was respected by the layout and ignored by the text. The wrap simulation already COUNTS such
                // a word as breaking inside itself; this is what makes the browser agree.
                overflowWrap: 'anywhere',
                // a label that does wrap (past the measure) shares its lines out, never leaving one glyph alone
                textWrap: 'balance',
                textAlign: leftSide ? 'right' : 'left'}}>
                {m.n != null ? <span style={{color: ACC}}>{m.n}&nbsp;&nbsp;</span> : null}{text}
              </div>) : null}
            </React.Fragment>
          );
        })}
      </Plane>

      {/* what the plate IS, and the licence line it requires — ONE flow block, so the credit sits under
          whatever the caption turned out to be rather than at an offset that assumed one line. */}
      {/* The caption block keeps a readable measure even when the plate is narrow — it describes the plate,
          it is not part of it, and squeezing it to a portrait plate's width truncated it mid-phrase. */}
      <div style={{position: 'absolute', left: px0, top: bottom + capGap,
        width: Math.max(PW, W * 0.46), opacity: land}}>
        {/* Clamped by HEIGHT rather than by the `-webkit-box` + line-clamp idiom: it does the same job
            without depending on a legacy box model, and the reserve above is already computed in these
            same units, so the two cannot disagree. */}
        <div style={{font: `700 ${capSize}px/1.25 ${disp}`, color: FG, width: '100%',
          maxHeight: Math.round(capSize * 1.25 * capLines), overflow: 'hidden'}}>{caption}</div>
        {credit ? (
          <div style={{marginTop: Math.round(creditSize * 0.5), opacity: 0.85,
            font: `400 ${creditSize}px/1.35 ${mono}`, color: DIM}}>{credit}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default PhotoPlate;
