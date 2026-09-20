// Aliasing — the specific MRI artifact, on the REAL scan: undersample k-space and the anatomy WRAPS AROUND,
// folding a shifted copy of itself on top (a ghost). Generic digital "datamosh" glitch showed corruption, not
// this fold-over. The image is a prop → generalises. Deterministic; credit line for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA, contrastOf, readableOn, tint} from '../runtime/dna';
import {onLight, ACCENT_CONTRAST_MIN, INK_CONTRAST_MIN} from '../runtime/light';
import {bottomInset, fitContentSquare, inkBlockH} from '../runtime/layout';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
// THE DIAGRAM'S OWN TERMS. Two of these were already declared; the other two belong with them and were
// simply missed. `ghost:` is the LABEL of the annotation whose explanation sits directly beneath it — half
// an annotation translatable and half not would be worse than either. `synthetic phantom` is the register
// keeping the promise it makes to itself twenty lines down ("never let a drawn ellipse pass for a scan"): it
// marks the picture as DRAWN whenever no real scan was supplied, so it is provenance, not copy, and a film
// must not be able to word it away.
export const INTRINSIC_TEXT = [
  'ghost:',
  'a wrapped copy folds in',
  'undersample → Nyquist violated → wrap-around',
  'synthetic phantom',
];

/**
 * A deterministic SYNTHETIC phantom, for when no real scan was fetched.
 *
 * WHY NOT REFUSE, the way the four evidence registers do. Their premise is *this artefact is the evidence*,
 * so without the artefact they have nothing to say. This register's premise is a PHYSICS DEMONSTRATION —
 * undersample and a shifted copy folds back over the image — and that demonstration works on any structured
 * field. Given no `src` it used to draw an empty outlined box with a dashed line across it and three labels
 * pointing at the fold-over: the one thing the frame exists to show was the one thing missing.
 *
 * LABELLED AS SYNTHETIC on the frame, always. The register's own header calls this "the REAL scan", and a
 * drawn ellipse presented without a word is a picture a viewer will read as one — inventing evidence is a
 * worse failure than the hole it replaces.
 */
/** The plate's own ground. A scan viewport is black in every reader that has ever shown one — the phantom
 *  paints it, and a real `src` is a scan that brings its own — so anything drawn ON the plate is judged
 *  against THIS and not against the film's paper. */
const PLATE = '#05070c';

const Phantom: React.FC<{ink: string}> = ({ink}) => (
  <svg viewBox="0 0 100 100" width="100%" height="100%" preserveAspectRatio="none"
    style={{display: 'block', background: PLATE}}>
    <defs>
      <radialGradient id="ph-body" cx="50%" cy="44%" r="62%">
        <stop offset="0%" stopColor="#e8eef6" stopOpacity="0.92" />
        <stop offset="70%" stopColor="#9fb0c6" stopOpacity="0.72" />
        <stop offset="100%" stopColor="#39445a" stopOpacity="0.55" />
      </radialGradient>
    </defs>
    {/* An elliptical body with interior structure. Two requirements, and the second is not cosmetic:
        (1) contrast at several scales, so a half-frame shift of it is legible AS a shifted copy rather than
            as a blur — a flat disc folds onto itself invisibly;
        (2) ASYMMETRY, top-to-bottom and left-to-right. A mirror-symmetric phantom shifted by half a frame
            looks like the same phantom, so the viewer cannot tell a ghost from the original and the whole
            demonstration collapses. The first version was symmetric — and read as a cartoon face, two eyes
            and a smile, which is its own problem on an MRI physics beat. */}
    <ellipse cx="50" cy="50" rx="33" ry="43" fill="url(#ph-body)" />
    <ellipse cx="50" cy="50" rx="33" ry="43" fill="none" stroke="#dbe6f4" strokeOpacity="0.5" strokeWidth="0.7" />
    <path d="M31 24 Q50 16 69 26 Q64 40 50 38 Q36 38 31 24 Z" fill="#f2f7ff" opacity="0.5" />
    <ellipse cx="43" cy="55" rx="14" ry="19" fill="#0d1420" opacity="0.8" />
    <ellipse cx="60" cy="47" rx="6" ry="9" fill="#0d1420" opacity="0.55" />
    <ellipse cx="55" cy="74" rx="9" ry="5" fill="#f2f7ff" opacity="0.65" />
    <path d="M28 62 Q40 70 44 84" fill="none" stroke={ink} strokeOpacity="0.6" strokeWidth="1.1" />
    <path d="M66 34 Q72 48 68 62" fill="none" stroke={ink} strokeOpacity="0.35" strokeWidth="0.9" />
    <circle cx="37" cy="35" r="2.2" fill="#f2f7ff" opacity="0.9" />
  </svg>
);

export const Aliasing: React.FC<{src?: string; accent?: string; label?: string; credit?: string}> = ({
  src, accent: ACC, label = 'The anatomy folds onto itself', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // THE INK IS THE FILM'S — EXCEPT WHAT IS DRAWN ON THE PLATE. The title, the ghost annotation and the
  // Nyquist line were literals picked for a near-black ground, and all eight DNA presets are near-black, so
  // on a film whose DNA came from a warm-white deck they drew white on white (measured median 1.16:1 over
  // 86% of the marks, `scripts/ink_contrast_qa.py`); those read from the DNA now. The plate is the
  // opposite case and must not follow: it is a scan, it paints its own night, and its marks — the fold-over
  // line, the phantom's own strokes, the provenance tag — would vanish INTO it if they took a light film's
  // dark ink. They are judged against `PLATE` instead. Each token keeps its OWN original literal as its
  // fallback, so an un-themed render is unchanged.
  const accent = ACC ?? dna?.accent ?? '#22d3ee';
  const ink = dna?.fg ?? '#dfe8f5';          // the title
  const inkGhost = dna?.fg ?? '#c9d6ea';     // what the ghost IS, under its label
  const meta = dna?.dim ?? '#8aa';           // the Nyquist line under the plate
  const metaCredit = dna?.dim ?? '#5f6b7d';  // the CC-BY credit
  // the ghost's own warning colour, which is a MEANING and not a palette choice — kept while it reads on
  // the film's ground, and taken to its dark twin when the ground is paper (measured 2.3:1 there)
  const ghostInk = readableOn(dna?.bg ?? '#05060a', '#ff8ad0', '#8f1d5f');
  // ...and the marks that live on the plate, lifted until they read on ITS night rather than on the paper
  const onPlate = (c: string, floor: number) => (contrastOf(c, PLATE) >= floor ? c : tint(c, 0.6));
  const plateAccent = onPlate(accent, ACCENT_CONTRAST_MIN);
  const tagInk = onPlate(dna?.dim ?? '#93a3b8', INK_CONTRAST_MIN);
  // A DROP SHADOW TUNED FOR A DARK GROUND IS A SMUDGE ON PAPER. `#000a` is black at two-thirds alpha
  // blurred 60px, which is invisible under a plate on near-black and, measured on a warm-white film, takes
  // the paper directly beneath the plate from 246 to 135 — the Nyquist line under it is then read
  // against a grey stain rather than against the page. The shadow itself is
  // right; its weight is not, so it lightens on a light ground and is untouched everywhere else.
  const plateShadow = onLight(dna) ? '#0003' : '#000a';
  // THE RESERVE HAS TO MATCH THE BRANCH THAT SPENDS IT. `bottomReserve: 44` is right beside the plate,
  // where the note sits 34 under it — and wrong when the annotation STACKS, where the note steps down to
  // +118 and needs its ink too. At 4:5 that put 'undersample -> Nyquist violated -> wrap-around' inside the
  // caption band. The square is measured twice: once to learn whether the side room exists, then again with
  // the reserve that branch actually spends. A second fit is cheaper than a note under the subtitle.
  const probe = fitContentSquare(W, H, {hFrac: 0.85, wFrac: 0.4, bottomReserve: 44});
  const stackedFit = W - (probe.left + probe.S) - 30 < 270;
  const {S, left, top} = fitContentSquare(W, H, {hFrac: 0.85, wFrac: 0.4,
    bottomReserve: stackedFit ? 118 + inkBlockH(19) : 44});
  // STACK when the side is too narrow, decided by the ROOM, not by naming aspects: the ghost annotation
  // needs ~260px beside the plate, which a 1080-wide portrait frame does not have (it rode 196px off the
  // edge). Portrait frames are tall where they are narrow, so the annotation goes UNDER the plate and the
  // Nyquist note steps down to make room.
  const stacked = stackedFit;   // decided on the probe above, so the reserve and the branch cannot disagree
  const gx = stacked ? left : left + S + 30;
  const gy = stacked ? top + S + 40 : top + S * 0.28;
  const noteY = stacked ? top + S + 118 : top + S + 34;
  const ghost = clamp01(seg(t, 0.2, 0.7));                   // the fold-over ghost grows as we undersample

  // ONE plate, drawn three times: the base and its two wrapped copies must be the same picture, or the
  // frame shows two different things overlapping instead of one thing folding onto itself.
  const plate = (wrapped: boolean, top?: string) => {
    const style: React.CSSProperties = wrapped
      ? {position: 'absolute', top, width: '100%', height: '100%', objectFit: 'cover',
         opacity: ghost * 0.6, mixBlendMode: 'screen'}
      : {width: '100%', height: '100%', objectFit: 'cover'};
    return src
      ? <Img src={staticFile(src)} style={style} />
      : <div style={{...style, position: wrapped ? 'absolute' : 'relative'}}><Phantom ink={plateAccent} /></div>;
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <div style={{position: 'absolute', left, top, width: S, height: S, borderRadius: 6, overflow: 'hidden',
        boxShadow: `0 0 0 1.5px ${accent}88, 0 20px 60px ${plateShadow}`}}>
        {plate(false)}
        {/* the wrapped copy: shifted by half, wrapping top→bottom, overlaid = the fold-over ghost */}
        {plate(true, '-50%')}
        {plate(true, '50%')}
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <line x1={left} y1={top + S / 2} x2={left + S} y2={top + S / 2} stroke={plateAccent} strokeWidth={1.4} strokeDasharray="5 6" opacity={ghost * 0.7} />
        <text x={gx} y={gy} fill={ghostInk} fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700} opacity={ghost}>ghost:</text>
        <text x={gx} y={gy + 30} fill={inkGhost} fontSize="20" fontFamily="var(--f-body, Inter, sans-serif)" opacity={ghost}>a wrapped copy folds in</text>
        <text x={left + S / 2} y={noteY} textAnchor="middle" fill={meta} fontSize="19" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t, 0.1, 0.4))}>undersample → Nyquist violated → wrap-around</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: bottomInset(W, H, 8), color: metaCredit, font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
      {/* never let a drawn ellipse pass for a scan */}
      {!src ? (
        <div style={{position: 'absolute', left: left + 10, top: top + S - 30, color: tagInk,
          font: "500 15px/1.2 var(--f-mono, 'JetBrains Mono', monospace)", letterSpacing: '0.06em'}}>
          synthetic phantom
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default Aliasing;
