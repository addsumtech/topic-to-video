// SHOT · Low-Poly Form — a crystalline low-poly plane: a jittered triangle mesh assembles centre-out (each
// facet scaling + fading in from its centroid), colour graded across a duotone, with a wordmark settling over
// it. Faceted generative geometry (family K · generative). Deterministic (vertices jittered by hash, reveal by
// distance-from-centre).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#080a14';
const GX = 11, GY = 7;

export const LowPolyForm: React.FC<{title?: string; tagline?: string; accent?: string; accent2?: string}> = ({
  title: TITLE = 'Faceted', tagline: TAG = 'many facets, one form', accent: ACC = '#5b8cff', accent2: ACC2 = '#ff5b9e'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cellW = W / GX, cellH = H / GY;
  // jittered vertex grid (deterministic)
  const vert = (gx: number, gy: number) => {
    const edge = gx === 0 || gy === 0 || gx === GX || gy === GY;
    const jx = edge ? 0 : (hash01(gx * 13.1 + gy * 7.7) - 0.5) * cellW * 0.7;
    const jy = edge ? 0 : (hash01(gx * 5.3 + gy * 19.1) - 0.5) * cellH * 0.7;
    return [gx * cellW + jx, gy * cellH + jy] as [number, number];
  };
  const cx = W / 2, cy = H / 2;
  const maxD = Math.hypot(cx, cy);
  const tris: {pts: string; col: string; r: number}[] = [];
  for (let gx = 0; gx < GX; gx++) for (let gy = 0; gy < GY; gy++) {
    const a = vert(gx, gy), b = vert(gx + 1, gy), c = vert(gx + 1, gy + 1), d = vert(gx, gy + 1);
    const flip = (gx + gy) % 2 === 0;
    const t1 = flip ? [a, b, c] : [a, b, d], t2 = flip ? [a, c, d] : [b, c, d];
    for (const tri of [t1, t2]) {
      const mx = (tri[0][0] + tri[1][0] + tri[2][0]) / 3, my = (tri[0][1] + tri[1][1] + tri[2][1]) / 3;
      const dist = Math.hypot(mx - cx, my - cy) / maxD;
      const gh = clamp01(mx / W + (0.5 - my / H) * 0.4);
      const col = `color-mix(in oklab, ${ACC} ${Math.round((1 - gh) * 100)}%, ${ACC2})`;
      tris.push({pts: tri.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' '), col, r: dist});
    }
  }
  const titleIn = easeOutCubic(seg(t, 0.52, 0.76));
  const tagIn = easeOutCubic(seg(t, 0.64, 0.86));
  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {tris.map((tr, i) => {
          const st = 0.04 + tr.r * 0.45;
          const e = easeOutBack(clamp01(seg(t, st, st + 0.26)));
          const bright = lerp(0.55, 1, clamp01(seg(t, st, st + 0.4)));
          return <polygon key={i} points={tr.pts} fill={tr.col} opacity={clamp01(e) * 0.92}
            style={{transformBox: 'fill-box', transformOrigin: 'center', transform: `scale(${lerp(0.2, 1, e)})`,
              filter: `brightness(${bright})`, stroke: '#00000022', strokeWidth: 1}} />;
        })}
      </svg>
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(38% 40% at 50% 50%, #080a14cc, #0000 72%)'}} />
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 16}px)`, color: '#fff',
          font: '800 138px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em', textShadow: '0 12px 50px #000'}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 22, color: '#c7d2e8',
          font: '600 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.18em', textShadow: '0 4px 20px #000'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default LowPolyForm;
