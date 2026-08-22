// SHOT · Fracture In — a hero poster ASSEMBLES from 25 tiles that fly in from scattered 3D space and lock
// into the grid center-out (a ripple by distance from centre), then the title resolves over the settled
// surface. Pure CSS 3D (preserve-3d) — no WebGL. The "many shards → one image" reveal (family E). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutExpo, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
const BG_D0 = '#080a12';
const COLS = 5, ROWS = 5, TW = 208, TH = 150;

export const FractureIn: React.FC<{title?: string; tagline?: string; accent?: string}> = ({
  title: TITLE = 'One picture', tagline: TAG = 'from many moving parts', accent: ACC = '#5b8cff'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const gw = COLS * TW, gh = ROWS * TH;
  const ox = (W - gw) / 2, oy = (H - gh) / 2 - 10;
  const cxi = (COLS - 1) / 2, cyi = (ROWS - 1) / 2;
  const titleIn = easeOutCubic(seg(t, 0.6, 0.82));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, #12162b, ${BG} 72%)`,
      overflow: 'hidden'}}>
      <AbsoluteFill style={{perspective: 1500}}>
        <div style={{position: 'absolute', left: ox, top: oy, width: gw, height: gh, transformStyle: 'preserve-3d'}}>
          {[...Array(COLS * ROWS)].map((_, i) => {
            const col = i % COLS, row = Math.floor(i / COLS);
            const dist = Math.hypot(col - cxi, row - cyi) / Math.hypot(cxi, cyi); // 0 centre → 1 edge
            const st = 0.06 + dist * 0.34;
            const r = easeOutExpo(seg(t, st, st + 0.26));
            // scattered start: random offset + Z + rotation, all → 0
            const sx = (hash01(i * 3) - 0.5) * 1400, sy = (hash01(i * 7) - 0.5) * 1000;
            const sz = 500 + hash01(i * 5) * 900, rot = (hash01(i * 11) - 0.5) * 160;
            const tx = lerp(sx, 0, r), ty = lerp(sy, 0, r), tz = lerp(sz, 0, r);
            const ro = lerp(rot, 0, r);
            // cohesive poster: a diagonal gradient tint per tile
            const g = (col + row) / (COLS + ROWS - 2);
            return (
              <div key={i} style={{position: 'absolute', left: col * TW, top: row * TH, width: TW - 6, height: TH - 6,
                opacity: clamp01(r * 1.6), borderRadius: 10, transformStyle: 'preserve-3d',
                transform: `translate3d(${tx}px, ${ty}px, ${tz}px) rotateY(${ro}deg) rotateX(${ro * 0.5}deg)`,
                background: `linear-gradient(135deg, ${ACC}, #b06bff ${lerp(20, 90, g)}%)`,
                boxShadow: `inset 0 1px 0 #ffffff30, 0 14px 40px #0006`,
                filter: `brightness(${lerp(0.72, 1.12, g)})`}} />
            );
          })}
        </div>
      </AbsoluteFill>

      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        pointerEvents: 'none'}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 20}px)`,
          color: '#fff', font: '800 128px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em',
          textShadow: '0 20px 60px #000a'}}>{TITLE}</div>
        <div style={{opacity: clamp01(seg(t, 0.72, 0.9)), marginTop: 22, color: '#dfe6ff',
          font: '600 34px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.14em',
          textShadow: '0 4px 20px #000'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default FractureIn;
