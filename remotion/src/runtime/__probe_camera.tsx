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
//
// `legacy` draws the camera with the unlock switched off (BaselineUnlockContext) — exactly the camera before the
// unlock existed — so the type-glide census can be shown the defect it exists to find. `typeGlide` mounts that
// census. `layer` puts the page through one of the things that change how Skia rasterises type — a css filter
// (`shadow`, `saturate`, `blur`, as runtime/depth's planes and runtime/focus's lens apply them) or a
// `will-change` compositing layer — so whether the unlock survives each one is measured, not assumed.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {SceneCamera, type CameraMove} from './depth';
import {useCurrentFrame} from 'remotion';
import {BASELINE_UNLOCK, BaselineUnlockContext} from './glide';
import {CONTENT_TOP} from './layout';
import {TypeGlideAudit} from './textSafe';

export type ProbeLayer = 'none' | 'shadow' | 'saturate' | 'blur' | 'will-change';
const LAYER_STYLE: Record<ProbeLayer, React.CSSProperties> = {
  none: {},
  // the shadow is YELLOW so the measurement cannot mistake it for type (red missing) or for the rule (red without
  // green): what is measured is the type drawn through the filter, not the shadow the filter adds
  shadow: {filter: 'drop-shadow(0 6px 8px rgba(255,255,0,0.85))'},
  saturate: {filter: 'saturate(0.955)'},
  blur: {filter: 'blur(0.6px)'},
  'will-change': {willChange: 'transform'},
};

export const DURATION = 120;

export const CameraTypeProbe: React.FC<{move?: CameraMove; amount?: number; pan?: [number, number];
  bare?: boolean; text?: string; legacy?: boolean; typeGlide?: boolean; layer?: ProbeLayer; inner?: boolean;
  drive?: 'camera' | 'transform' | 'layout' | 'inner'}> = ({
  move = 'push', amount, pan, bare = false, text = 'Type rides the camera 字随镜头走', legacy = false,
  typeGlide = false, layer = 'none', inner = false, drive = 'camera'}) => {
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const x = Math.round(W * 0.08), y = Math.round(CONTENT_TOP + H * 0.06), px = Math.round(U * 0.04);
  if (!(layer in LAYER_STYLE)) throw new Error(`CameraTypeProbe: unknown layer ${JSON.stringify(layer)}`);
  // `drive` other than the camera: the type and its rule move by themselves, 30px down across the probe at a
  // crawl — by a translate in their own element's transform (`transform`), or by their LAYOUT position, `top`
  // changing every frame, with the unlock written as the element's own transform (`layout`). The two are the two
  // ways a register moves a label, and only one of them is cured by a skew on the moving element.
  const frame = useCurrentFrame();
  const crawl = Math.min(1, Math.max(0, (frame - 10) / 100)) * 30;
  const own = drive === 'camera' || legacy ? undefined : BASELINE_UNLOCK;
  if (drive !== 'camera') {
    const ty = drive === 'transform' ? crawl : 0, dy = drive !== 'transform' ? crawl : 0;
    // `inner`: the unlock sits on a STILL wrapper and the type moves by layout inside it
    const tf = drive === 'transform' ? `translateY(${ty}px)${own ? ' ' + own : ''}` : drive === 'layout' ? own : undefined;
    return (
      <AbsoluteFill style={{background: '#ffffff', transform: drive === 'inner' ? own : undefined}}>
        <div style={{position: 'absolute', left: x, top: y + dy, color: '#000000', whiteSpace: 'nowrap',
          font: `700 ${px}px/1.2 Inter, "Noto Sans SC", sans-serif`, transform: tf}}>{text}</div>
        <div style={{position: 'absolute', left: x, top: y + dy + Math.round(px * 1.6), width: Math.round(W * 0.34),
          height: 3, background: '#ff0000', transform: drive === 'transform' ? `translateY(${ty}px)` : undefined}} />
        {typeGlide ? <TypeGlideAudit /> : null}
      </AbsoluteFill>
    );
  }
  const page = (
    <AbsoluteFill style={{background: '#ffffff'}}>
      <AbsoluteFill style={LAYER_STYLE[layer]}>
        <AbsoluteFill style={{transform: inner && !legacy ? BASELINE_UNLOCK : undefined}}>
          <div style={{position: 'absolute', left: x, top: y, color: '#000000', whiteSpace: 'nowrap',
            font: `700 ${px}px/1.2 Inter, "Noto Sans SC", sans-serif`}}>{text}</div>
          <div style={{position: 'absolute', left: x, top: y + Math.round(px * 1.6), width: Math.round(W * 0.34),
            height: 3, background: '#ff0000'}} />
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
  return (
    <AbsoluteFill style={{background: '#ffff00'}}>
      <BaselineUnlockContext.Provider value={!legacy}>
        {bare ? page : <SceneCamera move={move} amount={amount} pan={pan}>{page}</SceneCamera>}
      </BaselineUnlockContext.Provider>
      {typeGlide ? <TypeGlideAudit /> : null}
    </AbsoluteFill>
  );
};
