// MOTION BLUR — draws what runtime/motionBlurCore computes. One component, for anything a register moves fast:
//
//   <SpeedBlur at={(f) => ({x: ..., y: ..., s: ..., r: ...})}> ...the element, drawn around its own origin... </SpeedBlur>
//
// `at` is the element's pose as a pure function of the frame — the same function the register already uses to
// place it — so the velocity is the velocity on screen, not an estimate. The smear runs ALONG the motion (an SVG
// Gaussian blurred on one axis only, inside a wrapper turned to the direction of travel and its content turned
// back), so a horizontal whip softens edges across the motion and leaves the other axis sharp. `ghosts` adds
// earlier poses for the moves a one-axis blur cannot express: a card thrown along an arc while it spins. (Tried and
// dropped for a zoom toward the lens: its earlier poses are smaller and lie INSIDE it, so ghosts drawn over it read
// as a stuttering numeral, and under it they are hidden.)
//
// At rest nothing is filtered (motionBlurCore returns null), so a settled element is drawn exactly as it would be
// without this file. The type it carries keeps the baseline unlock for the whole span (runtime/glide), the same
// rule every moving path in the library follows.
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {smear, ghosts as ghostPoses, type Pose, type SmearOpts, type GhostOpts} from './motionBlurCore';
import {useGlide} from './glide';

export type {Pose} from './motionBlurCore';

const place = (p: Pose) => `translate(${p.x}px, ${p.y}px) rotate(${p.r ?? 0}deg) scale(${p.s ?? 1})`;

// The filter region: an HTML element's url() filter is sized from its own border box, and the wrapper here is a
// zero-size anchor, so the region is set in user space, wide enough for anything a frame can hold.
const REGION = {x: -4000, y: -4000, width: 8000, height: 8000};

export const SpeedBlur: React.FC<{
  at: (frame: number) => Pose;
  blur?: SmearOpts | false;
  ghosts?: GhostOpts | false;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({at, blur = {}, ghosts = false, style, children}) => {
  const frame = useCurrentFrame();
  const glide = useGlide();
  const id = 'sb' + React.useId().replace(/[^a-zA-Z0-9]/g, '');
  const now = at(frame);
  const s = blur === false ? null : smear(now, at(frame - 1), blur);
  const trail = ghosts === false ? [] : ghostPoses(at, frame, ghosts);
  const layer = (p: Pose, key: string, opacity = 1) => {
    if (!s) {
      return (
        <div key={key} style={{position: 'absolute', left: 0, top: 0, opacity, transformOrigin: '0 0',
          transform: glide(place(p), true)}}>
          {children}
        </div>
      );
    }
    // turned to the direction of travel, blurred on its own x axis, the content turned back
    return (
      <div key={key} style={{position: 'absolute', left: 0, top: 0, opacity, filter: `url(#${id})`, transformOrigin: '0 0',
        transform: glide(`translate(${p.x}px, ${p.y}px) rotate(${s.angle}deg)`, true)}}>
        <div style={{position: 'absolute', left: 0, top: 0, transformOrigin: '0 0',
          transform: `rotate(${-s.angle + (p.r ?? 0)}deg) scale(${p.s ?? 1})`}}>
          {children}
        </div>
      </div>
    );
  };
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 0, height: 0, ...style}}>
      {s ? (
        <svg width={0} height={0} style={{position: 'absolute'}} aria-hidden>
          <filter id={id} filterUnits="userSpaceOnUse" {...REGION} colorInterpolationFilters="sRGB">
            <feGaussianBlur stdDeviation={`${s.sigma.toFixed(3)} 0`} />
          </filter>
        </svg>
      ) : null}
      {trail.slice().reverse().map((g, i) => layer(g, 'g' + i, g.opacity))}
      {layer(now, 'now')}
    </div>
  );
};
