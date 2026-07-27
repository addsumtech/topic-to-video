import React from 'react';
import {AbsoluteFill, Series} from 'remotion';
import {Scene, SceneData} from './Scene';

// Extended theme tokens (matches theme/tokens.ts)
export type Theme = {
  bg: string;
  surface: string;
  fg: string;
  muted: string;
  accent: string;
  accent2: string;
  scrim: string;
  onAccent: string;
  onAccent2: string;
  fontDisplay: string;
  fontBody: string;
  fontNumber: string;
  fontKind: 'sans' | 'serif';
  style: string;
  radius: string;
  grainAmount: string;
  trackScale: string;
  lhDisplay: string;
};

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

// duration + canvas come from the storyboard (summed real per-scene durations).
export const calcMeta = ({props}: {props: VideoProps}) => {
  const fps = props.fps || 30;
  const total = props.scenes.reduce((a, s) => a + Math.max(1, s.durationInFrames || 1), 0) || fps;
  return {
    durationInFrames: total,
    fps,
    width: props.width || 1920,
    height: props.height || 1080,
  };
};

export const Video: React.FC<VideoProps> = ({theme, scenes, captionFontPx}) => {
  return (
    <AbsoluteFill style={{backgroundColor: theme.bg}}>
      <Series>
        {scenes.map((s) => (
          <Series.Sequence key={s.index} durationInFrames={Math.max(1, s.durationInFrames || 1)}>
            <Scene scene={s} theme={theme} captionFontPx={captionFontPx} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
