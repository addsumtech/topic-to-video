// KSpaceToImage — the inverse Fourier transform, MADE MEANINGFUL. A vertical sweep (the 2D inverse FFT
// "computing" across the frame) turns the raw k-space FREQUENCY pattern (a symmetric lattice of dots, bright at
// the low-frequency centre) on its right into the reconstructed IMAGE (a coherent brain cross-section) on its
// left. The contrast — incoherent frequencies vs a coherent picture — IS the idea (k-space is not the image;
// the transform makes it one). Purpose-built because no library shot encodes this. Deterministic (pure fn of
// useT); theme-driven palette.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic} from '../runtime/motion';

export const DURATION = 180; // 6s

export const KSpaceToImage: React.FC<{accent?: string; accent2?: string; label?: string; src?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'inverse Fourier transform', src,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const cx = W / 2, cy = H / 2;
  // the FFT sweep: k-space on the right, image resolving on the left. Holds a beat of pure k-space, then sweeps.
  const sweep = easeInOutCubic(seg(t, 0.1, 0.86));
  const sweepX = sweep * W;

  // --- k-space: a symmetric lattice of frequency dots, brightest at the centre (low freq = bulk energy) ---
  const cols = 30, rows = 18, dots: React.ReactNode[] = [];
  const maxR = Math.hypot(cx, cy);
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const x = (c + 0.5) * (W / cols), y = (r + 0.5) * (H / rows);
    const d = Math.hypot(x - cx, y - cy) / maxR;
    const amp = Math.exp(-d * d * 6);                       // energy concentrated at the centre
    const tw = 0.75 + 0.25 * Math.sin((c * 1.3 + r * 0.7) + t * 8);   // faint twinkle
    dots.push(<circle key={`${r}-${c}`} cx={x.toFixed(1)} cy={y.toFixed(1)} r={(1.3 + amp * 4).toFixed(2)}
      fill={(c + r) % 5 === 0 ? accent2 : accent} opacity={(0.10 + amp * 0.8) * tw} />);
  }

  // --- the reconstructed image: a stylised brain cross-section (skull ellipse + brain outline + fissure) ---
  const rx = Math.min(W, H) * 0.19, ry = rx * 1.22;
  const img = clamp01((sweep - 0.02) / 0.4);               // fades in just behind the sweep front
  const brain = `M ${cx} ${cy - ry * 0.86}
    C ${cx + rx * 0.95} ${cy - ry * 0.86}, ${cx + rx * 0.92} ${cy + ry * 0.55}, ${cx + rx * 0.5} ${cy + ry * 0.82}
    C ${cx + rx * 0.2} ${cy + ry * 0.98}, ${cx - rx * 0.2} ${cy + ry * 0.98}, ${cx - rx * 0.5} ${cy + ry * 0.82}
    C ${cx - rx * 0.92} ${cy + ry * 0.55}, ${cx - rx * 0.95} ${cy - ry * 0.86}, ${cx} ${cy - ry * 0.86} Z`;

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)'}}>
      {/* k-space frequencies (shown to the RIGHT of the sweep front) */}
      <AbsoluteFill style={{clipPath: `inset(0 0 0 ${sweepX.toFixed(1)}px)`}}>
        <svg width={W} height={H} style={{position: 'absolute'}}>{dots}</svg>
      </AbsoluteFill>

      {/* the reconstructed IMAGE (shown to the LEFT of the sweep front) — a REAL scan if `src` is given, else a
          drawn brain outline. The real image makes the reveal substantive: the sweep resolves the actual scan. */}
      <AbsoluteFill style={{clipPath: `inset(0 ${(W - sweepX).toFixed(1)}px 0 0)`, opacity: img}}>
        {src ? (
          <div style={{position: 'absolute', left: cx - ry, top: cy - ry, width: ry * 2, height: ry * 2,
            borderRadius: 8, overflow: 'hidden', boxShadow: `0 0 0 1.5px ${accent}88`}}>
            <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
          </div>
        ) : null}
        <svg width={W} height={H} style={{position: 'absolute', opacity: src ? 0 : 1}}>
          <defs>
            <radialGradient id="ksi-core" cx="50%" cy="46%" r="60%">
              <stop offset="0%" stopColor={accent} stopOpacity="0.5" />
              <stop offset="55%" stopColor={accent2} stopOpacity="0.16" />
              <stop offset="100%" stopColor="#05060a" stopOpacity="0" />
            </radialGradient>
          </defs>
          <ellipse cx={cx} cy={cy} rx={rx * 1.16} ry={ry * 1.08} fill="url(#ksi-core)" />
          <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="#0a1424" stroke={accent} strokeWidth={2.5} opacity={0.9} />
          <path d={brain} fill="#0e1b30" stroke={accent2} strokeWidth={2} opacity={0.85} />
          <line x1={cx} y1={cy - ry * 0.72} x2={cx} y2={cy + ry * 0.62} stroke={accent} strokeWidth={1.4} opacity={0.55} />
          <path d={`M ${cx - rx * 0.55} ${cy - ry * 0.2} C ${cx - rx * 0.2} ${cy - ry * 0.05}, ${cx - rx * 0.2} ${cy + ry * 0.25}, ${cx - rx * 0.5} ${cy + ry * 0.4}`}
            fill="none" stroke={accent} strokeWidth={1.2} opacity={0.4} />
          <path d={`M ${cx + rx * 0.55} ${cy - ry * 0.2} C ${cx + rx * 0.2} ${cy - ry * 0.05}, ${cx + rx * 0.2} ${cy + ry * 0.25}, ${cx + rx * 0.5} ${cy + ry * 0.4}`}
            fill="none" stroke={accent} strokeWidth={1.2} opacity={0.4} />
        </svg>
      </AbsoluteFill>

      {/* the sweep front — the FFT computing across the frame */}
      <div style={{position: 'absolute', left: sweepX - 1.5, top: 0, width: 3, height: H,
        background: '#eaf6ff', boxShadow: `0 0 26px 5px ${accent}`, opacity: sweep > 0.01 && sweep < 0.995 ? 0.9 : 0}} />

      {/* label (kept above the reserved caption band) */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 96, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        opacity: lerp(0.35, 1, clamp01(t * 4))}}>{label}
        <div style={{marginTop: 8, font: "500 22px/1 'JetBrains Mono', monospace", color: accent, letterSpacing: '0.14em'}}>
          k-space&nbsp;&nbsp;→&nbsp;&nbsp;image</div>
      </div>
    </AbsoluteFill>
  );
};
export default KSpaceToImage;
