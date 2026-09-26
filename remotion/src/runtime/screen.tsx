// What a device's screen shows: the user's screenshot (a long one scrolls), their recording, or a page the
// register draws. The scroll can never show past its end except inside a fling's overshoot — the range is
// computed from the image's real height, never from a box that happens to hold it.
import React from 'react';
import {Img, OffthreadVideo, Sequence, staticFile, useVideoConfig} from 'remotion';
import {clamp01, easeOutCubic, easeInOutCubic} from './motion';

/** The height a screenshot takes at width `w`. A size that is not positive is refused: floored instead, a zero
 *  width gave a 2.3-million-pixel scroll range, and NaN a CSS height the browser silently drops. */
const scaledHeight = (imageW: number, imageH: number, w: number): number => {
  if (!(imageW > 0) || !(imageH > 0)) {
    throw new Error(`screen: a screenshot needs a positive size (got ${imageW}x${imageH})`);
  }
  return (imageH * w) / imageW;
};

export const scrollRangePx = (imageW: number, imageH: number, screenW: number, screenH: number): number =>
  Math.max(0, scaledHeight(imageW, imageH, screenW) - screenH);

/** A fling: a fast start and an eased stop at 1 + overshoot by 72% of the gesture, then a spring back to 1. */
export const flingAt = (u: number, overshoot = 0.04): number => {
  const c = clamp01(u);
  if (c <= 0.72) return (1 + overshoot) * easeOutCubic(c / 0.72);
  return 1 + overshoot * (1 - easeInOutCubic((c - 0.72) / 0.28));
};

export type VideoSpan = {f0: number; f1: number; v0: number; v1: number};

export const ScreenImage: React.FC<{src: string; imageW: number; imageH: number; w: number; h: number; offsetPx?: number}> =
  ({src, imageW, imageH, w, h, offsetPx = 0}) => (
    <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden', background: '#ffffff'}}>
      <Img src={staticFile(src)} style={{position: 'absolute', left: 0, top: -offsetPx, width: w,
        height: scaledHeight(imageW, imageH, w)}} />
    </div>
  );

/** A recording, beat frames [f0, f1) showing its seconds [v0, v1) — one Sequence per span, so a mapping that
 *  bends at a cue is a chain of constant rates. */
export const ScreenVideo: React.FC<{src: string; spans: VideoSpan[]; w: number; h: number}> = ({src, spans, w, h}) => {
  const {fps} = useVideoConfig();
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden', background: '#000000'}}>
      {spans.map((s, i) => {
        const frames = Math.max(1, Math.round(s.f1 - s.f0));
        return (
          <Sequence key={i} from={Math.round(s.f0)} durationInFrames={frames} layout="none">
            <OffthreadVideo src={staticFile(src)} muted trimBefore={Math.round(s.v0 * fps)}
              playbackRate={Math.max(0.01, ((s.v1 - s.v0) * fps) / frames)}
              style={{position: 'absolute', left: 0, top: 0, width: w, height: h, objectFit: 'cover'}} />
          </Sequence>
        );
      })}
    </div>
  );
};
