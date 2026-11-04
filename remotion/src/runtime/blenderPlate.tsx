// A BLENDER PLATE under a film's own shot (scripts/blender_plate.py, references/blender-plates.md).
//
// Blender draws what 3D physicality is the content of — a real place or object, a material, a process, an optic, a
// space — and hands over a plate: a VP9 video with alpha, plus, per frame, its named points (anchors) and where each
// named object is (boxes). The shot draws everything that MEANS something on top: words, labels, data, timing. The
// overlay stays on the thing it names because the points come from the render itself, frame by frame.
//
// Imported only by workshop shots (a film's own code), never by a library register, so no register's source hash
// moves because this exists. `data-plate-object` boxes are what runtime/plateClear.tsx (plate_qa.py) reads.
import React from 'react';
import {OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export type Plate = {
  id: string;
  src: string;
  w: number;
  h: number;
  fps: number;
  frames: number;
  mode: 'rgba' | 'env';
  anchors: Record<string, number[][]>;           // per frame [x, y, depth, visible] in the plate's pixels
  boxes: Record<string, (number[] | null)[]>;    // per frame [x0, y0, x1, y1] in the plate's pixels, or null
};

export type PlateAnchor = {x: number; y: number; depth: number; visible: boolean};
export type PlateBox = {x: number; y: number; w: number; h: number};

const known = (rec: Record<string, unknown>, what: string, name: string) => {
  if (!(name in rec)) {
    throw new Error(`blender plate: no ${what} "${name}" — this plate has ${Object.keys(rec).join(', ') || '(none)'}`);
  }
};

/** Which of a plate's `frames` frames shows on beat frame `frame`: a whole frame, held at the plate's last past its
 *  end. A warped or timed clock hands a register FRACTIONS (Film's BeatClock), and per-frame data indexed by 3.4 is
 *  `undefined` — the glass film's full render died on exactly that, 2026-11-04. */
export const plateFrame = (frame: number, frames: number): number => {
  if (!Number.isFinite(frame)) throw new Error(`blender plate: the beat frame is ${frame}, not a number`);
  return Math.min(frames - 1, Math.max(0, Math.round(frame)));
};

/** The beat's clock as its VOICE runs it, provided by Film's BeatClock around a register it re-times. A plate's motion
 *  is on the voice already (its cues are baked from the word times), so the warp that moves a register's entrances
 *  onto their words would move the plate OFF them; the beat's time grammar (a hit-stop, a freeze) is authored time and
 *  stays in. Absent (a standalone still, an un-retimed beat) = the current frame, which is then that same clock. */
export const PlateClock = React.createContext<number | null>(null);

/** This frame of the plate, scaled to the composition: its anchors and its objects' boxes. The frame is the beat's
 *  own (plate time 0 = the beat's first frame = its voice's start), held at the last frame past the plate's end. */
export const usePlate = (p: Plate) => {
  const current = useCurrentFrame();
  const clock = React.useContext(PlateClock);
  const {width: W, height: H} = useVideoConfig();
  if (!(p.w > 0) || !(p.h > 0) || !(p.frames > 0)) {
    throw new Error(`blender plate ${p.src}: a plate needs a positive size and length (got ${p.w}x${p.h}, ${p.frames} frames)`);
  }
  const f = plateFrame(clock ?? current, p.frames);
  const kx = W / p.w, ky = H / p.h;
  return {
    f,
    anchor: (name: string): PlateAnchor => {
      known(p.anchors, 'anchor', name);
      const a = p.anchors[name][Math.min(f, p.anchors[name].length - 1)];
      return {x: a[0] * kx, y: a[1] * ky, depth: a[2], visible: Boolean(a[3])};
    },
    box: (name: string): PlateBox | null => {
      known(p.boxes, 'object', name);
      const b = p.boxes[name][Math.min(f, p.boxes[name].length - 1)];
      return b ? {x: b[0] * kx, y: b[1] * ky, w: (b[2] - b[0]) * kx, h: (b[3] - b[1]) * ky} : null;
    },
  };
};

/** The plate itself, full frame, and an empty marker over each of its objects on this frame. */
export const BlenderPlate: React.FC<{plate: Plate}> = ({plate}) => {
  const {width: W, height: H} = useVideoConfig();
  const u = usePlate(plate);
  return (
    // the plate, which of its frames is on screen, and its objects' boxes on that frame — one container, so
    // runtime/plateClear.tsx maps type into THIS plate's pixels even when a shot draws two
    <div data-plate={plate.id} data-plate-frame={u.f} data-plate-w={plate.w} data-plate-h={plate.h}
      style={{position: 'absolute', left: 0, top: 0, width: W, height: H, pointerEvents: 'none'}}>
      <OffthreadVideo src={staticFile(plate.src)} muted transparent={plate.mode === 'rgba'}
        style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} />
      {Object.keys(plate.boxes).map((name) => {
        const b = u.box(name);
        return b ? (
          <div key={name} data-plate-object={name}
            style={{position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h, pointerEvents: 'none'}} />
        ) : null;
      })}
    </div>
  );
};
