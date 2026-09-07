// POINT THE GL CAMERA WHERE THE LABEL MATHS THINKS IT POINTS.
//
// react-three-fiber aims a camera it created at the WORLD ORIGIN. Passing `camera={{position, fov}}` to
// <ThreeCanvas> sets the position and the lens and says nothing about the direction, so a shot that composes
// around any other aim gets two different cameras: the one three renders with (looking at 0,0,0) and the one
// `project()` is told about. Nothing errors. The picture is fine. Every DOM label is simply displaced by the
// aim offset — on PortRail's portrait cut, `aim.y = -0.62` put all six labels 215px above their own modules,
// each one landing on its NEIGHBOUR, which reads as a correct frame with the wrong words on it.
//
// So the aim is stated once and both cameras use it. It runs during render rather than in an effect because
// the frame is drawn from this matrix, and a still must not depend on effect ordering.

import React from 'react';
import {useThree} from '@react-three/fiber';
import type {Vec3} from './project3d';

export const AimCamera: React.FC<{at: Vec3; from?: Vec3}> = ({at, from}) => {
  const camera = useThree((s) => s.camera);
  // The POSITION is set here too, not only the aim, and for the same reason: a shot that MOVES its camera
  // hands <ThreeCanvas> a new `camera` prop every frame and has to trust r3f to re-apply it. Setting both
  // from one place makes the rendered camera and the camera `project()` was told about the same object by
  // construction, which is the only version of this that cannot drift back apart.
  if (from) camera.position.set(from[0], from[1], from[2]);
  camera.lookAt(at[0], at[1], at[2]);
  camera.updateMatrixWorld();
  return null;
};
export default AimCamera;
