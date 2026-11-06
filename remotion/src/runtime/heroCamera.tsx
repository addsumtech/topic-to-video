// HERO CAMERA — the showpiece grammar of a product film (spec 2026-11-06 F).
//
// WHY. Apple-style product films run three sections — the hero REVEAL, the DETAILS, the product in CONTEXT — with a
// slow, restrained camera (references/craft-bar.md). Our camera had push, pull and hold, and a push is a 2D ZOOM:
// everything grows at one rate, so it reads flat. A real dolly changes perspective — near things slide and grow more
// than far ones. Here a hero beat's layers declare a DEPTH (1 = the subject's plane, >1 behind it, <1 in front) and
// the move shifts and scales each by 1/depth:
//   reveal   the camera drifts in on a slow arc and comes to rest on the composed frame
//   macro    it moves close to the subject's plane; layers off that plane blur by their distance (depth of field)
//   context  it starts close and pulls back to the subject in its world
//
// TYPE NEVER RIDES IT. A label under a moving camera measured 0.16 px of tremble (jitter_qa ERROR on lone glyphs), so
// every move is done by HERO_SETTLE of the beat and labels stay at 0 until then (labelOpacity / useHeroLabel); after
// it nothing moves, so nothing can tremble.
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {SceneDurationContext, ReducedMotionContext} from './motion';

export const HERO_MOVES = ['reveal', 'macro', 'context'] as const;
export type HeroMove = typeof HERO_MOVES[number];
export type HeroLayerPose = {tx: number; ty: number; scale: number; blur: number};
export const HERO_SETTLE = 0.7;     // share of the beat by which every move has arrived
const LABEL_FADE = 0.08;           // share of the beat a label takes to come up once the move has settled
const MACRO_BLUR_PX = 10;          // blur at a layer one full 1/depth unit off the focus plane

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const ease = (u: number) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const z = (v: number) => (v === 0 ? 0 : v);

export const heroCamera = (move: HeroMove, t01: number, depths: number[]): HeroLayerPose[] => {
  if (!(HERO_MOVES as readonly string[]).includes(move)) {
    throw new Error(`heroCamera: unknown move ${JSON.stringify(move)} — ${HERO_MOVES.join(' | ')}`);
  }
  const e = ease(clamp01(t01 / HERO_SETTLE));
  return depths.map((d) => {
    if (!(d > 0)) throw new Error(`heroCamera: a layer's depth must be > 0, got ${d}`);
    const inv = 1 / d;
    if (move === 'reveal') {
      return {tx: z(-0.06 * (1 - e) * inv), ty: z(-0.015 * (1 - e) * inv), scale: 1 - 0.1 * (1 - e) * inv, blur: 0};
    }
    if (move === 'macro') {
      return {tx: 0, ty: 0, scale: 1 + 0.3 * e * inv, blur: Math.round(MACRO_BLUR_PX * e * Math.abs(inv - 1) * 10) / 10};
    }
    return {tx: 0, ty: 0, scale: 1 + 0.25 * (1 - e) * inv, blur: 0};
  });
};

export const labelOpacity = (move: HeroMove | null | undefined, t01: number, reduced = false): number =>
  move && !reduced ? clamp01((t01 - HERO_SETTLE) / LABEL_FADE) : 1;

/** One layer's pose; under reduced motion the frame is the composed, settled one at once — no move, no blur — as
 *  SceneCamera zeroes its own move (review I6). */
export const heroLayerPose = (move: HeroMove, t01: number, depth: number, reduced = false): HeroLayerPose =>
  reduced ? {tx: 0, ty: 0, scale: 1, blur: 0} : heroCamera(move, t01, [depth])[0];

export const HeroCameraContext = React.createContext<HeroMove | null>(null);

const useBeatT = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const dur = React.useContext(SceneDurationContext) ?? durationInFrames;
  return clamp01(frame / Math.max(1, dur));
};

/** A shot's layer at `depth` under the beat's hero move: a style to spread on its wrapper (identity on other beats).
 *  `origin` (shares of the frame) is the point the move closes in on — a macro goes TO the part it is about. */
export const useHeroLayer = (depth: number, origin: [number, number] = [0.5, 0.5]): React.CSSProperties => {
  const move = React.useContext(HeroCameraContext);
  const reduced = React.useContext(ReducedMotionContext);
  const t = useBeatT();
  const {width: W, height: H} = useVideoConfig();
  if (!move || reduced) return {};
  const p = heroLayerPose(move, t, depth);
  return {transform: `translate(${p.tx * W}px, ${p.ty * H}px) scale(${p.scale})`, transformOrigin: `${origin[0] * 100}% ${origin[1] * 100}%`,
    filter: p.blur ? `blur(${p.blur}px)` : undefined};
};

/** The opacity a label carries on this beat: 0 while a hero move is moving, 1 once it has settled. */
export const useHeroLabel = (): number =>
  labelOpacity(React.useContext(HeroCameraContext), useBeatT(), React.useContext(ReducedMotionContext));
