// OBJECTS IN TEMPLATES — the contract between a register that has room for a thing and the film that draws the
// thing (scripts/workshop.py; docs/superpowers/specs/2026-09-27-adaptive-build-design.md §3).
//
// A register that can hold an object declares a prop typed `ObjectRef` and draws `<ObjectSlot object=… box=…>`
// where the object goes. The object is a component the FILM wrote in its workshop, or one promoted into
// remotion/src/objects/. It receives its box's size, a clock and the film's Design DNA — nothing else — so the
// same object can sit on a device's screen, on a stage, or in a plate's drawing field.
//
// WHY BY ID, THROUGH A CONTEXT. A register cannot import a film's object: the register is library code and the
// object lives in one film's folder. So objects are looked up by name in a map the Root provides (the library's
// objects and the film's workshop), and the lookup REFUSES what it cannot find — naming what does exist —
// instead of drawing nothing. A blank slot on a delivered frame is the failure this is written against.
//
// THIS FILE IS IN THE SOURCE HASH OF EVERY REGISTER THAT HOLDS AN OBJECT (scripts/register_energy._deps), so an
// edit here stales their measured rows. Change it only together with a re-measure of those registers.
import React from 'react';
import {useVideoConfig} from 'remotion';
import {useT, useAnimSpan, clamp01, ENTRY_T, ReducedMotionContext} from './motion';
import {useDNA, type DesignDNA} from './dna';

export type ObjectRef = {id: string; props?: Record<string, unknown>};

/** What every object is given. `t` runs 0 → 1 over the part of the beat its host gives it, then holds at 1;
 *  `yaw` (radians) is set only by a stage that turns its object (ObjectTurntable); `idle` is the IDLE CLOCK —
 *  seconds the object has been held since its host's reveal ended (see `idleSeconds`), 0 until then and 0
 *  whenever idle motion is off. An object with a natural cycle (water flowing, a precession turning) keeps that
 *  cycle going from it; an object with none ignores it. */
export type ObjectProps = {w: number; h: number; t: number; dna: DesignDNA | null; yaw?: number; idle?: number};

/** `aspect` — the width / height the object is drawn at; the slot fits that shape inside its box.
 *  `turns` — the object draws its own 3D turn from `yaw`; otherwise a turning stage turns its card.
 *  `demo` — a stage's own standalone preview, never a film's object (validate.py refuses it in a film).
 *  `provenance` — the idiom world the object's look comes from (shot_director.IDIOM_WORLDS).
 *  `idle: false` — a static diagram whose motion would misrepresent it: the slot always hands it `idle` 0. */
export type ObjectMeta = {aspect?: number; turns?: boolean; demo?: boolean; provenance?: string; idle?: boolean};
export type ObjectEntry = {C: React.FC<any>; meta?: ObjectMeta};
export type Rect = {x: number; y: number; w: number; h: number};

export const ObjectsContext = React.createContext<Record<string, ObjectEntry>>({});

/** What the slot gives every object. A film that sets one of them in `object.props` is refused rather than
 *  silently overruled — an ignored prop is a prop its author believes was drawn. */
export const SLOT_KEYS = ['w', 'h', 't', 'dna', 'yaw', 'idle'] as const;

// THE IDLE CLOCK. A stage register runs its object's `t` over a reveal window (ObjectStage: 0.06–0.6 of the beat)
// and then HOLDS it, so the words can name a settled thing — and from there to the cut the frame was frozen: on
// all four acceptance films the held tails measured ~0.0001 frame-diff, a still picture with a voice over it.
// `t` cannot simply keep running (an object maps 0 → 1 onto its reveal; past 1 means nothing), so the slot hands
// a SECOND clock: seconds since the host's hold began. Its rate eases up from rest over IDLE_RAMP_S and back down
// to rest before the beat's end, so a cycle starts and stops gliding — never a jolt where the hold begins, and
// still on the outgoing dissolve (useT holds t at 1 there, and idle is derived from t, so the seam stays still).
// It moves nothing but what the object draws from it: the box, the stage's words and its callouts do not move.
// Off (0) under reduced motion, on a beat whose storyboard sets `"object_idle": false` (ObjectIdleContext), for
// an object whose META says `idle: false`, and on a host that names no `idleFrom`.
export const IDLE_RAMP_S = 1;
export const ObjectIdleContext = React.createContext<boolean>(true);

/** Idle seconds at beat time `t` for a hold beginning at beat time `from`, on a beat whose `useT` spans
 *  `spanFrames` frames at `fps`. Continuous, 0 through `from`, with a zero rate at both ends of the hold and a
 *  rate of one second per second in between (two smoothstep ramps, integrated in closed form). */
export const idleSeconds = (t: number, from: number, spanFrames: number, fps: number): number => {
  if (!(Number.isFinite(t) && Number.isFinite(from) && from >= 0 && from < 1 && spanFrames > 0 && fps > 0)) return 0;
  const perT = spanFrames / ((1 - ENTRY_T) * fps);           // seconds per unit of beat t (useT's own mapping)
  const H = (1 - from) * perT;                               // the hold, in seconds
  const tau = clamp01((t - from) / (1 - from)) * H;
  const r = Math.min(IDLE_RAMP_S, H / 2);
  if (!(r > 0)) return 0;
  const ramp = (x: number) => { const u = clamp01(x / r); return r * (u * u * u - (u * u * u * u) / 2); };
  if (tau <= r) return ramp(tau);
  if (tau <= H - r) return r / 2 + (tau - r);
  return r / 2 + (H - 2 * r) + (r / 2 - ramp(H - tau));
};

/** The largest rect of `aspect` (width / height) centred in `box`. No aspect, or a nonsense one: the box. */
export const fitAspect = (box: Rect, aspect?: number): Rect => {
  if (!(typeof aspect === 'number' && Number.isFinite(aspect) && aspect > 0)) return box;
  const w = Math.min(box.w, box.h * aspect);
  const h = w / aspect;
  return {x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h};
};

/** The object's entry — or a refusal that says what was sent and which objects exist. */
export const resolveObject = (objects: Record<string, ObjectEntry>, ref: unknown): ObjectEntry => {
  const r = ref as ObjectRef | null;
  if (!r || typeof r !== 'object' || typeof r.id !== 'string' || !r.id.trim()) {
    throw new Error(`ObjectSlot: an object is {"id": "<Name>", "props": {...}} — got ${JSON.stringify(ref)}`);
  }
  // A ref is EXACTLY {id, props}. A stray top-level key (a film's own props put at the top instead of inside
  // "props") draws the object's defaults with no error — silently, because it is a shape the reader below
  // never looks at. Refused before the lookup, naming the keys and where they belong.
  const stray = Object.keys(r).filter((k) => k !== 'id' && k !== 'props');
  if (stray.length) {
    throw new Error(`ObjectSlot: "${r.id}" has ${stray.join(', ')} outside "props" — an object is exactly ` +
      '{"id": ..., "props": {...}}; its own props go inside "props", not beside "id".');
  }
  // `objects[r.id]` reads the PROTOTYPE CHAIN too: an id of "constructor" or "toString" resolves to
  // Object.prototype's own function, passes this check, and fails later inside React with a generic "element
  // type is invalid" that names nothing. hasOwnProperty (the same pattern shotLuma.ts's isRegisteredShot
  // uses) only ever matches a REAL entry.
  if (!Object.prototype.hasOwnProperty.call(objects, r.id)) {
    const known = Object.keys(objects).sort();
    throw new Error(`ObjectSlot: no object "${r.id}" — defined here: ${known.length ? known.join(', ') : '(none)'}. ` +
      `A film builds its own in <out_dir>/workshop/objects/${r.id}.tsx ` +
      `(python3 scripts/workshop.py <out_dir> new-object ${r.id} --means "...").`);
  }
  const e = objects[r.id];
  if (r.props != null && (typeof r.props !== 'object' || Array.isArray(r.props))) {
    throw new Error(`ObjectSlot: "${r.id}".props must be an object — got ${JSON.stringify(r.props)}`);
  }
  const clash = SLOT_KEYS.filter((k) => r.props != null && k in r.props);
  if (clash.length) {
    throw new Error(`ObjectSlot: "${r.id}".props sets ${clash.join(', ')}, which the slot gives every object ` +
      "(its box, its clock, the film's DNA) — remove them.");
  }
  // `key` and `ref` are JSX's own — React strips them off the props object before the component ever runs, so
  // an object author who wrote `props: {key: ...}` believing it would reach their component is silently wrong.
  const reactOwn = ['key', 'ref'].filter((k) => r.props != null && k in (r.props as Record<string, unknown>));
  if (reactOwn.length) {
    throw new Error(`ObjectSlot: "${r.id}".props sets ${reactOwn.join(', ')} — those are JSX's own, stripped ` +
      'before the object ever sees them; rename them.');
  }
  return e;
};

/** A host that needs the object's META before it lays out (its aspect, whether it turns) asks here. */
export const useObjectEntry = (ref: unknown): ObjectEntry => resolveObject(React.useContext(ObjectsContext), ref);

/** `idleFrom` — the beat time (0–1, on useT's clock) at which the host has finished moving this object: its
 *  reveal is over AND nothing else of the host's turns or carries it. From there the object's idle clock runs. */
export const ObjectSlot: React.FC<{object: ObjectRef; box: Rect; t?: number; yaw?: number; idleFrom?: number;
  style?: React.CSSProperties}> = ({object, box, t, yaw, idleFrom, style}) => {
  const objects = React.useContext(ObjectsContext);
  const beatT = useT();
  const span = useAnimSpan();
  const {fps} = useVideoConfig();
  const reduced = React.useContext(ReducedMotionContext);
  const idleOn = React.useContext(ObjectIdleContext);
  const dna = useDNA();
  const {C, meta} = resolveObject(objects, object);
  const idle = (idleFrom === undefined || reduced || !idleOn || meta?.idle === false) ? 0
    : idleSeconds(beatT, idleFrom, span, fps);
  // A NaN/Infinity coordinate draws a NaN rect (the object never appears — CSS silently treats it as auto);
  // a zero (or negative) w/h draws a 0×0 object — a blank slot either way, the exact failure this file's
  // header is written against. Checked here, not in fitAspect: fitAspect is a plain layout function other
  // hosts call for other purposes, and its own tests pin its behaviour on the boxes they pass it.
  if (!(Number.isFinite(box.x) && Number.isFinite(box.y) && Number.isFinite(box.w) && Number.isFinite(box.h)
        && box.w > 0 && box.h > 0)) {
    throw new Error(`ObjectSlot: "${object.id}"'s box is unusable — {x, y, w, h} must all be finite and w/h ` +
      `positive; got ${JSON.stringify(box)}. The host drawing this slot has a layout bug.`);
  }
  const r = fitAspect(box, meta?.aspect);
  return (
    <div data-object-slot={object.id}
      style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, ...style}}>
      <C {...(object.props ?? {})} w={r.w} h={r.h} t={t ?? beatT} dna={dna} yaw={yaw} idle={idle} />
    </div>
  );
};
