// P6 FEASIBILITY PROBE — an isolated entry (its own registerRoot) that renders a true-3D R3F scene, to
// prove @remotion/three + WebGL actually render in the headless compositor BEFORE building the hero tier.
// Not part of the main pipeline (index.ts). Render with:
//   npx remotion still src/three/probe.tsx ThreeProbe out.png --frame=30 --gl=angle
import React from 'react';
import {Composition, registerRoot, useCurrentFrame, useVideoConfig, interpolate, Easing} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';

// A frame-driven camera that ORBITS the scene and looks down at it — the exact move the CSS-3D rig
// cannot make (card planes keystone/vanish past ~40°). This is 3D's reason to exist here.
const CameraRig: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const camera = useThree((s) => s.camera);
  const p = interpolate(frame, [0, durationInFrames], [0, 1], {easing: Easing.inOut(Easing.cubic), extrapolateRight: 'clamp'});
  const ang = interpolate(p, [0, 1], [-0.9, 0.5]);      // ~80° yaw orbit
  const height = interpolate(p, [0, 1], [7, 2.4]);      // crane down from high to eye level
  const radius = 7;
  camera.position.set(Math.sin(ang) * radius, height, Math.cos(ang) * radius);
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();
  return null;
};

const Probe: React.FC = () => {
  const frame = useCurrentFrame();
  const spin = frame * 0.02;
  return (
    <ThreeCanvas width={1280} height={720} style={{backgroundColor: '#0e1116'}} camera={{fov: 45, position: [0, 6, 7]}}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 8, 4]} intensity={1.4} />
      <pointLight position={[-4, 3, -3]} intensity={0.6} color="#5fb3c9" />
      <CameraRig />
      {/* a ground plane laid flat (real 3D — recedes to a true vanishing point) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.2, 0]}>
        <planeGeometry args={[24, 24]} />
        <meshStandardMaterial color="#141a24" />
      </mesh>
      {/* three upright content planes at different depths (the deck's panels, in true 3D) */}
      <mesh position={[-2.6, 0, -1]}>
        <planeGeometry args={[3, 1.8]} />
        <meshStandardMaterial color="#e3b23c" />
      </mesh>
      <mesh position={[0.4, 0.2, 1]} rotation={[0, -0.3, 0]}>
        <planeGeometry args={[3, 1.8]} />
        <meshStandardMaterial color="#5fb3c9" />
      </mesh>
      {/* a lit box — its shaded faces prove real 3D lighting, not a flat sprite */}
      <mesh position={[2.6, 0.1, -0.5]} rotation={[spin, spin * 1.3, 0]}>
        <boxGeometry args={[1.4, 1.4, 1.4]} />
        <meshStandardMaterial color="#f0f3f8" />
      </mesh>
    </ThreeCanvas>
  );
};

const ProbeRoot: React.FC = () => (
  <Composition id="ThreeProbe" component={Probe} durationInFrames={60} fps={30} width={1280} height={720} />
);

registerRoot(ProbeRoot);
