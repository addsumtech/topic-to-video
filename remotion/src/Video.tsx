import React from 'react';
import {AbsoluteFill} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import {Scene, SceneData} from './Scene';
import type {Theme} from './theme/tokens';

// Single authoritative Theme lives in theme/tokens.ts; re-exported here so the many modules that
// `import {Theme} from './Video'` and those that import from './theme/tokens' share ONE type.
export type {Theme};

// Seam-look KEY (from render_remotion._TRANSITION_STYLE) -> a @remotion/transitions presentation.
// fade = cross-dissolve (opacity only, reduced-motion-safe); slide/wipe are directional page moves.
// Under reduced motion every seam collapses to fade (no travel).
function presentationFor(style: string | undefined, reduced: boolean) {
  if (reduced) return fade();
  switch (style) {
    case 'slide': return slide({direction: 'from-right'});
    case 'slide-up': return slide({direction: 'from-bottom'});
    case 'wipe': return wipe();
    default: return fade(); // 'fade' + 'blur' (blur shader is out of P3 scope) + unknown
  }
}

export type VideoProps = {
  width: number;
  height: number;
  fps: number;
  captionFontPx: number;
  theme: Theme;
  scenes: SceneData[];
};

export const defaultProps: VideoProps = {
  width: 1920,
  height: 1080,
  fps: 30,
  captionFontPx: 48,
  theme: {
    bg: '#0d1117',
    surface: '#161b22',
    fg: '#f0f3f8',
    muted: '#94989e',
    accent: '#5fb3c4',
    accent2: '#e0894a',
    scrim: 'rgba(13,17,23,.55)',
    onAccent: '#ffffff',
    onAccent2: '#ffffff',
    fontDisplay: '"Space Grotesk","Helvetica Neue",Arial,sans-serif',
    fontBody: '"Space Grotesk","Helvetica Neue",Arial,sans-serif',
    fontNumber: '"Space Grotesk","Helvetica Neue",Arial,sans-serif',
    fontKind: 'sans',
    style: '',
    radius: '14px',
    grainAmount: '0',
    trackScale: '1',
    lhDisplay: '1.08',
  },
  scenes: [],
};

// Total duration = sum of scene durations MINUS the transition overlaps (a transition makes the next
// scene start early, shortening the whole). Must match render_remotion's overlap math or A/V drifts.
export const calcMeta = ({props}: {props: VideoProps}) => {
  const fps = props.fps || 30;
  const sum = props.scenes.reduce((a, s) => a + Math.max(1, s.durationInFrames || 1), 0);
  const overlaps = props.scenes.reduce((a, s) => a + (s.transitionToNext?.durationInFrames || 0), 0);
  return {
    durationInFrames: Math.max(1, sum - overlaps) || fps,
    fps,
    width: props.width || 1920,
    height: props.height || 1080,
  };
};

export const Video: React.FC<VideoProps> = ({theme, scenes, captionFontPx}) => {
  // Interleave scene Sequences with cross-scene Transitions. A seam only gets a Transition when
  // build_props set transitionToNext (a marked seam that rides the audio-breath silence); otherwise the
  // scenes simply cut. The overlap length is frame-exact (linearTiming) so it matches calcMeta + the srt.
  const children: React.ReactNode[] = [];
  scenes.forEach((s, i) => {
    children.push(
      <TransitionSeries.Sequence key={`s${s.index}`} durationInFrames={Math.max(1, s.durationInFrames || 1)}>
        <Scene scene={s} theme={theme} captionFontPx={captionFontPx} />
      </TransitionSeries.Sequence>,
    );
    const t = s.transitionToNext;
    if (t && i < scenes.length - 1) {
      children.push(
        <TransitionSeries.Transition
          key={`t${s.index}`}
          timing={linearTiming({durationInFrames: Math.max(1, t.durationInFrames || 1)})}
          presentation={presentationFor(t.style, !!s.reducedMotion)}
        />,
      );
    }
  });
  return (
    <AbsoluteFill style={{backgroundColor: theme.bg}}>
      <TransitionSeries>{children}</TransitionSeries>
    </AbsoluteFill>
  );
};
