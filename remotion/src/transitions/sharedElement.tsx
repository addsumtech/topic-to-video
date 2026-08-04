// SHARED-ELEMENT / MATCH-CUT transition (audit top-3 #3). A cross-scene seam where an ANCHOR shape is held
// (or morphed) across the cut while the two scenes cross-dissolve under it — the eye tracks one element from
// beat A into beat B, so a reel of separately-composed shots reads as ONE continuous authored space ("this
// IS that"). This is a REAL rendered transition, not just authoring discipline: it was long declared
// impossible ("-c copy can't see the neighbour"), but that limit was inherited from the ffmpeg image tier —
// here Video.tsx renders both scenes in ONE TransitionSeries where they co-exist during the overlap (clamped
// to the audio breath, A/V-safe). Deterministic: pure function of presentationProgress.
import React from 'react';
import {AbsoluteFill, useVideoConfig, Easing, interpolate} from 'remotion';
import type {TransitionPresentation, TransitionPresentationComponentProps} from '@remotion/transitions';
import type {Theme} from '../theme/tokens';

// [cx, cy, w, h] as FRACTIONS of the frame (0..1) — resolution-independent. `from` = the anchor's pose at
// A's end, `to` = its pose at B's start. from == to => a pure HOLD match-cut (the element stays put while
// everything else changes); from != to => a MORPH (it travels/scales from its A pose to its B pose).
export type MatchSpec = {
  shape?: 'box' | 'bar' | 'line' | 'dot';
  from: [number, number, number, number];
  to: [number, number, number, number];
  color?: string | null;
};

type Props = {match: MatchSpec; theme: Theme} & Record<string, unknown>;

const Anchor: React.FC<{match: MatchSpec; theme: Theme; p: number}> = ({match, theme, p}) => {
  const {width, height} = useVideoConfig();
  const e = Easing.inOut(Easing.cubic)(Math.max(0, Math.min(1, p)));
  const L = (a: number, b: number) => a + (b - a) * e;
  const f = match.from, t = match.to;
  const cx = L(f[0], t[0]) * width, cy = L(f[1], t[1]) * height;
  const w = L(f[2], t[2]) * width, h = L(f[3], t[3]) * height;
  const color = match.color || theme.accent;
  // hold the anchor solid through the middle; a gentle fade at the very ends so it blends into the real
  // element it sits on (the author aligns A's element with `from`, B's with `to`).
  const op = interpolate(p, [0, 0.12, 0.88, 1], [0.5, 1, 1, 0.5], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const base: React.CSSProperties = {position: 'absolute', left: cx - w / 2, top: cy - h / 2, width: w, height: h, opacity: op, pointerEvents: 'none'};
  const shape = match.shape || 'box';
  if (shape === 'bar' || shape === 'line') return <div style={{...base, background: color, borderRadius: shape === 'bar' ? 8 : 2, boxShadow: `0 0 34px ${color}55`}} />;
  if (shape === 'dot') return <div style={{...base, background: color, borderRadius: '50%', boxShadow: `0 0 40px ${color}77`}} />;
  return <div style={{...base, border: `3px solid ${color}`, borderRadius: 12, boxShadow: `0 0 34px ${color}55, inset 0 0 24px ${color}22`}} />; // box outline
};

const Presentation: React.FC<TransitionPresentationComponentProps<Props>> = ({children, presentationProgress, presentationDirection, passedProps}) => {
  const {match, theme} = passedProps;
  // cross-dissolve the two scenes; the anchor rides ABOVE both (drawn only on the entering side, which
  // stacks on top) at FULL opacity, so it reads as the continuity thread rather than fading with a scene.
  const opacity = presentationDirection === 'exiting' ? 1 - presentationProgress : presentationProgress;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{opacity}}>{children}</AbsoluteFill>
      {presentationDirection === 'entering' ? <Anchor match={match} theme={theme} p={presentationProgress} /> : null}
    </AbsoluteFill>
  );
};

export const sharedElement = (match: MatchSpec, theme: Theme): TransitionPresentation<Props> => ({
  component: Presentation,
  props: {match, theme},
});
