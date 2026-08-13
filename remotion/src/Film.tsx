// FILM · data-driven — sequences any list of bespoke shots into a narrated film. Each SCENE names a `shot`
// (looked up in REGISTRY), its topic `props`, a frame-length `durF`, an optional narration `mp3` (served from
// public/) and a `caption`. Scenes CROSS-DISSOLVE (overlapping ~0.4s to ride the narration breath); captions
// are scene-relative sentence chunks that edge-fade so they never collide. render_remotion.py drives this via
// --props; the WorkBuddy film is just the default. Deterministic (no Date.now/random).

import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, interpolate, Easing} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {SceneDurationContext, clamp01} from './runtime/motion';
import {REGISTRY} from './registry';
import {CAPTIONS} from './captions';

export type SceneSpec = {shot: string; props?: Record<string, unknown>; durF: number; mp3?: string; caption?: string};

const TR = 12; // cross-dissolve length (frames) — rides the ~0.42s narration breath so speech barely overlaps
export const filmDuration = (scenes: SceneSpec[]) =>
  Math.max(1, scenes.reduce((a, s) => a + Math.max(1, Math.round(s.durF)), 0) - Math.max(0, scenes.length - 1) * TR);

// The WorkBuddy film as DATA (the default) — 14 beats, families varied per LIBRARY.md; ChartLive shows the
// FAITHFUL sourced 68× Hy3 surge (never the shot's demo number).
const WB_SEC = [9.3, 9.075, 9.224, 11.495, 12.632, 10.538, 9.0, 10.41, 10.692, 15.363, 14.738, 11.311, 10.314, 4.624];
const WB_SHOTS = ['ChatThread', 'CinematicTitle', 'ExplodedSchematic', 'CollaborativeCursors', 'KnowledgeGraph',
  'BlockAssembly', 'BlueprintGrid', 'FocalIsolation', 'MapRoutes', 'MaterialHero', 'ParticleForm', 'ChartLive', 'HandDrawn', 'LiquidChrome'];
const WB_PROPS: Record<number, Record<string, unknown>> = {11: {endVal: 68, unit: '×', label: 'Hy3 call volume · first week'}};
// The default preview is SILENT (no demo audio ships with the skill) — a real film's per-scene narration is
// supplied by render_remotion.py from the out_dir (`sc.mp3`), served via --public-dir.
export const WORKBUDDY_SCENES: SceneSpec[] = WB_SHOTS.map((shot, i) => ({
  shot, props: WB_PROPS[i] ?? {}, durF: Math.round(WB_SEC[i] * 30), caption: CAPTIONS[i],
}));

const SceneCaption: React.FC<{text: string; dur: number}> = ({text, dur}) => {
  const frame = useCurrentFrame();
  const t = clamp01(frame / Math.max(1, dur - 1));
  const chunks = text.match(/[^.!?—]+[.!?]?(\s*—)?/g)?.map((c) => c.trim()).filter(Boolean) ?? [text];
  const merged: string[] = [];
  for (const c of chunks) {
    if (merged.length && (merged[merged.length - 1].length < 22 || c.length < 22)) merged[merged.length - 1] += ' ' + c;
    else merged.push(c);
  }
  const idx = Math.min(merged.length - 1, Math.floor(t * merged.length));
  const edge = Math.min(clamp01(frame / 10), clamp01((dur - frame) / 16));
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none', opacity: edge}}>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 240, background: 'linear-gradient(#0000, #00000099)'}} />
      <div style={{position: 'relative', maxWidth: 1500, margin: '0 auto 62px', padding: '0 60px', textAlign: 'center',
        color: '#ffffff', font: '700 46px/1.28 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        textShadow: '0 2px 10px #000c, 0 0 2px #000'}}>{merged[idx]}</div>
    </AbsoluteFill>
  );
};

// visible fallback if a storyboard names an unknown shot id (fail loud, never a silent blank)
const Missing: React.FC<{id: string}> = ({id}) => (
  <AbsoluteFill style={{background: '#2a0a0a', alignItems: 'center', justifyContent: 'center',
    color: '#ff8a8a', font: '700 44px/1.4 monospace', textAlign: 'center'}}>unknown shot:<br />{id}</AbsoluteFill>
);

export const Film: React.FC<{scenes?: SceneSpec[]}> = ({scenes = WORKBUDDY_SCENES}) => {
  const frame = useCurrentFrame();
  const total = filmDuration(scenes);
  const intro = interpolate(frame, [0, 12], [1, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const outro = interpolate(frame, [total - 16, total - 1], [0, 1], {extrapolateLeft: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <TransitionSeries>
        {scenes.flatMap((sc, i) => {
          const C = REGISTRY[sc.shot];
          const durF = Math.max(1, Math.round(sc.durF));
          const seq = (
            <TransitionSeries.Sequence key={`s${i}`} durationInFrames={durF}>
              <SceneDurationContext.Provider value={durF}>
                <AbsoluteFill>{C ? <C {...(sc.props ?? {})} /> : <Missing id={sc.shot} />}</AbsoluteFill>
                {sc.caption ? <SceneCaption text={sc.caption} dur={durF} /> : null}
              </SceneDurationContext.Provider>
              {sc.mp3 ? <Audio src={staticFile(sc.mp3)} /> : null}
            </TransitionSeries.Sequence>
          );
          if (i === scenes.length - 1) return [seq];
          return [seq, (
            <TransitionSeries.Transition key={`t${i}`} presentation={fade()} timing={linearTiming({durationInFrames: TR})} />
          )];
        })}
      </TransitionSeries>
      <AbsoluteFill style={{backgroundColor: '#05060a', opacity: Math.max(intro, outro), pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default Film;
