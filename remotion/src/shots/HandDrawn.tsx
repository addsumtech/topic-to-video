// SHOT · Hand-drawn / Riso — the "authenticity & imperfection" 2026 trend: a warm-paper sketch where ink
// strokes DRAW ON (rough boxes + arrows), with a two-colour risograph misregistration + grain. Analog, warm,
// hand-made — deliberately unlike every polished-digital shot. Deterministic (wobble seeded by index).
//
// EVERY STEP IS DRAWN AND LABELLED BEFORE THE FRAME IS READ. Box i used to start at `0.08 + i * 0.27` — a
// fixed step — with its label fading in 0.14 after it over 0.2, so even the demo's THIRD label was only half in
// on the settled frame (t = 0.86, the frame every gate and the shot-critic read, and the one reduced motion
// freezes on), a fourth box was half drawn when the clip ended with its label never appearing, and a fifth
// never started. The step is now laid out for the count — 0.27 stays the upper bound, so two steps keep their
// exact rhythm — and closes until the last label is fully in by LAND_BY. Past MAX_HAND_ITEMS a hand-drawn flow
// stops reading as a sketch and the boxes shrink toward illegible, so the register refuses.
//
// AND A ROW THAT DOES NOT FIT AT FULL SIZE NO LONGER FALLS STRAIGHT TO A COLUMN. Four steps on a 16:9 frame
// went DOWN at 0.56 scale — four small boxes stacked in the middle of a wide frame — when the same four run
// ACROSS at 0.88. The chart now takes whichever orientation lets it be drawn larger; every case that already
// fitted a full-size row, or a column, is unchanged.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {clamp01, hash01, useT, REDUCED_MOTION_T} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 165; // 5.5s
// LEVEL-C: cream paper + navy ink + red riso → a chalkboard-style dark sketch on a dark DNA (bg→dna.bg, ink→fg,
// riso→accent; the grain switches multiply→screen so it still reads on dark). Sketch takes its colour as a prop,
// so only the main component reads useDNA. Null DNA = the original warm-paper sketch.
const INK = '#243a6b', RISO = '#e0533f';
export const MAX_HAND_ITEMS = 5;
// Box i starts drawing at BOX_START + i * step and takes BOX_DRAW; its label fades in LABEL_DELAY after the
// box over LABEL_FADE, so an item has landed LABEL_DELAY + LABEL_FADE after it starts. BOX_STEP is the original
// gap and only an upper bound — the real step is derived from the count so the last label is in by LAND_BY.
const BOX_START = 0.08, BOX_STEP = 0.27, BOX_DRAW = 0.2, LABEL_DELAY = 0.14, LABEL_FADE = 0.2, ARROW_DELAY = 0.16;
const LAND_BY = REDUCED_MOTION_T - 0.02;

// a rough hand-drawn rectangle path (jittered corners, slightly overshooting)
function roughRect(x: number, y: number, w: number, h: number, s: number): string {
  const j = (k: number) => (hash01(s * 7 + k) - 0.5) * 10;
  return `M${x + j(1)},${y + j(2)} L${x + w + j(3)},${y + j(4)} L${x + w + j(5)},${y + h + j(6)} L${x + j(7)},${y + h + j(8)} Z`;
}

const Sketch: React.FC<{d: string; t: number; at: number; color: string; sw?: number}> = ({d, t, at, color, sw = 5}) => {
  const draw = clamp01((t - at) / BOX_DRAW);
  return <path d={d} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"
    {...drawOn(draw)} />;
};

export const HandDrawn: React.FC<{items?: string[]}> = ({items = ['You', 'WorkBuddy', 'Done ✓']} = {}) => {
  if (!Array.isArray(items) || items.length < 1 || items.length > MAX_HAND_ITEMS) {
    throw new Error(
      `HandDrawn needs 1-${MAX_HAND_ITEMS} \`items\` (got ${Array.isArray(items) ? items.length : typeof items}). ` +
      'Each is a box sketched in turn and must be drawn and labelled before the settled frame; past ' +
      `${MAX_HAND_ITEMS} the sketch stops reading as a hand-drawn flow. Use InOrder for a longer sequence.`);
  }
  items.forEach((label, i) => {
    if (typeof label !== 'string' || !label.trim()) {
      throw new Error(`HandDrawn: item ${i + 1} has no label (got ${JSON.stringify(label)}). Every box carries ` +
        'the step it stands for; pass a non-empty string for each.');
    }
  });
  const n = items.length;
  const step = n > 1 ? Math.min(BOX_STEP, (LAND_BY - BOX_START - LABEL_DELAY - LABEL_FADE) / (n - 1)) : BOX_STEP;
  const dna = useDNA();
  const BG = dna?.bg ?? '#f3ecda', INKc = dna?.fg ?? INK, RISOc = dna?.accent ?? RISO, grainBlend = dna ? 'screen' : 'multiply';
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  // TWO orientations, decided by whether the ROW fits. Fixed x = 200 + i*570 put the third box at 1340 on a
  // 1080-wide frame ('Done' rode 549px off the edge); the first repair squeezed the step until the boxes
  // OVERLAPPED — which no gate reports, because overlapping each other crosses neither the canvas nor the
  // caption band. It took looking at the frame. A flow chart that cannot run across runs DOWN.
  const rowFits = W >= n * 380 + (n - 1) * 130 + 80;
  // AND WHEN IT RUNS DOWN IT HAS TO FIT DOWN. Three 240px boxes stepping 336 apart is 912px of chart, and
  // the column was CENTRED on the content zone rather than sized to it — so on a short frame it hung out of
  // both ends: 'Done ✓' 46px inside the caption band at 1:1, and the first box up inside the title band. A
  // hand-drawn chart is a drawing; it scales. `V` is 1 wherever the chart already fitted, which is every
  // frame 1080 or more tall in the vertical branch, so 9:16 and 4:5 are untouched.
  const stackH = 240 + (240 + 96) * (n - 1);
  const V = Math.min(1, (zBot - zTop) / stackH);
  // The row, scaled to 92% of the frame's width (a full-size row keeps its own 40px margins), is the other
  // candidate; the larger drawing wins (see the header).
  const Hs = Math.min(1, (W * 0.92) / (380 + 570 * (n - 1)));
  const horizontal = rowFits || Hs > V;
  const S = rowFits ? 1 : horizontal ? Hs : V;       // one scale for boxes, gaps, labels and arrows
  const bw = 380 * S, bh = 240 * S;
  const stepX = (380 + 190) * S, stepY = bh + 96 * S;
  const x0h = (W - (bw + stepX * (n - 1))) / 2;
  const y0h = H / 2 - bh / 2;
  const y0v = zTop + ((zBot - zTop) - (bh + stepY * (n - 1))) / 2;
  const boxes = items.map((label, i) => ({
    x: horizontal ? x0h + i * stepX : (W - bw) / 2,
    y: horizontal ? y0h : y0v + i * stepY,
    label, at: BOX_START + i * step,
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
                const x1 = boxes[i].x + bw + 8 * S, x2 = boxes[i + 1].x - 8 * S, my = boxes[i].y + bh / 2;
                return `M${x1},${my} C${x1 + 60 * S},${my - 40 * S} ${x2 - 60 * S},${my + 30 * S} ${x2},${my} M${x2 - 26 * S},${my - 16 * S} L${x2},${my} L${x2 - 26 * S},${my + 16 * S}`;
              })()
            : (() => {
                const yA = boxes[i].y + bh + 8 * S, yB = boxes[i + 1].y - 8 * S, mx = W / 2;
                return `M${mx},${yA} C${mx + 46 * S},${yA + 30 * S} ${mx - 36 * S},${yB - 30 * S} ${mx},${yB} M${mx - 16 * S},${yB - 26 * S} L${mx},${yB} L${mx + 16 * S},${yB - 26 * S}`;
              })();
          return <Sketch key={i} d={d} t={t} at={boxes[i].at + ARROW_DELAY} color={INKc} sw={4} />;
        })}
      </svg>
      {/* labels (slightly rotated for a hand feel) */}
      {boxes.map((b, i) => {
        const show = clamp01((t - b.at - LABEL_DELAY) / LABEL_FADE);
        return <div key={i} style={{position: 'absolute', left: b.x, top: b.y, width: bw, height: bh, display: 'flex',
          alignItems: 'center', justifyContent: 'center', opacity: show, transform: `rotate(${(hash01(i + 9) - 0.5) * 3}deg)`,
          font: `800 ${Math.round(56 * S)}px/1.1 var(--f-body, Inter,system-ui,sans-serif)`, color: INKc, textAlign: 'center'}}>{b.label}</div>;
      })}
    </AbsoluteFill>
  );
};
export default HandDrawn;
