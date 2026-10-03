// Probe: does type ride a moving camera as smoothly as the drawing it sits in — and does the camera ever
// uncover the frame?
//
// The failure this exists for is the one a viewer reported as 字体还是会有很轻微的抖动 on a delivered film: under
// a push, Skia snapped every line of type to whole device pixels while the rules and shapes beside it glided,
// so the type advanced in 1px steps against its own drawing (runtime/depth.tsx, "the baseline unlock"). A
// still cannot show it and a frame difference cannot isolate it, so the probe draws the two things the
// measurement compares and nothing else: ONE line of black type and ONE red rule under it, both inside the
// real SceneCamera. tests/test_camera_type.py renders the move and fits the type's ink centroid against the
// rule's — a camera that moves both together leaves no residual; a snapped baseline leaves a sawtooth.
//
// Everything is told apart by COLOUR, not by position, so the test needs no crop that a later layout change
// could silently cut the type out of: the type is the only ink with red missing, the rule the only ink with
// red and no green. The camera's own ground is white and the frame BEHIND the camera is yellow, so any sliver
// the camera's layer fails to cover — the cost the unlock's skew would carry without its overscan — is the
// only ink with blue missing.
//
// The line sits far from the camera's origin (the content zone's centre), so a push carries it tens of
// pixels; a probe near the origin barely moves and proves nothing. `bare` draws the same page with no camera
// at all, which is what a beat that holds must look like to the pixel.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {SceneCamera, type CameraMove} from './depth';
import {CONTENT_TOP} from './layout';

export const DURATION = 120;

export const CameraTypeProbe: React.FC<{move?: CameraMove; amount?: number; pan?: [number, number];
  bare?: boolean; text?: string}> = ({move = 'push', amount, pan, bare = false,
  text = 'Type rides the camera 字随镜头走'}) => {
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const x = Math.round(W * 0.08), y = Math.round(CONTENT_TOP + H * 0.06), px = Math.round(U * 0.04);
  const page = (
    <AbsoluteFill style={{background: '#ffffff'}}>
      <div style={{position: 'absolute', left: x, top: y, color: '#000000', whiteSpace: 'nowrap',
        font: `700 ${px}px/1.2 Inter, "Noto Sans SC", sans-serif`}}>{text}</div>
      <div style={{position: 'absolute', left: x, top: y + Math.round(px * 1.6), width: Math.round(W * 0.34),
        height: 3, background: '#ff0000'}} />
    </AbsoluteFill>
  );
  return (
    <AbsoluteFill style={{background: '#ffff00'}}>
      {bare ? page : <SceneCamera move={move} amount={amount} pan={pan}>{page}</SceneCamera>}
    </AbsoluteFill>
  );
};
