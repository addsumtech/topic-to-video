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
import {useT} from './motion';
import {useDNA, type DesignDNA} from './dna';

export type ObjectRef = {id: string; props?: Record<string, unknown>};

/** What every object is given. `t` runs 0 → 1 over the part of the beat its host gives it, then holds at 1;
 *  `yaw` (radians) is set only by a stage that turns its object (ObjectTurntable). */
export type ObjectProps = {w: number; h: number; t: number; dna: DesignDNA | null; yaw?: number};

/** `aspect` — the width / height the object is drawn at; the slot fits that shape inside its box.
 *  `turns` — the object draws its own 3D turn from `yaw`; otherwise a turning stage turns its card.
 *  `demo` — a stage's own standalone preview, never a film's object (validate.py refuses it in a film).
 *  `provenance` — the idiom world the object's look comes from (shot_director.IDIOM_WORLDS). */
export type ObjectMeta = {aspect?: number; turns?: boolean; demo?: boolean; provenance?: string};
export type ObjectEntry = {C: React.FC<any>; meta?: ObjectMeta};
export type Rect = {x: number; y: number; w: number; h: number};

export const ObjectsContext = React.createContext<Record<string, ObjectEntry>>({});

/** What the slot gives every object. A film that sets one of them in `object.props` is refused rather than
 *  silently overruled — an ignored prop is a prop its author believes was drawn. */
export const SLOT_KEYS = ['w', 'h', 't', 'dna', 'yaw'] as const;

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
  const e = objects[r.id];
  if (!e) {
    const known = Object.keys(objects).sort();
    throw new Error(`ObjectSlot: no object "${r.id}" — defined here: ${known.length ? known.join(', ') : '(none)'}. ` +
      `A film builds its own in <out_dir>/workshop/objects/${r.id}.tsx ` +
      `(python3 scripts/workshop.py <out_dir> new-object ${r.id} --means "...").`);
  }
  if (r.props != null && (typeof r.props !== 'object' || Array.isArray(r.props))) {
    throw new Error(`ObjectSlot: "${r.id}".props must be an object — got ${JSON.stringify(r.props)}`);
  }
  const clash = SLOT_KEYS.filter((k) => r.props != null && k in r.props);
  if (clash.length) {
    throw new Error(`ObjectSlot: "${r.id}".props sets ${clash.join(', ')}, which the slot gives every object ` +
      "(its box, its clock, the film's DNA) — remove them.");
  }
  return e;
};

/** A host that needs the object's META before it lays out (its aspect, whether it turns) asks here. */
export const useObjectEntry = (ref: unknown): ObjectEntry => resolveObject(React.useContext(ObjectsContext), ref);

export const ObjectSlot: React.FC<{object: ObjectRef; box: Rect; t?: number; yaw?: number;
  style?: React.CSSProperties}> = ({object, box, t, yaw, style}) => {
  const objects = React.useContext(ObjectsContext);
  const beatT = useT();
  const dna = useDNA();
  const {C, meta} = resolveObject(objects, object);
  const r = fitAspect(box, meta?.aspect);
  return (
    <div data-object-slot={object.id}
      style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, ...style}}>
      <C {...(object.props ?? {})} w={r.w} h={r.h} t={t ?? beatT} dna={dna} yaw={yaw} />
    </div>
  );
};
