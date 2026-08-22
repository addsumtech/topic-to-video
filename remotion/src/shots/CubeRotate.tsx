// SHOT · Cube Rotate — content lives on the four side FACES of a 3D cube; the camera orbits, landing on and
// holding each face in turn (3/4 tilt, floor reflection, rim light). Pure CSS 3D (preserve-3d) — no WebGL.
// The "one subject, several sides" spatial register (family B). Deterministic (orbit angle = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette} from '../runtime/dna';

export const DURATION = 165; // 5.5s
const BG = '#080a11';
const TONES0 = ['#5b8cff', '#c07bff', '#ff6f91', '#31c9a6'];
const SIZE = 660;

export const CubeRotate: React.FC<{faces?: string[]; title?: string}> = ({
  faces: FACES = ['Plan', 'Build', 'Ship', 'Learn'], title: TITLE = 'The loop'} = {}) => {
  const t = useT();
  const dna = useDNA(); const TONES = dnaPalette(dna, 4) ?? TONES0;
  const {width: W, height: H} = useVideoConfig();
  const sides = FACES.slice(0, 4);
  const n = sides.length;
  // present each face in its own time-slot: rotate IN during the first 45%, HOLD the rest.
  const p = clamp01(t) * n;                        // 0..n
  const k = Math.min(n - 1, Math.floor(p));        // face being presented
  const arrive = easeInOutCubic(clamp01((p - k) / 0.45));
  const angle = lerp(-(k - 1) * 90, -k * 90, arrive); // from previous face to this one, then hold
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(120% 100% at 50% 36%, #12162c, ${BG} 70%)`,
      overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 80, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#aeb6ca', font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div>

      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center', perspective: 2100}}>
        <div style={{width: SIZE, height: SIZE, position: 'relative', transformStyle: 'preserve-3d',
          transform: `translateZ(${-SIZE / 2}px) rotateX(-10deg) rotateY(${angle}deg)`}}>
          {sides.map((label, i) => {
            const tone = TONES[i % TONES.length];
            const active = i === k && arrive > 0.6;
            const parts = label.split(' - ');                     // "2019 - Capped-profit" → big "2019" + label
            const big = parts.length > 1 ? parts[0] : String(i + 1);
            const small = parts.length > 1 ? parts.slice(1).join(' - ') : label;
            return (
              <div key={i} style={{position: 'absolute', width: SIZE, height: SIZE, boxSizing: 'border-box', padding: 72,
                transform: `rotateY(${i * 90}deg) translateZ(${SIZE / 2}px)`,
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
                background: `linear-gradient(155deg, #161a2b, #0d1018)`,
                border: `1px solid ${active ? tone : '#252a40'}`, borderRadius: 22,
                boxShadow: active ? `inset 0 0 160px ${tone}22, 0 0 60px ${tone}44` : 'inset 0 0 120px #0006'}}>
                <div style={{minWidth: 96, height: 96, borderRadius: 22, marginBottom: 30, padding: '0 20px',
                  background: `linear-gradient(150deg, ${tone}, #2b3ac6)`, boxShadow: `0 0 40px ${tone}66`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', font: `800 44px/1 Inter, system-ui, sans-serif`, whiteSpace: 'nowrap'}}>{big}</div>
                <div style={{color: '#eef2ff', font: `800 52px/1.08 Inter, system-ui, sans-serif`,
                  letterSpacing: '-0.02em', maxWidth: SIZE - 150}}>{small}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* floor reflection wash */}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 240,
        background: 'linear-gradient(#0000, #000000aa)'}} />
    </AbsoluteFill>
  );
};
export default CubeRotate;
