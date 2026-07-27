import React from 'react';
import {AbsoluteFill} from 'remotion';
import type {Theme} from './tokens';

// Finishing pass (OUTER 2D — never on a preserve-3d ancestor): style-driven graded wash + moving film grain.
// This is the single biggest "premium / filmic" uplift and it is deterministic (grain scroll = f(frame)).

const NOISE =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E" +
  "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E" +
  "%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E\")";

// Style-specific grade overlays (editorial = warm/cool split, technical = neutral contrast, minimal = subtle)
const GRADE_OVERLAYS: Record<string, string> = {
  editorial: 'linear-gradient(122deg, rgba(30,60,110,0.14) 0%, rgba(255,180,120,0.07) 100%)',
  technical: 'linear-gradient(135deg, rgba(20,40,80,0.10) 0%, rgba(100,100,120,0.05) 100%)',
  minimal: 'linear-gradient(180deg, rgba(0,0,0,0.03) 0%, rgba(0,0,0,0.01) 100%)',
};

export const Finish: React.FC<{frame: number; theme: Theme}> = ({frame, theme}) => {
  const grainAmount = parseFloat(theme.grainAmount || '0');
  const grade = GRADE_OVERLAYS[theme.style] || GRADE_OVERLAYS.editorial;
  const off = (frame * 11) % 200; // deterministic grain scroll

  return (
    <>
      {/* Graded wash layer */}
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          mixBlendMode: 'soft-light',
          background: grade,
        }}
      />
      {/* Film grain layer */}
      {grainAmount > 0 && (
        <AbsoluteFill
          style={{
            pointerEvents: 'none',
            mixBlendMode: 'overlay',
            opacity: grainAmount,
            backgroundImage: NOISE,
            backgroundRepeat: 'repeat',
            backgroundPosition: `${off}px ${off}px`,
          }}
        />
      )}
    </>
  );
};
