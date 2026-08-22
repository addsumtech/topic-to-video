// KSpaceAnatomy — how to READ k-space, encoded on the real data: the CENTER of k-space (low spatial frequency)
// holds the overall contrast, the EDGES (high spatial frequency) hold the fine detail. Proven by the two partial
// reconstructions — center-only k-space inverse-FFTs to a blurry contrast image, edge-only to pure outlines. A
// generic 2x2 "four ways it wins" grid showed none of this (and its bottom row collided with the caption). All
// three images are props → generalises to any modality. Deterministic; credit for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 175; // ~5.8s

export const KSpaceAnatomy: React.FC<{srcK?: string; srcLow?: string; srcHigh?: string;
  accent?: string; accent2?: string; label?: string; credit?: string}> = ({
  srcK, srcLow, srcHigh, accent = '#22d3ee', accent2 = '#a78bfa', label = 'Reading k-space', credit = '',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // phase A (center→contrast) then phase B (edges→detail)
  const pA = clamp01(seg(t, 0.12, 0.34));
  const pB = clamp01(seg(t, 0.5, 0.72));
  const K = 400, kx = W * 0.09, ky = H * 0.30;                 // the k-space panel (left)
  const P = 300, px = W * 0.56, py1 = H * 0.28, py2 = H * 0.28 + P + 40; // two recon panels (right, stacked)
  const kcx = kx + K / 2, kcy = ky + K / 2;

  const panel = (x: number, y: number, s: number, src: string | undefined, ring: string, op: number) => (
    <div style={{position: 'absolute', left: x, top: y, width: s, height: s, borderRadius: 6, overflow: 'hidden',
      boxShadow: `0 0 0 1.5px ${ring}, 0 14px 40px #000a`, opacity: op}}>
      {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
    </div>
  );

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      {/* k-space (grayscale FFT magnitude) */}
      {panel(kx, ky, K, srcK, `${accent}66`, 1)}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        {/* center zone = low spatial frequency → contrast */}
        <circle cx={kcx} cy={kcy} r={K * 0.1} fill="none" stroke={accent} strokeWidth={3}
          opacity={0.35 + 0.6 * pA} />
        {/* outer ring = high spatial frequency → detail */}
        <circle cx={kcx} cy={kcy} r={K * 0.46} fill="none" stroke={accent2} strokeWidth={2.5} strokeDasharray="6 8"
          opacity={0.3 + 0.6 * pB} />
        <text x={kx} y={ky - 16} fill="#c9d6ea" fontSize="22" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)">k-space (spatial frequencies)</text>
        {/* mapping arrows */}
        <line x1={kcx} y1={kcy} x2={px - 24} y2={py1 + P / 2} stroke={accent} strokeWidth={2} opacity={pA * 0.8} markerEnd="url(#kaA)" />
        <line x1={kx + K * 0.94} y1={kcy} x2={px - 24} y2={py2 + P / 2} stroke={accent2} strokeWidth={2} opacity={pB * 0.8} markerEnd="url(#kaB)" />
        <defs>
          <marker id="kaA" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto"><path d="M0,0 L7,5 L0,10 Z" fill={accent} /></marker>
          <marker id="kaB" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto"><path d="M0,0 L7,5 L0,10 Z" fill={accent2} /></marker>
        </defs>
      </svg>
      {/* the two partial reconstructions */}
      {panel(px, py1, P, srcLow, `${accent}88`, 0.25 + 0.75 * pA)}
      {panel(px, py2, P, srcHigh, `${accent2}88`, 0.25 + 0.75 * pB)}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        <text x={px + P + 24} y={py1 + 34} fill={accent} fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} opacity={pA}>center = contrast</text>
        <text x={px + P + 24} y={py1 + 66} fill="#9fb4cc" fontSize="19" fontFamily="var(--f-body, Inter, sans-serif)" opacity={pA}>low spatial frequency</text>
        <text x={px + P + 24} y={py2 + 34} fill={accent2} fontSize="26" fontFamily="var(--f-body, Inter, sans-serif)" fontWeight={800} opacity={pB}>edges = detail</text>
        <text x={px + P + 24} y={py2 + 66} fill="#9fb4cc" fontSize="19" fontFamily="var(--f-body, Inter, sans-serif)" opacity={pB}>high spatial frequency</text>
        <text x={kx} y={ky + K + 40} fill="#8aa" fontSize="19" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t, 0.06, 0.3))}>one point = a wave across the whole image</text>
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: 8, color: '#5f6b7d', font: "400 14px/1.3 var(--f-body, Inter, sans-serif)"}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default KSpaceAnatomy;
