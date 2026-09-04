// SHOT · Molecule Ball-Stick — a ball-and-stick molecule (a hex ring + outer atoms) rotates in 3D: bonds are
// depth-sorted sticks, atoms are depth-shaded spheres coloured by element, assembling with a spin. A chemistry
// register (family S · scientific/molecular). Deterministic (rotation = fn of t; positions fixed).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomInset} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#070a14';
const ELEM = ['#6b7488', '#ff5b5b', '#5b8cff', '#e6ecff']; // C, O, N, H

export const MoleculeBallStick: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Composed', tagline: TAG = 'the chemistry of it'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 - 10, S = 220;
  // atoms: a 6-ring (carbons) + an outer atom off each ring vertex
  const atoms: {p: [number, number, number]; el: number; r: number}[] = [];
  const bonds: [number, number][] = [];
  for (let k = 0; k < 6; k++) {
    const a = (k / 6) * Math.PI * 2;
    atoms.push({p: [Math.cos(a), Math.sin(a), Math.sin(a * 2) * 0.3], el: 0, r: 30});
    bonds.push([k, (k + 1) % 6]);
  }
  for (let k = 0; k < 6; k++) {
    const a = (k / 6) * Math.PI * 2, R = 1.9;
    atoms.push({p: [Math.cos(a) * R, Math.sin(a) * R, Math.sin(a * 2) * 0.5], el: (k % 3) + 1, r: k % 3 === 2 ? 18 : 24});
    bonds.push([k, 6 + k]);
  }
  const build = easeOutBack(clamp01(seg(t, 0.06, 0.44)));
  const ang = t * 1.6, ca = Math.cos(ang), sa = Math.sin(ang), tilt = -0.4;
  const proj = (p: [number, number, number]) => {
    let x = p[0] * ca + p[2] * sa, z = -p[0] * sa + p[2] * ca, y = p[1];
    const y2 = y * Math.cos(tilt) - z * Math.sin(tilt); z = y * Math.sin(tilt) + z * Math.cos(tilt);
    const persp = 2 / (2 - z * 0.5);
    return {x: cx + x * S * persp * build, y: cy + y2 * S * persp * build, z, persp};
  };
  const pa = atoms.map((at) => ({...at, s: proj(at.p)}));
  const titleIn = easeOutCubic(seg(t, 0.52, 0.76));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 42%, #101430, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {/* bonds (behind) */}
        {bonds.map(([a, b], i) => {
          const A = pa[a].s, B = pa[b].s;
          return <line key={'b' + i} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke="#9fb0d0"
            strokeWidth={7 * ((A.persp + B.persp) / 2)} strokeLinecap="round" opacity={0.5 * build} />;
        })}
        {/* atoms (depth-sorted) */}
        {[...pa].map((at, i) => ({at, i})).sort((u, v) => u.at.s.z - v.at.s.z).map(({at, i}) => {
          const depth = clamp01((at.s.z + 1) / 2);
          return <g key={'a' + i} opacity={clamp01(build)}>
            <circle cx={at.s.x} cy={at.s.y} r={at.r * at.s.persp} fill={ELEM[at.el]}
              style={{filter: `drop-shadow(0 0 10px ${ELEM[at.el]}66)`}} />
            <ellipse cx={at.s.x - at.r * 0.3 * at.s.persp} cy={at.s.y - at.r * 0.32 * at.s.persp}
              rx={at.r * 0.3 * at.s.persp} ry={at.r * 0.22 * at.s.persp} fill="#ffffff" opacity={0.4 + 0.3 * depth} />
          </g>;
        })}
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', paddingBottom: bottomInset(W, H, 110)}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#eaf2ff',
          font: '800 104px/1 var(--f-display, Inter, system-ui, sans-serif)', letterSpacing: '-0.03em', textShadow: '0 8px 40px #000'}}>{TITLE}</div>
        <div style={{opacity: easeOutCubic(seg(t, 0.62, 0.84)), marginTop: 16, color: '#9fb2d0',
          font: '600 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default MoleculeBallStick;
