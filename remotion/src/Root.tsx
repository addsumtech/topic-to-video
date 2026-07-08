import React from 'react';
import {Composition} from 'remotion';
import {Video, calcMeta, defaultProps} from './Video';

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
