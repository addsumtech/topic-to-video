// SHOT · Card Stack 3D — cards spring up one by one and PILE at centre, then fan out into a 3D arc (each
// tilted on Y + rotated on Z), labels facing the camera. Pure CSS 3D (preserve-3d) — no WebGL. The "a deck of
// things → laid out in hand" register (family E). Deterministic (pile + fan = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeInOutCubic, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG = '#090b12';
const TONES0 = ['#5b8cff', '#ff6f91', '#37d4a6', '#f6a531', '#c07bff', '#4dd0e1'];

export const CardStack3D: React.FC<{items?: string[]; title?: string}> = ({
  items: ITEMS = ['Docs', 'Chat', 'Tasks', 'Code', 'Data', 'Calls'], title: TITLE = 'All of it, in hand'} = {}) => {
  const t = useT();
  const dna = useDNA(); const TONES = dnaPalette(dna, 6) ?? TONES0;
  const {width: W, height: H} = useVideoConfig();
  const cards = ITEMS.slice(0, 7);
  const n = cards.length;
  const mid = (n - 1) / 2;
  const cw = 360, ch = 480;
  const fan = easeInOutCubic(seg(t, 0.58, 0.92));
  const titleIn = easeOutCubic(seg(t, 0.66, 0.86));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? `radial-gradient(120% 100% at 50% 38%, #12162b, ${BG} 72%)`, overflow: 'hidden'}}>
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center', perspective: 1800}}>
        <div style={{position: 'relative', width: cw, height: ch, transformStyle: 'preserve-3d',
          transform: `translateY(${lerp(40, -30, fan)}px)`}}>
          {cards.map((label, i) => {
            const st = 0.06 + i * 0.07;
            const rise = easeOutBack(clamp01(seg(t, st, st + 0.24)));    // spring up into the pile
            const pileY = -i * 10, pileR = (hash01(i * 5) - 0.5) * 5;    // slight messy stack
            const ang = (i - mid) * 13;                                  // fan spread angle
            const tx = fan * (i - mid) * 300;
            const ty = lerp(pileY, Math.abs(i - mid) * 26, fan);         // arc dip at the ends
            const rz = lerp(pileR, ang, fan);
            const ry = fan * (i - mid) * 7;
            const tone = TONES[i % TONES.length];
            return (
              <div key={i} style={{position: 'absolute', left: 0, top: 0, width: cw, height: ch, opacity: clamp01(rise * 1.5),
                transformStyle: 'preserve-3d', transformOrigin: 'bottom center',
                transform: `translate3d(${tx}px, ${lerp(120, 0, rise) + ty}px, ${i * 2}px) rotateZ(${rz}deg) rotateY(${ry}deg)`,
                borderRadius: 24, background: `linear-gradient(160deg, #1c2233, #0f1320), linear-gradient(160deg, ${tone}1c, #0000)`,
                border: `1px solid ${tone}66`, boxShadow: `0 40px 90px #0009, inset 0 1px 0 #ffffff14, 0 0 0 1px #0006`,
                display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: 34}}>
                <div style={{width: 60, height: 60, borderRadius: 16, background: `linear-gradient(150deg, ${tone}, #2b3ac6)`,
                  boxShadow: `0 0 26px ${tone}66`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', font: `800 30px/1 var(--f-body, Inter, system-ui, sans-serif)`}}>{i + 1}</div>
                <div style={{color: '#f4f7ff', font: `800 46px/1 var(--f-body, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em',
                  textShadow: '0 2px 10px #000'}}>{label}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <div style={{position: 'absolute', bottom: 96, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        transform: `translateY(${(1 - titleIn) * 16}px)`, color: '#dfe6ff',
        font: `800 62px/1 var(--f-body, Inter, system-ui, sans-serif)`, letterSpacing: '-0.02em',
        textShadow: '0 8px 30px #000'}}>{TITLE}</div>
    </AbsoluteFill>
  );
};
export default CardStack3D;
