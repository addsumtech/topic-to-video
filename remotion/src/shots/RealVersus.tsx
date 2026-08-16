// RealVersus — a comparison carried by REAL images, not drawn panels. Two real scans side by side (e.g. a T1 vs
// a T2 slice — the actual contrast difference; or the same scan labelled 9:56 vs 5:33 — same result, half the
// time). The design technique (split + divider + wipe-in) frames REAL substance. Images are props → generalises
// to any two-image comparison. Deterministic; credit line for CC-BY.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';

export const DURATION = 165; // 5.5s

export const RealVersus: React.FC<{srcLeft?: string; srcRight?: string; labelLeft?: string; labelRight?: string;
  title?: string; credit?: string; accent?: string}> = ({
  srcLeft, srcRight, labelLeft = '', labelRight = '', title = '', credit = '', accent = '#22d3ee',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const t = useT();
  const S = Math.min(H * 0.5, W * 0.32);                    // each panel square
  const gap = 90, cx = W / 2;
  const lx = cx - gap / 2 - S, rx = cx + gap / 2, py = (H - S) / 2 - 8;
  const inL = easeOutCubic(clamp01(seg(t, 0.1, 0.5)));      // panels wipe in from their sides
  const inR = easeOutCubic(clamp01(seg(t, 0.22, 0.62)));

  const panel = (src: string | undefined, x: number, label: string, prog: number, from: number) => (
    <>
      <div style={{position: 'absolute', left: x, top: py, width: S, height: S, borderRadius: 8, overflow: 'hidden',
        boxShadow: `0 0 0 1.5px ${accent}88, 0 20px 60px #000a`, opacity: prog, transform: `translateX(${(1 - prog) * from}px)`}}>
        {src ? <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
      </div>
      <div style={{position: 'absolute', left: x, top: py + S + 16, width: S, textAlign: 'center', opacity: prog,
        color: '#dfe8f5', font: '700 30px/1.15 Inter, system-ui, sans-serif'}}>{label}</div>
    </>
  );

  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 46%, #0b1120, #05060a)'}}>
      {title ? <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#c9d6ea', font: "600 26px/1.1 'JetBrains Mono', monospace", letterSpacing: '0.18em',
        textTransform: 'uppercase', opacity: lerp(0.4, 1, clamp01(t * 4))}}>{title}</div> : null}
      {panel(srcLeft, lx, labelLeft, inL, -40)}
      {panel(srcRight, rx, labelRight, inR, 40)}
      <div style={{position: 'absolute', left: cx - 26, top: H / 2 - 34, width: 52, height: 52, borderRadius: 26,
        background: '#0b1120', border: `2px solid ${accent}`, color: '#eaf6ff', display: 'flex',
        alignItems: 'center', justifyContent: 'center', font: '800 22px Inter, sans-serif',
        opacity: clamp01(seg(t, 0.5, 0.62))}}>vs</div>
      {credit ? <div style={{position: 'absolute', left: 20, bottom: 8, color: '#5f6b7d',
        font: "400 14px/1.3 Inter, system-ui, sans-serif"}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default RealVersus;
