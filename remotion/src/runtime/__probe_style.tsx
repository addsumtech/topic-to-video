// Probe: what the style engine (runtime/style.tsx) does to things whose places are KNOWN.
//
// A gradient ground, a filled rect, a gradient circle, a stroked line, a hairline under the heading, SVG type, an HTML box holding type and a display heading, each at
// a fixed place (tests/fixtures/style/probe_layout.json names them). tests/test_style_engine.py renders this styled
// and unstyled and asks the pixels: the rect's edge took the outline, the circle went flat, the box took a ring —
// and not one pixel of type changed.
import React from 'react';
import {AbsoluteFill} from 'remotion';

export const StyleProbe: React.FC = () => (
  <AbsoluteFill style={{background: '#f5f1e8'}}>
    <div data-probe="ground" style={{position: 'absolute', inset: 0,
      background: 'radial-gradient(circle at 50% 50%, #fbf8f1 0%, #e6dccb 100%)'}} />
    <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
      <defs>
        <linearGradient id="probe-g" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#1d4ed8" />
          <stop offset="1" stopColor="#93c5fd" />
        </linearGradient>
      </defs>
      <rect x={200} y={200} width={400} height={300} fill="#f4d35e" />
      <circle cx={900} cy={350} r={150} fill="url(#probe-g)" />
      <line x1={1200} y1={200} x2={1700} y2={500} stroke="#333333" strokeWidth={2} />
      {/* a hairline crossing the heading: a line under type keeps the weight it was drawn with */}
      <line x1={760} y1={880} x2={1090} y2={880} stroke="#9ca3af" strokeWidth={1.5} />
      <text x={1200} y={700} fontSize={48} fill="#1f2937" fontFamily="sans-serif">SVG 文字</text>
    </svg>
    <div style={{position: 'absolute', left: 200, top: 650, width: 400, height: 200, background: '#3b82f6',
      borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <span style={{color: '#ffffff', fontSize: 40, fontFamily: 'sans-serif'}}>盒子</span>
    </div>
    <div style={{position: 'absolute', left: 800, top: 800, fontSize: 120, lineHeight: '140px', color: '#111827',
      fontFamily: 'sans-serif'}}>标题</div>
  </AbsoluteFill>
);
