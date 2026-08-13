// SHOT · Hud Reticle — a sci-fi FUI: corner brackets snap inward around a central subject, a dashed scan ring
// rotates, tick marks and status readouts type in, and the system LOCKS (ring goes solid + green). The
// "targeting / analysing / locked on" technical register (family D). Readouts are QUALITATIVE status words, not
// stats. Deterministic (ring angle + reveals = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic} from '../runtime/motion';

export const DURATION = 150; // 5s
const BG = '#070b0e', CYAN = '#37e0d4', GREEN = '#3affa0';

export const HudReticle: React.FC<{target?: string; readouts?: string[]; title?: string}> = ({
  target: TARGET = 'WorkBuddy', readouts: READOUTS = ['SIGNAL · strong', 'SCOPE · full workspace', 'STATUS · ready'],
  title: TITLE = 'Locking on'} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 + 10, R = 300;
  const brackets = easeOutExpo(seg(t, 0.1, 0.4));       // corner brackets snap in
  const ringAng = t * 300;                              // continuous scan rotation (deg)
  const locked = t > 0.76;
  const col = locked ? GREEN : CYAN;
  const lockIn = easeOutExpo(seg(t, 0.76, 0.9));
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const bo = lerp(120, 0, brackets); // bracket offset from target (px)
  const half = R + 60;
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 45%, #0c151a, ${BG} 74%)`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 66, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#7fb6b2', font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* faint grid */}
        <g opacity={0.12 * brackets}>
          {[...Array(9)].map((_, i) => <line key={'v' + i} x1={cx - 400 + i * 100} y1={cy - 360} x2={cx - 400 + i * 100} y2={cy + 360} stroke={CYAN} strokeWidth={1} />)}
          {[...Array(7)].map((_, i) => <line key={'h' + i} x1={cx - 400} y1={cy - 300 + i * 100} x2={cx + 400} y2={cy - 300 + i * 100} stroke={CYAN} strokeWidth={1} />)}
        </g>
        {/* rotating dashed scan ring */}
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={col} strokeWidth={locked ? 5 : 2}
          strokeDasharray={locked ? undefined : '18 22'} opacity={0.85}
          transform={`rotate(${ringAng} ${cx} ${cy})`} style={{filter: `drop-shadow(0 0 8px ${col})`}} />
        <circle cx={cx} cy={cy} r={R - 26} fill="none" stroke={col} strokeWidth={1} opacity={0.3}
          transform={`rotate(${-ringAng * 0.6} ${cx} ${cy})`} strokeDasharray="4 14" />
        {/* crosshair */}
        <g opacity={brackets}>
          <line x1={cx - 60} y1={cy} x2={cx + 60} y2={cy} stroke={col} strokeWidth={2} />
          <line x1={cx} y1={cy - 60} x2={cx} y2={cy + 60} stroke={col} strokeWidth={2} />
        </g>
        {/* corner brackets */}
        {[[-1, -1], [1, -1], [-1, 1], [1, 1]].map((s, i) => {
          const bx = cx + s[0] * (half + bo), by = cy + s[1] * (half * 0.72 + bo), L = 54;
          return <g key={i} stroke={col} strokeWidth={4} fill="none" opacity={brackets}>
            <line x1={bx} y1={by} x2={bx - s[0] * L} y2={by} /><line x1={bx} y1={by} x2={bx} y2={by - s[1] * L} />
          </g>;
        })}
      </svg>

      {/* central subject */}
      <div style={{position: 'absolute', left: cx, top: cy, transform: `translate(-50%,-50%) scale(${lerp(0.9, 1, brackets)})`, textAlign: 'center'}}>
        <div style={{color: '#eafffb', font: '800 84px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.02em',
          textShadow: `0 0 40px ${col}66`}}>{TARGET}</div>
        <div style={{marginTop: 14, color: col, font: '700 26px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em',
          opacity: locked ? lockIn : 0.6 * clamp01(seg(t, 0.4, 0.6))}}>{locked ? '● LOCKED' : 'SCANNING…'}</div>
      </div>

      {/* side readouts */}
      <div style={{position: 'absolute', left: 120, top: cy - 60, display: 'flex', flexDirection: 'column', gap: 16}}>
        {READOUTS.map((rd, i) => {
          const on = clamp01(seg(t, 0.42 + i * 0.1, 0.6 + i * 0.1));
          return <div key={i} style={{opacity: on, transform: `translateX(${(1 - on) * -16}px)`,
            color: '#9fd6d0', font: '600 26px/1 "JetBrains Mono", monospace', letterSpacing: '0.08em',
            borderLeft: `3px solid ${col}`, paddingLeft: 14}}>{rd}</div>;
        })}
      </div>
    </AbsoluteFill>
  );
};
export default HudReticle;
