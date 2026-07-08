import React from 'react';
import {useCurrentFrame} from 'remotion';

// scene-local caption segments, in frames
export type CaptionSeg = {text: string; from: number; to: number};

export const Captions: React.FC<{segments: CaptionSeg[]; fontPx?: number}> = ({segments, fontPx}) => {
  const frame = useCurrentFrame();
  const seg = segments.find((s) => frame >= s.from && frame < s.to);
  if (!seg || !seg.text) return null;
  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 72, display: 'flex', justifyContent: 'center'}}>
      <div
        style={{
          maxWidth: '86%',
          textAlign: 'center',
          color: '#ffffff',
          fontSize: fontPx || 48,      // canvas-derived (min(W,H)*0.045), like the local renderer
          fontWeight: 600,
          lineHeight: 1.3,
          // Latin first, then CJK system fonts so zh/ja/ko don't tofu in headless Chromium
          fontFamily: 'Helvetica, Arial, "PingFang SC", "Hiragino Sans", "Noto Sans CJK SC", sans-serif',
          padding: '10px 26px',
          background: 'rgba(0,0,0,0.55)',
          borderRadius: 10,
          textShadow: '0 2px 8px rgba(0,0,0,0.6)',
        }}
      >
        {seg.text}
      </div>
    </div>
  );
};
