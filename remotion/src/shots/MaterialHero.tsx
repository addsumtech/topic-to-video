// SHOT · Material Hero — Bear/premium product-reveal language: a REAL 3D object turns on a turntable under a
// sweeping accent rake-light, metallic and reflective, on a dark stage. This is the Remotion edge the flat
// HTML tier structurally cannot make — genuine WebGL 3D + lighting (R3F via @remotion/three). Deterministic.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';

export const DURATION = 150; // 5s

const Hero: React.FC = () => {
  const frame = useCurrentFrame();
  const yaw = frame * 0.02;
  const rimX = Math.sin(frame * 0.03) * 7; // the rake light sweeps
  const rimZ = 4 + Math.cos(frame * 0.03) * 2;
  return (
    <>
      {/* a glossy (not pure-metal) object reads its FORM via diffuse shading even with no env map, so it
          never goes black; lights sculpt it and a coloured rim gives the premium edge glow. */}
      <ambientLight intensity={0.5} />
      <hemisphereLight args={['#8fa6d8', '#0a0d14', 0.7]} />
      <directionalLight position={[5, 7, 6]} intensity={2.0} color={'#ffffff'} />
      <directionalLight position={[-6, 2, 2]} intensity={0.9} color={'#cfe0ff'} />
      <pointLight position={[rimX, -1.2, rimZ]} color={'#5B8CFF'} intensity={5} />
      <pointLight position={[-5, 3.5, -3]} color={'#FFC978'} intensity={3} />
      <mesh rotation={[0.34, yaw, 0.12]}>
        <torusKnotGeometry args={[1.05, 0.35, 220, 36]} />
        <meshStandardMaterial color={'#6f83bf'} metalness={0.35} roughness={0.22} emissive={'#141a33'} emissiveIntensity={0.4} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.9, 0]}>
        <circleGeometry args={[6, 48]} />
        <meshStandardMaterial color={'#141a28'} metalness={0.5} roughness={0.4} />
      </mesh>
    </>
  );
};

export const MaterialHero: React.FC<{title?: string}> = ({title = 'One tool. Your whole team.'} = {}) => {
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 42%, #10131d, #05070c 72%)'}}>
      <ThreeCanvas width={width} height={height} camera={{position: [0, 0.4, 5], fov: 42}} style={{position: 'absolute', inset: 0}}>
        <Hero />
      </ThreeCanvas>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 250, textAlign: 'center'}}>
        <div style={{font: '800 92px/1 Inter,system-ui,sans-serif', color: '#f2f5fb', letterSpacing: '-0.02em'}}>{title}</div>
      </div>
    </AbsoluteFill>
  );
};
export default MaterialHero;
