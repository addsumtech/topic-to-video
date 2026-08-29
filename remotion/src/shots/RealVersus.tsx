// RealVersus — a comparison carried by REAL images, not drawn panels. Two real scans side by side (e.g. a T1 vs
// a T2 slice — the actual contrast difference; or the same scan labelled 9:56 vs 5:33 — same result, half the
// time). The design technique (split + divider + wipe-in) frames REAL substance. Images are props → generalises
// to any two-image comparison. Deterministic; credit line for CC-BY.
//
// THE INK COMES FROM THE DNA, NOT FROM THE FILM THIS WAS BORN IN. The register used to read only `bg`/`bgGrad`
// from the design system and keep every other colour hardcoded for its native near-black theme. Rendered into
// the delivered "section" film (cream ground #EFE7D8) that put a #c9d6ea title and #dfe8f5 panel labels on
// cream: measured on the actual frame, the title read 1.20:1 and the labels 1.29:1 against the ground under
// them — against the bare ground the labels are 1.005:1, i.e. the same colour. WCAG's floor for large text is
// 3:1. It was the least legible frame in a 35-beat film while being one of only three beats that show a real
// photograph. Every ink, container fill, border and rule below now resolves `dna?.token ?? <the original
// value>`, so an un-themed render is byte-identical and a themed one belongs to its film.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom} from '../runtime/layout';
import {lumValue} from '../runtime/shotLuma';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s

// The divider marker belongs to the FORM (it is what makes this a versus and not a diptych), so it is declared
// intrinsic rather than smuggled in as a bare literal.
export const INTRINSIC_TEXT = ['vs'];

// The register's own dark-theme palette — kept verbatim as the null-DNA fallback so an un-themed render is
// unchanged, and superseded token-for-token the moment a film supplies a design system.
const TITLE_D0 = '#c9d6ea', LABEL_D0 = '#dfe8f5', DIM_D0 = '#5f6b7d';
const ACC_D0 = '#22d3ee', SURF_D0 = '#0b1120', CHIP_INK_D0 = '#eaf6ff';

export const RealVersus: React.FC<{srcLeft?: string; srcRight?: string; labelLeft?: string; labelRight?: string;
  title?: string; credit?: string; accent?: string}> = ({
  srcLeft, srcRight, labelLeft = '', labelRight = '', title = '', credit = '', accent,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // Every ink from the system; the caller's explicit `accent` still wins over the film's, as before.
  const TITLE = dna?.fg ?? TITLE_D0;        // the title states the comparison — primary ink, not a whisper
  const LABEL = dna?.fg ?? LABEL_D0;        // the two terms being compared are primary ink too
  const DIM = dna?.dim ?? DIM_D0;           // the licence line is metadata
  const ACC = accent ?? dna?.accent ?? ACC_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const CHIP_INK = dna?.fg ?? CHIP_INK_D0;
  const mono = dna?.fontMono ?? "var(--f-mono, 'JetBrains Mono', monospace)";
  const body = dna?.fontBody ?? 'var(--f-body, Inter, system-ui, sans-serif)';
  const radius = dna?.radius ?? 8;

  // Type and spacing off the NARROW dimension: the old bare literals (30px labels, 26px title, 14px credit)
  // are 2.8%/2.4%/1.3% of a 1920x1080 frame but only 1.6%/1.4%/0.7% of a 1080-wide portrait one. Fractions are
  // calibrated so every 1080p size is the integer it was.
  const M = Math.min(W, H);
  const px = (frac: number) => Math.round(M * frac);
  const labelSize = px(0.0278);   // 30 @1080
  const titleSize = px(0.0241);   // 26 @1080
  const creditSize = px(0.013);   // 14 @1080
  const chipD = px(0.0481);       // 52 @1080
  const chipInk = px(0.0204);     // 22 @1080
  const chipRing = Math.max(1, px(0.00185));   // 2 @1080
  const gap = px(0.0833);         // 90 @1080
  const slide = px(0.037);        // 40 @1080 — the wipe-in offset
  const labelGap = px(0.0148);    // 16 @1080
  const strip = labelGap + Math.round(labelSize * 1.15);   // the label line under a panel

  // THE PANELS LIVE IN THE CONTENT ZONE, not in the whole frame. Centred on H/2 the label's line box closed at
  // y=852.5 against a caption band that opens at 852 (captionBand at 1080p = 228px) — the burned narration sat
  // on the words. Derived from contentBottom() so it also holds at 9:16, where the band is 298px.
  const top0 = CONTENT_TOP, bot0 = contentBottom(W, H);
  const zoneH = Math.max(1, bot0 - top0);
  // PORTRAIT READS TOP/BOTTOM. Side by side on a 1080-wide frame each panel is capped at W*0.32 = 346px — two
  // stamps adrift in a 1446px-tall zone. Stacked they take 605px each and the comparison is legible.
  const stack = W < H;
  // A block sized to EXACTLY zoneH ends flush on the caption band's first pixel: with no slack the 9:16 panels
  // solved to 627px and the lower label's box closed at y=1622 against a band opening at 1622. `air` buys that
  // boundary ~22px at both ends; it is not binding at 16:9, where H*0.5 caps the panel first (verified: the
  // themed 16:9 frame is pixel-identical with and without it).
  const air = px(0.02);
  const S = stack
    ? Math.max(1, Math.min(W * 0.82, (zoneH - 2 * air - gap - 2 * strip) / 2))
    : Math.max(1, Math.min(H * 0.5, W * 0.32, zoneH - 2 * air - strip, (W - gap) / 2));
  const cx = W / 2;
  const blockH = stack ? 2 * S + gap + 2 * strip : S + strip;
  const py = top0 + (zoneH - blockH) / 2;
  const aPos = stack ? {x: cx - S / 2, y: py} : {x: cx - gap / 2 - S, y: py};
  const bPos = stack ? {x: cx - S / 2, y: py + S + strip + gap} : {x: cx + gap / 2, y: py};
  const chipCy = stack ? py + S + strip + gap / 2 : py + S / 2;

  const inL = easeOutCubic(clamp01(seg(t, 0.1, 0.5)));      // panels wipe in from their sides
  const inR = easeOutCubic(clamp01(seg(t, 0.22, 0.62)));

  // A 67%-black 60px drop shadow is a lift on a near-black ground and a smear of grime on a cream one: it is
  // what dragged the ground under the labels from Y=0.80 to Y=0.608 in the delivered film. Chosen by the
  // ground's measured luminance, so any light DNA gets the short soft version and any dark one keeps the deep
  // one (null when there is no DNA, or when its bg is a gradient string → the original).
  const groundY = lumValue(dna?.bg ?? null);
  const plateShadow = groundY !== null && groundY > 0.5
    ? `0 ${px(0.0093)}px ${px(0.0231)}px rgba(0,0,0,0.14)`
    : '0 20px 60px #000a';
  // The ring was a 1.5px accent at 53% alpha, which needs the alpha to sit softly on a dark plate. A themed
  // border is a hairline of the system's own weight and has to be solid to read at all.
  const ringW = dna ? Math.max(1, dna.borderWidth) : 1.5;
  const ring = dna ? ACC : `${ACC}88`;

  const panel = (src: string | undefined, pos: {x: number; y: number}, label: string, prog: number, dir: number) => (
    <>
      <div style={{position: 'absolute', left: pos.x, top: pos.y, width: S, height: S, borderRadius: radius,
        overflow: 'hidden', boxShadow: `0 0 0 ${ringW}px ${ring}, ${plateShadow}`, opacity: prog,
        transform: stack ? `translateY(${(1 - prog) * dir}px)` : `translateX(${(1 - prog) * dir}px)`}}>
        {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
      </div>
      <div style={{position: 'absolute', left: pos.x, top: pos.y + S + labelGap, width: S, textAlign: 'center',
        opacity: prog, color: LABEL, font: `700 ${labelSize}px/1.15 ${body}`}}>{label}</div>
    </>
  );

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      {/* Padded to the frame's own margin: full-bleed left:0/right:0, a long title ran to both edges. */}
      {title ? <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center',
        padding: `0 ${px(0.046)}px`, boxSizing: 'border-box',
        color: TITLE, font: `600 ${titleSize}px/1.1 ${mono}`, letterSpacing: dna?.labelSpacing ?? '0.18em',
        textTransform: dna && !dna.uppercaseLabels ? 'none' : 'uppercase',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{title}</div> : null}
      {panel(srcLeft, aPos, labelLeft, inL, -slide)}
      {panel(srcRight, bPos, labelRight, inR, slide)}
      <div style={{position: 'absolute', left: cx - chipD / 2, top: chipCy - chipD / 2, width: chipD,
        height: chipD, borderRadius: chipD / 2, background: SURF, border: `${chipRing}px solid ${ACC}`,
        color: CHIP_INK, display: 'flex', alignItems: 'center', justifyContent: 'center',
        font: `800 ${chipInk}px ${body}`, opacity: clamp01(seg(t, 0.5, 0.62))}}>{INTRINSIC_TEXT[0]}</div>
      {credit ? <div style={{position: 'absolute', left: px(0.0185), right: px(0.0185), bottom: px(0.0074),
        color: DIM, font: `400 ${creditSize}px/1.3 ${body}`}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default RealVersus;
