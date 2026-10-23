// CARRY ANCHORS — the elements a seam can take hold of.
//
// Three seams operate on ONE THING ON THE FRAME rather than on the whole frame (Film's seams.tsx): `container` carries
// an element from beat A into beat B and FLIPs its rect from where it sat in A to where it sits in B; `grow` opens the
// next beat out of an element's own shape; `through-window` pushes the camera into an element until it fills the
// frame. A register says which of its elements those are by marking them — `data-carry="<id>"` on the element itself
// (the attribute changes no pixel; a test proves it on renders), or a `<CarryAnchor>` where the thing is drawn in
// several pieces and the anchor is their outline. When the thing is drawn as SIBLINGS of the anchor (an editor's
// code layer and output strip beside its window box), each of them says `data-carry-part="<id>"`: a container hides
// the parts with the anchor at the place the element leaves, so nothing of it is left behind there. Ids are shared
// words so two DIFFERENT registers can name the same thing: `screen` (a device's screen), `window` (an app or terminal
// window), `hero` (a stage's hero card), `figure` (the main figure), `card:<id>` (a stage's side card by its id),
// `word` (a line of display type). A text anchor that also says `data-carry-glyph` is a GLYPH anchor: a
// through-window seam looks through its letterforms rather than its box.
//
// WHY AN ANCHOR IS DECLARED AND NEVER GUESSED. The planner and the validator read these declarations out of the
// source (scripts/carry_anchors.py) so a board that asks for a seam on an anchor the register does not have is an
// ERROR before the render, and the seam itself refuses an anchor it cannot find on the frame (cancelRender, never a
// quiet fallback to a fade). A seam that silently turned into a cross-fade is the "built but unreachable" failure
// this repo has paid for twice (scripts/seam_plan.py's header).
//
// THE ARRIVAL. A container ends on the anchor's rect in beat B — so the anchor has to BE there on B's first frame.
// Most registers reveal their content after the seam (runtime/motion useT holds the beat at ENTRY_T while a seam runs
// over it), so a device that rises into place, say, is invisible at that moment and the container would land on
// nothing. A register whose anchor has an entrance reads `useCarried(id)` and, when the beat arrived by a container
// carrying that anchor, draws it already in place: the container IS its entrance. With no container the hook is
// false and the register draws exactly what it drew before (the value only exists inside Film's provider).
import React from 'react';

/** The anchor id this beat's incoming CONTAINER seam carries into it, or null (Film.tsx provides it per beat). */
export const CarryContext = React.createContext<string | null>(null);

/** True when this beat arrived by a container seam that carried the anchor `id` into it: draw that anchor settled. */
export const useCarried = (id: string): boolean => React.useContext(CarryContext) === id;

/**
 * An anchor's rect where the thing it names is drawn as several parts (a device's lid, strip and screen) — an empty,
 * absolutely placed box that paints nothing. `radius` is the outline's corner in px (a seam's clip follows it).
 */
export const CarryAnchor: React.FC<{id: string; x: number; y: number; w: number; h: number; radius?: number}> =
  ({id, x, y, w, h, radius}) => (
    <div data-carry={id} data-carry-radius={radius !== undefined ? String(radius) : undefined}
      style={{position: 'absolute', left: x, top: y, width: w, height: h, pointerEvents: 'none'}} />
  );
