// THE CONTINUOUS STAGE — one scene across several beats (SKILL.md "Continuous stage").
//
// A beat on its own is a register mounted inside its own Sequence with its own clock (`useT`), and nothing it draws
// survives the cut to the next beat. A STAGE RUN is consecutive beats that name the same `stage.run`: Film.tsx gives
// them ONE Sequence with no seam between them, and ONE stage component draws the whole run. Its actors (a card, a
// device, a document) keep their identity across the beats and move from each beat's state to the next.
//
// THE MODEL IS KEYFRAMES, NOT HISTORY. Each beat states where the actors should BE (its `shot_props`); the stage at any
// frame is a pure function of that list and the frame. That is what lets the per-beat segment render keep working —
// any frame range renders the same pixels it would inside a whole render — and what keeps a run deterministic.
//
// Imported only by Film.tsx and the stage components (remotion/src/stage/), never by a library register, so no
// register's measured manifest re-keys when this file changes.
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp01, easeInOutCubic, ReducedMotionContext} from './motion';

export type StageBeat = {
  index: number;                       // the beat's position in the film (0-based)
  start: number;                       // its first frame inside the run
  durF: number;                        // its length in frames
  props: Record<string, unknown>;      // its shot_props: the state the actors reach in this beat
  cues?: Record<string, number>;       // per-item cue seconds (inside the beat), when the renderer attached them
  caption?: string;
};
export type StageRunValue = {run: string; beats: StageBeat[]; runDur: number};

export const StageRunContext = React.createContext<StageRunValue | null>(null);

/** How long a beat takes to move the actors from the previous beat's state into its own: 0.8 s, never more than
 *  40% of the beat — the rest of the beat is the state HELD (and alive), which is what the voice is talking over. */
export const morphFrames = (durF: number, fps: number) => Math.max(1, Math.round(Math.min(durF * 0.4, fps * 0.8)));

export type StageNow = {
  frame: number; fps: number; runDur: number; beats: StageBeat[];
  k: number;            // which beat of the run is on screen
  beat: StageBeat;
  local: number;        // frames since that beat began
  t: number;            // 0..1 through that beat
  morph: number;        // 0..1 progress of the move into this beat's state (1 = arrived, and under reduced motion)
  reduced: boolean;
};

/** Where the run is at the current frame. Throws outside a stage run: a stage component rendered alone has no run. */
export const useStageRun = (): StageNow => {
  const ctx = React.useContext(StageRunContext);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reduced = React.useContext(ReducedMotionContext);
  if (!ctx || !ctx.beats.length) {
    throw new Error('a stage component was rendered outside a stage run — it draws several beats at once and needs ' +
      'the run Film.tsx builds from `stage.run` on consecutive beats');
  }
  let k = ctx.beats.findIndex((b) => frame < b.start + b.durF);
  if (k < 0) k = ctx.beats.length - 1;
  const beat = ctx.beats[k];
  const local = Math.max(0, frame - beat.start);
  const morph = reduced || k === 0 ? 1 : easeInOutCubic(clamp01(local / morphFrames(beat.durF, fps)));
  return {frame, fps, runDur: ctx.runDur, beats: ctx.beats, k, beat, local,
    t: clamp01(local / Math.max(1, beat.durF - 1)), morph, reduced};
};

/** One value in the middle of a move. Numbers interpolate; anything else switches at the halfway point; a key only
 *  one side has is taken from that side; arrays interpolate element by element when their lengths agree. */
export const lerpState = (a: unknown, b: unknown, p: number): unknown => {
  if (a === undefined) return b;
  if (b === undefined) return a;
  if (typeof a === 'number' && typeof b === 'number') return a + (b - a) * p;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return p < 0.5 ? a : b;
    return a.map((x, i) => lerpState(x, b[i], p));
  }
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    const out: Record<string, unknown> = {};
    for (const key of new Set([...Object.keys(a as object), ...Object.keys(b as object)])) {
      out[key] = lerpState((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key], p);
    }
    return out;
  }
  return p < 0.5 ? a : b;
};

/** The state of one actor right now: the value `pick` reads from each beat's props, carried forward from the last
 *  beat that set it (a beat that says nothing about an actor leaves it where it was), and moved into the current
 *  beat's value over the beat's morph window. */
export const useActorState = <T,>(pick: (props: Record<string, unknown>) => T | undefined, fallback: T): T => {
  const now = useStageRun();
  const held = (upTo: number): T => {
    for (let i = upTo; i >= 0; i--) {
      const v = pick(now.beats[i].props);
      if (v !== undefined) return v;
    }
    return fallback;
  };
  const target = held(now.k);
  if (now.k === 0 || now.morph >= 1) return target;
  return lerpState(held(now.k - 1), target, now.morph) as T;
};
