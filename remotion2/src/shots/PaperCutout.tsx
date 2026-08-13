// SHOT · Paper Cutout — a layered 2.5D parallax diorama (craft "style" axis): cut-paper landscape in stacked
// depth planes with soft paper shadows; a camera pan makes near layers slide more than far ones (real parallax),
// and a paper "DONE" banner rises in the mid-ground. Warm construction-paper palette. Deterministic (cam = t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack, hash01} from '../runtime/motion';

export const DURATION = 165; // 5.5s

export const PaperCutout: React.FC<{label?: string; tagline?: string}> = ({label = 'DONE ✓', tagline = 'your ai team · on your machine'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cam = Math.sin(t * Math.PI - Math.PI / 2) * 120; // eased L→R pan
  const push = lerp(1.0, 1.08, easeOutCubic(t));
  // a soft paper shadow filter is applied per layer via drop-shadow
  const shadow = 'drop-shadow(0 14px 10px rgba(90,60,40,0.22))';

  // paper hill layer as an SVG path
  const hill = (baseY: number, amp: number, k: number, phase: number) => {
    let d = `M${-200},${H} L${-200},${baseY}`;
    for (let x = -200; x <= W + 200; x += 60) d += ` L${x},${(baseY + Math.sin(x / W * k * Math.PI * 2 + phase) * amp).toFixed(1)}`;
    d += ` L${W + 200},${H} Z`;
    return d;
  };

  const Layer: React.FC<{depth: number; children: React.ReactNode}> = ({depth, children}) => (
    <g transform={`translate(${-cam * depth} 0) scale(${lerp(1, push, depth)})`} style={{transformOrigin: 'center', filter: shadow}}>{children}</g>
  );

  return (
    <AbsoluteFill style={{background: 'linear-gradient(#ffe3b8 0%, #ffd0a0 46%, #ffcaa0 60%)', overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}} viewBox={`0 0 ${W} ${H}`}>
        {/* sun (far) */}
        <Layer depth={0.06}><circle cx={W * 0.72} cy={H * 0.3} r={130} fill="#ffb15a" /></Layer>
        {/* far hills */}
        <Layer depth={0.16}><path d={hill(H * 0.52, 40, 1.4, 0.4)} fill="#e58a86" /></Layer>
        {/* clouds */}
        <Layer depth={0.24}>
          {[{x: 360, y: 200}, {x: 1300, y: 150}, {x: 900, y: 260}].map((c, i) => (
            <g key={i} fill="#fff5ea" opacity={0.95}>
              <ellipse cx={c.x} cy={c.y} rx={100} ry={40} /><ellipse cx={c.x + 66} cy={c.y + 10} rx={64} ry={34} /><ellipse cx={c.x - 66} cy={c.y + 12} rx={58} ry={30} />
            </g>
          ))}
        </Layer>
        {/* mid hills */}
        <Layer depth={0.4}><path d={hill(H * 0.64, 60, 1.1, 2.1)} fill="#d76a5f" /></Layer>
        {/* near hills */}
        <Layer depth={0.7}><path d={hill(H * 0.8, 80, 0.9, 4.0)} fill="#b5453f" /></Layer>
        {/* foreground grass tufts */}
        <Layer depth={1.0}>
          <path d={hill(H * 0.94, 34, 2.2, 1.2)} fill="#7d2f2c" />
        </Layer>
      </svg>

      {/* paper DONE banner rises in the mid-ground */}
      {(() => {
        const rise = easeOutBack(seg(t, 0.42, 0.68));
        return (
          <div style={{position: 'absolute', left: '50%', top: H * 0.42, transform: `translate(-50%, ${(1 - rise) * 120}px) rotate(-2deg)`, opacity: rise > 0 ? 1 : 0, filter: shadow}}>
            <div style={{background: '#fff6e9', border: '6px solid #7d2f2c', borderRadius: 14, padding: '16px 54px',
              font: '900 92px/1 "Baloo 2", Inter, sans-serif', color: '#b5453f', letterSpacing: '0.02em'}}>{label}</div>
          </div>
        );
      })()}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: H * 0.08, textAlign: 'center',
        opacity: clamp01(seg(t, 0.7, 0.9)), color: '#fff6e9', font: '800 40px/1 "Baloo 2", Inter, sans-serif',
        textShadow: '0 3px 0 #7d2f2c'}}>{tagline}</div>
    </AbsoluteFill>
  );
};
export default PaperCutout;
