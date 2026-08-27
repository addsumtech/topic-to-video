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

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP, placeLabel} from '../runtime/layout';
import {Plane, DEPTH} from '../runtime/depth';
import {useDNA} from '../runtime/dna';

export const DURATION = 175;

// The register's own diagnostic, not any film's copy: a plate with no photograph says so on the frame
// rather than rendering an empty box that looks like a design choice.
export const INTRINSIC_TEXT = ['no image supplied'];

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7', SURF_D0 = '#f6f1e6';

type Mark = {x?: number; y?: number; label?: string; n?: number};

export const PhotoPlate: React.FC<{
  src?: string;             // the real photograph, relative to the film's public dir
  title?: string;           // the plate's kicker
  caption?: string;         // what the plate IS — set under it, in the display face
  marks?: Mark[];           // things to point at, in fractions of the PLATE (0..1)
  credit?: string;          // the licence line a license-clean image requires
}> = ({
  src,
  title = '',
  caption = 'the thing itself',
  marks: MARKS = [{x: 0.32, y: 0.44, label: 'what to notice here'},
                  {x: 0.72, y: 0.62, label: 'and here'}],
  credit = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const disp = dna?.fontDisplay ?? 'Georgia, serif';
  const mono = dna?.fontMono ?? 'ui-monospace, monospace';
  const hair = Math.max(1, Math.round(W * 0.0011));
  // Type is sized off the NARROW dimension, which is the rule this library's scaffold states and the reason
  // is visible here: keyed to W, the mark labels came out at 15px on a 1080-wide portrait frame — present
  // and unreadable — while reading correctly at 16:9. The fractions are calibrated so the landscape sizes
  // are unchanged and portrait simply stops shrinking. The ratio between the plate's caption and its
  // auxiliary text (~0.57) is the same one a broadcast readability floor asks for.
  const base = Math.min(W, H);

  // THE PLATE IS THE SUBJECT, so it takes the content zone rather than a polite inset. It keeps a margin
  // only wide enough for the plate's own rule and its caption — the point of this register is that the
  // photograph is large enough to be READ, not acknowledged.
  const top = CONTENT_TOP + H * 0.01;
  const MAX_PLATE_ASPECT = 2.3;      // capped on the WIDE side: an uncapped plate came out a 2.78:1 slit
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
    const h = Math.max(1, (H - captionBand(W, H) - reserveFor(lines)) - top);
    return Math.min(W - W * 0.17, h * MAX_PLATE_ASPECT);
  };
  const linesIn = (w: number) =>
    Math.max(1, Math.min(2, Math.ceil(capText.length / Math.max(8, Math.floor(w / (capSize * advance))))));
  const capLines = linesIn(plateWidthFor(linesIn(plateWidthFor(1))));
  const capH = reserveFor(capLines);
  const bottom = H - captionBand(W, H) - capH;
  // The plate takes the content zone, but its ASPECT is capped. Left to fill the width it came out at
  // 2.78:1 on a 16:9 frame — a cinemascope slit that happened to suit this photograph and would have cut
  // the subject out of a portrait one. The cap is on the WIDE side only: a tall frame wants a tall plate,
  // and cropping a landscape photograph to it is what a portrait film asks for anyway.
  const PH = Math.max(1, bottom - top);
  const PW = Math.min(W - W * 0.17, PH * MAX_PLATE_ASPECT);
  const px0 = (W - PW) / 2, px1 = px0 + PW;

  const plate = easeOutCubic(clamp01(seg(t, 0.02, 0.26)));
  const land = easeOutExpo(clamp01(seg(t, 0.68, 0.90)));
  const dot = Math.max(8, Math.round(base * 0.013));
  const chipPad = Math.round(base * 0.010);
  const chipFont = Math.round(base * 0.030);

  const shown = MARKS.slice(0, 5);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {title ? (
        <div style={{position: 'absolute', left: px0, top: CONTENT_TOP - H * 0.055, opacity: plate,
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
        {shown.map((m, i) => {
          const st = 0.30 + i * (0.42 / Math.max(1, shown.length));
          const on = easeOutCubic(clamp01(seg(t, st, st + 0.20)));
          if (on <= 0) return null;
          const mx = px0 + clamp01(m.x ?? 0.5) * PW;
          const my = top + clamp01(m.y ?? 0.5) * PH;
          const text = String(m.label ?? '');
          // the chip is measured from its own text, then clamped inside the PLATE — a mark near an edge
          // must not push its label off the picture it is pointing into
          // same advance problem as the caption: a CJK label is one glyph per em, so the Latin estimate
          // makes its chip half as wide as it needs and the label wraps into a tall stack
          const mShare = text.length
            ? text.replace(/[^\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/g, '').length / text.length : 0;
          const chipW = Math.min(PW * 0.42,
            chipPad * 2 + text.length * chipFont * (0.54 + 0.46 * mShare) + chipFont * 1.6);
          const gap = dot + Math.round(W * 0.008);
          const {left, align} = placeLabel(mx, px0 + hair * 3, px1 - hair * 3, chipW, gap);
          const leftSide = align !== 'left';
          return (
            <React.Fragment key={i}>
              {/* the leader, from the chip to the point */}
              <div style={{position: 'absolute', top: my - hair,
                left: leftSide ? left + chipW : mx, width: Math.max(0, leftSide ? mx - (left + chipW) : left - mx),
                height: hair * 2, background: ACC, opacity: on * 0.9}} />
              {/* the point itself — a ring, so it marks WITHOUT covering what it marks */}
              <div style={{position: 'absolute', left: mx - dot, top: my - dot, width: dot * 2, height: dot * 2,
                borderRadius: dot * 2, border: `${hair * 3}px solid ${ACC}`, opacity: on,
                transform: `scale(${0.5 + 0.5 * on})`}} />
              {/* centred on the mark by TRANSFORM, not by half a line's height: the chip wraps to two lines
                  whenever the label is long, and a one-line assumption hangs it below the point it names. */}
              <div style={{position: 'absolute', left, top: my, width: chipW, transform: 'translateY(-50%)',
                opacity: on, background: SURF, border: `${hair}px solid ${LINE}`,
                padding: `${chipPad}px ${chipPad * 1.4}px`, boxSizing: 'border-box',
                font: `600 ${chipFont}px/1.25 ${mono}`, color: FG,
                textAlign: leftSide ? 'right' : 'left'}}>
                {m.n != null ? <span style={{color: ACC}}>{m.n}&nbsp;&nbsp;</span> : null}{text}
              </div>
            </React.Fragment>
          );
        })}
      </Plane>

      {/* what the plate IS, and the licence line it requires — ONE flow block, so the credit sits under
          whatever the caption turned out to be rather than at an offset that assumed one line. */}
      <div style={{position: 'absolute', left: px0, top: bottom + capGap, width: PW, opacity: land}}>
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
