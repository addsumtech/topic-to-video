// SHOT · Data Monolith — a nighttime skyline of glowing data TOWERS rises from a perspective grid floor, each
// with a bright cap + a mirrored reflection, the tallest pulsing as the hero. Data as architecture — bold,
// cinematic scale (family E · 3D / spatial). Heights are QUALITATIVE (no on-screen stats) unless a film
// supplies labels. Deterministic (tower growth = fn of t + fixed per-index height).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s
const BG_D0 = '#06070e', ACC_D0 = '#4db8ff', ACC2_D0 = '#a06bff';

export const DataMonolith: React.FC<{items?: string[]; title?: string; hero?: number}> = ({
  items: ITEMS = ['Docs', 'Chat', 'Tasks', 'Data', 'Code', 'Calls', 'Team'],
  title: TITLE = 'Everything, to scale', hero: HERO = 3} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0, ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const towers = ITEMS.slice(0, 9);
  const n = towers.length;
  const heroIdx = Math.min(HERO, n - 1);
  const floorY = H * 0.72;
  const bandW = Math.min(150, (W - 320) / n), gap = 30;
  const rowW = n * bandW + (n - 1) * gap;
  const x0 = (W - rowW) / 2;
  const titleIn = easeOutCubic(seg(t, 0.04, 0.2));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 90% at 50% 30%, #10162e, ${BG} 72%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 74, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#aeb6ca', font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em',
        textTransform: 'uppercase', zIndex: 3}}>{TITLE}</div>

      {/* perspective floor grid */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g opacity={0.28}>
          {[...Array(13)].map((_, i) => {
            const fx = (i / 12) * W;
            return <line key={'v' + i} x1={lerp(W / 2, fx, 0.2)} y1={floorY} x2={fx} y2={H} stroke="#2b3a6e" strokeWidth={1} />;
          })}
          {[...Array(6)].map((_, i) => {
            const yy = lerp(floorY, H, (i / 5) ** 1.7);
            return <line key={'h' + i} x1={0} y1={yy} x2={W} y2={yy} stroke="#2b3a6e" strokeWidth={1} />;
          })}
        </g>
      </svg>

      {towers.map((label, i) => {
        const hFrac = 0.4 + hash01(i * 4.7) * 0.6;                          // fixed per-index height
        const isHero = i === heroIdx;
        const maxH = floorY - 150;
        const grow = easeOutExpo(clamp01(seg(t, 0.14 + i * 0.06, 0.5 + i * 0.06)));
        const th = maxH * (isHero ? Math.max(0.9, hFrac) : hFrac) * grow;
        const x = x0 + i * (bandW + gap);
        const tone = isHero ? ACC : i % 2 ? ACC2 : (dna?.dim ?? '#3a6ad0');   // non-hero even bars → DNA dim (was a fixed blue that clashed on a themed film)
        const pulse = isHero && t > 0.6 ? 1 + 0.04 * Math.max(0, Math.sin((t - 0.6) * 9)) : 1;
        return (
          <div key={i}>
            {/* tower */}
            <div style={{position: 'absolute', left: x, top: floorY - th, width: bandW, height: th,
              transform: `scaleY(${pulse})`, transformOrigin: 'bottom',
              background: `linear-gradient(${tone}, ${tone}22)`, borderRadius: '6px 6px 0 0',
              boxShadow: `0 0 30px ${tone}55, inset 0 0 20px ${tone}44`,
              borderTop: `4px solid #ffffff`, opacity: clamp01(grow * 1.4)}} />
            {/* reflection */}
            <div style={{position: 'absolute', left: x, top: floorY, width: bandW, height: th * 0.5,
              background: `linear-gradient(${tone}55, #0000)`, borderRadius: '0 0 6px 6px',
              transform: 'scaleY(-1)', transformOrigin: 'top', opacity: 0.3 * grow, filter: 'blur(2px)'}} />
            {/* label */}
            <div style={{position: 'absolute', left: x, top: floorY + 22, width: bandW, textAlign: 'center',
              opacity: clamp01(seg(t, 0.3 + i * 0.05, 0.5 + i * 0.05)),
              color: isHero ? '#fff' : '#8b93a8', font: `${isHero ? 800 : 600} 22px/1 Inter, system-ui, sans-serif`}}>{label}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export default DataMonolith;
