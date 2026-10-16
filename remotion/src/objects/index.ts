// THE LIBRARY'S OBJECTS — things drawn for a film and PROMOTED into the library by scripts/promote.py, which
// adds the import and the entry below. Any film can put one into any register with a slot for one (a prop typed
// ObjectRef) by its id. See references/object-authoring.md.
import type {ObjectEntry} from '../runtime/objectSlot';
import * as O_DemoForm from './DemoForm';
import * as O_EraStrata from './EraStrata';
import * as O_GpsSatellite from './GpsSatellite';
import * as O_OffsetClock from './OffsetClock';

export const LIBRARY_OBJECTS: Record<string, ObjectEntry> = {
  DemoForm: {C: O_DemoForm.DemoForm, meta: O_DemoForm.META},
  EraStrata: {C: O_EraStrata.EraStrata, meta: O_EraStrata.META},
  GpsSatellite: {C: O_GpsSatellite.GpsSatellite, meta: O_GpsSatellite.META},
  OffsetClock: {C: O_OffsetClock.OffsetClock, meta: O_OffsetClock.META},
};
