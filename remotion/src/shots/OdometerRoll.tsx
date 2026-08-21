// SHOT · Odometer Roll — a single BIG metric where every digit is a mechanical reel that spins through
// 0-9 and SNAPS to its target, staggered column-to-column, with a lock-pulse and a drawing underline.
// The "one number, felt physically" register (data-story payoff). Deterministic (reel pos = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 140; // ~4.7s
const BG = '#0a0b12', ACC0 = '#5b8cff';
const CELL = 236; // digit cell height

export const OdometerRoll: React.FC<{value?: string; label?: string; unit?: string}> = ({
  value: VALUE = '1,240', label: LABEL = 'active teams this week', unit: UNIT = ''} = {}) => {
  const t = useT();
  const dna = useDNA(); const ACC = dna?.accent ?? ACC0;
  useVideoConfig();
  const chars = String(VALUE).split('');
  const nDigits = chars.filter((c) => /\d/.test(c)).length;
  const labIn = easeOutCubic(seg(t, 0.05, 0.22));
  let di = -1; // running index across DIGIT chars only (for stagger)
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(130% 100% at 50% 34%, #141a36, ${BG} 66%)`,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{opacity: labIn, color: '#8b93a8', font: '600 30px/1 "JetBrains Mono", monospace',
        letterSpacing: '0.32em', textTransform: 'uppercase', marginBottom: 44,
        transform: `translateY(${(1 - labIn) * 14}px)`}}>{LABEL}</div>

      <div style={{display: 'flex', alignItems: 'flex-end', height: CELL}}>
        {chars.map((c, i) => {
          if (!/\d/.test(c)) {
            return <div key={i} style={{font: `800 210px/1 Inter, system-ui, sans-serif`, color: '#eef2ff',
              padding: '0 4px', alignSelf: 'center'}}>{c}</div>;
          }
          di++;
          const target = parseInt(c, 10);
          const spins = 2;                       // 2 full rotations then land (keeps the strip small)
          const total = spins * 10 + target;     // last strip cell === target
          const start = 0.1 + di * 0.05, end = 0.52 + di * 0.07;
          const r = easeOutExpo(seg(t, start, end));
          const offset = -r * total * CELL;
          const locked = t > end;
          const pulse = locked
            ? 1 + 0.05 * Math.max(0, Math.sin((t - end) * 26)) * Math.exp(-(t - end) * 7)
            : 1;
          const strip: number[] = [];
          for (let n = 0; n <= total; n++) strip.push(n % 10);
          return (
            <div key={i} style={{position: 'relative', width: 150, height: CELL, overflow: 'hidden',
              margin: '0 3px', transform: `scale(${pulse})`, borderRadius: 18, background: '#11131f',
              border: `1px solid ${locked ? ACC + '66' : '#23273c'}`, boxShadow: 'inset 0 0 60px #0008'}}>
              <div style={{position: 'absolute', top: 0, left: 0, right: 0, transform: `translateY(${offset}px)`}}>
                {strip.map((n, k) => (
                  <div key={k} style={{height: CELL, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    font: `800 196px/1 Inter, system-ui, sans-serif`,
                    color: k === strip.length - 1 && locked ? '#fff' : '#dbe3ff'}}>{n}</div>
                ))}
              </div>
              <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
                background: 'linear-gradient(#11131f, #11131f00 24%, #11131f00 76%, #11131f)'}} />
            </div>
          );
        })}
        {UNIT ? <div style={{font: `800 116px/1 Inter, system-ui, sans-serif`, color: ACC,
          marginLeft: 14, marginBottom: 22}}>{UNIT}</div> : null}
      </div>

      <div style={{marginTop: 48, width: lerp(0, 60 + nDigits * 90, easeOutCubic(seg(t, 0.55, 0.85))),
        height: 5, background: ACC, borderRadius: 3, boxShadow: `0 0 22px ${ACC}`}} />
    </AbsoluteFill>
  );
};
export default OdometerRoll;
