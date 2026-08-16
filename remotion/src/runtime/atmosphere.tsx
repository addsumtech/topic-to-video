// ATMOSPHERE — the per-topic background WORLD that every shot sits inside, so a film reads as ONE adaptive
// system instead of serially-stacked templates. Per the video-craft research: adapt the ATMOSPHERE (background/
// texture) per topic behind a CONSTANT foreground chrome; carry ONE recurring motif; keep it low-contrast so it
// never fights the foreground. It's a design LANGUAGE expressed as tokens {motif, accent, accent2, bg} + a range
// of motif archetypes — re-skinning per topic = changing these tokens, not rewriting scenes. Deterministic
// (pure fn of frame; no Date.now/Math.random) so it's frame-seekable like every shot.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {hash01, clamp01} from './motion';

export type Motif = 'grid' | 'field' | 'particles' | 'waves' | 'plain';
export type Atmo = {motif?: Motif; accent?: string; accent2?: string; bg?: string; intensity?: number};

const TWO_PI = Math.PI * 2;
const withA = (hex: string, a: number) => {
  // append alpha to a #rrggbb — low-contrast is the whole point (research: muted range, never fights fg)
  const h = hex.replace('#', '');
  if (h.length !== 6) return hex;
  const A = Math.round(clamp01(a) * 255).toString(16).padStart(2, '0');
  return `#${h}${A}`;
};

// A faint frequency/k-space LATTICE: a grid of low-opacity dots brightest at center (like k-space energy),
// drifting almost imperceptibly. The default MRI motif.
const Grid: React.FC<{W: number; H: number; frame: number; a1: string; a2: string; k: number}> = ({W, H, frame, a1, a2, k}) => {
  const cols = 26, rows = 15, dots: React.ReactNode[] = [];
  const cx = W / 2, cy = H / 2, maxR = Math.hypot(cx, cy);
  const drift = Math.sin((frame / 900) * TWO_PI) * 6;
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const x = (c + 0.5) * (W / cols) + drift * Math.sin(r), y = (r + 0.5) * (H / rows) + drift * Math.cos(c);
    const d = Math.hypot(x - cx, y - cy) / maxR;                 // 0 center → 1 edge
    const op = (0.11 + 0.20 * (1 - d)) * k;                       // center brighter (k-space energy)
    const sz = 1.5 + 2.4 * (1 - d);
    dots.push(<circle key={`${r}-${c}`} cx={x} cy={y} r={sz} fill={c % 7 === r % 7 ? a2 : a1} opacity={op} />);
  }
  return <svg width={W} height={H} style={{position: 'absolute'}}>{dots}</svg>;
};

// Flowing FIELD lines (precession / flow) — a few long faint sine curves sweeping slowly.
const Field: React.FC<{W: number; H: number; frame: number; a1: string; a2: string; k: number}> = ({W, H, frame, a1, a2, k}) => {
  const lines = 7, paths: React.ReactNode[] = [];
  for (let i = 0; i < lines; i++) {
    const ph = hash01(i * 3 + 1) * TWO_PI, amp = 60 + hash01(i * 5) * 90, y0 = (i + 0.5) * (H / lines);
    const pts: string[] = [];
    for (let x = -40; x <= W + 40; x += 40) {
      const y = y0 + Math.sin(x / 260 + ph + (frame / 260)) * amp + Math.sin(x / 90) * 8;
      pts.push(`${x},${y.toFixed(1)}`);
    }
    paths.push(<polyline key={i} points={pts.join(' ')} fill="none" stroke={i % 2 ? a2 : a1}
      strokeWidth={1.4} opacity={(0.12 + 0.06 * hash01(i)) * k} />);
  }
  return <svg width={W} height={H} style={{position: 'absolute'}}>{paths}</svg>;
};

// Drifting PARTICLES (spins / points) — deterministic scatter, slow float.
const Particles: React.FC<{W: number; H: number; frame: number; a1: string; a2: string; k: number}> = ({W, H, frame, a1, a2, k}) => {
  const n = 46, dots: React.ReactNode[] = [];
  for (let i = 0; i < n; i++) {
    const bx = hash01(i * 2 + 3) * W, by = hash01(i * 2 + 7) * H;
    const x = bx + Math.sin(frame / (200 + hash01(i) * 200) + i) * 26;
    const y = by + Math.cos(frame / (240 + hash01(i * 3) * 200) + i) * 22;
    const sz = 1.5 + hash01(i * 9) * 3.5;
    dots.push(<circle key={i} cx={x} cy={y} r={sz} fill={i % 3 ? a1 : a2} opacity={(0.10 + 0.16 * hash01(i * 11)) * k} />);
  }
  return <svg width={W} height={H} style={{position: 'absolute'}}>{dots}</svg>;
};

// Stacked sine WAVES (signal) — a few faint horizontal wave bands.
const Waves: React.FC<{W: number; H: number; frame: number; a1: string; a2: string; k: number}> = ({W, H, frame, a1, a2, k}) => {
  const bands = 5, paths: React.ReactNode[] = [];
  for (let i = 0; i < bands; i++) {
    const y0 = (i + 0.5) * (H / bands), ph = hash01(i * 7) * TWO_PI;
    const pts: string[] = [];
    for (let x = 0; x <= W; x += 24) pts.push(`${x},${(y0 + Math.sin(x / 70 + ph + frame / 160) * (10 + i * 3)).toFixed(1)}`);
    paths.push(<polyline key={i} points={pts.join(' ')} fill="none" stroke={i % 2 ? a1 : a2} strokeWidth={1.2} opacity={0.13 * k} />);
  }
  return <svg width={W} height={H} style={{position: 'absolute'}}>{paths}</svg>;
};

// The full atmosphere: bg fill + a soft central glow + the chosen motif + a vignette. All low-contrast.
export const Atmosphere: React.FC<Atmo> = ({motif = 'grid', accent = '#22d3ee', accent2 = '#a78bfa', bg = '#05060a', intensity = 1}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const k = clamp01(intensity);
  const glow = interpolate(Math.sin((frame / 480) * TWO_PI), [-1, 1], [0.10, 0.18]) * k;
  const M = motif === 'field' ? Field : motif === 'particles' ? Particles : motif === 'waves' ? Waves : motif === 'plain' ? null : Grid;
  return (
    <AbsoluteFill style={{backgroundColor: bg}}>
      <AbsoluteFill style={{background:
        `radial-gradient(60% 55% at 50% 46%, ${withA(accent, glow)} 0%, ${withA(accent2, glow * 0.5)} 40%, #0000 72%)`}} />
      {M ? <M W={W} H={H} frame={frame} a1={accent} a2={accent2} k={k} /> : null}
      <AbsoluteFill style={{background: `radial-gradient(72% 72% at 50% 50%, #0000 55%, ${withA(bg, 0.85)} 100%)`}} />
    </AbsoluteFill>
  );
};
