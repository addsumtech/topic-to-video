// SHOT · Terrain Fly — a 3D wireframe heightmap terrain scrolls toward the viewer in perspective (hills drift
// in from the horizon), grid lines coloured by elevation, fog into a glowing horizon, a wordmark above. A
// camera/landscape register (family B · camera/space). Deterministic (heights = summed sines of x, z+t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic} from '../runtime/motion';

export const DURATION = 160; // ~5.3s
const BG = '#070312', ACC = '#00e0c8', ACC2 = '#ff4fa3';
const GX = 40, GZ = 24;

export const TerrainFly: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Cross it', tagline: TAG = 'new ground, ahead'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, horizon = H * 0.42, focal = 460, camH = 2.2;
  const scroll = t * 4;
  const heightAt = (gi: number, gjWorld: number) =>
    (Math.sin(gi * 0.5 + gjWorld * 0.4) + Math.sin(gi * 0.23 - gjWorld * 0.31) * 1.4 + Math.sin(gjWorld * 0.7) * 0.6);
  // project a grid point (gi 0..GX across, gj 0..GZ depth) to screen
  const proj = (gi: number, gj: number) => {
    const depth = gj + 1 - (scroll % 1);                          // near rows recycle toward the viewer
    const gjWorld = gj + Math.floor(scroll);
    const hx = (gi - GX / 2) * 0.5;
    const hy = heightAt(gi, gjWorld) * 0.55;
    return {x: cx + (hx / depth) * focal, y: horizon + ((camH - hy) / depth) * focal, depth, h: hy};
  };
  const titleIn = easeOutCubic(seg(t, 0.16, 0.44));
  const lines: React.ReactNode[] = [];
  for (let gj = 0; gj < GZ; gj++) {
    const fog = clamp01(1 - gj / GZ);                              // fade far rows
    for (let gi = 0; gi < GX; gi++) {
      const p = proj(gi, gj);
      const col = p.h > 0.4 ? ACC : p.h < -0.4 ? ACC2 : '#4a6cff';
      if (gi < GX - 1) { const q = proj(gi + 1, gj); lines.push(<line key={`h${gi}-${gj}`} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={col} strokeWidth={1.5} opacity={0.15 + 0.6 * fog} />); }
      if (gj < GZ - 1) { const q = proj(gi, gj + 1); lines.push(<line key={`v${gi}-${gj}`} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={col} strokeWidth={1.5} opacity={0.15 + 0.6 * fog} />); }
    }
  }
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, #16043a 0%, #3a0a4e ${horizon / H * 100}%, ${BG} 78%)`, overflow: 'hidden'}}>
      {/* horizon sun glow */}
      <div style={{position: 'absolute', left: cx, top: horizon, width: 700, height: 360, transform: 'translate(-50%,-70%)',
        background: `radial-gradient(circle, ${ACC}66, ${ACC2}33 40%, #0000 70%)`, filter: 'blur(6px)'}} />
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>{lines}</svg>
      <div style={{position: 'absolute', top: 96, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#eafcff',
        font: '800 120px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em',
        textShadow: `0 0 44px ${ACC}88, 0 10px 40px #000`}}>{TITLE}</div>
      <div style={{position: 'absolute', top: 244, left: 0, right: 0, textAlign: 'center',
        opacity: easeOutCubic(seg(t, 0.3, 0.56)), color: '#c7b6ff',
        font: '600 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.2em'}}>{TAG}</div>
    </AbsoluteFill>
  );
};
export default TerrainFly;
