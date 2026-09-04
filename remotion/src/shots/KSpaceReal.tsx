// KSpaceReal — the ACTUAL k-space, not a decorative mandala. It shows the real FFT-magnitude of the MRI (a `src`
// prop, computed as the image's spatial-frequency spectrum): a grainy point-symmetric STARBURST, bright at the
// low-frequency centre, faint at the high-frequency periphery — and unmistakably NOT a recognizable picture. The
// kx/ky axes are labelled as spatial frequencies. Deterministic; credit line for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 180; // 6s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'periphery = high freq · detail',
  "the image's spatial frequencies — not the image",
];

export const KSpaceReal: React.FC<{src?: string; accent?: string; label?: string; credit?: string}> = ({
  src, accent = '#22d3ee', label = 'k-space — not a picture', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
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
        boxShadow: `0 0 0 1.5px ${accent}88, 0 20px 60px #000a`, opacity: app}}>
        {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover',
          filter: 'saturate(0) brightness(1.05)', mixBlendMode: 'screen'}} /> : null}
        <AbsoluteFill style={{background: `radial-gradient(60% 60% at 50% 50%, ${accent}22, #0000 70%)`, mixBlendMode: 'screen'}} />
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* kx / ky axes = spatial frequencies */}
        <line x1={left - 26} y1={cy} x2={left + S + 26} y2={cy} stroke={`${accent}55`} strokeWidth={1} opacity={app} />
        <line x1={cx} y1={top - 26} x2={cx} y2={top + S + 26} stroke={`${accent}55`} strokeWidth={1} opacity={app} />
        <text x={left + S + 32} y={cy + 6} fill="#9fb4cc" fontSize="24" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={app}>kx</text>
        <text x={cx - 8} y={top - 32} fill="#9fb4cc" fontSize="24" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={app}>ky</text>
        <text x={cx} y={cy - S * 0.5 - 6} textAnchor="middle" fill="#8aa" fontSize="17" fontFamily="var(--f-body, Inter, sans-serif)" opacity={clamp01(seg(t,0.5,0.7))}>periphery = high freq · detail</text>
        <text x={cx} y={cy + 8} textAnchor="middle" fill="#dfe8f5" fontSize="17" fontFamily="var(--f-body, Inter, sans-serif)" opacity={clamp01(seg(t,0.4,0.6))}>center = low freq</text>
        <text x={cx} y={cy + S * 0.5 + 30} textAnchor="middle" fill="#8aa" fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t,0.55,0.75))}>the image's spatial frequencies — not the image</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: 8, color: '#5f6b7d', font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default KSpaceReal;
