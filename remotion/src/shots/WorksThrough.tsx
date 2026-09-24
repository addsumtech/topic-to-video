// SHOT · WorksThrough — the subject cut open, and the live path that threads THROUGH its parts.
//
// THE ARGUMENT SHAPE, and why boxes-and-arrows cannot carry it. MECHANISM is the emptiest shape in this
// library: clustered by the claim their "use when" makes, the mechanism registers measure a median of 2.4%
// ink and NONE clears the 12% floor. `RestsOn`'s header named the cause — "a mechanism is a RELATION, and
// relations are conventionally drawn as boxes and arrows" — and an arrow carries no information beyond
// "connected", so the frame is empty by construction. `MadeOf` escaped that by making the QUANTITY the
// pixels: every region's AREA is its share, 52.6% ink, all three floors clear.
//
// This takes the same route by a different road: the body is SECTIONED and fills the frame, so the density
// is the subject itself; and the mechanism is a path that runs INSIDE it, deflected by each part it passes
// through. A part the path crosses is doing work. A part it does not touch is context. Cover the caption
// and the frame still says "this is what is actually happening in there, and these are the parts it
// happens in".
//
// A FIRST DESIGN WAS BUILT AND DELETED. It drew the mechanism as a chain under load that parts at its
// thinnest link. It cleared the density floor (29.7%) and still went, because the claim it drew was
// NECESSITY — every link must hold — which `HardBarrier` and `RestsOn` already make, and because four
// renders in it still read as "rectangles of different sizes with a gap". Density without the argument is
// the exact trap the density study names: this library is dense where it says nothing.
//
// WHAT IT IS NOT. `RestsOn` is what holds a phenomenon UP (static, depth of explanation). `GearTrain` is
// TRANSMISSION, every gear surviving. `InOrder` is TIME. `MRIPipeline` is four stages side by side — the
// difference is that there the stages are separate pictures, and here there is ONE body and the path is
// inside it. `MadeOf` partitions and has no path: it answers "what is it made of", not "how does it work".
//
// EVERY WORD COMES FROM A PROP. `carries` is unitless and never printed — it sets the path's width where
// it crosses that part, so the register can show attenuation without putting a figure on screen that no
// source supports.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP, inkBlockH, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix, readableOn, dimOn} from '../runtime/dna';
import {rows} from '../runtime/rows';

export const DURATION = 180; // 6s — the path has to be seen TRAVELLING, or it is just a drawn line

const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', ACC_D0 = '#e0563f', DIM_D0 = '#7b8a9c', LINE_D0 = '#22303f';

export const MAX_PARTS = 5;
const PATH_MIN = 0.16, PATH_MAX = 0.42;   // the path's width across a part, as a fraction of its bay height

type Part = {
  /** what this part of the subject is, in the film's words */
  label?: string;
  /** what it does to what passes through — the film's own reading. Unitless; sets the path's width. */
  carries?: number;
  /** how far the path is deflected in this part, -1 (up) .. 1 (down). The film says where it goes. */
  deflect?: number;
};

const DEMO_PARTS: Part[] = [
  {label: 'where it goes in', carries: 1, deflect: -0.35},
  {label: 'what changes it', carries: 0.8, deflect: 0.45},
  {label: 'what most of it is lost to', carries: 0.3, deflect: -0.2},
  {label: 'what comes out', carries: 0.28, deflect: 0.1},
];

export const WorksThrough: React.FC<{
  kicker?: string;
  /** what is cut open */
  subject?: string;
  /** the parts the path runs through, in the order it reaches them — 2 to MAX_PARTS */
  parts?: Part[];
  /** what arrives at the far end, in the film's words */
  outcome?: string;
  /** one line under the section, in the film's voice */
  note?: string;
}> = ({kicker: KICK = 'WHAT HAPPENS INSIDE', subject: SUBJ = 'the subject, cut open',
       parts: PARTS_IN = DEMO_PARTS, outcome: OUT = 'what comes out',
       note: NOTE = 'the parts the path runs through are the ones doing the work'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  const parts = rows<Part>(PARTS_IN, 'parts', 'WorksThrough')
    .filter((p) => p && String(p.label ?? '').trim());
  if (parts.length < 2) {
    throw new Error(
      'WorksThrough needs at least two parts with a `label`. A mechanism with one part is a label on a box; ' +
      'the claim this register draws is that something travels THROUGH several of them.');
  }
  if (parts.length > MAX_PARTS) {
    throw new Error(
      `WorksThrough was given ${parts.length} parts and sections at most ${MAX_PARTS}; past that each bay ` +
      'is too narrow for the path to visibly deflect inside it, and the deflection is the picture. Group them.');
  }
  if (!parts.some((p) => Number(p.carries) > 0)) {
    throw new Error(
      'WorksThrough needs a `carries` above zero on at least one part — the path\'s width across a part IS ' +
      'how much gets through it, and a path of zero width everywhere draws a mechanism that does nothing.');
  }

  const BG = dna?.bgGrad ?? dna?.bg ?? BG_D0;
  const FLAT = dna?.bg ?? BG_D0;
  const FG = readableOn(FLAT, dna?.fg ?? FG_D0, '#ffffff', '#0a0d14');
  const ACC = dna?.accent ?? ACC_D0;
  const DIM = dimOn(FLAT, FG, 4.5);
  const LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? mix(FG, FLAT, 0.86);
  const body = 'var(--f-body, system-ui, sans-serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';

  const zTop = CONTENT_TOP;
  const zBot = H - captionBand(W, H);
  const KICK_PX = Math.round(U * 0.017), NOTE_PX = Math.round(U * 0.019), LAB_PX = Math.round(U * 0.02);
  const noteH = NOTE ? inkBlockH(NOTE_PX, wrapLines(String(NOTE), NOTE_PX, W * 0.84)) + U * 0.028 : 0;

  const kickIn = clamp01(seg(t, 0.02, 0.10));
  const cutIn = easeOutCubic(clamp01(seg(t, 0.06, 0.30)));      // the body being sectioned
  const run = easeOutCubic(clamp01(seg(t, 0.28, 0.76)));        // the path travelling through it
  const outIn = clamp01(seg(t, 0.72, 0.84));
  const noteIn = clamp01(seg(t, 0.74, 0.86));

  // THE SECTION fills the content zone. Its area is where the density comes from.
  const sx0 = W * 0.06, sx1 = W * 0.83;                          // the outcome lives to the right of it
  const sy0 = zTop + U * 0.055, sy1 = zBot - noteH - U * 0.03;
  const bayW = (sx1 - sx0) / parts.length;
  const midY = (sy0 + sy1) / 2;
  const bayH = sy1 - sy0;

  // the path's centre-line: entering at the middle, deflected by each part the film says deflects it
  // BOUNDED THE WAY `carries` IS. The prop documents itself as -1..1 and nothing held it there, so a film
  // that sent 3 would have pushed the path clean out of the section it is supposed to be threading — the
  // one place a mechanism register must never draw. A deflection is a degree, not a claim, so it clamps
  // rather than refusing; at the bound the band's far edge still sits inside the section by construction
  // (0.26 + PATH_MAX/2 = 0.47 of a bay's half-height).
  const nodeY = (i: number) =>
    midY + Math.max(-1, Math.min(1, Number(parts[i].deflect) || 0)) * bayH * 0.26;
  const halfW = (i: number) => bayH * (PATH_MIN + (PATH_MAX - PATH_MIN)
    * clamp01(Number(parts[i].carries) || 0)) / 2;

  // THE PATH RAMPS ACROSS THE PART THAT DEFLECTS IT; IT DOES NOT STEP AT THE EDGE BETWEEN TWO PARTS.
  // The first version held one y for the whole bay and put two vertices at the same x on the boundary, so
  // every change of direction was a vertical segment of ZERO WIDTH. With the demo's gentle deflections the
  // neighbouring bands overlapped and it read as a path anyway; fed ±0.9 on five parts it rendered as five
  // disconnected rectangles — no path at all, which is the one thing this register claims. So the centre
  // line ENTERS a bay where the previous part left it and reaches this part's own value by the bay's end:
  // the deflection is then visibly done BY the part, and the band is continuous whatever the film sends.
  const yIn = (i: number) => (i === 0 ? midY : nodeY(i - 1));
  const hIn = (i: number) => halfW(i === 0 ? 0 : i - 1);
  const bayOf = (x: number) =>
    Math.min(parts.length - 1, Math.max(0, Math.floor((x - sx0) / bayW)));
  const atX = (x: number) => {
    const i = bayOf(x);
    const f = clamp01((x - (sx0 + i * bayW)) / bayW);
    return {y: yIn(i) + (nodeY(i) - yIn(i)) * f, h: hIn(i) + (halfW(i) - hIn(i)) * f};
  };

  const top: string[] = [], bot: string[] = [];
  const reach = sx0 + (sx1 - sx0) * run;
  // vertices at every bay boundary — the centre line is piecewise linear and breaks only there — plus one
  // at the travelling head, so the band is cut flat wherever the path has got to.
  const xs: number[] = [];
  for (let i = 0; i <= parts.length; i++) {
    const x = sx0 + i * bayW;
    if (x <= reach) xs.push(x);
  }
  if (xs.length && reach > xs[xs.length - 1]) xs.push(reach);
  for (const x of xs) {
    const {y, h} = atX(x);
    top.push(`${x},${y - h}`);
    bot.unshift(`${x},${y + h}`);
  }

  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {KICK ? (
        <div style={{position: 'absolute', left: sx0, top: zTop, opacity: kickIn, color: DIM,
          letterSpacing: dna?.labelSpacing ?? '0.16em', font: `700 ${KICK_PX}px/1.2 ${mono}`}}>
          {dna?.uppercaseLabels === false ? KICK : String(KICK).toUpperCase()}
        </div>
      ) : null}

      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          {/* SECTION HATCHING — the convention that says "this is cut, you are looking at material". It is
              also most of the ink, and it is ink that MEANS something: it is the body of the subject. */}
          <pattern id="wt-hatch" width={Math.round(U * 0.018)} height={Math.round(U * 0.018)}
            patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2={Math.round(U * 0.018)} stroke={mix(FG, FLAT, 0.80)}
              strokeWidth={Math.max(1, U * 0.0015)} />
          </pattern>
        </defs>

        {/* the sectioned body, bay by bay, revealed left to right as the cut opens */}
        {parts.map((_p, i) => {
          const x = sx0 + i * bayW;
          const w = bayW * clamp01((cutIn * parts.length) - i);
          if (w <= 0) return null;
          return (
            <g key={i}>
              <rect x={x} y={sy0} width={w} height={bayH} fill={SURF} opacity={0.55} />
              <rect x={x} y={sy0} width={w} height={bayH} fill="url(#wt-hatch)" opacity={0.5} />
              <rect x={x} y={sy0} width={w} height={bayH} fill="none" stroke={LINE}
                strokeWidth={Math.max(1, U * 0.0016)} />
            </g>
          );
        })}

        {/* THE PATH, inside the body. Its width across a bay is what gets through that part. */}
        {top.length >= 2 ? (
          <polygon points={[...top, ...bot].join(' ')} fill={ACC} opacity={0.92} />
        ) : null}
      </svg>

      {/* the subject, named on the section itself */}
      <div style={{position: 'absolute', left: sx0 + U * 0.014, top: sy0 + U * 0.014, opacity: cutIn,
        color: DIM, font: `600 ${KICK_PX}px/1.2 ${mono}`, letterSpacing: dna?.labelSpacing ?? '0.12em'}}>
        {SUBJ}
      </div>

      {parts.map((p, i) => {
        const x = sx0 + i * bayW;
        const shown = clamp01((cutIn * parts.length) - i);
        // CLEAR OF THE PATH, AND INSIDE THE SECTION. A label goes to whichever side of the path has more
        // room in this bay — reading the DEFLECTION instead put it on the crowded side whenever the path
        // sat low, which printed it across the path itself. Same class as `placeLabel`'s rule for a point
        // near an edge: choose by the room left, never by which half the thing is in.
        const lab = inkBlockH(LAB_PX, wrapLines(String(p.label), LAB_PX, bayW - U * 0.024));
        // the band SLOPES across the bay now, so its room is measured against the whole span it occupies
        // here — not against the one y it happens to hold at the bay's right edge.
        const bTop = Math.min(yIn(i) - hIn(i), nodeY(i) - halfW(i));
        const bBot = Math.max(yIn(i) + hIn(i), nodeY(i) + halfW(i));
        const above = bTop - sy0;                                  // room over the path in this bay
        const under = sy1 - bBot;                                  // room under it
        const y = under >= above
          ? Math.min(bBot + U * 0.022, sy1 - lab - U * 0.014)
          : Math.max(bTop - lab - U * 0.022, sy0 + U * 0.05);
        return (
          <div key={i} style={{position: 'absolute', left: x + U * 0.012, top: y,
            width: bayW - U * 0.024, opacity: shown, color: FG, textWrap: 'balance',
            font: `600 ${LAB_PX}px/${leading(String(p.label), 1.35)} ${body}`}}>
            {p.label}
          </div>
        );
      })}

      {/* what arrives, outside the cut — the path runs out of the body and lands on it */}
      <div style={{position: 'absolute', left: sx1 + U * 0.02, top: nodeY(parts.length - 1) - U * 0.03,
        width: W - sx1 - U * 0.05, opacity: outIn, color: ACC, textWrap: 'balance',
        font: `800 ${Math.round(U * 0.026)}px/${leading(String(OUT), 1.25)} ${body}`}}>{OUT}</div>

      {NOTE ? (
        <div style={{position: 'absolute', left: sx0, width: W * 0.84, top: zBot - noteH, opacity: noteIn,
          color: DIM, font: `400 ${NOTE_PX}px/${leading(String(NOTE), 1.4)} ${body}`,
          borderTop: `1px solid ${LINE}`, paddingTop: Math.round(U * 0.012)}}>{NOTE}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export default WorksThrough;
