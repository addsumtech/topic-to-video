// SHOT · Circuit Trace — a PCB comes alive: copper traces route (Manhattan bends) between chips and pads and
// DRAW ON, signal pulses race along them, and a central chip lights up. A hardware / systems register
// (family T · circuit/hardware). Deterministic (trace draw + pulse position = fn of t).
//
// EVERY NODE IS A PAD, AND THE RING IS SPACED FOR THE PADS IT HAS. It used to draw `nodes.slice(0, 6)` while
// spacing the ring by the FULL count, so a film that named eight parts got six pads on an eight-way ring —
// a visible empty sector where two parts should be, and those two names gone without a word. The picture
// said the core has six connections and a gap; the film said eight. Now the ring divides by the pads actually
// drawn, and a seventh node THROWS. The ceiling is the clock, not the ring (eight pads still clear each other
// at every aspect): trace i draws over 0.18 + 0.07i -> 0.50 + 0.07i and its pulse only runs once it is drawn,
// ending at 0.92. The sixth trace is drawn by 0.85 and its signal reaches the chip; a seventh finishes at the
// very moment the pulses stop, so its signal never arrives, and an eighth never finishes drawing — a part
// shown as NOT connected. A blank node name throws too: a pad with nothing on it is a connection to nothing.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutCubic, easeOutBack, hash01} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {onLight, groundFrom} from '../runtime/light';
import {leading} from '../runtime/cjkType';
import {contentBottom, fitTextPx, inkBlockH, wrapLines} from '../runtime/layout';

export const DURATION = 155; // ~5.2s
const BOARD = '#08130f', COPPER = '#2fd6a0', LIVE = '#7dffcf';
const TITLE_D0 = '#8fd8bf';
const TRACE_OP_D0 = 0.5;   // a trace's stroke alpha (see the light-ground note in the body)

export const MAX_CIRCUIT_NODES = 6;

export const CircuitTrace: React.FC<{title?: string; chip?: string; nodes?: string[]}> = ({
  title: TITLE = 'Wired together', chip: CHIP = 'CORE', nodes: NODES = ['IN', 'MEM', 'I/O', 'NET', 'PWR']} = {}) => {
  const t = useT();
  const dna = useDNA();
  // MOST OF THIS REGISTER ALREADY READS ON PAPER: measured on a light film (`ink_contrast_qa.py`) the median
  // mark is 11.79:1, because the pads and the chip carry their own dark board under mint type. What fails is
  // everything drawn straight ONTO the film's ground — the title, the copper traces, the chip's pins and the
  // signal dots — all of which are a light mint picked against near-black. Those keep their copper HUE and move
  // only their exposure (`groundFrom`), as do the pad and chip EDGES, which touch the page on one side. The
  // dark FILLS stay — a PCB is a dark board, and at a median mark of 11.79:1 nothing measured asks them to
  // move. Null DNA and the eight (dark) presets never reach any of this.
  const lit = dna && onLight(dna) ? groundFrom(dna, {bg: dna.bg}) : null;
  const onGround = (c: string) => (dna && lit ? groundFrom(dna, {bg: dna.bg, fg: c}).fg : c);
  const TRACE = onGround(COPPER), SIGNAL = onGround(LIVE);
  // Alpha is a dark-ground device: half a bright mint still reads as copper on black, and on paper it is half
  // way from the page to the ink. On a light ground the trace is drawn nearly solid, which is what a copper
  // trace looks like on a light board anyway.
  const TRACE_OP = lit ? 0.9 : TRACE_OP_D0;
  // The title sits on the ground with nothing under it, so it is the film's ink rather than a board colour.
  const TITLE_INK = dna ? mix(dna.fg, dna.dim, 0.4) : TITLE_D0;
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 + 10;
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  const chipIn = easeOutBack(clamp01(seg(t, 0.1, 0.32)));
  // satellite pads around the core, each with an L-shaped trace to the core
  // THE PADS RING THE CORE AT A FIXED 320px RADIUS, and each holds a label in a 116x74 box. A Han glyph is
  // a full em, so a Chinese node name wraps out of that box — downward from a pad that is centred on its
  // own point — and the lowest pad's label lands in the caption band (90px of it at 1:1). The label is
  // fitted to the pad it sits in, and the ring's vertical radius yields so the deepest pad clears the zone.
  // Both are 1:1 with the old numbers for the Latin demo, whose names are four characters.
  // Every node once, on a ring divided by the pads drawn — see the header for the ceiling and the throw.
  if (!Array.isArray(NODES) || NODES.length < 1 || NODES.length > MAX_CIRCUIT_NODES) {
    throw new Error(
      `CircuitTrace wires 1-${MAX_CIRCUIT_NODES} nodes to its chip (got ${Array.isArray(NODES) ? NODES.length : typeof NODES}). ` +
      `A seventh trace finishes drawing as the pulses stop, so its signal would never reach the chip. Group ` +
      `the parts into six or fewer, or use a graph register for a larger system.`);
  }
  const nodes = NODES.map((s2, i) => {
    const label = String(s2 ?? '').trim();
    if (!label) throw new Error(`CircuitTrace: node ${i + 1} is empty. Every pad needs a name.`);
    return label;
  });
  const PAD_W = 116, PAD_H = 74;
  const padPx = nodes.reduce(
    (px, s2) => Math.min(px, fitTextPx(s2, PAD_W - 12, 26, {usable: 1})), 26);
  const padLines = Math.max(1, ...nodes.map((s2) => wrapLines(s2, padPx, PAD_W - 12)));
  const padDeep = Math.max(PAD_H, padLines * padPx * 1.15) / 2 + (inkBlockH(padPx) - padPx);
  const ringY = Math.min(320, Math.max(120, contentBottom(W, H) - cy - padDeep));
  const pads = nodes.map((label, i) => {
    const ang = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
    const px = cx + Math.cos(ang) * Math.min(560, W / 2 - 130), py = cy + Math.sin(ang) * ringY;
    return {label, px, py, i, ang};
  });
  const lpath = (x1: number, y1: number, x2: number, y2: number) => `M${x1} ${y1} L${x1} ${y2} L${x2} ${y2}`;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? (`radial-gradient(130% 100% at 50% 42%, #0d2018, ${BOARD} 74%)`), overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: 70, left: 0, right: 0, textAlign: 'center', opacity: titleIn, zIndex: 5,
        color: TITLE_INK, font: '700 30px/1 var(--f-mono, "JetBrains Mono", monospace)', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>
      {/* faint pad grid */}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g opacity={0.16}>{[...Array(28)].map((_, i) => [...Array(16)].map((__, j) =>
          <circle key={`${i}-${j}`} cx={60 + i * 66} cy={40 + j * 66} r={2} fill={TRACE} />))}</g>
        {/* traces */}
        {pads.map((p, i) => {
          const draw = easeOutCubic(clamp01(seg(t, 0.18 + i * 0.07, 0.5 + i * 0.07)));
          const len = Math.abs(p.px - cx) + Math.abs(p.py - cy);
          return <path key={i} d={lpath(p.px, p.py, cx, cy)} fill="none" stroke={TRACE} strokeWidth={5}
            strokeLinejoin="round" opacity={TRACE_OP} strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />;
        })}
      </svg>
      {/* signal pulses (rendered as absolutely-positioned dots for clean movement) */}
      {pads.map((p, i) => {
        const draw = clamp01(seg(t, 0.18 + i * 0.07, 0.5 + i * 0.07));
        const pulse = clamp01(seg(t, 0.52 + i * 0.05, 0.92));
        if (draw < 0.98) return null;
        // travel along the L path: first vertical (px,py)->(px,cy) then horizontal ->(cx,cy)
        const seg1 = clamp01(pulse * 2), seg2 = clamp01(pulse * 2 - 1);
        const x = p.px + (cx - p.px) * seg2;
        const y = p.py + (cy - p.py) * seg1;
        // the pulse's halo is a dark-ground device — on paper a mint bloom is a pale wash that only softens the
        // dot's own edge, and it is the dot that says where the signal is
        return <div key={i} style={{position: 'absolute', left: x, top: y, width: 14, height: 14, borderRadius: '50%',
          transform: 'translate(-50%,-50%)', background: SIGNAL, boxShadow: lit ? 'none' : `0 0 16px ${LIVE}`,
          opacity: pulse < 1 ? 1 : 0}} />;
      })}
      {/* satellite pads */}
      {pads.map((p, i) => {
        const on = easeOutBack(clamp01(seg(t, 0.12 + i * 0.06, 0.34 + i * 0.06)));
        return <div key={i} style={{position: 'absolute', left: p.px, top: p.py, transform: `translate(-50%,-50%) scale(${on})`,
          opacity: clamp01(on), width: 116, height: 74, borderRadius: 10, background: '#0c241a',
          // the pad's EDGE touches the ground, so on paper it is the exposed copper (it still reads against
          // the pad's own dark fill); the label inside it does not, and keeps the board's signal green
          border: `2px solid ${lit ? TRACE : COPPER}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: LIVE, font: `800 ${padPx}px/${leading(p.label, 1)} var(--f-mono, "JetBrains Mono", monospace)`,
          boxShadow: lit ? 'none' : `0 0 24px ${COPPER}44`}}>{p.label}</div>;
      })}
      {/* central chip */}
      <div style={{position: 'absolute', left: cx, top: cy, transform: `translate(-50%,-50%) scale(${chipIn})`,
        width: 260, height: 200, borderRadius: 14, background: 'linear-gradient(160deg, #103326, #0a1f17)',
        // same rule as the pads: the chip's edge is the one part of it that sits against the page
        border: `3px solid ${lit ? SIGNAL : LIVE}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#eafff6', font: `900 56px/${leading(CHIP, 1)} var(--f-body, Inter, system-ui, sans-serif)`,
        // THE CHIP'S OUTER GLOW IS WHAT THE GATE WAS READING THE CHIP'S EDGE AGAINST. On paper a 60px mint bloom
        // is not light, it is a pale wash lying on the page — the mark render shows the chip's own rim measured
        // against that wash instead of against the paper. Lit, the chip keeps only the inset light that says it
        // is powered; the board it sits on is dark either way, so nothing about the chip stops reading.
        boxShadow: lit
          ? (t > 0.5 ? `inset 0 0 30px ${COPPER}44` : 'none')
          : (t > 0.5 ? `0 0 60px ${LIVE}66, inset 0 0 30px ${COPPER}44` : `0 0 20px ${COPPER}44`)}}>
        {/* chip pins — copper on the film's ground, not on the chip, so they follow the trace's exposure */}
        {[...Array(8)].map((_, k) => <div key={k} style={{position: 'absolute', top: -12, left: 24 + k * 28, width: 12, height: 12, background: TRACE}} />)}
        {CHIP}
      </div>
    </AbsoluteFill>
  );
};
export default CircuitTrace;
