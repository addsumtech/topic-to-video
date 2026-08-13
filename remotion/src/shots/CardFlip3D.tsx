// SHOT · Card Flip 3D — a row of cards standing in perspective FLIP 180° on their Y axis (staggered), a
// light sheen sweeping the seam at the half-turn, revealing the payoff on the back. Pure CSS 3D
// (preserve-3d + backface-visibility) — no WebGL. The "question → answer, turned over" register. Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';

export const DURATION = 150; // 5s
const BG = '#0a0c13', ACC = '#6ea8ff';

type Item = {front?: string; back?: string};

const Face: React.FC<{children: React.ReactNode; back?: boolean; tone: string}> = ({children, back, tone}) => (
  <div style={{position: 'absolute', inset: 0, backfaceVisibility: 'hidden',
    transform: back ? 'rotateY(180deg)' : undefined, borderRadius: 26,
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40,
    background: back
      ? `linear-gradient(155deg, ${tone}, #2c3ac0)`
      : 'linear-gradient(155deg, #171a28, #0f1220)',
    border: `1px solid ${back ? 'transparent' : '#262a42'}`,
    boxShadow: '0 40px 90px #0008, inset 0 1px 0 #ffffff12'}}>{children}</div>
);

export const CardFlip3D: React.FC<{items?: Item[]; title?: string}> = ({
  items: ITEMS = [{front: 'Manual', back: 'Automated'}, {front: 'Hours', back: 'Seconds'}, {front: 'Guesswork', back: 'Grounded'}],
  title: TITLE = 'What changes'} = {}) => {
  const t = useT();
  const {width: W} = useVideoConfig();
  const cards = ITEMS.slice(0, 4);
  const n = cards.length;
  const cw = 440, ch = 560, gap = 56;
  const rowW = n * cw + (n - 1) * gap;
  const x0 = (W - rowW) / 2;
  const titleIn = easeOutCubic(seg(t, 0.04, 0.2));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 40%, #12162b, ${BG} 68%)`}}>
      <div style={{position: 'absolute', top: 96, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#aeb6ca',
        font: '700 32px/1 "JetBrains Mono", monospace', letterSpacing: '0.26em', textTransform: 'uppercase'}}>{TITLE}</div>

      <div style={{position: 'absolute', top: 300, left: 0, right: 0, height: ch, perspective: 1900}}>
        {cards.map((c, i) => {
          const st = 0.18 + i * 0.16;
          const r = clamp01(seg(t, st, st + 0.34));
          const rot = lerp(0, 180, easeInOutCubic(r));
          const rise = easeOutCubic(clamp01(seg(t, 0.06 + i * 0.06, 0.24 + i * 0.06)));
          const sheen = Math.max(0, 1 - Math.abs(r - 0.5) * 6); // flash at the half-turn
          const tone = [ACC, '#ff7aa8', '#37d4a6', '#f7b955'][i % 4];
          return (
            <div key={i} style={{position: 'absolute', left: x0 + i * (cw + gap), top: 0, width: cw, height: ch,
              transformStyle: 'preserve-3d', opacity: rise,
              transform: `translateY(${(1 - rise) * 60}px) rotateY(${rot}deg)`}}>
              <Face tone={tone}>
                <div style={{color: '#8b93a8', font: '600 22px/1 "JetBrains Mono", monospace',
                  letterSpacing: '0.14em', marginBottom: 22}}>{String(i + 1).padStart(2, '0')}</div>
                <div style={{color: '#eef2ff', font: '800 64px/1.02 Inter, system-ui, sans-serif',
                  textAlign: 'center', letterSpacing: '-0.02em'}}>{c.front}</div>
              </Face>
              <Face back tone={tone}>
                <div style={{color: '#ffffffcc', font: '600 22px/1 "JetBrains Mono", monospace',
                  letterSpacing: '0.14em', marginBottom: 22}}>→</div>
                <div style={{color: '#fff', font: '800 64px/1.02 Inter, system-ui, sans-serif',
                  textAlign: 'center', letterSpacing: '-0.02em'}}>{c.back}</div>
              </Face>
              {sheen > 0.01 ? <div style={{position: 'absolute', inset: 0, borderRadius: 26, pointerEvents: 'none',
                background: 'linear-gradient(105deg, #fff0 40%, #ffffffcc 50%, #fff0 60%)',
                opacity: sheen * 0.8, transform: 'translateZ(2px)'}} /> : null}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export default CardFlip3D;
