// SHOT · Halftone Pop — a print-comic / pop-art register (Ben-Day dots, primary flats, thick ink): a halftone
// field, radial speed-lines, a jagged comic BURST that pops with bold text, and a bordered caption box that
// slams in. Loud, retro, graphic. Distinct from the cel-shaded CartoonPop (this is PRINT texture, not a mascot).
// Deterministic (pop/slam = eased t).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutExpo} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s
// LEVEL-C: pop-art print is the TECHNIQUE (Ben-Day dots, radial speed lines, a jagged burst, thick panel rule,
// a slammed caption box). On a themed DNA the stock goes dark, the ink inverts to light and the dots/box take the
// DNA accents — an inked night-press poster. Null DNA = the original yellow/red pop page.
const YEL0 = '#ffcf2e', RED0 = '#f24b3a', INK0 = '#171717', BLUE0 = '#2b57ff';

function jaggedBurst(cx: number, cy: number, n: number, ro: number, ri: number): string {
  const pts: string[] = [];
  for (let i = 0; i < n * 2; i++) {
    const r = i % 2 === 0 ? ro : ri * (0.82 + 0.18 * ((i * 7) % 5) / 4);
    const a = (Math.PI / n) * i - Math.PI / 2;
    pts.push(`${(cx + Math.cos(a) * r).toFixed(1)},${(cy + Math.sin(a) * r).toFixed(1)}`);
  }
  return 'M' + pts.join('L') + 'Z';
}

export const HalftonePop: React.FC<{lead?: string; burstTop?: string; burstBottom?: string; brand?: string}> = ({
  lead = 'MEANWHILE…',
  burstTop = 'SHIP', burstBottom = 'IT!', brand = 'WorkBuddy'} = {}) => {
  const dna = useDNA();
  const YEL = dna?.bg ?? YEL0, RED = dna?.accent ?? RED0, INK = dna?.fg ?? INK0, BLUE = dna?.accent2 ?? BLUE0;
  const BURST_SHADOW = dna ? BLUE : INK0;     // the offset copy: black ink on paper, a colour offset on dark stock
  const BURST_BODY = dna?.fg ?? '#ffffff';    // the burst's bright body (the rim you read the type against)
  const BURST_IN = dna?.surface ?? YEL0;      // its inner fill
  const CARD = dna?.surface ?? '#fff';        // the caption box stock
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 - 20;
  const pop = easeOutBack(seg(t, 0.14, 0.4));
  const lines = easeOutExpo(seg(t, 0.08, 0.5));
  const slam = easeOutBack(seg(t, 0.5, 0.72));
  const spin = t * 12;

  return (
    <AbsoluteFill style={{background: YEL, overflow: 'hidden'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <pattern id="benday" width="26" height="26" patternUnits="userSpaceOnUse" patternTransform="rotate(12)">
            <circle cx="7" cy="7" r="5.5" fill={RED} opacity="0.85" />
          </pattern>
        </defs>
        {/* halftone field (bottom-right diagonal) */}
        <path d={`M0,${H} L${W},${H} L${W},0 L${W * 0.42},${H} Z`} fill="url(#benday)" opacity="0.9" />
        {/* radial speed lines */}
        <g opacity={lines}>
          {[...Array(40)].map((_, i) => {
            const a = (i / 40) * Math.PI * 2 + spin * 0.02;
            const r0 = 300, r1 = 300 + (700 + (i % 3) * 120) * lines;
            const w = (i % 2) ? 6 : 3;
            return <line key={i} x1={cx + Math.cos(a) * r0} y1={cy + Math.sin(a) * r0} x2={cx + Math.cos(a) * r1} y2={cy + Math.sin(a) * r1} stroke={INK} strokeWidth={w} />;
          })}
        </g>
        {/* burst */}
        <g transform={`translate(${cx} ${cy}) scale(${pop}) rotate(${spin * 0.1})`} opacity={pop > 0 ? 1 : 0}>
          <path d={jaggedBurst(8, 10, 16, 330, 220)} fill={BURST_SHADOW} />
          <path d={jaggedBurst(0, 0, 16, 330, 220)} fill={BURST_BODY} />
          <path d={jaggedBurst(0, 0, 16, 300, 200)} fill={BURST_IN} opacity={0.9} />
        </g>
      </svg>

      {/* burst text */}
      <div style={{position: 'absolute', left: cx, top: cy, transform: `translate(-50%,-50%) scale(${pop}) rotate(-8deg)`, textAlign: 'center'}}>
        <div style={{font: '900 150px/0.86 var(--f-display, "Bangers", "Anton", Impact, sans-serif)', color: RED, WebkitTextStroke: `8px ${INK}`,
          paintOrder: 'stroke', letterSpacing: '0.01em'}}>{burstTop}<br />{burstBottom}</div>
      </div>

      {/* caption box slams in */}
      <div style={{position: 'absolute', left: 90, top: H - 250, transform: `rotate(-3deg) scale(${slam})`, transformOrigin: 'left center',
        opacity: slam > 0 ? 1 : 0}}>
        <div style={{background: CARD, border: `7px solid ${INK}`, boxShadow: `12px 12px 0 ${BLUE}`, padding: '20px 34px',
          font: '800 52px/1.05 var(--f-body, "Bangers", Anton, Impact, sans-serif)', color: INK, letterSpacing: '0.02em'}}>
          MEANWHILE… <span style={{color: BLUE}}>{brand}</span> delivers.
        </div>
      </div>

      {/* thick panel border */}
      <div style={{position: 'absolute', inset: 26, border: `12px solid ${INK}`, borderRadius: 6, pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
export default HalftonePop;
