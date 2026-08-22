// Aliasing — the specific MRI artifact, on the REAL scan: undersample k-space and the anatomy WRAPS AROUND,
// folding a shifted copy of itself on top (a ghost). Generic digital "datamosh" glitch showed corruption, not
// this fold-over. The image is a prop → generalises. Deterministic; credit line for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {fitContentSquare} from '../runtime/layout';

export const DURATION = 165; // 5.5s

export const Aliasing: React.FC<{src?: string; accent?: string; label?: string; credit?: string}> = ({
  src, accent = '#22d3ee', label = 'The anatomy folds onto itself', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const {S, left, top} = fitContentSquare(W, H, {hFrac: 0.85, wFrac: 0.4, bottomReserve: 44});  // leaves room for the wrap-around note below
  const ghost = clamp01(seg(t, 0.2, 0.7));                   // the fold-over ghost grows as we undersample

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <div style={{position: 'absolute', left, top, width: S, height: S, borderRadius: 6, overflow: 'hidden',
        boxShadow: `0 0 0 1.5px ${accent}88, 0 20px 60px #000a`}}>
        {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
        {/* the wrapped copy: shifted by half, wrapping top→bottom, overlaid = the fold-over ghost */}
        {src ? <Img src={staticFile(src)} style={{position: 'absolute', top: '-50%', width: '100%', height: '100%',
          objectFit: 'cover', opacity: ghost * 0.6, mixBlendMode: 'screen'}} /> : null}
        {src ? <Img src={staticFile(src)} style={{position: 'absolute', top: '50%', width: '100%', height: '100%',
          objectFit: 'cover', opacity: ghost * 0.6, mixBlendMode: 'screen'}} /> : null}
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <line x1={left} y1={top + S / 2} x2={left + S} y2={top + S / 2} stroke={accent} strokeWidth={1.4} strokeDasharray="5 6" opacity={ghost * 0.7} />
        <text x={left + S + 30} y={top + S * 0.28} fill="#ff8ad0" fontSize="24" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={700} opacity={ghost}>ghost:</text>
        <text x={left + S + 30} y={top + S * 0.28 + 30} fill="#c9d6ea" fontSize="20" fontFamily="var(--f-body, Inter, sans-serif)" opacity={ghost}>a wrapped copy folds in</text>
        <text x={left + S / 2} y={top + S + 34} textAnchor="middle" fill="#8aa" fontSize="19" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t, 0.1, 0.4))}>undersample → Nyquist violated → wrap-around</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: 8, color: '#5f6b7d', font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default Aliasing;
