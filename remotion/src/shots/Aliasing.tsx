// Aliasing — the specific MRI artifact, on the REAL scan: undersample k-space and the anatomy WRAPS AROUND,
// folding a shifted copy of itself on top (a ghost). Generic digital "datamosh" glitch showed corruption, not
// this fold-over. The image is a prop → generalises. Deterministic; credit line for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {fitContentSquare} from '../runtime/layout';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'a wrapped copy folds in',
  'undersample → Nyquist violated → wrap-around',
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
const Phantom: React.FC<{ink: string}> = ({ink}) => (
  <svg viewBox="0 0 100 100" width="100%" height="100%" preserveAspectRatio="none"
    style={{display: 'block', background: '#05070c'}}>
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
  src, accent = '#22d3ee', label = 'The anatomy folds onto itself', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const {S, left, top} = fitContentSquare(W, H, {hFrac: 0.85, wFrac: 0.4, bottomReserve: 44});  // leaves room for the wrap-around note below
  // STACK when the side is too narrow, decided by the ROOM, not by naming aspects: the ghost annotation
  // needs ~260px beside the plate, which a 1080-wide portrait frame does not have (it rode 196px off the
  // edge). Portrait frames are tall where they are narrow, so the annotation goes UNDER the plate and the
  // Nyquist note steps down to make room.
  const sideRoom = W - (left + S) - 30;
  const stacked = sideRoom < 270;
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
      : <div style={{...style, position: wrapped ? 'absolute' : 'relative'}}><Phantom ink={accent} /></div>;
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <div style={{position: 'absolute', left, top, width: S, height: S, borderRadius: 6, overflow: 'hidden',
        boxShadow: `0 0 0 1.5px ${accent}88, 0 20px 60px #000a`}}>
        {plate(false)}
        {/* the wrapped copy: shifted by half, wrapping top→bottom, overlaid = the fold-over ghost */}
        {plate(true, '-50%')}
        {plate(true, '50%')}
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <line x1={left} y1={top + S / 2} x2={left + S} y2={top + S / 2} stroke={accent} strokeWidth={1.4} strokeDasharray="5 6" opacity={ghost * 0.7} />
        <text x={gx} y={gy} fill="#ff8ad0" fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700} opacity={ghost}>ghost:</text>
        <text x={gx} y={gy + 30} fill="#c9d6ea" fontSize="20" fontFamily="var(--f-body, Inter, sans-serif)" opacity={ghost}>a wrapped copy folds in</text>
        <text x={left + S / 2} y={noteY} textAnchor="middle" fill="#8aa" fontSize="19" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t, 0.1, 0.4))}>undersample → Nyquist violated → wrap-around</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: 8, color: '#5f6b7d', font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
      {/* never let a drawn ellipse pass for a scan */}
      {!src ? (
        <div style={{position: 'absolute', left: left + 10, top: top + S - 30, color: '#93a3b8',
          font: "500 15px/1.2 var(--f-mono, 'JetBrains Mono', monospace)", letterSpacing: '0.06em'}}>
          synthetic phantom
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
export default Aliasing;
