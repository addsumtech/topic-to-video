// SHOT · Liquid Fill — a fluid-progress register: a round vessel FILLS with gooey liquid (wobbling wave surface
// + rising metaball bubbles that merge via an SVG gooey filter), a % counts up, and at full it settles with a
// checkmark. The "watch it complete" beat as real fluid, not a bar. Deterministic (level + waves = fn of t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutBack} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 160; // ~5.3s

export const LiquidFill: React.FC<{label?: string}> = ({label = 'on your machine'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2, R = 300;
  const p = easeInOutCubic(seg(t, 0.1, 0.82));   // fill fraction
  const level = cy + R - 2 * R * p;               // liquid surface y
  const pct = Math.round(p * 100);
  const done = seg(t, 0.82, 1);

  // wave surface path across the vessel bbox, clipped to the circle
  const wave = (amp: number, k: number, phase: number, extra: number) => {
    const x0 = cx - R - 20, x1 = cx + R + 20, steps = 28;
    let d = `M${x0},${level + extra}`;
    for (let i = 0; i <= steps; i++) {
      const x = lerp(x0, x1, i / steps);
      const y = level + extra + Math.sin((x / (2 * R)) * k * Math.PI * 2 + phase) * amp;
      d += ` L${x.toFixed(1)},${y.toFixed(1)}`;
    }
    d += ` L${x1},${cy + R + 40} L${x0},${cy + R + 40} Z`;
    return d;
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 30%, #0d1830 0%, #060b18 70%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <clipPath id="vessel"><circle cx={cx} cy={cy} r={R} /></clipPath>
          <filter id="goo"><feGaussianBlur in="SourceGraphic" stdDeviation="11" result="b" />
            <feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -10" result="g" />
            <feBlend in="SourceGraphic" in2="g" /></filter>
          <linearGradient id="liq" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#38e0d0" /><stop offset="1" stopColor="#2a7bff" /></linearGradient>
          <filter id="lglow"><feGaussianBlur stdDeviation="8" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>

        {/* liquid + bubbles, merged by the gooey filter, clipped to the vessel */}
        <g clipPath="url(#vessel)">
          <g filter="url(#goo)" fill="url(#liq)">
            <path d={wave(20, 2, t * 7, 0)} opacity={0.95} />
            <path d={wave(14, 3, t * 9 + 1.6, 8)} opacity={0.6} />
            {/* rising metaball bubbles inside the liquid */}
            {[0, 1, 2, 3].map((i) => {
              const rise = ((t * (0.5 + i * 0.12) + i * 0.25) % 1);
              const by = (cy + R) - rise * (2 * R * p + 40);
              const bx = cx + Math.sin(i * 2 + t * 3) * (R * 0.5);
              if (by > level - 6) return <circle key={i} cx={bx} cy={by} r={16 + (i % 2) * 10} />;
              return null;
            })}
          </g>
        </g>

        {/* vessel ring */}
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="#4b6a9c" strokeWidth={6} />
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="#7fd8ff" strokeWidth={2} opacity={0.5} filter="url(#lglow)" />
      </svg>

      {/* centre readout: % counting, then a checkmark */}
      <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        {done < 0.15 ? (
          <div style={{color: '#eaf6ff', font: '800 150px/1 Inter, system-ui, sans-serif', fontVariantNumeric: 'tabular-nums',
            textShadow: '0 4px 30px #000a'}}>{pct}<span style={{fontSize: 70, opacity: 0.7}}>%</span></div>
        ) : (
          <svg width={360} height={360} viewBox="-180 -180 360 360" style={{transform: `scale(${easeOutBack(done)})`}}>
            <path d="M-88,6 L-26,74 L96,-78" fill="none" stroke="#eafff8" strokeWidth={34} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </AbsoluteFill>
      <div style={{position: 'absolute', left: 0, right: 0, top: cy + R + 70, textAlign: 'center',
        color: '#8fb0d8', font: '600 34px/1 "JetBrains Mono", monospace', letterSpacing: '0.06em'}}>{label}</div>
    </AbsoluteFill>
  );
};
export default LiquidFill;
