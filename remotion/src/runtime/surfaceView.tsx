// A CAMERA OVER A PANEL — a screen, a page, a UI redrawn in DOM — whose type GLIDES while the camera pans and
// pushes, on a flat frame or inside a 3D surface. The one way to build it, so no shot has to remember the rules.
//
// THE DEFECT THIS EXISTS FOR (2026-10-30). A product film redrew its app's panel as DOM inside a 3D Mac display
// (`Surface`, runtime/stage3d.tsx) and moved a keyframed camera across it the obvious way: every frame it
// recomputed each element's `left`/`top` and `font-size` from the view (`left: x * k - offset`, `font: size * k`).
// Every gate passed; the viewer saw the type tremble (字体抖动). Measured from the delivered pixels against the
// geometry (scripts/jitter_qa.py): 0.2-0.6px RMS of error on every line of the panel, steps of a pixel at the end of
// each move — against 0.002px (median) for the film's 2D type. Two separate causes, both of them paths that
// runtime/glide.ts already documents for flat type:
//   1. a LAYOUT position is rounded to whole pixels before Skia draws anything, and a font size re-set every
//      frame re-lays the line out — no skew reaches either;
//   2. under an axis-aligned matrix Skia snaps each baseline to a whole pixel of the raster it draws into — and
//      inside a 3D surface that raster is the LAYER's, not the screen's, so an unlock on the camera above the
//      surface never reaches it.
// The 3D layer did not cause the staircase (the same panel drawn flat stepped exactly as much: SlabTypeProbe
// `flat`); it HID it, because the type-glide census cannot judge type a compositor moves and skipped it.
//
// THE CURE, measured on SlabTypeProbe (runtime/__probe_slab.tsx; numbers in references/engineering-case-law.md):
// the panel is laid out ONCE at its own design size and never re-laid out; the view is ONE transform on its
// wrapper — translate and scale — carrying the baseline unlock (runtime/glide.ts) INSIDE the surface, raised for
// the size the panel is drawn at. Laid out once, nothing is rounded per frame; drawn under a skew in the layer's
// own raster, no baseline snaps.
//
// HOW TO USE. Children are laid out in the panel's own units (`w` x `h`, the design size). `k` is how many frame px
// one panel unit is drawn at, `x`/`y` where the panel's origin lands in the parent — a camera on the panel is just
// these three numbers per frame. Anything that MOVES inside the panel (a cursor, a marker) moves by a transform,
// never by `left`/`top` (use `usePlaceGlide` from runtime/glide.ts): a layout offset inside a panel drawn at k is
// rounded to a whole PANEL unit — k frame px a step.
//
// WHERE IT GOES. Inside the face, under the face's clip — `<Surface>` -> face -> `<SurfaceView>` -> the panel. The
// device kit (runtime/device.tsx) puts a live screen in a phone or a laptop the same way: its screen content is a
// SurfaceView, so a push onto the phone's screen glides. A 2D screen (no Surface) uses it unchanged.
//
// THE UNLOCK IS ON FOR THE WHOLE SHOT, not per frame (runtime/glide.ts "WHEN IT IS ON — over a SPAN"): a view that
// can move at all carries it from the first frame to the last, so there is no frame on which the type changes how
// it is rounded. `still` is for a panel whose view never moves: nothing is added and the panel is drawn exactly as
// a plain transform would draw it. The off switch (BaselineUnlockContext) is honoured.
import React from 'react';
import {unlockFor} from './glide';
import {BaselineUnlockContext} from './glide';

/** The transform that puts a panel of design units at (x, y), drawn at k, with the unlock while it can move. `outer`
 *  is any scale ABOVE the panel the caller knows of (a stage scaled up or down): Skia judges the skew times every
 *  scale above the type, so the unlock is raised for the smallest of them (runtime/glide.ts `unlockFor`). */
export const surfaceViewTransform = (k: number, x: number, y: number, unlocked: boolean, outer = 1): string => {
  if (!(k > 0) || !isFinite(k)) throw new Error(`SurfaceView: the panel's scale must be a positive number, got ${k}.`);
  if (!isFinite(x) || !isFinite(y)) throw new Error(`SurfaceView: the panel's place must be finite, got (${x}, ${y}).`);
  const base = `matrix(${k}, 0, 0, ${k}, ${x}, ${y})`;
  return unlocked ? `${base} ${unlockFor(Math.max(0.05, k * outer))}` : base;
};

/**
 * THE RASTER MODE — measured smoother still, for a view that ZOOMS. Under the unlock Skia still places each glyph to a
 * quarter pixel, and while the view's scale changes the glyphs are re-drawn at every new size: on a probe push the
 * residual was 0.083px RMS (pan 0.048), on a real film's push 0.11-0.14 with a small badge at 0.21. Laid out ONCE at
 * the largest scale the shot reaches (`raster` = that k, times any scale above the panel) and moved by a 3D transform
 * at k/raster <= 1, the panel becomes its own compositor layer, rasterised once, and every frame is the GPU resampling
 * one fixed picture: 0.019px pan, 0.020px push, as sharp at rest (SlabTypeProbe `raster`). The price: `raster` must
 * really be the largest scale — drawn larger than it, the picture is magnified and soft — so a k past it THROWS.
 */
export const surfaceRasterTransform = (k: number, x: number, y: number, raster: number): string => {
  if (!(raster > 0) || !isFinite(raster)) throw new Error(`SurfaceView: raster must be a positive number, got ${raster}.`);
  if (k > raster * 1.0005) {
    throw new Error(`SurfaceView: the view reaches scale ${k.toFixed(3)} past the raster it was laid out at ` +
      `(${raster.toFixed(3)}) — it would be magnified and soft; pass the LARGEST scale the shot reaches.`);
  }
  surfaceViewTransform(k, x, y, false);              // the same checks on k and the place
  const s = k / raster;
  return `matrix3d(${s},0,0,0,0,${s},0,0,0,0,1,0,${x},${y},0,1)`;
};

export const SurfaceView: React.FC<{
  /** the panel's own size, in its design units — what its children are laid out in */
  w: number; h: number;
  /** frame px per panel unit, now */
  k: number;
  /** where the panel's top-left corner lands in the parent, now */
  x: number; y: number;
  /** the view never moves in this shot: draw it with no unlock */
  still?: boolean;
  /** any known scale above the panel (default 1) */
  outer?: number;
  /** lay the panel out ONCE at this scale and let the compositor resample it (see surfaceRasterTransform) */
  raster?: number;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({w, h, k, x, y, still = false, outer = 1, raster, style, children}) => {
  const allowed = React.useContext(BaselineUnlockContext);
  if (raster !== undefined) {
    // `zoom` lays the children out at `raster` in their own units (positions and type sizes multiplied, as a panel
    // laid out at that size would be); the 3D transform makes the wrapper a layer of its own and only resamples it
    return (
      <div data-surface-view="raster" style={{position: 'absolute', left: 0, top: 0, width: w * raster,
        height: h * raster, transformOrigin: '0 0', transform: surfaceRasterTransform(k, x, y, raster), ...style}}>
        {/* the unlock INSIDE the layer too: anything that animates within the panel (a button pressed, a badge
            counting) is re-drawn into this one raster, and under a plain matrix there it would snap — measured on a
            film's approve button, a 0.6px dip and back on the press frame with the raster and no unlock */}
        <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, zoom: raster, transformOrigin: '0 0',
          transform: allowed && !still ? unlockFor(1) : undefined}}>{children}</div>
      </div>
    );
  }
  return (
    <div data-surface-view="" style={{position: 'absolute', left: 0, top: 0, width: w, height: h,
      transformOrigin: '0 0', transform: surfaceViewTransform(k, x, y, allowed && !still, outer), ...style}}>
      {children}
    </div>
  );
};
