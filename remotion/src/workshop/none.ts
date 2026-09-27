// THE EMPTY WORKSHOP. `@workshop` resolves here whenever no film is in scope — every library render, sweep and
// test. A film's workshop (scripts/workshop.py) replaces it by PATH, through remotion.config.ts; this file is
// never edited to add one.
import type React from 'react';
import type {ObjectEntry} from '../runtime/objectSlot';
import type {GroundSpec} from '../runtime/shotLuma';

export const WORKSHOP_SHOTS: Record<string, {C: React.FC<any>; d: number; ground: GroundSpec}> = {};
export const WORKSHOP_OBJECTS: Record<string, ObjectEntry> = {};
