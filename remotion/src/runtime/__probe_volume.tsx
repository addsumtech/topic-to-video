// VOLUME PROBE — the frames tests/test_volume.py and scripts/determinism_qa.py render to hold runtime/volume.tsx to
// its two promises: every form is DETERMINISTIC (twice, concurrency 1 vs 3, frame N cold vs after N-1 predecessors in
// one tab), and every form actually DRAWS (switched off, the frame must change — a layer that renders nothing passes a
// determinism check trivially).
//
// `only` draws one form full frame (what the stills and the look are judged on); without it the five forms share the
// frame, each in its own cell, so ONE render covers them all — and so the shared GL context is exercised the way a
// film exercises it, several volumes drawn one after another into one context in one frame.
//
// `stateLeak: true` is the POSITIVE CONTROL: a module-level counter that every render of the probe bumps and feeds
// into every volume's seed, so a frame depends on how many frames its tab drew before it — the class of defect the
// harness is for. The test asserts determinism_qa FAILS it (cold and concurrency) and blames that layer.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Volume, VOLUME_FORMS, type VolumeForm, type VolumeSpec} from './volume';

export const DURATION = 90;
let LEAKED = 0;

export const VolumeProbe: React.FC<{only?: VolumeForm; layers?: Partial<Record<VolumeForm, boolean>>;
  stateLeak?: boolean; keepOut?: boolean; res?: number; intensity?: number; spec?: Partial<VolumeSpec>}> = ({only, layers,
  stateLeak, keepOut, res, intensity, spec: extra}) => {
  // read the frame, so this component re-renders on every frame like a register does — the counter below then counts
  // how many frames this tab drew before (without it the probe rendered once per mount, the counter was the same cold
  // or warm, and the control could not fail: measured, cold vs warm 0/255 with stateLeak on)
  useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  if (stateLeak) LEAKED += 1;
  const specOf = (form: VolumeForm): VolumeSpec => ({form, seed: 3 + (stateLeak ? LEAKED : 0),
    ...(form === 'shafts' ? {source: [0.8, -0.08], occluder: 'clouds', open: 0.5} : {}),
    ...(intensity ? {intensity} : {}), ...(extra ?? {})} as VolumeSpec);
  const title = {x: W * 0.07, y: H * 0.1, w: W * 0.36, h: H * 0.12};
  if (only) {
    return (
      <AbsoluteFill style={{background: '#04070d'}}>
        <Volume spec={specOf(only)} res={res ?? 0.75} keepOut={keepOut ? [title] : undefined} where="VolumeProbe" />
        {keepOut ? <div style={{position: 'absolute', left: title.x, top: title.y, width: title.w, height: title.h,
          color: '#ffffff', font: `700 ${Math.round(Math.min(W, H) * 0.07)}px/1.1 system-ui`}}>Keep</div> : null}
      </AbsoluteFill>
    );
  }
  const landscape = W >= H;
  const n = VOLUME_FORMS.length;
  const cell = (i: number) => landscape
    ? {x: (i % 3) * W / 3, y: Math.floor(i / 3) * H / 2, w: W / 3, h: H / 2}
    : {x: (i % 2) * W / 2, y: Math.floor(i / 2) * H / 3, w: W / 2, h: H / 3};
  return (
    <AbsoluteFill style={{background: '#04070d'}}>
      {VOLUME_FORMS.slice(0, n).map((form, i) => {
        if (layers?.[form] === false) return null;
        const c = cell(i);
        return (
          <div key={form} style={{position: 'absolute', left: c.x, top: c.y, width: c.w, height: c.h, overflow: 'hidden'}}>
            <Volume spec={specOf(form)} width={c.w} height={c.h} res={res ?? 0.5} where={`VolumeProbe ${form}`} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
