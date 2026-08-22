// SHOT · Atom Orbital — a nucleus of protons/neutrons at the core with electron SHELLS: tilted elliptical
// orbits, electrons racing along them with glowing trails, the whole atom slowly turning. A scientific /
// physics register (family S · scientific/molecular). Deterministic (electron angle = t·speed + phase).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
const BG_D0 = '#060812', CORE = '#ffd36e';
const ORBITS = [{rx: 340, ry: 120, tilt: 0, col: '#37e0ff', n: 2, sp: 1.0},
  {rx: 300, ry: 300, tilt: 60, col: '#ff5b9e', n: 3, sp: -0.8},
  {rx: 340, ry: 120, tilt: 120, col: '#8f7bff', n: 2, sp: 1.3}];

export const AtomOrbital: React.FC<{title?: string; tagline?: string}> = ({
  title: TITLE = 'Elemental', tagline: TAG = 'the core of everything'} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 + 10;
  const build = easeOutBack(clamp01(seg(t, 0.06, 0.44)));
  const titleIn = easeOutCubic(seg(t, 0.52, 0.76));
  const tagIn = easeOutCubic(seg(t, 0.62, 0.84));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 50% 44%, #101430, ${BG} 74%)`, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${cx} ${cy})`}>
          {ORBITS.map((o, i) => (
            <ellipse key={'e' + i} rx={o.rx * build} ry={o.ry * build} fill="none" stroke={o.col} strokeWidth={2}
              opacity={0.35} transform={`rotate(${o.tilt})`} />
          ))}
          {/* nucleus */}
          <g opacity={clamp01(build * 1.4)}>
            {[...Array(7)].map((_, k) => {
              const a = (k / 7) * Math.PI * 2, r = 22;
              return <circle key={k} cx={Math.cos(a) * r} cy={Math.sin(a) * r} r={20}
                fill={k % 2 ? CORE : '#ff8f5e'} opacity={0.95} style={{filter: `drop-shadow(0 0 8px ${CORE})`}} />;
            })}
          </g>
          {/* electrons — each RACES with a motion trail (reads as an atom, vs DataOrrery's static labelled nodes) */}
          {ORBITS.map((o, i) => [...Array(o.n)].map((_, k) => {
            const base = t * o.sp * 2.2 + (k / o.n) * Math.PI * 2 + i;
            const tl = (o.tilt * Math.PI) / 180;
            const pos = (a: number): [number, number] => {
              const x0 = Math.cos(a) * o.rx * build, y0 = Math.sin(a) * o.ry * build;
              return [x0 * Math.cos(tl) - y0 * Math.sin(tl), x0 * Math.sin(tl) + y0 * Math.cos(tl)];
            };
            const [ex, ey] = pos(base);
            const dir = Math.sign(o.sp) || 1;
            const trail = [ex, ey].join(',') + ' ' + [0.14, 0.3, 0.5, 0.74].map((d) => pos(base - d * dir).map((n) => n.toFixed(1)).join(',')).join(' ');
            return <g key={`${i}-${k}`} opacity={clamp01(build)}>
              <polyline points={trail} fill="none" stroke={o.col} strokeWidth={5} strokeLinecap="round" opacity={0.32} />
              <circle cx={ex} cy={ey} r={13} fill={o.col} style={{filter: `drop-shadow(0 0 12px ${o.col})`}} />
            </g>;
          }))}
        </g>
      </svg>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 110}}>
        <div style={{opacity: titleIn, transform: `translateY(${(1 - titleIn) * 14}px)`, color: '#eaf2ff',
          font: '800 104px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em', textShadow: '0 8px 40px #000'}}>{TITLE}</div>
        <div style={{opacity: tagIn, marginTop: 16, color: '#9fb2d0',
          font: '600 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.18em'}}>{TAG}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
export default AtomOrbital;
