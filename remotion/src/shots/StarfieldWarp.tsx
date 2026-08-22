// SHOT · Starfield Warp — stars accelerate outward from a vanishing point into a hyperspace streak, the field
// building speed then DECELERATING as a wordmark blooms from the core light. A cosmic / "into the future"
// register (family V · cosmic/space). Deterministic (each star's radius = eased fn of t + seed; streak = the
// motion trail).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const BG_D0 = '#03040c';
const N = 240;

export const StarfieldWarp: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'Lightspeed', tagline: TAG = 'the next era, now', accent: ACC = '#8fb6ff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2;
  const speed = easeInOutCubic(clamp01(seg(t, 0.05, 0.62)));       // accelerate then hold
  const decel = clamp01(seg(t, 0.66, 0.9));                        // slow into the reveal
  const warp = speed * (1 - 0.7 * decel);
  const flash = Math.sin(clamp01(seg(t, 0.6, 0.78)) * Math.PI);    // white core bloom at peak
  const titleIn = easeOutCubic(seg(t, 0.72, 0.92));
  const maxR = Math.hypot(cx, cy) * 1.1;
  return (
    <AbsoluteFill style={{background: `radial-gradient(60% 60% at 50% 50%, #0a1030, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {[...Array(N)].map((_, i) => {
          const ang = hash01(i * 2.3) * Math.PI * 2;
          const seed = 0.02 + hash01(i * 5.1) * 0.98;
          const rr = ((seed + warp * 1.4) % 1);                    // looping radius so stars keep streaming
          const r = rr * maxR;
          const trail = (40 + warp * 260) * (0.3 + rr);            // longer streaks at higher speed / outer
          const x2 = cx + Math.cos(ang) * r, y2 = cy + Math.sin(ang) * r;
          const x1 = cx + Math.cos(ang) * Math.max(0, r - trail), y1 = cy + Math.sin(ang) * Math.max(0, r - trail);
          const op = clamp01(rr * 2) * (0.4 + 0.6 * warp);
          const col = rr > 0.7 ? '#ffffff' : ACC;
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={col} strokeWidth={lerp(1, 3, rr)}
            strokeLinecap="round" opacity={op} />;
        })}
      </svg>
      {/* core bloom */}
      <div style={{position: 'absolute', left: cx, top: cy, width: 900, height: 900, transform: 'translate(-50%,-50%)',
        background: `radial-gradient(circle, #ffffff ${flash * 8}%, ${ACC}55 ${20 + flash * 20}%, #0000 60%)`,
        opacity: 0.4 + 0.6 * flash, pointerEvents: 'none'}} />
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `scale(${lerp(1.3, 1, titleIn)})`, color: '#fff',
          font: '800 128px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em',
          textShadow: `0 0 60px ${ACC}, 0 0 120px ${ACC}88`}}>{TITLE}</div>
        <div style={{opacity: clamp01(seg(t, 0.82, 0.96)), marginTop: 20, color: '#c7d6ff',
          font: '600 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.2em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default StarfieldWarp;
