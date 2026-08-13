// SHOT · Map Routes — logistics/network language: glowing routes DRAW between pins on a dark night map, with
// packets travelling the arcs and pins pulsing. A cool, premium "it reaches everywhere / connects your stack"
// look. Deterministic (dash offset + packet position are pure fns of frame).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeInOutCubic, easeOutBack, clamp01, hash01} from '../runtime/motion';

export const DURATION = 165; // 5.5s
export const MapRoutes: React.FC<{items?: string[]; hub?: string; accent?: string}> = ({
  items: SPOKES = ['GitHub', 'Slack', 'Notion', 'Drive', 'Jira', 'Gmail'], hub: HUB = 'WorkBuddy', accent: TEAL = '#3FE0D0'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const hx = W / 2, hy = H / 2 + 20, R = 460;
  const pts = SPOKES.map((_, i) => {
    const a = (i / SPOKES.length) * Math.PI * 2 - Math.PI / 2;
    return [hx + Math.cos(a) * R * 1.5, hy + Math.sin(a) * R] as [number, number];
  });
  return (
    <AbsoluteFill style={{background: 'radial-gradient(130% 130% at 50% 45%, #0d2033, #060d16 72%)'}}>
      {/* faint map grid / graticule */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.35}}>
        {[...Array(30)].map((_, i) => <line key={`v${i}`} x1={i * 70} y1={0} x2={i * 70} y2={H} stroke="#123049" strokeWidth={1} />)}
        {[...Array(16)].map((_, i) => <ellipse key={`h${i}`} cx={hx} cy={hy} rx={120 + i * 130} ry={70 + i * 78} fill="none" stroke="#0f2a42" strokeWidth={1} />)}
      </svg>
      {/* glowing routes hub→spoke, drawing on, with a travelling packet */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {pts.map(([px, py], i) => {
          const midx = (hx + px) / 2, midy = (hy + py) / 2 - 140;
          const d = `M${hx},${hy} Q${midx},${midy} ${px},${py}`;
          const draw = clamp01((easeInOutCubic(seg(t, 0.12, 0.7)) - i * 0.03) / 0.4);
          const len = 1600;
          const pk = clamp01((t - 0.3 - i * 0.05) / 0.5); // packet position 0→1
          const bx = lerp(hx, px, pk), by = lerp(hy, py, pk) - Math.sin(pk * Math.PI) * 140;
          return <g key={i}>
            <path d={d} fill="none" stroke={TEAL} strokeWidth={3} strokeOpacity={0.9} strokeDasharray={len} strokeDashoffset={len * (1 - draw)}
              style={{filter: `drop-shadow(0 0 8px ${TEAL})`}} />
            {t > 0.3 + i * 0.05 && pk < 1 && <circle cx={bx} cy={by} r={7} fill="#eafffb" style={{filter: `drop-shadow(0 0 10px ${TEAL})`}} />}
          </g>;
        })}
      </svg>
      {/* spoke pins + labels */}
      {pts.map(([px, py], i) => {
        const pop = easeOutBack(seg(t, 0.14 + i * 0.05, 0.14 + i * 0.05 + 0.24));
        const pulse = 1 + 0.4 * Math.max(0, Math.sin((t - 0.3 - i * 0.05) * 9));
        return <div key={i} style={{position: 'absolute', left: px, top: py, transform: `translate(-50%,-50%) scale(${clamp01(pop)})`}}>
          <div style={{position: 'absolute', left: -18, top: -18, width: 36, height: 36, borderRadius: 18, background: TEAL, boxShadow: `0 0 20px ${TEAL}`}} />
          <div style={{position: 'absolute', left: -18 * pulse, top: -18 * pulse, width: 36 * pulse, height: 36 * pulse, borderRadius: '50%', border: `2px solid ${TEAL}`, opacity: 2 - pulse}} />
          <div style={{position: 'absolute', left: 34, top: -20, padding: '8px 16px', borderRadius: 8, background: 'rgba(10,25,35,.85)', border: `1px solid ${TEAL}55`, font: '700 26px/1 Inter', color: '#dffffa', whiteSpace: 'nowrap'}}>{SPOKES[i]}</div>
        </div>;
      })}
      {/* the hub */}
      <div style={{position: 'absolute', left: hx, top: hy, transform: 'translate(-50%,-50%)'}}>
        <div style={{width: 130, height: 130, borderRadius: 65, background: 'radial-gradient(circle,#fff,#8ff5e8 60%,#2fb5a5)', boxShadow: `0 0 60px ${TEAL}`, display: 'flex', alignItems: 'center', justifyContent: 'center', font: '800 30px/1 Inter', color: '#06322b', textAlign: 'center', padding: 8}}>{HUB}</div>
      </div>
    </AbsoluteFill>
  );
};
export default MapRoutes;
