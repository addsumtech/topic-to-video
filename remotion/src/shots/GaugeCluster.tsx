// SHOT · Gauge Cluster — a dashboard of circular gauges: two satellites sweep their arcs first, then the HERO
// gauge sweeps a 270° arc, its needle rising to the readout, and the big value counts up + locks. The
// "instrument panel / live status" register (family D). The value is number-bearing → a real film passes a
// SOURCED figure (see NUM guard). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {bottomTextY} from '../runtime/layout';

const BG = '#0a0c13', ACC0 = '#37d4a6';
export const DURATION = 145; // ~4.8s

const arcPath = (cx: number, cy: number, r: number, a0: number, a1: number) => {
  const p = (a: number) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M${x0} ${y0} A${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
};

const Gauge: React.FC<{cx: number; cy: number; r: number; fill: number; tone: string; label: string; big?: string; unit?: string}> = ({
  cx, cy, r, fill, tone, label, big, unit}) => {
  const START = Math.PI * 0.75, SWEEP = Math.PI * 1.5; // 270°, bottom gap
  const a1 = START + SWEEP * clamp01(fill);
  const needle = START + SWEEP * clamp01(fill);
  return (
    <g>
      <path d={arcPath(cx, cy, r, START, START + SWEEP)} fill="none" stroke="#20263a" strokeWidth={r * 0.16} strokeLinecap="round" />
      <path d={arcPath(cx, cy, r, START, a1)} fill="none" stroke={tone} strokeWidth={r * 0.16} strokeLinecap="round"
        style={{filter: `drop-shadow(0 0 ${r * 0.06}px ${tone})`}} />
      <line x1={cx} y1={cy} x2={cx + r * 0.72 * Math.cos(needle)} y2={cy + r * 0.72 * Math.sin(needle)}
        stroke="#e7ebf7" strokeWidth={r > 130 ? 6 : 4} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={r * 0.09} fill="#e7ebf7" />
      {big ? (
        <text x={cx} y={cy + r * 0.42} textAnchor="middle" fill="#fff"
          style={{font: `800 ${r * 0.42}px var(--f-display, Inter, system-ui, sans-serif)`}}>{big}<tspan fill={tone} style={{font: `800 ${r * 0.24}px var(--f-display, Inter)`}}>{unit}</tspan></text>
      ) : null}
      <text x={cx} y={cy + r * 1.42} textAnchor="middle" fill="#8b93a8"
        style={{font: '600 24px var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.1em'}}>{label}</text>
    </g>
  );
};

export const GaugeCluster: React.FC<{value?: string; unit?: string; label?: string; gauges?: {label?: string; fill?: number}[]; title?: string}> = ({
  value: VALUE = '98', unit: UNIT = '%', label: LABEL = 'uptime', title: TITLE = 'System health',
  gauges: SATS = [{label: 'latency', fill: 0.62}, {label: 'load', fill: 0.44}]} = {}) => {
  const t = useT();
  const dna = useDNA(); const ACC = dna?.accent ?? ACC0;   // inherit the film's Design DNA (else original look)
  const {width: W, height: H} = useVideoConfig();
  // EVERY OFFSET IN THIS CLUSTER WAS A 1920-WIDE NUMBER. It is 580px from the centre to the outer edge of a
  // side gauge (470 to its centre, plus its 110 radius) against a 540px half-frame at 1:1 — so both side
  // gauges hung off the edge with their labels cut, at 1:1, 4:5 AND 9:16. The type gate never said so
  // because what is cut is an ARC, and it measures text. Scale the cluster to the room it has.
  const HALF = 470 + 110;                                  // the cluster's half-width as drawn
  const S = Math.min(1, (W / 2 - 40) / HALF);
  const rHero = 210 * S, rSide = 110 * S, off = 470 * S;
  // and the hero's label is a BASELINE r*1.42 below the centre, so the centre yields where the band is
  // taller — 31px of 'uptime' was inside it at 1:1.
  const cx = W / 2, cy = Math.min(H / 2 + 20, bottomTextY(W, H) - rHero * 1.42);
  const heroFill = easeOutExpo(seg(t, 0.34, 0.78));
  const num = Math.round(parseFloat(String(VALUE).replace(/[^\d.]/g, '') || '0') * heroFill);
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? `radial-gradient(120% 100% at 50% 40%, #12182c, ${BG} 72%)`}}>
      <div style={{position: 'absolute', top: 74, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: '#aeb6ca', font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em',
        textTransform: 'uppercase'}}>{TITLE}</div>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <Gauge cx={cx - off} cy={cy} r={rSide} fill={easeOutExpo(seg(t, 0.12, 0.5)) * (SATS[0]?.fill ?? 0.6)}
          tone={dna?.accent2 ?? "#5b8cff"} label={SATS[0]?.label ?? ''} />
        <Gauge cx={cx + off} cy={cy} r={rSide} fill={easeOutExpo(seg(t, 0.2, 0.58)) * (SATS[1]?.fill ?? 0.5)}
          tone={dna?.dim ?? "#f6a531"} label={SATS[1]?.label ?? ''} />
        <Gauge cx={cx} cy={cy} r={rHero} fill={heroFill * clamp01(parseFloat(String(VALUE).replace(/[^\d.]/g, '') || '0') / 100)}
          tone={ACC} label={LABEL} big={String(num)} unit={UNIT} />
      </svg>
    </AbsoluteFill>
  );
};
export default GaugeCluster;
