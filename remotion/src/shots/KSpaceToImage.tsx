// KSpaceToImage — the inverse Fourier transform, MADE MEANINGFUL. A vertical sweep (the 2D inverse FFT
// "computing" across the frame) turns the raw k-space FREQUENCY pattern (a symmetric lattice of dots, bright at
// the low-frequency centre) on its right into the reconstructed IMAGE on its left — the film's own scan, passed
// as `src`. The contrast — incoherent frequencies vs a coherent picture — IS the idea (k-space is not the image;
// the transform makes it one). Purpose-built because no library shot encodes this. Deterministic (pure fn of
// useT); theme-driven palette.
//
// WITHOUT `src` THERE IS NO ANATOMY. The fallback used to be a drawn BRAIN — skull ellipse, cortex outline,
// midline fissure — so every film that reached for the register without an image reconstructed a head: a
// knee film's k-space resolved into a brain, and a film about a sound spectrum did too. What the transform
// produces is a claim about the subject, and only the film knows its subject. With no `src` the image side is
// now an empty image frame holding a soft, structure-free glow at its centre: the smooth blob that a lattice
// whose energy sits entirely at the centre transforms into, which says "the transform makes a coherent image"
// and nothing about what the image is of. It is the same in the standalone demo — there is no way to tell a
// demo render from a film that simply forgot `src`, so neither gets a picture the film did not choose.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 180; // 6s

export const KSpaceToImage: React.FC<{accent?: string; accent2?: string; label?: string; src?: string}> = ({
  accent: ACC, accent2: ACC2, label = 'inverse Fourier transform', src,
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  // THE INK IS THE FILM'S. The title, its line and the sweep front were literals picked for a near-black
  // ground, and all eight DNA presets are near-black, so on a film whose DNA came from a warm-white deck
  // this register's type drew white on white — measured median 1.12:1 over 100% of the marks
  // (`scripts/ink_contrast_qa.py`). The FREQUENCIES are not light either: their amplitude is drawn as
  // OPACITY (`0.10 + amp * 0.8`), so the lattice reads the same way in the film's own accents on paper as
  // it does on night — dense at the centre, thinning to nothing at the edges. What does keep its own dark
  // is the reconstructed image's frame, which already paints `#0a1424` under whatever the film's scan is:
  // a scan viewport is black in every reader that has ever shown one. Each token keeps its OWN original
  // literal as its fallback, so an un-themed render is unchanged.
  const accent = ACC ?? dna?.accent ?? '#22d3ee';
  const accent2 = ACC2 ?? dna?.accent2 ?? '#a78bfa';
  const front = dna?.fg ?? '#eaf6ff';        // the sweep front — the transform computing across the frame
  const ink = dna?.fg ?? '#dfe8f5';          // the title
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

  // --- the reconstructed image's frame: a square the film's scan fills (or, with no scan, a structure-free glow) ---
  const rx = Math.min(W, H) * 0.19, ry = rx * 1.22;
  const img = clamp01((sweep - 0.02) / 0.4);               // fades in just behind the sweep front

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)')}}>
      {/* k-space frequencies (shown to the RIGHT of the sweep front) */}
      <AbsoluteFill style={{clipPath: `inset(0 0 0 ${sweepX.toFixed(1)}px)`}}>
        <svg width={W} height={H} style={{position: 'absolute'}}>{dots}</svg>
      </AbsoluteFill>

      {/* the reconstructed IMAGE (shown to the LEFT of the sweep front) — the film's REAL scan when `src` is given:
          the sweep resolves the actual image. Without one, the same frame holds a soft centred glow and nothing
          that could be read as a body part (see the header). */}
      <AbsoluteFill style={{clipPath: `inset(0 ${(W - sweepX).toFixed(1)}px 0 0)`, opacity: img}}>
        <div style={{position: 'absolute', left: cx - ry, top: cy - ry, width: ry * 2, height: ry * 2,
          borderRadius: 8, overflow: 'hidden', boxShadow: `0 0 0 1.5px ${accent}88`,
          background: src ? undefined : `radial-gradient(closest-side, ${accent}6b 0%, ${accent}2b 40%, ${accent}0a 75%, #0a142400 100%), #0a1424`}}>
          {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
        </div>
      </AbsoluteFill>

      {/* the sweep front — the FFT computing across the frame */}
      <div style={{position: 'absolute', left: sweepX - 1.5, top: 0, width: 3, height: H,
        background: front, boxShadow: `0 0 26px 5px ${accent}`, opacity: sweep > 0.01 && sweep < 0.995 ? 0.9 : 0}} />

      {/* label (kept above the reserved caption band) */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 96, textAlign: 'center',
        color: ink, font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.35, 1, clamp01(t * 4))}}>{label}
        <div style={{marginTop: 8, font: "500 22px/1 var(--f-mono, 'JetBrains Mono', monospace)", color: accent, letterSpacing: '0.14em'}}>
          k-space&nbsp;&nbsp;→&nbsp;&nbsp;image</div>
      </div>
    </AbsoluteFill>
  );
};
export default KSpaceToImage;
