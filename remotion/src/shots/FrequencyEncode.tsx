// FrequencyEncode — the actual mechanism, not a generic spectrum. A readout gradient makes each COLUMN of the
// slice precess at its OWN frequency (a LINEAR ramp along the axis: left slow → right fast) = position→frequency.
// The coil reads ONE summed signal; a single Fourier transform then SEPARATES that signal back into the columns
// by frequency. Three stages: columns get their pitches → they sum into one readout → an FFT prism splits it back
// to the columns. A radial spectrum burst showed none of this. Deterministic (pure fn of useT).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 180; // 6s

export const FrequencyEncode: React.FC<{accent?: string; accent2?: string; label?: string; cols?: number}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Position becomes frequency', cols = 7,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const gx = W * 0.14, gw = W * 0.72, colW = gw / cols;
  const rowY = H * 0.3, rowH = H * 0.2;
  const sumY = H * 0.62, specY = H * 0.82;

  const p1 = clamp01(seg(t, 0.06, 0.34));   // columns get their pitches
  const p2 = clamp01(seg(t, 0.36, 0.56));   // they sum into one readout signal
  const p3 = clamp01(seg(t, 0.58, 0.9));    // FFT separates them back into columns

  const freqOf = (i: number) => 1.2 + i * 1.1;              // linear frequency ramp across the columns

  // per-column mini-waves (position → its own frequency)
  const colWaves: React.ReactNode[] = [];
  for (let i = 0; i < cols; i++) {
    const cx0 = gx + i * colW, f = freqOf(i);
    const pts: string[] = [];
    for (let x = 6; x <= colW - 6; x += 2) {
      const u = (x - 6) / (colW - 12);
      pts.push(`${(cx0 + x).toFixed(1)},${(rowY + rowH / 2 - Math.sin(u * f * Math.PI * 2 + t * 6) * rowH * 0.34 * p1).toFixed(1)}`);
    }
    colWaves.push(<g key={i}>
      <rect x={cx0 + 2} y={rowY} width={colW - 4} height={rowH} rx={5} fill="#0a1424" stroke={`${accent}55`} strokeWidth={1} opacity={0.5 + p1 * 0.5} />
      <polyline points={pts.join(' ')} fill="none" stroke={i % 2 ? accent2 : accent} strokeWidth={2} />
    </g>);
  }

  // the summed readout signal (one complex waveform = sum of the column frequencies)
  const sum: string[] = [];
  for (let x = 0; x <= gw; x += 2) {
    let y = 0;
    for (let i = 0; i < cols; i++) y += Math.sin((x / gw) * freqOf(i) * Math.PI * 2 + t * 6);
    sum.push(`${(gx + x).toFixed(1)},${(sumY - (y / cols) * H * 0.10 * p2).toFixed(1)}`);
  }

  // FFT spectrum: a peak per column, positioned by its frequency (→ recovers its column/position)
  const peaks: React.ReactNode[] = [];
  for (let i = 0; i < cols; i++) {
    const px = gx + (i + 0.5) * colW;
    const hgt = lerp(0, H * 0.12, p3) * (0.6 + 0.4 * Math.sin(i));
    peaks.push(<g key={i}>
      <line x1={px} y1={specY} x2={px} y2={specY - H * 0.11} stroke={`${accent}33`} strokeWidth={1} />
      <line x1={px} y1={specY} x2={px} y2={specY - hgt} stroke={i % 2 ? accent2 : accent} strokeWidth={5} />
      {p3 > 0.5 && <line x1={px} y1={rowY + rowH} x2={px} y2={specY - hgt} stroke={`${accent}22`} strokeWidth={1} strokeDasharray="2 5" />}
    </g>);
  }

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        {/* gradient ramp arrow above the row: position → frequency */}
        <line x1={gx} y1={rowY - 26} x2={gx + gw} y2={rowY - 26} stroke={accent} strokeWidth={2} opacity={0.5 * p1} markerEnd="url(#fah)" />
        <defs><marker id="fah" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill={accent} /></marker></defs>
        <text x={gx} y={rowY - 34} fill="#8aa" fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={p1}>low freq</text>
        <text x={gx + gw} y={rowY - 34} textAnchor="end" fill="#8aa" fontSize="18" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={p1}>high freq · readout gradient</text>
        {colWaves}
        {/* summed readout */}
        <polyline points={sum.join(' ')} fill="none" stroke="#eaf6ff" strokeWidth={2.4} opacity={p2} />
        <text x={gx} y={sumY - H * 0.11} fill="#c9d6ea" fontSize="18" fontFamily="var(--f-body, Inter, sans-serif)" opacity={p2}>one measured signal</text>
        {/* FFT separates it back into columns */}
        <text x={gx} y={specY - H * 0.13} fill={accent} fontSize="20" fontFamily="var(--f-mono, 'JetBrains Mono', monospace)" opacity={clamp01(seg(t,0.56,0.66))}>one Fourier transform → columns</text>
        {peaks}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default FrequencyEncode;
