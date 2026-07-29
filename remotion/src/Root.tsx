import React from 'react';
import {Composition} from 'remotion';
import {Video, calcMeta, defaultProps} from './Video';
import {loadDeckFonts} from './theme/fonts';

// Register the deck's bundled faces at bundle-eval time so every render BLOCKS until they're ready
// (loadFont uses delayRender internally). Without this the tier silently falls back to whatever fonts
// the render machine happens to have — the exact portability bug P1 exists to close.
loadDeckFonts();

// One composition, "Main". Its fps / width / height / duration are ALL derived from the
// input props (the storyboard) via calculateMetadata — render_remotion.py passes --props.
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Main"
      component={Video}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={defaultProps}
      calculateMetadata={calcMeta}
    />
  );
};
