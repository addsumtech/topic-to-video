// Probe: does type on a 3D SCREEN ride its camera as smoothly as the drawing it sits on?
//
// The failure this exists for: a delivered film's product shot (a Mac display leaning back in a dark room, its
// panel redrawn as DOM inside a 3D `Surface`, a keyframed camera panning and pushing across the panel) had every
// gate green — the type-glide census lists type inside a 3D layer and never judges it — and the viewer saw the
// type tremble (字体抖动). This probe draws the same structure and nothing else, so each way of building such a
// screen can be MEASURED from the pixels (scripts/jitter_qa.py --probe).
//
// `content` is how the panel is laid out under the camera:
//   layout     what the shot did: every position and every font size recomputed per frame from the view
//              (`left: x*k - offset`, `font-size: size*k`) — the panel re-laid out, at a new size, every frame
//   transform  the panel laid out ONCE at its own design size; the view is one transform on its wrapper
//   surface    `<SurfaceView>` (runtime/surfaceView.tsx): the transform, carrying the baseline unlock
//   layer      the transform on its own compositing layer (will-change): the GPU moves one raster
//   raster     laid out ONCE at the largest size the move reaches (K), moved by a 3D transform at k/K <= 1: its own
//              layer, rasterised at a fixed size and resampled by the GPU — `rasterWill` adds will-change
//   surfaceRaster  the same through `<SurfaceView raster>` (its `zoom` layout in place of multiplied units)
// `move` is what the camera does: a slow vertical `pan` over the panel, a slow `push` (the view narrowing), the
// screen's own `sway` with the view held, the `pull` back out of a screen that fills the frame, or `still`.
// `flat` draws the same screen with no 3D at all — the control that says what the 3D layer itself adds.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Stage3D, Surface, PERSP_FRAC, type Pose} from './stage3d';
import {SurfaceView} from './surfaceView';
import {TypeGlideAudit} from './textSafe';

export const DURATION = 120;
export type SlabContent = 'layout' | 'transform' | 'surface' | 'layer' | 'raster' | 'rasterWill' | 'surfaceRaster';
export type SlabMove = 'pan' | 'push' | 'sway' | 'pull' | 'still';

// the panel's own units (the slab's view is a window onto these)
const SW = 1000, SH = 486;
const ROWS = ['当前会话 Session 92%', '每周限制 · 所有模型 79%', 'Spark 5h 2h 00m 18%', 'DeepSeek · API ¥8.85',
  'Token 消耗 24h · 47M tok', '额度重置 2 次可用'];
const FONT = 'Inter, "Noto Sans SC", sans-serif';

const ease = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

/** The panel at scale k: every position and size multiplied out — the per-frame re-layout the shot did. */
const LaidOut: React.FC<{k: number}> = ({k}) => (
  <>
    {ROWS.map((r, i) => (
      <div key={i} style={{position: 'absolute', left: 120 * k, top: (60 + i * 46) * k, whiteSpace: 'nowrap',
        font: `700 ${16 * k}px/1.2 ${FONT}`, color: '#f2f3f5'}}>{r}</div>
    ))}
    <div style={{position: 'absolute', left: 120 * k, top: 340 * k, width: 600 * k, height: 3 * k, background: '#ff3030'}} />
  </>
);

/** The same panel at its own design size, for a transform to place. */
const Design: React.FC = () => <LaidOut k={1} />;

export const SlabTypeProbe: React.FC<{content?: SlabContent; move?: SlabMove; flat?: boolean; typeGlide?: boolean}> = ({
  content = 'layout', move = 'pan', flat = false, typeGlide = false}) => {
  const {width: W, height: H} = useVideoConfig();
  const f = useCurrentFrame();
  const U = Math.min(W, H);
  if (!['layout', 'transform', 'surface', 'layer', 'raster', 'rasterWill', 'surfaceRaster'].includes(content)) throw new Error(`SlabTypeProbe: content ${content}`);
  if (!['pan', 'push', 'sway', 'pull', 'still'].includes(move)) throw new Error(`SlabTypeProbe: move ${move}`);
  const p = ease((f - 10) / 100);
  // the view: [left, top] in panel units and its width; its height follows the face
  const faceW = Math.round(W * 0.62), faceH = Math.round(faceW * 0.42);
  const bez = Math.round(U * 0.012), innerW = faceW - 2 * bez, innerH = faceH - 2 * bez;
  let vw = 0.5, vx = 0.08, vy = 0.06;
  if (move === 'pan') vy = 0.06 + 0.07 * p;                         // ~0.6px a frame of a crawl, vertically
  if (move === 'push') { vw = 0.56 - 0.08 * p; vx = 0.08 + 0.02 * p; vy = 0.06 + 0.02 * p; }
  const k = innerW / (vw * SW);
  const ox = -vx * SW * k, oy = -vy * SH * k;
  const swayT = move === 'still' ? 0 : f / 30;
  const sway = move === 'sway' || move === 'pan' || move === 'push' || move === 'pull' ? Math.sin(swayT * 0.9) : 0;
  const pose: Pose = {rx: 9 + 1.2 * sway, ry: 2.0 * Math.sin(swayT * 0.7 + 1)};
  const stageScale = move === 'pull' ? 2.2 + (1 - 2.2) * p : 1;

  // the largest scale the view reaches over the move: the size the `raster` panel is laid out at once
  const kMax = innerW / ((move === 'push' ? 0.48 : 0.5) * SW);
  const panel = content === 'raster' || content === 'rasterWill' ? (
    <div style={{position: 'absolute', left: 0, top: 0, width: SW * kMax, height: SH * kMax, transformOrigin: '0 0',
      transform: `matrix3d(${k / kMax},0,0,0,0,${k / kMax},0,0,0,0,1,0,${ox},${oy},0,1)`,
      willChange: content === 'rasterWill' ? 'transform' : undefined}}><LaidOut k={kMax} /></div>
  ) : content === 'surfaceRaster' ? (
    <SurfaceView w={SW} h={SH} k={k} x={ox} y={oy} raster={kMax}><Design /></SurfaceView>
  ) : content === 'layout' ? (
    <div style={{position: 'absolute', left: ox, top: oy, width: SW * k, height: SH * k}}><LaidOut k={k} /></div>
  ) : content === 'transform' || content === 'layer' ? (
    <div style={{position: 'absolute', left: 0, top: 0, width: SW, height: SH, transformOrigin: '0 0',
      transform: `matrix(${k}, 0, 0, ${k}, ${ox}, ${oy})`, willChange: content === 'layer' ? 'transform' : undefined}}><Design /></div>
  ) : (
    <SurfaceView w={SW} h={SH} k={k} x={ox} y={oy} still={move === 'still'}><Design /></SurfaceView>
  );
  const face = (
    <div style={{position: 'absolute', inset: 0, borderRadius: 16, background: '#000', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: bez, top: bez, width: innerW, height: innerH, overflow: 'hidden',
        background: '#0b0b0e'}}>{panel}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{background: '#202230', overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transformOrigin: `${W / 2}px ${H / 2}px`,
        transform: stageScale !== 1 ? `scale(${stageScale})` : undefined}}>
        {flat ? (
          <div style={{position: 'absolute', left: (W - faceW) / 2, top: (H - faceH) / 2, width: faceW, height: faceH}}>{face}</div>
        ) : (
          <Stage3D persp={Math.round(U * PERSP_FRAC)}>
            <Surface pose={pose} w={faceW} h={faceH} style={{borderRadius: 16}}>{face}</Surface>
          </Stage3D>
        )}
      </div>
      {typeGlide ? <TypeGlideAudit /> : null}
    </AbsoluteFill>
  );
};
