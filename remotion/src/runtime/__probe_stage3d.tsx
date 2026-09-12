// Probe: does `projectPose` land where CSS actually draws?
//
// This is the one failure a 3D stage cannot be allowed to ship with, and this repo has already paid for it
// once — `runtime/aimCamera` records six PortRail labels sitting 215px off their own modules, on a frame
// that read as perfectly correct with the wrong words on it, because two cameras agreed until they quietly
// did not. So the probe draws each marker TWICE: a green dot at the surface's centre INSIDE the 3D world,
// where CSS positions it, and a magenta dot at `projectPose` OUTSIDE it, where the arithmetic says it is.
// Agreement is the two dots coinciding in the pixels; tests/test_stage3d.py measures the distance.
//
// The poses are deliberately awkward — all three rotations at once, off-centre, at depth, under a camera
// that is itself rotated and dollied. A probe that only tests an axis-aligned card proves the one case a
// transposed matrix also gets right.
import React from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, useVideoConfig} from 'remotion';
import {Stage3D, Surface, projectPose, faceShade, PERSP_FRAC, type Pose} from './stage3d';

export const DURATION = 30;

// THE POSES ARE EXTREME ON PURPOSE, and the reason is a measurement: with rotations under 40 degrees a
// TRANSPOSED rotY moved the dots only 3.5px, against a 1.7px antialiasing floor — a positive control with
// no daylight in it, which is a gate that will one day report noise or miss the defect. Turned past 60
// degrees and spread across the depth, the same mutant moves them by tens of pixels.
export const CAM: Pose = {x: -40, y: 26, z: 320, rx: -14, ry: 26, rz: 6, s: 1};
export const POSES: Pose[] = [
  {x: -520, y: -260, z: -420, rx: 22, ry: -62, rz: -10},
  {x: 470, y: -190, z: 300, rx: -28, ry: 68, rz: 14},
  {x: -380, y: 300, z: 120, rx: 46, ry: 24, rz: -22},
  {x: 430, y: 330, z: -520, rx: -16, ry: -74, rz: 16, s: 1.25},
  {x: 0, y: 0, z: 200, ry: 40},
];

export const StageProbe: React.FC<{report?: boolean}> = ({report = false}) => {
  const {width: W, height: H} = useVideoConfig();
  const P = Math.round(Math.min(W, H) * PERSP_FRAC);
  return (
    <AbsoluteFill style={{background: '#0b0d12'}}>
      <Stage3D cam={CAM} persp={P}>
        {POSES.map((p, i) => (
          <Surface key={i} pose={p} w={260} h={160}
            // backfaces VISIBLE here on purpose: the probe must draw all five centres whatever the maths
            // does to their facing, or a mutant that turns a card away is "caught" by a missing dot rather
            // than by the distance this is measuring.
            style={{background: `rgba(90,110,150,${faceShade(p, CAM).toFixed(3)})`, backfaceVisibility: 'visible',
              border: '2px solid #5a6e96', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            {/* the centre of the surface, placed by CSS */}
            {/* SMALL ON PURPOSE. A disc's centroid under perspective is not the projection of its centre —
                the nearer half projects larger — so the bias grows with the marker's radius AND with the
                foreshortening. Measured: a 10px dot on poses turned past 60 degrees put the clean code at
                4.4px, which is the marker lying about itself, not the camera disagreeing. At 4px the same
                poses measure under 2. */}
            <div data-stage-marker={i} style={{width: 4, height: 4, borderRadius: 2, background: '#00ff66'}} />
          </Surface>
        ))}
      </Stage3D>
      {/* the same centres, placed by the arithmetic — ordinary 2D, outside the 3D context */}
      {POSES.map((p, i) => {
        const q = projectPose(p, CAM, P, W, H);
        if (q.behind) return null;
        return <div key={i} style={{position: 'absolute', left: q.x - 1, top: q.y - 1,
          width: 2, height: 2, background: '#ff00cc'}} />;
      })}
      <StageReport enabled={report} />
    </AbsoluteFill>
  );
};

/** ASK THE BROWSER WHERE IT DREW, instead of reading it back out of the pixels.
 *
 *  The pixel version of this measurement has a bias of its own and it is not small: a disc's centroid under
 *  perspective is not the projection of its centre — the nearer half projects larger — so on poses turned
 *  past 60 degrees a 10px marker reported the CLEAN code 4.4px out, which is the marker lying about itself.
 *  Shrinking it traded that for a detection problem, and a mutant then got "caught" by a dot that had gone
 *  missing rather than by a distance. `getBoundingClientRect` has neither failure: it is what the browser
 *  computed, for every marker, present or not, and for a 4px square the box's centre IS its projection to
 *  well under a pixel. Armed with `stageReport`, it cancels the render with the numbers, the same channel
 *  runtime/textSafe uses.
 */
export const STAGE_REPORT_TAG = 'STAGE-PROBE ';

export const StageReport: React.FC<{enabled?: boolean}> = ({enabled = false}) => {
  const {width: W, height: H} = useVideoConfig();
  const [handle] = React.useState(() => (enabled ? delayRender('stage probe', {timeoutInMilliseconds: 30000}) : null));
  React.useEffect(() => {
    if (!enabled || handle === null) return;
    (async () => {
      await new Promise((res) => requestAnimationFrame(() => res(null)));
      const P = Math.round(Math.min(W, H) * PERSP_FRAC);
      const rows: unknown[] = [];
      document.querySelectorAll('[data-stage-marker]').forEach((el) => {
        const i = Number(el.getAttribute('data-stage-marker'));
        const r = el.getBoundingClientRect();
        const q = projectPose(POSES[i], CAM, P, W, H);
        rows.push({i, css: [r.left + r.width / 2, r.top + r.height / 2], math: [q.x, q.y], k: q.k});
      });
      cancelRender(new Error(STAGE_REPORT_TAG + JSON.stringify({W, H, rows})));
    })();
    return () => { if (handle !== null) continueRender(handle); };
  }, [enabled, handle, W, H]);
  return null;
};

export default StageProbe;
