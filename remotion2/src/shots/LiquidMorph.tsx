// SHOT · Liquid Morph — an ORIGINAL design: one living, iridescent blob of material breathes and MORPHS,
// and the tool it becomes (chat → doc → chart → done) fades through on its surface. "One tool, any shape."
// Dark premium + iridescent gradient. Deterministic (blob vertices = sin of frame).

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';

export const DURATION = 165; // 5.5s
const FORMS = ['ask', 'draft', 'analyse', 'done'];

// a smooth closed organic-blob path from N perturbed points
function blobPath(cx: number, cy: number, R: number, frame: number, wob: number): string {
  const N = 12, pts: [number, number][] = [];
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2;
    const r = R + Math.sin(a * 3 + frame * 0.05) * wob + Math.cos(a * 2 - frame * 0.037) * wob * 0.7;
    pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
  }
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < N; i++) {
    const p0 = pts[i], p1 = pts[(i + 1) % N];
    const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2;
    d += ` Q${p0[0]},${p0[1]} ${mx},${my}`;
  }
  return d + 'Z';
}

const Glyph: React.FC<{form: string; op: number}> = ({form, op}) => {
  const st = {stroke: '#fff', strokeWidth: 10, fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const};
  return <g opacity={op} transform="translate(-70,-70)">
    {form === 'ask' && <><rect x="4" y="10" width="132" height="94" rx="24" {...st} /><path d="M40 104 L40 132 L66 104" {...st} /></>}
    {form === 'draft' && <><rect x="20" y="8" width="100" height="128" rx="12" {...st} /><line x1="40" y1="42" x2="100" y2="42" {...st} /><line x1="40" y1="70" x2="100" y2="70" {...st} /><line x1="40" y1="98" x2="80" y2="98" {...st} /></>}
    {form === 'analyse' && <><line x1="24" y1="122" x2="132" y2="122" {...st} /><rect x="30" y="70" width="24" height="52" {...st} /><rect x="66" y="40" width="24" height="82" {...st} /><rect x="102" y="86" width="24" height="36" {...st} /></>}
    {form === 'done' && <path d="M30 74 L62 108 L118 40" {...st} strokeWidth={14} />}
  </g>;
};

export const LiquidMorph: React.FC = () => {
  const t = useT();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 - 20;
  const idx = clamp01(seg(t, 0.06, 0.96)) * (FORMS.length - 1); // which form (fractional)
  return (
    <AbsoluteFill style={{background: 'radial-gradient(120% 120% at 50% 42%, #141326, #05060d 72%)'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="iri" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#4F7BFF" /><stop offset="0.5" stopColor="#B14BFF" /><stop offset="1" stopColor="#FF5C9A" />
          </linearGradient>
          <filter id="glow"><feGaussianBlur stdDeviation="24" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <path d={blobPath(cx, cy, 300, frame, 34)} fill="url(#iri)" filter="url(#glow)" opacity={0.96} />
        {/* the tool-glyph fades through on the blob surface */}
        <g transform={`translate(${cx},${cy}) scale(1.5)`}>
          {FORMS.map((f, i) => <Glyph key={i} form={f} op={clamp01(1 - Math.abs(idx - i))} />)}
        </g>
      </svg>
      {/* current form label */}
      <div style={{position: 'absolute', left: 0, right: 0, top: cy + 300, textAlign: 'center'}}>
        {FORMS.map((f, i) => <div key={i} style={{position: 'absolute', left: 0, right: 0, font: '800 64px/1 Inter,system-ui,sans-serif',
          color: '#fff', opacity: clamp01(1 - Math.abs(idx - i) * 1.4), textTransform: 'capitalize'}}>{f}.</div>)}
      </div>
    </AbsoluteFill>
  );
};
export default LiquidMorph;
