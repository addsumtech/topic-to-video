// THE CONTINUOUS STAGE — one scene across several beats (SKILL.md "Continuous stage").
//
// A beat on its own is a register mounted inside its own Sequence with its own clock (`useT`), and nothing it draws
// survives the cut to the next beat. A STAGE RUN is consecutive beats that name the same `stage.run`: Film.tsx gives
// them ONE Sequence with no seam between them, and ONE stage component draws the whole run. Its actors (a card, a
// cursor, a mark, the camera) keep their identity across the beats and move from each state to the next.
//
// THE MODEL IS KEYFRAMES, NOT HISTORY. Each beat's `shot_props` is a keyframe at the beat's start, and each of its
// `steps` is a keyframe inside the beat, timed to a phrase of the narration (render_remotion resolves a step's `at`
// into `t`, SECONDS into the beat). A keyframe says WHAT CHANGES — the state after it is the state before it with
// those values merged in (objects field by field, `null` removes) — and the stage at any frame is a pure function of
// that list and the frame. That is what lets the per-beat segment render keep working — any frame range renders the
// same pixels it would inside a whole render — and what keeps a run deterministic.
//
// WHEN A MOVE HAPPENS. A beat's keyframe moves in over the beat's first moments (`morphFrames`). A step's keyframe
// ARRIVES on its phrase: its move runs over the `move` seconds BEFORE it (0.45 s by default), so a click lands on the
// word that names it — and the click's sound (scripts/stage_runs.py `events`, read by sfx.py) lands with it.
//
// Imported only by Film.tsx and the stage components (remotion/src/stage/), never by a library register, so no
// register's measured manifest re-keys when this file changes.
import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp01, ReducedMotionContext} from './motion';

export type StageBeat = {
  index: number;                       // the beat's position in the film (0-based)
  start: number;                       // its first frame inside the run
  durF: number;                        // its length in frames
  props: Record<string, unknown>;      // its shot_props: what changes at its start, and its `steps`
  cues?: Record<string, number>;       // per-item cue seconds (inside the beat), when the renderer attached them
  caption?: string;
};
export type StageRunValue = {run: string; beats: StageBeat[]; runDur: number};

export const StageRunContext = React.createContext<StageRunValue | null>(null);

/** How long a beat takes to move the actors into its own state: 0.8 s, never more than 40% of the beat — the rest of
 *  the beat is the state HELD (and alive), which is what the voice is talking over. */
export const morphFrames = (durF: number, fps: number) => Math.max(1, Math.round(Math.min(durF * 0.4, fps * 0.8)));
/** How long a step's move takes by default, ending on its phrase. scripts/stage_runs.py mirrors it. */
export const STEP_MOVE_S = 0.45;

export type State = Record<string, unknown>;
const isObj = (v: unknown): v is State => !!v && typeof v === 'object' && !Array.isArray(v);

/** `a` with `b`'s changes: objects merge field by field, `null` removes a key, anything else replaces. */
export const mergeState = (a: State, b: State): State => {
  const out: State = {...a};
  for (const [k, v] of Object.entries(b)) {
    if (v === null) delete out[k];
    else if (isObj(v) && isObj(out[k])) out[k] = mergeState(out[k] as State, v);
    else out[k] = v;
  }
  return out;
};

export type StageKey = {
  beat: number;        // which beat of the run (0-based)
  step: number;        // -1 for the beat's own keyframe, else the index into its `steps`
  from: number;        // run frame the move into this keyframe starts
  to: number;          // run frame it arrives (a click lands here)
  props: State;        // what this keyframe changes
  state: State;        // the whole state once it has arrived
  begin: State;        // what is on screen when its move starts — the state before it, or, when the move before it
                       // has not arrived yet, that move part-way (so a step can start mid-move without a jump)
};

/** THE FEEL OF A MOVE (references/craft-research.md §1). Premium UI motion is FRONT-LOADED: Stripe's, Raycast's and
 *  Linear's curves are half way at 13-16% of a move; `easeInOutCubic`, which every move here used, is half way at 49% —
 *  slow out of the blocks, slow into the stop, the "robotic" read. A move's share at frame f of a d-frame move is a
 *  critically damped spring stretched to land on d: fast off the mark, no overshoot. */
export const moveShare = (f: number, d: number, fps: number): number =>
  d <= 0 || f >= d ? 1 : f <= 0 ? 0 : clamp01(spring({frame: f, fps, durationInFrames: d, config: {damping: 200}}));

const progress = (kf: {from: number; to: number}, f: number, fps: number) => moveShare(f - kf.from, kf.to - kf.from, fps);

/** Every keyframe of the run, in time order. A step arrives on its phrase even while the move before it is still
 *  under way: its own move then starts from where that move has got to and carries the rest of it along — pushing the
 *  step back until the move before it had arrived squeezed the step's own move into a frame, and the card jumped. A
 *  step with no resolved `t` throws: the renderer resolves every step, so a missing one is a broken board, not a
 *  stage to guess at. */
/** How a stage turns "the state so far, with this keyframe's change merged in" into the state after the keyframe —
 *  for a rule the plain merge cannot know (CardStage: a new face drops the card's held shape). */
export type Normalize = (merged: State, change: State) => State;

export const buildKeys = (beats: StageBeat[], fps: number, normalize?: Normalize): StageKey[] => {
  const apply = (st: State, change: State) => (normalize ? normalize(mergeState(st, change), change)
    : mergeState(st, change));
  const keys: StageKey[] = [];
  let state: State = {};
  beats.forEach((b, k) => {
    const {steps, ...own} = b.props as State & {steps?: unknown};
    const from = b.start;
    const to = k === 0 ? b.start : b.start + morphFrames(b.durF, fps);
    state = apply(state, own);
    keys.push({beat: k, step: -1, from, to, props: own, state, begin: state});
    (Array.isArray(steps) ? steps : []).forEach((raw, j) => {
      if (!isObj(raw)) throw new Error(`stage beat ${b.index + 1}: step ${j + 1} is not an object`);
      const {t, at: _at, move, ...change} = raw as State & {t?: unknown; move?: unknown};
      if (typeof t !== 'number' || !isFinite(t)) {
        throw new Error(`stage beat ${b.index + 1}: step ${j + 1} has no resolved time \`t\` — render_remotion ` +
          'resolves each step\'s `at` ({"cue": "<words>"} or 0..1 of the beat) into it');
      }
      const prevFrom = keys[keys.length - 1].from;
      const arrive = Math.min(b.start + b.durF - 1, Math.max(prevFrom + 1, b.start + Math.round(t * fps)));
      const want = Math.round((typeof move === 'number' && move > 0 ? move : STEP_MOVE_S) * fps);
      const dur = Math.max(1, Math.min(want, arrive - prevFrom));
      state = apply(state, change);
      keys.push({beat: k, step: j, from: arrive - dur, to: arrive, props: change, state, begin: state});
    });
  });
  for (let i = 1; i < keys.length; i++) {
    const pr = keys[i - 1];
    keys[i].begin = partWay(pr.begin, pr.state, progress(pr, keys[i].from, fps));
  }
  return keys;
};

/** What is on screen part-way through a move from `a` to `b`: shared values in between, what only `b` has already in,
 *  what only `a` has (an actor the move REMOVES) still there before the halfway point and gone after it — and `b`
 *  itself once the move is over. Interpolating with `lerpState`, which keeps a key only one side has, brought every
 *  removed actor back: the camera a beat had settled with `camera: null` returned at full zoom on each later step. */
const partWay = (a: State, b: State, q: number): State => {
  if (q >= 1) return b;
  const out: State = {};
  for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) {
    if (!(k in b)) {
      if (q < 0.5) out[k] = a[k];
    } else out[k] = k in a ? lerpState(a[k], b[k], q) : b[k];
  }
  return out;
};

export type StageNow = {
  frame: number; fps: number; runDur: number; beats: StageBeat[];
  k: number;            // which beat of the run is on screen
  beat: StageBeat;
  local: number;        // frames since that beat began
  t: number;            // 0..1 through that beat
  keys: StageKey[];
  ki: number;           // the keyframe moving in (or the last one arrived)
  before: State;        // what was on screen when it started (its `begin`)
  state: State;         // the state it moves to
  p: number;            // 0..1 eased progress of that move (1 = arrived, and under reduced motion)
  reduced: boolean;
};

/** Where the run is at the current frame. Throws outside a stage run: a stage component rendered alone has no run. */
export const useStageRun = (normalize?: Normalize): StageNow => {
  const ctx = React.useContext(StageRunContext);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reduced = React.useContext(ReducedMotionContext);
  if (!ctx || !ctx.beats.length) {
    throw new Error('a stage component was rendered outside a stage run — it draws several beats at once and needs ' +
      'the run Film.tsx builds from `stage.run` on consecutive beats');
  }
  const keys = React.useMemo(() => buildKeys(ctx.beats, fps, normalize), [ctx.beats, fps, normalize]);
  let k = ctx.beats.findIndex((b) => frame < b.start + b.durF);
  if (k < 0) k = ctx.beats.length - 1;
  const beat = ctx.beats[k];
  const local = Math.max(0, frame - beat.start);
  let ki = 0;
  for (let i = 0; i < keys.length; i++) if (keys[i].from <= frame) ki = i;
  const key = keys[ki];
  const p = reduced ? 1 : progress(key, frame, fps);
  return {frame, fps, runDur: ctx.runDur, beats: ctx.beats, k, beat, local,
    t: clamp01(local / Math.max(1, beat.durF - 1)), keys, ki, before: key.begin, state: key.state, p, reduced};
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

/** One actor right now: its value before the current move, carried into its value after it. */
export const actor = <T,>(now: StageNow, name: string): T | undefined =>
  (now.p >= 1 ? now.state[name] : lerpState(now.before[name], now.state[name], now.p)) as T | undefined;

/** The two spring feels a stage's SPATIAL actors move with. `settle`: a card coming to rest, ζ≈0.8, ~1.5% overshoot.
 *  `glide`: a camera, a cursor, a size — ζ≈1, no overshoot (Cap's camera spring is ζ≈0.94). */
const FEEL = {settle: {mass: 1, stiffness: 158, damping: 20}, glide: {mass: 1, stiffness: 158, damping: 26}};
export type Feel = keyof typeof FEEL;

type Num = number | {[k: string]: unknown};
/** acc moved by (b - a) * k, field by field; a field only `b` has is taken from `b` (it appears), a field that is not a
 *  number switches at the halfway point */
const addMove = (acc: unknown, a: unknown, b: unknown, k: number): unknown => {
  if (typeof acc === 'number' && typeof a === 'number' && typeof b === 'number') return acc + (b - a) * k;
  if (acc && a && b && typeof acc === 'object' && typeof a === 'object' && typeof b === 'object' && !Array.isArray(b)) {
    const out: Record<string, unknown> = {...(acc as Record<string, unknown>)};
    for (const key of Object.keys(b as object)) {
      const av = (a as Record<string, unknown>)[key], bv = (b as Record<string, unknown>)[key];
      out[key] = key in (acc as object) && av !== undefined ? addMove(out[key], av, bv, k) : bv;
    }
    return out;
  }
  return k >= 0.5 ? b : acc;
};

/** A SPATIAL actor right now, moved by springs that ADD UP: every keyframe adds its own change, sprung from its own
 *  start — x(t) = x0 + Σ (x_k − x_{k−1}) · s(t − t_k). A move that begins before the last one has landed carries its
 *  speed on instead of starting again from rest (a fresh ease per key dropped a 53 px/frame move to 1 px/frame at the
 *  retarget — the stall the eye reads as robotic). An actor that appears snaps to its first value (its entrance is
 *  the stage's to draw); one that leaves holds its last. `lead` frames: a step's change lands that much before the
 *  step does (a cursor settles before its click, a camera has leaned in by the time the click lands). Pure in the
 *  frame, so a segment renders the pixels a whole render does. */
export const springSum = <T extends Num>(now: StageNow, get: (s: State) => T | undefined,
  opts: {feel?: Feel; lead?: number; frame?: number} = {}): T | undefined => {
  const f = opts.frame ?? now.frame;
  const cfg = FEEL[opts.feel ?? 'glide'];
  let acc: unknown = undefined, prev: unknown = undefined;
  now.keys.forEach((kf, i) => {
    const v = get(kf.state);
    const lead = kf.step >= 0 ? Math.max(0, opts.lead ?? 0) : 0;
    const start = i === 0 ? -Infinity : kf.from - lead;
    if (v === undefined) { prev = undefined; return; }
    if (prev === undefined || acc === undefined) {
      if (f >= start) acc = JSON.parse(JSON.stringify(v));
      prev = v;
      return;
    }
    const d = Math.max(1, kf.to - kf.from);
    const k = now.reduced || f - start >= d ? 1 : f <= start ? 0
      : spring({frame: f - start, fps: now.fps, durationInFrames: d, config: cfg});
    if (k !== 0) acc = addMove(acc, prev, v, k);
    prev = v;
  });
  return acc as T | undefined;
};

/** Frames since the latest keyframe that has ARRIVED and whose own change satisfies `test` — the clock a one-off
 *  event (a click) plays on — with that keyframe's change; null when none has. */
export const sinceEvent = (now: StageNow, test: (props: State) => boolean): {f: number; props: State} | null => {
  for (let i = now.keys.length - 1; i >= 0; i--) {
    const kf = now.keys[i];
    if (kf.to <= now.frame && test(kf.props)) return {f: now.frame - kf.to, props: kf.props};
  }
  return null;
};
