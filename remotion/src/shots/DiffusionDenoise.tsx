// DiffusionDenoise — the generative-reconstruction frontier, encoded: a field of pure NOISE is iteratively
// DENOISED into the real MRI, while a data-consistency clamp keeps it pinned to the measurements. Merging blobs
// showed neither the noise nor the image. The image is a prop → generalises. Deterministic; credit for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomInset, fitContentSquare} from '../runtime/layout';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'noise → image · denoising steps ·',
  'pinned to the measured data',
];

export const DiffusionDenoise: React.FC<{src?: string; accent?: string; label?: string; credit?: string}> = ({
  src, accent = '#22d3ee', label = 'Denoise into an image', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const {S, left, top} = fitContentSquare(W, H, {hFrac: 0.85, wFrac: 0.4, bottomReserve: 66});  // leaves room for the ticks + label below
  const clean = clamp01(seg(t, 0.12, 0.86));                 // noise → image
  const noiseOp = 1 - clean;
  // deterministic noise grain, thinning as it denoises
  const grain: React.ReactNode[] = [];
  const n = Math.round(700 * noiseOp);
  for (let i = 0; i < n; i++)
    grain.push(<rect key={i} x={hash01(i * 2 + 1) * S} y={hash01(i * 2 + 5) * S} width={2 + hash01(i) * 4} height={2 + hash01(i * 3) * 4}
      fill={hash01(i * 7) > 0.5 ? '#fff' : accent} opacity={0.2 + hash01(i * 9) * 0.6} />);
  const step = Math.min(8, Math.max(1, Math.round(clean * 8)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <div style={{position: 'absolute', left, top, width: S, height: S, borderRadius: 6, overflow: 'hidden',
        boxShadow: `0 0 0 1.5px ${accent}88, 0 20px 60px #000a`}}>
        {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', opacity: clean}} /> : null}
        <svg width={S} height={S} style={{position: 'absolute', left: 0, top: 0}}>{grain}</svg>
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* denoising-step ticks */}
        {Array.from({length: 8}).map((_, i) => (
          <rect key={i} x={left + i * (S / 8)} y={top + S + 20} width={S / 8 - 6} height={6} rx={3}
            fill={i < step ? accent : '#2a3446'} opacity={i < step ? 0.9 : 0.5} />))}
        <text x={W / 2} y={top + S + 54} textAnchor="middle" fill="#8aa" fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">noise → image · denoising steps · <tspan fill={accent}>pinned to the measured data</tspan></text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: bottomInset(W, H, 8), color: '#5f6b7d', font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default DiffusionDenoise;
