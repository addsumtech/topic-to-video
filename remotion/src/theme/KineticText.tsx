import React from 'react';
import {interpolate, spring, useVideoConfig} from 'remotion';

// Kinetic typography: text reveals unit-by-unit (word or line) with a restrained spring settle, instead
// of appearing all at once or with a single fade. This is the biggest "designed, not static" upgrade for
// the cinematic tier's type. Deterministic (pure function of frame). Reduced motion => everything visible
// instantly (no travel), so the accessibility variant stays a still frame.
//
// Premium-motion discipline (Apple/Stripe/Linear): RESTRAINED spring — overshootClamping so display type
// settles with quiet confidence, not a bouncy pop; ONE property leads (a small rise + fade), not many
// competing moves; a gentle per-unit stagger reads as choreography, not a wall appearing.

export type KineticSplit = 'word' | 'line' | 'none';

export const KineticText: React.FC<{
  text: string;
  frame: number; // scene-local frame
  startFrame?: number; // when the reveal begins (default 0)
  split?: KineticSplit; // word (default) | line | none (single fade)
  staggerFrames?: number; // per-unit delay (default 3)
  risePx?: number; // how far each unit rises in (default 22)
  reduced?: boolean;
  style?: React.CSSProperties; // typography (family/size/color/weight/tracking) from the caller
}> = ({text, frame, startFrame = 0, split = 'word', staggerFrames = 3, risePx = 22, reduced, style}) => {
  const {fps} = useVideoConfig();
  const units = split === 'none' ? [text] : split === 'line' ? text.split('\n') : text.split(' ');

  const renderUnit = (u: string, i: number, isWord: boolean) => {
    const start = startFrame + i * staggerFrames;
    let opacity = 1;
    let ty = 0;
    if (!reduced) {
      const s = spring({frame: frame - start, fps, config: {damping: 200, mass: 0.7, stiffness: 120}, durationInFrames: 22});
      opacity = interpolate(s, [0, 1], [0, 1]);
      ty = interpolate(s, [0, 1], [risePx, 0]);
    }
    return (
      <span
        key={i}
        style={{
          display: 'inline-block',
          opacity,
          transform: `translateY(${ty}px)`,
          // a hair of horizontal air after each word (inline-block eats the normal space)
          marginRight: isWord ? '0.28em' : undefined,
          whiteSpace: split === 'line' ? 'pre' : undefined,
        }}
      >
        {u}
      </span>
    );
  };

  if (split === 'line') {
    return (
      <span style={{...style, display: 'inline-block'}}>
        {units.map((u, i) => (
          <span key={i} style={{display: 'block'}}>{renderUnit(u, i, false)}</span>
        ))}
      </span>
    );
  }
  return <span style={{...style, display: 'inline-block'}}>{units.map((u, i) => renderUnit(u, i, split === 'word'))}</span>;
};
