// Probe: what the style engine (runtime/style.tsx) does to things whose places are KNOWN.
//
// A gradient ground, a filled rect, a gradient circle, a stroked line, a hairline under the heading, SVG type, an HTML box holding type and a display heading, each at
// a fixed place (tests/fixtures/style/probe_layout.json names them). tests/test_style_engine.py renders this styled
// and unstyled and asks the pixels: the rect's edge took the outline, the circle went flat, the box took a ring —
// and not one pixel of type changed.
import React from 'react';
import {AbsoluteFill} from 'remotion';

export const StyleProbe: React.FC<{overlay?: boolean; dark?: boolean}> = ({overlay = false, dark = false}) => (
  <AbsoluteFill style={{background: dark ? '#0b0f17' : '#f5f1e8'}}>
    <div data-probe="ground" style={{position: 'absolute', inset: 0, background: dark
      ? 'radial-gradient(circle at 50% 50%, #141b29 0%, #080b11 100%)'
      : 'radial-gradient(circle at 50% 50%, #fbf8f1 0%, #e6dccb 100%)'}} />
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      <defs>
        <linearGradient id="probe-g" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#1d4ed8" />
          <stop offset="1" stopColor="#93c5fd" />
        </linearGradient>
      </defs>
      <rect x={200} y={200} width={400} height={300} fill="#f4d35e" />
      {/* a glint on it: light, not a thing — no outline, no shadow */}
      <ellipse cx={330} cy={260} rx={80} ry={25} fill="#ffffff" fillOpacity={0.35} />
      <circle cx={900} cy={350} r={150} fill="url(#probe-g)" />
      <line x1={1200} y1={200} x2={1700} y2={500} stroke="#333333" strokeWidth={2} />
      {/* a hairline crossing the heading: a line under type keeps the weight it was drawn with */}
      <line x1={760} y1={880} x2={1090} y2={880} stroke="#9ca3af" strokeWidth={1.5} />
      {/* a data series (its colour is the series) over a hairline grid line, and an area fading to nothing */}
      <defs>
        <linearGradient id="probe-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#22c55e" stopOpacity={0.6} />
          <stop offset="1" stopColor="#22c55e" stopOpacity={0} />
        </linearGradient>
      </defs>
      <line x1={1250} y1={1040} x2={1850} y2={1040} stroke="#c8c2b6" strokeWidth={1} />
      <polygon points="1250,1000 1450,880 1650,950 1850,850 1850,1030 1250,1030" fill="url(#probe-area)" />
      <polyline points="1250,1000 1450,880 1650,950 1850,850" fill="none" stroke="#16a34a" strokeWidth={3} />
      <text x={1200} y={700} fontSize={48} fill="#1f2937" fontFamily="sans-serif">SVG 文字</text>
    </svg>
    <div style={{position: 'absolute', left: 200, top: 650, width: 400, height: 200, background: '#3b82f6',
      borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <span style={{color: '#ffffff', fontSize: 40, fontFamily: 'sans-serif'}}>盒子</span>
    </div>
    <div style={{position: 'absolute', left: 800, top: 800, fontSize: 120, lineHeight: '140px', color: '#111827',
      fontFamily: 'sans-serif'}}>标题</div>
    {/* a speck of dust (6 px, round): not a thing — no ring, no shadow */}
    <div data-probe="speck" style={{position: 'absolute', left: 1597, top: 117, width: 6, height: 6, borderRadius: 3,
      background: '#8a7f70'}} />
    {/* a vignette over everything: a translucent ground that must stay translucent */}
    {overlay ? <div data-probe="vignette" style={{position: 'absolute', inset: 0,
      background: 'radial-gradient(circle at 50% 50%, rgba(0, 0, 0, 0) 55%, rgba(0, 0, 0, 0.3) 100%)'}} /> : null}
    {/* a letterbox bar: the frame's own furniture, edge to edge */}
    {overlay ? <div data-probe="letterbox" style={{position: 'absolute', left: 0, right: 0, top: 0, height: 40,
      background: '#000000'}} /> : null}
  </AbsoluteFill>
);
