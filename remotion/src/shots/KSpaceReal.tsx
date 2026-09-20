// KSpaceReal — the ACTUAL k-space, not a decorative mandala. It shows the real FFT-magnitude of the MRI (a `src`
// prop, computed as the image's spatial-frequency spectrum): a grainy point-symmetric STARBURST, bright at the
// low-frequency centre, faint at the high-frequency periphery — and unmistakably NOT a recognizable picture. The
// kx/ky axes are labelled as spatial frequencies. Deterministic; credit line for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA, contrastOf, tint} from '../runtime/dna';
import {onLight, INK_CONTRAST_MIN, ACCENT_CONTRAST_MIN} from '../runtime/light';
import {CONTENT_TOP, bottomInset, contentBottom} from '../runtime/layout';

export const DURATION = 180; // 6s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  // the two AXES of a k-space plot. They belong to the diagram exactly as `x` and `y` belong to a graph.
  'kx',
  'ky',
  'periphery = high freq · detail',
  "the image's spatial frequencies — not the image",
];

export const KSpaceReal: React.FC<{src?: string; accent?: string; label?: string; credit?: string}> = ({
  src, accent: ACC, label = 'k-space — not a picture', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // THE TYPE IS THE FILM'S; THE SQUARE KEEPS ITS NIGHT. Two different things were wrong on a light ground
  // and they have two different answers. The labels and the title were literals picked for a near-black
  // ground — all eight DNA presets are near-black — so on a film whose DNA came from a warm-white deck they
  // drew white on white (measured median 1.12:1 over 99.97% of the marks, `scripts/ink_contrast_qa.py`);
  // those are ink and they read from the DNA below. The SQUARE is not ink: `src` is the FFT magnitude and it
  // is composited with `mix-blend-mode: screen`, and screen over paper IS paper — the k-space would be a
  // blank square with every label around it still perfectly legible, which is the most expensive shape this
  // defect takes. What the square holds is energy, and energy is drawn as light on a dark field, so the
  // SQUARE (not the frame — this is a diagram with a data panel in it) keeps its own ground when the film's
  // is paper. `#05060a` is the darkest stop of this register's own gradient, and with no DNA or a dark film
  // nothing is painted at all: the film's ground shows through exactly as before.
  const accent = ACC ?? dna?.accent ?? '#22d3ee';
  const ink = dna?.fg ?? '#dfe8f5';          // the title, and the label inside the square
  const meta = dna?.dim ?? '#9fb4cc';        // the kx / ky axis names
  const meta2 = dna?.dim ?? '#8aa';          // the two annotation lines above and below the square
  const metaCredit = dna?.dim ?? '#5f6b7d';  // the CC-BY credit
  const night = onLight(dna);
  const plateBg = night ? '#05060a' : undefined;
  const plateGround = night ? '#05060a' : (dna?.bg ?? '#05060a');
  // A DROP SHADOW TUNED FOR A DARK GROUND IS A SMUDGE ON PAPER. `#000a` is black at two-thirds alpha
  // blurred 60px, which is invisible under a plate on near-black and, measured on a warm-white film, takes
  // the paper directly beneath the plate from 246 to 135 — the line under the square is then read against a
  // grey stain rather than against the page, which was 23% of this register's marks. The shadow itself is
  // right; its weight is not, so it lightens on a light ground and is untouched everywhere else.
  const plateShadow = night ? '#0003' : '#000a';
  // A mark drawn ON that night reads against IT, never against the paper: a light film's `fg` is dark, and
  // dark on the square is the same disappearance one layer in.
  const onPlate = (c: string, own: string, floor: number = INK_CONTRAST_MIN) =>
    (contrastOf(c, plateGround) >= floor ? c : own);
  // the kx/ky axes run THROUGH the square, so they are judged on the night, not on the paper
  const axisInk = onPlate(accent, tint(accent, 0.6), ACCENT_CONTRAST_MIN);
  // Centred in the CONTENT ZONE, not in the frame, and reserving room for the line it hangs under itself.
  // Centred in the frame, the square's own caption — "the image's spatial frequencies — not the image" —
  // landed inside the strip the renderer burns the real caption over. Deriving from the zone also makes the
  // square correct at aspects where H * 0.62 is meaningless.
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const labelRoom = Math.round(Math.min(W, H) * 0.05);
  const S = Math.max(120, Math.min(zoneBot - zoneTop - labelRoom, W * 0.42));
  const left = (W - S) / 2, top = zoneTop + (zoneBot - labelRoom - zoneTop - S) / 2;
  const cx = left + S / 2, cy = top + S / 2;
  const app = clamp01(seg(t, 0.08, 0.5));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      {/* the real k-space, tinted into the palette */}
      <div style={{position: 'absolute', left, top, width: S, height: S, borderRadius: 6, overflow: 'hidden',
        background: plateBg, boxShadow: `0 0 0 1.5px ${accent}88, 0 20px 60px ${plateShadow}`, opacity: app}}>
        {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover',
          filter: 'saturate(0) brightness(1.05)', mixBlendMode: 'screen'}} /> : null}
        <AbsoluteFill style={{background: `radial-gradient(60% 60% at 50% 50%, ${accent}22, #0000 70%)`, mixBlendMode: 'screen'}} />
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* kx / ky axes = spatial frequencies */}
        <line x1={left - 26} y1={cy} x2={left + S + 26} y2={cy} stroke={`${axisInk}55`} strokeWidth={1} opacity={app} />
        <line x1={cx} y1={top - 26} x2={cx} y2={top + S + 26} stroke={`${axisInk}55`} strokeWidth={1} opacity={app} />
        <text x={left + S + 32} y={cy + 6} fill={meta} fontSize="24" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={app}>kx</text>
        <text x={cx - 8} y={top - 32} fill={meta} fontSize="24" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={app}>ky</text>
        <text x={cx} y={cy - S * 0.5 - 6} textAnchor="middle" fill={meta2} fontSize="17" fontFamily="var(--f-body, Inter, sans-serif)" opacity={clamp01(seg(t,0.5,0.7))}>periphery = high freq · detail</text>
        <text x={cx} y={cy + 8} textAnchor="middle" fill={onPlate(ink, '#dfe8f5')} fontSize="17" fontFamily="var(--f-body, Inter, sans-serif)" opacity={clamp01(seg(t,0.4,0.6))}>center = low freq</text>
        <text x={cx} y={cy + S * 0.5 + 30} textAnchor="middle" fill={meta2} fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t,0.55,0.75))}>the image's spatial frequencies — not the image</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: bottomInset(W, H, 8), color: metaCredit, font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default KSpaceReal;
