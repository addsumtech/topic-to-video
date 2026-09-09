// SHOT · Hand-drawn / Riso — the "authenticity & imperfection" 2026 trend: a warm-paper sketch where ink
// strokes DRAW ON (rough boxes + arrows), with a two-colour risograph misregistration + grain. Analog, warm,
// hand-made — deliberately unlike every polished-digital shot. Deterministic (wobble seeded by index).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, hash01} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 165; // 5.5s
// LEVEL-C: cream paper + navy ink + red riso → a chalkboard-style dark sketch on a dark DNA (bg→dna.bg, ink→fg,
// riso→accent; the grain switches multiply→screen so it still reads on dark). Sketch takes its colour as a prop,
// so only the main component reads useDNA. Null DNA = the original warm-paper sketch.
const INK = '#243a6b', RISO = '#e0533f';

// a rough hand-drawn rectangle path (jittered corners, slightly overshooting)
function roughRect(x: number, y: number, w: number, h: number, s: number): string {
  const j = (k: number) => (hash01(s * 7 + k) - 0.5) * 10;
  return `M${x + j(1)},${y + j(2)} L${x + w + j(3)},${y + j(4)} L${x + w + j(5)},${y + h + j(6)} L${x + j(7)},${y + h + j(8)} Z`;
}

const Sketch: React.FC<{d: string; t: number; at: number; color: string; sw?: number}> = ({d, t, at, color, sw = 5}) => {
  const draw = clamp01((t - at) / 0.2);
  return <path d={d} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"
    {...drawOn(draw)} />;
};

export const HandDrawn: React.FC<{items?: string[]}> = ({items = ['You', 'WorkBuddy', 'Done ✓']} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? '#f3ecda', INKc = dna?.fg ?? INK, RISOc = dna?.accent ?? RISO, grainBlend = dna ? 'screen' : 'multiply';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  // TWO orientations, decided by whether the ROW fits. Fixed x = 200 + i*570 put the third box at 1340 on a
  // 1080-wide frame ('Done' rode 549px off the edge); the first repair squeezed the step until the boxes
  // OVERLAPPED — which no gate reports, because overlapping each other crosses neither the canvas nor the
  // caption band. It took looking at the frame. A flow chart that cannot run across runs DOWN.
  const horizontal = W >= items.length * 380 + (items.length - 1) * 130 + 80;
  // AND WHEN IT RUNS DOWN IT HAS TO FIT DOWN. Three 240px boxes stepping 336 apart is 912px of chart, and
  // the column was CENTRED on the content zone rather than sized to it — so on a short frame it hung out of
  // both ends: 'Done ✓' 46px inside the caption band at 1:1, and the first box up inside the title band. A
  // hand-drawn chart is a drawing; it scales. `V` is 1 wherever the chart already fitted, which is every
  // frame 1080 or more tall in the vertical branch, so 9:16 and 4:5 are untouched.
  const stackH = 240 + (240 + 96) * (items.length - 1);
  const V = horizontal ? 1 : Math.min(1, (zBot - zTop) / stackH);
  const bw = 380 * V, bh = 240 * V;
  const stepX = 380 + 190, stepY = bh + 96 * V;
  const x0h = (W - (380 + stepX * (items.length - 1))) / 2;
  const y0h = H / 2 - 120;
  const y0v = zTop + ((zBot - zTop) - (bh + stepY * (items.length - 1))) / 2;
  const boxes = items.map((label, i) => ({
    x: horizontal ? x0h + i * stepX : (W - bw) / 2,
    y: horizontal ? y0h : y0v + i * stepY,
    label, at: 0.08 + i * 0.27,
  }));
  return (
    <AbsoluteFill style={{background: BG}}>
      {/* grain */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5, mixBlendMode: grainBlend}}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width={W} height={H} filter="url(#grain)" opacity="0.12" />
      </svg>
      {/* riso misregistered under-layer (warm red, offset) */}
      <svg width={W} height={H} style={{position: 'absolute', left: 6, top: 7, opacity: 0.55}}>
        {boxes.map((b, i) => <Sketch key={i} d={roughRect(b.x, b.y, bw, bh, i + 1)} t={t} at={b.at} color={RISOc} />)}
      </svg>
      {/* ink layer */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {boxes.map((b, i) => <Sketch key={i} d={roughRect(b.x, b.y, bw, bh, i + 1)} t={t} at={b.at} color={INKc} />)}
        {/* hand-drawn arrows between boxes */}
        {[...Array(Math.max(0, boxes.length - 1))].map((_, i) => {
          const d = horizontal
            ? (() => {
                const x1 = boxes[i].x + bw + 8, x2 = boxes[i + 1].x - 8, my = boxes[i].y + bh / 2;
                return `M${x1},${my} C${x1 + 60},${my - 40} ${x2 - 60},${my + 30} ${x2},${my} M${x2 - 26},${my - 16} L${x2},${my} L${x2 - 26},${my + 16}`;
              })()
            : (() => {
                const yA = boxes[i].y + bh + 8, yB = boxes[i + 1].y - 8, mx = W / 2;
                return `M${mx},${yA} C${mx + 46},${yA + 30} ${mx - 36},${yB - 30} ${mx},${yB} M${mx - 16},${yB - 26} L${mx},${yB} L${mx + 16},${yB - 26}`;
              })();
          return <Sketch key={i} d={d} t={t} at={boxes[i].at + 0.16} color={INKc} sw={4} />;
        })}
      </svg>
      {/* labels (slightly rotated for a hand feel) */}
      {boxes.map((b, i) => {
        const show = clamp01((t - b.at - 0.14) / 0.2);
        return <div key={i} style={{position: 'absolute', left: b.x, top: b.y, width: bw, height: bh, display: 'flex',
          alignItems: 'center', justifyContent: 'center', opacity: show, transform: `rotate(${(hash01(i + 9) - 0.5) * 3}deg)`,
          font: `800 ${Math.round(56 * V)}px/1.1 var(--f-body, Inter,system-ui,sans-serif)`, color: INKc, textAlign: 'center'}}>{b.label}</div>;
      })}
    </AbsoluteFill>
  );
};
export default HandDrawn;
