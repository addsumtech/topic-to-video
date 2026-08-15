// FILM · data-driven — sequences any list of bespoke shots into a narrated film. Each SCENE names a `shot`
// (looked up in REGISTRY), its topic `props`, a frame-length `durF`, an optional narration `mp3` (served from
// public/) and a `caption`. Scenes CROSS-DISSOLVE (overlapping ~0.4s to ride the narration breath). Captions
// ride a SINGLE top-level HUD track (a #hud sibling, per huashu's camera-rig discipline) that HARD-CUTS one
// caption at a time inside each scene's sole-visible window — so two captions can never overlap across a
// transition (the old A1 doubling bug) — and picks its ink CONTRAST against the scene's ground luminance.
// render_remotion.py drives this via --props; the WorkBuddy film is just the default. Deterministic.

import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import type {TransitionPresentation} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {dissolve} from '@remotion/transitions/dissolve';
import {SceneDurationContext, clamp01} from './runtime/motion';
import {groundLum, type Lum} from './runtime/shotLuma';
import {REGISTRY} from './registry';
import {CAPTIONS} from './captions';

// The scene EDL. `bgLum` is the first of the shot-director-emitted continuity fields (an explicit ground-
// luminance override; falls back to the measured shotLuma map). Future phases grow this schema (accent,
// camera{}, carry{}, transitionIn{}, audioCues[]) — all OPTIONAL + remotion-only, so the html tier is untouched.
export type SceneSpec = {shot: string; props?: Record<string, unknown>; durF: number; mp3?: string;
  caption?: string; bgLum?: Lum;
  // A MARKED seam (chapter break): the transition INTO this scene from the previous one. Optional +
  // remotion-only; unset = the luminance-safe default (a gentle cross-fade). A kinetic type is honored only
  // on a same/near-luminance seam — across a dark↔light gap it's suppressed back to fade (see pickPresentation).
  transitionIn?: {type: 'fade' | 'slide' | 'wipe' | 'clock' | 'dissolve' | 'carry'; direction?: string}};

const TR = 12; // cross-dissolve length (frames) — rides the ~0.42s narration breath so speech barely overlaps
export const filmDuration = (scenes: SceneSpec[]) =>
  Math.max(1, scenes.reduce((a, s) => a + Math.max(1, Math.round(s.durF)), 0) - Math.max(0, scenes.length - 1) * TR);

// The WorkBuddy film as DATA (the default) — 14 beats, families varied per LIBRARY.md; ChartLive shows the
// FAITHFUL sourced 68× Hy3 surge (never the shot's demo number).
const WB_SEC = [9.3, 9.075, 9.224, 11.495, 12.632, 10.538, 9.0, 10.41, 10.692, 15.363, 14.738, 11.311, 10.314, 4.624];
const WB_SHOTS = ['ChatThread', 'CinematicTitle', 'ExplodedSchematic', 'CollaborativeCursors', 'KnowledgeGraph',
  'BlockAssembly', 'BlueprintGrid', 'FocalIsolation', 'MapRoutes', 'MaterialHero', 'ParticleForm', 'ChartLive', 'HandDrawn', 'LiquidChrome'];
const WB_PROPS: Record<number, Record<string, unknown>> = {11: {endVal: 68, unit: '×', label: 'Hy3 call volume · first week'}};
// The ~3 MARKED seams (the rest ride the luminance-safe default fade) — each on a same-luminance boundary so
// the kinetic move can't flash, and each motivated by the two beats' relationship, never decoration:
const WB_TRANS: Record<number, NonNullable<SceneSpec['transitionIn']>> = {
  2: {type: 'clock'},                            // CinematicTitle → ExplodedSchematic: the title OPENS the mechanism
  9: {type: 'slide', direction: 'from-right'},   // MapRoutes → MaterialHero: the routes push forward into the hero
  10: {type: 'dissolve'},                         // MaterialHero → ParticleForm: the solid hero DISSOLVES to particles
  12: {type: 'carry'},                            // ChartLive → HandDrawn: the data COLLAPSES to a line, the human takeaway grows from it (crosses dark→light)
};
// The default preview is SILENT (no demo audio ships with the skill) — a real film's per-scene narration is
// supplied by render_remotion.py from the out_dir (`sc.mp3`), served via --public-dir.
export const WORKBUDDY_SCENES: SceneSpec[] = WB_SHOTS.map((shot, i) => ({
  shot, props: WB_PROPS[i] ?? {}, durF: Math.round(WB_SEC[i] * 30), caption: CAPTIONS[i], transitionIn: WB_TRANS[i],
}));

const splitCaption = (text: string): string[] => {
  const chunks = text.match(/[^.!?—]+[.!?]?(\s*—)?/g)?.map((c) => c.trim()).filter(Boolean) ?? [text];
  const merged: string[] = [];
  for (const c of chunks) {
    if (merged.length && (merged[merged.length - 1].length < 22 || c.length < 22)) merged[merged.length - 1] += ' ' + c;
    else merged.push(c);
  }
  return merged;
};

const CAP_PAD = 4;   // clean-gap frames inside each scene's sole-visible window → guarantees exit-before-enter
const CAP_FADE = 3;  // tiny in/out ramp WITHIN the window (never across a transition, so captions never double)

// One global caption HUD. It shows AT MOST ONE caption — the one belonging to the scene whose sole-visible
// window (between its two transitions) contains this frame — hard-cut, contrast-picked against that scene's
// ground luminance. Because the windows are disjoint, two captions can never coexist across a dissolve.
const CaptionTrack: React.FC<{scenes: SceneSpec[]}> = ({scenes}) => {
  const frame = useCurrentFrame();
  let acc = 0;
  const starts = scenes.map((sc) => { const s = acc; acc += Math.max(1, Math.round(sc.durF)) - TR; return s; });
  let active = -1, ws = 0, we = 0;
  for (let i = 0; i < scenes.length; i++) {
    const dur = Math.max(1, Math.round(scenes[i].durF));
    const a = starts[i] + (i > 0 ? TR : 14) + CAP_PAD;                       // clear the transition-in / intro
    const b = starts[i] + dur - (i < scenes.length - 1 ? TR : 16) - CAP_PAD; // clear the transition-out / outro
    if (frame >= a && frame <= b) { active = i; ws = a; we = b; break; }
  }
  const sc = active >= 0 ? scenes[active] : undefined;
  if (!sc || !sc.caption) return null;
  const merged = splitCaption(sc.caption);
  const local = clamp01((frame - ws) / Math.max(1, we - ws));
  const idx = Math.min(merged.length - 1, Math.floor(local * merged.length));
  const op = Math.min(clamp01((frame - ws) / CAP_FADE), clamp01((we - frame) / CAP_FADE));
  const lum = groundLum(sc.shot, sc.bgLum);
  const ink = lum === 'light' ? '#141414' : '#ffffff';
  const scrim = lum === 'light' ? 'linear-gradient(#0000, #f4f1eae0)' : 'linear-gradient(#0000, #00000099)';
  const shadow = lum === 'light' ? '0 1px 8px #ffffffe0, 0 0 2px #fff' : '0 2px 10px #000c, 0 0 2px #000';
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none', opacity: op}}>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 240, background: scrim}} />
      <div style={{position: 'relative', maxWidth: 1500, margin: '0 auto 62px', padding: '0 60px', textAlign: 'center',
        color: ink, font: '700 46px/1.28 Inter, system-ui, sans-serif', letterSpacing: '-0.01em',
        textShadow: shadow}}>{merged[idx]}</div>
    </AbsoluteFill>
  );
};

// CARRY (a collapse-to-line match-cut) — the one transition that reads as CONTINUITY, not a swap. The exiting
// scene collapses vertically into a thin neutral line at center; the incoming scene expands back out from that
// same line. The eye tracks the shared line across the cut, so two unrelated shots read as one continuous move
// (huashu's collapse-to-line). Because the bridge line is a MID-neutral, it doubles as the luminance dip — this
// is the only marked transition allowed to cross a dark↔light gap (its bright line IS the through-gray moment,
// by design, not an accidental flash). Deterministic (pure fn of presentationProgress); works for ANY pair.
const CarryPresentation = ({presentationProgress: p, presentationDirection, children, passedProps}: any) => {
  const line = (passedProps && passedProps.line) || '#9aa0aa';
  const isEnter = presentationDirection === 'entering';
  const ease = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const, easing: Easing.inOut(Easing.cubic)};
  const scaleY = isEnter ? interpolate(p, [0.5, 1], [0.006, 1], ease) : interpolate(p, [0, 0.5], [1, 0.006], ease);
  const clampBoth = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  const op = isEnter ? interpolate(p, [0.46, 0.56], [0, 1], clampBoth) : interpolate(p, [0.44, 0.54], [1, 0], clampBoth);
  const lineOp = interpolate(p, [0.15, 0.5, 0.85], [0, 1, 0], clampBoth);
  return (
    <>
      <AbsoluteFill style={{transform: `scaleY(${scaleY})`, transformOrigin: 'center', opacity: op}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: 2, marginTop: -1,
          background: line, opacity: lineOp, boxShadow: `0 0 18px 3px ${line}`}} />
      </AbsoluteFill>
    </>
  );
};
const carry = (line?: string): TransitionPresentation<any> => ({component: CarryPresentation, props: {line}});

const LUM_RANK: Record<Lum, number> = {dark: 0, mid: 1, light: 2};

// The seam GRAMMAR. A seam is luminance-SAFE by default and SEMANTIC when marked. A ground-luminance gap of
// ≥2 (a dark↔light cut) FORCES a gentle cross-fade — it blends through mid-gray so there's no brightness
// flash, and a hard kinetic edge (a bright scene sliding over a dark one) is exactly what we suppress there.
// On a same/near-luminance seam the EDL may MARK a kinetic move (slide/wipe/clock/dissolve) for a chapter
// break; unmarked seams stay a fade. Every seam holds at TR frames so it rides the audio-breath silence
// (A/V stays in sync); no spins, ever. Deterministic — pure fn of the two scenes' declared ground.
const pickPresentation = (prev: SceneSpec, next: SceneSpec, W: number, H: number): TransitionPresentation<any> => {
  const dLum = Math.abs(LUM_RANK[groundLum(next.shot, next.bgLum)] - LUM_RANK[groundLum(prev.shot, prev.bgLum)]);
  const want = next.transitionIn?.type ?? 'fade';
  // luminance guard: a dark↔light gap forces the gentle fade — EXCEPT carry, whose neutral bridge line IS the dip.
  const t = (dLum >= 2 && want !== 'carry') ? 'fade' : want;
  const dir = next.transitionIn?.direction;
  switch (t) {
    case 'slide': return slide({direction: (dir as any) ?? 'from-right'});
    case 'wipe': return wipe({direction: (dir as any) ?? 'from-bottom'});
    case 'clock': return clockWipe({width: W, height: H});
    case 'dissolve': return dissolve();
    case 'carry': return carry();
    default: return fade();
  }
};

// #camera — a subtle whole-film DRIFT (a slow breathing zoom + float) applied to the WORLD only; the HUD
// (captions + the intro/outro veil) stays OUTSIDE it, immune (huashu's camera-rig discipline). Low amplitude
// over a generous overscan (min scale ~1.025) so a pan can never reveal an edge; deterministic (pure fn of
// frame, sin never Math.random). amp scales with meta.motion_personality; amp 0 disables (reduced-motion).
const TWO_PI = Math.PI * 2;
const cameraTransform = (frame: number, amp: number): string => {
  if (amp <= 0) return 'none';
  const s = 1 + amp * (0.035 + 0.010 * Math.sin((frame / 720) * TWO_PI));     // breathe, ~24s period
  const x = amp * 6 * Math.sin((frame / 930) * TWO_PI + 1.3);                  // float — offset periods so it never repeats
  const y = amp * 4 * Math.sin((frame / 810) * TWO_PI + 0.4);
  return `scale(${s.toFixed(5)}) translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
};

// visible fallback if a storyboard names an unknown shot id (fail loud, never a silent blank)
const Missing: React.FC<{id: string}> = ({id}) => (
  <AbsoluteFill style={{background: '#2a0a0a', alignItems: 'center', justifyContent: 'center',
    color: '#ff8a8a', font: '700 44px/1.4 monospace', textAlign: 'center'}}>unknown shot:<br />{id}</AbsoluteFill>
);

export const Film: React.FC<{scenes?: SceneSpec[]; camera?: number; reducedMotion?: boolean}> =
  ({scenes = WORKBUDDY_SCENES, camera = 1, reducedMotion = false}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const total = filmDuration(scenes);
  const cam = cameraTransform(frame, reducedMotion ? 0 : Math.max(0, camera));
  const intro = interpolate(frame, [0, 12], [1, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const outro = interpolate(frame, [total - 16, total - 1], [0, 1], {extrapolateLeft: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <AbsoluteFill style={{transform: cam}}>
      <TransitionSeries>
        {scenes.flatMap((sc, i) => {
          const C = REGISTRY[sc.shot];
          const durF = Math.max(1, Math.round(sc.durF));
          const seq = (
            <TransitionSeries.Sequence key={`s${i}`} durationInFrames={durF}>
              <SceneDurationContext.Provider value={durF}>
                <AbsoluteFill>{C ? <C {...(sc.props ?? {})} /> : <Missing id={sc.shot} />}</AbsoluteFill>
              </SceneDurationContext.Provider>
              {sc.mp3 ? <Audio src={staticFile(sc.mp3)} /> : null}
            </TransitionSeries.Sequence>
          );
          if (i === scenes.length - 1) return [seq];
          return [seq, (
            <TransitionSeries.Transition key={`t${i}`}
              presentation={pickPresentation(sc, scenes[i + 1], width, height)}
              timing={linearTiming({durationInFrames: TR})} />
          )];
        })}
      </TransitionSeries>
      </AbsoluteFill>
      <AbsoluteFill style={{backgroundColor: '#05060a', opacity: Math.max(intro, outro), pointerEvents: 'none'}} />
      <CaptionTrack scenes={scenes} />
    </AbsoluteFill>
  );
};
export default Film;
