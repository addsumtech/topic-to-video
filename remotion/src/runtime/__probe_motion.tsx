// MOTION PROBE — the frames that show runtime/motionBlur doing its job: a card with type whipping across the frame
// (blurred along its travel, sharp across it, untouched once it lands) and a mark thrown along an arc while it spins
// (speed ghosts, which a one-axis blur cannot draw). `blur: false` / `ghosts: false` switch each off for an A/B.
import React from 'react';
import {AbsoluteFill, Easing, interpolate} from 'remotion';
import {SpeedBlur, type Pose} from './motionBlur';

export const DURATION = 60;

const ease = Easing.bezier(0.7, 0, 0.2, 1);

export const MotionProbe: React.FC<{blur?: boolean; ghosts?: boolean}> = ({blur = true, ghosts = true}) => {
  const card = (f: number): Pose => ({x: interpolate(f, [6, 30], [160, 1180], {extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp', easing: ease}), y: 220});
  const mark = (f: number): Pose => {
    const p = interpolate(f, [24, 40], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
    // thrown along an arc while it spins down to rest — the move a one-axis blur cannot draw
    return {x: 360 + 1100 * p, y: 860 - 260 * Math.sin(Math.PI * p), s: 0.6 + 0.4 * p, r: (1 - p) * -220};
  };
  return (
    <AbsoluteFill style={{background: '#101418', fontFamily: 'Inter, sans-serif'}}>
      <SpeedBlur at={card} blur={blur ? {} : false}>
        <div style={{width: 580, height: 260, borderRadius: 24, background: '#f3efe6', padding: '36px 44px',
          boxSizing: 'border-box', color: '#14181c'}}>
          <div style={{fontSize: 30, letterSpacing: '.12em', color: '#a45a1c', fontWeight: 700}}>SCROLL BRAKE</div>
          <div style={{fontSize: 76, fontWeight: 800, marginTop: 14}}>2,400 px</div>
        </div>
      </SpeedBlur>
      <SpeedBlur at={mark} blur={false} ghosts={ghosts ? {count: 4, spacing: 1} : false}>
        <div style={{width: 300, height: 300, marginLeft: -150, marginTop: -150, borderRadius: 64,
          background: '#ffb547', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 140, fontWeight: 900, color: '#14181c'}}>1</div>
      </SpeedBlur>
    </AbsoluteFill>
  );
};
