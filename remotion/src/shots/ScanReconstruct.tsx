// ScanReconstruct — a REAL image, revealed by a design TECHNIQUE. It takes a topic-fetched image (e.g. a real
// MRI slice) and reconstructs it from the CENTRE OUTWARD through a grid of tiles — center-first because that is
// where k-space concentrates its energy, so the reveal itself teaches "the image is computed, low frequencies
// first." The design language's vibe (assemble-from-a-grid) carries REAL substance, not colored blocks. The
// image is a prop, so this generalises to any topic with a real image. Deterministic; credit line for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {requireEvidence} from '../runtime/evidence';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {fitContentSquare} from '../runtime/layout';

export const DURATION = 180; // 6s

export const ScanReconstruct: React.FC<{src?: string; label?: string; credit?: string; accent?: string; cols?: number}> = ({
  src, label = '', credit = '', accent = '#22d3ee', cols = 22,
} = {}) => {
  requireEvidence('ScanReconstruct', 'src', src, 'the real image being reconstructed');
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const {S, left, top} = fitContentSquare(W, H, {hFrac: 0.85, wFrac: 0.44});  // centered in the content zone (clear of title + caption)
  const reveal = clamp01(seg(t, 0.06, 0.9));
  const revealR = reveal * 1.5;                             // grows past 1 so the corners finish

  const rows = Math.round(cols * (S / S));                  // square grid
  const tiles: React.ReactNode[] = [];
  const cell = S / cols;
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const dx = (c + 0.5) / cols - 0.5, dy = (r + 0.5) / rows - 0.5;
    const dist = Math.hypot(dx, dy) / 0.707;               // 0 centre → 1 corner
    const op = clamp01((dist - revealR) * 7 + 0.5);        // opaque until the reveal front passes
    if (op < 0.02) continue;
    tiles.push(<rect key={`${r}-${c}`} x={(c * cell).toFixed(1)} y={(r * cell).toFixed(1)}
      width={cell + 1} height={cell + 1} fill="#070b12" opacity={op} />);
  }
  // the reveal FRONT — a faint expanding ring
  const ringR = revealR * (S * 0.707);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      <div style={{position: 'absolute', left, top, width: S, height: S, borderRadius: 6,
        overflow: 'hidden', boxShadow: `0 0 0 1px ${accent}66, 0 24px 80px #000a`}}>
        {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
        <svg width={S} height={S} style={{position: 'absolute', left: 0, top: 0}}>
          {tiles}
          {reveal > 0.02 && reveal < 0.98 &&
            <circle cx={S / 2} cy={S / 2} r={ringR} fill="none" stroke={accent} strokeWidth={2} opacity={0.5} />}
        </svg>
      </div>
      {label ? <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div> : null}
      {credit ? <div style={{position: 'absolute', left: 20, bottom: 8, color: '#5f6b7d',
        font: "400 14px/1.3 var(--f-body, Inter, system-ui, sans-serif)", maxWidth: 520}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default ScanReconstruct;
